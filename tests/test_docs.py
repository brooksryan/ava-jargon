"""The research directory: the studies behind the lexicons and the checks.

The index and both studies ship with the repository. Each study states its
five parts. The feature docs link the matching study. No research document
points at a local-only path or names a handle.
"""
import re

import pytest

from conftest import REPO

RESEARCH = REPO / "research"
STUDIES = ("lexicons.md", "mechanical-checks.md")
PARTS = ("question", "method", "data", "result", "decision")
LOCAL_ONLY = ("corpus/", "notes/", "audit/", "tmp/", "lexicons/analysis-")
LINK = re.compile(r"\]\(([^)#\s]+)")


def headings(text):
    return [line[3:].strip().lower() for line in text.splitlines()
            if line.startswith("## ")]


def test_the_directory_holds_the_index_and_both_studies():
    assert sorted(p.name for p in RESEARCH.glob("*.md")) == ["README.md", *STUDIES]


@pytest.mark.parametrize("name", STUDIES)
def test_a_study_states_its_five_parts_in_order(name):
    found = headings((RESEARCH / name).read_text())
    positions = []
    for part in PARTS:
        hits = [i for i, h in enumerate(found) if part in h]
        assert hits, f"{name}: no heading for the {part}"
        positions.append(hits[0])
    assert positions == sorted(positions), f"{name}: parts out of order: {found}"


def test_the_index_lists_each_study_with_a_date():
    text = (RESEARCH / "README.md").read_text()
    for name in STUDIES:
        rows = [line for line in text.splitlines()
                if line.startswith("|") and f"]({name})" in line]
        assert len(rows) == 1, f"{name}: expected one table row, got {rows}"
        assert re.search(r"\b\d{4}-\d{2}-\d{2}\b", rows[0]), rows[0]


@pytest.mark.parametrize("doc, study", [
    ("app/lexicons/README.md", "lexicons.md"),
    ("app/checks/README.md", "mechanical-checks.md"),
])
def test_a_feature_doc_links_its_study(doc, study):
    text = (REPO / doc).read_text()
    assert f"](../../research/{study})" in text, f"{doc} does not link {study}"


def test_the_main_readme_read_more_table_has_a_research_row():
    text = (REPO / "README.md").read_text()
    rows = [line for line in text.splitlines()
            if line.startswith("|") and "](research/README.md)" in line]
    assert len(rows) == 1, rows


@pytest.mark.parametrize("name", ["README.md", *STUDIES])
def test_a_research_doc_points_only_at_shipped_paths(name):
    text = (RESEARCH / name).read_text()
    for marker in LOCAL_ONLY:
        assert marker not in text, f"{name} names the local-only path {marker}"
    for target in LINK.findall(text):
        if target.startswith("http"):
            continue
        assert (RESEARCH / target).exists(), f"{name} links {target}, which is absent"


@pytest.mark.parametrize("name", ["README.md", *STUDIES])
def test_a_research_doc_names_no_handle(name):
    text = (RESEARCH / name).read_text()
    assert not re.search(r"(?<![\w`])@\w+", text), f"{name} names a handle"
