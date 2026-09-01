"""谱系/溯源判定（docs/05 §2.3 决策树）。

把溯源结果 + 科学计量新颖性合成为 (L 级, 溯源) 标签。
- L0 由"T 前已有明确陈述"判定（exact_claim_found）。
- L1/L2 边界由共现计数 + 原子组合 z 客观锚定。
- L2→L3 需外部提供 validated 旗标。
- 溯源 P0/P1/P2 由 in_context / memory_flag 判定。
"""
from __future__ import annotations

from .models import (CodingResult, Hypothesis, NoveltyLevel, NoveltyScore,
                     Provenance, ProvenanceResult)


def code(h: Hypothesis,
         prov: ProvenanceResult,
         nov: NoveltyScore,
         memory_flag: bool,
         validated: bool = False,
         cooc_conventional_threshold: int = 5) -> CodingResult:

    # —— 溯源轴 ——
    if prov.in_context:
        provenance = Provenance.P0_SPOON_FED
    elif memory_flag:
        provenance = Provenance.P2_MEMORY
    elif prov.backend:
        provenance = Provenance.P1_RETRIEVAL
    else:
        provenance = Provenance.UNKNOWN

    # —— 新颖性层级 ——
    reasons: list[str] = []
    if prov.exact_claim_found:
        level = NoveltyLevel.L0_RECALL
        reasons.append(f"T({h.run_date})前已有明确陈述该 A–C 关联")
    elif prov.cooccurrence_count_before_T >= cooc_conventional_threshold:
        level = NoveltyLevel.L1_RECOMBINATION
        reasons.append(f"T 前 A、C 共现 {prov.cooccurrence_count_before_T} 篇(≥{cooc_conventional_threshold})，属常规组合")
    elif nov.atypical:
        if validated:
            level = NoveltyLevel.L3_VALIDATED_NOVEL
            reasons.append("跨文献新颖且有后续独立验证")
        else:
            level = NoveltyLevel.L2_CROSS_LIT_NOVEL
            reasons.append(f"原子组合 z={_fmt(nov.cooccurrence_z)}(反常)，A、C 近乎不共现")
    else:
        level = NoveltyLevel.L1_RECOMBINATION
        reasons.append("无明确陈述但未达反常阈值，归常规重组")

    if provenance is Provenance.P2_MEMORY and level in (NoveltyLevel.L2_CROSS_LIT_NOVEL,):
        reasons.append("⚠ 记忆旗标与'跨文献新颖'冲突，需人工金标准复核")

    return CodingResult(
        hypothesis_id=h.id,
        novelty_level=level,
        provenance=provenance,
        novelty=nov,
        provenance_result=prov,
        rationale="；".join(reasons),
        validated=validated,
    )


def _fmt(x):
    return "NA" if x is None else round(x, 2)
