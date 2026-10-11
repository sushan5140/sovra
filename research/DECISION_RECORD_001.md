# SOVRA — Research Decision Record 001
Date: 2026-10-12
Status: PROVISIONAL — no method validated, no benchmark executed

## Mission
Study when protein–ligand structure predictors fail, and test whether failure-informed decisions improve experimentally referenced pose recovery under matched compute budgets. Do not claim drug efficacy, binding affinity or clinical utility from pose scores.

## Primary candidate: failure-conditioned adaptive inference (FCI)
- Input: molecular representations, protein context, an initial ensemble of predicted poses and run metadata.
- Diagnostic: estimate *observable* signs of sampling shortage, pose-ranking weakness, conformation mismatch and chemical invalidity. A true failure label requires a held-out experimental structure and is never available to a test-time policy.
- Policy: choose among stop/abstain, additional sampling, independent reranking, and targeted refinement, subject to cost.
- Memory: use training-only intervention outcomes to learn conditional action value.
- Hypothesis: a learned policy improves top-1 experimentally referenced pose recovery per unit cost on unseen protein families versus fixed sampling, best-confidence selection, simple uncertainty heuristics and random action allocation.
- Null: the policy has no held-out accuracy–cost advantage; complexity is not justified.

## Competing hypotheses
H-R: relational molecular changes carry useful predictive signal beyond independent predictions.
H-S: explicit conformational state diversity improves recovery beyond additional ligand sampling.
H-E: identifying insufficient evidence and abstaining improves selective risk at a useful coverage.
These are alternatives to test, not mandatory modules.

## Source-anchored constraints
1. PoseBusters (Chemical Science 2024; DOI:10.1039/D3SC04185A): predicted poses can be chemically/physically implausible. Reuse established validation, don't claim invention.
2. PLINDER (https://github.com/plinder-org/plinder): similarity-aware splits, standardized evaluation, and linked apo structures. Verify snapshot version, allowed use and exact split before accessing test records.
3. GPCR co-folding study (npj Drug Discovery 2026, https://www.nature.com/articles/s44386-026-00066-1): unseen-target ligand pose errors can persist despite backbone accuracy; refinement may be useful in specific cases.
4. Ion-channel co-folding benchmark (Frontiers in Biophysics 2026, https://www.frontiersin.org/journals/biophysics/articles/10.3389/frbis.2026.1937302/full): limited pose recovery after repeated sampling; distinguish unsampled native poses from ranking mistakes.
Literature coverage is preliminary, not a systematic novelty clearance.

## Phase gates
P1. Build a prior-art matrix: paper, dataset, task, baseline, contribution, limitations, licenses, compute assumptions. Separate peer review from preprints.
P2. Choose one primary hypothesis and one fallback, define falsification and primary endpoint *before* test-set inspection.
P3. Select licensed benchmark subset and freeze identifiers/similarity-aware split. Audit chemical identity and leakage.
P4. Reproduce or transparently evaluate a baseline; report whether predictions were executed or cached.
P5. Build an error atlas; check chemical validity using established tools.
P6-8. Test relational, state-diversity and evidence-abstention ideas *only where benchmark evidence and resources make them feasible*.
P9. Train diagnosis using training partitions; tune only on validation.
P10. Assess intervention policies against equal-cost fixed/random/uncertainty baselines.
P11. Evaluate outcome memory with strict out-of-group testing.
P12. Complete ablations: base; diagnostic; policy; memory; each justified combination.
P13. Freeze code/model before untouched test evaluation; negative results and uncertainty intervals included.
P14. Build UI as a read-only view of traceable experiment artifacts, never simulated results disguised as measured science.
P15. Release protocol, code, model/data cards, metrics, caveats and a manuscript only if justified.

## Decision rules
- Exact input representation and receptor state must be logged; do not collapse chemically distinct cases.
- Treat correlated poses and proteins as non-independent where applicable.
- Define pose success threshold and evaluation metric in advance; compute/latency measured with specified hardware.
- Compare at matched computational cost (GPU/CPU-time or well-defined proxy), not merely number of samples.
- When using cached ensembles, label result **offline policy simulation**, not adaptive live compute savings.
- Reject apparent gains if leakage, performance collapse on held-out groups, or missing reference labels invalidate them.
- The flagship hypothesis is not yet locked. Do not implement the full FCI hybrid before P1–P4 evidence.

## Codex handoff gate
Call Codex at P3/P4 when (a) dataset and split version are decided, (b) baseline tool/license is fixed, (c) metric definitions and required artifacts are written. First Codex assignment should be a minimal reproducible evaluation pipeline with tests and provenance logs, not the full application.

## Current completion ledger
- Repository/README: initialized.
- P1: preliminary source collection; NOT complete.
- P2: candidate hypotheses; NOT selected.
- P3-P15: NOT started.
