"""Phase 03H: source-identity diagnostics and split-aware case coverage.

Read-only. Counts only. Never creates/guesses mapping IDs; never selects poses
from labels; does not compute model accuracy. Designed for pinned benchmark v4.
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
REFERENCE_COLUMNS = ("rmsd", "lddt_pli", "lddt_lp", "bb_rmsd", "pred_pocket_f1")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(2 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value):
    if value is None or not str(value).strip():
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def load_annotations(path, manifest):
    with open(manifest, encoding="utf-8") as handle:
        assignment = json.load(handle)
    if not isinstance(assignment, dict):
        raise ValueError("Split manifest must be an object")
    annotated = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        mandatory = {"system_id", "ligand_instance_chain", "group_key", "ligand_is_proper"}
        if mandatory - set(reader.fieldnames or []):
            raise ValueError("Missing annotation columns")
        for row in reader:
            group = row["group_key"]
            split = assignment.get(group)
            if split not in SPLITS:
                raise ValueError("Unassigned/invalid group_key")
            flag = row["ligand_is_proper"].strip().lower()
            if flag not in {"true", "false"}:
                raise ValueError("Invalid proper-ligand flag")
            identity = (row["system_id"], row["ligand_instance_chain"])
            if not all(identity) or identity in annotated:
                raise ValueError("Empty or repeated annotation identity")
            annotated[identity] = (group, split, flag == "true")
    if set(assignment) != {v[0] for v in annotated.values()}:
        raise ValueError("Manifest contains extra or omitted groups")
    return annotated


def audit(annotations, predictions, manifest):
    labels = load_annotations(annotations, manifest)
    known_targets = {s for s, chain in labels}
    method_reports = []
    eligible_sets = {}
    with tarfile.open(predictions, "r:*") as archive:
        for member in sorted(archive.getmembers(), key=lambda x: x.name):
            if not member.isfile() or not member.name.endswith(".csv"):
                continue
            file = archive.extractfile(member)
            if file is None:
                continue
            with io.TextIOWrapper(file, encoding="utf-8-sig", newline="") as f:
                table = csv.DictReader(f)
                fields = set(table.fieldnames or [])
                if {"target", "ligand_instance_chain", "method"} - fields:
                    raise ValueError("Missing required prediction fields: " + member.name)
                cnt = Counter()
                case_by_split = {s: set() for s in SPLITS}
                good_case_by_split = {s: set() for s in SPLITS}
                mapping_groups = defaultdict(list)
                labels_seen = set()
                for row in table:
                    cnt["rows"] += 1
                    labels_seen.add(row["method"])
                    target, chain = row["target"], row["ligand_instance_chain"]
                    if target not in known_targets:
                        cnt["unmatched_target"] += 1
                        continue
                    if not chain:
                        cnt["missing_reference_ligand_chain"] += 1
                        continue
                    observed = labels.get((target, chain))
                    if observed is None:
                        cnt["unmatched_reference_chain"] += 1
                        continue
                    group, split, proper = observed
                    cnt["matched_rows"] += 1
                    if not proper:
                        cnt["matched_nonproper_rows"] += 1
                        continue
                    cnt["proper_rows"] += 1
                    case_by_split[split].add(group)
                    score_ok = "ranking_score" in fields and finite(row.get("ranking_score"))
                    ref_ok = "rmsd" in fields and finite(row.get("rmsd"))
                    run_id = (target, chain, row.get("seed", ""), row.get("sample", ""))
                    # Model chain IDs are diagnostics, NOT approved inference-only mapping IDs.
                    model_chain = row.get("model_ligand_chain", "")
                    model_code = row.get("model_ligand_ccd_code", "")
                    mapping_groups[run_id].append((model_chain, model_code))
                    if model_chain:
                        cnt["proper_rows_with_model_ligand_chain"] += 1
                    else:
                        cnt["proper_rows_missing_model_ligand_chain"] += 1
                    if score_ok:
                        cnt["proper_rows_finite_score"] += 1
                    if ref_ok:
                        cnt["proper_rows_finite_reference"] += 1
                    if score_ok and ref_ok:
                        cnt["proper_rows_score_and_reference"] += 1
                        good_case_by_split[split].add(group)
                    if not (row.get("seed") and row.get("sample")):
                        cnt["proper_rows_missing_seed_or_sample"] += 1
                for members in mapping_groups.values():
                    if len(members) <= 1:
                        continue
                    cnt["repeated_case_seed_sample_keys"] += 1
                    cnt["rows_in_repeated_case_seed_sample_keys"] += len(members)
                    chains = [chain for chain, code in members]
                    if not all(chains):
                        cnt["repeated_keys_with_missing_model_chain"] += 1
                    if len(set(chains)) < len(chains):
                        cnt["repeated_keys_with_colliding_model_chain"] += 1
                    combos = [(chain, code) for chain, code in members]
                    if len(set(combos)) < len(combos):
                        cnt["repeated_keys_with_colliding_chain_ccd_pair"] += 1
                basename = Path(member.name).name
                if basename in eligible_sets:
                    raise ValueError("Repeated source model filename: " + basename)
                eligible_sets[basename] = good_case_by_split
                method_reports.append({
                    "source_table": basename,
                    "internal_method_labels": sorted(labels_seen),
                    "source_fields": sorted(fields),
                    "has_inference_model_chain_field": "model_ligand_chain" in fields,
                    "has_seed_and_sample": {"seed", "sample"}.issubset(fields),
                    "has_score": "ranking_score" in fields,
                    "reference_fields_present": sorted(fields & set(REFERENCE_COLUMNS)),
                    "counts": dict(sorted(cnt.items())),
                    "proper_cases_by_split": {s: len(case_by_split[s]) for s in SPLITS},
                    "score_and_reference_cases_by_split": {s: len(good_case_by_split[s]) for s in SPLITS},
                    "interpretation": "Candidate coverage only. Raw target ligand chain can be a reference-mediated join; model_ligand_chain is not automatically an approved mapping ID.",
                })
    if not method_reports:
        raise ValueError("No CSV tables found")
    pairs = {}
    for x, y in [("boltz.csv", "chai.csv"), ("boltz1x.csv", "chai.csv"), ("boltz2.csv", "chai.csv")]:
        if x in eligible_sets and y in eligible_sets:
            pairs[f"{x}__{y}"] = {
                s: len(eligible_sets[x][s] & eligible_sets[y][s]) for s in SPLITS
            }
    counts = Counter(part for group, part, proper in labels.values() if proper)
    return {
        "status": "AUDIT_ONLY_MAPPING_UNRESOLVED",
        "inputs_sha256": {"annotations": sha256(annotations),
                          "predictions": sha256(predictions), "manifest": sha256(manifest)},
        "source_annotation_cases": len(labels),
        "proper_annotation_cases_by_split": {s: counts[s] for s in SPLITS},
        "tables": method_reports,
        "paired_evaluable_case_intersections": pairs,
        "remaining_gates": [
            "Benchmark ligand_instance_chain associations may be reference mediated.",
            "Do not use any model_ligand_chain/mapping_id without independent no-reference validation.",
            "Source versions and score directions require verification before top-1 evaluation.",
            "Counts of finite evaluation labels are not a scientific performance measurement.",
            "Model output usage rights and scientific dataset freeze remain separately blocked.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    report = audit(args.annotations, args.predictions, args.manifest)
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "proper_annotation_cases_by_split": report["proper_annotation_cases_by_split"],
        "paired_evaluable_case_intersections": report["paired_evaluable_case_intersections"],
        "table_summaries": [{
            "source_table": row["source_table"],
            "score_and_reference_cases_by_split": row["score_and_reference_cases_by_split"],
            "repeated_case_seed_sample_keys": row["counts"].get("repeated_case_seed_sample_keys", 0),
            "repeated_keys_with_colliding_model_chain": row["counts"].get("repeated_keys_with_colliding_model_chain", 0),
            "model_ligand_chain_present": row["has_inference_model_chain_field"],
        } for row in report["tables"]]}, indent=2))


if __name__ == "__main__":
    main()
