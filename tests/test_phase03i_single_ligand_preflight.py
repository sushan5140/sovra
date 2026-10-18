"""Synthetic-only tests for Phase 03I single-ligand population audit."""
import csv
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from scripts.phase03i_single_ligand_preflight import audit


class StrictCohortTests(unittest.TestCase):
    def inputs(self, root, repeat=False):
        annotations = [
            dict(system_id="a", ligand_instance_chain="1.L", group_key="g0",
                 ligand_is_proper="true", num_ligand_chains="1"),
            dict(system_id="b", ligand_instance_chain="1.M", group_key="g1",
                 ligand_is_proper="true", num_ligand_chains="2"),
            dict(system_id="b", ligand_instance_chain="1.N", group_key="g2",
                 ligand_is_proper="true", num_ligand_chains="2"),
            dict(system_id="c", ligand_instance_chain="1.O", group_key="g3",
                 ligand_is_proper="false", num_ligand_chains="1"),
            dict(system_id="d", ligand_instance_chain="1.P", group_key="g4",
                 ligand_is_proper="true", num_ligand_chains="1"),
        ]
        path = root / "annotations.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=annotations[0])
            writer.writeheader()
            writer.writerows(annotations)
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(dict(g0="train",g1="val",g2="val",g3="test",g4="test")))
        rows = [
            dict(target="a",ligand_instance_chain="1.L",method="boltz",seed="1",sample="0",ranking_score="0.9",rmsd="1"),
            dict(target="d",ligand_instance_chain="1.P",method="boltz",seed="1",sample="0",ranking_score="0.8",rmsd="3"),
            dict(target="b",ligand_instance_chain="1.M",method="boltz",seed="1",sample="0",ranking_score="0.8",rmsd="0"),
        ]
        if repeat:
            rows.append(dict(rows[0]))
        archive = root / "predictions.tar.gz"
        with tarfile.open(archive, "w:gz") as tf:
            for method in ("boltz","chai"):
                output=root / f"{method}.csv"
                with output.open("w",newline="") as f:
                    writer=csv.DictWriter(f,fieldnames=rows[0])
                    writer.writeheader()
                    writer.writerows([dict(row,method=method) for row in rows])
                tf.add(output,arcname="predictions/"+method+".csv")
        return path,archive,manifest

    def test_strict_one_ligand_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,p,m=self.inputs(Path(tmp))
            r=audit(a,p,m)
            self.assertEqual(r["proper_single_ligand_cases_by_split"],dict(train=1,val=0,test=1))
            self.assertEqual(r["all_proper_ligand_cases_by_split"],dict(train=1,val=2,test=1))
            b=r["method_tables"]["boltz.csv"]
            self.assertEqual(b["cases"]["scored_unique_complete_reference"],dict(train=1,val=0,test=1))
            self.assertEqual(r["paired_single_ligand_complete_reference_case_intersections"]["boltz.csv__chai.csv"],
                             dict(train=1,val=0,test=1))

    def test_ambiguous_run_quarantines_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,p,m=self.inputs(Path(tmp),repeat=True)
            r=audit(a,p,m)
            b=r["method_tables"]["boltz.csv"]
            self.assertEqual(b["exclusion_cases"].get("case_with_repeated_seed_sample"),1)
            self.assertEqual(b["cases"]["scored_unique_complete_reference"],dict(train=0,val=0,test=1))

    def test_unknown_manifest_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,p,m=self.inputs(Path(tmp))
            m.write_text(json.dumps({"g0":"train"}))
            with self.assertRaises(ValueError):
                audit(a,p,m)


if __name__=="__main__":
    unittest.main()
