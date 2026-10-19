# CODEX 03 — Independent inference-run inventory reconciliation

Repository: `sushan5140/sovra`
Task: implement **Phase 05 synthetic-only infrastructure**, on a new feature branch from latest main after this research-only PR is reviewed and merged.
Recommended coding effort: **High**, with independent scientific audit at **Extra High** if available.
Status: **IMPLEMENTATION PROPOSAL. No real pose scoring authorized.**

## Read first
- `research/PHASE_05_SOURCE_RUN_INVENTORY_AUDIT.md` — evidence, limits, hypotheses.
- `research/PHASE_03H_PUBLISHER_MAPPING_AUDIT.md`, `research/PHASE_03I_VERIFIED_SINGLE_LIGAND_COHORT.md`.
- `scripts/phase04_prediction_index.py`, `scripts/phase04_boltz1_adapter.py`, `scripts/phase04_evaluation_reference.py`.
- Publisher [`extract_scores.ipynb` at pinned commit](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb), [example run](https://github.com/plinder-org/runs-n-poses/blob/main/examples/utils/run_boltz.sh), [analysis command](https://github.com/plinder-org/runs-n-poses/blob/main/examples/utils/analyze_models_boltz.sh).

## Specific objective

Build a **reference-independent source inventory comparison tool** that can, given a separately acquired trusted list of actual model inference artifacts, detect which original `(target,seed,sample)` runs were omitted in the downstream benchmark CSV and report aggregate counts. This is a detector for upstream filtering, **not** a pose-quality model and **not** proof the input inventory is genuine.

### Inputs (synthetic fixtures for now)

1. `inference_inventory.csv`: canonical `target,seed,sample,artifact_kind,artifact_path,data_origin` derived exclusively from inference-created files. Valid `artifact_kind` is one of `confidence_json`, `model_cif`. Keep the complete raw string IDs, no numeric sorting or renumbering. Distinguish missing artifact from an unreported file; accept independent confidence and structure lists.
2. `published_summary.csv`: exactly one synthetic table shaped like `boltz.csv`, potentially with adversarial `rmsd`, `lddt_pli`, `model_ligand_chain_rmsd`, `ligand_instance_chain`, etc. Project **only `target,seed,sample` and non-reference source label** for reconciliation. These reference fields must never affect matching, counts, candidate identity or process exit.
3. `annotations.csv` and exact, externally supplied `manifest.json`: for partition/group membership. Keep grouping independent of poses, validate entire manifest and split identities before any proper/strict-cohort filter.
4. `inventory_provenance.json`: exact allowed `Boltz-1` version/source, dataset version `v4`, inventory generation method, annotation/summary/inventory file hashes, and a flag that input is synthetic. **Do not assert that a caller-supplied string establishes real-world independence**. Real-input mode is absent.

### Required audit outputs

- Unique observed inference run IDs with `both_artifacts`, `confidence_only`, `structure_only`. Count missing artifact types distinctly.
- `inference_only` vs `summary_only` vs `intersecting` IDs, and `duplicate_inference_ids`/`duplicate_summary_ids`. Do not silently deduplicate collisions. Report count of quarantined IDs/rows and blocked reasons.
- Counters by `train, val, test`, plus `unknown/outside_cohort`. Include annotation groups and connected groups, and keep missing predictions in denominators.
- `planned_runs` is **not** derivable from an example script alone; if displayed at all, require an explicitly separate planned-run manifest, labeled `planned_not_observed` and never use it as actual coverage denominator.
- Only aggregate JSON and SHA256 provenance. No target strings, per-run IDs, paths, confidence values, reference values or molecular structures in output logs/artifacts. No metric or success-rate calculations.
- Explicit `REAL_RECONCILIATION_BLOCKED` for absent independent source inventory, ambiguous model/version provenance, uncertain rights, or source files derived from analysis/evaluation.
- Incomplete reference labels must **not** affect membership or top-1 selection. The tool must make no real-data decision about missing-reference failure/success.

### Security and scientific regression tests

- Poison all reference-only columns with values/objects that raise on access; re-permute/scramble reference labels; aggregate report and matching must not change (except hashes of changed input bytes).
- Remove reference columns entirely; reconciliation remains identical.
- Missing, padded, malformed, duplicated IDs; differences between numeric-like identifiers `"01"` vs `"1"`; malformed CSV headers; duplicate manifest keys; cross-partition shared component/PDB/group identity.
- Conflicting confidence/structure artifact filenames; contradictory provenance; archive source `af3.csv` or wrong model; path traversal/unapproved paths when scanning directories. No inference directory scanner until the true publisher naming contract is verified and allowed.
- Fail closed on `data_origin != synthetic`; no way to pass an unreviewed real archive under a newly added `--real` flag.
- Tests explicitly demonstrate that 25 nominal seeds/samples do not establish 25 observed runs, and that a run missing only from the evaluated summary is *not* an unsuccessful model pose.
- Byte-identical reports for repeated synthetic fixtures; run full repo tests with zero skips, compile checks and CI. Open a PR; do not merge or run real-data evaluation.

### Deliverables

One source module, synthetic tests, a runbook, QA and (if safe) an inert synthetic-only workflow template or extension of existing synthetic CI. Do not modify previous Phase 03/04 source evidence or real-data gates.

### Stop/go

If independent source inventory cannot be obtained from original inference artifacts or an authenticated publisher sidecar, **do not improvise one from `predictions.tar.gz`, OpenStructure JSON, `rmsd` coverage or the 5×5 example loop**. Report BLOCKED and propose the minimally necessary publisher metadata request.

No internet download of `prediction_files.tar.gz` (~38.2 GB), no model training, and no benchmark accuracy calculation unless separately authorized after rights and source validation.
