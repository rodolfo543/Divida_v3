"""Conciliação é uma camada de leitura: conceitos, ausências e cache explícitos."""
import hashlib
import json
import unittest
from decimal import Decimal as D
from pathlib import Path
from build_vortx_comparison import local_row, reference_row, collect_reference

ROOT = Path(__file__).resolve().parent


class ComparisonTests(unittest.TestCase):
    def test_cashflow_does_not_double_count_amex(self):
        row = reference_row({"paymentDate": "2026-10-15", "amortization": "63.5",
                             "ordinaryCashflowAmount": "4.7", "extraordinaryAmortization": "58.8"})
        self.assertEqual(row['ordinary'], '4.70000000')
        self.assertEqual(row['extra'], '58.80000000')
        self.assertIsNone(row['paid_interest'])

    def test_ex_event_and_cash_units(self):
        row = local_row({'date': '15/10/2026', 'pu_cheio': '1100', 'pu_vazio': '1000',
                         'pu_total': '75', 'interest': '500', 'pu_amort': '70',
                         'raw': {'Amortizacao_Extraordinaria': '60'}}, D('100'))
        self.assertEqual(row['empty'], '1025.00000000')
        self.assertEqual(row['empty_model'], '1000.00000000')
        self.assertEqual(row['paid_interest'], '5.00000000')
        self.assertEqual(row['ordinary'], '10.00000000')

    def test_interpolation_does_not_repeat_upcoming_incorporation(self):
        row = local_row({'date': '30/10/2026', 'sort_key': 'daily-AXSC12', 'pu_total': 0,
                         'raw': {'PU_Juros_Incorporado': '48.1003328'}}, D('64000'))
        self.assertIsNone(row['incorporation'])
        self.assertIsNone(row['total'])

    def test_failure_keeps_original_collection_time(self):
        previous = {'history': [{'d': '2026-10-29'}], 'history_collected_at': '2026-10-29T10:00:00Z'}
        def fail(_):
            raise OSError('indisponível')
        result = collect_reference({'code': 'PAXS12', 'operation_id': 97938}, previous, fail)
        self.assertEqual(result['history'], previous['history'])
        self.assertEqual(result['history_collected_at'], previous['history_collected_at'])
        self.assertTrue(result['cached'])
        self.assertEqual(len(result['errors']), 3)

    def test_ficha_mismatch_is_rejected(self):
        result = collect_reference({'code': 'PAXS12', 'operation_id': 97938}, fetch=lambda _: {
            'success': True, 'unitPrices': [], 'operations': [{'operation': {'ifCode': 'OTHER'}}]})
        self.assertEqual(result['terms'], {})
        self.assertIn('Código IF', result['errors'][0])

    def test_catalog_snapshots_and_original_sources(self):
        catalog = json.loads((ROOT / 'vortx_catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog), 17)
        self.assertEqual(len({c['code'] for c in catalog}), 17)
        self.assertEqual(len({c['operation_id'] for c in catalog}), 17)
        self.assertEqual({c['code'] for c in catalog if c.get('pending')}, {'AXSC12', 'AXSC22', 'AXSI11'})
        digests = {}
        for item in catalog:
            source = ROOT / 'data/operations' / (item['operation'] + '.json')
            digests.setdefault(item['operation'], hashlib.sha256(source.read_bytes()).hexdigest())
            path = Path('data/vortx/instruments') / (item['code'] + '.json')
            content = (ROOT / path).read_bytes()
            self.assertEqual(content, (ROOT / 'docs' / path).read_bytes())
            snap = json.loads(content)
            self.assertEqual(snap['local_source_sha256'], digests[item['operation']])
            self.assertGreater(len(snap['reference']['history']), 0)
            for key in ('local_rows',):
                dates = [row['d'] for row in snap[key]]
                self.assertEqual(len(dates), len(set(dates)), item['code'])


if __name__ == '__main__':
    unittest.main()
