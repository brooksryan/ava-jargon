import hashlib
import os
import tarfile
import zipfile
from importlib.resources import files
from pathlib import Path

import pytest

from conftest import REPO


EXPECTED = {
    "name_stoplist.txt", "config.schema.json", "voices/voice.schema.json",
    "bands/bands.schema.json", "assets/gate-contract.md",
    *{f"lexicons/universal-{name}.json" for name in
      ("chat", "code", "doc-shared", "doc-technical")},
    *{f"bands/{name}.json" for name in
      ("chat", "code", "doc-shared", "doc-technical")},
    *{f"voices/shipped/{name}.json" for name in
      ("westinghouse", "shared-docs", "technical-docs", "code")},
    *{f"assets/agents/{name}.md" for name in
      ("ava-prose-gate", "ava-technical-gate")},
    *{f"assets/skills/ava/{name}" for name in
      ("SKILL.md", "references/voices.md", "references/custom-lexicons.md")},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_installed_fixtures_match_the_maintained_sources():
    installed = files("ava_jargon.fixtures")
    source = REPO / "fixtures"
    for name in EXPECTED:
        assert digest(installed / name) == digest(source / name), name


def test_fixture_data_has_one_source():
    source = REPO / "fixtures"
    actual = {str(p.relative_to(source)) for p in source.rglob("*")
              if p.is_file() and p.suffix in (".json", ".txt", ".md")
              and p.name != "README.md"}
    assert actual == EXPECTED
    assert not any(p.is_symlink() for p in source.rglob("*"))
    assert not list((REPO / "lexicons").glob("universal-*.json"))
    assert not list((REPO / "app" / "lexicons").glob("*.json"))


def test_plugin_entries_use_the_fixture_sources():
    for name in EXPECTED:
        if name.startswith("assets/"):
            entry = REPO / name.removeprefix("assets/")
            source = REPO / "fixtures" / name
            assert digest(entry) == digest(source)
            if entry.is_symlink():
                assert entry.resolve() == source


def test_workspace_lexicons_cannot_shadow_shipped_defaults(tmp_path, monkeypatch):
    from ava_jargon import cli

    workspace = tmp_path / "lexicons"
    workspace.mkdir()
    (workspace / "universal-code.json").write_text("{}")
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "app" / "cli.py"))
    shipped = files("ava_jargon.fixtures") / "lexicons" / "universal-code.json"
    assert cli._universal_lexicon("code") == shipped
    assert cli._lexicon_by_name("universal-code") == shipped
    assert cli._lexicon_by_name(str(workspace / "universal-code.json")) == workspace / "universal-code.json"


def test_release_archives_contain_only_the_selected_fixture_data():
    directory = os.environ.get("AVA_DIST_DIR")
    if not directory:
        pytest.skip("./test supplies the built release archives")
    directory = Path(directory)
    with zipfile.ZipFile(next(directory.glob("*.whl"))) as wheel:
        prefix = "ava_jargon/fixtures/"
        data = {n.removeprefix(prefix) for n in wheel.namelist()
                if n.startswith(prefix) and not n.endswith(".py")}
        assert data == EXPECTED
        for name in EXPECTED:
            assert wheel.read(prefix + name) == (REPO / "fixtures" / name).read_bytes()
        assert all(n.startswith(("ava_jargon/", "ava_jargon-")) for n in wheel.namelist())
    with tarfile.open(next(directory.glob("*.tar.gz"))) as source:
        members = source.getmembers()
        root = members[0].name.split("/")[0] + "/"
        names = {m.name.removeprefix(root) for m in members}
        assert "tests/conftest.py" in names
        for name in EXPECTED:
            assert source.extractfile(root + "fixtures/" + name).read() == (REPO / "fixtures" / name).read_bytes()
        assert not any(n.split("/")[0] in {"corpus", "audit", "lexicons", "notes", "tmp"}
                       for n in names)
