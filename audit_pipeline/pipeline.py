"""端到端编排：一条假设走完 溯源 → 新颖性 → 谱系判定。"""
from __future__ import annotations

from .models import CodingResult, Hypothesis
from .provenance import probe_memory
from . import novelty as nov_mod
from . import coding as coding_mod


def audit_one(h: Hypothesis, *, searcher, corpus_stats, base_llm,
              validated: bool = False, **novelty_kw) -> CodingResult:
    """
    searcher       : Mock/PubMed 溯源器（含 .search(h)）
    corpus_stats   : novelty.CorpusStats（< T 快照统计）
    base_llm       : 被审基座 LLM（闭卷记忆探针用）
    """
    prov = searcher.search(h)
    memory_flag = probe_memory(h, base_llm)
    prov.memory_flag = memory_flag
    nov = nov_mod.score(corpus_stats, h.a, h.c, **novelty_kw)
    return coding_mod.code(h, prov, nov, memory_flag=memory_flag, validated=validated)


def audit_many(hyps, **kw) -> list[CodingResult]:
    return [audit_one(h, **kw) for h in hyps]
