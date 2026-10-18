"""Generated synthetic inputs only; assertions test software, not science."""

import csv
import json
import random
import subprocess
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from scripts.phase04_baselines import bootstrap_interval, evaluate, paired_comparison, select_top1
from scripts.phase04_eligibility import Candidate, InputError, load_inputs


def annotation(system="s0", chain="A", group="g0", cluster="c0", **extra):
    return dict(system_id=system, ligand_instance_chain=chain, group_key=group,
                cluster=cluster, ligand_is_proper="true", data_origin="synthetic", **extra)


def prediction(target="s0", chain="A", seed="0", score="0.9", rmsd="5", **extra):
    row = dict(target=target, ligand_instance_chain=chain, method="boltz", seed=seed,
               sample="0", ranking_score=score, rmsd=rmsd, data_origin="synthetic")
    row.update(extra)
    return row


def write_csv(path, rows):
    names = sorted({name for row in rows for name in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


class Phase04Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.annotations = [annotation(), annotation("s1", "B", "g1", "c1"),
                            annotation("s2", "C", "g2", "c2")]
        self.rows = [prediction(), prediction(seed="1", score="0.1", rmsd="1"),
                     prediction("s1", "B", rmsd="1"), prediction("s2", "C", rmsd="1")]
        self.splits = {"g0": "train", "g1": "val", "g2": "test"}

    def inputs(self, method="boltz.csv"):
        a, p, m = (self.root / name for name in ("annotations.csv", method, "split.json"))
        write_csv(a, self.annotations)
        write_csv(p, self.rows)
        m.write_text(json.dumps(self.splits), encoding="utf-8")
        return a, p, m

    def run_eval(self, method="boltz.csv", **kwargs):
        options = dict(method=method, score_direction="higher", success_threshold=2.0,
                       synthetic_only=True, bootstrap_iterations=100)
        options.update(kwargs)
        return evaluate(*self.inputs(method), **options)

    def test_top1_is_not_oracle_and_direction_is_required(self):
        higher = self.run_eval()
        self.assertFalse(higher["cases"][0]["top1_success"])
        self.assertTrue(higher["cases"][0]["oracle_success"])
        lower = self.run_eval(score_direction="lower")
        self.assertTrue(lower["cases"][0]["top1_success"])
        self.assertEqual(lower["cases"][0]["selected"]["seed"], "1")
        with self.assertRaises(TypeError):
            select_top1([])
        with self.assertRaises(InputError):
            self.run_eval(score_direction="automatic")

    def test_reference_mutation_cannot_change_decision_or_coverage(self):
        before = self.run_eval(risk_thresholds=[0.5])
        for row in self.rows:
            row.update(rmsd="0" if row["rmsd"] == "5" else "nan", lddt_pli="999",
                       model_ligand_chain_rmsd="reference-dependent-change")
        after = self.run_eval(risk_thresholds=[0.5])
        self.assertEqual([c["selected"] for c in before["cases"]], [c["selected"] for c in after["cases"]])
        self.assertEqual([c["selection_status"] for c in before["cases"]], [c["selection_status"] for c in after["cases"]])
        for split in ("train", "val", "test"):
            for old, new in zip(before["partitions"][split]["risk_coverage"], after["partitions"][split]["risk_coverage"]):
                self.assertEqual(old["coverage"], new["coverage"])
        self.assertEqual({f.name for f in fields(Candidate)}, {"case", "seed", "sample", "mapping_id", "score"})

    def test_missing_selected_label_never_falls_back(self):
        self.rows[0]["rmsd"] = ""
        case = self.run_eval()["cases"][0]
        self.assertEqual(case["selected"]["seed"], "0")
        self.assertIsNone(case["top1_success"])
        self.assertTrue(case["oracle_success"])
        summary = self.run_eval()["partitions"]["train"]
        self.assertEqual(summary["selected_without_reference"], 1)
        self.assertEqual(summary["selection_coverage"], 1)
        self.assertEqual(summary["evaluation_coverage"], 0)
        self.assertIsNone(summary["top1_accuracy"])

    def test_absent_reference_column_and_partial_oracle(self):
        for row in self.rows:
            row.pop("rmsd")
        report = self.run_eval()
        self.assertTrue(all(c["top1_success"] is None and c["oracle_success"] is None for c in report["cases"]))
        self.rows[0]["rmsd"] = "5"
        self.assertIsNone(self.run_eval()["cases"][0]["oracle_success"])
        self.rows[0]["rmsd"] = "1"
        self.assertTrue(self.run_eval()["cases"][0]["oracle_success"])

    def test_nonfinite_scores_and_invalid_references(self):
        for invalid in ("", "nan", "inf", "-inf", "not-a-number"):
            with self.subTest(invalid=invalid):
                self.rows[0]["ranking_score"] = invalid
                self.rows[1]["rmsd"] = "-1"
                report = self.run_eval()
                self.assertEqual(report["cases"][0]["selected"]["seed"], "1")
                self.assertIsNone(report["cases"][0]["top1_success"])
                self.assertEqual(report["eligibility"]["score_unavailability"]["missing_or_nonfinite_score"], 1)

    def test_no_finite_scores_do_not_become_failures(self):
        self.rows[0]["ranking_score"] = self.rows[1]["ranking_score"] = ""
        report = self.run_eval()
        self.assertEqual(report["cases"][0]["selection_status"], "no_finite_score")
        self.assertIsNone(report["partitions"]["train"]["top1_accuracy"])
        self.assertTrue(report["cases"][0]["oracle_success"])

    def test_rfaa_no_score_seed_or_sample(self):
        self.rows = [dict(target="s0", ligand_instance_chain="A", method="rfaa", rmsd="1", data_origin="synthetic")]
        report = self.run_eval("rfaa.csv")
        self.assertEqual(report["eligibility"]["score_unavailability"], {"score_column_absent": 1})
        self.assertEqual(report["cases"][0]["selection_status"], "no_finite_score")
        self.assertIsNone(report["partitions"]["train"]["top1_error"])
        self.assertEqual(report["partitions"]["train"]["selection_coverage"], 0)

    def test_multi_ligand_target_and_case_denominator(self):
        self.annotations.append(annotation("s0", "B", "g0b", "c0"))
        self.splits["g0b"] = "train"
        self.rows.append(prediction("s0", "B", rmsd="1"))
        report = self.run_eval()
        train = report["partitions"]["train"]
        self.assertEqual(train["proper_cases"], 2)
        self.assertEqual(train["top1_accuracy"], 0.5)
        self.assertEqual(train["annotation_group_count"], 2)
        self.assertEqual(train["resampling_group_count"], 1)
        self.assertEqual(train["top1_accuracy_ci95"]["reason"], "fewer_than_two_groups")

    def test_nonproper_and_unmatched_rows_are_counted(self):
        self.annotations[1]["ligand_is_proper"] = "false"
        self.rows.extend([prediction("UNKNOWN"), prediction(chain="UNKNOWN"), prediction(chain="")])
        report = self.run_eval()
        self.assertEqual(report["eligibility"]["row_exclusions"], {
            "nonproper_ligand": 1, "unmatched_target": 1, "unmatched_ligand_chain": 1,
            "missing_or_padded_case_identity": 1})
        self.assertEqual(report["partitions"]["val"]["proper_cases"], 0)
        self.assertEqual(report["eligibility"]["annotation_cases_by_split"]["val"]["nonproper"], 1)
        self.assertEqual(report["eligibility"]["retained_rows"] + sum(report["eligibility"]["row_exclusions"].values()), len(self.rows))

    def test_prediction_coverage_includes_missing_cases(self):
        self.rows = self.rows[:2]
        report = self.run_eval()
        self.assertEqual(report["partitions"]["test"]["proper_cases"], 1)
        self.assertEqual(report["partitions"]["test"]["selection_coverage"], 0)
        self.assertEqual(report["cases"][-1]["selection_status"], "no_predictions")

    def test_distinct_mapping_provenance_retained(self):
        self.rows[0].update(mapping_id="m1", model_ligand_chain_rmsd="X")
        self.rows.append({**self.rows[0], "mapping_id": "m2", "model_ligand_chain_rmsd": "Y", "rmsd": "0.1"})
        report = self.run_eval()
        case = report["cases"][0]
        self.assertEqual(case["candidate_mappings"], 3)
        self.assertEqual(case["distinct_seed_sample_runs"], 2)
        self.assertEqual(case["selected"]["mapping_id"], "m1")
        self.assertEqual(report["eligibility"]["row_exclusions"], {})
        self.assertEqual(report["eligibility"]["row_provenance"][-1]["source_mapping"]["model_ligand_chain_rmsd"], "Y")

    def test_duplicate_identity_quarantines_every_collision(self):
        self.rows.append(dict(self.rows[0]))
        report = self.run_eval()
        self.assertEqual(report["eligibility"]["row_exclusions"], {"ambiguous_prediction_identity": 2})
        self.assertEqual(report["cases"][0]["selected"]["seed"], "1")
        quarantined = [row for row in report["eligibility"]["row_provenance"] if row["exclusion_reason"]]
        self.assertEqual(len(quarantined), 2)

    def test_reference_mapping_does_not_disambiguate_identity(self):
        self.rows = [prediction(model_ligand_chain_rmsd="X"), prediction(model_ligand_chain_rmsd="Y")]
        report = self.run_eval()
        self.assertEqual(report["eligibility"]["row_exclusions"], {"ambiguous_prediction_identity": 2})
        self.assertEqual(report["cases"][0]["selection_status"], "all_rows_quarantined")
        self.assertIsNone(report["cases"][0]["oracle_success"])

    def test_partially_identified_mappings_quarantined(self):
        self.rows = [prediction(), prediction(mapping_id="m2")]
        self.assertEqual(self.run_eval()["eligibility"]["row_exclusions"], {"ambiguous_prediction_identity": 2})

    def test_missing_seed_is_explicit(self):
        self.rows[0].pop("seed")
        report = self.run_eval()
        self.assertEqual(report["eligibility"]["row_exclusions"], {"missing_run_provenance": 1})

    def test_ties_ignore_file_order_and_labels(self):
        self.rows[1]["ranking_score"] = self.rows[0]["ranking_score"]
        before = self.run_eval()
        self.rows.reverse()
        after = self.run_eval()
        self.assertEqual(before["cases"], after["cases"])
        self.assertEqual(before["partitions"], after["partitions"])
        self.assertEqual(after["cases"][0]["selected"]["seed"], "0")

    def test_source_filename_is_version_identity(self):
        report = self.run_eval("boltz2.csv")
        self.assertEqual(report["protocol"]["method"], "boltz2.csv")
        self.assertEqual(report["eligibility"]["method_labels"], ["boltz"])
        with self.assertRaises(InputError):
            evaluate(*self.inputs(), method="chai.csv", score_direction="higher", success_threshold=2, synthetic_only=True)

    def test_mixed_methods_and_af3_are_blocked(self):
        self.rows[0]["method"] = "chai"
        with self.assertRaises(InputError):
            self.run_eval()
        self.rows[0]["method"] = "af3"
        with self.assertRaisesRegex(InputError, "AlphaFold"):
            self.run_eval()
        with self.assertRaisesRegex(InputError, "AlphaFold"):
            self.run_eval("af3.csv")

    def test_synthetic_gate_is_fail_closed(self):
        with self.assertRaises(InputError):
            self.run_eval(synthetic_only=False)
        self.rows[0]["data_origin"] = "benchmark"
        with self.assertRaises(InputError):
            self.run_eval()
        self.rows[0]["data_origin"] = "synthetic"
        self.annotations[0]["data_origin"] = "real"
        with self.assertRaises(InputError):
            self.run_eval()

    def test_split_manifest_rejects_missing_unknown_and_invalid(self):
        for splits in ({"g0": "train"}, {**self.splits, "extra": "test"},
                       {**self.splits, "g0": "validation"}, {**self.splits, "g0": []}):
            with self.subTest(splits=splits):
                self.splits = splits
                with self.assertRaises(InputError):
                    self.run_eval()

    def test_duplicate_json_keys_rejected(self):
        a, p, m = self.inputs()
        m.write_text('{"g0":"train","g0":"test","g1":"val","g2":"test"}')
        with self.assertRaisesRegex(InputError, "Repeated manifest"):
            load_inputs(a, p, m, method="boltz.csv", synthetic_only=True)

    def test_cluster_system_pdb_component_cross_split_rejected(self):
        for field in ("cluster", "system_id", "entry_pdb_id", "component_id"):
            with self.subTest(field=field):
                originals = [dict(row) for row in self.annotations]
                for index, row in enumerate(self.annotations):
                    row[field] = "shared" if index < 2 else "separate"
                with self.assertRaisesRegex(InputError, "Cross-partition"):
                    self.run_eval()
                self.annotations = originals

    def test_shared_group_multiple_cases_valid(self):
        self.annotations.append(annotation("s0", "B", "g0", "c0"))
        report = self.run_eval()
        self.assertEqual(report["partitions"]["train"]["proper_cases"], 2)
        self.assertEqual(report["partitions"]["train"]["annotation_group_count"], 1)

    def test_duplicate_annotations_and_empty_metadata_rejected(self):
        self.annotations.append(dict(self.annotations[0]))
        with self.assertRaises(InputError) as raised:
            self.run_eval()
        self.assertEqual(raised.exception.count, 2)
        self.annotations.pop()
        for field in ("cluster", "ligand_is_proper"):
            old = self.annotations[0][field]
            self.annotations[0][field] = ""
            with self.assertRaises(InputError):
                self.run_eval()
            self.annotations[0][field] = old

    def test_risk_coverage_both_directions_and_total_abstention(self):
        for direction, threshold in (("higher", 0.95), ("lower", 0.05)):
            report = self.run_eval(score_direction=direction, risk_thresholds=[threshold])
            risk = report["partitions"]["train"]["risk_coverage"]
            self.assertEqual(risk[0]["coverage"], 1)
            self.assertEqual(risk[1]["coverage"], 0)
            self.assertIsNone(risk[1]["error"])
            self.assertIsNone(risk[-1]["error"])
            self.assertEqual(risk[-1]["coverage"], 0)

    def test_threshold_validation_and_inclusive_success(self):
        self.rows[0]["rmsd"] = "2"
        self.assertTrue(self.run_eval()["cases"][0]["top1_success"])
        for option in ({"success_threshold": float("nan")}, {"risk_thresholds": [float("inf")]},
                       {"success_threshold": -1}, {"bootstrap_iterations": 0}, {"subgroup_min_groups": 1}):
            with self.assertRaises(InputError):
                self.run_eval(**option)

    def test_bootstrap_whole_groups_matches_independent_draws(self):
        values = {"large": [1] * 20, "small": [0]}
        actual = bootstrap_interval(values, iterations=40, seed=9)
        rng = random.Random(9)
        expected = []
        for _ in range(40):
            groups = [rng.choice(sorted(values)) for _ in range(2)]
            total = sum(sum(values[group]) for group in groups)
            count = sum(len(values[group]) for group in groups)
            expected.append(total / count)
        expected.sort()
        self.assertEqual(actual["low"], expected[0])
        self.assertEqual(actual["high"], expected[-1])
        self.assertEqual(actual["low"], 0)
        self.assertEqual(actual["high"], 1)
        self.assertEqual(actual, bootstrap_interval(dict(reversed(list(values.items()))), iterations=40, seed=9))

    def test_connected_groups_built_before_eligibility(self):
        self.splits = {key: "test" for key in self.splits}
        self.annotations[0]["cluster"] = self.annotations[1]["cluster"] = "c-shared"
        self.annotations[1]["system_id"] = self.annotations[2]["system_id"] = "s-shared"
        self.annotations[1]["ligand_is_proper"] = "false"
        report = self.run_eval()
        self.assertEqual(report["partitions"]["test"]["resampling_group_count"], 1)

    def test_subgroups_require_metadata_and_enough_groups(self):
        self.splits = {key: "test" for key in self.splits}
        for row in self.annotations:
            row["ligand_exposure"] = "unseen"
        report = self.run_eval(subgroup_min_groups=2)
        subgroups = report["partitions"]["test"]["subgroups"]
        self.assertEqual(subgroups["ligand_exposure"]["unseen"]["evaluable_resampling_groups"], 3)
        self.assertEqual(subgroups["similarity_bin"]["unknown"]["status"], "insufficient_metadata_or_groups")

    def test_paired_comparison_uses_intersection_and_method_directions(self):
        self.splits = {key: "test" for key in self.splits}
        left = self.run_eval()
        self.rows = self.rows[:2]
        for row in self.rows:
            row["method"] = "chai"
        right = self.run_eval("chai.csv", score_direction="lower")
        paired = paired_comparison(left, right)["partitions"]["test"]
        self.assertEqual(paired["paired_cases"], 1)
        self.assertEqual(paired["left_only_evaluable"], 2)
        self.assertEqual(paired["right_only_evaluable"], 0)
        self.assertEqual(paired["left_minus_right_accuracy"], -1)
        right["eligibility"]["hashes"]["manifest"] = "different"
        with self.assertRaises(InputError):
            paired_comparison(left, right)

    def test_paired_comparison_rejects_different_metric_threshold(self):
        with self.assertRaises(InputError):
            paired_comparison(self.run_eval(), self.run_eval(success_threshold=3))

    def test_same_inputs_reproduce_full_report(self):
        first = self.run_eval()
        second = self.run_eval()
        self.assertEqual(first, second)
        self.assertEqual(len(first["eligibility"]["hashes"]["predictions"]), 64)
        json.dumps(first, allow_nan=False)

    def test_train_changes_do_not_tune_test_or_mutate_manifest(self):
        a, p, m = self.inputs()
        manifest_before = m.read_bytes()
        before = self.run_eval(risk_thresholds=[0.5])
        self.rows[0].update(ranking_score="-999", rmsd="0")
        after = self.run_eval(risk_thresholds=[0.5])
        self.assertEqual(before["partitions"]["test"], after["partitions"]["test"])
        self.assertEqual(before["protocol"], after["protocol"])
        self.assertEqual(m.read_bytes(), manifest_before)

    def cli_args(self):
        a, p, m = self.inputs()
        return ["--annotations", str(a), "--predictions", str(p), "--manifest", str(m),
                "--method", "boltz.csv", "--score-direction", "higher", "--success-threshold", "2",
                "--synthetic-only", "--bootstrap-iterations", "20", "--out", str(self.root / "report.json")]

    def cli(self, args, module=True):
        entry = ["-m", "scripts.phase04_baselines"] if module else ["scripts/phase04_baselines.py"]
        return subprocess.run([sys.executable, *entry, *args], cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True, check=False)

    def test_cli_module_script_reproducible_output_and_required_direction(self):
        args = self.cli_args()
        self.assertEqual(self.cli(args).returncode, 0)
        first = (self.root / "report.json").read_bytes()
        self.assertEqual(self.cli(args, module=False).returncode, 0)
        self.assertEqual(first, (self.root / "report.json").read_bytes())
        index = args.index("--score-direction")
        del args[index:index + 2]
        self.assertEqual(self.cli(args).returncode, 2)

    def test_cli_blocked_report_and_input_overwrite_protection(self):
        args = self.cli_args()
        (self.root / "split.json").write_text('{}')
        self.assertEqual(self.cli(args).returncode, 1)
        report = json.loads((self.root / "report.json").read_text())
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["exclusion_counts"], {"manifest_group_mismatch": 1})
        args[-1] = str(self.root / "boltz.csv")
        before = (self.root / "boltz.csv").read_bytes()
        self.assertEqual(self.cli(args).returncode, 2)
        self.assertEqual(before, (self.root / "boltz.csv").read_bytes())

    def test_invalid_csv_schema_and_width_fail_closed(self):
        a, p, m = self.inputs()
        for text in ("target,target,ligand_instance_chain,method,data_origin\ns0,s0,A,boltz,synthetic\n",
                     "target,ligand_instance_chain,method,data_origin\ns0,A,boltz,synthetic,extra\n",
                     "target,ligand_instance_chain,method,data_origin\ns0,A,boltz\n"):
            p.write_text(text)
            with self.assertRaises(InputError):
                load_inputs(a, p, m, method="boltz.csv", synthetic_only=True)


if __name__ == "__main__":
    unittest.main()
