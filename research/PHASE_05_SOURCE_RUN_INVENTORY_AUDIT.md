# Phase 05 — Original inference-run completeness audit

Status: **SOURCE EVIDENCE AUDITED; ORIGINAL RUN INVENTORY NOT RECOVERED; REAL POSE EVALUATION BLOCKED.**
Date: 2026-10-19. Scope: Boltz-1 from pinned Runs N' Poses **v4**; no training, accuracy evaluation, or release of molecular files.

## Question

Before evaluating confidence-based pose selection, can we identify **every inference-produced** `(target, seed, sample)` Boltz-1 output *without* looking at ground-truth RMSD, lDDT-PLI, ligand assignments, or the rows retained by the benchmark accuracy script?

A defensible selection denominator must start from inference outputs. The published `boltz.csv` by itself cannot certify this denominator.

## Primary-source evidence inspected

1. [Publisher extraction notebook, pinned](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb): `process_boltz_file` parses `target,seed,sample` from an **analysis** JSON basename, reads `confidence_input_model_{sample}.json` from the inference output tree and obtains `ranking_score` from `confidence_score`. It returns empty lists if either RMSD or lDDT-PLI `assigned_scores` is empty/missing. The downstream merge relies on model/reference ligand associations and reference annotations, then drops duplicate rows. Thus selection from the exported table alone is vulnerable to *upstream reference-availability selection bias* even if Sovra's selector is label-blind.
2. [Publisher Boltz example run script](https://github.com/plinder-org/runs-n-poses/blob/main/examples/utils/run_boltz.sh): loops over **five seeds** and requests **five diffusion samples** per call. This describes the sample *plan/example*, **not an observed inventory** or proof that all 25 predictions per target completed.
3. [Publisher Boltz analysis script](https://github.com/plinder-org/runs-n-poses/blob/main/examples/utils/analyze_models_boltz.sh): finds `input_model_*.cif` predictions and runs OpenStructure `compare-ligand-structures` against reference SDF/CIF, writing per-output **analysis** JSON. The analysis output list is downstream of inference, not itself an independent inference run list.
4. [Official Boltz output documentation](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md): predicted structure `input_model_{sample}.cif` and `confidence_input_model_{sample}.json` files are outputs made *before* evaluating against reference; the latter contains `confidence_score` (higher confidence is better). The exact archived Boltz build/weights still require independent pinning.
5. [Pinned Zenodo v4](https://zenodo.org/records/16754298) publishes `prediction_files.tar.gz` **38.2 GB** (MD5 `cdca8645f3a28317643be7de13f02145`) and `predictions.tar.gz` **48.4 MB** (MD5 `58648b836ff9434bc929b7fad25cd9bb`). The smaller one is *post-analysis* CSV tables, not a trustworthy complete run list.
6. [Zenodo v6, Jan 2026](https://zenodo.org/records/18366081) describes revisions to PoseBusters checks and missing **AF3** prediction files only; it retains the v4 checksum for `predictions.tar.gz` and `annotations.csv`. This is **not** evidence that Boltz-1 missing-run coverage was repaired. No automatic version upgrade.
7. Previous Sovra audits: `research/PHASE_03H_PUBLISHER_MAPPING_AUDIT.md`, `research/PHASE_03I_VERIFIED_SINGLE_LIGAND_COHORT.md`, and merged [PR #2](https://github.com/sushan5140/sovra/pull/2) (95 passing tests). The 190 paired Boltz/Chai strict test cases are only **post-analysis potentially evaluable cases**, not a sealed scientific holdout.

## What is actually established?

| Evidence | Supports | Does **not** establish |
| --- | --- | --- |
| Nominal 5 seeds × 5 samples run example | Intended experiment pattern for an example target | All 25 actually completed for every target |
| v4 Boltz `predictions.tar.gz` table | Count of evaluated/exported rows by target/run | Completeness of inference results |
| Confidence file from the model output tree | Inference-produced identity and model confidence, if authenticated | Ground truth, success, archive-output redistribution permission |
| OpenStructure analysis JSON | Correspondence to *scored* reference evaluations | Prediction-only candidate enumeration |
| Synthetic Boltz-1 adapter PR #2 | Software ranking cannot read reference metrics | Independence of archive construction or correctness of original pose mapping |
| v6 Zenodo metadata | Recorded changes in a newer release | Recovery of a missing Boltz-1 confidence manifest |

## Least-cost route to close the proof gap

**First choice:** locate or request a tiny independent *per-file inventory* from the dataset authors, built from the original **Boltz-1 inference output directory** (`confidence_input_model_*.json` and ideally matching `input_model_*.cif` names). Need no coordinates, confidence values, reference labels or raw structures in that manifest.

For each file, collect: `dataset_version`, exact source model/weights, `target`, `seed`, `sample`, inference artifact type, and relative path or immutable checksum, plus how missing/failed runs were recorded. The authors should confirm whether any inference results were deleted, re-ranked/renumbered, filtered, or withheld before deposition. Store the inventory with permission, and publish at most approved aggregates/hashes.

**Second choice:** independently enumerate the archived inference file list if access/rights are cleared, preferably from a publisher-provided sidecar `tar -tzf` output or an authenticated manifest. Do not download the 38.2 GB compressed blob just for a listing without a justified plan. A gzip-compressed tar is not generically random-access by HTTP range; remote byte-range capability alone is not a substitute for a tar listing.

**Fallback:** construct fresh *new* inference outputs with an explicitly specified Boltz release on a separately authorized small cohort. These are a different experiment and **cannot be presented as recovery of the original benchmark runs**. Computational feasibility and output rights must be checked first.

## Gates for a future reconciliation tool

- `source_inventory` must originate *before* reference-based accuracy analysis; its creation procedure and hash must be independently auditable. Never generate it from `boltz.csv` or the analysis file list.
- Compare `(target,seed,sample)` keys against the published summary **only as a diagnostic**: `in_both`, `source_only`, `summary_only`, duplicate IDs, missing score/structure, failures, and any unmatched/unreadable output. Preserve all source entries; never silently collapse sample identity.
- Classify missing source confidence vs missing structure vs missing OpenStructure analysis distinctly. Missing evaluation is **unknown**, not a failed pose or safe reason to remove a candidate from the selection population.
- Report **aggregate** counts by fixed train/val/test and confirmed independent components; no identified molecular rows, raw values or structures in PRs or logs.
- Never let the publisher's RMSD/lDDT assignment, reference chain, proper label or assessed outcome decide whether an **inference candidate** is present.
- Separate **planned runs** from **observed inference files**, and both from **published evaluation rows**.
- The comparison may quantify unknown coverage; it cannot supply labels for source-only runs automatically. A future evaluable population and missing-label estimand must be specified in advance.
- Source-output rights, experiment's permitted use, exact Boltz build/weights/cutoff, strict BiSyRMSD < 2 Å policy, and split/family independence remain independent freeze gates.

## Decision

**NO-GO for real accuracy evaluation** and no benchmark superiority claim.

**GO for a narrow, synthetic-only Phase 05 reconciliation-tool implementation and request for original inference metadata.** It would be misleading to multiply the 190 post-filtered cases by 25 or regard the score table as complete merely because the script requested 25 predictions.
