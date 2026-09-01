"""端到端联调用的 Mock 语料与事实表（仅演示，非真实统计）。

含两条对照假设：
- 来氟米特→AML：先导实验所见——机制 2016 已发表、共现多、裸 LLM 能背 → 预期 L0/L1 + P2。
- DrugX→DiseaseY：虚构的真新颖桥接——不共现、裸 LLM 不知、未被投喂 → 预期 L2 + P1。
"""
from .models import Hypothesis
from .novelty import CorpusStats
from .provenance import MockProvenanceSearcher
from .llm import MockLLMClient

HYPOTHESES = [
    Hypothesis(
        id="H1_leflunomide_AML",
        a="Leflunomide", c="Acute myeloid leukemia", b="DHODH inhibition",
        claim_text="来氟米特经抑制 DHODH 可作为 AML 的新型重定位候选。",
        system="Co-Scientist", rank=1, run_date="2025/02/03",
        context_sources=[],
    ),
    Hypothesis(
        id="H2_DrugX_DiseaseY",
        a="DrugX", c="DiseaseY", b="GeneZ pathway",
        claim_text="DrugX 经 GeneZ 通路或可治疗 DiseaseY（虚构新颖桥接）。",
        system="Co-Scientist", rank=7, run_date="2025/02/03",
        context_sources=[],
    ),
]

# Mock 溯源事实表
FACTS = {
    ("leflunomide", "acute myeloid leukemia"): {
        "exact_claim_found": True,            # DHODH 抑制治 AML = Cell 2016，已明确陈述
        "earliest_date": "2016/09/01",
        "earliest_id": "27641501",
        "cooc": 42,
    },
    ("drugx", "diseasey"): {
        "exact_claim_found": False,
        "cooc": 0,                            # 互不相关文献
    },
}

# Mock 语料统计（< T 快照；数字仅示意）
STATS = CorpusStats(
    n_total=1_000_000,
    doc_freq={
        "Leflunomide": 4_000, "Acute myeloid leukemia": 80_000,
        # H2 设为"各自被充分研究、却互不连接"的两支文献(忠实 Swanson 新颖情形)
        "DrugX": 25_000, "DiseaseY": 30_000,
    },
    cooc={
        ("Leflunomide", "Acute myeloid leukemia"): 42,
        ("DrugX", "DiseaseY"): 0,
    },
)

SEARCHER = MockProvenanceSearcher(FACTS)

# Mock 基座 LLM：来氟米特-AML 能"背出"，虚构对则 UNKNOWN
BASE_LLM = MockLLMClient(name="mock-deepseek", family="deepseek", canned={
    "Leflunomide": "Leflunomide inhibits DHODH and has been studied in acute myeloid leukemia.",
    "DrugX": "UNKNOWN",
})
