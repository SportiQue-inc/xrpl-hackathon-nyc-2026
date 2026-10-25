"""6. Paying participants in a stablecoin through an AMM: the payer holds only XRP, the
participant receives a USD stablecoin (cross-currency Payment routed through the XRP/USD AMM).

Part A: RLUSD on Testnet (issuer below), if an XRP/RLUSD AMM with liquidity exists.
Part B: a synthetic Testnet stablecoin we issue ourselves + our own AMM, so the flow is
proven even if the RLUSD pool is missing or thin. Synthetic token, Testnet only."""
import os
import time

from common import run
from agentrail.ledger.xrpl_extras import submit_capture
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.currencies import XRP, IssuedCurrency
from xrpl.models.requests import AMMInfo
from xrpl.models.transactions import AccountSet, AccountSetAsfFlag, AMMCreate, Payment, TrustSet

RLUSD_ISSUER = os.environ.get("RLUSD_TESTNET_ISSUER", "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV")
RLUSD = "524C555344000000000000000000000000000000"  # "RLUSD" as a 160-bit currency code


def amm_info(L, cur: IssuedCurrency):
    r = L.client.request(AMMInfo(asset=XRP(), asset2=cur)).result
    return r.get("amm")


def xrp_needed_drops(L, cur: IssuedCurrency, value: str) -> str:
    """SendMax for buying `value` of `cur` from the XRP/cur pool: spot price + 50% for fee and slippage."""
    info = amm_info(L, cur)
    price = int(info["amount"]) / float(info["amount2"]["value"])  # drops per token
    return str(int(price * float(value) * 1.5) + 1)


def pay_through_amm(c, L, payer, part, cur: IssuedCurrency, value: str, label: str):
    t = time.time()
    h, code, _ = submit_capture(L.client, TrustSet(account=part, limit_amount=IssuedCurrencyAmount(
        currency=cur.currency, issuer=cur.issuer, value="1000000")), L.wallets[part])
    c.step(f"[{label}] participant TrustSet to the stablecoin", h, code, "tesSUCCESS", t, "setup")
    t = time.time()
    send_max = xrp_needed_drops(L, cur, value)
    h, code, r = submit_capture(L.client, Payment(
        account=payer, destination=part, send_max=send_max,
        amount=IssuedCurrencyAmount(currency=cur.currency, issuer=cur.issuer, value=value)), L.wallets[payer])
    delivered = r.get("meta", {}).get("delivered_amount")
    c.step(f"[{label}] Payment XRP -> {value} stablecoin to participant via AMM", h, code, "tesSUCCESS", t,
           "success", f"delivered {delivered}, SendMax {send_max} drops")
    return code == "tesSUCCESS"


def main(c, L):
    payer = c.account("study payer (holds XRP only)", L.new_account("amm_payer"))
    part = c.account("participant", L.new_account("amm_participant"))
    nolines = c.account("participant without trust line", L.new_account("amm_participant_noline"))

    # Part A: RLUSD
    rl = IssuedCurrency(currency=RLUSD, issuer=RLUSD_ISSUER)
    try:
        info = amm_info(L, rl)
    except Exception as e:  # noqa: BLE001
        info = None
        c.note(f"amm_info XRP/RLUSD error: {e}")
    if info:
        c.note(f"XRP/RLUSD AMM on Testnet: account={info.get('account')} amount={info.get('amount')} "
               f"amount2={info.get('amount2')} fee={info.get('trading_fee')}")
        rlusd_ok = pay_through_amm(c, L, payer, part, rl, "1", "RLUSD")
    else:
        rlusd_ok = False
        c.note(f"no XRP/RLUSD AMM found for issuer {RLUSD_ISSUER}")

    # Part B: synthetic stablecoin with our own pool
    iss = c.account("tUSD issuer (synthetic)", L.new_account("amm_tusd_issuer"))
    lp = c.account("liquidity provider", L.new_account("amm_lp"))
    cur = IssuedCurrency(currency="USD", issuer=iss)
    if not amm_info_safe(L, cur):
        t = time.time()
        h, code, _ = submit_capture(L.client, AccountSet(account=iss, set_flag=AccountSetAsfFlag.ASF_DEFAULT_RIPPLE),
                                    L.wallets[iss])
        c.step("[tUSD] issuer DefaultRipple", h, code, "tesSUCCESS", t, "setup")
        t = time.time()
        h, code, _ = submit_capture(L.client, TrustSet(account=lp, limit_amount=IssuedCurrencyAmount(
            currency="USD", issuer=iss, value="1000000")), L.wallets[lp])
        c.step("[tUSD] LP TrustSet", h, code, "tesSUCCESS", t, "setup")
        t = time.time()
        h, code, _ = submit_capture(L.client, Payment(account=iss, destination=lp, amount=IssuedCurrencyAmount(
            currency="USD", issuer=iss, value="10000")), L.wallets[iss])
        c.step("[tUSD] issue 10,000 tUSD to LP", h, code, "tesSUCCESS", t, "setup")
        t = time.time()
        h, code, _ = submit_capture(L.client, AMMCreate(account=lp, amount="40000000", amount2=IssuedCurrencyAmount(
            currency="USD", issuer=iss, value="2000"), trading_fee=300), L.wallets[lp])
        c.step("[tUSD] AMMCreate 40 XRP / 2,000 tUSD", h, code, "tesSUCCESS", t, "setup")
    c.note(f"tUSD AMM: {amm_info_safe(L, cur)}")
    ok_b = pay_through_amm(c, L, payer, part, cur, "5", "tUSD")

    t = time.time()
    h, code, _ = submit_capture(L.client, Payment(account=payer, destination=nolines, send_max="5000000",
                                                  amount=IssuedCurrencyAmount(currency="USD", issuer=iss, value="5")),
                                L.wallets[payer])
    c.step("[tUSD] same payment to a participant with no trust line", h, code, "tecPATH_DRY", t, "failure",
           "participants must opt in to the stablecoin first (one TrustSet)")
    c.note("Fallback that always works: pay XRP, or the participant's agent swaps XRP->stablecoin itself.")
    return c.save(("RLUSD via the Testnet XRP/RLUSD AMM works. " if rlusd_ok else
                   "RLUSD Testnet AMM path not available (see notes). ")
                  + ("Synthetic stablecoin via our own AMM works: payer sends XRP, participant receives USD."
                     if ok_b else "Synthetic stablecoin path failed."),
                  alternative=None if rlusd_ok else "Use our synthetic tUSD + AMM on Testnet; RLUSD on Mainnet later")


def amm_info_safe(L, cur):
    try:
        return amm_info(L, cur)
    except Exception:  # noqa: BLE001
        return None


if __name__ == "__main__":
    run("6_amm", "AMM stablecoin payout (RLUSD / synthetic tUSD)", ["AMM", "fixAMMv1_1", "fixAMMv1_2"], main)
