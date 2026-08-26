#!/usr/bin/env python3
"""Fetch a workplace-email English baseline from the AESLC corpus (Enron-derived).

Pulls cleaned email bodies via the HuggingFace datasets-server rows API and writes
one .txt per email to corpus/baseline-workplace-email/. This supplies the
conversational/workplace register (let me know, discuss, update, agenda) that the
Wikipedia baseline lacks — combine both on the approved side of a build.
AESLC: Zhang & Tetreault 2019, Enron-derived, released for research use.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "corpus", "baseline-workplace-email")

API = "https://datasets-server.huggingface.co/rows"
PAGES = 12          # x100 rows
MIN_WORDS, MAX_WORDS = 30, 400

FWD_RE = re.compile(r"-{2,}\s*(Original Message|Forwarded by).*", re.S | re.I)


def fetch(offset, length=100):
    q = urllib.parse.urlencode({"dataset": "Yale-LILY/aeslc", "config": "default",
                                "split": "train", "offset": offset, "length": length})
    with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
        return json.loads(r.read())["rows"]


def clean(body):
    body = FWD_RE.sub("", body)                    # drop quoted/forwarded tails
    body = re.sub(r"<[^>\s]+>", " ", body)         # rare markup residue
    body = re.sub(r"\S+@\S+|https?://\S+|www\.\S+", " ", body)
    body = re.sub(r"[ \t]+", " ", body)
    return body.strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    n, words, seen = 0, 0, set()
    for page in range(PAGES):
        for row in fetch(page * 100):
            body = clean(row["row"]["email_body"])
            w = len(body.split())
            key = body[:120]
            if not (MIN_WORDS <= w <= MAX_WORDS) or key in seen:
                continue
            seen.add(key)
            n += 1
            words += w
            with open(os.path.join(OUT, f"{n:04d}_email.txt"), "w") as f:
                f.write(body + "\n")
        time.sleep(0.3)
    with open(os.path.join(OUT, "MANIFEST.md"), "w") as f:
        f.write("# baseline-workplace-email\n\n"
                "Cleaned workplace email bodies from AESLC (Annotated Enron Subject "
                "Line Corpus, Zhang & Tetreault 2019; Enron emails are public record). "
                "Fetched via the HuggingFace datasets-server rows API by "
                "app/scripts/fetch_workplace_baseline.py — re-run to refresh. "
                "Quoted/forwarded tails, addresses, and URLs stripped; "
                f"{MIN_WORDS}-{MAX_WORDS} word bodies kept, deduped.\n\n"
                f"{n} emails, ~{words:,} words.\n")
    print(f"wrote {n} emails, ~{words:,} words -> {OUT}")


if __name__ == "__main__":
    main()
