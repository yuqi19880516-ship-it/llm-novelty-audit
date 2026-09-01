#!/usr/bin/env python3
"""从真实审计数据生成论文图(中文标签,色盲友好)。输出 docs/manuscript/figures/*.png(300dpi)。"""
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 《情报学报》制图规格:图中文字六号宋体(≈7.5pt)、英文 Times New Roman、线条 0.5pt、300dpi
# 中西文混排:family 设为字体名列表,matplotlib 逐字回退——英文/数字 Times New Roman,中文宋体
plt.rcParams["font.family"] = ["Times New Roman", "Songti SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 7.5
SZ = 7.5      # 六号:正文标签
SZS = 6.5     # 小注解
for k in ("axes.linewidth", "lines.linewidth", "xtick.major.width",
          "ytick.major.width", "grid.linewidth", "patch.linewidth"):
    plt.rcParams[k] = 0.5

OUT = "docs/manuscript/figures"
os.makedirs(OUT, exist_ok=True)
# 色盲友好:L0 橙红(复述) / L1 灰(重组) / L2 蓝(新颖)
C = {"L0": "#D55E00", "L1": "#999999", "L2": "#0072B2"}
LAB = {"L0": "L0 复述", "L1": "L1 既知重组", "L2": "L2 跨文献新颖"}

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


# ── 图1:新颖性谱系(合计 + 分基座)横向堆叠 ──
fig, ax = plt.subplots(figsize=(4.6, 1.9))
groups = [("Qwen3.7-max", *spec(by_model(full, "qwen3.7-max"))),
          ("DeepSeek-V4-pro", *spec(by_model(full, "deepseek-v4-pro"))),
          ("合计", *spec(full))]
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
ax.set_xlim(0, 112); ax.set_xlabel("占比 (%)")
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ("L0", "L1", "L2")]
ax.legend(handles, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3,
          loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False, fontsize=SZS,
          handlelength=1.2, columnspacing=1.0)
nospine(ax); plt.tight_layout()
plt.savefig(f"{OUT}/fig1_spectrum.png", dpi=300, bbox_inches="tight"); plt.close()

# ── 图2(文件 fig4):裸基座 vs 完整系统消融(分基座,成对堆叠) ──
fig, ax = plt.subplots(figsize=(4.8, 2.6))
cells = [("合计", spec(bare)[0], spec(full)[0]),
         ("DeepSeek", spec(by_model(bare, "deepseek-v4-pro"))[0], spec(by_model(full, "deepseek-v4-pro"))[0]),
         ("Qwen", spec(by_model(bare, "qwen3.7-max"))[0], spec(by_model(full, "qwen3.7-max"))[0])]
x = 0; xticks = []; xlab = []
for name, bd, fd in cells:
    for j, (tag, d) in enumerate([("裸基座", bd), ("完整", fd)]):
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
ax.set_xticks([]); ax.set_ylim(0, 112); ax.set_ylabel("占比 (%)")
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ("L0", "L1", "L2")]
ax.legend(handles, [LAB[k] for k in ("L0", "L1", "L2")], ncol=3,
          loc="upper center", bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=SZS,
          handlelength=1.2, columnspacing=1.0)
nospine(ax); plt.tight_layout()
plt.savefig(f"{OUT}/fig4_ablation.png", dpi=300, bbox_inches="tight"); plt.close()

# ── 图3:阈值敏感性(atypicality 率 vs z 阈值,分基座) ──
def atyp_share(rows, zt):
    n = len(rows)
    a = sum(1 for r in rows if r["disjoint"] or (r["z"] is not None and r["z"] < zt))
    return a / n * 100


zts = [-0.5, -1.0, -1.5, -2.0, -2.5]
fig, ax = plt.subplots(figsize=(4.6, 2.9))
series = [("合计", full, "#000000", "o"),
          ("DeepSeek-V4-pro", by_model(full, "deepseek-v4-pro"), "#0072B2", "s"),
          ("Qwen3.7-max", by_model(full, "qwen3.7-max"), "#D55E00", "^")]
for name, rows, col, mk in series:
    ys = [atyp_share(rows, z) for z in zts]
    ax.plot(zts, ys, marker=mk, color=col, label=name, lw=1.0, ms=3.5)
ax.axvline(-1.0, color="grey", ls="--", lw=0.5, alpha=0.6)
ax.text(-1.02, 27, "基线 z<−1", color="grey", fontsize=SZS, rotation=90, va="bottom", ha="right")
ax.set_xlabel("z 阈值(越严越靠左)"); ax.set_ylabel("atypicality 率 = L2 信号 (%)")
ax.set_ylim(25, 80); ax.invert_xaxis()
ax.legend(frameon=False, fontsize=SZS, loc="lower left")
ax.grid(axis="y", alpha=0.25)
ax.text(-2.5, 73, "DeepSeek 全程高于 Qwen,\n基座差异免疫于阈值选择", fontsize=SZS, color="#444")
nospine(ax); plt.tight_layout()
plt.savefig(f"{OUT}/fig3_sensitivity.png", dpi=300, bbox_inches="tight"); plt.close()

# ── 图2:自评 × 审计 L 级构成(表3) —— 层内 100% 堆叠条,替代默认热图 ──
import numpy as np
M = np.array([[30, 6, 79], [9, 3, 9], [51, 22, 55], [12, 7, 3]], float)
ylab = ["完全新颖", "高", "中等", "已知"]          # 系统自评(归一)
tot = M.sum(1)
prop = M / tot[:, None] * 100
fig, ax = plt.subplots(figsize=(5.0, 2.9))
for gx in (25, 50, 75, 100):                      # 背景参考竖线
    ax.axvline(gx, color="#000000", lw=0.5, alpha=0.07, zorder=0)
ypos = np.arange(len(ylab))[::-1]                 # 完全新颖置顶
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
ax.set_xlabel("各自评层内的审计 L 级构成")
ax.set_ylabel("系统自评新颖性")
ax.annotate("自评\"完全新颖\"仍有 26% 实为 L0 复述", xy=(13, ypos[0]),
            xytext=(30, ypos[0] + 0.5), fontsize=SZS, color="#A4332B",
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
plt.savefig(f"{OUT}/fig2_selfeval.png", dpi=300, bbox_inches="tight"); plt.close()

# ── 图5:RQ4 扰动——原始 vs 反事实点头率,按 L 级(分组柱+落差标注) ──
rq = [json.loads(l) for l in open("outputs/rq4_coded.jsonl") if l.strip()]
rq = [r for r in rq if r["orig_verdict"] in ("可以", "存疑", "不可以")
      and r["cf_verdict"] in ("可以", "存疑", "不可以")]
levels = ["L0", "L1", "L2"]
labs = {"L0": "L0 复述", "L1": "L1 既知重组", "L2": "L2 跨文献新颖"}
orig_r, cf_r, gaps, ns = [], [], [], []
for L in levels:
    s = [r for r in rq if r["L_level"] == L]
    o = sum(1 for r in s if r["orig_verdict"] == "可以") / len(s) * 100
    c = sum(1 for r in s if r["cf_verdict"] == "可以") / len(s) * 100
    orig_r.append(o); cf_r.append(c); gaps.append(o - c); ns.append(len(s))

fig, ax = plt.subplots(figsize=(4.8, 3.0))
import numpy as np
x = np.arange(len(levels)); w = 0.36
b1 = ax.bar(x - w / 2, orig_r, w, label="原始(药→真病)", color="#0072B2")
b2 = ax.bar(x + w / 2, cf_r, w, label="反事实(药→无关病)", color="#E69F00")
for i in range(len(levels)):
    ax.text(x[i] - w / 2, orig_r[i] + 1.2, f"{orig_r[i]:.1f}", ha="center", fontsize=SZS)
    ax.text(x[i] + w / 2, cf_r[i] + 1.2, f"{cf_r[i]:.1f}", ha="center", fontsize=SZS)
    ax.annotate(f"落差 {gaps[i]:+.1f}pp", xy=(x[i], max(orig_r[i], cf_r[i]) + 5),
                ha="center", fontsize=SZS, color="#C00")
ax.set_xticks(x)
ax.set_xticklabels([f"{labs[L]}\n(n={ns[i]})" for i, L in enumerate(levels)])
ax.set_ylabel("点头率(判定\"可以\", %)"); ax.set_ylim(0, 60)
ax.legend(frameon=False, fontsize=SZS, loc="upper right")
ax.text(1.0, 54, "落差越小→判断越不特异(模式补全)", ha="center", fontsize=SZS, color="#444")
nospine(ax); plt.tight_layout()
plt.savefig(f"{OUT}/fig5_perturbation.png", dpi=300, bbox_inches="tight"); plt.close()

print("生成 5 张图 →", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)
