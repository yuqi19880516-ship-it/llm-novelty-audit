"""核心数据模型：假设、溯源结果、新颖性分数、编码结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NoveltyLevel(Enum):
    """新颖性谱系（docs/03 §2、docs/05 §2.1）。"""
    L0_RECALL = "L0_复述"
    L1_RECOMBINATION = "L1_既知重组"
    L2_CROSS_LIT_NOVEL = "L2_跨文献新颖"
    L3_VALIDATED_NOVEL = "L3_受验证新发现"
    UNDETERMINED = "不可判定"


class Provenance(Enum):
    """溯源轴：系统凭什么得到它（docs/05 §2.2）。"""
    P0_SPOON_FED = "P0_被投喂"
    P1_RETRIEVAL = "P1_开放检索"
    P2_MEMORY = "P2_参数记忆"
    UNKNOWN = "未知"


@dataclass
class Hypothesis:
    """一条被审计的假设，规约为 A–B–C 三元组。"""
    id: str
    a: str                       # 起点概念（如药物）
    c: str                       # 终点概念（如疾病）
    b: Optional[str] = None      # 中介机制（成分/靶点/通路）
    claim_text: str = ""         # 系统输出的原始陈述
    system: str = ""             # 产出该假设的系统
    rank: Optional[int] = None   # 在系统排序中的名次
    run_date: str = ""           # 系统运行日（ISO），溯源以此为截断 T
    context_sources: list[str] = field(default_factory=list)  # 被投喂的输入材料（用于 P0 判定）


@dataclass
class ProvenanceResult:
    earliest_source_date: Optional[str] = None  # T 前最早出现该关联的文献日期
    earliest_source_id: Optional[str] = None
    exact_claim_found: bool = False             # T 前是否已有来源明确陈述该 A–C 关联 → L0
    cooccurrence_count_before_T: int = 0        # T 前 A、C 共现文献数
    memory_flag: bool = False                   # 裸 LLM 闭卷可复现 → P2
    in_context: bool = False                    # 连接性来源在系统输入上下文中 → P0
    backend: str = ""                           # 实际使用的后端（mock / pubmed）


@dataclass
class NoveltyScore:
    cooccurrence_z: Optional[float] = None  # 度保持(超几何)零模型 z（越低/负越新颖）
    poisson_z: Optional[float] = None       # 一阶独立零模型 z（v0，留作对比）
    disjoint: Optional[bool] = None         # 两支均达文献量下限却近乎零共现（Swanson disjointness）
    embedding_distance: Optional[float] = None
    kg_path_length: Optional[float] = None
    composite: Optional[float] = None       # 合成新颖分（越高越新颖）
    atypical: Optional[bool] = None         # 是否达"跨文献新颖"阈值（disjoint 或 z 反常）


@dataclass
class CodingResult:
    hypothesis_id: str
    novelty_level: NoveltyLevel
    provenance: Provenance
    novelty: NoveltyScore
    provenance_result: ProvenanceResult
    rationale: str = ""
    validated: bool = False  # 是否有后续独立验证（用于 L2→L3）

    def as_row(self) -> dict:
        return {
            "id": self.hypothesis_id,
            "L级": self.novelty_level.value,
            "溯源": self.provenance.value,
            "z": None if self.novelty.cooccurrence_z is None else round(self.novelty.cooccurrence_z, 2),
            "合成新颖分": None if self.novelty.composite is None else round(self.novelty.composite, 3),
            "理由": self.rationale,
        }
