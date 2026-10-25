"""Who may call which route. Default deny: a route without a rule here answers 403, so a new endpoint
is closed until someone writes down who may use it (a test fails if any route has no rule).

Roles
  participant  their own requests, consent, preview, withdrawals (scope = their participant id)
  researcher   the study's console: goal, requests, rounds, sealed bundles (scope = study id, or one
               research contract id for the contract routes)
  approver     signs treasury approvals for that study (scope = study id, attrs.signer)
  reviewer     decides integrity cases for that study, under their own name
  operator     runs the service: dashboard state, audit verification and anchoring, demo harness;
               never opens bundles and cannot act for a participant, researcher or approver
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from .auth import AuthError
from .secrets import is_dev

STUDY = "org_sleeplab"


@dataclass(frozen=True)
class Rule:
    roles: tuple = ()
    scope: str | None = None       # "self" (path pid == token scope) | "study" (token scope == study)
    public: bool = False
    dev_only: bool = False


P, R, A, V, O = "participant", "researcher", "approver", "reviewer", "operator"
SELF = Rule((P,), "self")
STUDY_TEAM = Rule((R,), "study")

POLICY: dict[tuple[str, str], Rule] = {
    # login
    ("POST", "/api/auth/challenge"): Rule(public=True),
    ("POST", "/api/auth/token"): Rule(public=True),
    ("POST", "/api/auth/logout"): Rule((P, R, A, V, O)),
    ("GET", "/api/auth/me"): Rule((P, R, A, V, O)),
    # participant app
    ("GET", "/api/p/{pid}"): SELF,
    ("GET", "/api/p/{pid}/preview"): SELF,
    ("GET", "/api/p/{pid}/data"): SELF,
    ("POST", "/api/p/{pid}/requests/{rid}/approve"): SELF,
    ("POST", "/api/p/{pid}/data/upload"): SELF,
    ("POST", "/api/p/{pid}/requests/{rid}/decline"): SELF,
    ("POST", "/api/p/{pid}/pause"): SELF,
    ("POST", "/api/p/{pid}/resume"): SELF,
    ("POST", "/api/p/{pid}/revoke"): SELF,
    ("POST", "/api/p/{pid}/revoke/challenge"): SELF,
    ("POST", "/api/p/{pid}/consents/challenge"): SELF,
    ("POST", "/api/p/{pid}/consents/approve"): SELF,
    ("POST", "/api/p/{pid}/push/prepare"): SELF,
    ("POST", "/api/p/{pid}/push/sealed"): SELF,
    ("POST", "/api/p/{pid}/push/reveal"): SELF,
    ("POST", "/api/p/{pid}/push/revoke"): SELF,
    ("POST", "/api/p/{pid}/consent"): SELF,
    ("POST", "/api/p/{pid}/cases/{case_id}/respond"): SELF,
    ("POST", "/api/p/{pid}/resume-requests"): SELF,
    ("POST", "/api/p/{pid}/payout-currency"): SELF,
    ("GET", "/api/p/{pid}/uniqdata"): SELF,
    ("POST", "/api/p/{pid}/requests/{rid}/challenge"): SELF,
    ("GET", "/api/p/{pid}/passkey"): SELF,
    ("POST", "/api/p/{pid}/passkey/register/options"): SELF,
    ("POST", "/api/p/{pid}/passkey/register/complete"): SELF,
    ("GET", "/api/p/{pid}/relationship"): SELF,
    ("POST", "/api/p/{pid}/relationship/consent"): SELF,
    ("POST", "/api/p/{pid}/subprojects/{sid}/decision"): SELF,
    ("GET", "/api/institution"): Rule((R, O), "study"),
    ("POST", "/api/institution/subprojects"): Rule((R, O), "study"),
    ("POST", "/api/institution/subprojects/{sid}/run"): Rule((R, O), "study"),
    # researcher console
    ("GET", "/api/study"): Rule((R, A, V, O), "study"),
    ("POST", "/api/study/goal"): STUDY_TEAM,
    ("POST", "/api/study/send"): STUDY_TEAM,
    ("POST", "/api/study/close-round"): STUDY_TEAM,
    ("POST", "/api/study/sweep"): STUDY_TEAM,
    ("POST", "/api/study/payout/release"): STUDY_TEAM,
    ("GET", "/api/study/bundle/{oid}"): STUDY_TEAM,
    ("GET", "/api/study/dispute/{tx_hash}"): STUDY_TEAM,
    ("GET", "/api/study/live"): Rule((R, O), "study"),
    ("GET", "/api/engine/check"): Rule((R, O), "study"),
    ("POST", "/api/contract/round"): Rule((R, O), "study"),
    ("GET", "/api/contract/projection"): Rule((R, O), "study"),
    ("GET", "/api/catalog"): Rule((R, O), "study"),
    ("GET", "/api/report"): Rule((R, O), "study"),
    ("GET", "/api/costs"): Rule((R, O), "study"),
    ("GET", "/api/proof"): Rule((R, O), "study"),
    ("GET", "/api/market/network"): Rule((R, O), "study"),
    ("GET", "/api/market/contracts"): Rule((R, O), "study"),
    ("POST", "/api/market/run"): Rule((R, O), "study"),
    ("GET", "/api/market/activity"): Rule((R, O), "study"),
    ("GET", "/api/market/products"): Rule((R, O), "study"),
    ("GET", "/api/market/cohorts"): Rule((R, O), "study"),
    ("GET", "/api/events"): Rule((R, O), "study"),
    ("GET", "/api/boundaries"): Rule((R, O), "study"),
    # treasury approvals: researcher opens one, each approver signs on their own device
    ("POST", "/api/study/approvals"): STUDY_TEAM,
    ("GET", "/api/study/approvals/{aid}"): Rule((R, A), "study"),
    ("POST", "/api/study/approvals/{aid}/signatures"): Rule((A,), "study"),
    # integrity review: a named reviewer decides
    ("POST", "/api/study/cases/{case_id}/decide"): Rule((V,), "study"),
    # operations
    ("GET", "/api/ops/audit/verify"): Rule((O, R), "study"),
    ("POST", "/api/ops/audit/anchor"): Rule((O,)),
    ("GET", "/api/state"): Rule((O,)),
    # research contracts (agentrail/research_contracts.py): posting needs the posting code, joining the
    # invite code and the joiner's own signature; the researcher's token is scoped to one contract
    # "How my agent decides": stateless, synthetic owner, nothing read or stored
    ("GET", "/api/agent/explain/presets"): Rule(public=True),
    ("POST", "/api/agent/explain"): Rule(public=True),
    ("GET", "/api/contracts"): Rule(public=True),
    ("GET", "/api/institutions/overview"): Rule(public=True),   # counts and timings only, no member ids
    ("POST", "/api/contracts"): Rule(public=True),
    ("GET", "/api/contracts/{cid}"): Rule(public=True),
    ("POST", "/api/contracts/{cid}/join/start"): Rule(public=True),
    ("POST", "/api/contracts/{cid}/join/complete"): Rule(public=True),
    ("GET", "/api/contracts/{cid}/console"): Rule((R, O), "contract"),
    ("POST", "/api/contracts/{cid}/rounds"): Rule((R,), "contract"),
    ("POST", "/api/contracts/{cid}/close"): Rule((R,), "contract"),
    ("GET", "/api/p/{pid}/contracts"): SELF,
    ("POST", "/api/p/{pid}/contracts/records"): SELF,
    ("POST", "/api/p/{pid}/contracts/{cid}/requests/{rid}/approve"): SELF,
    ("POST", "/api/p/{pid}/contracts/{cid}/withdraw"): SELF,
    # demo harness: runs every party in one process; off when AGENTRAIL_ENV=prod
    ("POST", "/api/reset"): Rule((O,), dev_only=True),
    ("POST", "/api/run/{scene}"): Rule((O,), dev_only=True),
    ("POST", "/api/study/approve"): Rule((O,), dev_only=True),
    ("POST", "/api/dev/login/{sub}"): Rule(public=True, dev_only=True),
    ("POST", "/api/dev/devices/{sub}/sign-approval/{aid}"): Rule(public=True, dev_only=True),
    # pages and agent cards (no data)
    ("GET", "/"): Rule(public=True),
    ("GET", "/participant"): Rule(public=True),
    ("GET", "/console"): Rule(public=True),
    ("GET", "/institutions"): Rule(public=True),
    ("GET", "/demo"): Rule(public=True),
    ("GET", "/try"): Rule(public=True),
    ("GET", "/api/public/live"): Rule(public=True),
    ("GET", "/api/public/ap4m"): Rule(public=True),
    ("GET", "/.well-known/agent-card.json"): Rule(public=True),
    ("GET", "/agents/{pid}/.well-known/agent-card.json"): Rule(public=True),
}

# FastAPI's own pages are not part of the API surface.
OPEN_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def rule_for(request: Request) -> Rule | None:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    method = "GET" if request.method == "HEAD" else request.method
    return POLICY.get((method, path)) if path else None


def bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h.lower().startswith("bearer ") else None


def check(request: Request, authority) -> dict | None:
    """Raises HTTPException unless the caller may use this route. Returns the token claims."""
    path = getattr(request.scope.get("route"), "path", "")
    if path in OPEN_PATHS:
        if not is_dev():
            raise HTTPException(404, "not found")
        return None
    rule = rule_for(request)
    if rule is None:
        raise HTTPException(403, "no access rule for this route (default deny)")
    if rule.dev_only and not is_dev():
        raise HTTPException(404, "not found")
    if rule.public:
        return None
    tok = bearer(request)
    if not tok:
        raise HTTPException(401, "sign in: Authorization: Bearer <token>", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = authority.verify(tok)
    except AuthError as e:
        raise HTTPException(401, str(e), headers={"WWW-Authenticate": "Bearer"})
    if claims["role"] not in rule.roles:
        raise HTTPException(403, f"role {claims['role']} may not use this route")
    if rule.scope == "self" and request.path_params.get("pid") != claims["scope"]:
        raise HTTPException(403, "participants can act only on their own record")
    if rule.scope == "study" and claims["role"] != "operator" and claims["scope"] != STUDY:
        raise HTTPException(403, "this token is for another study")
    if rule.scope == "contract" and claims["role"] != "operator" and claims["scope"] != request.path_params.get("cid"):
        raise HTTPException(403, "this token is for another contract")
    request.state.claims = claims
    return claims
