# Sovra Phase 03D — Validation checkpoint and next input
Date: 2026-10-17
Status: Provisional dataset audit; split NOT frozen

## Independently rechecked locally
Inputs: user-supplied annotations.csv and provisional_splits.json. No dataset mutation.
- Annotation rows: 4,235
- Split rows: train=2,899; val=756; test=580
- Unique cluster labels: 1,005; cluster IDs shared between partitions: 0
- Exact ligand_smiles values in multiple partitions: 92, affecting 1,786 rows
- ligand_ccd_code values in multiple partitions: 91, affecting 1,767 rows
- entry_pdb_id values in multiple partitions: 5, affecting 17 rows

These figures are **identity overlaps**, not protein/pocket similarity estimates or demonstrated training contamination.

## Primary question for first baseline
Generalization to held-out protein / binding-pocket groups under a matched candidate-pose evaluation protocol.
Secondary stratification: recurring ligand identity versus unseen ligand. Do not claim unseen-ligand performance from this split.

## Outstanding blocker
Need all_similarity_scores.parquet **from the identical Runs N' Poses Zenodo record** used for the previous CSVs. Similarity metadata columns in annotations.csv cannot substitute for a cross-split pairwise similarity audit. Record the source record ID, exact SHA256, and terms-of-use before use.

## Work once file is provided
1. Inspect Parquet schema and row-level join keys. Verify provenance and identify which similarity measurements represent protein, pocket and ligand similarity.
2. Join only compatible identifiers and validate coverage; report unmatched pairs separately.
3. Quantify cross-split high-similarity relationships for preregistered thresholds, with explicit threshold sensitivity analysis.
4. Revise split policy to reduce inappropriate similarity overlap, while preserving independent groups and reporting exclusions.
5. Validate against all available model tables without leaking experimental reference metrics into test-time features.
6. Freeze manifest and hashes only if the resulting study design survives leakage, model coverage, license and sample-size checks.

## Guardrails
No model training, reported accuracy or benchmark improvement has occurred. Do not commit unlicensed third-party raw data. Retain previous manifest as audit provenance. Avoid selecting thresholds by observed pose accuracy.
