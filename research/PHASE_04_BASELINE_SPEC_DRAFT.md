# Sovra Phase 04 — Baseline implementation specification (draft)

**STATUS: PRE-HANDOFF DRAFT. DO NOT EXECUTE ON THE PROVISIONAL SPLIT UNTIL PHASE 03 APPROVAL.**
Date: 2026-10-17.

## Scientific objective
Reproduce existing *pose-selection* performance from **licensed, cached Runs N' Poses predictions**, without training new biomolecular models or claiming molecular efficacy. The baseline must be an exact reference for later Sovra FCI-lite comparisons.

## Locked principles
- Evaluate ligand-level cases on a similarity-audited partition. Keep train / validation / test partitions separate.
- Never expose `rmsd`, `lddt_pli`, reference structure geometry, or other ground-truth-dependent columns to a selection policy at test time.
- Report no-score methods separately (e.g., RFAA). Do not replace a missing score with fabricated confidence.
- Treat the archived `rmsd` metric as **the benchmark's BiSyRMSD**, not arbitrary coordinate RMSD, and confirm methodological conventions.
- For each supported method, group by an audited ligand instance and model/run provenance. Respect method-specific seed/sample fields, mappings and score directions.
- Calculate **deployable top-1 success** from a model's chosen prediction separately from **oracle best-of-K success** (upper bound using label only after selection).
- Use the same eligible population for paired comparisons; separately report model coverage and excluded cases rather than quietly dropping unmatched predictions.
- Evaluate subgroup behavior by ligand property, protein/pocket similarity, and repeat-ligand exposure with sufficient sample sizes.
- Prefer group-level uncertainty intervals and prevent tuning on test results.
- Distinguish foundational model zero-shot training cutoff issues from Sovra policy holdout leakage.
- Before reading AlphaFold 3 outputs for downstream ML, review source-specific noncommercial-use and derived-model restrictions; do not push third-party model outputs to public GitHub.

## Expected code deliverables once authorized
1. `scripts/phase04_baselines.py`: pure evaluation pipeline accepting explicit annotations/predictions/manifest paths and method selection.
2. `scripts/phase04_eligibility.py`: reproducible provenance, join and exclusion reason codes.
3. Synthetic fixtures/testing for duplicate/multi-ligand identity, missing scores, score direction, oracle-leak prevention, grouping and deterministic metrics.
4. `reports/phase04_baselines.json`: measured aggregate performance, confidence interval method, independent group counts, source hashes and exclusions; only after approved inputs/terms.
5. Short methodology/limitations document and command-line reproduction instructions.

## Before baseline numbers can be published
- Finalize Phase 03F independent cross-split recheck.
- Document chosen similarity policy, threshold sensitivity, residual leakage and group counts.
- Review output licenses and source labels for each model; select admissible methods.
- Fix RMSD metric semantics, eligible proper-ligand definition and frozen input version.
- Specify top-1 score directions independently for each method.

If these gates fail, do not calculate misleading metrics. Issue a blocking report instead.
