"""scripts/open_bundle.py: the key published on the ledger opens the study's copy of that round."""
import importlib.util
import os
import sys

import pytest

from agentrail import scenario, study
from tests.llm_doubles import capable_needs

SPEC = importlib.util.spec_from_file_location(
    "open_bundle", os.path.join(os.path.dirname(__file__), "..", "scripts", "open_bundle.py"))


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTRAIL_KEYSTORE", str(tmp_path / "ks"))
    db = str(tmp_path / "run.db")
    w = scenario.build_world("mock", db)
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)

    def fake_tx(h):            # what the public ledger returns for these hashes
        st = w.ledger.lookup(h)
        o = w.store.one("SELECT o.bundle_hash FROM payments p JOIN orders o ON o.id=p.order_id "
                        "WHERE p.tx_hash=? OR p.finish_tx=?", h, h)
        memo = f"order:x|bundle:{o['bundle_hash'][:16]}".encode().hex()
        return {"tx_json": {"TransactionType": st.tx_type, "Fulfillment": st.fulfillment,
                            "Condition": st.condition, "Memos": [{"Memo": {"MemoData": memo}}]},
                "meta": {"TransactionResult": "tesSUCCESS"}}
    monkeypatch.setattr(mod, "ledger_tx", fake_tx)
    return w, db, str(tmp_path / "ks"), mod


def _main(mod, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["open_bundle.py", *argv])
    with pytest.raises(SystemExit) as e:
        mod.main()
    return e.value.code


def test_key_from_the_ledger_opens_the_round_and_matches_the_ledger_hash(run, monkeypatch, capsys):
    w, db, ks, mod = run
    p = w.store.one("SELECT p.finish_tx FROM payments p JOIN bundles b ON b.order_id=p.order_id "
                    "WHERE p.kind='escrow' AND p.finish_tx IS NOT NULL")
    assert _main(mod, monkeypatch, p["finish_tx"], "--db", db, "--keystore", ks) == 0
    out = capsys.readouterr().out
    assert "Condition = SHA-256(K): yes" in out and "memo yes" in out and "rows (synthetic)" in out


def test_withdrawn_participants_copy_is_gone(run, monkeypatch, capsys):
    w, db, ks, mod = run
    from agentrail.cohort import HERO
    study.participant_revoke(w, HERO)
    p = w.store.one("SELECT p.finish_tx FROM payments p JOIN orders o ON o.id=p.order_id "
                    "WHERE o.seller_id=? AND p.finish_tx IS NOT NULL", HERO)
    mod.sys.argv = ["open_bundle.py", p["finish_tx"], "--db", db, "--keystore", ks]
    mod.main()
    assert "no longer exists" in capsys.readouterr().out
