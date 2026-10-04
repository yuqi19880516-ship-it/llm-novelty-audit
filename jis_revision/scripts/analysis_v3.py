#!/usr/bin/env python3
"""Analysis v3 (2026-10-03) for the JIS revision. Reads the 400-item frame, expanded PubMed counts, the dual-coder
reading of all co-occurring pairs (with adjudication), probe v2, perturbation v2 and baseline counts.
Writes coding_materials_v2/final_labels.json and outputs/analysis_v3.json; prints a report."""
import json, glob, math, random, os
from collections import Counter, defaultdict
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

R = json.load
f = R(open("outputs/frame_v2.json")); C = R(open("outputs/pubmed_counts_v2.json"))
key = lambda r: f"{r['drug']}||{r['disease']}"
EX = lambda k: C["pair"]["expanded"][k]; XA = lambda k: C["pair"]["exact"][k]
SE = lambda t: C["single"]["expanded"][t]
A, B = {}, {}
for p in glob.glob("coding_materials_v2/coder_A/*.json"): A.update({x["key"]: x["label"] for x in R(open(p))})
for p in glob.glob("coding_materials_v2/coder_B/*.json"): B.update({x["key"]: x["label"] for x in R(open(p))})
ADJ = {x["key"]: x["final_label"] for x in R(open("coding_materials_v2/adjudication.json"))}
OUT = {}
def wilson(k, n, z=1.959964):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h), 1), round(100 * (c + h), 1)
def pct(k, n): return f"{k}/{n} = {100*k/n:.1f}% (95% CI {wilson(k,n)[0]}–{wilson(k,n)[1]})"
def kappa(a, b):
    ks = [k for k in a if k in b]; n = len(ks); po = sum(a[k] == b[k] for k in ks) / n
    ca, cb = Counter(a[k] for k in ks), Counter(b[k] for k in ks); pe = sum(ca[c] * cb[c] for c in ca) / n / n
    return (po - pe) / (1 - pe), po, n

# ---------- final labels ----------
final = {}
for k in {key(r) for r in f}:
    if EX(k) == 0:
        final[k] = "L2" if min(SE(k.split("||")[0]), SE(k.split("||")[1])) >= 100 else "IND"
    elif A.get(k) == B.get(k): final[k] = A[k]
    else: final[k] = ADJ[k]
# ---------- extended check overrides (L2 pairs and L1 pairs with >6 records, both arms) ----------
EXT = {}; EXT_STATS = {}
def load_ext(tag):
    a = f"coding_materials_v2/coder_A_{tag}/all.json"; b = f"coding_materials_v2/coder_B_{tag}/all.json"; j = f"coding_materials_v2/adjudication_{tag}.json"
    if not (os.path.exists(a) and os.path.exists(b)): return
    XA_ = {x["key"]: x["label"] for x in R(open(a))}; XB_ = {x["key"]: x["label"] for x in R(open(b))}
    XJ = {x["key"]: x["final_label"] for x in R(open(j))} if os.path.exists(j) else {}
    kk = kappa(XA_, XB_); EXT_STATS[tag] = (round(kk[0], 2), round(100 * kk[1], 1), kk[2], sum(XA_[k] != XB_[k] for k in XA_ if k in XB_))
    for k in XA_:
        EXT[k] = XA_[k] if XA_[k] == XB_.get(k) else XJ.get(k, "UNRES")
load_ext("extL2"); load_ext("extL1")
EXT_BROAD = dict(EXT)
def _src(tag):
    out = {}
    a = R(open(f"coding_materials_v2/coder_A_{tag}/all.json")); b = {x["key"]: x for x in R(open(f"coding_materials_v2/coder_B_{tag}/all.json"))}
    j = {x["key"]: x for x in R(open(f"coding_materials_v2/adjudication_{tag}.json"))} if os.path.exists(f"coding_materials_v2/adjudication_{tag}.json") else {}
    for x in a:
        k = x["key"]
        if x["label"] == b[k]["label"]: out[k] = "parent" if (x.get("source") == "parent" and b[k].get("source") == "parent") else "same"
        elif k in j: out[k] = j[k].get("source", "same")
    return out
SRC0 = {**_src("extL2"), **_src("extL1")}
for k in EXT:
    if EXT[k] == "L1" and SRC0.get(k) == "parent": EXT[k] = "L2"   # primary construct: target disease and its subtypes only
# target-equivalent recheck (PDAC, IPF, NASH): parent category counts as target disease
TE = {}
if os.path.exists("coding_materials_v2/coder_A_extTE/all.json") and os.path.exists("coding_materials_v2/coder_B_extTE/all.json"):
    TA = {x["key"]: x["label"] for x in R(open("coding_materials_v2/coder_A_extTE/all.json"))}; TB = {x["key"]: x["label"] for x in R(open("coding_materials_v2/coder_B_extTE/all.json"))}
    TJ = {x["key"]: x["final_label"] for x in R(open("coding_materials_v2/adjudication_extTE.json"))} if os.path.exists("coding_materials_v2/adjudication_extTE.json") else {}
    kt = kappa(TA, TB); EXT_STATS["extTE"] = (round(kt[0], 2), round(100 * kt[1], 1), kt[2], sum(TA[k] != TB[k] for k in TA))
    for k in TA: TE[k] = TA[k] if TA[k] == TB.get(k) else TJ.get(k, "UNRES")
    for k, v in TE.items():
        EXT[k] = v; EXT_BROAD[k] = v if v != "L2" or EXT_BROAD.get(k) != "L1" else "L1"
RANK = {"L0": 0, "L1": 1, "L2": 2}
def higher(a, b):   # max rule: a re-check never lowers a label (its drug-name filter can miss synonyms)
    if a not in RANK or b not in RANK: return b if a not in RANK else a
    return a if RANK[a] <= RANK[b] else b
first_pass = dict(final)
for k in list(final):
    if k in EXT: final[k] = higher(first_pass[k], EXT[k])
json.dump(final, open("coding_materials_v2/final_labels.json", "w"), ensure_ascii=False, indent=1)
json.dump(first_pass, open("coding_materials_v2/final_labels_firstpass.json", "w"), ensure_ascii=False, indent=1)
for r in f: r["L"] = final[key(r)]; r["ex"] = EX(key(r)); r["xa"] = XA(key(r)); r["run"] = r["model"] + "_" + r["goal_id"]
print("=== 0. extended check", EXT_STATS, "| overrides", sum(1 for k in final if k in EXT), "| unresolved", sum(1 for k in final if final[k] == "UNRES"))
print("  system transitions first pass -> extended:", Counter((first_pass[k], final[k]) for k in final if k in EXT))
k_, po_, n_ = kappa(A, B)
print("=== 1. coding reliability"); print(f"pairs read {n_}; agreement {po_:.3f}; Cohen kappa {k_:.3f}; disagreements adjudicated {len(ADJ)}",
      "| adjudicated to", Counter(ADJ.values()))
OUT["kappa"] = round(k_, 2); OUT["agree"] = round(100 * po_, 1); OUT["n_read"] = n_
for lab in ("L0", "L1", "L2"):
    a_ = {k: int(v == lab) for k, v in A.items()}; b_ = {k: int(v == lab) for k, v in B.items()}
    print(f"  {lab} vs rest kappa {kappa(a_, b_)[0]:.2f}")

# ---------- 2. spectrum ----------
F = [r for r in f if r["L"] != "IND"]; N = len(F)
print("\n=== 2. spectrum (n items =", len(f), "; indeterminate", sum(r["L"] == "IND" for r in f), ")")
c = Counter(r["L"] for r in F)
for lab in ("L0", "L1", "L2"): print(f"  {lab}: {pct(c[lab], N)}")
k01 = c["L0"] + c["L1"]; print("  L0∪L1:", pct(k01, N), "| one-sided exact binomial p vs 0.5:", stats.binomtest(k01, N, 0.5, alternative="greater").pvalue)
runs = defaultdict(list)
for r in F: runs[r["run"]].append(r)
rk = list(runs); rng = random.Random(1); bs = defaultdict(list)
for _ in range(20000):
    d = [rng.choice(rk) for _ in rk]; v = [x for k in d for x in runs[k]]
    for lab in ("L0", "L1", "L2"): bs[lab].append(100 * sum(x["L"] == lab for x in v) / len(v))
    bs["L01"].append(100 * sum(x["L"] in ("L0", "L1") for x in v) / len(v))
cb = {k: (round(np.percentile(v, 2.5), 1), round(np.percentile(v, 97.5), 1)) for k, v in bs.items()}
print("  cluster bootstrap (runs) 95% CI:", cb)
OUT["spectrum"] = {lab: [c[lab], N, round(100 * c[lab] / N, 1), wilson(c[lab], N)] for lab in ("L0", "L1", "L2")}
OUT["L01"] = [k01, N, round(100 * k01 / N, 1), wilson(k01, N), cb["L01"]]; OUT["cluster"] = cb
# per source / model / target
for g in ("source", "model"):
    for v in sorted({r[g] for r in F}):
        s = [r for r in F if r[g] == v]; cc = Counter(r["L"] for r in s)
        print(f"  {g}={v}: n={len(s)} L0 {100*cc['L0']/len(s):.1f} L1 {100*cc['L1']/len(s):.1f} L2 {100*cc['L2']/len(s):.1f}")
print("  per target L2 share:")
tg = {}
for t in sorted({r["disease"] for r in F}):
    s = [r for r in F if r["disease"] == t]; tg[t] = (len(s), round(100 * sum(r["L"] == "L2" for r in s) / len(s), 1), round(100 * sum(r["L"] == "L0" for r in s) / len(s), 1))
    print(f"    {t[:36]:36s} n={tg[t][0]:3d} L2 {tg[t][1]:5.1f}  L0 {tg[t][2]:5.1f}")
OUT["targets"] = tg

# ---------- 3. old screening coding vs reading (307 overlap) ----------
old = {json.loads(l)["id"]: json.loads(l) for l in open("outputs/coded_sample.jsonl") if l.strip()}
ov = [r for r in f if r["id"] in old and r["L"] != "IND"]
cm = Counter((old[r["id"]]["L_level"][:2], r["L"]) for r in ov)
print("\n=== 3. June machine coding (rows) vs v3 reading (cols), n =", len(ov))
for a in ("L0", "L1", "L2"): print("  ", a, [cm[(a, b)] for b in ("L0", "L1", "L2")])
ko = kappa({r["id"]: old[r["id"]]["L_level"][:2] for r in ov}, {r["id"]: r["L"] for r in ov})
print(f"  agreement {ko[1]:.3f} kappa {ko[0]:.2f}"); OUT["old_vs_new"] = {"cm": {f"{a}>{b}": cm[(a, b)] for a in ("L0","L1","L2") for b in ("L0","L1","L2")}, "kappa": round(ko[0], 2), "agree": round(100*ko[1],1), "n": len(ov)}
# exact-phrase disjoint pairs that have expanded co-occurrence
oldL2 = [r for r in ov if old[r["id"]]["L_level"].startswith("L2")]
print("  June-L2 items:", len(oldL2), "of which expanded co-occurrence >=1:", sum(r["ex"] >= 1 for r in oldL2), "| read as L2:", sum(r["L"] == "L2" for r in oldL2))

# ---------- 4. construct sensitivity ----------
print("\n=== 4. construct sensitivity")
s_ex0 = sum(r["xa"] == 0 for r in F); s_en0 = sum(r["ex"] == 0 for r in F)
print("  zero co-occurrence: exact-phrase", pct(s_ex0, N), "| expanded", pct(s_en0, N))
l2_read_pos = sum(1 for r in F if r["L"] == "L2" and r["ex"] >= 1)
print("  L2 items with co-occurrence but no stated link (read):", l2_read_pos, "| L2 with zero expanded co-occurrence:", sum(1 for r in F if r["L"]=="L2" and r["ex"]==0))
strict = sum(r["L"] == "L2" and r["ex"] == 0 for r in F); print("  strict L2 (zero expanded co-occurrence):", pct(strict, N))
OUT["construct"] = {"exact0": [s_ex0, N], "expanded0": [s_en0, N], "L2_read_pos": l2_read_pos, "strictL2": [strict, N]}
# label-narrowness: L2 vs disease literature size
dl = pd.DataFrame({"L2": [int(r["L"] == "L2") for r in F], "log_dis": [math.log10(SE(r["disease"])) for r in F], "log_drug": [math.log10(max(1, SE(r["drug"]))) for r in F]})
m = sm.Logit(dl["L2"], sm.add_constant(dl[["log_dis", "log_drug"]])).fit(disp=0)
print("  logit L2 ~ log10 literature sizes:", m.params.round(2).to_dict(), "p", m.pvalues.round(4).to_dict())
OUT["litsize"] = {k: [round(m.params[k], 2), float(m.pvalues[k])] for k in ("log_dis", "log_drug")}

# ---------- 5. base model ----------
print("\n=== 5. base model")
df = pd.DataFrame({"y": [int(r["L"] in ("L0", "L1")) for r in F], "qwen": [int(r["model"] == "qwen3.7-max") for r in F],
                   "goal": [r["goal_id"] for r in F], "run": [r["run"] for r in F], "evolved": [int(r["evolved"]) for r in F],
                   "transl": [int(r["source"] == "translated") for r in F]})
for mo in ("deepseek-v4-pro", "qwen3.7-max"):
    s = [r for r in F if r["model"] == mo]; k = sum(r["L"] in ("L0", "L1") for r in s); print(f"  {mo}: L0∪L1 {pct(k, len(s))}")
X = sm.add_constant(pd.get_dummies(df[["qwen", "goal"]], columns=["goal"], drop_first=True, dtype=float))
fit = sm.GLM(df["y"], X, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df["run"])[0]})
orq = math.exp(fit.params["qwen"]); ci = [math.exp(x) for x in fit.conf_int().loc["qwen"]]
print(f"  FE logit (target FE, run-clustered SE): OR Qwen {orq:.2f} ({ci[0]:.2f}–{ci[1]:.2f}) p={fit.pvalues['qwen']:.4f}")
pr = []
for g in sorted(df.goal.unique()):
    a = df[(df.goal == g) & (df.qwen == 0)].y; b = df[(df.goal == g) & (df.qwen == 1)].y
    if len(a) >= 5 and len(b) >= 5: pr.append(b.mean() - a.mean())
w = stats.wilcoxon(pr); print(f"  run-level paired (targets with >=5 per model, n={len(pr)}): Qwen higher in {sum(x>0 for x in pr)}; mean diff {100*np.mean(pr):.1f} pp; Wilcoxon p={w.pvalue:.3f}")
OUT["model"] = {"OR": round(orq, 2), "CI": [round(x, 2) for x in ci], "p": float(fit.pvalues["qwen"]), "runlevel": [len(pr), sum(x > 0 for x in pr), round(100 * np.mean(pr), 1), float(w.pvalue)]}

# ---------- 6. orchestration: evolved vs generated ----------
print("\n=== 6. orchestration: evolved vs initially generated")
for e in (0, 1):
    s = [r for r in F if int(r["evolved"]) == e]; cc = Counter(r["L"] for r in s)
    print(f"  evolved={e}: n={len(s)} L0 {pct(cc['L0'],len(s))} | L2 {pct(cc['L2'],len(s))}")
d2 = df.copy(); d2["L2"] = [int(r["L"] == "L2") for r in F]
X2 = sm.add_constant(pd.get_dummies(d2[["evolved", "run"]], columns=["run"], drop_first=True, dtype=float))
f2 = sm.GLM(d2["L2"], X2, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d2["run"])[0]})
ore = math.exp(f2.params["evolved"]); cie = [math.exp(x) for x in f2.conf_int().loc["evolved"]]
print(f"  within-run logit (run FE, clustered): OR evolved→L2 {ore:.2f} ({cie[0]:.2f}–{cie[1]:.2f}) p={f2.pvalues['evolved']:.3f}")
ev = [r for r in F if r["evolved"]]; ge = [r for r in F if not r["evolved"]]
OUT["evolved"] = {"n": [len(ev), len(ge)], "L2": [sum(r["L"] == "L2" for r in ev), sum(r["L"] == "L2" for r in ge)],
                  "L0": [sum(r["L"] == "L0" for r in ev), sum(r["L"] == "L0" for r in ge)], "OR": round(ore, 2), "CI": [round(x, 2) for x in cie], "p": float(f2.pvalues["evolved"])}
# rank strata
for s_ in ("top", "mid", "bottom"):
    s = [r for r in F if r["stratum"] == s_]; print(f"  stratum {s_}: n={len(s)} L2 {100*sum(r['L']=='L2' for r in s)/len(s):.1f}%")
t = [[sum(1 for r in F if r["stratum"] == s_ and r["L"] == l) for l in ("L0", "L1", "L2")] for s_ in ("top", "mid", "bottom")]
OUT["strata"] = {"table": t, "chi2": [round(stats.chi2_contingency(t)[0], 2), float(stats.chi2_contingency(t)[1])]}
print("  chi2", OUT["strata"]["chi2"])

# ---------- 7. self-rating calibration ----------
print("\n=== 7. self-rating")
def norm(s):
    s = (s or "").strip().lower()
    if "completely" in s and "novel" in s: return 3
    if s in ("high", "高", "高度", "高新颖") or s.startswith("high"): return 2
    if s in ("moderate", "中", "medium", "中等", "中度"): return 1
    if s in ("known", "low", "低", "已知"): return 0
    return None
S = [r for r in F if norm(r["self_novelty"]) is not None]
for v, nm in ((3, "completely novel"), (2, "high"), (1, "moderate"), (0, "known")):
    s = [r for r in S if norm(r["self_novelty"]) == v]; cc = Counter(r["L"] for r in s)
    print(f"  {nm:16s} n={len(s):3d} L0 {100*cc['L0']/len(s):5.1f} L1 {100*cc['L1']/len(s):5.1f} L2 {100*cc['L2']/len(s):5.1f}")
cn = [r for r in S if norm(r["self_novelty"]) == 3]
k_cn = sum(r["L"] in ("L0", "L1") for r in cn); k_cn0 = sum(r["L"] == "L0" for r in cn)
p_h3 = stats.binomtest(k_cn, len(cn), 0.30, alternative="greater").pvalue
print("  completely novel: L0∪L1", pct(k_cn, len(cn)), "p vs 0.30 =", p_h3, "| L0", pct(k_cn0, len(cn)))
d3 = pd.DataFrame({"L2": [int(r["L"] == "L2") for r in S], "self": [norm(r["self_novelty"]) for r in S], "run": [r["run"] for r in S]})
X3 = sm.add_constant(pd.get_dummies(d3[["self", "run"]], columns=["run"], drop_first=True, dtype=float))
f3 = sm.GLM(d3["L2"], X3, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d3["run"])[0]})
print(f"  calibration logit (L2 ~ self-rating step, run FE, clustered): OR per step {math.exp(f3.params['self']):.2f} p={f3.pvalues['self']:.4f}")
auc = stats.mannwhitneyu([x for x, y in zip(d3.self, d3.L2) if y == 1], [x for x, y in zip(d3.self, d3.L2) if y == 0]).statistic / (sum(d3.L2) * (len(d3) - sum(d3.L2)))
print(f"  AUC of self-rating for L2: {auc:.2f}")
OUT["self"] = {"n_cn": len(cn), "cn_L01": k_cn, "cn_L0": k_cn0, "p_h3_index": p_h3, "OR_step": round(math.exp(f3.params["self"]), 2), "p": float(f3.pvalues["self"]), "auc": round(auc, 2),
               "strata": {nm: [len([r for r in S if norm(r['self_novelty']) == v]), Counter(r['L'] for r in S if norm(r['self_novelty']) == v)] for v, nm in ((3, 'cn'), (2, 'high'), (1, 'moderate'), (0, 'known'))}}

# ---------- 8. memory probe v2 ----------
print("\n=== 8. memory probe v2")
P = {json.loads(l)["id"]: json.loads(l) for l in open("outputs/probe_v2.jsonl")}
pv = [r for r in F if P.get(r["id"], {}).get("status", "?") != "?"]
print("  valid", len(pv), "of", len(F))
for lab in ("L0", "L1", "L2"):
    s = [r for r in pv if r["L"] == lab]; k = sum(P[r["id"]]["status"] == "published_evidence" for r in s); print(f"  {lab}: claims published evidence {pct(k, len(s))}")
OUT["probe"] = {lab: [sum(P[r["id"]]["status"] == "published_evidence" for r in pv if r["L"] == lab), sum(1 for r in pv if r["L"] == lab)] for lab in ("L0", "L1", "L2")}
if os.path.exists("outputs/probe_v2_negctl.jsonl"):
    neg = [json.loads(l) for l in open("outputs/probe_v2_negctl.jsonl")]; neg = [x for x in neg if x["status"] != "?"]
    k = sum(x["status"] == "published_evidence" for x in neg); print("  negative controls (zero co-occurrence pairs): claims published evidence", pct(k, len(neg)))
    for mo in ("deepseek-v4-pro", "qwen3.7-max"):
        s = [x for x in neg if x["model"] == mo]; print(f"    {mo}: {pct(sum(x['status']=='published_evidence' for x in s), len(s))}")
    OUT["probe_neg"] = [k, len(neg)]
    # discrimination: L0 items vs negative controls
    pos_ = [P[r["id"]]["status"] == "published_evidence" for r in pv if r["L"] == "L0"]; negv = [x["status"] == "published_evidence" for x in neg]
    sens = sum(pos_) / len(pos_); spec = 1 - sum(negv) / len(negv); print(f"  sensitivity on L0 {sens:.2f}; specificity on negative controls {spec:.2f}")
    OUT["probe_disc"] = [round(sens, 2), round(spec, 2)]

# ---------- 9. perturbation v2 ----------
if os.path.exists("outputs/perturb_v2.jsonl"):
    print("\n=== 9. perturbation v2")
    Q = [json.loads(l) for l in open("outputs/perturb_v2.jsonl")]
    lab = {r["id"]: r["L"] for r in f}
    def yes(x, f_): return x[f_]["verdict"] == "yes"
    ok = [x for x in Q if x["original"]["verdict"] in ("yes", "doubtful", "no")]
    res = {}
    for form in ("unrelated", "synthetic_form"):
        s = [x for x in ok if x[form]["verdict"] in ("yes", "doubtful", "no")]
        b = sum(yes(x, "original") and not yes(x, form) for x in s); cdisc = sum(not yes(x, "original") and yes(x, form) for x in s)
        p = stats.binomtest(cdisc, b + cdisc, 0.5, alternative="less").pvalue if b + cdisc else float("nan")
        oa = sum(yes(x, "original") for x in s); fa = sum(yes(x, form) for x in s)
        print(f"  {form}: n={len(s)} original yes {pct(oa,len(s))} | perturbed yes {pct(fa,len(s))} | discordant {b}/{cdisc} one-sided McNemar p={p:.2e}")
        res[form] = {"n": len(s), "orig": oa, "pert": fa, "b": b, "c": cdisc, "p": p}
        for mo in ("deepseek-v4-pro", "qwen3.7-max"):
            ss = [x for x in s if x["model"] == mo]
            if ss: print(f"     {mo}: n={len(ss)} orig yes {100*sum(yes(x,'original') for x in ss)/len(ss):.1f}% | perturbed yes {100*sum(yes(x,form) for x in ss)/len(ss):.1f}% | orig doubtful {100*sum(x['original']['verdict']=='doubtful' for x in ss)/len(ss):.0f}%")
            res[form][mo] = [len(ss), sum(yes(x, "original") for x in ss), sum(yes(x, form) for x in ss)]
        for L in ("L0", "L1", "L2"):
            ss = [x for x in s if lab.get(x["id"]) == L]
            if ss:
                b_ = sum(yes(x, "original") and not yes(x, form) for x in ss); c_ = sum(not yes(x, "original") and yes(x, form) for x in ss)
                pp = stats.binomtest(min(b_, c_), b_ + c_, 0.5).pvalue if b_ + c_ else float("nan")
                print(f"     {L}: n={len(ss)} orig {100*sum(yes(x,'original') for x in ss)/len(ss):.1f}% pert {100*sum(yes(x,form) for x in ss)/len(ss):.1f}% two-sided p={pp:.3f}")
                res[form][L] = [len(ss), sum(yes(x, "original") for x in ss), sum(yes(x, form) for x in ss), pp]
    OUT["perturb"] = res
    print("  unparseable originals:", len(Q) - len(ok), "| no zero-co-occurrence counterfactual:", sum(1 for x in Q if x["cf_disease"] is None))

# ---------- 10. baselines (screen level, expanded co-occurrence) ----------
if os.path.exists("outputs/baselines_v3.json"):
    BL = R(open("outputs/baselines_v3.json"))
    perm = [x for x in BL["perm"] if x["ex"] >= 0]
    print("\n=== 10. permutation baseline (same drugs, random other study target)")
    sys0 = sum(r["ex"] == 0 for r in f); pz = sum(x["ex"] == 0 for x in perm)
    sysmed = float(np.median([r["ex"] for r in f])); pmed = float(np.median([x["ex"] for x in perm]))
    print("  zero prior co-occurrence: system", pct(sys0, len(f)), "| permuted", pct(pz, len(perm)), f"| median co-occurrence {sysmed:.0f} vs {pmed:.0f}")
    t_ = [[sys0, len(f) - sys0], [pz, len(perm) - pz]]; pf = float(stats.fisher_exact(t_)[1]); print("  Fisher p", pf)
    OUT["perm"] = {"sys0": [sys0, len(f)], "perm0": [pz, len(perm)], "med": [sysmed, pmed], "p": pf}
    bare = [x for x in BL["bare"] if x["ex"] >= 0]
    cells = {(x["model"], x["goal_id"]) for x in bare} & {(r["model"], r["goal_id"]) for r in f}
    fb = [x for x in bare if (x["model"], x["goal_id"]) in cells]; ff = [r for r in f if (r["model"], r["goal_id"]) in cells and not r["evolved"]]
    fe = [r for r in f if (r["model"], r["goal_id"]) in cells]
    zb = sum(x["ex"] == 0 for x in fb); zf = sum(r["ex"] == 0 for r in fe)
    print("\n=== 11. bare vs full (screen: zero expanded co-occurrence), matched cells", len(cells))
    print(f"  bare {pct(zb,len(fb))} | full {pct(zf,len(fe))} | Fisher p {stats.fisher_exact([[zb,len(fb)-zb],[zf,len(fe)-zf]])[1]:.3f}")
    print(f"  median co-occurrence bare {np.median([x['ex'] for x in fb]):.0f} vs full {np.median([r['ex'] for r in fe]):.0f}")
    OUT["bare"] = {"cells": len(cells), "bare0": [zb, len(fb)], "full0": [zf, len(fe)], "p": float(stats.fisher_exact([[zb, len(fb) - zb], [zf, len(fe) - zf]])[1]),
                   "med": [float(np.median([x['ex'] for x in fb])), float(np.median([r['ex'] for r in fe]))]}
    rob = BL["robin"]; rip = [x for x in rob if x["drug"] == "Ripasudil"][0]; rob = [x for x in rob if x["drug"] not in ("Ripasudil", "Metformin hydrochloride")]
    print("\n=== 12. Robin (expanded, T = 2025-05-28)")
    z = [x for x in rob if x["ex"] == 0]; small = [x for x in z if x["n_drug"] < 100]
    print(f"  n {len(rob)}; zero co-occurrence {len(z)} (of which small literature {len(small)}); co-occurring {len(rob)-len(z)}; ripasudil ex {rip['ex']} n {rip['n_drug']}")
    print("  top-8:", [(x["drug"], x["ex"]) for x in rob[:8]])
    OUT["robin"] = {"n": len(rob), "zero": len(z), "small": len(small), "rip": [rip["ex"], rip["n_drug"]]}


# ---------- 13. reading-based permutation baseline ----------
if os.path.exists("coding_materials_v2/coder_A_perm/all.json") and os.path.exists("coding_materials_v2/coder_B_perm/all.json"):
    PA = {x["key"]: x["label"] for x in R(open("coding_materials_v2/coder_A_perm/all.json"))}
    PB = {x["key"]: x["label"] for x in R(open("coding_materials_v2/coder_B_perm/all.json"))}
    PADJ = {x["key"]: x["final_label"] for x in R(open("coding_materials_v2/adjudication_perm.json"))} if os.path.exists("coding_materials_v2/adjudication_perm.json") else {}
    kp = kappa(PA, PB); print("\n=== 13. permutation baseline, read: coder agreement", round(kp[1], 3), "kappa", round(kp[0], 2), "n", kp[2])
    def plab0(k):
        if PA.get(k) == PB.get(k): return PA[k]
        return PADJ.get(k, "UNRES")
    def plab(k):
        if k in EXT: return higher(plab0(k), EXT[k]) if k in PA else EXT[k]
        return plab0(k)
    BL = R(open("outputs/baselines_v3.json")); perm = [x for x in BL["perm"] if x["ex"] >= 0]
    lab = []
    for x in perm:
        k = f"{x['drug']}||{x['disease']}"
        lab.append(plab(k) if k in PA else (EXT[k] if k in EXT else "L2"))
    cP = Counter(lab); nP = sum(cP[l] for l in ("L0", "L1", "L2")); print("  unresolved", cP["UNRES"])
    for l in ("L0", "L1", "L2"): print(f"  permuted {l}: {pct(cP[l], nP)}  | system {pct(c[l], N)}")
    t0 = [[c["L0"], N - c["L0"]], [cP["L0"], nP - cP["L0"]]]; t2 = [[c["L2"], N - c["L2"]], [cP["L2"], nP - cP["L2"]]]
    print("  Fisher L0 p", stats.fisher_exact(t0)[1], "| L2 p", stats.fisher_exact(t2)[1])
    OUT["perm_read"] = {"kappa": round(kp[0], 2), "agree": round(100 * kp[1], 1), "n_read": kp[2], "perm": {l: [cP[l], nP] for l in ("L0", "L1", "L2")},
                        "pL0": float(stats.fisher_exact(t0)[1]), "pL2": float(stats.fisher_exact(t2)[1]), "rip": plab("Ripasudil||Age-related macular degeneration")}
    print("  ripasudil-AMD label:", OUT["perm_read"]["rip"])


# ---------- 14. reviewer-requested sensitivity ----------
print("\n=== 14. screening vs reading decomposition")
Nall = C["N"]["all"]
def rule(r, counts, single):
    if r["L"] == "L0": return "L0"
    na, nc, nac = single[r["drug"]], single[r["disease"]], counts[key(r)]
    if nac >= 5: return "L1"
    mu = na * nc / Nall; var = nc * (na / Nall) * (1 - na / Nall) * (Nall - nc) / (Nall - 1); z = (nac - mu) / math.sqrt(var) if var > 0 else 0
    return "L2" if ((nac <= 2 and na >= 100 and nc >= 100) or z < -1) else "L1"
for nm, cnt, sg in (("exact", C["pair"]["exact"], C["single"]["exact"]), ("expanded", C["pair"]["expanded"], C["single"]["expanded"])):
    lab = Counter(rule(r, cnt, sg) for r in F); kr = lab["L0"] + lab["L1"]
    print(f"  preregistered rule with {nm} counts and reading-based L0 (n={N}): L0 {lab['L0']} L1 {lab['L1']} L2 {lab['L2']} -> L0∪L1 {pct(kr, N)}")
    OUT[f"rule_{nm}"] = {k: lab[k] for k in ("L0", "L1", "L2")}
for nm, cnt in (("exact", C["pair"]["exact"]), ("expanded", C["pair"]["expanded"])):
    z0 = sum(cnt[key(r)] == 0 for r in F); print(f"  screen without reading, L2 = zero co-occurrence ({nm}): {pct(z0, N)}")
read_L0 = sum(r["L"] == "L0" for r in ov); caught = sum(r["L"] == "L0" and old[r["id"]]["L_level"].startswith("L0") for r in ov)
print(f"  June screen caught {caught} of {read_L0} read-L0 items among the 307")
OUT["june_caught"] = [caught, read_L0]
print("\n=== 15. perturbation vs literature presence")
if os.path.exists("outputs/perturb_v2.jsonl"):
    Q = [json.loads(l) for l in open("outputs/perturb_v2.jsonl")]
    z0 = [x for x in Q if EX(f"{x['drug']}||{x['disease']}") == 0 and x["original"]["verdict"] in ("yes", "doubtful", "no")]
    lp = [x for x in Q if EX(f"{x['drug']}||{x['disease']}") > 0 and x["original"]["verdict"] in ("yes", "doubtful", "no")]
    print(f"  original assent, pairs with no prior co-occurrence: {pct(sum(x['original']['verdict']=='yes' for x in z0), len(z0))}; with co-occurrence: {pct(sum(x['original']['verdict']=='yes' for x in lp), len(lp))}")
    OUT["pert_lit"] = {"z0": [sum(x['original']['verdict'] == 'yes' for x in z0), len(z0)], "lp": [sum(x['original']['verdict'] == 'yes' for x in lp), len(lp)]}
print("\n=== 16. self-rating calibration, initial hypotheses only (3-level scale)")
def n3(s):
    s = (s or "").strip().lower()
    if "completely" in s and "novel" in s: return 2
    if s in ("moderate", "中", "medium", "中等", "中度"): return 1
    if s in ("known", "low", "低", "已知"): return 0
S3 = [r for r in F if not r["evolved"] and n3(r["self_novelty"]) is not None]
d4 = pd.DataFrame({"L2": [int(r["L"] == "L2") for r in S3], "self": [n3(r["self_novelty"]) for r in S3], "run": [r["run"] for r in S3]})
X4 = sm.add_constant(pd.get_dummies(d4[["self", "run"]], columns=["run"], drop_first=True, dtype=float))
f4 = sm.GLM(d4["L2"], X4, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d4["run"])[0]})
pos = [x for x, y in zip(d4.self, d4.L2) if y]; neg = [x for x, y in zip(d4.self, d4.L2) if not y]
auc4 = stats.mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg))
ci4 = [math.exp(x) for x in f4.conf_int().loc["self"]]
print(f"  n {len(S3)}; OR per step {math.exp(f4.params['self']):.2f} ({ci4[0]:.2f}-{ci4[1]:.2f}) p={f4.pvalues['self']:.4f}; AUC {auc4:.2f}")
for v, nm in ((2, "cn"), (1, "moderate"), (0, "known")):
    s_ = [r for r in S3 if n3(r["self_novelty"]) == v]; cc = Counter(r["L"] for r in s_); print(f"   {nm}: n={len(s_)} L0 {100*cc['L0']/len(s_):.1f} L1 {100*cc['L1']/len(s_):.1f} L2 {100*cc['L2']/len(s_):.1f}")
OUT["calib3"] = {"n": len(S3), "OR": round(math.exp(f4.params["self"]), 2), "CI": [round(x, 2) for x in ci4], "p": float(f4.pvalues["self"]), "auc": round(auc4, 2)}


# ---------- 17. broad construct (parent-category records may raise to L1) ----------
def broad(r):
    k = key(r); return higher(first_pass[k], EXT_BROAD[k]) if k in EXT_BROAD else r["L"]
cs = Counter(broad(r) for r in F)
print("\n=== 17. broad construct:", {l: pct(cs[l], N) for l in ("L0", "L1", "L2")}, "| L0∪L1", pct(cs["L0"] + cs["L1"], N))
OUT["broad"] = {l: [cs[l], N] for l in ("L0", "L1", "L2")}
if "perm_read" in OUT:
    plabs = []
    for x in [x for x in R(open("outputs/baselines_v3.json"))["perm"] if x["ex"] >= 0]:
        kk = f"{x['drug']}||{x['disease']}"; plabs.append((higher(plab0(kk), EXT_BROAD[kk]) if kk in PA else EXT_BROAD[kk]) if kk in EXT_BROAD else ("L2" if x["ex"] == 0 else plab(kk)))
    cp = Counter(plabs); nP = sum(cp[l] for l in ("L0", "L1", "L2"))
    print("   permuted broad:", {l: pct(cp[l], nP) for l in ("L0", "L1", "L2")}, "| Fisher L2 p", stats.fisher_exact([[cs["L2"], N - cs["L2"]], [cp["L2"], nP - cp["L2"]]])[1])
    OUT["broad_perm"] = {l: [cp[l], nP] for l in ("L0", "L1", "L2")}

# ---------- BH ----------
ps = {"H1": stats.binomtest(k01, N, 0.5, alternative="greater").pvalue, "H3_index": p_h3}
if "perturb" in OUT: ps["H6_unrelated"] = OUT["perturb"]["unrelated"]["p"]; ps["H6_synthetic"] = OUT["perturb"]["synthetic_form"]["p"]
rej, adj, _, _ = multipletests(list(ps.values()), method="fdr_bh")
print("\n=== BH:", {k: (f"{p:.2e}", f"{a:.2e}") for k, p, a in zip(ps, ps.values(), adj)})
OUT["bh"] = {k: [float(p), float(a)] for k, p, a in zip(ps, ps.values(), adj)}
json.dump(OUT, open("outputs/analysis_v3.json", "w"), ensure_ascii=False, indent=1, default=str)
