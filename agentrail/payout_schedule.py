"""Payout schedules: one rail (key-reveal escrow, sealed push), three schedules by study type.

Every check that can run on values runs before any money moves: the source issuer's seal (the issuer
encrypted the columns with the participant agent's K and signed that they open with condition
SHA-256(K), which must equal the escrow's), the issuer's DATA_SOURCE credential, schema, units and
ranges. A tampered contribution therefore fails before payment and gets 0. What is held back covers
only what can be seen after opening (quality drift against the person's own history).

  prospective     data arrives week by week. Pay grows with continuity: the upfront share of a
                  verified week starts at 50% and rises with each consecutive verified week, and the
                  weekly rate steps up after 2, 4 and 8 consecutive weeks. A gap (missed or failed
                  week) resets the streak, never takes back what was paid
  retrospective   the dataset already exists in full: the buyer's agent inspects the certificate, a
                  hashed sample and the provenance seal before buying, then pays it whole on delivery
                  (one shot, nothing held)
  hybrid          a retrospective baseline paid once, then prospective follow-up weeks on the curve;
                  two parts of one contract
"""
from __future__ import annotations

FIRST_SHARE = 50          # % of a verified week paid when the key is revealed, first week of a streak
STEP_SHARE = 10           # + per consecutive verified week
MAX_SHARE = 90
RATE_STEPS = [(8, 1.3), (4, 1.2), (2, 1.1)]     # consecutive verified weeks -> weekly rate multiplier


def streak_after(history: list[bool]) -> int:
    """Consecutive verified weeks at the end of the history."""
    n = 0
    for ok in reversed(history):
        if not ok:
            break
        n += 1
    return n


def prospective(base_drops: int, history: list[bool]) -> dict:
    """Terms for the next week, given the verified/failed history so far."""
    s = streak_after(history)
    mult = next((m for k, m in RATE_STEPS if s >= k), 1.0)
    week = int(base_drops * mult)
    share = min(MAX_SHARE, FIRST_SHARE + STEP_SHARE * s)
    up = week * share // 100
    return {"schedule": "prospective", "streak_before": s, "rate_multiplier": mult, "week_drops": week,
            "upfront_pct": share, "upfront_drops": up, "held_drops": week - up,
            "held_covers": "quality drift visible only after opening"}


def retrospective(price_drops: int) -> dict:
    return {"schedule": "retrospective", "week_drops": price_drops, "upfront_pct": 100, "upfront_drops": price_drops,
            "held_drops": 0, "verified_before": ["quality certificate", "hashed sample", "provenance seal"]}


def hybrid(baseline_drops: int, base_week_drops: int, history: list[bool]) -> dict:
    return {"schedule": "hybrid", "baseline": retrospective(baseline_drops),
            "follow_up": prospective(base_week_drops, history)}


def simulate(base_drops: int, weeks: list[bool]) -> list[dict]:
    """Each week's terms and outcome: a failed week pays 0 (it failed before payment) and resets."""
    out, hist = [], []
    for ok in weeks:
        t = prospective(base_drops, hist)
        out.append({**t, "verified": ok, "paid_drops": t["week_drops"] if ok else 0})
        hist.append(ok)
    return out
