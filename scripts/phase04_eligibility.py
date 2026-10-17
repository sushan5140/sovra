"""Synthetic Phase 04 input validation, provenance and explicit quarantine.

No download, training, split generation, or reference-dependent selection.
Source filename (not the generic method column) identifies the model version.
"""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

SPLITS = ("train", "val", "test")
ANNOTATION_FIELDS = {
    "system_id", "ligand_instance_chain", "group_key", "cluster",
    "ligand_is_proper", "data_origin",
}
PREDICTION_FIELDS = {"target", "ligand_instance_chain", "method", "data_origin"}
SUBGROUP_FIELDS = ("ligand_property_bin", "similarity_bin", "ligand_exposure")


class InputError(ValueError):
    """Fail closed with a machine-readable reason and affected count."""

    def __init__(self, code, message, count=1):
        super().__init__(message)
        self.code = code
        self.count = count


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number(value):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def read_csv(path, required):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or required - set(fields):
            raise InputError("invalid_schema", f"{Path(path).name}: missing/duplicate columns")
        rows = list(reader)
    if not rows:
        raise InputError("empty_input", f"{Path(path).name}: no rows")
    malformed = sum(None in row or any(v is None for v in row.values()) for row in rows)
    if malformed:
        raise InputError("malformed_csv", "CSV row widths differ from header", malformed)
    nonsynthetic = sum(row["data_origin"] != "synthetic" for row in rows)
    if nonsynthetic:
        raise InputError("real_data_blocked", "Every row must declare data_origin=synthetic", nonsynthetic)
    return rows, set(fields)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate_manifest_key", f"Repeated manifest key: {key}")
        result[key] = value
    return result


def read_annotations(annotations_path, manifest_path):
    rows, fields = read_csv(annotations_path, ANNOTATION_FIELDS)
    with open(manifest_path, encoding="utf-8-sig") as stream:
        splits = json.load(stream, object_pairs_hook=unique_object)
    if not isinstance(splits, dict) or any(
        not isinstance(value, str) or value not in SPLITS for value in splits.values()
    ):
        raise InputError("invalid_manifest", "Manifest must map group_key to train/val/test")
    annotated = {}
    identities = Counter((row["system_id"], row["ligand_instance_chain"]) for row in rows)
    repeated = sum(n for n in identities.values() if n > 1)
    if repeated:
        raise InputError("ambiguous_annotation_identity", "Repeated annotation case identities", repeated)
    for row in rows:
        for field in ("system_id", "ligand_instance_chain", "group_key", "cluster"):
            if not row[field].strip() or row[field] != row[field].strip():
                raise InputError("invalid_annotation_identity", f"Empty/padded {field}")
        flag = row["ligand_is_proper"].lower()
        if flag not in ("true", "false"):
            raise InputError("invalid_proper_flag", "ligand_is_proper must be true/false")
        annotated[(row["system_id"], row["ligand_instance_chain"])] = {
            **row, "proper": flag == "true",
        }
    groups = {row["group_key"] for row in rows}
    if set(splits) != groups:
        raise InputError("manifest_group_mismatch", "Manifest must cover exactly all annotation groups")

    # Build connected resampling units from *all* annotations before filtering.
    # component_id, when supplied, must be frozen upstream, without pose labels.
    parents = {group: group for group in groups}

    def find(group):
        while parents[group] != group:
            parents[group] = parents[parents[group]]
            group = parents[group]
        return group

    for field in ("system_id", "cluster", "entry_pdb_id", "component_id"):
        linked = defaultdict(set)
        for row in rows:
            value = row.get(field, "")
            if field in fields and (not value.strip() or value != value.strip()):
                raise InputError("invalid_group_metadata", f"Empty/padded {field}")
            if value:
                linked[value].add(row["group_key"])
        for members in linked.values():
            if len({splits[group] for group in members}) > 1:
                raise InputError("split_leakage", f"Cross-partition {field}", len(members))
            first = min(members)
            for member in sorted(members):
                a, b = find(first), find(member)
                parents[max(a, b)] = min(a, b)
    for row in annotated.values():
        row["split"] = splits[row["group_key"]]
        row["resampling_group"] = find(row["group_key"])
    return annotated


@dataclass(frozen=True)
class Candidate:
    """Allowlisted policy input. No RMSD, reference mappings or raw-row access."""

    case: tuple
    seed: str
    sample: str
    mapping_id: str
    score: float | None

    @property
    def identity(self):
        return (*self.case, self.seed, self.sample, self.mapping_id)


@dataclass
class EligibleInput:
    annotations: dict
    candidates: list
    references: dict
    report: dict


def load_inputs(annotations, predictions, manifest, *, method, synthetic_only):
    if synthetic_only is not True:
        raise InputError("real_data_blocked", "Phase 04 currently permits synthetic fixtures only")
    path = Path(predictions)
    if path.suffix != ".csv" or path.name != method:
        raise InputError("source_mismatch", "--method must equal the single input CSV basename")
    if method.lower().startswith(("af3", "alphafold")):
        raise InputError("restricted_method", "AlphaFold 3 sources are blocked in Phase 04")
    annotated = read_annotations(annotations, manifest)
    rows, fields = read_csv(predictions, PREDICTION_FIELDS)
    labels = sorted({row["method"] for row in rows})
    if any(label.lower().startswith(("af3", "alphafold")) for label in labels):
        raise InputError("restricted_method", "AlphaFold 3 labels are blocked in Phase 04")
    if len(labels) != 1 or not labels[0].strip() or labels[0] != labels[0].strip():
        raise InputError("mixed_method_labels", "One nonempty method label required per source CSV")
    staged = []
    provenance = []
    exclusions = Counter()
    score_issues = Counter()
    targets = {key[0] for key in annotated}
    case_rows = Counter()
    proper_rows = Counter()
    for index, row in enumerate(rows, start=2):
        key = (row["target"], row["ligand_instance_chain"])
        reason = None
        if not key[0].strip() or not key[1].strip() or any(x != x.strip() for x in key):
            reason = "missing_or_padded_case_identity"
        elif key[0] not in targets:
            reason = "unmatched_target"
        elif key not in annotated:
            reason = "unmatched_ligand_chain"
        else:
            case_rows[key] += 1
            if not annotated[key]["proper"]:
                reason = "nonproper_ligand"
            else:
                proper_rows[key] += 1
        seed, sample, mapping = (row.get(name, "") for name in ("seed", "sample", "mapping_id"))
        score = number(row.get("ranking_score"))
        if reason is None:
            if "ranking_score" not in fields:
                score_issues["score_column_absent"] += 1
            elif score is None:
                score_issues["missing_or_nonfinite_score"] += 1
            if any(value != value.strip() for value in (seed, sample, mapping)):
                reason = "invalid_run_provenance"
            elif "ranking_score" in fields and (not seed or not sample):
                reason = "missing_run_provenance"
        detail = {
            "csv_record": index, "case": list(key), "seed": seed,
            "sample": sample, "mapping_id": mapping,
            # These archived matching fields are audit-only, never policy input.
            "source_mapping": {name: row[name] for name in (
                "model_ligand_ccd_code", "model_ligand_chain_rmsd"
            ) if name in fields},
            "exclusion_reason": reason,
        }
        provenance.append(detail)
        if reason:
            exclusions[reason] += 1
            continue
        staged.append((Candidate(key, seed, sample, mapping, score), row, detail))

    # A collision cannot be repaired by ordering on a label or dropping a row.
    identities = Counter(item[0].identity for item in staged)
    by_run = defaultdict(list)
    for candidate, _, _ in staged:
        by_run[(*candidate.case, candidate.seed, candidate.sample)].append(candidate)
    ambiguous_runs = {key for key, members in by_run.items()
                      if len(members) > 1 and any(not c.mapping_id for c in members)}
    candidates, references = [], {}
    for candidate, row, detail in staged:
        if identities[candidate.identity] > 1 or (
            *candidate.case, candidate.seed, candidate.sample
        ) in ambiguous_runs:
            reason = "ambiguous_prediction_identity"
            detail["exclusion_reason"] = reason
            exclusions[reason] += 1
            continue
        candidates.append(candidate)
        reference = number(row.get("rmsd"))
        references[candidate.identity] = reference if reference is not None and reference >= 0 else None
    return EligibleInput(annotated, candidates, references, {
        "source_table": path.name,
        "method_labels": labels,
        "hashes": {"annotations": sha256(annotations), "predictions": sha256(predictions),
                   "manifest": sha256(manifest)},
        "rows_total": len(rows),
        "retained_rows": len(candidates),
        "row_exclusions": dict(sorted(exclusions.items())),
        "score_unavailability": dict(sorted(score_issues.items())),
        "has_score_column": "ranking_score" in fields,
        "annotation_cases_by_split": {split: {
            "all": sum(row["split"] == split for row in annotated.values()),
            "proper": sum(row["split"] == split and row["proper"] for row in annotated.values()),
            "nonproper": sum(row["split"] == split and not row["proper"] for row in annotated.values()),
            "distinct_groups": len({row["group_key"] for row in annotated.values() if row["split"] == split}),
        } for split in SPLITS},
        "prediction_case_count": len(case_rows),
        "proper_prediction_case_count": len(proper_rows),
        "proper_prediction_cases": sorted(proper_rows),
        "row_provenance": provenance,
        "resampling_basis": "connected group_key/system_id/cluster plus optional entry_pdb_id/component_id",
        "has_upstream_component_id": "component_id" in next(iter(annotated.values())),
    })
