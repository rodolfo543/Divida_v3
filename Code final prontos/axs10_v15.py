# -*- coding: utf-8 -*-
"""Calculo da 2a emissao, 1a serie, da AXS Energia Unidade 10.

Termos contratuais considerados:
- Emissao: 15/05/2026; inicio da rentabilidade: 27/05/2026.
- 162.500 debentures com PU de emissao de R$ 1.000,00.
- Atualizacao monetaria mensal pelo IPCA.
- Juros de 13,6455% a.a., base 252 dias uteis.
- Cinco incorporacoes semestrais de juros ate 15/11/2028.
- Juros e amortizacao semestrais de 15/05/2029 a 15/05/2041.

O motor de IPCA e Focus e compartilhado com a AXS Goias para manter a mesma
metodologia e as mesmas fontes utilizadas pelas demais operacoes do portal.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

getcontext().prec = 34

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "axs_goias_v1.py"

DATA_EMISSAO = date(2026, 5, 15)
DATA_INICIO_RENTABILIDADE = date(2026, 5, 27)
DATA_VENCIMENTO = date(2041, 5, 15)
TAXA_AA = Decimal("0.136455")
QUANTIDADE = Decimal("162500")
PU_INICIAL = Decimal("1000.00000000")
VORTX_OPERATION_ID = 97386
VORTX_PU_HISTORY_URL = (
    f"https://apis.vortx.com.br/vxsite/api/operacao/{VORTX_OPERATION_ID}"
    "/preco-unitario/historico-pagamentos"
)

DATAS_INCORPORACAO_NOMINAIS = [
    date(2026, 11, 15),
    date(2027, 5, 15),
    date(2027, 11, 15),
    date(2028, 5, 15),
    date(2028, 11, 15),
]

# Anexo II da Escritura de Emissao. Os percentuais incidem sobre o saldo do
# Valor Nominal Unitario Atualizado existente em cada data.
CRONOGRAMA_RAW = [
    ("2029-05-15", "0.5000"), ("2029-11-15", "0.5025"),
    ("2030-05-15", "1.0570"), ("2030-11-15", "1.0683"),
    ("2031-05-15", "1.3894"), ("2031-11-15", "1.4592"),
    ("2032-05-15", "3.8140"), ("2032-11-15", "4.0024"),
    ("2033-05-15", "4.1105"), ("2033-11-15", "3.9684"),
    ("2034-05-15", "4.3218"), ("2034-11-15", "4.4782"),
    ("2035-05-15", "4.9136"), ("2035-11-15", "5.4347"),
    ("2036-05-15", "6.0445"), ("2036-11-15", "6.8221"),
    ("2037-05-15", "7.7272"), ("2037-11-15", "8.8815"),
    ("2038-05-15", "10.5027"), ("2038-11-15", "13.6206"),
    ("2039-05-15", "16.5325"), ("2039-11-15", "20.8645"),
    ("2040-05-15", "27.6699"), ("2040-11-15", "40.2696"),
    ("2041-05-15", "100.0000"),
]


def _carregar_engine_ipca():
    module_name = "axs10_ipca_shared_engine"
    spec = importlib.util.spec_from_file_location(module_name, ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar o motor IPCA: {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = _carregar_engine_ipca()


def trunc_dec(value: Decimal, casas: int = 8) -> Decimal:
    return value.quantize(Decimal("1").scaleb(-casas), rounding=ROUND_DOWN)


def round_dec(value: Decimal, casas: int = 2) -> Decimal:
    return value.quantize(Decimal("1").scaleb(-casas), rounding=ROUND_HALF_UP)


def eh_dia_util(dt: date) -> bool:
    return bool(_ENGINE.eh_dia_util(dt))


def proximo_dia_util(dt: date) -> date:
    resultado = dt
    while not eh_dia_util(resultado):
        resultado += timedelta(days=1)
    return resultado


def iter_dias_uteis(inicio_exclusivo: date, fim_inclusivo: date) -> Iterable[date]:
    dt = inicio_exclusivo + timedelta(days=1)
    while dt <= fim_inclusivo:
        if eh_dia_util(dt):
            yield dt
        dt += timedelta(days=1)


CRONOGRAMA_NOMINAL = [
    (datetime.strptime(data_txt, "%Y-%m-%d").date(), Decimal(percentual) / Decimal("100"))
    for data_txt, percentual in CRONOGRAMA_RAW
]
CRONOGRAMA = [(proximo_dia_util(dt), percentual) for dt, percentual in CRONOGRAMA_NOMINAL]
DATAS_INCORPORACAO_JUROS = [proximo_dia_util(dt) for dt in DATAS_INCORPORACAO_NOMINAIS]

# Configura o motor compartilhado antes de chamar suas rotinas de IPCA/Focus.
_ENGINE.DATA_EMISSAO = DATA_EMISSAO
_ENGINE.DATA_INICIO_RENTABILIDADE = DATA_INICIO_RENTABILIDADE
_ENGINE.DATAS_INCORPORACAO_JUROS = DATAS_INCORPORACAO_JUROS
_ENGINE.TAXA_AA = TAXA_AA
_ENGINE.QUANTIDADE = QUANTIDADE
_ENGINE.PU_INICIAL = PU_INICIAL
_ENGINE.CRONOGRAMA_RAW = CRONOGRAMA_RAW
_ENGINE.CRONOGRAMA = CRONOGRAMA


def obter_ipca_numero_indice_sidra() -> Tuple[Dict[str, Decimal], str]:
    return _ENGINE.obter_ipca_numero_indice_sidra()


def preencher_indices_futuros(indices: Dict[str, Decimal]) -> Tuple[Dict[str, Decimal], Dict[str, str]]:
    return _ENGINE.preencher_indices_futuros(indices)


def fator_juros_252(dias_uteis: int) -> Decimal:
    bruto = Decimal(str((1.0 + float(TAXA_AA)) ** (dias_uteis / 252.0)))
    return bruto.quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)


def fator_ipca(indices: Dict[str, Decimal], data_aniversario: date) -> Tuple[Decimal, str, str, Decimal, Decimal]:
    """Usa os indices divulgados nos meses M-1 e M-2 (referencias SIDRA M-2/M-3)."""
    mes_nik = _ENGINE.mes_str(_ENGINE.add_months(data_aniversario, -2))
    mes_nik_1 = _ENGINE.mes_str(_ENGINE.add_months(data_aniversario, -3))
    if mes_nik not in indices or mes_nik_1 not in indices:
        raise RuntimeError(f"IPCA necessario nao disponivel: NIk={mes_nik}, NIk_1={mes_nik_1}.")
    ni_k = indices[mes_nik]
    ni_k_1 = indices[mes_nik_1]
    return trunc_dec(ni_k / ni_k_1, 8), mes_nik, mes_nik_1, ni_k, ni_k_1


def fator_ipca_prorata(
    indices: Dict[str, Decimal],
    data_aniversario: date,
    inicio: date,
) -> Tuple[Decimal, str, str, Decimal, Decimal, int, int]:
    fator_cheio, mes_nik, mes_nik_1, ni_k, ni_k_1 = fator_ipca(indices, data_aniversario)
    mes_anterior = _ENGINE.add_months(data_aniversario, -1)
    inicio_aniversario = date(mes_anterior.year, mes_anterior.month, 15)
    dias_decorridos = _ENGINE.dias_uteis(inicio, data_aniversario)
    dias_periodo = _ENGINE.dias_uteis(inicio_aniversario, data_aniversario)
    bruto = Decimal(str(float(ni_k / ni_k_1) ** (dias_decorridos / dias_periodo)))
    return (
        trunc_dec(bruto, 8), mes_nik, mes_nik_1, ni_k, ni_k_1,
        dias_decorridos, dias_periodo,
    )


def _fator_ipca_parcial(
    indices: Dict[str, Decimal],
    inicio: date,
    fim: date,
    proximo_aniversario: date,
) -> Decimal:
    if fim <= inicio:
        return Decimal("1.00000000")

    _, _, _, ni_k, ni_k_1 = fator_ipca(indices, proximo_aniversario)
    mes_anterior = _ENGINE.add_months(proximo_aniversario, -1)
    inicio_aniversario = date(mes_anterior.year, mes_anterior.month, 15)
    dias_decorridos = _ENGINE.dias_uteis(inicio, fim)
    dias_periodo = _ENGINE.dias_uteis(inicio_aniversario, proximo_aniversario)
    if dias_periodo <= 0 or dias_decorridos <= 0:
        return Decimal("1.00000000")

    fator = Decimal(str(float(ni_k / ni_k_1) ** (dias_decorridos / dias_periodo)))
    return trunc_dec(fator, 8)


def atualizar_ipca_ate_data(
    saldo_abertura: Decimal,
    data_base_ipca: date,
    data_calculo: date,
    indices: Dict[str, Decimal],
) -> Decimal:
    """Atualiza o VNA ate uma data qualquer, inclusive no meio do mes."""
    saldo = trunc_dec(saldo_abertura, 8)
    if data_calculo <= data_base_ipca:
        return saldo

    data_atual = data_base_ipca
    proximo_aniversario = _ENGINE.proxima_data_aniversario(data_atual)

    while proximo_aniversario <= data_calculo:
        if data_atual == proximo_aniversario:
            proximo_mes = _ENGINE.add_months(proximo_aniversario, 1)
            proximo_aniversario = date(proximo_mes.year, proximo_mes.month, 15)
            continue

        if data_atual.day == 15:
            fator, *_ = fator_ipca(indices, proximo_aniversario)
        else:
            fator, *_ = fator_ipca_prorata(indices, proximo_aniversario, data_atual)
        saldo = trunc_dec(saldo * fator, 8)
        data_atual = proximo_aniversario
        proximo_mes = _ENGINE.add_months(proximo_aniversario, 1)
        proximo_aniversario = date(proximo_mes.year, proximo_mes.month, 15)

    if data_atual < data_calculo:
        fator_parcial = _fator_ipca_parcial(indices, data_atual, data_calculo, proximo_aniversario)
        saldo = trunc_dec(saldo * fator_parcial, 8)

    return saldo


def _linha_diaria_inicial() -> Dict[str, object]:
    return {
        "Evento": 0,
        "Data": DATA_INICIO_RENTABILIDADE.strftime("%d/%m/%Y"),
        "Data_Ref_Evento": DATA_INICIO_RENTABILIDADE.strftime("%d/%m/%Y"),
        "Data_Pgto_Evento": DATA_INICIO_RENTABILIDADE.strftime("%d/%m/%Y"),
        "Data_Inicio_Periodo": DATA_INICIO_RENTABILIDADE.strftime("%d/%m/%Y"),
        "Dia_Util": "SIM",
        "DU_Acumulado": 0,
        "PU_VNa_Abertura_Periodo": PU_INICIAL,
        "PU_VNa_Atualizado_Dia": PU_INICIAL,
        "PU_Juros_Acumulado": Decimal("0.00000000"),
        "PU_Valor_Bruto": PU_INICIAL,
        "PU_Juros_Pago_Dia": Decimal("0.00000000"),
        "PU_Juros_Capitalizado_Dia": Decimal("0.00000000"),
        "PU_Amort_Dia": Decimal("0.00000000"),
        "PU_Total_Pago_Dia": Decimal("0.00000000"),
        "PU_Saldo_Fechamento_Dia": PU_INICIAL,
        "Saldo_Bruto_R$": round_dec(PU_INICIAL * QUANTIDADE, 2),
        "Saldo_Fechamento_R$": round_dec(PU_INICIAL * QUANTIDADE, 2),
        "Tipo_Dia": "EMISSAO",
        "Fonte_Indexador": "IPCA SIDRA/IBGE e projecoes Focus/BCB",
    }


def detalhar_periodo_diario(
    numero_evento: int,
    data_inicio_periodo: date,
    data_base_ipca: date,
    data_evento: date,
    saldo_abertura: Decimal,
    percentual_amortizacao: Decimal,
    incorpora_juros: bool,
    indices: Dict[str, Decimal],
) -> List[Dict[str, object]]:
    linhas: List[Dict[str, object]] = []
    for data_corrente in iter_dias_uteis(data_inicio_periodo, data_evento):
        du = _ENGINE.dias_uteis(data_inicio_periodo, data_corrente)
        fator_juros = fator_juros_252(du)
        pu_vna = atualizar_ipca_ate_data(saldo_abertura, data_base_ipca, data_corrente, indices)
        pu_juros = trunc_dec(pu_vna * (fator_juros - Decimal("1")), 8)
        pu_cheio = trunc_dec(pu_vna + pu_juros, 8)

        eh_evento = data_corrente == data_evento
        pu_juros_pago = Decimal("0.00000000")
        pu_juros_capitalizado = Decimal("0.00000000")
        pu_amort = Decimal("0.00000000")
        pu_total_pago = Decimal("0.00000000")
        pu_fechamento = pu_cheio
        tipo_dia = "ACUMULACAO"

        if eh_evento and incorpora_juros:
            pu_juros_capitalizado = pu_juros
            pu_fechamento = pu_cheio
            tipo_dia = "CAPITALIZACAO"
        elif eh_evento:
            pu_juros_pago = pu_juros
            pu_amort = trunc_dec(pu_vna * percentual_amortizacao, 8)
            if percentual_amortizacao == Decimal("1"):
                pu_amort = pu_vna
            pu_total_pago = trunc_dec(pu_juros_pago + pu_amort, 8)
            pu_fechamento = trunc_dec(pu_vna - pu_amort, 8)
            tipo_dia = "PAGAMENTO_JUROS_E_AMORTIZACAO"

        linhas.append({
            "Evento": numero_evento,
            "Data": data_corrente.strftime("%d/%m/%Y"),
            "Data_Ref_Evento": data_evento.strftime("%d/%m/%Y"),
            "Data_Pgto_Evento": data_evento.strftime("%d/%m/%Y"),
            "Data_Inicio_Periodo": data_inicio_periodo.strftime("%d/%m/%Y"),
            "Dia_Util": "SIM",
            "DU_Acumulado": du,
            "Fator_Juros_Acumulado": fator_juros,
            "PU_VNa_Abertura_Periodo": saldo_abertura,
            "PU_VNa_Atualizado_Dia": pu_vna,
            "PU_Juros_Acumulado": pu_juros,
            "PU_Valor_Bruto": pu_cheio,
            "PU_Juros_Pago_Dia": pu_juros_pago,
            "PU_Juros_Capitalizado_Dia": pu_juros_capitalizado,
            "PU_Amort_Dia": pu_amort,
            "PU_Total_Pago_Dia": pu_total_pago,
            "PU_Saldo_Fechamento_Dia": pu_fechamento,
            "Saldo_Bruto_R$": round_dec(pu_vna * QUANTIDADE, 2),
            "Saldo_Fechamento_R$": round_dec(pu_fechamento * QUANTIDADE, 2),
            "Tipo_Dia": tipo_dia,
            "Fonte_Indexador": "IPCA SIDRA/IBGE e projecoes Focus/BCB",
        })
    return linhas


def obter_historico_pu_vortx() -> List[Dict[str, object]]:
    """Busca o historico oficial publicado para a operacao AXS412."""
    dados = _ENGINE.obter_json_url(VORTX_PU_HISTORY_URL, timeout=20)
    itens = dados.get("unitPrices", []) if isinstance(dados, dict) else []
    linhas: List[Dict[str, object]] = []
    for item in itens:
        data_txt = str(item.get("paymentDate", ""))[:10]
        try:
            data_pu = date.fromisoformat(data_txt)
        except ValueError:
            continue

        valor_nominal = Decimal(str(item.get("nominalValue", 0)))
        valor_juros = Decimal(str(item.get("interestValue", 0)))
        pu_cheio = Decimal(str(item.get("unitPriceFull", valor_nominal + valor_juros)))
        pu_vazio = Decimal(str(item.get("unitPriceEmpty", pu_cheio)))
        pu_amort = Decimal(str(item.get("amortization", 0)))
        pu_total = Decimal(str(item.get("total", 0)))
        tipo = "PAGAMENTO_JUROS_E_AMORTIZACAO" if pu_total > 0 else "ACUMULACAO"
        linhas.append({
            "Evento": 0,
            "Data": data_pu.strftime("%d/%m/%Y"),
            "Data_Ref_Evento": data_pu.strftime("%d/%m/%Y"),
            "Data_Pgto_Evento": data_pu.strftime("%d/%m/%Y"),
            "Data_Inicio_Periodo": DATA_INICIO_RENTABILIDADE.strftime("%d/%m/%Y"),
            "Dia_Util": "SIM",
            "DU_Acumulado": _ENGINE.dias_uteis(DATA_INICIO_RENTABILIDADE, data_pu),
            "PU_VNa_Abertura_Periodo": valor_nominal,
            "PU_VNa_Atualizado_Dia": valor_nominal,
            "PU_Juros_Acumulado": valor_juros,
            "PU_Valor_Bruto": pu_cheio,
            "PU_Juros_Pago_Dia": Decimal("0"),
            "PU_Juros_Capitalizado_Dia": Decimal("0"),
            "PU_Amort_Dia": pu_amort,
            "PU_Total_Pago_Dia": pu_total,
            "PU_Saldo_Fechamento_Dia": pu_vazio,
            "Saldo_Bruto_R$": round_dec(valor_nominal * QUANTIDADE, 2),
            "Saldo_Fechamento_R$": round_dec(pu_vazio * QUANTIDADE, 2),
            "Tipo_Dia": tipo,
            "Fonte_Indexador": f"Vortx operacao {VORTX_OPERATION_ID}",
        })
    return linhas


def calcular_fluxo() -> Tuple[List[Dict[str, object]], List[Dict[str, object]], str]:
    indices, fonte_ipca = obter_ipca_numero_indice_sidra()
    indices, fonte_mes = preencher_indices_futuros(indices)

    saldo_pu = trunc_dec(PU_INICIAL, 8)
    data_ref_juros = DATA_INICIO_RENTABILIDADE
    data_base_ipca = DATA_INICIO_RENTABILIDADE
    linhas: List[Dict[str, object]] = []
    linhas_diarias: List[Dict[str, object]] = [_linha_diaria_inicial()]
    numero_evento = 0

    eventos = [
        (data_nominal, data_efetiva, Decimal("0"), True)
        for data_nominal, data_efetiva in zip(DATAS_INCORPORACAO_NOMINAIS, DATAS_INCORPORACAO_JUROS)
    ]
    eventos.extend([
        (data_nominal, data_efetiva, percentual, False)
        for (data_nominal, percentual), (data_efetiva, _) in zip(CRONOGRAMA_NOMINAL, CRONOGRAMA)
    ])

    for data_nominal, data_evento, percentual_amort, incorpora_juros in eventos:
        numero_evento += 1
        saldo_abertura = trunc_dec(saldo_pu, 8)
        data_base_inicio = data_base_ipca
        data_inicio_periodo = data_ref_juros

        pu_vna_atualizado = atualizar_ipca_ate_data(
            saldo_abertura, data_base_inicio, data_evento, indices,
        )
        du = _ENGINE.dias_uteis(data_inicio_periodo, data_evento)
        fator_juros = fator_juros_252(du)
        pu_juros = trunc_dec(pu_vna_atualizado * (fator_juros - Decimal("1")), 8)

        if incorpora_juros:
            pu_juros_pago = Decimal("0.00000000")
            pu_juros_incorporado = pu_juros
            pu_amort = Decimal("0.00000000")
            saldo_pu = trunc_dec(pu_vna_atualizado + pu_juros, 8)
            evento_nome = "Incorporacao Juros Carencia"
        else:
            pu_juros_pago = pu_juros
            pu_juros_incorporado = Decimal("0.00000000")
            pu_amort = trunc_dec(pu_vna_atualizado * percentual_amort, 8)
            if percentual_amort == Decimal("1"):
                pu_amort = pu_vna_atualizado
            saldo_pu = trunc_dec(pu_vna_atualizado - pu_amort, 8)
            evento_nome = "Pagamento"

        juros_rs = round_dec(pu_juros_pago * QUANTIDADE, 2)
        juros_incorporados_rs = round_dec(pu_juros_incorporado * QUANTIDADE, 2)
        amort_rs = round_dec(pu_amort * QUANTIDADE, 2)

        linhas.append({
            "Evento": evento_nome,
            "Codigo_IF": "AXS412",
            "ISIN": "BRAXS4DBS014",
            "Data_Ref": data_nominal.strftime("%d/%m/%Y"),
            "Data_Pgto": data_evento.strftime("%d/%m/%Y"),
            "Data_Inicio_Periodo": data_inicio_periodo.strftime("%d/%m/%Y"),
            "DU_Juros": du,
            "Taxa_aa": TAXA_AA,
            "Fator_Juros": fator_juros,
            "TAI_Amort": percentual_amort,
            "Incorpora_Ate_Data": "SIM" if incorpora_juros else "NAO",
            "PU_VNa_Ini": saldo_abertura,
            "PU_VNa_Atualizado": pu_vna_atualizado,
            "PU_Juros": pu_juros,
            "PU_Juros_Pago": pu_juros_pago,
            "PU_Juros_Incorporado": pu_juros_incorporado,
            "PU_Amort": pu_amort,
            "PU_Total_Pago": trunc_dec(pu_juros_pago + pu_amort, 8),
            "PU_VNa_Fim": saldo_pu,
            "Juros_R$": juros_rs,
            "Juros_Incorporado_R$": juros_incorporados_rs,
            "Amort_R$": amort_rs,
            "PMT_Total": round_dec(juros_rs + amort_rs, 2),
            "Saldo_Devedor_R$": round_dec(saldo_pu * QUANTIDADE, 2),
            "Fonte_IPCA": fonte_ipca,
            "Fonte_Projecao": fonte_mes.get(_ENGINE.mes_str(_ENGINE.add_months(data_nominal, -2)), ""),
        })

        linhas_diarias.extend(detalhar_periodo_diario(
            numero_evento,
            data_inicio_periodo,
            data_base_inicio,
            data_evento,
            saldo_abertura,
            percentual_amort,
            incorpora_juros,
            indices,
        ))

        data_ref_juros = data_evento
        data_base_ipca = date(data_nominal.year, data_nominal.month, 15)

    try:
        linhas_oficiais = obter_historico_pu_vortx()
    except Exception:
        linhas_oficiais = []
    if linhas_oficiais:
        linhas_por_data = {str(item["Data"]): item for item in linhas_diarias}
        linhas_por_data.update({str(item["Data"]): item for item in linhas_oficiais})
        linhas_diarias = sorted(
            linhas_por_data.values(),
            key=lambda item: datetime.strptime(str(item["Data"]), "%d/%m/%Y").date(),
        )

    return linhas, linhas_diarias, fonte_ipca


def main() -> None:
    linhas, linhas_diarias, fonte = calcular_fluxo()
    print(f"Fonte IPCA: {fonte}")
    print(f"Eventos calculados: {len(linhas)}")
    print(f"Linhas diarias calculadas: {len(linhas_diarias)}")
    print(f"Saldo final: {linhas[-1]['Saldo_Devedor_R$']}")


if __name__ == "__main__":
    main()
