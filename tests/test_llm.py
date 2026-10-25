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


class DailyLimit(Exception):
    status_code = 429
    response = types.SimpleNamespace(headers={})


def test_model_out_of_daily_quota_moves_to_the_next_model(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("LLM_CACHE", str(tmp_path / "c.json"))
    v = Voice()
    v.provider, v.model, v.rpm, v.record = "openai", "gpt-4.1-mini", 6000, False
    v.fallbacks = ["missing-model", "gpt-5-mini"]
    calls = []

    def create(**kw):
        calls.append(kw)
        if kw["model"] == "gpt-4.1-mini":
            raise DailyLimit("Rate limit reached for gpt-4.1-mini on requests per day (RPD): Limit 50")
        if kw["model"] == "missing-model":
            e = Exception("model_not_found"); e.status_code = 404; raise e
        msg = types.SimpleNamespace(content=json.dumps({"ok": True}))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
    v._client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    assert v.propose("sys", {"a": 2}) == ({"ok": True}, "llm")
    assert [c["model"] for c in calls] == ["gpt-4.1-mini", "missing-model", "gpt-5-mini"]
    assert v.model == "gpt-5-mini" and calls[-1]["reasoning_effort"] == "low"


def test_scene_a_asks_the_llm_three_times_not_once_per_product(monkeypatch):
    import agentrail.llm as L
    from agentrail import scenario
    L.reset_voice()
    v, systems = L.voice(), []

    def fake(system, payload):
        systems.append(system)
        if "procurement analyst" in system:
            return {"required_fields": ["lidar", "imu"], "gaps": [{"scenario": "night", "evidence": "x"}],
                    "purpose": "commercial_training", "max_missing_rate": 0.05}, "llm"
        return None, "rules"
    monkeypatch.setattr(v, "propose", fake)
    try:
        scenario.scene_a(scenario.build_world())
    finally:
        L.reset_voice()
    assert len(systems) == 3 and all("'items'" in s for s in systems[1:])
