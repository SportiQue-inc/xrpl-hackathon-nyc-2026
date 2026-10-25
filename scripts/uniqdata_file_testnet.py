"""Resident Testnet operator for one main-UniQdata file contribution.

Run on the resident host, with the Core command on a local private pipe. The
participant uses the main app and existing passkey; this tool cannot approve or
withdraw their consent. Treasury approvers are separate simulated test devices,
not evidence of two humans. Only public commitments and Testnet receipts print.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

from x402_xrpl.vi import public_jwk_from_private_jwk

from agentrail.db import Store
from agentrail.engine import Engine, canonical
from agentrail.mandate import MandateChain
from agentrail.policy import BuyerMandate
from agentrail.security import cosign
from agentrail.security.devices import ApproverDevice, InstitutionVault, ParticipantKeyring
from agentrail.security.keystore import LocalKeyStore
from agentrail.uniqdata_contribution import ContributionBridge, PURPOSE, ResidentCore

BUYER = "uniqdata-file-testnet"
AMOUNT = 1_000_000
RPC = "https://s.altnet.rippletest.net:51234/"


class FileCase:
    def __init__(self, root: Path, ledger):
        self.root, self.ledger = root, ledger
        self.keys = lambda owner: LocalKeyStore(owner, str(root / "keys"))
        self.saved = self.keys("case")
        self.recipient = InstitutionVault(BUYER, self.keys("institution"))
        self.store = Store(str(root / "orders.db"))
        self.store.conn.executescript(cosign.SCHEMA)
        self.engine = Engine(self.store, ledger)
        self.approvers = {name: ApproverDevice("test-device-" + name, ledger.name, self.keys("approver-" + name))
                          for name in ("a", "b")}

    def prepare(self):
        """Separate Testnet wallets and a finite quote; no account/consent changes."""
        saved = self.saved.get("offer.json")
        if saved:
            return json.loads(saved)
        payer = self.ledger.new_account("payer")
        payee = self.ledger.new_account("payee")
        treasury = self.ledger.new_account("treasury")
        self.ledger.setup_multisig(treasury, [device.address for device in self.approvers.values()], 2)
        value = {"network": "xrpl-testnet", "currency": "XRP", "amount_drops": AMOUNT,
                 "payer_address": payer, "payee_address": payee,
                 "recipient_key_sha256": hashlib.sha256(bytes.fromhex(self.recipient.public_hex)).hexdigest(),
                 "request_ref": "file-testnet-" + uuid.uuid4().hex}
        self.saved.get_or_create("treasury", lambda: treasury.encode())
        return json.loads(self.saved.get_or_create("offer.json", lambda: canonical(value).encode()))

    def _bridge(self, source):
        saved = self.saved.get("offer.json")
        if not saved:
            raise PermissionError("Prepare the Testnet case and main-app offer first")
        info, current = json.loads(saved), source.call("inspect")
        if current["settlement"] != info:
            raise PermissionError("Contribution does not match this exact Testnet case")
        binding = canonical({key: current[key] for key in ("submission_ref", "consent_ref", "binding_sha256")}).encode()
        if self.saved.get_or_create("binding.json", lambda: binding) != binding:
            raise PermissionError("Case is already bound to another original contribution")
        self.engine.add_party(BUYER, "UniQdata Testnet verification", "organization", info["payer_address"])
        self.engine.register_public_key(BUYER, self.recipient.public_hex)
        chain = MandateChain(BUYER)
        for role in ("issuer", "owner", "agent"):
            key = json.loads(self.keys("mandate-" + role).get_or_create(
                "jwk.json", lambda role=role: canonical(getattr(chain, role + "_key")).encode()))
            setattr(chain, role + "_key", key)
            setattr(chain, role + "_pub", public_jwk_from_private_jwk(key))
        chain.ceiling_drops, chain.payees = AMOUNT, [current["participant_ref"]]
        grant = self.saved.get("delegation.json")
        if grant:
            chain.l1, chain.l2 = json.loads(grant)
        self.engine.mandate_chains[BUYER] = chain
        return ContributionBridge(self.engine, source, buyer_id=BUYER,
                                  keyring=ParticipantKeyring(current["participant_ref"], self.keys("participant-agent")),
                                  recipient=self.recipient), current

    def _budget(self, current):
        if self.saved.get("delegation.json"):
            return
        if current.get("active") is not True:
            raise PermissionError("Original Core consent is inactive")
        if not self.store.one("SELECT 1 FROM mandates WHERE buyer_id=?", BUYER):
            self.engine.set_mandate(BuyerMandate(BUYER, 0, AMOUNT, [PURPOSE]))
        treasury = self.saved.get("treasury").decode()
        world = SimpleNamespace(store=self.store, engine=self.engine, ledger=self.ledger,
                                security=SimpleNamespace(signer_lists={treasury: {
                                    name: device.address for name, device in self.approvers.items()}}))
        approval = self.store.one("SELECT * FROM approvals WHERE spec_hash=?", current["binding_sha256"])
        if approval is None:
            approval = cosign.open_for(world, BUYER, treasury, AMOUNT, current["binding_sha256"], "testnet-operator")
        if approval["status"] != "executed":
            signatures = self.store.q("SELECT signer_name FROM approval_signatures WHERE approval_id=?", approval["id"])
            if len(signatures) >= cosign.QUORUM or approval["status"] != "open":
                raise RuntimeError("Reconcile the prior treasury transaction; no new budget transfer sent")
            done = {row["signer_name"] for row in signatures}
            for name, device in self.approvers.items():
                if name not in done:
                    cosign.add_signature(world, approval["id"], device.sub, name,
                                         device.cosign(cosign.view(self.store, approval["id"])))
            approval = cosign.view(self.store, approval["id"])
        mandate = self.store.one("SELECT * FROM mandates WHERE buyer_id=?", BUYER)
        if approval["status"] != "executed" or mandate["total_drops"] != AMOUNT:
            raise RuntimeError("Reconcile the treasury receipt and finite budget before continuing")
        chain = self.engine.mandate_chains[BUYER]
        chain.issue(AMOUNT, AMOUNT, AMOUNT, [PURPOSE], [current["participant_ref"]], funded_by=approval["tx_hash"])
        self.saved.get_or_create("delegation.json", lambda: canonical([chain.l1, chain.l2]).encode())

    def settle(self, source):
        bridge, state = self._bridge(source)
        self._budget(state)
        bridge.prepare()
        bridge.deliver()
        result = bridge.finish()
        if result["status"] == "delivered":
            result["opened_package_sha256"] = hashlib.sha256(bridge.open_package()).hexdigest()
        return result

    def withdraw(self, source):
        bridge, _ = self._bridge(source)
        bridge.resume()
        result = bridge.sync_withdrawal()
        try:
            bridge.open_package()
        except PermissionError:
            result["future_access_denied"] = True
        else:
            raise RuntimeError("Withdrawal did not deny future access")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "settle", "withdraw", "status"])
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--core-command", type=Path, help="Private JSON argv file; resident local Core pipe")
    parser.add_argument("--country", choices=["KR", "MN"], required=True)
    args = parser.parse_args()
    if args.action != "prepare" and not args.core_command:
        parser.error("--core-command is required after the main-app contribution exists")
    from agentrail import units
    from agentrail.ledger.licence import XrplLicenceMixin
    from agentrail.ledger.xrpl_extras import XrplExtrasMixin
    from agentrail.ledger.xrpl_ledger import XrplLedger
    from xrpl.wallet import Wallet

    if units.TOKEN or units.UNIT != "XRP":
        parser.error("Run this isolated native-XRP verification with SETTLE_ASSET=XRP")

    class Ledger(XrplLicenceMixin, XrplExtrasMixin, XrplLedger):
        pass

    os.umask(0o077)
    args.case_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.case_dir.stat().st_mode & 0o077:
        parser.error("Case directory must be private (0700)")
    try:
        with (args.case_dir / "operator.lock").open("a") as lock, contextlib.redirect_stdout(sys.stderr):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = Ledger(RPC, str(args.case_dir / "wallets.json"))
            # Loading must never refill or create a wallet after the offer is committed.
            for seed in ledger._labels.values():
                wallet = Wallet.from_seed(seed)
                ledger.wallets[wallet.classic_address] = wallet
            case = FileCase(args.case_dir, ledger)
            if args.action == "prepare":
                output = case.prepare()
            else:
                if args.core_command.stat().st_mode & 0o077:
                    raise PermissionError("Core command file must be private (0600)")
                command = json.loads(args.core_command.read_text())
                source = ResidentCore(command, country=args.country, lane="prod")
                if args.action == "status":
                    state = source.call("inspect")
                    output = {key: state.get(key) for key in ("_core", "submission_ref", "binding_sha256",
                                                             "active", "status", "testnet_receipt")}
                else:
                    output = case.settle(source) if args.action == "settle" else case.withdraw(source)
        print(json.dumps(output, separators=(",", ":")))
    except Exception as exc:
        raise SystemExit(f"Testnet case stopped ({type(exc).__name__}); reconcile private state before retrying") from None


if __name__ == "__main__":
    main()
