"""Synthetic-only comparison of inference artifact inventory and published runs.

No directory scanner, artifact reader, ranking, reference join, or evaluator.
Inventory declarations and hashes are not evidence of real-world authenticity.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from .phase04_boltz1_adapter import ANNOTATION_FIELDS, GROUP_FIELDS, strict_cohort
    from .phase04_eligibility import InputError, SPLITS, sha256, unique_object
else:
    from phase04_boltz1_adapter import ANNOTATION_FIELDS, GROUP_FIELDS, strict_cohort
    from phase04_eligibility import InputError, SPLITS, sha256, unique_object

ID_FIELDS = ("target", "seed", "sample")
KINDS = ("confidence_json", "model_cif")
INVENTORY_FIELDS = set(ID_FIELDS) | {"artifact_kind", "artifact_path", "data_origin"}
SUMMARY_FIELDS = set(ID_FIELDS) | {"method", "data_origin"}
SOURCE = {
    "dataset_doi": "10.5281/zenodo.16754298",
    "dataset_version": "v4",
    "model_version": "Boltz-1",
    "source_table": "boltz.csv",
    "inventory_generation_method": "synthetic_inference_artifact_listing",
    "synthetic": True,
    "rights_status": "synthetic_only",
}
REAL_BLOCKERS = (
    "independent_original_inference_inventory_not_authenticated",
    "archived_model_build_weights_and_training_cutoff_not_verified",
    "source_output_usage_rights_not_cleared",
    "analysis_derived_summary_cannot_establish_original_inventory",
    "molecular_mapping_and_missing_reference_policy_not_reviewed",
    "scientific_cohort_split_and_group_independence_not_frozen",
    "real_metric_protocol_and_execution_not_authorized",
)
BUCKETS = (*SPLITS, "outside_cohort", "unknown")


def read_json(path):
    with open(path, encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=unique_object)


def read_projection(path, required, allowed):
    """Parse CSV syntax but retain only allowlisted non-reference columns."""
    result = []
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if (not header or len(header) != len(set(header)) or required - set(header)
                or any(not name or name != name.strip() for name in header)):
            raise InputError("invalid_schema", "Missing, empty, padded or duplicated CSV header")
        positions = {key: header.index(key) for key in sorted(allowed & set(header))}
        origin = header.index("data_origin")
        for row in reader:
            if len(row) != len(header):
                raise InputError("malformed_csv", "CSV record width differs from header")
            if row[origin] != "synthetic":
                raise InputError("real_data_blocked", "Only synthetic rows are accepted")
            result.append({key: row[pos] for key, pos in positions.items()})
    return result


def valid_id(value):
    # Raw, case-sensitive string tokens; never strip, cast, renumber or sort numerically.
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) is not None


def artifact_path(identity, kind):
    """Synthetic manifest convention relative to a Boltz output root, not a scanner.

    The notebook supplies the confidence basename/layout; the analysis script
    supplies the model basename. This does not authenticate archived filenames.
    """
    target, seed, sample = identity
    name = (f"confidence_input_model_{sample}.json" if kind == "confidence_json"
            else f"input_model_{sample}.cif")
    return f"{target}/{seed}/boltz_results_input/predictions/input/{name}"


def stage_rows(rows, *, inventory):
    """Project a closed key set even for in-memory adversarial mapping objects."""
    staged, invalid, reasons = defaultdict(list), [], Counter()
    for row in rows:
        if row.get("data_origin") != "synthetic":
            raise InputError("real_data_blocked", "Only synthetic rows are accepted")
        if not inventory and row.get("method") != "boltz":
            raise InputError("source_mismatch", "Only the Boltz-1 summary contract is accepted")
        identity = tuple(row.get(key) for key in ID_FIELDS)
        if not all(valid_id(value) for value in identity):
            # Keep only a valid target for aggregate bucket assignment; never repair IDs.
            invalid.append(identity[0] if valid_id(identity[0]) else None)
            reasons["invalid_inference_id" if inventory else "invalid_summary_id"] += 1
            continue
        staged[identity].append((row.get("artifact_kind"), row.get("artifact_path")) if inventory else None)
    return staged, invalid, reasons


def annotation_context(rows, manifest):
    """Validate all split links before filtering; retain every annotation denominator."""
    if not rows:
        raise InputError("empty_annotations", "Annotation universe cannot be empty")
    cases, exclusions = strict_cohort(rows, manifest)
    # strict_cohort validates *all* shared identities before its proper/singleton filter.
    parents = {group: group for group in manifest}

    def find(group):
        while parents[group] != group:
            parents[group] = parents[parents[group]]
            group = parents[group]
        return group

    for field in GROUP_FIELDS:
        members = defaultdict(set)
        for row in rows:
            if field in row:
                members[row[field]].add(row["group_key"])
        for groups in members.values():
            first = min(groups)
            for other in sorted(groups):
                a, b = find(first), find(other)
                parents[max(a, b)] = min(a, b)
    strict = {case.target for case in cases}
    by_target = defaultdict(list)
    for row in rows:
        by_target[row["system_id"]].append(row)

    def bucket(target):
        if target not in by_target:
            return "unknown"
        if target not in strict:
            return "outside_cohort"
        return manifest[by_target[target][0]["group_key"]]

    return by_target, {group: find(group) for group in parents}, bucket, exclusions


def reconcile_rows(inventory_rows, summary_rows, annotation_rows, manifest, *, synthetic_only=False):
    """Return aggregate diagnostics only; no selection and no reference-field access.

    Two different artifact kinds for one ID are expected. Repeated kinds or
    repeated summary IDs quarantine that ID on BOTH sides before set comparison.
    Invalid IDs cannot be matched; their rows remain explicit in denominators.
    """
    if synthetic_only is not True:
        raise InputError("real_data_blocked", "Real reconciliation is disabled")
    if any(row.get("data_origin") != "synthetic" for row in annotation_rows):
        raise InputError("real_data_blocked", "Only synthetic annotations are accepted")
    annotations, connected, bucket, exclusions = annotation_context(annotation_rows, manifest)
    inference, invalid_i, reasons_i = stage_rows(inventory_rows, inventory=True)
    summary, invalid_s, reasons_s = stage_rows(summary_rows, inventory=False)
    duplicate_i, duplicate_s, bad = set(), set(), set()
    reasons = reasons_i + reasons_s
    for identity, artifacts in inference.items():
        kinds = Counter(kind for kind, _ in artifacts if type(kind) is str)
        if any(count > 1 for count in kinds.values()):
            duplicate_i.add(identity)
            bad.add(identity)
            reasons["duplicate_inference_id"] += 1
        for kind, path in artifacts:
            if type(kind) is not str or kind not in KINDS:
                bad.add(identity)
                reasons["invalid_artifact_kind"] += 1
            elif type(path) is not str or path != artifact_path(identity, kind):
                bad.add(identity)
                reasons["artifact_path_identity_conflict"] += 1
    for identity, rows in summary.items():
        if len(rows) > 1:
            duplicate_s.add(identity)
            bad.add(identity)
            reasons["duplicate_summary_id"] += 1
    i_all, s_all = set(inference), set(summary)
    i_good, s_good = i_all - bad, s_all - bad

    def counts(targets=None, which_bucket=None):
        def selected(identity):
            return which_bucket is None or bucket(identity[0]) == which_bucket

        i, s = {key for key in i_good if selected(key)}, {key for key in s_good if selected(key)}
        raw_i, raw_s = {key for key in i_all if selected(key)}, {key for key in s_all if selected(key)}
        quarantined = {key for key in bad if selected(key)}
        invalid_inference = sum(which_bucket is None or bucket(t) == which_bucket for t in invalid_i)
        invalid_summary = sum(which_bucket is None or bucket(t) == which_bucket for t in invalid_s)
        confidence = {key for key in i if any(kind == "confidence_json" for kind, _ in inference[key])}
        structure = {key for key in i if any(kind == "model_cif" for kind, _ in inference[key])}
        result = {
            "inference_rows": sum(len(inference[key]) for key in raw_i) + invalid_inference,
            "summary_rows": sum(len(summary[key]) for key in raw_s) + invalid_summary,
            "observed_inference_ids_before_quarantine": len(raw_i),
            "observed_summary_ids_before_quarantine": len(raw_s),
            "usable_inference_ids": len(i), "usable_summary_ids": len(s),
            "both_artifacts": len(confidence & structure),
            "confidence_only": len(confidence - structure),
            "structure_only": len(structure - confidence),
            "missing_confidence_artifact_in_inventory": len(structure - confidence),
            "missing_structure_artifact_in_inventory": len(confidence - structure),
            "inference_only": len(i - s), "summary_only": len(s - i), "intersecting": len(i & s),
            "duplicate_inference_ids": len(raw_i & duplicate_i),
            "duplicate_summary_ids": len(raw_s & duplicate_s),
            "quarantined_ids": len(quarantined),
            "quarantined_inference_ids": len(raw_i & bad),
            "quarantined_summary_ids": len(raw_s & bad),
            "invalid_inference_id_rows": invalid_inference,
            "invalid_summary_id_rows": invalid_summary,
            "quarantined_inference_rows": sum(len(inference[key]) for key in raw_i & bad) + invalid_inference,
            "quarantined_summary_rows": sum(len(summary[key]) for key in raw_s & bad) + invalid_summary,
        }
        if targets is not None:
            rows = [row for target in targets for row in annotations[target]]
            groups = {row["group_key"] for row in rows}
            result.update({
                "annotated_targets": len(targets), "annotation_rows": len(rows),
                "annotation_groups": len(groups), "connected_groups": len({connected[g] for g in groups}),
                "targets_without_usable_inference": len(targets - {key[0] for key in i}),
                "targets_without_usable_summary": len(targets - {key[0] for key in s}),
                "targets_without_any_valid_inference_id": len(targets - {key[0] for key in raw_i}),
            })
        return result

    total = counts(set(annotations))
    quarantined = bool(bad or invalid_i or invalid_s)
    return {
        "schema_version": 1,
        "status": "SYNTHETIC_RECONCILIATION_QUARANTINED" if quarantined else "SYNTHETIC_RECONCILIATION_PASS",
        "real_status": "REAL_RECONCILIATION_BLOCKED", "real_reconciliation_enabled": False,
        "input_kind": "synthetic", "inventory_authenticity_verified": False,
        "counts": total,
        "partitions": {name: counts({t for t in annotations if bucket(t) == name}, name) for name in BUCKETS},
        "cohort_exclusions_by_annotation_partition": exclusions,
        "blocked_reason_counts": dict(sorted(reasons.items())),
        "real_execution_blockers": list(REAL_BLOCKERS),
        "limitations": [
            "Observed means declared in supplied synthetic inventory, not verified physical existence or completeness.",
            "Artifact absence means not listed; it does not distinguish absent, deleted, withheld or unreported files.",
            "Omission from the evaluated summary is not a failed pose or evidence of scientific improvement.",
            "Shared supplied groups are not proven independent protein families; no accuracy is computed.",
            "Strict-cohort partitions are reporting views only; all outside/unknown IDs remain in global comparison.",
            "No planned-run denominator, reference join, ranking or missing-label success/failure policy is applied.",
        ],
    }


def reconcile(inference_inventory, published_summary, annotations, manifest, inventory_provenance,
              *, synthetic_only=False):
    if synthetic_only is not True:
        raise InputError("real_data_blocked", "Real reconciliation is disabled")
    if Path(published_summary).name not in {"published_summary.csv", "boltz.csv"}:
        raise InputError("source_mismatch", "Expected the synthetic published_summary.csv or boltz.csv")
    provenance = read_json(inventory_provenance)
    if (type(provenance) is not dict or set(provenance) != set(SOURCE) | {"input_sha256"}
            or any(type(provenance[key]) is not type(value) or provenance[key] != value
                   for key, value in SOURCE.items())):
        raise InputError("ambiguous_or_disallowed_provenance", "Exact synthetic Boltz-1 v4 provenance required")
    sources = dict(inference_inventory=inference_inventory, published_summary=published_summary,
                   annotations=annotations, manifest=manifest)
    hashes = {key: sha256(path) for key, path in sources.items()}
    if provenance["input_sha256"] != hashes:
        raise InputError("input_hash_mismatch", "Input hashes differ from provenance")
    inventory = read_projection(inference_inventory, INVENTORY_FIELDS, INVENTORY_FIELDS)
    summary = read_projection(published_summary, SUMMARY_FIELDS, SUMMARY_FIELDS)
    annotation_fields = ANNOTATION_FIELDS | {"data_origin"}
    annotation_rows = read_projection(annotations, annotation_fields,
                                      annotation_fields | {"entry_pdb_id", "component_id"})
    report = reconcile_rows(inventory, summary, annotation_rows, read_json(manifest), synthetic_only=True)
    report["input_sha256"] = {**hashes, "inventory_provenance": sha256(inventory_provenance)}
    report["code_sha256"] = {name: sha256(Path(__file__).with_name(name)) for name in (
        "phase05_inference_run_reconciliation.py", "phase04_boltz1_adapter.py",
        "phase04_prediction_index.py", "phase04_eligibility.py")}
    report["source_contract"] = dict(SOURCE)
    return report


class AggregateParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes untrusted argument values/paths.
        print(json.dumps({"status": "REAL_RECONCILIATION_BLOCKED", "reason": "invalid_arguments"}))
        raise SystemExit(2)


def main(argv=None):
    parser = AggregateParser(description=__doc__)
    names = ("inference-inventory", "published-summary", "annotations", "manifest", "inventory-provenance")
    for name in (*names, "out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    sources = [getattr(args, name.replace("-", "_")) for name in names]
    output = Path(args.out)
    try:
        if any(output.resolve() == Path(path).resolve() or (
                output.exists() and Path(path).exists() and output.samefile(path)) for path in sources):
            raise InputError("output_aliases_input", "Output cannot overwrite an input")
    except (OSError, ValueError):
        print(json.dumps({"status": "REAL_RECONCILIATION_BLOCKED", "reason": "invalid_output"}))
        return 1
    try:
        report = reconcile(*sources, synthetic_only=args.synthetic_only)
    except (OSError, ValueError, csv.Error) as error:
        report = {"status": "REAL_RECONCILIATION_BLOCKED", "real_status": "REAL_RECONCILIATION_BLOCKED",
                  "real_reconciliation_enabled": False,
                  "blocked_reason_counts": {getattr(error, "code", "invalid_input"): getattr(error, "count", 1)},
                  "real_execution_blockers": list(REAL_BLOCKERS)}
    try:
        output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError):
        print(json.dumps({"status": "REAL_RECONCILIATION_BLOCKED", "reason": "output_write_failed"}))
        return 1
    print(json.dumps({"status": report["status"], "real_status": "REAL_RECONCILIATION_BLOCKED"}))
    return int(report["status"] != "SYNTHETIC_RECONCILIATION_PASS")


if __name__ == "__main__":
    raise SystemExit(main())
