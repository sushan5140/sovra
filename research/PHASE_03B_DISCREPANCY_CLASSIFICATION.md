# Sovra — Phase 03B Real-data discrepancy classification
Date: 2026-10-15
Status: DATA AUDIT ONLY, no benchmark evaluation or finalized data exclusion

Inputs: user-supplied annotations.csv and predictions.tar.gz from Runs N' Poses; processed read-only.

## Findings
- Annotation rows: 4,235; 4,235 unique (system_id, ligand_instance_chain) identifiers; 1,005 nominal cluster labels.
- Annotation rows with ligand_is_proper=True: 3,026; False: 1,209. Do not silently exclude invalid/flagged ligands before protocol decision.
- Across all eight prediction tables, exact full-row duplicates: **0**.
- Repeated (target, ligand_instance_chain, method, seed, sample) keys are **not** synonymous with duplicate rows. Every observed repeated base key can be distinguished by additional ligand-matching / mapping fields in the downloaded tables. A future row-granularity audit must confirm whether multiple mappings are legitimate and which can be treated as independent pose instances.
- RFAA has no seed/sample or ranking_score: it cannot enter a score-based selection task without a separate protocol.
- Boltz1x and Boltz2 filenames do not reliably identify the value inside the method column (both label records boltz): source filename/model version must be preserved as a provenance dimension.

| File | Rows | Joined annotation rows | Unmatched | Missing ligand chain* | Target absent* | Full-row duplicates |
|---|---:|---:|---:|---:|---:|---:|
| boltz1x.csv | 93,150 | 84,511 | 8,639 | 7,185 | 1,527 | 0 |
| boltz.csv | 91,543 | 85,351 | 6,192 | 4,645 | 1,547 | 0 |
| rfaa.csv | 2,863 | 2,837 | 26 | 0 | 26 | 0 |
| af3_no_template.csv | 107,458 | 105,908 | 1,550 | 0 | 1,550 | 0 |
| boltz2.csv | 38,001 | 36,079 | 1,922 | 1,647 | 275 | 0 |
| af3.csv | 107,464 | 105,853 | 1,611 | 62 | 1,549 | 0 |
| chai.csv | 103,133 | 101,556 | 1,577 | 14 | 1,563 | 0 |
| protenix.csv | 104,711 | 102,557 | 2,154 | 604 | 1,550 | 0 |

*Missing-chain and target-absent categories **overlap**, so do not add these two columns to derive unmatched totals. Identity matching used (target, ligand_instance_chain) against (system_id, ligand_instance_chain). For prediction records with a nonmissing chain and an annotated target, no unmatched chain identities were found.

## Immediate interpretation
1. Missing ligand_instance_chain and absent target identifiers are the two observed failure modes for the annotation join; neither is a scientific pose-prediction error by itself.
2. No exact duplicate rows means base-key collisions should **not** be deduplicated without further mapping analysis.
3. The previous validator's heuristic count of repeated identifiers is only a diagnostic and should not be used as a row-cleaning rule.
4. Dataset license and separate model-output terms must remain respected; raw third-party prediction tables are not committed.

## Next gate: splitting and consistency
- Create a deterministic **candidate** split at cluster level, not row level. Freeze the group mapping and checksum, document seed/method.
- Audit protein/pocket and ligand similarities *between* split clusters (same cluster ID is only a preliminary leakage guard).
- Check eligibility criteria and validate label/RMSD semantics before baseline.
- Mark prediction records ineligible for straightforward ligand-level joins as **quarantined**, not deleted; keep error counts by model.
- Treat all splits as PROVISIONAL until independent similarity audits and licensing are complete.

## Provenance
SHA256 annotations.csv: 259aa0a8f5ea6008d4036886f1ad5ae255689c223eb839fa1a2e7cb54adae609
SHA256 predictions.tar.gz: c4eaeec2d5cf7594325822127e8c014237611ba428750d7670bcb23608a82749
