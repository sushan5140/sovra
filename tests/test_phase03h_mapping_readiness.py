"""Synthetic Phase 03H mapping readiness tests; NO molecular accuracy scoring."""
import csv
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from scripts.phase03h_mapping_readiness import audit


class MappingReadinessTests(unittest.TestCase):
    def fixture(self, root, duplicate_model_chain=False):
        ann = root / "annotations.csv"
        annotations = [
            dict(system_id="s0", ligand_instance_chain="L0", group_key="g0", ligand_is_proper="true"),
            dict(system_id="s1", ligand_instance_chain="L1", group_key="g1", ligand_is_proper="true"),
            dict(system_id="s2", ligand_instance_chain="L2", group_key="g2", ligand_is_proper="false"),
        ]
        with ann.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(annotations[0]))
            w.writeheader()
            w.writerows(annotations)
        manifest = root / "split.json"
        manifest.write_text(json.dumps(dict(g0="train", g1="test", g2="val")))
        rows = [
            dict(target="s0", ligand_instance_chain="L0", method="boltz", seed="0", sample="0", model_ligand_chain="A", model_ligand_ccd_code="ATP", ranking_score="0.9", rmsd="1"),
            dict(target="s0", ligand_instance_chain="L0", method="boltz", seed="0", sample="0", model_ligand_chain="A" if duplicate_model_chain else "B", model_ligand_ccd_code="ATP", ranking_score="0.9", rmsd="3"),
            dict(target="s1", ligand_instance_chain="L1", method="boltz", seed="1", sample="0", model_ligand_chain="C", model_ligand_ccd_code="MOL", ranking_score="0.7", rmsd="1"),
            dict(target="s2", ligand_instance_chain="L2", method="boltz", seed="1", sample="0", model_ligand_chain="C", model_ligand_ccd_code="MOL", ranking_score="0.7", rmsd="1"),
            dict(target="unknown", ligand_instance_chain="L0", method="boltz", seed="0", sample="0", model_ligand_chain="C", model_ligand_ccd_code="ATP", ranking_score="0.9", rmsd="0"),
        ]
        archive = root / "predictions.tar.gz"
        with tarfile.open(archive, "w:gz") as t:
            boltz = root / "boltz.csv"
            with boltz.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            t.add(boltz, arcname="predictions/boltz.csv")
            chai = root / "chai.csv"
            with chai.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerow(dict(rows[0], method="chai"))
                w.writerow(dict(rows[2], method="chai"))
            t.add(chai, arcname="predictions/chai.csv")
        return ann, manifest, archive

    def test_split_coverage_and_pair_intersection(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, m, p = self.fixture(Path(tmp))
            r = audit(a, p, m)
            self.assertEqual(r["proper_annotation_cases_by_split"], {"train": 1, "val": 0, "test": 1})
            tables = {row["source_table"]: row for row in r["tables"]}
            boltz = tables["boltz.csv"]
            self.assertEqual(boltz["counts"]["matched_nonproper_rows"], 1)
            self.assertEqual(boltz["counts"]["unmatched_target"], 1)
            self.assertEqual(boltz["counts"]["repeated_case_seed_sample_keys"], 1)
            self.assertEqual(boltz["counts"].get("repeated_keys_with_colliding_model_chain", 0), 0)
            self.assertEqual(boltz["score_and_reference_cases_by_split"], {"train": 1, "val": 0, "test": 1})
            self.assertEqual(r["paired_evaluable_case_intersections"]["boltz.csv__chai.csv"], {"train": 1, "val": 0, "test": 1})

    def test_colliding_model_chain_detected_without_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, m, p = self.fixture(Path(tmp), duplicate_model_chain=True)
            r = audit(a, p, m)
            b = next(row for row in r["tables"] if row["source_table"] == "boltz.csv")
            self.assertEqual(b["counts"]["repeated_keys_with_colliding_model_chain"], 1)
            self.assertEqual(b["counts"]["proper_rows"], 3)

    def test_bad_manifest_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, m, p = self.fixture(Path(tmp))
            m.write_text(json.dumps({"g0": "train", "g1": "test"}))
            with self.assertRaises(ValueError):
                audit(a, p, m)


if __name__ == "__main__":
    unittest.main()
