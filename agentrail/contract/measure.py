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


def train(seed: int = 101, n: int = 400) -> tuple[forecast.Model, dict]:
    reg, issuers = world()
    pool = market.make_market(n, seed=seed)
    r = Round(requirements(), pool, reg, issuers, None, strategy="price", target=10 ** 6, drop_on_fail=False)
    r.run()
    X = [o["x"] for o in r.outcomes]
    y = [int(o["verdict"] == "pass") for o in r.outcomes]
    Xtr, ytr, Xte, yte = forecast.split(X, y)
    m = forecast.Model().fit(Xtr, ytr)
    ps = [m.p(x) for x in Xte]
    base = sum(ytr) / len(ytr)
    return m, {"train": len(Xtr), "test": len(Xte), "pass_rate": round(base, 3),
               "brier": forecast.brier(ps, yte), "brier_base_rate": forecast.brier([base] * len(yte), yte),
               "reliability": forecast.reliability(ps, yte), "weights": m.explain()}


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
