# Sovra Phase 03H — Verified Mapping & Paired-Coverage Findings

Audit performed: 2026-10-18, GitHub Actions https://github.com/sushan5140/sovra/actions/runs/39102253916
Status: **READ-ONLY AUDIT COMPLETE; UNAMBIGUOUS REAL POSE SELECTION NOT YET ESTABLISHED.**

Publisher MD5 matched for annotations.csv, all_similarity_scores.parquet and predictions.tar.gz. The regenerated candidate split SHA256 matched `48ad536f241cc6f68eb86fa509ec28d6ee4f205f7bba5536c15254081aa8a29b`. **57/57 automated regression tests passed** with no skips in the workflow, and Python compilation passed.

## Eligible annotation population

| Split | `ligand_is_proper=true` annotation cases |
| --- | ---: |
| Train | 2,109 |
| Validation | 460 |
| Test | 457 |
| **Total** | **3,026** |

## Per-model coverage (proper cases with at least one finite score AND finite reference label)

| Method source | Train | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| boltz.csv | 1,645 | 371 | 368 | 2,384 |
| boltz1x.csv | 1,619 | 354 | 359 | 2,332 |
| boltz2.csv | 651 | 168 | 114 | 933 |
| chai.csv | 1,769 | 406 | 396 | 2,571 |
| protenix.csv | 1,789 | 414 | 404 | 2,607 |
| af3.csv | 1,836 | 439 | 434 | 2,709 |
| af3_no_template.csv | 1,837 | 439 | 434 | 2,710 |
| rfaa.csv | 0 | 0 | 0 | 0 |

RFAA's zero count here is **score incompatibility, not model failure**; it has proper predictions but no comparable ranking score.

## Method pairs — intersection of *potentially evaluable* cases

| Pair | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| boltz.csv and chai.csv | 1,640 | 371 | **361** |
| boltz1x.csv and chai.csv | 1,613 | 354 | 354 |
| boltz2.csv and chai.csv | 650 | 167 | 114 |

These are upper-bound candidate sets **before** inference-only mapping validation, permissions and scientific freeze. Do not confuse overlapping method coverage with paired pose-selection test results.

## Critical mapping finding

**None** of the eight archived prediction CSVs provides the `model_ligand_chain` field, despite the publisher README describing it in the general schema. This was confirmed from the CSV headers in the pinned archive, not inferred from documentation.

Among **proper matched predictions**, multiple CSV rows shared the same `(target, ligand_instance_chain, seed, sample)` run key:

| Method | Repeated keys |
| --- | ---: |
| boltz.csv | 1,251 |
| boltz1x.csv | 1,302 |
| boltz2.csv | 296 |
| chai.csv | 1,421 |
| protenix.csv | 1,415 |
| af3.csv | 1,501 |
| af3_no_template.csv | 1,491 |
| rfaa.csv | 45 |

Since `model_ligand_chain` is absent, the audit's column for **colliding model-chain identity** counts these same repeated keys as non-disambiguated; this is *missing identity*, not a finding that all underlying real model chains are identical.

The publisher's original OpenStructure output JSON examples show `assigned_scores` that explicitly associate `model_ligand` with `reference_ligand`. Such alignment information must stay **reference/evaluation-only**.

**No pose label was used for selection and no RMSD/accuracy was calculated. Raw dataset/model outputs were not committed.**

## Next gate

A strictly conservative analysis can restrict candidate models to cases where: exactly **one ligand exists in the annotated system**, `ligand_is_proper=true`, and **every scored candidate run key is unique** within its source CSV. This narrows scope and may avoid some missing mapping IDs, but still requires checking model chain provenance, rights, score direction and unseen-protein claims. Do not call it scientifically valid before these checks.

Further reference: `research/PHASE_03H_FREEZE_GATE.md`.
