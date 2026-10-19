"""Synthetic adversarial tests; no molecular files, network or real evaluations."""

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import phase05_inference_run_reconciliation as gate
from scripts.phase04_eligibility import InputError, sha256

REFERENCES = ("rmsd", "lddt_pli", "model_ligand_chain_rmsd", "model_ligand_chain_lddt_pli",
              "ligand_instance_chain", "target_ligand_chain_rmsd", "target_ligand_chain_lddt_pli",
              "model_ligand_ccd_code", "mapping_id", "arbitrary_reference", "ranking_score")


def fixture_rows():
    annotations = [dict(system_id=f"private-target-{i}", group_key=f"private-group-{i}",
                        cluster=f"private-cluster-{i}", component_id=f"private-component-{i}",
                        entry_pdb_id=f"private-pdb-{i}", ligand_is_proper="true",
                        num_ligand_chains="1", data_origin="synthetic") for i in range(6)]
    annotations[3]["ligand_is_proper"] = "false"
    annotations[5]["cluster"] = annotations[0]["cluster"]
    manifest = {f"private-group-{i}": ("val" if i == 1 else "test" if i == 2 else "train") for i in range(6)}
    inventory = []
    specs = [("private-target-0", "01", gate.KINDS), ("private-target-0", "1", ("confidence_json",)),
             ("private-target-1", "0", ("model_cif",)), ("private-target-2", "0", gate.KINDS),
             ("private-target-3", "0", gate.KINDS), ("private-unknown", "0", ("confidence_json",))]
    for target, seed, kinds in specs:
        for kind in kinds:
            inventory.append(dict(target=target, seed=seed, sample="0", artifact_kind=kind,
                                  artifact_path=gate.artifact_path((target, seed, "0"), kind), data_origin="synthetic"))
    summary = [dict(target=target, seed=seed, sample="0", method="boltz", data_origin="synthetic",
                    **{field: f"private-reference-{i}" for i, field in enumerate(REFERENCES)})
               for target, seed in [("private-target-0", "01"), ("private-target-0", "9"),
                                    ("private-target-1", "0"), ("private-target-2", "0"),
                                    ("private-target-3", "0"), ("private-unknown", "0")]]
    return inventory, summary, annotations, manifest


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set(fields) | {key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)


def write_fixture(root, rows=None):
    """Documented fixture generator. Never creates or opens molecular artifacts."""
    root.mkdir(parents=True, exist_ok=True)
    inventory, summary, annotations, manifest = rows if rows is not None else fixture_rows()
    paths = [root / name for name in ("inference_inventory.csv", "published_summary.csv", "annotations.csv",
                                    "manifest.json", "inventory_provenance.json")]
    write_csv(paths[0], inventory, gate.INVENTORY_FIELDS)
    write_csv(paths[1], summary, gate.SUMMARY_FIELDS)
    write_csv(paths[2], annotations, gate.ANNOTATION_FIELDS | {"data_origin"})
    paths[3].write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    refresh_provenance(paths)
    return paths


def refresh_provenance(paths):
    paths[4].write_text(json.dumps({**gate.SOURCE, "input_sha256": {
        key: sha256(path) for key, path in zip(
            ("inference_inventory", "published_summary", "annotations", "manifest"), paths[:4])
    }}, sort_keys=True), encoding="utf-8")


class Poison:
    def __str__(self):
        raise AssertionError("Reference inspected")

    def __eq__(self, other):
        raise AssertionError("Reference compared")

    def __bool__(self):
        raise AssertionError("Reference tested")


class ProjectionOnly(dict):
    def get(self, key, default=None):
        if key not in gate.SUMMARY_FIELDS:
            raise AssertionError("Nonallowlisted key accessed: " + key)
        return super().get(key, default)

    def __getitem__(self, key):
        raise AssertionError("Only explicit get projection allowed")

    def items(self):
        raise AssertionError("Raw row enumerated")

    def values(self):
        raise AssertionError("Raw values enumerated")


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rows = fixture_rows()

    def report(self):
        return gate.reconcile_rows(*self.rows, synthetic_only=True)

    def files(self):
        return write_fixture(self.root, self.rows)

    def cli(self, paths, out=None, extra=()):
        args = []
        for name, path in zip(("inference-inventory", "published-summary", "annotations", "manifest", "inventory-provenance"), paths):
            args += ["--" + name, str(path)]
        return [*args, "--out", str(out or self.root / "aggregate.json"), "--synthetic-only", *extra]

    def test_inventory_artifact_counts_and_set_comparison(self):
        report = self.report()
        expected = dict(usable_inference_ids=6, both_artifacts=3, confidence_only=2, structure_only=1,
                        inference_only=1, summary_only=1, intersecting=5,
                        missing_confidence_artifact_in_inventory=1, missing_structure_artifact_in_inventory=2,
                        duplicate_inference_ids=0, duplicate_summary_ids=0, quarantined_ids=0)
        for key, count in expected.items():
            self.assertEqual(report["counts"][key], count, key)
        self.assertEqual(report["real_status"], "REAL_RECONCILIATION_BLOCKED")
        self.assertFalse(report["inventory_authenticity_verified"])

    def test_denominators_groups_unknown_and_outside_cohort(self):
        report = self.report()
        train = report["partitions"]["train"]
        self.assertEqual((train["annotated_targets"], train["annotation_groups"], train["connected_groups"]), (3, 3, 2))
        self.assertEqual(train["targets_without_usable_inference"], 2)
        self.assertEqual(report["counts"]["annotated_targets"], 6)
        self.assertEqual(report["partitions"]["outside_cohort"]["usable_inference_ids"], 1)
        self.assertEqual(report["partitions"]["unknown"]["usable_inference_ids"], 1)
        for key, count in report["counts"].items():
            self.assertEqual(sum(p[key] for p in report["partitions"].values()), count, key)

    def test_poisoned_reference_columns_never_accessed(self):
        before = self.report()
        self.rows[1][:] = [ProjectionOnly({**row, **{field: Poison() for field in REFERENCES}}) for row in self.rows[1]]
        with patch("builtins.open", side_effect=AssertionError("Core opened a file")):
            self.assertEqual(self.report(), before)

    def test_scrambled_and_missing_reference_fields_do_not_change_counts_or_exit(self):
        paths = self.files()
        before = gate.reconcile(*paths, synthetic_only=True)
        for variant in ("scramble", "remove"):
            for i, row in enumerate(self.rows[1]):
                for field in REFERENCES:
                    if variant == "remove":
                        row.pop(field, None)
                    else:
                        row[field] = ("nan", "", "0", "99")[i % 4]
            after = gate.reconcile(*self.files(), synthetic_only=True)
            self.assertNotEqual(after.pop("input_sha256"), before["input_sha256"])
            self.assertEqual(after, {k: v for k, v in before.items() if k != "input_sha256"})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(self.cli(paths)), 0)

    def test_annotation_reference_fields_are_unused(self):
        before = self.report()
        for row in self.rows[2]:
            row.update({key: Poison() for key in REFERENCES})
        self.assertEqual(self.report(), before)

    def test_raw_numeric_like_ids_remain_distinct(self):
        self.rows[1][1]["seed"] = "1"
        self.assertEqual(self.report()["counts"]["intersecting"], 6)
        self.rows[1][0]["seed"] = "001"
        self.assertEqual(self.report()["counts"]["intersecting"], 5)

    def test_duplicate_artifact_quarantines_both_sides(self):
        self.rows[0].append(dict(self.rows[0][0]))
        counts = self.report()["counts"]
        self.assertEqual(counts["duplicate_inference_ids"], 1)
        self.assertEqual(counts["quarantined_inference_rows"], 3)
        self.assertEqual(counts["quarantined_summary_rows"], 1)
        self.assertEqual((counts["inference_only"], counts["summary_only"], counts["intersecting"]), (1, 1, 4))

    def test_duplicate_summary_quarantines_both_sides_even_with_missing_labels(self):
        self.rows[1].append({key: value for key, value in self.rows[1][0].items() if key not in REFERENCES})
        counts = self.report()["counts"]
        self.assertEqual(counts["duplicate_summary_ids"], 1)
        self.assertEqual(counts["quarantined_summary_rows"], 2)
        self.assertEqual(counts["quarantined_inference_rows"], 2)
        self.assertEqual(counts["inference_only"], 1)

    def test_invalid_identifiers_are_not_repaired_or_dropped_from_row_counts(self):
        for field in gate.ID_FIELDS:
            for value in (None, "", " 1", "1 ", "../1", "a/b", "a\\b", "a\n1", "a\x00", 1, "..", "a:b"):
                with self.subTest(field=field, value=value):
                    self.rows = fixture_rows()
                    self.rows[0][0][field] = value
                    self.rows[1][0][field] = value
                    counts = self.report()["counts"]
                    self.assertEqual(counts["invalid_inference_id_rows"], 1)
                    self.assertEqual(counts["invalid_summary_id_rows"], 1)
                    self.assertEqual(counts["inference_rows"], 9)
                    self.assertEqual(counts["summary_rows"], 6)

    def test_missing_identifier_key_quarantines(self):
        del self.rows[0][0]["sample"]
        self.assertEqual(self.report()["counts"]["invalid_inference_id_rows"], 1)

    def test_conflicting_paths_and_unapproved_paths_quarantine(self):
        for path in ("../outside.json", "C:/private/confidence.json", "/tmp/confidence.json", "https://example.com/file",
                     "analysis/private_01_0.json", "target/0/boltz_results_input/predictions/input/input_model_1.cif",
                     "private-target-0/01/boltz_results_input/predictions/input/input_model_0.cif",
                     "private-target-0\\01\\confidence_input_model_0.json"):
            with self.subTest(path=path):
                self.rows = fixture_rows()
                self.rows[0][0]["artifact_path"] = path
                report = self.report()
                self.assertEqual(report["counts"]["quarantined_inference_rows"], 2)
                self.assertEqual(report["blocked_reason_counts"]["artifact_path_identity_conflict"], 1)

    def test_unknown_artifact_kind_quarantines(self):
        for kind in ("analysis_json", "rmsd", "", None, []):
            self.rows[0][0]["artifact_kind"] = kind
            self.assertEqual(self.report()["blocked_reason_counts"]["invalid_artifact_kind"], 1)

    def test_no_artifact_io_or_directory_scanner(self):
        paths = self.files()
        allowed = {path.resolve() for path in paths} | {Path(gate.__file__).with_name(name).resolve() for name in (
            "phase05_inference_run_reconciliation.py", "phase04_boltz1_adapter.py", "phase04_prediction_index.py", "phase04_eligibility.py")}
        actual_open = open

        def guarded_open(path, *args, **kwargs):
            self.assertIn(Path(path).resolve(), allowed)
            return actual_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=guarded_open), patch("os.scandir", side_effect=AssertionError("Directory scanned")):
            self.assertEqual(gate.reconcile(*paths, synthetic_only=True)["counts"]["usable_inference_ids"], 6)

    def test_empty_inventories_preserve_annotation_denominators(self):
        self.rows[0].clear()
        self.rows[1].clear()
        report = gate.reconcile(*self.files(), synthetic_only=True)
        self.assertEqual(report["counts"]["usable_inference_ids"], 0)
        self.assertEqual(report["counts"]["targets_without_usable_inference"], 6)
        self.assertEqual(report["real_status"], "REAL_RECONCILIATION_BLOCKED")

    def test_empty_inventory_does_not_reconstruct_runs_from_summary(self):
        self.rows[0].clear()
        report = self.report()
        self.assertEqual(report["counts"]["summary_only"], 6)
        self.assertEqual(report["counts"]["usable_inference_ids"], 0)
        self.assertEqual(report["counts"]["both_artifacts"], 0)

    def test_complete_artifacts_with_missing_summary_still_count_as_observed(self):
        self.rows[1].pop(0)
        self.assertEqual(self.report()["counts"]["both_artifacts"], 3)
        self.assertEqual(self.report()["counts"]["inference_only"], 2)

    def test_no_selection_or_evaluation_called(self):
        with patch("scripts.phase04_boltz1_adapter.rank_prediction_index", side_effect=AssertionError("Ranking called")):
            self.assertEqual(self.report()["counts"]["usable_inference_ids"], 6)

    def test_nominal_25_is_not_observed_coverage(self):
        nominal_only = 5 * 5
        report = self.report()
        self.assertEqual(nominal_only, 25)
        self.assertEqual(report["counts"]["usable_inference_ids"], 6)
        self.assertNotIn("planned_runs", report["counts"])

    def test_summary_omission_is_not_pose_failure(self):
        self.rows[1].clear()
        report = self.report()
        self.assertEqual(report["counts"]["inference_only"], 6)
        self.assertEqual(report["counts"]["usable_inference_ids"], 6)
        self.assertFalse(any("success" in key or "accuracy" in key or "pose_failure" in key for key in report["counts"]))

    def test_proper_flag_changes_reporting_view_not_inventory_comparison(self):
        before = self.report()["counts"]
        self.rows[2][0]["ligand_is_proper"] = "false"
        self.assertEqual(self.report()["counts"], before)

    def test_manifest_exact_coverage_and_values(self):
        original = dict(self.rows[3])
        variants = ({**original, "extra": "train"}, {k: v for k, v in original.items() if k != "private-group-3"},
                    {**original, "private-group-3": "holdout"}, [], None)
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(InputError):
                gate.reconcile_rows(*self.rows[:3], variant, synthetic_only=True)

    def test_cross_partition_links_checked_before_cohort_filter(self):
        for field in gate.GROUP_FIELDS:
            with self.subTest(field=field):
                self.rows = fixture_rows()
                self.rows[2][3][field] = self.rows[2][1][field]
                with self.assertRaisesRegex(InputError, "Shared annotation identity"):
                    self.report()

    def test_group_with_multiple_systems_is_one_denominator_group(self):
        self.rows[2][4]["group_key"] = "private-group-0"
        del self.rows[3]["private-group-4"]
        self.assertEqual(self.report()["partitions"]["train"]["annotation_groups"], 2)

    def test_duplicate_json_manifest_keys_rejected(self):
        paths = self.files()
        paths[3].write_text('{"private-group-0":"train","private-group-0":"test"}', encoding="utf-8")
        refresh_provenance(paths)
        with self.assertRaises(InputError) as error:
            gate.reconcile(*paths, synthetic_only=True)
        self.assertEqual(error.exception.code, "duplicate_manifest_key")

    def test_malformed_headers_and_records_rejected(self):
        for content in ("target,target,seed,sample,method,data_origin\n", "target,seed,method,data_origin\n",
                        "target,seed,sample,method,data_origin,\n", "target,seed,sample,method, data_origin\n",
                        'target,seed,sample,method,data_origin\n"unterminated',
                        "target,seed,sample,method,data_origin\na,b,c,boltz,synthetic,extra\n"):
            paths = self.files()
            paths[1].write_text(content, encoding="utf-8")
            refresh_provenance(paths)
            with self.subTest(content=content), self.assertRaises((InputError, csv.Error)):
                gate.reconcile(*paths, synthetic_only=True)

    def test_provenance_version_model_source_and_independence_fail_closed(self):
        for key, value in (("model_version", "Boltz-2"), ("source_table", "af3.csv"), ("dataset_version", "v6"),
                           ("inventory_generation_method", "analysis_json"), ("inventory_generation_method", "published_summary"),
                           ("inventory_generation_method", "planned_5x5"), ("rights_status", "unknown"),
                           ("synthetic", False), ("synthetic", 1), ("independence_verified", True)):
            paths = self.files()
            provenance = json.loads(paths[4].read_text())
            provenance[key] = value
            paths[4].write_text(json.dumps(provenance), encoding="utf-8")
            with self.subTest(key=key, value=value), self.assertRaises(InputError) as error:
                gate.reconcile(*paths, synthetic_only=True)
            self.assertEqual(error.exception.code, "ambiguous_or_disallowed_provenance")

    def test_missing_or_duplicate_provenance_fields_rejected(self):
        paths = self.files()
        for content in ('{}', '[]', '{"synthetic":true,"synthetic":false}'):
            paths[4].write_text(content, encoding="utf-8")
            with self.assertRaises(InputError):
                gate.reconcile(*paths, synthetic_only=True)

    def test_each_input_hash_is_checked(self):
        for index in range(4):
            paths = self.files()
            with paths[index].open("a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.subTest(index=index), self.assertRaises(InputError) as error:
                gate.reconcile(*paths, synthetic_only=True)
            self.assertEqual(error.exception.code, "input_hash_mismatch")

    def test_nonsynthetic_origins_fail_closed_in_every_input(self):
        for index in range(3):
            for origin in ("real", "", "Synthetic"):
                self.rows = fixture_rows()
                self.rows[index][0]["data_origin"] = origin
                with self.subTest(index=index, origin=origin), self.assertRaises(InputError):
                    self.report()
                with self.assertRaises(InputError):
                    gate.reconcile(*self.files(), synthetic_only=True)

    def test_wrong_or_mixed_summary_method_rejected(self):
        for method in ("af3", "chai", "boltz2", "boltz ", ""):
            self.rows[1][0]["method"] = method
            with self.assertRaises(InputError):
                self.report()

    def test_wrong_summary_file_source_rejected(self):
        paths = self.files()
        paths[1] = paths[1].rename(self.root / "af3.csv")
        refresh_provenance(paths)
        with self.assertRaises(InputError) as error:
            gate.reconcile(*paths, synthetic_only=True)
        self.assertEqual(error.exception.code, "source_mismatch")

    def test_missing_synthetic_only_cli_flag_rejected(self):
        args = self.cli(self.files())
        args.remove("--synthetic-only")
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
            gate.main(args)
        self.assertEqual(error.exception.code, 2)

    def test_api_gate_precedes_file_io(self):
        with patch("builtins.open", side_effect=AssertionError("Opened before gate")):
            with self.assertRaises(InputError):
                gate.reconcile(*(["absent"] * 5))
            with self.assertRaises(InputError):
                gate.reconcile_rows(*self.rows)

    def test_cli_has_no_real_or_scanning_option_and_redacts_arguments(self):
        for extra in (("--real",), ("--scan-directory", "private-path")):
            output = io.StringIO()
            with redirect_stdout(output), self.assertRaises(SystemExit) as error:
                gate.main(self.cli(self.files(), extra=extra))
            self.assertEqual(error.exception.code, 2)
            self.assertNotIn("private", output.getvalue())

    def test_missing_inventory_cli_reports_blocked_without_identifiers(self):
        paths = self.files()
        paths[0].unlink()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(gate.main(self.cli(paths)), 1)
        report = (self.root / "aggregate.json").read_text()
        self.assertIn("REAL_RECONCILIATION_BLOCKED", report)
        self.assertNotIn(str(self.root), report + output.getvalue())

    def test_output_cannot_overwrite_input_or_hardlink(self):
        paths = self.files()
        for target in paths:
            before = target.read_bytes()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(self.cli(paths, target)), 1)
            self.assertEqual(target.read_bytes(), before)
        alias = self.root / "alias.json"
        os.link(paths[0], alias)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(gate.main(self.cli(paths, alias)), 1)

    def test_cli_quarantine_status_and_aggregate_privacy(self):
        self.rows[0].append(dict(self.rows[0][0]))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(gate.main(self.cli(self.files())), 1)
        text = (self.root / "aggregate.json").read_text() + output.getvalue()
        for secret in ("private-target", "private-group", "private-reference", "private-cluster", "private-pdb", "boltz_results_input"):
            self.assertNotIn(secret, text)
        self.assertIn("SYNTHETIC_RECONCILIATION_QUARANTINED", text)

    def test_cli_repeat_and_hashseed_determinism(self):
        paths = self.files()
        script = Path(gate.__file__).resolve()
        payloads = []
        for seed in ("1", "17"):
            output = self.root / f"aggregate-{seed}.json"
            result = subprocess.run([sys.executable, str(script), *self.cli(paths, output)],
                                    capture_output=True, text=True, env={**os.environ, "PYTHONHASHSEED": seed})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")
            payloads.append(output.read_bytes())
        self.assertEqual(*payloads)

    def test_row_order_does_not_affect_diagnostics(self):
        before = self.report()
        for rows in self.rows[:3]:
            rows.reverse()
        self.assertEqual(self.report(), before)


if __name__ == "__main__":
    unittest.main()
