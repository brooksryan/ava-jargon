"""`ava check` end to end, through the installed script."""
import json

EM_DASH = "The deploy job — it went well.\n"
CLEAN = "The deploy job ran well.\n"


def test_a_finding_exits_1_and_prints_the_linter_line(ava):
    r = ava("check", "-", "--rules", "technical", stdin=EM_DASH)
    assert r.returncode == 1
    assert '<stdin>:1: [W-M1] em dash: "The deploy job — it went well."' in r.stdout


def test_clean_text_exits_0_with_an_empty_stdout(ava):
    r = ava("check", "-", "--rules", "technical", stdin=CLEAN)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
    assert "0 findings" in r.stderr


def test_json_emits_one_object(ava):
    r = ava("check", "-", "--rules", "technical", "--json", stdin=EM_DASH)
    assert r.returncode == 1
    doc = json.loads(r.stdout)
    assert doc["paths"] == ["<stdin>"]
    assert doc["rules"] == "technical"
    assert [f["rule"] for f in doc["findings"]] == ["W-M1"]
    assert doc["counts"]["findings"] == 1


def test_a_missing_file_exits_2(ava, project):
    r = ava("check", str(project / "nope.md"))
    assert r.returncode == 2
    assert "no such file" in r.stderr


def test_the_bundled_lexicon_loads_for_the_surface(ava):
    """The universal lexicons ship in the wheel; W-M10 runs without a flag."""
    r = ava("check", "-", "--rules", "technical", stdin=CLEAN)
    assert "lexicon: universal-doc-technical" in r.stderr
    assert "jargon density" in r.stderr
