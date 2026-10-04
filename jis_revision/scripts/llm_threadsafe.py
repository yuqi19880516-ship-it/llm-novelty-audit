"""Thread-safe chat-completion call for the audited base models (same endpoints, model IDs and keys as audit_pipeline.llm)."""
import json, time, urllib.request
from audit_pipeline.llm import load_env, REGISTRY
load_env()
_C = {m: REGISTRY[m]() for m in ("deepseek-v4-pro", "qwen3.7-max")}
def complete(model, prompt, max_tokens=2000, temperature=0.0, timeout=180):
    c = _C[model]
    body = json.dumps({"model": c.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": temperature}).encode()
    h = {"Authorization": f"Bearer {c.api_key}", "Content-Type": "application/json"}
    last = None
    for a in range(5):
        try:
            req = urllib.request.Request(c.base_url.rstrip("/") + "/chat/completions", data=body, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())["choices"][0]["message"]["content"] or ""
        except Exception as e:
            last = e; time.sleep(5 * (a + 1))
    raise last
