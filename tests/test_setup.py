"""`ava setup`: the harness install command, run from the installed package.

Every test runs in an empty project directory with a fresh HOME. The packaged
assets under `ava_jargon/assets` are the expected file contents.
"""
from importlib.resources import files

import pytest
import yaml

try:
    import tomllib
except ImportError:  # Python 3.10 and older
    import tomli as tomllib

from conftest import REPO

ASSETS = files("ava_jargon") / "assets"
SKILL_FILES = ("SKILL.md", "references/voices.md", "references/custom-lexicons.md")
GATES = ("ava-prose-gate.md", "ava-technical-gate.md")
CODEX_AGENTS = [f".codex/agents/{g[:-3]}.toml" for g in GATES]


def written(root):
    """Every file under root, relative, sorted."""
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def front_matter(text):
    """(meta, body) for a file with a `---` header. The header must parse as
    YAML: that is what a harness does with it."""
    lines = text.split("\n")
    assert lines[0] == "---", text[:80]
    end = lines.index("---", 1)
    meta = yaml.safe_load("\n".join(lines[1:end]))
    return meta, "\n".join(lines[end + 1:]).lstrip("\n")


def skill_paths(base=".agents"):
    return [f"{base}/skills/ava/{f}" for f in SKILL_FILES]


# --- the skill ---------------------------------------------------------------


def test_skills_writes_the_skill_and_nothing_else(ava, project):
    r = ava("setup", "skills")
    assert r.returncode == 0, r.stderr
    assert written(project) == sorted(skill_paths())
    assert sorted(r.stdout.split()) == sorted(skill_paths())
    for f in SKILL_FILES:
        assert ((project / ".agents/skills/ava" / f).read_text()
                == (ASSETS / "skills/ava" / f).read_text())


# --- the gate agents ---------------------------------------------------------


@pytest.mark.parametrize("name", GATES)
def test_cursor_rewrites_the_gate_front_matter(ava, project, name):
    r = ava("setup", "cursor")
    assert r.returncode == 0, r.stderr
    source_meta, source_body = front_matter((ASSETS / "agents" / name).read_text())
    meta, body = front_matter((project / ".cursor/agents" / name).read_text())
    assert meta == {"name": name[:-3], "description": source_meta["description"]}
    assert list(meta) == ["name", "description"]
    assert body == source_body


def test_cursor_writes_the_skill_and_both_gates(ava, project):
    r = ava("setup", "cursor")
    assert r.returncode == 0, r.stderr
    assert written(project) == sorted(skill_paths() + [f".cursor/agents/{g}" for g in GATES])


@pytest.mark.parametrize("name", GATES)
def test_opencode_marks_each_gate_a_subagent(ava, project, name):
    r = ava("setup", "opencode")
    assert r.returncode == 0, r.stderr
    source_meta, source_body = front_matter((ASSETS / "agents" / name).read_text())
    meta, body = front_matter((project / ".opencode/agents" / name).read_text())
    assert meta == {"description": source_meta["description"], "mode": "subagent"}
    assert list(meta) == ["description", "mode"]
    assert body == source_body


def test_cursor_global_writes_under_home(ava, project, home):
    r = ava("setup", "cursor", "-g")
    assert r.returncode == 0, r.stderr
    assert written(project) == []
    assert written(home) == sorted(skill_paths() + [f".cursor/agents/{g}" for g in GATES])


def test_opencode_global_writes_the_xdg_config_dir(ava, project, home):
    r = ava("setup", "opencode", "-g")
    assert r.returncode == 0, r.stderr
    assert written(project) == []
    assert written(home) == sorted(skill_paths()
                                   + [f".config/opencode/agents/{g}" for g in GATES])


def test_codex_writes_the_skill_and_both_gates(ava, project):
    r = ava("setup", "codex")
    assert r.returncode == 0, r.stderr
    assert written(project) == sorted(skill_paths() + CODEX_AGENTS)
    assert sorted(r.stdout.split()) == sorted(skill_paths() + CODEX_AGENTS)
    assert r.stderr == ""


@pytest.mark.parametrize("name", GATES)
def test_codex_renders_each_gate_as_a_custom_agent(ava, project, name):
    """Codex reads a custom agent from TOML: no front matter, the body under
    developer_instructions, and a read-only sandbox for a gate that edits nothing."""
    r = ava("setup", "codex")
    assert r.returncode == 0, r.stderr
    source_meta, source_body = front_matter((ASSETS / "agents" / name).read_text())
    doc = tomllib.loads((project / f".codex/agents/{name[:-3]}.toml").read_text())
    assert doc == {"name": name[:-3], "description": source_meta["description"],
                   "sandbox_mode": "read-only", "developer_instructions": source_body}
    assert list(doc) == ["name", "description", "sandbox_mode", "developer_instructions"]


def test_codex_global_writes_the_user_codex_dir(ava, project, home):
    r = ava("setup", "codex", "-g")
    assert r.returncode == 0, r.stderr
    assert written(project) == []
    assert written(home) == sorted(skill_paths() + CODEX_AGENTS)


# --- the AGENTS.md contract --------------------------------------------------


def test_agents_md_prints_the_contract_and_writes_nothing(ava, project, home):
    r = ava("setup", "agents-md")
    assert r.returncode == 0, r.stderr
    assert r.stdout == (ASSETS / "gate-contract.md").read_text()
    assert written(project) == [] and written(home) == []


def test_agents_md_refuses_global(ava):
    r = ava("setup", "agents-md", "-g")
    assert r.returncode == 2
    assert "agents-md prints to stdout" in r.stderr


# --- conflicts ---------------------------------------------------------------


def test_an_existing_file_stops_the_install(ava, project):
    assert ava("setup", "cursor").returncode == 0
    skill = project / ".agents/skills/ava/SKILL.md"
    skill.write_text("edited\n")
    r = ava("setup", "cursor")
    assert r.returncode == 2
    assert ".agents/skills/ava/SKILL.md exists (--force overwrites)" in r.stderr
    assert skill.read_text() == "edited\n"


def test_force_overwrites(ava, project):
    assert ava("setup", "cursor").returncode == 0
    skill = project / ".agents/skills/ava/SKILL.md"
    skill.write_text("edited\n")
    r = ava("setup", "cursor", "--force")
    assert r.returncode == 0, r.stderr
    assert skill.read_text() == (ASSETS / "skills/ava/SKILL.md").read_text()


# --- packaging ---------------------------------------------------------------


@pytest.mark.parametrize("rel", ["gate-contract.md"]
                         + [f"agents/{g}" for g in GATES]
                         + [f"skills/ava/{f}" for f in SKILL_FILES])
def test_the_packaged_asset_matches_the_repo_file(rel):
    """The assets are symlinks in the repo; the wheel must carry real copies."""
    assert (ASSETS / rel).read_text() == (REPO / rel).read_text()
