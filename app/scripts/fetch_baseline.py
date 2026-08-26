#!/usr/bin/env python3
"""Fetch a standard-technical-English baseline corpus from Wikipedia.

Pulls plain-text intro extracts of articles in mainstream computing/software
categories and writes one .txt per article to corpus/baseline-wikipedia-computing/.
Content: CC BY-SA 4.0 (attribution = article title in the filename; analysis use).
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "corpus", "baseline-wikipedia-computing")

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "voice-agents-corpus/1.0 (personal research; brooksryan19@gmail.com)"}

CATEGORIES = [
    "Category:Software_engineering",
    "Category:Web_development",
    "Category:Cloud_computing",
    "Category:Databases",
    "Category:Computer_networking",
    "Category:Software_project_management",
    "Category:User_interfaces",
    "Category:Application_programming_interfaces",
]
PER_CATEGORY = 40
MIN_WORDS = 60


def api(params):
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def category_titles(cat, limit):
    data = api({"action": "query", "list": "categorymembers", "cmtitle": cat,
                "cmlimit": limit, "cmnamespace": 0, "cmtype": "page"})
    return [m["title"] for m in data["query"]["categorymembers"]]


def extracts(titles):
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        data = api({"action": "query", "prop": "extracts", "exintro": 1,
                    "explaintext": 1, "titles": "|".join(batch)})
        for page in data["query"]["pages"].values():
            text = page.get("extract", "").strip()
            if text:
                out[page["title"]] = text
        time.sleep(0.3)
    return out


def slug(s, n=60):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n].rstrip("-")


def main():
    os.makedirs(OUT, exist_ok=True)
    titles, seen = [], set()
    for cat in CATEGORIES:
        for t in category_titles(cat, PER_CATEGORY):
            if t not in seen and not t.startswith(("List of", "Comparison of",
                                                   "Outline of", "Glossary of",
                                                   "Index of", "Timeline of")):
                seen.add(t)
                titles.append(t)
    print(f"{len(titles)} candidate articles")
    texts = extracts(titles)
    n, words = 0, 0
    manifest = []
    for title, text in sorted(texts.items()):
        w = len(text.split())
        if w < MIN_WORDS:
            continue
        n += 1
        words += w
        path = os.path.join(OUT, f"{n:03d}_{slug(title)}.txt")
        with open(path, "w") as f:
            f.write(text + "\n")
        manifest.append(f"- {title} ({w} words)")
    with open(os.path.join(OUT, "MANIFEST.md"), "w") as f:
        f.write("# baseline-wikipedia-computing\n\n"
                "Intro extracts of English Wikipedia computing/software articles, "
                "fetched via the MediaWiki API (action=query, prop=extracts, exintro, "
                "explaintext). One article intro per .txt. License: CC BY-SA 4.0; "
                "titles listed below are the attribution. Fetched 2026-08-18 by "
                "app/scripts/fetch_baseline.py — re-run it to refresh.\n\n"
                f"Categories: {', '.join(c.split(':', 1)[1] for c in CATEGORIES)}\n\n"
                f"{n} articles, ~{words:,} words.\n\n" + "\n".join(manifest) + "\n")
    print(f"wrote {n} articles, ~{words:,} words -> {OUT}")


if __name__ == "__main__":
    main()
