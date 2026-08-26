"""W-M3 assistant-phrase list. Eleven phrases, each one a fixed string."""
import re

from .common import scan, strip_code

RULE = "W-M3"
SETS = ("westinghouse", "technical", "personal")

PHRASES = [
    r"certainly",
    r"i'?d be happy to",
    r"great question",
    r"happy to help",
    r"i hope this helps",
    r"let me know if you have any questions",
    r"don'?t hesitate",
    r"i'?m excited to share",
    r"thrilled to",
    r"in summary",
    r"to recap",
]
PATTERN = re.compile(r"\b(?:" + "|".join(PHRASES) + r")\b", re.I)


def check(text, ctx):
    return scan(strip_code(text), PATTERN, RULE, "assistant phrase")
