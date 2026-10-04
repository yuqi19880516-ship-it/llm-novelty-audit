#!/usr/bin/env python3
"""Post hoc frame v2 (2026-10-03): 334 original items + 67 items recovered by translating Chinese-script drug names.
Adds evolved flag (n_reviews < 3: produced by the Evolution agent) and recomputes rank strata within each run."""
import json, glob
from collections import defaultdict
sample = json.load(open("outputs/sample.json")); tr = json.load(open("outputs/translated_items.json"))
gen = {}
for fn in glob.glob("outputs/generation/*.json"):
    d = json.load(open(fn)); m = fn.split("/")[-1].rsplit("_", 1)[0]
    for i, h in enumerate(d["hypotheses"]): gen[(m, d["goal_id"], i)] = h
frame = []
for h in sample:
    if h["drug"] == "ALS": continue  # malformed: hypothesis names no drug (A = "ALS", B = "Drug Repurposing")
    g = gen[(h["model"], h["goal_id"], h["rank"])]
    frame.append({"id": f"{h['model']}_{h['goal_id']}_{h['drug']}", "model": h["model"], "goal_id": h["goal_id"], "disease": h["disease"],
                  "drug": h["drug"], "rank": h["rank"], "self_novelty": h["self_novelty"], "evolved": len(g.get("reviews") or []) < 3,
                  "b": h.get("b", ""), "source": "parsed"})
for h in tr:
    g = gen[(h["model"], h["goal_id"], h["rank"])]
    frame.append({"id": f"{h['model']}_{h['goal_id']}_{h['drug']}", "model": h["model"], "goal_id": h["goal_id"], "disease": h["disease"],
                  "drug": h["drug"], "rank": h["rank"], "self_novelty": h["self_novelty"], "evolved": len(g.get("reviews") or []) < 3,
                  "b": g.get("b", ""), "source": "translated", "drug_zh": h["drug_zh"]})
cells = defaultdict(list)
for r in frame: cells[(r["model"], r["goal_id"])].append(r)
for c in cells.values():
    c.sort(key=lambda r: r["rank"]); n = len(c)
    for i, r in enumerate(c): r["stratum"] = ["top", "mid", "bottom"][min(2, i * 3 // n)]
json.dump(frame, open("outputs/frame_v2.json", "w"), ensure_ascii=False, indent=1)
print(len(frame), "items;", sum(r["evolved"] for r in frame), "evolved;", len(cells), "cells")
