#!/usr/bin/env python3
"""Figures for the JIS submission, v3 (reading-based labels). Writes jis-submission/figures/ (png 600 dpi + pdf, TrueType)."""
import json, math
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
OUT = "jis-submission/figures"
plt.rcParams.update({"font.family": ["Times New Roman"], "axes.unicode_minus": True, "font.size": 7.5, "pdf.fonttype": 42,
                     "ps.fonttype": 42, "hatch.color": "white", "hatch.linewidth": 0.6})
for k in ("axes.linewidth", "lines.linewidth", "xtick.major.width", "ytick.major.width", "patch.linewidth"): plt.rcParams[k] = 0.5
SZ, SZS = 7.5, 6.5
C = {"L0": "#D55E00", "L1": "#999999", "L2": "#0072B2"}; H = {"L0": "////", "L1": "", "L2": ""}
LAB = {"L0": "L0 restatement", "L1": "L1 prior link", "L2": "L2 no prior link"}
MD = {"deepseek-v4-pro": "DeepSeek-V4-pro", "qwen3.7-max": "Qwen3.7-max"}
f = json.load(open("outputs/frame_v2.json")); fin = json.load(open("coding_materials_v2/final_labels.json"))
for r in f: r["L"] = fin[f"{r['drug']}||{r['disease']}"]
F = [r for r in f if r["L"] != "IND"]
def spec(rows):
    n = len(rows); c = Counter(r["L"] for r in rows); return {k: 100 * c[k] / n for k in ("L0", "L1", "L2")}, n
def legend(ax, y):
    hs = [plt.Rectangle((0, 0), 1, 1, facecolor=C[k], hatch=H[k], edgecolor="white") for k in ("L0", "L1", "L2")]
    ax.legend(hs, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3, loc="upper center", bbox_to_anchor=(0.5, y), frameon=False, fontsize=SZS, handlelength=1.6)
def save(n): plt.savefig(f"{OUT}/{n}.png", dpi=600, bbox_inches="tight"); plt.savefig(f"{OUT}/{n}.pdf", bbox_inches="tight"); plt.close()
def hbar(ax, groups, xmax=112):
    for i, (name, d, n) in enumerate(groups):
        left = 0
        for k in ("L0", "L1", "L2"):
            ax.barh(i, d[k], left=left, color=C[k], hatch=H[k], edgecolor="white", height=0.62)
            if d[k] > 5: ax.text(left + d[k] / 2, i, f"{d[k]:.1f}%", va="center", ha="center", color="white", fontsize=SZS,
                                 bbox=dict(boxstyle="round,pad=0.1", fc=C[k], ec="none") if k == "L0" else None)
            left += d[k]
        ax.text(101, i, f"n = {n}", va="center", ha="left", fontsize=SZS, color="#555")
    ax.set_yticks(range(len(groups))); ax.set_yticklabels([g[0] for g in groups]); ax.set_xlim(0, xmax); ax.set_xlabel("Share (%)")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
# Figure 1
fig, ax = plt.subplots(figsize=(4.6, 1.9))
hbar(ax, [(MD["qwen3.7-max"], *spec([r for r in F if r["model"] == "qwen3.7-max"])), (MD["deepseek-v4-pro"], *spec([r for r in F if r["model"] == "deepseek-v4-pro"])), ("Total", *spec(F))])
legend(ax, -0.30); plt.tight_layout(); save("fig1_spectrum")
# Figure 2
def norm(s):
    s = (s or "").strip().lower()
    if "completely" in s and "novel" in s: return "completely novel"
    if s in ("high", "高", "高度", "高新颖") or s.startswith("high"): return "high"
    if s in ("moderate", "中", "medium", "中等", "中度"): return "moderate"
    if s in ("known", "low", "低", "已知"): return "known"
fig, ax = plt.subplots(figsize=(4.8, 2.3))
hbar(ax, [(lab, *spec([r for r in F if norm(r["self_novelty"]) == lab])) for lab in ("known", "moderate", "high", "completely novel")])
ax.set_ylabel("System self-rated novelty"); legend(ax, -0.25); plt.tight_layout(); save("fig2_selfeval")
# Figure 3 evolved vs generated
groups = []
for m in ("deepseek-v4-pro", "qwen3.7-max", None):
    for ev, tag in ((False, "initial"), (True, "evolved")):
        rows = [r for r in F if r["evolved"] == ev and (m is None or r["model"] == m)]
        groups.append((f"{MD[m] if m else 'Total'}, {tag}", *spec(rows)))
fig, ax = plt.subplots(figsize=(4.8, 2.6)); hbar(ax, groups[::-1]); legend(ax, -0.18); plt.tight_layout(); save("fig3_evolved")
print("figs 1-3 written")

# Figure 4 perturbation v2
from scipy import stats
Q = [json.loads(l) for l in open("outputs/perturb_v2.jsonl")]
def wil(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)
yes = lambda x, k: x[k]["verdict"] == "yes"
fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.6), sharey=True)
for ax, (form, title) in zip(axes, (("unrelated", "Unrelated disease (no prior co-occurrence)"), ("synthetic_form", "Invented compound name"))):
    for i, m in enumerate(MD):
        s = [x for x in Q if x["model"] == m and x[form]["verdict"] in ("yes", "doubtful", "no")]; n = len(s)
        o = sum(yes(x, "original") for x in s); p_ = sum(yes(x, form) for x in s)
        for j, (k, col, hat, lab) in enumerate(((o, "#0072B2", "", "Original pair"), (p_, "#E69F00", "////", "Perturbed pair"))):
            v = 100 * k / n; lo, hi = wil(k, n)
            ax.bar(i + (j - 0.5) * 0.36, v, 0.36, color=col, hatch=hat, edgecolor="white", label=lab if i == 0 else None)
            ax.errorbar(i + (j - 0.5) * 0.36, v, yerr=[[v - lo], [hi - v]], fmt="none", ecolor="#333", elinewidth=0.5, capsize=1.5)
            ax.text(i + (j - 0.5) * 0.36, hi + 1.5, f"{v:.1f}", ha="center", fontsize=SZS)
        ax.text(i, -9, f"n = {n}", ha="center", fontsize=SZS, color="#555")
    ax.set_xticks(range(2)); ax.set_xticklabels(list(MD.values())); ax.set_title(title, fontsize=SZ); ax.set_ylim(0, 50)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
axes[0].set_ylabel("Assent rate (“yes”, %)")
h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 1.03), ncol=2, frameon=False, fontsize=SZS)
plt.tight_layout(rect=(0, 0.03, 1, 0.93)); save("fig4_perturbation"); print("fig4 written")
