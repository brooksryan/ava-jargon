# Check definitions

DRAFT for Brooks's review. One entry per rule that `ava check` runs. Each entry states what the rule flags, one example, and how to fix it. The word lists live at the top of each rule's file under `app/checks/`; this page describes them, and the files define them.

Legend: **sets** = which `--rules` values include the rule. **needs** = an input without which the run skips the rule and names it in `rules_skipped`. **direction** = what a high rate means. `ai-high` marks an authorship signal: AI text runs high and humans run low. A band FAIL on it means the text matches the AI pattern. `human-high` marks a compliance dial: humans out-score AI on it everywhere. A band FAIL there means style drift, and the summary never claims AI authorship.

## Westinghouse rules (W-*) - every surface

Named after the Westinghouse phased plasma rifle Arnold Schwarzenegger asked for to help him defeat the robots. This is the base ruleset for filtering out common AI language. Employed by All ai-high unless the entry says otherwise.

### W-M1 dash ban
Sets: all. Flags every em dash and en dash; an en dash inside a date range passes. Connect clauses with a more appropriate separation. Example: `the timer — see below` -> `the timer (see below)`. Evidence: Humans don't usually use em or en dashes; the 0.30/1k his history once showed was pasted agent text, since removed. Agent drafts run 11-14/1k. An em dash marks pasted agent text.

### W-M2 inverted construction (partial)
Sets: all. Flags the "it is not X, it is Y" shape. The checker finds the fixed shape; a reviewer judges symmetric contrast pairs ("The tool didn't change. The workflow did."). Example: `It's not a bug, it's a feature.` -> state the one claim directly.

### W-M3 assistant phrases
Sets: all. Eleven fixed phrases that mark chat-assistant register: "Certainly", "I'd be happy to", "Great question", "Happy to help", "I hope this helps", "Let me know if you have any questions", "please don't hesitate", "I'm excited to share", "thrilled to", "In summary", "To recap". Delete the phrase; keep the content.

### W-M4 register words
Sets: all. Fifteen hype words with their inflections: delve, tapestry, seamless, robust, cutting-edge, best-in-class, world-class, leverage, utilize, unlock, synergy, passionate, spearheaded, thought leader, comprehensive. Replace with the plain verb or cut. Example: `we leverage the registry` -> `we use the registry`.

### W-M6 hedge phrases
Sets: all. Seven performative hedges: "seemed worth flagging", "for what it's worth", "just my two cents", "no urgency from me", "may or may not be useful", "I believe", "I feel that". Plain first-person uncertainty passes; the performance does not.

### W-M7 opener check (partial)
Sets: all. Flags five fixed throat-clearing openers on the first sentence, for example "I am writing to" and "I've been meaning to". A reviewer judges whether the first sentence carries the answer.

### W-M8 process language
Sets: all. Flags process residue in prose: ticket ids (`#57`, `FLEX-123`), slice/sprint/phase references, "per the PRD", "acceptance criteria", agent names, dated decision logs, and change narration ("this change adds", "now reads"). Prose states what is true about the content, not the workflow that produced it. Test: the sentence must stay true after you delete the tracker.

### W-M9 clusters
Sets: all. Flags adjacent emoji and the adjacent `!!` pair. Two exclamatory sentences are not a cluster and pass.

### W-M10 jargon score
Sets: all. Runs the jargon scorer and prints one density line on stderr. Advisory by design: never a finding, never the exit code - lexicon terms are often the document's own topic. The universal lexicon that matches the band surface loads automatically; `--lexicon PATH` overrides. `--extend NAME` overlays an extension from `ava jargon extend`: the terms its corpus uses stop counting as jargon.

### W-M11 passive voice (parser)
Sets: technical only (demoted from the universal set 2026-08-25 - passive runs 5-19/1k in normal human messages and edited prose). Direction: human-high. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags passive clauses ("the file is read by the parser"). A finding is a form note for technical docs, never AI evidence.

## Personal rules (P-*) - not in this build

The personal-voice rules (short-name preferences, watermark detection, the message input contract) are custom per author, so this build omits them. The package runs without them, and the CLI does not offer `--rules personal`. Version 3 brings them back with a build-your-own path - each author calibrates the term lists against a corpus of their own messages.

## Technical form rules (T-*) - prose next to code, docs

Simplified Technical English (STE100) form. All human-high: humans out-score AI on these rules on every surface we measured, because agents write short compliant sentences and humans do not. They measure STE compliance, never AI authorship. They also fire constantly on conversation (19-31% of chat messages); run them on documents, comments, and tickets only.

### T-M3 paragraph limit
Sets: technical. Flags a paragraph over six sentences. Split by topic.

### T-M8 approved vocabulary (partial)
Sets: technical. Flags the STE substitution list: commence/initiate -> start, perform -> do, utilize -> use, indicate/reveal -> show, approximately -> about. A reviewer judges the wider one-word-one-meaning rule.

### T-M9 idioms (partial)
Sets: technical. Flags known idioms ("touch base", "moving forward", "paint a picture"). A reviewer judges new idioms.

### T-M11 condition first
Sets: technical. In a conditional sentence the condition comes first: "If the build fails, stop." not "Stop, if the build fails."

### T-M12 numbered lists
Sets: technical. Flags a list item that joins two actions in one sentence. One action per sentence; a two-sentence item passes.

### T-M1 sentence length (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. An instruction takes 20 words maximum, a description 25. The parser classifies the sentence first, so the limits apply to the right kind. Technical names count as one word.

### T-M2 one instruction per sentence (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags a sentence with two imperative verbs. Split it.

### T-M4 simple tenses (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags perfect tenses: "has been completed", "had finished". Use simple present, past, or future.

### T-M5 no -ing main verb (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags a sentence whose main verb is an -ing form ("Running the script produces..."). Technical names and approved adjectives ("the following", "warning") pass.

### T-M7 noun clusters (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags four or more nouns in a row. Break the cluster with a preposition. Official technical names are exempt in the standard, and the checker cannot know which names are official. Expect findings on names. Judge them.

### T-M10 imperative instructions (parser)
Sets: technical. Parser tier: runs whenever spacy is installed; `--no-parser` skips it. Flags "You should X" in a list item. Write the instruction as a command: "Confirm the scope."

