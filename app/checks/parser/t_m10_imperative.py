"""T-M10 instructions are imperative.

Write "Confirm the scope." not "You should confirm the scope." The checker
reads each list item and finds the second-person modal form. A descriptive list
item is not an instruction, so the checker leaves it alone.
"""
from ..common import Finding, list_items, strip_code
from . import parse_fragment

RULE = "T-M10"
SETS = ("technical",)

MODALS = {"should", "must", "can", "could", "need", "have", "may", "might", "will"}


def check(text, ctx):
    out = []
    for line, ordered, body in list_items(strip_code(text)):
        doc = parse_fragment(body)
        if doc is None:
            return []
        subject = next((t for t in doc
                        if t.dep_ == "nsubj" and t.text.lower() in ("you", "we")), None)
        if subject is None:
            continue
        head = subject.head
        modal = next((t for t in head.children
                      if t.dep_ in ("aux", "auxpass") and t.text.lower() in MODALS), None)
        if modal is None:
            continue
        out.append(Finding(RULE, line,
                           f"non-imperative instruction ({subject.text} {modal.text})",
                           body[:70].strip(), f"{head.text.capitalize()} ..."))
    return out
