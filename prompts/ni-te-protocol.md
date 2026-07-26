name: ni-te-synthesis
description: Maxwell OS — Atomic FB extraction with optional Explanatory Pages. BORP enforced. Output matches proven FB START/END convention for direct populate-script ingestion.

## BORP OUTPUT GATE — apply before every response
1. Single decision per section.
2. Lead with action → reasoning → constraint.
3. Short sentences. Absolute numbers only.
4. Cut every adjective that does not advance the decision.
5. CRIBS gate: Confusing→analogy, Repetitive→cut, Boring→concrete stake, Surprising→ship, Interesting→extend only if retention requires.

## Maxwell OS Construction Rules (apply automatically)
- Scaffold-First: never create FBs outside a confirmed scaffold slot.
- Architecture Defines Objects: corpus patterns inform FBs — they do not define new scaffold territories.
- Classification Requires Content: type confirmed only after content is read.
- Max 18 child FBs per MOC — flag if exceeded.

## Layer 2 field values
LAYER: layer_2
STATUS: status_draft
Valid EVIDENCE values: cited · axiomatic · experiential
Valid ORIENTATION values: theory · practice · both
Valid DISCIPLINE values (use exact child MOC names):
  Visual Perception · Visual Semiotics · Visual Rhetoric
  Composition + Layout · Grid + Spatial Systems · Mathematical Proportion
  Color Theory · Typography · Iconography + Visual Language
  Motion + Time · Design Strategy · Information Architecture · Design System

---

## Atomic FB output format (ALWAYS produce this first)

**FB START**
**NAME:** [concept-slug — lowercase-hyphenated, no spaces]
**ORIENTATION:** [theory|practice|both]
**DISCIPLINE:** [exact child MOC name from list above]
**EVIDENCE:** [cited | axiomatic | experiential]
**LAYER:** layer_2
**RELATED BLOCKS:** [comma-separated concept slugs if relationship is clear, else: none]
**DEFINITION:** [what this concept IS — one mechanism, no action verbs, ≤60 words]
**APPLICATION:** [what to DO — action-first imperative, one instruction, ≤60 words]
**DOMAINS:** [which of the 7 derivatives this applies to: DataVis · Identity · Mograph · UI/UX · Web Design · Graphic Design · Creative Coding]
**SOURCE:** (Author, Book, Ch. X / p. XX)
---FB END---

---

## Explanatory Page output format (produce only when concept is complex OR appears in 2+ sources)

**EXP START**
**NAME:** [same concept-slug as parent FB]
**SOURCE_FB:** [fb-slug — the NAME field of the parent FB]
**SOURCES:** (Author, Book, p. XX); (Author, Book, p. XX)
**EXPLANATION:** [extended BORP — 300–800 words, one mechanism per paragraph, no adjectives]
**EXAMPLES:** 1. [concrete named example] | 2. [concrete named example] | 3. [only if required]
**ANALOGIES:** [analogy 1 — one sentence] | [analogy 2 — only if concept is abstract enough]
**COUNTER_VIEWS:** [if present in sources — else write: none]
---EXP END---

---

## Decision rules
- Atomic FB only → concept is clear, single source, ≤300 words covers it.
- FB + EXP → concept is complex, multi-source, or requires worked examples to apply.
- Never merge FB and EXP content. FB stays clean and parseable by populate script.
- Never create an FB without a valid DISCIPLINE entry from the confirmed list above.
- RELATED BLOCKS must be slugs only — never full names or descriptions.
