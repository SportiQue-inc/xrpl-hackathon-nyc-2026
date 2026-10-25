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

ORIGIN = os.environ.get("UNIQDATA_WEBAUTHN_ORIGIN", "https://app.uniqdata.io")
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
SOURCE = {"heart_rate.daily": "wearable", "sleep.daily": "wearable", "activity.daily": "wearable",
          "fatigue.survey": "survey_app", "blood_pressure.daily": "clinic_export"}
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
        self.key, self.cred_id, self.rp_id, self.count = key, cred_id, rp_id, 1

    @classmethod
    def new(cls) -> "SoftPasskey":
        return cls(ec.generate_private_key(ec.SECP256R1()), os.urandom(32))

    @classmethod
    def load(cls, path: str) -> "SoftPasskey":
        d = json.load(open(path))
        key = serialization.load_pem_private_key(d["key"].encode(), None)
        return cls(key, base64.urlsafe_b64decode(d["cred"] + "=="), d["rp_id"])

    def save(self, path: str):
        pem = self.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()).decode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"key": pem, "cred": _b64(self.cred_id), "rp_id": self.rp_id}, f)

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

    def assertion(self, challenge: str) -> dict:
        self.count += 1
        auth = self._rp_hash() + bytes([0x05]) + self.count.to_bytes(4, "big")
        cdj = json.dumps({"type": "webauthn.get", "challenge": challenge, "origin": ORIGIN,
                          "crossOrigin": False}).encode()
        sig = self.key.sign(auth + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
        return {"credentialId": _b64(self.cred_id), "rawId": _b64(self.cred_id),
                "authenticatorData": _b64(auth), "clientDataJson": _b64(cdj), "signature": _b64(sig)}


class UniQdataClient:
    """The person's side of UniQdata: write records, list what is held, read rows back."""

    def __init__(self, base_url: str, token: str, passkey: SoftPasskey):
        self.base = base_url.rstrip("/") + "/api/v1"
        self.passkey = passkey
        self.http = httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}",
                                                      "X-App-Id": "uniqdata-auth"})

    def _call(self, method: str, path: str, body=None, params=None) -> dict:
        """Send once; when UniQdata asks for a passkey approval of this exact request, sign its
        challenge and resend the same bytes with the assertion."""
        content = json.dumps(body).encode() if body is not None else None
        hdr = {"content-type": "application/json"} if content else {}
        for wait in (0.5, 1, 2, 4, 0):    # a just-issued session can read as unverified for a moment (503)
            r = self.http.request(method, self.base + path, content=content, params=params, headers=hdr)
            if r.status_code != 503 or not wait:
                break
            time.sleep(wait)
        detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
        if r.status_code in (401, 428) and isinstance(detail, dict) and detail.get("attestation"):
            opt = detail["attestation"]
            proof = _b64(json.dumps(self.passkey.assertion(opt["challenge"])).encode())
            r = self.http.request(method, self.base + path, content=content, params=params,
                                  headers={**hdr, ACTION_ID_HEADER: opt["actionId"], ASSERTION_HEADER: proof})
        if r.status_code >= 400:
            raise RuntimeError(f"UniQdata {method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

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


def load_person(path: str) -> UniQdataClient:
    s = json.load(open(path))
    return UniQdataClient(s["base_url"], s["token"], SoftPasskey.load(s["passkey"]))
