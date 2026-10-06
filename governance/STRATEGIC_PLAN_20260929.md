# STRATEGIC PLAN — 208 anchors + 7,995-object corpus (2026-09-29)

> Source of truth: `CONSTITUTION.md`. This plan supersedes the Phase wording in
> earlier handoffs on one point only — **triage precedes repair** (Phase 0, below).
> It is append-only over `STRATEGIC_PLAN_20260917.md`; nothing in the frozen
> 150/208 verdicts changes.

---

## 0. The Phase-0 correction (your question, answered)

You asked: *"shouldn't it be first to see which object out of the 208 is worth
keeping and which is drift results?"* — **Yes. You are right, and my earlier
"repair, don't blindly rerun" phrasing collapsed two distinct decisions into one.**

The correct order is **TRIAGE → REPAIR-OR-DROP**, not "repair everything":

1. **Triage (keep vs drop).** For each of the 208 anchors, answer one binary
   question: *is the definition faithful to its own `evidence_passages`, or is it
   drift?* Drift = the definition asserts a claim the evidence never makes
   (R013 invented "business-unit managers" + "performance targets"; R025
   over-claimed from a bibliographic blurb; R017 over-abstracted a first-person
   account). This is decided by an evidence-fidelity gate, **not** by a human
   eyeballing 208 rows.
2. **Dispose of drift.** A drift object is not "repaired" — it is quarantined or
   dropped. Regenerating garbage produces different garbage; the cost is nonzero
   and the value is zero.
3. **Repair only the keepers whose evidence is *recoverable*.** Two sub-cases:
   - *Evidence present but definition drifted* → regenerate quote-first from the
     surviving verbatim passages, preserving the human-locked 5-axis verdicts.
   - *Evidence truncated/contaminated* (R017 cut mid-sentence; `source_text`
     stores "[title] + echo" not verbatim) → recover raw text from stage0/stage1
     first, **then** regenerate. Never regenerate where evidence is absent.

So the two buckets I conflated are actually three: **keep-as-is / keep-and-repair
/ drop**. The triage gate is what tells them apart.

**Triage signal (local, no rerun):** a definition-vs-evidence faithfulness pass —
NLI entailment + an entity/dimension-mutation check + a truncation check. This is
exactly the Phase-2 meter, run on 208 rows first as a one-off, then on 7,995.

---

## 1. Market research: what to adopt, what to skip

The prior survey listed RAGAS faithfulness / HHEM-2.1-Open, FActScore, RARR,
FRONT, ALCE, and NLI factual-consistency. **Pragmatic verdict: adopt one model
and one idea; reuse what you already have; reject the frameworks.**

| Candidate | Verdict | Why |
|---|---|---|
| **HHEM-2.1-Open** (Vectara) | **ADOPT** | ~1.4B T5-based fact-consistency scorer. Runs local (C1/C3), small, purpose-built for "is this summary faithful to this source". Drop-in for the definition-vs-evidence triage gate. The one net-new model worth adding. |
| **FActScore** — *atomic-fact decomposition* | **ADOPT the idea** | Decompose a definition into atomic claims and verify each against evidence. This is the correct *granularity* for the triage. Skip the pipeline (Wikipedia-scale corpus + GPT-4 API assumptions). |
| **DeBERTa-v3-large NLI** | **REUSE** | Already in-house (`MoritzLaurer/DeBERTa-v3-large-mnli-...`, the S5 verifier, D2298). This *is* the local NLI factual-consistency tool. No purchase needed. |
| **RARR** — attribution + edit | **SKIP (already planned)** | Its "edit to be faithful" step = quote-first regeneration, which is Phase-1 of this plan. The concept is already in the roadmap. |
| **RAGAS (full framework)** | **REJECT** | RAG-eval harness, API-centric, overkill. The only useful atom inside it (faithfulness) is HHEM. |
| **FRONT / ALCE** | **REFERENCE ONLY** | Research benchmarks / datasets for hallucination. Cite for test design; do not integrate. |

**Bottom line:** the corpus problem is *grounding*, not retrieval. You need one
local fact-consistency scorer (HHEM-2.1-Open) and one granularity (FActScore's
atomic facts), wired behind the NLI you already run. Nothing here is a
lock-in risk; all are local or already local.

---

## 2. The plan (5 phases + 1 governance swimlane)

### Phase 0 — FREEZE & TRIAGE the 208 anchors *(this week)*
- The 208 (150 locked + 58 dedup'd extras) are **frozen** as the seed set.
- Run the evidence-fidelity triage gate over the 208 (HHEM/DeBERTa + mutation +
  truncation check). Output a ranked **keep / keep-and-repair / drop** list.
- Drop/quarantine the drift subset; **do not** spend repair budget on it.

### Phase 1 — FIX THE GENERATOR before scaling *(commit a decision)*
- S2 becomes **quote-first / grounding-first**: a claim may only enter the
  definition if a verbatim passage entails it.
- **Generation-time NLI entailment gate** at the S2/S4 write boundary.
- Repair `source_text` (store raw verbatim, not "[title] + echo" — BUG-288).
- Complete-sentence evidence truncation (fix R017-class mid-word cuts).
- Harden `is_summary` (fix R025-class blurb promotion — BUG-304/303 root).

### Phase 2 — MEASURE drift at scale via NLI, not a full rerun
- Run the same triage gate over all **7,995 fbs**. Rank at-risk objects.
- This *measures* drift (how much of the 37% quarantine + the PASS set is
  unfaithful) without discarding human verdicts.

### Phase 3 — RE-CLASSIFY with the closed menus, seeded by the 208
- Seed the classifier with the frozen 208 anchors, then re-label all 7,995:
  `content_type` (5-value menu + `noise_drop`/`quarantine` dispositions),
  `extraction_type` (4-value FORM), `discipline` (61), `depth` (4), `domain` (44).
- This closes BUG-304 (over-called `principle`), BUG-303 (over-claimed
  `causal_mechanism`), BUG-280 (single-valued role / undefined depth).

### Phase 4 — COMMIT & SERVE
- Commit to SQLite (sqlite-vec) + Parquet, stamped (schema_version, gen_model,
  pipeline_commit — R14).
- Serve behind a *verification-verdict* gate, not a label (BUG-299).

### Governance swimlane (separate, still owed)
- **BUG-593** (mutation-gate fixture carries one commit → limb (iv) unsatisfiable)
  blocks **BUG-559** (receipt-provenance store/prose half). Drain 593 → 559.
- **widening_log owed**: `MASTER-TASK-REGISTER.md` and `agent/session_seed.yaml`
  each need a recorded widening_log entry (both sit outside `may_touch`).
- **leak-scan declared home** owed since D-2686.

---

## 3. Governance supersession audit (bugs / decisions / tasks)

The 210→208 consolidation and the closed-menu work **supersede** several open
bugs. Recommended transitions (owner-ratify before the parser regenerates):

### Recommend mark SUPERSEDED (superseding artifact shown)
| Bug | Was | Superseded by |
|---|---|---|
| BUG-273 | domains axis violates cardinality | `config/closed_menu_v5.json` (44-domain menu) + 208-anchor domain adjudication |
| BUG-277 | content_type mixes two vocabularies, "7 values" | closed 5-value CT menu + dispositions |
| BUG-415 | depth has no anchor row | 208-anchor depth adjudication (this session) |
| BUG-416 | depth axis is not a menu | closed 4-class depth menu |
| BUG-425 | domains owned by a different cohort | domain ownership reconciled this session |
| BUG-426 | "150 domain never asked" vs "was done" | domain column resolved (150 in `anchor ruler final 5.csv`; 60 in workbook) |
| BUG-431 | FORM refreshed from ruler_raw | workbook FORM now adjudicated |
| BUG-450 | FORM carries 150 labels, void rater provenance | workbook FORM now carries model provenance |
| BUG-464 | stale `owner_answer_needed` snapshot | 208-row consolidation |
| BUG-466 | 148 vs 150 rows, no exclusion rule | 208 = 150 + 58, dedup rule explicit (R161/R194 stripped) |

### Still OPEN, scoped to the 7,995 (not the anchors)
- BUG-288 (`source_text` not source) → Phase 1.
- BUG-303 (extraction_type over-claims causal_mechanism) → Phase 1/3.
- BUG-304 (content_type over-calls principle) → Phase 3.
- BUG-280 (single-valued role, undefined depth) → Phase 3.
- BUG-299 (serving gate is a label, not a verdict) → Phase 4.

### Governance swimlane (still OPEN, separate from product lane)
- BUG-559, BUG-593, BUG-400 (Dropbox File Provider, C3/C22), plus the owed
  widening_log and leak-scan entries.

> Decisions (D2000–D2700) are append-only and amended, not "superseded"; none
> require status flips. The task register still carries stale "Next:" lines
> (BUG-356) and the two widening_log owes above — those are the task-level updates.

---

## 4. What I did this turn (workbook)

`governance/frontier_audit/REVIEW_WORKBOOK_210.csv` → **208 rows**. Fixes applied:
- **Stripped duplicates** R161 (=R055) and R194 (=R041).
- **Typos:** R028/R052 `specilazed`→`specialized`; R134 `normative heuristic`→`normative_heuristic`; R205 trailing-space; R012 `noise drop`→`noise_drop`.
- **Off-menu domain:** R152 `economics`→`industrial design` (majority).
- **Multi-label domain (cross-domain MAJORITY):** R157, R188, R204.
- **Notes:** R153, R186, R189.
- **Filled deterministic majority gaps:** R180 `depth`→`domain`; R200 `disc`→`strategic thinking`.

**Flagged, left as prior-agreed (150 group — did not touch):** `disc_final`
values `emerging` (R052/059/084/091/128/140/148) and `personal productivity`
(R117/148) are off the 61-discipline menu. These read as "held/undecidable"
dispositions (cf. R051 note "held emerging"), but `personal productivity` is a
domain, not a discipline. Recommend a one-line owner ruling before Phase-3 seed.
