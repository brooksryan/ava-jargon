"""The tier 2 (spacy) checkers. The module skips without the [parser] extra."""
import pytest

pytest.importorskip("spacy")
from ava_jargon.checks.parser import available  # noqa: E402

ready, reason = available()
pytestmark = pytest.mark.skipif(not ready, reason=reason or "parser not ready")

# 31 words: over the instruction limit (20) and the description limit (25).
LONG = ("Open the settings page, then choose the account tab, then scroll to the "
        "bottom of the list, then select the export option, then confirm the "
        "export and close the dialog window.\n")


def test_tier_2_runs_when_spacy_is_installed(ava):
    r = ava("check", "-", "--rules", "technical", stdin=LONG)
    assert r.returncode == 1
    assert "[T-M1]" in r.stdout


def test_no_parser_skips_tier_2(ava):
    r = ava("check", "-", "--rules", "technical", "--no-parser", stdin=LONG)
    assert "[T-M1]" not in r.stdout
    assert "T-M1" in r.stderr  # named in the skipped list
