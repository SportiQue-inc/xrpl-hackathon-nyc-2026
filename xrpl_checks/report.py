"""results/*.json -> RESULTS.md (paste-ready tables)."""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def link(s):
    return f"[`{s['tx'][:10]}…`]({s['explorer']})" if s.get("tx") else "—"


def main():
    out = ["# XRPL Testnet feature checks", "",
           "Synthetic faucet accounts on XRPL Testnet only. Re-run: `python xrpl_checks/run_all.py`.", ""]
    am = os.path.join(HERE, "results", "0_amendments.json")
    if os.path.exists(am):
        out += ["## Amendments on Testnet", "", "| amendment | status |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in json.load(open(am)).items()] + [""]
    res = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(HERE, "results", "[1-9]_*.json")))]
    out += ["## Summary", "", "| # | feature | status | success tx | failure tx (expected refusal) | time | conclusion |",
            "|---|---|---|---|---|---|---|"]
    for r in res:
        ok = next((s for s in r["steps"] if s["kind"] == "success" and s.get("tx") and s["result"] == "tesSUCCESS"), None)
        bad = next((s for s in r["steps"] if s["kind"] == "failure" and s.get("tx")), None)
        out.append(f"| {r['key'][0]} | {r['title']} | {r['status']} | {link(ok) if ok else '—'} | "
                   f"{(link(bad) + ' ' + str(bad['result'])) if bad else '—'} | {r['total_seconds']}s | "
                   f"{r['conclusion']}{' Blocker: ' + r['blocker'] if r.get('blocker') else ''} |")
    for r in res:
        out += ["", f"## {r['key'][0]}. {r['title']} — {r['status']}", "",
                "amendments: " + (", ".join(f"{k} {v}" for k, v in r["amendments"].items()) or "n/a"), "",
                "| step | result | expected | ok | s | tx |", "|---|---|---|---|---|---|"]
        for s in r["steps"]:
            out.append(f"| {s['label']} | {s['result']} | {s['expect'] or 'observe'} | "
                       f"{'✅' if s['ok'] else '❌'} | {s['seconds']} | {link(s)} |")
        if r["notes"]:
            out += [""] + [f"- {n}" for n in r["notes"]]
        if r.get("blocker"):
            out += ["", f"**Blocker:** {r['blocker']}"]
        if r.get("alternative"):
            out += ["", f"**Alternative:** {r['alternative']}"]
        out += ["", "accounts: " + ", ".join(f"{k} `{v}`" for k, v in r["accounts"].items())]
    open(os.path.join(HERE, "RESULTS.md"), "w").write("\n".join(out) + "\n")
    print("wrote RESULTS.md")


if __name__ == "__main__":
    main()
