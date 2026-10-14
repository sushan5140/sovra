# Phase 03 — Dataset, Provenance & Leakage Gate
Date: 2026-10-14
Status: PARTIAL — source/documentation audit performed, raw archives and splits not downloaded or inspected

## Decision
**Prefer Runs N' Poses as the first read-only, cached-prediction feasibility benchmark.** Use PLINDER 2026-09 as a separate reference for modern dataset APIs and future independently evaluated cases. Do **not** mix the old 2024 PLINDER archive schema with the current 2026-09 release.

Why: Runs N' Poses (https://github.com/plinder-org/runs-n-poses) explicitly documents downloads of:
- annotations.csv — system identifiers, ligand and target characteristics, clustering and similarity descriptors
- predictions.tar.gz — per-method model, seed, sample, ranking_score, reference-derived RMSD/lDDT and mapping metrics
- posebusters_results.tar.gz — physical/chemical pose checks
- ground_truth.tar.gz — receptor/ligand reference structures (evaluation only)
- all_similarity_scores.parquet — similarities calculated against historical PDB structures and training-cutoff sensitivity

**Critical:** This is *not automatically a train/validation/test split suited to learning our intervention policy*. The benchmark was designed for zero-shot model generalization with a model-specific structural training cutoff (the README highlights 2021-09-30); it is not automatically a leakage-free policy-training set. We must construct and freeze *separate policy* train, validation, and untouched test partitions grouped by protein/pocket clusters. The benchmark model's structural training cutoff and Sovra policy's training split are different things.

## Current source and permissions caveat
Runs N' Poses repository code displays Apache-2.0, but the Zenodo archive is a separate distribution. **Check its record-specific data license and model-output redistribution terms** before ingesting or rehosting files. A GitHub code license does not automatically cover all externally hosted data.
PLINDER current docs: PLINDER_RELEASE=2026-09 and newer path layout at https://cameo3d.org/plinder/PLINDER-2026-09/.
No source tarball, dataset content or checksums were downloaded in this phase.

## Mandatory column firewall
**Allowed policy features (subject to per-method existence, and never taken from ground truth):**
- run seed / sample index as provenance (not normally learning features), method identity
- model-produced ranking_score/confidence and protein–ligand interface scores *only when valid at inference*
- prediction-derived pose-to-pose dispersion if predicted coordinates are actually available
- pre-computable ligand/protein descriptors for allowed inputs; guard that none are derived from experimental pose or post-release annotations unavailable at inference

**Evaluation/training labels only; PROHIBITED test-time policy inputs:**
- rmsd, lddt_pli, lddt_lp, bb_rmsd, pred_pocket_f1
- reference-system geometry and ligand placement
- target_system and reference alignment dependent / future-PDB similarity fields
- any PoseBusters output that requires a reference; non-reference geometry validators may be input features only if actually computed from predicted outputs
- novel_splits/classification labels if derived from held-out reference details

Model ranking_score units/direction differ across methods. Do not concatenate or threshold across methods before calibration or explicit stratification.

## Required provenance/split audit before computing performance
1. Download Zenodo metadata, capture DOI, version, license, SHA256/known record checksums, sizes and file URLs. Freeze local manifest.
2. Read archive headers and real schemas; verify methods, sample counts, systems, missingness, coverage and ligand_is_proper.
3. Check whether actual predicted pose coordinates are distributed. Scored tables alone support **score-based selection experiments**, not geometric re-refinement, reranking of unobserved structures, or pose-to-pose dispersion.
4. Confirm correct relation among system_id, ligand_instance_chain, group_key, method, seed, sample and reference mappings; flag ambiguous/invalid compounds.
5. Audit same-system, pocket cluster, protein-family and ligand-fingerprint overlap. Group policy splits by structural pocket cluster, plus additional protein/ligand similarity tests.
6. Document model-specific training cutoffs. Beware newer model training sets might contain benchmark complexes; mark contamination risk rather than declaring zero-shot.
7. Verify that the held-out test set has adequate distinct independent groups and predefine coverage exclusions. Never tweak splits after seeing outcomes.
8. Prefer per-system paired bootstrap with cluster-level resampling; report both group count and case count.
9. Inspect minimum model/tool licensing and scientific restrictions before any new inference.

## Feasible first protocol (conditional on files passing audit)
- Aim 1: original model top-1 success (e.g., symmetry-aware ligand RMSD <2 Å) using source error column **only for evaluation**. Verify definition before accepting.
- Aim 2: oracle top-k success as inaccessible-reference upper bound; label explicitly ORACLE.
- Aim 3: choose among *already available* candidate samples via ranking_score/confidence and simple group-aware ranker trained only on training partition; benchmark held-out top-1.
- Aim 4: selective risk vs coverage at preregistered coverage levels (e.g., 50%, 70%, 90%) and calibration.
- No claimed live adaptive compute savings, no novel poses or new sampling intervention unless pose files and model-runtime infrastructure become available.

## Stop conditions
- Archive license not established, incomplete provenance, or ambiguity around reference-free features.
- Only one prediction per case; no feasible selection task (fallback to confidence-vs-error diagnostics).
- Too few independent protein/pocket groups for meaningful holdout.
- Predictions generated on cases possibly memorized in model training; report exclusions/sensitivity rather than bold generalization claim.
- No reproducible metric mapping or insufficient data integrity.

## Next required action
Dataset *accessibility and true schema* validation. Produce immutable schema/provenance report and small synthetic fixture-based firewall tests first; then secure archive, validate actual row fields, finalize protocol and hand off engineering work.

## Evidence examined
1. https://github.com/plinder-org/runs-n-poses
2. https://plinder-org.github.io/plinder/dataset.html
3. https://plinder-org.github.io/plinder/tutorial/dataset.html
4. https://plinder-org.github.io/plinder/evaluation.html
5. https://www.biorxiv.org/content/10.64898/2026.06.29.735309v1.full

No empirical Sovra results have yet been generated.
