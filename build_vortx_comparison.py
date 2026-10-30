"""Monta a conciliação separada, lendo os cálculos publicados sem recalculá-los."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = "https://apis.vortx.com.br/vxsite/api/operacao"
FIELDS = ("full", "empty", "nominal", "interest", "paid_interest", "ordinary", "extra", "incorporation", "total")
D = Decimal


def number(value):
    if value is None or value == "":
        return None
    return format(D(str(value)).quantize(D(".00000001"), rounding=ROUND_HALF_UP), ".8f")


def iso_day(value):
    text = str(value or "")
    if len(text) >= 10 and text[4:5] == "-":
        return date.fromisoformat(text[:10]).isoformat()
    return datetime.strptime(text, "%d/%m/%Y").date().isoformat()


def first(raw, *keys):
    return next((raw[key] for key in keys if raw.get(key) is not None and raw.get(key) != ""), None)


def local_row(row, quantity):
    raw = row.get("raw", {})
    estimated = str(row.get("sort_key", "")).startswith("daily-")
    extra = first(raw, "Amortizacao_Extraordinaria", "PU_Amort_Extraordinaria", "PU_Amex_Dia")
    # Ausência do campo é zero apenas quando o modelo não possui AMEX nesse dia.
    extra = D(str(extra or 0))
    amort = row.get("pu_amort")
    paid = first(raw, "Juros_Pago", "PU_Juros_Pago_Dia", "PU_Juros_Pago")
    if paid is None and quantity:
        paid = D(str(row.get("interest", 0))) / quantity
    incorporation = first(raw, "Juros_Capitalizado", "PU_Juros_Capitalizado_Dia", "PU_Juros_Incorporado", "PU_Juros_Capitalizado")
    if incorporation is None:
        kind = str(raw.get("Tipo_Dia", "")) + str(raw.get("Tipo_Evento", ""))
        if ("CAPITALIZ" in kind or "INCORPOR" in kind) and not row.get("payment"):
            incorporation = row.get("pu_juros")
        else:
            incorporation = 0
    full, total = number(row.get("pu_cheio")), number(row.get("pu_total"))
    result = {
        "d": iso_day(row["date"]),
        "full": full,
        # A Vórtx publica o PU ex-evento. Alguns motores chamam o nominal de
        # "PU vazio"; harmonizar a definição aqui evita uma falsa divergência.
        "empty": number(D(full) - D(total)) if full is not None and total is not None else None,
        "empty_model": number(row.get("pu_vazio")),
        "nominal": number(row.get("valor_nominal")), "interest": number(row.get("valor_juros", row.get("pu_juros"))),
        "paid_interest": number(paid),
        "ordinary": number(D(str(amort)) - extra) if amort is not None else None,
        "extra": number(extra), "incorporation": number(incorporation), "total": total,
    }
    if estimated:
        # O raw de uma linha interpolada aponta para o próximo vencimento,
        # não para um evento do próprio dia. Não repetir seus fluxos diariamente.
        for field in ("paid_interest", "ordinary", "extra", "incorporation", "total"):
            result[field] = None
    return result


def reference_row(row):
    return {
        "d": iso_day(row["paymentDate"]), "full": number(row.get("unitPriceFull")),
        "empty": number(row.get("unitPriceEmpty")), "nominal": number(row.get("nominalValue")),
        "interest": number(row.get("interestValue")), "paid_interest": number(row.get("interestCashflowAmount")),
        "ordinary": number(row.get("ordinaryCashflowAmount")), "extra": number(row.get("extraordinaryAmortization")),
        "incorporation": number(row.get("incorporationCashflowAmount")), "total": number(row.get("total")),
    }


def request_json(url):
    request = Request(url, headers={"User-Agent": "AXS-Debt-Comparison/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"), parse_float=D)


def collect_reference(config, previous=None, fetch=request_json):
    op_id = config["operation_id"]
    result = {"collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "errors": [], "cached": False}
    for key, suffix in (("history", "/preco-unitario/historico-pagamentos"), ("preview", "/preco-unitario/previa-pagamentos")):
        try:
            raw = fetch(f"{BASE}/{op_id}{suffix}")
            if raw.get("success") is not True or not isinstance(raw.get("unitPrices"), list):
                raise ValueError("Resposta sem histórico válido")
            result[key] = sorted((reference_row(row) for row in raw["unitPrices"]), key=lambda row: row["d"])
            result[key + "_collected_at"] = result["collected_at"]
        except Exception as error:
            result[key] = (previous or {}).get(key, [])
            result[key + "_collected_at"] = (previous or {}).get(key + "_collected_at", (previous or {}).get("collected_at"))
            result["errors"].append(f"{key}: {error}")
            result["cached"] = True
    try:
        raw = fetch(f"{BASE}/{op_id}")
        operation = raw["operations"][0]["operation"]
        if operation.get("ifCode") != config["code"]:
            raise ValueError("Código IF retornado difere do cadastro")
        result["terms"] = {key: operation.get(key) for key in (
            "ifCode", "isinCode", "issue", "serie", "firstIntegralizationDate", "issueDate", "issueDuty",
            "quantity", "nominalUnitValue", "totalVolume", "interestRate", "index", "percentageIndex",
            "periodoAmortizacao", "periodoPagamentoJuros",
        )}
        result["terms_collected_at"] = result["collected_at"]
    except Exception as error:
        result["terms"] = (previous or {}).get("terms", {})
        result["terms_collected_at"] = (previous or {}).get("terms_collected_at")
        result["errors"].append(f"ficha: {error}")
    return result


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")


def build_comparison(root=ROOT, *, offline=False):
    catalog = json.loads((root / "vortx_catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "data/operations.json").read_text(encoding="utf-8"))
    local_as_of = str(manifest["generated_at_iso"])[:10]
    cutoff = (date.fromisoformat(local_as_of) + timedelta(days=180)).isoformat()
    sources = {}
    entries = []
    for config in catalog:
        op = config["operation"]
        if op not in sources:
            path = root / "data/operations" / f"{op}.json"
            content = path.read_bytes()
            sources[op] = (json.loads(content, parse_float=D), hashlib.sha256(content).hexdigest())
        payload, digest = sources[op]
        view = payload["variants"][config["variant"]] if config["variant"] else payload
        fields = {field["label"]: field["value"] for field in view["operation"]["overview_fields"]}
        quantity = D(str(fields["Quantidade emitida"]))
        rows = view.get("daily_pu_series", [])
        if not rows:
            raise ValueError(f"Série diária local ausente: {config['code']}")
        instrument = {**config, "quantity": str(quantity), "local_as_of": local_as_of,
                      "local_generated_at": payload.get("generated_at"), "local_source_sha256": digest,
                      "local_method": "estimated" if any(str(row.get("sort_key", "")).startswith("daily-") for row in rows) else "calculated",
                      "local_rows": [local_row(row, quantity) for row in rows if iso_day(row["date"]) <= cutoff]}
        path = root / "data/vortx/instruments" / f"{config['code']}.json"
        previous = json.loads(path.read_text(encoding="utf-8")).get("reference") if path.exists() else None
        entries.append((instrument, previous))
    def collect(entry):
        instrument, previous = entry
        if offline and not previous:
            raise ValueError(f"Sem retrato Vórtx anterior para uso offline: {instrument['code']}")
        reference = previous if offline else collect_reference(instrument, previous)
        instrument["reference"] = reference
        return instrument
    with ThreadPoolExecutor(max_workers=2) as pool:
        instruments = list(pool.map(collect, entries))
    index = {"schema_version": 1, "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "local_as_of": local_as_of, "local_generated_at": manifest.get("generated_at"),
             "instruments": []}
    for instrument in instruments:
        filename = f"instruments/{instrument['code']}.json"
        for directory in (root / "data/vortx", root / "docs/data/vortx"):
            write(directory / filename, instrument)
        index["instruments"].append({key: instrument[key] for key in (
            "code", "operation_id", "operation", "variant", "label", "series", "quantity", "local_method",
        )} | {"pending": instrument.get("pending", False), "file": filename})
        print(f"Conciliação {instrument['code']}: {len(instrument['reference']['history'])} referências", flush=True)
    for directory in (root / "data/vortx", root / "docs/data/vortx"):
        write(directory / "manifest.json", index)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Atualiza apenas o espelho local e preserva a última referência coletada")
    args = parser.parse_args()
    build_comparison(offline=args.offline)
