"""Optional LLM voice for the agents.

The LLM only turns a decision that code already made into a sentence. It never sees
raw data (only item names, prices, reasons) and its output is never parsed back into
a decision, so it cannot widen a permission or raise a limit.

  LLM_PROVIDER   openai (default when OPENAI_API_KEY is set) | anthropic | none
  OPENAI_API_KEY, OPENAI_MODEL       (default gpt-4o-mini)
  ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default claude-opus-5-5)
  LLM_RECORD=1   save every JSON proposal to fixtures/llm_cache.json
  LLM_PROVIDER=replay   answer proposals from that file only (recorded runs, for a stable video)

No key, a timeout or any API error -> the rule-based sentence is used and the LLM is
switched off for the rest of the run, so the demo never stalls.
"""
from __future__ import annotations

import json
import os
import threading

SYSTEM = (
    "You write one short line of dialogue (max 30 words) for a software agent in a data "
    "procurement demo. Speak as the agent, to the counterpart named. State only the facts "
    "given; do not add numbers, items, promises or permissions that are not in the facts. "
    "Plain English, no emoji, no markdown.")


def _load_dotenv(path: str = ".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Voice:
    def __init__(self):
        _load_dotenv()
        p = os.environ.get("LLM_PROVIDER", "").lower()
        self.cache_path = os.environ.get("LLM_CACHE", os.path.join(os.path.dirname(__file__), "..", "fixtures",
                                                                    "llm_cache.json"))
        self.record = os.environ.get("LLM_RECORD") == "1"
        self.cache = {}
        if os.path.exists(self.cache_path):
            with open(self.cache_path) as f:
                self.cache = json.load(f)
        if not p:
            p = "openai" if os.environ.get("OPENAI_API_KEY") else (
                "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "none")
        self.provider = p
        self.timeout = float(os.environ.get("LLM_TIMEOUT", "8"))
        self.max_calls = int(os.environ.get("LLM_MAX_CALLS", "60"))
        self.calls = 0
        self.error: str | None = None
        self._lock = threading.Lock()
        self._client = None
        try:
            if p == "openai":
                from openai import OpenAI
                self._client = OpenAI(timeout=self.timeout, max_retries=0)
                self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            elif p == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(timeout=self.timeout, max_retries=0)
                self.model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")
        except Exception as e:  # SDK missing or no credentials
            self._off(e)

    @property
    def active(self) -> bool:
        return self._client is not None

    def label(self) -> str:
        if self.provider == "replay":
            return f"replay of recorded LLM answers ({len(self.cache)})"
        return f"{self.provider}:{self.model}" if self.active else "rules"

    @staticmethod
    def _key(system: str, payload: dict) -> str:
        import hashlib
        return hashlib.sha256((system + json.dumps(payload, sort_keys=True)).encode()).hexdigest()

    def _off(self, e: Exception):
        self.error = f"{type(e).__name__}: {e}"[:200]
        self._client = None

    def _ask(self, prompt: str) -> str:
        if self.provider == "openai":
            r = self._client.chat.completions.create(
                model=self.model, max_completion_tokens=400,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
            return (r.choices[0].message.content or "").strip()
        r = self._client.messages.create(
            model=self.model, max_tokens=1000, system=SYSTEM, output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in r.content if b.type == "text").strip()

    def _ask_json(self, system: str, prompt: str) -> dict:
        if self.provider == "openai":
            r = self._client.chat.completions.create(
                model=self.model, max_completion_tokens=1500, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
            text = r.choices[0].message.content or ""
        else:
            r = self._client.messages.create(
                model=self.model, max_tokens=4000, system=system + " Reply with one JSON object only.",
                output_config={"effort": "low"}, messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in r.content if b.type == "text")
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[1] if "\n" in text else text
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1])

    def propose(self, system: str, payload: dict) -> tuple[dict | None, str]:
        """Ask for a JSON proposal. Returns (proposal, 'llm') or (None, 'rules').
        The caller validates every field; nothing here is trusted."""
        key = self._key(system, payload)
        if self.provider == "replay":
            hit = self.cache.get(key)
            return (hit["answer"], "llm") if hit else (None, "rules")
        with self._lock:
            if not self.active or self.calls >= self.max_calls:
                return None, "rules"
            self.calls += 1
        try:
            out = self._ask_json(system, json.dumps(payload, ensure_ascii=False))
            if self.record and isinstance(out, dict):
                with self._lock:
                    self.cache[key] = {"model": self.model, "answer": out}
                    with open(self.cache_path, "w") as f:
                        json.dump(self.cache, f, indent=1, sort_keys=True)
        except Exception as e:
            with self._lock:
                self._off(e)
            return None, "rules"
        return (out, "llm") if isinstance(out, dict) else (None, "rules")

    def say(self, speaker: str, to: str | None, facts: dict, fallback: str) -> tuple[str, str]:
        """Return (sentence, source). Source is 'llm' or 'rules'."""
        with self._lock:
            if not self.active or self.calls >= self.max_calls:
                return fallback, "rules"
            self.calls += 1
        prompt = (f"Agent: {speaker}\nTalking to: {to or 'its owner'}\n"
                  f"Facts (already decided by code): {json.dumps(facts, ensure_ascii=False)}\n"
                  f"Reference sentence: {fallback}")
        try:
            text = self._ask(prompt)
        except Exception as e:
            with self._lock:
                self._off(e)
            return fallback, "rules"
        if not text or len(text) > 400:
            return fallback, "rules"
        return text, "llm"


_voice: Voice | None = None


def voice() -> Voice:
    global _voice
    if _voice is None:
        _voice = Voice()
    return _voice


def reset_voice():
    global _voice
    _voice = None
