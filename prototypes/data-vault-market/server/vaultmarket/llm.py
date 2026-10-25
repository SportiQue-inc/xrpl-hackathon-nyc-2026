"""The agents' LLM. Every call is rate-limited across all 50 agents and capped per day.

The LLM writes the agent's thinking and its message to the other side, and may pick a price or a
verdict, but only inside the range code allows: `agents.py` clamps and checks every answer. When no
key is set, the cap is reached or a call fails, the agent answers from its written rules and the
trace says "rules" instead of the model name, so nobody mistakes a rule answer for an LLM one.
"""
from __future__ import annotations

import json
import threading
import time

from . import config

_lock = threading.Lock()
_calls: list[float] = []
USAGE = {"calls": 0, "fallbacks": 0, "in_tokens": 0, "out_tokens": 0, "day": time.strftime("%Y-%m-%d"), "provider": config.LLM_PROVIDER}
_client = None


def model_name() -> str:
    if config.LLM_PROVIDER == "anthropic":
        return config.ANTHROPIC_MODEL
    if config.LLM_PROVIDER == "openai":
        return config.OPENAI_MODEL
    return "rules"


def _slot() -> bool:
    """Take one call slot under the per-minute and per-day caps, or say no."""
    with _lock:
        now = time.time()
        if USAGE["day"] != time.strftime("%Y-%m-%d"):
            USAGE.update(day=time.strftime("%Y-%m-%d"), calls=0)
        if USAGE["calls"] >= config.LLM_DAILY_CALLS:
            return False
        while _calls and now - _calls[0] > 60:
            _calls.pop(0)
        if len(_calls) >= config.LLM_RPM:
            return False
        _calls.append(now)
        USAGE["calls"] += 1
        return True


_local = threading.local()


def free_slots() -> int:
    with _lock:
        now = time.time()
        recent = sum(1 for t in _calls if now - t <= 60)
        return max(0, min(config.LLM_RPM - recent, config.LLM_DAILY_CALLS - USAGE["calls"]))


def budget(n: int | None):
    """Cap the LLM calls the current thread may make (None = no extra cap). A negotiation takes a few
    slots at once so its key turns are all model-written, instead of a scatter of single calls."""
    _local.left = n


def _get_client():
    global _client
    if _client is None:
        if config.LLM_PROVIDER == "anthropic":
            import anthropic
            _client = anthropic.Anthropic()
        elif config.LLM_PROVIDER == "openai":
            import openai
            _client = openai.OpenAI()
    return _client


def ask_json(system: str, prompt: str, max_tokens: int = 500) -> dict | None:
    """One JSON object from the model, or None (caller falls back to its rules)."""
    left = getattr(_local, "left", None)
    if left is not None and left <= 0:
        USAGE["fallbacks"] += 1
        return None
    if config.LLM_PROVIDER not in ("anthropic", "openai") or not _slot():
        USAGE["fallbacks"] += 1
        return None
    if left is not None:
        _local.left = left - 1
    try:
        c = _get_client()
        if config.LLM_PROVIDER == "anthropic":
            r = c.messages.create(model=config.ANTHROPIC_MODEL, max_tokens=max_tokens,
                                  system=system + " Reply with one JSON object only, no prose around it.",
                                  messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            USAGE["in_tokens"] += r.usage.input_tokens
            USAGE["out_tokens"] += r.usage.output_tokens
        else:
            r = c.chat.completions.create(model=config.OPENAI_MODEL, max_tokens=max_tokens, response_format={"type": "json_object"},
                                          messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
            text = r.choices[0].message.content
            USAGE["in_tokens"] += r.usage.prompt_tokens
            USAGE["out_tokens"] += r.usage.completion_tokens
        s, e = text.find("{"), text.rfind("}")
        return json.loads(text[s:e + 1])
    except Exception:
        USAGE["fallbacks"] += 1
        return None
