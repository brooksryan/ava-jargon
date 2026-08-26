#!/usr/bin/env python3
"""Build the check-matrix report page from audit/raw/check_matrix.json.
Writes notes/check-matrix-report.html. Rerun after any checker tuning."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
DATA = json.load(open(os.path.join(ROOT, "audit", "raw", "check_matrix.json")))

# Column order: Westinghouse, Personal, Technical/STE.
COLS = ["W-M1", "W-M2", "W-M3", "W-M4", "W-M6", "W-M7", "W-M8", "W-M9", "W-M11",
        "P-M1", "P-M3",
        "T-M1", "T-M2", "T-M3", "T-M4", "T-M5", "T-M7", "T-M8", "T-M9",
        "T-M10", "T-M11", "T-M12"]
FAMILY = {"W": ("Westinghouse", 9), "P": ("Personal", 2), "T": ("Technical / STE form", 10)}

LABELS = {
    "W-M1": "dash", "W-M2": "inversion", "W-M3": "assistant", "W-M4": "register",
    "W-M6": "hedge", "W-M7": "opener", "W-M8": "process", "W-M9": "clusters",
    "W-M11": "passive", "P-M1": "short names", "P-M3": "watermark",
    "T-M1": "sent. length", "T-M2": "1 instruction", "T-M3": "para limit",
    "T-M4": "tenses", "T-M5": "-ing verb", "T-M7": "noun cluster",
    "T-M8": "vocabulary", "T-M9": "idioms", "T-M10": "imperative",
    "T-M11": "cond. first", "T-M12": "list items",
}


def tint(v):
    if v == 0:
        return "z"
    if v <= 0.5:
        return "t1"
    if v <= 2:
        return "t2"
    if v <= 5:
        return "t3"
    if v <= 10:
        return "t4"
    return "t5"


def fmt(v):
    return "0" if v == 0 else (f"{v:.2f}".rstrip("0").rstrip(".") if v < 10 else f"{v:.1f}")


rows_html = []
head_cells = "".join(
    f'<th class="rh"><span class="rid">{r}</span><span class="rlbl">{LABELS[r]}</span></th>'
    for r in COLS)
fam_cells = "".join(
    f'<th class="fam" colspan="{n}">{name}</th>'
    for name, n in [FAMILY["W"], FAMILY["P"], FAMILY["T"]])

for g in DATA["groups"]:
    rows_html.append(
        f'<tr class="grp"><td colspan="{len(COLS) + 2}">{g["name"]}</td></tr>')
    for row in g["rows"]:
        cells = []
        for r in COLS:
            v = row["per_1k_words"].get(r, 0)
            c = row["counts"].get(r, 0)
            dh = row["docs_hit"].get(r, 0)
            cells.append(
                f'<td class="v {tint(v)}" title="{c} findings in {dh} of '
                f'{row["docs"]} docs">{fmt(v)}</td>')
        rows_html.append(
            f'<tr><td class="corp">{row["label"]}</td>'
            f'<td class="meta">{row["docs"]:,} docs · {row["words"]:,} w</td>'
            + "".join(cells) + "</tr>")

table = (f'<table><thead><tr><th class="corp"></th><th class="meta"></th>{fam_cells}</tr>'
         f'<tr><th class="corp">corpus</th><th class="meta">size</th>{head_cells}</tr>'
         f'</thead><tbody>{"".join(rows_html)}</tbody></table>')

FINDINGS = """
<section>
  <h2>What the matrix says about each check</h2>

  <h3>Validated agent tells - keep, and trust them</h3>
  <ul>
    <li><b>W-M1 dash</b> is the cleanest separator in the set: Brooks 0.30/1k and
    workplace email 0 against 11.5-14.3 on every agent corpus. The Slack gate cuts
    it 14.3 to 3.65 but does not reach zero.</li>
    <li><b>P-M1 short names</b> survives the gate untouched: 8.61 before, 8.77
    after, against Brooks at 0.11. This is the strongest argument for the
    mechanical layer - the judgment gate never catches it.</li>
    <li><b>W-M8 process language</b>: comments went 12.45 before the
    comment-adversary gate to 0 after, so the old gate did fix what it was built
    for. Agent documents still carry 2.69/1k.</li>
  </ul>

  <h3>Scope evidence - technical-only rules behave as designed</h3>
  <ul>
    <li><b>T-M1, T-M4, T-M5</b> fire on all human conversation (Brooks -ing verbs
    8.72/1k - his fragment style; Wikipedia sentence length 14.3/1k). They are
    surface rules, not universal rules. The matrix confirms the v2 decision to
    suspend the STE form rules in the Personal Voice agent.</li>
    <li><b>ste100 after</b> is the cleanest row in the table - near-zero in every
    column. The ste100 gate genuinely cleans its output.</li>
  </ul>

  <h3>Tuning actions the matrix recommends</h3>
  <ul>
    <li><b>W-M11 passive voice: demote from the universal set to technical-only.</b>
    It fires 5.28/1k on Brooks's own Slack and 5-12/1k on every human corpus.
    Passive is normal register in conversation; the promotion from W-J2 holds for
    documents, not for messages. One-line change in TIER_2_RULES.</li>
    <li><b>W-M7 opener: verify the checker.</b> Zero across all 17 corpora,
    including 8,600+ documents of agent output. Either throat-clearing openers are
    rarer than assumed or the five-pattern list is too narrow. Worth a manual spot
    check against known throat-clearing drafts before trusting the zero.</li>
    <li><b>P-M3 watermark: zero is correct.</b> Every corpus was collected with
    watermark filtering, so the rule has nothing to find here. It exists for live
    drafts, not corpora. No action.</li>
    <li><b>W-M2, W-M3, W-M6, W-M9</b> sit near zero everywhere, including agent
    drafts. These are always-fail lists whose value is blocking single incidents,
    not measuring rates. Low base rates are expected; no tuning signal.</li>
  </ul>
</section>
"""

page = """<title>ava check x corpus matrix</title>
<style>
:root {
  --ground:#F4F5F7; --surface:#FFFFFF; --ink:#171A1F; --ink2:#4A5160; --ink3:#788093;
  --rule:#DFE3E9; --rulesoft:#EBEEF2; --acc:#9A3F14;
  --z:transparent; --c1:#F8E8DF; --c2:#F2CDB9; --c3:#E8A883; --c4:#DB7F4C; --c5:#C05A21;
  --inkhi:#FFFFFF;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial,sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --ground:#101318; --surface:#181C23; --ink:#E8EAEE; --ink2:#ACB4C2; --ink3:#7C8494;
  --rule:#2A303A; --rulesoft:#222831; --acc:#E58B5A;
  --z:transparent; --c1:#3A2A20; --c2:#57351F; --c3:#7A451F; --c4:#A2551E; --c5:#C86A2B;
  --inkhi:#FFF6EF;
}}
:root[data-theme="dark"] {
  --ground:#101318; --surface:#181C23; --ink:#E8EAEE; --ink2:#ACB4C2; --ink3:#7C8494;
  --rule:#2A303A; --rulesoft:#222831; --acc:#E58B5A;
  --z:transparent; --c1:#3A2A20; --c2:#57351F; --c3:#7A451F; --c4:#A2551E; --c5:#C86A2B;
  --inkhi:#FFF6EF;
}
body { background:var(--ground); color:var(--ink); font-family:var(--sans);
  font-size:16px; line-height:1.55; margin:0; padding:0 20px 90px; }
.wrap { max-width:1200px; margin:0 auto; }
header { padding:52px 0 26px; border-bottom:2px solid var(--ink); margin-bottom:30px; }
.eyebrow { font-size:11px; font-weight:650; letter-spacing:.13em; text-transform:uppercase;
  color:var(--ink3); margin:0 0 8px; }
h1 { font-size:clamp(26px,4.5vw,38px); font-weight:680; letter-spacing:-.02em;
  line-height:1.1; margin:0 0 12px; text-wrap:balance; }
header p { margin:0; color:var(--ink2); max-width:72ch; }
h2 { font-size:13px; font-weight:680; letter-spacing:.12em; text-transform:uppercase;
  margin:40px 0 12px; }
h3 { font-size:16px; font-weight:650; margin:22px 0 8px; }
ul { padding-left:20px; margin:8px 0 18px; max-width:78ch; }
li { margin-bottom:8px; color:var(--ink2); }
li b { color:var(--ink); font-weight:640; }
.legend { display:flex; gap:14px; flex-wrap:wrap; align-items:center;
  font-size:12.5px; color:var(--ink3); margin:14px 0 10px; }
.legend .sw { display:inline-block; width:26px; height:13px; border:1px solid var(--rule);
  border-radius:2px; vertical-align:-2px; margin-right:5px; }
.scroll { overflow-x:auto; background:var(--surface); border:1px solid var(--rule);
  border-radius:4px; box-shadow:0 1px 2px rgba(0,0,0,.05); }
table { border-collapse:collapse; font-size:12.5px; min-width:1140px; width:100%; }
th,td { padding:5px 7px; text-align:right; border-bottom:1px solid var(--rulesoft); }
th { font-size:10px; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
  color:var(--ink3); position:sticky; top:0; background:var(--surface); }
th.fam { text-align:left; border-bottom:1px solid var(--rule); color:var(--ink2);
  border-left:2px solid var(--rule); }
th.rh { vertical-align:bottom; }
th .rid { display:block; font-family:var(--mono); font-size:10.5px; color:var(--ink); }
th .rlbl { display:block; font-weight:500; letter-spacing:0; text-transform:none;
  font-size:10px; color:var(--ink3); }
td.corp, th.corp { text-align:left; font-weight:600; white-space:nowrap;
  position:sticky; left:0; background:var(--surface); }
td.meta, th.meta { text-align:left; font-family:var(--mono); font-size:10.5px;
  color:var(--ink3); white-space:nowrap; }
tr.grp td { text-align:left; font-size:11px; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--acc); background:var(--surface);
  border-bottom:1px solid var(--rule); padding-top:14px; }
td.v { font-family:var(--mono); font-variant-numeric:tabular-nums; }
td.z { color:var(--ink3); opacity:.45; }
td.t1 { background:var(--c1); }
td.t2 { background:var(--c2); }
td.t3 { background:var(--c3); }
td.t4 { background:var(--c4); color:var(--inkhi); }
td.t5 { background:var(--c5); color:var(--inkhi); font-weight:700; }
footer { margin-top:44px; padding-top:16px; border-top:1px solid var(--rule);
  font-size:13px; color:var(--ink3); max-width:78ch; }
</style>
<div class="wrap">
<header>
  <p class="eyebrow">voice-agents · ava check · 2026-08-22</p>
  <h1>Every mechanical check against every corpus</h1>
  <p>Cells are findings per 1,000 words; hover a cell for the raw count and how many
  documents it touched. 22 checkers over 8,634 documents (~840k words). W-M10 needs a
  lexicon and P-M5 needs caller fields, so both sat out. The combined all_humans /
  all_agents dirs are excluded so nothing counts twice.</p>
</header>
<div class="legend">
  <span>findings / 1k words:</span>
  <span><span class="sw" style="background:var(--z)"></span>0</span>
  <span><span class="sw" style="background:var(--c1)"></span>&le;0.5</span>
  <span><span class="sw" style="background:var(--c2)"></span>&le;2</span>
  <span><span class="sw" style="background:var(--c3)"></span>&le;5</span>
  <span><span class="sw" style="background:var(--c4)"></span>&le;10</span>
  <span><span class="sw" style="background:var(--c5)"></span>&gt;10</span>
</div>
<div class="scroll">__TABLE__</div>
__FINDINGS__
<footer>
  Data: audit/raw/check_matrix.json via app/scripts/check_matrix.py (all tiers, spacy
  parser included). Page: app/scripts/build_check_matrix_page.py - rerun both after any
  checker tuning. Rule IDs follow the v2 rules proposal; P-M2 was removed before this
  run (see BACKLOG.md).
</footer>
</div>
"""

page = page.replace("__TABLE__", table).replace("__FINDINGS__", FINDINGS)
dest = os.path.join(ROOT, "notes", "check-matrix-report.html")
with open(dest, "w") as f:
    f.write(page)
print(f"wrote {dest}")
