"""LLM agents add signals, never verdicts."""
from agentrail import signals as S


def test_presend_asks_the_person_about_slips():
    r = S.presend("P-1", [{"day": 4, "fatigue.survey": 15}, {"day": 5, "fatigue.survey": 6}], propose=lambda s, i: None)
    assert r["hold_until_answered"] and "15" in r["questions"][0] and len(r["slips"]) == 1
    llm = lambda s, i: {"questions": ["4주차 피로도가 15로 나와요. 맞나요?"]}
    assert S.presend("P-1", [{"day": 4, "fatigue.survey": 15}], llm)["questions"] == ["4주차 피로도가 15로 나와요. 맞나요?"]
    assert not S.presend("P-1", [{"day": 1, "fatigue.survey": 5}], llm)["hold_until_answered"]


def test_buyer_flags_have_evidence_and_decide_nothing():
    feats = S.features({"P-1": [1, 2, 3, 4, 5, 6], "P-2": [5, 3, 6, 2, 7, 4], "P-3": [4, 6, 5, 3, 5, 6]},
                       answer_ms={"P-2": [300, 250, 280]},
                       free_text={"P-2": ["I slept poorly because of the night shift"],
                                  "P-3": ["I slept poorly because of the night shift"]})
    llm = lambda s, i: {"flags": [{"person": "P-3", "signal": "odd", "evidence": "x"},                # no evidence: dropped
                                  {"person": "P-9", "signal": "x", "evidence": "a long enough evidence"},  # unknown person
                                  {"person": "P-1", "signal": "pattern", "evidence": "rises by exactly 1 every day"}]}
    r = S.buyer_flags(feats, llm)
    sig = {(f["person"], f["signal"], f["by"]) for f in r["flags"]}
    assert ("P-1", "too_smooth", "code") in sig and ("P-2", "inhuman_answer_time", "code") in sig
    assert ("P-2", "shared_free_text", "code") in sig and ("P-3", "shared_free_text", "code") in sig
    assert ("P-1", "pattern", "llm") in sig and not any(f["person"] == "P-9" for f in r["flags"])
    assert r["llm_calls"] == 1 and "named reviewer" in r["decides"]


def test_signals_cannot_touch_payout():
    import inspect
    src = inspect.getsource(S)
    assert "payout.decide(" not in src and "UPDATE" not in src and "holdbacks" not in src
