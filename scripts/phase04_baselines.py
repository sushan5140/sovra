"""Reproducible synthetic-only pose selection and held-out evaluation.

Run as python -m scripts.phase04_baselines, or directly as a script.
No training, threshold fitting, downloads, or real-data authorization path.
"""

import argparse
import csv
import json
import math
import platform
import random
from collections import Counter, defaultdict
from pathlib import Path

if __package__:
    from .phase04_eligibility import InputError, SPLITS, SUBGROUP_FIELDS, load_inputs, sha256
else:
    from phase04_eligibility import InputError, SPLITS, SUBGROUP_FIELDS, load_inputs, sha256


def validate_direction(direction):
    if direction not in ("higher", "lower"):
        raise InputError("invalid_score_direction", "Score direction must be explicitly higher or lower")


def select_top1(candidates, *, score_direction):
    """Decision phase: receives only allowlisted Candidate objects, never labels."""
    validate_direction(score_direction)
    by_case = defaultdict(list)
    for candidate in candidates:
        if candidate.score is not None and math.isfinite(candidate.score):
            by_case[candidate.case].append(candidate)
    sign = -1 if score_direction == "higher" else 1
    return {case: min(items, key=lambda c: (sign * c.score, c.seed, c.sample, c.mapping_id))
            for case, items in sorted(by_case.items())}


def bootstrap_interval(values, *, iterations, seed):
    """Percentile interval for case-weighted means, resampling whole groups.

    values maps one connected group ID to all its case outcomes. Each draw
    includes every case in the drawn group, including repeated group draws.
    """
    groups = sorted(values)
    if len(groups) < 2:
        return {"low": None, "high": None, "reason": "fewer_than_two_groups"}
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        draw = [value for _ in groups for value in values[rng.choice(groups)]]
        means.append(sum(draw) / len(draw))
    means.sort()
    return {"low": means[math.floor(0.025 * (iterations - 1))],
            "high": means[math.ceil(0.975 * (iterations - 1))], "reason": None}


def summarize(cases, *, iterations, seed):
    selected = [case for case in cases if case["selected"] is not None]
    evaluable = [case for case in selected if case["top1_success"] is not None]
    oracle = [case for case in cases if case["oracle_success"] is not None]
    paired = [case for case in evaluable if case["oracle_success"] is not None]
    values = defaultdict(list)
    for case in evaluable:
        values[case["resampling_group"]].append(int(case["top1_success"]))
    n = len(cases)
    accuracy = sum(case["top1_success"] for case in evaluable) / len(evaluable) if evaluable else None
    return {
        "proper_cases": n,
        "annotation_group_count": len({case["group_key"] for case in cases}),
        "resampling_group_count": len({case["resampling_group"] for case in cases}),
        "cases_with_predictions": sum(case["has_predictions"] for case in cases),
        "selected_cases": len(selected),
        "evaluable_top1_cases": len(evaluable),
        "selected_without_reference": len(selected) - len(evaluable),
        "evaluable_resampling_groups": len(values),
        "selection_coverage": len(selected) / n if n else None,
        "evaluation_coverage": len(evaluable) / n if n else None,
        "top1_accuracy": accuracy,
        "top1_error": 1 - accuracy if accuracy is not None else None,
        "top1_accuracy_ci95": bootstrap_interval(values, iterations=iterations, seed=seed),
        "oracle_determinate_cases": len(oracle),
        "oracle_success_rate": sum(case["oracle_success"] for case in oracle) / len(oracle) if oracle else None,
        "paired_top1_oracle_cases": len(paired),
        "paired_top1_accuracy": sum(case["top1_success"] for case in paired) / len(paired) if paired else None,
        "paired_oracle_success_rate": sum(case["oracle_success"] for case in paired) / len(paired) if paired else None,
        "candidate_mapping_count_distribution": dict(sorted(Counter(case["candidate_mappings"] for case in cases).items())),
        "case_exclusions": dict(sorted(Counter(case["selection_status"] for case in cases
                                              if case["selection_status"] != "selected").items())),
    }


def risk_coverage(cases, scores, *, direction, thresholds):
    """Apply predeclared thresholds; never optimize a cutoff against labels."""
    available = [case for case in cases if case["selected"] is not None]
    points = [("accept_all_scored", None, available)]
    for threshold in thresholds:
        accepted = [case for case in available if (
            scores[tuple(case["case"])] >= threshold if direction == "higher"
            else scores[tuple(case["case"])] <= threshold
        )]
        points.append(("fixed_threshold", threshold, accepted))
    points.append(("abstain_all", None, []))
    result = []
    for policy, threshold, accepted in points:
        labeled = [case for case in accepted if case["top1_success"] is not None]
        result.append({
            "policy": policy, "threshold": threshold, "accepted_cases": len(accepted),
            "evaluable_cases": len(labeled),
            "accepted_without_reference": len(accepted) - len(labeled),
            "coverage": len(accepted) / len(cases) if cases else None,
            "evaluation_coverage": len(labeled) / len(cases) if cases else None,
            "error": sum(not case["top1_success"] for case in labeled) / len(labeled) if labeled else None,
        })
    return result


def evaluate(annotations, predictions, manifest, *, method, score_direction,
             success_threshold, synthetic_only=False, risk_thresholds=(),
             bootstrap_iterations=1000, bootstrap_seed=0, subgroup_min_groups=5):
    validate_direction(score_direction)
    if not math.isfinite(success_threshold) or success_threshold < 0:
        raise InputError("invalid_success_threshold", "BiSyRMSD threshold must be finite and nonnegative")
    if bootstrap_iterations < 1 or subgroup_min_groups < 2:
        raise InputError("invalid_statistics_config", "Positive bootstrap iterations and >=2 subgroup groups required")
    thresholds = sorted(set(risk_thresholds))
    if any(not math.isfinite(value) for value in thresholds):
        raise InputError("invalid_risk_threshold", "Risk thresholds must be finite and predeclared")
    data = load_inputs(annotations, predictions, manifest, method=method, synthetic_only=synthetic_only)

    # All decisions are finalized before any reference metric is consulted.
    chosen = select_top1(data.candidates, score_direction=score_direction)
    by_case = defaultdict(list)
    for candidate in data.candidates:
        by_case[candidate.case].append(candidate)
    prediction_cases = set(data.report.pop("proper_prediction_cases"))
    cases = []
    for key, annotation in sorted(data.annotations.items()):
        if not annotation["proper"]:
            continue
        candidates = by_case[key]
        selected = chosen.get(key)
        label = data.references[selected.identity] if selected is not None else None
        labels = [data.references[c.identity] for c in candidates]
        known = [value for value in labels if value is not None]
        # A known success proves oracle success even with missing other labels;
        # failure requires complete labels. Never count missing labels as failure.
        oracle = (True if any(value <= success_threshold for value in known)
                  else False if labels and len(known) == len(labels) else None)
        status = "selected" if selected is not None else (
            "no_predictions" if key not in prediction_cases else
            "all_rows_quarantined" if not candidates else "no_finite_score")
        cases.append({
            "case": list(key), "group_key": annotation["group_key"],
            "resampling_group": annotation["resampling_group"], "split": annotation["split"],
            "has_predictions": key in prediction_cases, "selection_status": status,
            "selected": {"seed": selected.seed, "sample": selected.sample, "mapping_id": selected.mapping_id}
            if selected is not None else None,
            "top1_success": label <= success_threshold if label is not None else None,
            "oracle_success": oracle, "oracle_labels_complete": bool(labels) and len(known) == len(labels),
            "candidate_mappings": len(candidates), "reference_labeled_mappings": len(known),
            "distinct_seed_sample_runs": len({(c.seed, c.sample) for c in candidates}),
            "subgroups": {name: annotation.get(name) or "unknown" for name in SUBGROUP_FIELDS},
        })
    scores = {key: selected.score for key, selected in chosen.items()}
    partitions = {}
    for split in SPLITS:
        subset = [case for case in cases if case["split"] == split]
        summary = summarize(subset, iterations=bootstrap_iterations, seed=bootstrap_seed)
        summary["risk_coverage"] = risk_coverage(subset, scores, direction=score_direction, thresholds=thresholds)
        subgroups = {}
        for field in SUBGROUP_FIELDS:
            bins = {}
            for value in sorted({case["subgroups"][field] for case in subset}):
                members = [case for case in subset if case["subgroups"][field] == value]
                stats = summarize(members, iterations=bootstrap_iterations, seed=bootstrap_seed)
                if value == "unknown" or stats["evaluable_resampling_groups"] < subgroup_min_groups:
                    bins[value] = {"status": "insufficient_metadata_or_groups",
                                   "proper_cases": len(members),
                                   "evaluable_resampling_groups": stats["evaluable_resampling_groups"]}
                else:
                    bins[value] = stats
            subgroups[field] = bins
        summary["subgroups"] = subgroups
        partitions[split] = summary
    return {
        "status": "SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE", "schema_version": 1,
        "protocol": {
            "method": method, "score_direction": score_direction,
            "selection_feature": "ranking_score", "reference_metric": "BiSyRMSD",
            "success_rule": "rmsd <= success_threshold", "success_threshold": success_threshold,
            "tie_break": "lexicographic seed, sample, inference-only mapping_id",
            "risk_thresholds": thresholds, "threshold_policy": "predeclared; no fitting or test tuning",
            "bootstrap_method": "case-weighted percentile 95%; whole connected groups with replacement",
            "bootstrap_iterations": bootstrap_iterations, "bootstrap_seed": bootstrap_seed,
            "subgroup_min_groups": subgroup_min_groups,
        },
        "reproducibility": {
            "python": platform.python_version(),
            "code_sha256": {name: sha256(Path(__file__).with_name(name)) for name in (
                "phase04_baselines.py", "phase04_eligibility.py")},
        },
        "eligibility": data.report, "partitions": partitions, "cases": cases,
        "limitations": [
            "Synthetic fixtures only; no measured scientific improvement or model accuracy claim.",
            "Manifest validation checks supplied identities, not unobserved similarity or model-training contamination.",
            "Resampling units are connected supplied groups, not proven independent protein families.",
            "Oracle uses reference labels after decisions; mapping K may exceed distinct pose/run K.",
            "Top-1 and oracle marginal denominators differ with missing labels; use paired fields for comparison.",
            "No-score sources are unavailable for score selection, not model failures.",
        ],
    }


def paired_comparison(left, right):
    """Compare two separately evaluated methods on matched evaluable cases only."""
    if any(report.get("status") != "SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE" for report in (left, right)):
        raise InputError("unapproved_comparison", "Only synthetic evaluation reports accepted")
    for name in ("annotations", "manifest"):
        if left["eligibility"]["hashes"][name] != right["eligibility"]["hashes"][name]:
            raise InputError("comparison_population_mismatch", "Paired reports need identical annotations and manifest")
    for name in ("reference_metric", "success_rule", "success_threshold", "bootstrap_iterations", "bootstrap_seed"):
        if left["protocol"][name] != right["protocol"][name]:
            raise InputError("comparison_protocol_mismatch", f"Paired reports disagree on {name}")
    result = {"status": "SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE",
              "methods": [left["protocol"]["method"], right["protocol"]["method"]], "partitions": {}}
    for split in SPLITS:
        populations = [{tuple(case["case"]): case for case in report["cases"]
                        if case["split"] == split and case["top1_success"] is not None}
                       for report in (left, right)]
        common = sorted(populations[0].keys() & populations[1].keys())
        differences = defaultdict(list)
        for key in common:
            a, b = (population[key] for population in populations)
            differences[a["resampling_group"]].append(int(a["top1_success"]) - int(b["top1_success"]))
        result["partitions"][split] = {
            "paired_cases": len(common), "paired_resampling_groups": len(differences),
            "left_only_evaluable": len(populations[0]) - len(common),
            "right_only_evaluable": len(populations[1]) - len(common),
            "left_minus_right_accuracy": sum(sum(v) for v in differences.values()) / len(common) if common else None,
            "paired_delta_ci95": bootstrap_interval(differences,
                iterations=left["protocol"]["bootstrap_iterations"], seed=left["protocol"]["bootstrap_seed"]),
        }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--method", required=True, help="exact predictions CSV basename, including version")
    parser.add_argument("--score-direction", choices=("higher", "lower"), required=True)
    parser.add_argument("--success-threshold", type=float, required=True)
    parser.add_argument("--risk-threshold", type=float, action="append", default=[])
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--bootstrap-seed", type=int, default=0)
    parser.add_argument("--subgroup-min-groups", type=int, default=5)
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    # Refuse accidental source replacement, including aliases/symlinks.
    output = Path(args.out)
    for source in (args.annotations, args.predictions, args.manifest):
        source_path = Path(source)
        if output.resolve() == source_path.resolve() or (
            output.exists() and source_path.exists() and output.samefile(source_path)
        ):
            parser.error("--out must not overwrite an input file")
    try:
        report = evaluate(args.annotations, args.predictions, args.manifest,
            method=args.method, score_direction=args.score_direction,
            success_threshold=args.success_threshold, synthetic_only=args.synthetic_only,
            risk_thresholds=args.risk_threshold, bootstrap_iterations=args.bootstrap_iterations,
            bootstrap_seed=args.bootstrap_seed, subgroup_min_groups=args.subgroup_min_groups)
    except (OSError, ValueError, csv.Error) as error:
        report = {"status": "BLOCKED", "errors": [str(error)],
                  "exclusion_counts": {getattr(error, "code", "invalid_input"): getattr(error, "count", 1)}}
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "out": str(output)}))
    return int(report["status"] == "BLOCKED")


if __name__ == "__main__":
    raise SystemExit(main())
