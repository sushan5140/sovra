# Phase 03H — Publisher score extraction & reference-mapping source audit
Date: 2026-10-18

**Primary source read directly:** https://github.com/plinder-org/runs-n-poses/blob/main/extract_scores.ipynb

This notebook is the *publisher's executable extraction logic*, not merely schema documentation. These findings are based on reading `process_boltz_file`, `process_chai_file`, `process_af3_file`, `process_protenix_file`, and `merge_to_final_df` from the notebook.

## Verified extraction facts
- Boltz source `ranking_score` is extracted from the prediction confidence JSON `confidence_score`. Official Boltz docs (https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md) state it is used to sort predicted structures and that **higher is better**.
- Chai source `ranking_score` is extracted from `data["aggregate_score"][0]`. Confirm its specific release and ordering semantics before asserting it is the same calibrated statistic as Boltz. No score pooling across methods.
- AF3 source `ranking_score` is taken from `ranking_scores.csv`; Protenix from its `ranking_score` confidence field. AF3 rights remain restricted regardless of technical availability.
- The `rmsd` and `lddt_pli` subreports supply **separate** `assigned_scores`, each with `model_ligand` and `reference_ligand` objects. They are *evaluation-derived chain mappings*, not a deployable source of pose identity.
- In `merge_to_final_df`, the notebook merges RMSD- and lDDT-based mappings, adding suffixes `_rmsd` and `_lddt_pli`; it joins `model_ligand_ccd_code` and `target_ligand_chain_lddt_pli` back to reference `ligand_instance_chain`, drops certain join fields, then invokes `drop_duplicates()`. Thus the archived per-reference-ligand table is already **post-evaluation processing**. Do not treat its reference ligand chain or mapped model-chain identifiers as inference-time evidence.
- The real Phase 03H archive headers lacked unsuffixed `model_ligand_chain` in all eight models. That is now *explained* by the suffixing and merging step; the suffixed `model_ligand_chain_rmsd`/`_lddt_pli` fields are not reference-free mapping IDs. Never infer the absence of raw structure chain identifiers from the absence of an unsuffixed archived column.
- Preprocessing `drop_duplicates()` does not justify deduplicating the new model's remaining prediction rows with a chosen heuristic, and it cannot prove the original source contained no duplicates.

## Consequences for Sovra
The first real dataset adapter must be **prediction-centric**, keyed by a uniquely recoverable *sample output* that was available before reference scoring. The evaluation join may attach BiSyRMSD only *after* selection. If the archived summary table does not carry enough such information, request upstream raw `prediction_files.tar.gz` (38GB) **only with an explicit reason and permission**, or restrict to independently proven single-ligand, unique-run cases first.

Do not download the huge archive by default. The cheaper Phase 03I strict-cohort feasibility study must be examined first.

The publisher's [Polaris benchmark](https://polarishub.io/benchmarks/plinder-org/runs-n-poses) specifies **BiSyRMSD <2 Å**; the synthetic baseline's `<=` threshold is a test implementation convention and not the future real benchmark protocol.

No held-out pose-success rates or FCI model improvements were calculated in this audit.
