"""Act 1 as a node network, replayed from the run's own trade log (works offline for recording).

Every account is a node on a ring. Each trade lights the edge between buyer and seller: blue when it
settled, red when it was refused, declined or settled unfit, amber while it waits for the owner. A node
grows as data it bought accumulates. Then the view zooms into one settled trade and one refused trade
and steps through the agent's decision in the order it made it.
"""
from __future__ import annotations

import json
import math

DECISION = {"settled": "sell", "settled_unfit": "sell", "awaiting_owner": "ask", "declined": "ask", "refused": "block"}
COLOR = {"settled": "ok", "settled_unfit": "bad", "refused": "bad", "declined": "bad", "awaiting_owner": "wait",
         "no_budget": "bad", "not_settled": "bad"}


def _weeks(t: dict) -> str:
    n = t.get("weeks", "?")
    return f"{n} week" if n == 1 else f"{n} weeks"


def trace(t: dict) -> list[dict]:
    """The agent's steps for one trade, in order, from the logged record only."""
    xrp = t["price_drops"] / 1e6
    steps = [
        {"k": "Need", "v": f"{t['buyer']} asks for {', '.join(t['columns'])}, {_weeks(t)}, "
                           f"purpose {t.get('purpose', '?')}"},
        {"k": "Match", "v": f"{t['seller']}'s agent holds a dataset with those columns; its rules: {t['policy']}; "
                            f"buyer trust grade {t.get('buyer_grade', '?')}"},
        {"k": "Quality", "v": f"certificate grade {t['grade']} (buyer's minimum {t.get('min_grade', '?')}); "
                              f"{t.get('sample_k', '?')} hashed sample rows opened and checked against it"},
        {"k": "Provenance", "v": f"certified root {t.get('root', '?')}…; the delivery must hash to it"},
        {"k": "Scope and price", "v": f"{', '.join(t['columns'])} × {_weeks(t)} for {xrp:g} XRP; "
                                      f"contract {t['contract']}"},
        {"k": "Decision", "v": f"{DECISION.get(t['status'], t['status']).upper()}: {t['why']}",
         "tone": COLOR.get(t["status"], "bad")},
    ]
    if t.get("txs"):
        sig = ", ".join(s["code"] for s in t.get("signals", [])) or "none"
        steps.append({"k": "Escrow and key reveal",
                      "v": f"EscrowCreate {t['txs']['escrow_create'][:16]}…, EscrowFinish (key revealed) "
                           f"{(t['txs'].get('escrow_finish') or '')[:16]}…; delivery checks: {sig}",
                      "urls": [u for u in (t.get("urls") or {}).values() if u]})
    else:
        steps.append({"k": "Escrow", "v": "nothing created, nothing paid", "tone": "bad"})
    return steps


def build(ex) -> dict:
    ids = list(ex.accounts)
    n = len(ids)
    nodes = [{"id": a, "org": ex.accounts[a].kind != "person",
              "x": round(500 + 400 * math.cos(2 * math.pi * i / n - math.pi / 2), 1),
              "y": round(500 + 400 * math.sin(2 * math.pi * i / n - math.pi / 2), 1)} for i, a in enumerate(ids)]
    events = [{"b": t["buyer"], "s": t["seller"], "st": t["status"], "c": COLOR.get(t["status"], "bad"),
               "rows": t.get("weeks", 1) * len(t["columns"]) if t["status"] in ("settled", "settled_unfit") else 0}
              for t in ex.trades]
    ok = next((t for t in ex.trades if t["status"] == "settled" and t.get("policy") == "autonomy"),
              next(t for t in ex.trades if t["status"] == "settled"))
    no = next((t for t in ex.trades if t["status"] == "refused" and t["seller"] != ok["seller"]),
              next((t for t in ex.trades if t["status"] == "refused"), None))
    spot = [{"b": t["buyer"], "s": t["seller"], "label": lab, "steps": trace(t)}
            for t, lab in ((ok, "A settled trade"), (no, "A refused trade")) if t]
    st = [e["st"] for e in events]
    return {"nodes": nodes, "events": events, "spotlight": spot, "ledger": ex.ledger.name,
            "totals": {"trades": len(st), "settled": st.count("settled"), "unfit": st.count("settled_unfit"),
                       "refused": st.count("refused") + st.count("declined"), "awaiting": st.count("awaiting_owner")}}


def render(data: dict) -> str:
    return PAGE.replace("/*DATA*/null", json.dumps(data))


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Act 1 network</title>
<style>
:root{--bg:#0b0f17;--fg:#e6ebf2;--mut:#7d8796;--ok:#3b8cff;--bad:#ff4d5e;--wait:#f5b041;--node:#2a3446;--org:#7a5cff}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,sans-serif}
#wrap{display:flex;height:100%}#stage{flex:1;position:relative}svg{width:100%;height:100%;display:block}
#hud{position:absolute;top:16px;left:16px;display:flex;gap:22px}#hud div{font-variant-numeric:tabular-nums}
#hud b{display:block;font-size:26px}#hud span{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
#panel{width:0;overflow:hidden;transition:width .6s;background:#111827;border-left:1px solid #1f2937}
#panel.on{width:min(440px,42vw)}#panel .in{padding:22px;width:min(440px,42vw)}
#panel h2{margin:0 0 4px;font-size:18px}#panel .who{color:var(--mut);margin-bottom:16px}
.step{opacity:0;transform:translateY(6px);transition:all .45s;margin:0 0 12px;padding-left:12px;border-left:3px solid #334155}
.step.on{opacity:1;transform:none}.step .k{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.step.ok{border-color:var(--ok)}.step.bad{border-color:var(--bad)}.step.wait{border-color:var(--wait)}
.step a{color:var(--ok)}
#foot{position:absolute;bottom:12px;left:16px;color:var(--mut);font-size:12px}
#ctl{position:absolute;top:16px;right:16px}button{background:#1f2937;color:var(--fg);border:1px solid #334155;border-radius:6px;padding:6px 12px;cursor:pointer}
.edge{stroke-width:2.2;fill:none;transition:opacity 1.2s}.lbl{fill:var(--mut);font-size:11px}
.dim .node,.dim .lbl{opacity:.12}.dim .node.hot,.dim .lbl.hot{opacity:1}
</style></head><body>
<div id="wrap"><div id="stage">
<svg id="svg" viewBox="0 0 1000 1000"><g id="edges"></g><g id="nodes"></g></svg>
<div id="hud"><div><b id="cT">0</b><span>trades</span></div><div><b id="cS" style="color:var(--ok)">0</b><span>settled</span></div>
<div><b id="cR" style="color:var(--bad)">0</b><span>refused / unfit</span></div><div><b id="cE">0.0</b><span>seconds</span></div></div>
<div id="ctl"><button id="play">Replay</button></div>
<div id="foot">Act 1 replayed from the run's trade log · ledger: <span id="led"></span> · synthetic data · Testnet · not legal advice</div>
</div><div id="panel"><div class="in"><h2 id="pt"></h2><div class="who" id="pw"></div><div id="steps"></div></div></div></div>
<script>
const D=/*DATA*/null;
const NS="http://www.w3.org/2000/svg",svg=document.getElementById("svg"),E=document.getElementById("edges"),N=document.getElementById("nodes");
const pos={},circ={},lbl={},db={};document.getElementById("led").textContent=D.ledger;
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p&&p.appendChild(e);return e}
function setup(){E.innerHTML="";N.innerHTML="";for(const n of D.nodes){pos[n.id]=n;db[n.id]=0;
 circ[n.id]=el("circle",{cx:n.x,cy:n.y,r:6,fill:n.org?"var(--org)":"var(--node)",stroke:"#4b5563","stroke-width":1,class:"node"},N);
 const a=Math.atan2(n.y-500,n.x-500),lx=500+435*Math.cos(a),ly=500+435*Math.sin(a);
 lbl[n.id]=el("text",{x:lx,y:ly+4,"text-anchor":lx<500?"end":"start",class:"lbl"},N);lbl[n.id].textContent=n.id}}
const C={ok:"var(--ok)",bad:"var(--bad)",wait:"var(--wait)"};
function flash(e,keep){const a=pos[e.b],b=pos[e.s];if(!a||!b)return;
 const mx=(a.x+b.x)/2*0.7+150,my=(a.y+b.y)/2*0.7+150;
 const p=el("path",{d:`M${b.x},${b.y} Q${mx},${my} ${a.x},${a.y}`,stroke:C[e.c],class:"edge"},E);
 if(!keep)setTimeout(()=>p.style.opacity=0,700),setTimeout(()=>p.remove(),2000);return p}
function grow(e){if(!e.rows)return;db[e.b]+=e.rows;circ[e.b].setAttribute("r",(6+Math.sqrt(db[e.b])*1.6).toFixed(1))}
let vb=[0,0,1000,1000],timers=[],raf;
function zoomTo(t,ms){const s=[...vb],t0=performance.now();cancelAnimationFrame(raf);
 return new Promise(r=>{function f(now){const k=Math.min(1,(now-t0)/ms),q=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
 vb=s.map((v,i)=>v+(t[i]-v)*q);svg.setAttribute("viewBox",vb.join(" "));k<1?raf=requestAnimationFrame(f):r()}raf=requestAnimationFrame(f)})}
const wait=ms=>new Promise(r=>timers.push(setTimeout(r,ms)));
async function spotlight(s){const a=pos[s.b],b=pos[s.s];svg.classList.add("dim");
 for(const id of [s.b,s.s]){circ[id].classList.add("hot");lbl[id].classList.add("hot")}
 const p=flash({b:s.b,s:s.s,c:s.steps[s.steps.length-2].tone||"ok"},true);
 const sw=innerWidth-Math.min(440,.42*innerWidth),ar=sw/innerHeight,cx=(a.x+b.x)/2,cy=(a.y+b.y)/2;
 const w=Math.max(Math.abs(a.x-b.x)+200,(Math.abs(a.y-b.y)+200)*ar),h=w/ar;
 await zoomTo([cx-w/2,cy-h/2,w,h],1600);const P=document.getElementById("panel");
 document.getElementById("pt").textContent=s.label;document.getElementById("pw").textContent=`${s.s}'s agent, asked by ${s.b}`;
 const box=document.getElementById("steps");box.innerHTML="";P.classList.add("on");await wait(700);
 for(const st of s.steps){const d=document.createElement("div");d.className="step "+(st.tone||"");
  d.innerHTML=`<div class="k"></div><div class="v"></div>`;d.querySelector(".k").textContent=st.k;d.querySelector(".v").textContent=st.v;
  for(const u of st.urls||[]){const l=document.createElement("a");l.href=u;l.target="_blank";l.textContent=" explorer ↗";d.querySelector(".v").appendChild(l)}
  box.appendChild(d);requestAnimationFrame(()=>d.classList.add("on"));await wait(1500)}
 await wait(2200);P.classList.remove("on");await zoomTo([0,0,1000,1000],1400);
 p.remove();svg.classList.remove("dim");for(const id of [s.b,s.s]){circ[id].classList.remove("hot");lbl[id].classList.remove("hot")}}
async function run(){timers.forEach(clearTimeout);timers=[];document.getElementById("panel").classList.remove("on");
 vb=[0,0,1000,1000];svg.setAttribute("viewBox","0 0 1000 1000");setup();
 const c={T:0,S:0,R:0},t0=performance.now(),dt=Math.max(40,Math.min(140,14000/D.events.length));
 const tick=setInterval(()=>document.getElementById("cE").textContent=((performance.now()-t0)/1000).toFixed(1),100);
 for(const e of D.events){flash(e);grow(e);c.T++;if(e.st==="settled")c.S++;else if(e.c==="bad")c.R++;
  cT.textContent=c.T;cS.textContent=c.S;cR.textContent=c.R;await wait(dt)}
 await wait(1500);for(const s of D.spotlight)await spotlight(s);clearInterval(tick)}
document.getElementById("play").onclick=run;run();
</script></body></html>"""
