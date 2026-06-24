from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "operations"
TARGET_XLSX = Path(r"C:\Users\rodolfo.crotti\AXS ENERGIA S A\Financeiro - Documentos\000 - FD\Rodolfo relatórios\PMT.xlsx")
EXPORT_FILES = [
    ("axs01--primeira.json", "1ª Emissão"),
    ("axs01--segunda.json", "2ª Emissão"),
    ("axs02--cri.json", "CRI"),
    ("axs02--deb.json", "Debênture"),
    ("axs03.json", ""),
    ("axs04.json", ""),
    ("axs05--primeira.json", "1ª Emissão"),
    ("axs05--segunda.json", "2ª Emissão"),
    ("axs06--primeira.json", "1ª Emissão"),
    ("axs06--segunda.json", "2ª Emissão"),
    ("axs07.json", ""),
    ("axs08.json", ""),
    ("axs09.json", ""),
    ("axs10.json", ""),
    ("axs11.json", ""),
    ("axsgoias.json", ""),
]
COMPANY_REGISTRY = {
    "axs01": {"number": 10, "name": "AXS ENERGIA UNIDADE 01 LTDA"},
    "axs02": {"number": 11, "name": "AXS ENERGIA UNIDADE 02 S.A."},
    "axs03": {"number": 16, "name": "AXS ENERGIA UNIDADE 03 LTDA"},
    "axs04": {"number": 17, "name": "AXS ENERGIA UNIDADE 04 S.A."},
    "axs05": {"number": 18, "name": "AXS ENERGIA UNIDADE 05 S.A."},
    "axs06": {"number": 19, "name": "AXS ENERGIA UNIDADE 06 S.A."},
    "axs07": {"number": 25, "name": "AXS ENERGIA UNIDADE 07 S.A."},
    "axs08": {"number": 26, "name": "AXS ENERGIA UNIDADE 08 S.A."},
    "axs09": {"number": 27, "name": "AXS ENERGIA UNIDADE 09 S.A."},
    "axs10": {"number": 28, "name": "AXS ENERGIA UNIDADE 10 S.A."},
    "axs11": {"number": 29, "name": "AXS ENERGIA UNIDADE 11 S.A."},
    "axsgoias": {"number": 32, "name": "AXS ENERGIA UFV GOIAS SPE LTDA"},
}
HEADERS = [
    "Número empresa",
    "Empresa",
    "Data de pagamento",
    "Operação",
    "Emissão / instrumento",
    "Valor PMT",
    "Juros",
    "Amortização",
    "Saldo após pagamento",
    "Indexador",
    "Atualizado em",
]


def parse_br_date(value: str) -> datetime:
    return datetime.strptime(value, "%d/%m/%Y")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def company_info(operation_id: str, fallback_name: str) -> dict[str, str | int]:
    info = COMPANY_REGISTRY.get(operation_id, {})
    return {
        "number": info.get("number", ""),
        "name": info.get("name", fallback_name),
    }


def future_payment_rows(payload: dict, emission_label: str) -> list[dict]:
    today = datetime.now().date()
    operation = payload["operation"]
    operation_id = operation.get("id") or ""
    company = company_info(operation_id, operation.get("issuer") or operation.get("label") or "-")
    rows: list[dict] = []
    for item in payload.get("table_series", []):
        date_text = item.get("date")
        payment = item.get("payment") or 0
        if not date_text or payment <= 0:
            continue
        payment_date = parse_br_date(date_text).date()
        if payment_date < today:
            continue
        rows.append(
            {
                "date": payment_date,
                "date_text": date_text,
                "company_number": company["number"],
                "company_name": company["name"],
                "operation": operation.get("label") or "-",
                "emission": emission_label or item.get("component_label") or operation.get("badge") or "-",
                "payment": payment,
                "interest": item.get("interest") or 0,
                "amortization": item.get("amortization") or 0,
                "balance": item.get("balance") or 0,
                "indexer": operation.get("indexer") or "-",
            }
        )
    return rows


def collect_rows() -> list[dict]:
    rows: list[dict] = []
    for filename, emission_label in EXPORT_FILES:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        payload = load_json(path)
        rows.extend(future_payment_rows(payload, emission_label))
    rows.sort(
        key=lambda item: (
            item["date"],
            str(item["company_number"]),
            str(item["company_name"]),
            item["operation"],
            item["emission"],
        )
    )
    return rows


def ensure_workbook() -> Workbook:
    if TARGET_XLSX.exists():
        return load_workbook(TARGET_XLSX)
    workbook = Workbook()
    workbook.save(TARGET_XLSX)
    return workbook


def format_sheet(sheet) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="16324F")
    header_font = Font(color="FFFFFF", bold=True)
    widths = {
        "A": 16,
        "B": 34,
        "C": 18,
        "D": 14,
        "E": 24,
        "F": 18,
        "G": 18,
        "H": 18,
        "I": 20,
        "J": 28,
        "K": 22,
    }
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    for column in ("F", "G", "H", "I"):
        for cell in sheet[column][1:]:
            cell.number_format = 'R$ #,##0.00'


def write_rows(rows: list[dict]) -> None:
    workbook = ensure_workbook()
    sheet = workbook["Plan1"] if "Plan1" in workbook.sheetnames else workbook.active
    sheet.title = "Plan1"
    if sheet.max_row:
        sheet.delete_rows(1, sheet.max_row)
    sheet.append(HEADERS)
    updated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for item in rows:
        sheet.append(
            [
                item["company_number"],
                item["company_name"],
                item["date_text"],
                item["operation"],
                item["emission"],
                item["payment"],
                item["interest"],
                item["amortization"],
                item["balance"],
                item["indexer"],
                updated_at,
            ]
        )
    format_sheet(sheet)
    workbook.save(TARGET_XLSX)


def main() -> None:
    rows = collect_rows()
    write_rows(rows)
    print(f"PMT.xlsx atualizada com {len(rows)} linhas futuras em {TARGET_XLSX}")


if __name__ == "__main__":
    main()
