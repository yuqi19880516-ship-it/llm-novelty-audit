"""LLM 适配器接口 + Mock 实现。

被审基座(DeepSeek-V4 / Qwen-最新 / DeepSeek-V3 断层切点)与外部编码器(Claude/Gemini)
都通过 LLMClient 接口接入。编码器**必须异于被审基座家族**(防"自己审自己"，docs/05 §2.4)。

真实客户端读环境变量里的 API key；此处仅给最小骨架与 Mock，保证无 key 也能跑通。
"""
from __future__ import annotations

import os
from typing import Protocol


def load_env(path: str = ".env") -> None:
    """把 .env 读进 os.environ（不覆盖已存在变量）。"""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class LLMClient(Protocol):
    name: str
    family: str  # "deepseek" / "qwen" / "anthropic" / "google" ...

    def complete(self, prompt: str, **kw) -> str: ...


class MockLLMClient:
    """确定性 Mock：用于无 key 的端到端联调。"""
    def __init__(self, name: str = "mock", family: str = "mock", canned: dict | None = None):
        self.name = name
        self.family = family
        self._canned = canned or {}

    def complete(self, prompt: str, **kw) -> str:
        for key, val in self._canned.items():
            if key in prompt:
                return val
        return "MOCK_RESPONSE"


class OpenAICompatibleClient:
    """DeepSeek / Qwen 等 OpenAI 兼容接口的占位实现。

    需要 `pip install openai` 与对应 api_key/base_url；未配置时 complete() 抛错。
    """
    def __init__(self, name: str, family: str, base_url: str, api_key_env: str, model: str):
        self.name = name
        self.family = family
        self.base_url = base_url
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        # 用量计量（用于成本估算）
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def complete(self, prompt: str, max_tokens: int = 1024,
                 temperature: float = 0.0, timeout: int = 120, **kw) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.name}: 未设置 API key（检查 .env / 环境变量）。")
        import json
        import signal
        import time
        import urllib.request

        class _CallTimeout(Exception):
            pass

        def _on_alarm(signum, frame):
            raise _CallTimeout("hard deadline exceeded")

        url = self.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last = None
        for attempt in range(6):  # 扛断网/代理挂死连接
            try:
                prev = signal.signal(signal.SIGALRM, _on_alarm)
                signal.alarm(int(timeout) + 5)  # 硬截止：即便 urllib timeout 不生效也强制中断
                try:
                    req = urllib.request.Request(url, data=body, headers=headers)
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        data = json.loads(r.read().decode())
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, prev)
                u = data.get("usage", {}) or {}
                self.calls += 1
                self.prompt_tokens += u.get("prompt_tokens", 0)
                self.completion_tokens += u.get("completion_tokens", 0)
                return data["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(min(60.0, 5.0 * (2 ** attempt)))
        raise last


# 预置注册表（2026-06 实测可用的确切型号 ID）
_DASHSCOPE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
REGISTRY = {
    # 主审基座（强档）
    "deepseek-v4-pro":   lambda: OpenAICompatibleClient("deepseek-v4-pro", "deepseek",
                            "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-v4-pro"),
    "qwen3.7-max":       lambda: OpenAICompatibleClient("qwen3.7-max", "qwen",
                            _DASHSCOPE, "DASHSCOPE_API_KEY", "qwen3.7-max-2026-05-20"),
    # 省档（大规模生成可选，降成本）
    "deepseek-v4-flash": lambda: OpenAICompatibleClient("deepseek-v4-flash", "deepseek",
                            "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-v4-flash"),
    "qwen3.7-plus":      lambda: OpenAICompatibleClient("qwen3.7-plus", "qwen",
                            _DASHSCOPE, "DASHSCOPE_API_KEY", "qwen3.7-plus-2026-05-26"),
    # 断层测试(RQ2)用的老模型：DeepSeek 官方已无 V3，走 DashScope
    "deepseek-v3":       lambda: OpenAICompatibleClient("deepseek-v3", "deepseek",
                            _DASHSCOPE, "DASHSCOPE_API_KEY", "vanchin/deepseek-v3"),
}
