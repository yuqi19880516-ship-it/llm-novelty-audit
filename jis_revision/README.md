# Revision materials (October 2026): "Restatement, recombination or discovery? A preregistered literature-based audit of hypotheses from a multi-agent LLM system"

Materials for the revised manuscript submitted to the *Journal of Information Science*. They extend the original replication package in the repository root.

- Preregistration: https://doi.org/10.17605/OSF.IO/C38BD
- Addendum (scoring plan for the human validation, registered 3 October 2026 before expert coding): https://doi.org/10.17605/OSF.IO/PAZC4

## Contents

| Path | Contents |
|---|---|
| `scripts/` | Sampling frame (`build_frame_v2.py`), exact and synonym-expanded PubMed counts (`pubmed_counts_v2.py`), record retrieval (`fetch_abstracts_v2.py`, `fetch_abstracts_perm.py`, `fetch_l2_extended.py`), coding batches, memory probe v2 with negative controls (`probe_v2.py`), perturbation v2 (`perturb_v2_plan.py`, `perturb_v2.py`), permutation and other baselines (`baselines_v3.py`), the full analysis (`analysis_v3.py`) and figures (`fig_gen_v3.py`) |
| `outputs/` | Sampling frame (`frame_v2.json`, 400 items), translated items, PubMed counts, the retrieved records with full abstracts (`abstracts_v2.json`, `abstracts_perm.json`), probe and perturbation runs, permutation-baseline pairs, and the analysis report (`analysis_v3_report.txt`, `analysis_v3.json`) |
| `coding/` | Codebook v2 with its two addenda (extended re-check; target-equivalent categories) and the coding batches (drug, disease and the records the coders read) |
| `human_validation/` | Registered scoring plan, scoring script, and the blank expert workbooks (150 read pairs; 30 free-search pairs) with the scripts that built them |

## Withheld until the human validation is complete

The per-item machine labels (both coders' first-pass and re-check labels, adjudications, final labels), the lists of pairs selected for the extended re-check, the re-check records, and the answer key of the human-validation sample are not yet published, because the outside experts must code the same items blind. They will be added to this folder, with SHA-256 checksums frozen on 3 October 2026, once the expert coding is finished. Until then `analysis_v3.py` cannot be re-run from this folder; its output is provided in `outputs/analysis_v3_report.txt`.

## Running

Scripts expect to run from a directory containing `outputs/` and `coding_materials_v2/` (the `coding/` folder here) next to them, as in the authors' working copy, with Python 3.10+ and `requirements.txt` from the repository root. LLM API keys, where needed, are read from environment variables; no keys are included.
