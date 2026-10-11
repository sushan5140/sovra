# sovra.

**Question the prediction.**

Sovra is an open research project investigating **how reliably computational methods rank protein–ligand binding candidates**, and whether simple checks can identify misleading confidence before candidates are prioritized for experimental study.

> **Status:** research design / baseline planning — no benchmark results or validated drug discoveries claimed.

## The research question

Can a transparent reliability layer detect unstable or misleading molecular ranking results **better than simple baselines**, without merely discarding all hard cases?

The first study is not a drug-discovery claim. It is a *falsifiable evaluation* of computational predictions.

## Planned first experiment

1. Select a legitimately redistributable benchmark with measured binding labels, assay metadata and train/test grouping information.
2. Reproduce a documented baseline and establish a fixed data split before tuning.
3. Evaluate molecular rankings with appropriate metrics (e.g., Spearman rank correlation and enrichment metrics where applicable).
4. Quantify prediction instability under documented, scientifically defensible perturbations and alternative model assumptions.
5. Evaluate whether a reliability/abstention rule improves *selective* performance at specified coverage levels against score-only and random-abstention baselines.
6. Repeat with scaffold-level and, where metadata allow, protein-family or temporal holdouts to test generalization.
7. Publish configs, seeds, provenance, failure cases and negative findings.

**Important:** docking scores and predicted poses are not experimental evidence of efficacy, toxicity, safety, or clinical suitability. Predicted protein structures are not guaranteed to be valid docking targets. Any compound-specific conclusion requires appropriate experimental validation.

## Success and failure criteria

A meaningful result must outperform preregistered simple baselines on **held-out data** with uncertainty intervals and disclose coverage–performance tradeoffs. If the reliability layer fails, that negative result is still a valid outcome. Selective performance alone is not enough if coverage collapses.

## Repository roadmap

- [ ] Data provenance, licensing and leakage audit
- [ ] Data schema + fixed split manifest
- [ ] Reproducible baseline scorer
- [ ] Reliability indicators with ablation study
- [ ] Calibration and selective-risk evaluation
- [ ] External holdout or distribution-shift audit
- [ ] Research visualization (only after metrics are real)

## Ethics and limitations

- Computational, non-clinical research only.
- No claim of discovering, validating, or recommending a medicine.
- No wet-lab or synthesis instructions.
- Respect benchmark licenses, assay provenance, and any chemical-use restrictions.
- Track model versions, code versions, parameter choices, and reproducibility limits.

## Why the name?

**sovra.** is the project name; the science lives in the methods, not the branding.

Maintained by [sushan5140](https://github.com/sushan5140).
