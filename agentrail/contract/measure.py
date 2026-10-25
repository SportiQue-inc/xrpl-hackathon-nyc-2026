"""Measurement on synthetic streams: train and calibrate the delivery reliability forecast, then
compare three ways of buying the same target of usable provider-windows from the same market, in
which bad records start partway through the round:

  manual         lowest price, terms as asked, everything paid on delivery, reviewed at the end
                 (the current way: people collect, then check)
  checks         lowest price, negotiated contracts, incremental checks, per-contribution holdback,
                 replacement of failed providers while the round is open
  forecast       the same, but providers ranked by expected usable windows per XRP from the
                 delivery reliability forecast, with early backups when a window looks short

Synthetic market, synthetic faults: the numbers show what the mechanism does on this generator,
not what a real market would do.
"""
from __future__ import annotations

from ..ledger.mock import MockLedger
from . import forecast, market, provenance
from .round import Round, requirements


def world(seed: int = 0):
    L = MockLedger()
    reg = provenance.Registry(L, L.new_account("org_registry"))
    issuers = {n: provenance.SourceIssuer(n, n.encode().ljust(32, b"0")) for n in market.ISSUERS + ["unknown_app"]}
    for n in market.ISSUERS:
        reg.register(issuers[n], L.new_account("src_" + n))
    return reg, issuers


def train(seed: int = 101, n: int = 900, calibration: str = "platt") -> tuple[forecast.Model, dict]:
    """Fit on 50% of the synthetic histories, calibrate on 25%, report on the last 25% (seen by
    neither). Returns the calibrated model and the numbers before and after calibration."""
    reg, issuers = world()
    pool = market.make_market(n, seed=seed)
    r = Round(requirements(), pool, reg, issuers, None, strategy="price", target=10 ** 6, drop_on_fail=False)
    r.run()
    X = [o["x"] for o in r.outcomes]
    y = [int(o["verdict"] == "pass") for o in r.outcomes]
    Xtr, ytr, Xrest, yrest = forecast.split(X, y, test=0.5)
    k = len(Xrest) // 2
    Xcal, ycal, Xte, yte = Xrest[:k], yrest[:k], Xrest[k:], yrest[k:]
    base = forecast.Model().fit(Xtr, ytr)
    cal = (forecast.Isotonic() if calibration == "isotonic" else forecast.Platt()).fit(
        [base.p(x) for x in Xcal], ycal)
    m = forecast.Calibrated(base, cal)
    raw, ps = [base.p(x) for x in Xte], [m.p(x) for x in Xte]
    rate = sum(ytr) / len(ytr)
    return m, {"train": len(Xtr), "calibration_set": len(Xcal), "test": len(Xte), "pass_rate": round(rate, 3),
               "calibration": calibration, "brier_base_rate": forecast.brier([rate] * len(yte), yte),
               "brier_before": forecast.brier(raw, yte), "brier": forecast.brier(ps, yte),
               "ece_before": forecast.ece(raw, yte), "ece": forecast.ece(ps, yte),
               "reliability_before": forecast.reliability(raw, yte), "reliability": forecast.reliability(ps, yte),
               "weights": base.explain()}


def compare(model: forecast.Model, seeds=(21, 22, 23, 24, 25), n: int = 150, target: int = 40) -> dict:
    out = {"manual": [], "checks": [], "forecast": []}
    for s in seeds:
        for name, kw in (("manual", dict(strategy="price", negotiation=False, checks=False)),
                         ("checks", dict(strategy="price")),
                         ("forecast", dict(strategy="forecast"))):
            reg, issuers = world()
            r = Round(requirements(), market.make_market(n, seed=s), reg, issuers, model, target=target, **kw)
            out[name].append(r.run())
    agg = {}
    for name, runs in out.items():
        k = len(runs)
        mean = lambda f: round(sum(f(x) for x in runs) / k, 3)
        agg[name] = {"usable": mean(lambda x: x["usable"]), "target": target,
                     "target_met": f"{sum(x['target_met'] for x in runs)}/{k}",
                     "unfit_paid": mean(lambda x: x["unfit_paid"]),
                     "xrp_paid_for_unfit": mean(lambda x: x["xrp_paid_for_unfit"]),
                     "xrp_paid": mean(lambda x: x["xrp_paid"]),
                     "xrp_per_usable": mean(lambda x: x["xrp_per_usable"] or 0),
                     "unfit_rate": mean(lambda x: x["unfit"] / max(1, x["contributions"]))}
    return {"seeds": list(seeds), "market_size": n, "runs": agg}
