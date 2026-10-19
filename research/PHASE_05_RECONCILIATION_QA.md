# Phase 05 inference-run reconciliation QA

Date: 2026-10-19. Scope: synthetic infrastructure; **no scientific improvement claim**.

## Provenance and implementation scope

Created `feat/phase05-inference-run-reconciliation` from latest main at
`3679d42` (merged Phase 04 reference-blind adapter). Read both complete Phase 05
research documents from `research/phase05-inference-inventory-gate`, commit
`9e851a339b302e7c837b64e7356199614dbfb79e` (PR #3), as explicitly requested.
The implementation branch does not merge the research branch or modify earlier
source evidence. Publisher source links and exact input contract are in the
[runbook](PHASE_05_RECONCILIATION_RUNBOOK.md).

Changed files:

1. `scripts/phase05_inference_run_reconciliation.py`: aggregate-only inventory
   reconciliation, full split validation, strict synthetic provenance and quarantine.
2. `tests/test_phase05_inference_run_reconciliation.py`: 39 synthetic tests and
   reproducible in-memory/CSV fixture generator; no molecular artifact files.
3. `research/PHASE_05_RECONCILIATION_RUNBOOK.md`: execution, contract, counting
   semantics, limits and minimal publisher-side metadata request.
4. `research/PHASE_05_RECONCILIATION_QA.md`: this report.

## Validation results

Local environment: Windows, Python 3.10.11, `pyarrow==21.0.0`.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -v` | **134 passed, 0 failures/errors, 0 skips**; 95 existing + 39 Phase 05 |
| `python -m compileall -q scripts tests` | Passed |
| `git diff --check` | Passed |
| CLI subprocesses with `PYTHONHASHSEED=1` and `17` | Byte-identical complete reports |
| Row-order permutation | Identical diagnostics |
| Reference values scrambled/removed | Identical report except input/provenance hashes; unchanged exit status |
| Reference fields replaced with raise-on-access objects | No access; identical diagnostics |

The existing `.github/workflows/phase04-synthetic.yml` runs the complete suite and
compilation on PR changes under `scripts/**` or `tests/**`, including Phase 05.
No workflow edit, new real-data dispatch or relaxed gate is required. The PR's
checks are the authoritative CI result; local results above are separately verified.

An initial sandboxed run failed only when `os.link` was denied by the Windows
sandbox. Re-running with normal filesystem access passed the actual hard-link
overwrite test; it was neither skipped nor replaced by a mock. The final complete
suite used that access. Tests create only temporary synthetic files.

## QA findings and safeguards

- Summary projection reads only target/seed/sample, method and synthetic-origin
  metadata. It never reads confidence, RMSD, lDDT, reference chains or mappings.
  Reconciliation performs no selection; existing top-1/reference-boundary tests
  also passed. CSV parsing checks syntax, not ignored reference value semantics.
- The fixture has six actual declared IDs despite a nominal 5x5 example; one
  inventory-only ID is reported without a pose-failure label. A wholly empty
  inventory is not reconstructed from summary rows. A structure/confidence-only
  entry remains observed and has a distinct missing-artifact counter.
- Repeated artifact kinds and summary IDs quarantine the known ID on both sides,
  preventing a collision from becoming a false one-sided omission. Invalid rows
  remain explicit. `01`/`1` stay distinct. Unsupported IDs and paths are not repaired.
- Exact full manifest coverage, duplicate JSON keys, shared system/cluster/PDB/
  component leakage, including nonproper systems, are tested before filtering.
  Missing predictions stay in denominators; unknown/outside systems stay in the
  global inventory. Connected group counts are not independence estimates.
- Wrong model/version, AF3 source names, mixed methods, analysis/summary/planned
  provenance, contradictory extra metadata and changed hashes fail closed.
  Non-synthetic rows fail in every CSV. Missing `--synthetic-only`, `--real` and
  scanner options are rejected. Input aliases and actual hard links cannot be
  overwritten. CLI failures emit sanitized reasons, not input identifiers.
- Manifest paths are checked lexically against a narrow synthetic convention;
  no inference directory is scanned and no artifact is opened. File-access guards
  permit only the five declared inputs and source files used for provenance hashes.
- Synthetic declarations and hashes are not an authenticity mechanism. A dishonest
  caller can relabel data; this tool must not be presented as an OS sandbox or
  real-data provenance verifier. The always-blocked real status makes that limit explicit.

## Unresolved scientific and licensing blockers

No blocker prevents this synthetic implementation. Real use remains blocked:

1. No independently authenticated original inference inventory or publisher sidecar.
2. Archived Boltz-1 build, weights and training cutoff are not verified.
3. Explicit rights for source outputs and proposed downstream uses are not cleared.
4. Reference-dependent summary enumeration cannot establish original completeness.
5. Molecular mapping and missing-reference policy require separate review.
6. Cohort/split/group independence and future strict BiSyRMSD `<2` protocol are not
   scientifically frozen or authorized for execution.

The runbook specifies the small publisher metadata request needed to investigate
these gaps. No large archive was downloaded, no real benchmark or model training
was run, and no restricted data was published. Aggregate synthetic agreement is
software validation only; it provides no evidence of molecular accuracy improvement.
