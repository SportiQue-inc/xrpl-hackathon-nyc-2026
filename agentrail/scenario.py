"""Demo scenes. All parties and data are synthetic.

  Scene A  organization -> organization: a robotics buyer agent procures data
  Scene B  same engine, personal health data with consent, sensitivity and automation settings
  Scene C  failure handling: retries, lost responses, restart
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

from .agents import BuyerAgent, InstitutionAgent, PersonalAgent, SellerAgent
from .connectors import Person, Product, RoboticsConnector
from .db import Store
from .engine import Engine, OrderRequest
from .ledger import make_ledger
from .reasoning import OwnerLimits, Spec
from .policy import BuyerMandate, ComplianceRules, SellerPolicy

XRP = 1_000_000
CELL_PRICE = XRP // 5          # 0.2 XRP per participant-week item
ETHICS_CREDENTIAL = "ETHICS_REVIEW_SLEEP"

# What the buyer's owner types, and what the company already holds and has measured.
GOAL_TEXT = "Close the gaps our latest evaluation found before commercial deployment. Spend up to 40 XRP."
ROBOT_SENSORS = ["lidar", "imu"]
INVENTORY = {
    "robot_sensors": ROBOT_SENSORS,
    "coverage": {"daytime": {"episodes": 1200, "target": 400}, "loading_dock": {"episodes": 310, "target": 200},
                 "narrow_aisle": {"episodes": 380, "target": 400}, "night": {"episodes": 40, "target": 400},
                 "dynamic_obstacle": {"episodes": 25, "target": 400}, "outdoor": {"episodes": 150, "target": 150}},
    "evaluation_report": [
        "Night runs: collision rate 3.1x the daytime rate (12 incidents in 40 runs).",
        "People and forklifts crossing: 42 avoidance failures; model rarely saw moving obstacles.",
        "Narrow aisles: within tolerance after last month's data.",
        "Loading dock and outdoor yard: within tolerance."]}
# Second input: same goal, different evaluation -> different spec and different sellers.
INVENTORY_2 = {
    "robot_sensors": ROBOT_SENSORS,
    "coverage": {"daytime": {"episodes": 1200, "target": 400}, "loading_dock": {"episodes": 310, "target": 200},
                 "narrow_aisle": {"episodes": 380, "target": 400}, "night": {"episodes": 420, "target": 400},
                 "dynamic_obstacle": {"episodes": 390, "target": 400}, "outdoor": {"episodes": 12, "target": 300}},
    "evaluation_report": [
        "New outdoor yard route: wheel slip and localisation loss on ramps, 37 failures in 50 runs.",
        "Night and moving obstacles: within tolerance after the last purchase.",
        "Indoor aisles and loading dock: within tolerance."]}

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
    goal: Spec | None = None
    limits: OwnerLimits | None = None
    treasury: str | None = None
    treasury_signers: list = field(default_factory=list)


def build_world(ledger_kind: str = "mock", db_path: str = ":memory:") -> World:
    store = Store(db_path)
    ledger = make_ledger(ledger_kind)
    engine = Engine(store, ledger)
    w = World(store, engine, ledger)
    engine.relay = ledger.new_account("vault_relay")   # publishes keys for contributors without a funded key

    def party(pid, name, kind):
        engine.add_party(pid, name, kind, ledger.new_account(pid))

    # ----- Scene A cast -----
    party("org_robodev", "Robot developer (buyer)", "organization")
    # Each seller names fields its own way; the buyer agent has to work out which is which.
    specs = [
        ("org_alpha", "Alpha Sim", [Product(
            "A1", "org_alpha", "Warehouse runs, depth camera", "robotics", ["depth_cam", "imu_6axis", "camera_rgb"],
            {"night": 30, "narrow_aisle": 30, "dynamic_obstacle": 30}, 6 * XRP,
            {"commercial_training": True, "evaluation": True, "redistribution": False},
            kinds={"depth_cam": "depth", "imu_6axis": "imu"},
            licence_text="Licensed for commercial training and evaluation. No redistribution.")], []),
        ("org_beta", "Beta Logistics", [Product(
            "B1", "org_beta", "Night warehouse navigation", "robotics", ["point_cloud", "imu", "odom", "raw_video"],
            {"night": 40, "narrow_aisle": 30}, 20 * XRP,
            {"commercial_training": True, "evaluation": True, "redistribution": False},
            kinds={"point_cloud": "lidar", "odom": "wheel_odometry"},
            licence_text="Licensed for commercial model training. No resale or redistribution of the data. "
                         "Term: 24 months.")], ["raw_video"]),
        ("org_gamma", "Gamma Robotics", [
            Product("C1", "org_gamma", "Dynamic obstacle encounters", "robotics", ["lidar_xyz", "imu_6axis"],
                    {"dynamic_obstacle": 35, "night": 10}, 15 * XRP,
                    {"commercial_training": True, "evaluation": True, "redistribution": False},
                    kinds={"lidar_xyz": "lidar", "imu_6axis": "imu"},
                    licence_text="Any internal use, including training commercial models. Attribution required."),
            Product("C2", "org_gamma", "Obstacle benchmark set", "robotics", ["lidar_xyz", "imu_6axis"],
                    {"dynamic_obstacle": 40}, 8 * XRP,
                    {"commercial_training": False, "evaluation": True, "redistribution": False},
                    kinds={"lidar_xyz": "lidar", "imu_6axis": "imu"},
                    licence_text="For research evaluation and benchmarking only. Not for training commercial "
                                 "models.")], []),
        ("org_delta", "Delta Fleet", [Product(
            "D1", "org_delta", "Mixed fleet logs", "robotics", ["lidar", "imu"],
            {"dynamic_obstacle": 30, "narrow_aisle": 20}, 10 * XRP,
            {"commercial_training": True, "evaluation": True, "redistribution": False},
            licence_text="Commercial use permitted.", missing_rate=0.2),
            Product("D2", "org_delta", "Outdoor yard and ramp runs", "robotics", ["lidar", "imu"],
                    {"outdoor": 60}, 12 * XRP,
                    {"commercial_training": True, "evaluation": True, "redistribution": False},
                    licence_text="Commercial use permitted. No redistribution.")], []),
    ]
    for pid, name, products, excluded in specs:
        party(pid, name, "organization")
        w.sellers.append(SellerAgent(pid, RoboticsConnector(products),
                                     SellerPolicy(pid, ["*"], ["commercial_training", "evaluation"],
                                                  excluded_fields=excluded), engine))
    engine.set_mandate(BuyerMandate("org_robodev", 50 * XRP, 25 * XRP, ["commercial_training"]))
    w.robot_buyer = BuyerAgent("org_robodev", engine)
    w.limits = OwnerLimits(purposes=["commercial_training"], budget_cap_drops=50 * XRP,
                           allow_sensitive_fields=False, max_missing_rate_ceiling=0.05,
                           auto_approve_limit_drops=40 * XRP)

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
    if w.goal is None:
        w.goal = w.robot_buyer.plan(GOAL_TEXT, INVENTORY, w.limits)
    return w.robot_buyer.procure(w.goal, w.sellers)


def top_up(w: World, buyer_id: str, amount_xrp: float, signers: list[str], treasury: str | None = None) -> str | None:
    """Raise an agent's budget. Only a multi-signed treasury payment can do it."""
    try:
        h = w.ledger.multisig_payment(treasury or w.treasury, w.engine.party(buyer_id)["address"],
                                      int(amount_xrp * XRP), signers)
    except Exception as e:
        # submit_and_wait wraps the engine result in a timeout message; show just the code.
        m = re.search(r"\b(te[cfmlr][A-Z_]+)\b", str(e))
        w.store.log(buyer_id, "refused", f"top-up of {amount_xrp:g} XRP rejected by the ledger: "
                    f"{m.group(1) if m else e} (agent key is not on the treasury SignerList)")
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
    if first["status"] == "purchased" or "gap_xrp" not in first:
        return first
    gap = first["gap_xrp"]
    w.store.log("org_robodev", "ask_human", f"agent requests +{gap:g} XRP; tries to sign the top-up alone")
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
    # The gate stores only sealed bundles: the operator's own key cannot open them.
    from nacl.exceptions import CryptoError
    from nacl.public import PrivateKey, SealedBox
    sealed = w.store.one("SELECT sealed FROM bundles WHERE order_id=?", oid)["sealed"]
    try:
        SealedBox(PrivateKey.generate()).decrypt(sealed)
        w.store.log("gate", "error", "operator could open a bundle (should never happen)")
    except CryptoError:
        final = w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
        opened = f"{len(e2.open_bundle(req.buyer_id, oid))} rows" if final == "delivered" else f"order is {final}"
        w.store.log("gate", "sealed", f"operator tries to open order {oid}'s bundle with its own key: fails; "
                    f"only {req.buyer_id}'s key opens it ({opened})")
    final = w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
    deliveries = w.store.one("SELECT COUNT(*) n FROM deliveries WHERE order_id=?", oid)["n"]
    return {"order_id": oid, "after_first_try": status1, "final": final, "delivery_attempts": deliveries,
            "payments_for_order": 1}


FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "testnet-addresses.public.json")


def scene_d(w: World, n: int = 50, workers: int = 10) -> dict:
    """Cohort round: one institution agent buys one week from n people at once.
    Payees are public Testnet addresses (receive-only; no keys needed)."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    w.store.scene = "D"
    e = w.engine
    accounts = [a for a in json.load(open(FIXTURE))["accounts"] if a["role"] == "participant"][:n]
    compliance = ComplianceRules(credential_check=lambda buyer: False)
    e.add_party("org_cohort", "Cohort study (synthetic)", "organization", w.ledger.new_account("org_cohort"))
    e.set_mandate(BuyerMandate("org_cohort", 60 * XRP, 2 * XRP, ["sleep_research"]))
    people = []
    for a in accounts:
        pid = a["account_id"]
        e.add_party(pid, f"Participant {pid}", "person", a["classic_address"])
        pa = PersonalAgent(Person(pid, pid), e, compliance)
        pa.set_consent("org_cohort", "sleep_research", ["sleep.daily"], automation="auto_all")
        people.append(pa)
    lab = InstitutionAgent("org_cohort", e, "sleep_research")
    w.store.log("org_cohort", "round", f"week 1: buying sleep.daily from {len(people)} people, 1 XRP each, "
                f"{workers} payments in flight")
    oids = []
    for pa in people:
        d = pa.handle_request("org_cohort", "sleep_research", ["sleep.daily"], 1, 1 * XRP)
        if d.ok:
            oids.append(e.place_order(OrderRequest("org_cohort", pa.id, pa.id, "personal.weekly",
                                                   f"{pa.id}|week1", "sleep_research", d.granted, 1 * XRP,
                                                   pa.vault.extract(d.granted, 1), d)))
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        statuses = list(ex.map(e.process, oids))
    dt = time.time() - t0
    done = statuses.count("delivered")
    w.store.log("org_cohort", "report", f"{done}/{len(oids)} people paid on a validated ledger and data "
                f"delivered in {dt:.1f}s")
    return {"orders": len(oids), "delivered": done, "seconds": round(dt, 1)}


COHORT_PROFILES = (["auto_all"] * 7) + ["auto_standard", "auto_standard", "confirm_each"]


def build_cohort(w: World, n: int = 50):
    """50 participants with their own agents. Payees on Testnet are the public fixture addresses."""
    from .cohort import synthetic_coverage
    e = w.engine
    accounts = [a for a in json.load(open(FIXTURE))["accounts"] if a["role"] == "participant"][:n]
    compliance = ComplianceRules(credential_check=lambda buyer: w.ledger.has_credential(
        e.party(buyer)["address"], e.party("org_ethics")["address"], ETHICS_CREDENTIAL))
    w.cohort_people = {}
    for i, a in enumerate(accounts):
        pid = a["account_id"]
        from .cohort import HERO
        if w.ledger.name != "testnet":
            addr = w.ledger.new_account(pid)
        elif pid == HERO:
            addr = w.ledger.new_account(f"participant_{pid}")   # the followed participant's agent holds a key
        else:
            addr = a["classic_address"]                        # receive-only public fixture address
        e.add_party(pid, f"Participant {pid}", "person", addr)
        pa = PersonalAgent(Person(pid, pid), e, compliance)
        auto = "auto_standard" if pid == HERO else COHORT_PROFILES[i % len(COHORT_PROFILES)]
        items = STANDARD_ITEMS + (["fatigue.survey"] if auto != "auto_standard" else [])
        pa.set_consent("org_sleeplab", "sleep_research", items, automation=auto, quiet=True)
        w.cohort_people[pid] = pa
    w.coverage = synthetic_coverage(list(w.cohort_people))
    e.set_mandate(BuyerMandate("org_sleeplab", 80 * XRP, 3 * XRP, ["sleep_research"]))


def scene_h(w: World, propose=None, workers: int = 8) -> dict:
    """Stalled study: infer the missing cells, ask each participant's agent, pay, fill the table."""
    from concurrent.futures import ThreadPoolExecutor
    from .cohort import apply_deliveries, fill, heatmap, infer_needs
    w.store.scene = "H"
    if not getattr(w, "cohort_people", None):
        build_cohort(w)
    before = heatmap(w, w.coverage, "org_sleeplab")
    w.store.log("org_sleeplab", "goal", f"study stalled: {before['complete_pairs']}/{before['total']} complete "
                f"sleep+fatigue participant-weeks, power {before['power']} (plan 0.80)")
    ethics = w.ledger.has_credential(w.engine.party("org_sleeplab")["address"],
                                     w.engine.party("org_ethics")["address"], ETHICS_CREDENTIAL)
    needs = infer_needs(w.store, "org_sleeplab", w.coverage, ["sleep_research"], 40 * XRP, ethics, propose)
    w.needs = needs
    gap_txt = "; ".join(f"{i} weeks {ws}" for i, ws in needs.gaps.items()) or "none"
    w.store.log("org_sleeplab", "spec", f"needs ({'LLM' if needs.source == 'llm' else 'rule baseline'}): {gap_txt}; "
                f"{len(needs.cells)} participants, "
                f"{sum(len(v) for wk in needs.cells.values() for v in wk.values())} cells",
                {"evidence": needs.evidence, "notes": needs.notes, "hash": needs.proposal_hash})
    if needs.notes:
        w.store.log("org_sleeplab", "verify", "code narrowed the proposal: " + "; ".join(needs.notes))
    res = fill(w, "org_sleeplab", needs, w.coverage, w.cohort_people, CELL_PRICE)
    oids = [r["order_id"] for r in res if r.get("order_id")]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(w.engine.process, oids))
    apply_deliveries(w, w.coverage, res)
    after = heatmap(w, w.coverage, "org_sleeplab")
    waiting = [r["person"] for r in res if r.get("pending") or r.get("status") == "needs_approval"]
    w.store.log("org_sleeplab", "report", f"filled {after['complete_pairs'] - before['complete_pairs']} "
                f"participant-weeks from {len(oids)} people; power {before['power']} -> {after['power']}; "
                f"{len(waiting)} people asked to decide")
    return {"before": {k: before[k] for k in ("complete_pairs", "power")},
            "after": {k: after[k] for k in ("complete_pairs", "power")},
            "orders": len(oids), "waiting": waiting, "gaps": needs.gaps, "source": needs.source}


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
    # Credential, SignerListSet, master-key disable and co-signed top-up transactions.
    out["ledger_setup"] = []
    for r in s.q("SELECT actor, kind, data FROM events WHERE kind IN ('credential','multisig','top_up') ORDER BY id"):
        d = json.loads(r["data"])
        txs = d.get("tx") or ([d["tx_hash"]] if d.get("tx_hash") else [])
        out["ledger_setup"] += [{"actor": r["actor"], "kind": r["kind"], "tx_hash": h,
                                 "url": w.ledger.explorer_url(h)} for h in txs if h]
    return out


def main():
    kind = os.environ.get("LEDGER", "mock")
    w = build_world(kind, os.environ.get("AGENTRAIL_DB", ":memory:"))
    from .llm import voice
    print(f"agent voice: {voice().label()}", file=sys.stderr)
    results = {"A": scene_a_guarded(w), "B": scene_b(w), "C": scene_c(w)}
    if os.environ.get("COHORT", "1") != "0":
        results["D"] = scene_d(w, int(os.environ.get("COHORT_SIZE", "50")))
    for e in w.store.q("SELECT scene, actor, message FROM events ORDER BY id"):
        print(f"[{e['scene'] or '-'}] {e['actor']:<12} {e['message']}")
    print(json.dumps({"scene_c": results["C"], "scene_d": results.get("D"), "summary": summary(w)},
                     indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
