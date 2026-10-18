"""Boltz-1 reference-blind adapter: synthetic preflight, aggregate output only.

Real preflight/evaluation is blocked while source rights and reference-free
candidate completeness remain unproven. No reference values are projected,
no labels are loaded for evaluation, and the toy baseline is never called.
"""

import argparse
import csv
import json
import platform
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from .phase04_eligibility import InputError, SPLITS, sha256, unique_object
    from .phase04_prediction_index import PREDICTION_FIELDS, build_prediction_index, clean_identifier, rank_prediction_index
else:
    from phase04_eligibility import InputError, SPLITS, sha256, unique_object
    from phase04_prediction_index import PREDICTION_FIELDS, build_prediction_index, clean_identifier, rank_prediction_index

SOURCE = {
    "dataset_doi": "10.5281/zenodo.16754298", "dataset_version": "v4",
    "source_table": "boltz.csv", "model_version": "Boltz-1",
    "score_source": "confidence_score", "score_direction": "higher",
    "publisher_notebook_commit": "197fafc60a5cef3a9e7f8a4b0dac7c965eed3839",
    "publisher_notebook_sha256": "36d3531c6f693f3ee11363e7acaa98233d86237ab75618b8185ef95e906a8e1c",
    "boltz_writer_commit": "b1ebfc46ecf57f5414e0d1a6f9027bbb122c53bc",
    "boltz_writer_sha256": "65b7fd13f6fdd0d06c0f241a9b717529cf1bbe5e2d5fb70e1aa068400ac2f815",
}
REAL_BLOCKERS = (
    "archive_output_rights_not_cleared",
    "archive_candidate_completeness_reference_dependent",
    "singleton_molecular_mapping_not_independently_proven",
    "archived_model_release_and_training_cutoff_not_verified",
    "scientific_cohort_split_and_group_independence_not_frozen",
    "real_metric_protocol_and_execution_not_authorized",
)
ANNOTATION_FIELDS = {"system_id", "group_key", "cluster", "ligand_is_proper", "num_ligand_chains"}
GROUP_FIELDS = ("system_id", "cluster", "entry_pdb_id", "component_id")
OPTIONAL_METADATA = {"entry_pdb_id", "component_id", "class"}


def read_json(path):
    with open(path, encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=unique_object)


def read_projection(path, required, allowed, *, allow_empty=False):
    """Read CSV syntax, then retain only allowed columns, never reference values."""
    projected = []
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if len(header) != len(set(header)) or (required | {"data_origin"}) - set(header):
            raise InputError("invalid_schema", "Required columns absent or duplicate CSV columns")
        positions = {name: header.index(name) for name in allowed & set(header)}
        origin = header.index("data_origin")
        for values in reader:
            if len(values) != len(header):
                raise InputError("malformed_csv", "CSV record width does not match header")
            if values[origin] != "synthetic":
                raise InputError("real_data_blocked", "Only generated synthetic fixtures are accepted")
            projected.append({name: values[index] for name, index in positions.items()})
    if not projected and not allow_empty:
        raise InputError("empty_input", "Annotations cannot be empty")
    return projected, set(header)


@dataclass(frozen=True, slots=True)
class CohortCase:
    target: str
    group_key: str
    cluster: str
    split: str
    resampling_group: str
    # Whitelisted class/group provenance, never passed to ranking.
    metadata: tuple


def strict_cohort(rows, manifest):
    """Filter on fixed annotation metadata, without reading any ligand mapping."""
    if not isinstance(manifest, dict) or any(type(s) is not str or s not in SPLITS for s in manifest.values()):
        raise InputError("invalid_manifest", "Expected group_key -> train/val/test")
    if set(manifest) != {row["group_key"] for row in rows}:
        raise InputError("manifest_group_mismatch", "Manifest must cover exactly the annotation groups")
    systems = defaultdict(list)
    for row in rows:
        if not all(clean_identifier(row[field]) for field in ("system_id", "group_key", "cluster")):
            raise InputError("invalid_annotation_identity", "Empty or padded annotation/group identifier")
        if row["ligand_is_proper"].lower() not in ("true", "false"):
            raise InputError("invalid_proper_flag", "Expected true/false proper flag")
        if not row["num_ligand_chains"].isascii() or not row["num_ligand_chains"].isdigit():
            raise InputError("invalid_ligand_count", "Expected a nonnegative integer total ligand count")
        systems[row["system_id"]].append(row)
    parents = {group: group for group in manifest}

    def find(group):
        while group != parents[group]:
            parents[group] = parents[parents[group]]
            group = parents[group]
        return group

    # Enforce boundaries and build connected units before any cohort filtering.
    for field in GROUP_FIELDS:
        members = defaultdict(set)
        for row in rows:
            if field in row:
                if not clean_identifier(row[field]):
                    raise InputError("invalid_group_metadata", "Empty or padded group metadata")
                members[row[field]].add(row["group_key"])
        for groups in members.values():
            if len({manifest[g] for g in groups}) != 1:
                raise InputError("split_leakage", "Shared annotation identity crosses partitions", len(groups))
            first = min(groups)
            for other in sorted(groups):
                a, b = find(first), find(other)
                parents[max(a, b)] = min(a, b)
    cases = []
    excluded = {split: Counter() for split in SPLITS}
    for target, annotations in sorted(systems.items()):
        row = annotations[0]
        split = manifest[row["group_key"]]
        reason = ("multiple_annotation_rows" if len(annotations) != 1 else
                  "not_one_total_ligand" if int(row["num_ligand_chains"]) != 1 else
                  "nonproper_ligand" if row["ligand_is_proper"].lower() != "true" else None)
        if reason:
            excluded[split][reason] += 1
        else:
            cases.append(CohortCase(target, row["group_key"], row["cluster"], split,
                                    find(row["group_key"]),
                                    tuple((field, row[field]) for field in sorted(OPTIONAL_METADATA) if field in row)))
    return tuple(cases), {split: dict(sorted(counts.items())) for split, counts in excluded.items()}


def prepare_synthetic(annotations, predictions, manifest, source_provenance, *, synthetic_only=False):
    """Return an isolated index and aggregate report; never an evaluation mapping."""
    if synthetic_only is not True:
        raise InputError("real_preflight_blocked", "Rights and reference-free provenance gates remain unresolved")
    if Path(predictions).name != "boltz.csv":
        raise InputError("source_mismatch", "Only the explicit Boltz-1 source basename boltz.csv is supported")
    provenance = read_json(source_provenance)
    if not isinstance(provenance, dict) or provenance.get("input_kind") != "synthetic":
        raise InputError("source_mismatch", "Synthetic source provenance is required")
    if any(provenance.get(key) != value for key, value in SOURCE.items()):
        raise InputError("source_mismatch", "Pinned source/version/score provenance does not match Boltz-1 contract")
    hashes = {name: sha256(path) for name, path in (
        ("annotations", annotations), ("predictions", predictions), ("manifest", manifest)
    )}
    if provenance.get("input_sha256") != hashes:
        raise InputError("input_hash_mismatch", "Input bytes do not match supplied SHA256 provenance")
    annotation_rows, annotation_schema = read_projection(
        annotations, ANNOTATION_FIELDS, ANNOTATION_FIELDS | OPTIONAL_METADATA)
    assignments = read_json(manifest)
    cases, cohort_exclusions = strict_cohort(annotation_rows, assignments)
    prediction_rows, prediction_schema = read_projection(
        predictions, {"target", "method"}, set(PREDICTION_FIELDS) | {"method"}, allow_empty=True)
    if any(row["method"] != "boltz" for row in prediction_rows):
        raise InputError("method_mismatch", "Only exact method=boltz is allowed")
    # Strip method metadata too. No raw row/annotation/reference is attached.
    projected = [{field: row.get(field) for field in PREDICTION_FIELDS} for row in prediction_rows]
    prediction_index, diagnostics = build_prediction_index(projected, (case.target for case in cases))
    decisions = rank_prediction_index(prediction_index)
    selected_targets = {decision.selected.target for decision in decisions}
    by_split = {}
    for split in SPLITS:
        subset = [case for case in cases if case.split == split]
        stats = [diagnostics["target_stats"][case.target] for case in subset]
        indexed = [case for case in subset if case.target in selected_targets]
        by_split[split] = {
            "annotation_rows": sum(assignments[row["group_key"]] == split for row in annotation_rows),
            "strict_single_ligand_targets": len(subset),
            "annotation_groups": len({case.group_key for case in subset}),
            "connected_groups": len({case.resampling_group for case in subset}),
            "targets_with_source_rows": sum(item["source_rows"] > 0 for item in stats),
            "indexed_targets": len(indexed), "indexed_runs": sum(item["indexed_rows"] for item in stats),
            "indexed_connected_groups": len({case.resampling_group for case in indexed}),
            "source_rows_in_strict_cohort": sum(item["source_rows"] for item in stats),
            "quarantined_rows": sum(item["source_rows"] for item in stats
                                    if item["status"] in ("missing_or_invalid_run_id", "duplicate_run_id")),
            "missing_score_rows": sum(item["source_rows"] - item["indexed_rows"] for item in stats
                                      if item["status"] in ("indexed", "no_finite_score")),
            "target_status_counts": dict(sorted(Counter(item["status"] for item in stats).items())),
            "cohort_exclusion_systems": cohort_exclusions[split],
        }
    report = {
        "status": "SYNTHETIC_PREFLIGHT_PASS_REAL_EVALUATION_BLOCKED", "schema_version": 1,
        "input_kind": "synthetic", "real_evaluation_enabled": False,
        "source_contract": dict(SOURCE),
        "source_contract_note": "Intended archive lineage, not authentication of a real archive or archived model release",
        "input_sha256": {**hashes, "source_provenance": sha256(source_provenance)},
        "code_sha256": {name: sha256(Path(__file__).with_name(name)) for name in (
            "phase04_boltz1_adapter.py", "phase04_prediction_index.py", "phase04_eligibility.py")},
        "python": platform.python_version(),
        "schema_presence": {
            "prediction_fields": {field: field in prediction_schema for field in PREDICTION_FIELDS},
            "optional_group_metadata": {field: field in annotation_schema for field in sorted(OPTIONAL_METADATA)},
        },
        "selection_protocol": {"fields": list(PREDICTION_FIELDS), "score_direction": "higher",
                               "tie_break": "lexicographic seed then sample", "threshold_fitting": False},
        "row_counts": diagnostics["row_counts"], "partitions": by_split,
        "real_execution_blockers": list(REAL_BLOCKERS),
        "limitations": [
            "Publisher enumeration and empty-assignment filtering make archived candidate membership reference-dependent.",
            "Singleton post-decision association is not proof of original molecular mapping or complete run inventory.",
            "Connected supplied groups and historical paired case counts are not independent protein-family counts.",
            "No reference values, accuracy, fitted policy, or scientific improvement are computed by this preflight.",
        ],
    }
    return prediction_index, report


def preflight(*args, **kwargs):
    return prepare_synthetic(*args, **kwargs)[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("annotations", "predictions", "manifest", "source-provenance", "out"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    output = Path(args.out)
    sources = (args.annotations, args.predictions, args.manifest, args.source_provenance)
    if any(output.resolve() == Path(path).resolve() or (
        output.exists() and Path(path).exists() and output.samefile(path)
    ) for path in sources):
        parser.error("Output must not overwrite an input")
    try:
        report = preflight(*sources, synthetic_only=args.synthetic_only)
    except (OSError, ValueError, csv.Error) as error:
        # Do not print exception messages that could contain raw IDs or values.
        report = {"status": "BLOCKED", "real_evaluation_enabled": False,
                  "exclusion_counts": {getattr(error, "code", "invalid_input"): getattr(error, "count", 1)},
                  "real_execution_blockers": list(REAL_BLOCKERS)}
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "real_evaluation_enabled": False}))
    return int(report["status"] == "BLOCKED")


if __name__ == "__main__":
    raise SystemExit(main())
