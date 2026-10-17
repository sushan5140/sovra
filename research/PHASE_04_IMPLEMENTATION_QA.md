# Phase 04 implementation QA

Date: 2026-10-18. Scope: synthetic baseline foundation only.

## Implemented

- Single explicit source CSV, filename/version provenance, strict synthetic
  gate, input/code hashes and fixed protocol recorded in deterministic JSON.
- Stable target/ligand cases, proper-ligand annotation, counted quarantine of
  ambiguous mappings, no silent deduplication, explicit missing-score coverage.
- Required score direction, deterministic reference-independent ties,
  separate per-case top-1 and reference-only oracle, missing-label accounting,
  fixed-threshold risk/coverage and separate train/val/test summaries.
- Exact manifest coverage and shared-identity split checks, connected-group
  bootstrap, optional subgroup summaries and paired method intersections.
- A complete synthetic CLI runbook and a synthetic-only CI workflow template.

## Verification

Local environment: Windows, Python 3.10.11, pyarrow 21.0.0 in a local venv.

- `python -m unittest discover -s tests -v`: **54 passed, 0 failed, 0 skipped**
  (18 existing + 36 Phase 04 regression tests).
- `python -m compileall -q scripts tests`: passed.
- `git diff --cached --check`: passed.
- Executed the fixture generation and exact evaluation command from the
  runbook twice: reports were byte-for-byte identical.
- CLI module and direct-script entry points, required arguments, blocked-input
  JSON and input-overwrite protection are covered by subprocess tests.
- Regression checks include reference-label mutation, missing selected labels,
  direction reversal, row permutation, multi-ligand cases, duplicate mappings,
  method coverage, RFAA no-score behavior, invalid splits, whole-group
  resampling, paired intersections, and train/test isolation.

No repository lint or static-typecheck configuration was found. Compilation
is a syntax/import-bytecode check, not a substitute for static type analysis.
The primary code graph backend returned `Transport closed`; implementation
used targeted current-source reads instead. No prior Sovra session memory was
found. These tooling limitations did not block source-based implementation.

GitHub rejected the initial push of `.github/workflows/phase04-synthetic.yml`
because the OAuth credential lacks `workflow` scope. The tested implementation
is delivered with an inert workflow template under `research/` instead.
Activating CI requires authorized workflow access; no GitHub CI pass is claimed.

## Limits and remaining gates

No real benchmark evaluation, training, raw prediction/structure download,
model-weight download, restricted dataset upload, or scientific performance
measurement was performed. No measured Sovra improvement is claimed.

The synthetic `mapping_id` extension requires reference-independent provenance;
it does not resolve archive mapping semantics. Reference-derived mapping
fields cannot disambiguate a deployed prediction. Synthetic provenance flags
are caller assertions, not proof of data origin.

Real execution remains blocked pending exact-source output permissions,
scientific dataset/split freeze, audited similarity components, mapping and
BiSyRMSD conventions, method-specific score definitions/directions, fixed
thresholds/subgroups, and explicit authorization. Connected group counts are
not proof of independent protein families. See the execution runbook for
the complete contract and TODO list.

## Changed files

- `scripts/phase04_eligibility.py`
- `scripts/phase04_baselines.py`
- `tests/test_phase04_baselines.py`
- `research/PHASE_04_EXECUTION_RUNBOOK.md`
- `research/PHASE_04_IMPLEMENTATION_QA.md`
- `research/phase04-synthetic.workflow.yml.example`

All are additions. Existing research, audit scripts, test files and real-data
workflows are unchanged. Generated fixtures/reports and the virtual environment
remain local and are excluded from the feature commit.
