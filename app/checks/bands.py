"""Baseline-band comparison for check output.

Reads one band table by name, from app/bands/ or a project or personal
.ava/bands/ directory, and turns a run's per-rule counts into band positions. Direction matters: an
ai-high rule compares against both the human band and the AI reference; a
human-high rule is a compliance dial and only ever compares against the human
band, so its wording can never call a high rate AI evidence.
"""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from ..schema_check import validate_against
except ImportError:  # flat script layout: the module sits one directory up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from schema_check import validate_against

MIN_WORDS = 300  # below this a rate is noise: one dash in 200 words reads 5/1k

RULES_TO_BANDS = {"personal": "chat", "technical": "doc-technical"}

SHIPPED_ROOT = Path(__file__).resolve().parent.parent / "bands"
SCHEMA_PATH = SHIPPED_ROOT / "bands.schema.json"
PROJECT_DIR = Path(".ava") / "bands"
RULE_ID_RE = re.compile(r"^[WTP]-M[0-9]+$")


class BandsError(Exception):
    """A table that fails the schema, or a name that resolves to nothing."""


def schema():
    return json.loads(SCHEMA_PATH.read_text())


def personal_root():
    return Path(os.environ.get("AVA_HOME") or Path.home() / ".ava") / "bands"


def project_root():
    """The nearest .ava/bands at or above the working directory, else ./.ava/bands."""
    here = Path.cwd()
    for d in (here, *here.parents):
        if (d / PROJECT_DIR).is_dir():
            return d / PROJECT_DIR
    return here / PROJECT_DIR


SCOPE_ROOTS = (("shipped", lambda: SHIPPED_ROOT),
               ("project", project_root),
               ("personal", personal_root))


def catalog():
    """Every table on this machine as (name, scope, path), in resolution order."""
    rows = []
    for scope, root_of in SCOPE_ROOTS:
        root = root_of()
        if root.is_dir():
            rows += [(p.stem, scope, p) for p in sorted(root.glob("*.json"))
                     if p.name != SCHEMA_PATH.name]
    return rows


def resolve(name):
    """A table name resolves shipped first, then project, then personal."""
    for scope, root_of in SCOPE_ROOTS:
        candidate = root_of() / f"{name}.json"
        if candidate.is_file() and candidate.name != SCHEMA_PATH.name:
            return candidate, scope
    known = ", ".join(sorted({n for n, _, _ in catalog()})) or "none"
    raise BandsError(f"no band table named {name} (known: {known})")


def validate(doc):
    errors = []
    validate_against(doc, schema(), schema(), "bands", errors)
    for rule in (doc.get("rules") or {}):
        if not RULE_ID_RE.match(rule):
            errors.append(f"bands.rules: {rule!r} is not a rule id such as W-M1")
    return errors


def load(path):
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise BandsError(f"{path}: not JSON ({e.msg} at line {e.lineno})")
    errors = validate(doc)
    if errors:
        raise BandsError(f"{path} fails the bands schema:\n  " + "\n  ".join(errors))
    return doc


def load_by_name(name):
    path, scope = resolve(name)
    return load(path), scope


def rule_counts(findings):
    return Counter(f.rule for f in findings)


def _position(rate, entry):
    """Return (status, reason) for one rule's rate against its bands.

    status is PASS, WARN, or FAIL. reason names the band position behind the
    status, so an agent can still read why.
    """
    hu = entry.get("human_universal")
    ai = entry.get("ai_universal", entry.get("ai_internal"))
    if hu is None:
        return "-", "no band"
    if entry.get("direction") == "human-high":
        if rate <= hu[1]:
            return "PASS", "within human range"
        return "FAIL", "above human range (style)"
    if ai is not None and rate >= ai:
        return "FAIL", "ai-range"
    if rate > hu[1]:
        return "WARN", "elevated above human band"
    return "PASS", "human-band"


_GREEN, _YELLOW, _RED, _RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"


def paint(status, color):
    if not color:
        return status
    tint = {"PASS": _GREEN, "WARN": _YELLOW, "FAIL": _RED}.get(status)
    return f"{tint}{status}{_RESET}" if tint else status


def _fmt(v):
    return "0" if v == 0 else (f"{v:.2f}".rstrip("0").rstrip(".") if v < 10 else f"{v:.1f}")


def summarize(findings, words, bands_name, rules_checked, color=False):
    """Return (lines, data): the stderr footer lines and the --json object."""
    if bands_name is None:
        return (["bands: pass --bands NAME for band comparison (ava bands list)"],
                {"bands": None, "available": False})
    table, scope = load_by_name(bands_name)
    counts = rule_counts(findings)
    data = {"bands": bands_name, "scope": scope, "words": words, "available": True,
            "rules": {}}
    if words < MIN_WORDS:
        return ([f"bands: sample too small ({words} words < {MIN_WORDS}), "
                 "counts only, no band comparison"],
                {**data, "guard": "small-sample"})
    show = sorted(set(counts) | ({"W-M1"} & set(rules_checked)))
    lines = [f"band summary (bands: {bands_name}, {words:,} words):"]
    for rule in show:
        entry = table["rules"].get(rule)
        if entry is None:
            continue
        rate = round(1000 * counts.get(rule, 0) / words, 2)
        status, reason = _position(rate, entry)
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
        tail = paint(status, color)
        if status != "PASS":
            tail += f" · {reason}"
        lines.append(" · ".join(parts) + f" -> {tail}")
        data["rules"][rule] = {
            "rate_per_1k": rate, "status": status, "position": reason,
            "direction": entry.get("direction"),
            "human_universal": hu, "human_internal": hi,
            "ai_universal": entry.get("ai_universal"),
            "ai_internal": entry.get("ai_internal"),
        }
    return lines, data
