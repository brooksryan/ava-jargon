"""Voices: one JSON document per voice, validated against voice.schema.json.

A voice records the checks that run, the band table and lexicon they run
against, and the extensions the audience accepts. It also records the rubric
a reviewer scores where mechanics cannot decide. Four voices ship with the
package. A personal voice lives in $AVA_HOME/voices/NAME.json; a project
voice lives in .ava/voices/NAME.json and travels with the repository. A name
resolves project first, then personal, then shipped.
"""
import json
import re
from pathlib import Path

try:
    from ..schema_check import validate_against
    from ..resources import FIXTURES
    from ..config import project_ancestors, personal_path
    from ..checks import all_rule_ids, rule_ids_in_set
    from ..checks import bands as B
except ImportError:
    from schema_check import validate_against
    from resources import FIXTURES
    from config import project_ancestors, personal_path
    from checks import all_rule_ids, rule_ids_in_set
    from checks import bands as B

SCHEMA_PATH = FIXTURES / "voices" / "voice.schema.json"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PROJECT_DIR = Path(".ava") / "voices"


class VoiceError(Exception):
    """A voice document that fails the schema, or a name that resolves to nothing."""


def schema():
    return json.loads(SCHEMA_PATH.read_text())


# --- validation -------------------------------------------------------------

def _cross_checks(doc, errors):
    """The rules the schema language cannot state."""
    seen = set()
    for i, rule in enumerate(doc.get("rubric", [])):
        if not isinstance(rule, dict):
            continue
        path = f"rules[{i}]"
        name = rule.get("name")
        if name in seen:
            errors.append(f"{path}.name: duplicate rule name '{name}'")
        seen.add(name)
        scoring = rule.get("scoring") or {}
        req = rule.get("requirement") or {}
        kind = scoring.get("type")
        if kind == "pass-fail" and "pass" not in req:
            errors.append(f"{path}.requirement: a pass-fail rule needs "
                          "{\"pass\": true}")
        if kind == "scale":
            lo, hi = scoring.get("min"), scoring.get("max")
            if isinstance(lo, int) and isinstance(hi, int) and lo >= hi:
                errors.append(f"{path}.scoring: min must be below max")
            if "min" not in req:
                errors.append(f"{path}.requirement: a scale rule needs "
                              "{\"min\": N}")
            elif isinstance(req["min"], int) and isinstance(lo, int) \
                    and isinstance(hi, int) and not lo <= req["min"] <= hi:
                errors.append(f"{path}.requirement.min: {req['min']} is "
                              f"outside the scale {lo}-{hi}")
            for key in (scoring.get("anchors") or {}):
                if not key.lstrip("-").isdigit() or not \
                        (isinstance(lo, int) and isinstance(hi, int)
                         and lo <= int(key) <= hi):
                    errors.append(f"{path}.scoring.anchors: key "
                                  f"{json.dumps(key)} is outside the scale")


SET_FOR_BANDS = {"chat": "westinghouse", "doc-shared": "westinghouse",
                 "doc-technical": "technical", "code": "technical"}
KEY_ORDER = ("name", "description", "checks", "bands", "lexicon", "extend", "rubric", "ava")


def upgrade(doc):
    """A document from before this schema: `surface` becomes `bands`, `rules`
    becomes `rubric`, and the checks come from the set the surface implied."""
    doc = dict(doc)
    older_shape = "surface" in doc or "rules" in doc
    if "surface" in doc:
        doc.setdefault("bands", doc.pop("surface"))
    if "rules" in doc:
        doc.setdefault("rubric", doc.pop("rules"))
    if older_shape and "checks" not in doc and doc.get("bands") in SET_FOR_BANDS:
        doc["checks"] = rule_ids_in_set(SET_FOR_BANDS[doc["bands"]])
    return doc


def _checks_cross_checks(doc, errors):
    checks = doc.get("checks") or []
    known = set(all_rule_ids())
    for i, rule_id in enumerate(checks):
        if rule_id not in known:
            errors.append(f"voice.checks[{i}]: unknown rule id: {rule_id}")
    if len(set(checks)) != len(checks):
        errors.append("voice.checks: a rule id repeats")
    if isinstance(doc.get("bands"), str):
        try:
            B.resolve(doc["bands"])
        except B.BandsError as e:
            errors.append(f"voice.bands: {e}")


def validate(doc):
    """Return the list of schema errors for `doc`; empty means valid."""
    errors = []
    validate_against(doc, schema(), schema(), "voice", errors)
    if not errors:
        _checks_cross_checks(doc, errors)
        _cross_checks(doc, errors)
    return errors


# --- storage ----------------------------------------------------------------

SHIPPED_ROOT = FIXTURES / "voices" / "shipped"
SCOPES = ("project", "personal", "shipped")


def personal_root():
    return personal_path().parent / "voices"


def project_root():
    """The nearest .ava/voices at or above the working directory, else ./.ava/voices."""
    for d in project_ancestors():
        if (d / PROJECT_DIR).is_dir():
            return d / PROJECT_DIR
    return Path.cwd() / PROJECT_DIR


def root_for(scope):
    if scope == "shipped":
        return SHIPPED_ROOT
    return project_root() if scope == "project" else personal_root()


def catalog():
    """Every voice on this machine as (name, scope, path), in resolution order."""
    rows = []
    for scope in SCOPES:
        root = root_for(scope)
        if root.is_dir():
            rows += [(p.stem, scope, p) for p in sorted(root.glob("*.json"))]
    return rows


def resolve(spec):
    """A voice is a file path or a name: project first, then personal, then shipped."""
    p = Path(spec).expanduser()
    if p.suffix == ".json" and p.is_file():
        return p, "file"
    for scope in SCOPES:
        candidate = root_for(scope) / f"{spec}.json"
        if candidate.is_file():
            return candidate, scope
    known = ", ".join(sorted({n for n, _, _ in catalog()})) or "none"
    raise VoiceError(f"no such voice: {spec} (known: {known}; "
                     "create one with ava voice new)")


def load(path):
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise VoiceError(f"{path}: not JSON ({e.msg} at line {e.lineno})")
    doc = upgrade(doc)
    errors = validate(doc)
    if errors:
        raise VoiceError(f"{path} fails the voice schema:\n  " + "\n  ".join(errors))
    return doc


def save(path, doc):
    doc = upgrade(doc)
    errors = validate(doc)
    if errors:
        raise VoiceError("the voice fails the schema:\n  " + "\n  ".join(errors))
    doc = {**{k: doc[k] for k in KEY_ORDER if k in doc},
           **{k: v for k, v in doc.items() if k not in KEY_ORDER}}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return path


def merge(base, patch):
    """Overlay `patch` on `base`. Rubric entries merge by name; other keys replace."""
    out = dict(base)
    for key, value in upgrade(patch).items():
        if key == "rubric" and isinstance(value, list) and isinstance(base.get("rubric"), list):
            rules = {r.get("name"): r for r in base["rubric"] if isinstance(r, dict)}
            for r in value:
                if isinstance(r, dict) and r.get("name") in rules:
                    rules[r["name"]] = {**rules[r["name"]], **r}
                else:
                    rules[r.get("name") if isinstance(r, dict) else id(r)] = r
            out["rubric"] = list(rules.values())
        else:
            out[key] = value
    return out


LIST_FIELDS = ("checks", "extend")
SCALAR_FIELDS = ("bands", "lexicon", "description")


def set_field(doc, field, values):
    """Edit one field from the command line: `+id` adds, `-id` drops, bare
    values replace a list; a scalar field takes one value."""
    out = dict(doc)
    if field in LIST_FIELDS:
        current = list(out.get(field) or [])
        if all(v[:1] in "+-" for v in values):
            for v in values:
                if v[0] == "+" and v[1:] not in current:
                    current.append(v[1:])
                elif v[0] == "-":
                    current = [c for c in current if c != v[1:]]
        else:
            current = list(values)
        out[field] = current
    elif field in SCALAR_FIELDS:
        if len(values) != 1:
            raise VoiceError(f"{field} takes one value")
        out[field] = values[0]
    else:
        raise VoiceError(f"no editable field {field!r} (one of: "
                         f"{', '.join(LIST_FIELDS + SCALAR_FIELDS)})")
    return out


# --- rubric -----------------------------------------------------------------

def lexicon_name(doc):
    """The lexicon the voice names, or the universal one named after its bands."""
    return doc.get("lexicon") or f"universal-{doc['bands']}"


def _scoring_label(rule):
    s = rule["scoring"]
    if s["type"] == "pass-fail":
        return "pass/fail"
    return f"{s['min']}-{s['max']}"


def _requirement_label(rule):
    r = rule["requirement"]
    return "must pass" if "pass" in r else f"min {r['min']}"


def rubric(doc, scope=None):
    """The rules as a reviewer reads them."""
    head = f"voice: {doc['name']}"
    if scope:
        head += f" ({scope})"
    head += f" · bands {doc['bands']} · lexicon {lexicon_name(doc)}"
    head += f" · checks {len(doc['checks'])}"
    ext = doc.get("extend") or []
    head += " · extend: " + (", ".join(ext) if ext else "none")
    lines = [head]
    if doc.get("description"):
        lines.append(doc["description"])
    for i, rule in enumerate(doc.get("rubric") or [], 1):
        lines.append(f"{i}. {rule['name']} · {_scoring_label(rule)} · "
                     f"{_requirement_label(rule)}")
        lines.append(f"   {rule['description']}")
        for c in rule["criteria"]:
            lines.append(f"   - {c}")
        anchors = rule["scoring"].get("anchors") or {}
        for key in sorted(anchors, key=int):
            lines.append(f"   {key}: {anchors[key]}")
    return "\n".join(lines)
