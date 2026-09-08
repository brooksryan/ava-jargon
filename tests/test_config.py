"""`.ava/config.json`: the version stamp on a user's store, and the defaults a run takes.

The personal config lives at `$AVA_HOME/config.json`. The first run writes it
with the installed version. A project config at `.ava/config.json` sets defaults
for the repository and overrides the personal one.
"""
import json
import re

from conftest import installed_version

DOC = "The deploy job ran well and the team read the report.\n\n" * 40


def write_config(root, doc):
    (root / ".ava").mkdir(parents=True, exist_ok=True)
    (root / ".ava" / "config.json").write_text(json.dumps(doc))


def read_config(root):
    return json.loads((root / ".ava" / "config.json").read_text())


def verdict_line(stderr):
    return next(line for line in stderr.splitlines() if line.startswith("checked "))


# --- the version stamp -------------------------------------------------------------


def test_the_first_run_writes_the_personal_config(ava, home):
    r = ava("check", "-", "--rules", "westinghouse", stdin="Hello there.\n")
    assert r.returncode in (0, 1), r.stderr
    assert read_config(home) == {"ava": installed_version()}
    assert f"wrote {home / '.ava' / 'config.json'} (ava {installed_version()})" in r.stderr


def test_an_older_store_takes_the_current_stamp(ava, home):
    write_config(home, {"ava": "0.1.0", "voice": "code"})
    r = ava("check", "-", "--rules", "westinghouse", stdin="Hello there.\n")
    assert read_config(home) == {"ava": installed_version(), "voice": "code"}
    assert f"config.json: ava 0.1.0 -> {installed_version()}" in r.stderr


def test_a_newer_store_is_left_alone(ava, home):
    write_config(home, {"ava": "99.0.0"})
    r = ava("check", "-", "--rules", "westinghouse", stdin="Hello there.\n")
    assert read_config(home) == {"ava": "99.0.0"}
    assert "written by a newer ava (99.0.0)" in r.stderr


def test_a_config_that_fails_the_schema_exits_2(ava, project):
    write_config(project, {"voice": 5})
    r = ava("check", "-", "--rules", "westinghouse", stdin="Hello there.\n")
    assert r.returncode == 2
    assert "fails the config schema" in r.stderr and "voice" in r.stderr


def test_the_personal_store_is_never_a_project_config(ava, home):
    write_config(home, {"ava": installed_version(), "voice": "code"})
    repo = home / "repo"
    repo.mkdir()
    r = ava("config", "show", cwd=repo)
    assert r.returncode == 0, r.stderr
    assert "project: none" in r.stdout and re.search(r"^voice\s+code\s+\(personal\)", r.stdout, re.M)


def test_a_project_inside_the_home_directory_still_resolves(ava, home):
    repo = home / "repo"
    write_config(repo, {"voice": "code"})
    r = ava("config", "show", cwd=repo)
    assert f"project: {repo / '.ava' / 'config.json'}" in r.stdout
    assert re.search(r"^voice\s+code\s+\(project\)", r.stdout, re.M)


# --- the defaults ---------------------------------------------------------------------


def test_a_project_config_sets_the_default_voice(ava, project):
    write_config(project, {"voice": "code"})
    (project / "doc.txt").write_text(DOC)
    by_config = ava("check", "doc.txt")
    by_flag = ava("check", "doc.txt", "--voice", "code")
    assert verdict_line(by_config.stderr) == verdict_line(by_flag.stderr)
    assert "voice: code (personal, from config)" in by_config.stderr


def test_a_flag_beats_the_config_voice(ava, project):
    write_config(project, {"voice": "code"})
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--voice", "westinghouse")
    assert "voice: westinghouse (personal)" in r.stderr and "from config" not in r.stderr


def test_the_project_config_wins_over_the_personal_one(ava, project, home):
    write_config(home, {"ava": installed_version(), "voice": "westinghouse"})
    write_config(project, {"voice": "code"})
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt")
    assert "voice: code (personal, from config)" in r.stderr


def test_config_extend_and_bands_fill_the_flags(ava, project):
    write_config(project, {"bands": "chat"})
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--rules", "technical")
    assert "band summary (bands: chat, 440 words):" in r.stderr


# --- the config command --------------------------------------------------------------


def test_config_show_prints_the_resolved_settings(ava, project, home):
    write_config(home, {"ava": installed_version(), "voice": "westinghouse"})
    write_config(project, {"voice": "code"})
    r = ava("config", "show")
    assert r.returncode == 0, r.stderr
    assert f"personal: {home / '.ava' / 'config.json'}" in r.stdout
    assert f"project: {project / '.ava' / 'config.json'}" in r.stdout
    assert re.search(r"^voice\s+code\s+\(project\)", r.stdout, re.M)
    assert re.search(r"^ava\s+" + re.escape(installed_version()), r.stdout, re.M)


def test_config_schema_prints_the_schema(ava):
    r = ava("config", "schema")
    assert json.loads(r.stdout)["title"] == "ava config"


# --- the version in every run and every file -----------------------------------------


def test_check_output_carries_the_version(ava, project):
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--rules", "westinghouse")
    assert verdict_line(r.stderr).endswith(f" · ava {installed_version()}")
    r = ava("check", "doc.txt", "--rules", "westinghouse", "--json")
    assert json.loads(r.stdout)["ava"] == installed_version()


def test_a_new_voice_is_stamped(ava, project):
    (project / "mine.json").write_text(json.dumps({"bands": "chat"}))
    r = ava("voice", "new", "mine", "mine.json", "--project", "--checks", "westinghouse")
    assert r.returncode == 0, r.stderr
    saved = json.loads((project / ".ava" / "voices" / "mine.json").read_text())
    assert saved["ava"] == installed_version()


def test_a_built_lexicon_and_an_extension_are_stamped(ava, project, home):
    for side, texts in (("approved", ["the widget shipped today", "the widget invoice is paid",
                                      "customer asked about the widget"]),
                        ("contrast", ["the seam between the router and the widget"] * 8)):
        (project / side).mkdir()
        for i, text in enumerate(texts):
            (project / side / f"{i}.txt").write_text(text)
    r = ava("jargon", "build", "approved", "contrast", "-o", str(project / "lex.json"),
            "--min-contrast-count", "2", "--min-approved-count", "2",
            "--min-contrast-dispersion", "0.1", "--max-approved-dispersion", "0.01",
            "--ll", "0", "--lr", "1")
    assert r.returncode == 0, r.stderr
    assert json.loads((project / "lex.json").read_text())["meta"]["ava"] == installed_version()
    r = ava("jargon", "extend", "mine", "approved")
    assert r.returncode == 0, r.stderr
    ext = json.loads((home / ".ava" / "extensions" / "mine.json").read_text())
    assert ext["meta"]["ava"] == installed_version()
