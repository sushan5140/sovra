# Phase 03 — Runnable dataset firewall

The preliminary source audit selected Runs N' Poses for **candidate data inspection**, not yet as an approved train/test benchmark.

## Run locally after legally obtaining archives

1. Read the Zenodo record's **Legally_Binding_Terms_of_Use.txt** and **OUTPUT_TERMS_OF_USE.md**. Resolve dataset-specific use/redistribution restrictions before fetching or using model outputs. Keep files out of Git.
2. Record exact Zenodo version/record ID, file checksums, sizes, retrieval dates and model versions.
3. Extract `annotations.csv` and **one individual method's** prediction CSV from `predictions.tar.gz`; never concatenate multiple methods without assigning a method dimension.
4. Execute from repository root:

```bash
python -m unittest discover -s tests -v
python scripts/audit_dataset.py --annotations /path/annotations.csv --predictions /path/method_predictions.csv --out audit_report.json
```

The script accepts `--split-manifest /path/splits.json`: JSON object mapping every annotation `group_key` to train/val/test. It rejects cluster overlap between splits. It does **not** create an evidence-based split for you or prove that chosen clusters are sufficient to prevent all similarity leakage.

Select features explicitly, for example `--feature ranking_score`. The firewall rejects known reference-derived accuracy columns such as RMSD, but **this is only a denylist**: you must still review any new feature's source, calculation time and dependency on the experimental answer.

## Source warnings

- GitHub source: https://github.com/plinder-org/runs-n-poses
- Versioned dataset records: https://zenodo.org/records/15348481 and https://zenodo.org/records/16754298
- The model output archives have their own legal terms. A repository code license cannot replace reading these terms.
- Prediction score tables are not the same as full predicted-coordinate archives.
- Due to network restrictions in the execution environment, live Zenodo archives were **not downloaded or inspected** in this phase.

## Scope and status

Added executable schema validation, split-cluster collision checking, and synthetic regression tests. **Not** completed: real-data validation, license clearance, checksums, frozen splitting, performance measurement, or any pose-selection model. No efficacy claims.

## Future improvements before real data
- Join and validate record-specific additional ligand/chain identifiers and multi-model prediction identity.
- Check fingerprint/protein-similarity links across clusters, not just identical cluster IDs.
- Validate source-dependent features individually and prevent post-hoc annotations.
- Report missing scores, missing labels, chemically improper ligands and case counts by model.
- Establish exact symmetry-aware pose metric provenance and reference mappings.
