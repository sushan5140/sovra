# Phase 03C — Provisional partition overlap audit

Date: 2026-10-17. Source: uploaded Runs N' Poses annotations.csv and previously generated provisional_splits.json.

**Outcome: BLOCK FREEZE.** Identity overlap was assessed on the original, unmodified data. No predictions were trained or removed.

- Manifest SHA256: e3bb0433c6a367ebd5a8cc0403d11f300ee7913534e289f072668c7c01222604
- Annotation rows: 4,235 (train 2,899; val 756; test 580); group keys: 4,235.
- Cluster count: 1,005; **0 cluster IDs cross splits**.
- Exact ligand_smiles: **92 unique values cross splits**, affecting **1,786 rows**.
- Ligand CCD codes: **91 cross splits**, affecting **1,767 rows**.
- Entry PDB IDs: **5 cross splits**, affecting **17 rows**.

**Interpretation:** These are overlap indicators, not evidence of erroneous splits. Exact ligand overlap may be intended in target-generalization studies; it conflicts with a strict unseen-ligand claim. A protein-family/generalization experiment must additionally audit target and pocket similarity across split boundaries before locking its claim.

## Reproduction

```bash
python scripts/audit_split_overlap.py --annotations /path/to/annotations.csv --manifest /path/to/provisional_splits.json --out split_overlap_report.json
```

Only metadata and aggregate results are tracked here, not third-party raw datasets.

## Required follow-up

1. Choose generalization estimand explicitly: unseen protein families, unseen ligands or both.
2. Audit protein/pocket similarities with an appropriate source, including all_similarity_scores.parquet if licensed and obtainable.
3. Revise splits based on this preregistered target, preserve frozen train/validation/test groups and document unavoidable overlap.
4. Resolve model-output usage terms before running experiments, especially AlphaFold 3.
5. Verify the actual submitted code and full real-data tests; prior tests are not a substitute for future held-out scientific validation.
