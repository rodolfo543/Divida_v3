"""Insumos de mercado independentes dos PUs: projeção corrente da ANBIMA.

O cache guarda a publicação de origem e sua data, nunca resultados de títulos.
As projeções Focus de prazo mais longo são mantidas pelas rotinas existentes.
"""
import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://www.anbima.com.br/informacoes/indicadores/"
CACHE = Path(__file__).resolve().parents[1] / "data" / "market" / "anbima_ipca.json"
MESES = {m: i + 1 for i, m in enumerate("jan fev mar abr mai jun jul ago set out nov dez".split())}


@lru_cache(maxsize=1)
def projecao_anbima():
    try:
        request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=25) as response:
            html = response.read().decode("latin-1")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        match = re.search(r"IPCA.{0,180}?Proje.{0,30}?\(([a-z]{3})/(\d{2})\).*?(\d+,\d+)", text, re.I)
        publication = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}:\d{2})", text)
        if not match or not publication:
            raise ValueError("Projeção IPCA ou data da publicação não localizada na ANBIMA")
        snapshot = {
            "source": URL,
            "published_at": " ".join(publication.groups()),
            "retrieved_at": date.today().isoformat(),
            "month": f"20{match[2]}-{MESES[match[1].lower()]:02d}",
            "rate": str(Decimal(match[3].replace(",", ".")) / 100),
        }
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        if not CACHE.exists():
            raise RuntimeError("Projeção ANBIMA indisponível e sem publicação salva")
        snapshot = json.loads(CACHE.read_text(encoding="utf-8"))
    return snapshot


def aplicar_projecao_anbima(indices, fontes, oficiais, decimal_places=None):
    """Substitui somente o mês projetado vigente; nunca altera índice oficial."""
    snapshot = projecao_anbima()
    compact = "-" not in next(iter(indices))
    month = snapshot["month"].replace("-", "") if compact else snapshot["month"]
    if month in oficiais or month not in indices:
        return
    previous = max((key for key in indices if key < month), default=None)
    if previous is None:
        raise ValueError("Índice anterior à projeção ANBIMA ausente")
    old = indices[month]
    new = indices[previous] * (1 + Decimal(snapshot["rate"]))
    if decimal_places is not None:
        new = new.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)
    scale = new / old
    indices[month] = new
    fontes[month] = f"ANBIMA {snapshot['published_at']} | {snapshot['source']}"
    # Preserva a variação Focus de cada mês posterior, sem salto de base.
    for key in sorted(key for key in indices if key > month):
        indices[key] *= scale
