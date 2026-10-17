"""Synthetic parquet fixture tests. pip install pyarrow."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = pq = None

from scripts.audit_parquet_similarity import audit


@unittest.skipUnless(pa is not None, "pyarrow not installed")
class ParquetSimilarityAuditTests(unittest.TestCase):
    def test_cross_partition_links_and_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            annotations = root / "annotations.csv"
            with annotations.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["group_key", "system_id", "cluster"])
                writer.writeheader()
                writer.writerows([
                    {"group_key": "g0", "system_id": "s0", "cluster": "c0"},
                    {"group_key": "g1", "system_id": "s1", "cluster": "c1"},
                    {"group_key": "g2", "system_id": "s2", "cluster": "c2"},
                ])
            manifest = root / "splits.json"
            manifest.write_text(json.dumps({"g0": "train", "g1": "test", "g2": "val"}))
            parquet = root / "similarity.parquet"
            table = pa.table({
                "group_key": ["g0", "g1", "g2", "g0"],
                "target_system": ["s1", "s0", "not-in-dataset", "s1"],
                "sucos_shape_pocket_qcov": [91.0, 30.0, 97.0, 88.0],
                "pocket_qcov": [89.0, 24.0, 40.0, 89.0],
            })
            pq.write_table(table, parquet, row_group_size=2)
            report = audit(annotations, manifest, parquet, threshold=80)
            self.assertEqual(report["unique_cross_partition_links"], 2)
            self.assertEqual(report["threshold_links_by_metric"]["sucos_shape_pocket_qcov"], 1)
            self.assertEqual(report["threshold_links_by_metric"]["pocket_qcov"], 1)
            self.assertEqual(report["query_groups_without_any_similarity_rows"], 0)
            self.assertEqual(report["row_counters"]["target_not_in_benchmark_annotations"], 1)
            self.assertEqual(report["status"], "SOURCE_MD5_MISMATCH_REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
