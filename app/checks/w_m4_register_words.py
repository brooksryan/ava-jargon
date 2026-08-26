"""W-M4 register-word list. Fifteen words, with their common inflections."""
import re

from .common import scan, strip_code

RULE = "W-M4"
SETS = ("westinghouse", "technical", "personal")

WORDS = [
    r"delve",
    r"tapestry",
    r"seamless(?:ly)?",
    r"robust",
    r"cutting-edge",
    r"best-in-class",
    r"world-class",
    r"leverag(?:e|ed|es|ing)",
    r"utiliz(?:e|ed|es|ing|ation)",
    r"unlock",
    r"synerg(?:y|ies)",
    r"passionate",
    r"spearhead(?:ed|ing)?",
    r"thought leader",
    r"comprehensive",
]
PATTERN = re.compile(r"\b(?:" + "|".join(WORDS) + r")\b", re.I)


def check(text, ctx):
    return scan(strip_code(text), PATTERN, RULE, "register word")
