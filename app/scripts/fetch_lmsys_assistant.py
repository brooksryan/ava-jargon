#!/usr/bin/env python3
"""Fetch AI-authored chat turns from LMSYS-Chat-1M.

Negative-side Chat-surface corpus, companion to fetch_wildchat_assistant.py.
Every document is an ASSISTANT turn from a published LLM-conversation dataset,
so AI authorship is known by construction (dataset label, proof type (a)).
User turns are dropped.

The canonical `lmsys/lmsys-chat-1m` repo is gated and the local HuggingFace
token has no grant, so this script reads the public mirror
`AarushSah/lmsys-chat-1m` — same schema, same 1,000,000 rows, same LMSYS arena
model labels (vicuna, koala, alpaca, llama-2, claude, gpt-3.5 ...). Change
DATASET below if a grant on the canonical repo arrives.

Filters: row language English, role == assistant, moderation-flagged messages
dropped, fenced code stripped, 60-600 remaining prose words, deduped, at most
two turns per conversation.
"""
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "corpus", "lmsys-assistant-turns")

API = "https://datasets-server.huggingface.co/rows"
DATASET = "AarushSah/lmsys-chat-1m"
CANONICAL = "lmsys/lmsys-chat-1m"
NUM_ROWS = 1_000_000
PAGE = 100
TARGET_TURNS = 1400
TARGET_WORDS = 60_000
MIN_WORDS, MAX_WORDS = 60, 600
MAX_PER_CONV = 2
SEED = 20260824

FENCE_RE = re.compile(r"```.*?```", re.S)
OPEN_FENCE_RE = re.compile(r"```.*", re.S)
URL_RE = re.compile(r"\S+@\S+|https?://\S+|www\.\S+")
SAFE_RE = re.compile(r"[^a-z0-9]+")

TOKEN_PATH = os.path.expanduser("~/.cache/huggingface/token")


def token():
    try:
        with open(TOKEN_PATH) as f:
            return f.read().strip()
    except OSError:
        return ""


def fetch(offset, length=PAGE, tries=4):
    q = urllib.parse.urlencode({"dataset": DATASET, "config": "default",
                                "split": "train", "offset": offset, "length": length})
    req = urllib.request.Request(f"{API}?{q}")
    t = token()
    if t:
        req.add_header("Authorization", f"Bearer {t}")
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["rows"]
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            if attempt == tries - 1:
                return []
            time.sleep(3 * (attempt + 1))
    return []


def clean(text):
    text = FENCE_RE.sub(" ", text)
    text = OPEN_FENCE_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slug(value):
    return SAFE_RE.sub("-", str(value).lower()).strip("-")[:28] or "unknown"


def flagged(row, index):
    mod = row.get("openai_moderation") or []
    if index < len(mod) and isinstance(mod[index], dict):
        return bool(mod[index].get("flagged"))
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(SEED)
    pages = list(range(0, NUM_ROWS - PAGE, PAGE))
    rng.shuffle(pages)

    n, words, seen, records, models = 0, 0, set(), [], {}
    for offset in pages:
        if n >= TARGET_TURNS and words >= TARGET_WORDS:
            break
        for row in fetch(offset):
            r = row["row"]
            if r.get("language") != "English":
                continue
            kept = 0
            for i, msg in enumerate(r.get("conversation") or []):
                if kept >= MAX_PER_CONV:
                    break
                if msg.get("role") != "assistant" or flagged(r, i):
                    continue
                body = clean(msg.get("content") or "")
                w = len(body.split())
                key = body[:120]
                if not (MIN_WORDS <= w <= MAX_WORDS) or key in seen:
                    continue
                seen.add(key)
                kept += 1
                n += 1
                words += w
                model = r.get("model") or "unknown"
                models[model] = models.get(model, 0) + 1
                name = (f"{n:04d}_{slug(model)}_"
                        f"{str(r.get('conversation_id'))[:8]}_t{i}.txt")
                with open(os.path.join(OUT, name), "w") as f:
                    f.write(body + "\n")
                records.append((name, w, model))
        time.sleep(0.2)

    with open(os.path.join(OUT, "MANIFEST.md"), "w") as f:
        f.write("# lmsys-assistant-turns\n\n"
                f"{n} assistant turns, ~{words:,} words. Source: LMSYS-Chat-1M, read "
                f"from the public mirror {DATASET} because the canonical "
                f"{CANONICAL} repo is gated. HuggingFace datasets-server rows API, "
                "fetched by app/scripts/fetch_lmsys_assistant.py.\n\n")
        f.write("## Models that wrote these turns\n\n")
        for model, count in sorted(models.items(), key=lambda kv: -kv[1]):
            f.write(f"- {model}: {count} turns\n")
        f.write("\n## Files\n\n")
        for name, w, model in records:
            f.write(f"- {name} ({w} words, {model})\n")
    print(f"wrote {n} turns, ~{words:,} words -> {OUT}")


if __name__ == "__main__":
    main()
