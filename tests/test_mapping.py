"""Schema mapping: the LLM proposes, code verifies. A scripted proposer stands in for the LLM and
makes the kinds of mistakes a model makes; code must catch the ones checks can see."""
from agentrail.contract import mapping as M

# per (format, column): what the scripted model proposes
SCRIPT = {
    ("apple_health_xml", "sleep_minutes"): ("HKCategoryTypeIdentifierSleepAnalysis:HKCategoryValueSleepAnalysisAsleepCore", "min"),
    ("apple_health_xml", "resting_hr"): ("HKQuantityTypeIdentifierHeartRate", "count/min"),       # average HR: semantic
    ("garmin_json", "sleep_minutes"): ("sleeps.deepSleepDurationInSeconds", "s"),                  # one stage: typical band
    ("garmin_json", "resting_hr"): ("dailies.restingHeartRateInBeatsPerMinute", "bpm"),
    ("fitbit_json", "sleep_minutes"): ("sleep.timeInBed", "min"),                                  # in bed: semantic
    ("fitbit_json", "resting_hr"): ("activities-heart.value.restingHeartRate", "bpm"),
    ("fhir_bundle", "sleep_minutes"): ("Observation:93832-4", "min"),                              # hours called minutes
    ("fhir_bundle", "resting_hr"): ("Observation:8480-6", "bpm"),                                  # blood pressure
    ("survey_csv", "sleep_minutes"): (None, None),
    ("survey_csv", "resting_hr"): (None, None),
    ("robot_log_csv", "lidar_points"): ("lidar_n", "points"),
    ("robot_log_csv", "accel_x"): ("ax_mg", "m/s2"),                                               # mg called m/s2
    ("robot_log_csv", "wheel_speed"): ("wheel_rpm", "m/s"),                                        # no such field
}


def scripted(system, inp):
    fmt = inp["format"]
    return {"mappings": [{"column": c["column"], "field": SCRIPT[(fmt, c["column"])][0],
                          "unit": SCRIPT[(fmt, c["column"])][1], "why": "scripted"} for c in inp["columns"]]}


def run(fmt):
    return {r["column"]: r for r in M.map_source(None, "t", fmt, M.SOURCES[fmt](seed=1), M.TARGETS[fmt], scripted)["mappings"]}


def test_parse_every_format():
    for fmt, gen in M.SOURCES.items():
        vals, meta = M.parse(fmt, gen(seed=1))
        assert vals and all(isinstance(v, list) for v in vals.values())
    _, meta = M.parse("fhir_bundle", M.fhir(seed=1))
    assert meta["units"]["Observation:93832-4"] == "h"
    assert meta["display"]["Observation:40443-4"] == "Heart rate --resting"


def test_code_catches_unit_dimension_range_and_missing_field():
    f = run("fhir_bundle")
    assert not f["sleep_minutes"]["accepted"] and "declares h" in f["sleep_minutes"]["verdict"]
    assert not f["resting_hr"]["accepted"] and "mmHg" in f["resting_hr"]["verdict"]
    g = run("garmin_json")
    assert not g["sleep_minutes"]["accepted"] and "converted values" in g["sleep_minutes"]["verdict"]
    assert g["resting_hr"]["accepted"]
    r = run("robot_log_csv")
    assert not r["accel_x"]["accepted"] and "declares mg" in r["accel_x"]["verdict"]
    assert not r["wheel_speed"]["accepted"] and "no field" in r["wheel_speed"]["verdict"]
    assert r["lidar_points"]["accepted"]


def test_semantic_mistakes_pass_checks_and_are_counted_as_missed():
    assert run("fitbit_json")["sleep_minutes"]["accepted"]           # time in bed looks like sleep
    m = M.measure(scripted, seeds=(1,))
    out = {(d["format"], d["column"]): d["outcome"] for d in m["detail"]}
    assert out[("fitbit_json", "sleep_minutes")] == "missed"
    assert out[("garmin_json", "sleep_minutes")] == "caught"
    assert out[("survey_csv", "sleep_minutes")] == "declined"
    assert m["counts"]["caught"] == 5 and m["counts"]["missed"] == 2


def test_conversion_factor_and_declared_unit_agree():
    r = run("apple_health_xml")
    assert r["sleep_minutes"]["final"]["factor"] == 1.0
    ok, _ = M.verify("sleep_minutes", "Observation:93832-4", "h", *M.parse("fhir_bundle", M.fhir(seed=1)))
    assert ok
    ok, why = M.verify("wheel_speed", "v_kmh", "km/h", *M.parse("robot_log_csv", M.robot_log(seed=1)))
    assert ok, why


def test_rules_fallback_when_no_llm():
    m = M.measure(lambda s, i: None, seeds=(1,))
    assert all(d["by"] == "rules" for d in m["detail"])
    assert m["cases"] == 13 and 0 < m["final_accuracy"] <= 1


def test_proposal_audited(tmp_path):
    from agentrail.db import Store
    s = Store(str(tmp_path / "t.db"))
    M.map_source(s, "mapper", "fhir_bundle", M.fhir(seed=1), M.HEALTH, scripted)
    row = s.one("SELECT * FROM proposals WHERE task='map_source'")
    assert row and "declares h" in row["verdict"]
