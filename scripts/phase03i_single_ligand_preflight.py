"""Sovra Phase 03I: conservative single-ligand & unique-run preflight.

NO experimental accuracy, pose selection or training; no raw inputs exported.
Only tests feasibility of a future reference-independent baseline adapter.
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

SPLITS = ("train", "val", "test")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(2 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def is_finite(value):
    try:
        return value is not None and value.strip() != "" and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def load_single_ligands(annotations, manifest):
    with open(manifest, encoding="utf-8") as f:
        assignments = json.load(f)
    if not isinstance(assignments, dict):
        raise ValueError("Manifest must be a dictionary")
    records = []
    system_count = Counter()
    with open(annotations, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"system_id", "ligand_instance_chain", "group_key", "ligand_is_proper", "num_ligand_chains"}
        if required - set(reader.fieldnames or ()):
            raise ValueError("Missing columns: " + str(sorted(required - set(reader.fieldnames or ()))))
        for row in reader:
            system_count[row["system_id"]] += 1
            records.append(row)
    if set(assignments) != {r["group_key"] for r in records}:
        raise ValueError("Split manifest does not match annotation groups")
    eligible = {}
    proper_all = Counter()
    for row in records:
        split = assignments[row["group_key"]]
        if split not in SPLITS:
            raise ValueError("Invalid split assignment")
        flag = row["ligand_is_proper"].strip().lower()
        if flag not in ("true", "false"):
            raise ValueError("Invalid proper flag")
        if flag == "true":
            proper_all[split] += 1
        if flag != "true" or row["num_ligand_chains"].strip() != "1" or system_count[row["system_id"]] != 1:
            continue
        identity = (row["system_id"], row["ligand_instance_chain"])
        if identity in eligible:
            raise ValueError("Duplicate strict ligand identity")
        eligible[identity] = (row["group_key"], split)
    return eligible, proper_all


def analyze_table(reader, strict):
    cols = set(reader.fieldnames or [])
    if {"target", "ligand_instance_chain", "method"} - cols:
        raise ValueError("Prediction table missing required columns")
    case_runs = defaultdict(list)
    total = Counter()
    methods = set()
    for row in reader:
        total["source_rows"] += 1
        methods.add(row["method"])
        key = (row["target"], row["ligand_instance_chain"])
        if key not in strict:
            continue
        total["rows_in_single_ligand_candidates"] += 1
        case_runs[key].append((
            row.get("seed", ""),
            row.get("sample", ""),
            is_finite(row.get("ranking_score")) if "ranking_score" in cols else False,
            is_finite(row.get("rmsd")) if "rmsd" in cols else False,
        ))
    buckets = {name: defaultdict(set) for name in (
        "observed", "unique_runs", "scored_unique_runs", "scored_unique_complete_reference"
    )}
    exclusions = Counter()
    for key, rows in case_runs.items():
        group, part = strict[key]
        buckets["observed"][part].add(group)
        run_keys = [(seed, sample) for seed, sample, _, _ in rows]
        if any(not seed or not sample for seed, sample in run_keys):
            exclusions["case_missing_seed_or_sample"] += 1
            continue
        if len(run_keys) != len(set(run_keys)):
            exclusions["case_with_repeated_seed_sample"] += 1
            continue
        buckets["unique_runs"][part].add(group)
        if not any(scored for _, _, scored, _ in rows):
            exclusions["unscored_unique_case"] += 1
            continue
        buckets["scored_unique_runs"][part].add(group)
        if all(labeled for _, _, scored, labeled in rows if scored):
            buckets["scored_unique_complete_reference"][part].add(group)
        else:
            exclusions["scored_case_with_missing_reference"] += 1
    return {
        "source_rows": total["source_rows"],
        "rows_in_single_ligand_candidates": total["rows_in_single_ligand_candidates"],
        "method_labels": sorted(methods),
        "has_score": "ranking_score" in cols,
        "has_seed_sample": {"seed", "sample"}.issubset(cols),
        "has_rmsd": "rmsd" in cols,
        "cases": {name: {s: len(items[s]) for s in SPLITS} for name, items in buckets.items()},
        "exclusion_cases": dict(sorted(exclusions.items())),
    }, buckets


def audit(annotations, predictions, manifest):
    strict, all_proper = load_single_ligands(annotations, manifest)
    reports = {}
    populations = {}
    with tarfile.open(predictions, "r:*") as tar:
        for member in sorted(tar.getmembers(), key=lambda m: m.name):
            if not member.isfile() or not member.name.lower().endswith(".csv"):
                continue
            name = Path(member.name).name
            if name in reports:
                raise ValueError("Duplicate prediction filename: " + name)
            stream = tar.extractfile(member)
            if stream is None:
                continue
            with io.TextIOWrapper(stream, encoding="utf-8-sig", newline="") as handle:
                report, groups = analyze_table(csv.DictReader(handle), strict)
            reports[name] = report
            populations[name] = groups["scored_unique_complete_reference"]
    if not reports:
        raise ValueError("Missing prediction tables")
    pairs = {}
    for left, right in (("boltz.csv", "chai.csv"), ("boltz1x.csv", "chai.csv")):
        if left in populations and right in populations:
            pairs[left + "__" + right] = {s: len(populations[left][s] & populations[right][s]) for s in SPLITS}
    eligible = Counter(split for group, split in strict.values())
    return {
        "status": "CONSERVATIVE_COHORT_FEASIBILITY_NOT_FROZEN",
        "source_sha256": {"annotations": file_sha256(annotations),
                          "predictions": file_sha256(predictions),
                          "manifest": file_sha256(manifest)},
        "all_proper_ligand_cases_by_split": {s: all_proper[s] for s in SPLITS},
        "proper_single_ligand_cases_by_split": {s: eligible[s] for s in SPLITS},
        "method_tables": reports,
        "paired_single_ligand_complete_reference_case_intersections": pairs,
        "limitations": [
            "One annotated ligand, one reference row per system and unique seed/sample run IDs are only necessary controls, not proven source-level mapping correctness.",
            "Requiring complete reference labels can bias real comparisons; counts are readiness diagnostics, not a preapproved exclusion rule.",
            "Never transform archive labels into decision-time features or relabel real data as synthetic.",
            "Output permissions, score definitions, strict RMSD<2 convention, frozen splits and prediction provenance remain open gates.",
            "No molecular prediction accuracy or selection performance is computed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    r = audit(args.annotations, args.predictions, args.manifest)
    Path(args.out).write_text(json.dumps(r, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({
        "status": r["status"],
        "proper_single_ligand_cases_by_split": r["proper_single_ligand_cases_by_split"],
        "boltz": r["method_tables"].get("boltz.csv", {}).get("cases", {}),
        "chai": r["method_tables"].get("chai.csv", {}).get("cases", {}),
        "paired_intersections": r["paired_single_ligand_complete_reference_case_intersections"],
    }, indent=2))


if __name__ == "__main__":
    main()
