#!/usr/bin/env python3
"""Build per-rule, per-surface baseline bands from the corpus library.

Implements the band computation from notes/baseline-bands-plan.md. Runs every
checker (tier 1 + parser) over every mapped corpus (.txt only), then writes:

  audit/raw/baselines_run.json   per-corpus per-rule rates (page builder input)
  app/checks/baselines.json      the bands ava check will read

Bands: human = [min, max] corpus-level rate per 1k words across that surface's
human corpora; agent = median across its AI corpora. Universal (public) and
internal (Evolv) sides are kept separate per Brooks's ship-both requirement.
Run with the venv python so the parser tier loads.
"""
import json
import os
import re
import statistics
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "app"))

from app import checks  # noqa: E402
from app.checks import Context  # noqa: E402

C = "corpus"

# (surface, side, origin, label, path). side: human|ai. origin: universal|internal.
CORPORA = [
    ("chat", "human", "internal", "brooks-all-slack", f"{C}/brooks-all-slack"),
    ("chat", "human", "internal", "internal-slack-messages", f"{C}/internal-slack-messages"),
    ("chat", "human", "internal", "customer-slack-messages", f"{C}/customer-slack-messages"),
    ("chat", "human", "internal", "customer-linear-messages", f"{C}/customer-linear-messages"),
    ("chat", "human", "internal", "brooks-claude-prompts", f"{C}/brooks-claude-prompts"),
    ("chat", "human", "universal", "hn-comments-pre2022", f"{C}/hn-comments-pre2022"),
    ("chat", "human", "universal", "ubuntu-irc-pre2022", f"{C}/ubuntu-irc-pre2022"),
    ("chat", "human", "universal", "mailinglist-email-pre2022", f"{C}/mailinglist-email-pre2022"),
    ("chat", "human", "universal", "workplace-email (Enron)", f"{C}/baseline-workplace-email"),
    ("chat", "ai", "universal", "generated-chat-haiku", f"{C}/generated-chat-haiku"),
    ("chat", "ai", "universal", "generated-chat-opus", f"{C}/generated-chat-opus"),
    ("chat", "ai", "universal", "generated-chat-sonnet", f"{C}/generated-chat-sonnet"),
    ("chat", "ai", "universal", "wildchat-frontier-turns", f"{C}/wildchat-frontier-turns"),
    ("chat", "ai", "internal", "slack-agent-drafts (before)", f"{C}/slack-agent-messages/before"),
    ("chat", "ai", "internal", "agent-pasted-messages", f"{C}/agent-pasted-messages"),

    ("doc-shared", "human", "universal", "berkshire-letters", f"{C}/berkshire-letters"),
    ("doc-shared", "human", "universal", "bezos-letters", f"{C}/bezos-letters"),
    ("doc-shared", "human", "universal", "pg-essays-pre2022", f"{C}/pg-essays-pre2022"),
    ("doc-shared", "human", "universal", "howard-marks-memos", f"{C}/howard-marks-memos"),
    ("doc-shared", "human", "universal", "grantland-articles", f"{C}/grantland-articles"),
    ("doc-shared", "human", "universal", "increment-articles", f"{C}/increment-articles"),
    ("doc-shared", "human", "universal", "plainlanguage-guides", f"{C}/plainlanguage-guides"),
    ("doc-shared", "human", "universal", "wikipedia-computing", f"{C}/baseline-wikipedia-computing"),
    ("doc-shared", "ai", "universal", "ai-blogposts-post2024", f"{C}/ai-blogposts-post2024"),
    ("doc-shared", "ai", "universal", "ai-marketing-copy-post2024", f"{C}/ai-marketing-copy-post2024"),

    ("doc-technical", "human", "universal", "rfc-technical", f"{C}/rfc-technical"),
    ("doc-technical", "human", "universal", "oss-docs-pre2022", f"{C}/oss-docs-pre2022"),
    ("doc-technical", "human", "universal", "arxiv-cs-pre2022", f"{C}/arxiv-cs-pre2022"),
    ("doc-technical", "human", "universal", "distill-pub", f"{C}/distill-pub"),
    ("doc-technical", "human", "universal", "sre-book", f"{C}/sre-book"),
    ("doc-technical", "ai", "internal", "evolv-agent-artifacts", f"{C}/evolv-agent-artifacts"),
    ("doc-technical", "ai", "internal", "notion-howto", f"{C}/notion-howto_2026-08-19"),
    ("doc-technical", "ai", "universal", "ai-github-docs-post2024", f"{C}/ai-github-docs-post2024"),

    ("code", "human", "universal", "github-readmes-human-pre2022", f"{C}/github-readmes-human-pre2022"),
    ("code", "human", "universal", "github-comments-human-pre2022", f"{C}/github-comments-human-pre2022"),
    ("code", "ai", "universal", "github-readmes-ai-post2024", f"{C}/github-readmes-ai-post2024"),
    ("code", "ai", "universal", "github-comments-ai-post2024", f"{C}/github-comments-ai-post2024"),
]

# Direction of each rule's signal, embedded per rule in baselines.json.
# ai-high: an authorship signal - AI text runs high, a high rate is AI evidence.
# human-high: a compliance dial - humans out-score AI on it everywhere, so a
# high rate means style drift, never AI authorship.
DIRECTIONS = {
    "W-M1": "ai-high", "W-M2": "ai-high", "W-M3": "ai-high", "W-M4": "ai-high",
    "W-M6": "ai-high", "W-M7": "ai-high", "W-M8": "ai-high", "W-M9": "ai-high",
    "P-M1": "ai-high", "P-M3": "ai-high",
    "W-M11": "human-high",
    "T-M1": "human-high", "T-M2": "human-high", "T-M3": "human-high",
    "T-M4": "human-high", "T-M5": "human-high", "T-M7": "human-high",
    "T-M8": "human-high", "T-M9": "human-high", "T-M10": "human-high",
    "T-M11": "human-high", "T-M12": "human-high",
}

# (corpus label, rule) pairs whose rate is a format artifact, never band input.
EXCLUDE = {
    ("rfc-technical", "W-M1"),  # ASCII-only source: dashes cannot occur
    # Prompts quote pasted tool/agent text (24 files carry dashes inside pasted
    # snippets), the same paste vector purged from brooks-all-slack 2026-08-22.
    ("brooks-claude-prompts", "W-M1"),
}

# Soft negatives and controls stay out of CORPORA entirely:
# ai-arxiv-post2024 (soft), control-wildchat-predash, control-lmsys-predash.

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


def docs_of(path):
    out = []
    for dirpath, _, names in os.walk(path):
        out += [os.path.join(dirpath, n) for n in sorted(names) if n.endswith(".txt")]
    return sorted(out)


def main():
    if "--reuse" in sys.argv and os.path.exists("audit/raw/baselines_run.json"):
        run = json.load(open("audit/raw/baselines_run.json"))
        write_bands(run)
        return
    ctx = Context(path="", lexicon=None, fields=None)
    sel_p, _, _, _ = checks.select("personal", ctx, use_parser=True)
    sel_t, _, _, _ = checks.select("technical", ctx, use_parser=True)
    by_rule = {m.RULE: m for m in sel_p + sel_t}
    modules = [by_rule[r] for r in sorted(by_rule)]
    rules = [m.RULE for m in modules]
    print(f"rules: {rules}", file=sys.stderr)

    run = {"rules": rules, "corpora": []}
    for surface, side, origin, label, path in CORPORA:
        files = docs_of(path)
        counts = {r: 0 for r in rules}
        words = 0
        for i, fp in enumerate(files):
            text = open(fp, errors="ignore").read()
            words += len(WORD_RE.findall(text))
            c = Context(path=fp, lexicon=None, fields=None)
            for m in modules:
                fs = m.check(text, c)
                if fs:
                    counts[m.RULE] += len(fs)
            if i and i % 1000 == 0:
                print(f"  {label}: {i}/{len(files)}", file=sys.stderr)
        run["corpora"].append({
            "surface": surface, "side": side, "origin": origin, "label": label,
            "docs": len(files), "words": words,
            "per_1k": {r: round(1000 * counts[r] / max(words, 1), 2) for r in rules},
            "counts": counts,
        })
        print(f"{label}: {len(files)} docs, {words} words, "
              f"{sum(counts.values())} findings", file=sys.stderr)

    with open("audit/raw/baselines_run.json", "w") as f:
        json.dump(run, f, indent=1)
    write_bands(run)


def write_bands(run):
    rules = run["rules"]
    # Bands.
    bands = {}
    surfaces = sorted({c["surface"] for c in run["corpora"]})
    for surface in surfaces:
        bands[surface] = {}
        rows = [c for c in run["corpora"] if c["surface"] == surface]
        for r in rules:
            entry = {}
            for side in ("human", "ai"):
                for origin in ("universal", "internal"):
                    vals = [c["per_1k"][r] for c in rows
                            if c["side"] == side and c["origin"] == origin
                            and (c["label"], r) not in EXCLUDE]
                    if not vals:
                        continue
                    key = f"{side}_{origin}"
                    if side == "human":
                        entry[key] = [min(vals), max(vals)]
                    else:
                        entry[key] = round(statistics.median(vals), 2)
                    entry[f"{key}_n"] = len(vals)
            entry["direction"] = DIRECTIONS.get(r, "ai-high")
            bands[surface][r] = entry
    out = {
        "meta": {
            "generated": "2026-08-25",
            "script": "app/scripts/build_baselines.py",
            "unit": "findings per 1,000 words, corpus-level",
            "band_rule": "human = [min,max] across corpora; ai = median",
            "min_words_guard": 300,
            "excluded_format_artifacts": sorted([list(x) for x in EXCLUDE]),
        },
        "surfaces": bands,
    }
    with open("app/checks/baselines.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote audit/raw/baselines_run.json + app/checks/baselines.json",
          file=sys.stderr)


if __name__ == "__main__":
    main()
