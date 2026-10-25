"""LLM client behaviour without the network: pacing, 429 retry, replay on failure."""
import json
import types

from agentrail.llm import Voice


class RateLimited(Exception):
    status_code = 429
    response = types.SimpleNamespace(headers={"retry-after": "0"})


def fake_client(fail_times):
    calls = []

    def create(**kw):
        calls.append(kw)
        if len(calls) <= fail_times:
            raise RateLimited("rate limit reached for requests")
        msg = types.SimpleNamespace(content=json.dumps({"ok": True}))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))), calls


def voice(tmp_path, monkeypatch, fail_times):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("LLM_CACHE", str(tmp_path / "c.json"))
    v = Voice()
    v.provider, v.model, v.rpm, v.record = "openai", "o3-mini", 6000, True
    v._client, calls = fake_client(fail_times)
    return v, calls


def test_429_is_retried_and_reasoning_model_gets_effort_and_user_tag(tmp_path, monkeypatch):
    v, calls = voice(tmp_path, monkeypatch, fail_times=2)
    assert v.propose("sys", {"a": 1}) == ({"ok": True}, "llm")
    assert len(calls) == 3 and calls[-1]["reasoning_effort"] == "low" and calls[-1]["user"]


def test_failed_call_replays_the_recorded_answer(tmp_path, monkeypatch):
    v, _ = voice(tmp_path, monkeypatch, fail_times=0)
    v.propose("sys", {"a": 1})                       # recorded
    v2, _ = voice(tmp_path, monkeypatch, fail_times=9)  # every live call fails now
    assert v2.propose("sys", {"a": 1}) == ({"ok": True}, "llm")
    assert v2.propose("sys", {"a": 2}) == (None, "rules")
