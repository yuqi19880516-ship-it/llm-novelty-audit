#!/usr/bin/env python3
"""Blinded coding batches for the permutation baseline (and ripasudil-AMD), same format and codebook as the main coding.
Writes coding_materials_v2/batches_perm/batch_NN.json (shuffled, seed 8)."""
import json, os, random
A = json.load(open("outputs/abstracts_perm.json")); keys = sorted(k for k, v in A.items() if v); random.Random(8).shuffle(keys)
os.makedirs("coding_materials_v2/batches_perm", exist_ok=True); B = 6; size = -(-len(keys) // B)
for b in range(B):
    items = [{"key": k, "drug": k.split("||")[0], "disease": k.split("||")[1], "records": A[k]} for k in keys[b * size:(b + 1) * size]]
    json.dump(items, open(f"coding_materials_v2/batches_perm/batch_{b:02d}.json", "w"), ensure_ascii=False, indent=1)
print(len(keys), "pairs;", sum(1 for v in A.values() if not v), "with no records")
