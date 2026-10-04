#!/usr/bin/env python3
"""Memory probe v2 (run 2026-10-03; replaces the June probe, whose replies were not archived).
Asks the generating base model, closed-book, whether a published link exists; archives every raw reply.
Usage: python3 probe_v2.py items.json out.jsonl   (items: [{"id","model","drug","disease"}])"""
import json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from llm_threadsafe import complete as llm_complete
PROMPT = ('Answer from your own knowledge only, without searching. Before 2026, had {drug} been proposed, studied or used as a '
          'treatment for {disease} in the published biomedical literature? Reply with JSON only: '
          '{{"status": "published_evidence" | "plausible_but_not_known" | "no_known_link", '
          '"evidence": "one sentence naming the kind of study or paper you recall, or empty"}}')
items = json.load(open(sys.argv[1])); out = sys.argv[2]
done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
lock = threading.Lock()
def parse(t):
    m = re.search(r'"status"\s*:\s*"(published_evidence|plausible_but_not_known|no_known_link)"', t)
    return m.group(1) if m else "?"
def run(it):
    if it["id"] in done: return
    raw = ""; err = ""
    for k in range(4):
        try:
            raw = llm_complete(it["model"], PROMPT.format(drug=it["drug"], disease=it["disease"]))
            if raw.strip(): break
        except Exception as e: err = f"{type(e).__name__}: {e}"[:200]; time.sleep(5)
    rec = {**it, "status": parse(raw), "raw": raw, "error": err, "run_at": time.strftime("%Y-%m-%d %H:%M")}
    with lock:
        open(out, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
with ThreadPoolExecutor(8) as ex: list(ex.map(run, items))
print("done", sum(1 for _ in open(out)))
