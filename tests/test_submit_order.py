"""Out-of-order submits from one account are resubmitted instead of left to expire."""
from types import SimpleNamespace

from agentrail.ledger import xrpl_ledger
from agentrail.ledger.base import Prepared


def test_pre_seq_is_resubmitted(monkeypatch):
    monkeypatch.setattr(xrpl_ledger.time, "sleep", lambda s: None)
    answers = iter(["terPRE_SEQ", "terPRE_SEQ", "tesSUCCESS"])
    calls = []

    class C:
        def request(self, r):
            calls.append(r)
            return SimpleNamespace(result={"engine_result": next(answers)})

    led = xrpl_ledger.XrplLedger.__new__(xrpl_ledger.XrplLedger)
    led.client = C()
    led.submit(Prepared("h", "AB"))
    assert len(calls) == 3
