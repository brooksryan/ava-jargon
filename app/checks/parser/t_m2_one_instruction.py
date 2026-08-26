"""T-M2 one instruction per sentence.

The checker counts the imperative verbs of each sentence. A second base-form
verb that the parser joins to the root with `conj` is a second instruction.
"""
from ..common import Finding, line_of, line_starts, one_line
from . import doc_of, is_imperative, sentences

RULE = "T-M2"
SETS = ("technical",)


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for sent in sentences(doc):
        if not is_imperative(sent):
            continue
        extra = [t for t in sent
                 if t.dep_ == "conj" and t.tag_ == "VB" and t.head == sent.root]
        if not extra:
            continue
        verbs = ", ".join([sent.root.text] + [t.text for t in extra])
        out.append(Finding(RULE, line_of(starts, sent.start_char),
                           f"{len(extra) + 1} instructions ({verbs})",
                           one_line(sent.text)))
    return out
