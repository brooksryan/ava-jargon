"""Shared parts for the mechanical checkers.

Three exports carry the weight:

1. `Finding` holds one rule violation.
2. `strip_code` blanks the fenced blocks and the inline code.
3. `scan` turns one compiled pattern into a list of findings.

Every stripper replaces a span with spaces and keeps each newline. The offsets
and the line numbers of the stripped text therefore match the source text.
"""
import bisect
import re
from dataclasses import dataclass, field, replace

# --- the finding record -----------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One rule violation. The runner fills `path` after the checker returns."""

    rule: str
    line: int
    label: str
    match: str
    fix: str = ""
    path: str = "<stdin>"

    def with_path(self, path):
        return replace(self, path=path)

    def as_line(self):
        tail = f' for "{self.fix}"' if self.fix else ""
        return f'{self.path}:{self.line}: [{self.rule}] {self.label}: "{self.match}"{tail}'

    def as_dict(self):
        out = {"rule": self.rule, "path": self.path, "line": self.line,
               "label": self.label, "match": self.match}
        if self.fix:
            out["fix"] = self.fix
        return out


@dataclass
class Context:
    """The run settings that two checkers need.

    `lexicon` enables W-M10. `fields` enables P-M5. The runner skips each rule
    when its value is None. A checker appends an advisory line to `notes`, and
    the runner prints each note on stderr.
    """

    path: str = "<stdin>"
    lexicon: object = None
    fields: object = None
    notes: list = field(default_factory=list)


# --- the strippers ----------------------------------------------------------

# A fenced block opens on its own line. The block closes on the next fence,
# which Slack writes at the end of the code line instead of on its own line. An
# unclosed block runs to the end of the document.
_FENCE_RE = re.compile(r"^[ \t]*(?P<f>```+|~~~+).*?(?:(?P=f)|\Z)", re.S | re.M)
_INLINE_RE = re.compile(r"`[^`\n]+`")
_HEADING_RE = re.compile(r"^[ \t]*#{1,6}[ \t][^\n]*$", re.M)
_SETEXT_RE = re.compile(r"^[ \t]*(?:=+|-{3,})[ \t]*$", re.M)
_TABLE_RE = re.compile(r"^[ \t]*\|[^\n]*$", re.M)
_LIST_MARKER_RE = re.compile(r"^([ \t]*)(?:[-*+]|\d+[.)])[ \t]+", re.M)
_ITEM_RE = re.compile(r"^[ \t]*(?P<mark>[-*+]|(?P<num>\d+)[.)])[ \t]+(?P<body>[^\n]*)$",
                      re.M)


def blank(match):
    """Return the matched span as spaces. Each newline stays in place."""
    return re.sub(r"[^\n]", " ", match.group(0))


def strip_code(text):
    """Blank the fenced code blocks and the inline code spans."""
    return _INLINE_RE.sub(blank, _FENCE_RE.sub(blank, text))


def strip_markup(text):
    """Blank the Markdown headings, the tables, and the list markers.

    The parser joins two heading lines into one sentence, which reports a false
    noun run. This stripper removes that source of error.
    """
    text = _HEADING_RE.sub(blank, text)
    text = _SETEXT_RE.sub(blank, text)
    text = _TABLE_RE.sub(blank, text)
    return _LIST_MARKER_RE.sub(blank, text)


# --- the line map -----------------------------------------------------------


def line_starts(text):
    """Return the offset of each line start."""
    starts = [0]
    pos = text.find("\n")
    while pos != -1:
        starts.append(pos + 1)
        pos = text.find("\n", pos + 1)
    return starts


def line_of(starts, pos):
    """Return the 1-based line number for one offset."""
    return bisect.bisect_right(starts, pos)


def one_line(text, limit=80):
    """Return the text as one line. A finding always prints on one line."""
    out = re.sub(r"\s+", " ", text).strip()
    return out[:limit].rstrip()


def snippet(text, start, end, width=0):
    """Return the matched text plus `width` characters of context, on one line.

    The window opens and closes on a word boundary, so no half word prints.
    """
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    if lo > 0 and text[lo - 1].isalnum():
        while lo < start and text[lo].isalnum():
            lo += 1
    if hi < len(text) and text[hi - 1].isalnum():
        while hi > end and text[hi - 1].isalnum():
            hi -= 1
    return one_line(text[lo:hi], 200)


def scan(text, pattern, rule, label, width=0, fix=""):
    """Return one finding for each match of one compiled pattern."""
    starts = line_starts(text)
    return [Finding(rule, line_of(starts, m.start()), label,
                    snippet(text, m.start(), m.end(), width), fix)
            for m in pattern.finditer(text)]


# --- text units -------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9\"'(])")
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-_/.]*")


def split_sentences(text):
    """Split prose into sentences. Sentences of under three words drop out."""
    out = []
    for part in _SENT_SPLIT_RE.split(text):
        part = part.strip()
        if len(_WORD_RE.findall(part)) >= 3:
            out.append(part)
    return out


def count_words(text):
    """Count the words of one sentence. A hyphenated compound counts as one."""
    return len(_WORD_RE.findall(text))


def paragraphs(text):
    """Return each prose paragraph as (first_line, text).

    A block that holds a heading, a list item, a table row, or a quote is not a
    prose paragraph, so the paragraph rules never read one.
    """
    out = []
    lines = text.split("\n")
    block, first = [], 0
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if not block:
                first = i
            block.append(line)
            continue
        if block:
            out.append((first, block))
            block = []
    if block:
        out.append((first, block))
    keep = []
    for first, block in out:
        if any(re.match(r"^[ \t]*(#{1,6}[ \t]|[-*+][ \t]|\d+[.)][ \t]|>|\|)", ln)
               for ln in block):
            continue
        keep.append((first, " ".join(ln.strip() for ln in block)))
    return keep


def list_item_offsets(text):
    """Return the character offset where each list item body starts."""
    return {m.start("body") for m in _ITEM_RE.finditer(text) if m.group("body").strip()}


def list_items(text):
    """Return each list item as (line, ordered, body)."""
    starts = line_starts(text)
    out = []
    for m in _ITEM_RE.finditer(text):
        body = m.group("body").strip()
        if body:
            out.append((line_of(starts, m.start()), m.group("num") is not None, body))
    return out
