#!/usr/bin/env python3
"""Precompute CPIDR idea-density scores for every curated pair (run with the venv python)."""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
import os
BASE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(os.path.dirname(os.path.dirname(BASE)), "audit")
sys.path.insert(0, BASE)
from build_page import AGENT_SHORT, CUR, clean, strip_noise  # noqa: E402

from ideadensity import cpidr  # noqa: E402

out = {}
for full in AGENT_SHORT:
    with open(f"{CUR}/{full}.json") as f:
        pairs = json.load(f)["pairs"]
    rows = []
    for p in pairs:
        rec = {}
        for side, key in (("before", "b"), ("after", "f")):
            text = strip_noise(clean(p.get(side) or ""))
            wc, props, density, _ = cpidr(text)
            rec[key] = round(density, 3)
            rec["w" + key] = wc
            rec["p" + key] = props
        rows.append(rec)
    out[full] = rows
    ds = [(r["f"] - r["b"]) for r in rows]
    print(f"{full}: {len(rows)} pairs, mean density delta {sum(ds)/len(ds):+.3f}")

with open(os.path.join(AUDIT, "raw", "cpidr_scores.json"), "w") as f:
    json.dump(out, f, indent=1)
print("wrote raw/cpidr_scores.json")
