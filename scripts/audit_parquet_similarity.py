"""Sovra Phase 03E: read-only, row-group-streamed similarity audit.

Reports cross-partition links among *annotated* Runs N' Poses systems.
Does not prove absence of data leakage: the source Parquet compares queries to
the wider PDB, not necessarily every benchmark-system pair.
Requires: pip install pyarrow
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None

METRIC_CANDIDATES = (
    "sucos_shape_pocket_qcov",
    "pocket_qcov",
    "pocket_fident_qcov",
    "protein_fident_weighted_sum",
    "pocket_fident",
)
SPLITS = {"train", "val", "test"}
ZENODO_PARQUET_MD5 = "eeac5530410568f91ff3a4cdd5756e56"


def file_hash(path, name):
    h = hashlib.new(name)
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(annotations, manifest, similarity, threshold=80.0):
    if pq is None:
        raise RuntimeError("pyarrow is required: pip install pyarrow")
    with open(manifest, encoding="utf-8") as fh:
        assignments = json.load(fh)
    if not isinstance(assignments, dict):
        raise ValueError("Split manifest must map group_key to train/val/test")

    group_split = {}
    system_splits = defaultdict(set)
    group_to_system = {}
    group_to_cluster = {}
    with open(annotations, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        required = {"group_key", "system_id", "cluster"}
        if required - set(reader.fieldnames or ()):
            raise ValueError("Missing annotation columns: " + str(sorted(required - set(reader.fieldnames or ()))))
        for row in reader:
            group, system, cluster = (row["group_key"], row["system_id"], row["cluster"])
            split = assignments.get(group)
            if split not in SPLITS:
                raise ValueError("Missing or invalid split: " + group)
            if group in group_to_system and group_to_system[group] != system:
                raise ValueError("Group maps to multiple system IDs: " + group)
            if group in group_to_cluster and group_to_cluster[group] != cluster:
                raise ValueError("Group maps to multiple cluster IDs: " + group)
            group_split[group] = split
            group_to_system[group] = system
            group_to_cluster[group] = cluster
            system_splits[system].add(split)

    path = Path(similarity)
    pf = pq.ParquetFile(path)
    columns = set(pf.schema_arrow.names)
    required = {"group_key", "target_system"}
    if required - columns:
        raise ValueError("Similarity Parquet missing columns: " + str(sorted(required - columns)))
    metrics = [m for m in METRIC_CANDIDATES if m in columns]
    if not metrics:
        raise ValueError("No documented similarity metrics found; inspect Parquet schema")
    projected = ["group_key", "target_system"] + metrics
    if "target_release_date" in columns:
        projected.append("target_release_date")

    seen_link = set()
    violations = {m: set() for m in metrics}
    link_samples = {m: [] for m in metrics}
    flow_counts = Counter()
    stats = Counter()
    uncovered_queries = set(group_split)
    for batch in pf.iter_batches(batch_size=50000, columns=projected):
        for row in batch.to_pylist():
            stats["parquet_rows_read"] += 1
            group, target = row["group_key"], row["target_system"]
            if group not in group_split:
                stats["query_missing_annotation"] += 1
                continue
            uncovered_queries.discard(group)
            possible_splits = system_splits.get(target)
            if not possible_splits:
                stats["target_not_in_benchmark_annotations"] += 1
                continue
            source_split = group_split[group]
            target_splits = possible_splits - {source_split}
            if not target_splits:
                stats["target_only_same_partition"] += 1
                continue
            stats["cross_partition_similarity_rows"] += 1
            for target_split in target_splits:
                pair = (group, target, target_split)
                if pair not in seen_link:
                    seen_link.add(pair)
                    flow_counts[source_split + "->" + target_split] += 1
                for metric in metrics:
                    val = row.get(metric)
                    if val is None:
                        continue
                    try:
                        score = float(val)
                    except (ValueError, TypeError):
                        continue
                    if score >= threshold:
                        violations[metric].add(pair)
                        if len(link_samples[metric]) < 5:
                            sample = dict(group_key=group, target_system=target,
                                          source_split=source_split, target_split=target_split,
                                          score=round(score, 2))
                            if sample not in link_samples[metric]:
                                link_samples[metric].append(sample)
    actual_md5 = file_hash(path, "md5")
    result = {
        "status": "AUDIT_ONLY_NOT_FROZEN",
        "source": "Runs N' Poses / Zenodo record 16754298, v4",
        "parquet_size_bytes": path.stat().st_size,
        "parquet_md5": actual_md5,
        "zenodo_md5_expected": ZENODO_PARQUET_MD5,
        "zenodo_md5_matches": actual_md5 == ZENODO_PARQUET_MD5,
        "parquet_sha256": file_hash(path, "sha256"),
        "manifest_sha256": file_hash(manifest, "sha256"),
        "annotations_sha256": file_hash(annotations, "sha256"),
        "parquet_row_groups": pf.num_row_groups,
        "parquet_rows_metadata": pf.metadata.num_rows,
        "parquet_columns": list(pf.schema_arrow.names),
        "included_similarity_metrics": metrics,
        "threshold_score_out_of_100": threshold,
        "benchmark_systems": len(system_splits),
        "systems_assigned_multiple_splits": sum(len(s) > 1 for s in system_splits.values()),
        "query_groups_without_any_similarity_rows": len(uncovered_queries),
        "unique_cross_partition_links": len(seen_link),
        "cross_partition_link_direction_counts": dict(sorted(flow_counts.items())),
        "threshold_links_by_metric": {m: len(pairs) for m, pairs in violations.items()},
        "example_high_links_by_metric": link_samples,
        "row_counters": dict(stats),
        "limitations": [
            "Scores describe comparisons to wider PDB, not guaranteed exhaustive all-pairs among current benchmark systems.",
            "An absent match does not prove dissimilarity.",
            "One target_system can have multiple annotated ligand groups in different partitions; split mapping is potentially ambiguous.",
            "Similarity criteria are directed and metric-specific; results do not certify leakage-free splits.",
            "Training-set contamination of a foundation model is distinct from leakage across Sovra policy splits.",
            "A threshold hit is an audit warning; scientific cutoff must be justified before split revision.",
        ],
    }
    if not result["zenodo_md5_matches"]:
        result["status"] = "SOURCE_MD5_MISMATCH_REVIEW_REQUIRED"
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--similarity", required=True)
    p.add_argument("--threshold", type=float, default=80)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    if not 0 <= args.threshold <= 100:
        p.error("Expected a 0–100 similarity threshold")
    report = audit(args.annotations, args.manifest, args.similarity, args.threshold)
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "unique_cross_partition_links": report["unique_cross_partition_links"],
        "threshold_links_by_metric": report["threshold_links_by_metric"],
        "report": args.out,
    }, indent=2))


if __name__ == "__main__":
    main()
