"""Voices: one JSON document per voice, validated against voice.schema.json.

A voice records the surface and the vocabulary extensions the mechanical
check runs under, and the rubric a reviewer scores where mechanics cannot
decide. A personal voice lives in $AVA_HOME/voices/NAME.json; a project
voice lives in .ava/voices/NAME.json and travels with the repository. On a
name clash the project voice wins.
"""
import json
import os
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "voice.schema.json"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PROJECT_DIR = Path(".ava") / "voices"


class VoiceError(Exception):
    """A voice document that fails the schema, or a name that resolves to nothing."""


def schema():
    return json.loads(SCHEMA_PATH.read_text())


# --- validation -------------------------------------------------------------
#
# A small validator for the subset of JSON Schema the voice schema uses, so
# the schema file stays the single source of truth and the CLI adds no
# dependency. Errors name the path of the field that failed.

_TYPES = {"string": str, "integer": int, "number": (int, float),
          "boolean": bool, "array": list, "object": dict}


def _type_ok(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def _deref(node, root):
    ref = node.get("$ref")
    if not ref:
        return node
    target = root
    for part in ref.lstrip("#/").split("/"):
        target = target[part]
    return target


def _validate(value, node, root, path, errors):
    node = _deref(node, root)
    if "oneOf" in node:
        attempts = []
        for branch in node["oneOf"]:
            sub = []
            _validate(value, branch, root, path, sub)
            if not sub:
                return
            attempts.append(sub)
        # Report the branch that came closest, so the message names one field.
        errors.extend(min(attempts, key=len))
        return
    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected {json.dumps(node['const'])}, "
                      f"got {json.dumps(value)}")
        return
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: expected one of {', '.join(map(str, node['enum']))}, "
                      f"got {json.dumps(value)}")
        return
    if "type" in node and not _type_ok(value, node["type"]):
        errors.append(f"{path}: expected {node['type']}, "
                      f"got {type(value).__name__}")
        return
    if isinstance(value, str):
        if "pattern" in node and not re.match(node["pattern"], value):
            errors.append(f"{path}: {json.dumps(value)} does not match "
                          f"{node['pattern']}")
        if "minLength" in node and len(value) < node["minLength"]:
            errors.append(f"{path}: must not be empty")
    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{path}: needs at least {node['minItems']} item(s)")
        if "items" in node:
            for i, item in enumerate(value):
                _validate(item, node["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        props = node.get("properties", {})
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], root, f"{path}.{key}", errors)
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field '{key}'")
            elif isinstance(node.get("additionalProperties"), dict):
                _validate(item, node["additionalProperties"], root,
                          f"{path}.{key}", errors)


def _cross_checks(doc, errors):
    """The rules the schema language cannot state."""
    seen = set()
    for i, rule in enumerate(doc.get("rules", [])):
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


def validate(doc):
    """Return the list of schema errors for `doc`; empty means valid."""
    errors = []
    _validate(doc, schema(), schema(), "voice", errors)
    if not errors:
        _cross_checks(doc, errors)
    return errors


# --- storage ----------------------------------------------------------------

def personal_root():
    return Path(os.environ.get("AVA_HOME") or Path.home() / ".ava") / "voices"


def project_root():
    """The nearest .ava/voices at or above the working directory, else ./.ava/voices."""
    here = Path.cwd()
    for d in (here, *here.parents):
        if (d / PROJECT_DIR).is_dir():
            return d / PROJECT_DIR
    return here / PROJECT_DIR


def root_for(scope):
    return project_root() if scope == "project" else personal_root()


def catalog():
    """Every voice on this machine as (name, scope, path), project rows first."""
    rows = []
    for scope in ("project", "personal"):
        root = root_for(scope)
        if root.is_dir():
            rows += [(p.stem, scope, p) for p in sorted(root.glob("*.json"))]
    return rows


def resolve(spec):
    """A voice is a file path or a name: project first, then personal."""
    p = Path(spec).expanduser()
    if p.suffix == ".json" and p.is_file():
        return p, "file"
    for scope in ("project", "personal"):
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
    errors = validate(doc)
    if errors:
        raise VoiceError(f"{path} fails the voice schema:\n  " + "\n  ".join(errors))
    return doc


def save(path, doc):
    errors = validate(doc)
    if errors:
        raise VoiceError("the voice fails the schema:\n  " + "\n  ".join(errors))
    order = ("name", "description", "surface", "extend", "rules")
    doc = {**{k: doc[k] for k in order if k in doc},
           **{k: v for k, v in doc.items() if k not in order}}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return path


def merge(base, patch):
    """Overlay `patch` on `base`. Rules merge by name; other keys replace."""
    out = dict(base)
    for key, value in patch.items():
        if key == "rules" and isinstance(value, list) and isinstance(base.get("rules"), list):
            rules = {r.get("name"): r for r in base["rules"] if isinstance(r, dict)}
            for r in value:
                if isinstance(r, dict) and r.get("name") in rules:
                    rules[r["name"]] = {**rules[r["name"]], **r}
                else:
                    rules[r.get("name") if isinstance(r, dict) else id(r)] = r
            out["rules"] = list(rules.values())
        else:
            out[key] = value
    return out


# --- rubric -----------------------------------------------------------------

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
    head += f" · surface {doc['surface']}"
    ext = doc.get("extend") or []
    head += " · extend: " + (", ".join(ext) if ext else "none")
    lines = [head]
    if doc.get("description"):
        lines.append(doc["description"])
    for i, rule in enumerate(doc["rules"], 1):
        lines.append(f"{i}. {rule['name']} · {_scoring_label(rule)} · "
                     f"{_requirement_label(rule)}")
        lines.append(f"   {rule['description']}")
        for c in rule["criteria"]:
            lines.append(f"   - {c}")
        anchors = rule["scoring"].get("anchors") or {}
        for key in sorted(anchors, key=int):
            lines.append(f"   {key}: {anchors[key]}")
    return "\n".join(lines)
