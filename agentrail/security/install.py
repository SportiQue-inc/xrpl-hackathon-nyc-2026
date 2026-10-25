"""Wire the security layer into a demo world: institution vaults, approver devices, enrolled identities.

In the demo every device is simulated in this process (`SecurityContext.devices`). They are reachable
only through the dev harness routes, which are off when AGENTRAIL_ENV=prod; in production each device
enrols its own public key and keeps its private key (phone secure enclave, institution KMS).
"""
from __future__ import annotations

import os

from .auth import Authority, Identity
from .devices import ApproverDevice, Device, InstitutionVault
from .keystore import LocalKeyStore

STUDY = "org_sleeplab"
BUYERS = ("org_robodev", "org_sleeplab", "org_adtech")
SIGNER_NAMES = ("owner", "compliance")


class SecurityContext:
    def __init__(self, w):
        self.w = w
        self.authority = Authority()
        self.devices: dict[str, Device] = {}          # simulated client devices (dev harness only)
        self.vaults: dict[str, InstitutionVault] = {}
        persist = w.ledger.name == "testnet"        # approver keys are on a live SignerList: keep them
        root = os.environ.get("AGENTRAIL_KEYSTORE") or (".keystore" if persist else None)
        self.approvers_by_org = {org: {n: ApproverDevice(f"approver:{n}@{org}", w.ledger.name,
                                                         LocalKeyStore(f"approver.{n}.{org}", root))
                                       for n in SIGNER_NAMES} for org in (STUDY, "org_robodev")}
        self.approvers = self.approvers_by_org[STUDY]
        self.signer_lists: dict[str, dict[str, str]] = {}      # treasury address -> {name: address}

    def install_institutions(self):
        e = self.w.engine
        for org in BUYERS:
            if e.party(org) is None:
                continue
            v = InstitutionVault(org)
            e.register_public_key(org, v.public_hex)
            e.openers[org] = v
            self.vaults[org] = v

    def signer_addresses(self, org: str = STUDY) -> dict[str, str]:
        return {n: d.address for n, d in self.approvers_by_org[org].items()}

    def register_treasury(self, treasury: str, org: str = STUDY) -> dict[str, str]:
        self.signer_lists[treasury] = self.signer_addresses(org)
        return self.signer_lists[treasury]

    def _enrol(self, sub, role, scope, device=None, **attrs):
        d = device or Device(sub)
        self.devices[sub] = d
        self.authority.enrol(Identity(sub, role, scope, d.public_hex, attrs))

    def enrol_staff(self):
        self._enrol(f"researcher@{STUDY}", "researcher", STUDY)
        self._enrol(f"reviewer@{STUDY}", "reviewer", STUDY)
        self._enrol("operator", "operator", "*")
        for org, devs in self.approvers_by_org.items():
            for n, d in devs.items():
                self._enrol(d.sub, "approver", org, d, signer=n)

    def enrol_participants(self, pids):
        for pid in pids:
            if pid not in self.authority.identities:
                self._enrol(pid, "participant", pid)


def install(w) -> SecurityContext:
    from .audit import ANCHOR_SCHEMA
    from .consent import SCHEMA as CONSENT_SCHEMA
    from .cosign import SCHEMA
    w.store._keepalive.executescript(SCHEMA + ANCHOR_SCHEMA + CONSENT_SCHEMA)
    sc = SecurityContext(w)
    w.security = sc
    sc.enrol_staff()
    sc.enrol_participants(list(getattr(w, "people", {})))
    from ..scenario import FIXTURE
    import json
    with open(FIXTURE) as f:      # the study's synthetic participants enrol their phones up front
        sc.enrol_participants([a["account_id"] for a in json.load(f)["accounts"] if a["role"] == "participant"])
    return sc
