# Phase 03G — Verified model coverage and eligibility
Date: 2026-10-17 UTC
Status: **MEASURED COVERAGE AUDIT COMPLETE — SCIENTIFIC DATASET FREEZE STILL CONDITIONAL**

## Reproducibility
Source dataset: Runs N' Poses Zenodo [record 16754298 v4](https://zenodo.org/records/16754298).
Actual GitHub Actions run: https://github.com/sushan5140/sovra/actions/runs/38998564649
Run: **SUCCESS**, all **18/18 synthetic regression tests passed**.
Zenodo MD5 verified for annotations.csv, predictions.tar.gz and all_similarity_scores.parquet.
Candidate split JSON regenerated, matching frozen-in-repo expected SHA256: `48ad536f241cc6f68eb86fa509ec28d6ee4f205f7bba5536c15254081aa8a29b`.

Audit source: `scripts/phase03g_coverage.py`, tests: `tests/test_phase03g_coverage.py`.
Real-data report: workflow artifact `phase03g-aggregate-only` (14-day retention); no raw model outputs pushed.

## Case coverage: actual calculated results

Annotation inputs: **4,235 ligand cases**, of which **3,026 are marked proper ligands** by the source.
Candidate group partition: train 2,965; validation 635; test 635 **before method-specific eligibility filtering**.

| Prediction source | Proper ligand cases with predictions | Distinct cases with finite ranking score AND finite reference RMSD | Matched proper prediction rows with both |
| --- | ---: | ---: | ---: |
| af3.csv | 2,709 | 2,709 | 68,577 |
| af3_no_template.csv | 2,710 | 2,710 | 68,591 |
| boltz.csv | **2,384** | **2,384** | **57,120** |
| boltz1x.csv | 2,332 | 2,332 | 57,597 |
| boltz2.csv | 933 | 933 | 23,412 |
| chai.csv | **2,571** | **2,571** | **65,079** |
| protenix.csv | 2,607 | 2,607 | 66,322 |
| rfaa.csv | 1,945 | **0** | **0** |

**Interpretation:**
- These are **coverage counts**, not model accuracy or legal authorization for policy training.
- Source filename is the model identity; several different Boltz files contain a generic `method=boltz` column.
- RFAA has no `ranking_score` in its table. Its 1,945 proper cases **must not be labeled model failures** or assigned fake scores.
- Source proper-ligand filtering excludes ions/artifacts for the main *potential* benchmark, while retaining all rows in archives. All exclusion counts remain reviewable.
- Many rows belong to repeated seeds/samples for a **single case**. Never use 57,120 or 65,079 as independent test sample counts.
- The existence of a finite reference metric is checked only to establish potential evaluability. **Reference RMSD must never be fed to a test-time selection policy.**
- The source calls its column `rmsd` **BiSyRMSD**, requiring agreed success threshold and atom-mapping conventions before accuracy measurements.

## Decision for the first implementation
First evaluate **one independently cleared open-model source at a time**; Boltz (2,384 eligible cases) and Chai (2,571) have meaningful apparent coverage. A paired model comparison must use the **intersection of eligible ligand cases** and separate method-specific score calibrations/directions, not the union. Score-based baselines require explicit rank direction and exact ties/mapping rules.

## Still blocking scientific freeze / training
1. Model-output licenses: AlphaFold 3 restricted; preserve terms and cite paper; do not use its outputs to train Sovra without validated permission. Boltz/Chai upstream code/weight licenses are permissive but archive-specific output provenance and acceptable downstream use still need confirmation. See `PHASE_03G_RIGHTS_AND_USAGE_GATE.md`.
2. Individual model/ligand coverage in train/val/test to be reviewed from full aggregate workflow artifact, not inferred from the 70/15/15 all-case candidate split.
3. Case identity: distinct `seed`/`sample` mapping, alignment, multi-ligand pose duplicates and missingness need explicit evaluation protocol.
4. Split independence: observed protein/pocket links ≥80 were eliminated (Phase 03F) but unobserved relationships and foundation-model training overlap are not ruled out.
5. No train/test baseline accuracy, oracle recovery, calibrated abstention or FCI improvement is reported. Maintain the untouched test split.

### Exact next decision
Define **per-method eligible intersection**, model-appropriate score-direction baselines, and license-cleared Phase 04 reproducibility requirements. Codex implementation handoff should be a fixed-scope baseline pipeline, not a full research agent or application.
