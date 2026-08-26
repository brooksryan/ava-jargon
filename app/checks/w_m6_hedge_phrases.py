"""W-M6 hedge-phrase list. Seven phrases."""
import re

from .common import scan, strip_code

RULE = "W-M6"
SETS = ("westinghouse", "technical", "personal")

PHRASES = [
    r"seemed worth (?:flagging|looking)",
    r"for what it'?s worth",
    r"just my two cents",
    r"no urgency from me",
    r"may or may not be useful",
    r"i believe",
    r"i feel that",
]
PATTERN = re.compile(r"\b(?:" + "|".join(PHRASES) + r")\b", re.I)


def check(text, ctx):
    return scan(strip_code(text), PATTERN, RULE, "hedge phrase")
