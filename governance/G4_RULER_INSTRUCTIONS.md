# G4 — CERTIFY THE RULER: your instruction file

**Owner of the human work:** you. **Everything else in this file is already built and verified.**
**Status:** ready as of 2026-09-17. **Scripts:** R5 gemma-4-E4B APPROVE (`a3a5da9f6658bd95`, `16b91f133abf382a`).

---

## 0. Why this is the #1 task (one paragraph)

Every axis in this system currently measures **0.000 human-BLIND** — the labels we trust were produced by
the very models we are trying to evaluate. That is circular, so the floors in `config/eval_integrity.yaml`
(0.60 content_type / 0.60 discipline / 0.50 depth / 0.50 domains / 0.60 extraction_type) cannot be evaluated,
and **no model assignment, no 3,348-row relabel and no rerun can be *approved* — only asserted.** This sheet
converts that into a bounded, one-pass human job. One sitting produces: the certified reference (ruler), the
measured accuracy of the stored labels, and a direct test of the largest defect in the KB (F-14).

## 1. The artifacts (all exist now)

| what | path | who opens it |
|---|---|---|
| **the sheet you fill** | `governance/RULER_BLIND_SHEET_20260917.csv` | **YOU** (Numbers / Excel) |
| the menus you answer from | `governance/RULER_MENUS_20260917.md` | YOU (read-only reference) |
| the answer key | `governance/ruler_sheet_key_20260917.json` | **NOBODY while labelling** — it holds the stored labels and would destroy blindness |
| completeness check | `python3 scripts/build_ruler_sheet.py --validate` | you (one command, after filling) |
| scoring | `python3 scripts/score_ruler_labels.py` | you (one command) |
| the output you then read | `governance/ruler_measurement_20260917.md` | you + me |

**Blindness is the whole point.** Do not open the key, do not query the DB for these rows, do not look up
the object's existing label. Verified: the sheet contains **zero** stored-label columns — only the object's
own text plus empty answer cells.

## 2. What is in the sheet (150 rows, two strata)

| stratum | n | why it exists | may the FLOOR be measured on it? |
|---|---|---|---|
| **A — proportional** | **100** | a faithful sample of the KB's content_type mix (largest-remainder: 83 principle / 13 noise_drop / 2 process_template / 2 process_instance) | **YES — the only stratum the floor may use** |
| **B — forced-minority** | **50** | all 6 minority content_types (6 each), 8 rare-discipline rows, **6 rows from the F-14 untraceable pocket** | **NO** — deliberately not proportional; scoring it as raw accuracy would repeat the majority-class mistake (BUG-269) |

Rows were shuffled after sampling, so the order tells you nothing. Every row verified to carry ≥200
characters of judgeable text (0 of 7,995 rows are thinner than that — BUG-268's pre-flight condition).

## 3. Before you start — the five rules that make the result valid

1. **One pass, no lookups.** If you look up the existing label, the measurement is worthless (it becomes
   attested, not blind, and the tier vocabulary treats those as different data).
2. **Answer ONLY from the numbers in the menus.** Never invent a label. If nothing fits, pick the closest
   and say so with note code 1 or 3.
3. **Answer all three axes on every row** you answer (CT, DISC, FORM). A half-answered row is not scorable.
4. **You may stop early — that is designed in, not a failure.** See §6 (the stop rule). The scorer refuses
   an incomplete sheet precisely so that a partial pass cannot be mistaken for a full one.
5. **Blank is allowed to mean "skip this row"** at the end; the scorer will refuse until you either answer
   it or delete the row.

## 4. The procedure (step by step)

**Step 1 — open the menus (5 min).** `governance/RULER_MENUS_20260917.md`. Three menus:
`content_type` 1–7, `discipline` 1–62, `extraction_type` (FORM) 1–4.

**Step 2 — open the sheet.** `governance/RULER_BLIND_SHEET_20260917.csv` in Numbers or Excel.
Columns are readable in the order you need them: `name`, `DEFINITION`, `APPLICATION`, `MECHANISM`,
`BOUNDARY`, `SOURCE EXCERPT`, then the answer columns.

**Step 3 — answer session 1: rows R001–R050 (~2 hours).** Fill for each row:
`CT (1-7)`, `DISC (1-62)`, `FORM (1-4)`, `conf_ct`, `conf_disc`, `conf_form` (0.0–1.0), `note_codes`
(0–2 codes, comma-separated), `reviewer`, `date`.

**Step 4 — score the partial pass (1 min).** Two commands:

```bash
python3 scripts/build_ruler_sheet.py --validate    # completeness + menu ranges + namespace check
python3 scripts/score_ruler_labels.py              # refuses unless ALL 150 rows are answered
```

Because the scorer refuses a partial sheet, the interim signal comes from `--validate` plus the raw counts.
If you want a formal interim verdict at 50 rows, say so and I will add a `--partial` mode (2 min of work).

**Step 5 — decide: continue to 150, or stop.** Use the stop rule in §6.

**Step 6 — final scoring, then hand it to me.** The measurement lands in
`governance/ruler_measurement_20260917.md`. I then: repoint the floors at the certified core (see §7),
stamp the 150 rows as `human-blind`, and unblock the F-14 repair + retrain decisions.

## 5. How to answer each axis (the actual decision rules)

**Full definitions, per-item ASK / NOT THIS / TRAP lines, near-neighbour NOT lists and a real worked
example are in `governance/RULER_MENUS_20260917.md`** (regenerated from config, never hand-edited).
What follows is the short version.

**CT — content_type: what ROLE does this object play?** 1–7 = **5 roles** (1 principle, 2 process_template, 3 process_instance,
4 tool_instruction, 5 growth_edge) + **2 dispositions** (6 noise_drop, 7 quarantine). A role says what the object IS; a disposition says it carries no role and must be dropped or held. Ask: *is this a principle (a transferable truth),
a template (a reusable shape with slots), an instance (one concrete completed case), an instruction (how to
operate a tool), a growth edge (an open question / frontier), noise (not knowledge at all), or quarantine
(untrustworthy content kept for the record)?*

**DISC — discipline: ONE canonical field.** 1–62 from the menu (61 canonical + `emerging`). Pick the field a
researcher would publish it in. **Never** put a domain name here: `validate_discipline_domain` enforces the
namespace and `--validate` will reject it. `emerging` is a fail-closed catch-all, not a real answer — use it
only when genuinely no field fits, and add note code 5.

**FORM — extraction_type: what EPISTEMIC SHAPE is the claim?** 1–4:
- `causal_mechanism` — asserts WHY, and the evidence must show the causal chain.
- `descriptive_model` — a structure/category scheme; the test is: categories complete + mutually exclusive.
- `normative_heuristic` — tells you what to DO; the test is practical efficacy, not truth.
- `empirical_pattern` — asserts a CORRELATION only; if it asserts causation without a chain, say so (note 4).

**note_codes** (numbered, max 2): 1 ambiguous between two classes · 2 definition shown insufficient ·
3 wrong granularity · 4 source text contradicts · 5 needs domain knowledge · 6 near-duplicate of another
item · 7 noise/junk.

**conf_***: your probability that the answer is right (0.0–1.0). Be honest, not optimistic — these feed a
selective-risk curve and a conformal threshold, which only work if low confidence means low confidence.

## 6. Time budget and the stop rule

| segment | rows | estimated |
|---|---|---|
| CT per row | — | ~40 s |
| DISC per row | — | ~60 s |
| FORM per row | — | ~60 s |
| **per row total** | — | **~2.7 min** |
| session 1 | 50 | **~2 h 15 min** |
| session 2 | 50 | ~2 h 15 min |
| session 3 | 50 | ~2 h 15 min |
| **full sheet** | **150** | **~6 h 45 min** |

**Stop rule (A1 sequential, config-driven):** after **≥60 stratum-A rows**, if the measured accuracy sits at
least **0.10** away from the floor for that axis, the verdict is *decisive* — stop. If it is inside that
margin, continue. In practice: **50 rows is a legitimate stopping point if the picture is clear**, and the
last 50 rows (stratum B) are optional extras that buy per-class detail and the F-14 test.

## 7. What your answers change (and the one decision they create)

- The 150 rows become **`human-blind`** — the strongest provenance tier (today there are **zero** such rows).
- The stored labels' accuracy becomes **measured with an interval**, beside the constant-answer baseline, on
  the proportional stratum only.
- **The F-14 test:** the untraceable pocket is **50.7% of the KB**, so it appears **83 times** in this sheet
  (not 6 — that was my earlier estimate and it was wrong). The scorer compares untraceable vs traceable
  **within stratum A**, where both sides come from the same sampling frame, so we learn whether the 4,054-row
  pre-repair pocket is actually mislabelled — the cheapest possible probe of the KB's largest defect.
- **Decision D-G4a (yours, one line):** the floors currently divide over the 251-row anchor
  (`governance/gold_4axis.jsonl`). The certified core is a better denominator because it is blind by
  construction. **My recommendation: repoint the floors at the certified core, keep the anchor for eval.**
  Until you rule, both are reported and neither is silently swapped.

## 8. Why FORM is in this batch (your question)

You are **not** being asked to *decide* about FORM. Three separate things were being conflated:

1. **LABEL it (60 s/row) — yes, this is yours.** FORM is the one axis with **zero** human data: 0 of 251 in
   the anchor, 0 of 1,027 in the silver set. Its floor (0.60) cannot even be *evaluated* today, which is why
   it appears in this sheet.
2. **ONE binary governance call — D-G2a, already open.** The F-14 repair touches 3,348 rows plus 591 junk
   rows (`noise_drop` 572 + `quarantine` 19); the question is *exclude or delete* those 591. It is yours
   because it is destructive, and per the standing rule a destructive operation is never gated by a model.
   **Recommendation: exclude + flag now, deletion its own decision later (R-D410).**
3. **Wiring FORM to a verifier (F-15) and running the 3,348-row repair — NOT yours.** My work.

**Why it matters at all:** FORM is the axis where the KB is *provably* wrong. Measured: 4,054 rows (49.9% of
the KB) serve a pre-repair distribution (causal_mechanism **55.8%**) while every one of them reports
`classification_status=CLEAN`, against 8.8% causal in the traceable generation — and `causal_mechanism` is a
known S2 bias. FORM is also what an epistemic verifier would consume; with no consumer it is decorative
(F-15), and with 0% human data it is unfalsifiable. This sheet is what makes it both.

## 9. Troubleshooting

- **"This row looks like junk."** Good — that is information. Answer CT=6 (noise_drop) or 7 (quarantine),
  or note code 7.
- **"I disagree with how I labelled this earlier."** Answer as you see it now, blind. That disagreement is
  the measurement, not a mistake.
- **"Two menus seem to fit."** Pick the closer one, confidence ~0.5, note code 1.
- **"A discipline I need is missing."** Use the closest canonical field and note code 5. Do not invent
  labels — an invented label is a taxonomy change, which is a separate, gated decision (and renames are
  frozen under D-271c).
- **Numbers/Excel changed my leading zeros or turned `1-7` into a date.** Answer cells are plain integers;
  if your editor reformats them, save as CSV with text-format columns.
- **`--validate` complains about a discipline resolving to a domain.** That is the namespace guard working:
  pick the discipline, not the domain (e.g. `research methodology` is a discipline; `research & methodology`
  is a domain).

## 10. The single next action

```bash
open governance/RULER_MENUS_20260917.md                 # read the three menus
open governance/RULER_BLIND_SHEET_20260917.csv          # fill R001-R050 in one sitting
python3 scripts/build_ruler_sheet.py --validate         # then
python3 scripts/score_ruler_labels.py                   # (needs all 150 rows)
```

Do not open `governance/ruler_sheet_key_20260917.json`.
