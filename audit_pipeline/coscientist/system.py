"""Co-Scientist 范式复刻：生成-反思-Elo锦标赛-进化-元评审。"""
from __future__ import annotations

import itertools
import json
import random
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------- 工具：从 LLM 文本里稳健抽 JSON ----------
def _extract_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # 找第一个 [ 或 { 起的合法 JSON
    for opener, closer in (("[", "]"), ("{", "}")):
        i = text.find(opener)
        if i >= 0:
            depth = 0
            for j in range(i, len(text)):
                if text[j] == opener:
                    depth += 1
                elif text[j] == closer:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[i:j + 1])
                        except Exception:
                            break
    try:
        return json.loads(text)
    except Exception:
        return None


def _as_list(data) -> list:
    """把 LLM 解析结果归一成 list：数组直接用；{"hypotheses":[...]} 取其列表值；其余包成单元素。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    return []


@dataclass
class CoSciHypothesis:
    a: str = ""
    b: str = ""
    c: str = ""
    statement: str = ""
    rationale: str = ""
    self_novelty: str = ""          # 系统自评新颖性（供叙事落差分析）
    elo: float = 1200.0
    review_score: Optional[float] = None  # 反思 agent 的均分（novelty/correctness/plausibility）
    reviews: list = field(default_factory=list)

    def key(self) -> str:
        return f"{self.a.lower()}|{self.c.lower()}"


# ---------- 主系统 ----------
class CoScientist:
    def __init__(self, llm, *, n_initial: int = 6, rounds: int = 1,
                 max_matches_per_round: int = 12, seed: int = 42,
                 enable_reflection: bool = True,
                 enable_tournament: bool = True,
                 enable_evolution: bool = True,
                 verbose: bool = True):
        self.llm = llm
        self.n_initial = n_initial
        self.rounds = rounds
        self.max_matches = max_matches_per_round
        self.seed = seed
        random.seed(seed)  # 对决配对抽样可复现
        self.enable_reflection = enable_reflection
        self.enable_tournament = enable_tournament
        self.enable_evolution = enable_evolution
        self.verbose = verbose

    def _log(self, msg):
        if self.verbose:
            print(f"  [co-sci] {msg}")

    # —— Generation ——
    def generate(self, goal: str, n: int) -> list[CoSciHypothesis]:
        prompt = (
            f"你是科研假设生成 agent。研究目标：{goal}\n"
            f"提出 {n} 条**新颖、可验证**的假设，每条规约为 A(起点)–B(中介机制)–C(终点)。\n"
            f"self_novelty 自评 completely_novel/moderate/known；statement 与 rationale **各限一句话**。\n"
            f"⚠ 只输出合法 JSON 数组本身，不要 markdown 代码块、不要任何解释文字。元素形如："
            '{"A":"","B":"","C":"","statement":"","rationale":"","self_novelty":""}'
        )
        out: list[CoSciHypothesis] = []
        for _ in range(2):
            data = _as_list(_extract_json(self.llm.complete(prompt, max_tokens=8000)))
            for d in data[:n]:
                if isinstance(d, dict) and d.get("A") and d.get("C"):
                    out.append(CoSciHypothesis(
                        a=d.get("A", ""), b=d.get("B", ""), c=d.get("C", ""),
                        statement=d.get("statement", ""), rationale=d.get("rationale", ""),
                        self_novelty=d.get("self_novelty", "")))
            if out:
                break
        self._log(f"Generation → {len(out)} 条假设")
        return out

    # —— Reflection（批量一次）——
    def reflect(self, hyps: list[CoSciHypothesis], goal: str):
        if not self.enable_reflection or not hyps:
            return
        listing = "\n".join(
            f'{i}. {h.a} → {h.c} (via {h.b}): {h.statement}' for i, h in enumerate(hyps))
        prompt = (
            f"你是同行评审 agent。研究目标：{goal}\n对下列假设逐条评审：\n{listing}\n\n"
            "对每条给 novelty/correctness/plausibility 三个 1-5 分及一句(≤20字)critique。\n"
            '⚠ 只输出合法 JSON 数组本身，不要 markdown、不要解释。元素：'
            '{"index":0,"novelty":3,"correctness":4,"plausibility":4,"critique":""}'
        )
        data = []
        for _ in range(2):
            data = _as_list(_extract_json(self.llm.complete(prompt, max_tokens=4000)))
            if data:
                break
        applied = 0
        for d in data:
            if not isinstance(d, dict):
                continue
            i = d.get("index")
            if not (isinstance(i, int) and 0 <= i < len(hyps)):
                continue
            hyps[i].reviews.append(d)
            sc = [d.get(k) for k in ("novelty", "correctness", "plausibility")]
            sc = [s for s in sc if isinstance(s, (int, float))]
            if sc:
                ms = sum(sc) / len(sc)
                hyps[i].review_score = ms
                hyps[i].elo += (ms - 3.0) * 15.0   # 反思质量先验 → 影响排序，使消融有效
            applied += 1
        self._log(f"Reflection → 评审 {applied} 条")

    # —— Ranking：Elo 锦标赛，成对科学辩论 ——
    def _debate(self, h1: CoSciHypothesis, h2: CoSciHypothesis, goal: str) -> int:
        prompt = (
            f"科研目标：{goal}\n两条假设做科学辩论，哪条更优（新颖性+合理性+可验证性）？\n"
            f"A) {h1.a}→{h1.c}: {h1.statement}\n"
            f"B) {h2.a}→{h2.c}: {h2.statement}\n"
            '只输出 JSON：{"winner":"A" 或 "B","reason":""}'
        )
        d = _extract_json(self.llm.complete(prompt, max_tokens=400)) or {}
        return 1 if str(d.get("winner", "A")).upper().startswith("A") else 2

    def tournament(self, hyps: list[CoSciHypothesis], goal: str):
        if not self.enable_tournament or len(hyps) < 2:
            return
        pairs = list(itertools.combinations(range(len(hyps)), 2))
        random.shuffle(pairs)            # 无偏抽样对决（替代偏向靠前索引的截断）
        pairs = pairs[:self.max_matches]
        for i, j in pairs:
            w = self._debate(hyps[i], hyps[j], goal)
            self._elo_update(hyps[i], hyps[j], winner_first=(w == 1))
        self._log(f"Ranking → {len(pairs)} 场对决")

    @staticmethod
    def _elo_update(h1, h2, *, winner_first: bool, k: float = 32.0):
        e1 = 1 / (1 + 10 ** ((h2.elo - h1.elo) / 400))
        s1 = 1.0 if winner_first else 0.0
        h1.elo += k * (s1 - e1)
        h2.elo += k * ((1 - s1) - (1 - e1))

    # —— Evolution：从 top 假设衍生新假设 ——
    def evolve(self, hyps: list[CoSciHypothesis], goal: str, top_k: int = 3) -> list[CoSciHypothesis]:
        if not self.enable_evolution or not hyps:
            return []
        top = sorted(hyps, key=lambda h: h.elo, reverse=True)[:top_k]
        listing = "\n".join(f'- {h.a}→{h.c}: {h.statement}' for h in top)
        prompt = (
            f"你是进化 agent。研究目标：{goal}\n基于下列高分假设，通过组合/精化/跳出框，"
            f"生成 2 条**新**假设（不要重复原有），statement 与 rationale 各限一句话：\n{listing}\n"
            '⚠ 只输出合法 JSON 数组本身，不要 markdown、不要解释。元素：'
            '{"A":"","B":"","C":"","statement":"","rationale":"","self_novelty":""}'
        )
        out: list[CoSciHypothesis] = []
        for _ in range(2):
            data = _as_list(_extract_json(self.llm.complete(prompt, max_tokens=2500)))
            for d in data:
                if isinstance(d, dict) and d.get("A") and d.get("C"):
                    out.append(CoSciHypothesis(a=d.get("A", ""), b=d.get("B", ""), c=d.get("C", ""),
                        statement=d.get("statement", ""), rationale=d.get("rationale", ""),
                        self_novelty=d.get("self_novelty", "")))
            if out:
                break
        self._log(f"Evolution → 新增 {len(out)} 条")
        return out

    # —— Meta-review ——
    def meta_review(self, hyps: list[CoSciHypothesis], goal: str) -> str:
        top = sorted(hyps, key=lambda h: h.elo, reverse=True)[:5]
        listing = "\n".join(f'- {h.a}→{h.c} (Elo {h.elo:.0f}): {h.statement}' for h in top)
        prompt = (f"你是元评审 agent。研究目标：{goal}\n请用中文写一段 150–200 字的研究综述，"
                  f"直接给出综述正文（不要前言、标题或解释）：\n{listing}")
        ov = ""
        for _ in range(2):
            try:
                ov = self.llm.complete(prompt, max_tokens=1200).strip()
            except Exception:
                ov = ""
            if ov:
                break
        if not ov:  # 兜底：本地拼一段，避免空综述
            ov = "Top hypotheses: " + "; ".join(f"{h.a}→{h.c}" for h in top)
        return ov

    # —— 编排 ——
    def run(self, goal: str) -> dict:
        hyps = self.generate(goal, self.n_initial)
        for r in range(self.rounds):
            self._log(f"—— round {r + 1}/{self.rounds} ——")
            self.reflect(hyps, goal)
            self.tournament(hyps, goal)
            hyps += self.evolve(hyps, goal)
        self.reflect(hyps, goal)
        self.tournament(hyps, goal)
        overview = self.meta_review(hyps, goal)
        hyps.sort(key=lambda h: h.elo, reverse=True)
        return {"goal": goal, "hypotheses": hyps, "overview": overview}
