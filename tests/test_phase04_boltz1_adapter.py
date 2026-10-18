"""Synthetic adversarial proofs of the adapter's reference-blind API boundary."""

import csv
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import fields, FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from scripts.phase04_boltz1_adapter import SOURCE, preflight, prepare_synthetic, strict_cohort
from scripts.phase04_eligibility import InputError, sha256
from scripts.phase04_evaluation_reference import EvaluationReference, FUTURE_REAL_PROTOCOL, associate_after_selection
from scripts.phase04_prediction_index import (
    PREDICTION_FIELDS, PredictionIndex, PredictionRun, build_prediction_index, rank_prediction_index,
)


def write_csv(path, rows):
    names = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


class ProjectionOnly(dict):
    """Fail on any attempted access outside the four inference keys."""

    def get(self, key, default=None):
        if key not in PREDICTION_FIELDS:
            raise AssertionError("Reference/unproven field accessed: " + key)
        return super().get(key, default)

    def items(self):
        raise AssertionError("Raw-row enumeration is forbidden")

    def values(self):
        raise AssertionError("Raw-row enumeration is forbidden")

    def __getitem__(self, key):
        raise AssertionError("Only allowlisted get projection is expected")


class BoltzAdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.annotations = [dict(system_id=f"private-target-{i}", group_key=f"private-group-{i}",
                                 cluster=f"private-cluster-{i}", ligand_instance_chain=f"ref-chain-{i}",
                                 ligand_is_proper="true", num_ligand_chains="1", data_origin="synthetic")
                            for i in range(3)]
        self.rows = [dict(target=f"private-target-{i}", seed=str(seed), sample="0", ranking_score=score,
                          method="boltz", data_origin="synthetic", rmsd=label, lddt_pli="0.8",
                          ligand_instance_chain=f"ref-chain-{i}", model_ligand_chain_rmsd="mapped-A",
                          model_ligand_chain_lddt_pli="mapped-B", target_ligand_chain_rmsd="ref-chain")
                     for i in range(3) for seed, score, label in (("0", "0.9", "9"), ("1", "0.1", "1"))]
        self.manifest = {f"private-group-{i}": split for i, split in enumerate(("train", "val", "test"))}

    def inputs(self):
        a, p, m, s = (self.root / name for name in ("annotations.csv", "boltz.csv", "manifest.json", "source.json"))
        write_csv(a, self.annotations)
        write_csv(p, self.rows)
        m.write_text(json.dumps(self.manifest), encoding="utf-8")
        s.write_text(json.dumps({**SOURCE, "input_kind": "synthetic", "input_sha256": {
            "annotations": sha256(a), "predictions": sha256(p), "manifest": sha256(m),
        }}), encoding="utf-8")
        return a, p, m, s

    def prepare(self):
        return prepare_synthetic(*self.inputs(), synthetic_only=True)

    def test_four_field_index_and_higher_first(self):
        index, report = self.prepare()
        self.assertEqual({field.name for field in fields(PredictionRun)}, set(PREDICTION_FIELDS))
        self.assertEqual([field.name for field in fields(PredictionIndex)], ["runs"])
        self.assertEqual(len(index.runs), 6)
        self.assertTrue(all(decision.selected.seed == "0" for decision in rank_prediction_index(index)))
        self.assertEqual(report["selection_protocol"]["score_direction"], "higher")
        self.assertFalse(report["real_evaluation_enabled"])
        self.assertEqual(report["partitions"]["test"]["indexed_targets"], 1)

    def test_poisoned_reference_values_are_never_accessed(self):
        class Poison:
            def __str__(self):
                raise AssertionError("Reference value inspected")

            def __float__(self):
                raise AssertionError("Reference value converted")

        row = ProjectionOnly(target="toy", seed="0", sample="0", ranking_score="0.7")
        for field in ("rmsd", "lddt_pli", "ligand_instance_chain", "target_ligand_chain_unproven",
                      "model_ligand_chain_rmsd", "model_ligand_chain_lddt_pli", "novel_rmsd", "novel_lddt_pli",
                      "model_ligand_ccd_code", "mapping_id"):
            row[field] = Poison()
        index, _ = build_prediction_index([row], ["toy"])
        with patch("builtins.open", side_effect=AssertionError("Selection attempted file access")):
            self.assertEqual(rank_prediction_index(index)[0].selected.identity, ("toy", "0", "0"))

    def test_reference_permutation_and_suffix_fields_do_not_change_decisions(self):
        before, old_report = self.prepare()
        for i, row in enumerate(self.rows):
            row.update(rmsd=("nan" if i % 2 else "0"), lddt_pli="",
                       ligand_instance_chain="different-reference",
                       model_ligand_chain_rmsd="wrong", model_ligand_chain_lddt_pli="wrong",
                       target_ligand_chain_rmsd="different", target_ligand_chain_lddt_pli="different",
                       unexpected_rmsd="-100", unexpected_lddt_pli="100", mapping_id="reference-derived")
        for row in self.annotations:
            row["ligand_instance_chain"] = ""
        after, new_report = self.prepare()
        self.assertEqual(before, after)
        self.assertEqual(rank_prediction_index(before), rank_prediction_index(after))
        self.assertEqual(old_report["partitions"], new_report["partitions"])
        self.assertEqual(old_report["row_counts"], new_report["row_counts"])
        self.assertNotEqual(old_report["input_sha256"], new_report["input_sha256"])

    def test_reference_columns_can_be_absent(self):
        expected, _ = self.prepare()
        keep = {*PREDICTION_FIELDS, "method", "data_origin"}
        self.rows = [{key: value for key, value in row.items() if key in keep} for row in self.rows]
        for row in self.annotations:
            row.pop("ligand_instance_chain")
        actual, _ = self.prepare()
        self.assertEqual(expected, actual)

    def test_ties_and_row_order_are_deterministic(self):
        for row in self.rows:
            row["ranking_score"] = "0.5"
        index, before = self.prepare()
        self.rows.reverse()
        self.annotations.reverse()
        reordered, after = self.prepare()
        self.assertEqual(index, reordered)
        self.assertEqual(before["partitions"], after["partitions"])
        self.assertTrue(all(d.selected.seed == "0" for d in rank_prediction_index(index)))

    def test_missing_and_nonfinite_scores(self):
        for score in ("", "nan", "inf", "-inf", "bad"):
            with self.subTest(score=score):
                self.rows[0]["ranking_score"] = score
                index, report = self.prepare()
                self.assertEqual(rank_prediction_index(index)[0].selected.seed, "1")
                self.assertEqual(report["row_counts"]["missing_score_rows"], 1)
                self.assertEqual(report["partitions"]["train"]["missing_score_rows"], 1)
        for row in self.rows:
            row.pop("ranking_score")
        index, report = self.prepare()
        self.assertFalse(index.runs)
        self.assertFalse(report["schema_presence"]["prediction_fields"]["ranking_score"])
        self.assertEqual(report["partitions"]["test"]["target_status_counts"], {"no_finite_score": 1})

    def test_missing_seed_or_sample_quarantines_whole_target(self):
        for field in ("seed", "sample"):
            original = self.rows[0][field]
            self.rows[0][field] = ""
            index, report = self.prepare()
            self.assertEqual(report["row_counts"]["quarantined_rows"], 2)
            self.assertEqual(report["partitions"]["train"]["target_status_counts"], {"missing_or_invalid_run_id": 1})
            self.assertFalse(any(run.target == "private-target-0" for run in index.runs))
            self.rows[0][field] = original

    def test_missing_run_column_is_reported(self):
        for row in self.rows:
            row.pop("seed")
        index, report = self.prepare()
        self.assertFalse(index.runs)
        self.assertEqual(report["row_counts"]["quarantined_rows"], 6)
        self.assertFalse(report["schema_presence"]["prediction_fields"]["seed"])

    def test_duplicate_before_score_filter_quarantines_entire_target(self):
        self.rows.append({**self.rows[0], "ranking_score": "", "rmsd": "0", "ligand_instance_chain": "other",
                          "model_ligand_chain_rmsd": "other", "mapping_id": "cannot-disambiguate"})
        index, report = self.prepare()
        self.assertEqual(report["row_counts"]["quarantined_rows"], 3)
        self.assertEqual(report["partitions"]["train"]["target_status_counts"], {"duplicate_run_id": 1})
        self.assertFalse(any(run.target == "private-target-0" for run in index.runs))

    def test_one_proper_among_multiple_total_ligands_is_excluded(self):
        self.annotations[0]["num_ligand_chains"] = "2"
        _, report = self.prepare()
        self.assertEqual(report["partitions"]["train"]["cohort_exclusion_systems"], {"not_one_total_ligand": 1})
        self.assertEqual(report["row_counts"]["outside_cohort_rows"], 2)

    def test_repeated_annotation_system_excluded_even_with_one_proper(self):
        self.annotations.append({**self.annotations[0], "ligand_is_proper": "false", "ligand_instance_chain": "second"})
        _, report = self.prepare()
        self.assertEqual(report["partitions"]["train"]["cohort_exclusion_systems"], {"multiple_annotation_rows": 1})

    def test_nonproper_singleton_excluded(self):
        self.annotations[0]["ligand_is_proper"] = "false"
        _, report = self.prepare()
        self.assertEqual(report["partitions"]["train"]["cohort_exclusion_systems"], {"nonproper_ligand": 1})

    def test_invalid_and_outside_targets_have_explicit_counts(self):
        self.rows.extend([{**self.rows[0], "target": ""}, {**self.rows[0], "target": "unknown"}])
        _, report = self.prepare()
        counts = report["row_counts"]
        self.assertEqual(counts["invalid_target_rows"], 1)
        self.assertEqual(counts["outside_cohort_rows"], 1)
        self.assertEqual(sum(value for key, value in counts.items() if key != "rows_total"), counts["rows_total"])

    def test_missing_predictions_retains_annotation_denominator(self):
        self.rows = self.rows[:4]
        _, report = self.prepare()
        self.assertEqual(report["partitions"]["test"]["strict_single_ligand_targets"], 1)
        self.assertEqual(report["partitions"]["test"]["target_status_counts"], {"no_predictions": 1})

    def test_model_filename_blocks_before_read(self):
        with patch("builtins.open", side_effect=AssertionError("Wrong model file opened")):
            for name in ("af3.csv", "boltz2.csv", "boltz1x.csv", "predictions.tar.gz"):
                with self.assertRaises(InputError):
                    prepare_synthetic("a", name, "m", "p", synthetic_only=True)

    def test_method_and_version_provenance_mismatch(self):
        for field in ("model_version", "dataset_version", "source_table", "score_source", "score_direction", "publisher_notebook_commit"):
            paths = self.inputs()
            provenance = json.loads(paths[3].read_text())
            provenance[field] = "wrong"
            paths[3].write_text(json.dumps(provenance))
            with self.assertRaises(InputError):
                preflight(*paths, synthetic_only=True)
        self.rows[0]["method"] = "af3"
        with self.assertRaises(InputError):
            self.prepare()

    def test_hash_mismatch_and_duplicate_provenance_key_block(self):
        paths = self.inputs()
        paths[1].write_text(paths[1].read_text() + "\n")
        with self.assertRaises(InputError) as raised:
            preflight(*paths, synthetic_only=True)
        self.assertEqual(raised.exception.code, "input_hash_mismatch")
        paths = self.inputs()
        paths[3].write_text('{"input_kind":"synthetic","input_kind":"synthetic"}')
        with self.assertRaises(InputError):
            preflight(*paths, synthetic_only=True)

    def test_real_paths_are_not_read_and_baseline_gate_unchanged(self):
        with patch("builtins.open", side_effect=AssertionError("Real input opened")):
            with self.assertRaises(InputError):
                preflight("a", "boltz.csv", "m", "p")
            with self.assertRaises(ValueError):
                EvaluationReference({}, {})
            with self.assertRaises(ValueError):
                associate_after_selection((), None)
        from scripts.phase04_baselines import evaluate
        with self.assertRaises(InputError) as raised:
            evaluate("a", "boltz.csv", "m", method="boltz.csv", score_direction="higher", success_threshold=2)
        self.assertEqual(raised.exception.code, "real_data_blocked")

    def test_non_synthetic_row_marker_blocks(self):
        self.rows[0]["data_origin"] = "real"
        with self.assertRaises(InputError):
            self.prepare()
        self.rows[0]["data_origin"] = "synthetic"
        self.annotations[0]["data_origin"] = "real"
        with self.assertRaises(InputError):
            self.prepare()

    def test_manifest_missing_extra_invalid_and_duplicate_keys(self):
        base = dict(self.manifest)
        for mapping in ({}, {**base, "extra": "train"}, {**base, "private-group-0": "validation"}):
            self.manifest = mapping
            with self.assertRaises(InputError):
                self.prepare()
        self.manifest = base
        with self.assertRaises(InputError):
            strict_cohort(self.annotations, {**base, "private-group-0": []})
        paths = self.inputs()
        paths[2].write_text('{"private-group-0":"train","private-group-0":"test"}')
        provenance = json.loads(paths[3].read_text())
        provenance["input_sha256"]["manifest"] = sha256(paths[2])
        paths[3].write_text(json.dumps(provenance))
        with self.assertRaises(InputError) as raised:
            preflight(*paths, synthetic_only=True)
        self.assertEqual(raised.exception.code, "duplicate_manifest_key")

    def test_shared_cluster_system_pdb_component_cannot_cross_splits(self):
        for field in ("cluster", "system_id", "entry_pdb_id", "component_id"):
            old = [dict(row) for row in self.annotations]
            for i, row in enumerate(self.annotations):
                row[field] = "shared" if i < 2 else "separate"
            with self.assertRaises(InputError) as raised:
                self.prepare()
            self.assertEqual(raised.exception.code, "split_leakage")
            self.annotations = old

    def test_class_and_connected_group_metadata_retained_separate(self):
        self.manifest = {key: "test" for key in self.manifest}
        for row in self.annotations:
            row.update(component_id="same-component", **{"class": "small-molecule"})
        cases, _ = strict_cohort(self.annotations, self.manifest)
        self.assertEqual(dict(cases[0].metadata)["class"], "small-molecule")
        self.assertEqual(len({case.resampling_group for case in cases}), 1)
        index, report = self.prepare()
        self.assertEqual(report["partitions"]["test"]["connected_groups"], 1)
        self.assertFalse(hasattr(index, "metadata"))

    def test_train_changes_cannot_change_test_ordering_or_protocol(self):
        before, old_report = self.prepare()
        self.rows[0].update(ranking_score="-100", rmsd="0", ligand_instance_chain="wrong")
        after, new_report = self.prepare()
        test = lambda index: [d for d in rank_prediction_index(index) if d.selected.target == "private-target-2"]
        self.assertEqual(test(before), test(after))
        self.assertEqual(old_report["partitions"]["test"], new_report["partitions"]["test"])
        self.assertEqual(old_report["selection_protocol"], new_report["selection_protocol"])
        self.assertEqual(list(inspect.signature(rank_prediction_index).parameters), ["prediction_index"])

    def test_reference_association_is_after_selection_without_fallback(self):
        index, _ = self.prepare()
        decisions = rank_prediction_index(index)
        refs = EvaluationReference({"private-target-0": ["lone-reference"]}, {
            ("private-target-0", "1", "0"): {"rmsd": "0"},
        }, synthetic_only=True)
        associated = associate_after_selection(decisions, refs, synthetic_only=True)
        self.assertEqual(associated[0]["status"], "reference_unavailable")
        self.assertEqual(associated[0]["run_identity"], ("private-target-0", "0", "0"))
        self.assertEqual(decisions, rank_prediction_index(index))
        with self.assertRaises(TypeError):
            rank_prediction_index(refs)

    def test_association_does_not_use_mapped_chain_or_compute_success(self):
        index, _ = self.prepare()
        decisions = rank_prediction_index(index)
        refs = EvaluationReference({"private-target-0": ["only-annotation-ligand"]}, {
            decisions[0].selected.identity: {"rmsd": "9", "model_ligand_chain_rmsd": "wrong-chain"},
        }, synthetic_only=True)
        result = associate_after_selection(decisions, refs, synthetic_only=True)[0]
        self.assertEqual(result["reference_ligand"], "only-annotation-ligand")
        self.assertNotIn("success", result)
        self.assertEqual(result["evaluation_reference"]["rmsd"], "9")
        multi = EvaluationReference({"private-target-0": ["a", "b"]}, {}, synthetic_only=True)
        self.assertEqual(associate_after_selection(decisions, multi, synthetic_only=True)[0]["status"], "blocked_not_single_reference")

    def test_exact_types_and_immutable_index_prevent_reference_attachment(self):
        run = PredictionRun("toy", "0", "0", 0.5)
        with self.assertRaises(FrozenInstanceError):
            run.ranking_score = 0.1
        self.assertFalse(hasattr(run, "__dict__"))
        self.assertFalse(hasattr(PredictionIndex((run,)), "__dict__"))
        with self.assertRaises(TypeError):
            PredictionIndex(({**self.rows[0]},))
        with self.assertRaises(ValueError):
            PredictionIndex((run, run))
        class SubRun(PredictionRun):
            pass
        with self.assertRaises(TypeError):
            PredictionIndex((SubRun("toy", "0", "0", 0.5),))

    def test_separate_disabled_future_strict_metric_policy(self):
        self.assertEqual(FUTURE_REAL_PROTOCOL["comparison"], "<")
        self.assertEqual(FUTURE_REAL_PROTOCOL["threshold_angstrom"], 2.0)
        self.assertFalse(FUTURE_REAL_PROTOCOL["enabled"])
        with self.assertRaises(TypeError):
            FUTURE_REAL_PROTOCOL["enabled"] = True

    def test_aggregate_report_has_no_identified_rows_or_reference_values(self):
        _, report = self.prepare()
        text = json.dumps(report, sort_keys=True, allow_nan=False)
        for forbidden in ("private-target", "private-group", "private-cluster", "ref-chain", "mapped-A", '"rmsd"', '"lddt_pli"'):
            self.assertNotIn(forbidden, text)
        for field in ("cases", "prediction_index", "evaluation_reference", "accuracy", "success_rate", "ordering"):
            self.assertNotIn(field, report)
        self.assertEqual(report["source_contract"], SOURCE)

    def test_full_report_reproducible_and_inputs_immutable(self):
        paths = self.inputs()
        before = [path.read_bytes() for path in paths]
        first = preflight(*paths, synthetic_only=True)
        self.assertEqual(first, preflight(*paths, synthetic_only=True))
        self.assertEqual(before, [path.read_bytes() for path in paths])

    def cli(self, paths, extra=(), direct=False):
        entry = ["scripts/phase04_boltz1_adapter.py"] if direct else ["-m", "scripts.phase04_boltz1_adapter"]
        args = [sys.executable, *entry, "--synthetic-only", "--out", str(self.root / "report.json")]
        for field, path in zip(("annotations", "predictions", "manifest", "source-provenance"), paths):
            args.extend(["--" + field, str(path)])
        return subprocess.run([*args, *extra], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

    def test_cli_reproducible_and_no_threshold_override(self):
        paths = self.inputs()
        result = self.cli(paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = (self.root / "report.json").read_bytes()
        result = self.cli(paths, direct=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(first, (self.root / "report.json").read_bytes())
        self.assertEqual(self.cli(paths, ["--risk-threshold", "0.5"]).returncode, 2)

    def test_cli_blocked_errors_do_not_emit_identifiers(self):
        paths = self.inputs()
        paths[3].write_text('{"private-secret-key":1,"private-secret-key":2}')
        result = self.cli(paths)
        self.assertEqual(result.returncode, 1)
        text = (self.root / "report.json").read_text()
        self.assertIn("duplicate_manifest_key", text)
        self.assertNotIn("private-secret-key", text)
        self.assertNotIn("private-secret-key", result.stdout)

    def test_cli_input_overwrite_protection(self):
        paths = self.inputs()
        original = paths[0].read_bytes()
        self.assertEqual(self.cli(paths, ["--out", str(paths[0])]).returncode, 2)
        self.assertEqual(original, paths[0].read_bytes())

    def test_selector_in_fresh_process_has_no_adapter_reference_or_io(self):
        code = '''
import sys
from unittest.mock import patch
from scripts.phase04_prediction_index import PredictionRun, PredictionIndex, rank_prediction_index
assert "scripts.phase04_evaluation_reference" not in sys.modules
assert "scripts.phase04_boltz1_adapter" not in sys.modules
index = PredictionIndex((PredictionRun("toy", "0", "0", 0.9), PredictionRun("toy", "1", "0", 0.1)))
with patch("builtins.open", side_effect=AssertionError("Reference I/O attempted")):
    assert rank_prediction_index(index)[0].selected.identity == ("toy", "0", "0")
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_table_reports_absent_predictions(self):
        paths = self.inputs()
        paths[1].write_text("target,method,data_origin\n")
        provenance = json.loads(paths[3].read_text())
        provenance["input_sha256"]["predictions"] = sha256(paths[1])
        paths[3].write_text(json.dumps(provenance))
        index, report = prepare_synthetic(*paths, synthetic_only=True)
        self.assertEqual(index.runs, ())
        self.assertEqual(report["partitions"]["test"]["target_status_counts"], {"no_predictions": 1})

    def test_invalid_annotation_metadata_blocks(self):
        for field, value in (("num_ligand_chains", "1.5"), ("ligand_is_proper", "maybe"),
                             ("cluster", ""), ("system_id", " padded ")):
            old = self.annotations[0][field]
            self.annotations[0][field] = value
            with self.assertRaises(InputError):
                self.prepare()
            self.annotations[0][field] = old


if __name__ == "__main__":
    unittest.main()
