#!/usr/bin/env python3
"""English-label versions of the paper figures for the Scientometrics submission.
Same data, same geometry as fig_gen.py; outputs scientometrics-submission/figures/*.png (600 dpi) + .pdf (vector)."""
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = ["Times New Roman"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 7.5
SZ = 7.5
SZS = 6.5
for k in ("axes.linewidth", "lines.linewidth", "xtick.major.width",
          "ytick.major.width", "grid.linewidth", "patch.linewidth"):
    plt.rcParams[k] = 0.5

OUT = "scientometrics-submission/figures"
os.makedirs(OUT, exist_ok=True)
C = {"L0": "#D55E00", "L1": "#999999", "L2": "#0072B2"}
LAB = {"L0": "L0 restatement", "L1": "L1 known recombination", "L2": "L2 cross-literature novel"}

full = [json.loads(l) for l in open("outputs/coded_sample.jsonl") if l.strip()]
bare = json.load(open("outputs/bare_coded_final.json"))


def spec(rows):
    n = len(rows); c = Counter(r["L_level"][:2] for r in rows)
    return {k: c[k] / n * 100 for k in ("L0", "L1", "L2")}, n


def by_model(rows, m):
    return [r for r in rows if r["model"] == m]


def nospine(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def save(name):
    plt.savefig(f"{OUT}/{name}.png", dpi=600, bbox_inches="tight")
    plt.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight")
    plt.close()


# ── Fig. 1: novelty spectrum (total + by base model), horizontal stacked ──
fig, ax = plt.subplots(figsize=(4.6, 1.9))
groups = [("Qwen3.7-max", *spec(by_model(full, "qwen3.7-max"))),
          ("DeepSeek-V4-pro", *spec(by_model(full, "deepseek-v4-pro"))),
          ("Total", *spec(full))]
ypos = range(len(groups))
for i, (name, d, n) in enumerate(groups):
    left = 0
    for k in ("L0", "L1", "L2"):
        ax.barh(i, d[k], left=left, color=C[k], edgecolor="white", height=0.62)
        if d[k] > 5:
            ax.text(left + d[k] / 2, i, f"{d[k]:.1f}%", va="center", ha="center",
                    color="white", fontsize=SZ)
        left += d[k]
    ax.text(101, i, f"n={n}", va="center", ha="left", fontsize=SZS, color="#555")
ax.set_yticks(list(ypos)); ax.set_yticklabels([g[0] for g in groups])
ax.set_xlim(0, 112); ax.set_xlabel("Share (%)")
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ("L0", "L1", "L2")]
ax.legend(handles, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3,
          loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False, fontsize=SZS,
          handlelength=1.2, columnspacing=1.0)
nospine(ax); plt.tight_layout()
save("fig1_spectrum")

# ── Fig. 4: bare base model vs full system ablation ──
fig, ax = plt.subplots(figsize=(4.8, 2.6))
cells = [("Total", spec(bare)[0], spec(full)[0]),
         ("DeepSeek", spec(by_model(bare, "deepseek-v4-pro"))[0], spec(by_model(full, "deepseek-v4-pro"))[0]),
         ("Qwen", spec(by_model(bare, "qwen3.7-max"))[0], spec(by_model(full, "qwen3.7-max"))[0])]
x = 0; xticks = []
for name, bd, fd in cells:
    for j, (tag, d) in enumerate([("Bare", bd), ("Full", fd)]):
        left = 0
        for k in ("L0", "L1", "L2"):
            ax.bar(x, d[k], bottom=left, color=C[k], edgecolor="white", width=0.8)
            if d[k] > 6:
                ax.text(x, left + d[k] / 2, f"{d[k]:.0f}", va="center", ha="center",
                        color="white", fontsize=SZS)
            left += d[k]
        ax.text(x, -4, tag, ha="center", va="top", fontsize=SZS, color="#444")
        xticks.append(x); x += 1
    ax.text(x - 1.5, 107, name, ha="center", fontsize=SZ)
    x += 0.6
ax.set_xticks([]); ax.set_ylim(0, 112); ax.set_ylabel("Share (%)")
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ("L0", "L1", "L2")]
ax.legend(handles, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3,
          loc="upper center", bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=SZS,
          handlelength=1.2, columnspacing=1.0)
nospine(ax); plt.tight_layout()
save("fig4_ablation")

# ── Fig. 3: threshold sensitivity ──
def atyp_share(rows, zt):
    n = len(rows)
    a = sum(1 for r in rows if r["disjoint"] or (r["z"] is not None and r["z"] < zt))
    return a / n * 100


zts = [-0.5, -1.0, -1.5, -2.0, -2.5]
fig, ax = plt.subplots(figsize=(4.6, 2.9))
series = [("Total", full, "#000000", "o"),
          ("DeepSeek-V4-pro", by_model(full, "deepseek-v4-pro"), "#0072B2", "s"),
          ("Qwen3.7-max", by_model(full, "qwen3.7-max"), "#D55E00", "^")]
for name, rows, col, mk in series:
    ys = [atyp_share(rows, z) for z in zts]
    ax.plot(zts, ys, marker=mk, color=col, label=name, lw=1.0, ms=3.5)
ax.axvline(-1.0, color="grey", ls="--", lw=0.5, alpha=0.6)
ax.text(-1.02, 27, "baseline z < −1", color="grey", fontsize=SZS, rotation=90, va="bottom", ha="right")
ax.set_xlabel("z threshold"); ax.set_ylabel("Atypicality rate (L2 signal, %)")
ax.set_ylim(25, 80); ax.invert_xaxis()
ax.legend(frameon=False, fontsize=SZS, loc="lower left")
ax.grid(axis="y", alpha=0.25)
ax.text(-2.5, 73, "DeepSeek stays above Qwen throughout:\nthe base-model gap is immune to threshold choice",
        fontsize=SZS, color="#444")
nospine(ax); plt.tight_layout()
save("fig3_sensitivity")

# ── Fig. 2: self-rating × audited level composition ──
M = np.array([[30, 6, 79], [9, 3, 9], [51, 22, 55], [12, 7, 3]], float)
ylab = ["completely novel", "high", "moderate", "known"]
tot = M.sum(1)
prop = M / tot[:, None] * 100
fig, ax = plt.subplots(figsize=(5.0, 2.9))
for gx in (25, 50, 75, 100):
    ax.axvline(gx, color="#000000", lw=0.5, alpha=0.07, zorder=0)
ypos = np.arange(len(ylab))[::-1]
for i in range(len(ylab)):
    left = 0
    for j, k in enumerate(("L0", "L1", "L2")):
        w = prop[i, j]
        ax.barh(ypos[i], w, left=left, color=C[k], edgecolor="white",
                linewidth=0.8, height=0.56, zorder=3)
        if w >= 7:
            ax.text(left + w / 2, ypos[i], f"{int(M[i, j])}\n{w:.0f}%",
                    va="center", ha="center", color="white", fontsize=SZS,
                    linespacing=0.92, zorder=4)
        left += w
    ax.text(101.5, ypos[i], f"n={int(tot[i])}", va="center", ha="left",
            fontsize=SZS, color="#666")
ax.set_yticks(ypos); ax.set_yticklabels(ylab, fontsize=SZ)
ax.set_ylim(-0.6, 4.0); ax.set_xlim(0, 113)
ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0", "25", "50", "75", "100%"])
ax.set_xlabel("Audited level composition within each self-rating stratum")
ax.set_ylabel("System self-rated novelty")
ax.annotate('26% of "completely novel"\nare L0 restatements', xy=(13, ypos[0]),
            xytext=(30, ypos[0] + 0.45), fontsize=SZS, color="#A4332B",
            ha="left", va="bottom",
            arrowprops=dict(arrowstyle="->", color="#A4332B", lw=0.5))
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ("L0", "L1", "L2")]
ax.legend(handles, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3,
          loc="upper center", bbox_to_anchor=(0.5, -0.22), frameon=False, fontsize=SZS,
          handlelength=1.2, columnspacing=1.0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(left=False)
plt.tight_layout()
save("fig2_selfeval")

# ── Fig. 5: perturbation — original vs counterfactual assent by level ──
rq = [json.loads(l) for l in open("outputs/rq4_coded.jsonl") if l.strip()]
rq = [r for r in rq if r["orig_verdict"] in ("可以", "存疑", "不可以")
      and r["cf_verdict"] in ("可以", "存疑", "不可以")]
levels = ["L0", "L1", "L2"]
orig_r, cf_r, gaps, ns = [], [], [], []
for L in levels:
    s = [r for r in rq if r["L_level"] == L]
    o = sum(1 for r in s if r["orig_verdict"] == "可以") / len(s) * 100
    c = sum(1 for r in s if r["cf_verdict"] == "可以") / len(s) * 100
    orig_r.append(o); cf_r.append(c); gaps.append(o - c); ns.append(len(s))

fig, ax = plt.subplots(figsize=(4.8, 3.0))
x = np.arange(len(levels)); w = 0.36
ax.bar(x - w / 2, orig_r, w, label="Original (drug → real disease)", color="#0072B2")
ax.bar(x + w / 2, cf_r, w, label="Counterfactual (drug → unrelated disease)", color="#E69F00")
for i in range(len(levels)):
    ax.text(x[i] - w / 2, orig_r[i] + 1.2, f"{orig_r[i]:.1f}", ha="center", fontsize=SZS)
    ax.text(x[i] + w / 2, cf_r[i] + 1.2, f"{cf_r[i]:.1f}", ha="center", fontsize=SZS)
    ax.annotate(f"gap {gaps[i]:+.1f} pp", xy=(x[i], max(orig_r[i], cf_r[i]) + 5),
                ha="center", fontsize=SZS, color="#C00")
ax.set_xticks(x)
ax.set_xticklabels([f"{LAB[L]}\n(n={ns[i]})" for i, L in enumerate(levels)])
ax.set_ylabel('Assent rate ("yes", %)'); ax.set_ylim(0, 60)
ax.legend(frameon=False, fontsize=SZS, loc="upper right")
ax.text(1.0, 54, "Smaller gap → less specific judgment (pattern completion)",
        ha="center", fontsize=SZS, color="#444")
nospine(ax); plt.tight_layout()
save("fig5_perturbation")

print("5 figures (EN) →", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)
