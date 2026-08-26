"""T-M8 one word, one meaning.

The checker holds the substitution list that the rule names. The agent judges
whether the document holds one term per concept.
"""
import re

from .common import Finding, line_of, line_starts, strip_code

RULE = "T-M8"
SETS = ("technical",)
LIMIT = ("substitution list only: the agent judges one term per concept across "
         "the document")

SUBSTITUTIONS = [
    (r"commenc(?:e|es|ed|ing|ement)", "start"),
    (r"perform(?:s|ed|ing)?", "do"),
    (r"utiliz(?:e|es|ed|ing|ation)", "use"),
    (r"indicat(?:e|es|ed|ing)", "show"),
    (r"approximately", "about"),
]
PATTERNS = [(re.compile(r"\b" + word + r"\b", re.I), fix)
            for word, fix in SUBSTITUTIONS]


def check(text, ctx):
    body = strip_code(text)
    starts = line_starts(body)
    out = []
    for pattern, fix in PATTERNS:
        for m in pattern.finditer(body):
            out.append(Finding(RULE, line_of(starts, m.start()),
                               "unapproved word", m.group(0), fix))
    return out
