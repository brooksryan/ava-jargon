"""W-M10 jargon score.

The checker calls the scoring engine in `app/jargon.py` directly. `--lexicon`
enables the rule, and the runner skips the rule without that path. The densities
go to stderr as notes, because stdout holds findings only. Unapproved terms are
notes as well, never findings.
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
    ctx.jargon_summary = res
    ctx.notes.append(
        f"{ctx.path}: jargon density {res['jargon_density_per_1k']}, "
        f"unapproved unigrams {res['unapproved_unigram_density_per_1k']}, "
        f"unapproved bigrams {res['unapproved_bigram_density_per_1k']} "
        f"per 1,000 content words, approved coverage {res['approved_coverage']:.0%}")
    for label, terms in (("unapproved unigrams", res["unapproved_unigrams"]),
                         ("unapproved bigrams", res["unapproved_bigrams"])):
        if terms:
            top = ", ".join(f"{t}×{c}" for t, c in list(terms.items())[:5])
            ctx.notes.append(f"{ctx.path}: {label}: {top}")
    body = strip_code(text)
    lower = body.lower()
    starts = line_starts(body)
    out = []
    for term, stats in res["flagged"].items():
        pos = lower.find(term)
        out.append(Finding(RULE, line_of(starts, pos) if pos >= 0 else 1,
                           f"jargon term x{stats['count']}", term))
    return out
