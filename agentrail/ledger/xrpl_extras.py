"""XRPL-native controls used around the agents:

- Credentials (XLS-70): an ethics board issues "ethics review approved" to a buyer;
  sensitive items are released only if the ledger shows an accepted credential.
- Multi-signing: the buyer's treasury is controlled by a SignerList (human owner +
  compliance officer), master key disabled. The agent spends from its own capped
  account; topping it up needs the human co-signatures.
"""
from __future__ import annotations

from xrpl.models.requests import GenericRequest
from xrpl.models.transactions import (AccountSet, AccountSetAsfFlag, CredentialAccept, CredentialCreate,
                                      Payment, SignerEntry, SignerListSet)
from xrpl.transaction import autofill, multisign, sign, submit_and_wait
from xrpl.wallet import Wallet

LSF_ACCEPTED = 0x00010000


def _hex(s: str) -> str:
    return s.encode().hex().upper()


def _check(resp, what: str) -> str:
    r = resp.result
    code = r.get("meta", {}).get("TransactionResult")
    if code != "tesSUCCESS":
        raise RuntimeError(f"{what} failed: {code or r}")
    return r.get("hash") or r.get("tx_json", {}).get("hash")


class XrplExtrasMixin:
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
        h1 = _check(submit_and_wait(CredentialCreate(account=issuer, subject=subject,
                                                     credential_type=_hex(cred_type)),
                                    self.client, self.wallets[issuer]), "CredentialCreate")
        h2 = _check(submit_and_wait(CredentialAccept(account=subject, issuer=issuer,
                                                     credential_type=_hex(cred_type)),
                                    self.client, self.wallets[subject]), "CredentialAccept")
        return [h1, h2]

    def has_credential(self, subject: str, issuer: str, cred_type: str) -> bool:
        r = self.client.request(GenericRequest(method="account_objects", account=subject,
                                               type="credential", ledger_index="validated")).result
        for o in r.get("account_objects", []):
            if (o.get("Issuer") == issuer and o.get("Subject") == subject
                    and o.get("CredentialType", "").upper() == _hex(cred_type)
                    and int(o.get("Flags", 0)) & LSF_ACCEPTED):
                return True
        return False

    # ---------- multi-signing ----------

    def setup_multisig(self, account: str, signers: list[str], quorum: int) -> list[str]:
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
