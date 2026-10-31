"""Agenda usa o fluxo publicado, sem duplicação das variantes nem alteração de datas."""
import hashlib
import json
import unittest
from decimal import Decimal as D
from pathlib import Path
from build_calendar import calendar_event, money

ROOT = Path(__file__).resolve().parent
INSTRUMENT = {'code':'TEST','operation':'axs02','label':'AXS 02','series':'CRI'}


class CalendarTests(unittest.TestCase):
    def test_capitalization_is_not_a_payment(self):
        e = calendar_event({'date':'15/03/2027','payment':0,'label':'Capitalização',
                            'pu_juros':'50.25','raw':{}}, INSTRUMENT, D('1000'), 0)
        self.assertEqual(e['payment'], '0.00')
        self.assertEqual(e['incorporation'], '50250.00')
        self.assertEqual(e['type'], 'incorporation')

    def test_extra_is_part_of_amortization(self):
        e = calendar_event({'date':'15/10/2026','payment':'75','interest':'5','amortization':'70',
                            'balance':900, 'raw':{'Amort_Extraordinaria_R$':'60'}}, INSTRUMENT, D(1), 0)
        self.assertEqual(e['ordinary'], '10.00')
        self.assertEqual(e['extra'], '60.00')
        self.assertEqual(e['payment'], '75.00')

    def test_maturity_and_weekend_date_are_preserved(self):
        e = calendar_event({'date':'15/08/2026','payment':1050,'interest':50,'amortization':1000,
                            'balance':0}, INSTRUMENT, D(1), 0)
        self.assertEqual(e['type'], 'maturity')
        self.assertEqual(e['date'], '2026-08-15')
        self.assertIsNone(calendar_event({'date':'15/08/2026'}, INSTRUMENT, D(1), 0))

    def test_all_source_payments_are_included_once(self):
        data = json.loads((ROOT/'data/calendar.json').read_text(encoding='utf-8'))
        self.assertEqual((ROOT/'data/calendar.json').read_bytes(), (ROOT/'docs/data/calendar.json').read_bytes())
        self.assertEqual(len(data['instruments']),17)
        self.assertEqual(len({e['id'] for e in data['events']}),len(data['events']))
        self.assertEqual({e['code'] for e in data['events']},{i['code'] for i in data['instruments']})
        catalog = json.loads((ROOT/'vortx_catalog.json').read_text(encoding='utf-8'))
        for i in catalog:
            content=(ROOT/'data/operations'/f"{i['operation']}.json").read_bytes()
            source=json.loads(content)
            view=source['variants'][i['variant']] if i['variant'] else source
            expected=sum(D(money(r['payment'])) for r in view['table_series'] if D(str(r['payment']))>0)
            actual=sum(D(e['payment']) for e in data['events'] if e['code']==i['code'])
            self.assertEqual(actual,expected,i['code'])
            descriptor=next(x for x in data['instruments'] if x['code']==i['code'])
            self.assertEqual(descriptor['source_sha256'],hashlib.sha256(content).hexdigest())
        confirmed=sum(D(e['extra']) for e in data['events'] if e['operation']=='axs02' and e['date']=='2026-10-15')
        self.assertEqual(confirmed,D('5000000.00'))


if __name__=='__main__':
    unittest.main()
