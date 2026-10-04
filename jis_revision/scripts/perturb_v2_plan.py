#!/usr/bin/env python3
"""Build the perturbation-v2 plan (2026-10-03): for each frame_v2 item choose (seeded) another study target with zero
expanded PubMed co-occurrence with the drug before T, and a synthetic compound name with zero PubMed hits.
Queries are cached in outputs/perturb_v2_qcache.json and run with 3 parallel workers (NCBI limit)."""
import json, os, random, time, threading, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
T = "2026/06/05"; ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"; QC = "outputs/perturb_v2_qcache.json"
cache = json.load(open(QC)) if os.path.exists(QC) else {}; lock = threading.Lock()
def count(term):
    if term in cache and cache[term] >= 0: return cache[term]
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "0"}
    v = -1
    for _ in range(6):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=30) as r:
                v = int(json.loads(r.read().decode())["esearchresult"]["count"]); break
        except Exception: time.sleep(3)
    time.sleep(1.0)
    with lock: cache[term] = v
    return v
frame = json.load(open("outputs/frame_v2.json")); targets = sorted({r["disease"] for r in frame})
rng = random.Random(20261003)
order = {r["id"]: (lambda o: (rng.shuffle(o), o)[1])([t for t in targets if t != r["disease"]]) for r in frame}
drugs = sorted({r["drug"] for r in frame})
# pre-query all drug x target pairs in parallel (3 workers, ~1 req/s each)
todo = [f"({d}) AND ({t})" for d in drugs for t in targets]
print("queries", len(todo), "cached", sum(1 for q in todo if cache.get(q, -1) >= 0), flush=True)
def job(q):
    count(q)
with ThreadPoolExecutor(3) as ex:
    for i, _ in enumerate(ex.map(job, todo)):
        if i % 200 == 0:
            with lock: json.dump(cache, open(QC, "w"))
            print(i, flush=True)
json.dump(cache, open(QC, "w"))
SYL1 = ["Vel", "Tor", "Zan", "Quel", "Bri", "Lor", "Fex", "Nor", "Dar", "Pel", "Ros", "Kel", "Mir", "Tav", "Sol"]
SYL2 = ["avor", "ixan", "otel", "umar", "ezol", "atin", "iprel", "onex", "aril", "uvan"]
STEM = ["tinib", "zumab", "pril", "sartan", "gliptin", "statin", "mycin", "afil", "olol", "dronate"]
used = set(); plan = []
for r in frame:
    cf = next((t for t in order[r["id"]] if cache.get(f"({r['drug']}) AND ({t})", -1) == 0), None)
    while True:
        n = rng.choice(SYL1) + rng.choice(SYL2) + rng.choice(STEM)
        if n not in used and count(n) == 0: used.add(n); break
    plan.append({"id": r["id"], "model": r["model"], "drug": r["drug"], "disease": r["disease"], "cf_disease": cf, "synthetic": n})
json.dump(cache, open(QC, "w")); json.dump(plan, open("outputs/perturb_v2_plan.json", "w"), ensure_ascii=False, indent=1)
print("plan done; no counterfactual:", sum(1 for p in plan if p["cf_disease"] is None))
