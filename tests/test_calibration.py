import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "app/scripts/build_baselines.py"
spec = importlib.util.spec_from_file_location("calibration", SCRIPT)
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


@pytest.fixture
def inputs(tmp_path):
    entries = []
    for side, text in (("human", "The team read the report."),
                       ("ai", "The team read the report — then left.")):
        folder = tmp_path / side
        folder.mkdir()
        (folder / "sample.txt").write_text(text)
        for surface in ("chat", "code", "doc-shared", "doc-technical"):
            entries.append(dict(surface=surface, side=side, origin="universal",
                                label=f"{surface}-{side}", path=side))
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps({"corpora": entries}))
    return manifest


@pytest.fixture
def ready(monkeypatch):
    ids = ["W-M1", "W-M2", "W-M3", "W-M4", "W-M6", "W-M7", "W-M8", "W-M9",
           "W-M11", "P-M1", "P-M3", "T-M1", "T-M2", "T-M3", "T-M4", "T-M5",
           "T-M7", "T-M8", "T-M9", "T-M10", "T-M11", "T-M12"]
    modules = [SimpleNamespace(RULE=rule, check=lambda text, ctx: []) for rule in ids]
    modules[0].check = lambda text, ctx: [None] * text.count("—")
    monkeypatch.setattr(calibration.checks, "select",
                        lambda *args, **kwargs: (modules, ["1", "1b", "2"], [], ""))


def run(inputs, output, *extra):
    return calibration.main(["--manifest", str(inputs), "--output", str(output), *extra])


def test_complete_run_has_rates_and_provenance(inputs, tmp_path, ready):
    output = tmp_path / "result"
    assert run(inputs, output) == 0
    table = json.loads((output / "bands/chat.json").read_text())
    assert len(table["rules"]) == 22
    assert table["rules"]["W-M1"]["human_universal"] == [0, 0]
    assert table["rules"]["W-M1"]["ai_universal"] == 142.86
    cached = json.loads((output / "baselines_run.json").read_text())
    assert cached["provenance"]["completed_checks"] == cached["rules"]
    assert cached["provenance"]["generated"].endswith("Z")
    assert all(row["docs"] == 1 and row["words"] > 0 for row in cached["corpora"])
    assert str(tmp_path) not in json.dumps(cached)
    assert cached["corpora"][0]["label"] == "chat-human"
    assert "chat-human" not in json.dumps(table)
    assert table["meta"]["provenance"]["sources"] == [
        {key: row[key] for key in ("id", "sha256", "docs", "words")}
        for row in cached["corpora"]]


@pytest.mark.parametrize("failure", ["missing", "empty", "no_words"])
def test_bad_source_preserves_results(inputs, tmp_path, ready, failure):
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_text("reviewed")
    source = tmp_path / "human/sample.txt"
    source.unlink()
    if failure == "missing":
        source.parent.rmdir()
    elif failure == "no_words":
        source.write_text(" \n")
    output = tmp_path / "result"
    assert run(inputs, output) == 2
    assert not output.exists()
    assert reviewed.read_text() == "reviewed"


def test_missing_parser_names_dependency(inputs, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(calibration.checks, "select", lambda *a, **k:
                        ([], ["1"], ["W-M11"], "the en_core_web_sm model is not installed"))
    output = tmp_path / "result"
    assert run(inputs, output) == 2
    assert "en_core_web_sm" in capsys.readouterr().err
    assert not output.exists()


def test_unreadable_source_and_checker_failure_create_no_output(inputs, tmp_path, ready, monkeypatch):
    original = Path.read_bytes
    def unreadable(path):
        if path.name == "sample.txt":
            raise PermissionError("source is unreadable")
        return original(path)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", unreadable)
        assert run(inputs, tmp_path / "unreadable") == 2
    assert not (tmp_path / "unreadable").exists()
    def broken(text, context):
        raise RuntimeError("analysis failed")
    selected = calibration.checks.select()[0]
    selected[0].check = broken
    assert run(inputs, tmp_path / "broken") == 2
    assert not (tmp_path / "broken").exists()


def test_source_change_after_preflight_cannot_produce_a_run(inputs, tmp_path, ready, monkeypatch):
    select = calibration.checks.select
    def change_source(*args, **kwargs):
        (tmp_path / "human/sample.txt").write_text("This document changed.")
        return select(*args, **kwargs)
    monkeypatch.setattr(calibration.checks, "select", change_source)
    assert run(inputs, tmp_path / "result") == 2
    assert not (tmp_path / "result").exists()


def test_manifest_exclusions_do_not_distort_the_human_range(inputs, tmp_path, ready):
    data = json.loads(inputs.read_text())
    data["corpora"].append(dict(surface="chat", side="human", origin="universal",
                               label="excluded-example", path="ai", exclude_rules=["W-M1"]))
    inputs.write_text(json.dumps(data))
    output = tmp_path / "result"
    assert run(inputs, output) == 0
    entry = json.loads((output / "bands/chat.json").read_text())["rules"]["W-M1"]
    assert entry["human_universal"] == [0, 0]
    assert entry["human_universal_n"] == 1


def test_exclusions_cannot_empty_a_configured_reference_group(inputs, tmp_path, ready):
    data = json.loads(inputs.read_text())
    data["corpora"].append(dict(surface="chat", side="human", origin="internal",
                               label="format-example", path="human", exclude_rules=["W-M1"]))
    inputs.write_text(json.dumps(data))
    assert run(inputs, tmp_path / "result") == 2
    assert not (tmp_path / "result").exists()


def test_reuse_rejects_changed_sources_and_incomplete_cache(inputs, tmp_path, ready):
    first = tmp_path / "first"
    assert run(inputs, first) == 0
    cache = first / "baselines_run.json"
    assert run(inputs, tmp_path / "second", "--reuse", str(cache)) == 0
    original = cache.read_bytes()
    data = json.loads(original)
    data["corpora"][0]["counts"].pop("W-M1")
    cache.write_text(json.dumps(data))
    assert run(inputs, tmp_path / "incomplete", "--reuse", str(cache)) == 2
    assert not (tmp_path / "incomplete").exists()
    cache.write_bytes(original)
    (tmp_path / "human/sample.txt").write_text("A different report.")
    assert run(inputs, tmp_path / "changed", "--reuse", str(cache)) == 2
    assert not (tmp_path / "changed").exists()
    assert cache.read_bytes() == original


@pytest.mark.parametrize("invalid", ["missing", "nan", "checks", "extra_provenance"])
def test_invalid_reuse_never_falls_back_to_analysis(inputs, tmp_path, ready, invalid):
    first = tmp_path / "first"
    assert run(inputs, first) == 0
    cache = first / "baselines_run.json"
    data = json.loads(cache.read_text())
    if invalid == "missing":
        cache.unlink()
    else:
        if invalid == "nan":
            data["corpora"][0]["per_1k"]["W-M1"] = float("nan")
        elif invalid == "checks":
            data["provenance"]["completed_checks"].pop()
        else:
            data["provenance"]["notes"] = "local research notes"
        cache.write_text(json.dumps(data))
    assert run(inputs, tmp_path / "result", "--reuse", str(cache)) == 2
    assert not (tmp_path / "result").exists()


def test_existing_output_and_failed_writes_preserve_results(inputs, tmp_path, ready, monkeypatch):
    output = tmp_path / "result"
    output.mkdir()
    marker = output / "reviewed.json"
    marker.write_text("reviewed")
    assert run(inputs, output) == 2
    assert marker.read_text() == "reviewed"


    original = Path.write_text

    def fail_table(path, *args, **kwargs):
        if path.name == "code.json":
            raise OSError("test write failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_table)
    assert run(inputs, tmp_path / "failed") == 2
    assert not (tmp_path / "failed").exists()
    assert marker.read_text() == "reviewed"


def test_shipped_fixture_target_is_refused(inputs, tmp_path, ready, monkeypatch):
    monkeypatch.setattr(calibration, "ROOT", tmp_path)
    assert run(inputs, tmp_path / "fixtures/new-calibration") == 2
    assert not (tmp_path / "fixtures").exists()


def test_cli_with_real_parser(inputs, tmp_path):
    from app.checks.parser import available
    if not available()[0]:
        pytest.skip("requires the parser extra")
    output = tmp_path / "cli-result"
    result = subprocess.run([sys.executable, str(SCRIPT), "--manifest", str(inputs),
                             "--output", str(output)], capture_output=True, text=True,
                            cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert len(json.loads((output / "bands/chat.json").read_text())["rules"]) == 22
