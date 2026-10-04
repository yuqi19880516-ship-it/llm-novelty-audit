#!/usr/bin/env python3
"""Post hoc (2026-10-03): synonym/MeSH-expanded co-occurrence for all 307 audited pairs.
Queries use PubMed Automatic Term Mapping (untagged terms: drug AND disease), which maps each
term to MeSH headings, supplementary concepts and all-fields synonyms; date range up to T.
Output: outputs/expanded_cooc.json {"drug||disease": {"n_ac":..,"n_a":..,"n_c":..}}"""
import json, os, time, urllib.parse, urllib.request
T = "2026/06/05"; OUT = "outputs/expanded_cooc.json"
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
def count(term):
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "0"}
    for _ in range(6):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=60) as r:
                d = json.loads(r.read().decode()); time.sleep(0.36)
                return int(d["esearchresult"]["count"]), d["esearchresult"].get("querytranslation", "")
        except Exception:
            time.sleep(4)
    return -1, ""
rows = [json.loads(l) for l in open("outputs/coded_sample.jsonl") if l.strip()]
cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
single = cache.setdefault("_single", {})
for i, r in enumerate(rows):
    k = f"{r['drug']}||{r['disease']}"
    if k in cache and cache[k].get("n_ac", -1) >= 0: continue
    for t in (r["drug"], r["disease"]):
        if t not in single or single[t][0] < 0: single[t] = count(f"({t})")
    n, qt = count(f"({r['drug']}) AND ({r['disease']})")
    cache[k] = {"n_ac": n, "n_a": single[r["drug"]][0], "n_c": single[r["disease"]][0], "qt": qt[:400]}
    if i % 25 == 0:
        json.dump(cache, open(OUT, "w"), ensure_ascii=False); print(i, k, n, flush=True)
N, _ = count('("1800/01/01"[PDAT] : "2026/06/05"[PDAT])'); cache["_N"] = N
json.dump(cache, open(OUT, "w"), ensure_ascii=False); print("done N", N)
