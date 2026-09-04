#!/usr/bin/env python3
"""Draw the figures of the research studies as static SVG files.

  python app/scripts/build_research_figures.py

The script writes one file per figure into research/figures/. Each figure
holds the numbers the study reports. The figures therefore stay in step with
the text, and the script needs no corpus on the machine. The style follows FiveThirtyEight: a
gray panel, light solid gridlines, no spines, a bold title, and a source line.
The fonts are the system stacks GitHub renders with, because GitHub shows an
SVG inside an image tag and loads no web font for it.
"""
import html
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "research", "figures")

W = 860
PANEL = "#f0f0f0"
INK = "#1f2328"
INK2 = "#3c3c3c"
MUTED = "#6e6e6e"
GRID = "#cbcbcb"
HUMAN = "#008fd5"
AI = "#fc4f30"
GRAY = "#8b8b8b"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"


def esc(s):
    return html.escape(str(s), quote=True)


class Svg:
    """Collect SVG elements; render one panel with title, subtitle, and source."""

    def __init__(self, height):
        self.h = height
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=12, fill=INK2, anchor="start", weight="normal", font=MONO, extra=""):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" font-family="{esc(font)}" {extra}>{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=GRID, width=1, cap="butt"):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{width}" stroke-linecap="{cap}"/>')

    def rect(self, x, y, w, h, fill, opacity=1.0):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" fill-opacity="{opacity}"/>')

    def dot(self, x, y, r, fill):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{PANEL}" stroke-width="2"/>')

    def render(self, title, subtitle, source):
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {self.h}" width="{W}" height="{self.h}" role="img">',
                f'<title>{esc(title)}</title>',
                f'<rect width="{W}" height="{self.h}" fill="{PANEL}"/>']
        body = []
        y = 34
        body.append(f'<text x="24" y="{y}" font-size="20" font-weight="700" fill="{INK}" font-family="{esc(SANS)}">{esc(title)}</text>')
        for i, line in enumerate(subtitle):
            body.append(f'<text x="24" y="{y + 24 + i * 18}" font-size="13" fill="{INK2}" font-family="{esc(SANS)}">{esc(line)}</text>')
        foot_y = self.h - 30
        body.append(f'<line x1="24" y1="{foot_y}" x2="{W - 24}" y2="{foot_y}" stroke="{INK2}" stroke-width="2"/>')
        body.append(f'<text x="24" y="{foot_y + 18}" font-size="11" fill="{INK2}" font-family="{esc(MONO)}" letter-spacing="0.5">SOURCE: {esc(source.upper())}</text>')
        body.append(f'<text x="{W - 24}" y="{foot_y + 18}" font-size="11" fill="{INK2}" font-family="{esc(MONO)}" text-anchor="end" letter-spacing="0.5">AVA RESEARCH</text>')
        return "\n".join(head + body + self.parts + ["</svg>"])


def legend(svg, y, items):
    """Draw one legend row; items hold (label, color)."""
    x = 24
    for label, color in items:
        svg.rect(x, y - 10, 12, 12, color)
        svg.text(x + 18, y, label, size=12)
        x += 18 + len(label) * 7.4 + 26


# --- the figures --------------------------------------------------------------


def idea_density():
    """Figure 2: idea density by writer, a dot plot with the human cluster shaded."""
    rows = [("my prompts to a coding agent", 0.515, HUMAN), ("my messages", 0.509, HUMAN),
            ("my team's messages", 0.507, HUMAN), ("end users", 0.500, HUMAN),
            ("encyclopedia and email reference set", 0.472, HUMAN), ("agent drafts", 0.463, AI),
            ("planning documents my agents wrote", 0.418, AI)]
    top, rh, x0, x1, lo, hi = 118, 30, 320, W - 60, 0.40, 0.53
    svg = Svg(top + len(rows) * rh + 90)
    sx = lambda v: x0 + (x1 - x0) * (v - lo) / (hi - lo)
    legend(svg, top - 26, [("human writers", HUMAN), ("agent writers", AI)])
    svg.rect(sx(0.50), top, sx(0.52) - sx(0.50), len(rows) * rh, HUMAN, 0.14)
    svg.text((sx(0.50) + sx(0.52)) / 2, top - 6, "human cluster", size=11, fill=MUTED, anchor="middle")
    for v in (0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.52):
        svg.line(sx(v), top, sx(v), top + len(rows) * rh)
        svg.text(sx(v), top + len(rows) * rh + 16, f"{v:.2f}", size=11, fill=MUTED, anchor="middle")
    svg.text(x1, top + len(rows) * rh + 32, "ideas per word (CPIDR)", size=11, fill=MUTED, anchor="end")
    for i, (label, v, color) in enumerate(rows):
        y = top + i * rh + 15
        svg.line(sx(lo), y, sx(v), y, stroke="#dedede")
        svg.dot(sx(v), y, 7, color)
        svg.text(x0 - 12, y + 4, label, size=12, fill=INK, anchor="end")
        svg.text(sx(v) + 13, y + 4, f"{v:.3f}", size=11.5, fill=INK)
    return svg.render("Agent documents sit 18 percent below every human register",
                      ["CPIDR idea density over about 150 documents per corpus, round one. Every human register",
                       "sits between 0.50 and 0.52 ideas per word."],
                      "CPIDR 3.2 port over part-of-speech tags")


def two_sides():
    """Figure 3: human and AI density per surface, a dumbbell on a log scale."""
    rows = [("messages", 0.43, 4.78), ("general documents", 6.37, 106.24),
            ("technical documents", 6.28, 83.57), ("READMEs and code comments", 3.60, 50.07)]
    top, rh, x0, x1, lo, hi = 118, 46, 250, W - 60, 0.1, 300
    svg = Svg(top + len(rows) * rh + 92)
    sx = lambda v: x0 + (x1 - x0) * (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    legend(svg, top - 26, [("human side", HUMAN), ("AI side", AI)])
    for v in (0.1, 0.3, 1, 3, 10, 30, 100, 300):
        svg.line(sx(v), top, sx(v), top + len(rows) * rh)
        svg.text(sx(v), top + len(rows) * rh + 16, f"{v:g}", size=11, fill=MUTED, anchor="middle")
    svg.text(x1, top + len(rows) * rh + 32, "jargon hits per 1,000 tokens, log scale", size=11, fill=MUTED, anchor="end")
    for i, (label, hv, av) in enumerate(rows):
        y = top + i * rh + 24
        svg.line(sx(hv), y, sx(av), y, stroke=GRAY, width=3, cap="round")
        svg.dot(sx(hv), y, 7, HUMAN)
        svg.dot(sx(av), y, 7, AI)
        svg.text(x0 - 12, y + 4, label, size=12, fill=INK, anchor="end")
        svg.text(sx(hv) - 13, y + 4, f"{hv:.2f}", size=11.5, fill=INK, anchor="end")
        svg.text(sx(av) + 13, y + 4, f"{av:.2f}", size=11.5, fill=INK)
        svg.text((sx(hv) + sx(av)) / 2, y - 11, f"{round(av / hv)}x", size=11, fill=MUTED, anchor="middle")
    return svg.render("The gap between the two sides is 11 to 17 times on every surface",
                      ["Density of each side against its own general lexicon, self-scored. On a log scale",
                       "the length of each connector is the ratio."],
                      "the four general lexicons that ship, scored on the corpora that built them")


SPECTRUM = [
    # word, audience side per million, AI side per million, log ratio
    ("cli", 0.0, 1034.4, 11.31),
    ("claude", 0.8, 1289.9, 10.63),
    ("repo", 1.6, 770.7, 8.89),
    ("env", 5.7, 1038.4, 7.51),
    ("docs", 21.1, 1137.0, 5.75),
    ("install", 44.7, 1082.7, 4.6),
    ("json", 129.3, 1911.8, 3.89),
    ("config", 109.7, 1110.8, 3.34),
    ("agent", 217.0, 1662.2, 2.94),
    ("path", 371.5, 1448.9, 1.96),
    ("mode", 201.6, 760.7, 1.92),
    ("default", 486.1, 1662.2, 1.77),
    ("tests", 315.4, 1074.6, 1.77),
    ("token", 321.1, 1070.6, 1.74),
    ("file", 767.4, 1652.2, 1.11),
    ("error", 746.3, 845.2, 0.18),
    ("code", 1864.8, 1843.3, -0.02),
    ("field", 1082.0, 959.9, -0.17),
    ("client", 981.2, 835.1, -0.23),
    ("server", 1305.5, 1082.7, -0.27),
    ("user", 1234.8, 1014.2, -0.28),
    ("set", 1397.4, 1145.0, -0.29),
    ("change", 833.2, 672.1, -0.31),
    ("function", 1388.4, 150.9, -3.2),
    ("software", 948.7, 86.5, -3.45),
    ("approach", 720.2, 48.3, -3.9),
    ("algorithm", 756.8, 12.1, -5.97),
]
ZONES = [("jargon: tested side 4x or more", 0, 9), ("significant, under 4x", 9, 15),
         ("shared vocabulary", 15, 23), ("audience's own words", 23, 27)]


def keyness_spectrum():
    """Figure 10: twenty-seven words drawn twice, sorted by the ratio test."""
    top, plot_h, x0, x1, lo, hi = 166, 280, 64, W - 24, 1, 20000
    y0 = top + plot_h
    svg = Svg(y0 + 136)
    legend(svg, top - 74, [("audience side", HUMAN), ("tested side, the AI documents", AI)])
    n = len(SPECTRUM)
    slot = (x1 - x0) / n
    sy = lambda v: y0 - plot_h * (math.log10(max(v, lo)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    for v in (1, 10, 100, 1000, 10000):
        svg.line(x0, sy(v), x1, sy(v))
        svg.text(x0 - 8, sy(v) + 4, f"{v:,}", size=11, fill=MUTED, anchor="end")
    svg.text(x0 - 52, top - 46, "occurrences per million tokens, log scale", size=11, fill=MUTED)
    for i, (name, a, b) in enumerate(ZONES):
        xa, xb = x0 + a * slot + 3, x0 + b * slot - 3
        lift = 16 if i in (1, 3) else 0
        svg.line(xa, top - 8 - lift, xb, top - 8 - lift, stroke=INK2, width=1.5)
        svg.text(xb if i == 3 else (xa + xb) / 2, top - 13 - lift, name, size=11, fill=MUTED, anchor="end" if i == 3 else "middle")
        if i:
            svg.line(x0 + a * slot, top, x0 + a * slot, y0, stroke=GRAY)
    for i, (word, ra, rc, _) in enumerate(SPECTRUM):
        cx = x0 + i * slot + slot / 2
        for color, v, w in sorted([(HUMAN, ra, 16), (AI, rc, 8)], key=lambda t: -t[1]):
            svg.rect(cx - w / 2, sy(v), w, y0 - sy(v), color)
        svg.add(f'<text x="{cx + 4:.1f}" y="{y0 + 8}" font-size="11.5" fill="{INK}" font-family="{esc(MONO)}" '
                f'text-anchor="end" transform="rotate(-55 {cx + 4:.1f} {y0 + 8})">{esc(word)}</text>')
    svg.line(x0, y0, x1, y0, stroke=INK2, width=2)
    return svg.render("Keyness is the gap between two bars, not the height of one",
                      ["Twenty-seven words from the technical-documents build, each drawn twice: how often the audience",
                       "writes it and how often the AI documents do. Past the 4x line on the left, a word is jargon."],
                      "single-word counts, technical-documents build, 1.23M audience tokens against 497k AI tokens")


SENTENCES = [
    ("a sentence from this study", HUMAN, 9, 18, 0.50,
     [("The", "determiner", 0), ("parser", "noun", 0), ("joins", "verb", 1), ("two", "number", 1), ("heading", "verb", 1),
      ("lines", "noun", 0), ("into", "preposition", 1), ("one", "number", 1), ("sentence", "noun", 0), ("so", "conjunction", 1),
      ("the", "determiner", 0), ("checker", "noun", 0), ("strips", "verb", 1), ("headings", "noun", 0),
      ("before", "preposition", 1), ("it", "pronoun", 0), ("counts", "verb", 1), ("nouns", "noun", 0)]),
    ("a sentence in the register my agents write", AI, 8, 20, 0.40,
     [("This", "determiner", 1), ("change", "noun", 0), ("introduces", "verb", 1), ("a", "determiner", 0), ("unified", "adjective", 1),
      ("approach", "noun", 0), ("to", "preposition", 1), ("error", "noun", 0), ("handling", "noun", 0), ("across", "preposition", 1),
      ("the", "determiner", 0), ("service", "noun", 0), ("layer", "noun", 0), ("ensuring", "verb", 1), ("consistency", "noun", 0),
      ("and", "conjunction", 1), ("maintainability", "noun", 0), ("throughout", "preposition", 1), ("the", "determiner", 0),
      ("codebase", "noun", 0)]),
]


def idea_density_sentences():
    """Figure 11: two sentences word by word, the counted words highlighted."""
    top = 118
    char_w, size, chip_h, gap, row_h = 9.0, 15, 44, 6, 52
    blocks = []
    y = top
    for label, color, props, words, dens, tokens in SENTENCES:
        rows, x, row = [], 24, []
        for word, tag, counted in tokens:
            w = max(len(word) * char_w, len(tag) * 5.4) + 14
            if x + w > W - 24:
                rows.append(row)
                row, x = [], 24
            row.append((x, w, word, tag, counted))
            x += w + gap
        rows.append(row)
        blocks.append((label, color, props, words, dens, rows, y))
        y += 26 + len(rows) * row_h + 36
    svg = Svg(y + 56)
    legend(svg, top - 26, [("counts, in the study's sentence", HUMAN), ("counts, in the agent-register sentence", AI), ("does not count", "#c9c9c9")])
    for label, color, props, words, dens, rows, y in blocks:
        svg.rect(24, y - 10, 12, 12, color)
        svg.text(42, y, label, size=12)
        for r, row in enumerate(rows):
            ry = y + 14 + r * row_h
            for x, w, word, tag, counted in row:
                if counted:
                    svg.rect(x, ry, w, chip_h, color, 0.12)
                    svg.rect(x, ry + chip_h - 3, w, 3, color)
                svg.text(x + w / 2, ry + 19, word, size=size, fill=INK if counted else GRAY, anchor="middle",
                         weight="700" if counted else "normal")
                svg.text(x + w / 2, ry + 36, tag, size=9, fill=GRAY, anchor="middle")
        ty = y + 14 + len(rows) * row_h + 14
        svg.text(24, ty, f"{props} propositions in {words} words = {dens:.2f} ideas per word", size=13, fill=INK)
    ref_y = y + 26 + len(rows) * row_h + 22
    svg.line(24, ref_y - 16, W - 24, ref_y - 16, stroke=GRID)
    svg.text(24, ref_y, "For scale, the corpus averages from round one:", size=12)
    svg.rect(392, ref_y - 10, 12, 12, HUMAN)
    svg.text(410, ref_y, "every human register 0.50 to 0.52", size=12)
    svg.rect(660, ref_y - 10, 12, 12, AI)
    svg.text(678, ref_y, "agent documents 0.418", size=12)
    return svg.render("Idea density counts the words that carry a claim and skips the ones that only name things",
                      ["Verbs, adjectives, adverbs, prepositions, conjunctions, and numbers count as one proposition each.",
                       "Nouns, pronouns, articles, and helper verbs do not. Two sentences scored with the same port as round one."],
                      "CPIDR 3.2 port over part-of-speech tags")


FIGURES = {
    "idea-density.svg": idea_density,
    "two-sides.svg": two_sides,
    "keyness-spectrum.svg": keyness_spectrum,
    "idea-density-sentences.svg": idea_density_sentences,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, draw in FIGURES.items():
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            f.write(draw())
        print(os.path.relpath(path))


if __name__ == "__main__":
    main()
