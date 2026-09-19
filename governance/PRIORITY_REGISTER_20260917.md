# PRIORITY REGISTER — the critical items in strategically consequential order (2026-09-17)

Ranked by **consequence**, not by effort or by recency. Each row names what it unblocks, and whether a human
is required (nothing below can be delegated if the human cell says HUMAN). Companion to
`PRIORITY_DECISION_20260917.md` (which set the sequence) and `CONTEXT_INDEX.md` (which holds the recall map).

| # | item | type | unblocks | human? | effort |
|---|---|---|---|---|---|
| **1** | **G4 — certify the RULER: 100–150 blind human labels on content_type + discipline + FORM** | task | **everything measurable**: P2/P3 role consolidation, F-14 relabels, ModernBERT/DSPy, the S2→S6 rerun. Every axis reads **0.000 blind** against floors of 0.6/0.6/0.6/0.5/0.5, so today no model, relabel or rerun can be *approved* — only asserted | **YES** | ~3–4 h labelling + instrument build (build is mine) |
| **2** | **BUG-276 — restore the safety net** (C13's `backup_guardian.sh` is dead; the DB has **no** automated backup) **+ F-08 disk** (46 GiB free vs floor 150) | bug | safe execution of #3 and #5, both of which are **bulk writes** (164,202 edges; 3,348 relabels) | no | hours |
| **3** | **D-271c — implement the identity layer** (`concept_id` + authority control + re-key the 164,202 edges) under the rename freeze | task | reversibility of *every* future taxonomy decision; removes the latent tax (one rename orphans **320 edges**) | no (gated on G8 ratification) | 1–2 days |
| **4** | **F-02 — provenance on every relabel path** | task | #5, and the root cause of the circular anchor (F-05/F-16) | no | hours |
| **5** | **F-14 — FORM re-derivation for 3,348 rows + 115 to review** (with #4's provenance) | task | the largest data-integrity defect: **4,054 rows (49.9% of the KB)** serve a pre-repair distribution while reporting CLEAN | D-G2a only (exclude vs delete the 591 junk) | 2–3 days |
| **6** | **Decision queue** — ratify D-271a (revised), D-271b, D-271c, D-G2a, D-G2b, D-G3a, D-G3b, G1, G5–G7 | decision | #3 and #5 (they are blocked on paperwork, not work) | **YES**, minutes each | minutes |
| **7** | **F-15 + T3/T6 mechanisation** — give FORM a consumer (per-FORM `verification_standard` at the S5 wiring point) and mechanise the D2587 step/verb boundary for T3 | task | verifiable FORM and content_type; replaces the cancelled ~650-call judge swap (BUG-269: only T1 survives, gemma 1.000 vs 0.571 baseline) | no | 1–2 days |
| **8** | **P2/P3 model-role consolidation (G5)** — 19 uncited roles; the live `S4_CLASSIFIER` conflict (gpt-oss on n=60 vs the 251-row voting study ranking it 4th of 6, *below* gemma); the tier-A run is **DEAD** (PID 70847 gone, checkpoint 4,260 rows, last write 9 h ago) → decide resume vs abandon; granite-4.2-8b now questionable for R5 family diversity | decision + task | a coherent, citable model map | **YES** (approve the map) | 1 day + GPU |
| **9** | **F-06 + F-11** — harness contract test; one shared response reader (content/tool_calls/reasoning_content) | task | the BUG-262..266 class; the corrected defects (gpt-oss "33% parse failure" was a harness artifact; `guided_grammar_enabled` is a no-op without a per-request json_schema) | no | ~1 day |
| **10** | **Data-quality tail** — BUG-273 (domains contract 1..3 vs **up to 7** on 1,002 rows), BUG-274 (`related_fbs` **56.8% asymmetric**, 88,592 one-way edges + 7 self-references), F-13 tree drift, F-12 vote partition, F-08 retention | bug | consistency of the facets and the graph | no | 1 day |

## Which is the most important

**#1 — G4, certify the ruler.** One sentence: *you cannot approve a model assignment, a 3,348-row relabel, or
a 40–52 h rerun against a ruler that has never been calibrated by a human.* Every other row in this table
either **feeds** the ruler (T3 108 + T6 69 + T2 triage ≈ 177 rows, of which 166 already feed G4 — they are the
same work) or is **measured by** it.

## What I would do first in wall-clock terms (no human available now)

**#2 then #3.** #2 has the highest consequence-per-hour in the register and protects #3 and #5; #3 is the only
preventive item and is almost entirely deterministic. Both are no-human, so they can proceed while #1 waits
for you — and neither can start a stage, so neither violates the "fix the ruler first" ruling.

## Standing rules that outrank all of the above

- **Rename freeze** (D-271c, in force in `config/identity.yaml`): no renames of object names, discipline,
  domain or content_type until the identity layer exists.
- **LINK, never MERGE**; and LINK must also set `status='QUARANTINE'` (`duplicate_of` has no reader).
- **Fail closed on unknown**; **a design state is not a violation**; **no spotless without a number**;
  **quote the measured population, not the felt one**.
- Any **destructive** operation may never be gated by a judge that does not beat the constant-answer baseline.
