"""Act 1 as a node network, replayed from the run's own logs (works offline for recording).

Every account is a node on a ring; the shared offer book sits in the middle (its root is anchored on
the ledger). Each trade lights the edge between buyer and seller: blue when it settled, red when it was
refused, declined or settled unfit, amber while it waits for the owner. A node grows as data it bought
accumulates. Then, for one settled trade and one refused trade, the view replays the buyer agent's
path from the logs: the need it formed from the gap in its own store, the query to the offer book, the
fan-out to every candidate, the sample checks, the scores, the negotiation, and the one trade; then it
zooms into that pair and steps through the decision. Each step is labelled with what produced it
(engine rule, LLM, ledger).
"""
from __future__ import annotations

import json
import math

DECISION = {"settled": "sell", "settled_unfit": "sell", "awaiting_owner": "ask", "declined": "ask", "refused": "block"}
COLOR = {"settled": "ok", "settled_unfit": "bad", "refused": "bad", "declined": "bad", "awaiting_owner": "wait",
         "no_budget": "bad", "not_settled": "bad"}


def _weeks(n) -> str:
    return f"{n} week" if n == 1 else f"{n} weeks"


def _xrp(d) -> str:
    return f"{d / 1e6:g} XRP"


def trace(t: dict, need: dict | None) -> list[dict]:
    """The buyer agent's path to this trade, then the seller agent's decision, from the logs only."""
    plan, disc = (need or {}).get("plan") or {}, (need or {}).get("discovery") or {}
    steps = []
    if plan:
        steps.append({"k": "1. Need formed", "by": "LLM" if plan.get("source") == "llm" else "engine rule",
                      "v": f"store holds {len(plan.get('holds', []))} columns; gap: {', '.join(plan.get('gap', []))}. "
                           f"Wants {', '.join(t['columns'])} × {_weeks(t.get('weeks', '?'))}, grade "
                           f"{plan.get('min_grade', 'C')}+, at most {_xrp(plan['max_price_drops'])} each "
                           f"(budget {_xrp(plan.get('budget_drops', 0))}). “{plan.get('why', '')}”"})
    else:
        steps.append({"k": "1. Need", "by": "engine rule",
                      "v": f"{t['buyer']} asks for {', '.join(t['columns'])}, {_weeks(t.get('weeks', '?'))}"})
    if disc:
        dropped = ", ".join(f"{v} {k}" for k, v in sorted(disc.get("dropped", {}).items(), key=lambda x: -x[1]))
        steps.append({"k": "2. Offer book queried", "by": "ledger + engine",
                      "v": f"{disc.get('listed', 0)} listings; root {str(disc.get('anchored_root'))[:12]}… anchored "
                           f"in tx {str(disc.get('anchor_tx'))[:12]}…. Filtered out: {dropped or 'none'}"})
        sampled = disc.get("sampled", [])
        bad = [x for x in sampled if not x["ok"]]
        steps.append({"k": "3. Fan-out: sample checks", "by": "engine rule",
                      "v": f"{len(sampled)} candidates; each opened {t.get('sample_k', 12)} hashed rows against its "
                           f"certificate; {len(bad)} failed" + (f" ({bad[0]['seller']}: {bad[0]['why']})" if bad else "")})
        top = disc.get("ranked", [])[:5]
        steps.append({"k": "4. Compared", "by": "engine rule",
                      "v": "; ".join(f"{r['seller']} {r['score']} (grade {r['grade']}, ask {_xrp(r['ask_drops'])})"
                                     for r in top),
                      "table": [{"seller": r["seller"], "grade": r["grade"], "ask": r["ask_drops"], "score": r["score"],
                                 **r["parts"]} for r in top]})
        mine = next((r for r in disc.get("ranked", []) if r["seller"] == t["seller"] and r.get("negotiation")), None)
        if mine:
            n = mine["negotiation"]
            rounds = " → ".join(f"{x['bid']}/{x['counter']}" for x in n["rounds"])
            steps.append({"k": "5. Negotiated", "by": "engine rule",
                          "v": f"bid/counter in drops: {rounds}; " +
                               (f"deal at {_xrp(n['price_drops'])} (ask {_xrp(mine['ask_drops'])})" if n["deal"]
                                else f"no deal: {n.get('why')}")})
        ex = disc.get("explanation") or {}
        if ex.get("why"):
            steps.append({"k": "Why this seller", "by": "LLM" if ex.get("source") == "llm" else "engine rule",
                          "v": ex["why"]})
    steps.append({"k": "6. Seller's agent decides", "by": "engine rule",
                  "v": f"{DECISION.get(t['status'], t['status']).upper()}: {t['why']} (its rules: {t['policy']}, "
                       f"buyer trust grade {t.get('buyer_grade', '?')})", "tone": COLOR.get(t["status"], "bad")})
    if t.get("txs"):
        sig = ", ".join(s["code"] for s in t.get("signals", [])) or "none"
        steps.append({"k": "7. Escrow and key reveal", "by": "ledger",
                      "v": f"EscrowCreate {t['txs']['escrow_create'][:16]}…, EscrowFinish publishes the key "
                           f"{(t['txs'].get('escrow_finish') or '')[:16]}…; delivery hashed to the certified root "
                           f"{t.get('root', '?')}…; checks: {sig}",
                      "urls": [u for u in (t.get("urls") or {}).values() if u]})
    else:
        steps.append({"k": "7. Escrow", "by": "ledger", "v": "nothing created, nothing paid", "tone": "bad"})
    return steps


def _pick(ex, needs):
    def rich(t):
        d = (needs.get(t["need"]) or {}).get("discovery") or {}
        top = d.get("ranked", [])[:5]
        # a need whose candidates differ (grade, price, track record), so the comparison shows a choice
        return len(top) >= 3 and len(d.get("sampled", [])) >= 5 and len({r["score"] for r in top}) >= 3 and \
            top[0]["seller"] == t["seller"]
    ok = next((t for t in ex.trades if t["status"] == "settled" and t.get("policy") == "autonomy" and rich(t)),
              next(t for t in ex.trades if t["status"] == "settled"))
    no = next((t for t in ex.trades if t["status"] == "refused" and t["seller"] != ok["seller"] and rich(t)),
              next((t for t in ex.trades if t["status"] == "refused"), None))
    return ok, no


def build(ex) -> dict:
    ids = list(ex.accounts)
    n = len(ids)
    nodes = [{"id": a, "org": ex.accounts[a].kind != "person",
              "x": round(500 + 400 * math.cos(2 * math.pi * i / n - math.pi / 2), 1),
              "y": round(500 + 400 * math.sin(2 * math.pi * i / n - math.pi / 2), 1)} for i, a in enumerate(ids)]
    needs = {e["need"]: e for e in ex.events if e.get("kind") == "need"}
    events = [{"b": t["buyer"], "s": t["seller"], "st": t["status"], "c": COLOR.get(t["status"], "bad"),
               "rows": t.get("weeks", 1) * len(t["columns"]) if t["status"] in ("settled", "settled_unfit") else 0}
              for t in ex.trades]
    spot = []
    for t, lab in zip(_pick(ex, needs), ("A settled trade", "A refused trade")):
        if not t:
            continue
        d = (needs.get(t["need"]) or {}).get("discovery") or {}
        spot.append({"b": t["buyer"], "s": t["seller"], "label": lab, "steps": trace(t, needs.get(t["need"])),
                     "trace": t.get("trace"),
                     "sampled": [{"s": x["seller"], "ok": x["ok"]} for x in d.get("sampled", [])],
                     "top": [{"s": r["seller"], "score": r["score"]} for r in d.get("ranked", [])[:5]]})
    st = [e["st"] for e in events]
    book = next((e for e in ex.events if e.get("kind") == "offer_book"), None)
    return {"nodes": nodes, "events": events, "spotlight": spot, "ledger": ex.ledger.name,
            "contracts": getattr(ex, "contracts", []),
            "book": {"listings": book["listings"], "root": book["root"], "tx": book["tx"]} if book else None,
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
#panel.on{width:min(480px,45vw)}#panel .in{padding:22px;width:min(480px,45vw)}
#panel h2{margin:0 0 4px;font-size:18px}#panel .who{color:var(--mut);margin-bottom:16px}
.step{opacity:0;transform:translateY(6px);transition:all .45s;margin:0 0 12px;padding-left:12px;border-left:3px solid #334155}
.step.on{opacity:1;transform:none}.step .k{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.step.ok{border-color:var(--ok)}.step.bad{border-color:var(--bad)}.step.wait{border-color:var(--wait)}
.step a{color:var(--ok)}.step .k em{float:right;font-style:normal;color:var(--wait);text-transform:none;letter-spacing:0}
.step table{border-collapse:collapse;font-size:12px;margin-top:4px;width:100%}.step td,.step th{padding:2px 4px;text-align:right;border-bottom:1px solid #1f2937}
.step th{color:var(--mut);font-weight:500}.step td:first-child,.step th:first-child{text-align:left}
#steps{max-height:calc(100vh - 110px);overflow-y:auto}.score{fill:var(--ok);font-size:13px;font-weight:600}
.booklbl{fill:var(--wait)}
#modal{position:fixed;inset:0;background:rgba(5,8,14,.72);display:none;align-items:center;justify-content:center;z-index:9;padding:16px}
#modal.on{display:flex}#modal .box{background:#111827;border:1px solid #334155;border-radius:12px;width:min(760px,100%);max-height:92vh;display:flex;flex-direction:column}
.mh{display:flex;justify-content:space-between;align-items:flex-start;padding:16px 18px;border-bottom:1px solid #1f2937}
#chat,#mlist{overflow-y:auto;padding:14px 18px}#mv{padding:10px 18px;border-top:1px solid #1f2937;color:var(--mut);font-size:13px}
.turn{max-width:78%;margin:0 0 10px;opacity:0;transform:translateY(6px);transition:all .35s}.turn.on{opacity:1;transform:none}
.turn .who{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 2px}
.turn .msg{padding:8px 11px;border-radius:10px;background:#1e293b}.turn .why{font-size:12px;color:var(--mut);margin-top:3px}
.turn.buyer{margin-right:auto}.turn.buyer .msg{background:#15305c}
.turn.seller,.turn.owner{margin-left:auto;text-align:right}.turn.seller .msg{background:#2a2350}.turn.owner .msg{background:#4a3410}
.turn.ledger{margin:0 auto 10px;text-align:center;max-width:92%}.turn.ledger .msg{background:#0f2a22;font-family:ui-monospace,monospace;font-size:12px}
.chk{display:inline-block;font-size:11px;margin:3px 4px 0 0;padding:1px 6px;border-radius:9px;border:1px solid #334155}
.chk.ok{color:#7dd3a0;border-color:#1f5e3d}.chk.no{color:var(--bad);border-color:#7f1d2d}
.row{display:flex;gap:10px;padding:6px 4px;border-bottom:1px solid #1f2937;cursor:pointer;font-size:13px}.row:hover{background:#1e293b}
.row .st{margin-left:auto}.st.ok{color:var(--ok)}.st.bad{color:var(--bad)}.st.wait{color:var(--wait)}.dim .book.hot{opacity:1}
#foot{position:absolute;bottom:12px;left:16px;color:var(--mut);font-size:12px}
#ctl{position:absolute;top:16px;right:16px}button{background:#1f2937;color:var(--fg);border:1px solid #334155;border-radius:6px;padding:6px 12px;cursor:pointer}
.edge{stroke-width:2.2;fill:none;transition:opacity 1.2s}.lbl{fill:var(--mut);font-size:11px}
.dim .node,.dim .lbl{opacity:.12}.dim .node.hot,.dim .lbl.hot{opacity:1}
</style></head><body>
<div id="wrap"><div id="stage">
<svg id="svg" viewBox="0 0 1000 1000"><g id="edges"></g><g id="nodes"></g></svg>
<div id="hud"><div><b id="cT">0</b><span>trades</span></div><div><b id="cS" style="color:var(--ok)">0</b><span>settled</span></div>
<div><b id="cR" style="color:var(--bad)">0</b><span>refused / unfit</span></div><div><b id="cE">0.0</b><span>seconds</span></div></div>
<div id="ctl"><button id="list">Contracts</button> <button id="play">Replay</button></div>
<div id="foot">Act 1 replayed from the run's trade log · ledger: <span id="led"></span> · synthetic data · Testnet · not legal advice</div>
</div><div id="modal"><div class="box"><div class="mh"><div><b id="mt"></b><div id="ms" class="who"></div></div><button id="mx">Close</button></div>
<div id="mlist"></div><div id="chat"></div><div id="mv"></div></div></div><div id="panel"><div class="in"><h2 id="pt"></h2><div class="who" id="pw"></div><div id="steps"></div></div></div></div>
<script>
const D=/*DATA*/null;
const NS="http://www.w3.org/2000/svg",svg=document.getElementById("svg"),E=document.getElementById("edges"),N=document.getElementById("nodes");
const pos={},circ={},lbl={},db={};document.getElementById("led").textContent=D.ledger;
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p&&p.appendChild(e);return e}
let bookC,bookPos={x:500,y:500};
function setup(){E.innerHTML="";N.innerHTML="";
 if(D.book){bookC=el("circle",{cx:500,cy:500,r:26,fill:"#1e293b",stroke:"var(--wait)","stroke-width":1.5,class:"node book"},N);
  const t=el("text",{x:500,y:545,"text-anchor":"middle",class:"lbl booklbl"},N);t.textContent=`offer book · ${D.book.listings} listings · root on ledger`}for(const n of D.nodes){pos[n.id]=n;db[n.id]=0;
 circ[n.id]=el("circle",{cx:n.x,cy:n.y,r:6,fill:n.org?"var(--org)":"var(--node)",stroke:"#4b5563","stroke-width":1,class:"node"},N);
 const a=Math.atan2(n.y-500,n.x-500),lx=500+435*Math.cos(a),ly=500+435*Math.sin(a);
 lbl[n.id]=el("text",{x:lx,y:ly+4,"text-anchor":lx<500?"end":"start",class:"lbl"},N);lbl[n.id].textContent=n.id}}
const C={ok:"var(--ok)",bad:"var(--bad)",wait:"var(--wait)"};
function viaBook(e){const a=pos[e.b],b=pos[e.s];if(!a||!b)return;const B=bookPos;
 // every trade goes through the shared offer book: the buyer's agent queries it, the match leads to the seller
 const d=`M${a.x},${a.y} L${B.x},${B.y} L${b.x},${b.y}`;
 const q=el("path",{d:`M${a.x},${a.y} L${B.x},${B.y}`,stroke:"var(--wait)","stroke-dasharray":"3 4",class:"edge"},E);
 const p=el("path",{d,stroke:C[e.c],class:"edge",opacity:0},E);
 const dot=el("circle",{r:4,fill:C[e.c]},E);const m=el("animateMotion",{dur:".7s",path:d,fill:"freeze"},dot);
 setTimeout(()=>{p.setAttribute("opacity",.9);m.beginElement&&m.beginElement()},140);
 if(bookC){bookC.setAttribute("stroke-width",3.5);setTimeout(()=>bookC.setAttribute("stroke-width",1.5),260)}
 setTimeout(()=>{q.style.opacity=0;p.style.opacity=0;dot.remove()},900);setTimeout(()=>{q.remove();p.remove()},2100)}
function flash(e,keep){const a=pos[e.b],b=pos[e.s];if(!a||!b)return;
 if(!keep)return viaBook(e);
 const mx=(a.x+b.x)/2*0.45+275,my=(a.y+b.y)/2*0.45+275;
 const p=el("path",{d:`M${b.x},${b.y} Q${mx},${my} ${a.x},${a.y}`,stroke:C[e.c],class:"edge"},E);
 if(!keep)setTimeout(()=>p.style.opacity=0,700),setTimeout(()=>p.remove(),2000);return p}
function grow(e){if(!e.rows)return;db[e.b]+=e.rows;circ[e.b].setAttribute("r",(6+Math.sqrt(db[e.b])*1.6).toFixed(1))}
let vb=[0,0,1000,1000],timers=[],raf;
function zoomTo(t,ms){const s=[...vb],t0=performance.now();cancelAnimationFrame(raf);
 return new Promise(r=>{function f(now){const k=Math.min(1,(now-t0)/ms),q=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
 vb=s.map((v,i)=>v+(t[i]-v)*q);svg.setAttribute("viewBox",vb.join(" "));k<1?raf=requestAnimationFrame(f):r()}raf=requestAnimationFrame(f)})}
const wait=ms=>new Promise(r=>timers.push(setTimeout(r,ms)));
function tmp(){const g=el("g",{},E);return g}
function line(g,a,b,c,dash,w){return el("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:c,"stroke-width":w||1.6,"stroke-dasharray":dash||"",opacity:.9},g)}
function hot(id,on){circ[id]&&circ[id].classList.toggle("hot",on);lbl[id]&&lbl[id].classList.toggle("hot",on)}
function addStep(st){const box=document.getElementById("steps"),d=document.createElement("div");d.className="step "+(st.tone||"");
 d.innerHTML=`<div class="k"><span></span><em></em></div><div class="v"></div>`;d.querySelector(".k span").textContent=st.k;
 d.querySelector(".k em").textContent=st.by||"";d.querySelector(".v").textContent=st.v;
 if(st.table){const t=document.createElement("table");t.innerHTML="<tr><th>seller</th><th>grade</th><th>ask</th><th>quality</th><th>price</th><th>track</th><th>score</th></tr>";
  for(const r of st.table){const tr=document.createElement("tr");for(const v of [r.seller,r.grade,r.ask,r.quality,r.price,r.track,r.score]){const td=document.createElement("td");td.textContent=v;tr.appendChild(td)}t.appendChild(tr)}
  d.querySelector(".v").textContent="";d.querySelector(".v").appendChild(t)}
 for(const u of st.urls||[]){const l=document.createElement("a");l.href=u;l.target="_blank";l.textContent=" explorer ↗";d.querySelector(".v").appendChild(l)}
 box.appendChild(d);requestAnimationFrame(()=>d.classList.add("on"));box.scrollTop=box.scrollHeight}
const ST={settled:"ok",settled_unfit:"bad",refused:"bad",declined:"bad",awaiting_owner:"wait",no_deal:"bad"};
const M=document.getElementById("modal");document.getElementById("mx").onclick=()=>M.classList.remove("on");
function verdicts(c){return `buyer: ${c.verdicts.buyer} · seller: ${c.verdicts.seller}`}
async function chat(c,animate){const box=document.getElementById("chat");box.innerHTML="";document.getElementById("mlist").innerHTML="";
 document.getElementById("mt").textContent=`${c.buyer} ⇄ ${c.seller} · ${c.columns.join(", ")}`;
 document.getElementById("ms").textContent=`need ${c.need} · contract ${c.contract||"none"} · ${c.status}`;
 document.getElementById("mv").textContent=verdicts(c)+(c.txs&&c.txs.escrow_create?` · EscrowCreate ${c.txs.escrow_create.slice(0,16)}… · EscrowFinish ${(c.txs.escrow_finish||"").slice(0,16)}…`:"");
 M.classList.add("on");
 for(const t of c.turns){const d=document.createElement("div");d.className="turn "+t.speaker;
  d.innerHTML=`<div class="who"></div><div class="msg"></div><div class="why"></div><div class="cks"></div>`;
  d.querySelector(".who").textContent=`${t.speaker==="buyer"?c.buyer+"'s agent":t.speaker==="seller"?c.seller+"'s agent":t.speaker}${t.layer?" · "+t.layer:""}`;
  d.querySelector(".msg").textContent=t.message;d.querySelector(".why").textContent=t.reasoning||"";
  for(const k of t.checks||[]){const s=document.createElement("span");s.className="chk "+(k.ok?"ok":"no");s.textContent=(k.ok?"✓ ":"✗ ")+k.name+(k.detail?": "+k.detail:"");d.querySelector(".cks").appendChild(s)}
  box.appendChild(d);requestAnimationFrame(()=>d.classList.add("on"));box.scrollTop=box.scrollHeight;if(animate)await wait(900)}}
function list(){const L=document.getElementById("mlist");L.innerHTML="";document.getElementById("chat").innerHTML="";
 document.getElementById("mt").textContent=`${D.contracts.length} contracts`;document.getElementById("ms").textContent="click one to read the two agents' conversation";
 document.getElementById("mv").textContent="";
 D.contracts.forEach(c=>{const r=document.createElement("div");r.className="row";
  r.innerHTML=`<span></span><span></span><span class="st"></span>`;r.children[0].textContent=`${c.buyer} ⇄ ${c.seller}`;
  r.children[1].textContent=c.columns.join(", ");r.children[2].textContent=c.status;r.children[2].classList.add(ST[c.status]||"bad");
  r.onclick=()=>chat(c,false);L.appendChild(r)});M.classList.add("on")}
document.getElementById("list").onclick=list;
async function spotlight(s){const a=pos[s.b],b=pos[s.s],B=bookPos,g=tmp(),P=document.getElementById("panel");
 svg.classList.add("dim");hot(s.b,true);document.getElementById("pt").textContent=s.label;
 document.getElementById("pw").textContent=`${s.b}'s agent looking for data; ${s.s}'s agent selling`;
 document.getElementById("steps").innerHTML="";P.classList.add("on");await wait(700);
 const fan=[],labels=[];
 for(const st of s.steps){const n=st.k[0];addStep(st);
  if(n==="1"){circ[s.b].setAttribute("stroke","#fff");}
  if(n==="2"){line(g,a,B,"var(--wait)","4 4",2);bookC.classList.add("hot")}
  if(n==="3"){for(const c of s.sampled){const q=pos[c.s];if(!q)continue;fan.push([c.s,line(g,B,q,c.ok?"#64748b":"var(--bad)","",1)]);hot(c.s,true);await wait(Math.max(15,500/s.sampled.length))}}
  if(n==="4"){const top=new Set(s.top.map(x=>x.s));for(const [id,l] of fan){if(!top.has(id)){l.setAttribute("opacity",.08);hot(id,false)}else{l.setAttribute("stroke","var(--ok)");l.setAttribute("stroke-width",2.4)}}
   for(const t of s.top){const q=pos[t.s];if(!q)continue;const tx=el("text",{x:q.x,y:q.y-14,"text-anchor":"middle",class:"score"},g);tx.textContent=t.score}}
  if(n==="5"){line(g,a,b,"var(--wait)","6 5",3)}
  if(n==="6"){for(const [id,l] of fan){if(id!==s.s){l.setAttribute("opacity",.05);hot(id,false)}}hot(s.s,true);
   const sw=innerWidth-Math.min(480,.45*innerWidth),ar=sw/innerHeight,cx=(a.x+b.x)/2,cy=(a.y+b.y)/2;
   const w=Math.max(Math.abs(a.x-b.x)+200,(Math.abs(a.y-b.y)+200)*ar),h=w/ar;
   await zoomTo([cx-w/2,cy-h/2,w,h],1600);flash({b:s.b,s:s.s,c:st.tone||"ok"},true).classList.add("final")}
  await wait(st.table?2600:1900)}
 await wait(1500);if(s.trace!=null&&D.contracts[s.trace]){await chat(D.contracts[s.trace],true);await wait(3000);M.classList.remove("on")}
 await wait(800);P.classList.remove("on");await zoomTo([0,0,1000,1000],1400);
 g.remove();E.querySelectorAll(".final").forEach(x=>x.remove());svg.classList.remove("dim");bookC.classList.remove("hot");
 circ[s.b].setAttribute("stroke","#4b5563");for(const id in circ)hot(id,false)}
async function run(){timers.forEach(clearTimeout);timers=[];document.getElementById("panel").classList.remove("on");
 vb=[0,0,1000,1000];svg.setAttribute("viewBox","0 0 1000 1000");setup();
 const c={T:0,S:0,R:0},t0=performance.now(),dt=Math.max(40,Math.min(140,14000/D.events.length));
 const tick=setInterval(()=>document.getElementById("cE").textContent=((performance.now()-t0)/1000).toFixed(1),100);
 for(const e of D.events){flash(e);grow(e);c.T++;if(e.st==="settled")c.S++;else if(e.c==="bad")c.R++;
  cT.textContent=c.T;cS.textContent=c.S;cR.textContent=c.R;await wait(dt)}
 await wait(1500);for(const s of D.spotlight)await spotlight(s);clearInterval(tick)}
document.getElementById("play").onclick=run;run();
</script></body></html>"""
