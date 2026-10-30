import importlib.util
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
import dashboard_server as dashboard

spec = importlib.util.spec_from_file_location('paxs12', Path(__file__).parent / 'Code final prontos' / 'paxs12_v1.py')
paxs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paxs)

class PAXS12Test(unittest.TestCase):
    def test_pus_vortx(self):
        # Histórico publicado pela Vórtx, consultado em 30/10/2026.
        valores = ['1000.00000000','1000.71670800','1001.43393200','1002.15166200',
                   '1002.86991700','1003.58868000','1004.30795900','1005.02775400',
                   '1005.74806700','1006.46889800','1007.19023600','1007.91210200','1008.63447600']
        taxas = {date(2026,10,d): Decimal('13.65') for d in (14,15,16,19,20,21,22,23,26,27,28,29)}
        eventos, dias, _ = paxs.calcular_fluxo(taxas, date(2026,10,30))
        self.assertEqual([row['PU_Valor_Bruto'] for row in dias[:13]], [Decimal(v) for v in valores])
        self.assertEqual(eventos[0]['Data_Pgto'], '30/09/2031')
        self.assertEqual(eventos[0]['Amort_R$'], Decimal('151899000'))
        self.assertEqual(dias[-1]['Saldo_Fechamento_R$'], 0)

    def test_nao_projeta_dados_historicos_ausentes(self):
        with self.assertRaisesRegex(ValueError, 'DI histórico ausente'):
            paxs.calcular_fluxo({date(2026,10,14):Decimal('13.65')}, date(2026,10,19))

    def test_carteira_inclui_saldo_antes_do_vencimento_e_zera_apos(self):
        def evento(d, saldo, pagamento=0):
            return {'parsed_date': d, 'balance': saldo, 'payment': pagamento,
                    'interest': 0, 'amortization': 0, 'principal': 0, 'pu_cheio': 0, 'pu_vazio': 0}
        payloads = [
            {'operation': {'id': 'outra'}, 'series': [evento(date(2026, 10, 1), 500)], 'daily_pu_series': []},
            {'operation': {'id': 'paxs12'}, 'series': [evento(date(2031, 9, 30), 0, 1100)],
             'daily_pu_series': [{'parsed_date': date(2026, 10, 14), 'balance': 1000},
                                 {'parsed_date': date(2031, 9, 30), 'balance': 0}]},
        ]
        series = dashboard.build_portfolio_series(payloads)
        self.assertEqual(next(r['balance'] for r in series if r['parsed_date'] == date(2026,10,14)), 1500)
        self.assertEqual(next(r['balance'] for r in series if r['parsed_date'] == date(2031,9,30)), 500)

if __name__ == '__main__':
    unittest.main()
