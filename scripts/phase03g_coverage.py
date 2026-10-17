"""Phase 03G: read-only, provenance-aware ligand eligibility & method coverage.

No prediction accuracy is calculated. Ground-truth RMSD is checked for
availability only; it must NEVER become an inference-time policy feature.
Input is the pinned Runs N' Poses v4 annotations, predictions archive and
Phase 03F candidate split JSON. Stdlib-only; never writes source rows.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

ANNOTATION_FIELDS = {
    "system_id", "ligand_instance_chain", "group_key",
    "ligand_is_proper", "cluster"
}
PREDICTION_FIELDS = {"target", "ligand_instance_chain", "method"}
SPLITS = {"train", "val", "test"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(value):
    try:
        return value is not None and value.strip() != "" and math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def proper_boolean(value):
    if str(value).strip().lower() == "true":
        return True
    if str(value).strip().lower() == "false":
        return False
    raise ValueError("Invalid ligand_is_proper boolean: " + repr(value))


def audit(annotations, predictions, manifest):
    with open(manifest, encoding="utf-8") as f:
        splits = json.load(f)
    if not isinstance(splits, dict):
        raise ValueError("Manifest must be a group_key to train/val/test dictionary")
    annotated = {}
    targets = set()
    with open(annotations, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = ANNOTATION_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing annotation columns: " + str(sorted(missing)))
        for row in reader:
            group = row["group_key"]
            split = splits.get(group)
            if split not in SPLITS:
                raise ValueError("Missing or invalid split for annotation: " + repr(group))
            key = (row["system_id"], row["ligand_instance_chain"])
            if not all(key) or not group:
                raise ValueError("Empty annotation identity")
            if key in annotated:
                raise ValueError("Duplicate annotation ligand identity: " + repr(key))
            annotated[key] = (group, split, proper_boolean(row["ligand_is_proper"]))
            targets.add(row["system_id"])
    if set(splits) != {v[0] for v in annotated.values()}:
        raise ValueError("Split manifest has unknown/missing group keys")

    table_reports = []
    with tarfile.open(predictions, "r:*") as archive:
        for member in sorted(archive.getmembers(), key=lambda m: m.name):
            if not member.isfile() or not member.name.lower().endswith(".csv"):
                continue
            fd = archive.extractfile(member)
            if fd is None:
                continue
            with io.TextIOWrapper(fd, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fields = set(reader.fieldnames or ())
                missing = PREDICTION_FIELDS - fields
                if missing:
                    raise ValueError(member.name + " missing columns " + str(sorted(missing)))
                counts = Counter({
                    "rows_total": 0,
                    "matched_rows": 0,
                    "unmatched_target": 0,
                    "unmatched_missing_ligand_chain": 0,
                    "unmatched_chain": 0,
                    "matched_improper_ligand_rows": 0,
                    "proper_matched_rows": 0,
                    "proper_rows_with_finite_score": 0,
                    "proper_rows_without_finite_score": 0,
                    "proper_rows_with_finite_reference_metric": 0,
                    "proper_rows_without_finite_reference_metric": 0,
                    "proper_rows_with_score_and_reference": 0,
                })
                splits_all = Counter()
                split_eligible = Counter()
                observed_methods = set()
                all_cases = set()
                eligible_cases = set()
                selected_cases = set()
                selected_samples = defaultdict(set)
                for row in reader:
                    counts["rows_total"] += 1
                    observed_methods.add(row["method"])
                    target = row["target"].strip()
                    chain = row["ligand_instance_chain"].strip()
                    # Reason codes are mutually exclusive, to avoid double counting.
                    if not target or target not in targets:
                        counts["unmatched_target"] += 1
                        continue
                    if not chain:
                        counts["unmatched_missing_ligand_chain"] += 1
                        continue
                    annotation = annotated.get((target, chain))
                    if annotation is None:
                        counts["unmatched_chain"] += 1
                        continue
                    group, split, proper = annotation
                    counts["matched_rows"] += 1
                    splits_all[split] += 1
                    all_cases.add(group)
                    if not proper:
                        counts["matched_improper_ligand_rows"] += 1
                        continue
                    counts["proper_matched_rows"] += 1
                    split_eligible[split] += 1
                    eligible_cases.add(group)
                    has_score = "ranking_score" in fields and finite(row.get("ranking_score"))
                    has_label = "rmsd" in fields and finite(row.get("rmsd"))
                    if has_score:
                        counts["proper_rows_with_finite_score"] += 1
                    else:
                        counts["proper_rows_without_finite_score"] += 1
                    if has_label:
                        counts["proper_rows_with_finite_reference_metric"] += 1
                    else:
                        counts["proper_rows_without_finite_reference_metric"] += 1
                    if has_score and has_label:
                        counts["proper_rows_with_score_and_reference"] += 1
                        selected_cases.add(group)
                        # Informational only; same seed/sample may have distinct mappings.
                        selected_samples[group].add((row.get("seed"), row.get("sample")))
                if not counts["rows_total"]:
                    raise ValueError(member.name + " empty prediction table")
                table_reports.append({
                    "source_table": member.name,
                    "method_labels": sorted(observed_methods),
                    "has_ranking_score_column": "ranking_score" in fields,
                    "has_rmsd_column": "rmsd" in fields,
                    "has_seed_and_sample": {"seed", "sample"}.issubset(fields),
                    "counts": dict(counts),
                    "matched_rows_by_split": dict(sorted(splits_all.items())),
                    "proper_rows_by_split": dict(sorted(split_eligible.items())),
                    "unique_matched_ligand_cases": len(all_cases),
                    "unique_proper_ligand_cases": len(eligible_cases),
                    "unique_score_and_reference_cases": len(selected_cases),
                    "cases_with_two_or_more_distinct_seed_sample_pairs": sum(
                        len(pairs) >= 2 for pairs in selected_samples.values()
                    ),
                    "note": "Coverage eligibility ONLY; no top-1 or oracle scoring. Source filename is the model provenance.",
                })
    if not table_reports:
        raise ValueError("No prediction CSV tables in archive")
    return {
        "status": "COVERAGE_AUDITED_NOT_FROZEN",
        "annotations_sha256": sha256(annotations),
        "predictions_sha256": sha256(predictions),
        "candidate_manifest_sha256": sha256(manifest),
        "annotation_ligand_cases": len(annotated),
        "annotation_proper_ligand_cases": sum(x[2] for x in annotated.values()),
        "candidate_group_count_by_split": dict(Counter(x[1] for x in annotated.values())),
        "model_tables": table_reports,
        "safeguards": [
            "Counts are rows unless explicitly marked distinct cases; repeated mappings are not deduplicated.",
            "Only matching, proper ligands with finite scores AND finite reference labels may enter a future supervised selection evaluation.",
            "Reference RMSD is NOT allowed as an inference-time input.",
            "Scores cannot be compared across models until score direction and calibration are validated.",
            "Snapshot/model licenses, pose label semantics, and final holdout policy remain open gates.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    r = audit(a.annotations, a.predictions, a.manifest)
    Path(a.out).write_text(json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": r["status"],
        "annotation_proper_ligand_cases": r["annotation_proper_ligand_cases"],
        "candidate_group_count_by_split": r["candidate_group_count_by_split"],
        "method_summary": [{
            "source_table": m["source_table"],
            "model_labels": m["method_labels"],
            "proper_ligand_cases": m["unique_proper_ligand_cases"],
            "score_and_reference_cases": m["unique_score_and_reference_cases"],
            "usable_rows": m["counts"].get("proper_rows_with_score_and_reference", 0),
        } for m in r["model_tables"]],
    }, indent=2))


if __name__ == "__main__":
    main()
