"""Treasury approvals signed by each approver on their own device.

The server never holds an approver key. A researcher opens an approval for the current spec; it fixes
treasury, destination, amount, spec hash, a nonce and an expiry (and on XRPL the exact unsigned
transaction, LastLedgerSequence included). Each approver signs it on their device and posts the
signature with their own token. The server checks that

  - the approval is open and not expired, and the signature is over exactly this approval,
  - the signing key is the one on the treasury's SignerList for that approver's name,
  - each approver name and each person signs at most once, and
  - one spec gets at most one approval.

With quorum the server combines the signatures and submits; the ledger checks them again
(SignerList, quorum, master key disabled). A single signature is never submitted except by the demo
harness to show the ledger's own refusal.
"""
from __future__ import annotations

import json
import secrets as pysecrets
import time

from .devices import approval_message, mock_address, verify_ed25519

APPROVAL_TTL_S = 600
QUORUM = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, study TEXT NOT NULL, treasury TEXT NOT NULL, destination TEXT NOT NULL,
  amount_drops INTEGER NOT NULL, spec_hash TEXT NOT NULL UNIQUE, nonce TEXT NOT NULL, expires_at REAL NOT NULL,
  tx_json TEXT, status TEXT NOT NULL, result TEXT, tx_hash TEXT, created_by TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_signatures (
  approval_id INTEGER NOT NULL, signer_name TEXT NOT NULL, signer_address TEXT NOT NULL,
  approver_sub TEXT NOT NULL, payload TEXT NOT NULL, ts REAL NOT NULL,
  PRIMARY KEY (approval_id, signer_name), UNIQUE (approval_id, approver_sub)
);
"""


class ApprovalError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _row(store, aid):
    r = store.one("SELECT * FROM approvals WHERE id=?", aid)
    if r is None:
        raise KeyError(aid)
    return r


def view(store, aid: int) -> dict:
    r = dict(_row(store, aid))
    r["tx_json"] = json.loads(r["tx_json"]) if r["tx_json"] else None
    r["signatures"] = [{"signer": x["signer_name"], "approver": x["approver_sub"], "ts": x["ts"]} for x in
                       store.q("SELECT * FROM approval_signatures WHERE approval_id=? ORDER BY ts", aid)]
    r["quorum"] = QUORUM
    return r


def open_approval(w, created_by: str) -> dict:
    """The study's budget for its current draft spec."""
    from ..study import LAB, ensure
    s = ensure(w)
    if s.status != "draft" or not s.needs:
        raise ApprovalError(409, "no draft spec to approve")
    return open_for(w, LAB, s.treasury, s.needs.budget_drops, f"{s.needs.proposal_hash}:{s.needs.budget_drops}",
                    created_by)


def open_for(w, buyer: str, treasury: str, amount: int, spec_hash: str, created_by: str) -> dict:
    """An approval to pay `amount` drops from a multi-signed treasury to the buyer's agent account."""
    st = w.store
    ex = st.one("SELECT id, status, expires_at FROM approvals WHERE spec_hash=?", spec_hash)
    if ex and ex["status"] == "open" and ex["expires_at"] > time.time():
        return view(st, ex["id"])
    if ex and ex["status"] == "executed":
        raise ApprovalError(409, "this spec was already approved; a new budget needs a new spec")
    if ex:   # expired or refused: a fresh approval with a fresh nonce replaces it
        with st.tx() as c:
            c.execute("DELETE FROM approval_signatures WHERE approval_id=?", (ex["id"],))
            c.execute("DELETE FROM approvals WHERE id=?", (ex["id"],))
    dest = w.engine.party(buyer)["address"]
    nonce, exp = pysecrets.token_hex(16), time.time() + APPROVAL_TTL_S
    tx_json = _unsigned_tx(w.ledger, treasury, dest, amount, spec_hash, nonce)
    with st.tx() as c:
        cur = c.execute("INSERT INTO approvals (study,treasury,destination,amount_drops,spec_hash,nonce,expires_at,"
                        "tx_json,status,created_by,ts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (buyer, treasury, dest, amount, spec_hash, nonce, exp,
                         json.dumps(tx_json) if tx_json else None, "open", created_by, time.time()))
        aid = cur.lastrowid
    st.log(buyer, "approval_open", f"{created_by} asked the approvers to release {amount / 1e6:g} XRP "
           f"for spec {spec_hash[:12]}; each approver signs on their own device (expires in "
           f"{APPROVAL_TTL_S // 60} min)", {"approval": aid})
    return view(st, aid)


def _unsigned_tx(ledger, treasury, dest, amount, spec_hash, nonce):
    if ledger.name != "testnet":
        return None
    from xrpl.ledger import get_latest_validated_ledger_sequence
    from xrpl.models.transactions import Memo, Payment
    from xrpl.transaction import autofill
    lls = get_latest_validated_ledger_sequence(ledger.client) + 200      # about 10 minutes to sign
    tx = autofill(Payment(account=treasury, destination=dest, amount=str(amount), last_ledger_sequence=lls,
                          memos=[Memo(memo_type=b"agentrail/approval".hex().upper(),
                                      memo_data=f"spec:{spec_hash[:32]}|nonce:{nonce}".encode().hex().upper())]),
                  ledger.client, signers_count=QUORUM)
    return tx.to_xrpl()


def add_signature(w, aid: int, approver_sub: str, signer_name: str, payload: dict) -> dict:
    st = w.store
    a = _row(st, aid)
    if a["status"] != "open":
        raise ApprovalError(409, f"approval is {a['status']}")
    if a["expires_at"] < time.time():
        with st.tx() as c:
            c.execute("UPDATE approvals SET status='expired' WHERE id=?", (aid,))
        raise ApprovalError(410, "approval expired; open a new one")
    signers = w.security.signer_lists.get(a["treasury"], {})
    if signer_name not in signers:
        raise ApprovalError(403, f"{signer_name} is not on the treasury's signer list")
    address = signers[signer_name]
    if not _valid(w.ledger, view(st, aid), address, payload):
        raise ApprovalError(400, "signature is not by this approver's key over this approval")
    try:
        with st.tx() as c:
            c.execute("INSERT INTO approval_signatures VALUES (?,?,?,?,?,?)",
                      (aid, signer_name, address, approver_sub, json.dumps(payload), time.time()))
    except Exception:
        raise ApprovalError(409, "this approver (or this signer name) already signed this approval")
    st.log(a["study"], "approval_signed",
           f"{approver_sub} signed approval {aid} as {signer_name} on their device", {"approval": aid})
    n = st.one("SELECT COUNT(*) n FROM approval_signatures WHERE approval_id=?", aid)["n"]
    if n >= QUORUM:
        return execute(w, aid)
    return {"ok": True, "status": "open", "signed": n, "quorum": QUORUM, **view(st, aid)}


def _valid(ledger, a: dict, address: str, payload: dict) -> bool:
    if ledger.name != "testnet":
        pub = payload.get("public_key", "")
        return (payload.get("signer") == address and mock_address(pub) == address
                and verify_ed25519(pub, approval_message(a), payload.get("signature", "")))
    from xrpl.core.addresscodec import is_valid_classic_address
    from xrpl.core.binarycodec import encode_for_multisigning
    from xrpl.core.keypairs import derive_classic_address, is_valid_message
    signed = payload.get("signed_tx") or {}
    sig_entries = signed.get("Signers") or []
    if len(sig_entries) != 1 or not is_valid_classic_address(address):
        return False
    e = sig_entries[0]["Signer"]
    # Multi-signing signs the tx with an empty SigningPubKey; nothing else may differ.
    body = {k: v for k, v in signed.items() if k not in ("Signers", "TxnSignature")}
    want = {**{k: v for k, v in a["tx_json"].items() if k not in ("Signers", "TxnSignature")}, "SigningPubKey": ""}
    if body != want or e.get("Account") != address:
        return False
    try:
        return (derive_classic_address(e["SigningPubKey"]) == address and
                is_valid_message(bytes.fromhex(encode_for_multisigning(want, address)),
                                 bytes.fromhex(e["TxnSignature"]), e["SigningPubKey"]))
    except Exception:
        return False


def execute(w, aid: int, allow_short: bool = False) -> dict:
    """Combine signatures and submit. allow_short only for the demo harness's ledger-refusal check."""
    st = w.store
    a = view(st, aid)
    sigs = st.q("SELECT * FROM approval_signatures WHERE approval_id=? ORDER BY signer_name", aid)
    if len(sigs) < QUORUM and not allow_short:
        raise ApprovalError(409, f"{len(sigs)} of {QUORUM} signatures")
    response = None
    try:
        h = _submit(w.ledger, a, sigs)
        result = "tesSUCCESS"
    except LedgerRefusal as e:
        result, h, response = e.result, None, e.response
    except Exception as e:
        import re
        m = re.search(r"\b(te[cfmlr][A-Z_]+)\b", str(e))
        result, h = (m.group(1) if m else str(e)[:120]), None
    if h is None:
        # A tef refusal never enters a ledger, so the server's answer is kept as the evidence.
        st.log("org_sleeplab", "refused", f"treasury payment for approval {aid} with {len(sigs)} signature(s) "
               f"rejected by the ledger: {result}", {"ledger_response": response} if response else None)
        return {"ok": False, "engine_result": result, "signed": len(sigs), "quorum": QUORUM,
                "message": f"rejected by the ledger: {result}", "ledger_response": response}
    with st.tx() as c:
        c.execute("UPDATE approvals SET status='executed', result=?, tx_hash=? WHERE id=?", (result, h, aid))
    _apply_budget(w, a, h, [x["approver_sub"] for x in sigs])
    return {"ok": True, "status": "executed", "tx": h, "url": w.ledger.explorer_url(h), **view(st, aid)}


def _submit(ledger, a: dict, sigs) -> str:
    addrs = [x["signer_address"] for x in sigs]
    if ledger.name != "testnet":
        try:
            return ledger.multisig_payment(a["treasury"], a["destination"], a["amount_drops"], addrs)
        except RuntimeError as e:
            code, _, msg = str(e).partition(": ")
            raise LedgerRefusal(code, {"engine_result": code, "engine_result_message": msg, "accepted": False,
                                       "applied": False, "signers": len(addrs), "ledger": ledger.name})
    from xrpl.models.transactions.transaction import Transaction
    from xrpl.transaction import multisign
    from xrpl.transaction import submit
    tx = Transaction.from_xrpl(a["tx_json"])
    signed = [Transaction.from_xrpl(json.loads(x["payload"])["signed_tx"]) for x in sigs]
    ms = multisign(tx, signed)
    r = submit(ms, ledger.client).result
    if not str(r.get("engine_result", "")).startswith(("tes", "ter", "tec")):
        raise LedgerRefusal(r.get("engine_result", "?"), {k: r.get(k) for k in (
            "engine_result", "engine_result_code", "engine_result_message", "accepted", "applied")}
            | {"tx_hash": r.get("tx_json", {}).get("hash"), "signers": len(signed)})
    h = r.get("tx_json", {}).get("hash")
    st = ledger.wait_validated(h)
    if not (st.validated and st.success):
        raise RuntimeError(f"multisigned Payment {st.result}")
    return h


class LedgerRefusal(Exception):
    def __init__(self, result: str, response: dict):
        super().__init__(result)
        self.result, self.response = result, response


def _apply_budget(w, a: dict, h: str, approvers: list[str]):
    from ..policy import BuyerMandate
    from ..study import _tx
    st, e, buyer = w.store, w.engine, a["study"]
    m = st.one("SELECT * FROM mandates WHERE buyer_id=?", buyer)
    e.set_mandate(BuyerMandate(buyer, m["total_drops"] + a["amount_drops"], m["per_order_limit_drops"],
                               json.loads(m["purposes"])))
    chain = e.mandate_chains.get(buyer)
    if chain is not None:
        chain.issue_from(st.one("SELECT * FROM mandates WHERE buyer_id=?", buyer), st)
    st.log(buyer, "top_up", f"{' + '.join(approvers)} co-signed a {a['amount_drops'] / 1e6:g} XRP treasury payment "
           f"on their own devices (approval {a['id']}); mandate now {(m['total_drops'] + a['amount_drops']) / 1e6:g} XRP",
           {"tx_hash": h, "url": w.ledger.explorer_url(h)})
    s = getattr(w, "study", None)
    if s is None or a["treasury"] != s.treasury:
        return
    s.status = "approved"
    s.approval = {"signers": [x for x in s.signers if x in {r["signer_name"] for r in st.q(
        "SELECT signer_name FROM approval_signatures WHERE approval_id=?", a["id"])}],
        **_tx(w, h), "amount_xrp": a["amount_drops"] / 1e6, "approval_id": a["id"], "approvers": approvers}


def approve_with_devices(w, names: list[str], buyer: str = "org_sleeplab", opener=None) -> dict:
    """Demo harness and scripts: the named approvers' (simulated) devices sign. With fewer than the
    quorum the harness submits anyway so the ledger's own refusal is shown."""
    devices = w.security.approvers_by_org[buyer]
    unknown = [n for n in names if n not in devices]
    if unknown:
        return {"ok": False, "engine_result": "unknown_signer", "signers": names,
                "message": f"not on the treasury's signer list: {', '.join(unknown)}"}
    try:
        a = opener() if opener else open_approval(w, f"researcher@{buyer}")
    except ApprovalError as e:
        return {"ok": False, "message": str(e)}
    out = None
    done = {x["signer"] for x in a["signatures"]}
    for n in names:
        if n in done:
            continue
        d = devices[n]
        out = add_signature(w, a["id"], d.sub, n, d.cosign(view(w.store, a["id"])))
    if out and out.get("status") == "executed":
        if opener:
            return out
        from ..study import study_view
        return {"ok": True, **study_view(w)}
    r = execute(w, a["id"], allow_short=True)
    r["signers"] = names
    return r
