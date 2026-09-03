"""The tier 1 checkers and the runner, called as a library."""
import pytest

from ava_jargon.checks import (TIER_2_RULES, Context, check_document, select,
                               w_m1_dash)


def rules(findings):
    return [f.rule for f in findings]


def test_em_dash_is_a_finding():
    out = w_m1_dash.check("The deploy job — it went well.\n", Context())
    assert rules(out) == ["W-M1"]
    assert out[0].label == "em dash"
    assert out[0].line == 1


def test_en_dash_in_a_date_range_passes():
    assert w_m1_dash.check("The plan covers 2024–2026.\n", Context()) == []


def test_en_dash_outside_a_date_range_is_a_finding():
    out = w_m1_dash.check("The plan – it slipped.\n", Context())
    assert [f.label for f in out] == ["en dash"]


def test_code_is_blank_to_the_checker():
    text = "Use `a — b` here.\n\n```\nx — y\n```\n"
    assert w_m1_dash.check(text, Context()) == []


def test_line_numbers_survive_code_stripping():
    text = "```\ncode\n```\n\nProse — here.\n"
    assert [f.line for f in w_m1_dash.check(text, Context())] == [5]


def test_select_technical_holds_the_technical_rules_only():
    chosen, tiers, skipped, warning = select("technical", Context(), use_parser=False)
    assert chosen and all("technical" in m.SETS for m in chosen)
    assert w_m1_dash in chosen
    assert tiers == ["1", "1b"]
    assert "W-M10" in skipped  # no lexicon on the context
    assert {rule for rule, _ in TIER_2_RULES} <= set(skipped)
    assert warning == ""


def test_select_rejects_an_unknown_rule_set():
    with pytest.raises(ValueError):
        select("nope", Context())


def test_check_document_stamps_the_path_and_sorts_by_line():
    ctx = Context(path="draft.md")
    out = check_document("A — b.\n\nC — d.\n", ctx, [w_m1_dash])
    assert [(f.path, f.line) for f in out] == [("draft.md", 1), ("draft.md", 3)]
