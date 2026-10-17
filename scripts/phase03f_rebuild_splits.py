"""Sovra Phase 03F: derive candidate similarity-aware splits.

This is an observational linkage audit, not a proof of protein-family
independence. No experimental labels or model success scores are read.
Input: Runs N' Poses annotations.csv, all_similarity_scores.parquet.
Requires: pyarrow. Output: aggregated JSON and candidate manifest, NEVER frozen.
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

METRICS = ("protein_fident_weighted_sum", "pocket_fident",
           "pocket_fident_qcov")
THRESHOLDS = (70.0, 80.0, 90.0, 95.0)
POLICIES = ("protein_or_pocket", "protein_or_coverage_adjusted_pocket")
SPLITS = ("train", "val", "test")
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        x, y = self.find(a), self.find(b)
        if x == y:
            return False
        if self.size[x] < self.size[y]:
            x, y = y, x
        self.parent[y] = x
        self.size[x] += self.size[y]
        return True


def read_annotations(path):
    entries = {}
    systems = defaultdict(set)
    clusters = defaultdict(set)
    pdbs = defaultdict(set)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        needed = {"group_key", "system_id", "cluster", "entry_pdb_id"}
        if needed - set(reader.fieldnames or ()):
            raise ValueError("Missing annotation columns: " + str(sorted(needed-set(reader.fieldnames or ()))))
        for row in reader:
            group = row["group_key"]
            if not group or not row["system_id"] or not row["cluster"]:
                raise ValueError("Empty group, system or cluster")
            if group in entries:
                raise ValueError("Repeated group_key: " + group)
            entries[group] = row
            systems[row["system_id"]].add(group)
            clusters[row["cluster"]].add(group)
            if row.get("entry_pdb_id"):
                pdbs[row["entry_pdb_id"]].add(group)
    if not entries:
        raise ValueError("No annotation rows")
    return entries, systems, clusters, pdbs


def active(protein, pocket, coverage_pocket, threshold, policy):
    if protein is not None and protein >= threshold:
        return True
    if policy == "protein_or_pocket":
        return pocket is not None and pocket >= threshold
    return coverage_pocket is not None and coverage_pocket >= threshold


def number(value):
    if value is None:
        return None
    try:
        n = float(value)
        if n != n:
            return None
        return n
    except (ValueError, TypeError):
        return None


def component_split(uf, groups, seed):
    components = defaultdict(list)
    for group, idx in groups.items():
        components[uf.find(idx)].append(group)
    ordered = sorted(components.values(), key=lambda members: (
        -len(members),
        hashlib.sha256((seed + "|" + min(members)).encode()).hexdigest(),
    ))
    targets = {s: RATIOS[s] * len(groups) for s in SPLITS}
    counts = Counter()
    manifest = {}
    for members in ordered:
        # Deterministic greedy balancing by desired group counts.
        split = max(SPLITS, key=lambda s: (targets[s] - counts[s], -SPLITS.index(s)))
        for g in members:
            manifest[g] = split
        counts[split] += len(members)
    sizes = sorted((len(c) for c in ordered), reverse=True)
    return dict(sorted(manifest.items())), {
        "components": len(sizes),
        "largest_component_groups": sizes[0],
        "largest_component_fraction": round(sizes[0] / len(groups), 6),
        "five_largest_component_sizes": sizes[:5],
        "split_group_counts": {s: counts[s] for s in SPLITS},
        "split_component_counts": {
            s: len({uf.find(groups[g]) for g, part in manifest.items() if part == s})
            for s in SPLITS
        },
    }


def audit(annotations, similarity, out_manifest=None, seed="sovra-v1"):
    if pq is None:
        raise RuntimeError("Install pyarrow")
    rows, by_system, by_cluster, by_pdb = read_annotations(annotations)
    names = sorted(rows)
    indices = {k: i for i, k in enumerate(names)}
    test_cases = {(th, policy): UnionFind(len(names))
                  for th in THRESHOLDS for policy in POLICIES}

    # Enforce exact identity boundaries before linking by estimated similarity.
    for uf in test_cases.values():
        for grouping in (by_cluster, by_system, by_pdb):
            for members in grouping.values():
                items = sorted(members)
                for other in items[1:]:
                    uf.union(indices[items[0]], indices[other])

    pf = pq.ParquetFile(similarity)
    required = {"group_key", "target_system", *METRICS}
    missing = required - set(pf.schema_arrow.names)
    if missing:
        raise ValueError("Similarity columns missing: " + str(sorted(missing)))
    counters = Counter()
    activated = Counter()
    cols = ["group_key", "target_system", *METRICS]
    for batch in pf.iter_batches(batch_size=30000, columns=cols):
        for record in batch.to_pylist():
            counters["rows_scanned"] += 1
            g = record["group_key"]
            if g not in indices:
                counters["unknown_source_group"] += 1
                continue
            target = by_system.get(record["target_system"])
            if not target:
                counters["target_outside_annotations"] += 1
                continue
            counters["mapped_links"] += 1
            p, q, qc = (number(record[k]) for k in METRICS)
            for th in THRESHOLDS:
                for policy in POLICIES:
                    if active(p, q, qc, th, policy):
                        activated[f"{policy}_{int(th)}"] += 1
                        uf = test_cases[(th, policy)]
                        for dest in target:
                            uf.union(indices[g], indices[dest])

    candidates = {}
    summaries = {}
    for (th, policy), uf in test_cases.items():
        manifest, stats = component_split(uf, indices, seed)
        # Verify all annotated equivalent identities stay together.
        for grouping in (by_system, by_cluster, by_pdb):
            if any(len({manifest[g] for g in members}) > 1 for members in grouping.values()):
                raise AssertionError("Identity grouping split detected")
        key = f"{policy}_{int(th)}"
        candidates[key] = manifest
        summaries[key] = dict(stats, triggering_parquet_rows=activated[key])

    selected = "protein_or_pocket_80"
    if out_manifest:
        Path(out_manifest).write_text(
            json.dumps(candidates[selected], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "REBUILT_PROVISIONAL_NOT_FROZEN",
        "source_annotations_sha256": hashlib.sha256(Path(annotations).read_bytes()).hexdigest(),
        "source_similarity_sha256": hashlib.sha256(Path(similarity).read_bytes()).hexdigest(),
        "dataset_group_count": len(names),
        "distinct_systems": len(by_system),
        "distinct_clusters": len(by_cluster),
        "distinct_pdb_entries": len(by_pdb),
        "counter": dict(counters),
        "thresholds": list(THRESHOLDS),
        "policy_definitions": {
            "protein_or_pocket": "protein_fident_weighted_sum >= threshold OR pocket_fident >= threshold",
            "protein_or_coverage_adjusted_pocket": "protein_fident_weighted_sum >= threshold OR pocket_fident_qcov >= threshold",
        },
        "candidate_summary": summaries,
        "candidate_manifest_policy": selected,
        "caveats": [
            "A connected component over observed links is not proof of unseen protein families.",
            "Source similarity rows may omit true within-benchmark pairwise relationships.",
            "Selected 80 threshold is exploratory; compare other thresholds before freezing.",
            "RMSD and all reference-derived model quality labels are absent from this algorithm.",
            "No model training or real pose evaluation was performed.",
            "Third-party raw data and full manifest should not be redistributed before terms review.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--similarity", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest")
    args = parser.parse_args()
    summary = audit(args.annotations, args.similarity, args.manifest)
    Path(args.out).write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "dataset_group_count": summary["dataset_group_count"],
        "counter": summary["counter"],
        "candidate_summary": summary["candidate_summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
