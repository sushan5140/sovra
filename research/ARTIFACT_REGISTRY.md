# Sovra — Reproducibility & Artifact Registry

All corrected **source files** are tracked in this repository. User-provided third-party raw archives stay local until source-specific licensing permits redistribution.

## Committed artifacts

- `scripts/audit_dataset.py`: schema checker / leakage-feature firewall; flags mapping and duplicates without removing rows.
- `tests/test_audit_dataset.py`: synthetic regression checks.
- `scripts/make_candidate_splits.py`: deterministic candidate group/cluster split generator.
- `tests/test_candidate_splits.py`: cluster and reproducibility checks.
- `research/PHASE_03_REAL_DATA_INGESTION.md`: real-file schema inspection summary.
- `research/PHASE_03B_DISCREPANCY_CLASSIFICATION.md`: unmatched rows and duplicate-key analysis.
- `research/PHASE_03_VALIDATION_RUNBOOK.md`: usage instructions.

## Local-only input archives (DO NOT commit)

- `annotations.csv`: SHA256 `259aa0a8f5ea6008d4036886f1ad5ae255689c223eb839fa1a2e7cb54adae609`
- `predictions.tar.gz`: SHA256 `c4eaeec2d5cf7594325822127e8c014237611ba428750d7670bcb23608a82749`
- `posebusters_results.tar.gz`: SHA256 `d8d75ee4be18590ed6ff1ee4a30f6342da4e724b8389c989b6867ab2d3f4b431`

These hashes identify the specific user-provided input files, not a publisher's official verified release signature.

## Candidate split snapshot

A provisional local `provisional_splits.json` was generated from the uploaded annotation file. Its SHA256 is `e3bb0433c6a367ebd5a8cc0403d11f300ee7913534e289f072668c7c01222604`. It is **not yet checked into GitHub**. Use the script below to recreate a candidate manifest from `annotations.csv` (the identical checksum must be independently confirmed; split-script changes may affect output). The split is *not* certified leakage-free.

```bash
python scripts/make_candidate_splits.py --annotations /path/to/annotations.csv --output provisional_splits.json --seed sovra-v1
python scripts/audit_dataset.py --annotations /path/to/annotations.csv --predictions /path/to/predictions.tar.gz --split-manifest provisional_splits.json --out audit_report.json
python -m unittest discover -s tests -v
```

Never train on the candidate test split until independent ligand/protein similarity leakage checks, licenses, and exclusion rules are resolved.

## Limitations

- Repository scripts are **not** full pose-generation models.
- Predicted-coordinate archives are not stored or mirrored here.
- No experimental-performance improvements have been measured.
- A local generation manifest is **not** a finalized scientific data freeze.
