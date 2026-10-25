"""XRPL-native controls used around the agents:

- Credentials (XLS-70): an ethics board issues "ethics review approved" to a buyer;
  sensitive items are released only if the ledger shows an accepted credential.
- KYB deposit gate: a participant account turns on DepositAuth and preauthorizes the
  VERIFIED_ORG credential (DepositPreauth with AuthorizeCredentials). A Payment from an
  org that does not carry a matching CredentialIDs entry fails on the ledger with
  tecNO_PERMISSION. EscrowCreate is not gated by DepositAuth; EscrowFinish is, unless
  the destination itself submits it.
- Multi-signing: the buyer's treasury is controlled by a SignerList (human owner +
  compliance officer), master key disabled. The agent spends from its own capped
  account; topping it up needs the human co-signatures.
"""
from __future__ import annotations

import time

from xrpl.core.binarycodec import encode
from xrpl.models.requests import AccountInfo, AccountTx, GenericRequest, SubmitOnly, Tx
from xrpl.models.transactions import (AccountSet, AccountSetAsfFlag, CredentialAccept, CredentialCreate,
                                      DepositPreauth, Payment, SignerEntry, SignerListSet)
from xrpl.models.transactions.deposit_preauth import Credential
from xrpl.transaction import autofill, autofill_and_sign, multisign, sign
from xrpl.wallet import Wallet
from .xrpl_ledger import submit_and_wait  # resyncs the local sequence cache

LSF_ACCEPTED = 0x00010000
LSF_DISABLE_MASTER = 0x00100000
LSF_DEPOSIT_AUTH = 0x01000000


def _hex(s: str) -> str:
    return s.encode().hex().upper()


def _check(resp, what: str) -> str:
    r = resp.result
    code = r.get("meta", {}).get("TransactionResult")
    if code != "tesSUCCESS":
        raise RuntimeError(f"{what} failed: {code or r}")
    return r.get("hash") or r.get("tx_json", {}).get("hash")


def submit_capture(client, tx, wallet, timeout: float = 90.0) -> tuple[str, str, dict]:
    """Sign, submit and wait for a validated result without raising on tec codes,
    so failed transactions keep their hash (submit_and_wait raises and loses it).
    Returns (hash, result code, tx result). tem/tef/tel never reach a ledger."""
    signed = autofill_and_sign(tx, client, wallet)
    h = signed.get_hash()
    from .xrpl_ledger import _LEDGERS
    for led in _LEDGERS:                       # autofilled from the ledger: drop any cached counter
        with led._seq_lock:
            led._seq.pop(tx.account, None)
    r = client.request(SubmitOnly(tx_blob=encode(signed.to_xrpl()))).result
    prelim = r.get("engine_result", "")
    if prelim.startswith(("tem", "tef", "tel")):
        return h, prelim, r
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(1.5)
        t = client.request(Tx(transaction=h)).result
        if t.get("validated"):
            return h, t.get("meta", {}).get("TransactionResult"), t
    return h, f"timeout({prelim})", r


class XrplExtrasMixin:
    def _past_hashes(self, account: str, wanted: list[str], match=lambda tx: True) -> list[str]:
        """Hashes of earlier successful txs of the given types (re-runs reuse wallets.local.json)."""
        # Oldest first: setup txs sit at the start of an account's history, which grows by
        # hundreds of payments per run (the newest-200 window lost them after a few runs).
        found: dict[str, str] = {}
        marker = None
        for _ in range(20):
            r = self.client.request(AccountTx(account=account, limit=200, forward=True, marker=marker)).result
            for t in r.get("transactions", []):
                tx = t.get("tx_json") or t.get("tx") or {}
                ty = tx.get("TransactionType")
                if (ty in wanted and ty not in found and match(tx)
                        and t.get("meta", {}).get("TransactionResult") == "tesSUCCESS"):
                    found[ty] = t.get("hash") or tx.get("hash")
            marker = r.get("marker")
            if len(found) == len(wanted) or not marker:
                break
        return [found[ty] for ty in wanted if ty in found]

    def new_keypair(self, label: str) -> str:
        """Unfunded key (signer entries do not need to be funded accounts)."""
        if label in self._labels:
            w = Wallet.from_seed(self._labels[label])
        else:
            w = Wallet.create()
            self._labels[label] = w.seed
            self._save()
        self.wallets[w.classic_address] = w
        return w.classic_address

    # ---------- credentials ----------

    def issue_credential(self, issuer: str, subject: str, cred_type: str) -> list[str]:
        self.__dict__.pop("_cred_cache", None)
        if self.has_credential(subject, issuer, cred_type):
            return self._past_hashes(subject, ["CredentialCreate", "CredentialAccept"],
                                     lambda tx: tx.get("CredentialType", "").upper() == _hex(cred_type))
        h1 = _check(submit_and_wait(CredentialCreate(account=issuer, subject=subject,
                                                     credential_type=_hex(cred_type)),
                                    self.client, self.wallets[issuer]), "CredentialCreate")
        h2 = _check(submit_and_wait(CredentialAccept(account=subject, issuer=issuer,
                                                     credential_type=_hex(cred_type)),
                                    self.client, self.wallets[subject]), "CredentialAccept")
        return [h1, h2]

    def has_credential(self, subject: str, issuer: str, cred_type: str) -> bool:
        """Cached for a few seconds: 50 participants' agents check the same lab in one round, and a
        positive answer does not change between ledgers unless the issuer deletes it."""
        import time
        cache = self.__dict__.setdefault("_cred_cache", {})
        k = (subject, issuer, cred_type)
        hit = cache.get(k)
        if hit and time.monotonic() - hit[1] < float(__import__("os").environ.get("XRPL_CRED_CACHE_S", "10")):
            return hit[0]
        ok = self._has_credential(subject, issuer, cred_type)
        cache[k] = (ok, time.monotonic())
        return ok

    def _has_credential(self, subject: str, issuer: str, cred_type: str) -> bool:
        r = self.client.request(GenericRequest(method="account_objects", account=subject,
                                               type="credential", ledger_index="validated")).result
        for o in r.get("account_objects", []):
            if (o.get("Issuer") == issuer and o.get("Subject") == subject
                    and o.get("CredentialType", "").upper() == _hex(cred_type)
                    and int(o.get("Flags", 0)) & LSF_ACCEPTED):
                return True
        return False

    def credential_id(self, subject: str, issuer: str, cred_type: str) -> str | None:
        """Ledger index of the accepted credential; this is what CredentialIDs carries."""
        r = self.client.request(GenericRequest(method="account_objects", account=subject,
                                               type="credential", ledger_index="validated")).result
        for o in r.get("account_objects", []):
            if (o.get("Issuer") == issuer and o.get("Subject") == subject
                    and o.get("CredentialType", "").upper() == _hex(cred_type)
                    and int(o.get("Flags", 0)) & LSF_ACCEPTED):
                return o["index"]
        return None

    def require_credential_deposits(self, account: str, issuer: str, cred_type: str) -> list[str]:
        """DepositAuth on `account` + DepositPreauth for (issuer, cred_type). Idempotent."""
        info = self.client.request(AccountInfo(account=account, ledger_index="validated")).result
        flag_set = bool(int(info.get("account_data", {}).get("Flags", 0)) & LSF_DEPOSIT_AUTH)
        rule = (issuer, _hex(cred_type))
        have = rule in self._deposit_rules(account, refresh=True)
        hashes = []
        if flag_set and have:
            return self._past_hashes(account, ["AccountSet", "DepositPreauth"],
                                     lambda tx: tx.get("TransactionType") == "DepositPreauth"
                                     or tx.get("SetFlag") == AccountSetAsfFlag.ASF_DEPOSIT_AUTH.value)
        w = self.wallets[account]
        if not flag_set:
            hashes.append(_check(submit_and_wait(AccountSet(account=account,
                                                            set_flag=AccountSetAsfFlag.ASF_DEPOSIT_AUTH),
                                                 self.client, w), "AccountSet DepositAuth"))
        if not have:
            hashes.append(_check(submit_and_wait(DepositPreauth(
                account=account, authorize_credentials=[Credential(issuer=issuer, credential_type=_hex(cred_type))]),
                self.client, w), "DepositPreauth"))
        self._deposit_rules(account, refresh=True)
        return hashes

    # ---------- multi-signing ----------

    def setup_multisig(self, account: str, signers: list[str], quorum: int) -> list[str]:
        info = self.client.request(AccountInfo(account=account, ledger_index="validated",
                                               signer_lists=True)).result
        flags = int(info.get("account_data", {}).get("Flags", 0))
        lists = info.get("signer_lists") or info.get("account_data", {}).get("signer_lists") or []
        current = {e["SignerEntry"]["Account"] for e in (lists[0]["SignerEntries"] if lists else [])}
        if flags & LSF_DISABLE_MASTER and current == set(signers) and lists[0]["SignerQuorum"] == quorum:
            return self._past_hashes(account, ["SignerListSet", "AccountSet"])
        w = self.wallets[account]
        h1 = _check(submit_and_wait(SignerListSet(
            account=account, signer_quorum=quorum,
            signer_entries=[SignerEntry(account=s, signer_weight=1) for s in signers]),
            self.client, w), "SignerListSet")
        h2 = _check(submit_and_wait(AccountSet(account=account, set_flag=AccountSetAsfFlag.ASF_DISABLE_MASTER),
                                    self.client, w), "AccountSet disable master")
        return [h1, h2]

    def multisig_payment(self, source: str, destination: str, amount_drops: int,
                         signers: list[str], memo: str = "") -> str:
        tx = autofill(Payment(account=source, destination=destination, amount=str(amount_drops)),
                      self.client, signers_count=len(signers))
        signed = [sign(tx, self.wallets[s], multisign=True) for s in signers]
        return _check(submit_and_wait(multisign(tx, signed), self.client, autofill=False),
                      "multisigned Payment")
