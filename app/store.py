"""Personal defaults and the hashes of the fixture copies ava manages."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

try:
    from .resources import FIXTURES
except ImportError:
    from resources import FIXTURES


def root():
    return Path(os.environ.get("AVA_HOME") or Path.home() / ".ava").expanduser()


def encode(document):
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_bytes(path, content):
    if path.is_file() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def seed(version):
    target = root()
    manifest_path = target / ".fixtures.json"
    previous = json.loads(manifest_path.read_bytes()) if manifest_path.is_file() else {}
    managed = previous.get("files", {}) if isinstance(previous, dict) else None
    if not isinstance(managed, dict) or any(not isinstance(value, str) for value in managed.values()):
        raise ValueError(f"{manifest_path}: invalid fixture hashes")
    installed = {}
    for directory, source_directory in (("bands", "bands"), ("lexicons", "lexicons"),
                                        ("voices", "voices/shipped")):
        for source in sorted((FIXTURES / source_directory).iterdir(), key=lambda path: path.name):
            if not source.name.endswith(".json") or source.name.endswith(".schema.json"):
                continue
            document = json.loads(source.read_bytes())
            if directory == "voices":
                document["ava"] = version
            else:
                document.setdefault("meta", {})["ava"] = version
            desired = encode(document)
            desired_hash = hashlib.sha256(desired).hexdigest()
            name = f"{directory}/{source.name}"
            destination = target / name
            if destination.is_file():
                current = hashlib.sha256(destination.read_bytes()).hexdigest()
                if current != desired_hash and current != managed.get(name):
                    if name in managed:
                        installed[name] = managed[name]
                    continue
            write_bytes(destination, desired)
            installed[name] = desired_hash
    (target / "extensions").mkdir(parents=True, exist_ok=True)
    return {"ava": version, "files": installed}
