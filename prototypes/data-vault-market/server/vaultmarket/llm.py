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
USAGE = {"calls": 0, "fallbacks": 0, "in_tokens": 0, "out_tokens": 0, "day": time.strftime("%Y-%m-%d", time.gmtime()), "provider": config.LLM_PROVIDER}
_client = None


_rest: dict[str, float] = {}      # model -> time it may be called again (after a 429)
_last = threading.local()


def model_name() -> str:
    """The actual source of this thread's last answer."""
    return getattr(_last, "model", "rules")


def models() -> list[str]:
    """Only model IDs already allowed by the service's current provider configuration."""
    if config.LLM_PROVIDER == "anthropic":
        return ["auto", config.ANTHROPIC_MODEL]
    if config.LLM_PROVIDER == "openai":
        return ["auto", *dict.fromkeys(config.OPENAI_MODELS)]
    return ["auto"]


def _reset_seconds(text: str | None) -> float:
    """OpenAI's x-ratelimit-reset-requests, e.g. '1m30s', '6h0m0s', '850ms' -> seconds (15 min if unknown)."""
    import re
    if not text:
        return 900.0
    total = 0.0
    for n, unit in re.findall(r"([\d.]+)(ms|h|m|s)", text):
        total += float(n) * {"ms": 0.001, "h": 3600, "m": 60, "s": 1}[unit]
    return total or 900.0


def _openai(c, system: str, prompt: str, max_tokens: int, model: str = "auto"):
    """Try each configured model in order; one that is rate-limited rests until its reset and the next is tried."""
    import openai
    system += " Reply with one JSON object only."     # json_object mode requires the word JSON in the prompt
    for m in config.OPENAI_MODELS if model == "auto" else [model]:
        if _rest.get(m, 0) > time.time():
            continue
        kw = {"max_completion_tokens": max_tokens}
        if m.startswith(("gpt-5", "o")):
            kw = {"max_completion_tokens": max_tokens + 1500, "reasoning_effort": config.OPENAI_REASONING}
        try:
            r = c.chat.completions.create(model=m, response_format={"type": "json_object"},
                                          messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}], **kw)
        except openai.RateLimitError as e:
            h = getattr(getattr(e, "response", None), "headers", {}) or {}
            quota = "insufficient_quota" in str(e)
            _rest[m] = time.time() + (6 * 3600 if quota else _reset_seconds(h.get("x-ratelimit-reset-requests")))
            USAGE.setdefault("rate_limited", {})[m] = time.strftime("%H:%M:%S")
            continue
        except openai.BadRequestError:
            if "reasoning_effort" in kw:              # a model that takes no reasoning setting: once more without it
                kw.pop("reasoning_effort")
                r = c.chat.completions.create(model=m, response_format={"type": "json_object"},
                                              messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}], **kw)
            else:
                raise
        _last.model = getattr(r, "model", None) or m
        return r
    return None


def _slot() -> bool:
    """Take one call slot under the per-minute and per-day caps, or say no."""
    with _lock:
        now = time.time()
        if USAGE["day"] != time.strftime("%Y-%m-%d", time.gmtime()):
            USAGE.update(day=time.strftime("%Y-%m-%d", time.gmtime()), calls=0)
        if USAGE["calls"] >= _paced_cap(now):
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
        return max(0, min(config.LLM_RPM - recent, _paced_cap(now) - USAGE["calls"]))


def _paced_cap(now: float) -> int:
    """The daily cap spread over the UTC day (plus a small head start), so it isn't spent in the first hour."""
    t = time.gmtime(now)
    return min(config.LLM_DAILY_CALLS, int(config.LLM_DAILY_CALLS * (t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec) / 86400) + 12)


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


def ask_json(system: str, prompt: str, max_tokens: int = 500, model: str = "auto") -> dict | None:
    """One JSON object from the model, or None (caller falls back to its rules)."""
    _last.model = "rules"
    if not isinstance(model, str) or model not in models():
        USAGE["fallbacks"] += 1
        return None
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
            _last.model = getattr(r, "model", None) or config.ANTHROPIC_MODEL
        else:
            r = _openai(c, system, prompt, max_tokens, model)
            if r is None:                            # every model is resting after a 429: rules until one resets
                USAGE["fallbacks"] += 1
                return None
            text = r.choices[0].message.content
            USAGE["in_tokens"] += r.usage.prompt_tokens
            USAGE["out_tokens"] += r.usage.completion_tokens
        s, e = text.find("{"), text.rfind("}")
        out = json.loads(text[s:e + 1])
        if not isinstance(out, dict):
            raise ValueError("Expected a JSON object")
        return out
    except Exception:
        _last.model = "rules"
        USAGE["fallbacks"] += 1
        return None
