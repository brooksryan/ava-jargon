"""The tier 2 package. The `spacy` import lives here and nowhere else.

The caller tests `available()` before it runs a tier 2 checker. Tier 1 runs
without `spacy`, so the CLI keeps the standard-library floor.

Every tier 2 checker reads one document from `doc_of`. That document comes from
`strip_markup(strip_code(text))`: the fenced code, the headings, the table rows,
and the list markers are blank. The blanks hold their length, so a character
offset in the document is a character offset in the source text.
"""
import re

from ..common import list_item_offsets, strip_code, strip_markup

try:
    import spacy
    HAVE_SPACY = True
except ImportError:  # tier 1 still runs
    spacy = None
    HAVE_SPACY = False

MODEL = "en_core_web_sm"
BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")

_ITEM_STARTS = set()

if HAVE_SPACY:

    @spacy.Language.component("block_boundaries")
    def block_boundaries(doc):
        """Start a new sentence at a blank line and at a list item.

        A Markdown paragraph ends on a blank line, and a list item often carries
        no full stop. Without these boundaries the parser joins two blocks into
        one sentence, which reports a false length and a false noun run.
        """
        text = doc.text  # one build; per-token access rebuilds the string, O(n^2)
        last_end = 0
        for token in doc:
            if token.is_space:
                continue
            if last_end and (token.idx in _ITEM_STARTS
                             or BLANK_LINE_RE.search(text[last_end:token.idx])):
                token.is_sent_start = True
            last_end = token.idx + len(token.text)
        return doc

_NLP = None
_REASON = ""
_CACHE = (None, None)


def available():
    """Return (ready, reason). The reason names the missing part."""
    if load() is not None:
        return True, ""
    return False, _REASON


def load():
    """Load the pipeline once. Return None when the pipeline is absent."""
    global _NLP, _REASON
    if _NLP is not None:
        return _NLP
    if not HAVE_SPACY:
        _REASON = "spacy is not installed"
        return None
    try:
        _NLP = spacy.load(MODEL, disable=["ner"])
    except OSError:
        _REASON = f"the {MODEL} model is not installed"
        return None
    _NLP.add_pipe("block_boundaries", before="parser")
    return _NLP


def doc_of(text):
    """Return the parsed document for one source text, or None."""
    global _CACHE, _ITEM_STARTS
    nlp = load()
    if nlp is None:
        return None
    coded = strip_code(text)
    body = strip_markup(coded)
    if _CACHE[0] == body:
        return _CACHE[1]
    _ITEM_STARTS = list_item_offsets(coded)
    doc = nlp(body)
    _CACHE = (body, doc)
    return doc


def parse_fragment(text):
    """Parse one list item. Return None when the pipeline is absent."""
    nlp = load()
    return nlp(text) if nlp is not None else None


def sentences(doc):
    """Return each sentence that holds three words or more."""
    out = []
    for sent in doc.sents:
        words = [t for t in sent if not t.is_space and not t.is_punct]
        if len(words) >= 3:
            out.append(sent)
    return out


def is_imperative(sent):
    """Test the root verb for the imperative form.

    An imperative root is a base-form verb with no subject.
    """
    root = sent.root
    if root.pos_ not in ("VERB", "AUX") or root.tag_ != "VB":
        return False
    return not any(child.dep_ in ("nsubj", "nsubjpass", "expl") for child in root.children)
