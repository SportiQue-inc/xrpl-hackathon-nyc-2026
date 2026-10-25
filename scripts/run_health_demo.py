"""Run the whole health study on one ledger and print every transaction link.

    LEDGER=testnet python scripts/run_health_demo.py      # or LEDGER=mock

Research side: goal -> gap reading -> one-signer approval refused -> co-signed approval ->
participation requests. Participant P-017: preview -> approve -> contribution + licence.
Then the boundary checks (consent, re-identification, the three withdrawals) and, on Testnet,
a wait for the held escrow's deadline so the refund lands. Output: JSON summary on stdout.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentrail import boundaries, scenario, study  # noqa: E402
from agentrail.llm import voice  # noqa: E402

kind = os.environ.get("LEDGER", "mock")
w = scenario.build_world(kind, os.environ.get("AGENTRAIL_DB", ":memory:"))
print(f"ledger {kind}; agent voice {voice().label()}", file=sys.stderr)
study.ensure(w)
v = study.set_goal(w, "Bring the primary analysis back to 80% power before the interim report.")
print(f"gaps: {v['proposal']['gaps']} (source {v['proposal']['source']})", file=sys.stderr)
refused = study.approve(w, ["owner"])
print(f"one signer: {refused.get('engine_result')}", file=sys.stderr)
ok = study.approve(w, ["owner", "compliance"])
v = study.send(w)
print(f"power {v['heatmap']['power_before']} -> {v['heatmap']['power']}", file=sys.stderr)
b = boundaries.run(w)
if kind == "testnet":
    deadline = time.time() + 240
    while time.time() < deadline:
        r = study.sweep(w)
        if r["refunded"]:
            for oid in r["refunded"]:
                h = w.store.one("SELECT cancel_tx FROM payments WHERE order_id=?", oid)["cancel_tx"]
                boundaries._ev(w, "withdrawal", f"3. Escrow for order {oid} refunded after its deadline",
                               **study._tx(w, h))
            break
        time.sleep(10)
    b = boundaries.view(w)
out = {"ledger": kind, "voice": voice().label(), "study": study.study_view(w), "approval": ok.get("approval"),
       "refused_single_signer": refused, "boundaries": b, "hero": study.participant_view(w, "P-017"),
       "events": [f"[{e['scene'] or '-'}] {e['actor']}: {e['message']}" for e in study.events(w)["events"]]}
print(json.dumps(out, indent=1, default=str))
