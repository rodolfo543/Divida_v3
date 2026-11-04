"""Regressões contratuais; índices IBGE de entrada e nenhum PU no motor."""
import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import dashboard_server as dashboard
from daily_contracts import calculate_daily, update_nominal, trunc

ROOT = Path(__file__).parent


def module(operation):
    return dashboard.load_module(f"test_contract_{operation}", dashboard.OPERATIONS[operation].script_path)


class DebtCorrectionTest(unittest.TestCase):
    def test_axs04_amortizacoes_liquidadas_opea_e_pu(self):
        m = module("axs04")
        raw = json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text())
        indices = {key[:4] + "-" + key[4:]: D(value) for key, value in raw.items()}
        self.assertEqual(dict(m.CRONOGRAMA_RAW)["2025-09-15"], "0.5219")
        self.assertEqual(dict(m.CRONOGRAMA)[date(2025, 9, 15)], D("0.005218"))
        self.assertEqual(dict(m.CRONOGRAMA)[date(2025, 10, 15)], D("0.005246"))
        m.CRONOGRAMA = [(day, pct) for day, pct in m.CRONOGRAMA if day <= date(2026, 10, 15)]
        with patch.object(m, "obter_ipca_numero_indice_sidra", return_value=(indices, "IBGE")), \
             patch.object(m, "preencher_indices_futuros", return_value=(indices, {}, "fixture")):
            events, _, _ = m.calcular_fluxo()
        by_date = {row["Data_Pgto"]: row for row in events}
        # Valores unitários de amortização publicados pela Opea para eventos liquidados.
        self.assertEqual(by_date[date(2025, 9, 15)]["PU_Amort"], D("5.50518436"))
        self.assertEqual(by_date[date(2025, 10, 15)]["PU_Amort"], D("5.49978515"))
        start, end = date(2026, 10, 15), date(2026, 11, 3)
        nominal = update_nominal(events[-1]["PU_VNa_Fim"], start, end, indices, m, 2)
        interest = trunc(nominal * (m.fator_juros_252(m.dias_uteis(start, end)) - D(1)))
        self.assertEqual(nominal + interest, D("1033.77714827"))
        self.assertEqual(nominal + interest - D("1033.77714556"), D("0.00000271"))

    def test_axs07_primeiro_periodo_e_residuo_posterior(self):
        m = module("axs07")
        raw = json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text())
        indices = {key[:4] + "-" + key[4:]: D(value) for key, value in raw.items()}
        indices["2026-10"] = indices["2026-09"] * D("1.0021")
        m.CRONOGRAMA = [(day, pct) for day, pct in m.CRONOGRAMA if day <= date(2026, 10, 15)]
        with patch.object(m, "obter_ipca_numero_indice_sidra", return_value=(indices, "IBGE")), \
             patch.object(m, "preencher_indices_futuros", return_value=(indices, {})):
            events, _ = m.calcular_fluxo()
        first = events[0]
        self.assertEqual(first["Fator_C_IPCA"], D("1.00198846"))
        self.assertEqual(first["PU_VNa_Atualizado"] + first["PU_Juros"], D("1006.36498427"))
        start, end = date(2026, 10, 15), date(2026, 11, 3)
        nominal = update_nominal(events[-1]["PU_VNa_Fim"], start, end, indices, m)
        interest = trunc(nominal * (m.fator_juros_252(m.dias_uteis(start, end)) - D(1)))
        self.assertEqual(nominal + interest, D("949.32633374"))
        # A referência é externa ao cálculo; o resíduo remanescente não é zerado.
        self.assertEqual(nominal + interest - D("949.32633233"), D("0.00000141"))

    def test_axs10_produtorio_concilia_pu_diario_vortx(self):
        m = module("axs10")
        raw = json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text())
        indices = {key[:4] + "-" + key[4:]: D(value) for key, value in raw.items()}
        expected = {
            date(2026, 10, 15): (D("1008.92397000"), D("1060.38137364")),
            date(2026, 10, 30): (D("1013.24894000"), D("1070.88961725")),
            date(2026, 11, 3): (D("1013.64303000"), D("1071.85005277")),
            date(2026, 11, 4): (D("1014.03728000"), D("1072.81135734")),
        }
        for day, (nominal_ref, pu_ref) in expected.items():
            nominal = m.atualizar_ipca_ate_data(D("1000"), m.DATA_INICIO_RENTABILIDADE, day, indices)
            du = m._ENGINE.dias_uteis(m.DATA_INICIO_RENTABILIDADE, day)
            juros = m.trunc_dec(nominal * (m.fator_juros_252(du) - D(1)))
            self.assertEqual((nominal, nominal + juros), (nominal_ref, pu_ref))

    def test_axsc12_taxa_confirmada_no_aditivo(self):
        self.assertEqual(module("axs05").SERIES["primeira"].taxa_aa, D("0.093515"))

    def test_feriado_b3_so_a_partir_2024(self):
        for operation in ("axs03", "axs04"):
            m = module(operation)
            self.assertTrue(m.eh_dia_util(date(2023, 11, 20)))
            self.assertFalse(m.eh_dia_util(date(2024, 11, 20)))
            self.assertEqual(m.dias_uteis(date(2023, 11, 15), date(2023, 12, 15)), 21)

    def test_axs01_mes_divulgacao_e_incorporacao(self):
        m = module("axs01")
        indices = {key: D(value) for key, value in json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text()).items()}
        self.assertEqual(m.aniversario_do_periodo(date(2026, 10, 30))[2], "202609")
        m.CRONOGRAMA = m.CRONOGRAMA[:1]
        # Referência externa somente na asserção: validação da incorporação de agosto.
        expected = {"AXSA11": D("1070.29875552"), "AXSA21": D("1076.97973714")}
        for conf in m.SERIES:
            events, daily = m.calcular_serie(conf, indices, {})
            self.assertEqual(daily[-1]["PU_Cheio"], expected[conf.codigo_if])
            self.assertEqual(events[-1]["PU_VNa_Fim"], daily[-1]["PU_Cheio"])

    def test_axs06_nao_aplica_taxa_nova_antes_migracao(self):
        m = module("axs06")
        conf = m.EMISSOES["primeira"]
        from dataclasses import replace
        conf = replace(conf, datas_incorporacao_juros=(date(2026, 3, 15),), cronograma=[])
        events = m.calcular_fluxo_primeira_emissao(conf, {}, {})
        migration = events[-1]
        self.assertEqual(migration["Taxa_AA"], conf.taxa_aa_antiga)
        self.assertEqual(migration["DU_Juros"], 125)
        self.assertEqual(migration["PU_VNa_Fim"], D("1066.68837400"))

    def test_axs06_produtorio_e_evento_de_setembro(self):
        from dataclasses import replace
        m = module("axs06")
        raw = json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text())
        indices = {key[:4] + "-" + key[4:]: D(value) for key, value in raw.items()}
        indices["2026-10"] = indices["2026-09"] * D("1.0021")
        expected = {
            "primeira": (2, D("1099.71987286"), D("1173.34839206")),
            "segunda": (1, D("1020.92034000"), D("1097.24408421")),
        }
        for variant, (lag, expected_nominal, expected_daily) in expected.items():
            conf = m.EMISSOES[variant]
            conf = replace(conf, datas_incorporacao_juros=tuple(
                day for day in conf.datas_incorporacao_juros if day <= date(2026, 9, 15)), cronograma=[])
            events = getattr(m, f"calcular_fluxo_{variant}_emissao")(conf, indices, {})
            self.assertEqual(events[-1]["PU_VNa_Atualizado"], expected_nominal)
            start, end = date(2026, 9, 15), date(2026, 11, 3)
            nominal = update_nominal(events[-1]["PU_VNa_Fim"], start, end, indices, m, lag)
            interest = trunc(nominal * (m.fator_juros_252(m.dias_uteis(start, end), conf.taxa_aa_nova) - D(1)))
            self.assertEqual(nominal + interest, expected_daily)

    def test_axs02_amortizacao_confirmada_soma_cinco_milhoes(self):
        m = module("axs02")
        m.CRONOGRAMA = [(day, rate) for day, rate in m.CRONOGRAMA if day <= date(2026, 10, 15)]
        indices = {month: D("7000") for month in m.iter_periodos("202210", "202610")}
        extra = D(0)
        for conf in m.INSTRUMENTOS:
            events, daily = m.calcular_instrumento(conf, indices, {})
            event = events[-1]
            extra += event["Amort_Extraordinaria_R$"]
            amounts = {"22L1467623": D("2647060.00"), "AXSD11": D("2352940.00")}
            self.assertEqual(event["Amort_Extraordinaria_R$"], amounts[conf.codigo_if])
            if conf.codigo_if == "22L1467623":
                self.assertEqual(event["PU_Amort_Extraordinaria"], D("58.82355555"))
            self.assertEqual(event["PU_Amort"], event["PU_Amort_Programada"] + event["PU_Amort_Extraordinaria"])
            self.assertEqual(event["PU_VNa_Fim"], event["PU_VNa_Atualizado"] - event["PU_Amort"])
        self.assertEqual(extra, D("5000000.00"))

    def test_pu_atual_nao_depende_do_pu_de_evento_futuro(self):
        m = module("axs07")
        events = [
            {"Data_Ref": "15/10/2026", "PU_VNa_Fim": D("1000"), "PU_VNa_Atualizado": D("1000"), "PU_Juros": D(0)},
            {"Data_Ref": "16/11/2026", "PU_VNa_Fim": D("900"), "PU_VNa_Atualizado": D("1000"), "PU_Juros": D(10)},
        ]
        indices = {"2026-09": D("100"), "2026-10": D("100.21"), "2026-11": D("100.5")}
        before = calculate_daily(m, events, start=date(2026, 10, 15), indices=indices)
        events[-1]["PU_VNa_Fim"] = D("1000000")
        after = calculate_daily(m, events, start=date(2026, 10, 15), indices=indices)
        self.assertEqual(next(row for row in before if row["Data"] == "30/10/2026"), next(row for row in after if row["Data"] == "30/10/2026"))

    def test_projecao_anbima_preserva_indices_oficiais_e_taxas_futuras(self):
        module("axs07")
        import ipca_inputs
        indices = {"2026-09": D("100"), "2026-10": D("101"), "2026-11": D("102.01")}
        original = dict(indices)
        snapshot = {"month": "2026-10", "rate": "0.0021", "published_at": "30/10/2026", "source": ipca_inputs.URL}
        with patch.object(ipca_inputs, "projecao_anbima", return_value=snapshot):
            ipca_inputs.aplicar_projecao_anbima(indices, {}, {"2026-09"})
            self.assertEqual(indices["2026-09"], original["2026-09"])
            self.assertEqual(indices["2026-10"], D("100.21"))
            self.assertEqual(indices["2026-11"] / indices["2026-10"], D("1.01"))
            ipca_inputs.aplicar_projecao_anbima(original, {}, set(original))
            self.assertEqual(original["2026-10"], D("101"))

    def test_carteira_zera_no_ultimo_dia_util_do_vencimento(self):
        def row(day, balance, payment=0):
            return {"parsed_date": day, "date": day.strftime("%d/%m/%Y"), "component": "diario",
                    "balance": balance, "principal": balance, "payment": payment,
                    "interest": 0, "amortization": 0, "pu_cheio": 0, "pu_vazio": 0}
        payload = {"operation": {"id": "teste"},
                   "series": [row(date(2026, 11, 15), 0, 1000)],
                   "daily_pu_series": [row(date(2026, 11, 13), 1000), row(date(2026, 11, 16), 0)]}
        result = dashboard.build_portfolio_series([payload])
        self.assertEqual(result[-1]["parsed_date"], date(2026, 11, 16))
        self.assertEqual(result[-1]["balance"], 0)


if __name__ == "__main__":
    unittest.main()
