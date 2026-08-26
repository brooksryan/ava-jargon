"""W-M2 inverted construction ban.

The checker finds the "it is not X, it is Y" shape and the "not only X, but Y"
shape. The agent judges the symmetric contrast pair, for example "The tool did
not change. The workflow did."
"""
import re

from .common import scan, strip_code

RULE = "W-M2"
SETS = ("westinghouse", "technical", "personal")
LIMIT = ("closed shape only: the agent judges the symmetric contrast pair "
         "across two sentences")

PATTERNS = [
    ("inverted construction",
     re.compile(r"\b(it'?s|that'?s|this is|isn'?t|is not|not)\b[^.!?\n]{2,60}?,"
                r"\s*(it'?s|its|it is)\b", re.I)),
    ("not-only construction",
     re.compile(r"\bnot (just|only|about)\b[^.!?\n]{2,60}?,?\s*(but|it'?s)\b", re.I)),
]


def check(text, ctx):
    body = strip_code(text)
    out = []
    for label, pattern in PATTERNS:
        out += scan(body, pattern, RULE, label)
    return out
