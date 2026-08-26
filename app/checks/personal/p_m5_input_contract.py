"""P-M5 input contract.

The gate needs six fields. The runner supplies them with `--field NAME=VALUE`,
and the runner skips this rule when the caller supplies none.
"""
from ..common import Finding

RULE = "P-M5"
SETS = ("personal",)

REQUIRED = ("content", "surface", "destination_type", "channel_id", "audience",
            "intent")


def check(text, ctx):
    if ctx.fields is None:
        return []
    fields = dict(ctx.fields)
    fields.setdefault("content", text.strip())
    return [Finding(RULE, 1, "missing field", name)
            for name in REQUIRED if not str(fields.get(name, "")).strip()]
