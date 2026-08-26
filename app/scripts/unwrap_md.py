#!/usr/bin/env python3
"""Unwrap hard-wrapped Markdown paragraphs to one line each.

The pre-commit hook runs this over staged .md files, so prose in the repo
wraps in the reader's viewport instead of at a fixed column. Code fences,
headings, tables, list markers, and quotes keep their own lines; a wrapped
continuation line joins the line above it. Idempotent.

Usage: unwrap_md.py FILE [FILE ...]   (rewrites in place; prints changed files)
"""
import re
import sys

FENCE = re.compile(r"^\s*(```|~~~)")
STRUCTURAL = re.compile(
    r"^\s*$"              # blank
    r"|^#{1,6} "          # heading
    r"|^\s*([-*+]|\d+\.) "  # list item
    r"|^\s*\|"            # table row
    r"|^\s*>"             # quote
    r"|^\s*[-=]{3,}\s*$"  # rule / setext underline
    r"|^<"                # raw html block
)
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.) ")


def joinable_next(line):
    """A line that may continue the previous paragraph or list item."""
    return not STRUCTURAL.match(line) and not FENCE.match(line)


def unwrap(text):
    lines = text.splitlines()
    out = []
    start = 0
    # YAML front matter passes through verbatim: its key: value lines would
    # otherwise read as one wrapped paragraph and join into a single line.
    if lines and lines[0].strip() == "---":
        try:
            end = lines.index("---", 1)
            out = lines[:end + 1]
            start = end + 1
        except ValueError:
            pass
    in_fence = False
    for line in lines[start:]:
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        prev = out[-1] if out else ""
        prev_joinable = prev and (not STRUCTURAL.match(prev)
                                  or LIST_ITEM.match(prev)) and not FENCE.match(prev)
        if prev_joinable and joinable_next(line):
            out[-1] = prev.rstrip() + " " + line.strip()
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def main():
    changed = 0
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new = unwrap(text)
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            print(path)
            changed += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
