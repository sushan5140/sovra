# Phase 03E — Verified similarity audit results
**Audit state: COMPLETE. Dataset freeze state: BLOCKED.**
Date: 2026-10-17 (UTC). Analysis against published Runs N' Poses Zenodo v4 (record 16754298).
Workflow run: https://github.com/sushan5140/sovra/actions/runs/38995170462
Run ID: 38995170462; job 117286027328; conclusion: SUCCESS.
Report artifact: phase03e-similarity-report (artifact ID 12087200172, SHA256 digest fb20d827de01a88950c3bae0932e42d3f83f01bab69b28127806500390112610; expires 2026-10-31).
**All 12 synthetic tests passed.** Publisher MD5 checks for annotations.csv and all_similarity_scores.parquet passed.
Manifest SHA256: e3bb0433c6a367ebd5a8cc0403d11f300ee7913534e289f072668c7c01222604.

## Machine-observed result (GitHub Actions logs)
The audit scanned **3,862,734 Parquet rows**, finding **19,615 observed distinct directed cross-partition (query group, target system, target partition) links** on the provisional split.

| Metric | Distinct cross-partition links with score ≥80/100 |
|---|---:|
| protein_fident_weighted_sum | 5,716 |
| pocket_fident | 6,016 |
| pocket_fident_qcov | 1,732 |
| pocket_qcov | 3,425 |
| sucos_shape_pocket_qcov | 0 |

**These columns are overlapping sets of links and must not be summed.** A lack of SuCOS≥80 hits does not establish a lack of significant sequence/pocket overlap.

Row audit counters:
- 3,862,734 scanned
- 137,326 source query records not matched to benchmark annotations
- 3,587,551 target references not in benchmark annotation systems
- 118,242 records mapping only to the same partition
- 19,615 cross-partition similarity rows

The different row counts reflect the audit's filtering logic. A directed link is not an independent protein family or proof of training contamination. Scores derived from comparison to the broader PDB may not cover all benchmark-to-benchmark pairs.

## Audit interpretation and decision
- **Phase 03E complete:** real similarity archive analyzed on GitHub Actions, checksums passed, and results confirmed from job logs.
- **Do not freeze the old split.** Despite zero shared cluster IDs, 5,716 high protein-identity and 6,016 high pocket-identity observed links show that cluster isolation alone is insufficient to justify a claim of unseen protein-family generalization.
- The ≥80 cutoff was exploratory, not a validated biophysical leakage threshold. Threshold selection and connected-component clustering must be declared before using pose-success labels.
- A protein-family holdout needs a new leakage-aware split with clearly specified protein/pocket linkage rules, and documented attrition/coverage.
- Chemical ligand overlap remains a separate issue (92 ligand SMILES cross partitions in Phase 03C).
- **No training, pose-accuracy benchmarking, or novel model improvement has yet occurred.** This is a split audit, not a model evaluation.

## Next steps before Phase 04
1. Define a protein-family similarity policy and threshold sensitivity analysis; do not cherry-pick threshold based on downstream performance.
2. Construct connected components from observed benchmark-to-benchmark high-similarity edges (taking care of system→multiple-group mappings), then assign entire components to one partition. Do not infer absence of edges as independent proof of dissimilarity.
3. Re-audit cross-split links for the chosen metrics and alternative thresholds; quantify retained independent clusters/cases by method.
4. Review remaining third-party model-output restrictions (especially AlphaFold 3) and ensure train/test actions do not use experimental-reference columns.
5. Freeze only if sufficient independent held-out systems remain and the scientific estimand can be defended.

## Reproducibility
Source code: scripts/audit_parquet_similarity.py
Workflow: .github/workflows/phase03e-audit.yml
Detailed artifact available from the workflow run through 2026-10-31. Public report preserves aggregated counts, not original third-party Parquet rows.
