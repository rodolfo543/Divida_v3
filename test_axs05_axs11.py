"""Regras dos aditivos, com índices de entrada; sem puxar PUs para o motor."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D, ROUND_DOWN, ROUND_HALF_UP
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import dashboard_server as dashboard
from daily_contracts import calculate_daily


def module(op):
    return dashboard.load_module(f"contract_{op}", dashboard.OPERATIONS[op].script_path)


def indices():
    raw = json.loads((Path(__file__).parent / "tests/fixtures/ipca_indices_2026.json").read_text())
    return {f"{key[:4]}-{key[4:]}": D(value) for key, value in raw.items()}


class AXS05AXS11Test(unittest.TestCase):
    def test_axs05_mes_de_divulgacao_nao_mes_de_referencia(self):
        m = module("axs05")
        _, nik, previous, _, _ = m.fator_ipca(indices(), date(2026, 8, 15))
        self.assertEqual((nik, previous), ("2026-06", "2026-05"))

    def test_axs05_inicio_exato_e_primeiro_trecho(self):
        m = module("axs05")
        idx = indices()
        self.assertEqual(m.atualizar_nominal_diario(D(1000), date(2026,3,13), date(2026,3,13), idx), D(1000))
        nominal = m.atualizar_nominal_diario(D(1000), date(2026,3,13), date(2026,3,16), idx)
        # Jan/Dez, 1 DU desde integralização em período de 18 DU.
        factor = (idx['2026-01']/idx['2025-12']) ** (D(1)/18)
        expected = (D(1000)*factor.quantize(D('.00000001'), rounding=ROUND_DOWN)).quantize(D('.00000001'))
        self.assertEqual(nominal, expected)

    def test_axs05_produtorio_e_incorporacao_sem_caixa(self):
        m = module("axs05")
        idx = indices()
        m.DATAS_INCORPORACAO_JUROS = [date(2026,8,15)]
        # Produtório independente: trecho inicial + meses completos até agosto.
        factors = [(idx['2026-01']/idx['2025-12']) ** (D(1)/18)]
        months = ['2026-02','2026-03','2026-04','2026-05','2026-06']
        previous = '2026-01'
        for month in months:
            factors.append(idx[month]/idx[previous]); previous = month
        product = D(1)
        for factor in reversed(factors):
            factor = factor.quantize(D('.00000001'),rounding=ROUND_DOWN)
            product = (product*factor).quantize(D('.0000000000000001'),rounding=ROUND_DOWN)
        nominal = D(1000)*product.quantize(D('.00000001'),rounding=ROUND_DOWN)
        for conf in m.SERIES.values():
            events = m.calcular_fluxo_serie(replace(conf,cronograma=[]),idx,{})
            event = events[0]
            self.assertEqual(event['PU_VNa_Atualizado'],nominal)
            self.assertGreater(event['PU_Juros_Incorporado'],0)
            self.assertEqual(event['PMT_Total'],0)
            self.assertEqual(event['PU_VNa_Fim'],nominal+event['PU_Juros_Incorporado'])
            self.assertEqual(m.dia_util_seguinte(date(2026,8,15)),date(2026,8,17))

    def test_axs05_diario_independe_evento_futuro_e_preserva_evento(self):
        m = module('axs05'); idx = indices()
        conf = replace(m.SERIES['primeira'],cronograma=[])
        m.DATAS_INCORPORACAO_JUROS = [date(2026,8,15)]
        events = m.calcular_fluxo_serie(conf,idx,{})
        events.append({'Data_Ref':'03/11/2026','PU_VNa_Fim':D(1),'PU_Juros':D(0)})
        before = calculate_daily(m,events,rate=conf.taxa_aa,indices=idx,lag=2)
        event_row = next(r for r in before if r['Data']=='17/08/2026')
        self.assertEqual(event_row['PU_Cheio'],events[0]['PU_VNa_Fim'])
        events[-1]['PU_VNa_Fim'] = D(1000000000)
        after = calculate_daily(m,events,rate=conf.taxa_aa,indices=idx,lag=2)
        self.assertEqual(next(r for r in before if r['Data']=='30/10/2026'),next(r for r in after if r['Data']=='30/10/2026'))

    def test_axs11_ipca_referencia_e_projecao_contratual_preservados(self):
        m = module('axs11'); idx = indices()
        _,nik,previous,_,_ = m.fator_ipca(idx,date(2026,10,15))
        self.assertEqual((nik,previous),('2026-09','2026-08'))
        import ipca_inputs
        projection = {'month':'2026-10','rate':'0.0021','published_at':'30/10/2026','source':ipca_inputs.URL}
        with patch.object(m,'obter_focus_ipca',return_value=({}, {}, 'teste')), patch.object(ipca_inputs,'projecao_anbima',return_value=projection):
            filled,sources = m.preencher_indices_futuros(idx)
        self.assertEqual(filled['2026-10'],D('7711.98'))
        self.assertEqual(filled['2026-09'],idx['2026-09'])
        self.assertIn('ANBIMA',sources['2026-10'])

    def test_juros_decimais_mantem_taxas_e_base_252(self):
        m05,m11=module('axs05'),module('axs11')
        for m,rate in [(m05,D('.093515')),(m05,D('.109659')),(m11,D('.107385'))]:
            expected=((1+rate)**(D(159)/252)).quantize(D('.000000001'),rounding=ROUND_HALF_UP)
            self.assertEqual(m.fator_juros_252(159,rate),expected)

    def test_diagnostico_taxas_da_memoria_reproduz_pus_externos_so_no_teste(self):
        m = module('axs05'); idx = indices()
        fixtures = json.loads((Path(__file__).parent/'tests/fixtures/vortx_axs05_conflict_2026-10-30.json').read_text())
        nominal = m.atualizar_nominal_diario(D(1000),date(2026,3,13),date(2026,10,30),idx)
        for sample in fixtures:
            reference = sample['reference']
            start = date(2026,3,13) if sample['code']=='AXSC12' else date(2026,8,17)
            # Esta hipótese usa a taxa declarada pela API SOMENTE para diagnosticar
            # a memória externa. O motor mantém taxa e incorporações dos aditivos.
            factor = m.fator_juros_252(m.dias_uteis(start,date(2026,10,30)),D(reference['interest']))
            interest = (nominal*(factor-1)).quantize(D('.00000001'),rounding=ROUND_DOWN)
            self.assertEqual(nominal,D(reference['nominalValue']))
            self.assertEqual(interest,D(reference['interestValue']))
            self.assertEqual(nominal+interest,D(reference['unitPriceFull']))
        self.assertEqual(m.SERIES['primeira'].taxa_aa,D('.093515'))
        self.assertEqual(m.SERIES['segunda'].taxa_aa,D('.109659'))


if __name__ == '__main__':
    unittest.main()
