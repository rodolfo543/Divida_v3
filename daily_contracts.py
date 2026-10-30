"""PU por dia útil, calculado por índice e juros, sem interpolar PUs de eventos."""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

D = Decimal


def trunc(value, places=8):
    return value.quantize(D(1).scaleb(-places), rounding=ROUND_DOWN)


def parse(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%d/%m/%Y").date()


def month_shift(day, count):
    total = day.year * 12 + day.month - 1 + count
    return date(total // 12, total % 12 + 1, 15)


def prepared_indices(module):
    indices, source = module.obter_ipca_numero_indice_sidra()
    result = module.preencher_indices_futuros(indices)
    return result[0], source


def update_nominal(balance, start, end, indices, module, lag=1):
    """Reinicia a atualização em cada aniversário, truncando o VNA a 8 casas."""
    cursor = start
    while cursor < end:
        previous = date(cursor.year, cursor.month, 15)
        if cursor < previous:
            previous = month_shift(previous, -1)
        following = month_shift(previous, 1)
        stop = min(following, end)
        nik = month_shift(following, -lag).strftime("%Y-%m")
        nik_previous = month_shift(following, -lag - 1).strftime("%Y-%m")
        du = module.dias_uteis(cursor, stop)
        dut = module.dias_uteis(previous, following)
        if du:
            ratio = indices[nik] / indices[nik_previous]
            factor = trunc(ratio ** (D(du) / D(dut)))
            balance = trunc(balance * factor)
        cursor = stop
    return balance


def calculate_daily(module, events, *, start=None, rate=None, lag=1,
                    migration=None, old_rate=None, grace_end=None, indices=None):
    indices = indices if indices is not None else prepared_indices(module)[0]
    start = start or module.DATA_INICIO_RENTABILIDADE
    rate = rate if rate is not None else module.TAXA_AA
    schedule = []
    for event in events:
        value = event.get("Data_Pgto") or event.get("Data_Ref")
        effective = parse(value)
        while not module.eh_dia_util(effective):
            effective += timedelta(days=1)
        reference = parse(event.get("Data_Ref") or value)
        schedule.append((effective, reference, event))
    schedule.sort(key=lambda item: item[0])
    end = schedule[-1][0]
    result = []
    pointer = 0
    current = start
    while current <= end:
        if not module.eh_dia_util(current):
            current += timedelta(days=1)
            continue
        while pointer < len(schedule) and schedule[pointer][0] < current:
            pointer += 1
        previous = schedule[pointer - 1] if pointer else None
        base_date = previous[1] if previous else start
        interest_start = previous[0] if previous else start
        base = D(str(previous[2]["PU_VNa_Fim"])) if previous else module.PU_INICIAL
        if grace_end and current <= grace_end:
            base_date = interest_start = start
            base = module.PU_INICIAL
        nominal = base
        if not migration or current > migration:
            nominal = update_nominal(base, max(base_date, migration) if migration else base_date,
                                     current, indices, module, lag)
        period_rate = old_rate if migration and current <= migration else rate
        du = module.dias_uteis(interest_start, current)
        factor = ((1 + period_rate) ** (D(du) / D(252))).quantize(D("0.000000001"), rounding=ROUND_HALF_UP)
        interest = trunc(nominal * (factor - 1))
        full = trunc(nominal + interest)
        event = schedule[pointer][2] if pointer < len(schedule) and schedule[pointer][0] == current else None
        amort = D(str(event.get("PU_Amort", 0))) if event else D(0)
        paid = D(str(event.get("PU_Total_Pago", event.get("PU_Total", 0)))) if event else D(0)
        residual = D(str(event["PU_VNa_Fim"])) if event else full
        if event:
            nominal = D(str(event.get("PU_VNa_Atualizado", nominal)))
            interest = D(str(event.get("PU_Juros", interest)))
            full = trunc(nominal + interest)
        result.append({
            "Data": current.strftime("%d/%m/%Y"),
            "Data_Inicio_Periodo": interest_start.strftime("%d/%m/%Y"),
            "Tipo_Dia": "PAGAMENTO" if paid else ("CAPITALIZACAO" if event else "ACUMULACAO"),
            "Valor_Nominal": nominal, "Valor_dos_Juros": interest,
            "PU_Cheio": full, "PU_Vazio": residual,
            "Amortizacao": amort, "Total": paid,
            "Juros_Pago": D(str(event.get("PU_Juros", 0))) if paid else D(0),
            "Fator_Juros": factor,
            "Fonte_PU": "Cálculo independente: índices IPCA, projeção ANBIMA e juros em 252 DU",
        })
        current += timedelta(days=1)
    return result
