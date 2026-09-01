"""
audit_pipeline —— 多智能体大模型科研系统"知识新颖性"审计流水线。

对应研究蓝图 docs/03、方法落地 docs/05。
一条假设(A–B–C 三元组)的处理链路:
    Hypothesis → Provenance(溯源) → Novelty(科学计量新颖性) → Coding(谱系/溯源判定) → CodingResult

设计原则:
- 所有外部依赖(LLM、PubMed)通过适配器接口注入;默认提供 Mock 实现,无 key/无网亦可端到端跑通。
- L0(复述)由自动溯源判定;L1/L2 边界由科学计量原子组合客观锚定;LLM 仅做实体抽取与边界辅助。
"""

__version__ = "0.1.0"
