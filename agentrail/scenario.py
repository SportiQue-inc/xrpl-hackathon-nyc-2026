"""Demo scenes. All parties and data are synthetic.

  Scene A  organization -> organization: a robotics buyer agent procures data
  Scene B  same engine, personal health data with consent, sensitivity and automation settings
  Scene C  failure handling: retries, lost responses, restart
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field

from .agents import BuyerAgent, Goal, InstitutionAgent, PersonalAgent, SellerAgent
from .connectors import Person, Product, RoboticsConnector
from .db import Store
from .engine import Engine, OrderRequest
from .ledger import make_ledger
from .policy import BuyerMandate, ComplianceRules, SellerPolicy

XRP = 1_000_000
ETHICS_CREDENTIAL = "ETHICS_REVIEW_SLEEP"

STANDARD_ITEMS = ["sleep.daily", "activity.daily", "heart_rate.daily"]
EXTRA_ITEMS = ["fatigue.survey", "blood_pressure.daily"]


@dataclass
class World:
    store: Store
    engine: Engine
    ledger: object
    robot_buyer: BuyerAgent | None = None
    sellers: list = field(default_factory=list)
    lab: InstitutionAgent | None = None
    people: dict = field(default_factory=dict)
    goal: Goal | None = None
    treasury: str | None = None
    treasury_signers: list = field(default_factory=list)


def build_world(ledger_kind: str = "mock", db_path: str = ":memory:") -> World:
    store = Store(db_path)
    ledger = make_ledger(ledger_kind)
    engine = Engine(store, ledger)
    w = World(store, engine, ledger)

    def party(pid, name, kind):
        engine.add_party(pid, name, kind, ledger.new_account(pid))

    # ----- Scene A cast -----
    party("org_robodev", "Robot developer (buyer)", "organization")
    specs = [
        ("org_alpha", "Alpha Sim", [Product("A1", "org_alpha", "Warehouse runs, camera only", "robotics",
                                            ["imu", "wheel_odometry", "camera_rgb"],
                                            {"night": 30, "narrow_aisle": 30, "dynamic_obstacle": 30},
                                            6 * XRP, {"commercial_training": True})], []),
        ("org_beta", "Beta Logistics", [Product("B1", "org_beta", "Night warehouse navigation", "robotics",
                                                ["lidar", "imu", "wheel_odometry", "raw_video"],
                                                {"night": 40, "narrow_aisle": 30},
                                                20 * XRP, {"commercial_training": True, "resale": False})],
         ["raw_video"]),
        ("org_gamma", "Gamma Robotics", [
            Product("C1", "org_gamma", "Dynamic obstacle encounters", "robotics", ["lidar", "imu"],
                    {"dynamic_obstacle": 25, "night": 10}, 15 * XRP, {"commercial_training": True}),
            Product("C2", "org_gamma", "Obstacle set (evaluation only)", "robotics", ["lidar", "imu"],
                    {"dynamic_obstacle": 40}, 8 * XRP, {"commercial_training": False})], []),
        ("org_delta", "Delta Fleet", [Product("D1", "org_delta", "Mixed fleet logs", "robotics", ["lidar", "imu"],
                                              {"dynamic_obstacle": 30, "narrow_aisle": 20}, 10 * XRP,
                                              {"commercial_training": True}, missing_rate=0.2)], []),
    ]
    for pid, name, products, excluded in specs:
        party(pid, name, "organization")
        w.sellers.append(SellerAgent(pid, RoboticsConnector(products),
                                     SellerPolicy(pid, ["*"], ["commercial_training", "evaluation"],
                                                  excluded_fields=excluded), engine))
    engine.set_mandate(BuyerMandate("org_robodev", 50 * XRP, 25 * XRP, ["commercial_training"]))
    w.robot_buyer = BuyerAgent("org_robodev", engine)
    w.goal = Goal(
        text="indoor warehouse navigation data at night with LiDAR + IMU, covering dynamic obstacles "
             "and narrow aisles, commercial training allowed",
        purpose="commercial_training", required_fields=["lidar", "imu"], optional_fields=["raw_video"],
        required_scenarios=["night", "narrow_aisle", "dynamic_obstacle"])

    # Buyer treasury controlled by multi-signing (owner + compliance officer, master key off).
    # The agent spends only from its own account, capped by the mandate.
    w.treasury = ledger.new_account("org_robodev_treasury")
    w.treasury_signers = [ledger.new_keypair("robodev_owner"), ledger.new_keypair("robodev_compliance")]
    hashes = ledger.setup_multisig(w.treasury, w.treasury_signers, quorum=2)
    store.log("org_robodev", "multisig", "treasury: SignerList (owner + compliance, quorum 2), master key "
              "disabled; agent spends only from its capped account", {"tx": hashes})

    # ----- Scene B cast -----
    party("org_sleeplab", "Northside Sleep Lab (synthetic)", "organization")
    party("org_adtech", "Ad network (synthetic)", "organization")
    party("org_ethics", "Ethics review board (synthetic)", "organization")
    addr = lambda pid: engine.party(pid)["address"]
    hashes = ledger.issue_credential(addr("org_ethics"), addr("org_sleeplab"), ETHICS_CREDENTIAL)
    store.log("org_ethics", "credential", f"issued XRPL Credential {ETHICS_CREDENTIAL} to org_sleeplab "
              "(accepted on ledger)", {"tx": hashes, "url": ledger.explorer_url(hashes[-1])})
    compliance = ComplianceRules(credential_check=lambda buyer: ledger.has_credential(
        addr(buyer), addr("org_ethics"), ETHICS_CREDENTIAL))
    for pid, label in [("P017", "P017"), ("P023", "P023"), ("P031", "P031")]:
        party(pid, f"Participant {label}", "person")
        w.people[pid] = PersonalAgent(Person(pid, label), engine, compliance)
    engine.set_mandate(BuyerMandate("org_sleeplab", 40 * XRP, 6 * XRP, ["sleep_research"]))
    engine.set_mandate(BuyerMandate("org_adtech", 40 * XRP, 6 * XRP, ["marketing_profiling"]))
    w.lab = InstitutionAgent("org_sleeplab", engine, "sleep_research")
    return w


def scene_a(w: World, budget_xrp: float | None = None) -> dict:
    w.store.scene = "A"
    if budget_xrp is not None:
        w.engine.set_mandate(BuyerMandate("org_robodev", int(budget_xrp * XRP), 25 * XRP, ["commercial_training"]))
    return w.robot_buyer.procure(w.goal, w.sellers)


def top_up(w: World, buyer_id: str, amount_xrp: float, signers: list[str]) -> str | None:
    """Raise an agent's budget. Only a multi-signed treasury payment can do it."""
    try:
        h = w.ledger.multisig_payment(w.treasury, w.engine.party(buyer_id)["address"],
                                      int(amount_xrp * XRP), signers)
    except Exception as e:
        w.store.log(buyer_id, "refused", f"top-up of {amount_xrp:g} XRP rejected by the ledger: {e}")
        return None
    m = w.store.one("SELECT * FROM mandates WHERE buyer_id=?", buyer_id)
    w.engine.set_mandate(BuyerMandate(buyer_id, m["total_drops"] + int(amount_xrp * XRP),
                                      m["per_order_limit_drops"], json.loads(m["purposes"])))
    w.store.log(buyer_id, "top_up", f"owner + compliance co-signed a {amount_xrp:g} XRP treasury top-up; "
                f"mandate now {(m['total_drops'] / XRP) + amount_xrp:g} XRP",
                {"tx_hash": h, "url": w.ledger.explorer_url(h)})
    return h


def scene_a_guarded(w: World) -> dict:
    """Budget too small -> agent buys nothing and asks; agent alone cannot raise it;
    owner + compliance co-sign a top-up; agent completes the purchase."""
    first = scene_a(w, budget_xrp=30)
    if first["status"] == "purchased":
        return first
    gap = 5
    w.store.log("org_robodev", "ask_human", f"agent requests +{gap} XRP; tries to sign the top-up alone")
    top_up(w, "org_robodev", gap, [w.engine.party("org_robodev")["address"]])   # agent key: not on the list
    top_up(w, "org_robodev", gap, w.treasury_signers)                             # human approval
    return w.robot_buyer.procure(w.goal, w.sellers)


def scene_b(w: World) -> dict:
    w.store.scene = "B"
    p = w.people
    p["P017"].set_consent("org_sleeplab", "sleep_research", STANDARD_ITEMS, automation="auto_standard")
    p["P023"].set_consent("org_sleeplab", "sleep_research", STANDARD_ITEMS, automation="auto_all")
    p["P031"].set_consent("org_sleeplab", "sleep_research", STANDARD_ITEMS, automation="confirm_each")
    people = list(p.values())
    out = {}
    # Week 1: consented items; P031 confirms its round by hand.
    out["week1"] = w.lab.run_round(people, 1, STANDARD_ITEMS, 1 * XRP)
    r = p["P031"].open_requests()[0]
    p["P031"].approve(r["id"], json.loads(r["items"]))
    out["week1_P031"] = w.lab.run_round([p["P031"]], 1, STANDARD_ITEMS, 1 * XRP)
    # Week 2: lab also wants fatigue + blood pressure and offers more. Consented items still run.
    out["week2"] = w.lab.run_round(people, 2, STANDARD_ITEMS, 1 * XRP, EXTRA_ITEMS, 2 * XRP)
    # P017 approves only the fatigue survey. Blood pressure stays blocked.
    req = [r for r in p["P017"].open_requests() if r["kind"] == "scope"][0]
    p["P017"].approve(req["id"], ["fatigue.survey"])
    # Week 3: runs without anyone opening the app, within the new scope.
    out["week3"] = w.lab.run_round([p["P017"], p["P023"]], 3, STANDARD_ITEMS, 1 * XRP, EXTRA_ITEMS, 2 * XRP)
    # P023 pauses. Week 4 skips P023; P017 continues.
    p["P023"].pause("org_sleeplab")
    out["week4"] = w.lab.run_round([p["P017"], p["P023"]], 4, STANDARD_ITEMS + ["fatigue.survey"], 1 * XRP)
    # Another institution, prohibited purpose -> refused by the compliance layer.
    w.store.log("org_adtech", "round", "ad network asks P017 for sleep.daily (marketing_profiling)")
    out["adtech"] = InstitutionAgent("org_adtech", w.engine, "marketing_profiling").run_round(
        [p["P017"]], 4, ["sleep.daily"], 3 * XRP)
    return out


def scene_c(w: World) -> dict:
    """Failure handling on a fresh order (week 5, P017)."""
    w.store.scene = "C"
    e, pa = w.engine, w.people["P017"]
    items = STANDARD_ITEMS + ["fatigue.survey"]
    d = pa.handle_request("org_sleeplab", "sleep_research", items, 5, 1 * XRP)
    req = OrderRequest("org_sleeplab", "P017", "P017", "personal.weekly", "P017|week5", "sleep_research",
                       d.granted, 4 * XRP, pa.vault.extract(d.granted, 5), d)
    oid = e.place_order(req)
    again = e.place_order(req)                                   # retry: same order
    w.store.log("org_sleeplab", "retry", f"same request sent twice -> order {again} (no new order)")
    if hasattr(w.ledger, "lose_next_response"):
        w.ledger.lose_next_response = True                       # payment response lost
    e.inbox.lose_next_ack = True                                 # delivery ack lost
    status1 = e.process(oid)
    w.store.log("engine", "restart", "server restart: new engine instance, recovering from outbox")
    e2 = Engine(w.store, w.ledger, e.inbox)
    e2.policies, e2.box_keys = e.policies, e.box_keys
    e2.recover()
    w.engine = e2
    final = w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
    deliveries = w.store.one("SELECT COUNT(*) n FROM deliveries WHERE order_id=?", oid)["n"]
    return {"order_id": oid, "after_first_try": status1, "final": final, "delivery_attempts": deliveries,
            "payments_for_order": 1}


def summary(w: World) -> dict:
    s = w.store
    out = {}
    for buyer in ("org_robodev", "org_sleeplab"):
        m = s.one("SELECT * FROM mandates WHERE buyer_id=?", buyer)
        out[buyer] = {"budget_xrp": m["total_drops"] / XRP, "spent_xrp": m["spent_drops"] / XRP,
                      "reserved_xrp": m["reserved_drops"] / XRP,
                      "available_xrp": w.engine.available_drops(buyer) / XRP}
    out["payments"] = [dict(r) | {"url": w.ledger.explorer_url(r["tx_hash"]) if r["tx_hash"] else None}
                       for r in s.q("SELECT p.order_id, o.payee_id, p.amount_drops, p.tx_hash, p.status, "
                                    "p.ledger_index FROM payments p JOIN orders o ON o.id=p.order_id")]
    return out


def main():
    kind = os.environ.get("LEDGER", "mock")
    w = build_world(kind, os.environ.get("AGENTRAIL_DB", ":memory:"))
    results = {"A": scene_a_guarded(w), "B": scene_b(w), "C": scene_c(w)}
    for e in w.store.q("SELECT scene, actor, message FROM events ORDER BY id"):
        print(f"[{e['scene'] or '-'}] {e['actor']:<12} {e['message']}")
    print(json.dumps({"scene_c": results["C"], "summary": summary(w)}, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
