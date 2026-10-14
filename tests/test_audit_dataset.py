"""Synthetic regression tests: no benchmark data or measured science."""
import csv, json, tempfile, unittest
from pathlib import Path
from scripts.audit_dataset import audit

class DatasetAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.a=root/'annotations.csv';self.p=root/'predictions.csv';self.s=root/'splits.json'
        self.ann=[dict(system_id=f's{i}',ligand_instance_chain='A',group_key=f'g{i}',cluster=f'c{i}') for i in range(3)]
        self.pred=[dict(system_id=f's{i}',ligand_instance_chain='A',seed='0',sample='0',ranking_score='.8',rmsd='1.5') for i in range(3)]
        self.s.write_text(json.dumps(dict(g0='train',g1='val',g2='test')))
        self.save()
    def tearDown(self): self.tmp.cleanup()
    def save(self):
        for path,rows in [(self.a,self.ann),(self.p,self.pred)]:
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def test_valid_dataset(self):
        self.assertEqual(audit(self.a,self.p,self.s)['status'],'PASS')
    def test_reference_metric_leak(self):
        result=audit(self.a,self.p,self.s,['ranking_score','rmsd'])
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any('leakage' in s for s in result['errors']))
    def test_pocket_cluster_leak(self):
        self.ann[1]['cluster']='c0';self.save()
        self.assertIn('Cluster leakage across splits',audit(self.a,self.p,self.s)['errors'])
    def test_unmapped_prediction(self):
        self.pred[1]['system_id']='other';self.save()
        self.assertIn('Predictions without annotation mapping',audit(self.a,self.p)['errors'])
    def test_duplicate_identity(self):
        self.pred[1]=dict(self.pred[0]);self.save()
        self.assertTrue(any('Duplicate' in s for s in audit(self.a,self.p)['errors']))

if __name__=='__main__':unittest.main()
