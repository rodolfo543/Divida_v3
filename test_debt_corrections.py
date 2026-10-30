"""Regressões contratuais; índices IBGE de entrada e nenhum PU no motor."""
import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import dashboard_server as dashboard
from daily_contracts import calculate_daily

ROOT = Path(__file__).parent


def module(operation):
    return dashboard.load_module(f"test_contract_{operation}", dashboard.OPERATIONS[operation].script_path)


class DebtCorrectionTest(unittest.TestCase):
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

    def test_axs02_amortizacao_confirmada_soma_cinco_milhoes(self):
        m = module("axs02")
        m.CRONOGRAMA = [(day, rate) for day, rate in m.CRONOGRAMA if day <= date(2026, 10, 15)]
        indices = {month: D("7000") for month in m.iter_periodos("202210", "202610")}
        extra = D(0)
        for conf in m.INSTRUMENTOS:
            events, daily = m.calcular_instrumento(conf, indices, {})
            event = events[-1]
            extra += event["Amort_Extraordinaria_R$"]
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
