"""The supported release tools under app/scripts.

The directory holds the calibration script, the figure script, the Markdown
unwrap hook, and their inventory. Research scripts, corpus collectors, and
one-off reports stay outside the repository. Every documented script path
resolves, and no supported tool reads a local-only directory.
"""
import importlib.util
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from conftest import REPO

SCRIPTS = REPO / "app" / "scripts"
SUPPORTED = {"build_baselines.py", "build_research_figures.py", "unwrap_md.py"}
LOCAL_ONLY = ("corpus/", "audit/", "notes/", "tmp/", "lexicons/analysis-", ".claude/")
SCRIPT_PATH = re.compile(r"app/scripts/([\w.-]+\.py)")
DOCUMENTS = [
    *REPO.glob("*.md"), REPO / "MANIFEST.in", REPO / "Dockerfile",
    *REPO.glob("app/**/*.md"), *REPO.glob("agents/*.md"), *REPO.glob("fixtures/*.md"),
    *REPO.glob("fixtures/bands/*.json"), *REPO.glob("research/*.md"),
    *REPO.glob("tests/*.md"), REPO / "githooks" / "pre-commit",
]


def load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_directory_holds_only_the_supported_tools():
    present = {p.name for p in SCRIPTS.iterdir() if p.is_file()}
    assert present == {"README.md", *SUPPORTED}


@pytest.mark.parametrize("name", sorted(SUPPORTED))
def test_the_inventory_names_each_supported_tool(name):
    assert name in (SCRIPTS / "README.md").read_text()


@pytest.mark.parametrize("name", sorted(SUPPORTED))
def test_a_supported_tool_reads_no_local_only_directory(name):
    text = (SCRIPTS / name).read_text()
    for marker in LOCAL_ONLY:
        assert marker not in text, f"{name} names the local-only path {marker}"


@pytest.mark.parametrize("document", [p for p in DOCUMENTS if p.is_file()],
                         ids=lambda p: str(p.relative_to(REPO)))
def test_a_documented_script_path_resolves(document):
    for name in SCRIPT_PATH.findall(document.read_text()):
        assert (SCRIPTS / name).is_file(), f"{document.name} names app/scripts/{name}"


def test_the_figure_script_reproduces_the_shipped_figures(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPTS / "build_research_figures.py"),
                             str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    shipped = REPO / "research" / "figures"
    assert {p.name for p in tmp_path.iterdir()} == {p.name for p in shipped.glob("*.svg")}
    for figure in shipped.glob("*.svg"):
        assert (tmp_path / figure.name).read_bytes() == figure.read_bytes(), figure.name


def test_the_figure_script_writes_the_research_directory_by_default():
    module = load("build_research_figures.py")
    assert Path(module.OUT).resolve() == (REPO / "research" / "figures").resolve()


def test_unwrap_joins_wrapped_prose_and_keeps_structure():
    unwrap = load("unwrap_md.py").unwrap
    text = ("---\ntitle: a\nkey: b\n---\n"
            "# Heading\n\nOne line\nwraps here.\n\n"
            "- item one\n  continues\n- item two\n\n"
            "```\ncode line\nkeeps its break\n```\n\n"
            "| a | b |\n| - | - |\n")
    assert unwrap(text) == ("---\ntitle: a\nkey: b\n---\n"
                            "# Heading\n\nOne line wraps here.\n\n"
                            "- item one continues\n- item two\n\n"
                            "```\ncode line\nkeeps its break\n```\n\n"
                            "| a | b |\n| - | - |\n")


def test_unwrap_is_idempotent_and_rewrites_only_changed_files(tmp_path):
    module = load("unwrap_md.py")
    wrapped = tmp_path / "wrapped.md"
    wrapped.write_text("One line\nwraps here.\n")
    flat = tmp_path / "flat.md"
    flat.write_text("One line stays.\n")
    before = flat.stat().st_mtime_ns
    result = subprocess.run([sys.executable, str(SCRIPTS / "unwrap_md.py"),
                             str(wrapped), str(flat)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(wrapped)
    assert wrapped.read_text() == "One line wraps here.\n"
    assert flat.stat().st_mtime_ns == before
    once = module.unwrap(wrapped.read_text())
    assert module.unwrap(once) == once


def test_the_source_archive_ships_the_supported_tools_only():
    directory = os.environ.get("AVA_DIST_DIR")
    if not directory:
        pytest.skip("./test supplies the built release archives")
    with tarfile.open(next(Path(directory).glob("*.tar.gz"))) as source:
        members = source.getmembers()
        root = members[0].name.split("/")[0] + "/"
        names = {m.name.removeprefix(root) for m in members if m.isfile()}
    shipped = {n.removeprefix("app/scripts/") for n in names if n.startswith("app/scripts/")}
    assert shipped == {"README.md", *SUPPORTED}
