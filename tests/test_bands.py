"""`ava bands` and `--bands`: one band table per file, resolved by name.

A name resolves in this order: the shipped tables, `.ava/bands/NAME.json` in
the project, `$AVA_HOME/bands/NAME.json` for the user.
"""
import json
from importlib.resources import files

import pytest

SHIPPED = files("ava_jargon.fixtures") / "bands"
SHIPPED_NAMES = ("chat", "code", "doc-shared", "doc-technical")
# 440 words: over the 300-word guard. The check may report findings on it, so
# a test reads the band summary and accepts exit code 0 or 1.
LONG_DOC = "The deploy job ran well and the team read the report. " * 40

CHECK = ("check", "doc.txt", "--rules", "technical")


def shipped_table(name):
    return json.loads((SHIPPED / f"{name}.json").read_text())


def write_table(root, name, table):
    (root / ".ava" / "bands").mkdir(parents=True, exist_ok=True)
    (root / ".ava" / "bands" / f"{name}.json").write_text(json.dumps({**table, "name": name}))


# --- the shipped tables --------------------------------------------------------


@pytest.mark.parametrize("name", SHIPPED_NAMES)
def test_every_shipped_table_carries_every_rule_with_a_direction(name):
    table = shipped_table(name)
    assert table["name"] == name
    assert len(table["rules"]) == 22
    assert all(r["direction"] in ("ai-high", "human-high") for r in table["rules"].values())
    assert table["meta"]["min_words_guard"] == 300


def test_list_names_the_shipped_tables(ava):
    r = ava("bands", "list")
    assert r.returncode == 0, r.stderr
    for name in SHIPPED_NAMES:
        assert f"{name:<16} shipped" in r.stdout


@pytest.mark.parametrize("name", SHIPPED_NAMES)
def test_show_prints_a_row_per_rule(ava, name):
    r = ava("bands", "show", name)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith(f"{name} (shipped): 22 rules")
    assert "  W-M1  " in r.stdout and "human " in r.stdout


def test_schema_prints_the_schema(ava):
    r = ava("bands", "schema")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["title"] == "ava bands"


# --- resolution ----------------------------------------------------------------


def test_a_project_table_reaches_the_summary_by_name(ava, project):
    write_table(project, "mine", shipped_table("code"))
    (project / "doc.txt").write_text(LONG_DOC)
    r = ava(*CHECK, "--bands", "mine")
    assert r.returncode in (0, 1), r.stderr
    assert "band summary (bands: mine, 440 words):" in r.stderr
    assert "mine             project" in ava("bands", "list").stdout


def test_a_personal_table_resolves_under_the_home_ava_dir(ava, home):
    write_table(home, "home-table", shipped_table("chat"))
    r = ava("bands", "list")
    assert "home-table       personal" in r.stdout
    assert ava("bands", "show", "home-table").stdout.startswith("home-table (personal)")


def test_a_shipped_name_wins_over_a_project_table(ava, project):
    write_table(project, "code", {**shipped_table("code"), "description": "MARKER"})
    r = ava("bands", "show", "code")
    assert r.returncode == 0, r.stderr
    assert "MARKER" not in r.stdout
    assert "code             shipped" in ava("bands", "list").stdout


def test_a_project_table_wins_over_a_personal_one(ava, project, home):
    write_table(project, "mine", {**shipped_table("code"), "description": "PROJECT"})
    write_table(home, "mine", {**shipped_table("code"), "description": "PERSONAL"})
    assert "PROJECT" in ava("bands", "show", "mine").stdout


def test_an_unknown_name_exits_2(ava, project):
    (project / "doc.txt").write_text(LONG_DOC)
    r = ava(*CHECK, "--bands", "nope")
    assert r.returncode == 2
    assert "no band table named nope" in r.stderr and "chat, code, doc-shared" in r.stderr


def test_a_table_that_fails_the_schema_exits_2(ava, project):
    write_table(project, "bad", {"meta": {}})
    r = ava("bands", "show", "bad")
    assert r.returncode == 2
    assert "fails the bands schema" in r.stderr and "rules" in r.stderr


# --- the check command ---------------------------------------------------------


def test_surface_stays_as_an_alias_of_bands(ava, project):
    (project / "doc.txt").write_text(LONG_DOC)
    r = ava(*CHECK, "--surface", "code")
    assert r.returncode in (0, 1), r.stderr
    assert "band summary (bands: code, 440 words):" in r.stderr


def test_the_footer_names_the_flag_when_no_table_is_named(ava, project):
    (project / "doc.txt").write_text(LONG_DOC)
    r = ava("check", "doc.txt", "--rules", "westinghouse")
    assert "bands: pass --bands NAME for band comparison (ava bands list)" in r.stderr


def test_the_json_report_names_the_table(ava, project):
    (project / "doc.txt").write_text(LONG_DOC)
    r = ava(*CHECK, "--bands", "code", "--json")
    assert r.returncode in (0, 1), r.stderr
    bands = json.loads(r.stdout)["bands"]
    assert bands["bands"] == "code" and bands["scope"] == "shipped" and bands["available"]
    assert "W-M1" in bands["rules"]
