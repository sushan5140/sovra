# Phase 03 — Real dataset ingestion checkpoint (2026-10-14)

**Status:** Files received and parsed; not cleared for training or baseline evaluation.

## Observed files
- annotations.csv: 4,235 unique system/ligand annotation rows; 2,579 systems; 1,005 cluster labels. ligand_is_proper: True 3,026; False 1,209.
- predictions.tar.gz: eight prediction CSVs, with method-specific fields and differing coverage.
- posebusters_results.tar.gz: seven method CSVs, without a Boltz2 table.
- AlphaFold 3 output terms + legally binding notice: provided; non-commercial, attribution, redistribution and derived-model limitations require compliance.

| Prediction file | Rows | Distinct targets | Rows with annotation match | Duplicate 4-field keys* |
|---|---:|---:|---:|---:|
| boltz1x.csv | 93,150 | 2,137 | 84,511 | 11,200 |
| boltz.csv | 91,543 | 2,187 | 85,351 | 9,784 |
| rfaa.csv | 2,863 | 1,782 | 2,837 | 264 |
| af3_no_template.csv | 107,458 | 2,431 | 105,908 | 11,164 |
| boltz2.csv | 38,001 | 878 | 36,079 | 4,443 |
| af3.csv | 107,464 | 2,430 | 105,853 | 11,201 |
| chai.csv | 103,133 | 2,317 | 101,556 | 11,096 |
| protenix.csv | 104,711 | 2,354 | 102,557 | 11,290 |

*4-field key: (target, ligand_instance_chain, seed, sample). Repetitions are **not automatically erroneous duplicates**; investigate row granularity before removal. RFAA has no seed/sample or ranking_score fields.

### Validator discrepancy discovered
Actual prediction CSVs use `target`, not `system_id`. The earlier proof-of-concept validator expects `system_id` and **must be adapted and retested before it can be used on these real files**. Some prediction-to-annotation joins fail; do not silently drop unmatched rows.

### Restrictions
The uploaded AlphaFold 3 output terms restrict uses to specified non-commercial contexts and prohibit certain derived models, with notice and citation requirements on dissemination. External Zenodo data and other model output permissions remain to be checked. **Do not put raw third-party model outputs into the public Sovra repository.**

### Next gates
1. Resolve real identity schema and repeated keys, and document exclusion rationale.
2. Audit missing annotation matches and chemically improper ligand rows.
3. Confirm legally appropriate use and record-level dataset licenses; document source hashes.
4. Define leakage-controlled protein/pocket-group policy splits and any across-group similarity exceptions.
5. Patch validator; run synthetic and real-data tests.
6. Then compare deployable top-1 versus **oracle** top-k on frozen evaluation cases.

### SHA256
- annotations.csv: 259aa0a8f5ea6008d4036886f1ad5ae255689c223eb839fa1a2e7cb54adae609
- predictions.tar.gz: c4eaeec2d5cf7594325822127e8c014237611ba428750d7670bcb23608a82749
- posebusters_results.tar.gz: d8d75ee4be18590ed6ff1ee4a30f6342da4e724b8389c989b6867ab2d3f4b431

**No scientific performance has been measured by Sovra.**
