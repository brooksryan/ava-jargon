#!/usr/bin/env python3
"""Run every mechanical checker over every corpus. One JSON out.

Rows: corpora, grouped by source. Columns: rules. Cell: findings per 1,000
words plus raw counts. Run with the venv python so tier 2 loads.
Writes audit/raw/check_matrix.json.
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, ROOT)

from app import checks  # noqa: E402
from app.checks import Context  # noqa: E402

C = os.path.join(ROOT, "corpus")

# (group, label, path). Combined all_humans/all_agents dirs are supersets and
# stay out so no message counts twice.
CORPORA = [
    ("Brooks (human)", "brooks-all-slack", f"{C}/brooks-all-slack"),
    ("Brooks (human)", "brooks-claude-prompts", f"{C}/brooks-claude-prompts"),
    ("Team + customer (human)", "internal-slack-messages", f"{C}/internal-slack-messages"),
    ("Team + customer (human)", "customer-slack-messages", f"{C}/customer-slack-messages"),
    ("Team + customer (human)", "customer-linear-messages", f"{C}/customer-linear-messages"),
    ("Agent drafts (pre-gate)", "slack-drafts before", f"{C}/slack-agent-messages/before"),
    ("Agent drafts (pre-gate)", "comments before", f"{C}/comment-adversary-agent-comments/before"),
    ("Agent drafts (pre-gate)", "process-scrub before", f"{C}/process-scrub-agent-mixed/before"),
    ("Agent drafts (pre-gate)", "ste100 before", f"{C}/ste100-agent-mixed/before"),
    ("Agent shipped (post-gate)", "slack-drafts after", f"{C}/slack-agent-messages/after"),
    ("Agent shipped (post-gate)", "comments after", f"{C}/comment-adversary-agent-comments/after"),
    ("Agent shipped (post-gate)", "process-scrub after", f"{C}/process-scrub-agent-mixed/after"),
    ("Agent shipped (post-gate)", "ste100 after", f"{C}/ste100-agent-mixed/after"),
    ("Agent documents", "evolv-agent-artifacts", f"{C}/evolv-agent-artifacts"),
    ("Agent documents", "notion-howto", f"{C}/notion-howto_2026-08-19"),
    ("Baselines", "wikipedia-computing", f"{C}/baseline-wikipedia-computing"),
    ("Baselines", "workplace-email", f"{C}/baseline-workplace-email"),
]

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


def docs_of(path):
    out = []
    for dirpath, _, names in os.walk(path):
        for n in sorted(names):
            if n.endswith(".txt"):
                out.append(os.path.join(dirpath, n))
    return sorted(out)


def main():
    # Every implemented rule, once: personal covers P rules, technical covers
    # T rules; the union with parser is the full set. W-M10 (needs a lexicon,
    # covered by the jargon pipeline) and P-M5 (needs caller fields) stay out.
    ctx = Context(path="", lexicon=None, fields=None)
    sel_p, _, _, _ = checks.select("personal", ctx, use_parser=True)
    sel_t, _, _, _ = checks.select("technical", ctx, use_parser=True)
    by_rule = {m.RULE: m for m in sel_p + sel_t}
    modules = [by_rule[r] for r in sorted(by_rule)]
    rules = [m.RULE for m in modules]
    print(f"rules: {rules}", file=sys.stderr)

    out = {"rules": rules, "groups": []}
    groups = {}
    for group, label, path in CORPORA:
        files = docs_of(path)
        counts = {r: 0 for r in rules}
        docs_hit = {r: 0 for r in rules}
        words = 0
        for i, fp in enumerate(files):
            text = open(fp, errors="ignore").read()
            words += len(WORD_RE.findall(text))
            c = Context(path=fp, lexicon=None, fields=None)
            seen = set()
            for m in modules:
                fs = m.check(text, c)
                if fs:
                    counts[m.RULE] += len(fs)
                    if m.RULE not in seen:
                        docs_hit[m.RULE] += 1
                        seen.add(m.RULE)
            if i and i % 1000 == 0:
                print(f"  {label}: {i}/{len(files)}", file=sys.stderr)
        row = {
            "label": label, "docs": len(files), "words": words,
            "counts": counts, "docs_hit": docs_hit,
            "per_1k_words": {r: round(1000 * counts[r] / max(words, 1), 2)
                             for r in rules},
        }
        groups.setdefault(group, []).append(row)
        total = sum(counts.values())
        print(f"{label}: {len(files)} docs, {words} words, "
              f"{total} findings", file=sys.stderr)

    for group, _, _ in CORPORA:
        if group in groups:
            out["groups"].append({"name": group, "rows": groups.pop(group)})

    dest = os.path.join(ROOT, "audit", "raw", "check_matrix.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
