#!/usr/bin/env python3
"""Score the blinded human validation (lodged scoring plan: scoring_plan.md).
Usage: python3 score_human.py expert1.xlsx expert2.xlsx adjudication.xlsx [free_search_expert1.xlsx free_search_expert2.xlsx]
   or: python3 score_human.py --merged 合并结果表_作者填写.xlsx
- expert workbooks: sheet "Coding", label in column E (L0/L1/L2).
- adjudication workbook (optional): same layout, filled only for rows where the experts disagree; a third expert or the
  two experts in discussion record the agreed label. Without it, disagreements are reported but the consensus is incomplete.
Reports: human-human kappa; each expert and the adjudicated consensus vs final machine labels (kappa with bootstrap CI,
stratum-weighted agreement, precision and recall per level); prior-knowledge share reweighted to the full sample of 398."""
import sys, json, random
from collections import Counter
from openpyxl import load_workbook
HERE = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."
def read(f):
    ws = load_workbook(f)["Coding"]
    return {int(r[0]): str(r[4] or "").strip().upper()[:2] for r in ws.iter_rows(min_row=2, values_only=True) if r[0]}
def kappa(a, b, ks):
    ks = [k for k in ks if a.get(k) in ("L0","L1","L2") and b.get(k) in ("L0","L1","L2")]; n = len(ks)
    po = sum(a[k] == b[k] for k in ks) / n; ca, cb = Counter(a[k] for k in ks), Counter(b[k] for k in ks)
    pe = sum(ca[c] * cb[c] for c in ca) / n / n; return (po - pe) / (1 - pe), po, n
def boot_kappa(a, b, ks, B=5000, seed=1):
    rng = random.Random(seed); v = []
    for _ in range(B):
        s = [rng.choice(ks) for _ in ks]
        try: v.append(kappa(a, b, s)[0])
        except ZeroDivisionError: pass
    v.sort(); return v[int(.025 * len(v))], v[int(.975 * len(v))]
key = {x["no"]: x["key"] for x in json.load(open(f"{HERE}/answer_key_DO_NOT_SEND.json"))}
final = json.load(open(f"{HERE}/../final_labels_firstpass.json"))  # labels from the same six records the experts see
strat = {x["no"]: x["stratum_machine_coderA"] for x in json.load(open(f"{HERE}/answer_key_DO_NOT_SEND.json"))}
m = {i: final[key[i]] for i in key}
MERGED = sys.argv[1] == "--merged"   # alternative input: one merged workbook (合并结果表_作者填写.xlsx), cols D/E = experts, G = adjudicated
def read_merged(f, sheet):
    ws = load_workbook(f)[sheet]; g = lambda v: str(v or "").strip().upper()[:2]
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    return ({int(r[0]): g(r[3]) for r in rows}, {int(r[0]): g(r[4]) for r in rows}, {int(r[0]): g(r[6]) for r in rows})
if MERGED: h1, h2, adj = read_merged(sys.argv[2], "第一部分_150")
else: h1, h2 = read(sys.argv[1]), read(sys.argv[2]); adj = read(sys.argv[3]) if len(sys.argv) > 3 else {}
ks = sorted(key)
print("human-human kappa %.3f, agreement %.3f, n %d" % kappa(h1, h2, ks))
cons = {}
for i in ks:
    if h1.get(i) == h2.get(i): cons[i] = h1[i]
    elif adj.get(i) in ("L0","L1","L2"): cons[i] = adj[i]
print("consensus available for", len(cons), "of", len(ks), "(unresolved disagreements:", len([i for i in ks if i not in cons]), ")")
for name, h in (("expert 1", h1), ("expert 2", h2), ("consensus", cons)):
    k_, po, n = kappa(h, m, ks); lo, hi = boot_kappa(h, m, [i for i in ks if i in h])
    print(f"{name} vs machine: kappa {k_:.3f} (95% CI {lo:.3f}-{hi:.3f}), raw agreement {po:.3f}, n {n}")
# stratum weights: machine-label distribution among the 300 read pairs (sampling frame of the validation)
frame = Counter(v for v in final.values() if v in ("L0","L1","L2"))
read_pairs = json.load(open(f"{HERE}/../adjudication.json"))  # not used for weights; frame below uses read pairs
A = {}
import glob
for p in glob.glob(f"{HERE}/../coder_A/*.json"): A.update({x["key"]: x["label"] for x in json.load(open(p))})
W = Counter(A.values()); sampled = Counter(strat.values())
w = {s: W[s] / sampled[s] for s in sampled}
c = [i for i in ks if i in cons]
wa = sum(w[strat[i]] * (cons[i] == m[i]) for i in c) / sum(w[strat[i]] for i in c)
print(f"stratum-weighted agreement consensus vs machine: {wa:.3f}")
for L in ("L0","L1","L2"):
    tp = sum(w[strat[i]] * (m[i] == L and cons[i] == L) for i in c); pp = sum(w[strat[i]] * (m[i] == L) for i in c); ap = sum(w[strat[i]] * (cons[i] == L) for i in c)
    print(f"  {L}: machine precision {tp/pp if pp else float('nan'):.3f}, recall {tp/ap if ap else float('nan'):.3f}")
# reweighted prior-knowledge share for the full 398-item sample: machine L-level x human transition rates
frame_items = json.load(open(f"{HERE}/../../outputs/frame_v2.json"))
full = Counter(final[f"{r['drug']}||{r['disease']}"] for r in frame_items)
zero_L2 = sum(1 for r in frame_items if final[f"{r['drug']}||{r['disease']}"] == "L2") - sum(1 for r in frame_items if f"{r['drug']}||{r['disease']}" in A and final[f"{r['drug']}||{r['disease']}"] == "L2")
def est(sample):
    T = {L: Counter() for L in ("L0","L1","L2")}
    for i in sample: T[m[i]][cons[i]] += 1
    read_items = Counter(final[f"{r['drug']}||{r['disease']}"] for r in frame_items if f"{r['drug']}||{r['disease']}" in A)
    tot = sum(full[L] for L in ("L0","L1","L2")); pk = 0
    for L in ("L0","L1","L2"):
        n_ = sum(T[L].values()); share = (T[L]["L0"] + T[L]["L1"]) / n_ if n_ else (1.0 if L != "L2" else 0.0)
        pk += read_items[L] * share
    return pk / tot   # zero-co-occurrence L2 items (not read, not in sample) are kept as L2
pt = est(c); rng = random.Random(2); bs = []
by = {L: [i for i in c if m[i] == L] for L in ("L0","L1","L2")}
for _ in range(5000): bs.append(est([rng.choice(by[L]) for L in by for _ in by[L]]))
bs.sort(); print(f"human-reweighted prior-knowledge share: {100*pt:.1f}% (95% CI {100*bs[125]:.1f}-{100*bs[4875]:.1f})")

# ---- part 2: free-search check of zero-co-occurrence L2 pairs (optional 4th and 5th arguments: expert1 and expert2 free-search workbooks)
if len(sys.argv) > 5 or MERGED:
    def readfs(f):
        ws = load_workbook(f)["FreeSearch"]; return {int(r[0]): str(r[3] or "").strip().upper()[:2] for r in ws.iter_rows(min_row=2, values_only=True) if r[0]}
    if MERGED: a, b, fadj = read_merged(sys.argv[2], "第二部分_30")
    else: a, b, fadj = readfs(sys.argv[4]), readfs(sys.argv[5]), {}
    ks2 = sorted(a)
    if MERGED and all(a.get(i) in ("L0","L1","L2") for i in ks2):
        fc = {i: (a[i] if a[i] == b.get(i) else fadj.get(i, "")) for i in ks2}
        nc = sum(1 for i in ks2 if fc[i] in ("L0","L1","L2")); c2 = sum(1 for i in ks2 if fc[i] == "L2")
        print(f"free search (adjudicated consensus): {c2} of {nc} confirmed L2; unresolved {len(ks2)-nc}")
    agree = [i for i in ks2 if a[i] == b.get(i)]
    conf = sum(1 for i in agree if a[i] == "L2")
    import math
    n = len(agree); p = conf / n if n else float("nan"); z = 1.959964
    lo = (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n) if n else float("nan")
    print(f"free search: experts agree on {n} of {len(ks2)}; of these, {conf} confirmed L2 ({100*p:.1f}%, Wilson lower bound {100*lo:.1f}%)")
