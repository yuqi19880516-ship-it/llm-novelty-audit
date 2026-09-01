"""科学计量新颖性度量（docs/05 §3）。

三个互为三角验证的指标，均在 < T 时间快照语料上计算：
1. 共现原子组合 z 分数（Uzzi 改编）—— 本骨架已实现"独立零模型"的一阶版本；
   完整的度保持 Monte-Carlo 重洗零模型见 TODO。
2. 语义嵌入距离（stub，接入 sentence-transformers 后启用）。
3. 知识图最短路径长（stub，接入 networkx + KG 后启用）。

约定：合成新颖分越高 → 越新颖（低/负 z、远嵌入距离、长路径 → 高分）。
"""
from __future__ import annotations

import math
from typing import Optional

from .models import NoveltyScore


class CorpusStats:
    """提供新颖性度量所需的语料统计（< T 快照）。"""
    def __init__(self, n_total: int, doc_freq: dict[str, int], cooc: dict[tuple[str, str], int]):
        self.n_total = n_total
        self.doc_freq = {k.lower(): v for k, v in doc_freq.items()}
        self.cooc = {(a.lower(), c.lower()): v for (a, c), v in cooc.items()}

    def n(self, term: str) -> int:
        return self.doc_freq.get(term.lower(), 0)

    def n_ac(self, a: str, c: str) -> int:
        key = (a.lower(), c.lower())
        return self.cooc.get(key, self.cooc.get((c.lower(), a.lower()), 0))


def poisson_z(stats: CorpusStats, a: str, c: str) -> Optional[float]:
    """v0：一阶独立零模型 z = (观测 - E)/sqrt(E)，E=n_a*n_c/N（Poisson 近似）。留作对比。"""
    N, n_a, n_c = stats.n_total, stats.n(a), stats.n(c)
    if N <= 0 or n_a <= 0 or n_c <= 0:
        return None
    expected = n_a * n_c / N
    if expected <= 0:
        return None
    return (stats.n_ac(a, c) - expected) / math.sqrt(expected)


def cooccurrence_z(stats: CorpusStats, a: str, c: str) -> Optional[float]:
    """v1：度保持(超几何)零模型 z —— Uzzi 度保持重洗的精确解析形式。

    给定 A、C 的文献频次 n_a、n_c 与语料量 N，独立"度保持"重洗下共现数
        n_ac ~ Hypergeometric(N, K=n_a, n=n_c)
        mean = n_a*n_c/N
        var  = n_c * (n_a/N) * (1 - n_a/N) * (N - n_c)/(N - 1)   # 含有限总体校正
        z    = (观测 - mean)/sqrt(var)
    比 Poisson 更精确地校准方差（尤其大文献）。单个概念对用闭式即可，无需 Monte-Carlo。
    注意：当 mean << 1（小/不对称文献），零共现并不"稀奇" → z 接近 0，须配 disjointness 判据。
    """
    N, n_a, n_c = stats.n_total, stats.n(a), stats.n(c)
    if N <= 1 or n_a <= 0 or n_c <= 0:
        return None
    mean = n_a * n_c / N
    var = n_c * (n_a / N) * (1.0 - n_a / N) * (N - n_c) / (N - 1)
    if var <= 0:
        return None
    return (stats.n_ac(a, c) - mean) / math.sqrt(var)


def is_disjoint(stats: CorpusStats, a: str, c: str,
                cooc_floor: int = 2, lit_floor: int = 100) -> bool:
    """Swanson disjointness：两支文献均达规模下限(≥lit_floor)，却近乎零共现(≤cooc_floor)。
    捕捉"各自成立但互不相交"的跨文献新颖（如鱼油↔雷诺：142/1851 篇，共现 0）。
    """
    n_a, n_c, n_ac = stats.n(a), stats.n(c), stats.n_ac(a, c)
    return (n_ac <= cooc_floor) and (n_a >= lit_floor) and (n_c >= lit_floor)


def embedding_distance(a: str, c: str, embedder=None) -> Optional[float]:
    """语义距离 stub。接入 embedder(返回向量)后启用余弦距离。"""
    if embedder is None:
        return None
    import numpy as np  # noqa: 延迟导入
    va, vc = embedder(a), embedder(c)
    cos = float(np.dot(va, vc) / (np.linalg.norm(va) * np.linalg.norm(vc) + 1e-9))
    return 1.0 - cos


def kg_path_length(a: str, c: str, graph=None) -> Optional[float]:
    """知识图最短路径长 stub。接入 networkx 图后启用。"""
    if graph is None:
        return None
    import networkx as nx  # noqa
    try:
        return float(nx.shortest_path_length(graph, a.lower(), c.lower()))
    except Exception:
        return math.inf  # 不连通 → 最大新颖


def score(stats: CorpusStats, a: str, c: str,
          z_atypical_threshold: float = -1.0,
          cooc_floor: int = 2, lit_floor: int = 100,
          embedder=None, graph=None) -> NoveltyScore:
    z = cooccurrence_z(stats, a, c)            # 度保持(超几何)
    pz = poisson_z(stats, a, c)                # 对比用
    disjoint = is_disjoint(stats, a, c, cooc_floor, lit_floor)
    emb = embedding_distance(a, c, embedder)
    kgp = kg_path_length(a, c, graph)

    # 合成：各指标映射到"越高越新颖"再平均（骨架版）。
    parts: list[float] = []
    if z is not None:
        parts.append(_sigmoid(-z))                 # 低/负 z → 高新颖
    if emb is not None:
        parts.append(min(max(emb, 0.0), 1.0))
    if kgp is not None:
        parts.append(_sigmoid(kgp - 2.0))
    composite = sum(parts) / len(parts) if parts else None
    if disjoint:                                   # disjointness 直接抬升合成分
        composite = max(composite or 0.0, 0.9)

    # 双判据：度保持 z 反常（管大文献）或 disjoint（管小/不对称文献）
    atypical = bool(disjoint or (z is not None and z < z_atypical_threshold))
    return NoveltyScore(cooccurrence_z=z, poisson_z=pz, disjoint=disjoint,
                        embedding_distance=emb, kg_path_length=kgp,
                        composite=composite, atypical=atypical)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
