"""Regras financeiras da AGD de 10/11/2026 e do segundo aditamento de Goias."""
import json
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import dashboard_server as dashboard
from build_calendar import calendar_event
from build_vortx_comparison import local_row

ROOT = Path(__file__).resolve().parent


class GoiasAditamentoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = dashboard.load_module("test_goias_aditamento", dashboard.OPERATIONS["axsgoias"].script_path)
        cls.indices = {f"{y}-{m:02d}": D("1") for y in range(2024, 2042) for m in range(1, 13)}
        cls.events, _ = cls.m.calcular_fluxo(cls.indices, {}, "IPCA neutro")
        cls.daily = {r['Data']: r for r in cls.m.calcular_pu_diario_local(cls.indices, cls.events, date(2028, 6, 16))}

    def test_carencia_28_pagamentos_e_quitacao(self):
        payments = [r for r in self.events if r['PMT_Total'] > 0]
        self.assertEqual(len(payments), 28)
        self.assertEqual(payments[0]['Data_Pgto'], '15/06/2028')
        self.assertEqual(payments[0]['TAI_Amort'], D('0.019671'))
        self.assertEqual(payments[-1]['Data_Pgto'], '15/12/2041')
        self.assertEqual(payments[-1]['PU_VNa_Fim'], 0)
        for day in ['15/12/2026', '15/06/2027', '15/12/2027']:
            r = next(r for r in self.events if r['Data_Ref'] == day)
            self.assertGreater(r['PU_Juros_Incorporado'], 0)
            self.assertEqual(r['PMT_Total'], 0)
            self.assertEqual(r['PU_Amort'], 0)

    def test_premio_sobre_saldo_com_juros_e_sem_caixa(self):
        m = self.m
        p = next(r for r in self.events if r.get('PU_Premio_Incorporado'))
        self.assertEqual(p['Data_Ref'], '10/11/2026')
        self.assertEqual(p['PU_Premio_Incorporado'], m.trunc_dec(p['PU_Base_Premio'] * D('.01')))
        self.assertEqual(p['PU_Base_Premio'], p['PU_VNa_Atualizado'] + p['PU_Juros'])
        self.assertEqual(p['PU_VNa_Fim'], p['PU_VNa_Atualizado'] + p['PU_Premio_Incorporado'])
        self.assertEqual(p['PU_Juros_Incorporado'], 0)
        self.assertEqual(p['PMT_Total'], 0)
        r = self.daily['10/11/2026']
        self.assertEqual(r['Valor_Nominal'], p['PU_VNa_Fim'])
        self.assertEqual(r['Valor_Juros'], p['PU_Juros'])
        self.assertEqual(r['PU_Cheio'], p['PU_Base_Premio'] + p['PU_Premio_Incorporado'])
        self.assertEqual(r['PU_Total_Pago_Dia'], 0)
        self.assertEqual(self.daily['09/11/2026']['PU_Premio_Incorporado'], 0)
        self.assertEqual(self.daily['11/11/2026']['PU_Premio_Incorporado'], 0)

    def test_premio_rende_desde_agd_sem_reiniciar_juros_anteriores(self):
        m = self.m
        p = next(r for r in self.events if r.get('PU_Premio_Incorporado'))
        base = next(r for r in self.events if r['Data_Ref'] == '15/06/2026')['PU_VNa_Fim']
        for day in ['11/11/2026', '15/12/2026']:
            dt = dashboard.parse_date(day)
            expected_interest = m.trunc_dec(base * (m.fator_juros_252(m.dias_uteis(date(2026, 6, 15), dt)) - 1))
            expected_interest += m.trunc_dec(p['PU_Premio_Incorporado'] * (m.fator_juros_252(m.dias_uteis(m.DATA_PREMIO, dt)) - 1))
            self.assertEqual(self.daily[day]['Valor_Juros'], expected_interest)
        for event in self.events:
            day = event['Data_Ref']
            if day in self.daily and event['Evento'] == 'Incorporacao Juros Carencia' and dashboard.parse_date(day) > date(2026, 6, 15):
                self.assertEqual(self.daily[day]['PU_Cheio'], event['PU_VNa_Fim'])

    def test_ipca_corrige_premio_e_preserva_historico(self):
        m = self.m
        indices, index = {}, D('1')
        for key in sorted(self.indices):
            index *= D('1.003')
            indices[key] = index
        events, _ = m.calcular_fluxo(indices, {}, 'IPCA de teste')
        daily = {r['Data']: r for r in m.calcular_pu_diario_local(indices, events, date(2026, 12, 16))}
        legacy = dashboard.load_module('goias_historico_teste', dashboard.OPERATIONS['axsgoias'].script_path)
        legacy.DATAS_INCORPORACAO_JUROS = legacy.DATAS_INCORPORACAO_JUROS[:4]
        legacy.CRONOGRAMA = []
        previous, _ = legacy.calcular_fluxo(indices, {}, 'IPCA de teste')
        historical = legacy.calcular_pu_diario_local(indices, previous, date(2026, 11, 9))
        self.assertEqual(events[:4], previous)
        self.assertEqual([daily[r['Data']] for r in historical], historical)
        p = next(r for r in events if r.get('PU_Premio_Incorporado'))
        june = events[3]['PU_VNa_Fim']
        day = date(2026, 11, 11)
        expected = m.aplicar_ipca_ate_data(june, date(2026, 6, 15), day, indices)
        expected += m.aplicar_ipca_ate_data(p['PU_Premio_Incorporado'], m.DATA_PREMIO, day, indices)
        self.assertEqual(daily['11/11/2026']['Valor_Nominal'], expected)
        december = next(r for r in events if r['Data_Ref'] == '15/12/2026')
        self.assertEqual(daily['15/12/2026']['PU_Cheio'], december['PU_VNa_Fim'])

    def test_calendario_conciliacao_e_tir_sem_pagamento_ficticio(self):
        p = next(r for r in self.events if r.get('PU_Premio_Incorporado'))
        row = dashboard.normalize_base_row(p)
        e = calendar_event(row, {'code': 'AXS311', 'operation': 'axsgoias', 'label': 'AXS Goias', 'series': 'Unica'}, self.m.QUANTIDADE, 0)
        self.assertEqual(e['type'], 'incorporation')
        self.assertEqual(e['payment'], '0.00')
        self.assertEqual(e['premium'], e['incorporation'])
        daily = dict(row, raw=self.daily['10/11/2026'])
        self.assertEqual(D(local_row(daily, self.m.QUANTIDADE)['incorporation']), p['PU_Premio_Incorporado'])
        flows = dashboard.build_return_cashflows(dashboard.OPERATIONS['axsgoias'], dashboard.normalize_series(self.events), self.m)
        self.assertEqual(len(flows), 29)
        self.assertEqual(flows[1]['date'], '15/06/2028')
        self.assertEqual(flows[1]['amount'], float(next(r for r in self.events if r['PMT_Total'] > 0)['PMT_Total']))

    def test_bases_geradas_refletem_nova_carencia(self):
        data = json.loads((ROOT / 'data/operations/axsgoias.json').read_text(encoding='utf-8'))
        self.assertEqual(data['summary']['next_payment_date'], '15/06/2028')
        self.assertEqual((ROOT / 'data/operations/axsgoias.json').read_bytes(), (ROOT / 'docs/data/operations/axsgoias.json').read_bytes())
        calendar = json.loads((ROOT / 'data/calendar.json').read_text(encoding='utf-8'))
        payments = [r for r in calendar['events'] if r['code'] == 'AXS311' and D(r['payment']) > 0]
        self.assertEqual(payments[0]['date'], '2028-06-15')
        self.assertEqual(len(payments), 28)
        summary = data['summary']
        self.assertGreater(summary['monthly_balance_premium'], 0)
        self.assertAlmostEqual(summary['monthly_balance_variation'],
                               summary['monthly_balance_update'] + summary['monthly_balance_interest']
                               + summary['monthly_balance_premium'] - summary['monthly_balance_amortization'], places=5)
        general = json.loads((ROOT / 'data/operations/geral.json').read_text(encoding='utf-8'))
        self.assertEqual(general['summary']['monthly_balance_premium'], summary['monthly_balance_premium'])
        instruments = json.loads((ROOT / 'data/recomposition.json').read_text(encoding='utf-8'))['instruments']
        goias = next(i for i in instruments if i['code'] == 'AXS311')
        self.assertEqual(goias['start_month'], '2027-12')
        self.assertEqual(goias['cycles'][0]['payment_date'], '2028-06-15')


if __name__ == '__main__':
    unittest.main()
