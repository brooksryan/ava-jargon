"""T-M3 paragraph limit. Six sentences maximum, one topic.

The checker reads prose paragraphs only. A block that holds a heading, a list
item, a table row, or a quote is not a paragraph.
"""
from .common import Finding, paragraphs, split_sentences, strip_code

RULE = "T-M3"
SETS = ("technical",)
LIMIT_SENTENCES = 6


def check(text, ctx):
    out = []
    for line, body in paragraphs(strip_code(text)):
        count = len(split_sentences(body))
        if count > LIMIT_SENTENCES:
            out.append(Finding(RULE, line, f"{count} sentences in one paragraph",
                               body[:60].strip()))
    return out
