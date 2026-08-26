"""Baseline-band comparison for check output.

Reads app/checks/baselines.json (built by app/scripts/build_baselines.py) and
turns a run's per-rule counts into band positions. Direction matters: an
ai-high rule compares against both the human band and the AI reference; a
human-high rule is a compliance dial and only ever compares against the human
band, so its wording can never call a high rate AI evidence.
"""
import json
import os
from collections import Counter

MIN_WORDS = 300  # below this a rate is noise: one dash in 200 words reads 5/1k

SURFACES = ("chat", "doc-shared", "doc-technical", "code")

# The default band surface for each rule set. westinghouse maps to no surface:
# the caller names one with --surface or the footer explains how.
RULES_TO_SURFACE = {"personal": "chat", "technical": "doc-technical"}

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines.json")


def load():
    """Return the baselines document, or None when the file is absent."""
    if not os.path.isfile(_PATH):
        return None
    with open(_PATH) as f:
        return json.load(f)


def rule_counts(findings):
    return Counter(f.rule for f in findings)


def _position(rate, entry):
    """Return (position, detail) for one rule's rate against its bands."""
    hu = entry.get("human_universal")
    ai = entry.get("ai_universal", entry.get("ai_internal"))
    if entry.get("direction") == "human-high":
        if hu is None:
            return "no-band", ""
        state = "within human range" if rate <= hu[1] else "above human range (style)"
        return state, "compliance dial"
    if hu is None:
        return "no-band", ""
    if ai is not None and rate >= ai:
        return "ai-range", ""
    if rate > hu[1]:
        return "elevated", ""
    return "human-band", ""


def _fmt(v):
    return "0" if v == 0 else (f"{v:.2f}".rstrip("0").rstrip(".") if v < 10 else f"{v:.1f}")


def summarize(findings, words, surface, rules_checked):
    """Return (lines, data): the stderr footer lines and the --json object."""
    base = load()
    if base is None:
        return (["bands: app/checks/baselines.json is absent, no band comparison"],
                {"surface": surface, "available": False})
    if surface is None:
        return (["bands: pass --surface chat|doc-shared|doc-technical|code "
                 "for band comparison"],
                {"surface": None, "available": False})
    counts = rule_counts(findings)
    data = {"surface": surface, "words": words, "available": True, "rules": {}}
    if words < MIN_WORDS:
        return ([f"bands: sample too small ({words} words < {MIN_WORDS}), "
                 "counts only, no band comparison"],
                {**data, "guard": "small-sample"})
    table = base["surfaces"].get(surface, {})
    show = sorted(set(counts) | ({"W-M1"} & set(rules_checked)))
    lines = [f"band summary (surface: {surface}, {words:,} words):"]
    for rule in show:
        entry = table.get(rule)
        if entry is None:
            continue
        rate = round(1000 * counts.get(rule, 0) / words, 2)
        pos, note = _position(rate, entry)
        hu = entry.get("human_universal")
        hi = entry.get("human_internal")
        ai = entry.get("ai_universal", entry.get("ai_internal"))
        parts = [f"  {rule}  {_fmt(rate)}/1k"]
        if hu:
            parts.append(f"human {_fmt(hu[0])}-{_fmt(hu[1])}")
        if hi:
            parts.append(f"int {_fmt(hi[0])}-{_fmt(hi[1])}")
        if ai is not None and entry.get("direction") != "human-high":
            parts.append(f"ai ~{_fmt(ai)}")
        if note:
            parts.append(note)
        lines.append(" · ".join(parts) + f" -> {pos}")
        data["rules"][rule] = {
            "rate_per_1k": rate, "position": pos,
            "direction": entry.get("direction"),
            "human_universal": hu, "human_internal": hi,
            "ai_universal": entry.get("ai_universal"),
            "ai_internal": entry.get("ai_internal"),
        }
    return lines, data
