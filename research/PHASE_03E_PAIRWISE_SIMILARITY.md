# Phase 03E — Pairwise similarity audit execution

Date: 2026-10-17
Status: **AUDIT EXECUTED AND VERIFIED; DATASET NOT FROZEN**

## New artifacts in Sovra
- scripts/audit_parquet_similarity.py — read-only PyArrow streaming, partition-crossing system links, metric threshold tables, md5/sha256 provenance.
- tests/test_parquet_similarity.py — synthetic parquet fixture.
- .github/workflows/phase03e-audit.yml — reproducible one-off GitHub Actions job. Downloads *exactly* annotations.csv and all_similarity_scores.parquet from Runs N' Poses Zenodo v4, checks publisher MD5 hashes, recreates provisional split, then saves a small JSON audit report as a workflow artifact. Raw third-party datasets are not pushed to the repository.

## Important interpretation
The source Parquet contains **benchmark-query → wider-PDB target** similarity links through January 2025. Our script filters targets to those also present in the benchmark annotations and compares the source group split with the target system's recorded split(s).

This is a **directed, observed-links audit**. Absence of a cross-split link does **not** imply the two systems are dissimilar; the source need not contain every required benchmark-to-benchmark pair. Threshold ≥80 is an exploratory flag, not a scientifically fixed partition rule.

A target_system may map to multiple ligand groups and split assignments. The report surfaces the count of those cases, but an interpretation requires manual inspection.

## Publisher-provided exact file checksums (Zenodo 16754298 v4)
- all_similarity_scores.parquet MD5: eeac5530410568f91ff3a4cdd5756e56
- annotations.csv MD5: 793c711638ba20ae40518ed0e36b0a56

Only metadata, scripts and resulting aggregate reports may be put in Sovra GitHub; no raw AF3 outputs or large dataset archives.

## Execution confirmation
GitHub Actions run [38995170462](https://github.com/sushan5140/sovra/actions/runs/38995170462) completed successfully on 2026-10-17; both downloaded source MD5 checks passed and all 12 synthetic tests passed. The real Parquet audit processed 3,862,734 rows and found 19,615 observed cross-partition links. See [verified results](PHASE_03E_VERIFIED_RESULTS.md). The old split remains provisional and is not acceptable for a strict unseen-protein generalization claim.

Once report exists:
1. Verify checksums, query/target mapping coverage and model data source.
2. Examine highest-risk protein/pocket links and partition ambiguity.
3. Decide exact held-out target (unseen protein vs unseen ligand) and whether test groups must be rebuilt.
4. Freeze only after sufficient similarity evidence and licensing restrictions are addressed.
5. Never use reference-dependent similarity to make test-time intervention decisions.

## Run link
https://github.com/sushan5140/sovra/actions/workflows/phase03e-audit.yml

## Scientific source
https://github.com/plinder-org/runs-n-poses
