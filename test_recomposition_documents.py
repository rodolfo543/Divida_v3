import hashlib
import json
import unittest
from decimal import Decimal as D
from pathlib import Path
from build_recomposition import split_six, shift_month, cents
from build_documents import public_documents, collect

ROOT = Path(__file__).resolve().parent


class RecompositionTests(unittest.TestCase):
    def test_rounding_closes_all_six_installments(self):
        for value in ['100.00', '0.01', '0.03', '7639997.64', '8835783.97']:
            parts = split_six(value)
            self.assertEqual(len(parts), 6)
            self.assertEqual(sum(D(p) for p in parts), D(value))
            self.assertTrue(all(D(p) >= 0 for p in parts))
            self.assertLessEqual(max(map(cents, parts)) - min(map(cents, parts)), 1)
        self.assertEqual(shift_month('2028-02', -6), '2027-08')

    def test_rules_carencia_months_and_source_integrity(self):
        data = json.loads((ROOT/'data/recomposition.json').read_text(encoding='utf-8'))
        self.assertEqual((ROOT/'data/recomposition.json').read_bytes(), (ROOT/'docs/data/recomposition.json').read_bytes())
        self.assertEqual(data['calendar_sha256'], hashlib.sha256((ROOT/'data/calendar.json').read_bytes()).hexdigest())
        instruments = {i['code']: i for i in data['instruments']}
        self.assertEqual(sum(i['eligible'] for i in instruments.values()), 10)
        self.assertFalse(instruments['AXS412']['eligible'])
        self.assertEqual(instruments['AXSA11']['start_month'], '2027-08')
        self.assertEqual(instruments['AXSE11']['start_month'], '2027-09')
        self.assertEqual(instruments['AXSE12']['start_month'], '2027-09')
        self.assertEqual(instruments['AXS311']['start_month'], '2026-12')
        self.assertEqual(instruments['AXSI11']['start_month'], '2027-03')
        oct_rows = [r for r in data['contributions'] if r['month'] == '2026-10']
        self.assertEqual({r['code'] for r in oct_rows}, {'AXS811', 'AXS911'})
        self.assertEqual(sum(D(r['amount']) for r in oct_rows), D('2745963.60'))
        self.assertEqual(len({(r['code'],r['month']) for r in data['contributions']}),len(data['contributions']))
        for i in instruments.values():
            for cycle in i['cycles']:
                self.assertEqual(sum(D(r['amount']) for r in cycle['installments']),D(cycle['payment']))
                self.assertEqual(cycle['start_month'],shift_month(cycle['payment_date'][:7],-6))
                self.assertEqual(cycle['end_month'],shift_month(cycle['payment_date'][:7],-1))
        self.assertEqual(instruments['AXSA11']['cycles'][-1]['payment_date'],'2041-08-15')
        self.assertEqual(instruments['AXSA21']['cycles'][-1]['payment_date'],'2042-02-19')


class DocumentsTests(unittest.TestCase):
    def test_only_public_documents_are_exposed(self):
        docs = public_documents([{'type':'Contrato','documents':[
            {'id':1,'public':True,'url':'https://arquivos-vx-informa.vortx.com.br/test.pdf','description':'A.pdf','userId':999},
            {'id':2,'public':False,'url':'https://arquivos-vx-informa.vortx.com.br/private.pdf'},
            {'id':3,'public':True,'url':'https://vortx.com.br.evil.example/test.pdf'},
            {'id':4,'public':True,'url':'http://arquivos-vx-informa.vortx.com.br/test.pdf'}]}], 'PAXS12')
        self.assertEqual([d['id'] for d in docs],['1'])
        self.assertNotIn('url',docs[0])
        self.assertNotIn('userId',docs[0])

    def test_failed_refresh_preserves_last_collection_and_documents(self):
        previous={'documents':[{'id':'1','category':'Teste','name':'A.pdf'}],'collected_at':'2026-10-29T12:00:00Z'}
        def fail(_):raise OSError('offline')
        result=collect({'code':'PAXS12','operation_id':97938},previous,fail)
        self.assertEqual(result['documents'],previous['documents'])
        self.assertEqual(result['collected_at'],previous['collected_at'])
        self.assertTrue(result['cached'])

    def test_catalog_has_all_operations_and_no_signed_links(self):
        content=(ROOT/'data/documents.json').read_bytes()
        self.assertEqual(content,(ROOT/'docs/data/documents.json').read_bytes())
        data=json.loads(content)
        self.assertEqual(len(data['instruments']),17)
        self.assertEqual(len({i['operation'] for i in data['instruments']}),13)
        self.assertGreater(len({d['id'] for i in data['instruments'] for d in i['documents']}),0)
        for i in data['instruments']:
            self.assertEqual(len(i['documents']),len({d['id'] for d in i['documents']}))
        self.assertNotIn(b'Signature=',content)
        self.assertNotIn(b'userId',content)
        self.assertNotIn(b'Key-Pair-Id',content)


if __name__=='__main__':unittest.main()
