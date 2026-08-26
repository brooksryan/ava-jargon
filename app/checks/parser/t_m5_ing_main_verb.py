"""T-M5 no -ing main verb.

The checker tests the root verb tag for `VBG`. A technical name and an approved
adjective such as "the following" never hold the root, so both stay exempt.
"""
from ..common import Finding, line_of, line_starts, one_line
from . import doc_of, sentences

RULE = "T-M5"
SETS = ("technical",)


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for sent in sentences(doc):
        root = sent.root
        if root.tag_ != "VBG":
            continue
        out.append(Finding(RULE, line_of(starts, sent.start_char),
                           f"-ing main verb ({root.text})", one_line(sent.text)))
    return out
