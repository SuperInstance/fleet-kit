"""
fleet_kit.models — Fleet-native model router.

Three modes:
  creative — Seed-2.0-mini via local MCP (localhost:9438), temp 0.85
  fast     — DeepSeek-V3 via SiliconFlow API
  deep     — GLM-5.1 via z.ai API

Usage:
    from fleet_kit.models import FleetModelClient, ModelResponse

    client = FleetModelClient()
    resp = client.ask("What are 5 ways to solve X?", mode="creative")
    print(resp.text, resp.model, resp.tokens_in, resp.tokens_out)
"""

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ── Key loading ───────────────────────────────────────────────────────────────

def _load_key(name: str) -> str:
    """Load API key from environment, fallback to ~/.credentials_vault."""
    key = os.environ.get(name, "")
    if key:
        return key
    vault = Path.home() / ".credentials_vault"
    if vault.exists():
        for line in vault.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


# ── Response type ─────────────────────────────────────────────────────────────

@dataclass
class ModelResponse:
    """Standardized model response."""
    text: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


# ── FleetModelClient ──────────────────────────────────────────────────────────

class FleetModelClient:
    """
    Stateless model router — three modes, urllib only, no requests library.

    Keys loaded from environment then ~/.credentials_vault on first use.
    """
    # Per-mode config: (base_url, model, temperature, key_name, needs_ssl)
    _MODES = {
        "creative": dict(
            url="http://localhost:9438/v1/chat/completions",
            model="ByteDance/Seed-2.0-mini",
            temperature=0.85,
            key_name="DEEPINFRA_API_KEY",
            needs_ssl=False,
        ),
        "fast": dict(
            url="https://api.siliconflow.com/v1/chat/completions",
            model="deepseek-ai/DeepSeek-V3",
            temperature=0.7,
            key_name="SILICONFLOW_API_KEY",
            needs_ssl=True,
        ),
        "deep": dict(
            url="https://api.z.ai/api/coding/paas/v4/chat/completions",
            model="glm-5.1",
            temperature=0.7,
            key_name="ZAI_API_KEY",
            needs_ssl=True,
        ),
    }

    def __init__(self):
        self._keys = {mode: _load_key(cfg["key_name"]) for mode, cfg in self._MODES.items()}

    def ask(self, prompt: str, mode: str = "fast", max_tokens: int = 500) -> ModelResponse:
        """
        Call the model for the given mode.

        creative → Seed-2.0-mini via local MCP, temp 0.85
        fast     → DeepSeek-V3 via SiliconFlow, temp 0.7
        deep     → GLM-5.1 via z.ai, temp 0.7
        """
        cfg = self._MODES.get(mode)
        if not cfg:
            raise ValueError(f"Unknown mode {mode!r}. Valid: creative, fast, deep")

        payload = json.dumps({
            "model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": cfg["temperature"],
        }).encode()

        headers = {"Content-Type": "application/json"}
        if cfg["key_name"] != "DEEPINFRA_API_KEY":
            headers["Authorization"] = f"Bearer {self._keys[mode]}"

        req = urllib.request.Request(cfg["url"], data=payload, headers=headers)

        if cfg["needs_ssl"]:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            with opener.open(req, timeout=30) as r:
                resp = json.loads(r.read())
        else:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())

        choice = resp["choices"][0]["message"]
        text = choice.get("content") or choice.get("reasoning_content", "")
        usage = resp.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        return ModelResponse(text=text, model=cfg["model"], tokens_in=tokens_in, tokens_out=tokens_out)

    def ask_parallel(self, prompts: List[str], mode: str = "fast") -> List[ModelResponse]:
        """Call the model for each prompt in sequence (stateless, no batching)."""
        return [self.ask(p, mode=mode) for p in prompts]