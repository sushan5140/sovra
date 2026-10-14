# Phase 02 — Hypothesis decision gate (v1)
Date: 2026-10-14
Status: PROVISIONAL — protocol design, not an experimental result

## Decision
Select H-FCI-lite as the lead hypothesis to test, not as an established novel method:
Given an initial set of protein–ligand pose predictions, can observable, reference-free features choose between reranking, further sampling, or abstention more effectively than fixed or confidence-only strategies on held-out protein groups?

## Hypothesis tournament
| Candidate | Scientific question | Role | Decision |
| --- | --- | --- | --- |
| A: Chemical sensitivity | Do molecular modifications and representations expose errors? | Diagnostic feature | Include as an ablation, with chemically valid perturbations |
| B: Conformational recovery | Can alternative receptor states rescue missed binding configurations? | Expensive intervention | Defer |
| C: Adaptive compute | Which cases warrant more samples? | Policy and strong baseline | Compare to published TADS-Auto |
| D: Biological Git | Can experiment branches improve researcher exploration? | Product UX | Defer |
| E: Counterfactual memory | Do prior failure/action outcomes generalize to unseen proteins? | Optional policy extension | Only after simpler baselines |
| F: Failure-conditioned inference | Can observable errors guide selection among *different* interventions? | Primary hypothesis | Feasibility test |
| H-R: Relational learning | Can modeling molecular differences improve prediction? | Competing research task | Separate fallback, not first pose benchmark |
| H-E: Evidence-limited inference | Can calibrated abstention improve risk at useful coverage? | Safety / baseline | Mandatory comparison |

## Experimental decision gate
- Primary future live endpoint: top-1 symmetry-aware ligand heavy-atom RMSD under 2 Å against the experimental reference on suitable non-covalent complexes, evaluated at matched measured compute. Exact protocol and threshold must be preregistered before a test run.
- Distinguish sampling failure (no successful pose among K) from ranking failure (good pose present but top-1 wrong); use reference only for evaluation and training labels, never at test-time choice.
- Offline reranking/abstention on cached poses is a retrospective simulation and cannot prove real-time adaptive compute savings or discovery of absent poses.
- Compare: baseline rank/confidence, fixed K, simple confidence/pose diversity heuristic, random cost-matched allocation, simple learner without memory, and a relevant published adaptive perturbation method in later live testing.
- Do not claim efficiency at unequal compute or count oracle-best-K recovery as deployable top-1 accuracy.
- Group resampling/statistical analysis by protein or pocket. Freeze splits, candidate provenance, chemistry mapping, and costs before training.
- If features do not beat confidence heuristics on held-out groups, reject extra complexity. If memory does not help, remove it. Negative results must be published.

## Dataset choice is Phase 03, not already completed
PLINDER is a candidate; verify current release version, license, split manifest, chemical validation, and whether genuine predicted pose ensembles are obtainable.
Current dataset docs indicate a 2026-09 release; older layouts differ. PLINDER evaluation supports reference system IDs, ranks, ligand pose files, and optional confidence fields. Some binding-affinity annotations are flagged as problematic in upstream documentation, so affinity is not the initial endpoint.

## Decision
Provisional lead: FCI-lite (diagnostic features + limited action routing).
Fallback: calibrated evidence-limited abstention.
Memory and full physics/state interventions require separate proof of incremental value.
P2 **protocol drafted**, scientific novelty and feasibility **not established**.

## Sources
- https://www.biorxiv.org/content/10.64898/2026.08.05.742877v1.full
- https://plinder-org.github.io/plinder/dataset.html
- https://plinder-org.github.io/plinder/evaluation.html
- https://github.com/plinder-org/plinder
- https://www.nature.com/articles/s41467-025-67495-w
