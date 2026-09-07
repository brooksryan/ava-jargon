import json
from importlib.resources import files

import pytest


def build_inputs(project):
    for name, text in (("audience", "The team read the report."),
                       ("drafts", "The team wrote a report.")):
        folder = project / name
        folder.mkdir()
        (folder / "one.txt").write_text(text)
    return ("jargon", "build", "audience", "drafts")


def test_build_defaults_to_the_personal_store_and_resolves_by_name(ava, project, home):
    assert ava(*build_inputs(project)).returncode == 0
    target = home / ".ava/lexicons/lexicon.json"
    assert target.is_file()
    assert not (project / "lexicons").exists()
    assert ava("jargon", "score", "audience/one.txt", "-l", "lexicon").returncode == 0
    assert ava("jargon", "delta", "audience", "drafts", "-l", "lexicon", "--boot", "10").returncode == 0
    assert ava("check", "audience/one.txt", "--lexicon", "lexicon").returncode in (0, 1)


def test_project_build_and_explicit_output(ava, project, home):
    args = build_inputs(project)
    assert ava(*args, "--project").returncode == 0
    assert (project / ".ava/lexicons/lexicon.json").is_file()
    assert not (home / ".ava/lexicons/lexicon.json").exists()
    assert ava(*args, "--out", "results/chosen.json").returncode == 0
    assert (project / "results/chosen.json").is_file()


def test_project_lexicon_overrides_personal_default_from_a_subdirectory(ava, project, home):
    assert ava("config", "show").returncode == 0
    source = files("ava_jargon.fixtures") / "lexicons/universal-chat.json"
    doc = json.loads(source.read_text())
    doc["jargon"] = {}
    folder = project / ".ava/lexicons"
    folder.mkdir(parents=True)
    (folder / "universal-chat.json").write_text(json.dumps(doc))
    child = project / "child"
    child.mkdir()
    from ava_jargon import cli
    from unittest.mock import patch
    with patch("pathlib.Path.cwd", return_value=child), patch("pathlib.Path.home", return_value=home):
        assert cli._lexicon_by_name("universal-chat") == folder / "universal-chat.json"


@pytest.mark.parametrize("name", ["chosen.data", "chosen"])
def test_explicit_lexicon_paths_keep_any_filename(ava, project, name):
    assert ava(*build_inputs(project), "--out", f"results/{name}").returncode == 0
    for args in (("jargon", "score", "audience/one.txt", "-l", f"results/{name}"),
                 ("jargon", "delta", "audience", "drafts", "-l", f"results/{name}", "--boot", "10"),
                 ("check", "audience/one.txt", "--lexicon", f"results/{name}")):
        result = ava(*args)
        assert result.returncode in (0, 1), result.stderr


def test_nearer_config_directory_does_not_hide_project_lexicons(ava, project, home):
    assert ava(*build_inputs(project), "--project").returncode == 0
    nested = project / "nested"
    (nested / ".ava").mkdir(parents=True)
    (nested / ".ava/config.json").write_text("{}")
    result = ava("jargon", "score", str(project / "audience/one.txt"), "-l", "lexicon", cwd=nested)
    assert result.returncode == 0, result.stderr
    result = ava("jargon", "build", str(project / "audience"), str(project / "drafts"),
                 "--project", cwd=nested)
    assert result.returncode == 0, result.stderr
    assert not (nested / ".ava/lexicons").exists()


def test_ava_home_controls_default_files_and_personal_resolution(ava, project, home):
    environment = {"AVA_HOME": "~/custom-data"}
    result = ava(*build_inputs(project), env=environment)
    assert result.returncode == 0, result.stderr
    target = home / "custom-data"
    assert (target / "lexicons/lexicon.json").is_file()
    assert (target / "voices/code.json").is_file()
    assert (target / "bands/code.json").is_file()
    assert not (home / ".ava").exists()
    assert ava("jargon", "score", "audience/one.txt", "-l", "lexicon", env=environment).returncode == 0
    assert "code (personal)" in ava("check", "audience/one.txt", "--voice", "code", env=environment).stderr
    assert "code (personal)" in ava("bands", "show", "code", env=environment).stdout
