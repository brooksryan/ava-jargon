"""T-M11 condition first.

Write "If the build fails, stop." The checker finds a condition word that opens
the second clause of a sentence.
"""
import re

from .common import Finding, line_of, line_starts, split_sentences, strip_code

RULE = "T-M11"
SETS = ("technical",)

PATTERN = re.compile(r"^[A-Z][^.!?\n]{3,}?,\s*(?:if|when|unless)\b", re.I)


def check(text, ctx):
    body = strip_code(text)
    starts = line_starts(body)
    out = []
    for sentence in split_sentences(body):
        hit = PATTERN.match(sentence)
        if not hit:
            continue
        pos = body.find(sentence)
        out.append(Finding(RULE, line_of(starts, pos if pos >= 0 else 0),
                           "condition after the first clause",
                           re.sub(r"\s+", " ", hit.group(0))))
    return out
