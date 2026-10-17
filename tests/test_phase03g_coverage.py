"""Synthetic fixtures for Phase 03G; no benchmark results are asserted."""
import csv
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.phase03g_coverage import audit


class CoverageTests(unittest.TestCase):
    def fixture(self, root, rows=None, annotation_rows=None):
        annotations = root / "annotations.csv"
        preds = root / "preds.csv"
        manifest = root / "split.json"
        annot = annotation_rows or [
            {"system_id": "s0", "ligand_instance_chain": "A", "group_key": "g0", "cluster": "c0", "ligand_is_proper": "True"},
            {"system_id": "s1", "ligand_instance_chain": "B", "group_key": "g1", "cluster": "c1", "ligand_is_proper": "False"},
            {"system_id": "s2", "ligand_instance_chain": "C", "group_key": "g2", "cluster": "c2", "ligand_is_proper": "True"},
        ]
        with annotations.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=annot[0].keys())
            writer.writeheader()
            writer.writerows(annot)
        data = rows if rows is not None else [
            {"target": "s0", "ligand_instance_chain": "A", "method": "af3", "seed": "0", "sample": "0", "ranking_score": "0.5", "rmsd": "1.4"},
            {"target": "s0", "ligand_instance_chain": "A", "method": "af3", "seed": "1", "sample": "0", "ranking_score": "0.6", "rmsd": "1.2"},
            {"target": "s1", "ligand_instance_chain": "B", "method": "af3", "seed": "0", "sample": "0", "ranking_score": "0.9", "rmsd": "1.0"},
            {"target": "s2", "ligand_instance_chain": "C", "method": "af3", "seed": "0", "sample": "0", "ranking_score": "", "rmsd": "2.0"},
            {"target": "s0", "ligand_instance_chain": "", "method": "af3", "seed": "0", "sample": "0", "ranking_score": "0.9", "rmsd": "2.0"},
            {"target": "UNKNOWN", "ligand_instance_chain": "A", "method": "af3", "seed": "0", "sample": "0", "ranking_score": "0.9", "rmsd": "2.0"},
        ]
        with preds.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        manifest.write_text(json.dumps({"g0": "train", "g1": "val", "g2": "test"}))
        archive = root / "prediction.tar.gz"
        with tarfile.open(archive, "w:gz") as t:
            t.add(preds, arcname="prediction/af3.csv")
        return annotations, archive, manifest

    def test_partition_eligibility_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            a, p, m = self.fixture(Path(folder))
            report = audit(a, p, m)
            self.assertEqual(report["annotation_proper_ligand_cases"], 2)
            table = report["model_tables"][0]
            c = table["counts"]
            self.assertEqual(c["rows_total"], 6)
            self.assertEqual(c["matched_rows"], 4)
            self.assertEqual(c["matched_improper_ligand_rows"], 1)
            self.assertEqual(c["unmatched_target"], 1)
            self.assertEqual(c["unmatched_missing_ligand_chain"], 1)
            self.assertEqual(c["proper_rows_with_score_and_reference"], 2)
            self.assertEqual(table["cases_with_two_or_more_distinct_seed_sample_pairs"], 1)
            self.assertEqual(table["proper_rows_by_split"], {"test": 1, "train": 2})
            self.assertEqual(report["candidate_group_count_by_split"], {"train": 1, "val": 1, "test": 1})

    def test_no_score_rfaa(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [{"target": "s0", "ligand_instance_chain": "A", "method": "rfaa", "rmsd": "1.2"}]
            a, p, m = self.fixture(root, rows)
            table = audit(a, p, m)["model_tables"][0]
            self.assertFalse(table["has_ranking_score_column"])
            self.assertEqual(table["counts"]["proper_rows_with_score_and_reference"], 0)

    def test_unapproved_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, p, m = self.fixture(root)
            m.write_text(json.dumps({"g0": "train", "g1": "train", "g2": "test", "extra": "test"}))
            with self.assertRaises(ValueError):
                audit(a, p, m)

    def test_improper_boolean_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, p, m = self.fixture(root)
            contents = a.read_text().replace(",False", ",unknown")
            a.write_text(contents)
            with self.assertRaises(ValueError):
                audit(a, p, m)


if __name__ == "__main__":
    unittest.main()
