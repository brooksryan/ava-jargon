#!/usr/bin/env python3
"""Compute baseline bands from a local corpus manifest into a new review directory."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import checks
from app import config as CFG
from app.checks import Context, bands

SURFACES = {"chat", "code", "doc-shared", "doc-technical"}
DIRECTIONS = {
    **{rule: "ai-high" for rule in (
        "W-M1", "W-M2", "W-M3", "W-M4", "W-M6", "W-M7", "W-M8", "W-M9", "P-M1", "P-M3")},
    **{rule: "human-high" for rule in (
        "W-M11", "T-M1", "T-M2", "T-M3", "T-M4", "T-M5", "T-M7", "T-M8", "T-M9",
        "T-M10", "T-M11", "T-M12")},
}
RULES = sorted(DIRECTIONS)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_inputs(path):
    raw = path.read_bytes()
    manifest = json.loads(raw)
    entries = manifest.get("corpora") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest needs a nonempty corpora list")
    sources, documents, labels = [], [], set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"corpus {index + 1}: expected an object")
        label = entry.get("label")
        if not isinstance(label, str) or not label.strip() or label in labels:
            raise ValueError(f"corpus {index + 1}: label must be nonempty and unique")
        labels.add(label)
        for key, allowed in (("surface", SURFACES), ("side", {"human", "ai"}),
                             ("origin", {"universal", "internal"})):
            if not isinstance(entry.get(key), str) or entry[key] not in allowed:
                raise ValueError(f"{label}: invalid {key}")
        excluded = entry.get("exclude_rules", [])
        if (not isinstance(excluded, list) or any(rule not in RULES for rule in excluded)
                or len(set(excluded)) != len(excluded)):
            raise ValueError(f"{label}: exclude_rules must contain unique calibration rule IDs")
        if not isinstance(entry.get("path"), str) or not entry["path"]:
            raise ValueError(f"{label}: provide a corpus path")
        folder = (path.parent / entry["path"]).resolve()
        if not folder.is_dir():
            raise ValueError(f"{label}: missing corpus directory {folder}")
        files = []
        def walk_error(error):
            raise error
        for directory, _, names in os.walk(folder, onerror=walk_error):
            files.extend(Path(directory) / name for name in names if name.endswith(".txt"))
        files.sort()
        if not files:
            raise ValueError(f"{label}: no .txt documents in {folder}")
        documents_of_source, hashes, words = [], [], 0
        for file in files:
            content = file.read_bytes()
            text = content.decode("utf-8")
            relative = file.relative_to(folder).as_posix()
            fingerprint = digest(relative.encode() + b"\0" + content)
            documents_of_source.append((file, relative, fingerprint))
            hashes.append(fingerprint)
            words += len(WORD_RE.findall(text))
        if not words:
            raise ValueError(f"{label}: corpus contains no words")
        sources.append({"id": f"corpus-{index + 1}", "label": label,
                        **{key: entry[key] for key in ("surface", "side", "origin")},
                        "exclude_rules": sorted(excluded), "docs": len(files), "words": words,
                        "sha256": digest(json.dumps(hashes).encode()), "file_sha256": hashes})
        documents.append(documents_of_source)
    if {source["surface"] for source in sources} != SURFACES:
        raise ValueError("manifest must cover chat, code, doc-shared and doc-technical")
    for surface in SURFACES:
        for side in ("human", "ai"):
            if not any(s["surface"] == surface and s["side"] == side
                       and s["origin"] == "universal" for s in sources):
                raise ValueError(f"{surface}: missing {side} universal corpus")
    return digest(raw), sources, documents


def required_checks():
    selected, tiers, skipped, warning = checks.select(
        RULES, Context(path="", lexicon=None, fields=None), use_parser=True)
    actual = [module.RULE for module in selected]
    if warning or skipped or sorted(actual) != RULES or "2" not in tiers:
        missing = sorted(set(RULES) - set(actual))
        raise ValueError(warning or f"incomplete analysis; missing checks: {', '.join(missing or skipped)}")
    return selected


def engine_identity():
    paths = sorted((ROOT / "app/checks").rglob("*.py"))
    paths += [Path(__file__).resolve(), ROOT / "pyproject.toml"]
    code = hashlib.sha256()
    for path in paths:
        code.update(path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes())
    versions = {}
    for package in ("spacy", "en-core-web-sm"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "unavailable"
    return {"code_sha256": code.hexdigest(), "python": sys.version.split()[0], **versions}


def analyze(sources, documents, selected, provenance):
    rows = []
    for source, files in zip(sources, documents):
        counts = dict.fromkeys(RULES, 0)
        for path, relative, expected in files:
            content = path.read_bytes()
            if digest(relative.encode() + b"\0" + content) != expected:
                raise ValueError(f"source changed after validation: {path}")
            text = content.decode("utf-8")
            context = Context(path=str(path), lexicon=None, fields=None)
            for module in selected:
                try:
                    counts[module.RULE] += len(module.check(text, context) or [])
                except Exception as error:
                    raise ValueError(f"{module.RULE} failed for {path}: {error}") from error
        rows.append({**source, "counts": counts,
                     "per_1k": {rule: round(1000 * count / source["words"], 2)
                                for rule, count in counts.items()}})
    return {"format": 1, "rules": RULES, "provenance": provenance, "corpora": rows}


def validate_run(run, sources, identity):
    if not isinstance(run, dict) or run.get("format") != 1 or run.get("rules") != RULES:
        raise ValueError("cache needs a complete calibration run in format 1")
    provenance = run.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("cache lacks provenance")
    if (set(provenance) != {*identity, "generated"}
            or any(provenance.get(key) != value for key, value in identity.items())):
        raise ValueError("cache inputs or checks differ; run the calibration again")
    generated = provenance.get("generated")
    if not isinstance(generated, str) or not generated.endswith("Z"):
        raise ValueError("cache lacks its analysis time")
    datetime.fromisoformat(generated[:-1] + "+00:00")
    rows = run.get("corpora")
    if not isinstance(rows, list) or len(rows) != len(sources):
        raise ValueError("cache has incomplete corpus results")
    for source, row in zip(sources, rows):
        if not isinstance(row, dict) or any(row.get(key) != value for key, value in source.items()):
            raise ValueError("cache source fingerprints or counts differ")
        counts, rates = row.get("counts"), row.get("per_1k")
        if (not isinstance(counts, dict) or set(counts) != set(RULES)
                or not isinstance(rates, dict) or set(rates) != set(RULES)):
            raise ValueError("cache has incomplete check results")
        for rule in RULES:
            count, rate = counts[rule], rates[rule]
            if type(count) is not int or count < 0:
                raise ValueError(f"cache has invalid count for {rule}")
            if (type(rate) not in (int, float) or not math.isfinite(rate)
                    or rate != round(1000 * count / source["words"], 2)):
                raise ValueError(f"cache has inconsistent rate for {rule}")


def make_tables(run):
    tables = {}
    for surface in sorted(SURFACES):
        rows = [row for row in run["corpora"] if row["surface"] == surface]
        entries = {}
        for rule in RULES:
            entry = {"direction": DIRECTIONS[rule]}
            for side in ("human", "ai"):
                for origin in ("universal", "internal"):
                    values = [row["per_1k"][rule] for row in rows
                              if row["side"] == side and row["origin"] == origin
                              and rule not in row["exclude_rules"]]
                    if not values:
                        configured = any(row["side"] == side and row["origin"] == origin
                                         for row in rows)
                        if origin == "universal" or configured:
                            raise ValueError(f"{surface}: exclusions leave no {side} {origin} reference for {rule}")
                        continue
                    key = f"{side}_{origin}"
                    entry[key] = ([min(values), max(values)] if side == "human"
                                  else round(statistics.median(values), 2))
                    entry[f"{key}_n"] = len(values)
            entries[rule] = entry
        table = {"name": surface, "rules": entries,
                 "meta": {"ava": source_version(),
                          "generated": run["provenance"]["generated"],
                          "script": "app/scripts/build_baselines.py",
                          "unit": "findings per 1,000 words, corpus-level",
                          "band_rule": "human = [min,max] across corpora; ai = median",
                          "min_words_guard": 300, "provenance": run["provenance"]}}
        errors = bands.validate(table)
        if errors:
            raise ValueError("invalid band table: " + "; ".join(errors))
        tables[surface] = table
    return tables


def output_path(path):
    if path.exists() or path.is_symlink():
        raise ValueError(f"output already exists: {path}; choose a new directory")
    resolved = path.resolve()
    for protected in (ROOT / "fixtures", ROOT / "app"):
        if resolved == protected or protected in resolved.parents:
            raise ValueError("output must be outside shipped fixtures and app")
    return resolved


def source_version():
    text = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    if not match:
        raise ValueError("pyproject.toml lacks the source version")
    return match.group(1)


def default_output():
    return CFG.personal_path().parent / "bands" / "generated" / uuid4().hex


def write_results(output, run, tables):
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".calibration-", dir=output.parent))
    try:
        (staging / "bands").mkdir()
        (staging / "baselines_run.json").write_text(json.dumps(run, indent=2, allow_nan=False) + "\n")
        for name, table in tables.items():
            (staging / "bands" / f"{name}.json").write_text(json.dumps(table, indent=2, allow_nan=False) + "\n")
        output_path(output)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="local JSON corpus manifest")
    parser.add_argument("--output", type=Path,
                        help="new review directory (default: $AVA_HOME/bands/generated/<run>)")
    parser.add_argument("--reuse", type=Path, help="complete cached run with unchanged inputs and checks")
    args = parser.parse_args(argv)
    try:
        output = output_path(args.output if args.output is not None else default_output())
        for note in CFG.ensure_store(source_version()):
            print(f"note: {note}", file=sys.stderr)
        manifest_hash, sources, documents = read_inputs(args.manifest.resolve())
        selected = required_checks()
        identity = {"manifest_sha256": manifest_hash, "engine": engine_identity(),
                    "completed_checks": RULES,
                    "sources": [{key: source[key] for key in ("id", "sha256", "docs", "words")}
                                for source in sources]}
        if args.reuse:
            run = json.loads(args.reuse.read_bytes())
        else:
            run = analyze(sources, documents, selected, {**identity, "generated": utc_now()})
        validate_run(run, sources, identity)
        tables = make_tables(run)
        write_results(output, run, tables)
    except (OSError, ValueError, UnicodeError, CFG.ConfigError) as error:
        print(f"calibration: {error}", file=sys.stderr)
        return 2
    print(f"Wrote complete calibration to {output}. Review bands before copying them to "
          f"{CFG.personal_path().parent / 'bands'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
