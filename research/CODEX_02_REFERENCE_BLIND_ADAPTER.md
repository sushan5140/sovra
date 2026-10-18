# CODEX 02 — Boltz-1 reference-blind real-data adapter (preflight only)
Date: 2026-10-18
**Do not run real RMSD/accuracy evaluation or fit downstream ML policies.**
Repo: `sushan5140/sovra`, branch from latest main and open a PR.

## Before coding read these exact repo files
1. `research/PHASE_03H_PUBLISHER_MAPPING_AUDIT.md`
2. `research/PHASE_03H_VERIFIED_MAPPING_COVERAGE.md`
3. `research/PHASE_03I_VERIFIED_SINGLE_LIGAND_COHORT.md`
4. `research/PHASE_03F_FEASIBILITY_RESULTS.md`
5. `research/PHASE_03G_RIGHTS_AND_USAGE_GATE.md`
6. `scripts/phase04_baselines.py`, `scripts/phase04_eligibility.py`

Publisher extraction notebook (must verify actual logic, not assume README alone):
https://github.com/plinder-org/runs-n-poses/blob/main/extract_scores.ipynb

## Objective
Build the separately reviewed *preflight* bridge between pinned archive provenance and the synthetic Phase 04 infrastructure. **Use test fixtures and optional aggregate-only checks, not unapproved real model evaluation.**

## Scope
- One source only: `boltz.csv` from pinned Runs N' Poses v4, with method version/filename retained and `ranking_score` traceable to Boltz `confidence_score`. Official Boltz writer sorts high confidence first.
- Strict cohort: source `ligand_is_proper=True`, exactly one `num_ligand_chains` per annotated system, exactly one annotation row for that system, and unique nonempty `(target,seed,sample)` model run ID. Any duplicate/missing run is **quarantined**, with reason counts; multi-ligand cases remain out of scope.
- Select only from inference-available input `(target,seed,sample,ranking_score)`. `ligand_instance_chain`, `target_ligand_chain_*`, `model_ligand_chain_rmsd`, `model_ligand_chain_lddt_pli`, `rmsd`, `lddt_pli`, `*_rmsd` and `*_lddt_pli` are all evaluation/reference-derived or unproven: **none may influence ranking, run identity, tie breaks, exclusion decisions based on prediction difficulty, or downstream trained policy features**.
- For singleton cases, document explicitly why joining a preselected run with the lone proper reference ligand is a *post-decision evaluation association*, not a pose-selection operation. If this cannot be demonstrated from source, **BLOCK**.
- Keep `prediction_index` (without labels) separate from an inaccessible `evaluation_reference` mapping. The current `scripts/phase04_baselines.py` must remain `synthetic_only` — do not trick the provenance flag.
- Use publisher's **strict BiSyRMSD < 2 Å** in a clearly separate, disabled future real protocol; do not change toy `<=` behavior without review.
- Preserve class/split group identifier, SHA256 input provenance and all source versions. Do not treat 190 paired strict cases as independent protein families or as the final scientific sample size.
- The new adapter must **not** compute any real success rate, inspect the held-out labels to tune anything, train any model, consume AF3 output, or upload raw archives/molecular coordinates. Do not pull the ~38 GB raw prediction-files archive by default.
- Add deterministic synthetic adversarial tests: test/reference label permutation must not alter predicted ordering or identity; missing scores/seed/sample; duplicate run; one proper among multiple total ligands **excluded**; model provenance mismatch; reference mapping suffix names; train-test isolation and no data-dependent threshold selection.
- On the actual pinned data, only a read-only **aggregate preflight** may be run if rights/provenance checks permit: schema presence, count of strict single-ligand and score/run availability per split, pass/block status. Do not emit identified per-case rows or raw data artifacts.
- Provide a reproducible runbook, permissions checklist, and explicit list of gates still required before first real baseline.

## Acceptance
1. Synthetic full suite passes, no skips.
2. PR with code, tests and preflight-only QA; no merged real experiment without explicit approval.
3. Independent reviewer can verify that reference-dependent assignments in the publisher notebook are never used to select or identify a candidate inference run.
4. Real-data Phase 04 execution remains disabled.
5. The repo main historical Phase 03/04 reports remain unchanged.

## Real-data science still gated
Archive-output usage terms, training-cutoff contamination, experiment-specific group independence, score protocol, and reference-free mapping proof. Avoid optimizing threshold/cohort using outcome labels.
