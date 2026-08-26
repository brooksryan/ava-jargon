"""T-M1 sentence length. An instruction takes 20 words. A description takes 25.

The parser classifies the sentence. An imperative root verb marks an
instruction. A hyphenated compound and a technical name each count as one word.
"""
from ..common import Finding, count_words, line_of, line_starts, one_line
from . import doc_of, is_imperative, sentences

RULE = "T-M1"
SETS = ("technical",)
INSTRUCTION_LIMIT = 20
DESCRIPTION_LIMIT = 25


def check(text, ctx):
    doc = doc_of(text)
    if doc is None:
        return []
    starts = line_starts(text)
    out = []
    for sent in sentences(doc):
        body = sent.text.strip()
        words = count_words(body)
        instruction = is_imperative(sent)
        limit = INSTRUCTION_LIMIT if instruction else DESCRIPTION_LIMIT
        if words <= limit:
            continue
        kind = "instruction" if instruction else "description"
        out.append(Finding(RULE, line_of(starts, sent.start_char),
                           f"{words}-word {kind}, limit {limit}", one_line(body)))
    return out
