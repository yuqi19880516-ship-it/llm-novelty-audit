#!/usr/bin/env python3
"""Post hoc (2026-10-03): scientometric coding of the 27 frame items skipped by audit_sample.py
(memory probe failed). Same T, same PubMed queries, same coding rule; no LLM call, no L0 abstract check,
provenance left missing. Output: outputs/skipped27_coded.jsonl"""
import json
from audit_pipeline.provenance import PubMedProvenanceSearcher, PubMedCorpusStats
from audit_pipeline.novelty import score
T = "2026/06/05"
sample = json.load(open("outputs/sample.json"))
done = {json.loads(l)["id"] for l in open("outputs/coded_sample.jsonl") if l.strip()}
skipped = [h for h in sample if f"{h['model']}_{h['goal_id']}_{h['drug']}" not in done]
print("skipped", len(skipped))
searcher = PubMedProvenanceSearcher(); cache = {}
out = open("outputs/skipped27_coded.jsonl", "w")
for h in skipped:
    try:
        st = cache.setdefault(h["disease"], PubMedCorpusStats(T, searcher))
        cooc = st.n_ac(h["drug"], h["disease"]); ns = score(st, h["drug"], h["disease"])
        L = "L1" if cooc >= 5 else ("L2" if ns.atypical else "L1")
        rec = {"id": f"{h['model']}_{h['goal_id']}_{h['drug']}", "model": h["model"], "goal_id": h["goal_id"],
               "drug": h["drug"], "disease": h["disease"], "stratum": h["stratum"], "self_novelty": h["self_novelty"],
               "cooc": cooc, "z": ns.cooccurrence_z, "disjoint": ns.disjoint, "atypical": ns.atypical, "L_provisional": L}
    except Exception as e:
        rec = {"id": f"{h['model']}_{h['goal_id']}_{h['drug']}", "error": f"{type(e).__name__}: {e}"}
    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush(); print(rec.get("drug"), rec.get("cooc"), rec.get("L_provisional", rec.get("error")), flush=True)
