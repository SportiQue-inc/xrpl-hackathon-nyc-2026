"""One synthetic goal through the research-contract lane, end to end, on the mock ledger with no LLM and no AP4M rail.

Run from the repository root:  PYTHONPATH=. .venv/bin/python docs/review-20261027/demo/run_demo.py
Writes demo_run.json (every API response that matters, trimmed) and demo_log.md (the narrative) next to this file.

Goal (synthetic): "Probe Sleep Lab" wants sleep.daily and fatigue.survey for weeks 1-3 at 0.01 per item-week,
budget 0.08 (= 4 member-weeks of two items). Three synthetic members join with their own Ed25519 keys and their
own choices. Nothing here touches XRPL Testnet, AP4M, UniQdata or an LLM: those are the limits, listed at the end.
"""
import json, os, pathlib, time
# Whatever the shell has set, this run must not reach a deployed store, keystore, wallet file, UniQdata roster or a
# live LLM: those variables are dropped before `web` is imported, and both stores are forced in-memory.
for _name in ("AGENTRAIL_DB", "AGENTRAIL_CONTRACTS_DB", "AGENTRAIL_KEYSTORE", "AGENTRAIL_CONTRACTS_WALLETS",
              "RAILWAY_VOLUME_MOUNT_PATH", "UNIQDATA_ROSTER", "LLM_SAY"):
    os.environ.pop(_name, None)
os.environ["AGENTRAIL_DB"] = ":memory:"
os.environ["AGENTRAIL_CONTRACTS_DB"] = ":memory:"
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_RECORD"] = "0"
os.environ.setdefault("LLM_CACHE", "tests/no_llm_cache.json")
os.environ["LEDGER"] = "mock"
os.environ["AGENTRAIL_CONTRACTS_PAY"] = "ledger"
os.environ["AGENTRAIL_CONTRACTS_AUTORUN"] = "0"
os.environ["AGENTRAIL_ANCHOR_S"] = "0"
from fastapi.testclient import TestClient
from agentrail import web
from agentrail.security.devices import Device
from agentrail.security.http import reset_rate_limits

HERE = pathlib.Path(__file__).resolve().parent
reset_rate_limits(); web._state.pop("lane", None); web.reset()
c = TestClient(web.app)
lane = web.lane()
LOG, OUT = [], {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ledger": "mock", "llm": "none", "ap4m_rail": "not connected", "uniqdata": "not connected"}

def say(line): LOG.append(line)
def token(dev):
    n = c.post("/api/auth/challenge", json={"sub": dev.sub}).json()["nonce"]
    r = c.post("/api/auth/token", json={"sub": dev.sub, "nonce": n, "signature": dev.sign_challenge(n)}); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}
def trim(x):
    return {k: x.get(k) for k in ("person", "status", "reason", "order_id", "amount_drops", "slot", "granted") if k in x} | ({"payment": x["payment"]["status"], "escrow_finish_tx": (x.get("escrow_finish") or {}).get("tx")} if "payment" in x else {})

# 1. need: the researcher posts the terms (nothing about them is in the code)
TERMS = {"title": "Sleep and fatigue, 3 weeks (synthetic demo)", "institution": "Probe Sleep Lab", "irb_approval": "IRB-DEMO-2026-10",
         "purpose": "sleep_research", "items": ["sleep.daily", "fatigue.survey"], "weeks": [1, 3],
         "price_per_item_drops": 10_000, "budget_drops": 80_000, "capacity": 10,
         "summary": "Synthetic demo contract for the 2026-10-27 review. No real person, no real institution."}
R = Device("demo-researcher")
r = c.post("/api/contracts", json={"terms": TERMS, "researcher_key": R.public_hex}); assert r.status_code == 200, r.text
posted = r.json(); cid = posted["contract"]["id"]; invite = posted["invite_code"]; R.sub = posted["researcher_sub"]; rh = token(R)
iid = posted["contract"]["terms"]["institution_id"]
OUT["1_need_posted"] = {"contract": cid, "terms_hash": posted["contract"]["terms_hash"], "institution_id": iid,
                        "mandate": {"budget_drops": TERMS["budget_drops"], "per_order_limit_drops": TERMS["price_per_item_drops"] * len(TERMS["items"]), "purposes": [TERMS["purpose"]]},
                        "ethics_credential": posted["ethics_credential"], "public_listing_has_invite_code": invite in json.dumps(c.get("/api/contracts").json())}
say(f"1. NEED. The researcher posts the terms over HTTP: {TERMS['items']} weeks 1-3, 0.01 per item-week, budget 0.08 (per-order limit 0.02 = one member-week). "
    f"The engine opens institution {iid}, sets its BuyerMandate from the terms, and issues the ethics credential on the (mock) ledger. Contract {cid}. The invite code is returned once and never listed.")

# 2. candidates: members join with their own keys and their own choices; each one's agent answers for that member only
members = {}
for name, automation, items in (("M1", "auto_all", None), ("M2", "auto_all", ["sleep.daily"]), ("M3", "confirm_each", None)):
    d = Device("demo-" + name)
    body = {"invite_code": invite, "public_key": d.public_hex, "automation": automation, **({"items": items} if items else {})}
    s = c.post(f"/api/contracts/{cid}/join/start", json=body).json(); d.sub = s["pid"]
    r = c.post(f"/api/contracts/{cid}/join/complete", json={"pid": s["pid"], "signature": d.sign_consent(s["consent_hash"]), "generate_test_weeks": [1, 2, 3]}); assert r.status_code == 200, r.text
    members[name] = {"dev": d, "h": token(d), "consent_hash": s["consent_hash"], "items": s["consent"]["items"] if "items" in s["consent"] else items or TERMS["items"], "automation": automation}
    say(f"2. CANDIDATE {name} ({d.sub}): joins with its own Ed25519 key, {automation}, items {items or TERMS['items']}; signs consent {s['consent_hash'][:12]}…; stores generated test readings for weeks 1-3 (labelled generated_test).")
OUT["2_members"] = {n: {"pid": m["dev"].sub, "automation": m["automation"], "items": m["items"], "consent_hash": m["consent_hash"]} for n, m in members.items()}
pid = lambda n: members[n]["dev"].sub

# 3+4. authority on both sides, then the first round: the institution asks every member's agent for everything it posted
r1 = c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=rh).json()
by1 = {x["person"]: trim(x) for x in r1["results"]}
OUT["3_round1"] = {"summary": r1["summary"], "results": by1}
say("3. AUTHORITY, both sides, in the same call. Institution side: engine.place_order checks the BuyerMandate (purpose in mandate, price <= per-order limit, budget left) and the ethics credential on the ledger. "
    "Person side: PersonalConsentPolicy.evaluate checks consent status, period, purpose, minimum price, consented items and the member's automation choice.")
say(f"4. ROUND 1 (week 1): M1 -> {by1[pid('M1')]['status']} {by1[pid('M1')].get('granted')} {by1[pid('M1')].get('amount_drops')}; "
    f"M2 -> {by1[pid('M2')]['status']} granted {by1[pid('M2')].get('granted')} for {by1[pid('M2')].get('amount_drops')} (fatigue.survey was asked and offered, not consented: not sent, a scope question is opened for M2 instead); "
    f"M3 -> {by1[pid('M3')]['status']} (confirm_each: the agent STOPS and waits for M3).")
v2 = c.get(f"/api/p/{pid('M2')}/contracts", headers=members["M2"]["h"]).json()
OUT["4_M2_scope_question"] = v2["contracts"][0]["pending_approvals"]

# 5. the stop: M3 must approve with a fresh signature from M3's own key; wrong or borrowed signatures are refused
v3 = c.get(f"/api/p/{pid('M3')}/contracts", headers=members["M3"]["h"]).json()
ask = v3["contracts"][0]["pending_approvals"][0]
path = f"/api/p/{pid('M3')}/contracts/{cid}/requests/{ask['request_id']}/approve"
msg = lane.action_message(pid("M3"), cid, f"approve:{ask['request_id']}:{','.join(sorted(ask['items']))}")
bad = c.post(path, json={"items": ask["items"], "signature": members["M3"]["dev"].sign_consent("0" * 64)}, headers=members["M3"]["h"])
borrowed = c.post(path, json={"items": ask["items"], "signature": members["M1"]["dev"].sign(msg)}, headers=members["M3"]["h"])
good = c.post(path, json={"items": ask["items"], "signature": members["M3"]["dev"].sign(msg)}, headers=members["M3"]["h"])
OUT["5_M3_approval"] = {"pending": ask, "wrong_signature_http": bad.status_code, "borrowed_key_http": borrowed.status_code, "own_key_http": good.status_code,
                        "order_after_approval": trim(good.json()["order"]) if good.status_code == 200 else good.text}
say(f"5. STOP FOR THE PERSON. M3's pending request: week {ask['week']} {ask['items']}. A wrong signature -> HTTP {bad.status_code}; M1's key on M3's approval -> HTTP {borrowed.status_code}; "
    f"M3's own fresh signature -> HTTP {good.status_code}, order {OUT['5_M3_approval']['order_after_approval'].get('status')} for {OUT['5_M3_approval']['order_after_approval'].get('amount_drops')}.")

# 6. allowed execution continues: round 2; the budget (0.08) runs out inside it, so the institution's own limit refuses the rest
r2 = c.post(f"/api/contracts/{cid}/rounds", json={"week": 2}, headers=rh).json()
by2 = {x["person"]: trim(x) for x in r2["results"]}
OUT["6_round2"] = {"summary": r2["summary"], "results": by2}
v3b = c.get(f"/api/p/{pid('M3')}/contracts", headers=members["M3"]["h"]).json()
ask2 = v3b["contracts"][0]["pending_approvals"][0]
msg2 = lane.action_message(pid("M3"), cid, f"approve:{ask2['request_id']}:{','.join(sorted(ask2['items']))}")
good2 = c.post(f"/api/p/{pid('M3')}/contracts/{cid}/requests/{ask2['request_id']}/approve", json={"items": ask2["items"], "signature": members["M3"]["dev"].sign(msg2)}, headers=members["M3"]["h"])
OUT["6_M3_approval_after_budget_gone"] = good2.json() if good2.status_code == 200 else {"http": good2.status_code, "text": good2.text}
say(f"6. ALLOWED EXECUTION, then the institution's limit. Round 2: M1 -> {by2[pid('M1')]['status']} ({by2[pid('M1')].get('reason') or by2[pid('M1')].get('amount_drops')}); M2 -> {by2[pid('M2')]['status']} ({by2[pid('M2')].get('reason') or by2[pid('M2')].get('amount_drops')}); "
    f"M3 -> {by2[pid('M3')]['status']}. M3 then approves week 2 with a valid signature, but the budget is spent: order -> {OUT['6_M3_approval_after_budget_gone'].get('order', {}).get('status')} ({OUT['6_M3_approval_after_budget_gone'].get('order', {}).get('reason')}). A person's approval never widens the institution's budget.")

# 7. delivery confirmation: the researcher's console, each member's own view, and the institution opening what it paid for
con = c.get(f"/api/contracts/{cid}/console", headers=rh).json()
delivered = [o for o in con["orders"] if o["status"] == "delivered"]
opened = []
for o in delivered:
    payload = lane.engine.open_payload(iid, o["order_id"])     # raises BundleMismatch if the bundle does not hash to the order
    rows = payload["rows"]
    opened.append({"order_id": o["order_id"], "slot": o["slot"], "rows": len(rows), "items_in_row": sorted(k for k in rows[0] if k not in ("person", "day")) if rows else [], "hash_matches_order": True})
views = {n: {k: v for k, v in c.get(f"/api/p/{pid(n)}/contracts", headers=m["h"]).json().items() if k in ("settled_drops", "held_drops", "active_institutions")} for n, m in members.items()}
OUT["7_delivery"] = {"console": {"members": con["members"], "spent_drops": con["spent_drops"], "budget_drops": con["budget_drops"], "rounds": con["rounds"],
                                 "orders": [trim(o) for o in con["orders"]], "payments": con["payments"]},
                     "institution_opened_bundles": opened, "member_views": views}
say(f"7. DELIVERY CONFIRMED. Researcher console: {len(delivered)} delivered orders, spent {con['spent_drops']} of {con['budget_drops']}; every delivered order has an EscrowCreate and EscrowFinish record on the mock ledger. "
    f"The institution's vault opens each delivered bundle with the key read from the ledger and the hash matches the order: {[(o['slot'], o['rows'], o['items_in_row']) for o in opened]}. Member views: {views}.")

# 8. withdrawal: M2 leaves; the next round does not ask M2 and pays nothing to M2
sig = members["M2"]["dev"].sign(lane.action_message(pid("M2"), cid, "withdraw"))
w = c.post(f"/api/p/{pid('M2')}/contracts/{cid}/withdraw", json={"signature": sig}, headers=members["M2"]["h"]).json()
r3 = c.post(f"/api/contracts/{cid}/rounds", json={"week": 3}, headers=rh).json()
OUT["8_withdraw_round3"] = {"M2_status": w["contracts"][0]["status"], "round3_members": [x["person"] for x in r3["results"]], "M2_asked_in_round3": pid("M2") in {x["person"] for x in r3["results"]},
                            "round3": {x["person"]: trim(x) for x in r3["results"]}}
say(f"8. WITHDRAWAL. M2 withdraws with its own signature -> status {w['contracts'][0]['status']}; round 3 asks {len(r3['results'])} members, M2 not among them; M2 keeps what it was paid.")

OUT["limits"] = [
    "Ledger: mock. EscrowCreate/EscrowFinish here are in-memory records, not XRPL Testnet transactions (the lane runs the same code with LEDGER=testnet; not exercised in this run).",
    "Payment rail: ledger (mock escrow). The AP4M rail was not connected: no RLUSD moved, no VoucherRedeemed, no receipt URL.",
    "Data: generated test readings labelled generated_test; no UniQdata account was connected, so nothing was written to or read from UniQdata and no settlement record was reported to it.",
    "LLM: off. Every sentence and every decision came from the rule-based code paths; no proposal was made or checked.",
    "Candidate comparison: the research-contract lane has none. The institution asks every member at the posted price; the only choices are each member's own consent and the institution's budget. Price negotiation and seller ranking exist only in the market simulation (agentrail/market) and the vault market prototype.",
    "The researcher has no API or page to download a delivered bundle in this lane; step 7 opened it in-process with the engine's institution vault to show the data is readable by the payer.",
    "Approvals are Ed25519 signatures from a software key in this script, the same contract the browser join page uses with WebCrypto; no passkey/Touch ID was involved.",
]
OUT["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
(HERE / "demo_run.json").write_text(json.dumps(OUT, indent=1, default=str) + "\n")
md = ["# Research-contract lane: one synthetic goal end to end (2026-10-27)", "",
      "Produced by `run_demo.py` on the mock ledger, LLM off, AP4M rail and UniQdata not connected. Raw responses: `demo_run.json`.", ""]
md += [f"- {l}" for l in LOG] + ["", "## Limits of this run", ""] + [f"- {l}" for l in OUT["limits"]] + [""]
(HERE / "demo_log.md").write_text("\n".join(md))
print("\n".join(LOG)); print("\nlimits:", *OUT["limits"], sep="\n- ")
