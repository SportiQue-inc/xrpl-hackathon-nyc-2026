"""Running cost of keeping the agents up: LLM calls and tokens per side, ledger transactions and fees,
reserve tied up, per participant-week. Counts come from this process; nothing is estimated except
where marked (the mock ledger has no fees, so it uses the reference fee)."""
from __future__ import annotations

REFERENCE_FEE = 10           # drops, the base transaction cost
OWNER_RESERVE = 200_000      # drops per ledger object (escrow, credential) while it exists
BASE_RESERVE = 1_000_000     # drops per account


def ledger_stats(ledger) -> dict:
    if ledger.name == "mock":
        n = len(ledger.txs)
        return {"txs": n, "fee_drops": n * REFERENCE_FEE, "fee_source": f"reference fee {REFERENCE_FEE} drops (mock)",
                "open_escrows": len(ledger.escrows)}
    from .ledger.xrpl_ledger import TX_STATS
    return {"txs": TX_STATS["submitted"], "fee_drops": TX_STATS["fee_drops"], "fee_source": "Fee field of each tx sent",
            "open_escrows": None}


def line(c: dict) -> str:
    """The cost block printed at the end of the integrated run."""
    u, l, p = c["llm"], c["ledger"], c["per_participant_week"]
    side = lambda s: (f"{s}: {u[s]['live_calls']} live + {u[s]['replayed_calls']} recorded calls, "
                      f"{u[s]['input_tokens']} in / {u[s]['output_tokens']} out tokens live "
                      f"({u[s]['replayed_input_tokens']} / {u[s]['replayed_output_tokens']} recorded)")
    return "\n".join([
        f"Running cost ({u['model']}, {c['participants']} participants, {c['participant_weeks']} participant-weeks)",
        "  LLM " + side("research"), "  LLM " + side("participant"),
        f"  Ledger: {l['txs']} tx, {l['fee_drops']} drops in fees ({l['fee_source']})",
        f"  Reserve tied up: {l['reserve_tied_xrp']:g} XRP in open escrows, "
        f"plus {l['participant_wallet_base_reserve_xrp']:g} XRP base reserve per participant wallet",
        f"  Per participant-week: {p['llm_calls']} LLM calls, {p['llm_tokens_live']} live tokens, "
        f"{p['ledger_txs']} tx, {p['fee_xrp']:.6f} XRP in fees"])


def summarize(w) -> dict:
    from .llm import voice
    v = voice()
    led = ledger_stats(w.ledger)
    people = len(getattr(w, "cohort_people", {}) or {}) or 1
    weeks = w.store.one("SELECT COUNT(*) AS n FROM orders WHERE status='delivered'")["n"] or 1
    open_esc = led["open_escrows"] if led["open_escrows"] is not None else \
        w.store.one("SELECT COUNT(*) AS n FROM holdbacks WHERE status IN ('held','suspected')")["n"]
    u = v.usage
    tok = {s: u[s]["input_tokens"] + u[s]["output_tokens"] for s in u}
    rtok = {s: u[s]["replayed_input_tokens"] + u[s]["replayed_output_tokens"] for s in u}
    return {"llm": {"model": v.label(), **u},
            "ledger": {**led, "reserve_tied_xrp": open_esc * OWNER_RESERVE / 1e6,
                       "participant_wallet_base_reserve_xrp": BASE_RESERVE / 1e6},
            "participants": people, "participant_weeks": weeks,
            "per_participant_week": {
                "llm_calls": round(sum(u[s]["live_calls"] + u[s]["replayed_calls"] for s in u) / weeks, 3),
                "llm_tokens_live": round(sum(tok.values()) / weeks, 1),
                "llm_tokens_recorded": round(sum(rtok.values()) / weeks, 1),
                "ledger_txs": round(led["txs"] / weeks, 2),
                "fee_xrp": round(led["fee_drops"] / weeks / 1e6, 6)}}
