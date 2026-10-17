# Phase 03G — Model Output Permissions and Baseline Gate
Date: 2026-10-17
Status: **RESTRICTIONS IDENTIFIED; NOT LICENSE-CLEARED FOR TRAINING OR PUBLIC REDISTRIBUTION**

## Provenance
- Pinned benchmark: Runs N' Poses Zenodo record [16754298](https://zenodo.org/records/16754298), version v4, DOI 10.5281/zenodo.16754298.
- Publisher-provided checksums: annotations.csv MD5 793c711638ba20ae40518ed0e36b0a56; predictions.tar.gz MD5 58648b836ff9434bc929b7fad25cd9bb.
- Source project: https://github.com/plinder-org/runs-n-poses. Its Apache-2.0 code license does NOT automatically override model output terms bundled with the benchmark.
- The Zenodo record's visible general license field is not sufficient, by itself, to authorize all uses of every model output. This is a compliance checklist, not legal advice.

## Model-by-model clearance gate
| Source tables | License / use checkpoint | Provisional action |
| --- | --- | --- |
| af3.csv and af3_no_template.csv | Bundled **ALPHAFOLD 3 OUTPUT TERMS OF USE** (dated 2024-11-09) restrict outputs to noncommercial contexts, limit eligible institutional affiliations and prohibit training / making models similar to AlphaFold 3 from outputs. Notice and paper citation apply to distribution/publication. | **Exclude from Sovra's downstream ML training/policy learning until permitted use is affirmatively established**. Aggregate archive inspection is not scientific training approval. |
| boltz.csv, boltz1x.csv, boltz2.csv | Model/software licenses and output rights need confirmation for the exact variants/files before training or downstream distribution. The archive's method field may not uniquely identify the source version. | **Rights review pending**. Preserve filename and version provenance. |
| chai.csv, protenix.csv, rfaa.csv | Independently verify the appropriate model's usage rights and output provenance. RFAA lacks ranking_score/seed/sample columns, so comparison design differs even aside from permissions. | **Rights review pending**. |
| posebusters_results.tar.gz | Derived chemical validity diagnostics, potentially mixed with reference-based tests; also preserve source terms and distinguish reference-required fields. | Do not promote unreviewed reference fields to policy features. |

The provided AlphaFold 3 terms can be checked against https://github.com/google-deepmind/alphafold3/blob/main/OUTPUT_TERMS_OF_USE.md. The source scientific paper is Abramson et al. (2024), Nature, https://www.nature.com/articles/s41586-024-07487-w.

## Allowed now
- Document provenance, file hashes and aggregate row/schema counts.
- Test the synthetic pipeline on generated toy data.
- Build a conditional analysis plan, subject to rights checks.
- Link back to official dataset/model sources; do NOT rehost raw outputs in the Sovra public repository.

## Before Phase 04
1. Confirm permissible uses for **each selected method's** output under the intended independent/academic research context. Get explicit written clarification from the rights holder if ambiguous; do not assume noncommercial personal use qualifies.
2. Exclude nonpermitted outputs from any trained models or public demos.
3. Validate ligand eligibility, RMSD metric definitions (source calls 'rmsd' BiSyRMSD), mapping granularity and ranking score semantics.
4. Freeze a permissible method-specific subset with exact group counts, manifest checksum and no reference leakage.
5. No model improvement claim without reproducible baselines and held-out evidence.

**No clinical, affinity, or drug efficacy conclusion is authorized by this dataset.**
