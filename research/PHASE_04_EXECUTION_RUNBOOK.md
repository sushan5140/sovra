# Phase 04 baseline foundation — synthetic execution runbook

Status: **IMPLEMENTATION ONLY. REAL EVALUATION BLOCKED.**

This implements `CODEX_01_PHASE04_BASELINE_FOUNDATION.md` against the
Phase 03F feasibility results, Phase 03G verified coverage and rights gate,
and Phase 04 draft specification. Synthetic metrics test software behavior;
they are not benchmark measurements or evidence of Sovra improvement.
Existing research documents and provisional manifests are not replaced.

## Environment and regression suite

Python 3.10 or later. Phase 04 itself uses only the standard library.
The existing Phase 03 Parquet regression tests require `pyarrow==21.0.0`.
From the repository root:

```sh
python -m venv .venv
# POSIX: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install pyarrow==21.0.0
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

Without pyarrow, existing tests may skip; a skipped suite is not full validation.
The reviewed template `research/phase04-synthetic.workflow.yml.example` runs
only generated synthetic tests. Activating it as
`.github/workflows/phase04-synthetic.yml` requires a GitHub credential with
`workflow` scope; the available OAuth credential rejected that file's push.
The template is inert in this PR, so no CI result is claimed. Once authorized
workflow access is available, copy the template to that exact path and commit
it. Do not run the existing Phase 03 real-data download workflows for this phase.

## Reproduce a synthetic CLI run

This example creates toy CSVs in local scratch space; it downloads nothing.
Save the following as a local Python script or run it in a Python REPL from
the repository root:

```python
import csv
import json
from pathlib import Path

root = Path("work/phase04-synthetic")
root.mkdir(parents=True, exist_ok=True)
annotations = [
    dict(system_id=f"toy{i}", ligand_instance_chain="A", group_key=f"g{i}",
         cluster=f"c{i}", ligand_is_proper="true", data_origin="synthetic")
    for i in range(6)
]
predictions = [
    dict(target=f"toy{i}", ligand_instance_chain="A", method="boltz",
         seed=str(seed), sample="0", ranking_score=str(0.9 - seed * 0.5),
         rmsd=str(4 - seed * 3), data_origin="synthetic")
    for i in range(6) for seed in range(2)
]
for name, rows in (("toy_annotations.csv", annotations), ("toy_boltz.csv", predictions)):
    with (root / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
(root / "split.json").write_text(json.dumps({
    f"g{i}": ("train", "val", "test")[i // 2] for i in range(6)
}), encoding="utf-8")
```

Run this single-line command on PowerShell or POSIX:

```sh
python -m scripts.phase04_baselines --annotations work/phase04-synthetic/toy_annotations.csv --predictions work/phase04-synthetic/toy_boltz.csv --manifest work/phase04-synthetic/split.json --method toy_boltz.csv --score-direction higher --success-threshold 2 --risk-threshold 0.5 --risk-threshold 0.95 --bootstrap-iterations 1000 --bootstrap-seed 17 --synthetic-only --out work/phase04-synthetic/report.json
```

Direct invocation with `python scripts/phase04_baselines.py` is also supported.
All three input paths, the exact source filename, score direction, success
threshold, synthetic flag and output path are required. Exit codes: 0 for a
completed synthetic report, 1 for a blocked input (JSON reason/count), 2 for
invalid CLI arguments. Create the output directory first. Input overwrite is
rejected, including symlink/hardlink aliases.

Run twice with the same inputs, code, Python version and parameters: report
bytes must match. Reports include SHA256s of all input files and both Phase 04
modules, Python version, seed and protocol. A byte-level change in an input
changes its hash, even if row-order-independent decisions remain identical.
No timestamp, random split generation, threshold fitting, or network access
is part of this pipeline. Keep scratch reports out of commits. No real
`reports/phase04_baselines.json` is created by this implementation.

## Input contract

Every annotation and prediction row must contain `data_origin=synthetic`.
This explicit provenance assertion prevents accidental use of unmodified
benchmark files; it cannot independently prove data origin. Do not relabel
real data as synthetic. There is no real-data execution switch.

Annotations CSV requires:

| Field | Contract |
| --- | --- |
| `system_id`, `ligand_instance_chain` | Unique nonempty case pair; no whitespace normalization |
| `group_key` | Nonempty annotation group; several ligand cases may share a group |
| `cluster` | Nonempty published/synthetic cluster identity |
| `ligand_is_proper` | `true`/`false` (case insensitive); invalid values block the run |
| `data_origin` | Exactly `synthetic` |

Optional `entry_pdb_id` and `component_id`, if present, must be nonempty for
every annotation. `component_id` represents an externally audited, frozen
similarity component, never a grouping inferred from pose-success labels.
Optional `ligand_property_bin`, `similarity_bin`, `ligand_exposure` are
predeclared annotation strata. Missing values are `unknown`; no properties or
similarity scores are inferred. Subgroup accuracy is reported only with known
metadata and at least `--subgroup-min-groups` evaluable connected groups
(default 5, minimum 2). This is a reporting floor, not a power analysis.

The separate JSON manifest maps **exactly** every annotation `group_key` to
`train`, `val`, or `test`. Unknown/missing groups, duplicate JSON keys, invalid
partitions and shared system/cluster/PDB/component identities across partitions
block execution. Validation includes nonproper cases before filtering. The
manifest is read-only. These checks do not re-audit similarity edges, establish
unobserved family independence, or clear the Phase 03 freeze gates.

One predictions CSV is accepted at a time; archives are rejected. Required:
`target`, `ligand_instance_chain`, `method`, `data_origin`. Its **basename** must
equal `--method`, including version (e.g. `boltz2.csv`); the generic `method`
column may still say `boltz`. Exactly one nonempty method label is allowed.

Additional columns:

| Field | Use |
| --- | --- |
| `ranking_score` | Only numeric policy feature; missing/nonfinite values cannot select a pose |
| `seed`, `sample` | Required nonempty provenance when the score column exists; strings, not numeric ordering |
| `mapping_id` | Optional inference-only identifier; required on **all** rows of a repeated case/seed/sample run |
| `rmsd` | Optional held-out BiSyRMSD; missing, negative, nonnumeric or nonfinite values are unevaluable |
| `model_ligand_ccd_code`, `model_ligand_chain_rmsd` | Preserved as audit-only mapping provenance, never a tie breaker or feature |

`mapping_id` is a Phase 04 synthetic input-contract extension, not a claim
that the archive already provides it. It must be a stable identity available
without a reference structure, RMSD, lDDT or evaluation-based atom matching.
Do not derive it from row order, labels, or `model_ligand_chain_rmsd`. Before
future real use, an approved adapter and mapping protocol must establish such
identities. Without them, ambiguous runs are explicitly quarantined.

Distinct valid mapping IDs are retained as separate candidate mappings.
Repeated full identities quarantine **every** colliding row, including exact
duplicates; nothing is silently deduplicated. A partially identified repeated
run quarantines all its rows. The report records CSV record ordinals (header
is record 1), source mapping provenance, and mutually exclusive row-exclusion
counts. Missing scores are counted separately from identity exclusions.

## Selection and evaluation semantics

`higher` selects maximum finite score; `lower` selects minimum finite score.
There is no default or cross-model score normalization. Exact ties use
lexicographic `(seed, sample, mapping_id)`; for example string `10` precedes
string `2`. Reference fields, file order and ground-truth availability cannot
break ties. The selector receives a frozen allowlisted `Candidate` object,
with no reference/raw-row field. All decisions precede label evaluation.

A selected pose with no reference stays selected and unevaluable; it is never
replaced with a lower-ranked labeled pose. Success means BiSyRMSD **<=** the
explicit success threshold. The example threshold is a toy test parameter,
not an approved scientific convention.

The oracle checks all retained candidate mappings, including ones without a
finite score, only after selection. Any known successful label proves oracle
success; oracle failure requires complete labels and no success. Otherwise
the oracle is unknown. Reports distinguish mapping K from distinct seed/sample
run K; multiple mappings are not independent poses or independent cases.
Oracle values are a reference-only upper bound, never deployable decisions.

Every partition is summarized separately; no pooled train/val/test metric.
Top-1 accuracy is case-weighted over selected cases with known reference.
The denominator for selection coverage is **all proper annotation cases** in
that partition, including absent method predictions and quarantined cases.
Evaluation coverage, selected-but-unlabeled cases and oracle denominators are
separate. Compare top-1 with oracle using the paired fields on their shared
evaluable population; marginal denominators can differ.

Risk/coverage always includes accept-all-scored and abstain-all endpoints,
plus explicitly supplied thresholds. `higher` accepts score >= threshold;
`lower` accepts score <= threshold. Error is over accepted labeled cases;
coverage is accepted/all proper cases. No accepted labeled cases means null
error, never zero error. Thresholds must be fixed externally before test
inspection; the code does not select, optimize or recommend a cutoff.

Uncertainty uses a seeded percentile 95% bootstrap of **whole connected
groups**, with replacement, and a case-weighted mean within each draw.
Connections include group/system/cluster and supplied PDB/component identity,
constructed before eligibility filtering. Samples/mappings are never bootstrap
units. Reported group counts are not a claim of protein-family independence.
With fewer than two evaluable groups the interval is null with a reason.

For a paired comparison, evaluate each CSV separately with its own explicit
direction, then call `paired_comparison(left_report, right_report)` from
`scripts.phase04_baselines`. It requires identical annotation/manifest hashes,
metric, success threshold and bootstrap settings. It compares only the
intersection of top-1-evaluable cases within each partition, reports unmatched
coverage, and resamples the paired differences by the same groups. There is
no cross-method score comparison. This helper accepts in-memory reports from
`evaluate`; it does not execute a second CSV implicitly.

## Model caveats and blocked TODOs

- AlphaFold 3 source names/labels are rejected; no downstream model training
  exists. Do not use AF3 outputs to train Sovra or infer institutional rights.
- Boltz, Boltz1x and Boltz2 source filenames remain distinct even when their
  table labels are identical. Confirm each source's score direction and rights.
- Chai and Protenix require their own archived-version provenance, score
  definitions and permissions. No direction is inferred from the method name.
- RFAA without score/seed/sample remains visible as no-score coverage; no
  confidence is fabricated and unavailable selection is not a model failure.
  Repeated unidentifiable RFAA rows still require an explicit mapping protocol.
- TODO: resolve output licensing/allowed uses for each exact source; do not
  download, rehost or commit raw predictions, structures or new model weights.
- TODO: approve the study estimand, proper-ligand treatment, mapping protocol,
  BiSyRMSD conventions, success threshold, per-method score direction, frozen
  risk thresholds and subgroup definitions before examining test outcomes.
- TODO: freeze the permitted method populations and manifest checksum; review
  per-partition group counts and independently audit observed similarity links.
  Supply audited components for resampling; residual unobserved similarity and
  foundation-model training overlap remain limitations.
- TODO: obtain explicit authorization for real evaluation after review. Only
  then design a separately reviewed real-data entry point and aggregate report
  release process. Synthetic implementation tests do not satisfy these gates.

No clinical, affinity, efficacy, pose-recovery improvement or Sovra scientific
improvement is claimed.
