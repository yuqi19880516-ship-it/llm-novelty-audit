#!/usr/bin/env python3
"""Perturbation test v2 (run 2026-10-03), implementing the preregistered forms more closely than the June run.
For each frame_v2 item, the generating base model judges closed-book, at temperature 0, whether a repurposing hypothesis holds for:
  original     (drug A, target disease C)
  unrelated    (drug A, another study target C' with ZERO expanded PubMed co-occurrence with A before T)
  synthetic    (a fictitious but valid-looking compound name, verified to have zero PubMed hits, for disease C)
Raw replies are archived. Output: outputs/perturb_v2.jsonl"""
import json, os, re, sys, time, random, threading, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from llm_threadsafe import complete as llm_complete
T = "2026/06/05"; OUT = "outputs/perturb_v2.jsonl"; ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
def count(term):
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "0"}
    for _ in range(6):
        try:
            with urllib.request.urlopen(ES + "?" + urllib.parse.urlencode(p), timeout=60) as r:
                time.sleep(0.36); return int(json.loads(r.read().decode())["esearchresult"]["count"])
        except Exception: time.sleep(4)
    return -1
PROMPT = ("You are a pharmacology expert. Using only your existing knowledge, without consulting any source, judge whether the "
          "following drug-repurposing hypothesis holds.\nDrug: {drug}\nProposed indication: {disease}\n"
          "Answer in exactly two lines, without further reasoning:\nVerdict: <yes/doubtful/no>\nEvidence strength: <strong/medium/weak/speculative>")
def parse(t):
    v = re.findall(r"Verdict:\s*<?\s*(yes|doubtful|no)\b", t, re.I); b = re.findall(r"Evidence strength:\s*<?\s*(strong|medium|weak|speculative)", t, re.I)
    return (v[-1].lower() if v else "?"), (b[-1].lower() if b else "?")
frame = json.load(open("outputs/frame_v2.json")); C = json.load(open("outputs/pubmed_counts_v2.json"))
targets = sorted({r["disease"] for r in frame})
rng = random.Random(20261003)
# synthetic names: pharmacological stems, each verified absent from PubMed
SYL1 = ["Vel", "Tor", "Zan", "Quel", "Bri", "Lor", "Fex", "Nor", "Dar", "Pel", "Ros", "Kel", "Mir", "Tav", "Sol"]
SYL2 = ["avor", "ixan", "otel", "umar", "ezol", "atin", "iprel", "onex", "aril", "uvan"]
STEM = ["tinib", "zumab", "pril", "sartan", "gliptin", "statin", "mycin", "afil", "olol", "dronate"]
synth_cache = {}
def synthetic():
    while True:
        n = rng.choice(SYL1) + rng.choice(SYL2) + rng.choice(STEM)
        if n in synth_cache: continue
        if count(f"{n}") == 0: synth_cache[n] = 1; return n
plan_path = "outputs/perturb_v2_plan.json"
if os.path.exists(plan_path): plan = json.load(open(plan_path))
else:
    plan = []
    for r in frame:
        others = [t for t in targets if t != r["disease"]]; rng.shuffle(others); cf = None
        for t in others:
            if count(f"({r['drug']}) AND ({t})") == 0: cf = t; break
        plan.append({"id": r["id"], "model": r["model"], "drug": r["drug"], "disease": r["disease"], "cf_disease": cf, "synthetic": synthetic()})
    json.dump(plan, open(plan_path, "w"), ensure_ascii=False, indent=1)
print("plan ready; items without zero-co-occurrence counterfactual:", sum(1 for p in plan if p["cf_disease"] is None), flush=True)
done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
lock = threading.Lock()
def ask(model, drug, dis):
    if dis is None: return {"verdict": "NA", "basis": "NA", "raw": ""}
    raw = ""
    for k in range(4):
        try:
            raw = llm_complete(model, PROMPT.format(drug=drug, disease=dis))
            if raw.strip(): break
        except Exception as e: raw = ""; time.sleep(5)
    v, b = parse(raw); return {"verdict": v, "basis": b, "raw": raw}
def run(p):
    if p["id"] in done: return
    rec = {**p, "original": ask(p["model"], p["drug"], p["disease"]), "unrelated": ask(p["model"], p["drug"], p["cf_disease"]),
           "synthetic_form": ask(p["model"], p["synthetic"], p["disease"]), "run_at": time.strftime("%Y-%m-%d %H:%M")}
    with lock: open(OUT, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
with ThreadPoolExecutor(8) as ex: list(ex.map(run, plan))
print("done", sum(1 for _ in open(OUT)))
