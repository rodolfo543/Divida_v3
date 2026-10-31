"""Produtório IPCA contratual, independente de qualquer preço de referência."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN


def truncate(value, places):
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN)


def shift_month(day, offset):
    total = day.year * 12 + day.month - 1 + offset
    return date(total // 12, total % 12 + 1, 15)


def update_nominal(balance, start, end, indices, sources, *, lag, business_days, is_business_day):
    """Fatores a 8 casas, mais recente primeiro, intermediários a 16 casas.

    O saldo-base só é reiniciado em eventos financeiros. Aniversários delimitam
    fatores do produtório, sem truncar um saldo-base novo em cada mês.
    """
    def roll(day):
        while not is_business_day(day):
            day += timedelta(days=1)
        return day

    start, end = roll(start), roll(end)
    if end < start:
        raise ValueError("Data de atualização anterior à base do IPCA")
    original = truncate(balance, 8)
    nominal = original
    cursor = start
    factors, details = [], []
    while cursor < end:
        previous = date(cursor.year, cursor.month, 15)
        if cursor < roll(previous):
            previous = shift_month(previous, -1)
        following = shift_month(previous, 1)
        stop = min(roll(following), end)
        month = shift_month(following, -lag).strftime("%Y-%m")
        month_previous = shift_month(following, -lag - 1).strftime("%Y-%m")
        nik, nik_previous = indices[month], indices[month_previous]
        dup = business_days(cursor, stop)
        dut = business_days(roll(previous), roll(following))
        factor = truncate((nik / nik_previous) ** (Decimal(dup) / Decimal(dut)), 8)
        factors.append(factor)
        product = Decimal(1)
        for item in reversed(factors):
            product = truncate(product * item, 16)
        before = nominal
        nominal = truncate(original * truncate(product, 8), 8)
        details.append({
            "Data_Aniv_IPCA": stop.strftime("%d/%m/%Y"),
            "Mes_NIk": month, "Mes_NIk_1": month_previous,
            "NIk": nik, "NIk_1": nik_previous,
            "Fonte_NIk": sources.get(month, ""),
            "DUP_IPCA": dup, "DUT_IPCA": dut,
            "Fator_C_IPCA": factor, "PU_Antes_IPCA": before,
            "PU_Apos_IPCA": nominal,
        })
        cursor = stop
    return nominal, details, end
