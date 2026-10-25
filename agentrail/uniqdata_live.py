"""Live connection to a running UniQdata Core (local sandbox): the person's own records are written
to and read back from UniQdata's real API, and the engine's personal vault reads them from there.

Written during the hackathon. No UniQdata code is imported; this is an HTTP client for its public
API (`/api/v1/data/write/batch`, `/api/v1/data/inventory`, `/api/v1/data/query`). UniQdata asks
for a passkey assertion bound to each sensitive request; the person's software passkey (synthetic
person, local sandbox only) answers it here, the way the phone app does with the device passkey.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

ORIGIN = os.environ.get("UNIQDATA_WEBAUTHN_ORIGIN", "http://localhost:8000")
ASSERTION_HEADER, ACTION_ID_HEADER = "X-UniQdata-Action-Assertion", "X-UniQdata-Action-Id"

# engine item -> UniQdata (OMOP) records, with concepts UniQdata accepts without a vocabulary load.
# Sleep has no such concept yet, so it goes in as UniQdata's generic typed answer with the item named
# in source_value; the other four use their own concepts.
CONCEPTS = {
    "heart_rate.daily": [("measurement", 3027018, "resting_bpm", "WEARABLE")],
    "activity.daily": [("measurement", 3034985, "steps", "WEARABLE")],
    "fatigue.survey": [("observation", 2000000102, "score_0_10", "MANUAL")],
    "blood_pressure.daily": [("measurement", 3004249, "SYSBP", "EMR_IMPORT"),
                             ("measurement", 3012888, "DIABP", "EMR_IMPORT")],
    "sleep.daily": [("observation", 2000000160, "minutes", "WEARABLE")],
}
# The wider health catalog (tiers T0-T3) stored for the cohort. T2/T3 items have no concept UniQdata
# accepts without a vocabulary load either, so they use the generic typed answer as sleep does.
GENERIC = 2000000160
CATALOG = {
    # T0 everyday device data
    "spo2.daily": ("T0", "wearable", [("measurement", 40762499, "pct", "WEARABLE")]),
    "body_weight.daily": ("T0", "smart_scale", [("measurement", 3025315, "kg", "SENSOR")]),
    "body_temp.daily": ("T0", "wearable", [("measurement", 3020891, "celsius", "WEARABLE")]),
    # T1 life log and self-report
    "meal.log": ("T1", "meal_app", [("observation", GENERIC, "kcal", "MANUAL")]),
    "medication.taken": ("T1", "pill_reminder", [("observation", GENERIC, "taken", "MANUAL")]),
    "mood.daily": ("T1", "survey_app", [("observation", GENERIC, "score_1_5", "MANUAL")]),
    "energy.survey": ("T1", "survey_app", [("observation", 2000000101, "score_0_10", "MANUAL")]),
    # T2 clinical
    "lab.glucose": ("T2", "clinic_export", [("measurement", 3004501, "mg_dl", "EMR_IMPORT")]),
    "lab.hba1c": ("T2", "clinic_export", [("measurement", 3034639, "pct", "EMR_IMPORT")]),
    "diagnosis.code": ("T2", "clinic_export", [("observation", GENERIC, "icd10_index", "EMR_IMPORT")]),
    "prescription.active": ("T2", "clinic_export", [("observation", GENERIC, "count", "EMR_IMPORT")]),
    # T3 highly sensitive
    "genome.variant": ("T3", "genomics_lab", [("observation", GENERIC, "risk_score", "LAB_UPLOAD")]),
    "imaging.ct": ("T3", "hospital_pacs", [("observation", GENERIC, "slices", "EMR_IMPORT")]),
    "imaging.mri": ("T3", "hospital_pacs", [("observation", GENERIC, "series", "EMR_IMPORT")]),
    "mental.phq9": ("T3", "clinic_export", [("observation", GENERIC, "score_0_27", "MANUAL")]),
}
CONCEPTS.update({k: v[2] for k, v in CATALOG.items()})
TIER = {"sleep.daily": "T0", "activity.daily": "T0", "heart_rate.daily": "T0", "fatigue.survey": "T1",
        "blood_pressure.daily": "T2", **{k: v[0] for k, v in CATALOG.items()}}

SOURCE = {"heart_rate.daily": "wearable", "sleep.daily": "wearable", "activity.daily": "wearable",
          "fatigue.survey": "survey_app", "blood_pressure.daily": "clinic_export",
          **{k: v[1] for k, v in CATALOG.items()}}
DAY0 = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)      # study day 1 (Monday)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _cbor(v) -> bytes:
    """Minimal CBOR (ints, bytes, text, maps): enough for a WebAuthn attestation object."""
    def head(major, n):
        if n < 24:
            return bytes([major << 5 | n])
        for ai, size in ((24, 1), (25, 2), (26, 4), (27, 8)):
            if n < 1 << (8 * size):
                return bytes([major << 5 | ai]) + n.to_bytes(size, "big")
    if isinstance(v, int):
        return head(0, v) if v >= 0 else head(1, -1 - v)
    if isinstance(v, bytes):
        return head(2, len(v)) + v
    if isinstance(v, str):
        return head(3, len(v.encode())) + v.encode()
    if isinstance(v, dict):
        return head(5, len(v)) + b"".join(_cbor(k) + _cbor(x) for k, x in v.items())
    raise TypeError(type(v))


class SoftPasskey:
    """ES256 software passkey for a synthetic person. Stored in a local file, never committed."""

    def __init__(self, key: ec.EllipticCurvePrivateKey, cred_id: bytes, rp_id: str = "uniqdata.io"):
        # signature counter must only go up across runs: derive it from the clock
        self.key, self.cred_id, self.rp_id, self.count = key, cred_id, rp_id, int(time.time() * 10) & 0x7FFFFFFF

    @classmethod
    def new(cls) -> "SoftPasskey":
        return cls(ec.generate_private_key(ec.SECP256R1()), os.urandom(32))

    @classmethod
    def load(cls, path: str) -> "SoftPasskey":
        d = json.load(open(path))
        key = serialization.load_pem_private_key(d["key"].encode(), None)
        return cls(key, base64.urlsafe_b64decode(d["cred"] + "=="), d["rp_id"])

    def dump(self) -> dict:
        pem = self.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()).decode()
        return {"key": pem, "cred": _b64(self.cred_id), "rp_id": self.rp_id}

    @classmethod
    def from_dump(cls, d: dict) -> "SoftPasskey":
        key = serialization.load_pem_private_key(d["key"].encode(), None)
        return cls(key, base64.urlsafe_b64decode(d["cred"] + "=="), d["rp_id"])

    def save(self, path: str):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(self.dump(), f)

    def _rp_hash(self):
        return hashlib.sha256(self.rp_id.encode()).digest()

    def attestation(self, challenge: str) -> dict:
        n = self.key.public_key().public_numbers()
        cose = _cbor({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})
        auth = (self._rp_hash() + bytes([0x45]) + (0).to_bytes(4, "big") + bytes(16)
                + len(self.cred_id).to_bytes(2, "big") + self.cred_id + cose)
        cdj = json.dumps({"type": "webauthn.create", "challenge": challenge, "origin": ORIGIN,
                          "crossOrigin": False}).encode()
        return {"credentialId": _b64(self.cred_id), "rawId": _b64(self.cred_id),
                "attestationObject": _b64(_cbor({"fmt": "none", "attStmt": {}, "authData": auth})),
                "clientDataJson": _b64(cdj), "transports": "internal"}

    def prf(self, salt: bytes) -> bytes:
        """WebAuthn PRF emulation (hmac-secret): a 32-byte secret only this passkey can produce for a
        salt. The person's agent derives its vault and per-trade keys from it, like a device would."""
        import hmac
        secret = hashlib.sha256(b"agentrail-prf|" + self.key.private_numbers().private_value.to_bytes(32, "big")).digest()
        return hmac.new(secret, salt, hashlib.sha256).digest()

    def assertion(self, challenge: str) -> dict:
        self.count = max(self.count + 1, int(time.time() * 10) & 0x7FFFFFFF)
        auth = self._rp_hash() + bytes([0x05]) + self.count.to_bytes(4, "big")
        cdj = json.dumps({"type": "webauthn.get", "challenge": challenge, "origin": ORIGIN,
                          "crossOrigin": False}).encode()
        sig = self.key.sign(auth + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
        return {"credentialId": _b64(self.cred_id), "rawId": _b64(self.cred_id),
                "authenticatorData": _b64(auth), "clientDataJson": _b64(cdj), "signature": _b64(sig)}


class DevLaneApproval:
    """Approval on a UniQdata server's dev lane (synthetic QA accounts): instead of a device passkey,
    the account password is re-confirmed for each exact request (`dev-action-preflight`). The password
    stays in this process's memory only; it is never logged or written."""

    def __init__(self, password: str):
        self._password = password

    def proof(self, client: "UniQdataClient", method: str, path: str, params, content: bytes | None) -> tuple[str, str]:
        pairs = sorted([[k, str(v)] for k, v in (params or {}).items()])
        q = hashlib.sha256(json.dumps(pairs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        r = client.http.post(client.base + "/auth/identity-authority/dev-action-preflight", json={
            "method": method, "path": "/api/v1" + path, "query_sha256": q,
            "body_sha256": hashlib.sha256(content or b"").hexdigest(), "dev_password": self._password})
        if r.status_code >= 400:
            raise RuntimeError(f"UniQdata dev-lane approval refused -> {r.status_code}: {r.text[:200]}")
        att = r.json()["attestation"]
        return att["actionId"], _b64(json.dumps({"devSessionProof": att["devSessionProof"]}).encode())


class UniQdataClient:
    """The person's side of UniQdata: write records, list what is held, read rows back. Each sensitive
    request is approved by the person's software passkey (local sandbox) or, on a server's dev lane,
    by re-confirming the QA account password (DevLaneApproval)."""

    def __init__(self, base_url: str, token: str, passkey: "SoftPasskey | DevLaneApproval | None",
                 email: str | None = None):
        self.base = base_url.rstrip("/") + "/api/v1"
        self.passkey = passkey
        self.token = token
        self.email = email
        self.http = httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}",
                                                      "X-App-Id": "uniqdata-auth"})

    def _call(self, method: str, path: str, body=None, params=None) -> dict:
        """Send once; when UniQdata asks for a passkey approval of this exact request, sign its
        challenge and resend the same bytes with the assertion."""
        content = json.dumps(body).encode() if body is not None else None
        hdr = {"content-type": "application/json"} if content else {}
        # a just-issued session can read as unverified for a moment (503); writes are rate-limited (429)
        for wait in (0.5, 1, 2, 4, 7, 7, 7, 7, 7, 7, 7, 7, 0):
            r = self.http.request(method, self.base + path, content=content, params=params, headers=hdr)
            if r.status_code not in (429, 503) or not wait:
                break
            time.sleep(wait)
        detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
        if r.status_code in (401, 428) and isinstance(detail, dict) and detail.get("attestation"):
            if isinstance(self.passkey, DevLaneApproval):
                action_id, proof = self.passkey.proof(self, method, path, params, content)
            else:
                opt = detail["attestation"]
                action_id = opt["actionId"]
                proof = _b64(json.dumps(self.passkey.assertion(opt["challenge"])).encode())
            r = self.http.request(method, self.base + path, content=content, params=params,
                                  headers={**hdr, ACTION_ID_HEADER: action_id, ASSERTION_HEADER: proof})
        if r.status_code >= 400:
            raise RuntimeError(f"UniQdata {method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

    def approve_consent(self, consent_id: str) -> dict:
        """UniQdata's consent-signing ceremony: the challenge is derived from the consent's own hash,
        the passkey signs it, UniQdata verifies and stores the signature with that consent."""
        opt = self._call("POST", f"/consents/{consent_id}/attestation/options", {})
        a = self.passkey.assertion(opt["challenge"])
        return self._call("POST", f"/consents/{consent_id}/approve",
                          {"passkey_assertion": {"challengeId": opt.get("challengeId"), **a}})

    # ---- the six calls the engine's passkey approval (agentrail/security/passkey.py) relays ----

    def passkey_register_options(self) -> dict:
        """PublicKeyCredentialCreationOptions for the person's own device passkey (Touch ID). When the
        person's agent already holds a passkey, UniQdata's managed path adds this one as a second
        passkey, approved by the existing one."""
        if self.passkey is not None:
            return self._call("POST", "/auth/passkeys/register/options", {"device_name": "Touch ID (participant page)"})
        return self._call("POST", "/auth/passkey/register/options", {"email": self.email})

    def passkey_register_complete(self, body: dict) -> dict:
        path = "/auth/passkeys/register/complete" if self.passkey is not None else "/auth/passkey/register/complete"
        out = self._call("POST", path, {"device_name": "Touch ID (participant page)", **body})
        if out.get("access_token"):                 # UniQdata issues a passkey-level session
            self.token = out["access_token"]
            self.http.headers["Authorization"] = f"Bearer {self.token}"
        self._credential_ids = [out.get("credential_id")]
        return {"credential_id": out.get("credential_id")}

    def passkey_registered(self) -> list[str]:
        """UniQdata has no list call; its session says whether a passkey is registered."""
        if getattr(self, "_credential_ids", None):
            return list(self._credential_ids)
        claims = json.loads(base64.urlsafe_b64decode(self.token.split(".")[1] + "=="))
        return ["registered"] if claims.get("passkey_registered") else []

    def consent_create_pending(self, statement: dict, statement_hash: str) -> dict:
        """A pending UniQdata consent that carries the request's statement: its consent hash (what the
        passkey ceremony signs) covers the statement hash through participation_request_id."""
        items = sorted({i.split(".")[0] for i in statement.get("items", [])}) or ["research"]
        c = self._call("POST", "/consents/", {
            "scopes": [f"health:{i}:read" for i in items], "consent_type": "app_access",
            "app_id": f"agentrail.{statement.get('study', 'study')}",
            "participation_request_id": f"agentrail-{statement_hash[:40]}"})
        return {"id": c["consent_id"], "consent_hash": c.get("consent_hash")
                or hashlib.sha256(json.dumps(c, sort_keys=True, default=str).encode()).hexdigest(),
                "participation_request_id": c.get("participation_request_id")}

    def consent_attestation_options(self, consent_id: str) -> dict:
        return self._call("POST", f"/consents/{consent_id}/attestation/options", {})

    def consent_approve(self, consent_id: str, assertion: dict) -> dict:
        out = self._call("POST", f"/consents/{consent_id}/approve", {"passkey_assertion": assertion})
        return {"status": out.get("status"), "xrpl_tx_hash": out.get("xrpl_tx_hash")}

    def write(self, records: list[dict]) -> dict:
        return self._call("POST", "/data/write/batch", {"data_points": records})

    def inventory(self) -> dict:
        return self._call("GET", "/data/inventory")

    def query(self, body: dict) -> dict:
        return self._call("POST", "/data/query", body)


def records_for(item: str, day: int, value: dict) -> list[dict]:
    """One engine reading as UniQdata write records (study day -> timestamp)."""
    at = (DAY0 + timedelta(days=day - 1)).isoformat()
    out = []
    for category, concept, field, source_type in CONCEPTS[item]:
        out.append({"category": category, "concept_id": concept, "occurred_at": at, "source_type": source_type,
                    "source_value": f"agentrail:{item}:{field}", "value_as_number": value[field]})
    return out


def synthetic_readings(pid: str, weeks: list[int], items: list[str], sources) -> list[tuple[str, int, dict]]:
    """The same synthetic readings the engine's sources would produce for this person."""
    by_item = {i: s for s in sources for i in s.items}
    out = []
    for wk in weeks:
        for it in items:
            for day in range((wk - 1) * 7 + 1, wk * 7 + 1):
                v = by_item[it].read(pid, it, day, random.Random(f"{pid}-{wk}-{it}-{day}"))
                if v is not None:
                    out.append((it, day, v))
    return out


# ---------------- the engine's personal vault, backed by UniQdata ----------------

class UniQdataReader:
    """The person's records as UniQdata returns them, indexed by (item, study day)."""

    def __init__(self, client: UniQdataClient):
        self.client = client
        self.values: dict[tuple[str, int], dict] = {}
        self.records: dict[tuple[str, int], list[dict]] = {}

    def refresh(self) -> "UniQdataReader":
        values, records, offset = {}, {}, 0
        while True:
            page = self.client.query({"limit": 1000, "offset": offset})
            for r in page["data"]:
                sv = r.get("source_value") or ""
                if not sv.startswith("agentrail:") or r.get("value_as_number") is None:
                    continue
                _, item, field = sv.split(":", 2)
                at = datetime.fromisoformat(r["occurred_at"]).replace(tzinfo=timezone.utc)
                day = (at - DAY0).days + 1
                num = float(r["value_as_number"])
                values.setdefault((item, day), {})[field] = int(num) if num.is_integer() else num
                records.setdefault((item, day), []).append({"record_id": r["record_id"],
                                                            "record_hash": r["record_hash"]})
            offset += len(page["data"])
            if not page.get("has_more") or not page["data"]:
                break
        self.values, self.records = values, records
        return self

    def value(self, item: str, day: int):
        v = self.values.get((item, day))
        if not v:
            return None
        need = [f for _, _, f, _ in CONCEPTS[item]]
        return v if all(f in v for f in need) else None


class UniQdataSource:
    """One of the person's sources (wearable, survey app, clinic export) as stored in UniQdata."""

    def __init__(self, name: str, items: list[str], reader: UniQdataReader, original):
        self.name, self.items, self.reader, self.original = name, items, reader, original

    def read(self, pid, item, day, rng):
        return self.reader.value(item, day)


def attach(pa, client: UniQdataClient) -> UniQdataReader:
    """Point a participant's vault at their UniQdata records instead of the built-in synthetic sources."""
    reader = UniQdataReader(client).refresh()
    originals = pa.vault.sources
    pa.vault.sources = [UniQdataSource(s.name, list(s.items), reader, s) for s in originals]
    pa.vault.by_item = {i: s for s in pa.vault.sources for i in s.items}
    pa.vault.uniqdata = reader
    return reader


def upload_synthetic(pa, weeks: list[int], items: list[str]) -> dict:
    """The person uploads synthetic records into UniQdata (the readings their own wearable, survey app
    and clinic export would give), then the vault re-reads what UniQdata now holds."""
    reader = pa.vault.uniqdata
    originals = [s.original for s in pa.vault.sources]
    readings = [r for r in synthetic_readings(pa.vault.person.id, weeks, items, originals)
                if reader.value(r[0], r[1]) is None]           # already stored: not written twice
    recs = [x for it, day, v in readings for x in records_for(it, day, v)]
    written = []
    for i in range(0, len(recs), 500):
        written += reader.client.write(recs[i:i + 500]).get("records", [])
    reader.refresh()
    return {"written": len(written),
            "receipts": [{"record_id": r["record_id"], "record_hash": r["record_hash"]} for r in written[:5]]}


def my_data(pa, labels: dict, weeks: list[int]) -> dict:
    """'My data': what the person's UniQdata holds, per source and item (no values)."""
    reader = pa.vault.uniqdata
    days = sorted({d for (_, d) in reader.values})
    out = []
    for s in pa.vault.sources:
        items = []
        for it in s.items:
            ds = sorted(d for (i, d) in reader.values if i == it and reader.value(it, d) is not None)
            if ds:
                items.append({"item": it, "label": labels.get(it, it), "days": len(ds),
                              "records": sum(len(reader.records[(it, d)]) for d in ds),
                              "weeks": sorted({(d - 1) // 7 + 1 for d in ds if (d - 1) // 7 + 1 in weeks})})
        out.append({"source": s.name, "items": items})
    day_iso = lambda d: (DAY0 + timedelta(days=d - 1)).date().isoformat()
    return {"system": "UniQdata", "connected": True, "base_url": reader.client.base[:-len("/api/v1")],
            "records": sum(len(v) for v in reader.records.values()),
            "period": {"from": day_iso(days[0]), "to": day_iso(days[-1])} if days else None,
            "sources": out,
            "sharing": "Stored in your UniQdata account. Nothing is shared until you approve a request."}


def provenance(pa, items: list[str], weeks: list[int]) -> dict | None:
    """UniQdata record hashes behind the rows a request would send (for the preview and the bundle)."""
    reader = getattr(pa.vault, "uniqdata", None)
    if reader is None:
        return None
    hashes = [r["record_hash"] for wk in weeks for it in items for d in range((wk - 1) * 7 + 1, wk * 7 + 1)
              for r in reader.records.get((it, d), [])]
    return {"system": "UniQdata", "records": len(hashes), "record_hashes": hashes}


CLIENT: "UniQdataClient | None" = None    # set by a launcher that signed in on a UniQdata server


def server_login(base_url: str, fixture_id: str, role: str, password: str) -> UniQdataClient:
    """Sign in a dev-lane QA fixture account on a UniQdata server; approvals re-confirm the password."""
    r = httpx.post(base_url.rstrip("/") + "/api/v1/auth/dev/qa/authenticate", timeout=30,
                   headers={"X-App-Id": "uniqdata-auth"},
                   json={"fixture_id": fixture_id, "role": role, "password": password})
    if r.status_code >= 400:
        raise RuntimeError(f"UniQdata QA sign-in refused -> {r.status_code}")
    return UniQdataClient(base_url, r.json()["access_token"], DevLaneApproval(password))


def _client(s: dict) -> UniQdataClient:
    pk = s["passkey"]
    key = SoftPasskey.from_dump(pk) if isinstance(pk, dict) else SoftPasskey.load(pk) if pk else None
    return UniQdataClient(s["base_url"], s["token"], key, s.get("email"))


def load_person(path: str) -> UniQdataClient:
    return _client(json.load(open(path)))


def load_roster(path: str) -> dict[str, UniQdataClient]:
    """pid -> client, from scripts/uniqdata_sandbox_person.py --cohort."""
    return {pid: _client(s) for pid, s in json.load(open(path)).items()}


# ---------------- the market (acts 1 and 2) reads the same UniQdata accounts ----------------

# UniQdata item:field -> market catalog column (scalar value per day; scale applied)
TO_CATALOG = {
    ("sleep.daily", "minutes"): ("sleep.daily", 1), ("activity.daily", "steps"): ("steps.daily", 1),
    ("heart_rate.daily", "resting_bpm"): ("heart_rate.daily", 1),
    ("fatigue.survey", "score_0_10"): ("fatigue.survey", 1),
    ("spo2.daily", "pct"): ("spo2.night", 1),
    ("body_temp.daily", "celsius"): ("body_temp.daily", 1), ("meal.log", "kcal"): ("meal.kcal", 1),
    ("mood.daily", "score_1_5"): ("mood.score", 2),
}
# Only daily columns: the market grades a dataset as daily series, so periodic ones (weight every few
# days, the weekly surveys) would read as mostly missing; they keep generated values there.
# Visit-based clinical columns (blood pressure, labs, PHQ-9) and T3 stay on the engine side in the
# market: the catalog trades them as daily series, while a UniQdata account holds a few visits.


def feed_market(accounts, clients: dict) -> dict:
    """Replace the generated rows of each account's health datasets with what that person's UniQdata
    account actually holds, column by column, so the pre-trade quality check sees that person's real
    completeness and bad records. Columns the account does not store at all keep their generated
    values and are labelled so (meta["source"]). Returns {pid: records used}."""
    from .market import quality
    used = {}
    for a in accounts:
        client = clients.get(a.id)
        if client is None:
            continue
        reader = UniQdataReader(client).refresh()
        by_col = {}
        for (item, day), vals in reader.values.items():
            for field_, v in vals.items():
                tgt = TO_CATALOG.get((item, field_))
                if tgt and isinstance(v, (int, float)):
                    by_col[(tgt[0], day)] = round(v * tgt[1], 3)
        n_used = 0
        held = {c for (c, _) in by_col}
        for ds in a.datasets:
            # columns this person's UniQdata account holds come from it; the rest keep generated values
            cols = [c for c in ds.columns if c in held]
            if not cols or ds.meta.get("rows") is not None:
                continue
            rows = []
            for d in range(len(ds.rows) or ds.weeks * 7):
                r = {"day": d}
                for c in ds.columns:
                    r[c] = by_col.get((c, d + 1)) if c in cols else (ds.rows[d].get(c) if d < len(ds.rows) else None)
                    n_used += r[c] is not None and c in cols
                rows.append(r)
            ds.rows, ds.fault = rows, None          # UniQdata's own bad records replace injected faults
            ds.salts = [hashlib.sha256(f"{ds.id}|uq|{i}".encode()).hexdigest()[:16] for i in range(len(rows))]
            ds.shown = quality.Committed(rows, ds.salts)
            ds.meta["source"] = {c: ("UniQdata" if c in cols else "generated") for c in ds.columns}
        used[a.id] = n_used
    return used


def market_clients() -> dict:
    """pid -> client from UNIQDATA_ROSTER, or {} when the market runs on generated data."""
    path = os.environ.get("UNIQDATA_ROSTER")
    return load_roster(path) if path else {}
