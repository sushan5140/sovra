# Boltz-1 reference-blind adapter — preflight only

Date: 2026-10-18. Implements `CODEX_02_REFERENCE_BLIND_ADAPTER.md`.

**Synthetic software preflight only. Real preflight and molecular evaluation
remain BLOCKED.** No training, threshold fitting, success-rate computation,
raw archive downloads, molecular coordinates, or restricted data publication
are part of this adapter. The existing Phase 04 toy pipeline is unchanged,
including its synthetic-only gate and `<=` success convention.

## Publisher source verification and the remaining proof gap

The actual code cells of the [publisher extraction notebook at commit
197fafc60a5cef3a9e7f8a4b0dac7c965eed3839](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb)
were read, not executed. Notebook byte SHA256:
`36d3531c6f693f3ee11363e7acaa98233d86237ab75618b8185ef95e906a8e1c`.

Relevant data flow:

1. `process_boltz_file` parses target, seed and sample from the analysis JSON
   basename. Those tokens address an inference confidence file under
   `<target>/<seed>/boltz_results_input/predictions/input/` named
   `confidence_input_model_<sample>.json`.
2. The exported `ranking_score` comes from that file's `confidence_score`.
   It is a per-run score, not a reference-chain confidence field.
3. The function returns no rows if either RMSD or lDDT-PLI `assigned_scores`
   is absent/empty. The outer notebook loop enumerates the **analysis**
   directory. This makes the archived candidate population dependent on
   reference evaluation availability before Sovra ever reads the CSV.
4. Assignment records supply model/reference ligand identities.
   `merge_to_final_df` joins RMSD/lDDT tables and reference ligand metadata,
   suffixes mapping columns, and drops duplicate rows. None of these
   reference assignments is an inference-run identity.

The [official Boltz writer at commit
b1ebfc46ecf57f5414e0d1a6f9027bbb122c53bc](https://github.com/jwohlwend/boltz/blob/b1ebfc46ecf57f5414e0d1a6f9027bbb122c53bc/src/boltz/data/write/writer.py#L73)
sorts confidence in descending order and writes per-model confidence files.
Writer byte SHA256:
`65b7fd13f6fdd0d06c0f241a9b717529cf1bbe5e2d5fb70e1aa068400ac2f815`.
This is a pinned source audit of the retrieved writer; it is **not proof of
the exact executable/model release that produced the v4 archive**.

For a system with exactly one total ligand and one proper annotation row,
joining the already selected whole-system run to the lone reference ligand
offers no ligand choice that could change ranking. The synthetic association
helper demonstrates that sequencing: it accepts finalized decisions and
never searches for another candidate. Missing references cannot cause a
fallback. It does **not** establish complete source-run coverage or the
original output-to-molecule assignment. Those facts cannot be demonstrated
from the summary table and notebook alone, so real execution stays blocked.
Do not infer reference-free cohort completeness from the historical 190
paired cases, and do not describe those cases as independent protein families.

## Software boundary

`scripts/phase04_prediction_index.py` is standalone: no adapter/reference
imports, filesystem access, annotations, labels, ligand chain, or mapping ID.
Its frozen, slotted `PredictionRun` has exactly four primitive fields:
`target`, `seed`, `sample`, `ranking_score`. `PredictionIndex` contains only
exact-type runs; it rejects raw dictionaries, subclasses and repeated IDs.
Ranking takes only this index, uses descending finite score, and breaks ties
lexicographically by seed then sample. There is no threshold or fitting API.

`scripts/phase04_boltz1_adapter.py` validates provenance/cohort metadata and
projects the four columns before constructing the index. It never reads
reference **values** for eligibility, candidate identity, ranking, or report
denominators. CSV parsing necessarily reads file bytes; only allowed column
positions are retained. SHA256 provenance covers the entire input bytes,
including ignored columns, and is not a selection feature.

`scripts/phase04_evaluation_reference.py` is separate and is not imported by
the adapter or selector. `EvaluationReference` accepts explicitly synthetic
test mappings only. `associate_after_selection` receives finalized decisions
and attaches a singleton annotation reference after the decision. It performs
no metric computation. No real label loader or real association path exists.

The separation is a testable API/data boundary, **not an operating-system
sandbox against arbitrary hostile Python introspection**. Tests include
poisoned forbidden fields, immutable/type-restricted inputs, and a fresh
process that imports only the selector and disables file access during ranking.

## Synthetic input contract

Use one local CSV named **`boltz.csv`**, never an archive. Its method column
must contain exactly `boltz`. Every input CSV row must have
`data_origin=synthetic`. Do not add that marker to real data. It is a caller
assertion, not cryptographic proof of origin. No real-mode override exists.

Annotations require `system_id`, `group_key`, `cluster`, `ligand_is_proper`,
and `num_ligand_chains`. A cohort system needs exactly one annotation row,
one **total** ligand chain, and a true proper flag. One proper ligand among
several total ligands is excluded. Repeated systems are excluded, not
deduplicated. Invalid boolean/count/schema values block the input.
`ligand_instance_chain` is neither required nor inspected for this preflight.

The separate JSON manifest must map every annotation group, and no other
group, to `train`, `val`, or `test`. Duplicate keys are rejected. Shared
system/cluster and optional PDB/component identities must remain in one
partition, even for annotations later excluded from the cohort. Connected
group IDs and optional `class`/PDB/component metadata are preserved internally
apart from inference runs. No split is created or modified. Supplied connected
groups are not a claim of independent protein-family sampling.

Prediction identity is exactly `(target, seed, sample)`. Seed/sample are
nonempty unpadded strings, not normalized numeric aliases. If any run for a
strict target has missing/invalid identifiers or a duplicate identity, the
**whole target's prediction rows are quarantined** before score filtering.
Even a duplicate with a missing score or different reference chain cannot
be silently discarded or disambiguated using a mapping suffix.

Missing score columns/values, NaN and infinities are unavailable, not model
failures. Finite scored runs remain selectable when other runs lack scores.
Absent predictions remain in strict-cohort denominators. Empty prediction
tables with valid headers are reported as no predictions. Row totals reconcile
to indexed, missing-score, quarantined, outside-cohort and invalid-target rows.
Target-status and cohort-exclusion counts are distinct, documented populations.

All unknown columns are discarded. In particular, `ligand_instance_chain`,
`target_ligand_chain_*`, `model_ligand_chain_rmsd`,
`model_ligand_chain_lddt_pli`, `rmsd`, `lddt_pli`, arbitrary `*_rmsd` and
`*_lddt_pli`, CCD/SMILES mapping fields, and `mapping_id` never enter the
index. Removing/permuting their values cannot change selection or exclusions.

The source-provenance JSON must match the `SOURCE` contract in the adapter:
pinned v4 DOI, `boltz.csv`, Boltz-1 identity, confidence source/direction and
the audited upstream source commits/hashes. It additionally requires
`input_kind=synthetic` and `input_sha256` with exact annotation, prediction
and manifest hashes. This binds **synthetic fixtures to an intended source
contract**, not to authenticated publisher archive bytes. Extra model versions
and AF3 sources are rejected before their prediction files are opened.

## Reproduction

Use Python >=3.10. The adapter is standard-library-only. Existing synthetic
Parquet tests need pyarrow 21.0.0. Activate a repository-local virtual environment:

```sh
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# POSIX: source .venv/bin/activate
python -m pip install pyarrow==21.0.0
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

Create fixture files by running this Python block from the repository root:

```python
import csv
import json
from pathlib import Path
from scripts.phase04_boltz1_adapter import SOURCE
from scripts.phase04_eligibility import sha256

root = Path("work/boltz1-adapter-synthetic")
root.mkdir(parents=True, exist_ok=True)
annotations = [dict(system_id=f"toy{i}", group_key=f"g{i}", cluster=f"c{i}",
    ligand_is_proper="true", num_ligand_chains="1", data_origin="synthetic") for i in range(3)]
predictions = [dict(target=f"toy{i}", seed=str(seed), sample="0", ranking_score=str(0.9 - seed * 0.5),
    method="boltz", data_origin="synthetic", rmsd="IGNORED", model_ligand_chain_rmsd="IGNORED")
    for i in range(3) for seed in range(2)]
for name, rows in (("annotations.csv", annotations), ("boltz.csv", predictions)):
    with (root / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
(root / "manifest.json").write_text(json.dumps(dict(g0="train", g1="val", g2="test")), encoding="utf-8")
(root / "source.json").write_text(json.dumps({**SOURCE, "input_kind": "synthetic", "input_sha256": {
    name: sha256(root / filename) for name, filename in (
        ("annotations", "annotations.csv"), ("predictions", "boltz.csv"), ("manifest", "manifest.json"))
}}), encoding="utf-8")
```

Execute this command (one line on PowerShell or POSIX):

```sh
python -m scripts.phase04_boltz1_adapter --annotations work/boltz1-adapter-synthetic/annotations.csv --predictions work/boltz1-adapter-synthetic/boltz.csv --manifest work/boltz1-adapter-synthetic/manifest.json --source-provenance work/boltz1-adapter-synthetic/source.json --synthetic-only --out work/boltz1-adapter-synthetic/report.json
```

Direct-script invocation is also supported. Exit 0 means synthetic preflight
completed; it does not authorize real use. Exit 1 writes a blocked report with
reason counts, and exit 2 indicates CLI misuse. Output aliases of input files
are rejected. Create the output directory first. No threshold override is
accepted. Run twice with identical files/code/runtime to obtain identical
report bytes. Existing `phase04-synthetic.yml` runs the full suite on this PR;
do not dispatch the older real-data download workflows.

The report contains only schema-presence flags, hashes, source versions,
protocol, per-split aggregate cohort/run/score/group counts, exclusions and
blocked gates. It contains no identified case rows, ranked runs, scores,
reference values, molecular success rates or raw data artifacts. Library
`prepare_synthetic` returns the isolated synthetic index for adversarial tests;
the CLI exposes only `preflight`'s aggregate report.

## Permissions and science checklist before any real baseline

- [ ] Clear exact archive-output usage terms for the intended independent
  research use. Upstream permissive code/weight licensing is not output-rights
  clearance. Preserve notices; no assumption of institutional affiliation.
- [ ] Independently inventory inference-produced runs and score paths, including
  runs missing from analysis/assigned-score outputs. Reconcile archive filtering
  and publisher deduplication without reading success labels to choose a cohort.
- [ ] Prove singleton model output/ligand provenance from inference-side inputs;
  resolve original mapping semantics without reference-dependent assignments.
- [ ] Identify the exact archived Boltz release/weights and training cutoff;
  document contamination limits separately from Sovra split boundaries.
- [ ] Freeze approved cohort, split hash, similarity components, estimand and
  uncertainty plan. Historical paired-case counts are feasibility, not final N.
- [ ] Review and enable a separate future real protocol: **BiSyRMSD < 2 Å**.
  `FUTURE_REAL_PROTOCOL` is immutable/disabled metadata only, with no evaluator.
  Do not change the existing toy baseline's `<=` convention.
- [ ] Authorize a separately reviewed real aggregate preflight and, later,
  evaluation only after prerequisites pass. There is currently no real entry
  point or rights override flag. Do not relabel inputs as synthetic to bypass it.
- [ ] Confirm release policy for any permitted aggregates. Never upload raw
  archives, structures, model outputs or restricted data. Do not request the
  approximately 38 GB raw prediction-files archive without explicit justification
  and permission; this implementation does not download it.

No real data preflight was run for this PR because rights/provenance gates
remain unresolved. No real accuracy benchmark, model training or scientific
improvement claim is made.
