"""P-M1 short-name rule. Brooks writes modeler, b-gate, and hydralib."""
import re

from ..common import Finding, line_of, line_starts, strip_code

RULE = "P-M1"
SETS = ("personal",)

NAMES = {
    "evo-modeler": "modeler",
    "evo-b-gate": "b-gate",
    "evo-hydra-lib": "hydralib",
}
PATTERN = re.compile(r"\bevo-(?:modeler|b-gate|hydra-lib)\b", re.I)


def check(text, ctx):
    body = strip_code(text)
    starts = line_starts(body)
    return [Finding(RULE, line_of(starts, m.start()), "short name", m.group(0),
                    NAMES[m.group(0).lower()])
            for m in PATTERN.finditer(body)]
