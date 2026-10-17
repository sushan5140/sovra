# Codex Handoff 01 — Phase 04 Baseline Foundation (implementation only)
Date: 2026-10-17
**Mode:** Build/test on synthetic fixtures only. Real dataset freeze and output permissions are not complete.

## Work order for Codex
Repository: `sushan5140/sovra`.
Create a new feature branch and open a PR against main when tested; do not force-push or replace existing research files.

Read in order:
- `research/PHASE_03F_FEASIBILITY_RESULTS.md`
- `research/PHASE_03G_VERIFIED_COVERAGE.md`
- `research/PHASE_03G_RIGHTS_AND_USAGE_GATE.md`
- `research/PHASE_04_BASELINE_SPEC_DRAFT.md`
- `scripts/audit_dataset.py` and `scripts/phase03g_coverage.py`

### Objective
Implement a **reproducible, leakage-safe ligand pose selection baseline framework** that accepts one explicit, permission-cleared method CSV at a time and a separately provided, validated split manifest.

### Files to build
- `scripts/phase04_eligibility.py`: stable case identity `(target/system_id, ligand_instance_chain)`, annotate proper ligands, source-filename model version, explicit exclusion reason codes; never silently deduplicate multiple legitimate mappings.
- `scripts/phase04_baselines.py`: method-specific baseline selection based on an **explicit required score-direction argument**, deterministic ties, missing/nonfinite score handling, per-case top-1 accuracy, reference-only oracle best-of-K upper bound and risk-vs-coverage summaries.
- `tests/test_phase04_baselines.py`: synthetic-only fixtures and regression tests for leakage, multi-ligand targets, missing scores, absent ground truth, method coverage, RFAA no-score behavior, duplicate mapping provenance, valid/invalid splits, reversed score direction, deterministic ties, group-level resampling. Don't assume RMSD is a model feature.
- `research/PHASE_04_EXECUTION_RUNBOOK.md`: commands, expected input schema, model-specific caveats, no raw model results.

### Guardrails
1. **No training or use of AlphaFold 3 outputs in a downstream predictive model.** Its terms require specific permissible noncommercial uses and prohibit certain derived models. Don't assume user is institution-affiliated.
2. Do not download or commit raw predictions, experimental structures, or new large model weights.
3. No real dataset accuracy computations while the Phase 03 freeze, output rights and score definitions are unresolved.
4. The source `rmsd` is BiSyRMSD. Use it **only after** the deterministic decision has already been made from score/metadata, strictly as held-out evaluation.
5. Separate pose selection (top-1) from oracle (best-of-K); **never** use reference RMSD to pick the deployed answer.
6. A failed score-mapping or ambiguous row identity must produce an explicit exclusion/quarantine and a count, not a silent drop.
7. Train/validation/test boundaries are immutable; never tune score thresholds on test.
8. Abstention must report both error and coverage; abstaining on 100% of cases is not a scientific win.
9. A sample row is not an independent protein case. Report distinct group counts and paired comparisons where possible.
10. Document the score direction separately per model; don't assume ranking_score across methods shares scale.
11. The suite must run with `python -m unittest discover -s tests -v` and pass all existing tests.

### Definition of done
Open a feature PR with (a) implementation, (b) passing synthetic tests, (c) complete command/runbook, (d) explicit TODO items blocked by data licensing/freeze, and (e) a brief implementation QA report. **Do not claim any measured Sovra research improvement.**

Only after review and confirmation of legal/scientific prerequisites should the real Phase 04 evaluation be authorized.
