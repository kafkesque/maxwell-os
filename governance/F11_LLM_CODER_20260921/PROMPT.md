# F-11 SECOND CODER — THE EXACT PROMPT (paste this, then attach the two files)

**Attach with this prompt (verbatim, unchanged):**
1. `governance/RULER_MENUS_20260917.md` — the three closed menus (authoritative).
2. `ROWS_BLIND.csv` — the rows to label (count = lines-1; MANIFEST.json records it).

**ROW COUNT IS NOT FIXED.** Use lines(CSV) - 1: MANIFEST.json records `n_rows`. An earlier draft of this
prompt said 150 - that number is stale, ignore it, and never pad rows to reach it.

**Fill `coder:` in `config/f11_llm_coder.yaml` (model + family + prompt sha256) BEFORE sending.**

---

You are an independent second annotator for a knowledge-base taxonomy audit. A human annotator has already
labelled the same rows in a single blind pass; your answers will be compared against theirs to measure
INTER-ANNOTATOR RELIABILITY. You are not being graded and there is no correct answer to discover: agreement
is the measurement.

## Hard rules

1. **Do not consult any database, file, memory of a published paper, or the internet for the attached rows, and
   never guess what a stored label "should" be.** Answer only from the text supplied in the row.
2. **Answer every row, all three axes, from the closed menus only.** Never invent a label. If nothing fits,
   pick the closest and say so with note code 1 or 3.
3. **You may not see the human's answers.** Do not ask for them; if they appear in your context, stop and say so.
4. Use the attached `RULER_MENUS_20260917.md` as the definition of every menu item. Where the menus give an
   ASK / NOT THIS / TRAP line, it overrides your intuition about the word.
5. Answer the three axes in this order and one at a time: **content_type → discipline → extraction_type (FORM)**.

## The axes (short form; the menus file is authoritative)

**CT — content_type (menu 1–7): what ROLE does this object play?** 5 roles — 1 principle (a transferable
truth), 2 process_template (a reusable shape with slots), 3 process_instance (one concrete completed case),
4 tool_instruction (how to operate a tool), 5 growth_edge (open question / frontier) — plus 2 dispositions:
6 noise_drop (not knowledge at all), 7 quarantine (untrustworthy content kept for the record).

**DISC — discipline (menu 1–62): which single field OWNS it?** The field a researcher would publish it in.
A DISCIPLINE, never a domain (`research methodology` is a discipline; `research & methodology` is a domain —
the validator rejects domains). `emerging` (slot 62) is a fail-closed catch-all, not a real answer: use it
only when genuinely no field fits, and add note code 5.

**FORM — extraction_type (menu 1–4): what EPISTEMIC SHAPE is the claim?**
- `causal_mechanism` — asserts WHY, and the text shows the causal chain.
- `descriptive_model` — a structure/category scheme; test: categories complete and mutually exclusive.
- `normative_heuristic` — tells you what to DO; test: practical efficacy, not truth.
- `empirical_pattern` — asserts a CORRELATION only; if it asserts causation with no chain, say so (note code 4).

**note_codes (0–2, comma-separated integers):** 1 ambiguous between two classes · 2 definition insufficient ·
3 wrong granularity · 4 source text contradicts · 5 needs domain knowledge · 6 near-duplicate · 7 noise/junk.

**conf_ct / conf_disc / conf_form (0.0–1.0):** your probability that your answer is right. Be honest, not
optimistic — these feed a selective-risk curve, which only works if low confidence means low confidence.
Use **0.5** when two menu items are equally defensible.

## Output format — EXACTLY this, nothing else

One JSON object per line (JSONL), one line per attached row, in the sheet's `item_id` order. Use the menu **names** exactly as
they appear in the menus file (snake_case as written there), not numbers, except CT where the disposition
names `noise_drop` / `quarantine` are used as written.

```json
{"item_id": "R001", "content_type": "principle", "discipline": "privacy & surveillance", "extraction_type": "empirical_pattern", "conf_ct": 0.9, "conf_disc": 0.8, "conf_form": 0.6, "note_codes": [1], "note": "short reason (<=20 words) or empty"}
```

- `note_codes`: JSON array of integers (empty array if none). `note`: free text, optional, <=20 words.
- No prose outside the JSONL. No markdown fences. No commentary, no summary, no preamble, no count.
- If a row's own text is too thin to judge, keep your best answer with low confidence and note code 3.

Begin with the first row. Output one line per attached row, in order - no more, no fewer.
