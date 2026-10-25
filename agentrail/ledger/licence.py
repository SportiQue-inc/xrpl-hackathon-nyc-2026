"""Per-(study, participant) data licence as an XRPL Multi-Purpose Token (MPT).

The participant's agent is the issuer. One issuance per study, maximum supply 1:
- RequireAuth: only the study the participant authorized can hold it;
- no CanTransfer: the study cannot pass it on (no onward transfer);
- CanClawback: on revoke the participant takes it back.
Metadata holds only the study, DUO codes and the consent document hash; no health data.
The study's delivery gate checks that it still holds the licence.
"""
from __future__ import annotations

import json

from xrpl.models.amounts import MPTAmount
from xrpl.models.requests import GenericRequest
from xrpl.models.transactions import (Clawback, MPTokenAuthorize, MPTokenIssuanceCreate,
                                      MPTokenIssuanceCreateFlag as F, Payment)

from .xrpl_extras import _check, submit_capture
from .xrpl_ledger import submit_and_wait  # resyncs the local sequence cache

LICENCE_FLAGS = F.TF_MPT_REQUIRE_AUTH | F.TF_MPT_CAN_CLAWBACK


def licence_metadata(study: str, duo: list[str], consent_hash: str) -> str:
    import hashlib
    # The study is referenced by hash only: no study names or conditions on the ledger.
    return json.dumps({"t": "agentrail.licence/v1", "study": hashlib.sha256(study.encode()).hexdigest()[:16], "duo": duo,
                       "consent": consent_hash[:32]}, separators=(",", ":"), sort_keys=True)


class XrplLicenceMixin:
    def issue_licence(self, issuer: str, holder: str, metadata: str) -> tuple[str, list[str]]:
        r = submit_and_wait(MPTokenIssuanceCreate(
            account=issuer, maximum_amount="1", flags=LICENCE_FLAGS,
            mptoken_metadata=metadata.encode().hex().upper()), self.client, self.wallets[issuer])
        h1 = _check(r, "MPTokenIssuanceCreate")
        mpt_id = r.result.get("meta", {}).get("mpt_issuance_id") or r.result.get("mpt_issuance_id")
        if not mpt_id:
            seq = r.result.get("tx_json", {}).get("Sequence") or r.result.get("Sequence")
            from xrpl.core.addresscodec import decode_classic_address
            mpt_id = (int(seq).to_bytes(4, "big") + decode_classic_address(issuer)).hex().upper()
        h2 = _check(submit_and_wait(MPTokenAuthorize(account=holder, mptoken_issuance_id=mpt_id),
                                    self.client, self.wallets[holder]), "MPTokenAuthorize (holder)")
        h3 = _check(submit_and_wait(MPTokenAuthorize(account=issuer, mptoken_issuance_id=mpt_id, holder=holder),
                                    self.client, self.wallets[issuer]), "MPTokenAuthorize (issuer)")
        h4 = _check(submit_and_wait(Payment(account=issuer, destination=holder,
                                            amount=MPTAmount(mpt_issuance_id=mpt_id, value="1")),
                                    self.client, self.wallets[issuer]), "MPT Payment")
        return mpt_id, [h1, h2, h3, h4]

    def licence_held(self, holder: str, mpt_id: str) -> bool:
        marker, ledger_index, seen = None, "validated", set()
        while True:
            response = self.client.request(GenericRequest(method="account_objects", account=holder, type="mptoken",
                ledger_index=ledger_index, **({"marker": marker} if marker is not None else {})))
            r = response.result
            if (not response.is_successful() or r.get("validated") is not True or r.get("account") != holder
                    or type(r.get("ledger_index")) is not int or not isinstance(r.get("account_objects"), list)
                    or (ledger_index != "validated" and r["ledger_index"] != ledger_index)):
                raise RuntimeError("Validated licence status is unavailable")
            if any(o.get("MPTokenIssuanceID", "").upper() == mpt_id.upper() and int(o.get("MPTAmount", "0")) > 0
                   for o in r["account_objects"]):
                return True
            marker = r.get("marker")
            if marker is None:
                return False
            key = json.dumps(marker, sort_keys=True)
            if key in seen:
                raise RuntimeError("Licence pagination did not advance")
            seen.add(key)
            ledger_index = r["ledger_index"]

    def licence_metadata_of(self, mpt_id: str) -> str | None:
        """The licence terms as written on the ledger (MPTokenMetadata of the issuance)."""
        r = self.client.request(GenericRequest(method="ledger_entry", mpt_issuance=mpt_id,
                                               ledger_index="validated")).result
        hx = r.get("node", {}).get("MPTokenMetadata")
        return bytes.fromhex(hx).decode() if hx else None

    def clawback_licence(self, issuer: str, holder: str, mpt_id: str) -> str:
        return _check(submit_and_wait(Clawback(account=issuer, holder=holder,
                                               amount=MPTAmount(mpt_issuance_id=mpt_id, value="1")),
                                      self.client, self.wallets[issuer]), "Clawback")

    def transfer_licence(self, holder: str, to: str, mpt_id: str) -> str:
        """Used only to show the ledger refusing onward transfer. Returns the result code;
        the failed tx hash is kept in self.last_tx_hash (submit_and_wait raises on tec codes)."""
        h, code, _ = submit_capture(self.client, Payment(account=holder, destination=to,
                                                         amount=MPTAmount(mpt_issuance_id=mpt_id, value="1")),
                                    self.wallets[holder])
        self.last_tx_hash = h
        return code
