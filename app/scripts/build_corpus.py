#!/usr/bin/env python3
"""Regenerate corpus/ from audit/curated/ — one .txt per source text.

Layout: corpus/<agent-dir>/{before,after}/NNN_date_slug.txt
The -mixed dirs hold several source kinds (docs, commit messages, comments,
retros); split them by source when the pairs carry a source tag.
"""
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT = os.path.join(ROOT, "audit")

DIRS = {
    "brooks-slack-voice": "slack-agent-messages",
    "comment-adversary": "comment-adversary-agent-comments",
    "process-scrub-reviewer": "process-scrub-agent-mixed",
    "ste100-validator": "ste100-agent-mixed",
}


def clean(t):
    return (t or "").replace("\\n", "\n").replace('\\"', '"')


def slug(s, n=44):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:n].rstrip("-") or "pair"


README = {
    "slack-agent-messages":
        "16 pairs from the brooks-slack-voice gate's FAIL chains (Claude Code "
        "transcripts, Jun 30 - Aug 14, 2026). before/ = first draft; after/ = the "
        "message actually posted to Slack.",
    "comment-adversary-agent-comments":
        "30 finding-level pairs from the comment-adversary code-comment gate "
        "(Jul 2026). before/ = offending comment; after/ = text applied to the file.",
    "process-scrub-agent-mixed":
        "34 finding-level pairs from the process-scrub-reviewer gate (Jul-Aug 2026). "
        "Mixed sources: comments, commit messages, docs. before/ = offending prose; "
        "after/ = applied text.",
    "ste100-agent-mixed":
        "30 finding-level pairs from the ste100-validator STE gate (Jul-Aug 2026). "
        "Mixed sources: design docs, retros, module headers. before/ = offending "
        "sentence; after/ = applied rewrite.",
}


def main():
    corpus = os.path.join(ROOT, "corpus")
    total = 0
    for full, name in DIRS.items():
        agent_dir = os.path.join(corpus, name)
        if os.path.isdir(agent_dir):
            shutil.rmtree(agent_dir)  # only this script's own dirs, never all of corpus/
        with open(os.path.join(AUDIT, "curated", f"{full}.json")) as f:
            pairs = json.load(f)["pairs"]
        for side in ("before", "after"):
            os.makedirs(os.path.join(agent_dir, side), exist_ok=True)
        with open(os.path.join(agent_dir, "README.md"), "w") as f:
            f.write(f"# {name}\n{README[name]}\nSame filename in before/ and after/ = "
                    f"same pair. Source: audit/curated/{full}.json - regenerate: "
                    "python3 app/scripts/build_corpus.py\n")
        for i, p in enumerate(pairs):
            date = (p.get("timestamp") or "")[:10] or "undated"
            base = f"{i:03d}_{date}_{slug(p.get('context'))}.txt"
            for side in ("before", "after"):
                path = os.path.join(corpus, name, side, base)
                with open(path, "w") as f:
                    f.write(clean(p.get(side)).strip() + "\n")
                total += 1
        print(f"{name}: {len(pairs)} pairs")
    print(f"total files: {total}")


if __name__ == "__main__":
    main()
