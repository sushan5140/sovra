# Phase 03F — Similarity-aware split feasibility: measured results

Date: 2026-10-17 UTC
Status: **REAL-DATA REBUILD SUCCESSFUL; INDEPENDENT CROSS-SPLIT VERIFICATION PENDING; NOT SCIENTIFICALLY FROZEN**.

## Reproducibility
Initial real-data workflow run: https://github.com/sushan5140/sovra/actions/runs/38997811499
Status: completed / success.
All **14 synthetic tests passed** and both publisher MD5 checks passed.
Source: Runs N' Poses / Zenodo v4 (https://zenodo.org/records/16754298).
Reads the official `annotations.csv` and `all_similarity_scores.parquet`; no model-success labels or experimental pose metrics were used for grouping.
Processed 3,862,734 Parquet rows; 137,857 candidate query-to-target rows joined both ends to benchmark annotations.
The old split failed its observed-link audit (Phase 03E).

## Rebuilt graph components and feasibility
We preserve exact published cluster IDs, system IDs and PDB entry IDs, then link candidate pairs for the chosen identity threshold and policy.

| Threshold | Components: protein OR pocket identity | Components: protein OR coverage-adjusted pocket identity |
| ---: | ---: | ---: |
| 70 | 676 | 702 |
| 80 | **704** | 725 |
| 90 | 715 | 736 |
| 95 | 725 | 748 |

At all eight configurations, the largest component contains **410 of 4,235 groups** (9.6812%); therefore the graph did **not** collapse into one giant component.
The candidate split generator assigned **2,965 train, 635 validation and 635 test annotation groups**. This balancing is deterministic but does not guarantee equal representation of model outputs, actual proteins, ligand diversity, or independent protein families.

The proposed stricter policy is *protein weighted identity ≥80 OR unadjusted pocket identity ≥80*, with the connected components isolated across partitions. This is a sensitivity-analysis candidate rather than a validated biophysical threshold.
Selected candidate manifest SHA256: `48ad536f241cc6f68eb86fa509ec28d6ee4f205f7bba5536c15254081aa8a29b`.
The manifest was produced in workflow scratch space; it was not uploaded to the public repository due to unresolved data redistribution terms. Regenerate deterministically with the script and pinned source.

## What this does and does not prove
This shows **feasible component sizes and stable candidate counts**. It is not evidence of scientific model improvement or proof of complete leakage control.

Limitations:
1. Source Parquet compares benchmark queries with a wider PDB snapshot, not necessarily an exhaustive current benchmark-to-benchmark similarity graph.
2. Thresholds are exploratory and not calibrated protein-family definitions.
3. Two systems can have similar binding sites without crossing chosen identity cutoffs.
4. Ligand identity overlaps are not eliminated by this protein-centric policy; analyze stratified by repeated versus unseen ligands.
5. It says nothing about which complexes were included in the original foundation model's training data.
6. AlphaFold 3 and other model-output terms may constrain downstream training and redistribution.

## Final phase gate
An independent re-read of the source using `scripts/audit_parquet_similarity.py` must confirm **zero observed ≥80 cross-partition protein and pocket identity links** under the candidate. This is a necessary check, not a sufficient basis to claim unseen-protein-family independence.
Then verify method-specific coverage, appropriate ligand eligibility, observed-pair coverage and model-output usage rights before freezing a Phase 04 evaluation protocol.

**No pose-recovery accuracy, trained policy, or Sovra improvement has been measured yet.**
