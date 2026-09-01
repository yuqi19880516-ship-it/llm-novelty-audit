"""溯源：判定 A–C 关联在系统运行日 T 之前的存在情况。

后端：
- MockProvenanceSearcher：内置已知事实，无网可跑。
- PubMedProvenanceSearcher：NCBI E-utilities（免 key），按 maxdate=T 限定 → 共现计数。

memory_flag(P2) 由 base_llm 闭卷探针给出；in_context(P0) 由假设的 context_sources 判定。
exact_claim_found(L0) 在自动层给"疑似"，最终由编码层(LLM+人工金标准)确认。
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Optional

from .models import Hypothesis, ProvenanceResult
from .llm import LLMClient


class MockProvenanceSearcher:
    """内置事实表，供端到端联调与单测。"""
    def __init__(self, facts: dict | None = None):
        # key: (a.lower(), c.lower()) -> dict
        self.facts = facts or {}
        self.backend = "mock"

    def search(self, h: Hypothesis) -> ProvenanceResult:
        f = self.facts.get((h.a.lower(), h.c.lower()), {})
        return ProvenanceResult(
            earliest_source_date=f.get("earliest_date"),
            earliest_source_id=f.get("earliest_id"),
            exact_claim_found=f.get("exact_claim_found", False),
            cooccurrence_count_before_T=f.get("cooc", 0),
            in_context=_in_context(h),
            backend=self.backend,
        )


class PubMedProvenanceSearcher:
    """NCBI E-utilities esearch；统计 T 之前 A、C 共现的 PubMed 记录数。"""
    ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    def __init__(self, timeout: int = 20, email: str = ""):
        self.timeout = timeout
        self.email = email
        self.backend = "pubmed"

    def _count(self, term: str, maxdate: str) -> tuple[int, Optional[str]]:
        params = {
            "db": "pubmed", "term": term, "retmode": "json",
            "datetype": "pdat", "mindate": "1900/01/01",
            "maxdate": maxdate.replace("-", "/"), "retmax": "1",
            "sort": "pub+date",
        }
        if self.email:
            params["email"] = self.email
        url = self.ESEARCH + "?" + urllib.parse.urlencode(params)
        last = None
        for attempt in range(4):  # NCBI 无 key 易抖动，指数退避重试
            try:
                with urllib.request.urlopen(url, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode())
                time.sleep(0.4)  # 限速 ~3 req/s
                res = data.get("esearchresult", {})
                return int(res.get("count", 0)), (res.get("idlist") or [None])[0]
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(1.0 * (attempt + 1))
        raise last

    # 语料总量 N(≤ T)：日期区间查询；失败回退常数并告警。
    _FALLBACK_TOTAL = 37_000_000

    def total_count(self, maxdate: str) -> int:
        term = f'("1800/01/01"[PDAT] : "{maxdate.replace("-", "/")}"[PDAT])'
        try:
            n, _ = self._count(term, maxdate)
            return n if n > 0 else self._FALLBACK_TOTAL
        except Exception:
            return self._FALLBACK_TOTAL

    def search(self, h: Hypothesis) -> ProvenanceResult:
        maxdate = h.run_date or "3000/01/01"
        term = f'("{h.a}"[tiab]) AND ("{h.c}"[tiab])'
        cooc, earliest_id = self._count(term, maxdate)
        return ProvenanceResult(
            earliest_source_id=earliest_id,
            exact_claim_found=False,          # 共现≠明确陈述；交编码层确认
            cooccurrence_count_before_T=cooc,
            in_context=_in_context(h),
            backend=self.backend,
        )


def _in_context(h: Hypothesis) -> bool:
    """连接 A 与 C 的来源是否被投喂进系统上下文 → P0。"""
    blob = " ".join(h.context_sources).lower()
    return bool(blob) and h.a.lower() in blob and h.c.lower() in blob


def probe_memory(h: Hypothesis, base_llm: LLMClient) -> bool:
    """闭卷记忆探针：裸基座 LLM(无工具)能否直接说出 A–C 关联 → P2 旗标。"""
    prompt = (
        f"仅凭你已有的知识、不要联网检索，回答：'{h.a}' 与 '{h.c}' 之间是否存在已知的"
        f"机制性关联或治疗用途？若存在，请直接给出该关联。若不知道，请只回答 'UNKNOWN'。"
    )
    ans = base_llm.complete(prompt).strip()
    return "UNKNOWN" not in ans.upper() and h.c.lower() in ans.lower()


class PubMedCorpusStats:
    """实时 PubMed 计数，接口兼容 novelty.score 所需的 .n_total / .n() / .n_ac()。

    所有计数按 maxdate=T 限定（< T 时间快照），带缓存避免重复查询。
    """
    def __init__(self, maxdate: str, searcher: "PubMedProvenanceSearcher"):
        self.maxdate = maxdate or "3000/01/01"
        self._searcher = searcher
        self._cache: dict[str, int] = {}
        self._n_total: Optional[int] = None

    @property
    def n_total(self) -> int:
        if self._n_total is None:
            self._n_total = self._searcher.total_count(self.maxdate)
        return self._n_total

    def n(self, term: str) -> int:
        key = term.lower()
        if key not in self._cache:
            cnt, _ = self._searcher._count(f'("{term}"[tiab])', self.maxdate)
            self._cache[key] = cnt
        return self._cache[key]

    def n_ac(self, a: str, c: str) -> int:
        key = f"{a.lower()}|{c.lower()}"
        if key not in self._cache:
            cnt, _ = self._searcher._count(f'("{a}"[tiab]) AND ("{c}"[tiab])', self.maxdate)
            self._cache[key] = cnt
        return self._cache[key]
