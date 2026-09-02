# Maxwell OS — S5 Quarantine Batch-Adjudication Prompt (frontier-model triage)

> **Purpose:** Replace one-by-one human review of 2,793 S5-quarantined facts with a
> single batch call to a frontier model (Claude/GPT), asking the *right* question.
> You are NOT asking the model to "is this fact true?" — you are asking it to classify
> the *failure mode* so we know which of 3 fix-paths each record belongs to.
> Feed this prompt + the `quarantine_triage_sample.csv` rows (or a JSONL of the
> `fb_id, definition, mechanism, evidence_passages, source_books` fields).

---

## SYSTEM

You are a senior RAG-verification auditor. A pipeline extracted 2,793 "fact blocks" (FBs)
from a multi-source corpus and a DeBERTa NLI verifier quarantined them (entailment score
below 0.10). Your job is NOT to re-judge factual truth. Your job is to classify **why**
the entailment failed, so the correct fix path can be applied. Answer with a single label
per record and a one-line reason. Be terse and deterministic.

## CLASSIFICATION SCHEMA (pick exactly one label per record)

1. **`EVIDENCE-GARBAGE`** — the `evidence_passages` contain non-evidence fragments:
   figure captions, book/chapter titles (often with `____` or `___`), UI strings
   ("Time 3 minutes", "The cloud template…"), truncated sentences, or EPUB/Markdown
   artifacts. The real claim may be fine; the passages are not usable evidence.
   → fix = evidence-passage filter (S2), no FB rewrite needed.

2. **`SYNTHESIS-NO-SINGLE-ENTAIL`** — the definition is a *convergent synthesis* across
   multiple sources (`source_diversity >= 3`); every individual passage is genuine and
   relevant, but no *single* passage states the full generalized claim verbatim.
   → fix = B2 aggregation rule (allow cross-passage entailment / majority), no FB rewrite.

3. **`SINGLE-SOURCE-PARAPHRASE`** — `source_diversity == 1`; the definition is a
   paraphrase/abstraction of one source that does not literally entail. The source does
   support the idea, but loosely.
   → fix = evidence-side sourcing (find a 2nd corroborating source) or tighten definition.

4. **`DESCRIPTIVE-NOT-CAUSAL`** — the "mechanism" is a restatement/description, not a
   causal chain ("this is a descriptive model…", "an empirical pattern…"), so there is no
   causal claim for NLI to entail.
   → fix = mechanism rewrite (S2) or drop if not a real principle.

5. **`TRUE-CONTRADICTION`** — a *genuine, clean* evidence passage contradicts the
   definition. The FB is actually wrong.
   → fix = DROP (or correct) the FB.

6. **`REAL-UNSUPPORTED`** — the definition is a real, well-formed claim but the cited
   sources genuinely do not support it (not synthesis, not garbage — just unsupported).
   → fix = DROP or re-source.

7. **`OK-RELEASABLE`** — the FB is correct, evidence is clean, and the quarantine is a
   false negative of the NLI verifier. Recoverable as PASS.
   → fix = none (whitelist / re-verify).

## OUTPUT FORMAT

For each record, output exactly one line:
```
<fb_id>|<LABEL>|<one-line reason>
```
No prose. No hedging. If you are unsure between two labels, pick the one that determines
the *cheapest* correct fix.

## CONSTRAINTS

- Do not invent facts. Base the label ONLY on the provided definition/mechanism/evidence.
- `EVIDENCE-GARBAGE` takes priority: if any passage is obviously a caption/title/UI string,
  label it `EVIDENCE-GARBAGE` even if other passages look fine.
- Tally the labels at the end in a compact summary.

---

## EXPECTED USE

| label | action | stage |
|---|---|---|
| EVIDENCE-GARBAGE | deterministic passage filter + re-run S5 | S2 post-hoc (filter) |
| SYNTHESIS-NO-SINGLE-ENTAIL | B2 aggregation fix + re-run S5 | S5 (code) |
| SINGLE-SOURCE-PARAPHRASE | evidence-side sourcing pass | S2 re-extract |
| DESCRIPTIVE-NOT-CAUSAL | mechanism rewrite | S2 re-extract |
| TRUE-CONTRADICTION / REAL-UNSUPPORTED | drop FB | S4/S5 |
| OK-RELEASABLE | whitelist | S5 |

Run this against the **50-record stratified sample** first (20 strong/15 medium/10 weak
NEUTRAL + 5 CONTRA). The CSV MUST carry the `evidence_passages` column (verbatim passage
text) — without it, `EVIDENCE-GARBAGE`, `TRUE-CONTRADICTION`, `REAL-UNSUPPORTED`, and
`OK-RELEASABLE` are unadjudicatable (D2506: confirmed by claude0041/chatgpt0041 reviews).

Acceptance (D2506): require **per-record agreement** (Cohen's κ ≥ 0.6 across the two
frontier models), NOT merely label-distribution stability — aggregate distributions can
look identical while the models disagree on most individual records. Also: do NOT trust
`source_diversity >= 3` as the B2 synthesis discriminator until S1/S2 book-level dedup is
fixed — the field over-counts near-duplicate book files (same book, different download
source/edition), so `SYNTHESIS-NO-SINGLE-ENTAIL` may be assigned to effectively
single/double-sourced records.
