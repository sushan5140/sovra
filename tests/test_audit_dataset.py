"""Synthetic tests for real Runs N' Poses prediction schema (no research results)."""
import csv,json,tempfile,unittest,tarfile
from pathlib import Path
from scripts.audit_dataset import audit

class DatasetAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.a=root/'annotations.csv';self.p=root/'predictions.csv';self.s=root/'splits.json'
        self.ann=[dict(system_id=f's{i}',ligand_instance_chain='1.B',group_key=f'g{i}',cluster=f'c{i}') for i in range(3)]
        self.pred=[dict(target=f's{i}',ligand_instance_chain='1.B',method='af3',seed='1',sample='0',ranking_score='0.8',rmsd='1.2') for i in range(3)]
        self.s.write_text(json.dumps(dict(g0='train',g1='val',g2='test')))
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):
        for path,rows in [(self.a,self.ann),(self.p,self.pred)]:
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def test_valid_dataset(self):
        r=audit(self.a,self.p,self.s)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['prediction_files'][0]['matched_rows'],3)
    def test_reference_metric_leak(self):
        self.assertEqual(audit(self.a,self.p,self.s,['ranking_score','rmsd'])['status'],'FAIL')
    def test_unknown_feature_rejected(self):
        self.assertEqual(audit(self.a,self.p,self.s,['lddt_pli'])['status'],'FAIL')
    def test_pocket_cluster_leak(self):
        self.ann[1]['cluster']='c0';self.save()
        self.assertIn('Cluster leakage across splits',audit(self.a,self.p,self.s)['errors'])
    def test_unmapped_prediction(self):
        self.pred[1]['target']='other';self.save()
        self.assertEqual(audit(self.a,self.p)['prediction_files'][0]['unmatched_rows'],1)
    def test_duplicate_preserved(self):
        self.pred.append(dict(self.pred[0]));self.save()
        r=audit(self.a,self.p)
        self.assertEqual(r['prediction_files'][0]['rows'],4)
        self.assertEqual(r['prediction_files'][0]['repeated_extended_identifiers'],1)
    def test_multiple_ligands_are_distinct(self):
        self.ann.append(dict(system_id='s0',ligand_instance_chain='1.C',group_key='g0',cluster='c0'))
        self.pred.append(dict(self.pred[0],ligand_instance_chain='1.C'));self.save()
        self.assertEqual(audit(self.a,self.p)['prediction_files'][0]['repeated_extended_identifiers'],0)
    def test_no_score_is_reported(self):
        for row in self.pred:row.pop('ranking_score')
        self.save()
        self.assertFalse(audit(self.a,self.p)['prediction_files'][0]['has_ranking_score'])
    def test_tar_gz(self):
        tar=Path(self.tmp.name)/'predictions.tar.gz'
        with tarfile.open(tar,'w:gz') as f:f.add(self.p,arcname='predictions/af3.csv')
        self.assertEqual(len(audit(self.a,tar)['prediction_files']),1)
if __name__=='__main__':unittest.main()
