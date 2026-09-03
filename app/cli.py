#!/usr/bin/env python3
"""voice-agents CLI - compare and score corpuses against different metrics.

Corpus dirs hold one .txt per document. Current metric groups:

  jargon   corpus-relative jargon (keyness lexicon: build / score / delta;
           extend = one more approved corpus, applied with --extend at check time)
  check    mechanical rule checkers for the v2 gates (see app/checks/README.md)
  voice    a named voice: surface + extensions for the check, and a rubric a
           reviewer scores (new / list / rubric / set / rm / schema)

Planned: cpidr, surface stats (word/sentence/paragraph) - the audit scripts in
app/scripts/ are the basis and will fold in here.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from . import jargon as J  # installed package layout
    from . import voices as V
except ImportError:  # flat script layout via the ./ava wrapper
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import jargon as J
    import voices as V


def cmd_jargon_build(args):
    stop = J.load_stoplist(args.stoplist)
    lex = J.build(args.approved, args.contrast,
                  min_contrast_count=args.min_contrast_count,
                  ll_threshold=args.ll, lr_threshold=args.lr,
                  min_contrast_dispersion=args.min_contrast_dispersion,
                  max_approved_dispersion=args.max_approved_dispersion,
                  zipf_gate=args.zipf_gate,
                  min_approved_count=args.min_approved_count,
                  stoplist=stop)
    lex["meta"]["params"]["stoplist"] = {"path": args.stoplist, "terms": len(stop)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lex, indent=1))
    m = lex["meta"]
    auto = m["params"].get("dispersion_auto") or {}
    for side, info in auto.items():
        print(f"auto dispersion ({side}): median doc {info['median_doc_tokens']} tokens "
              f"-> {info['value']}")
    print(f"approved: {m['approved_docs']} docs, {m['approved_tokens']:,} tokens "
          f"({args.approved})")
    print(f"contrast: {m['contrast_docs']} docs, {m['contrast_tokens']:,} tokens "
          f"({args.contrast})")
    if m["approved_tokens"] < 30000 or m["contrast_tokens"] < 30000:
        print("warning: under the ~30k-token floor per side - keyness will be noisy; "
              "consider raising --ll")
    if not J.HAVE_WORDFREQ:
        print("warning: wordfreq not installed - Zipf gate disabled "
              "(ordinary English words may be flagged)")
    print(f"jargon terms: {len(lex['jargon'])}   "
          f"approved vocabulary: {len(lex['approved_vocabulary'])}")
    print(f"lexicon written to {out}")
    for t, s in list(lex["jargon"].items())[:15]:
        print(f"  {t:<28} G2={s['log_likelihood']:>8}  LR={s['log_ratio']:>5}  "
              f"contrast_docs={s['contrast_doc_share']:.0%}")


def cmd_jargon_score(args):
    lex, _ = _apply_extensions(J.load_lexicon(args.lexicon), args.extend)
    target = Path(args.target)
    if target.is_dir():
        res = J.score_dir(target, lex)
        if args.json:
            print(json.dumps(res, indent=1))
            return
        print(f"{res['dir']}: {res['docs']} docs, {res['tokens']:,} tokens")
        print(f"jargon density: {res['jargon_density_per_1k']} per 1,000 tokens   "
              f"approved coverage: {res['approved_coverage']:.0%}   "
              f"docs with jargon: {res['docs_with_jargon']}/{res['docs']}")
        if res["top_flagged"]:
            print("top flagged terms across corpus:")
            for t, c in res["top_flagged"]:
                print(f"  {t:<28} x{c}")
        print(f"{'file':<52} {'tokens':>6} {'dens/1k':>8} {'coverage':>8}  top terms")
        for r in res["files"][:args.top]:
            terms = ", ".join(r["top_terms"])
            print(f"{r['file'][:52]:<52} {r['tokens']:>6} "
                  f"{r['jargon_density_per_1k']:>8} {r['approved_coverage']:>8.0%}  {terms}")
        if len(res["files"]) > args.top:
            print(f"... {len(res['files']) - args.top} more files (use --top N or --json)")
    else:
        res = J.score_file(target, lex)
        if args.json:
            print(json.dumps(res, indent=1))
            return
        print(f"tokens: {res['tokens']}")
        print(f"jargon density: {res['jargon_density_per_1k']} per 1,000 tokens")
        print(f"approved coverage: {res['approved_coverage']:.0%} of content words")
        if res["flagged"]:
            print("flagged terms:")
            for t, s in res["flagged"].items():
                print(f"  {t:<28} x{s['count']}  (approved corpus used it "
                      f"{s['approved_count']} times)")
        for row in res["sentences_with_jargon"]:
            print(f"  -> {row['terms']}: \"{row['sentence']}\"")


def cmd_jargon_delta(args):
    lex, _ = _apply_extensions(J.load_lexicon(args.lexicon), args.extend)
    res = J.delta(args.a, args.b, lex, n_boot=args.boot)
    if args.json:
        print(json.dumps(res, indent=1))
        return
    print(f"A: {res['a']['path']}  ({res['a']['units']} {res['unit']})  "
          f"density {res['a']['density']} /1k")
    print(f"B: {res['b']['path']}  ({res['b']['units']} {res['unit']})  "
          f"density {res['b']['density']} /1k")
    print(f"delta (A - B): {res['delta']:+.2f} per 1,000 tokens, "
          f"95% bootstrap CI [{res['ci95'][0]:+.2f}, {res['ci95'][1]:+.2f}]")
    print("CI excludes zero: " + ("YES, difference is credible" if res["credible"]
                                  else "NO, treat as noise"))


# --- extensions: one more approved corpus, kept as a vocabulary profile -----

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
RECORD_SUFFIXES = (".json", ".jsonl")
_FENCE_RE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.M | re.S)
_INLINE_RE = re.compile(r"`[^`\n]+`")


def _extension_root():
    return Path(os.environ.get("AVA_HOME") or Path.home() / ".ava") / "extensions"


def _extension_names():
    root = _extension_root()
    return sorted(p.stem for p in root.glob("*.json")) if root.is_dir() else []


def _resolve_extension(spec):
    """An extension is a file path or a name under $AVA_HOME/extensions."""
    p = Path(spec).expanduser()
    if p.is_file():
        return p
    candidate = _extension_root() / f"{spec}.json"
    return candidate if candidate.is_file() else None


def _apply_extensions(lexicon, specs):
    """Overlay each --extend on the lexicon. Returns (lexicon, labels)."""
    labels = []
    for spec in specs or []:
        path = _resolve_extension(spec)
        if path is None:
            known = ", ".join(_extension_names()) or "none"
            print(f"error: no such extension: {spec} (known: {known}; "
                  "build one with ava jargon extend)", file=sys.stderr)
            sys.exit(2)
        lexicon = J.extend(lexicon, J.load_extension(path), name=path.stem)
        info = lexicon["meta"]["extensions"][-1]
        labels.append(f"{path.stem} ({len(info['vetoed'])} vetoed, "
                      f"{info['added']} added)")
    if labels:
        print("extend: " + ", ".join(labels), file=sys.stderr)
    return lexicon, labels


def _records(obj, field):
    """Yield the string under `field` from every object in a JSON document."""
    if isinstance(obj, list):
        for item in obj:
            yield from _records(item, field)
    elif isinstance(obj, dict):
        value = obj.get(field)
        if isinstance(value, str):
            yield value
        else:
            for v in obj.values():
                if isinstance(v, (list, dict)):
                    yield from _records(v, field)


def _record_texts(path, field):
    text = path.read_text(errors="ignore")
    chunks = text.splitlines() if path.suffix.lower() == ".jsonl" else [text]
    out = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            out += list(_records(json.loads(chunk), field))
        except ValueError:
            continue
    return out


def _split_text(text, mode):
    if mode == "blank":
        parts = re.split(r"\n\s*\n", text)
    elif mode == "line":
        parts = text.splitlines()
    else:
        parts = [text]
    return [p for p in parts if p.strip()]


def _extension_documents(paths, split, field, keep_code):
    """Return ([(name, tokens)], errors) for the sources of an extension."""
    documents, errors = [], []
    for entry in paths:
        if entry == "-":
            for i, piece in enumerate(_split_text(sys.stdin.read(), split)):
                documents.append((f"<stdin>#{i}", J.tokenize(piece)))
            continue
        target = Path(entry).expanduser()
        if target.is_dir():
            files = sorted(p for p in target.glob("**/*") if p.is_file()
                           and p.suffix.lower() in DOC_SUFFIXES + RECORD_SUFFIXES)
            if not files:
                errors.append(f"no .txt, .md, .json, or .jsonl file under {entry}")
        elif target.is_file():
            files = [target]
        else:
            errors.append(f"no such file or directory: {entry}")
            continue
        for path in files:
            if path.suffix.lower() in RECORD_SUFFIXES:
                for i, text in enumerate(_record_texts(path, field)):
                    documents.append((f"{path}#{i}", J.tokenize(text)))
                continue
            text = path.read_text(errors="ignore")
            if path.suffix.lower() == ".md" and not keep_code:
                text = _INLINE_RE.sub(" ", _FENCE_RE.sub(" ", text))
            for i, piece in enumerate(_split_text(text, split)):
                documents.append((f"{path}#{i}", J.tokenize(piece)))
    return documents, errors


def cmd_jargon_extend(args):
    """Profile one more approved corpus into $AVA_HOME/extensions/NAME.json."""
    if not NAME_RE.match(args.name):
        print(f"error: bad name {args.name!r}: lowercase letters, digits, '.', "
              "'_', '-'", file=sys.stderr)
        return 2
    documents, errors = _extension_documents(args.paths, args.split, args.field,
                                             args.keep_code)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    if errors:
        return 2
    kept = [(n, t) for n, t in documents if len(t) >= 3]
    if not kept:
        print("error: no documents found (check --split and --field)",
              file=sys.stderr)
        return 2
    ext = J.profile(kept)
    m = ext["meta"]
    m.update({"name": args.name, "sources": args.paths, "built": J.today(),
              "options": {"split": args.split, "field": args.field,
                          "keep_code": args.keep_code},
              "note": args.note})
    out = _extension_root() / f"{args.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ext, indent=1))
    dropped = len(documents) - len(kept)
    print(f"{args.name}: {m['docs']} docs, {m['tokens']:,} tokens, median doc "
          f"{m['median_doc_tokens']} tokens"
          + (f" ({dropped} docs under 3 tokens dropped)" if dropped else ""))
    print(f"vocabulary: {len(ext['vocabulary']):,} terms (count >= 3 in >= 2 docs); "
          f"a term vetoes jargon above {m['max_approved_dispersion']:.1%} of docs")
    if m["tokens"] < 30000:
        print("warning: under the ~30k-token floor - the veto will miss terms the "
              "audience does use")
    for surface in ("chat", "doc-shared", "doc-technical", "code"):
        path = _universal_lexicon(surface)
        if path is None:
            continue
        lex = J.load_lexicon(str(path))
        info = J.extend(lex, ext)["meta"]["extensions"][-1]
        top = ", ".join(info["vetoed"][:8])
        print(f"  universal-{surface:<14} vetoes {len(info['vetoed']):>3} of "
              f"{len(lex['jargon']):>3} jargon terms" + (f": {top}" if top else ""))
    print(f"extension written to {out}")
    print(f"use it: ava check FILE --rules technical --extend {args.name}")
    return 0


def cmd_jargon_extensions(args):
    """List the extensions on this machine, one row each."""
    root = _extension_root()
    names = _extension_names()
    if not names:
        print(f"no extensions in {root} (build one: ava jargon extend NAME PATH...)",
              file=sys.stderr)
        return 0
    print(f"{'extension':<24} {'docs':>6} {'tokens':>9} {'terms':>6}  note")
    for name in names:
        ext = J.load_extension(root / f"{name}.json")
        m = ext["meta"]
        print(f"{name:<24} {m['docs']:>6} {m['tokens']:>9,} "
              f"{len(ext['vocabulary']):>6}  {m.get('note') or ''}")
    return 0


DOC_SUFFIXES = (".md", ".txt")


def _read_stdin():
    return [("<stdin>", sys.stdin.read())]


def _collect(paths):
    """Return (documents, errors). A document is one (name, text) pair."""
    documents, errors = [], []
    if not paths:
        return _read_stdin(), errors
    for entry in paths:
        if entry == "-":
            documents += _read_stdin()
            continue
        target = Path(entry)
        if target.is_dir():
            found = sorted(p for p in target.glob("**/*")
                           if p.is_file() and p.suffix in DOC_SUFFIXES)
            if not found:
                errors.append(f"no .md or .txt file under {entry}")
            documents += [(str(p), p.read_text(errors="ignore")) for p in found]
        elif target.is_file():
            documents.append((str(target), target.read_text(errors="ignore")))
        else:
            errors.append(f"no such file or directory: {entry}")
    return documents, errors


def _import_checks():
    try:
        from . import checks as C
        from .checks import bands as B
    except ImportError:
        import checks as C
        from checks import bands as B
    return C, B


def _universal_lexicon(surface):
    """Path of the universal lexicon for a surface: workspace copy, then packaged."""
    here = Path(__file__).resolve().parent
    name = f"universal-{surface}.json"
    for auto in (here.parent / "lexicons" / name, here / "lexicons" / name):
        if auto.is_file():
            return auto
    return None


def cmd_check(args):
    """Run the mechanical checkers. Findings go to stdout, notes to stderr."""
    C, B = _import_checks()

    documents, errors = _collect(args.paths)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    if errors:
        return 2

    lexicon = None
    if args.lexicon:
        if not Path(args.lexicon).is_file():
            print(f"error: no such lexicon: {args.lexicon}", file=sys.stderr)
            return 2
        lexicon = J.load_lexicon(args.lexicon)
    fields = None
    if args.field:
        fields = {}
        for pair in args.field:
            name, _, value = pair.partition("=")
            fields[name.strip()] = value

    voice = None
    if args.voice:
        try:
            path, scope = V.resolve(args.voice)
            voice = V.load(path)
        except V.VoiceError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        # The voice fills what the flags left out; an explicit flag wins.
        args.surface = args.surface or voice["surface"]
        args.extend = list(args.extend or []) + [
            e for e in voice.get("extend", []) if e not in (args.extend or [])]
        print(f"voice: {voice['name']} ({scope})", file=sys.stderr)

    surface = args.surface or B.RULES_TO_SURFACE.get(args.rules)

    if lexicon is None and surface:
        auto = _universal_lexicon(surface)
        if auto is not None:
            lexicon = J.load_lexicon(str(auto))
            print(f"lexicon: universal-{surface} (auto; --lexicon overrides)",
                  file=sys.stderr)
    if args.extend:
        if lexicon is None:
            print("error: --extend needs a lexicon: pass --surface or --lexicon",
                  file=sys.stderr)
            return 2
        lexicon, _ = _apply_extensions(lexicon, args.extend)

    ctx = C.Context(lexicon=lexicon, fields=fields)
    checkers, tiers, skipped, warning = C.select(args.rules, ctx,
                                                 use_parser=not args.no_parser)
    if warning:
        print(f"warning: {warning}, so the run holds tier 1 only", file=sys.stderr)

    findings = []
    words = 0
    for name, text in documents:
        ctx.path = name
        words += len(J.tokenize(text))
        findings += C.check_document(text, ctx, checkers)
    findings = C.sort_findings(findings)

    for note in ctx.notes:
        print(f"note: {note}", file=sys.stderr)
    for rule in skipped:
        print(f"skipped: {rule}", file=sys.stderr)

    # W-M10 is advisory (see checks/CHECKS.md): its density prints as a summary line
    # and never joins the findings or the exit code.
    w10 = [f for f in findings if f.rule == "W-M10"]
    findings = [f for f in findings if f.rule != "W-M10"]
    if w10:
        hits = []
        for f in w10:
            m = re.search(r"x(\d+)$", f.label)
            hits.append((int(m.group(1)) if m else 1, f.match))
        total = sum(n for n, _ in hits)
        top = ", ".join(f"{t}×{n}" for n, t in sorted(hits, reverse=True)[:5])
        print(f"jargon (W-M10, advisory): {round(1000 * total / max(words, 1), 1)}"
              f"/1k over {words:,} words · top: {top}", file=sys.stderr)

    rules_checked = [m.RULE for m in checkers]
    verdict = (f"checked {len(checkers)} rules over {words:,} words: "
               f"{len(findings)} findings")
    if skipped:
        verdict += f" ({len(skipped)} skipped: {', '.join(skipped)})"
    print(verdict, file=sys.stderr)
    color = (sys.stderr.isatty() and "NO_COLOR" not in os.environ
             and os.environ.get("TERM") != "dumb")
    band_lines, band_data = B.summarize(findings, words, surface, rules_checked,
                                        color=color)

    if args.json:
        doc = C.report_json([n for n, _ in documents], args.rules,
                            tiers, skipped, findings, len(checkers))
        doc["bands"] = band_data
        if voice:
            doc["voice"] = {"name": voice["name"], "scope": scope, "path": str(path)}
        report = json.dumps(doc, indent=1)
    else:
        report = C.report_text(findings)
    if args.out:
        Path(args.out).write_text(report + ("\n" if report else ""))
    elif report:
        print(report)
    if not args.json:
        for line in band_lines:
            print(line, file=sys.stderr)
    return 1 if findings else 0


# --- voices: a named surface + extensions + rubric ---------------------------

def _read_json_doc(spec):
    """A JSON document from a path or stdin (- or empty)."""
    text = sys.stdin.read() if spec in (None, "-") else Path(spec).read_text()
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise V.VoiceError(f"not JSON: {e.msg} at line {e.lineno}")
    if not isinstance(doc, dict):
        raise V.VoiceError("the document must be a JSON object")
    return doc


def _voice_scope(args):
    return "project" if getattr(args, "project", False) else "personal"


def cmd_voice_new(args):
    """Create $AVA_HOME/voices/NAME.json (or .ava/voices/NAME.json with --project)."""
    if not V.NAME_RE.match(args.name):
        print(f"error: bad voice name: {args.name} (lowercase, digits, . _ -)",
              file=sys.stderr)
        return 2
    try:
        doc = _read_json_doc(args.file)
        doc.setdefault("name", args.name)
        if doc["name"] != args.name:
            raise V.VoiceError(f"the document names the voice {doc['name']!r}, "
                               f"the command names it {args.name!r}")
        dst = V.root_for(_voice_scope(args)) / f"{args.name}.json"
        if dst.exists() and not args.force:
            raise V.VoiceError(f"{dst} exists (--force overwrites, "
                               "ava voice set edits)")
        V.save(dst, doc)
    except (V.VoiceError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(dst)


def cmd_voice_list(args):
    """One row per voice on this machine."""
    rows = V.catalog()
    if not rows:
        print(f"no voices in {V.personal_root()} or {V.project_root()} "
              "(create one: ava voice new NAME FILE)", file=sys.stderr)
        return 0
    width = max(len(n) for n, _, _ in rows)
    seen = set()
    for name, scope, path in rows:
        try:
            doc = V.load(path)
            detail = f"{doc['surface']:<13} {len(doc['rules'])} rules"
        except V.VoiceError:
            detail = "INVALID (ava voice rubric NAME shows why)"
        if name in seen:  # a personal voice a project voice of the same name hides
            detail += "  (shadowed)"
        seen.add(name)
        print(f"{name:<{width}}  {scope:<8}  {detail}  {path}")


def cmd_voice_rubric(args):
    """Print the rubric a reviewer reads; --json prints the document."""
    try:
        path, scope = V.resolve(args.name)
        doc = V.load(path)
    except V.VoiceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    else:
        print(V.rubric(doc, scope))


def cmd_voice_set(args):
    """Merge a partial document into the voice and re-validate."""
    try:
        path, _ = V.resolve(args.name)
        base = V.load(path)
        patch = _read_json_doc(args.file)
        if patch.get("name", args.name) != args.name:
            raise V.VoiceError("a voice cannot change its name; "
                               "create a new one")
        V.save(path, V.merge(base, patch))
    except (V.VoiceError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(path)


def cmd_voice_rm(args):
    """Delete the voice the name resolves to."""
    try:
        path, scope = V.resolve(args.name)
    except V.VoiceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    path.unlink()
    print(f"removed {path} ({scope})")


def cmd_voice_schema(args):
    """Print the schema so an agent knows the shape before it writes."""
    sys.stdout.write(V.SCHEMA_PATH.read_text())


GATE_AGENT_FILES = ("ava-prose-gate.md", "ava-technical-gate.md")


def _asset_root():
    return Path(__file__).resolve().parent / "assets"


def _split_front_matter(text):
    """Return (meta, body) for a markdown file with a simple YAML header."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, text
    meta = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, "\n".join(lines[end + 1:]).lstrip("\n")


def _yaml_quote(value):
    """Single-quote a scalar: the descriptions hold ": " and "|"."""
    return "'" + value.replace("'", "''") + "'"


def _cursor_front_matter(meta):
    return ("---\n"
            f"name: {meta['name']}\n"
            f"description: {_yaml_quote(meta['description'])}\n"
            "---\n\n")


def _opencode_front_matter(meta):
    return ("---\n"
            f"description: {_yaml_quote(meta['description'])}\n"
            "mode: subagent\n"
            "---\n\n")


def cmd_setup(args):
    """Copy the gate files out of the package into a harness's directories."""
    assets = _asset_root()
    if not assets.is_dir():
        print(f"error: package assets not found at {assets}", file=sys.stderr)
        return 2

    if args.harness == "agents-md":
        if args.global_install:
            print("error: agents-md prints to stdout; redirect it where your "
                  "harness reads instructions", file=sys.stderr)
            return 2
        sys.stdout.write((assets / "gate-contract.md").read_text())
        return 0

    base = Path.home() if args.global_install else Path(".")
    writes = []

    skills_src = assets / "skills"
    skills_dst = base / ".agents" / "skills"
    # One skill per directory. In the repo layout each is a symlink, and
    # rglob does not descend into a symlinked directory, so walk each one.
    for skill in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        for src in sorted(skill.rglob("*")):
            if src.is_file():
                writes.append((skills_dst / skill.name / src.relative_to(skill),
                               src.read_text()))

    if args.harness == "cursor":
        agents_dst = base / ".cursor" / "agents"
        front = _cursor_front_matter
    elif args.harness == "opencode":
        agents_dst = (Path.home() / ".config" / "opencode" / "agents"
                      if args.global_install else Path(".opencode") / "agents")
        front = _opencode_front_matter
    else:  # codex and the generic skills target ship the skill only
        agents_dst = front = None

    if agents_dst is not None:
        for name in GATE_AGENT_FILES:
            meta, body = _split_front_matter((assets / "agents" / name).read_text())
            writes.append((agents_dst / name, front(meta) + body))

    conflicts = [dst for dst, _ in writes if dst.exists()]
    if conflicts and not args.force:
        for dst in conflicts:
            print(f"error: {dst} exists (--force overwrites)", file=sys.stderr)
        return 2

    for dst, content in writes:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content)
        print(dst)

    if args.harness == "codex":
        target = "~/.codex/AGENTS.md" if args.global_install else "AGENTS.md"
        print(f"codex has no subagents; append the gate contract with: "
              f"ava setup agents-md >> {target}", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser(prog="ava", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    jg = sub.add_parser("jargon", help="corpus-relative jargon scoring")
    jsub = jg.add_subparsers(dest="jcmd", required=True)

    b = jsub.add_parser("build", help="build a lexicon from two corpus dirs")
    b.add_argument("approved",
                   help="dir(s) of the audience's own words, comma-separated")
    b.add_argument("contrast",
                   help="dir(s) of the writing under suspicion, comma-separated")
    b.add_argument("-o", "--out", default="lexicons/lexicon.json")
    b.add_argument("--min-contrast-count", type=int, default=5)
    b.add_argument("--min-approved-count", type=int, default=3)
    b.add_argument("--ll", type=float, default=15.13,
                   help="Dunning G2 threshold (default 15.13, p<.0001)")
    b.add_argument("--lr", type=float, default=2.0,
                   help="Hardie log-ratio threshold (default 2.0 = 4x rate)")
    b.add_argument("--min-contrast-dispersion", type=float, default=None,
                   help="doc-share floor for jargon terms (default: auto-scaled "
                        "by contrast median doc length, 0.10 x L/250 in [0.015, 0.10])")
    b.add_argument("--max-approved-dispersion", type=float, default=None,
                   help="doc-share ceiling for 'the audience says it too' (default: "
                        "auto-scaled by approved median doc length, 0.05 x L/250 "
                        "in [0.01, 0.05])")
    b.add_argument("--zipf-gate", type=float, default=5.0,
                   help="skip unigrams at/above this general-English Zipf frequency")
    b.add_argument("--stoplist",
                   default=str(Path(__file__).resolve().parent / "name_stoplist.txt"),
                   help="terms never flagged as jargon (default: app/name_stoplist.txt; "
                        "pass an empty string to disable)")
    b.set_defaults(fn=cmd_jargon_build)

    x = jsub.add_parser("extend",
                        help="profile one more approved corpus; apply it with "
                             "--extend at check time")
    x.add_argument("name", help="extension name (lowercase, digits, . _ -)")
    x.add_argument("paths", nargs="+",
                   help="files, directories, or - for stdin: .txt and .md are "
                        "one document each; .json and .jsonl one per record")
    x.add_argument("--split", choices=("none", "blank", "line"), default="none",
                   help="none: one file = one document; blank: a blank line "
                        "starts a new document; line: one line = one document")
    x.add_argument("--field", default="text",
                   help="the string field that holds one document in a .json "
                        "or .jsonl record (default: text)")
    x.add_argument("--keep-code", action="store_true",
                   help="keep fenced code and inline code in .md files")
    x.add_argument("--note", help="source note kept in the extension file")
    x.set_defaults(fn=cmd_jargon_extend)
    xl = jsub.add_parser("extensions", help="list the extensions on this machine")
    xl.set_defaults(fn=cmd_jargon_extensions)

    s = jsub.add_parser("score", help="score a file or corpus dir against a lexicon")
    s.add_argument("target", help="a .txt file or a corpus dir")
    s.add_argument("-l", "--lexicon", required=True)
    s.add_argument("--extend", action="append", metavar="NAME",
                   help="extension name or path to overlay, repeatable")
    s.add_argument("--top", type=int, default=20, help="rows shown for dir scoring")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_jargon_score)

    d = jsub.add_parser("delta", help="A vs B density with bootstrap CI")
    d.add_argument("a", help="file or dir A")
    d.add_argument("b", help="file or dir B")
    d.add_argument("-l", "--lexicon", required=True)
    d.add_argument("--extend", action="append", metavar="NAME",
                   help="extension name or path to overlay, repeatable")
    d.add_argument("--boot", type=int, default=2000)
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_jargon_delta)

    ck = sub.add_parser("check", help="mechanical rule checkers for the v2 gates")
    ck.add_argument("paths", nargs="*",
                    help="files, directories, or - for stdin (default: stdin)")
    C, _ = _import_checks()
    rule_sets = ("westinghouse", "technical")
    if C.p_m1_short_names is not None:  # the personal subpackage is installed
        rule_sets += ("personal",)
    ck.add_argument("--rules", default="westinghouse", choices=rule_sets,
                    help="rule set; the non-westinghouse sets include the "
                         "Westinghouse rules (default: westinghouse)")
    ck.add_argument("--surface", choices=("chat", "doc-shared",
                                          "doc-technical", "code"),
                    help="band surface for the rate summary (default: inferred "
                         "from --rules: personal=chat, technical=doc-technical; "
                         "westinghouse has no default)")
    ck.add_argument("--json", action="store_true",
                    help="print one JSON object instead of one line per finding")
    ck.add_argument("--parser", action="store_true",
                    help="kept for compatibility: the tier 2 checkers now run "
                         "whenever spacy is installed")
    ck.add_argument("--no-parser", action="store_true",
                    help="skip the tier 2 checkers even when spacy is installed")
    ck.add_argument("--lexicon", help="jargon lexicon path; enables W-M10")
    ck.add_argument("--extend", action="append", metavar="NAME",
                    help="overlay an extension (ava jargon extend) on the "
                         "lexicon: its audience's terms join the approved "
                         "side; repeatable")
    ck.add_argument("--field", action="append", metavar="NAME=VALUE",
                    help="an input-contract field; enables P-M5, repeatable")
    ck.add_argument("--voice", metavar="NAME",
                    help="run under a voice (ava voice list): its surface and "
                         "extensions apply where the flags left them out")
    ck.add_argument("-o", "--out", help="write the report to this file")
    ck.set_defaults(fn=cmd_check)

    vc = sub.add_parser("voice", help="a named voice: surface, extensions, "
                                      "and a rubric a reviewer scores")
    vsub = vc.add_subparsers(dest="vcmd", required=True)

    vn = vsub.add_parser("new", help="create a voice from a JSON document")
    vn.add_argument("name", help="voice name (lowercase, digits, . _ -)")
    vn.add_argument("file", nargs="?", default="-",
                    help="JSON document, or - for stdin (default: stdin); "
                         "ava voice schema prints the shape")
    vn.add_argument("--project", action="store_true",
                    help="write to .ava/voices/ in the project instead of "
                         "$AVA_HOME/voices/")
    vn.add_argument("--force", action="store_true",
                    help="overwrite a voice that already exists")
    vn.set_defaults(fn=cmd_voice_new)

    vl = vsub.add_parser("list", help="list the voices on this machine")
    vl.set_defaults(fn=cmd_voice_list)

    vr = vsub.add_parser("rubric", help="print a voice's rubric")
    vr.add_argument("name", help="voice name or path")
    vr.add_argument("--json", action="store_true",
                    help="print the JSON document instead of the rubric")
    vr.set_defaults(fn=cmd_voice_rubric)

    vs = vsub.add_parser("set", help="merge a partial JSON document into a voice")
    vs.add_argument("name", help="voice name or path")
    vs.add_argument("file", nargs="?", default="-",
                    help="partial JSON document, or - for stdin; rules merge "
                         "by name, other fields replace")
    vs.set_defaults(fn=cmd_voice_set)

    vd = vsub.add_parser("rm", help="delete a voice")
    vd.add_argument("name", help="voice name or path")
    vd.set_defaults(fn=cmd_voice_rm)

    vh = vsub.add_parser("schema", help="print the voice JSON schema")
    vh.set_defaults(fn=cmd_voice_schema)

    st = sub.add_parser("setup", help="install the gate files for a harness")
    st.add_argument("harness",
                    choices=("cursor", "opencode", "codex", "skills", "agents-md"),
                    help="cursor/opencode: skill + gate agents; codex/skills: "
                         "skill only; agents-md: print the AGENTS.md gate "
                         "contract to stdout")
    st.add_argument("-g", "--global", dest="global_install", action="store_true",
                    help="install to user space instead of the current project")
    st.add_argument("--force", action="store_true",
                    help="overwrite files that already exist")
    st.set_defaults(fn=cmd_setup)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
