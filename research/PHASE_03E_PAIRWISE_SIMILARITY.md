# Phase 03E — Pairwise similarity audit execution

Date: 2026-10-17
Status: **AUTOMATED AUDIT CONFIGURED; COMPUTED RESULTS NOT YET CONFIRMED**

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

## Current blockers and action
The chat's local container runtime could not open the 376 MB user upload (runtime ClientError). GitHub Actions was configured as a separate reproducible compute option. **Do not claim it executed successfully until a workflow run, tests and artifact are verified.**

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
