# Draft request — Original Boltz-1 inference-run manifest

Status: **DRAFT ONLY — NOT SENT.** Do not send without user approval.

**Suggested subject:** Runs N' Poses v4 — lightweight Boltz-1 inference-file manifest for a reference-blind audit

Dear Runs N' Poses team,

Thank you for making the dataset and benchmark available.

I am investigating whether the published `boltz.csv` permits a fully reference-blind analysis of Boltz-1 pose selection. In `extract_scores.ipynb`, `process_boltz_file` reads the original `confidence_score` but skips analysis outputs with missing/empty RMSD or lDDT-PLI assignments. This makes it difficult to determine how many model-produced runs exist independently of reference scoring.

Would you be willing to share a **small file-list manifest**, derived directly from the original Boltz-1 inference output folders (not the accuracy-analysis folders), listing only:
- `target`, `seed`, `sample`, and the relative filenames of `confidence_input_model_*.json` and matching `input_model_*.cif` files;
- whether all originally completed runs are represented, and how failed/missing runs were tracked;
- which Boltz version/weights produced these files and any restrictions on using the archived inference confidence outputs for independent, noncommercial research.

**I am not requesting molecular structures, confidence values, or reference labels.** A simple `find`/directory listing or hashed inventory would be sufficient to validate coverage without downloading the 38.2 GB archive.

I will preserve attribution and source terms and will not publish raw predictions or claim accuracy improvements without a separate audit.

Thank you for considering this request.

Best regards,
SUSAN

---

Source refs:
- https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb
- https://zenodo.org/records/16754298
