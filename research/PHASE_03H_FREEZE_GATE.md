# Phase 03H — Final real-data protocol & freeze decision

Date: 2026-10-18
**Current status: CONDITIONALLY READY FOR A SINGLE-METHOD BASELINE ADAPTER; REAL POSE EVALUATION STILL BLOCKED.**

## Grounded publisher-defined benchmark policy
Source: https://github.com/plinder-org/runs-n-poses (Runs N' Poses README)
and https://polarishub.io/benchmarks/plinder-org/runs-n-poses.

1. The archived `rmsd` column is **BiSyRMSD**, a reference-based evaluation label. The publisher's RMSD success rule is **BiSyRMSD < 2 Å**, not `<= 2`; Phase 04's configurable `<=` is synthetic-only and must be updated or explicitly separated in a later real-baseline adapter.
2. The original Runs N' Poses "zero-shot" study assumes structural training cutoff **30 September 2021**. The benchmark docs explicitly describe a separate **June 2023 Boltz-2 cutoff**. A Sovra graph split among benchmark cases controls Sovra's policy fitting/evaluation, not pretrained model contamination or original zero-shot validity. Never claim zero-shot unseen-protein performance for every method.
3. The README documents model ligand chains (`model_ligand_chain`) and multiple confidence/accuracy fields where chain mappings are chosen depending on RMSD/lDDT metrics. The archive's `ligand_instance_chain` is a reference system ligand. Neither column alone establishes a deployable reference-free **prediction↔target-ligand association**. This remains a **hard adapter gate**, particularly in multi-ligand systems.
4. `ranking_score` is a per-prediction model-specific score, not a universal calibrated probability; higher is better for official Boltz `confidence_score` (see official Boltz prediction documentation), but the Runs N' Poses extraction convention and other model score direction must be checked before approval.
5. The original benchmark includes proper and nonproper ligands; in Sovra's first candidate selection study, use `ligand_is_proper=True` as the primary eligibility criterion as recommended by the dataset authors, keep exclusions auditable.
6. The Phase 03F provisional manifest SHA256 is `48ad536f241cc6f68eb86fa509ec28d6ee4f205f7bba5536c15254081aa8a29b`. It passed *observed ≥80* protein and pocket identity cross-split checks. It is not a demonstrated full protein-family holdout.

## Source-use rights (not legal clearance)
- Boltz-1/2 upstream **code and weights** are MIT-licensed (https://github.com/jwohlwend/boltz); Chai-1 upstream **code and weights** are Apache-2.0 (https://github.com/chaidiscovery/chai-lab).
- Neither automatically establishes all rights to copy or train on separately published third-party benchmark prediction outputs; source terms, attribution and any model-specific limitations must be applied.
- **AF3** output terms (https://github.com/google-deepmind/alphafold3/blob/main/OUTPUT_TERMS_OF_USE.md) explicitly restrict eligible noncommercial research users and prohibit certain similar derived models. Do NOT use AF3-derived scores/structures for Sovra training or public demos absent affirmative permissible-use verification.
- For the first controlled baseline, prefer separately validated Boltz-1 source outputs; do not combine all models into one unqualified "training dataset".

## Existing verified work
- Phase 03F observed-link split feasibility + independent audit: research/PHASE_03F_FEASIBILITY_RESULTS.md.
- Phase 03G source model coverage: research/PHASE_03G_VERIFIED_COVERAGE.md. Boltz-1 has 2,384 potentially evaluable proper ligand cases; Chai has 2,571, before per-split mapping and rights gates.
- Phase 04 synthetic baseline foundation merged PR #1 and CI 54/54. Its `synthetic_only=True` gate MUST remain in effect.

## Phase 03H measurement
- Code: `scripts/phase03h_mapping_readiness.py`.
- Tests: `tests/test_phase03h_mapping_readiness.py`.
- Workflow: `.github/workflows/phase03h-mapping.yml` verifies publisher hashes, rebuilds exactly the previously audited manifest, inventories reference-free candidate mapping identifiers and computes proper case eligibility by train/val/test and the Boltz/Chai intersection **without pose success computation**.
- Raw predictions/third-party coordinates are not committed to this public GitHub repo; only aggregate summaries, scripts and test fixtures are permitted.

## Freeze acceptance checklist
- [x] Dataset provenance and exact pinned hashes.
- [x] Candidate graph split with zero *observed ≥80* cross-partition protein and pocket identity links.
- [x] Synthetic baseline framework merged and CI tested.
- [ ] Independent evidence that the archived prediction-to-reference ligand association can be constructed with **no evaluation reference**.
- [ ] Per-method source rights clearance for the precise intended evaluation/training usage.
- [ ] Model-specific `ranking_score` extraction semantics and direction verified in source code.
- [ ] Freeze published RMSD strict inequality and mapping conventions in a real-data adapter; do not retrofit frozen synthetic tests silently.
- [ ] Approve method-specific evaluation population, properly handle multi-ligand cases, and document independence/coverage limits.
- [ ] Lock threshold and uncertainty procedure before held-out outcomes.

**Decision:** Keep the dataset split provisional and Phase 04 real-data scoring BLOCKED until the unchecked gates are evidenced. Do not relabel real predictions as `synthetic` or weaken the safety checks.
