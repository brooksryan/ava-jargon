#!/usr/bin/env python3
"""voice-agents CLI - compare and score corpuses against different metrics.

Corpus dirs hold one .txt per document. Current metric groups:

  jargon   corpus-relative jargon (keyness lexicon: build / score / delta)
  check    mechanical rule checkers for the v2 gates (see app/checks/README.md)

Planned: cpidr, surface stats (word/sentence/paragraph) - the audit scripts in
app/scripts/ are the basis and will fold in here.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    from . import jargon as J  # installed package layout
except ImportError:  # flat script layout via the ./ava wrapper
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import jargon as J


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
    lex = J.load_lexicon(args.lexicon)
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
    lex = J.load_lexicon(args.lexicon)
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

    surface = args.surface or B.RULES_TO_SURFACE.get(args.rules)

    if lexicon is None and surface:
        here = Path(__file__).resolve().parent
        name = f"universal-{surface}.json"
        # The workspace copy wins over the packaged copy.
        for auto in (here.parent / "lexicons" / name, here / "lexicons" / name):
            if auto.is_file():
                lexicon = J.load_lexicon(str(auto))
                print(f"lexicon: universal-{surface} (auto; --lexicon overrides)",
                      file=sys.stderr)
                break

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

    # W-M10 is advisory (see CHECKS.md): its density prints as a summary line
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
    band_lines, band_data = B.summarize(findings, words, surface, rules_checked)

    if args.json:
        doc = C.report_json([n for n, _ in documents], args.rules,
                            tiers, skipped, findings, len(checkers))
        doc["bands"] = band_data
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

    s = jsub.add_parser("score", help="score a file or corpus dir against a lexicon")
    s.add_argument("target", help="a .txt file or a corpus dir")
    s.add_argument("-l", "--lexicon", required=True)
    s.add_argument("--top", type=int, default=20, help="rows shown for dir scoring")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_jargon_score)

    d = jsub.add_parser("delta", help="A vs B density with bootstrap CI")
    d.add_argument("a", help="file or dir A")
    d.add_argument("b", help="file or dir B")
    d.add_argument("-l", "--lexicon", required=True)
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
    ck.add_argument("--field", action="append", metavar="NAME=VALUE",
                    help="an input-contract field; enables P-M5, repeatable")
    ck.add_argument("-o", "--out", help="write the report to this file")
    ck.set_defaults(fn=cmd_check)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
