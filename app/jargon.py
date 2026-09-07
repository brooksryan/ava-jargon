"""Corpus-relative jargon scoring engine.

Generic two-corpus keyness: build a lexicon from any APPROVED dir (the audience's
own words) vs any CONTRAST dir (the writing under suspicion), then score any file
or dir against it. Method per tmp/customer_vs_internal_corpus_README.md:
Dunning log-likelihood (G2) for significance, Hardie log ratio for effect size,
document dispersion on both sides, optional wordfreq Zipf gate for ordinary English.

A corpus dir holds one .txt per document (searched recursively). Many small
documents beat a few big ones — dispersion counts documents.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from wordfreq import zipf_frequency
    HAVE_WORDFREQ = True
except ImportError:
    HAVE_WORDFREQ = False

try:
    from .resources import FIXTURES
except ImportError:
    from resources import FIXTURES

TOKEN_RE = re.compile(r"[a-z][a-z0-9'\-]+")
EMOJI_SHORTCODE_RE = re.compile(r":[a-z0-9_+'\-]+:")

STOPWORDS = set("""a an and are as at be but by for from has have i if in into is it its
me my no not of on or our ours so that the their them they this to was we were what when
which who will with you your yours he she his her had do does did been than then there
these those can could would should may might must shall about above after again all am
any because before below between both down during each few further here how just more
most only other out over own same some such too under until up very while""".split())


def tokenize(text):
    return TOKEN_RE.findall(EMOJI_SHORTCODE_RE.sub(" ", text.lower()))


def ngrams(tokens, n_max=3):
    """Content unigrams plus bigrams/trigrams that don't start or end on a stopword."""
    out = [t for t in tokens if t not in STOPWORDS]
    for n in (2, 3):
        if n > n_max:
            break
        for i in range(len(tokens) - n + 1):
            gram = tokens[i:i + n]
            if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                continue
            out.append(" ".join(gram))
    return out


def load_corpus(path):
    """Load one corpus. `path` may be several dirs joined with commas."""
    docs = []
    parts = [q for q in str(path).split(",") if q]
    for part in parts:
        base = Path(part)
        for p in sorted(base.glob("**/*.txt")):
            text = p.read_text(errors="ignore")
            if text.strip():
                rel = str(p.relative_to(base))
                name = f"{base.name}/{rel}" if len(parts) > 1 else rel
                docs.append((name, tokenize(text)))
    if not docs:
        sys.exit(f"No .txt documents found in {path}")
    return docs


def log_likelihood(o1, n1, o2, n2):
    """Dunning G2 for a term with count o1 in corpus of size n1 vs o2 in n2."""
    e1 = n1 * (o1 + o2) / (n1 + n2)
    e2 = n2 * (o1 + o2) / (n1 + n2)
    ll = 0.0
    if o1 > 0:
        ll += o1 * math.log(o1 / e1)
    if o2 > 0:
        ll += o2 * math.log(o2 / e2)
    return 2 * ll


def log_ratio(o1, n1, o2, n2):
    """Hardie log2 ratio of normalized frequencies, 0.5 floor for zero counts."""
    f1 = (o1 if o1 > 0 else 0.5) / n1
    f2 = (o2 if o2 > 0 else 0.5) / n2
    return math.log2(f1 / f2)


def _counts(docs, n_max):
    tf, df = Counter(), Counter()
    total = 0
    for _, toks in docs:
        grams = ngrams(toks, n_max)
        total += len(toks)
        tf.update(grams)
        df.update(set(grams))
    return tf, df, total


def load_stoplist(path):
    """One term per line, # comments allowed. Returns a lowercase set."""
    if not path or not Path(path).is_file():
        return set()
    out = set()
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            out.add(line)
    return out


def _median_doc_len(docs):
    lens = sorted(len(toks) for _, toks in docs)
    return lens[len(lens) // 2] if lens else 0


def auto_dispersion(docs, base, ref_len, lo, hi, min_docs):
    """Scale a doc-share threshold by median doc length; never below min_docs docs."""
    L = _median_doc_len(docs)
    p = max(lo, min(hi, base * L / ref_len))
    p = max(p, min_docs / max(len(docs), 1))
    return round(p, 4), L


def build(approved_dir, contrast_dir,
          min_contrast_count=5, ll_threshold=15.13, lr_threshold=2.0,
          min_contrast_dispersion=None, max_approved_dispersion=None,
          zipf_gate=5.0, min_approved_count=3, n_max=3, stoplist=None,
          stoplist_path=None):
    """Return a lexicon dict: jargon terms overused in CONTRAST, vocabulary of APPROVED.

    Dispersion thresholds default to None = auto-scaled by the side's median
    document length (base x L/250, clamped), so message corpora and article
    corpora get equivalent per-token bars. Explicit values always win.
    """
    stoplist = stoplist or set()
    a_docs = load_corpus(approved_dir)
    c_docs = load_corpus(contrast_dir)

    dispersion_auto = {}
    if min_contrast_dispersion is None:
        min_contrast_dispersion, L = auto_dispersion(
            c_docs, base=0.10, ref_len=250, lo=0.015, hi=0.10, min_docs=8)
        dispersion_auto["contrast"] = {"median_doc_tokens": L,
                                       "value": min_contrast_dispersion}
    if max_approved_dispersion is None:
        max_approved_dispersion, L = auto_dispersion(
            a_docs, base=0.05, ref_len=250, lo=0.01, hi=0.05, min_docs=3)
        dispersion_auto["approved"] = {"median_doc_tokens": L,
                                       "value": max_approved_dispersion}

    a_tf, a_df, a_n = _counts(a_docs, n_max)
    c_tf, c_df, c_n = _counts(c_docs, n_max)
    n_ad, n_cd = len(a_docs), len(c_docs)

    approved = {t: {"approved_count": c, "approved_doc_share": round(a_df[t] / n_ad, 4)}
                for t, c in a_tf.items()
                if c >= min_approved_count and a_df[t] >= 2}
    _approve_stoplist_names(approved, stoplist, a_tf, a_df, n_ad)

    jargon = {}
    for t, o_c in c_tf.items():
        if o_c < min_contrast_count:
            continue
        if t in stoplist or any(w in stoplist for w in t.split()):
            continue
        o_a = a_tf.get(t, 0)
        disp_c = c_df[t] / n_cd
        disp_a = a_df.get(t, 0) / n_ad
        if disp_c < min_contrast_dispersion:      # one document's tic, not shared jargon
            continue
        if disp_a > max_approved_dispersion:      # the audience says it too: not jargon
            continue
        ll = log_likelihood(o_c, c_n, o_a, a_n)
        lr = log_ratio(o_c, c_n, o_a, a_n)
        if ll < ll_threshold or lr < lr_threshold:
            continue
        z = zipf_frequency(t, "en") if (HAVE_WORDFREQ and " " not in t) else 0.0
        if HAVE_WORDFREQ and " " not in t and z >= zipf_gate:
            continue                              # ordinary English word, skip
        jargon[t] = {
            "contrast_count": o_c, "approved_count": o_a,
            "log_likelihood": round(ll, 2), "log_ratio": round(lr, 2),
            "contrast_doc_share": round(disp_c, 4),
            "approved_doc_share": round(disp_a, 4),
            "zipf_en": round(z, 2),
        }

    return {
        "meta": {
            "approved_dir": str(approved_dir), "contrast_dir": str(contrast_dir),
            "approved_docs": n_ad, "approved_tokens": a_n,
            "contrast_docs": n_cd, "contrast_tokens": c_n,
            "params": {"min_contrast_count": min_contrast_count,
                       "ll_threshold": ll_threshold, "lr_threshold": lr_threshold,
                       "min_contrast_dispersion": min_contrast_dispersion,
                       "max_approved_dispersion": max_approved_dispersion,
                       "dispersion_auto": dispersion_auto or None,
                       "zipf_gate": zipf_gate if HAVE_WORDFREQ else None,
                       "min_approved_count": min_approved_count,
                       "stoplist": {"path": stoplist_path, "terms": sorted(stoplist)}},
            "stopwords": sorted(STOPWORDS),
        },
        "jargon": dict(sorted(jargon.items(), key=lambda kv: -kv[1]["log_likelihood"])),
        "approved_vocabulary": approved,
    }


def _approve_stoplist_names(approved, stoplist, term_counts, doc_counts, n_docs):
    for name in sorted(stoplist or ()):
        approved.setdefault(name, {
            "approved_count": term_counts.get(name, 0),
            "approved_doc_share": round(doc_counts.get(name, 0) / max(n_docs, 1), 4),
            "source": "stoplist"})


DIGIT_RE = re.compile(r"\d")


def _is_code_fragment(term):
    return bool(DIGIT_RE.search(term))


def _unapproved_terms(tokens, lex):
    """The terms in neither list, as (unigram counts, bigram counts)."""
    approved = lex["approved_vocabulary"]
    jargon = lex["jargon"]
    stoplist_names = set(lex["meta"]["params"]["stoplist"]["terms"])
    zipf_gate = lex["meta"]["params"]["zipf_gate"]

    def is_ordinary_english(unigram):
        return HAVE_WORDFREQ and zipf_frequency(unigram, "en") >= zipf_gate

    def is_known(term):
        return term in approved or term in jargon

    def is_unapproved_unigram(term):
        return (not is_known(term) and not _is_code_fragment(term)
                and term not in stoplist_names and not is_ordinary_english(term))

    def is_unapproved_bigram(term):
        halves = term.split()
        return (not is_known(term)
                and not any(_is_code_fragment(h) or h in stoplist_names for h in halves))

    unigrams = Counter(t for t in tokens if t not in STOPWORDS and is_unapproved_unigram(t))
    bigrams = Counter(g for g in ngrams(tokens, 2) if " " in g and is_unapproved_bigram(g))
    return unigrams, bigrams


def score_tokens(tokens, lex, n_max=3):
    """Score one token list. Every rate is per 1,000 content words."""
    grams = ngrams(tokens, n_max)
    jargon = lex["jargon"]
    approved = lex["approved_vocabulary"]
    hits = Counter(g for g in grams if g in jargon)
    content = [t for t in tokens if t not in STOPWORDS]
    covered = sum(1 for t in content if t in approved)
    unapproved_unigrams, unapproved_bigrams = _unapproved_terms(tokens, lex)
    per_1k = 1000 / max(len(content), 1)
    return {
        "tokens": len(tokens),
        "content_words": len(content),
        "jargon_hits": sum(hits.values()),
        "jargon_density_per_1k": round(per_1k * sum(hits.values()), 2),
        "unapproved_unigram_hits": sum(unapproved_unigrams.values()),
        "unapproved_bigram_hits": sum(unapproved_bigrams.values()),
        "unapproved_unigram_density_per_1k": round(per_1k * sum(unapproved_unigrams.values()), 2),
        "unapproved_bigram_density_per_1k": round(per_1k * sum(unapproved_bigrams.values()), 2),
        "approved_coverage": round(covered / max(len(content), 1), 4),
        "flagged": {t: {"count": c,
                        "log_ratio": jargon[t]["log_ratio"],
                        "approved_count": jargon[t]["approved_count"]}
                    for t, c in hits.most_common()},
        "unapproved_unigrams": dict(unapproved_unigrams.most_common()),
        "unapproved_bigrams": dict(unapproved_bigrams.most_common()),
    }


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p for p in parts if len(tokenize(p)) >= 3]


def score_file(path, lex):
    text = Path(path).read_text(errors="ignore")
    res = score_tokens(tokenize(text), lex)
    res["sentences_with_jargon"] = []
    for s in split_sentences(text):
        r = score_tokens(tokenize(s), lex)
        if r["jargon_hits"] or r["unapproved_unigram_hits"] or r["unapproved_bigram_hits"]:
            res["sentences_with_jargon"].append(
                {"sentence": s.strip()[:160], "terms": list(r["flagged"]),
                 "unapproved": list(r["unapproved_unigrams"]) + list(r["unapproved_bigrams"])})
    return res


def _rank_by_document_count(doc_counts, hit_counts, limit=15):
    ranked = sorted(doc_counts, key=lambda t: (-doc_counts[t], -hit_counts[t], t))
    return [[t, doc_counts[t], hit_counts[t]] for t in ranked[:limit]]


PER_FILE_FIELDS = ("tokens", "content_words", "jargon_hits", "jargon_density_per_1k",
                   "unapproved_unigram_hits", "unapproved_unigram_density_per_1k",
                   "unapproved_bigram_density_per_1k", "approved_coverage")


def score_dir(path, lex):
    """Score every .txt in a dir: per-file rows plus corpus-level aggregate."""
    docs = load_corpus(path)
    rows = []
    totals = Counter()
    flagged = Counter()
    unigram_hits, unigram_docs = Counter(), Counter()
    bigram_hits, bigram_docs = Counter(), Counter()
    approved = lex["approved_vocabulary"]
    for name, toks in docs:
        r = score_tokens(toks, lex)
        rows.append({"file": name, **{k: r[k] for k in PER_FILE_FIELDS},
                     "top_terms": list(r["flagged"])[:3],
                     "top_unapproved": list(r["unapproved_unigrams"])[:3]})
        content = [t for t in toks if t not in STOPWORDS]
        totals["tokens"] += r["tokens"]
        totals["content"] += len(content)
        totals["covered"] += sum(1 for t in content if t in approved)
        totals["jargon"] += r["jargon_hits"]
        totals["unigrams"] += r["unapproved_unigram_hits"]
        totals["bigrams"] += r["unapproved_bigram_hits"]
        for t, s in r["flagged"].items():
            flagged[t] += s["count"]
        for t, c in r["unapproved_unigrams"].items():
            unigram_hits[t] += c
            unigram_docs[t] += 1
        for t, c in r["unapproved_bigrams"].items():
            bigram_hits[t] += c
            bigram_docs[t] += 1
    per_1k = 1000 / max(totals["content"], 1)
    return {
        "dir": str(path),
        "docs": len(rows),
        "tokens": totals["tokens"],
        "content_words": totals["content"],
        "jargon_hits": totals["jargon"],
        "jargon_density_per_1k": round(per_1k * totals["jargon"], 2),
        "unapproved_unigram_hits": totals["unigrams"],
        "unapproved_bigram_hits": totals["bigrams"],
        "unapproved_unigram_density_per_1k": round(per_1k * totals["unigrams"], 2),
        "unapproved_bigram_density_per_1k": round(per_1k * totals["bigrams"], 2),
        "approved_coverage": round(totals["covered"] / max(totals["content"], 1), 4),
        "docs_with_jargon": sum(1 for r in rows if r["jargon_hits"]),
        "docs_with_unapproved_unigrams": sum(1 for r in rows if r["unapproved_unigram_hits"]),
        "top_flagged": flagged.most_common(15),
        "top_unapproved_unigrams": _rank_by_document_count(unigram_docs, unigram_hits),
        "top_unapproved_bigrams": _rank_by_document_count(bigram_docs, bigram_hits),
        "files": sorted(rows, key=lambda r: -r["jargon_density_per_1k"]),
    }


DELTA_CLASSES = (("jargon", "jargon_hits"),
                 ("unapproved_unigrams", "unapproved_unigram_hits"),
                 ("unapproved_bigrams", "unapproved_bigram_hits"))


def delta(a_path, b_path, lex, n_boot=2000, seed=7):
    """A vs B density per class with a bootstrap CI.

    Files resample sentences; dirs resample documents.
    """
    import random
    rng = random.Random(seed)

    def units(path):
        p = Path(path)
        if p.is_dir():
            return [score_tokens(toks, lex) for _, toks in load_corpus(p)]
        return [score_tokens(tokenize(s), lex)
                for s in split_sentences(p.read_text(errors="ignore"))]

    A, B = units(a_path), units(b_path)
    resamples = [([A[rng.randrange(len(A))] for _ in A], [B[rng.randrange(len(B))] for _ in B])
                 for _ in range(n_boot)]

    def density(sample, hits_key):
        hits = sum(r[hits_key] for r in sample)
        content = sum(r["content_words"] for r in sample)
        return 1000 * hits / max(content, 1)

    result = {
        "unit": "documents" if Path(a_path).is_dir() else "sentences",
        "a": {"path": str(a_path), "units": len(A)},
        "b": {"path": str(b_path), "units": len(B)},
    }
    for cls, hits_key in DELTA_CLASSES:
        observed = density(A, hits_key) - density(B, hits_key)
        diffs = sorted(density(a, hits_key) - density(b, hits_key) for a, b in resamples)
        lo, hi = diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot)]
        result[cls] = {
            "a_density": round(density(A, hits_key), 2),
            "b_density": round(density(B, hits_key), 2),
            "delta": round(observed, 2),
            "ci95": [round(lo, 2), round(hi, 2)],
            "credible": bool(lo > 0 or hi < 0),
        }
    return result


DEFAULT_STOPLIST_PATH = FIXTURES / "name_stoplist.txt"


def load_lexicon(path):
    lex = json.loads(Path(path).read_text())
    if "jargon" not in lex:
        sys.exit(f"{path} is not a lexicon file (missing 'jargon' key)")
    _backfill_fields_older_files_lack(lex)
    return lex


def _backfill_fields_older_files_lack(lex):
    meta, params = lex["meta"], lex["meta"]["params"]
    meta.setdefault("stopwords", sorted(STOPWORDS))
    if not params.get("zipf_gate"):
        params["zipf_gate"] = 5.0
    stoplist = params.get("stoplist") or {}
    if not isinstance(stoplist.get("terms"), list):
        names = load_stoplist(DEFAULT_STOPLIST_PATH)
        params["stoplist"] = {"path": str(DEFAULT_STOPLIST_PATH), "terms": sorted(names)}
        _approve_stoplist_names(lex["approved_vocabulary"], names, {}, {}, 1)


# --- extensions ------------------------------------------------------------
#
# An extension is the vocabulary profile of one more approved corpus. Applied
# to a lexicon at check time, it adds to the approved side only: every term
# its audience uses joins the approved vocabulary, and any such term leaves
# the jargon list. Nothing new becomes jargon.


def profile(docs, min_count=3, min_docs=2, n_max=3):
    """Return the vocabulary profile of a corpus: the terms that can veto jargon.

    Keeps terms with count >= min_count in >= min_docs documents, the same
    floor `build()` applies to an approved vocabulary. The dispersion bar is
    the auto-scaled ceiling `build()` uses for "the audience says it too".
    """
    tf, df, total = _counts(docs, n_max)
    n = len(docs)
    bar, median = auto_dispersion(docs, base=0.05, ref_len=250, lo=0.01, hi=0.05,
                                  min_docs=3)
    bar = min(bar, 1.0)  # under 3 docs nothing can veto; keep the share readable
    vocab = {t: {"count": c, "doc_share": round(df[t] / n, 4)}
             for t, c in tf.items() if c >= min_count and df[t] >= min_docs}
    return {
        "meta": {"docs": n, "tokens": total, "median_doc_tokens": median,
                 "max_approved_dispersion": bar},
        "vocabulary": dict(sorted(vocab.items(), key=lambda kv: -kv[1]["count"])),
    }


def extend(lex, ext, name=None):
    """Return a new lexicon with `ext` overlaid; the input stays untouched."""
    bar = ext["meta"]["max_approved_dispersion"]
    vocab = ext["vocabulary"]
    vetoed = [t for t in lex["jargon"]
              if t in vocab and vocab[t]["doc_share"] > bar]
    gone = set(vetoed)
    approved = dict(lex["approved_vocabulary"])
    added = 0
    for t, s in vocab.items():
        if t not in approved:
            approved[t] = {"approved_count": s["count"],
                           "approved_doc_share": s["doc_share"]}
            added += 1
    meta = dict(lex["meta"])
    meta["extensions"] = list(meta.get("extensions", [])) + [
        {"name": name, "vetoed": vetoed, "added": added}]
    return {"meta": meta,
            "jargon": {t: s for t, s in lex["jargon"].items() if t not in gone},
            "approved_vocabulary": approved}


def today():
    import datetime
    return datetime.date.today().isoformat()


def load_extension(path):
    ext = json.loads(Path(path).read_text())
    if "vocabulary" not in ext:
        sys.exit(f"{path} is not an extension file (missing 'vocabulary' key)")
    return ext
