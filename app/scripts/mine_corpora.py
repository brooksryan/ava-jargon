#!/usr/bin/env python3
"""One-shot corpus mining: builds analysis lexicons, scores every corpus,
runs the key deltas, computes surface stats. Dumps one JSON for reporting.
Run with the venv python (wordfreq + ideadensity available)."""
import json
import os
import statistics
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, os.path.join(ROOT, "app"))
import jargon as J  # noqa: E402

C = os.path.join(ROOT, "corpus")
LEX = os.path.join(ROOT, "lexicons")
os.makedirs(LEX, exist_ok=True)

CORPORA = {
    "customer": f"{C}/customer-slack-messages,{C}/customer-linear-messages",
    "internal-human": f"{C}/internal-slack-messages",
    "brooks-slack": f"{C}/brooks-all-slack",
    "brooks-prompts": f"{C}/brooks-claude-prompts",
    "agent-docs": f"{C}/evolv-agent-artifacts",
    "agent-slack-before": f"{C}/slack-agent-messages/before",
    "agent-slack-after": f"{C}/slack-agent-messages/after",
    "baselines": f"{C}/baseline-wikipedia-computing,{C}/baseline-workplace-email",
}

STOP = J.load_stoplist(os.path.join(ROOT, "app", "name_stoplist.txt"))

BUILDS = [
    ("analysis-customer-vs-internal", "customer", "internal-human"),
    ("analysis-baselines-vs-internal", "baselines", "internal-human"),
    ("analysis-human-vs-agentdocs", "brooks-slack", "agent-docs"),
    ("analysis-agentdocs-vs-brooks", "agent-docs", "brooks-slack"),
    ("analysis-brooksslack-vs-prompts", "brooks-slack", "brooks-prompts"),
]

out = {"lexicons": {}, "scores": {}, "deltas": {}, "surface": {}}

for name, ap, ct in BUILDS:
    lex = J.build(CORPORA[ap], CORPORA[ct], stoplist=STOP)
    path = os.path.join(LEX, f"{name}.json")
    with open(path, "w") as f:
        json.dump(lex, f, indent=1)
    out["lexicons"][name] = {
        "approved": ap, "contrast": ct,
        "approved_tokens": lex["meta"]["approved_tokens"],
        "contrast_tokens": lex["meta"]["contrast_tokens"],
        "n_terms": len(lex["jargon"]),
        "top30": [(t, s["log_likelihood"], s["log_ratio"], s["approved_count"])
                  for t, s in list(lex["jargon"].items())[:30]],
    }
    print(f"built {name}: {len(lex['jargon'])} terms")

gate = json.load(open(os.path.join(LEX, "analysis-customer-vs-internal.json")))
for cname, cpath in CORPORA.items():
    docs = J.load_corpus(cpath)
    hits, toks = 0, 0
    content, covered = 0, 0
    approved = gate["approved_vocabulary"]
    flagged = {}
    for _, t in docs:
        r = J.score_tokens(t, gate)
        hits += r["jargon_hits"]
        toks += r["tokens"]
        cw = [w for w in t if w not in J.STOPWORDS]
        content += len(cw)
        covered += sum(1 for w in cw if w in approved)
        for term, s in r["flagged"].items():
            flagged[term] = flagged.get(term, 0) + s["count"]
    out["scores"][cname] = {
        "docs": len(docs), "tokens": toks,
        "density_per_1k": round(1000 * hits / max(toks, 1), 2),
        "approved_coverage": round(covered / max(content, 1), 3),
        "top_flagged": sorted(flagged.items(), key=lambda kv: -kv[1])[:8],
    }
    lens = [len(t) for _, t in docs]
    slens = []
    for _, t in docs[:2000]:
        pass
    out["surface"][cname] = {
        "docs": len(docs), "tokens": toks,
        "mean_doc_words": round(statistics.fmean(lens), 1),
        "median_doc_words": sorted(lens)[len(lens) // 2],
    }
    print(f"scored {cname}: {out['scores'][cname]['density_per_1k']}/1k")

for a, b in [("agent-slack-before", "agent-slack-after"),
             ("agent-slack-after", "brooks-slack"),
             ("agent-docs", "internal-human")]:
    pa = CORPORA[a].split(",")[0]
    res = J.delta(CORPORA[a].split(",")[0], CORPORA[b].split(",")[0], gate)
    out["deltas"][f"{a}__vs__{b}"] = res
    print(f"delta {a} vs {b}: {res['delta']} CI {res['ci95']}")

# CPIDR idea-density sample per corpus (cap 150 docs each)
try:
    import warnings
    warnings.filterwarnings("ignore")
    from ideadensity import cpidr
    out["cpidr"] = {}
    for cname, cpath in CORPORA.items():
        docs = J.load_corpus(cpath)
        step = max(1, len(docs) // 150)
        ds = []
        for _, t in docs[::step][:150]:
            text = " ".join(t)
            if len(t) < 5:
                continue
            _, _, d, _ = cpidr(text)
            if d:
                ds.append(d)
        out["cpidr"][cname] = {"n": len(ds), "mean": round(statistics.fmean(ds), 3)} if ds else None
        print(f"cpidr {cname}: {out['cpidr'][cname]}")
except ImportError:
    out["cpidr"] = None

with open(os.path.join(ROOT, "audit", "raw", "corpus_mining.json"), "w") as f:
    json.dump(out, f, indent=1)
print("wrote audit/raw/corpus_mining.json")
