#!/usr/bin/env python3
"""Build the baseline comparison artifact from audit/raw/baselines_run.json.
Rev 2: matched human/AI pairs sit adjacent, green-low -> red-high scale, and
percentile-normalized comparison rows (rank against every corpus in the rule)."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
RUN = json.load(open(os.path.join(ROOT, "audit", "raw", "baselines_run.json")))
BANDS = json.load(open(os.path.join(ROOT, "app", "checks", "baselines.json")))

COLS = ["W-M1", "W-M2", "W-M3", "W-M4", "W-M6", "W-M7", "W-M8", "W-M9", "W-M11",
        "P-M1", "T-M1", "T-M2", "T-M3", "T-M4", "T-M5", "T-M7", "T-M8", "T-M9",
        "T-M10", "T-M11", "T-M12"]
LABELS = {
    "W-M1": "dash", "W-M2": "inversion", "W-M3": "assistant", "W-M4": "register",
    "W-M6": "hedge", "W-M7": "opener", "W-M8": "process", "W-M9": "clusters",
    "W-M11": "passive", "P-M1": "short names",
    "T-M1": "sent. length", "T-M2": "1 instruction", "T-M3": "para limit",
    "T-M4": "tenses", "T-M5": "-ing verb", "T-M7": "noun cluster",
    "T-M8": "vocabulary", "T-M9": "idioms", "T-M10": "imperative",
    "T-M11": "cond. first", "T-M12": "list items",
}
SURFACE_TITLES = [
    ("chat", "Chat"),
    ("doc-shared", "Document - Shared"),
    ("doc-technical", "Document - Technical"),
    ("code", "Code"),
]

# Explicit contrast pairs (human label, ai label): rendered adjacent.
PAIRS = {
    "code": [("github-readmes-human-pre2022", "github-readmes-ai-post2024"),
             ("github-comments-human-pre2022", "github-comments-ai-post2024")],
    "chat": [("brooks-all-slack", "slack-agent-drafts (before)"),
             ("internal-slack-messages", "agent-pasted-messages")],
}

BY_LABEL = {c["label"]: c for c in RUN["corpora"]}

# Percentile pool: every corpus rate in that rule column, whole table.
POOL = {r: sorted(c["per_1k"][r] for c in RUN["corpora"]) for r in COLS}


def pct_rank(rule, v):
    pool = POOL[rule]
    below = sum(1 for x in pool if x < v)
    equal = sum(1 for x in pool if x == v)
    return round(100 * (below + 0.5 * equal) / len(pool))


def tint(v):
    if v == 0:
        return "g0"
    if v <= 0.5:
        return "g1"
    if v <= 2:
        return "g2"
    if v <= 5:
        return "g3"
    if v <= 10:
        return "g4"
    return "g5"


def ptint(p):
    if p <= 20:
        return "g0"
    if p <= 35:
        return "g1"
    if p <= 50:
        return "g2"
    if p <= 65:
        return "g3"
    if p <= 80:
        return "g4"
    return "g5"


def fmt(v):
    return "0" if v == 0 else (f"{v:.2f}".rstrip("0").rstrip(".") if v < 10 else f"{v:.1f}")


def corpus_row(c, paired=False):
    side = c["side"]
    chip = f'<span class="chip c-{side}">{"HUMAN" if side == "human" else "AI"}</span>'
    origin = "int" if c["origin"] == "internal" else "univ"
    cells = []
    for r in COLS:
        v = c["per_1k"].get(r, 0)
        n = c["counts"].get(r, 0)
        cells.append(f'<td class="v {tint(v)}" title="{n} findings · p{pct_rank(r, v)}">{fmt(v)}</td>')
    cls = f"side-{side}" + (" paired" if paired else "")
    return (f'<tr class="{cls}"><td class="corp">{chip}{c["label"]}</td>'
            f'<td class="meta">{origin} · {c["docs"]:,}d · {c["words"]:,}w</td>'
            + "".join(cells) + "</tr>")


def band_row(surface, key, title, cls):
    cells = []
    for r in COLS:
        e = BANDS["surfaces"].get(surface, {}).get(r, {})
        v = e.get(key)
        if v is None:
            cells.append('<td class="v z">-</td>')
        elif isinstance(v, list):
            cells.append(f'<td class="v band">{fmt(v[0])}-{fmt(v[1])}</td>')
        else:
            cells.append(f'<td class="v band">{fmt(v)}</td>')
    return (f'<tr class="bandrow {cls}"><td class="corp">{title}</td>'
            f'<td class="meta">raw /1k</td>' + "".join(cells) + "</tr>")


def pct_row(surface, side, title, cls):
    """Percentile of the side's median corpus rate vs ALL corpora in the rule."""
    rows = [c for c in RUN["corpora"] if c["surface"] == surface and c["side"] == side]
    cells = []
    for r in COLS:
        vals = sorted(c["per_1k"][r] for c in rows)
        if not vals:
            cells.append('<td class="v z">-</td>')
            continue
        med = vals[len(vals) // 2]
        p = pct_rank(r, med)
        cells.append(f'<td class="v {ptint(p)}" title="median {fmt(med)}/1k">p{p}</td>')
    return (f'<tr class="bandrow pctrow {cls}"><td class="corp">{title}</td>'
            f'<td class="meta">percentile</td>' + "".join(cells) + "</tr>")


head_cells = "".join(
    f'<th class="rh"><span class="rid">{r}</span><span class="rlbl">{LABELS[r]}</span></th>'
    for r in COLS)

sections = []
for skey, stitle in SURFACE_TITLES:
    rows = [c for c in RUN["corpora"] if c["surface"] == skey]
    used = set()
    body = [f'<tr class="grp"><td colspan="{len(COLS) + 2}"><span class="stick">{stitle}</span></td></tr>']
    for h, a in PAIRS.get(skey, []):
        if h in BY_LABEL and a in BY_LABEL:
            body.append(corpus_row(BY_LABEL[h], paired=True))
            body.append(corpus_row(BY_LABEL[a], paired=True))
            body.append(f'<tr class="gap"><td colspan="{len(COLS) + 2}"></td></tr>')
            used.update([h, a])
    rest_h = [c for c in rows if c["side"] == "human" and c["label"] not in used]
    rest_a = [c for c in rows if c["side"] == "ai" and c["label"] not in used]
    body += [corpus_row(c) for c in rest_h]
    body += [corpus_row(c) for c in rest_a]
    body.append(f'<tr class="cmphead"><td colspan="{len(COLS) + 2}"><span class="stick">comparison - human vs AI, adjacent</span></td></tr>')
    body.append(band_row(skey, "human_universal", "human band (universal)", "b-h"))
    if any("ai_universal" in BANDS["surfaces"].get(skey, {}).get(r, {}) for r in COLS):
        body.append(band_row(skey, "ai_universal", "AI reference (universal)", "b-a"))
    if any("human_internal" in BANDS["surfaces"].get(skey, {}).get(r, {}) for r in COLS):
        body.append(band_row(skey, "human_internal", "human band (internal)", "b-h"))
    if any("ai_internal" in BANDS["surfaces"].get(skey, {}).get(r, {}) for r in COLS):
        body.append(band_row(skey, "ai_internal", "AI reference (internal)", "b-a"))
    body.append(pct_row(skey, "human", "human percentile (of all corpora in rule)", "b-h"))
    body.append(pct_row(skey, "ai", "AI percentile (of all corpora in rule)", "b-a"))
    sections.append("".join(body))

table = (f'<table><thead><tr><th class="corp">corpus</th><th class="meta">origin · size</th>'
         f'{head_cells}</tr></thead><tbody>{"".join(sections)}</tbody></table>')

page = """<title>Baseline bands - human vs AI by surface</title>
<style>
:root {
  --ground:#F4F5F7; --surface:#FFFFFF; --ink:#171A1F; --ink2:#4A5160; --ink3:#788093;
  --rule:#DFE3E9; --rulesoft:#EBEEF2; --hum:#0E6A5E; --ai:#8C2F3B;
  --z:transparent;
  --s0:#DBEEDF; --s1:#B7DFC0; --s2:#F2E3A8; --s3:#F4C173; --s4:#E5804A; --s5:#C43D2E;
  --bandbg:#EDF0F4; --inkhi:#FFFFFF;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial,sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --ground:#101318; --surface:#181C23; --ink:#E8EAEE; --ink2:#ACB4C2; --ink3:#7C8494;
  --rule:#2A303A; --rulesoft:#222831; --hum:#4FC5B0; --ai:#E58794;
  --z:transparent;
  --s0:#1D3A26; --s1:#2A5236; --s2:#59511F; --s3:#7A511E; --s4:#98421F; --s5:#B23325;
  --bandbg:#1E242C; --inkhi:#FFF6EF;
}}
:root[data-theme="dark"] {
  --ground:#101318; --surface:#181C23; --ink:#E8EAEE; --ink2:#ACB4C2; --ink3:#7C8494;
  --rule:#2A303A; --rulesoft:#222831; --hum:#4FC5B0; --ai:#E58794;
  --z:transparent;
  --s0:#1D3A26; --s1:#2A5236; --s2:#59511F; --s3:#7A511E; --s4:#98421F; --s5:#B23325;
  --bandbg:#1E242C; --inkhi:#FFF6EF;
}
body { background:var(--ground); color:var(--ink); font-family:var(--sans);
  font-size:16px; line-height:1.55; margin:0; padding:0 20px 90px; }
.wrap { max-width:1240px; margin:0 auto; }
header { padding:52px 0 26px; border-bottom:2px solid var(--ink); margin-bottom:26px; }
.eyebrow { font-size:11px; font-weight:650; letter-spacing:.13em; text-transform:uppercase;
  color:var(--ink3); margin:0 0 8px; }
h1 { font-size:clamp(26px,4.5vw,38px); font-weight:680; letter-spacing:-.02em;
  line-height:1.1; margin:0 0 12px; text-wrap:balance; }
header p { margin:0; color:var(--ink2); max-width:76ch; }
h2 { font-size:13px; font-weight:680; letter-spacing:.12em; text-transform:uppercase;
  margin:40px 0 12px; }
ul { padding-left:20px; margin:8px 0 18px; max-width:80ch; }
li { margin-bottom:8px; color:var(--ink2); }
li b { color:var(--ink); font-weight:640; }
.legend { display:flex; gap:14px; flex-wrap:wrap; align-items:center;
  font-size:12.5px; color:var(--ink3); margin:14px 0 10px; }
.legend .sw { display:inline-block; width:26px; height:13px; border:1px solid var(--rule);
  border-radius:2px; vertical-align:-2px; margin-right:5px; }
.scroll { overflow:auto; max-height:86vh; background:var(--surface); border:1px solid var(--rule);
  border-radius:4px; box-shadow:0 1px 2px rgba(0,0,0,.05); }
table { border-collapse:collapse; font-size:12.5px; min-width:1480px; width:100%; }
th,td { padding:5px 7px; text-align:right; border-bottom:1px solid var(--rulesoft); }
th { font-size:10px; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
  color:var(--ink3); position:sticky; top:0; background:var(--surface); z-index:2; }
th.rh { vertical-align:bottom; }
th .rid { display:block; font-family:var(--mono); font-size:10.5px; color:var(--ink); }
th .rlbl { display:block; font-weight:500; letter-spacing:0; text-transform:none;
  font-size:10px; color:var(--ink3); }
td.corp, th.corp { text-align:left; font-weight:600; white-space:nowrap;
  position:sticky; left:0; background:var(--surface); z-index:1; }
th.corp { z-index:4; }
td.meta, th.meta { text-align:left; font-family:var(--mono); font-size:10.5px;
  color:var(--ink3); white-space:nowrap; }
tr.grp td { text-align:left; font-size:11px; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink); background:var(--surface);
  border-bottom:1px solid var(--rule); padding-top:16px; }
tr.cmphead td { text-align:left; font-size:10px; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink3); background:var(--surface); padding-top:10px; }
tr.gap td { border-bottom:none; height:6px; background:var(--surface); }
.stick { position:sticky; left:8px; display:inline-block; }
.chip { display:inline-block; font-size:8.5px; font-weight:800; letter-spacing:.08em;
  border-radius:2px; padding:1px 4px; margin-right:7px; vertical-align:1px;
  color:var(--inkhi); }
.c-human { background:var(--hum); }
.c-ai { background:var(--ai); }
tr.paired td.corp { border-left:3px solid var(--rule); }
td.v { font-family:var(--mono); font-variant-numeric:tabular-nums; white-space:nowrap; }
td.z { color:var(--ink3); opacity:.45; }
td.g0 { background:var(--s0); } td.g1 { background:var(--s1); }
td.g2 { background:var(--s2); } td.g3 { background:var(--s3); }
td.g4 { background:var(--s4); color:var(--inkhi); }
td.g5 { background:var(--s5); color:var(--inkhi); font-weight:700; }
tr.bandrow td { background:var(--bandbg); font-weight:600; border-top:1px solid var(--rule);
  border-bottom:1px solid var(--rule); }
tr.bandrow td.corp { background:var(--bandbg); }
tr.pctrow td.v { font-weight:700; }
tr.b-h td.corp { color:var(--hum); }
tr.b-a td.corp { color:var(--ai); }
footer { margin-top:44px; padding-top:16px; border-top:1px solid var(--rule);
  font-size:13px; color:var(--ink3); max-width:80ch; }
</style>
<div class="wrap">
<header>
  <p class="eyebrow">voice-agents · baselines.json · 2026-08-25 · rev 2</p>
  <h1>Human vs AI, rule by rule, surface by surface</h1>
  <p>Findings per 1,000 words, .txt-only, parser tier included. Matched contrast pairs
  (same sub-surface, human then AI) sit adjacent with a connecting rule. Each section
  ends with the comparison block: the shipped raw bands from
  <code>app/checks/baselines.json</code>, then the percentile rows - each side's median
  ranked against every corpus in that rule column, so a 0.3-vs-12 gap and a
  0.05-vs-0.2 gap read on the same scale. Hover any cell for raw count and percentile.</p>
</header>
<div class="legend">
  <span>rate / percentile:</span>
  <span><span class="sw" style="background:var(--s0)"></span>low / p&le;20</span>
  <span><span class="sw" style="background:var(--s1)"></span>&le;0.5 / p&le;35</span>
  <span><span class="sw" style="background:var(--s2)"></span>&le;2 / p&le;50</span>
  <span><span class="sw" style="background:var(--s3)"></span>&le;5 / p&le;65</span>
  <span><span class="sw" style="background:var(--s4)"></span>&le;10 / p&le;80</span>
  <span><span class="sw" style="background:var(--s5)"></span>&gt;10 / p&gt;80</span>
  <span>· gray label rows = shipped bands · green low, red high</span>
</div>
<div class="scroll">__TABLE__</div>
<h2>Reading notes</h2>
<ul>
  <li><b>T-* rows and W-M11 read backwards on purpose.</b> Humans out-score AI on most
  STE form rules (sentence length, tenses, passive) on every surface - agents write
  short compliant sentences; humans do not. Those rules measure STE compliance, never
  AI-ness. The discriminators are W-M1 dash, W-M4 register, W-M2 inversion, and the
  W-M3/W-M6/W-M7 backstop lists - read their percentile rows: human sits p&le;35 and
  AI p&ge;80 on every surface.</li>
  <li><b>Two W-M1 band exclusions</b>: rfc-technical (ASCII-only source - dashes cannot
  occur) and brooks-claude-prompts (24 files quote pasted tool/agent snippets, the same
  paste vector purged from brooks-all-slack).</li>
  <li><b>Controls and soft negatives are not in this table</b>: control-wildchat-predash,
  control-lmsys-predash (pre-2024 models, no dash tell), ai-arxiv-post2024 (LLM-polish,
  unproven authorship).</li>
  <li><b>Origin column</b>: univ = public sources (ship to anyone); int = Evolv/Brooks.
  Bands are computed separately per origin so the bundle ships both.</li>
  <li><b>7 duplicate READMEs</b> were removed from ai-github-docs-post2024 before this
  run (same repos as github-readmes-ai-post2024).</li>
</ul>
<footer>
  Data: audit/raw/baselines_run.json via app/scripts/build_baselines.py; page:
  app/scripts/build_baseline_matrix_page.py. Rerun both after corpus or checker
  changes. Companion artifact: the internal-corpus check matrix (2026-08-22).
</footer>
</div>
"""

page = page.replace("__TABLE__", table)
dest = os.path.join(ROOT, "notes", "baseline-matrix-report.html")
with open(dest, "w") as f:
    f.write(page)
print(f"wrote {dest}")
