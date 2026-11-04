"""Conciliação do produtório IPCA Goiás; referências externas só nas asserções."""
import json
import unittest
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path

import dashboard_server as dashboard

ROOT = Path(__file__).resolve().parent


class GoiasPrecisionTest(unittest.TestCase):
    def setUp(self):
        self.m = dashboard.load_module("test_goias_contract_precision", dashboard.OPERATIONS["axsgoias"].script_path)
        raw = json.loads((ROOT / "tests/fixtures/ipca_indices_2026.json").read_text())
        self.indices = {key[:4] + "-" + key[4:]: D(value) for key, value in raw.items()}
        self.indices["2026-10"] = self.indices["2026-09"] * D("1.0021")
        self.m.CRONOGRAMA = []

    def test_capitalizacoes_e_detalhes_do_produtorio(self):
        m = self.m
        events, _ = m.calcular_fluxo(self.indices, {}, "IBGE fixture")
        expected = [D("1032.49955960"), D("1119.12602450"), D("1190.27097846"), D("1292.87406778")]
        self.assertEqual([row["PU_VNa_Fim"] for row in events], expected)
        nominal, details, last = m.aplicar_ipca_ate(D("1000"), date(2024, 10, 1), date(2026, 6, 15), self.indices, {})
        self.assertEqual(nominal, D("1094.17943000"))
        self.assertEqual(details[-1]["PU_Apos_IPCA"], nominal)
        self.assertEqual(last, date(2026, 6, 15))
        self.assertEqual([row["PU_Antes_IPCA"] for row in details[1:]], [row["PU_Apos_IPCA"] for row in details[:-1]])

    def test_sete_dias_do_produtorio_e_residuo_na_data_base(self):
        m = self.m
        events, _ = m.calcular_fluxo(self.indices, {}, "IBGE fixture")
        daily = m.calcular_pu_diario_local(self.indices, events, date(2026, 11, 4))
        rows = {row["Data"]: row for row in daily}
        # Data, resultado corrigido, Vórtx, resultado anterior. Nenhum destes PUs
        # participa do cálculo; a referência permanece isolada no teste.
        expected = [
            ("26/10/2026", "1351.66960420", "1351.66960710", "1351.66963124"),
            ("27/10/2026", "1352.33548690", "1352.33558996", "1352.33551188"),
            ("28/10/2026", "1353.00169633", "1353.00197139", "1353.00171931"),
            ("29/10/2026", "1353.66823516", "1353.66838408", "1353.66825623"),
            ("30/10/2026", "1354.33510219", "1354.33509145", "1354.33512143"),
            ("03/11/2026", "1355.00229617", "1355.00228832", "1355.00231366"),
            ("04/11/2026", "1355.66981980", "1355.66981370", "1355.66983563"),
        ]
        for day, actual, reference, previous in expected:
            with self.subTest(day=day):
                self.assertEqual(rows[day]["PU_Cheio"], D(actual))
                if day == "03/11/2026":
                    self.assertLess(abs(D(actual) - D(reference)), abs(D(previous) - D(reference)))


if __name__ == "__main__":
    unittest.main()
