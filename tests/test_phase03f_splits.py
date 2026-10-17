"""Synthetic regression coverage for Phase 03F observed-link split rebuilding."""
import csv
import tempfile
import unittest
from pathlib import Path

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = pq = None

from scripts.phase03f_rebuild_splits import audit


@unittest.skipUnless(pa is not None, "pyarrow unavailable")
class Phase03FSplitsTests(unittest.TestCase):
    def make_input(self, root):
        ann = root / "annotations.csv"
        rows = [
            dict(group_key="g0", system_id="s0", cluster="c0", entry_pdb_id="p0"),
            dict(group_key="g1", system_id="s1", cluster="c1", entry_pdb_id="p1"),
            dict(group_key="g2", system_id="s2", cluster="c2", entry_pdb_id="p2"),
            dict(group_key="g3", system_id="s3", cluster="c3", entry_pdb_id="p3"),
            dict(group_key="g4", system_id="s4", cluster="c4", entry_pdb_id="p4"),
            dict(group_key="g5", system_id="s5", cluster="c5", entry_pdb_id="p5"),
        ]
        with ann.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        parquet = root / "similarity.parquet"
        data = pa.table({
            "group_key": ["g0", "g1", "g3", "g5"],
            "target_system": ["s1", "s2", "s4", "not-in-annotation"],
            "protein_fident_weighted_sum": [88.0, 76.0, 42.0, 99.0],
            "pocket_fident": [10.0, 10.0, 96.0, 99.0],
            "pocket_fident_qcov": [5.0, 5.0, 35.0, 99.0],
        })
        pq.write_table(data, parquet, row_group_size=2)
        return ann, parquet

    def test_threshold_sensitivity_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ann, parquet = self.make_input(root)
            manifest = root / "manifest.json"
            report = audit(ann, parquet, manifest)
            import json
            splits = json.loads(manifest.read_text())
            self.assertEqual(splits["g0"], splits["g1"])
            self.assertEqual(splits["g3"], splits["g4"])
            self.assertEqual(report["counter"]["rows_scanned"], 4)
            self.assertEqual(report["candidate_summary"]["protein_or_pocket_80"]["components"], 4)
            self.assertEqual(report["candidate_summary"]["protein_or_coverage_adjusted_pocket_80"]["components"], 5)
            self.assertEqual(report["candidate_summary"]["protein_or_pocket_70"]["components"], 3)
            self.assertEqual(manifest.read_text(), self._run_again(ann, parquet, root))

    def _run_again(self, ann, parquet, root):
        again = root / "again.json"
        audit(ann, parquet, again)
        return again.read_text()

    def test_shared_pdb_identity_kept_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ann, parquet = self.make_input(root)
            contents = ann.read_text().replace("g5,s5,c5,p5", "g5,s5,c5,p0")
            ann.write_text(contents)
            manifest = root / "splits.json"
            audit(ann, parquet, manifest)
            import json
            splits = json.loads(manifest.read_text())
            self.assertEqual(splits["g0"], splits["g5"])


if __name__ == "__main__":
    unittest.main()
