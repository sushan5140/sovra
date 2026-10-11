# sovra.

**Question the prediction. Then question the intervention.**

Sovra is an early-stage, open computational research project studying **failure modes in protein–ligand structure prediction**. We want to understand not only *when* a prediction is unreliable, but whether an appropriate next action can improve experimentally referenced pose recovery **at a controlled computational cost**.

> **Research status:** hypothesis and experimental-design stage. **No model, benchmark result, demonstrated improvement, or drug discovery is claimed.**

## The problem

A predicted protein–ligand complex may look plausible yet be wrong. Different cases can involve different issues: inadequate pose exploration, incorrect selection among sampled poses, wrong protein conformational states, or chemically invalid geometry. Additional random sampling or rescoring is not guaranteed to fix every failure.

**Our question:** Can evidence available *before* seeing the experimental answer help determine which action to take next—and when to stop?

## Working hypothesis: failure-conditioned adaptive inference (FCI)

We are **investigating**, not asserting, whether three components improve accuracy–compute trade-offs on genuinely held-out protein families:

1. **Failure signals:** assess observable pose diversity, geometry, representation consistency and other diagnostic features without access to the reference answer at test time.
2. **Intervention policy:** choose between additional sampling, reranking, refinement, alternative-state exploration, or abstention within a specified compute budget.
3. **Outcome memory:** learn from interventions and outcomes on *training-only* cases to inform decisions on unseen cases.

This is a candidate research architecture, **not a novelty claim**. Before implementation we will audit existing adaptive inference, perturbation methods and physics-based refinement literature.

### Competing hypotheses

We are also evaluating:

- **Relational learning:** can differences across related molecular cases be modeled more accurately than independent predictions?
- **Conformational diversity:** can explicit protein-state exploration recover states missed by ordinary inference?
- **Evidence-limited inference:** can a model identify when the available evidence cannot distinguish competing hypotheses and abstain appropriately?

The final research direction remains open until the baseline and prior-art gates are passed.

## Experimental principles

- **Reproduce before proposing improvement.** Compare against relevant established methods, fixed-budget sampling, simple uncertainty rules and random routing.
- **No hidden reference access.** Experimental structures can produce training labels and held-out evaluation metrics, but cannot inform test-time decisions.
- **Fair comparison.** Match computational budgets and report hardware, runtime, versions, seeds and settings.
- **Check generalization.** Use data provenance audits, similarity-aware splits and untouched out-of-group evaluations.
- **Ablate everything.** If a simpler system matches the hybrid, prefer the simpler system.
- **Publish failures.** Negative results, chemically invalid structures, uncertainty and limitations belong in the report.

Cached predictions may support an **offline policy simulation**, which is not evidence of real-time compute savings.

## Roadmap

| Stage | Phases | Goal | Status |
| --- | --- | --- | --- |
| Scientific foundation | 01–03 | Literature audit, hypothesis selection, benchmark and leakage plan | Planning |
| Reproducible evidence | 04–05 | Reproduce baseline and build a labeled failure atlas | Not started |
| Competing experiments | 06–08 | Test relational, state-diversity and evidence-limited alternatives | Not started |
| Adaptive research engine | 09–11 | Diagnosis, intervention policy, outcome memory | Not started |
| Scientific validation | 12–13 | Ablations, out-of-group generalization and falsification | Not started |
| Research experience & release | 14–15 | Traceable experiment viewer, documentation and results | Not started |

**Detailed research decisions:** [Research Decision Record 001](research/DECISION_RECORD_001.md).

## References for the starting investigation

- [PoseBusters](https://doi.org/10.1039/D3SC04185A) — physical and chemical plausibility checks for predicted binding poses.
- [PLINDER](https://github.com/plinder-org/plinder) — protein–ligand structural evaluation resource.
- [GPCR co-folding generalization study (2026)](https://www.nature.com/articles/s44386-026-00066-1) — unfamiliar-target pose errors and refinement.
- [Ion-channel co-folding benchmark (2026)](https://www.frontiersin.org/journals/biophysics/articles/10.3389/frbis.2026.1937302/full) — pose sampling, ranking and input-representation limitations.

References motivate questions; they do **not** establish that Sovra's proposed combination is original or effective.

## Scope and integrity

Sovra is computational research, **not** a clinical tool. Docking scores, predicted structures and computational rankings do not establish binding, drug efficacy, toxicity or medical safety. No invented benchmark statistics or simulated experimental outcomes will be presented as measured findings.

---

Maintained by [sushan5140](https://github.com/sushan5140).  
**sovra.** — research first, evidence always.
