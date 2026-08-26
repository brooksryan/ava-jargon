"""W-M11 active voice, named actor.

The rule moved from the judgment list (W-J2) to a mechanical checker, because
the parser marks a passive clause with `nsubjpass` and `auxpass`. The probe
returned no false positive on either gated plan.
"""
from ..common import Finding, line_of, line_starts, one_line
from . import doc_of, sentences

RULE = "W-M11"
# Demoted to technical-only 2026-08-25: passive runs 5-19/1k in normal human
# messages and edited prose, so it is a form dial, not a universal rule.
SETS = ("technical",)


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for sent in sentences(doc):
        mark = next((t for t in sent if t.dep_ in ("nsubjpass", "auxpass")), None)
        if mark is None:
            continue
        out.append(Finding(RULE, line_of(starts, sent.start_char),
                           f"passive clause ({mark.head.text})",
                           one_line(sent.text)))
    return out
