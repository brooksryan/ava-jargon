"""W-M10 jargon score.

The checker calls the scoring engine in `app/jargon.py` directly. `--lexicon`
enables the rule, and the runner skips the rule without that path. The density
goes to stderr as a note, because stdout holds findings only.
"""
import sys
from pathlib import Path

try:
    from .. import jargon as J  # installed package layout
except ImportError:  # flat script layout: the engine sits one directory up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import jargon as J

from .common import Finding, line_of, line_starts, strip_code

RULE = "W-M10"
SETS = ("westinghouse", "technical", "personal")


def check(text, ctx):
    if ctx.lexicon is None:
        return []
    path = Path(ctx.path)
    if path.is_file():
        res = J.score_file(path, ctx.lexicon)
    else:
        res = J.score_tokens(J.tokenize(text), ctx.lexicon)
    ctx.notes.append(
        f"{ctx.path}: jargon density {res['jargon_density_per_1k']} per 1,000 "
        f"tokens, approved coverage {res['approved_coverage']:.0%}")
    body = strip_code(text)
    lower = body.lower()
    starts = line_starts(body)
    out = []
    for term, stats in res["flagged"].items():
        pos = lower.find(term)
        out.append(Finding(RULE, line_of(starts, pos) if pos >= 0 else 1,
                           f"jargon term x{stats['count']}", term))
    return out
