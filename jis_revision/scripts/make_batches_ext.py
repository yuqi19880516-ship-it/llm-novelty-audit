#!/usr/bin/env python3
"""Batches for the extended check (codebook v2 + addendum). Usage: python3 make_batches_ext.py <name> <keys-json-or-'all'> <n_batches>"""
import json, os, random, sys
A = json.load(open("outputs/l2_extended.json")); name = sys.argv[1]
keys = sorted(A) if sys.argv[2] == "all" else json.load(open(sys.argv[2]))
random.Random(9).shuffle(keys); B = int(sys.argv[3]); size = -(-len(keys) // B)
os.makedirs(f"coding_materials_v2/batches_{name}", exist_ok=True)
for b in range(B):
    items = [{"key": k, "drug": k.split("||")[0], "disease": k.split("||")[1], "parent_term": A[k]["parent_term"],
              "same": A[k]["same"], "parent": A[k]["parent"]} for k in keys[b * size:(b + 1) * size]]
    json.dump(items, open(f"coding_materials_v2/batches_{name}/batch_{b:02d}.json", "w"), ensure_ascii=False, indent=1)
print(len(keys), "items;", B, "batches")
