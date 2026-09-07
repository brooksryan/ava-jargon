import hashlib
import importlib
import json
from pathlib import Path

import pytest

from app import config


@pytest.fixture
def seeded_inputs(tmp_path, monkeypatch):
    store = importlib.import_module("app.store")
    fixtures = tmp_path / "fixtures"
    documents = {
        "voices/shipped/code.json": {"name": "code", "checks": ["W-M1"]},
        "lexicons/universal-chat.json": {"meta": {}, "jargon": {}},
        "bands/chat.json": {"name": "chat", "rules": {}},
        "bands/bands.schema.json": {"type": "object"},
        "voices/voice.schema.json": {"type": "object"},
        "assets/gate-contract.md": None,
    }
    for name, document in documents.items():
        path = fixtures / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document))
    target = tmp_path / "personal"
    monkeypatch.setenv("AVA_HOME", str(target))
    monkeypatch.setattr(store, "FIXTURES", fixtures)
    return store, fixtures, target


def read(path):
    return json.loads(path.read_text())


def snapshot(root):
    return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob("*") if path.is_file()}


def test_first_run_copies_only_editable_defaults_and_stamps_them(seeded_inputs):
    _, _, target = seeded_inputs
    config.ensure_store("0.7.0")
    assert read(target / "voices/code.json")["ava"] == "0.7.0"
    assert read(target / "lexicons/universal-chat.json")["meta"]["ava"] == "0.7.0"
    assert read(target / "bands/chat.json")["meta"]["ava"] == "0.7.0"
    assert (target / "extensions").is_dir()
    manifest = read(target / ".fixtures.json")
    assert manifest["ava"] == "0.7.0"
    assert set(manifest["files"]) == {"voices/code.json", "lexicons/universal-chat.json", "bands/chat.json"}
    assert all(value == hashlib.sha256((target / name).read_bytes()).hexdigest()
               for name, value in manifest["files"].items())
    assert not list(target.rglob("*.schema.json"))
    assert not (target / "assets").exists()
    assert read(target / "config.json") == {"ava": "0.7.0"}
    before = snapshot(target)
    assert config.ensure_store("0.7.0") == []
    assert snapshot(target) == before


def test_existing_stamp_still_fills_missing_defaults(seeded_inputs):
    _, _, target = seeded_inputs
    target.mkdir()
    (target / "config.json").write_text('{"ava":"0.7.0","voice":"code"}')
    config.ensure_store("0.7.0")
    assert (target / "voices/code.json").is_file()
    assert read(target / "config.json")["voice"] == "code"
    (target / "bands/chat.json").unlink()
    config.ensure_store("0.7.0")
    assert (target / "bands/chat.json").is_file()


def test_existing_and_edited_files_remain_unchanged(seeded_inputs):
    _, _, target = seeded_inputs
    (target / "voices").mkdir(parents=True)
    personal = target / "voices/code.json"
    personal.write_text('{"name":"my code"}')
    custom = target / "voices/custom.json"
    custom.write_text('{"name":"custom"}')
    config.ensure_store("0.7.0")
    edited = target / "bands/chat.json"
    edited.write_text('{"name":"edited"}')
    before = {path: path.read_bytes() for path in (personal, custom, edited)}
    config.ensure_store("0.8.0")
    assert all(path.read_bytes() == value for path, value in before.items())
    assert "voices/code.json" not in read(target / ".fixtures.json")["files"]


def test_upgrade_replaces_only_untouched_defaults(seeded_inputs):
    _, fixtures, target = seeded_inputs
    config.ensure_store("0.7.0")
    document = read(fixtures / "voices/shipped/code.json")
    document["description"] = "Updated default."
    (fixtures / "voices/shipped/code.json").write_text(json.dumps(document))
    config.ensure_store("0.8.0")
    saved = read(target / "voices/code.json")
    assert saved["description"] == "Updated default."
    assert saved["ava"] == "0.8.0"
    assert read(target / ".fixtures.json")["ava"] == "0.8.0"
    assert read(target / "config.json")["ava"] == "0.8.0"


def test_store_root_expands_ava_home_and_defaults_to_home(tmp_path, monkeypatch):
    store = importlib.import_module("app.store")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AVA_HOME", "~/voice-store")
    assert store.root() == tmp_path / "voice-store"
    assert config.personal_path() == tmp_path / "voice-store/config.json"
    monkeypatch.delenv("AVA_HOME")
    assert store.root() == tmp_path / ".ava"


def test_partial_write_failure_has_no_completion_and_retry_recovers(seeded_inputs, monkeypatch):
    store, _, target = seeded_inputs
    write = store.write_bytes
    def fail_lexicon(path, content):
        if path.name == "universal-chat.json":
            raise OSError("fixture write failed")
        return write(path, content)
    with monkeypatch.context() as patch:
        patch.setattr(store, "write_bytes", fail_lexicon)
        with pytest.raises(config.ConfigError, match="fixture write failed"):
            config.ensure_store("0.7.0")
    assert (target / "bands/chat.json").exists()
    assert not (target / ".fixtures.json").exists()
    assert not (target / "config.json").exists()
    config.ensure_store("0.7.0")
    assert "bands/chat.json" in read(target / ".fixtures.json")["files"]
    assert read(target / "config.json")["ava"] == "0.7.0"


@pytest.mark.parametrize("existing", [False, True])
def test_config_failure_does_not_advance_fixture_completion(seeded_inputs, monkeypatch, existing):
    store, _, target = seeded_inputs
    if existing:
        config.ensure_store("0.7.0")
    manifest = target / ".fixtures.json"
    stamp = target / "config.json"
    before_manifest = manifest.read_bytes() if existing else None
    before_stamp = stamp.read_bytes() if existing else None
    write = store.write_bytes
    def fail_config(path, content):
        if path == stamp:
            raise OSError("config write failed")
        return write(path, content)
    with monkeypatch.context() as patch:
        patch.setattr(store, "write_bytes", fail_config)
        with pytest.raises(config.ConfigError, match="config write failed"):
            config.ensure_store("0.8.0")
    assert (manifest.read_bytes() if manifest.exists() else None) == before_manifest
    assert (stamp.read_bytes() if stamp.exists() else None) == before_stamp
    config.ensure_store("0.8.0")
    assert read(stamp)["ava"] == "0.8.0"
    assert read(manifest)["ava"] == "0.8.0"


def test_failed_upgrade_preserves_old_completion_and_recovers(seeded_inputs, monkeypatch):
    store, _, target = seeded_inputs
    config.ensure_store("0.7.0")
    old_manifest = (target / ".fixtures.json").read_bytes()
    old_stamp = (target / "config.json").read_bytes()
    write = store.write_bytes
    def fail_lexicon(path, content):
        if path.name == "universal-chat.json":
            raise OSError("upgrade write failed")
        return write(path, content)
    with monkeypatch.context() as patch:
        patch.setattr(store, "write_bytes", fail_lexicon)
        with pytest.raises(config.ConfigError, match="upgrade write failed"):
            config.ensure_store("0.8.0")
    assert read(target / "bands/chat.json")["meta"]["ava"] == "0.8.0"
    assert (target / ".fixtures.json").read_bytes() == old_manifest
    assert (target / "config.json").read_bytes() == old_stamp
    config.ensure_store("0.8.0")
    assert read(target / ".fixtures.json")["ava"] == "0.8.0"


def test_newer_config_prevents_all_seed_writes(seeded_inputs):
    _, _, target = seeded_inputs
    target.mkdir()
    (target / "config.json").write_text('{"ava":"99.0.0"}')
    before = snapshot(target)
    notes = config.ensure_store("0.7.0")
    assert "newer ava" in notes[0]
    assert snapshot(target) == before
    assert not (target / "extensions").exists()
