#!/usr/bin/env python3
"""Build the voice-agent audit artifact page from curated JSON files."""
import json
import html as htmlmod

import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT = os.path.join(ROOT, "audit")
CUR = os.path.join(AUDIT, "curated")
OUT = os.path.join(AUDIT, "voice-agent-audit.html")

SECTIONS = [
    {
        "key": "brooks-slack-voice",
        "title": "Slack voice gate",
        "slug": "slack",
        "kicker": "brooks-slack-voice",
        "what": "Judges every agent-drafted Slack message against Brooks's real recent posts in the exact destination channel or DM before it can be sent. It polices mechanical tells (em dashes vs the ASCII “ - ” connector, AI-speak phrases), per-channel register and casing, his bullet templates, point-first openers, and hedging or summarizing closers.",
        "better": "Every failed draft in the history was fixed and posted (16 of 16 traced to a real Slack post; the rows below are those chains). The effect is structural, not cosmetic: prose walls and “Three things to know” scaffolds become the per-channel templates — the “&lt;!here&gt; … What's new:” bullet format in #fc-announcements, @-mention-led ask bullets in #dev-ops — jargon gets swapped for plain words, and AI-flavored openers/closers get cut. The posted versions read more like real Brooks messages. Caveats: the gate tightened between July and August (em dashes passed in July, auto-fail by August), and its strictest rounds police shape — dash characters, list markers, casing — over substance; one near-verbatim user-dictated draft failed purely on two casing tells.",
    },
    {
        "key": "comment-adversary",
        "title": "Comment adversary",
        "slug": "comment",
        "kicker": "comment-adversary",
        "what": "Adversarial gate over code comments in just-edited files. Rule 1 scrubs process artifacts — ticket numbers, slice/phase labels, agent and person names, dated decisions. Rule 2 enforces copy mechanics: active voice, no all-caps emphasis, no ungrounded shorthand (“HOST-INJECTED”, “LEGACY”), no inverted constructions, no filler narration.",
        "better": "Mostly yes. Every row is verified applied to the files, but the fuller sample shows partial application is common — callers take the Rule-1 deletion while keeping their own wording or emphasis (“host-adapted”, the “legacy full profile” phrasing, retained all-caps), a healthy sign the gate isn't blindly obeyed. The best rewrites convert a ticket pointer or label into the durable invariant it stood for — “keep it LEGACY” becomes the exact route regression at stake. Weak edges: occasional hair-splitting on borderline terms, and Rule 1 fixes can balloon a one-line comment because the context the ticket number carried now has to be inlined.",
    },
    {
        "key": "process-scrub-reviewer",
        "title": "Process-scrub reviewer",
        "slug": "scrub",
        "kicker": "process-scrub-reviewer",
        "what": "PASS/FAIL gate over the prose in a diff — comments, docs, commit messages, PR bodies. Its dominant flags: agentless passive voice, change narration anchored to the edit (“as it does today”, “converted”), coined or ungrounded referents, tracker vocabulary (“separate tickets”), filler, and double negatives. It also fact-checks prose claims against the code.",
        "better": "Largely yes — every row is verified applied, essentially all adopted verbatim (via file edits 3–7 minutes after the verdict, or corrected commit messages), so its rewrites function as drop-in text, not advice. Most name the actor, survive loss of project history, and get shorter. Its highest-value behavior is the fact-checking: it catches claims that are literally false or overclaim what a test covers. The weak edge is pedantry — splitting short semicolon-joined TODO imperatives and banning “-ing” forms sometimes stiffens prose with no clarity gain — and the tail shows two limits: it sometimes re-flags its own earlier rewrite once the edit context is gone, and callers occasionally cure an overclaim by changing the code instead of the prose.",
    },
    {
        "key": "ste100-validator",
        "title": "STE-100 validator",
        "slug": "ste",
        "kicker": "ste100-validator",
        "what": "Pre-publication gate that validates docs, retros, module headers, and questions to colleagues against ASD-STE100 Simplified Technical English. Dominant targets: figurative verbs (“lives”, “ships”, “dies”, “is green”), synonym drift against one-term-per-concept, dropped articles, noun clusters, and compound sentences split to one topic or instruction each.",
        "better": "For controlled documentation, yes — every row is verified applied to the docs (nearly all verbatim; one shows the real applied paragraph split rather than the gate's instruction), with confirmation passes over the corrected text. The ambiguity catches (“read as” vs a data read) are real, and actor-naming fixes add accountability. The cost is voice: punchy compressed phrases get flatter and splits introduce stilted connectors, so it suits reference docs and retros better than narrative prose. It is context-aware — it checks which verb the doc already uses and exempts technical names and code.",
    },
]


import re
import statistics

AGENT_SHORT = {
    "brooks-slack-voice": ("slack", "Slack voice"),
    "comment-adversary": ("comment", "Comment adversary"),
    "process-scrub-reviewer": ("scrub", "Process scrub"),
    "ste100-validator": ("ste100", "STE-100"),
}

URL_RE = re.compile(r"<https?[^>\s|]*(\|[^>]*)?>|https?://\S+")
MENTION_RE = re.compile(r"<[!@#][^>]*>")
CODE_RE = re.compile(r"`[^`]+`")
BULLET_RE = re.compile(r"^\s*([•◦\-\*]|\d+[.)])\s+")

JARGON_TOKEN_RES = [
    re.compile(r"[a-z][A-Z]"),                  # camelCase
    re.compile(r"\w_\w"),                       # snake_case
    re.compile(r"[a-z0-9]+-[a-z0-9]+-[a-z0-9]"),  # kebab, 2+ hyphens
    re.compile(r"^\W*[A-Z]{2,}\W*$"),           # ALL-CAPS acronym
    re.compile(r"(?=.*[A-Za-z])(?=.*\d)"),      # letter+digit mix
    re.compile(r"[\w.]+/[\w.]+"),               # path segment
    re.compile(r"^#\d+$"),                      # ticket ref
]


def clean(t):
    return (t or "").replace("\\n", "\n").replace('\\"', '"')


def strip_noise(t):
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    return t


def toks(t):
    return [w for w in re.split(r"\s+", t) if w and re.search(r"[\w`]", w)]


def word_count(t):
    return len(toks(strip_noise(t)))


def sentence_lengths(t):
    t = strip_noise(t)
    out = []
    for line in t.split("\n"):
        line = BULLET_RE.sub("", line.strip())
        if not line:
            continue
        for seg in re.split(r"(?<=[.!?])\s+", line):
            n = len(toks(seg))
            if n:
                out.append(n)
    return out


def paragraph_lengths(t):
    t = strip_noise(t)
    paras = []
    for block in re.split(r"\n\s*\n", t):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        bullets = [l for l in lines if BULLET_RE.match(l)]
        if len(bullets) >= 2:
            paras.extend(lines)
        else:
            paras.append(" ".join(lines))
    return [len(toks(p)) for p in paras if toks(p)]


def jargon_density(t):
    t = strip_noise(t)
    code_spans = len(CODE_RE.findall(t))
    t2 = CODE_RE.sub(" CODESPAN ", t)
    words = toks(t2)
    if not words:
        return 0.0
    jargon = code_spans
    for w in words:
        if w == "CODESPAN":
            continue
        core = w.strip(".,;:()[]{}\"'—")
        if not core:
            continue
        if any(rx.search(core) for rx in JARGON_TOKEN_RES):
            jargon += 1
    return round(jargon / len(words) * 100, 1)


def mean(xs):
    return statistics.fmean(xs) if xs else 0.0


METRIC_DEFS = [
    {
        "key": "words",
        "title": "Word count",
        "unit": "words",
        "summary_kind": "pct",
        "fn": lambda t: word_count(t),
        "caption": "Words per message or passage; URLs and Slack mentions excluded. Summary bar = mean of each pair's % change after revision.",
    },
    {
        "key": "sentence",
        "title": "Sentence length",
        "unit": "words / sentence",
        "summary_kind": "pct",
        "fn": lambda t: round(mean(sentence_lengths(t)), 1),
        "caption": "Mean words per sentence; bullet lines count as sentences. Summary bar = mean of each pair's % change after revision.",
    },
    {
        "key": "jargon",
        "title": "Jargon density",
        "unit": "jargon tokens / 100 words",
        "summary_kind": "pp",
        "fn": lambda t: jargon_density(t),
        "caption": "Provisional measure, pending your rev-2 research: backticked spans, camelCase / snake_case / multi-hyphen identifiers, ALL-CAPS acronyms, letter-digit mixes, file paths, and #ticket refs per 100 words. Summary bar = mean change in density, percentage points (not %), since many passages start at zero.",
    },
    {
        "key": "paragraph",
        "title": "Paragraph length",
        "unit": "words / paragraph",
        "summary_kind": "pct",
        "fn": lambda t: round(mean(paragraph_lengths(t)), 1),
        "caption": "Mean words per paragraph; blank lines split paragraphs and each bullet line counts as its own. Summary bar = mean of each pair's % change after revision.",
    },
    {
        "key": "cpidr",
        "title": "Idea density (CPIDR)",
        "unit": "propositions / word",
        "summary_kind": "abs",
        "fn": None,
        "band": [0.4, 0.6],
        "caption": "Propositional idea density: propositions per word, where propositions are counted from POS predicating categories (verbs, adjectives, adverbs, prepositions, conjunctions) with CPIDR 3's adjustment rules — computed with the ideadensity port of CPIDR 3.2 (Brown et al. 2008; r = 0.97 against human consensus). Typical English runs 0.4–0.6 (shaded on the raw chart); higher reads as telegraphese. Summary bar = mean change in density, absolute (a ±0.05 move is large).",
    },
]

CPIDR_PATH = os.path.join(AUDIT, "raw", "cpidr_scores.json")
try:
    with open(CPIDR_PATH) as _f:
        CPIDR_SCORES = json.load(_f)
except OSError:
    CPIDR_SCORES = None


def compute_metrics(datasets):
    metrics = {}
    for md in METRIC_DEFS:
        if md["fn"] is None and not CPIDR_SCORES:
            continue
        per_agent = []
        pts = []
        for full, (short, label) in AGENT_SHORT.items():
            deltas = []
            for idx, p in enumerate(datasets[full]["pairs"]):
                if md["fn"] is None:
                    rec = CPIDR_SCORES[full][idx]
                    b, a = rec["b"], rec["f"]
                else:
                    b = md["fn"](clean(p.get("before")))
                    a = md["fn"](clean(p.get("after")))
                pts.append({
                    "a": short, "b": b, "f": a,
                    "d": (p.get("timestamp") or "")[5:10],
                    "c": (p.get("context") or "")[:70],
                })
                if md["summary_kind"] == "pct":
                    if b:
                        deltas.append((a - b) / b * 100)
                else:
                    deltas.append(a - b)
            digits = 3 if md["summary_kind"] == "abs" else 1
            per_agent.append({
                "agent": short, "label": label,
                "val": round(mean(deltas), digits), "n": len(deltas),
            })
        metrics[md["key"]] = {
            "title": md["title"], "unit": md["unit"],
            "kind": md["summary_kind"], "per_agent": per_agent, "pts": pts,
        }
        if md.get("band"):
            metrics[md["key"]]["band"] = md["band"]
    return metrics


def esc(s):
    if s is None:
        return ""
    s = s.replace("\\n", "\n").replace('\\"', '"')
    return htmlmod.escape(s)


def fmt_date(ts):
    if not ts:
        return ""
    return ts[:10]


def chip(label, cls="chip"):
    return f'<span class="{cls}">{label}</span>'


def stat_chips(key, stats):
    out = [chip(f"{stats['total_invocations']} invocations")]
    if "pass" in stats:
        out.append(chip(f"{stats['pass']} PASS", "chip chip-pass"))
    if "pass_first_try" in stats:
        out.append(chip(f"{stats['pass_first_try']} passed first try", "chip chip-pass"))
    if "fail" in stats:
        out.append(chip(f"{stats['fail']} FAIL", "chip chip-fail"))
    if "fail_traced_to_post" in stats:
        out.append(chip(f"{stats['fail_traced_to_post']} failed → fixed → posted", "chip chip-fail"))
    if "fail_never_posted" in stats:
        out.append(chip(f"{stats['fail_never_posted']} failed, never posted"))
    if stats.get("pairs_verified_applied"):
        out.append(chip(f"{stats['pairs_verified_applied']} fixes verified applied"))
    if stats.get("sentences_checked_total"):
        out.append(chip(f"{stats['sentences_checked_total']:,} sentences checked"))
    return "\n".join(out)


def pair_card(p, sec_key):
    before = (p.get("before") or "").replace("\\n", "\n").replace('\\"', '"')
    after = (p.get("after") or "").replace("\\n", "\n").replace('\\"', '"')
    verdict = p.get("verdict") or ""
    rule = p.get("rule") or ""
    meta_left = f"{fmt_date(p.get('timestamp'))} · {esc(p.get('project', ''))}"
    context = esc(p.get("context", ""))
    note = esc(p.get("note", ""))

    rule_chip = f'<span class="rule">{esc(rule)}</span>' if rule else ""
    verdict_chip = ""
    if verdict:
        vcls = "v-pass" if verdict.upper().startswith("PASS") else "v-fail"
        verdict_chip = f'<span class="verdict {vcls}">{esc(verdict)}</span>'

    if sec_key == "brooks-slack-voice":
        before_label = "Before — first draft"
        after_label = "After — message as posted"
    else:
        before_label = "Before — original prose"
        after_label = "After — as applied"

    body = f'''<div class="cols">
  <div class="cell cell-before">
    <div class="cell-label label-before">{before_label}</div>
    <div class="cell-text">{htmlmod.escape(before)}</div>
  </div>
  <div class="cell cell-after">
    <div class="cell-label label-after">{after_label}</div>
    <div class="cell-text">{htmlmod.escape(after)}</div>
  </div>
</div>'''

    return f'''<article class="pair">
  <div class="pair-meta">
    <span class="meta-left">{meta_left}</span>
    <span class="meta-context">{context}</span>
    <span class="meta-right">{rule_chip}{verdict_chip}</span>
  </div>
  {body}
  <p class="pair-note">{note}</p>
</article>'''


CHART_CSS = '''
:root { --s-before:#eb6834; --s-after:#2a78d6; --s-bar:#2a78d6; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --s-before:#d95926; --s-after:#3987e5; --s-bar:#3987e5; }
}
:root[data-theme="dark"] { --s-before:#d95926; --s-after:#3987e5; --s-bar:#3987e5; }
.tabs { display:flex; gap:8px; margin-top:22px; border-bottom:1px solid var(--line); }
.tabbtn { appearance:none; background:none; border:none; border-bottom:2px solid transparent; color:var(--muted); font:600 0.95rem/1.2 "Avenir Next",-apple-system,sans-serif; padding:10px 14px; cursor:pointer; }
.tabbtn.on { color:var(--accent); border-bottom-color:var(--accent); }
.tabbtn:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.stats-intro { margin-top:26px; max-width:74ch; color:var(--muted); font-size:0.92rem; }
.stat-sec { margin-top:40px; background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:20px 22px; }
.stat-sec h2 { font-size:1.2rem; font-weight:600; }
.stat-cap { color:var(--muted); font-size:0.85rem; max-width:74ch; margin:6px 0 14px; }
.stat-head { display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
.seg { display:inline-flex; border:1px solid var(--line); border-radius:7px; overflow:hidden; }
.seg button { appearance:none; border:none; background:var(--surface); color:var(--muted); font:600 0.78rem/1.2 -apple-system,sans-serif; padding:7px 14px; cursor:pointer; }
.seg button.on { background:var(--accent-soft); color:var(--accent); }
.seg button:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.legend { display:flex; gap:14px; font-size:0.78rem; color:var(--muted); align-items:center; }
.legend[hidden] { display:none; }
.lg { display:inline-flex; gap:6px; align-items:center; }
.lg svg { display:block; }
.lg-before { fill:var(--surface); stroke:var(--s-before); stroke-width:2; }
.lg-after { fill:var(--s-after); stroke:var(--surface); stroke-width:2; }
.chart { margin-top:10px; }
.chart svg { width:100%; height:auto; display:block; }
.chart .grid { stroke:var(--line); stroke-width:1; }
.chart .axis { stroke:var(--muted); stroke-width:1; }
.chart .tick, .chart .xlab2 { fill:var(--muted); font:0.68rem/1.2 -apple-system,sans-serif; font-variant-numeric:tabular-nums; }
.chart .xlab { fill:var(--ink); font:600 0.74rem/1.2 -apple-system,sans-serif; }
.chart .vlabel { fill:var(--ink); font:600 0.72rem/1.2 -apple-system,sans-serif; font-variant-numeric:tabular-nums; }
.chart .bar { fill:var(--s-bar); }
.chart .dot-before { fill:var(--surface); stroke:var(--s-before); stroke-width:2; }
.chart .dot-after { fill:var(--s-after); stroke:var(--surface); stroke-width:2; }
.chart .band { fill:var(--accent-soft); opacity:0.55; }
.tip { position:fixed; z-index:10; background:var(--surface); border:1px solid var(--line); border-radius:7px; padding:8px 11px; font-size:0.78rem; color:var(--ink); max-width:280px; pointer-events:none; box-shadow:0 4px 14px rgba(0,0,0,0.12); }
.tipc { color:var(--muted); }
.dtable { margin-top:12px; }
.dtable summary { cursor:pointer; color:var(--muted); font-size:0.8rem; }
.tblwrap { overflow-x:auto; margin-top:8px; }
.dtable table { border-collapse:collapse; font-size:0.78rem; font-variant-numeric:tabular-nums; width:100%; }
.dtable th, .dtable td { text-align:left; padding:4px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }
.dtable td.num, .dtable th.num { text-align:right; }
.dtable td.ctx { white-space:normal; min-width:200px; color:var(--muted); }
.rule-meta { display:flex; gap:16px; flex-wrap:wrap; font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:0.7rem; color:var(--muted); margin:8px 0 4px; }
.rule-grid { display:grid; grid-template-columns:1.45fr 1fr; gap:18px; margin-top:14px; }
.rule-col h3 { font-size:0.78rem; letter-spacing:0.07em; text-transform:uppercase; color:var(--accent); font-weight:600; margin-bottom:10px; }
.rulelist { margin:0; padding-left:18px; font-size:0.88rem; }
.rulelist li { margin-bottom:8px; }
.rulelist code { font-size:0.8em; background:var(--surface-2); padding:1px 4px; border-radius:4px; }
.quote { color:var(--accent); font-style:italic; }
@media (max-width:760px){ .rule-grid { grid-template-columns:1fr; } }
'''

STATS_JS = '''
(function(){
  const T=document.createElement('div'); T.className='tip'; T.hidden=true; document.body.appendChild(T);
  function tip(html,x,y){ T.innerHTML=html; T.hidden=false; const r=T.getBoundingClientRect();
    let L=x+12,U=y-r.height-10; if(L+r.width>innerWidth-8)L=x-r.width-12; if(U<8)U=y+14;
    T.style.left=L+'px'; T.style.top=U+'px'; }
  function untip(){ T.hidden=true; }
  const NS='http://www.w3.org/2000/svg';
  function el(n,at){ const e=document.createElementNS(NS,n); for(const k in at)e.setAttribute(k,at[k]); return e; }
  function niceStep(span,n){ const raw=span/n,mag=Math.pow(10,Math.floor(Math.log10(raw))),r=raw/mag;
    return (r<=1?1:r<=2?2:r<=5?5:10)*mag; }
  function ticks(min,max,n){ const s=niceStep((max-min)||1,n); const t=[];
    for(let v=Math.ceil(min/s)*s; v<=max+1e-9; v+=s) t.push(Math.round(v*100)/100); return t; }
  const AGENTS=[["slack","Slack voice"],["comment","Comment adversary"],["scrub","Process scrub"],["ste100","STE-100"]];
  function fmtVal(v,kind){
    if(kind==='abs'){ const s=(Math.round(v*1000)/1000).toString(); return (v>0?'+':'')+s; }
    const s=(Math.round(v*10)/10).toLocaleString();
    return (v>0?'+':'')+s+(kind==='pct'?'%':kind==='pp'?' pp':''); }

  function barChart(host,m){
    host.innerHTML='';
    const W=860,H=330,L=64,R=16,TP=28,B=56,pw=W-L-R,ph=H-TP-B;
    const vals=m.per_agent.map(d=>d.val);
    let lo=Math.min(0,...vals),hi=Math.max(0,...vals);
    const pad=((hi-lo)*0.15)||1; if(lo<0)lo-=pad; if(hi>0)hi+=pad; if(lo===hi)hi=lo+1;
    const y=v=>TP+ph*(1-(v-lo)/(hi-lo));
    const svg=el('svg',{viewBox:'0 0 '+W+' '+H,role:'img'});
    ticks(lo,hi,5).forEach(t=>{ if(t===0)return;
      svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(t),y2:y(t),class:'grid'}));
      const tx=el('text',{x:L-8,y:y(t)+4,class:'tick','text-anchor':'end'}); tx.textContent=fmtVal(t,m.kind); svg.appendChild(tx); });
    svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(0),y2:y(0),class:'axis'}));
    const tz=el('text',{x:L-8,y:y(0)+4,class:'tick','text-anchor':'end'}); tz.textContent='0'; svg.appendChild(tz);
    const slot=pw/m.per_agent.length,bw=24;
    m.per_agent.forEach((d,i)=>{
      const cx=L+slot*i+slot/2,v=d.val,y0=y(0),y1=y(v);
      const h=Math.max(2,Math.abs(y1-y0)),top=Math.min(y0,y1),r=4,x0=cx-bw/2;
      let p;
      if(v>=0){ p='M'+x0+','+(top+h)+' V'+(top+r)+' Q'+x0+','+top+' '+(x0+r)+','+top+' H'+(x0+bw-r)+' Q'+(x0+bw)+','+top+' '+(x0+bw)+','+(top+r)+' V'+(top+h)+' Z'; }
      else { p='M'+x0+','+top+' V'+(top+h-r)+' Q'+x0+','+(top+h)+' '+(x0+r)+','+(top+h)+' H'+(x0+bw-r)+' Q'+(x0+bw)+','+(top+h)+' '+(x0+bw)+','+(top+h-r)+' V'+top+' Z'; }
      svg.appendChild(el('path',{d:p,class:'bar'}));
      const lb=el('text',{x:cx,y:v>=0?y1-7:y1+15,class:'vlabel','text-anchor':'middle'}); lb.textContent=fmtVal(v,m.kind); svg.appendChild(lb);
      const a1=el('text',{x:cx,y:H-30,class:'xlab','text-anchor':'middle'}); a1.textContent=d.label; svg.appendChild(a1);
      const a2=el('text',{x:cx,y:H-14,class:'xlab2','text-anchor':'middle'}); a2.textContent='n='+d.n; svg.appendChild(a2);
      const hit=el('rect',{x:L+slot*i,y:TP,width:slot,height:ph,fill:'transparent'});
      hit.addEventListener('pointermove',e=>tip('<b>'+d.label+'</b><br>mean '+fmtVal(v,m.kind)+' · '+d.n+' pairs',e.clientX,e.clientY));
      hit.addEventListener('pointerleave',untip); svg.appendChild(hit);
    });
    host.appendChild(svg);
  }

  function stripChart(host,m){
    host.innerHTML='';
    const W=860,H=380,L=64,R=16,TP=24,B=60,pw=W-L-R,ph=H-TP-B;
    const vals=m.pts.flatMap(p=>[p.b,p.f]);
    const hi=(Math.max(...vals)||1)*1.08, lo=0;
    const y=v=>TP+ph*(1-(v-lo)/(hi-lo));
    const svg=el('svg',{viewBox:'0 0 '+W+' '+H,role:'img'});
    if(m.band){
      svg.appendChild(el('rect',{x:L,y:y(m.band[1]),width:pw,height:y(m.band[0])-y(m.band[1]),class:'band'}));
      const bl=el('text',{x:W-R-6,y:y(m.band[1])+14,class:'xlab2','text-anchor':'end'});
      bl.textContent='typical English '+m.band[0]+'–'+m.band[1]; svg.appendChild(bl);
    }
    ticks(lo,hi,5).forEach(t=>{ svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(t),y2:y(t),class:'grid'}));
      const tx=el('text',{x:L-8,y:y(t)+4,class:'tick','text-anchor':'end'}); tx.textContent=t.toLocaleString(); svg.appendChild(tx); });
    svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(0),y2:y(0),class:'axis'}));
    const gw=pw/AGENTS.length, slot=gw/2;
    AGENTS.forEach((ag,gi)=>{
      const key=ag[0],label=ag[1],gx=L+gw*gi;
      ['before','after'].forEach((phase,si)=>{
        const t1=el('text',{x:gx+slot*si+slot/2,y:H-36,class:'xlab2','text-anchor':'middle'}); t1.textContent=phase; svg.appendChild(t1);
      });
      const t0=el('text',{x:gx+gw/2,y:H-16,class:'xlab','text-anchor':'middle'}); t0.textContent=label; svg.appendChild(t0);
      if(gi>0) svg.appendChild(el('line',{x1:gx,x2:gx,y1:TP,y2:TP+ph,class:'grid'}));
      m.pts.filter(p=>p.a===key).forEach((p,i)=>{
        [['b',0],['f',1]].forEach(pair=>{
          const f2=pair[0],si=pair[1],cx=gx+slot*si+slot/2;
          const j=((((i*2654435761)>>>0)%97)/97-0.5)*slot*0.55;
          const v=p[f2];
          svg.appendChild(el('circle',{cx:cx+j,cy:y(v),r:4.5,class:f2==='b'?'dot-before':'dot-after'}));
          const hit=el('circle',{cx:cx+j,cy:y(v),r:9,fill:'transparent'});
          hit.addEventListener('pointermove',e=>tip('<b>'+label+'</b> · '+p.d+'<br>'+(f2==='b'?'before':'after')+': '+v.toLocaleString()+' '+m.unit+'<br><span class="tipc">'+p.c+'</span>',e.clientX,e.clientY));
          hit.addEventListener('pointerleave',untip);
          svg.appendChild(hit);
        });
      });
    });
    host.appendChild(svg);
  }

  for(const key in DATA){
    barChart(document.getElementById('c-'+key+'-summary'),DATA[key]);
    stripChart(document.getElementById('c-'+key+'-raw'),DATA[key]);
  }
  document.querySelectorAll('.seg').forEach(seg=>{
    seg.addEventListener('click',e=>{
      const b=e.target.closest('button'); if(!b)return;
      seg.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
      const sec=seg.closest('.stat-sec'),v=b.dataset.view;
      sec.querySelectorAll('.chart').forEach(c=>{c.hidden=!c.id.endsWith('-'+v);});
      const lg=sec.querySelector('.legend'); if(lg)lg.hidden=(v!=='raw');
    });
  });
  const TABS=['pairs','stats','rules'];
  document.querySelectorAll('.tabbtn').forEach(b=>b.addEventListener('click',()=>{
    document.querySelectorAll('.tabbtn').forEach(x=>x.classList.toggle('on',x===b));
    TABS.forEach(t=>{const el=document.getElementById('tab-'+t); if(el)el.hidden=b.dataset.tab!==t;});
  }));
  if(location.hash==='#stats'||location.hash==='#stats-raw'){
    document.querySelector('.tabbtn[data-tab="stats"]').click();
    if(location.hash==='#stats-raw')
      document.querySelectorAll('.seg button[data-view="raw"]').forEach(b=>b.click());
  }
  if(location.hash==='#rules'){
    document.querySelector('.tabbtn[data-tab="rules"]').click();
  }
})();
'''


RULES_HTML = '''
<p class="stats-intro">What each gate is instructed to check and how it reaches a verdict, distilled from the actual agent definition files on this machine (paths cited per section; read 2026-08-17). All four are read-only adversarial reviewers: they return verdicts and prescribed fixes, never edit or post anything themselves.</p>

<section class="stat-sec" id="rules-slack">
  <p class="kicker">brooks-slack-voice</p>
  <h2>Slack voice gate</h2>
  <div class="rule-meta"><span>~/.claude/agents/brooks-slack-voice.md + brooks-slack-voice-guide skill</span><span>model: opus</span><span>tools: read-only Slack (get_channel_history, get_thread, list_channels)</span></div>
  <div class="rule-grid">
    <div class="rule-col">
      <h3>What it checks</h3>
      <ul class="rulelist">
        <li><b>Input contract first (Step 0).</b> Caller must supply five fields: verbatim <code>content</code>, <code>destination_type</code> (channel|dm), <code>channel_id</code>, <code>audience</code>, <code>intent</code> (announcement|status|question|ack|request). Anything missing → <code>INPUT_INVALID</code>, no guessing.</li>
        <li><b>Live anchors (Step 1).</b> Pulls ~40 messages from the exact destination with <code>exclude_agent=true</code> — agent-sent messages carry an invisible U+2060 watermark and must never anchor judgment. Keeps Brooks's 3–8 most recent genuine posts as the primary bar: length, formatting, greeting habits, emoji, tone <i>in this specific conversation</i>. Anchors beat the generic rubric everywhere except the always-fail list.</li>
        <li><b>Mechanical tell scan (Step 2, automatic FAIL).</b> A single em/en dash anywhere — Brooks joins clauses with <code>&nbsp;-&nbsp;</code> — or any phrase on the always-fail list fails the draft before judgment starts, "even if his own history contains one."</li>
        <li><b>Always-fail AI tells (never relaxed):</b> "Certainly" / "I'd be happy to" / "Great question"; generic courtesy closers ("don't hesitate"); manufactured enthusiasm and emoji clusters; balanced "It's not X, it's Y" constructions; performative hedging ("seemed worth flagging", "no urgency from me", "just my two cents"); summarizing closers ("In summary"); length bloat.</li>
        <li><b>Constant markers:</b> leads with the point or @mention; concrete (repo, env, surface, time window); lowercase tech terms (qa, evo-pro, curl); soft short asks ("can you…", "when you have a minute…").</li>
        <li><b>DM branch:</b> no greeting or sign-off, fragments fine, drifting lowercase fine, <code>•</code> bullets or numbered todos only, one-two sentences by default.</li>
        <li><b>Channel branch:</b> <code>&lt;!here&gt;</code> in-voice for announcements; light structure (<code>*bold*</code> for one critical instruction, <code>&gt; TL;DR</code> on long posts). Courtesy dial set by audience: external/testers → greeting and genuine sign-off are in-voice; internal-eng → ceremony reads off-voice (soft negative).</li>
      </ul>
    </div>
    <div class="rule-col">
      <h3>How it scores</h3>
      <ul class="rulelist">
        <li><b>Posture: default to FAIL.</b> "Fine, clear, or professional is a FAIL — the bar is <span class="quote">Brooks would actually have typed this, here</span>. When uncertain, FAIL."</li>
        <li><b>Order of evaluation:</b> input contract → mechanical scan (any hit ends it) → anchors → branch rules → always-fail list.</li>
        <li><b>Verdict only, no rewrite.</b> Returns <code>INPUT: OK|INVALID</code>, <code>REFERENCES</code> (which anchors were used), <code>BRANCH</code>, <code>VERDICT: PASS|FAIL</code>, then numbered violations quoting each offending span with an imperative fix — explicitly forbidden from writing the replacement text or posting.</li>
        <li><b>Loop:</b> caller revises and resubmits until PASS; the PASS must be on the exact final text, covering every outbound surface (post, thread reply, upload comment).</li>
      </ul>
    </div>
  </div>
</section>

<section class="stat-sec" id="rules-comment">
  <p class="kicker">comment-adversary</p>
  <h2>Comment adversary</h2>
  <div class="rule-meta"><span>tmp/local-evo-mcp-test/.claude/agents/comment-adversary.md (project-local)</span><span>model: sonnet</span><span>tools: Read, Grep, Glob, Bash (read-only use)</span></div>
  <div class="rule-grid">
    <div class="rule-col">
      <h3>What it checks</h3>
      <ul class="rulelist">
        <li><b>Scope:</b> only developer comments in just-changed files — line/block comments, JSDoc/docstrings, JSX comments. Not string literals, logs, or user-facing copy. Not code logic or style.</li>
        <li><b>Rule 1 — no process-specific language.</b> A comment explains the code, never the workflow that produced it. Flags: ticket refs (<code>#57</code>, JIRA-…); slice/phase/sprint/release language; PRD/spec/object-map pointers; agent and workflow terms (server-dev, team-lead, qa gate, "as the analyst noted"); authoring narration and dated decision logs ("decided 2026-06-30", "as requested"); any sentence whose subject is the workflow rather than the code.</li>
        <li><b>Rule 1 carve-out:</b> behavior, invariants, non-obvious rationale ("debounced because the upstream API rate-limits at 10/s"), gotcha warnings, durable doc references — "rationale is good; process bookkeeping is not."</li>
        <li><b>Rule 2 — Brooks's copy rules:</b> concise (sacrifice grammar for concision); active voice with first-person attribution ("We debounce here"); causal logic chains; no "not X, it's Y" inversions; no editorial superlatives ("cleanest", "the right way"); name things before coining shorthand; no vague diplomatic hedging — honest first-person uncertainty is fine.</li>
      </ul>
    </div>
    <div class="rule-col">
      <h3>How it scores</h3>
      <ul class="rulelist">
        <li><b>Posture:</b> "a comment is guilty until it reads clean. When borderline, FLAG it. A false flag costs a glance; a missed one ships noise into the codebase permanently."</li>
        <li><b>One strike fails all:</b> a single violating comment fails the whole review.</li>
        <li><b>Findings carry the fix:</b> each violation reports file:line, the verbatim comment, the rule and sub-rule (active-voice | inverted | superlative | filler | shorthand | hedge), and a concrete rewrite — or "delete" when the comment is pure process noise.</li>
        <li><b>Output is a bare verdict block</b> — machine-and-human-readable, no preamble, no sign-off.</li>
      </ul>
    </div>
  </div>
</section>

<section class="stat-sec" id="rules-scrub">
  <p class="kicker">process-scrub-reviewer</p>
  <h2>Process-scrub reviewer</h2>
  <div class="rule-meta"><span>~/.claude/agents/process-scrub-reviewer.md + process-scrub-reviewer-guide skill</span><span>tools: Read, Grep, Glob, Bash (read-only use)</span></div>
  <div class="rule-grid">
    <div class="rule-col">
      <h3>What it checks</h3>
      <ul class="rulelist">
        <li><b>Surfaces:</b> broader than comment-adversary — comments, JSDoc, test titles and describe blocks, Markdown docs, PR titles/descriptions, commit messages.</li>
        <li><b>Requires explicit scope:</b> changed files + which prose the change introduced. Judges only in-scope prose; violations it happens to see elsewhere are filed PRE-EXISTING and never affect the verdict.</li>
        <li><b>Rule 1 — no process residue:</b> ticket/issue refs; slice/sprint/phase/unit refs; agent and reviewer names; workflow narration ("passed the design gate"); dated decision-log headers; self-referential change narration ("now reads", "this change adds", "updated to fix the review finding" — describe the state, not the edit); plan/PRD/ADR pointers where the reader needs the constraint inline.</li>
        <li><b>The durability test:</b> "would the sentence still be true and useful after the tracker is deleted and the team disbands?" Naming a concrete consumer or constraint passes; paperwork pointers fail.</li>
        <li><b>Rule 2 — copy rules:</b> concise; active voice, never agentless passive ("is memoized"); no inverted constructions; no empty superlatives or filler; no ungrounded shorthand (the def records real precedent: "The Designer/AI binds" failed, "The sys_view binds" passed); comments state constraints the code can't show.</li>
        <li><b>Hunts mechanically too:</b> instructed to grep for leak patterns — <code>#[0-9]+</code>, slice/sprint tokens, known agent names from .claude/agents/.</li>
      </ul>
    </div>
    <div class="rule-col">
      <h3>How it scores</h3>
      <ul class="rulelist">
        <li><b>Verdicts:</b> PASS | FAIL | INPUT_INVALID. PASS requires zero in-scope findings; findings ranked most-severe first, each with verbatim text, the rule violated, and the exact replacement text.</li>
        <li><b>Anti-ratchet protocol (hard rule):</b> at most two rounds per change. The confirmation pass verifies only that the prescribed rewrites are present and faithful — it must not flag prose it passed in round one, "even if it would flag it fresh today." New discoveries go to PRE-EXISTING for a future change.</li>
        <li><b>Stance:</b> read "as the skeptical future maintainer with zero project history."</li>
      </ul>
    </div>
  </div>
</section>

<section class="stat-sec" id="rules-ste">
  <p class="kicker">ste100-validator</p>
  <h2>STE-100 validator</h2>
  <div class="rule-meta"><span>evo-root/.claude/agents/ste100-validator.md (project-local)</span><span>tools: Read, Grep, Glob</span><span>standard: ASD-STE100 Issue 8</span></div>
  <div class="rule-grid">
    <div class="rule-col">
      <h3>What it checks — twelve numbered rules</h3>
      <ol class="rulelist">
        <li><b>Sentence length:</b> instructions max 20 words, descriptions max 25. Hyphenated compounds and technical names count as one word.</li>
        <li><b>One topic per sentence; one instruction per sentence.</b></li>
        <li><b>Paragraphs:</b> max 6 sentences, one topic each.</li>
        <li><b>Active voice;</b> passive only when the agent is unknown/unimportant, never in instructions.</li>
        <li><b>Simple tenses only</b> — no perfect tenses, no conditional perfect.</li>
        <li><b>Verbs, not gerunds:</b> no -ing form as an instruction's main verb.</li>
        <li><b>Articles required</b> — never dropped telegraphically.</li>
        <li><b>Noun clusters:</b> max 3 nouns in a row unless an official technical name.</li>
        <li><b>One word, one meaning;</b> approved vocabulary preferred ("start" not "commence", "use" not "utilize", "show" not "indicate", "about" not "approximately").</li>
        <li><b>No idioms, slang, or rhetorical flourishes.</b></li>
        <li><b>Instructions are imperative</b> ("Confirm the scope." not "You should confirm the scope."); questions allowed for question-kind text under rules 1–10.</li>
        <li><b>Conditions first:</b> "If the build fails, stop."</li>
      </ol>
      <p class="stat-cap">Technical names, paths, and identifiers are exempt from the vocabulary but still count toward sentence length. Caller must supply the verbatim candidate text and its kind (question | doc | issue).</p>
    </div>
    <div class="rule-col">
      <h3>How it scores</h3>
      <ul class="rulelist">
        <li><b>PASS means zero violations.</b> "Borderline judgment calls (a 21-word descriptive sentence that reads clearly) are still FAIL — the caller asked for the standard, not your taste."</li>
        <li><b>Form only:</b> content and technical accuracy are explicitly out of scope.</li>
        <li><b>Per-sentence findings:</b> reports SENTENCES CHECKED, then numbered findings citing the rule number and name, the verbatim sentence, and a compliant rewrite the caller applies.</li>
        <li><b>Two rounds max:</b> one full review, then one confirmation pass strictly limited to the prescribed rewrites.</li>
      </ul>
    </div>
  </div>
</section>
'''


def stats_table(m):
    rows = []
    for p in m["pts"]:
        b, f = p["b"], p["f"]
        if m["kind"] == "pct":
            d = f"{(f - b) / b * 100:+.0f}%" if b else "—"
        elif m["kind"] == "abs":
            d = f"{f - b:+.3f}"
        else:
            d = f"{f - b:+.1f} pp"
        rows.append(
            f"<tr><td>{p['a']}</td><td>{p['d']}</td><td class='num'>{b}</td>"
            f"<td class='num'>{f}</td><td class='num'>{d}</td>"
            f"<td class='ctx'>{htmlmod.escape(p['c'])}</td></tr>"
        )
    return (
        "<table><thead><tr><th>agent</th><th>date</th><th class='num'>before</th>"
        "<th class='num'>after</th><th class='num'>Δ</th><th>context</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def stats_sections_html(metrics, total_pairs):
    parts = [
        f'<p class="stats-intro">Each section compares one metric before and after revision '
        f'across all {total_pairs} shipped pairs. Summary = per-agent mean change; '
        f'Raw = every datapoint, one dot per input and output. Hover any mark for detail; '
        f'the data table under each chart lists every value.</p>'
    ]
    for md in METRIC_DEFS:
        if md["key"] not in metrics:
            continue
        m = metrics[md["key"]]
        parts.append(f'''<section class="stat-sec" id="stat-{md["key"]}">
  <h2>{md["title"]}</h2>
  <p class="stat-cap">{md["caption"]}</p>
  <div class="stat-head">
    <div class="seg">
      <button class="on" data-view="summary">Summary</button>
      <button data-view="raw">Raw</button>
    </div>
    <div class="legend" hidden>
      <span class="lg"><svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" class="lg-before"/></svg>before</span>
      <span class="lg"><svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" class="lg-after"/></svg>after</span>
    </div>
  </div>
  <div class="chart" id="c-{md["key"]}-summary"></div>
  <div class="chart" id="c-{md["key"]}-raw" hidden></div>
  <details class="dtable"><summary>Data table — {md["title"].lower()}, all pairs</summary><div class="tblwrap">{stats_table(m)}</div></details>
</section>''')
    return "\n".join(parts)


def section_html(sec, data):
    pairs = [
        p for p in data["pairs"]
        if (p.get("before") or "").strip() != (p.get("after") or "").strip()
    ]
    cards = "\n".join(pair_card(p, sec["key"]) for p in pairs)
    return f'''<section id="{sec['slug']}">
  <header class="sec-head">
    <p class="kicker">{sec['kicker']}</p>
    <h2>{sec['title']}</h2>
    <div class="chips">{stat_chips(sec['key'], data['stats'])}</div>
    <div class="sec-notes">
      <div class="sec-note"><h3>What it changes</h3><p>{sec['what']}</p></div>
      <div class="sec-note"><h3>Is it better?</h3><p>{sec['better']}</p></div>
    </div>
  </header>
  <div class="pairs">{cards}</div>
</section>'''


def main():
    datasets = {}
    total_inv = 0
    total_pairs = 0
    for sec in SECTIONS:
        with open(f"{CUR}/{sec['key']}.json") as f:
            d = json.load(f)
        d["pairs"] = [
            p for p in d["pairs"]
            if (p.get("before") or "").strip() != (p.get("after") or "").strip()
        ]
        datasets[sec["key"]] = d
        total_inv += d["stats"]["total_invocations"]
        total_pairs += len(d["pairs"])

    nav = "\n".join(
        f'<a href="#{s["slug"]}"><span class="nav-name">{s["title"]}</span>'
        f'<span class="nav-count">{len(datasets[s["key"]]["pairs"])} pairs</span></a>'
        for s in SECTIONS
    )

    sections = "\n".join(section_html(s, datasets[s["key"]]) for s in SECTIONS)

    metrics = compute_metrics(datasets)
    stats_html = stats_sections_html(metrics, total_pairs)
    data_json = json.dumps(metrics, separators=(",", ":"))

    page = f'''<title>Voice Agent Audit — before/after</title>
<style>
:root {{
  --bg: #F3F5F6;
  --surface: #FFFFFF;
  --surface-2: #EBEEF0;
  --ink: #1B2228;
  --muted: #5C6873;
  --line: #DDE2E6;
  --accent: #0E6E6A;
  --accent-soft: #E3EFEE;
  --before-mark: #A8514B;
  --before-tint: #FAF2F1;
  --after-mark: #3F7D52;
  --after-tint: #F0F6F1;
  --chip-bg: #EBEEF0;
  --pass-bg: #E7F1E9;
  --pass-ink: #2E6440;
  --fail-bg: #F7ECEA;
  --fail-ink: #8A423C;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #14181A;
    --surface: #1C2226;
    --surface-2: #232A2F;
    --ink: #E6E9EB;
    --muted: #93A0A8;
    --line: #2B3339;
    --accent: #58B7B1;
    --accent-soft: #1E3230;
    --before-mark: #CF867E;
    --before-tint: #291F1E;
    --after-mark: #82BA8D;
    --after-tint: #1D2A20;
    --chip-bg: #232A2F;
    --pass-bg: #1E2F23;
    --pass-ink: #93C79F;
    --fail-bg: #33221F;
    --fail-ink: #D69B93;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #14181A;
  --surface: #1C2226;
  --surface-2: #232A2F;
  --ink: #E6E9EB;
  --muted: #93A0A8;
  --line: #2B3339;
  --accent: #58B7B1;
  --accent-soft: #1E3230;
  --before-mark: #CF867E;
  --before-tint: #291F1E;
  --after-mark: #82BA8D;
  --after-tint: #1D2A20;
  --chip-bg: #232A2F;
  --pass-bg: #1E2F23;
  --pass-ink: #93C79F;
  --fail-bg: #33221F;
  --fail-ink: #D69B93;
}}
* {{ box-sizing: border-box; }}
body {{
  background: var(--bg);
  color: var(--ink);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 0 24px 96px;
}}
.wrap {{ max-width: 1160px; margin: 0 auto; }}
h1, h2, h3 {{
  font-family: "Avenir Next", "Seravek", -apple-system, sans-serif;
  text-wrap: balance;
  margin: 0;
}}
.masthead {{ padding: 56px 0 12px; max-width: 74ch; }}
.masthead .kicker {{ margin-bottom: 14px; }}
h1 {{ font-size: 2.1rem; font-weight: 600; letter-spacing: -0.015em; line-height: 1.15; }}
.lede {{ color: var(--muted); margin: 14px 0 0; font-size: 1.04rem; max-width: 66ch; }}
.kicker {{
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 8px;
}}
.topstats {{
  display: flex; flex-wrap: wrap; gap: 26px;
  padding: 22px 0 26px;
  border-bottom: 1px solid var(--line);
  font-variant-numeric: tabular-nums;
}}
.topstat .n {{ font-size: 1.5rem; font-weight: 600; font-family: "Avenir Next", -apple-system, sans-serif; }}
.topstat .l {{ color: var(--muted); font-size: 0.82rem; }}
nav.toc {{ display: flex; flex-wrap: wrap; gap: 10px; padding: 22px 0 8px; }}
nav.toc a {{
  display: flex; flex-direction: column; gap: 1px;
  padding: 10px 16px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  text-decoration: none;
  color: var(--ink);
  min-width: 150px;
}}
nav.toc a:hover, nav.toc a:focus-visible {{ border-color: var(--accent); outline: none; }}
.nav-name {{ font-weight: 600; font-size: 0.92rem; }}
.nav-count {{ color: var(--muted); font-size: 0.78rem; font-variant-numeric: tabular-nums; }}
section {{ margin-top: 64px; scroll-margin-top: 24px; }}
.sec-head h2 {{ font-size: 1.5rem; font-weight: 600; letter-spacing: -0.01em; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
.chip {{
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.74rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--chip-bg);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}}
.chip-pass {{ background: var(--pass-bg); color: var(--pass-ink); }}
.chip-fail {{ background: var(--fail-bg); color: var(--fail-ink); }}
.sec-notes {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  margin-top: 18px;
}}
.sec-note {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 16px 18px;
}}
.sec-note h3 {{
  font-size: 0.78rem; letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--accent); font-weight: 600; margin-bottom: 8px;
}}
.sec-note p {{ margin: 0; font-size: 0.92rem; color: var(--ink); }}
.pairs {{ display: flex; flex-direction: column; gap: 18px; margin-top: 24px; }}
.pair {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px 12px;
}}
.pair-meta {{
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px;
  font-size: 0.78rem; color: var(--muted);
  margin-bottom: 12px;
}}
.meta-left {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.72rem; white-space: nowrap; }}
.meta-context {{ flex: 1 1 260px; min-width: 200px; }}
.meta-right {{ display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; }}
.rule, .verdict {{
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}}
.rule {{ background: var(--accent-soft); color: var(--accent); }}
.verdict.v-pass {{ background: var(--pass-bg); color: var(--pass-ink); }}
.verdict.v-fail {{ background: var(--fail-bg); color: var(--fail-ink); }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.cols.one {{ grid-template-columns: 1fr; }}
.cell {{
  border-radius: 6px;
  padding: 10px 14px 12px;
  border-left: 3px solid var(--line);
  overflow-x: auto;
}}
.cell-before {{ background: var(--before-tint); border-left-color: var(--before-mark); }}
.cell-after  {{ background: var(--after-tint);  border-left-color: var(--after-mark); }}
.cell-pass   {{ background: var(--after-tint);  border-left-color: var(--after-mark); }}
.cell-label {{
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase;
  margin-bottom: 7px;
}}
.label-before {{ color: var(--before-mark); }}
.label-after, .label-pass {{ color: var(--after-mark); }}
.cell-text {{
  white-space: pre-wrap;
  overflow-wrap: break-word;
  font-size: 0.9rem;
  line-height: 1.5;
}}
.pair-note {{ margin: 11px 2px 2px; font-size: 0.83rem; color: var(--muted); }}
.method {{
  margin-top: 72px;
  border-top: 1px solid var(--line);
  padding-top: 26px;
  max-width: 74ch;
  color: var(--muted);
  font-size: 0.88rem;
}}
.method h2 {{ font-size: 1.05rem; color: var(--ink); margin-bottom: 10px; }}
.method p {{ margin: 0 0 10px; }}
@media (max-width: 760px) {{
  .cols, .sec-notes {{ grid-template-columns: 1fr; }}
  .masthead {{ padding-top: 36px; }}
  body {{ padding: 0 14px 72px; }}
}}
a {{ color: var(--accent); }}
{CHART_CSS}
</style>
<div class="wrap">
  <header class="masthead">
    <p class="kicker">Claude Code history audit · Jun 30 – Aug 14, 2026</p>
    <h1>Voice Agent Audit: what the gates actually change</h1>
    <p class="lede">Every voice sub-agent invocation recovered from local Claude Code transcripts, sampled newest-first. Only failed gates are shown: the left column is the text as first drafted, the right column is what actually shipped — the Slack message as posted, the prose as applied to the file or doc.</p>
  </header>
  <div class="topstats">
    <div class="topstat"><div class="n">4</div><div class="l">voice agents</div></div>
    <div class="topstat"><div class="n">{total_inv}</div><div class="l">invocations recovered</div></div>
    <div class="topstat"><div class="n">{total_pairs}</div><div class="l">before/after pairs shown</div></div>
    <div class="topstat"><div class="n">46</div><div class="l">days of history</div></div>
  </div>
  <div class="tabs">
    <button class="tabbtn on" data-tab="pairs">Before / after pairs</button>
    <button class="tabbtn" data-tab="stats">Stats</button>
    <button class="tabbtn" data-tab="rules">Rules</button>
  </div>
  <div id="tab-pairs">
  <nav class="toc">{nav}</nav>
  {sections}
  <footer class="method">
    <h2>Method &amp; caveats</h2>
    <p>Source: all <code>*.jsonl</code> transcripts under <code>~/.claude/projects/</code> (579&nbsp;MB, including subagent transcripts). Every <code>Task</code>/<code>Agent</code> tool call with a voice-agent <code>subagent_type</code> was paired with its <code>tool_result</code> by tool-use id — 168 invocations total. Curation agents sampled FAIL verdicts newest-first, then traced each one forward through the same session's transcripts to the end product: the Slack post call that actually sent the message, or the Edit/Write call that applied the fix to the file. The “after” column is that shipped text, verified — not the gate's suggestion.</p>
    <p>Caveats: drafts that failed and were never posted or applied are excluded (counted in the chips). Review-agent pairs (comment, scrub, STE) are finding-level: one invocation can contribute several rows. Many review-gate invocations were async spawns whose verdicts landed as notifications elsewhere, so pass/fail counts undercount slightly. The <code>scribe</code> agent matched the search but is sprint bookkeeping, not voice — excluded. Pairs over ~600–1100 characters and code-dominant text were filtered out. Idea density is computed with the <code>ideadensity</code> Python port of CPIDR 3.2 (Brown et al. 2008) over spaCy POS tags, URLs and Slack mentions stripped first, matching the other metrics.</p>
  </footer>
  </div>
  <div id="tab-stats" hidden>
{stats_html}
  </div>
  <div id="tab-rules" hidden>
{RULES_HTML}
  </div>
</div>
<script>
const DATA = {data_json};
{STATS_JS}
</script>'''

    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT}: {len(page)} bytes, {total_pairs} pairs, {total_inv} invocations")


if __name__ == "__main__":
    main()
