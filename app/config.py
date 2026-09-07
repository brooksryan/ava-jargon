"""The store stamp and the run defaults: $AVA_HOME/config.json and .ava/config.json.

The personal config carries the ava version that last wrote the store. A
later ava reads the stamp and migrates the files under it. A project config
sets defaults for a repository and overrides the personal one.
"""
import json
import os
import re
from pathlib import Path

try:
    from .schema_check import validate_against
except ImportError:
    from schema_check import validate_against

SCHEMA_PATH = Path(__file__).resolve().parent / "config.schema.json"
PROJECT_FILE = Path(".ava") / "config.json"
DEFAULT_FIELDS = ("voice", "extend", "bands")
MIGRATIONS = ()


class ConfigError(Exception):
    """A config that fails the schema or is not JSON."""


def schema():
    return json.loads(SCHEMA_PATH.read_text())


def personal_path():
    return Path(os.environ.get("AVA_HOME") or Path.home() / ".ava") / "config.json"


def project_path():
    """The nearest .ava/config.json at or above the working directory, or None."""
    for d in project_ancestors():
        if (d / PROJECT_FILE).is_file():
            return d / PROJECT_FILE
    return None


def project_ancestors():
    """The working directory and its parents, stopped before the home directory."""
    here, home = Path.cwd(), Path.home()
    return [d for d in (here, *here.parents) if d != home and d not in home.parents]


def validate(doc):
    errors = []
    validate_against(doc, schema(), schema(), "config", errors)
    return errors


def load(path):
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: not JSON ({e.msg} at line {e.lineno})")
    errors = validate(doc)
    if errors:
        raise ConfigError(f"{path} fails the config schema:\n  " + "\n  ".join(errors))
    return doc


def version_tuple(text):
    return tuple(int(n) for n in re.findall(r"\d+", text or "")) or (0,)


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n")


def ensure_store(version):
    """Stamp the personal store with `version`. Returns the notes for stderr."""
    path = personal_path()
    if not path.is_file():
        _write(path, {"ava": version})
        return [f"wrote {path} (ava {version})"]
    doc = load(path)
    stored = doc.get("ava")
    if version_tuple(stored) < version_tuple(version):
        for _, migrate in MIGRATIONS:
            migrate(path.parent)
        doc["ava"] = version
        _write(path, doc)
        return [f"{path}: ava {stored} -> {version}"]
    if version_tuple(stored) > version_tuple(version):
        return [f"{path}: written by a newer ava ({stored}); this is ava {version}"]
    return []


def resolved():
    """(settings, paths): each default as (value, scope), project over personal."""
    settings, paths = {}, {"personal": None, "project": None}
    for scope, path in (("personal", personal_path()), ("project", project_path())):
        if path is None or not path.is_file():
            continue
        paths[scope] = path
        doc = load(path)
        for field, value in doc.items():
            settings[field] = (value, scope)
    return settings, paths
