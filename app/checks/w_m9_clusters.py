"""W-M9 cluster ban. No emoji cluster and no exclamation cluster.

A cluster is two adjacent marks. A wider window counts two separate exclamatory
sentences as a cluster: that window fired 13 times in the 5,733 Slack messages
that Brooks typed, against 1 time for the adjacent pair. Brooks writes "Safe
travels! Welcome to Evolve!", so the wide window tests the writer, not the rule.
"""
import re

from .common import scan, strip_code

RULE = "W-M9"
SETS = ("westinghouse", "technical", "personal")

PATTERNS = [
    ("emoji cluster", re.compile(r"(?:[\U0001F300-\U0001FAFF✀-➿]\s*){2,}")),
    ("exclamation cluster", re.compile(r"!\s*!+")),
]


def check(text, ctx):
    body = strip_code(text)
    out = []
    for label, pattern in PATTERNS:
        out += scan(body, pattern, RULE, label)
    return out
