"""W-M1 dash ban.

No em dash and no en dash. An en dash is allowed in a date range only.
"""
import re

from .common import Finding, line_of, line_starts, snippet, strip_code

RULE = "W-M1"
SETS = ("westinghouse", "technical", "personal")

EM_DASH = "—"
EN_DASH = "–"
DASH_RE = re.compile(f"[{EM_DASH}{EN_DASH}]")

# A date range reads "2024-2026" or "Jun 30 - Aug 14": a number closes the left
# side and a number opens the right side.
_LEFT_DATE_RE = re.compile(r"\d[\d,]*\s*$")
_RIGHT_DATE_RE = re.compile(r"^\s*\d")


def _is_date_range(text, pos):
    return bool(_LEFT_DATE_RE.search(text[max(0, pos - 12):pos])
                and _RIGHT_DATE_RE.match(text[pos + 1:pos + 13]))


def check(text, ctx):
    body = strip_code(text)
    starts = line_starts(body)
    out = []
    for m in DASH_RE.finditer(body):
        if m.group(0) == EN_DASH and _is_date_range(body, m.start()):
            continue
        label = "em dash" if m.group(0) == EM_DASH else "en dash"
        out.append(Finding(RULE, line_of(starts, m.start()), label,
                           snippet(body, m.start(), m.end(), 16)))
    return out
