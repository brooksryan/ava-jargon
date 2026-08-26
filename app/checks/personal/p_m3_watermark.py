"""P-M3 anchor hygiene.

The agent marks its own Slack message with U+2060 U+2060. The legacy mark is
U+200B U+2060. A message that holds either pair is never an anchor.
"""
import re

from ..common import scan

RULE = "P-M3"
SETS = ("personal",)

CURRENT = "⁠⁠"
LEGACY = "​⁠"
PATTERN = re.compile(f"{CURRENT}|{LEGACY}")


def check(text, ctx):
    # A mark can sit inside a code span, so this rule reads the source text.
    return scan(text, PATTERN, RULE, "agent watermark")
