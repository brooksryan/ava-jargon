"""T-M12 sequences are numbered lists. One action per item.

The checker finds two actions joined inside one item. A conjunction such as
"and then" joins them. An item that holds two full sentences passes, because
both gated plans use that form and both gates passed it.
"""
import re

from .common import Finding, list_items, strip_code

RULE = "T-M12"
SETS = ("technical",)

JOINERS = re.compile(r",\s*then\s|\band then\b|\band also\b|;\s", re.I)


def check(text, ctx):
    out = []
    for line, ordered, body in list_items(strip_code(text)):
        if not ordered:
            continue
        hit = JOINERS.search(body)
        if hit:
            out.append(Finding(RULE, line, "two actions in one item",
                               body[:70].strip()))
    return out
