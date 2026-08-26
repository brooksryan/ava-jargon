"""T-M9 no idiom, no slang, no flourish.

The checker holds a known idiom list. The agent judges a new idiom. The rule
belongs to the Technical Documentation set only, because an anchor can carry an
idiom in Brooks's own voice.
"""
import re

from .common import scan, strip_code

RULE = "T-M9"
SETS = ("technical",)
LIMIT = "known idioms only: the agent judges a new idiom"

IDIOMS = [
    r"touch(?:ing|ed)? base",
    r"moving forward",
    r"paint(?:s|ed|ing)? a picture",
    r"circl(?:e|ing|ed) back",
    r"deep div(?:e|ing)",
    r"low-hanging fruit",
    r"at the end of the day",
    r"on the same page",
    r"hit the ground running",
    r"mov(?:e|es|ed|ing) the needle",
    r"boil the ocean",
    r"double(?:d)? down",
    r"in the weeds",
    r"heavy lifting",
    r"apples to apples",
    r"under the hood",
    r"out of the box",
    r"table stakes",
    r"north star",
    r"game changer",
]
PATTERN = re.compile(r"\b(?:" + "|".join(IDIOMS) + r")\b", re.I)


def check(text, ctx):
    return scan(strip_code(text), PATTERN, RULE, "idiom")
