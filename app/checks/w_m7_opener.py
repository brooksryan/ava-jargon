"""W-M7 opener check.

The checker tests the first sentence against five throat-clearing openers. The
agent judges whether the first sentence carries the answer or the news.
"""
import re

from .common import Finding, line_starts, line_of, strip_code

RULE = "W-M7"
SETS = ("westinghouse", "technical", "personal")
LIMIT = ("five fixed openers only: the agent judges whether the first sentence "
         "carries the answer")

OPENERS = [
    r"i'?ve been meaning to",
    r"i am writing to",
    r"i wanted to reach out",
    r"as an ai",
    r"(?:in this (?:document|doc|post)|this (?:document|doc) (?:will|aims))",
]
PATTERN = re.compile(r"^\s*(?:" + "|".join(OPENERS) + r")", re.I)


def check(text, ctx):
    body = strip_code(text)
    starts = line_starts(body)
    for m in re.finditer(r"[^\s][^\n]*", body):
        head = m.group(0)
        hit = PATTERN.match(head)
        if not hit:
            return []
        return [Finding(RULE, line_of(starts, m.start()), "throat-clearing opener",
                        head[:60].strip())]
    return []
