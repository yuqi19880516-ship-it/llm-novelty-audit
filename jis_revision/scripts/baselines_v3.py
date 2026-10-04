#!/usr/bin/env python3
"""Post hoc baselines (2026-10-03), synonym-expanded PubMed counts up to T:
(1) permutation baseline: each frame drug paired with a random other study target (seed 20261004);
(2) bare base model (ablation) pairs; (3) Robin first-stage candidates x "age-related macular degeneration" (T = 2025/05/28),
plus ripasudil. Reuses outputs/perturb_v2_qcache.json. Output: outputs/baselines_v3.json"""
import json, os, time, urllib.parse, urllib.request
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"; QC = "outputs/perturb_v2_qcache.json"
cache = json.load(open(QC))
def count(term, T="2026/06/05"):
    k = term if T == "2026/06/05" else f"{term}@@{T}"
    if cache.get(k, -1) >= 0: return cache[k]
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "0"}
    v = -1
    for _ in range(6):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=30) as r:
                v = int(json.loads(r.read().decode())["esearchresult"]["count"]); break
        except Exception: time.sleep(3)
    time.sleep(0.4); cache[k] = v; return v
perm = json.load(open("outputs/permuted_baseline_pairs.json"))
bare = json.load(open("outputs/bare_coded_final_v2.json"))
rob = json.load(open("outputs/robin/robin_coded.json"))
out = {"perm": [], "bare": [], "robin": []}
for p in perm: out["perm"].append({**p, "ex": count(f"({p['drug']}) AND ({p['disease']})")})
print("perm done", flush=True)
for i, r in enumerate(bare):
    out["bare"].append({"model": r["model"], "goal_id": r["goal_id"], "drug": r["drug"], "disease": r["disease"],
                        "ex": count(f"({r['drug']}) AND ({r['disease']})"), "n_drug": count(f"({r['drug']})")})
    if i % 50 == 0: json.dump(cache, open(QC, "w")); print("bare", i, flush=True)
AMD = "age-related macular degeneration"; TR = "2025/05/28"
for r in rob + [{"drug": "Ripasudil"}]:
    out["robin"].append({"drug": r["drug"], "ex": count(f"({r['drug']}) AND ({AMD})", TR), "n_drug": count(f"({r['drug']})", TR)})
json.dump(cache, open(QC, "w")); json.dump(out, open("outputs/baselines_v3.json", "w"), ensure_ascii=False, indent=1)
print("done", {k: sum(x["ex"] < 0 for x in v) for k, v in out.items()})
