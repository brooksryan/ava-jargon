"""The mechanical-checker runner.

One import line per checker and no discovery logic. A rule enters with one new
file and one import line, and leaves the same way.

Each checker declares three names:

1. `RULE` holds the rule identifier, for example "W-M1".
2. `SETS` holds the rule sets that include the rule.
3. `check(text, ctx)` returns the findings for one document.

The `ctx` record carries the path, the lexicon, and the input fields. Two rules
need it: W-M10 reads the lexicon and P-M5 reads the fields.
"""
from .common import Context, Finding  # noqa: F401  (the public record types)

# The P-* rules live in the optional `personal` subpackage, which the package
# build does not include. These guards keep the runner working without it.
try:
    from .personal import p_m1_short_names
    from .personal import p_m3_watermark
    from .personal import p_m5_input_contract
except ImportError:
    p_m1_short_names = p_m3_watermark = p_m5_input_contract = None
from . import t_m3_paragraph_limit
from . import t_m11_condition_first
from . import t_m12_numbered_lists
from . import w_m1_dash
from . import w_m3_assistant_phrases
from . import w_m4_register_words
from . import w_m6_hedge_phrases
from . import w_m8_process_language
from . import w_m9_clusters
from . import w_m10_jargon_score

from . import t_m8_approved_vocabulary
from . import t_m9_idioms
from . import w_m2_inversion
from . import w_m7_opener

RULE_SETS = ("westinghouse", "technical", "personal")

# Tier 1: the standard library finds the whole rule.
TIER_1 = [
    w_m1_dash,
    w_m3_assistant_phrases,
    w_m4_register_words,
    w_m6_hedge_phrases,
    w_m8_process_language,
    w_m9_clusters,
    w_m10_jargon_score,
    t_m3_paragraph_limit,
    t_m11_condition_first,
    t_m12_numbered_lists,
]
TIER_1 += [m for m in (p_m1_short_names, p_m3_watermark, p_m5_input_contract)
           if m is not None]

# Tier 1b: the standard library finds the closed list. The agent judges the rest.
TIER_1B = [
    w_m2_inversion,
    w_m7_opener,
    t_m8_approved_vocabulary,
    t_m9_idioms,
]


# The tier 2 rules and their sets. This table lets the runner name a skipped
# tier 2 rule without an import, which keeps `spacy` out of a tier 1 run.
TIER_2_RULES = (
    ("T-M1", ("technical",)),
    ("T-M2", ("technical",)),
    ("T-M4", ("technical",)),
    ("T-M5", ("technical",)),
    ("T-M7", ("technical",)),
    ("T-M10", ("technical",)),
    ("W-M11", ("technical",)),
)


def load_tier_2():
    """Import the tier 2 checkers. The `spacy` import happens here, never before.

    Returns (checkers, ready, reason). `ready` is False when the parser or the
    model is absent, and `reason` names the missing part.
    """
    from .parser import available
    from .parser import t_m1_sentence_length
    from .parser import t_m2_one_instruction
    from .parser import t_m4_simple_tenses
    from .parser import t_m5_ing_main_verb
    from .parser import t_m7_noun_clusters
    from .parser import t_m10_imperative
    from .parser import w_m11_passive_voice

    checkers = [
        t_m1_sentence_length,
        t_m2_one_instruction,
        t_m4_simple_tenses,
        t_m5_ing_main_verb,
        t_m7_noun_clusters,
        t_m10_imperative,
        w_m11_passive_voice,
    ]
    ready, reason = available()
    return checkers, ready, reason


def select(rules, ctx, use_parser=False):
    """Return (checkers, tiers_run, rules_skipped, warning) for one run.

    A rule is skipped when its input is absent: W-M10 needs a lexicon, P-M5
    needs the input fields, and every tier 2 rule needs the parser.
    """
    if rules not in RULE_SETS:
        raise ValueError(f"unknown rule set: {rules}")
    chosen = [m for m in TIER_1 + TIER_1B if rules in m.SETS]
    tiers, skipped, warning = ["1", "1b"], [], ""

    if ctx.lexicon is None:
        chosen = [m for m in chosen if m is not w_m10_jargon_score]
        skipped.append(w_m10_jargon_score.RULE)
    if (p_m5_input_contract is not None and ctx.fields is None
            and rules in p_m5_input_contract.SETS):
        chosen = [m for m in chosen if m is not p_m5_input_contract]
        skipped.append(p_m5_input_contract.RULE)

    wanted = [rule for rule, sets in TIER_2_RULES if rules in sets]
    if use_parser:
        tier_2, ready, warning = load_tier_2()
        run_now = [m for m in tier_2 if rules in m.SETS]
        if ready and run_now:
            tiers.append("2")
            chosen += run_now
        else:
            skipped += wanted
    else:
        skipped += wanted
    return chosen, tiers, sorted(set(skipped)), warning


def check_document(text, ctx, checkers):
    """Run every selected checker over one document."""
    out = []
    for module in checkers:
        out += [f.with_path(ctx.path) for f in module.check(text, ctx)]
    return sort_findings(out)


def sort_findings(findings):
    return sorted(findings, key=lambda f: (f.path, f.line, f.rule, f.match))


def report_text(findings):
    """Return the linter form: one finding per line."""
    return "\n".join(f.as_line() for f in findings)


def report_json(paths, rules, tiers, skipped, findings, rules_checked):
    """Return the JSON form as one dictionary."""
    return {
        "paths": list(paths),
        "rules": rules,
        "tiers_run": list(tiers),
        "rules_skipped": list(skipped),
        "findings": [f.as_dict() for f in findings],
        "counts": {"findings": len(findings), "rules_checked": rules_checked},
    }
