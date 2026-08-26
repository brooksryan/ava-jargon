"""W-M8 process-language scan.

The checker finds a ticket identifier, a slice or sprint or phase or milestone
reference, a PRD or spec or acceptance-criteria pointer, a dated decision log,
and change narration such as "this change adds" or "now reads".
"""
import re

from .common import scan, strip_code

RULE = "W-M8"
SETS = ("westinghouse", "technical", "personal")

PATTERNS = [
    # Brooks writes a ticket id in either case, for example "flex-360".
    ("ticket id", re.compile(r"(?:#\d+|\b(?:JIRA|LINEAR|GH|CE|EXEC|FLEX)-\d+)", re.I)),
    ("process reference",
     re.compile(r"\b(?:slice|sprint|phase|milestone) \d", re.I)),
    ("document pointer",
     re.compile(r"\b(?:per the (?:PRD|spec|object map|retro)|acceptance criteri"
                r"|decision log)", re.I)),
    ("change narration",
     re.compile(r"\b(?:this change (?:adds|makes)|now reads)\b", re.I)),
]


def check(text, ctx):
    body = strip_code(text)
    out = []
    for label, pattern in PATTERNS:
        out += scan(body, pattern, RULE, label)
    return out
