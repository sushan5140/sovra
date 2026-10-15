"""Synthetic-only tests for deterministic group/cluster splits."""
import csv,tempfile,unittest
from pathlib import Path
from scripts.make_candidate_splits import assign

class CandidateSplitsTests(unittest.TestCase):
    def test_deterministic_and_cluster_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ann.csv'
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=['group_key','cluster']);writer.writeheader()
                for i in range(30):
                    for j in range(2):
                        writer.writerow({'group_key':f'g{i}_{j}','cluster':f'c{i}'})
            a,meta=assign(path)
            b,_=assign(path)
            self.assertEqual(a,b)
            for i in range(30):self.assertEqual(a[f'g{i}_0'],a[f'g{i}_1'])
            self.assertEqual(sum(meta['cluster_counts'].values()),30)

    def test_conflicting_groups_fail(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ann.csv'
            path.write_text('group_key,cluster\na,c0\na,c1\n')
            with self.assertRaises(ValueError):assign(path)

if __name__=='__main__':unittest.main()
