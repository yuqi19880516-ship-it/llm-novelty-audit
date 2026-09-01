"""Co-Scientist 范式的忠实但精简复刻（被审系统）。

对应原型 arXiv:2502.18864 的 生成-辩论-进化-排序 内核：
    Generation → Reflection → Ranking(Elo 锦标赛) → Evolution →（循环）→ Meta-review
产出 = 带 A–B–C、新颖性自评、Elo 排名的假设列表，交审计流水线评估。

注意：这是"被审计对象"，不是审计器。它故意做成可消融（关掉某个 agent）以支持消融实验。
"""
from .system import CoScientist, CoSciHypothesis  # noqa: F401
