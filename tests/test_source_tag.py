"""Every XRPL L1 tx we sign carries the team SourceTag (XRPL Commons counts activity by it)."""
import asyncio

from xrpl.asyncio.transaction import main, reliable_submission
from xrpl.models.transactions import Payment

import agentrail  # noqa: F401  (installs the tag)
from agentrail.ledger import source_tag

PAY = dict(account="rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh", destination="rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe",
           amount="10")


def test_default_tag_is_the_team_tag(monkeypatch):
    monkeypatch.delenv("XRPL_SOURCE_TAG", raising=False)
    assert source_tag.tagged(Payment(**PAY)).source_tag == 2610250016


def test_env_overrides_and_can_turn_it_off(monkeypatch):
    monkeypatch.setenv("XRPL_SOURCE_TAG", "42")
    assert source_tag.tagged(Payment(**PAY)).source_tag == 42
    monkeypatch.setenv("XRPL_SOURCE_TAG", "off")
    assert source_tag.tagged(Payment(**PAY)).source_tag is None


def test_an_existing_tag_is_kept(monkeypatch):
    monkeypatch.delenv("XRPL_SOURCE_TAG", raising=False)
    assert source_tag.tagged(Payment(**PAY, source_tag=804681468)).source_tag == 804681468


def test_every_xrpl_py_sign_path_goes_through_the_tagging_autofill(monkeypatch):
    monkeypatch.delenv("XRPL_SOURCE_TAG", raising=False)
    assert main.autofill._agentrail_tagged and reliable_submission._autofill is main.autofill
    seen = []

    async def fake_inner(tx, client, *a, **kw):
        seen.append(tx.source_tag)
        return tx
    # rebuild the wrapper around a fake inner autofill so no network is needed
    monkeypatch.setattr(reliable_submission, "_autofill", reliable_submission._autofill)
    monkeypatch.setattr(main, "autofill", fake_inner)
    source_tag.install()
    from xrpl.transaction import autofill   # the sync wrapper used by multisign and cosign paths
    autofill(Payment(**PAY), client=None)
    asyncio.run(reliable_submission._autofill(Payment(**PAY), None))
    assert seen == [2610250016, 2610250016]


def test_x402_requirements_carry_the_team_tag():
    from agentrail.ledger import x402_rail
    assert x402_rail.SOURCE_TAG == 2610250016
