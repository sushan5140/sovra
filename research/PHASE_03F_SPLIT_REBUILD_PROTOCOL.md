# Phase 03F — Similarity-graph split reconstruction
Date: 2026-10-17
Status: **METHOD & TESTS COMMITTED; LIVE RESULT PENDING**

## Why this phase exists
Phase 03E (verified GitHub Actions run 38995170462) measured **19,615** observed links across provisional train/validation/test partitions and thousands of high-similarity protein/pocket matches at the exploratory ≥80/100 threshold. A cluster-ID-only split cannot establish a strict unseen-protein/pocket evaluation.

## Independent grouping algorithm
1. Read annotations and form an initial group per `group_key`.
2. **Never separate** groups sharing the same published `cluster`, `system_id`, or `entry_pdb_id`.
3. For links in the pinned Zenodo Runs N' Poses Parquet file, join benchmark-query `group_key` to benchmark target `target_system`, including *all* its annotated ligand groups.
4. Union linked groups where either protein identity exceeds threshold or pocket identity exceeds threshold.
5. Analyze **70, 80, 90, 95** thresholds and two policies:
   - protein weighted identity OR unadjusted pocket identity
   - protein weighted identity OR query-coverage-adjusted pocket identity
6. Assign entire connected components deterministically to candidate train/validation/test buckets; prefer roughly 70%/15%/15% by group count. A giant connected component may make those proportions impossible.
7. Report component sizes, largest share, partition count and matching coverage without examining pose accuracy, labels or model quality.

## Scientific boundaries
- These are **observed database similarity links**, not proven protein-family labels or necessarily exhaustive benchmark all-pairs comparisons.
- A successful identity-preserving split is not proof of independence from foundation-model training data.
- The 80 threshold is exploratory, not selected by downstream performance; stronger family holdouts may require alternative clustering.
- The candidate JSON is NOT scientifically frozen and not for unqualified training.
- Licensing and redistribution rules for third-party model outputs remain separate approval gates.
- Source data, molecules, and large CSV/Parquet files do not belong in the public GitHub repository.

## Reproduction
Workflow: [Phase 03F similarity-aware split feasibility](../.github/workflows/phase03f-rebuild.yml).
Implementation: [scripts/phase03f_rebuild_splits.py](../scripts/phase03f_rebuild_splits.py).
Synthetic tests: [tests/test_phase03f_splits.py](../tests/test_phase03f_splits.py).

Use the same Zenodo v4 metadata source and verify publisher checksums before reading it.
The workflow stores an **aggregate-only report**, not full raw third-party records.

## Decision gate
A split is only eligible for freeze if it retains meaningful independent train/validation/test group counts, meets predefined within-graph overlap controls at the chosen threshold, and the remaining unobserved-link risk is explicitly quantified or bounded. If giant components eliminate an independent holdout, do not force a 70/15/15 split; narrow the study or choose a different well-motivated benchmark protocol.

No scientific accuracy or intervention advantage has been evaluated in this phase.
