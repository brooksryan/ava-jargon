"""T-M7 noun cluster limit. Three nouns maximum in a row.

The document that `doc_of` returns holds no heading and no list marker. The
parser therefore joins no two heading lines into one sentence, which was the
source of a false six-noun run in the feasibility probe.

The checker counts a run inside one noun phrase. The parser tags an occasional
verb as a noun, and that tag extends a three-noun phrase to a false four-noun
run. A noun phrase never holds the main verb, so the phrase boundary stops it.
"""
from ..common import Finding, line_of, line_starts
from . import doc_of

RULE = "T-M7"
SETS = ("technical",)
LIMIT = 3


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for chunk in doc.noun_chunks:
        run, longest = [], []
        for token in chunk:
            run = run + [token] if token.pos_ in ("NOUN", "PROPN") else []
            if len(run) > len(longest):
                longest = run
        if len(longest) > LIMIT:
            out.append(Finding(RULE, line_of(starts, longest[0].idx),
                               f"{len(longest)} nouns in a row",
                               " ".join(t.text for t in longest)))
    return out
