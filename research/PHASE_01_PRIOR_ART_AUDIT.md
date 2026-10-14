# Phase 01 — Targeted prior-art audit v1
Date: 2026-10-14
Status: preliminary, sourced; not a comprehensive systematic review

## Critical correction
**Adaptive perturbation schedules already exist.** Boltz-Perturb contains TADS-Auto, an adaptive schedule based on model noise variance. Therefore Sovra cannot claim novelty for adaptive perturbation alone.

## Point-by-point evidence
| Work | Verified contribution | What is NOT solved by that result | Implication |
|---|---|---|---|
| Masters, Mahmoud & Lill, Nature Communications (2025), DOI: 10.1038/s41467-025-63947-5 | Controlled chemically plausible perturbations reveal that co-folding predictions can respond inconsistently with physics and chemistry. | Paper diagnoses model behavior; does not establish a generally reliable universal test-time correction policy. | Treat chemistry perturbations as **diagnostics**, not automatically truth labels. |
| Jung, Lee & Cheng, Boltz-Perturb (bioRxiv, 2026-08-05), DOI: 10.64898/2026.08.05.742877 | Training-free conditioning perturbations (TBP/TCP) can improve sample diversity and oracle pose recovery; **TADS-Auto** adapts perturbation schedule. | Oracle top-k recovery is not necessarily a deployable top-1 pose selector. Adaptive perturbation *within one intervention family* does not alone answer which distinct intervention should be chosen. | Must compare with Boltz-Perturb, including TADS-Auto, if feasibility/data permit. Do not claim generic novelty for adaptive sampling. |
| PLINDER repository, plinder-org/plinder, current accessed 2026-10-14 | Similarity-aware split design, structured protein–ligand data, linked apo/holo structures, benchmark tooling. | An evaluation resource, not proof a new Sovra method works. README flags a disabled ligand binding affinity query due to a BindingDB parsing bug. | Prefer structural pose metrics in initial study. Freeze dataset version, splits, and licensing before running experiments. |
| PLINDER article/preprint | Quantifies leakage problems in historic dataset splits. | Similarity-aware splits still require rigorous per-experiment leakage analysis. | Split manifests must be immutable across training and test evaluation. |

## Research hypothesis H-FCI (revised, not yet validated)
*On held-out protein families, observable failure indicators can support selection among **distinct** corrective actions (additional sampling, candidate reranking, refinement, or abstention), providing better top-1 ligand-pose success at a matched compute budget than any single fixed action or confidence-only routing.*

Important: if reranking, refinement or alternative sampling is not genuinely available for an example, the action space must be constrained and transparently logged.

## Two separate upper/lower outcomes
- **Oracle best-of-k success** establishes whether a valid pose exists in a generated candidate pool. It is a diagnostic upper bound; an inference-time policy cannot select using reference RMSD.
- **Deployable top-1 success** measures the actually selected pose without reference information.
Do not substitute the former for the latter.

## Provisional initial experiment design
1. Freeze one benchmark snapshot and train/validation/test grouping, excluding unresolved ligands or problematic mappings.
2. Prepare or obtain **legitimately cached** baseline candidate poses with known provenance and permissions.
3. Measure top-1 reference pose success and oracle top-k success separately, with a specified RMSD alignment / symmetry-aware protocol.
4. Estimate whether observable features predict failure labels *using training data only*; start with interpretable heuristics and a small classifier.
5. Simulate candidate reranking and abstention on cached predictions; label as **offline retrospective evaluation**, no compute savings claim.
6. Only after that, attempt live adaptive inference on appropriate hardware and compare at measured matched CPU/GPU cost.
7. Report bootstrap uncertainty with grouping by protein or pocket where necessary, and subgroup failure results.

## Mandatory baselines
- Original model confidence/top-1 ranking.
- Fixed sampling budget (where generated candidates are available).
- Simple confidence and ensemble diversity heuristics.
- Random intervention / abstention.
- Relevant published adaptive sampling method, especially TADS-Auto if implementation and compute can be secured.

## Abandon / revise conditions
- No leakage-free sufficient sample size.
- No valid provenance for candidate pose ensembles.
- Features fail to predict out-of-group failures better than simple heuristics.
- The adaptive policy has no benefit over matched-cost fixed methods.
- Apparent improvements are exclusive to oracle selection.

## Phase gate
P1 is NOT complete. Next: verify dataset snapshot/API/licensing and inspect candidate outputs/available models. Do not start heavy model training or claim benchmark performance.

## Sources checked
1. https://www.nature.com/articles/s41467-025-63947-5
2. https://www.biorxiv.org/content/10.64898/2026.08.05.742877v1.full
3. https://github.com/plinder-org/plinder
4. https://openreview.net/pdf?id=7UvbaTrNbP
