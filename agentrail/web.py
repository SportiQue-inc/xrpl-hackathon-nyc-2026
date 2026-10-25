"""API and dashboard. Every route goes through security.rbac.check (default deny); see
docs/SECURITY.md for roles, login and the demo harness."""
from __future__ import annotations

from . import units

import hmac
import json
import os
import re
import threading
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import payout, scenario, study
from . import uniqdata_port as port
from .llm import voice
from .security import audit, consent as signed_consent, cosign, passkey, rbac
from .security.auth import AuthError
from .security.http import AccessAudit, RateLimit, SecurityHeaders, cors_origins
from .security.masking import install_logging_filter
from .security.secrets import is_dev

_lock = threading.Lock()
_state: dict = {}


def _authority():
    return world().security.authority


def authorize(request: Request):
    rbac.check(request, _authority())


app = FastAPI(title="AgentRail", dependencies=[Depends(authorize)],
              docs_url="/docs" if is_dev() else None, redoc_url=None,
              openapi_url="/openapi.json" if is_dev() else None)
app.add_middleware(AccessAudit, get_store=lambda: _state["w"].store if "w" in _state else None)
app.add_middleware(RateLimit)
app.add_middleware(SecurityHeaders)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
install_logging_filter()
# The clinic's export service (x402, HTTP 402) is its own app: not behind the API's sign-in.
from . import clinic as _clinic  # noqa: E402
app.mount("/clinic", _clinic.app)


@app.on_event("startup")
def _start_anchoring():
    """Anchor the event log's head on the ledger every AGENTRAIL_ANCHOR_S seconds (0 = off)."""
    every = float(os.environ.get("AGENTRAIL_ANCHOR_S", "300"))
    if every > 0:
        audit.Anchorer(world, every, _lock).start()

ID = r"^[A-Za-z0-9_.:@-]{1,80}$"
ITEM = r"^[a-z0-9_.]{1,40}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChallengeBody(Strict):
    sub: str = Field(pattern=ID)


class TokenBody(Strict):
    sub: str = Field(pattern=ID)
    nonce: str = Field(min_length=16, max_length=64)
    signature: str = Field(pattern=r"^[0-9a-f]{128}$")


class PasskeyRegistration(Strict):
    credentialId: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    rawId: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    attestationObject: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    clientDataJson: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    transports: list[str] | str | None = None


class PasskeyAssertion(Strict):
    challengeId: str | None = Field(None, max_length=128)
    credentialId: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    rawId: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    authenticatorData: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    clientDataJson: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    signature: str = Field(max_length=8192, pattern=r"^[A-Za-z0-9_-]*$")
    userHandle: str | None = Field(None, max_length=1024, pattern=r"^[A-Za-z0-9_-]*$")


class ItemsBody(Strict):
    items: list[str] = Field(default_factory=list, max_length=20)

    def clean(self):
        bad = [i for i in self.items if not re.match(ITEM, i)]
        if bad:
            raise HTTPException(422, "unknown item names")
        return list(self.items)


class GoalBody(Strict):
    goal: str = Field(default="", max_length=500)


class SignersBody(Strict):
    signers: list[Literal["owner", "compliance"]] = Field(default_factory=list, max_length=2)


class SignatureBody(Strict):
    signer: str = Field(pattern=r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$|^r[0-9a-f]{24}$")
    public_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    signature: str | None = Field(default=None, pattern=r"^[0-9a-f]{128}$")
    signed_tx: dict | None = None


class DecideBody(Strict):
    reviewer_id: str = Field(pattern=ID)
    confirm: bool = False


class RespondBody(Strict):
    text: str = Field(default="", max_length=2000)


class ConsentBody(Strict):
    buyer: str = Field(default=study.LAB, pattern=ID)
    purpose: str = Field(default="sleep_research", pattern=r"^[a-z_]{1,40}$")
    items: list[str] = Field(max_length=20)
    weeks: tuple[int, int] = (1, 8)
    automation: Literal["confirm_each", "auto_standard", "auto_all"] = "confirm_each"
    signature: str | None = Field(default=None, pattern=r"^[0-9a-f]{128}$")


def _claims(request: Request) -> dict:
    return getattr(request.state, "claims", None) or {}


def world() -> scenario.World:
    if "w" not in _state:
        reset()
    return _state["w"]


@app.post("/api/reset")
def reset(ledger: Literal["mock", "testnet"] | None = None):
    default = os.environ.get("LEDGER", "mock")
    if ledger and ledger != default and os.environ.get("AGENTRAIL_ALLOW_LEDGER_SWITCH") != "1":
        raise HTTPException(403, "switching ledgers over HTTP is off (AGENTRAIL_ALLOW_LEDGER_SWITCH=1)")
    with _lock:
        kind = ledger or default
        _state["w"] = scenario.build_world(kind, os.environ.get("AGENTRAIL_DB", ":memory:"))
        _state["results"] = {}
        if "lane" in _state:      # research contracts outlive the demo world; their keys move to the new authority
            _state["lane"].enrol_all(_state["w"].security.authority)
    if "lane" not in _state and (os.environ.get("AGENTRAIL_CONTRACTS_DB") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")):
        lane()                    # stored contracts: their members can sign in straight after a restart
    return {"ok": True, "ledger": kind}


@app.post("/api/run/{scene}")
def run(scene: Literal["a", "a-guarded", "b", "c", "d", "h", "boundaries"],
        budget: float | None = Query(default=None, ge=0, le=1000)):
    w = world()
    with _lock:
        if scene == "a":
            r = scenario.scene_a(w, budget)
        elif scene == "a-guarded":
            r = scenario.scene_a_guarded(w)
            scene = "a"
        elif scene == "b":
            r = scenario.scene_b(w)
        elif scene == "c":
            r = scenario.scene_c(w)
        elif scene == "d":
            r = scenario.scene_d(w)
        elif scene == "h":
            r = scenario.scene_h(w)
        elif scene == "boundaries":
            from . import boundaries
            r = boundaries.run(w)
        else:
            return {"error": "unknown scene"}
        _state["results"][scene] = r
    return r


@app.get("/api/state")
def state():
    w = world()
    s = w.store
    rows = lambda sql, *a: [dict(r) for r in s.q(sql, *a)]
    orders = rows("""SELECT o.id, o.buyer_id, o.seller_id, o.payee_id, o.product_id, o.scope, o.purpose,
                     o.price_drops, o.status, o.note, o.bundle_hash, o.policy_snapshot,
                     p.tx_hash, p.status AS pay_status, p.ledger_index
                     FROM orders o LEFT JOIN payments p ON p.order_id=o.id ORDER BY o.id""")
    for o in orders:
        o["url"] = w.ledger.explorer_url(o["tx_hash"]) if o["tx_hash"] else None
        o["scope"] = json.loads(o["scope"])
        o["policy_snapshot"] = json.loads(o["policy_snapshot"])
    accounts = {}
    named = {pid: w.engine.party(pid)["address"] for pid in ("org_robodev", "org_sleeplab")}
    named["org_robodev treasury"] = w.treasury
    for pid, address in named.items():
        p = {"address": address}
        try:
            accounts[pid] = {"address": p["address"], **w.ledger.account_settings(p["address"])}
        except Exception as e:  # network hiccup should not break the page
            accounts[pid] = {"address": p["address"], "error": str(e)}
    return {
        "ledger": w.ledger.name,
        "unit": units.UNIT, "unit_label": units.LABEL,
        "voice": voice().label(),
        "mandates": rows("SELECT * FROM mandates"),
        "orders": orders,
        "events": rows("SELECT id, scene, actor, kind, message, data FROM events ORDER BY id"),
        "consents": rows("SELECT person_id, buyer_id, purpose, items, automation, status, version, doc_hash "
                         "FROM consents ORDER BY person_id"),
        "approvals": rows("SELECT * FROM approval_requests ORDER BY id"),
        "exceptions": rows("SELECT * FROM exceptions ORDER BY id"),
        "accounts": accounts,
        "results": _state.get("results", {}),
    }


# ---------- participant app and researcher console (docs/API.md) ----------

def _call(fn, *a, **k):
    w = world()
    with _lock:
        try:
            return fn(w, *a, **k)
        except KeyError as e:
            raise HTTPException(404, f"not found: {e}")
        except study.Gone as e:
            raise HTTPException(410, str(e))
        except ValueError as e:
            raise HTTPException(409, str(e))
        except cosign.ApprovalError as e:
            raise HTTPException(e.status, str(e))
        except PermissionError as e:
            raise HTTPException(403, str(e))


@app.get("/api/events")
def events(after: int = 0):
    return _call(study.events, after)


@app.get("/api/boundaries")
def boundaries_view():
    from . import boundaries
    return _call(boundaries.view)


@app.get("/api/p/{pid}")
def participant(pid: str):
    return _call(study.participant_view, pid)


@app.get("/api/p/{pid}/preview")
def participant_preview(pid: str, request: int):
    return _call(study.preview, pid, request)


class UploadBody(Strict):
    weeks: list[int] = Field(default_factory=lambda: list(range(1, 9)), max_length=8)
    items: list[str] = Field(default_factory=lambda: ["sleep.daily", "activity.daily", "heart_rate.daily",
                                                      "fatigue.survey", "blood_pressure.daily"], max_length=20)


@app.get("/api/p/{pid}/data")
def participant_data(pid: str):
    return _call(study.my_data, pid)


@app.post("/api/p/{pid}/data/upload")
def participant_upload(pid: str, body: UploadBody = UploadBody()):
    return _call(study.upload_data, pid, body.weeks, ItemsBody(items=body.items).clean())


class ApproveBody(ItemsBody):
    assertion: PasskeyAssertion | None = None


@app.post("/api/p/{pid}/requests/{rid}/approve")
def participant_approve(pid: str, rid: int, body: ApproveBody = ApproveBody()):
    """With a registered passkey, the body must carry the assertion over this request's statement."""
    a = body.assertion.model_dump() if body.assertion else None
    return _call(study.participant_approve, pid, rid, body.clean(), assertion=a)


@app.post("/api/p/{pid}/requests/{rid}/challenge")
def participant_challenge(pid: str, rid: int, body: ItemsBody = ItemsBody()):
    """The approval statement for these items and the WebAuthn options to sign it with."""
    return _call(study.approval_challenge, pid, rid, body.clean())


class ConsentMark(Strict):
    kind: str = Field(pattern=r"^(research|third_party|sensitive|international)$")
    text_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class BatchEntry(Strict):
    request: int
    items: list[str] = Field(max_length=20)
    consents: list[ConsentMark] = Field(default_factory=list, max_length=8)

    def clean(self):
        if [i for i in self.items if not re.match(ITEM, i)]:
            raise HTTPException(422, "unknown item names")
        return {"request": self.request, "items": list(self.items), "consents": [c.model_dump() for c in self.consents]}


class BatchBody(Strict):
    entries: list[BatchEntry] = Field(min_length=1, max_length=10)
    assertion: PasskeyAssertion | None = None


@app.post("/api/p/{pid}/consents/challenge")
def participant_batch_challenge(pid: str, body: BatchBody):
    """Statements for several requests with their separate consents, and one WebAuthn challenge over all."""
    return _call(study.batch_challenge, pid, [e.clean() for e in body.entries])


@app.post("/api/p/{pid}/consents/approve")
def participant_batch_approve(pid: str, body: BatchBody):
    """One passkey assertion applies every request of the batch, each bound to its own statement."""
    if not body.assertion:
        raise HTTPException(403, "a passkey signature is required")
    return _call(study.participant_approve_batch, pid, [e.clean() for e in body.entries], body.assertion.model_dump())


@app.get("/api/p/{pid}/passkey")
def participant_passkey(pid: str):
    return _call(lambda w: {"registered": passkey.has_passkey(w, pid), "held_by": passkey.backend(w, pid).name,
                            "rp_id": passkey.rp_id()})


@app.post("/api/p/{pid}/passkey/register/options")
def participant_passkey_options(pid: str):
    return _call(lambda w: passkey.register_options(w, pid, w.cohort_people[pid].vault.pseudonym(study.LAB)))


@app.post("/api/p/{pid}/passkey/register/complete")
def participant_passkey_complete(pid: str, body: PasskeyRegistration):
    return _call(passkey.register_complete, pid, body.model_dump())


@app.post("/api/p/{pid}/requests/{rid}/decline")
def participant_decline(pid: str, rid: int):
    return _call(study.participant_decline, pid, rid)


@app.post("/api/p/{pid}/pause")
def participant_pause(pid: str):
    return _call(study.participant_pause, pid)


@app.post("/api/p/{pid}/resume")
def participant_resume(pid: str):
    return _call(study.participant_pause, pid, True)


class RevokeBody(Strict):
    assertion: PasskeyAssertion | None = None


@app.post("/api/p/{pid}/revoke/challenge")
def participant_revoke_challenge(pid: str):
    """The withdrawal statement and the WebAuthn options to sign it with."""
    return _call(study.withdrawal_challenge, pid)


@app.post("/api/p/{pid}/revoke")
def participant_revoke(pid: str, body: RevokeBody = RevokeBody()):
    """With a registered passkey, the body must carry the assertion over the withdrawal statement."""
    return _call(study.participant_revoke, pid, assertion=body.assertion.model_dump() if body.assertion else None)


class PushPrepareBody(Strict):
    institution: str = Field(pattern=ID)
    columns: list[str] = Field(min_length=1, max_length=20)
    purpose: str = Field(pattern=ITEM)
    contract: str = Field(pattern=r"^[0-9a-f]{16,64}$")
    price_drops: int = Field(ge=1, le=10**9)
    days: int = Field(default=7, ge=1, le=56)


class PushSealedBody(Strict):
    record: dict
    condition: str = Field(pattern=r"^[0-9A-Fa-f]{78}$")


class PushRevealBody(Strict):
    order_id: str = Field(pattern=ID)
    key_b64u: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class PushRevokeBody(Strict):
    institution: str = Field(pattern=ID)


def _push():
    """Push delivery on the study's engine. The receiving institutions' keys live with them; this demo
    process stands in for their stores."""
    if _state.get("push_world") is not world():
        from .market.acts import load
        from .vault import delivery, keys
        pd = delivery.PushDelivery(world().engine)
        for inst in load()["institutions"]:
            pd.register_institution(inst["id"], inst["country"], keys.InstitutionKey())
        _state["push"], _state["push_world"] = pd, world()
    return _state["push"]


@app.post("/api/p/{pid}/push/prepare")
def push_prepare(pid: str, body: PushPrepareBody):
    """The agreed rows as canonical bytes for the person's page to seal, and the institution's public key."""
    from .catalog import columns as cat
    pd = _push()
    cols = [cat.canon(c) for c in body.columns]
    if any(c not in cat.CATALOG for c in cols) or body.institution not in pd.institutions:
        raise HTTPException(400, "unknown column or institution")
    with _lock:
        if (pid, body.institution) not in pd.consents:
            pd.consent(pid, body.institution, cols, body.purpose)
        rows = [{"day": d, **{c: cat.synth(c, pid, d) for c in cols}} for d in range(body.days)]
        try:
            return pd.prepare(pid, body.institution, rows, cols, body.contract, body.price_drops)
        except PermissionError as e:
            raise HTTPException(403, str(e))


@app.post("/api/p/{pid}/push/sealed")
def push_sealed(pid: str, body: PushSealedBody):
    """The page's sealed bundle and escrow condition: the engine creates the escrow and pushes the bundle."""
    with _lock:
        return _push().accept_sealed(pid, body.record, body.condition)


@app.post("/api/p/{pid}/push/reveal")
def push_reveal(pid: str, body: PushRevealBody):
    """K published in EscrowFinish: the person is paid; the institution opens what it already holds."""
    from .vault.keys import unb64u
    with _lock:
        return _push().reveal(pid, body.order_id, unb64u(body.key_b64u))


@app.post("/api/p/{pid}/push/revoke")
def push_revoke(pid: str, body: PushRevokeBody):
    with _lock:
        return _push().revoke(pid, body.institution)


@app.get("/api/study")
def study_state():
    return _call(study.study_view)


@app.post("/api/study/goal")
def study_goal(body: GoalBody = GoalBody()):
    return _call(study.set_goal, body.goal)


@app.post("/api/study/approve")
def study_approve(body: SignersBody = SignersBody()):
    """Demo harness only: drives the approvers' simulated devices (see /api/study/approvals)."""
    return _call(study.approve, list(body.signers))


@app.post("/api/study/approvals")
def approval_open(request: Request):
    """The researcher asks the treasury approvers to release the spec's budget."""
    return _call(lambda w: cosign.open_approval(w, _claims(request)["sub"]))


@app.get("/api/study/approvals/{aid}")
def approval_view(aid: int):
    return _call(lambda w: cosign.view(w.store, aid))


@app.post("/api/study/approvals/{aid}/signatures")
def approval_sign(aid: int, body: SignatureBody, request: Request):
    """An approver posts the signature their device made. The signer name comes from the token."""
    c = _claims(request)
    return _call(lambda w: cosign.add_signature(w, aid, c["sub"], c["attrs"].get("signer", ""),
                                                body.model_dump(exclude_none=True)))


@app.post("/api/study/send")
def study_send():
    return _call(study.send)


@app.post("/api/study/close-round")
def study_close_round():
    return _call(study.close_round)


@app.post("/api/study/sweep")
def study_sweep():
    return _call(study.sweep)


@app.post("/api/study/payout/release")
def study_payout_release():
    """Pay held shares whose review ended (default: pay) and return what must go back."""
    return _call(lambda w: payout.release_due(w))


@app.post("/api/study/cases/{case_id}/decide")
def study_case_decide(case_id: int, body: DecideBody, request: Request):
    """A named reviewer decides, after the response period. The name must be the signed-in reviewer."""
    if body.reviewer_id != _claims(request)["sub"]:
        raise HTTPException(403, "reviewer_id must be the signed-in reviewer")
    return _call(lambda w: payout.decide(w, study.LAB, case_id, body.reviewer_id, body.confirm))


@app.post("/api/p/{pid}/cases/{case_id}/respond")
def participant_case_respond(pid: str, case_id: int, body: RespondBody = RespondBody()):
    case = world().store.one("SELECT person FROM integrity_cases WHERE id=?", case_id)
    if case is None or case["person"] != pid:
        raise HTTPException(404, "not found")
    return _call(lambda w: payout.respond(w, study.LAB, pid, case_id, body.text))


@app.post("/api/p/{pid}/consent")
def participant_consent(pid: str, body: ConsentBody):
    """New consent (also the only way back after a revoke). Without a signature: the document to sign.
    With the device's signature over its hash: applied and recorded."""
    w = world()
    items = ItemsBody(items=body.items).clean()
    if body.signature is None:
        return signed_consent.draft(w, pid, body.buyer, body.purpose, items, body.weeks, body.automation)
    ident = w.security.authority.identities[pid]
    return _call(lambda w: signed_consent.sign_and_apply(w, pid, body.buyer, body.purpose, items, body.weeks,
                                                         body.automation, body.signature, ident.public_hex))


@app.post("/api/p/{pid}/resume-requests")
def participant_resume_requests(pid: str):
    """One tap after automatic requests were paused for missed rounds."""
    return _call(lambda w: (payout.resume_requests(w, study.LAB, pid), study.participant_view(w, pid))[1])


class PayoutCurrency(BaseModel):
    currency: str          # "XRP" or "stable"


@app.post("/api/p/{pid}/payout-currency")
def participant_payout_currency(pid: str, body: PayoutCurrency):
    """How the participant wants to hold what they earn; a stablecoin is swapped by their own agent."""
    return _call(study.set_payout_currency, pid, body.currency)


@app.get("/api/p/{pid}/uniqdata")
def participant_uniqdata(pid: str, project: str = "project-sleeplab", privacy_epoch: int = Query(0, ge=0)):
    """The participant's engine records in the shapes UniQdata and UniQLab store (uniqdata_port)."""
    def records(w):
        v = study.participant_view(w, pid)
        c = w.store.one("SELECT doc FROM consents WHERE person_id=? AND buyer_id=?", pid, study.LAB)
        try:
            grants, unmapped = (port.consent_grants(json.loads(c["doc"]), project) if c else []), None
        except port.UnmappedConsent as e:
            grants, unmapped = [], str(e)
        rev = next((x for x in reversed(w.study.withdrawals) if x["person"] == pid and x["kind"] == "revoke"), None)
        return {"project_id": project, "participant_number": v["person"]["study_pseudonym"],
                "consent_grants": grants, "unmapped_consent": unmapped,
                "payout_receipts": port.payout_receipts(v["contributions"], w.ledger.name, v["payout"]["holdbacks"]),
                "withdrawal": port.withdrawal_record({**rev, **v}, project, privacy_epoch) if rev else None}
    return _call(records)


@app.get("/api/study/dispute/{tx_hash}")
def study_dispute(tx_hash: str):
    """From one ledger tx back to the signed chain that authorized it (Verifiable Intent)."""
    return _call(study.dispute, tx_hash)


@app.post("/api/contract/round")
def contract_round(providers: int = Query(default=14, ge=2, le=40), target: int = Query(default=8, ge=1, le=100)):
    """The study's agent buys per-column data under negotiated contracts, checked as it arrives."""
    from .contract import onledger
    with _lock:
        return onledger.run(world(), providers, target, model=_forecast_model())


def _market_view(act: int) -> dict:
    r = _state.get(f"market{act}")
    if r is None:
        return {"act": act, "status": "not run"}
    ex = r["exchange"]
    out = {k: v for k, v in r.items() if k not in ("exchange", "needs")}
    out["activity"] = ex.activity()
    out["needs"] = [{k: v for k, v in n.items() if k != "fills"} for n in r["needs"]]
    out["pending_for_manual"] = [{k: v for k, v in p.items() if k not in ("trade", "offer")} for p in ex.pending]
    return json.loads(json.dumps(out, default=str))


@app.post("/api/market/run")
def market_run(act: int = Query(default=1, ge=1, le=2)):
    """Act 1: the 50 accounts' agents trade among themselves. Act 2: the same pipeline with the
    healthcare sensitivity policy plugged into each participant's agent."""
    from .market import acts
    with _lock:
        _state[f"market{act}"] = (acts.act1 if act == 1 else acts.act2)()
        return _market_view(act)


@app.get("/api/market/products")
def market_products(pid: str = Query(default="P-017"), tap: bool = Query(default=True)):
    """One person's agent: everyday data supply-first (collect, bundle by domain, list), sensitive data
    demand-first (search postings, match, review); then de-identify and sell as a sealed push."""
    from .market import products
    try:
        r = products.scene(pid, tap=tap)
    except KeyError:
        raise HTTPException(404, "unknown participant")
    _state["products"] = r
    return json.loads(json.dumps(r, default=str))


@app.get("/api/market/cohorts")
def market_cohorts():
    """Lots of at least k people assembled by the sellers' agents per need; nothing leaves below k."""
    from .market import cohort
    r = cohort.run()
    _state["cohorts"] = r
    return r


@app.get("/api/market/activity")
def market_activity(act: int = Query(default=1, ge=1, le=2)):
    return _market_view(act)


@app.get("/api/catalog")
def catalog():
    """Every column with its tier, data use codes, retention and deletion rule; plus the approval bottleneck."""
    from .catalog import columns, simulate
    if "bottleneck" not in _state:
        _state["bottleneck"] = simulate.run()
    return {"columns": [c.card() for c in columns.CATALOG.values()], "duo": columns.DUO,
            "bottleneck": _state["bottleneck"]}


@app.get("/api/contract/projection")
def contract_projection():
    """Live projection of the round (usable so far, expected final with a 90% band, power, risks)."""
    from .contract import onledger
    return onledger.view(world())


def _forecast_model():
    if "forecast" not in _state:
        from .contract import measure
        _state["forecast"] = measure.train()[0]
    return _state["forecast"]


@app.get("/api/report")
def run_report():
    """One self-contained HTML page for this run: contract, negotiation, checks, projection, payments,
    holdbacks, tx links, and the market acts if they ran."""
    from fastapi.responses import HTMLResponse
    from . import engine_check as ec, report
    from .contract import onledger
    with _lock:
        w = world()
        markets = [_market_view(a) for a in (1, 2) if f"market{a}" in _state]
        return HTMLResponse(report.render(onledger.view(w), markets, {"flows": ec.flows(w)}, ledger=w.ledger.name,
                                          products=_state.get("products"), cohorts=_state.get("cohorts")))


@app.get("/api/market/network")
def market_network():
    """Act 1 as a node network replayed from the trade log, with one settled and one refused trade
    zoomed in and the agent's decision stepped through (self-contained HTML)."""
    from fastapi.responses import HTMLResponse
    from . import network_view
    from .market import acts
    with _lock:
        if "market1" not in _state:
            _state["market1"] = acts.act1()
        return HTMLResponse(network_view.render(network_view.build(_state["market1"]["exchange"])))


@app.get("/api/market/contracts")
def market_contracts(act: int = Query(default=1, ge=1, le=2), i: int | None = Query(default=None, ge=0)):
    """One record per contract attempt: both agents' conversation (turns with reasoning and checks),
    verdicts and tx hashes (schema agentrail.contract_trace/1)."""
    r = _state.get(f"market{act}")
    if r is None:
        raise HTTPException(404, "market act not run")
    cs = r["exchange"].contracts
    if i is not None:
        if i >= len(cs):
            raise HTTPException(404, "no such contract")
        return json.loads(json.dumps(cs[i], default=str))
    return [{"i": k, **{x: c[x] for x in ("need", "buyer", "seller", "columns", "status", "price_drops", "verdicts")}}
            for k, c in enumerate(cs)]


class SubProjectBody(Strict):
    name: str = Field(min_length=1, max_length=80)
    purpose: str = Field(pattern=r"^[a-z_]{1,40}$")
    data_types: list[str] = Field(min_length=1, max_length=20)
    budget: float = Field(gt=0, le=1_000_000)          # in the settlement unit (units.UNIT)
    weeks: int = Field(ge=1, le=52)


class RelationshipConsentBody(Strict):
    institution: str = Field(default=study.LAB, pattern=ID)
    items: list[Annotated[str, Field(pattern=r"^[a-z0-9_.]{1,60}$")]] | None = Field(default=None, max_length=40)


class SubProjectDecisionBody(Strict):
    item: str = Field(pattern=r"^[a-z0-9_.]{1,60}$")
    allow: bool


def _rel(fn):
    from . import subprojects
    return json.loads(json.dumps(_call(lambda w: fn(subprojects.of(w))), default=str))


@app.get("/api/institution")
def institution_view():
    """The institution's scope, how many people hold the relationship, and its sub-projects."""
    return _rel(lambda r: r.institution())


@app.post("/api/institution/subprojects")
def institution_create_subproject(body: SubProjectBody):
    """A sub-project under the institution's one account and consented scope; returns the routing per
    person and item (auto inside the scope, ask outside it or for T3, blocked by the person's rules)."""
    return _rel(lambda r: r.create(body.name, body.purpose, body.data_types, int(body.budget * 1e6), body.weeks))


@app.post("/api/institution/subprojects/{sid}/run")
def institution_run_subproject(sid: str):
    """One delivery round of a sub-project: one escrow per person, memo tagged sub:<sid>."""
    return _rel(lambda r: r.run(sid) if sid in r.subprojects else {"ok": False, "reason": "unknown sub-project"})


@app.get("/api/p/{pid}/relationship")
def participant_relationship(pid: str):
    """The person's one relationship with the institution: scope, consent, each sub-project's payouts."""
    return _rel(lambda r: r.relationship(pid))


@app.post("/api/p/{pid}/relationship/consent")
def participant_relationship_consent(pid: str, body: RelationshipConsentBody):
    return _rel(lambda r: {"ok": True, "consented": r.consent(pid, body.items), **r.relationship(pid)})


@app.post("/api/p/{pid}/subprojects/{sid}/decision")
def participant_subproject_decision(pid: str, sid: str, body: SubProjectDecisionBody):
    """The person's answer for an item outside the scope or T3, for this sub-project only."""
    return _rel(lambda r: r.decide(pid, sid, body.item, body.allow) if sid in r.subprojects
                else {"ok": False, "reason": "unknown sub-project"})


@app.get("/api/proof")
def proof_of_one_trade():
    """One paid contract checked link by link (contract, stamps, escrow memo, K, bundle), one
    contribution refused before payment, one withdrawal that stopped the next delivery."""
    from . import binding
    with _lock:
        return json.loads(json.dumps(binding.proof(world()), default=str))


@app.get("/api/costs")
def running_costs():
    """What keeping the agents up cost in this run: LLM calls and tokens per side, ledger transactions and
    fees, reserve tied up, per participant-week."""
    from . import costs
    with _lock:
        return costs.summarize(world())


@app.get("/api/engine/check")
def engine_check():
    """One row per flow of the health trade, each with the ledger transaction that proves it."""
    from . import engine_check as ec
    with _lock:
        return {"ledger": world().ledger.name, "flows": ec.flows(world())}


@app.get("/api/study/live")
def study_live(after: int = 0):
    """Clawback and EscrowCancel as the ledger stream delivers them (Testnet: WebSocket subscribe)."""
    from . import live
    return live.feed(world()).since(after)


@app.get("/api/study/bundle/{oid}")
def study_bundle(oid: int, use: str = "sleep_research"):
    return _call(study.open_bundle, oid, use)


# ---------- login ----------

@app.post("/api/auth/challenge")
def auth_challenge(body: ChallengeBody):
    return _authority().challenge(body.sub)


@app.post("/api/auth/token")
def auth_token(body: TokenBody):
    try:
        return _authority().token_for_signature(body.sub, body.nonce, body.signature)
    except AuthError as e:
        raise HTTPException(401, str(e))


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    _authority().revoke(_claims(request))
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(request: Request):
    c = _claims(request)
    return {k: c[k] for k in ("sub", "role", "scope", "attrs", "exp")}


# ---------- operations ----------

@app.get("/api/ops/audit/verify")
def audit_verify():
    return _call(lambda w: audit.verify_chain(w.store))


@app.post("/api/ops/audit/anchor")
def audit_anchor():
    return _call(audit.anchor)


# ---------- research contracts: posted by a researcher, joined by people (agentrail/research_contracts.py) ----------

def lane():
    if "lane" not in _state:
        from .research_contracts import Lane
        with _lock:
            if "lane" not in _state:
                _state["lane"] = Lane()
                _state["lane"].enrol_all(_authority())
    return _state["lane"]


def _lcall(fn, *a):
    from .research_contracts import ContractError
    try:
        return fn(lane(), *a)
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ContractError as e:
        raise HTTPException(422, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


HEX64 = r"^[0-9a-f]{64}$"
SIG = r"^[0-9a-f]{128}$"


class ContractTerms(Strict):
    title: str = Field(min_length=1, max_length=120)
    institution: str = Field(min_length=1, max_length=120)
    irb_approval: str = Field(min_length=1, max_length=60)
    purpose: str = Field(pattern=r"^[a-z_]{1,40}$")
    items: list[str] = Field(min_length=1, max_length=10)
    weeks: tuple[int, int]
    price_per_item_drops: int = Field(gt=0, le=1_000_000_000)
    budget_drops: int = Field(gt=0, le=100_000_000_000)
    capacity: int = Field(default=60, ge=1, le=500)
    summary: str = Field(default="", max_length=600)
    # the researcher's agent runs the next week on its own every this many seconds (60 for a demo, 604800 weekly)
    round_every_s: int | None = Field(default=None, ge=60, le=31_536_000)


class ContractPost(Strict):
    terms: ContractTerms
    researcher_key: str = Field(pattern=HEX64)


class JoinStart(Strict):
    invite_code: str = Field(min_length=8, max_length=64)
    public_key: str = Field(pattern=HEX64)
    items: list[str] = Field(default_factory=list, max_length=10)
    automation: Literal["confirm_each", "auto_standard", "auto_all"] = "confirm_each"
    uniqdata_account: str | None = Field(default=None, pattern=ID)
    # the member's XRPL EVM address: AP4M payments are forwarded there from the team's merchant wallet
    payout_address: str | None = Field(default=None, pattern=r"^0x[0-9a-fA-F]{40}$")


class JoinComplete(Strict):
    pid: str = Field(pattern=ID)
    signature: str = Field(pattern=SIG)
    # a test account without a UniQdata account: store generated test readings for these weeks (labelled so)
    generate_test_weeks: list[int] = Field(default_factory=list, max_length=52)


class RoundBody(Strict):
    week: int = Field(ge=1, le=52)


class RecordIn(Strict):
    item: str = Field(pattern=ITEM)
    day: int = Field(ge=1, le=366)
    value: dict


class RecordsBody(Strict):
    records: list[RecordIn] = Field(default_factory=list, max_length=2000)
    generate_test_weeks: list[int] = Field(default_factory=list, max_length=52)


class SignedItems(Strict):
    items: list[str] = Field(default_factory=list, max_length=10)
    signature: str = Field(pattern=SIG)


class Signed(Strict):
    signature: str = Field(pattern=SIG)


def _posting_code(request: Request):
    """Posting a contract creates ledger accounts and a budget: localhost, or the code in
    AGENTRAIL_POSTING_CODE (at least 8 characters)."""
    code = os.environ.get("AGENTRAIL_POSTING_CODE", "")
    if (request.client.host if request.client else "") in LOCAL:
        return
    if len(code) >= 8 and hmac.compare_digest(request.headers.get("x-posting-code", "").encode(), code.encode()):
        return
    raise HTTPException(403, "posting code required")


@app.get("/api/contracts")
def contracts_list():
    return _lcall(lambda L: {"contracts": L.list()})


@app.post("/api/contracts")
def contracts_post(body: ContractPost, request: Request):
    _posting_code(request)
    def post(L):
        out = L.create(body.terms.model_dump(), body.researcher_key)
        L.enrol_all(_authority())              # the researcher signs in with the key they posted
        return out
    return _lcall(post)


@app.get("/api/contracts/{cid}")
def contracts_get(cid: str):
    return _lcall(lambda L: L.public(cid))


@app.post("/api/contracts/{cid}/join/start")
def contracts_join_start(cid: str, body: JoinStart):
    return _lcall(lambda L: L.join_start(cid, body.invite_code, body.public_key, body.items, body.automation,
                                         body.uniqdata_account, body.payout_address))


@app.post("/api/contracts/{cid}/join/complete")
def contracts_join_complete(cid: str, body: JoinComplete):
    def complete(L):
        out = L.join_complete(cid, body.pid, body.signature, _authority())
        if body.generate_test_weeks:
            L.store_records(body.pid, None, body.generate_test_weeks)
        return out
    return _lcall(complete)


@app.get("/api/contracts/{cid}/console")
def contracts_console(cid: str):
    return _lcall(lambda L: L.console(cid))


@app.post("/api/contracts/{cid}/rounds")
def contracts_round(cid: str, body: RoundBody):
    return _lcall(lambda L: L.run_round(cid, body.week))


@app.post("/api/contracts/{cid}/close")
def contracts_close(cid: str):
    return _lcall(lambda L: L.close(cid))


@app.get("/api/p/{pid}/contracts")
def member_contracts(pid: str):
    return _lcall(lambda L: L.member_view(pid))


@app.post("/api/p/{pid}/contracts/records")
def member_records(pid: str, body: RecordsBody):
    return _lcall(lambda L: L.store_records(pid, [r.model_dump() for r in body.records], body.generate_test_weeks))


@app.post("/api/p/{pid}/contracts/{cid}/requests/{rid}/approve")
def member_approve(pid: str, cid: str, rid: int, body: SignedItems):
    return _lcall(lambda L: L.approve(pid, cid, rid, body.items, body.signature))


@app.post("/api/p/{pid}/contracts/{cid}/withdraw")
def member_withdraw(pid: str, cid: str, body: Signed):
    return _lcall(lambda L: L.withdraw(pid, cid, body.signature))


# ---------- demo harness (AGENTRAIL_ENV=dev only; rbac returns 404 in prod) ----------

LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}


def _local(request: Request):
    if (request.client.host if request.client else "") not in LOCAL:
        raise HTTPException(403, "the demo harness answers on localhost only")


def _local_or_code(request: Request, sub: str):
    """The demo devices answer on localhost, or to a visitor who sends the access code set in
    AGENTRAIL_SANDBOX_CODE (at least 8 characters). The operator (reset, scene runner) stays local.
    One code can act as both co-signers, so it only counts on the mock ledger (unless
    AGENTRAIL_SANDBOX_ALLOW_TESTNET=1) and never in prod."""
    code = os.environ.get("AGENTRAIL_SANDBOX_CODE", "")
    sent = request.headers.get("x-sandbox-code", "")
    if (request.client.host if request.client else "") in LOCAL:
        return
    sandbox = is_dev() and (world().ledger.name == "mock" or os.environ.get("AGENTRAIL_SANDBOX_ALLOW_TESTNET") == "1")
    if sandbox and len(code) >= 8 and sub != "operator" and hmac.compare_digest(sent.encode(), code.encode()):
        return
    raise HTTPException(403, "access code required")


@app.post("/api/dev/login/{sub}")
def dev_login(sub: str, request: Request):
    """The simulated device of `sub` answers a challenge, exactly as a real device would."""
    _local_or_code(request, sub)
    sec = world().security
    d = sec.devices.get(sub)
    if d is None:
        raise HTTPException(404, "no such demo device")
    ch = sec.authority.challenge(sub)
    return sec.authority.token_for_signature(sub, ch["nonce"], d.sign_challenge(ch["nonce"]))


@app.post("/api/dev/devices/{sub}/sign-approval/{aid}")
def dev_sign_approval(sub: str, aid: int, request: Request):
    """What the approver's phone would return after showing the approval; posting it still needs
    that approver's own token at /api/study/approvals/{aid}/signatures."""
    _local_or_code(request, sub)
    sec = world().security
    d = next((x for x in sec.approvers.values() if x.sub == sub), None)
    if d is None:
        raise HTTPException(404, "no such approver device")
    return _call(lambda w: d.cosign(cosign.view(w.store, aid)))


def _page(*parts):
    p = Path(__file__).parent.parent.joinpath(*parts)
    if not p.exists():
        raise HTTPException(404, "page not built yet")
    return FileResponse(p)


def _card(name, desc, url, skills):
    return {"name": name, "description": desc, "version": "0.1.0",
            "supportedInterfaces": [{"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
            "capabilities": {"streaming": False, "pushNotifications": False,
                             "extensions": [{"uri": "https://github.com/google-agentic-commerce/ap2", "required": False},
                                            {"uri": "https://x402.org", "required": False}]},
            "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
            "skills": skills}


@app.get("/.well-known/agent-card.json")
def research_agent_card():
    """A2A v1.0 Agent Card for the study's research agent (static; demo only)."""
    return _card("Sleep study research agent (synthetic)",
                 "Finds missing person-weeks in a study and sends participation requests; pays by XRPL escrow.",
                 "/api/study", [{"id": "research_request", "name": "Participation request",
                                 "description": "Ask a participant's agent for protocol items and weeks.",
                                 "tags": ["research", "consent", "xrpl"]}])


@app.get("/agents/{pid}/.well-known/agent-card.json")
def personal_agent_card(pid: str):
    return _card(f"Personal agent of {pid} (synthetic)",
                 "Answers research participation requests within the person's consent; asks the person otherwise.",
                 f"/api/p/{pid}", [{"id": "answer_research_request", "name": "Answer participation request",
                                    "description": "auto / ask the person / blocked, then sealed contribution.",
                                    "tags": ["consent", "health-record", "xrpl-escrow"]}])


@app.get("/participant")
def participant_page():
    return _page("apps", "participant", "index.html")


@app.get("/console")
def console_page():
    return _page("apps", "researcher", "index.html")


@app.get("/api/public/live")
def public_live(after: int = 0):
    """Read-only view for visitors without the access code: structure, cohort and the ledger log
    (synthetic study, study pseudonyms only where the engine already uses them)."""
    from . import subprojects

    def view(w):
        s = study.study_view(w)
        e = study.events(w, after)
        ev = [x for x in e["events"] if x["kind"] != "access"]
        return {"study": {k: s["study"][k] for k in ("id", "name", "ledger", "protocol")},
                "heatmap": s["heatmap"], "settlement": s["settlement"], "spec_status": s["spec_status"],
                "institution": subprojects.of(w).institution(), "events": ev, "last": e["last"]}
    return _call(view)


@app.get("/api/public/ap4m")
def public_ap4m(verify: bool = False):
    """The agent's RLUSD payments on the AP4M rail (synthetic exports). With verify=1 each VoucherRedeemed
    transaction is checked on an XRPL EVM Testnet RPC node against the run record."""
    from . import ap4m_receipts
    return ap4m_receipts.view(check=verify)


@app.get("/try")
def try_it(request: Request):
    """Entry for visitors: pick researcher (UniQLab live view), participant (UniQdata) or the before/after story."""
    return RedirectResponse(f"/apps/try/index.html{'?' + request.url.query if request.url.query else ''}")


@app.get("/demo")
def before_after_demo(request: Request):
    """Before/after stage: UniQLab and UniQdata side by side, today's flow and the flow with agents."""
    return RedirectResponse(f"/apps/demo/index.html{'?' + request.url.query if request.url.query else ''}")


if (Path(__file__).parent.parent / "apps").is_dir():
    app.mount("/apps", StaticFiles(directory=Path(__file__).parent.parent / "apps", html=True), name="apps")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
