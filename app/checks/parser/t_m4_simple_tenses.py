"""T-M4 simple tenses only.

The checker finds a form of "have" and a past participle within three tokens.
The pattern covers "has been", "had done", and the conditional perfect.
"""
from ..common import Finding, line_of, line_starts, one_line
from . import doc_of, sentences

RULE = "T-M4"
SETS = ("technical",)

HAVE = {"have", "has", "had", "having", "'ve", "'s", "'d"}


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for sent in sentences(doc):
        for token in sent:
            if token.text.lower() not in HAVE or token.pos_ not in ("AUX", "VERB"):
                continue
            window = [t for t in sent if t.i > token.i][:3]
            hit = next((t for t in window if t.tag_ == "VBN"), None)
            if hit is None:
                continue
            out.append(Finding(RULE, line_of(starts, sent.start_char),
                               f"perfect tense ({token.text} {hit.text})",
                               one_line(sent.text)))
            break
    return out
