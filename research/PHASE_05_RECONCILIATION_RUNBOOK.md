# Phase 05 synthetic inference-run reconciliation runbook

Status: synthetic infrastructure only. Every report includes
`real_status: REAL_RECONCILIATION_BLOCKED`. No real inventory has been authenticated.

## Scope and reviewed sources

Implementation specification and source audit were read from research PR #3,
commit `9e851a339b302e7c837b64e7356199614dbfb79e`:

- [CODEX 03 specification](https://github.com/sushan5140/sovra/blob/9e851a339b302e7c837b64e7356199614dbfb79e/research/CODEX_03_INFERENCE_RUN_RECONCILIATION.md)
- [Phase 05 source inventory audit](https://github.com/sushan5140/sovra/blob/9e851a339b302e7c837b64e7356199614dbfb79e/research/PHASE_05_SOURCE_RUN_INVENTORY_AUDIT.md)
- Existing Phase 03H/03I evidence and Phase 04 prediction index, adapter and separate
  evaluation-reference boundary remain unchanged.

The publisher [notebook](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb)
reads confidence JSONs but enumerates analysis files and drops empty reference
assignments. The [example run script](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/examples/utils/run_boltz.sh)
requests five seeds and five samples; it supplies no completion ledger. The
[analysis script](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/examples/utils/analyze_models_boltz.sh)
compares model CIFs against reference SDF/CIF files. These sources were read, not
executed. Their naming examples are not authentication of an archived build.

## Inputs and identity contract

`scripts/phase05_inference_run_reconciliation.py` accepts five local inputs:

| Input | Required content |
| --- | --- |
| `inference_inventory.csv` | `target,seed,sample,artifact_kind,artifact_path,data_origin` |
| `published_summary.csv` (or `boltz.csv`) | `target,seed,sample,method,data_origin`; `method=boltz` |
| `annotations.csv` | `system_id,group_key,cluster,ligand_is_proper,num_ligand_chains,data_origin`; optional `entry_pdb_id,component_id` |
| `manifest.json` | Exact external mapping of every annotation `group_key` to `train`, `val` or `test` |
| `inventory_provenance.json` | Exact `SOURCE` object below, plus SHA256 hashes of all four preceding files |

Every CSV row must declare `data_origin=synthetic`. Empty inventory/summary CSVs
with valid headers are supported; annotations cannot be empty. Duplicate, empty
or padded headers, malformed records and duplicate JSON keys are rejected.
Summary reference columns and scores may be present, scrambled or absent. They
are never projected or inspected for matching, cohort membership or status.
CSV syntax must still be well formed even in ignored columns.

Raw IDs are case-sensitive ASCII tokens matching `[A-Za-z0-9][A-Za-z0-9_.-]*`.
They are never trimmed, converted to numbers, renumbered or numerically sorted;
`01` differs from `1`. Unsupported identifiers are quarantined, not normalized.
This is a deliberately narrow synthetic contract, not a universal archive parser.

One inventory row describes one declared inference artifact. Confidence and
structure listings may be independently incomplete; neither requires the other.
Allowed kinds are `confidence_json` and `model_cif`. Paths must exactly match the
synthetic convention, relative to a Boltz output root:

```text
{target}/{seed}/boltz_results_input/predictions/input/confidence_input_model_{sample}.json
{target}/{seed}/boltz_results_input/predictions/input/input_model_{sample}.cif
```

Paths are compared as strings only. No listed path is opened, resolved, scanned,
downloaded or extracted. Absolute paths, traversal, backslashes, alternate
basenames and ID/path disagreements are quarantined. There is no directory
scanner or `--real` option. No molecular fixture files need to exist.

Exact provenance fields (unknown fields are rejected):

```json
{
  "dataset_doi": "10.5281/zenodo.16754298",
  "dataset_version": "v4",
  "model_version": "Boltz-1",
  "source_table": "boltz.csv",
  "inventory_generation_method": "synthetic_inference_artifact_listing",
  "synthetic": true,
  "rights_status": "synthetic_only",
  "input_sha256": {
    "inference_inventory": "<SHA256 of inventory bytes>",
    "published_summary": "<SHA256 of summary bytes>",
    "annotations": "<SHA256 of annotation bytes>",
    "manifest": "<SHA256 of manifest bytes>"
  }
}
```

These declarations and hashes bind local fixture bytes. They cannot establish
independence, authenticity, physical file existence, completeness or usage rights.
Do not relabel real files as synthetic. Analysis JSONs, summary-derived listings
and planned-run grids are not accepted provenance methods.

## Reproduce the synthetic example

Run from the repository root using Python 3.10 or newer. The Phase 05 module uses
only the standard library. The complete existing suite also needs `pyarrow==21.0.0`.
Use your activated environment's `python`; on Windows this checkout used
`.venv/Scripts/python.exe`.

```sh
python -c "import sys; from pathlib import Path; sys.path.insert(0, 'tests'); from test_phase05_inference_run_reconciliation import write_fixture; write_fixture(Path('work/phase05-synthetic'))"
python -m scripts.phase05_inference_run_reconciliation --inference-inventory work/phase05-synthetic/inference_inventory.csv --published-summary work/phase05-synthetic/published_summary.csv --annotations work/phase05-synthetic/annotations.csv --manifest work/phase05-synthetic/manifest.json --inventory-provenance work/phase05-synthetic/inventory_provenance.json --synthetic-only --out work/phase05-synthetic/report-1.json
python -m scripts.phase05_inference_run_reconciliation --inference-inventory work/phase05-synthetic/inference_inventory.csv --published-summary work/phase05-synthetic/published_summary.csv --annotations work/phase05-synthetic/annotations.csv --manifest work/phase05-synthetic/manifest.json --inventory-provenance work/phase05-synthetic/inventory_provenance.json --synthetic-only --out work/phase05-synthetic/report-2.json
python -c "from pathlib import Path; a=Path('work/phase05-synthetic/report-1.json').read_bytes(); b=Path('work/phase05-synthetic/report-2.json').read_bytes(); assert a == b; print('byte-identical')"
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
git diff --check
```

Expected counts: nine artifact rows, six unique usable inference IDs, three with
both artifacts, two confidence-only, one structure-only; one inference-only,
one summary-only and five intersecting IDs. Six annotated targets remain in the
denominator, including two without listed predictions. One known excluded target
and one unknown target remain in global comparison. No count is a pose outcome.

## Reading the report

- Exit 0: `SYNTHETIC_RECONCILIATION_PASS`. Exit 1 with
  `SYNTHETIC_RECONCILIATION_QUARANTINED`: inspect aggregate reasons; do not treat
  the remaining set comparison as a complete inventory. Exit 1 with
  `REAL_RECONCILIATION_BLOCKED`: invalid/unavailable inputs or provenance. Argument
  errors exit 2 with a sanitized aggregate message. Real use is blocked in all cases.
- `observed_*_ids_before_quarantine` counts unique syntactically valid declared
  IDs, including IDs whose artifact metadata is invalid. `usable_*_ids` excludes
  quarantined IDs. `both_artifacts`, `confidence_only`, `structure_only` and set
  comparisons use only usable IDs.
- One confidence row plus one structure row is normal. Repeated rows of the same
  kind, conflicting filenames and repeated summary IDs quarantine the entire
  known run ID on **both sides**. No collision is silently deduplicated or repaired
  with a score/reference mapping. Reason counts may overlap; row/ID totals do not.
- Malformed IDs have no usable run key. Their rows count as quarantined and in raw
  row denominators, but not unique-ID counts; they cannot be associated with or
  used to repair a valid counterpart. A valid target places such a row in its
  reporting bucket; otherwise it goes to `unknown`.
- Missing artifact counters mean **not listed in this inventory**, not proven
  physically missing. They cannot distinguish absent, deleted, withheld or
  unreported files. A summary-only ID is not proof that no inference occurred.
- All manifest coverage and shared system/cluster/PDB/component partition links
  are checked before strict-cohort filtering. Strict means exactly one annotation
  row, one total ligand and proper=true. `train/val/test` are strict-cohort views;
  known excluded systems use `outside_cohort`, all other targets use `unknown`.
  Global matching includes all buckets. Cohort flags cannot change global run sets.
- Annotation denominators include targets without usable runs; counts distinguish
  no valid ID at all from quarantined IDs. Group connectivity uses all annotations
  before filtering. Group counts across strict/outside views can overlap; do not
  sum them as independent families. No split is generated and no holdout is unsealed.
- Reports contain aggregates, constant protocol text and input/code SHA256 hashes.
  No target/group/run IDs, artifact paths, scores, reference values or structures
  are emitted. Changed reference bytes affect input/provenance hashes only.
  Byte identity requires the same input and source bytes; Git newline conversion
  can change source hashes across platforms without changing diagnostics.
- No planned-run input or denominator exists. A 5x5 example cannot establish 25
  observed runs. There is no top-1 selection, accuracy calculation or missing-label
  failure policy here; the existing Phase 04 selection tests remain in the suite.

## Real-world stop/go and minimum publisher request

Real reconciliation remains blocked by the absence of an authenticated inventory
from original inference outputs, unresolved exact model build/weights/cutoff,
uncleared output rights, downstream reference-filtered summaries, unreviewed
molecular mapping/missing-label policy, provisional split independence and lack
of authorization for a real metric protocol. Historical paired case counts do
not establish independent protein families or a sealed holdout.

Request a **small authenticated per-file metadata sidecar**, generated from the
original inference tree before analysis: v4 dataset identity; exact Boltz-1 code
and weights; unmodified target/seed/sample; artifact kind; relative path and file
checksum; enumeration method and completeness statement. Include separate
planned/attempted/failed/missing-run records and disclosure of files deleted,
renumbered, reranked, filtered or withheld. Request explicit permitted uses of
that metadata and source outputs. No coordinates, confidence values or reference
labels are needed. This runbook does not send that request or authorize acquisition.

Do not reconstruct this sidecar from `predictions.tar.gz`, OpenStructure JSON,
reference-label coverage or an example sampling grid. Do not download the 38.2 GB
archive. Fresh inference would be a different, separately authorized experiment.
AF3 restrictions, future strict BiSyRMSD `<2` review and all prior gates remain.
