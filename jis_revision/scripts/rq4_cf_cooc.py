#!/usr/bin/env python3
"""Post hoc check (run 2026-10-03): whether counterfactual (drug, C') pairs of the perturbation test have prior PubMed
co-occurrence before T (2026/06/05). Same query form as the main pipeline (rq2_dates.py).
Output: cf_cooc.json {"drug||cf_disease": count}
"""
import json, os, time, urllib.parse, urllib.request
R = "."
OUT = "outputs/rq4_cf_cooc.json"
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
def count(term, maxdate="2026/06/05"):
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1900/01/01", "maxdate": maxdate, "retmax": "0"}
    for _ in range(5):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=45) as r:
                d = json.loads(r.read().decode()); time.sleep(0.4)
                return int(d["esearchresult"]["count"])
        except Exception as e:
            time.sleep(4)
    return -1
rq = [json.loads(l) for l in open(f"{R}/outputs/rq4_coded.jsonl") if l.strip()]
pairs = {}
for r in rq: pairs.setdefault(f"{r['drug']}||{r['cf_disease']}", (r["drug"], r["cf_disease"]))
cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
print("unique cf pairs", len(pairs), flush=True)
for i, (k, (drug, dis)) in enumerate(pairs.items()):
    if k in cache and cache[k] >= 0: continue
    cache[k] = count(f'("{drug}"[tiab]) AND ("{dis}"[tiab])')
    if (i+1) % 25 == 0:
        json.dump(cache, open(OUT, "w"), ensure_ascii=False); print(f"  {i+1}/{len(pairs)}", flush=True)
json.dump(cache, open(OUT, "w"), ensure_ascii=False)
vals = list(cache.values())
print("done; failed", sum(1 for v in vals if v < 0), "| cf pairs with cooc=0:", sum(1 for v in vals if v == 0), "| cooc>=1:", sum(1 for v in vals if v >= 1), "| cooc>=5:", sum(1 for v in vals if v >= 5))
