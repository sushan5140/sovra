# Phase 03I — Conservative single-ligand cohort: verified real-data result

Date: 2026-10-18 UTC
**Status: FEASIBLE NARROW SUBSET; NO SCIENTIFIC FREEZE OR POSE-EVALUATION AUTHORIZATION**

## Independent execution
- Official pinned Runs N' Poses Zenodo v4 source data; publisher MD5 checks for all 3 inputs passed.
- Candidate manifest SHA256 matched `48ad536f241cc6f68eb86fa509ec28d6ee4f205f7bba5536c15254081aa8a29b`.
- GitHub Actions: https://github.com/sushan5140/sovra/actions/runs/39102756407
- **60/60 regression tests passed**, Python compilation passed.
- Code: `scripts/phase03i_single_ligand_preflight.py`; tests: `tests/test_phase03i_single_ligand_preflight.py`.
- Workflow artifact `phase03i-single-ligand-aggregate` holds only aggregate JSON, not any raw model data or structures.

## Why the restriction
The publishers' `extract_scores.ipynb` merges RMSD and lDDT-PLI assignments and then maps the results to reference ligand identities. The Phase 03H audit established that **no unsuffixed `model_ligand_chain` is available in any archived CSV**, and many case/seed/sample keys collide in broader multi-ligand cases. We cannot safely treat reference-derived mapped rows as separate inference-time poses.

This follow-up counts only cases meeting *all* of:
- Reference annotations indicate `ligand_is_proper=true`.
- **One total ligand chain** (`num_ligand_chains == 1`) and **one annotation row per system**. Using merely one proper ligand is insufficient.
- All included archived candidate rows for the case have unique, nonempty `seed` and `sample` values, avoiding the measured repeated-key ambiguity.
- The source table exposes a finite `ranking_score`; cases where every scored row has a finite reference label are reported **separately**, not automatically authorized for inclusion/exclusion.

## Measured single-ligand population

| Population | Train | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| All proper ligand annotation cases (Phase 03H) | 2,109 | 460 | 457 | 3,026 |
| **Strict proper single-ligand cases** | **926** | **267** | **233** | **1,426** |
| Strict scored/unique-run Boltz-1 `boltz.csv` cases with complete reference | **849** | **239** | **193** | **1,281** |
| Strict scored/unique-run Chai `chai.csv` cases with complete reference | **882** | **248** | **206** | **1,336** |
| **Paired Boltz-1/Chai strict case intersection** | **846** | **239** | **190** | **1,275** |

In the observed strict cohort, all Boltz-1 and Chai cases with source predictions had unique run keys, finite scores and complete reference labels. **This still does NOT guarantee the original output-to-ligand join or molecular pose structure identity is reference independent.**

The first hypothetical *narrow* held-out test has **at most 190 paired ligand cases**. This is **not 190 independent protein families**. Require component-level effective sample and uncertainty checks before deciding whether an experiment can support a meaningful claim.

## Key unresolved requirements
1. The publisher's extraction notebook gives per-run source `ranking_score` provenance (Boltz: `confidence_score`; Chai: `aggregate_score[0]`). Boltz confidence is officially high-is-better. Do not assume Chai scores share a scale or that either was calibrated for ligand-pose correctness.
2. The benchmark uses **strict BiSyRMSD < 2 Å**. The Phase 04 synthetic runner uses `<=` for toy fixtures only. Before real evaluation, create a separate, reviewed metric policy rather than changing past tests silently.
3. The sample identities and the singleton reference association must be independently traced back to *inference outputs* (not the reference-matched `assigned_scores`).
4. Explicit source-output usage rights for the proposed independent research need clearance; AF3 output restrictions still prohibit its unqualified use for a downstream structure-related policy.
5. Phase 03F's observed-link graph split is provisional; foundation-model memorization and incomplete similarity graph coverage remain.
6. Predeclare grouping/CI, subgroup criteria and success threshold before unsealing the untouched test labels. Do not select a cohort *based on model success labels*.

## Recommendation
Continue with a **Boltz-1-first, single-ligand, unique-run adapter** as the initial scientific-method implementation task. Keep it strict, reference-blind and **preflight-only** (no accuracy or learned policy) until missing gates are satisfied. Add Chai only as an independent per-method comparator on the intersection after its own provenance checks. Do not request/download the 38GB raw prediction archive unless this smaller cohort proves insufficient.

**No actual pose-success measurements or FCI improvements were computed.**
