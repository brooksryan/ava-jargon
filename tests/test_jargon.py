"""`ava jargon`: the three classes a scored document belongs to, and one denominator.

A jargon term sits in the lexicon's jargon list. An approved term sits in its
approved vocabulary. An unapproved term sits in neither. Every rate divides by
content words: the tokens left after the function-word list.
"""
import json

import pytest

AUDIENCE = ["the widget shipped to the customer today",
            "customer asked about the widget invoice",
            "widget invoice went out, customer happy",
            "the invoice for the widget is paid"]
AGENTS = ["the seam between the router and the widget lands here"] * 4 + \
         ["the router leverages the seam, honestly"] * 4
STOPLIST_NAMES = "avneet\naslantas\n"

CHECK = ("--rules", "westinghouse", "--surface", "chat")


@pytest.fixture
def lexicon(ava, project):
    """A lexicon from two tiny corpora. Every threshold is explicit, because the
    auto floors assume 30k tokens a side."""
    for side, texts in (("approved", AUDIENCE), ("contrast", AGENTS)):
        (project / side).mkdir()
        for i, text in enumerate(texts):
            (project / side / f"{i}.txt").write_text(text)
    (project / "names.txt").write_text(STOPLIST_NAMES)
    out = project / "lex.json"
    r = ava("jargon", "build", "approved", "contrast", "-o", str(out),
            "--min-contrast-count", "2", "--min-approved-count", "2",
            "--min-contrast-dispersion", "0.1", "--max-approved-dispersion", "0.01",
            "--ll", "0", "--lr", "1", "--stoplist", str(project / "names.txt"))
    assert r.returncode == 0, r.stderr
    return out


def score(ava, lexicon, project, text):
    (project / "doc.txt").write_text(text)
    r = ava("jargon", "score", "doc.txt", "-l", str(lexicon), "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# --- the build: the stoplist joins the approved side --------------------------


def test_a_stoplist_name_is_approved_at_zero_uses(lexicon):
    lex = json.loads(lexicon.read_text())
    assert lex["approved_vocabulary"]["avneet"] == {
        "approved_count": 0, "approved_doc_share": 0.0, "source": "stoplist"}


def test_the_file_records_the_stoplist_and_the_function_words(lexicon, project):
    lex = json.loads(lexicon.read_text())
    assert lex["meta"]["params"]["stoplist"] == {
        "path": str(project / "names.txt"), "terms": ["aslantas", "avneet"]}
    stopwords = lex["meta"]["stopwords"]
    assert {"the", "and", "of"} <= set(stopwords) and stopwords == sorted(stopwords)


def test_the_build_line_counts_the_stoplist_names(ava, lexicon):
    r = ava("jargon", "build", "approved", "contrast", "-o", str(lexicon),
            "--min-contrast-count", "2", "--min-approved-count", "2",
            "--min-contrast-dispersion", "0.1", "--max-approved-dispersion", "0.01",
            "--ll", "0", "--lr", "1", "--stoplist", str(lexicon.parent / "names.txt"))
    assert r.returncode == 0, r.stderr
    assert "(2 from the stoplist)" in r.stdout


# --- the third class ----------------------------------------------------------


def test_a_word_in_neither_list_is_an_unapproved_unigram(ava, lexicon, project):
    res = score(ava, lexicon, project, "the seam is fine but the gasket is here")
    assert "seam" in res["flagged"]
    assert res["unapproved_unigrams"] == {"gasket": 1}


def test_an_unapproved_term_counts_every_use(ava, lexicon, project):
    res = score(ava, lexicon, project, "gasket gasket gasket")
    assert res["unapproved_unigrams"] == {"gasket": 3}
    assert res["unapproved_bigrams"] == {"gasket gasket": 2}
    assert res["unapproved_unigram_hits"] == 3 and res["unapproved_bigram_hits"] == 2


def test_an_ordinary_english_word_is_not_unapproved(ava, lexicon, project):
    res = score(ava, lexicon, project, "however the widget works")
    assert res["unapproved_unigrams"] == {}


def test_a_stoplist_name_is_not_unapproved(ava, lexicon, project):
    res = score(ava, lexicon, project, "avneet and the widget")
    assert res["unapproved_unigrams"] == {}


def test_a_code_fragment_is_not_unapproved(ava, lexicon, project):
    res = score(ava, lexicon, project, "widget v2 hash 9f3a in app.tsx")
    assert not {"v2", "f3a"} & set(res["unapproved_unigrams"])
    assert not [b for b in res["unapproved_bigrams"] if "v2" in b or "f3a" in b]


def test_a_jargon_term_is_never_also_unapproved(ava, lexicon, project):
    res = score(ava, lexicon, project, "seam seam router")
    assert not set(res["flagged"]) & set(res["unapproved_unigrams"])


def test_an_unapproved_bigram_is_judged_as_a_unit(ava, lexicon, project):
    res = score(ava, lexicon, project, "invoice widget")
    assert res["unapproved_unigrams"] == {}
    assert res["unapproved_bigrams"] == {"invoice widget": 1}


def test_an_approved_bigram_is_not_unapproved(ava, lexicon, project):
    res = score(ava, lexicon, project, "widget invoice")
    assert res["unapproved_bigrams"] == {}


# --- one denominator ----------------------------------------------------------


def test_every_rate_divides_by_content_words(ava, lexicon, project):
    res = score(ava, lexicon, project, "the the the the seam gasket")
    assert res["tokens"] == 6 and res["content_words"] == 2
    assert res["jargon_density_per_1k"] == 500.0
    assert res["unapproved_unigram_density_per_1k"] == 500.0
    assert res["unapproved_bigram_density_per_1k"] == 500.0
    assert res["approved_coverage"] == 0.0


def test_coverage_counts_a_stoplist_name(ava, lexicon, project):
    res = score(ava, lexicon, project, "avneet widget")
    assert res["approved_coverage"] == 1.0


# --- the text output ----------------------------------------------------------


def test_the_text_output_lists_the_classes_apart(ava, lexicon, project):
    (project / "doc.txt").write_text("the seam gasket")
    r = ava("jargon", "score", "doc.txt", "-l", str(lexicon))
    assert r.returncode == 0, r.stderr
    assert "content words: 2 of 3 tokens" in r.stdout
    assert "jargon density: 500.0 per 1,000 content words" in r.stdout
    assert "unapproved unigrams: 500.0 per 1,000 content words" in r.stdout
    assert "unapproved bigrams: 500.0 per 1,000 content words" in r.stdout
    assert "unapproved unigrams (in neither list):" in r.stdout
    assert "unapproved bigrams (in neither list):" in r.stdout
    assert "  gasket" in r.stdout and "  seam gasket" in r.stdout
    assert "-> ['seam'] + unapproved ['gasket', 'seam gasket']:" in r.stdout


def test_a_clean_doc_prints_no_unapproved_block(ava, lexicon, project):
    (project / "doc.txt").write_text("the widget invoice")
    r = ava("jargon", "score", "doc.txt", "-l", str(lexicon))
    assert r.returncode == 0, r.stderr
    assert "in neither list" not in r.stdout


# --- a directory ----------------------------------------------------------------


def test_dir_scoring_ranks_unapproved_terms_by_document_count(ava, lexicon, project):
    (project / "docs").mkdir()
    (project / "docs" / "a.txt").write_text("gasket gasket")
    (project / "docs" / "b.txt").write_text("the widget")
    (project / "docs" / "c.txt").write_text("gasket flange")
    r = ava("jargon", "score", "docs", "-l", str(lexicon), "--json")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["content_words"] == 5
    assert res["top_unapproved_unigrams"] == [["gasket", 2, 3], ["flange", 1, 1]]
    assert res["top_unapproved_bigrams"] == [["gasket flange", 1, 1], ["gasket gasket", 1, 1]]
    assert res["docs_with_unapproved_unigrams"] == 2
    assert res["unapproved_unigram_density_per_1k"] == 800.0
    assert res["unapproved_bigram_density_per_1k"] == 400.0


def test_dir_text_output_names_the_top_unapproved_terms(ava, lexicon, project):
    (project / "docs").mkdir()
    (project / "docs" / "a.txt").write_text("gasket gasket")
    r = ava("jargon", "score", "docs", "-l", str(lexicon))
    assert r.returncode == 0, r.stderr
    assert "unapproved unigrams: 1000.0" in r.stdout
    assert "top unapproved unigrams across corpus:" in r.stdout
    assert "gasket" in r.stdout and "in 1 docs" in r.stdout


# --- delta ------------------------------------------------------------------------


def test_delta_reports_every_class(ava, lexicon, project):
    for side, text in (("a", "gasket gasket flange"), ("b", "the widget invoice")):
        (project / side).mkdir()
        for i in range(3):
            (project / side / f"{i}.txt").write_text(text)
    r = ava("jargon", "delta", "a", "b", "-l", str(lexicon), "--json")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert set(res) >= {"unit", "a", "b", "jargon", "unapproved_unigrams", "unapproved_bigrams"}
    assert res["unapproved_unigrams"]["delta"] == 1000.0
    assert res["unapproved_bigrams"]["delta"] == round(1000 * 2 / 3, 2)
    assert res["jargon"]["delta"] == 0.0
    text = ava("jargon", "delta", "a", "b", "-l", str(lexicon)).stdout
    assert "unapproved unigrams (A - B): +1000.00 per 1,000 content words" in text


# --- a file from before this change ------------------------------------------------


def test_a_lexicon_from_before_this_change_still_scores(ava, lexicon, project):
    lex = json.loads(lexicon.read_text())
    del lex["meta"]["stopwords"]
    del lex["meta"]["params"]["zipf_gate"]
    lex["meta"]["params"]["stoplist"] = {"path": "names.txt", "terms": 2}
    lex["approved_vocabulary"] = {t: s for t, s in lex["approved_vocabulary"].items()
                                  if s.get("source") != "stoplist"}
    (project / "old.json").write_text(json.dumps(lex))
    res = score(ava, project / "old.json", project, "avneet gasket")
    assert res["unapproved_unigrams"] == {"gasket": 1}


# --- ava check ---------------------------------------------------------------------


def test_the_check_note_carries_every_density(ava, lexicon, project):
    (project / "doc.txt").write_text("the seam gasket")
    r = ava("check", "doc.txt", *CHECK, "--lexicon", str(lexicon))
    assert ("jargon density 500.0, unapproved unigrams 500.0, unapproved bigrams 500.0 "
            "per 1,000 content words") in r.stderr
    assert "unapproved unigrams: gasket×1" in r.stderr
    assert "unapproved bigrams: seam gasket×1" in r.stderr


def test_the_advisory_line_matches_the_scorer(ava, lexicon, project):
    text = "the seam gasket " * 120
    (project / "doc.txt").write_text(text)
    check = ava("check", "doc.txt", *CHECK, "--lexicon", str(lexicon)).stderr
    res = score(ava, lexicon, project, text)
    assert (f"jargon (W-M10, advisory): {res['jargon_density_per_1k']}/1k · "
            f"unapproved {res['unapproved_unigram_density_per_1k']}/1k unigrams, "
            f"{res['unapproved_bigram_density_per_1k']}/1k bigrams over "
            f"{res['content_words']:,} content words") in check


def test_unapproved_terms_never_reach_stdout_or_the_exit_code(ava, lexicon, project):
    (project / "doc.txt").write_text("the gasket leaks")
    r = ava("check", "doc.txt", *CHECK, "--lexicon", str(lexicon))
    assert r.returncode == 0 and r.stdout == ""
