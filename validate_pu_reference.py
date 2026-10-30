"""Conciliação externa: lê uma planilha de referência, sem alimentar os motores.

Exemplo: python validate_pu_reference.py --reference "C:/.../PUdia.xlsx" --date 30/10/2026 --output "C:/.../resultado.json"
"""
import argparse
import json
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent
PENDING = {"AXSC12", "AXSC22", "AXSI11"}


def reconcile(reference, target_date):
    book = openpyxl.load_workbook(reference, read_only=True, data_only=True)
    official = {str(row[0]): D(str(row[3])) for row in book.active.iter_rows(min_row=2, values_only=True)
                if row[1] == target_date and row[3] is not None}
    book.close()
    manifest = json.loads((ROOT / "data/operations.json").read_text(encoding="utf-8"))
    report = []
    for operation in manifest["operations"]:
        if operation["id"] == "geral":
            continue
        payload = json.loads((ROOT / "data/operations" / f"{operation['id']}.json").read_text(encoding="utf-8"))
        views = {key: view for key, view in payload.get("variants", {}).items() if key != "total"} or {"": payload}
        for variant, view in views.items():
            code = next(field["value"] for field in view["operation"]["identity_fields"] if field["label"] == "Código IF")
            daily = next(row for row in view["daily_pu_series"] if row["date"] == target_date)
            calculated = D(str(daily["pu_cheio"]))
            expected = official[code]
            report.append({
                "operation": operation["id"], "variant": variant, "code": code,
                "date": target_date, "calculated": str(calculated), "reference": str(expected),
                "difference": str(calculated - expected),
                "same_cents": calculated.quantize(D(".01"), rounding=ROUND_HALF_UP) == expected.quantize(D(".01"), rounding=ROUND_HALF_UP),
                "same_eight_places": calculated.quantize(D(".00000001")) == expected.quantize(D(".00000001")),
                "pending_external_confirmation": code in PENDING,
            })
    return {"reference_file": str(Path(reference).resolve()), "date": target_date, "items": report}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = reconcile(args.reference, args.date)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    validated = [row for row in result["items"] if not row["pending_external_confirmation"]]
    for row in result["items"]:
        print(row["code"], row["calculated"], row["reference"], row["difference"], "PENDENTE" if row["pending_external_confirmation"] else ("CENTAVOS OK" if row["same_cents"] else "DIVERGENTE"))
    print(f"Centavos: {sum(row['same_cents'] for row in validated)}/{len(validated)}; 8 casas: {sum(row['same_eight_places'] for row in validated)}/{len(validated)}.")
    raise SystemExit(0 if all(row["same_cents"] for row in validated) else 1)
