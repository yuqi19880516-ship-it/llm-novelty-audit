#!/usr/bin/env python3
"""Post hoc (2026-10-03): PubMed counts up to T = 2026/06/05 for every pair in frame_v2 under two constructs.
exact:    ("drug"[tiab]) AND ("disease"[tiab])  -- the original pipeline query
expanded: (drug) AND (disease)                  -- PubMed Automatic Term Mapping (MeSH, supplementary concepts, synonyms)
Output: outputs/pubmed_counts_v2.json"""
import json, os, time, urllib.parse, urllib.request, sys
T = "2026/06/05"; OUT = "outputs/pubmed_counts_v2.json"
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
def count(term):
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "0"}
    for _ in range(6):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=60) as r:
                d = json.loads(r.read().decode()); time.sleep(0.36)
                return int(d["esearchresult"]["count"])
        except Exception:
            time.sleep(4)
    return -1
Q = {"exact": lambda t: f'("{t}"[tiab])', "expanded": lambda t: f"({t})"}
frame = json.load(open("outputs/frame_v2.json"))
extra = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else []   # optional extra pairs [{"drug","disease"}]
pairs = {(r["drug"], r["disease"]) for r in frame} | {(r["drug"], r["disease"]) for r in extra}
C = json.load(open(OUT)) if os.path.exists(OUT) else {"single": {}, "pair": {}, "N": {}}
for k in Q:
    C["single"].setdefault(k, {}); C["pair"].setdefault(k, {})
for i, (a, c) in enumerate(sorted(pairs)):
    for k, q in Q.items():
        for t in (a, c):
            if C["single"][k].get(t, -1) < 0: C["single"][k][t] = count(q(t))
        key = f"{a}||{c}"
        if C["pair"][k].get(key, -1) < 0: C["pair"][k][key] = count(f"{q(a)} AND {q(c)}")
    if i % 25 == 0: json.dump(C, open(OUT, "w"), ensure_ascii=False); print(i, len(pairs), a, c, C["pair"]["exact"][f"{a}||{c}"], C["pair"]["expanded"][f"{a}||{c}"], flush=True)
if C["N"].get("all", -1) < 0: C["N"]["all"] = count('("1800/01/01"[PDAT] : "2026/06/05"[PDAT])')
json.dump(C, open(OUT, "w"), ensure_ascii=False); print("done; N =", C["N"]["all"])
