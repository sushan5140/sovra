"""Four-field Boltz-1 selection boundary: no files, labels or ligand mappings.

This module deliberately has no dependency on the adapter or evaluation code.
Ranking receives only immutable, exact-type primitive projections.
"""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

PREDICTION_FIELDS = ("target", "seed", "sample", "ranking_score")


def clean_identifier(value):
    return type(value) is str and bool(value) and value == value.strip()


@dataclass(frozen=True, slots=True)
class PredictionRun:
    target: str
    seed: str
    sample: str
    ranking_score: float

    def __post_init__(self):
        if not all(clean_identifier(v) for v in (self.target, self.seed, self.sample)):
            raise ValueError("Prediction run requires nonempty, unpadded string identifiers")
        if type(self.ranking_score) is not float or not math.isfinite(self.ranking_score):
            raise ValueError("Prediction run requires a finite float score")

    @property
    def identity(self):
        return self.target, self.seed, self.sample


@dataclass(frozen=True, slots=True)
class PredictionIndex:
    runs: tuple

    def __post_init__(self):
        if type(self.runs) is not tuple or any(type(run) is not PredictionRun for run in self.runs):
            raise TypeError("PredictionIndex accepts only a tuple of exact PredictionRun objects")
        keys = [run.identity for run in self.runs]
        if len(keys) != len(set(keys)):
            raise ValueError("Repeated inference run identity")


@dataclass(frozen=True, slots=True)
class Decision:
    """Full deterministic ordering; the first run is the preselected answer."""

    ordered_runs: tuple

    def __post_init__(self):
        PredictionIndex(self.ordered_runs)
        if not self.ordered_runs or len({r.target for r in self.ordered_runs}) != 1:
            raise ValueError("A decision must contain runs for exactly one target")

    @property
    def selected(self):
        return self.ordered_runs[0]


def rank_prediction_index(prediction_index):
    """Fixed Boltz confidence descending, then lexical seed/sample; no tuning."""
    if type(prediction_index) is not PredictionIndex:
        raise TypeError("Ranking requires an isolated PredictionIndex")
    grouped = defaultdict(list)
    for run in prediction_index.runs:
        grouped[run.target].append(run)
    return tuple(Decision(tuple(sorted(grouped[target], key=lambda r: (
        -r.ranking_score, r.seed, r.sample
    )))) for target in sorted(grouped))


def finite_score(value):
    # No conversion of arbitrary objects with potentially reference-aware hooks.
    if type(value) not in (str, int, float):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def build_prediction_index(rows, eligible_targets):
    """Project only four keys; quarantine an entire target on run ambiguity.

    Diagnostic maps are returned separately and never passed to ranking.
    Duplicate detection precedes score filtering, so an unscored collision
    cannot silently disappear. Reference fields are never requested.
    """
    targets = frozenset(eligible_targets)
    if not all(clean_identifier(target) for target in targets):
        raise ValueError("Invalid cohort target")
    staged = defaultdict(list)
    counts = Counter({key: 0 for key in (
        "rows_total", "invalid_target_rows", "outside_cohort_rows",
        "quarantined_rows", "missing_score_rows", "indexed_rows",
    )})
    for row in rows:
        counts["rows_total"] += 1
        target = row.get("target")
        if not clean_identifier(target):
            counts["invalid_target_rows"] += 1
        elif target not in targets:
            counts["outside_cohort_rows"] += 1
        else:
            staged[target].append((row.get("seed"), row.get("sample"), row.get("ranking_score")))
    runs, target_stats = [], {}
    for target in sorted(targets):
        source = staged[target]
        ids = [(seed, sample) for seed, sample, _ in source]
        missing = any(not clean_identifier(seed) or not clean_identifier(sample) for seed, sample in ids)
        duplicate = not missing and len(ids) != len(set(ids))
        status = ("no_predictions" if not source else
                  "missing_or_invalid_run_id" if missing else
                  "duplicate_run_id" if duplicate else "indexed")
        indexed = []
        if missing or duplicate:
            counts["quarantined_rows"] += len(source)
        else:
            for seed, sample, raw_score in source:
                score = finite_score(raw_score)
                if score is None:
                    counts["missing_score_rows"] += 1
                else:
                    indexed.append(PredictionRun(target, seed, sample, score))
            if source and not indexed:
                status = "no_finite_score"
        runs.extend(indexed)
        counts["indexed_rows"] += len(indexed)
        target_stats[target] = {"status": status, "source_rows": len(source), "indexed_rows": len(indexed)}
    return (PredictionIndex(tuple(sorted(runs, key=lambda r: r.identity))),
            {"row_counts": dict(counts), "target_stats": target_stats})
