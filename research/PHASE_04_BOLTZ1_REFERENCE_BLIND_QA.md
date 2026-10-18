# Boltz-1 reference-blind adapter QA

Date: 2026-10-18. Handoff: `CODEX_02_REFERENCE_BLIND_ADAPTER.md`.
Base: main `9dadb134ae1d94e73f05a7f92fd35f27a5b9e4de`.
Branch: `feat/boltz1-reference-blind-adapter`.

## Outcome

Synthetic preflight implementation passes. Real preflight and real molecular
evaluation remain explicitly blocked. The change adds a reference-blind
prediction index, aggregate adapter, separate synthetic post-decision
association helper, adversarial tests, runbook and this QA record.

All existing audit/baseline source, tests, workflows and historical Phase
03/04 reports remain unchanged. The existing synthetic-only baseline and
its toy `<=` convention are preserved. The proposed real BiSyRMSD `< 2 Å`
protocol is disabled metadata only; no real evaluator is implemented.

## Validation performed

Local: Windows, Python 3.10.11, pyarrow 21.0.0 in the repository virtualenv.

- `python -m unittest discover -s tests -v`: **95 passed, 0 failed, 0 skipped**
  (60 existing and 35 new adapter tests).
- `python -m compileall -q scripts tests`: passed.
- Executed the runbook's fixture generator and exact CLI command twice;
  aggregate JSON reports were byte-for-byte identical.
- Module and direct-script CLIs, malformed provenance, input hashes,
  source/model mismatch, error redaction, overwrite protection, and forbidden
  threshold overrides are covered by subprocess/integration tests.
- No configured repository lint/static-typecheck command was identified;
  compilation is not claimed as static type analysis.

The primary code graph service returned `Transport closed`, and the compact
memory search returned no matching observations. Current source and exact
upstream code were inspected directly. No raw archive was downloaded.

## Adversarial boundary checks

1. Prediction runs contain only target, seed, sample and finite score.
   Immutable/slotted exact types reject reference-bearing raw dictionaries
   and subclasses. Ranking has no reference or annotation parameter.
2. Poisoned forbidden values and suffix mappings are never accessed during
   projection/ranking. Mutating or removing reference columns and annotation
   ligand-chain values leaves the index, ordering and exclusion counts intact.
   Input-byte hashes change as expected when input bytes change.
3. A fresh Python process imports only the selection module and ranks with
   file access disabled; neither adapter nor reference module is imported.
4. Duplicate identities are detected before score filtering and quarantine
   the whole target, even when one colliding row is unscored or has different
   reference-derived chains. Missing run IDs also quarantine the target.
5. One proper ligand among multiple total ligand chains is excluded; repeated
   annotation systems are excluded without using reference chains to deduplicate.
6. Changing train scores/references cannot alter test ordering or the fixed
   protocol. Shared system/cluster/PDB/component identities cannot cross splits.
   No data-dependent cutoff selection exists.
7. The evaluation-reference helper takes finalized decisions. Missing selected
   references do not trigger fallback, mapped chains do not choose the reference,
   and no success calculation occurs. Real access is rejected before file I/O.
8. Aggregate reports and blocked CLI errors expose no identified cases, raw
   scores, reference values or selected runs.

This proves the tested software API/data boundary, not isolation from malicious
arbitrary Python introspection, and not the scientific validity of the archive.

## Source-audit finding: real execution BLOCKED

The actual publisher `process_boltz_file` and `merge_to_final_df` code was
read at notebook commit `197fafc60a5cef3a9e7f8a4b0dac7c965eed3839`.
The official Boltz writer was read at
`b1ebfc46ecf57f5414e0d1a6f9027bbb122c53bc`. Immutable links, file SHA256s,
function-level findings, and reproduction instructions are in
`PHASE_04_BOLTZ1_REFERENCE_BLIND_RUNBOOK.md`.

Per-run confidence is inference-derived and the writer orders higher values
first. However, the notebook enumerates analysis files and discards runs when
reference-based RMSD/lDDT assignment lists are absent or empty. Later merges
use reference ligand assignments and remove duplicate rows. Projecting four
columns from that summary cannot recover a complete reference-independent
candidate universe. Strict singletons remove the choice between reference
ligands after selection, but do not prove original molecular mapping or run
completeness. The adapter reports these unresolved gates rather than treating
the historical strict-cohort counts as proof.

Remaining gates: exact archive-output rights for the intended use, independent
inference-run inventory and molecular mapping proof, archived Boltz release/
weights/training-cutoff provenance, scientific cohort/split/group freeze,
reviewed strict real metric policy, and explicit execution authorization.
The 190 historical paired ligand cases are neither the final scientific sample
size nor 190 independent protein families.

No real-data aggregate preflight, accuracy benchmark, model training, AF3 output
consumption, restricted data upload, molecular-coordinate download or large
prediction archive download was performed. No scientific improvement is claimed.

## New files

- `scripts/phase04_prediction_index.py`
- `scripts/phase04_boltz1_adapter.py`
- `scripts/phase04_evaluation_reference.py`
- `tests/test_phase04_boltz1_adapter.py`
- `research/PHASE_04_BOLTZ1_REFERENCE_BLIND_RUNBOOK.md`
- `research/PHASE_04_BOLTZ1_REFERENCE_BLIND_QA.md`

Generated fixture files, source-inspection scratch files and reports stay local
outside the feature commit. Existing synthetic CI will discover the new tests;
real-data workflows are not dispatched by this task.
