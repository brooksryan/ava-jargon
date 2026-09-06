"""`ava voice` and `--voice`: a voice names its checks, bands, lexicon, and rubric.

Four voices ship. A name resolves shipped first, then `.ava/voices/NAME.json`
in the project, then `$AVA_HOME/voices/NAME.json`. A file from before this
schema, with `surface` and `rules`, still loads.
"""
import json
import re
from importlib.resources import files

import pytest

WESTINGHOUSE = {"W-M1", "W-M2", "W-M3", "W-M4", "W-M6", "W-M7", "W-M8", "W-M9", "W-M10"}
TECHNICAL = WESTINGHOUSE | {"W-M11", "T-M1", "T-M2", "T-M3", "T-M4", "T-M5", "T-M7",
                            "T-M8", "T-M9", "T-M10", "T-M11", "T-M12"}
SHIPPED = {"westinghouse": ("chat", WESTINGHOUSE), "shared-docs": ("doc-shared", WESTINGHOUSE),
           "technical-docs": ("doc-technical", TECHNICAL), "code": ("code", TECHNICAL)}
PASS_FAIL_RULE = {"name": "plain", "description": "The text says one thing.",
                  "criteria": ["Every sentence carries one claim."],
                  "scoring": {"type": "pass-fail"}, "requirement": {"pass": True}}
DOC = "The deploy job ran well and the team read the report.\n\n" * 40


def voice_json(ava, name):
    r = ava("voice", "rubric", name, "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def write_voice(root, name, doc):
    (root / ".ava" / "voices").mkdir(parents=True, exist_ok=True)
    (root / ".ava" / "voices" / f"{name}.json").write_text(json.dumps({**doc, "name": name}))


def new_voice(ava, project, name, doc, *flags):
    (project / f"{name}.json").write_text(json.dumps(doc))
    return ava("voice", "new", name, f"{name}.json", "--project", *flags)


def verdict_line(stderr):
    return next(line for line in stderr.splitlines() if line.startswith("checked "))


# --- the shipped voices ---------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SHIPPED))
def test_a_shipped_voice_names_its_checks_bands_and_lexicon(ava, name):
    doc = voice_json(ava, name)
    bands, checks = SHIPPED[name]
    assert doc["bands"] == bands
    assert set(doc["checks"]) == checks and len(doc["checks"]) == len(checks)
    assert doc["lexicon"] == f"universal-{bands}"
    assert doc["rubric"] == [] and doc["extend"] == []
    assert "surface" not in doc and "rules" not in doc


def test_list_names_the_shipped_voices(ava):
    r = ava("voice", "list")
    assert r.returncode == 0, r.stderr
    assert re.search(r"^code\s+shipped\s+code\s+21 checks\s+0 rubric", r.stdout, re.M)
    assert re.search(r"^westinghouse\s+shipped\s+chat\s+9 checks", r.stdout, re.M)


def test_the_schema_requires_checks_and_bands(ava):
    r = ava("voice", "schema")
    schema = json.loads(r.stdout)
    assert schema["title"] == "ava voice"
    assert set(schema["required"]) == {"name", "checks", "bands"}
    assert "rubric" in schema["properties"] and "rules" not in schema["properties"]


def test_a_shipped_voice_refuses_set_and_rm(ava, project):
    (project / "patch.json").write_text('{"bands": "chat"}')
    r = ava("voice", "set", "code", "patch.json")
    assert r.returncode == 2 and "shipped voice" in r.stderr
    r = ava("voice", "rm", "code")
    assert r.returncode == 2 and "shipped voice" in r.stderr


# --- ava check under a voice ----------------------------------------------------


def test_a_voice_equals_its_flags(ava, project):
    (project / "doc.txt").write_text(DOC)
    by_voice = ava("check", "doc.txt", "--voice", "code")
    by_flags = ava("check", "doc.txt", "--rules", "technical", "--bands", "code")
    assert by_voice.returncode == by_flags.returncode
    assert by_voice.stdout == by_flags.stdout
    assert verdict_line(by_voice.stderr) == verdict_line(by_flags.stderr)
    assert "voice: code (shipped)" in by_voice.stderr
    assert "lexicon: universal-code (voice; --lexicon overrides)" in by_voice.stderr
    assert "band summary (bands: code, 440 words):" in by_voice.stderr


def test_an_explicit_flag_overrides_the_voice(ava, project):
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--voice", "code", "--rules", "westinghouse", "--bands", "chat")
    plain = ava("check", "doc.txt", "--rules", "westinghouse", "--bands", "chat")
    assert verdict_line(r.stderr) == verdict_line(plain.stderr)
    assert "band summary (bands: chat, 440 words):" in r.stderr


def test_rules_accepts_rule_ids(ava, project):
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--rules", "W-M1,W-M4")
    assert "checked 2 rules over 440 words" in r.stderr
    r = ava("check", "doc.txt", "--rules", "W-M1,W-M99")
    assert r.returncode == 2 and "unknown rule id: W-M99" in r.stderr


def test_a_voice_lexicon_may_be_a_path(ava, project):
    (project / "lex.json").write_text((files("ava_jargon") / "lexicons" / "universal-code.json").read_text())
    write_voice(project, "mine", {"checks": ["W-M1", "W-M10"], "bands": "code",
                                  "lexicon": str(project / "lex.json")})
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--voice", "mine")
    assert f"lexicon: {project / 'lex.json'} (voice; --lexicon overrides)" in r.stderr
    assert "jargon density" in r.stderr


def test_a_voice_without_a_lexicon_takes_the_universal_one_for_its_bands(ava, project):
    write_voice(project, "mine", {"checks": ["W-M1", "W-M10"], "bands": "chat"})
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--voice", "mine")
    assert "lexicon: universal-chat (auto; --lexicon overrides)" in r.stderr


def test_the_json_report_names_the_voice(ava, project):
    (project / "doc.txt").write_text(DOC)
    r = ava("check", "doc.txt", "--voice", "code", "--json")
    doc = json.loads(r.stdout)
    assert doc["voice"]["name"] == "code" and doc["voice"]["scope"] == "shipped"
    assert doc["rules"] == "code"


# --- a file from before this schema ---------------------------------------------


def test_an_older_voice_file_upgrades_on_load(ava, project):
    write_voice(project, "old", {"surface": "chat", "rules": [PASS_FAIL_RULE]})
    doc = voice_json(ava, "old")
    assert doc["bands"] == "chat" and "surface" not in doc
    assert set(doc["checks"]) == WESTINGHOUSE
    assert doc["rubric"] == [PASS_FAIL_RULE] and "rules" not in doc


def test_an_older_voice_runs_the_set_its_surface_implied(ava, project):
    write_voice(project, "old", {"surface": "code", "rules": [PASS_FAIL_RULE]})
    (project / "doc.txt").write_text(DOC)
    by_voice = ava("check", "doc.txt", "--voice", "old")
    by_flags = ava("check", "doc.txt", "--rules", "technical", "--bands", "code")
    assert verdict_line(by_voice.stderr) == verdict_line(by_flags.stderr)


def test_set_writes_the_new_keys_back(ava, project):
    write_voice(project, "old", {"surface": "chat", "rules": [PASS_FAIL_RULE]})
    r = ava("voice", "set", "old", "bands", "code")
    assert r.returncode == 0, r.stderr
    saved = json.loads((project / ".ava" / "voices" / "old.json").read_text())
    assert list(saved)[:4] == ["name", "checks", "bands", "lexicon"] or list(saved)[:3] == ["name", "checks", "bands"]
    assert "surface" not in saved and "rules" not in saved and saved["bands"] == "code"


# --- new voices and edits --------------------------------------------------------


def test_new_seeds_the_checks_from_a_set(ava, project):
    r = new_voice(ava, project, "mine", {"bands": "code"}, "--checks", "technical")
    assert r.returncode == 0, r.stderr
    assert set(voice_json(ava, "mine")["checks"]) == TECHNICAL


def test_new_without_checks_fails_the_schema(ava, project):
    r = new_voice(ava, project, "mine", {"bands": "code"})
    assert r.returncode == 2 and "missing required field 'checks'" in r.stderr


def test_set_adds_and_drops_rule_ids(ava, project):
    assert new_voice(ava, project, "mine", {"bands": "chat"}, "--checks", "westinghouse").returncode == 0
    r = ava("voice", "set", "mine", "checks", "+W-M11", "-W-M1")
    assert r.returncode == 0, r.stderr
    assert set(voice_json(ava, "mine")["checks"]) == (WESTINGHOUSE - {"W-M1"}) | {"W-M11"}


def test_set_replaces_a_scalar_field(ava, project):
    assert new_voice(ava, project, "mine", {"bands": "chat"}, "--checks", "westinghouse").returncode == 0
    assert ava("voice", "set", "mine", "bands", "code").returncode == 0
    assert ava("voice", "set", "mine", "lexicon", "universal-code").returncode == 0
    doc = voice_json(ava, "mine")
    assert doc["bands"] == "code" and doc["lexicon"] == "universal-code"


def test_set_still_merges_a_patch_file(ava, project):
    assert new_voice(ava, project, "mine", {"bands": "chat"}, "--checks", "westinghouse").returncode == 0
    (project / "patch.json").write_text(json.dumps({"rubric": [PASS_FAIL_RULE]}))
    r = ava("voice", "set", "mine", "patch.json")
    assert r.returncode == 0, r.stderr
    assert voice_json(ava, "mine")["rubric"] == [PASS_FAIL_RULE]


def test_an_unknown_rule_id_fails_the_schema(ava, project):
    r = new_voice(ava, project, "mine", {"bands": "chat", "checks": ["W-M1", "W-M99"]})
    assert r.returncode == 2 and "unknown rule id: W-M99" in r.stderr


def test_an_unknown_band_table_fails_the_voice(ava, project):
    r = new_voice(ava, project, "mine", {"bands": "nope", "checks": ["W-M1"]})
    assert r.returncode == 2 and "no band table named nope" in r.stderr


def test_a_project_voice_wins_over_a_personal_one_but_not_over_a_shipped_one(ava, project, home):
    write_voice(project, "mine", {"checks": ["W-M1"], "bands": "chat", "description": "PROJECT"})
    write_voice(home, "mine", {"checks": ["W-M1"], "bands": "chat", "description": "PERSONAL"})
    write_voice(project, "code", {"checks": ["W-M1"], "bands": "chat", "description": "MARKER"})
    assert voice_json(ava, "mine")["description"] == "PROJECT"
    assert voice_json(ava, "code")["description"] != "MARKER"


def test_rubric_prints_the_settings_then_the_rules(ava, project):
    write_voice(project, "mine", {"checks": ["W-M1"], "bands": "chat", "rubric": [PASS_FAIL_RULE]})
    r = ava("voice", "rubric", "mine")
    assert r.stdout.startswith("voice: mine (project) · bands chat · lexicon universal-chat · checks 1 · extend: none")
    assert "1. plain · pass/fail · must pass" in r.stdout
