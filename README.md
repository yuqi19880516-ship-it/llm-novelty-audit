# Replication materials — "Discovery or retrieval? A preregistered scientometric audit of knowledge novelty in multi-agent LLM scientific-discovery systems"

Replication package for a manuscript submitted to *Scientometrics*. Preregistration: OSF, DOI [10.17605/OSF.IO/C38BD](https://doi.org/10.17605/OSF.IO/C38BD).

> **Update (October 2026):** materials for the revised version submitted to the *Journal of Information Science* (synonym-expanded retrieval, blinded reading of all co-occurring records, permutation baseline, probe and perturbation v2, human-validation protocol) are in [`jis_revision/`](jis_revision/). Scoring-plan addendum: [10.17605/OSF.IO/PAZC4](https://doi.org/10.17605/OSF.IO/PAZC4).

## Contents

| Path | Contents |
|---|---|
| `audit_pipeline/` | The audit pipeline: goal definitions (`goals.py`), replica-system and bare-model generation (`coscientist/`, `models.py`), triple coding (`coding.py`), time-sliced PubMed scientometric novelty measurement (`novelty.py` — degree-preserving hypergeometric z + Swanson-style disjointness), provenance/memory probes (`provenance.py`), and the orchestrating `pipeline.py`. All LLM API keys are read from environment variables (`llm.py`) |
| `outputs/` | Raw and derived data: the coded main sample (`coded_sample.jsonl`, N = 307), bare-base-model ablation (`bare_coded_final.json`, N = 266), counterfactual perturbation records (`rq4_coded.jsonl`), L0 abstract-verification shards (`l0_abs_shard*.jsonl`, `l0_abstracts.json`), Robin external audit (`robin/`), raw generation logs (`generation/`, `bare/`), and threshold-sensitivity grids |
| `coding_materials/` | The coding codebook and instructions, worksheet, and the four-rater reliability answer sheets behind the Fleiss κ = 0.94 panel |
| `fig_gen.py` / `fig_gen_en.py` | Figure generation from the raw coded data (Chinese/English label versions); `fig_gen_en.py` produces the five figures in the manuscript at 600 dpi PNG + vector PDF |
| `requirements.txt` | Python dependencies |

## Reproducing the paper's numbers

1. Python 3.10+, `pip install -r requirements.txt`.
2. All headline quantities — the novelty-spectrum shares (Table 2), provenance/memory bounds, self-assessment calibration (Fig. 2), base-model contrasts, threshold-sensitivity grid (Table 4, Fig. 3), ablation spectra (Fig. 4), and perturbation assent rates (Table 5, Fig. 5) — are computed from the files in `outputs/` by the scripts in `audit_pipeline/` and `fig_gen_en.py`. No API access is needed to reproduce the paper from the archived outputs.
3. Re-running generation or probes from scratch requires API keys for the audited base models, set via the environment variables named in `audit_pipeline/llm.py`. Model versions iterate; the archived outputs are the versions reported in the paper.
4. Scientometric measures query PubMed via NCBI E-utilities with per-target time slicing (< T literature only); cached counts used in the paper are included in `outputs/`.

## External data (not redistributed)

- Robin's dry-AMD candidates were taken from the public [FutureHouse Robin repository](https://github.com/Future-House/robin); the audited 47 deduplicated candidates and their audit records are in `outputs/robin/`.
- PubMed/MeSH corpus statistics are queried live from NCBI E-utilities.

## License

Code: MIT. Data files in `outputs/` and `coding_materials/` are released CC BY 4.0.
