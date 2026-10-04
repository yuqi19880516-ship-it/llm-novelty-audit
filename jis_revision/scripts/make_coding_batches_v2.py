#!/usr/bin/env python3
"""Blinded coding batches for codebook v2: one entry per unique drug–disease pair with >=1 fetched record.
No system, model, rank or self-rating information. Order shuffled (seed 7). Writes coding_materials_v2/batches/batch_NN.json"""
import json, os, random
A = json.load(open("outputs/abstracts_v2.json"))
keys = sorted(k for k, v in A.items() if v); random.Random(7).shuffle(keys)
os.makedirs("coding_materials_v2/batches", exist_ok=True)
B = 8; size = -(-len(keys) // B)
for b in range(B):
    chunk = keys[b * size:(b + 1) * size]
    items = [{"key": k, "drug": k.split("||")[0], "disease": k.split("||")[1],
              "records": [{"pmid": r["pmid"], "year": r["year"], "title": r["title"], "abstract": r["abstract"]} for r in A[k]]} for k in chunk]
    json.dump(items, open(f"coding_materials_v2/batches/batch_{b:02d}.json", "w"), ensure_ascii=False, indent=1)
print(len(keys), "pairs in", B, "batches of <=", size)
