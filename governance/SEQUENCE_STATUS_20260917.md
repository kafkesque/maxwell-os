> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Part of the 2026-09-17 report set.
> Floors, provenance vocabulary and the calibration decision rule live in
> `config/eval_integrity.yaml` — never restate them here, cite the path.

# SEQUENCE STATUS — 2026-09-17

> **This is the execution tracker. The HUMAN GATE REGISTER at the bottom is the authoritative list
> of everything waiting on a person.**

## The ruled sequence (from `PRIORITY_DECISION_20260917.md`)

Order is not arbitrary: each step makes the next one **measurable**. Ruler -> instrument -> repairs
-> axis 5 -> freeze -> re-verify -> *only then* retrain / rerun.

| # | step | cost | status | notes |
|---|---|---|---|---|
| 1 | **BUG-267 / F-16 fix** — exact-match provenance tiers, blind vs attested, fail closed | 0 model | ✅ **DONE** | `_tier()` substring test replaced; `human-blind` tier declared (0 rows — the honest number); unregistered source now fails closed |
| 2 | **Judge calibration** (G3) | 72 calls + HUMAN | ✅ **DONE 2026-09-17** | 36/36 answered blind. Only **T1 dedup** yields a usable judge (gemma, 1.000 vs 0.571 baseline). T2/T3/T6 **degenerate** — no judge beats a constant answer |
| 3 | **F-14 decision gate** (G2) | 0 model + HUMAN | ✅ **DONE 2026-09-17** | 30/30 answered: keep 18 / quarantine 8 / retire 4. Junk is already labelled junk -> scope narrows to **3,348 relabel / 591 excluded / 115 to review**. Awaiting ratification (D-G2) |
| 4 | **Free repairs** — F-03, F-11, F-06 | 0 model | 🟡 **PARTIAL** | **F-03 RE-SCOPED AND DONE** (see below); F-11 + F-06 still open |
| 5 | **Certified eval core** (G4) — blind human labels, n=100-150 | 6-10 h HUMAN | ⏸ not started | concentrated on content_type + discipline + FORM; depth/domains already at floor |
| 6 | **P2 freeze** (G5) + R5 re-verification | 1 h + **~299 calls only** | 🔁 **SCOPE REVISED** | the ~650-call swap is cancelled: T2 -> **deterministic string test** (0 calls), T3 -> mechanise the D2587 step boundary then judge the residue, T6 -> requires the F-15 per-FORM `verification_standard` first. Only T1 (299 dedup calls) is re-judged |
| 7 | **F-14 run** — re-derive FORM for the orphans with provenance | ~2.5-3 h model | ⏸ | **needs F-02 provenance first + the G2 ruling** |
| 8 | ModernBERT retrain / DSPy / S2->S6 rerun | 40-52 h | 🔒 **GATED** | do not start while a floor is unmet (do-not list) |

## Done this session (2026-09-17, after the priority ruling)

- **BUG-267 / F-16 fixed.** `scripts/audit_eval_integrity.py::_tier()` was a *substring* test, so
  `p5:human-frontier69` (48 anchor cells) counted as **HUMAN** although its name asserts a frontier
  component, and the `FRONTIER` branch was unreachable dead code. It is now an **exact-match
  allow-list read from `config/eval_integrity.yaml::provenance_tiers`**, and an unregistered source
  **fails closed** instead of being absorbed into the wrong bucket. The floor check now prints
  **both** numbers: `<axis>=<blind> blind / <attested> attested`.
- **The measured result (why this mattered).** Every axis reads **0.000 blind**:
  `content_type=0.000 blind / 0.116 attested | discipline=0.000/0.347 | depth=0.000/0.526 |
  domains=0.000/0.920 | extraction_type=0.000 (no anchor)`. Nothing in the anchor was produced
  blind, so **the attested figures are upper bounds**, as BUG-267 records. The floor still gates on
  *attested* so the criterion does not fire on a taxonomy change; the blind figure prints every run
  so it cannot be forgotten.
- **F-03 re-scoped** (this overrides the "cheap deterministic fix" I recommended earlier).
  The old invariant **exited 1 for the DESIGNED state** — NULL depth on a non-principle row — i.e.
  it reported a non-defect as a violation, which is the same signal-inversion class as the
  NA-as-DRIFT bug and creates pressure to weaken a gate. It now fails only on the invariants that
  actually matter (a `principle` row with a blank axis; any row with blank discipline/domains), and
  reports the NULL depth as a design state with a **deferred** remedy.
  **Why the stamp is deferred:** stamping 1,470 rows writes the row's `content_type` into a second
  axis, and content_type is the project's weakest-provenance axis (0.000 blind; BUG-238 measured
  13-29% of `principle` rows are genuinely non-principle). **The sentinel is cheap to add and
  expensive to un-add.** Stamp after content_type is certified.
- **Governance sync:** `governance/CONTEXT_INDEX.md` created (the recall map, the metric register,
  the anti-drift rules, the DO-NOT-QUOTE list, and the human-gate register); cross-reference headers
  added to the four 2026-09-17 reports; `AGENTS.md` `<knowledge_sources>` now points at the index.
- **G2 artifact:** `governance/F14_RELABEL_OR_RETIRE_SAMPLE_20260917.csv` (30 stratified orphan rows).
- **G3 artifact:** `governance/JUDGE_CALIBRATION_SHEET_20260917.csv` (36 blind rows, 4 tasks) +
  `governance/JUDGE_CALIBRATION_SPEC_20260917.md`.

## Next actions that need NO human (I can proceed immediately)

1. **F-06** — `tests/test_eval_harness_contract.py` (the harness that produced every model score has
   zero tests; BUG-262..266 were harness bugs).
2. **F-11** — one shared response reader (content / tool_calls / reasoning_content, `''` retryable).
3. **F-15 prep** — define the per-FORM rubric wiring point for S5 (consumes the
   `verification_standard` values already in `config/content_types.yaml`).
4. **A1/A2 instrument** — Krippendorff alpha per axis + per-suite `n_min` + sequential stop rule
   (market research A1/A2), so "spotless" becomes a number.
5. **F-02 precondition work** — add the provenance fields to the relabel path so the F-14 run is not
   born untraceable.
6. **G4 generator** — build the blind certified-core sheet from the anchor's weakest cells.

---

## D-271 RULED (2026-09-17) — identity, authority control, LINK vs MERGE

Artifact: `governance/DECISION_D271_IDENTITY_20260917.md` | config: `config/identity.yaml`
Instrument: `scripts/identity_tax_ab_test.py` (R5 gemma-4-E4B APPROVE, digest `d89a44a21a1a8295`).

- **D-271a (REVISED 2026-09-17): DECLARED HOMONYM — change nothing.** Both labels stay canonical; the
  742-row "collision" is a missing *declaration*, not a data defect: 0 migrated, 0 relabelled, **0 human
  labelling**. Retrieval precedence is now explicit — discipline wins for partitioning (single-valued,
  exact, load-bearing for `depth: cross-domain` on 789 rows), domains wins for recall — so if a collapse
  were ever forced the **discipline** side survives, the reverse of a row-count heuristic. Verified safe:
  no flat combined vocabulary in `taxonomy_v5.yaml`; 0 undeclared normalised collisions over 7,995 rows.
  **G8 downgraded to a ratification.** See `DECISION_D271_IDENTITY_20260917.md` section 2a.
- **D-271b (No duplicate flood):** the production identity rule can express only **12 rows (0.15%)**;
  the semantic flag set is 273 groups / 662 rows / **389 rows a MERGE would delete**. Ruled **LINK**.
  D2627 already said this; it was never wired into retrieval.
- **D-271c:** stable `concept_id` + authority control + edges on `concept_id`. Tested: **S1 alone FAILS**
  (164,202 edges keep the old hash), **S2 alone FAILS** (5 labels carry >1 concept), **S1+S2+S3 PASSES**
  (0 broken edges, 0 rows lost).
- **D-271d (no human):** `duplicate_of IS NULL` in `retrieve.py` + indexes on discipline/domains (BUG-275).
- **Interim rule in force: NO renames anywhere** until the identity layer exists (cost 0, prevents the only
  irreversible event).

**NEW HUMAN GATE — G8: adjudicate the 167 rows that carry BOTH `research methodology` (discipline) and
`research & methodology` (domain).** This is the collision itself and cannot be delegated: the discipline
axis has an attested human share of 0.347, so a model judging it would be the judge of itself.

# HUMAN GATE REGISTER (authoritative)

Nothing below can be delegated to a model without destroying the value of the step.

| gate | what only a human can do | artifact to fill | est. time | blocks |
|---|---|---|---|---|
| **G1** | **Ratify the priority ruling** — confirm "fix the ruler first" (or overrule it) | `PRIORITY_DECISION_20260917.md` (mark ratified) | 10 min reading | the whole sequence's authority |
| **G2** | **Rule relabel vs retire on 30 sampled orphan rows** — are the 4,054 untraceable KB objects legitimate knowledge, or stale residue the checkpoint already dropped? | `F14_RELABEL_OR_RETIRE_SAMPLE_20260917.csv` (fill `G2_VERDICT_keep_or_retire`, `G2_quality_1to5`, `G2_note`) | 30-45 min | F-14 (~4,054 calls / 3 h) — and possibly saves all of it |
| **G3** | **Blind-label 36 rows** (4 tasks x 9) *before* any model runs | `JUDGE_CALIBRATION_SHEET_20260917.csv` (fill `HUMAN_VERDICT`) | 35-50 min | R5 re-verification (~650 calls) + which judge owns T1/T2/T3/T6 |
| **G4** | **Blind-label the certified eval core**, n=100-150, concentrated on `content_type` + `discipline` + FORM **— LABELLED; attestation SIGNED 2026-09-21 (D-317)** | `governance/anchor1_frozen_20260920.json` (`0ec321a7…`) | done | still blocks: nothing — it *enables* every model-accuracy claim. Independence remains open (F-11: no second coder) |
| **G5** | **Ratify the P2 freeze** — 19 uncited roles: 4 need a real DECISION, 11 get stamped `UNVERIFIED` | `governance/consolidation_drafts_20260916/02_model_assignments.yaml.draft` | 45-60 min | `config/pipeline_config.yaml` freeze, CONSTITUTION §2 |
| **G6** | **Decide the synced-folder question (F-09)** — corpus, DB and config live under a third-party sync root (C3 sovereignty / leak vector) | `FORENSIC_AUDIT_20260917.md` F-09 | decision | leak-risk posture |
| **G7** | **Decide the domain aggregation policy** — 63 contested rows, exact-set vs union | `governance/domain_aggregation_policy_decision.md` | decision | the domain axis |

**Recommended order:** G1 (10 min) -> G2 (45 min — it decides whether 3 h of calls happen) ->
G3 (50 min — it decides *which judge*) -> then G4 (the big one, 6-10 h, splittable) -> G5/G6/G7.
G2 and G3 are the two that unblock machine work, so they come first.

---

## G2 DONE (2026-09-17) — outcome and what it changes

**Answered:** 30/30. `keep` 18 / `quarantine` 8 / `retire` 4. Two rubric deviations, both kept:
the operator used a **third value** (`quarantine`) — ratified as a real third state — and left
`G2_note_codes` blank, so the *coded reason* is missing. Full analysis:
`governance/HUMAN_GATE_RUBRIC_20260917.md` (G2 OUTCOME).

**The decisive finding:** the verdict tracks the *existing* `content_type` almost perfectly.
`principle` (8/8), `process_template` (4/4) and `tool_instruction` (3/3) scored **no** retire;
`noise_drop` and `quarantine` scored **no** keep. The junk is already labelled junk.

**Proposed scope (revised from "relabel all 4,054"):**

| bucket | orphans | action | basis |
|---|---|---|---|
| principle, process_template, tool_instruction | **3,348** | **relabel** (the F-14 run) | 15/15 sampled `keep` |
| noise_drop, quarantine | **591** | **exclude from relabel** | 0/8 sampled `keep` |
| process_instance, growth_edge | **115** | **review queue** (the operator's `quarantine` bucket) | mixed sample |

**Two follow-on decisions this creates (both need a human):**

- **D-G2a — exclude or delete the 591?** Excluding is reversible and costs nothing; deleting is
  `pipeline/safe_delete.py` (R-D410) and changes the KB. Recommendation: **exclude + flag**, and
  leave deletion as its own decision.
- **D-G2b — how does the invariant treat excluded rows?** `AX5.form_axis_traceable` would stay
  permanently DRIFT if 591 rows keep untraceable FORM labels. Either the invariant gains a
  "traceable OR explicitly scoped-out" state, or those rows are retired. **Recommendation:** add the
  scoped-out state, because a permanently-red criterion trains people to ignore it.

**Rubric change recorded:** the G2 verdict column is now a **three**-state decision
(`keep` / `quarantine` / `retire`). The two-state version was mine and under-described the task.

---

## STEP 2 DONE — judge calibration (2026-09-17), and it cancels most of the planned re-verification

**Method:** 36 blind human answers (33 decisive, 3 `inbetween`, 0 unscoreable) vs the two eligible
cross-family judges, 72 calls. Artifacts: `governance/judge_calibration_20260917.md` + `.json`.
Full write-up: **BUG-269**.

| task | n | constant-answer baseline | best judge | lift | outcome |
|---|---|---|---|---|---|
| T1 dedup | 7 | 0.571 (`same`) | gemma 1.000 | **+0.43** | **ADOPT gemma** |
| T2 suffix-merge | 8 | 0.875 (`merge`) | gemma 0.875 | 0.00 | **degenerate** |
| T3 content_type | 9 | 0.778 (`principle`) | gpt-oss 0.333 | **−0.44** | **worse than constant** |
| T6 frontier69 | 9 | 0.778 (`justified`) | both 0.778 | 0.00 | **degenerate** |

**What it cancels / replaces**

- **cancelled:** the ~650-call cross-family re-verification of the decision lists. Re-judging T2/T3/T6
  with another model produces a *different opinion with no information* — verification theatre.
- **T2 → deterministic.** "base name + suffix" is a string operation, not a judgement. 0 calls,
  no possibility of being wrong by opinion.
- **T3 → mechanise first.** The human answered `principle` 7/9 while both models leaned
  `process_template`: D2587's boundary (one instruction = principle, >=2 steps = template) is defined
  but not applied by any consumer. Build the step-count/verb test, judge only the residue.
- **T6 → blocked on F-15.** Both models answered `justified` 9/9 (yes-bias). The question must be
  re-posed as the per-FORM `verification_standard` already written in `config/content_types.yaml`.
- **kept:** T1 dedup (299 calls, gemma).

**Two new decisions this created (human):**

- **D-G3a — accept the revision?** (drop the 650-call swap; make T2 deterministic; sequence T3/T6 behind
  the rubric.) Recommendation: **yes** — the measurement is unambiguous about direction.
- **D-G3b — T3 ownership.** If the mechanised step test cannot separate principle from
  process_template on the residue, T3 becomes human-owned or its taxonomy is merged. Decide after
  the test exists.

**Also newly surfaced by the operator's own answers:**

- **BUG-270** — `frontier_qwen38_69_objects.json` disagrees with the DB on **10 of 69** objects, and
  **2 concepts sit in both taxonomies** (`research & methodology` as a domain on **648 rows** vs
  `research methodology` as a discipline). Needs a ruling on which side is authoritative.
- The coded note vocabulary was **not** used by the operator (prose was written instead, exactly as in
  G2). Free-text note fields will be used as free text; the walkthrough should offer a numbered menu.
  Recorded as a process defect, not an operator error.

---

## D-272 RULED (2026-09-19) — the blind ruler result and the ontology forensic

The G4 ruler came back. `governance/ruler_measurement_20260917.md` is generated from
`governance/RULER_BLIND_SHEET_20260917.csv` (150 rows, reviewer `human`, 17.09.26, filled **by name, not by
index**, with 29 discipline + 22 FORM cells left blank and 31 typo'd answers — all resolved and itemised, see
BUG-283). Registry now 623 decisions.

**Measured on stratum A (n=100, the only floor denominator):**

- **ROLE 0.740 vs a 0.750 constant-answer baseline → lift −0.010.** The axis is *no better than always
  answering "principle"*. Decisive.
- **DISCIPLINE 0.506, CI [0.401, 0.611], floor 0.60 → the floor lies INSIDE the interval.** Not failed:
  **unresolved**. ~85 more stratum-A rows decide it (D-272g). 17% of stratum-A rows were left blank.
- **FORM 0.831 vs 0.360 baseline → decisive PASS.** The best-measured axis in the system.

**Rulings issued (this session):**

- **D-272a** the ruler is certified (150 blind labels; the measurement above).
- **D-272b** **THE AXIS INVERSION** is the governing architectural finding: the axes are ranked inversely to
  their reliability relative to their retrieval load. This — not any single bad label — is why "a new weak
  point appears every day".
- **D-272c** **constrained, definition-anchored classification supersedes D2138 free-generation**; the 999-rule
  `alias_map.yaml` is to be **retired**, not extended.
- **D-272d** **split `QUARANTINE` into `UNVERIFIED` | `CONTRADICTED`** and persist the S5 verdict (recovers
  ~1,780 principles into reach).
- **D-272e** **relevance becomes its own axis**, separate from `noise_drop`.
- **D-272f** **instrument repair, NOT re-engineering** — the market-research programme adopted in ranked order;
  cluster-derived labelling and a larger alias table are documented **dead ends**.
- **D-272g** the ruler is **not finished** (discipline unresolved) **and F-14 is retargeted**: FORM does not
  degrade in the untraceable pocket (0.860 vs 0.804); **ROLE** does (0.667 vs 0.816).

**New human gates opened:**

- **G4a** repoint the floors at the certified core (recommended) and **continue the ruler on discipline**
  (~85 more stratum-A rows).
- **G9** approve the `QUARANTINE` → `UNVERIFIED` | `CONTRADICTED` split.
- **G10** approve the relevance axis and its criteria.
- **G11** ratify the ~10–12 vocabulary slots to rebuild or demote (the abstract/coined/hybrid ones:
  `cultural design` 0.00, `emerging` 0.11, `behavioral economics` 0.20, `psychology` 0.44 vs the concrete
  `typography`/`information science`/`organizational theory` at 1.00).

**New defects logged:** BUG-278 (quarantine conflation), BUG-279 (free-generation labelling), BUG-280 (ROLE
decorative), BUG-281 (no relevance axis), BUG-282 (24/45 dead columns), BUG-283 (ruler scorer accepted only
indices — FIXED).

**Standing rule added:** *validate an instrument against the worst realistic input, not the best.* The scorer
was proven against an idealised sheet (indices, complete) and crashed on the first real one.

---

## D-273 RULED (2026-09-19, second pass) — the retrieval and ingestion layers

The first pass audited **labels**. The second audited the **retrieval path**, the **ingestion path** and my own
**sampling frame**. It produced **10 new defects (BUG-285…BUG-294)** and **corrected three of my own claims** —
which is the point of running the audit before consolidating the review.

**The order of the repair programme CHANGED.** It now begins with a **correctness** bug, not a labelling one:

- **D-273a (NEW #1) — the facet filters do not filter.** `search_hybrid` applies `discipline = ?` to **one of
  three legs** and post-filters nothing. Measured: `discipline='typography'` returned **2 of 10 results that were
  not typography**. Independent of label quality; precedes every labelling repair. → **G12**
- **D-273b (NEW #2) — the write guard destroys the label D-271a ruled legal.** `validate_discipline_domain` fires
  on the discipline alone and is a hard error at `stage4_merge.py:823` (quarantine) and
  `stage6_commit.py:402` (**REJECTED**). **The D-271a ruling is NOT in force in code**, and **R1 as specified would
  have every correct `research methodology` answer destroyed** — one of the *most* reliable labels (0.83). One
  config-driven line. → **G13**
- **D-273c** `graph_expand` carries **no status predicate** → the quarantined 40.7% is **inconsistently visible**,
  not hidden, and expansion propagates label error structurally (the edges were built from ~50%-wrong labels).
- **D-273d** the vector leg embeds **`definition` only = 11.1%** of the FB body; **88.9% is unembedded and
  unindexed**, and **4.8M chars of verbatim `evidence_passages` are indexed by nothing**. `source_text` is
  `"[book.md] " + definition`.
- **D-273e** `source_diversity` counts **filenames, not works**: **29.1% of "convergence" is the same book twice**
  (757 of 2,597 rows; 369 work-identities with >1 filename). It is the **merge criterion at stage 1.5**. → **G14**
- **D-273f** `emerging` is an **illegal facet value**: 744 domain rows (not canonical) and 447 PASS discipline rows.
- **D-273g** a **chunk/evidence leg is worth it at step 8**, not now: RRF is **already correct**; the join is
  **100% (205,813/205,813)** so the cost is ~214k vectors; but it fixes grounding, not labels, and adding a leg
  before D-273a **amplifies** the filter leak. → **G16**
- **D-273h** cross the ruler strata with `status`: on `PASS`-only rows ROLE's lift is **exactly 0.000**.

**Measurements that REFUTED my own hypotheses (kept for the record):** FTS staleness (integrity-check **passed**);
label-poisoned production embeddings (`contextual_embed.enabled: False`); and over-merging causing unlabelability
(singletons are **3× more** unlabelable — 24.1% blank vs 0%).

**Standing rule added:** *a filter is not a filter until it constrains every candidate generator.* And: *an
instrument that reports a decision as pending, or a filter that does not filter, is a defect of the same class as a
wrong label — it makes the system unmeasurable.*

Registry now **631 decisions**; buglog now **BUG-294**.

---

## D-274 — RULED (2026-09-19, later the same day): the round-2 cross-examination

Three frontier reviews (temp/qwen0080.md, temp/chatgpt0080.md, temp/claude0080.md) were returned against
ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919.md and every load-bearing claim was re-derived against the repo
or the live DB. **Full record: governance/ROUNDTABLE_CROSSEXAM_20260919.md.**

**THE FINDING NONE OF THE THREE REACHED.** The serving gate is a **label**, not a verification verdict.
scripts/apply_phase1_finalize.py:18 sets status = 'PASS' if content_type == 'principle' else 'QUARANTINE'
and writes it at :163; three hand-run scripts can move rows across the gate on label grounds. The DB
matches that rule on **4,745/4,745 PASS rows and 0/1,470 non-principle rows**.

| measurement | value |
|---|---|
| status disagrees with its own persisted verification_results[factual].passed | **2,447 (30.6%)** |
| PASS rows whose own verification says passed=False | **1,941** |
| — NLI CONTRA-majority (contradicted, served) | **138** |
| — NLI NEUTRAL (unverified, served) | **1,514** |
| — all evidence flagged non-evidence fragments (served) | **278** |
| — MECH FAIL / conversion artifacts (served) | 11 |
| QUARANTINE rows that are NLI ENTAIL-majority (verified, hidden) | **506** |
| honest gate (status := factual.passed) | PASS **4,745 → 3,310** |

⇒ **ROLE is the highest-leverage axis, not decorative.** D6 / BUG-280 / D272g are **INVERTED**, and the
gating axis is the one with **lift −0.010 over a constant answer** on a column that is 81.6% one value.

**Confirmed from the reviews (all re-derived):** Claude's D11 "confirmed, worse" — search_keyword takes
**no query text** (retrieve.py:123-134), is called only when a facet is present (:363-370), and its
insertion-ordered rows receive **equal RRF weight** (:355-390), with the rerank pool cut from the fused
list (:411-415); the **guard SPLIT** (better than the G13 exemption); the hardcoded verifier stamp
(stage5_verify.py:898); the QUARANTINE split as a **parse, not a re-run** (verification_results populated
on 7,995/7,995); the catch-all sentinel by design (taxonomy_v5.yaml:2131); the golden set whose ids were
chosen from live search output ("verified via live hybrid search BEFORE locking them in").

**Corrected in my own record:** BUG-295 (the FLOOR estimand), BUG-296 (F-14 retarget null),
BUG-297/299 (ROLE inversion), BUG-298 (no provenance column), BUG-300 (query-blind leg),
BUG-301 (stage5 tier dropped by stage6; verifier literal).

**Rejected:** ChatGPT's and Qwen's "D3 CONFIRMED" (both replicated my error — the pocket contrasts are
null); ChatGPT's "stage 5 does not preserve the NLI distinction" (it does; it is never queried);
ChatGPT's D6 direction; Qwen's "Outlines replaces R1/R2" (constrained decoding enforces membership, not
semantic correctness) and "RAGAS/ARES replace the ruler" (category error — they measure retrieval, not
label correctness).

**Programme order is now:** 0a serving gate from the verification record → 0b facet predicate in every leg
→ 0c guard split → 1 persist the tier → 2 fix the estimand → 3 R5/R1 → 4 index what is in the DB →
5 work-identity dedup → 6 S5 aggregation fix → 7 chunk/evidence leg → 8 distilled model.

**Explicitly excluded:** re-labelling the corpus; ~85 more stratum-A rows; training S2/S4 on the current
labels; extending the alias map; ACORN; re-cutting the ontology; re-deriving FORM on the pocket; the chunk
leg / vec_fbs_ctx / contextual embeddings / weighted RRF before 0a-0b; R2 before R5/R1; deleting the junk
rows. The D-2637 model-eval workstream is **not on the critical path**.

**Standing rule added:** *a governed value that a hand-run script can redefine is not governed. A label
may not determine serving eligibility, and a filter that is not asserted on the final pool is not a
filter.*

Registry now **639 decisions**; buglog now **BUG-301**; new gates **G17–G20**; **G4a withdrawn**.

---

## 0a/0b/0c IMPLEMENTED (2026-09-19, later session)

The first three programme steps are executed and verified (forensic audit first, then change):

- **0a / G17 (D-274a):** `scripts/apply_serving_gate.py` is the single writer for `status`, derived from
  `verification_results[factual].passed` + a typed `s5_reason` (new `fbs.s5_reason` column; rule +
  vocabulary in `config/serving_gate.yaml`; invariant in `pipeline/serving_gate.py` + 15 tests). Applied
  PASS 4,745 → 3,299 (de-served 1,941 + 11 duplicates; restored 506); integrity ok; CI invariant 0
  violations; `duplicate_of` rows hard-quarantined. The four label scripts no longer write `status`
  (BUG-299, BUG-302).
- **0b / G12 (D-273a):** facet predicate pushed into every retrieval leg + asserted on the fused pool
  (`pipeline/retrieve.py`); constraint-violation rate **0.5911 → 0.0000** over 470 probes
  (`scripts/measure_constraint_violation.py`). Closed BUG-285, BUG-300.
- **0c / G18 (D-273b):** write guard split into `validate_discipline_domain()` (row guard) vs
  `lint_discipline_domain_vocabulary()` (vocabulary lint); `research methodology` now writes clean
  (BUG-286). `audit_taxonomy_disjointness.py` updated to report declared debt via the lint.
- **BUG-276:** `pipeline/backup_guardian.sh` repointed at the SQLite DB (consistent `.backup` + integrity).

**Remaining path (unchanged after step 3):** 1 (G19 persist the tier) → 2 (ruler estimand) → 3 (R5→R1) →
4 (G15) → 5 (G14) → 6 (S5 aggregation) → 7 (G16) → 8 (distilled).

## Ruler key inversion + guardrail (2026-09-19, evening)

**Step 1 (D-275a) executed.** The ruler's answer key was the stored (corrupt free-generated) label.
`scripts/rescore_ruler_inverted.py` inverts it: blind human = ground truth, stored = under test, reports
error rate. FORM pass (reviewer's updated labels): **stored error 0.253 [0.177, 0.346]**;
normative_heuristic 50% mislabeled (→ causal 9×, → descriptive 6×); "irrelevant" written in 4 FORM cells
(evidence for R4). Artifacts: `governance/ruler_form_inverted_20260919.{md,json}`.

**D-275b (PROPOSED, pending ratification):** content-type guardrail — procedural intent + done condition
as the principle/process_template discriminator (not "≥2 steps"); atomic unit = one self-contained
epistemic claim; checklist → process_template; decision matrix → inline_gate_content.

**Next:** reviewer re-labels CT/discipline with the D-275b guardrail → re-score CT/discipline (inverted)
→ freeze ANCHOR-1 → per-slot reliability → R5 ratification → R1 → R2.

## G19 — persist the S5 verification tier (2026-09-19, evening)

`pipeline/stage6_commit.py` now persists `s5_reason`, `epistemic_status`, `verification_method`, `isor`
(CREATE TABLE + migrate + INSERT columns/placeholders/bindings), and `stage5_verify.py:897` derives
`verifier_model` from config (`S5_NLI_MODEL_LARGE (threshold S5_NLI_PASS_THRESHOLD)`). Live DB migrated
68 → 71 columns; integrity CHECK 8 passes (71 placeholders = 71 columns); 15 serving-gate tests green.
Fixed the latent 0a drift (s5_reason in DB but not in stage6). BUG-301 RESOLVED. Also recorded D-275c
(System One Models / Jev → REJECT for pipeline, ADAPT framing).

## Full-axis inverted re-score + ANCHOR-1 freeze (2026-09-20)

Reviewer locked CT + DISC + FORM. Inverted re-score (D-276): stored error **CT 0.353 / DISC 0.474 /
FORM 0.283**. CT over-calls principle (93 vs 89), under-calls quarantine (18→6) and process_template
(16→9). DISC: 8 zero-agreement slots (design psychology 0/5, cultural studies 0/4, risk management 0/4,
+ 5 more) — alias map discards them into `emerging`. ANCHOR-1 frozen (`anchor1_frozen_20260920.{md,json}`);
R5 slot vote PROPOSED (DEMOTE design psychology / cultural studies / risk management / behavioral
economics / decision making; BOUND design thinking / organizational theory). `ruler_measurement_20260917.md`
SUPERSEDED (A5).

Next (dependency order): R5 ratification → R1 (closed menu + `menu_hash` + `*_source` provenance) →
R2 (definition NLI).

## R5 repair-not-demote + D-275b ratified + raw/canonical clarified (2026-09-20, later)

D-277 RESOLVED: (1) R5 is repair-not-demote — zero-agreement measures pipeline failure, not slot badness;
DEMOTE vote withdrawn, replaced by RE-DERIVE definition + BOUND (human review) + merge only if
inseparable. (2) raw AND canonical are both post-hoc model stamps — corpus has zero human labels; both
demoted to G9, re-derive from source only. (3) error rate is a meter (calibration + abstention), never
a label-picker. D-275b RATIFIED → `content_type_decision_procedure` written into config/content_types.yaml
(6-step first-match-wins tree + edge rules + calibration block). anchor1 dispositions regenerated
(RE-DERIVE+BOUND, no DEMOTE); D-275b RESOLVED, D-276 retraction noted, D-277 added; BUG-304 corrected.

Next (dependency order): R5 repair execution → single-coder ceiling (2nd human, 30 rows) → R1 (closed
menu + `menu_hash` + `*_source` provenance) → R2 (definition NLI).

## Next-4 executed (2026-09-20, final batch) — D-278..D-281

1. **R5 repair (D-278):** `config/r5_slot_repair.yaml` — OntoClean definition + include
   + exclude for the 7 weak slots (5 discipline + 2 content-type) and 2 BOUND-only
   slots. Exclude sets name the correct sibling target. Awaiting human ratification.
2. **Single-coder ceiling (D-280, PROPOSED/human gate):** 30-row blind sheet +
   protocol; second human pass not yet performed.
3. **R1 (D-279, RESOLVED):** closed menu (`pipeline/closed_menu.py`), `menu_hash`
   sha256 `25b10c44…`, and `content_type_source`/`discipline_source`/
   `extraction_type_source`/`menu_hash` columns in stage4_merge + stage6_commit +
   schemas. Verified 75==75==75 + temp-DB insert round-trip.
4. **R2 (D-281, RESOLVED):** `scripts/definition_nli_verify.py` (definition-anchored
   NLI, R5 override first); selfcheck green, corpus run pending.

Registry: 648 decisions (resolved 93, proposed 3). Next (dependency order): human
ratification of R5 defs → single-coder second pass → R2 corpus NLI run → re-measure
per-slot κ → lift BOUND / merge only if inseparable.

## Forensic audit + D-282 (2026-09-20) — depth-vs-role conflation fixed

User-caught: "3+ domains" was used as the principle-role boundary in the D-278 defs and
D-275b procedure — it is the universal-DEPTH threshold, not the principle-ROLE criterion.
A domain/specialized-depth principle (1-2 domains) is still a principle. D-282 removes
the domain-count criterion from `r5_slot_repair.yaml` + `content_types.yaml`; closed menu
re-rendered (new menu_hash e8a8b546...). Also fixed a contra-flag threshold reuse in
definition_nli_verify.py. Registry: 649 decisions (resolved 94, proposed 3). Remaining
order unchanged: R5 ratification → single-coder pass → R2 corpus NLI → per-slot κ.

### 2026-09-21 update (D-307..D-312, BUG-325/326)
* Menu repair CLOSED: PART1 B normalisation applied + domain-scoped; PART1 A disproved (zero slots); 16/16 discipline
  boundary pairs settled DIFFERENT. Taxonomy stays v5.5 (audit marker in meta).
* Governance sync: config/decisions.yaml 673 -> 677 (D307..D312), DECISION-LOG + MTR + buglog updated, summary
  recomputed and `--check` clean.
* HUMAN GATES still open: (1) approve/deny the benchmark-only laya-mlx install (isolated venv, pinned revision);
  (2) approve the abstention operating point before `verify_abstention.yaml` is ever flipped; (3) the R3 held-out
  run must be published before R3 is adopted.

## 2026-09-21 (session 6) — audit, BUG-328 landed, gates re-counted to FOUR

- **Landed**: serving-gate / menu_hash / principle-role production set (BUG-328 closed) + audit report.
- **HUMAN GATES — FOUR**: (1) benchmark-only laya-mlx install, isolated venv, pinned revision;
  (2) abstention operating point `t_low = p25` (-0.006, -8.3 pp, 25% queue) — still `enabled: false`;
  (3) R3 adoption only after the held-out number is published; **(4) NEW — name the canonical ruler
  version (v0 lost / v1 HEAD / v2 working, BUG-329) before ANY ruler re-measure.**
- **R3 is not config-only runnable**: the ANCHOR-1 key is an fb_id dict with pipeline labels while the
  harness reads `key['rows'][*]['stored']`; a pre-registered adapter (D-311 amendment) is required
  first, else the measurement is post-hoc and inadmissible under D-300.

<!-- s7-sync 2026-09-21 -->

### Session 7 update (2026-09-21) — gates and the R3 disposition
- **R3 (step 5 of the session plan): DONE — REJECTED.** Held-out n=57 of the pre-registered 58: incumbent
  0.5088, R3 0.5088 (0.00 pp), R2 0.4286 at a 75.4% human queue, R4 0.5965, constant floor 0.8421. The owner
  gate is therefore reduced to an administrative ratification of D-314 (no adoption, no deploy change).
- **HUMAN GATES — now THREE live + one administrative:**
  1. laya-mlx install (benchmark-only, isolated venv, pinned revision) — unchanged.
  2. abstention operating point `t_low = p25` (error 0.4231 at a ~25% queue; `enabled: false`) — unchanged.
  3. **BUG-329 (HIGH): name the canonical ruler version** (freeze `4d0c856a` / HEAD `2d456720` / working
     `38323192`). Nothing on the ruler may be re-measured before this; D-313 makes a freeze-time hash that
     matches no repo version a fail-closed abort.
  4. (administrative) ratify D-314 = R3 not adopted, D-311 closed as measured-rejected.

<!-- s8-sync 2026-09-21 -->

### Session 8 update (2026-09-21) — D-315 RULER RATIFIED, ruler gate CLOSED
- **GATE 3 (BUG-329, was blocking) is CLOSED.** The owner ratified the session's recommendation: the canonical ruler
  is `governance/anchor1_frozen_20260920.json` (`0ec321a7…`). Three-version disposition recorded in the buglog
  (v0 `4d0c856a` byte-lost; v1 `2d456720` = superseded draft; v2 `38323192` = the measured label set, now HEAD).
  Re-scoring from the authority reproduces the published numbers EXACTLY (CT 0.3533 / DISC 0.4741 / FORM 0.2828) —
  the ruling moves no published number.
- **Truth-blinding self-test on the ruler path: PASS** (all 3 axes; reference invariant, blinded agrees 0). This is
  the mechanical channel, because the LLM reviewer returned a rubber stamp (BUG-333).
- **HUMAN GATES — now TWO live + one administrative:**
  1. laya-mlx install (benchmark-only, isolated venv, pinned revision) — unchanged.
  2. abstention operating point `t_low = p25` (error 0.4231 at a ~25% queue; `enabled: false`) — unchanged.
  3. (administrative) ratify D-314 = R3 not adopted, D-311 closed as measured-rejected. **D-314 is now RATIFIED
     as part of the D-315 ratification** — no adoption, no deploy change, abstention still disabled.
- **NEW STANDING GAP (F-11, methodological, not a gate):** the ruler declares
  `second_coder_required_before_repointing: true`. No second coder exists, so NO floor may be repointed — every
  floor number in this repo is single-coder. Re-measurement for diagnosis is unblocked; floor REPOINTING is not.
- Housekeeping debt carried, not silently dropped: 46 `config/*.bak_*` + 1 `governance/buglog.md.bak_*` (gitignored;
  the only recovery copies) — the stale-config confusion risk is real and belongs to a cleanup pass with the owner.
### Session 9 update (2026-09-21) — D-316, ruler annotation restored, stage5 snapshot regression declared
- D-316 RATIFIED: one answer key (the authority); the abstention REASON comes from the hash-pinned workspace, annotation only, fail-closed on drift.
- BUG-340 FIXED; BUG-342 FIXED (C15 is now mechanical: 60 open / 27 closed of 87 ids -- every handoff must carry it).
- BUG-341 OPEN (HIGH): the live stage5 checkpoint is absent (rotated 18:59:42; no re-run). Bytes preserved and cited; NOT restored to the live path by design.
- BUG-330 FIXED; BUG-343 OPEN (a smoke test cannot show its own failure output).
- HUMAN GATES (unchanged, untouched this session): (1) laya-mlx benchmark-only install in an isolated venv; (2) abstention operating point t_low=p25; (3) owner signature on the human_attestation line.


### Session 10 update (2026-09-21) — D-317: the human attestation is SIGNED (owner gate CLOSED)
- **D-317 RATIFIED.** Owner signed `human_attestation: "these 150 labels are mine, made blind to pipeline output."`
  Recorded in `config/eval_integrity.yaml:ruler_authority.human_attestation` with the scope (n=150; 100 A + 50 B) and
  the attested artifact sha256 (`governance/anchor1_frozen_20260920.json`, `0ec321a7…`). "human-anchored" is now
  **ATTESTED**, not verified-by-reconstruction. No published number moves.
- **HUMAN GATES — now TWO live** (the signature gate is CLOSED):
  1. laya-mlx benchmark-only install, isolated venv, pinned revision — unchanged.
  2. abstention operating point `t_low = p25` (error 0.4231 at a ~25% queue; `enabled: false`) — unchanged.
  Plus G2..G7 in the register below; G4's *labelling* is done and its attestation is now signed.
- **NOT converted:** attestation is not independence. F-11 (`second_coder_required_before_repointing: true`, no second
  coder) still forbids repointing any floor. Every floor is single-coder, now single-coder-ATTESTED.
- **BUG-344 opened + FIXED:** the `*_sha256` pins declared in config were never read by `authority_paths()`, so the
  annotation drift guard was inert in the run path and the artifact cited an EMPTY `annotation_sha256`; declared pins
  are now enforced fail-closed and the artifact cites the hash it consumed.
- Carried, not dropped: BUG-341 (live stage5 checkpoint absent), BUG-343, BUG-312, F-11, 46 `config/*.bak_*` +
  32 `governance/*.bak_*` housekeeping debt (the only recovery copies; owner pass).

### Session 10 addendum (2026-09-21) — audit found THREE real defects, all fixed
- **BUG-344 (HIGH, FIXED)** — declared pins were never read by `authority_paths()`, so the annotation drift
  guard was INERT in the run path and the artifact cited an empty `annotation_sha256` (D-313 failure).
- **BUG-345 (HIGH, FIXED)** — the authority pin itself carried a one-character typo (index 34) that passed two
  sessions of "verification" because every check compared a 16-char PREFIX.
- **BUG-346 (MED, FIXED)** — `score_ruler_labels.py` (stored-label-as-answer-key) retired as a second truth path.
- **D-318 RATIFIED** — a pin is a control only if byte-compared in the run path; `scripts/pin_audit.py` is the
  standing audit (5 pins, 0 failing). **BUG-333 partially fixed** (quoted-evidence R5 gate; BUG-331 still open).
- Nothing published moved: 4750 result leaves identical to HEAD; CT 0.3533 / DISC 0.4741 / FORM 0.2828.

### Session 13 — owner rulings applied (2026-09-21 19:54Z)

**Owner gates: one closed, one new, three still open.**

| gate | state |
|---|---|
| (1) prune the dead `normalization_map` entry (BUG-355b) | **CLOSED by owner** — verified inert: kappa artifact byte-identical after the prune |
| (2) PART 2 boundary items 17-26 | **PARTLY RULED** — items 24 and 26 REJECTED (BE terminology); 17-23 and 25 remain silently accepted unless rejected. Part C (adopt `default_home` + escape instead of per-pair name rules) still unanswered |
| (3) **NEW**: `behavioral economics` definition is narrower than its denotation (BUG-357) | **OPEN** — widen the `definition:` string (recommended) or re-label row 60 |
| (4) laya-mlx benchmark-only install | **OPEN** — recommendation: narrow feasibility arm only; full A/B waits on the second coder (F-11) |
| (5) abstention operating point `t_low = p25` | **OPEN** — still `enabled: false`, INERT |
| (6) `repair_queue` path (BUG-358) | **OPEN** — recommendation: repoint to the write-path + `fb_id` de-dup key + owner; do not create an empty queue |

**Corrected boundary tests** (definition-anchored, `behavioral economics` R1/R2/R3) are drafted in
`governance/BOUNDARY_DISCRIMINATORS_20260921.md` **Part D**; the two rejected tests are struck but kept.

**Bug register:** cite `governance/bug_status.json` — the count is deliberately NOT restated in a handoff (BUG-349);
BUG-355 is PARTIALLY FIXED, not closed.

**Not done, by design:** nothing wired into the S4 classifier prompt; no menu slot added; no canonical
renamed; `config/taxonomy_v5.yaml` bytes unchanged; `arm_typed_head` still a stub.

### Session 13b — three owner approvals executed (2026-09-21 22:0xZ)

| owner decision | state |
|---|---|
| widen the `behavioral economics` definition | **DONE (D-321)** — BUG-357 FIXED at the source; `taxonomy_v5.yaml` v5.6, sha `994e056b…`; 0 slots added; menu pin unchanged; row-60 effect predicted, not yet measured |
| laya-mlx, my recommendation (Phase A only) | **DONE (D-322)** — `.venv_laya`, `laya-mlx 0.1.0`, menu accepted as 62 criteria, pins live in `config/bakeoff_laya.yaml`; Phase B remains blocked on a second coder (F-11) |
| repair_queue, my recommendation (declare, do not create) | **DONE (D-323)** — BUG-358 CLOSED; contract declared, no empty queue file |

**RATIFY (one word each, if you disagree):** (a) the **v5.6 version bump** that rode along with the definition
widening — required so two emission behaviours do not share one stamp (R14); (b) `config/bakeoff_laya.yaml`
and the `.venv_laya` sandbox as declared.

**Bug register:** cite `governance/bug_status.json` (BUG-349: not restated in handoffs).

**Still not done, by design:** nothing wired into the S4 classifier prompt yet; items 17-23 and 25 of Part B
are silently accepted unless rejected; Part C (adopt `default_home` + escape instead of per-pair name rules)
is still unanswered.

### Session 13c — Part C ruled (2026-09-21 22:1xZ)

Owner: ratifications (a)(b) accepted; **Part B items 17-23 and 25 ACCEPTED**; **Part C ruled in favour of the
recommendation** — `default_home` + named escape condition is the discriminator of record, per-pair NAME rules
only where the object test converges. laya: owner accepts the Phase A/B recommendation (Phase B held on F-11).
Abstention `t_low=p25` and G1/G5 ratified as recommended.

Owner gates remaining: none blocking the next step. Step 1 (wire the ruled boundaries into the S4 prompt and
measure on the frozen ruler) is now UNBLOCKED and is the only step that can move emission coverage.

### Session 14 — the ruled boundaries are now IN the classifier (2026-09-21)
Owner: "accept your recommendation / do the next 6 steps / forensic audit first / hand over anything blocked
by a manual review or decision / update and sync governance dependencies / list next strategically
consequential steps".

DONE (audit first, then work):
1. FORENSIC AUDIT GREEN — clean tree at 0e681c1 (no drift/bind/gap/conflict/leak/contamination); menu pin
   unchanged (73597ee2); pin_audit.py PINS 5 checked 0 failing PASS; decisions summary in sync; bug register
   104 ids / 67 open / 37 closed; anchored ruler unchanged (0ec321a7 / a91f9c85 / 20a4a437).
   RED/orange carried: integrity [14] (now FIXED, see below) and stage-5 Verify = 0 (BUG-341, still OPEN).
2. D-325 — the ruled discriminator set is WIRED: config/boundary_discriminators.yaml (10 default_home + 10
   boundary tests: 17-23, 25, 24', 26'), injected into the S4 merged-classify system prompt, fail-closed
   (C16), prompt_versions.s4_cribs_classify v2.0→v2.1, and the rule bytes folded into manifest_hash
   (D-318: byte-compared in the run path; manifest_hash now 024579b6).
   Control artifact: scripts/verify_boundary_injection.py → PASS.
3. D-326 — BUG-353 integrity gate greened: 11 shell scripts self-locating cd + a COUNTED C12-FIXTURE
   exemption for synthetic eval fixtures → integrity_check --quick 10/10.
4. Measurement launched: scripts/s4_emission_ruler.py (config/s4_emission_ruler.yaml) — A/B, baseline vs
   treatment, 60 frozen rows, gpt-oss-20b, temp 0.0 → governance/anchor2_s4_emission_20260921.json.
   This is the first run that can CONFIRM OR FALSIFY the BUG-357 row-60 prediction.
5. STALE NOTE CORRECTED (BUG-359): the justfile config_audit path was already correct.

OWNER GATES REMAINING (nothing here blocks the measurement): decisions.yaml registry entries for D-319..D-326
(owner-owned file); F-11 second coder; abstention operating point; laya Phase B; GitHub gate.

### Session 15 — first measured verdict on the ruled boundaries (2026-09-21, D-327/D-328)
1. MEASUREMENT RETURNED (D-327). 60 frozen rows, two arms, same model, temp 0.0:
   baseline emitted 47/60 (78.3%) / error_rate 0.8000 / oov 13; treatment 42/60 (70.0%) / 0.8333 / oov 18.
   The ruled boundary block is REJECTED as an intervention (worse on all three readings) -> injected prompt
   switched off by config flip; artifacts kept as evidence. BUG-357's row-60 prediction: NOT CONFIRMED.
   NEW DOMINANT DEFECT, measured: 13-18/60 rows emit a label that is not in the closed menu, and agreement with
   the human slot is ~20%. The next intervention should target MENU COMPLIANCE (forcing an in-menu answer),
   not boundaries.
2. ABSTENTION ENABLED at p25 (D-328), triage owner named; queue stays a declared view (no empty file).
3. decisions.yaml registry SYNCHRONISED: D-319..D-328 added; `--check` in sync (693 -> recomputed).
4. stage-5 re-verification LAUNCHED (background): "550 FBs already verified -> 7445 remaining" (BUG-341 was stale).
5. laya-mlx weights FETCHED into .venv_laya (advisory arm) - Phase B remains held on F-11.

## Session 16 (2026-09-22, morning) - F-11 first measurement (D-329)
- Built and ran the F-11 second-coder package (config/f11_llm_coder.yaml, scripts/f11_llm_coder.py,
  governance/F11_LLM_CODER_20260921/): blind export of 122 fully-answered rows + declared-partial handling,
  menus file included, count-neutral prompt. Two LLM coders returned labels (claude-sonnet 122/122, kimi-k3 79/122).
- RESULT (same 79 rows): human~claude k = 0.47/0.40/0.37, human~kimi k = 0.55/0.35/0.33,
  claude~kimi k = 0.80/0.71/0.62 (CT/DISC/FORM). The rubric is measured, not asserted: two independent
  families agree with each other ~2x more than either agrees with the single human coder.
- CONSEQUENCES: no eval floor certifiable from this sheet; D-327's relative verdict stands but its absolute
  error rate (0.8000) is not a classifier property; both LLM coders emitted 0 out-of-menu labels, so the
  closed menu IS usable from text and the S4 OOV emission is a classifier/prompt defect (supports the
  menu-compliance intervention); F-11 stays OPEN (llm-attested cannot unfreeze floors).
- New bugs: BUG-365 (harness crashed on a relative coder path - FIXED), BUG-366 (kimi under-delivered 43 rows).
- STILL OPEN from session 15: BUG-361 (no S5 single-writer lock), BUG-362 (any commit discards a live S5
  checkpoint - nothing committed since 249c9d1 for this reason), BUG-363 (28 ruler rows unanswered), BUG-364
  (laya R14 pins unfilled).

### Session 16 addendum - the 3-way worksheet (D-329 evidence, governance/f11_disagreement_3way_20260922.md)
Kimi's full 122 rows landed; human~kimi k = 0.51 (CT) / 0.40 (DISC) / 0.30 (FORM) - converging with Claude's, so the
effect is stable, not sampling noise. Worksheet over all 122 rows:
  CT    94/122 unanimous | 18 consensus divergence (15%) |  6 model split |  4 three-way
  DISC  43/122 unanimous | 43 consensus divergence (35%) | 21 model split | 15 three-way
  FORM  51/122 unanimous | 41 consensus divergence (34%) | 20 model split | 10 three-way
("consensus divergence" = BOTH independent coders agree with each other and the human is the odd one out.)
Named patterns: DISC - human 'design psychology'/'psychology'/'organizational theory' vs BOTH coders 'behavioral
economics' (7 rows), human 'research methodology' vs 'cognitive science' - the human reads the INSTITUTIONAL field,
both models read the SUBJECT MATTER (exactly the D-325 default_home discriminator, applied in the opposite direction).
FORM - human 'causal mechanism'/'descriptive model' vs BOTH coders 'normative heuristic' (16 rows) plus 10 mutual
swaps among causal/descriptive/normative: the FORM axis is the weakest AND the most contested.
CT - the 18 human 'quarantine' rows (a legal DISPOSITION, menu item 7) are the human refusing a role where both models
assign one: a threshold-of-clean-role policy difference, not a labelling error.
New bug BUG-367 (FORM column is 38% non-canonical spellings - corroborates F-14).

### Session 16 addendum 2 - the freeze is lifted (D-330)
Owner ruling: option A on BUG-362. Implemented and committed (81b813f): path-scoped S5 fingerprint + single-writer
lock (BUG-361) + `--adopt-fingerprint` migration with a substantive-input guard. Audit after the change: integrity
10/10, decisions 696 in sync, pins 5/5 PASS, taxonomy v5.6, S5 fingerprint MATCH, a second S5 writer REFUSED live,
0 tracked .bak. S5 is running again (pid 4194) with the 1,250 records kept: "1250 FBs already verified -> 6745
remaining". Commits no longer kill a live S5 run - that was the whole point.

## Session 17 addendum - F-11 ROUND 2 measured (D-331, 2026-09-22)

Round 2 re-ran the second-coder task over ALL 150 rows (round 1 exported only the 122 fully-answered rows).
Both coders delivered 150/150, schema-clean. Coder-vs-coder (two families, 150 rows): CT k=0.758, DISC
k=0.682, FORM k=0.638 - against human-vs-coder CT 0.487/0.554, DISC 0.445/0.403, FORM 0.305/0.266. D-329 is
reproduced and strengthened: the human reference is the outlier; no floor is certifiable; F-11 stays open.
The 28 DISC abstentions are genuinely contested (coders 64% agree) and remain declared-missing; the 5 FORM
abstentions are uncontested (100%) and await the owner's own call. Fixed BUG-369 (blank cells scored as
disagreements). HUMAN GATE unchanged: only a genuinely independent second HUMAN coder lifts F-11.

## Session 17 addendum (2026-09-23 12:30) - F-11 anchor CONSOLIDATED from the owner's judgement

* Owner returned governance/F11_ANCHOR_REVIEW_20260923.csv filled: 216 owner cells across all 108 flagged rows.
* Result: governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv (150 rows, schema 1.0, provenance tier
  human-mixed+llm-attested) + companion .md. Deterministic, no LLM in the loop.
* 50 overrules (18 content-type, 32 discipline); 28 discipline labels SUPPLIED by the owner where the ruler had
  abstained (tier owner-supplied, flagged human_present=no so scoring can exclude them); 0 declared-missing.
* FORM was deliberately NOT adjudicated by the owner (no adequate LLM reference point) -> the axis is 100%
  human-ruled, the 5 ruler abstentions stay declared-missing, and no FORM floor may rest on coder agreement (D-336).
* 6 owner discipline cells are OFF-MENU and were kept verbatim with a nearest-match proposal only:
  personal productivity x3 (R086/R091/R117), design strategy (R042), computer graphic (R030), media studie (R063).
  OPEN HUMAN DECISION: confirm the two obvious typo repairs (computer graphics, media studies) and rule on the two
  domain-valued labels. Nothing was guessed.
* HUMAN GATE unchanged: this anchor cannot unfreeze F-11, D-300 adoption or the eval_integrity floors. The
  second-coder gate still needs an independent HUMAN coder.
## Session 17 addendum 2 (2026-09-23 12:35) - HUMAN GATE REGISTER updated: F-11 gate REDEFINED (D-337)

* Owner ruling: there will be NO independent human truth. The "second independent HUMAN coder" gate is
  UNSATISFIABLE in a single-owner sovereign project, so it is closed as a MISSING PERSON and re-opened as a
  DECLARED LIMITATION. It is no longer something to wait for.
* Effective now: governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv (150 rows, human-mixed+llm-attested) is the
  terminal reference for RELATIVE comparisons only - arm ranking, A/B, relative deltas.
* Still forbidden: certifying an ABSOLUTE error floor from it (bounded below by reference reproducibility,
  D-329/D-331); every adoption record must state the ruler tier, the non-independence and the bound.
* Owner typos repaired by instruction (declared aliases, C12): `computer graphic` -> `computer graphics` (R030),
  `media studie` -> `media studies` (R063). The remaining 4 owner cells `personal productivity` x3
  (R086/R091/R117) and `design strategy` (R042) are DOMAIN-vocabulary values used in the discipline column; they
  are preserved verbatim and flagged OFF_MENU_DOMAIN - a declared vocabulary choice, NOT an error and NOT a typo.
* Anchor re-consolidated: 150 rows x 31 cols, sha256 3911eece4555a2da... (D-335/D-336/D-337).

## Session 18 addendum 3 (2026-09-23) - abstention gate closed, flag-consumer check live

* **HUMAN GATE REGISTER:** F-11 unchanged (REDEFINED, D-337). **NEW GATE: C-2 / BUG-374** - the S4
  boundary block is still injected (`stage4.boundary_inject_enabled: true`) although D-327 ruled it
  false; D-327's flip never landed (git -S: one change, added as true). Needs a one-line owner GO.
* **D-338/D-339 registered** (707 decisions, `--check` in sync). The abstention operating point is
  approved in principle and NOT activated: `status: gated`, `consumers: []`, four-item activation
  gate, `enabled: false` unchanged - zero production behaviour change.
* **New check:** `python3 scripts/audit_flag_consumers.py` (in `just health`) - RED on a flag whose
  state disagrees with its decision, or an ON flag with no consumer that reads it.
* Anchor re-issued after F-1: sha256 `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698`.

## Session 19 addendum 4 (2026-09-23) — C-2 closed, C-3 opened, ANCHOR-3 frozen, C15 register live
* **HUMAN GATE REGISTER:** F-11 unchanged (REDEFINED, D-337). C-2/BUG-374 **CLOSED**. **NEW GATE C-3/BUG-376**
  (S5 input moved after completion: `S5 REVERIFY` ~1.3 h, or `S5 FREEZE` = freeze the pair and cite it).
* Decisions 707, `recompute_decision_summary.py --check` in sync. No new ids minted this session (C-2/D-327 already
  ruled; the freeze is covered by D-337).
* **Frozen artifacts:** ANCHOR-3 manifest `governance/ANCHOR_MANIFEST_20260923.json`, sha256
  `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698`, verified by
  `scripts/verify_anchor_manifest.py` in `just health`.
* **S5 t11:** live and COMPLETE (7995 = 5023 PASS + 2972 QUARANTINE), fingerprint `c2754fc6...`,
  status **COMPLETE-BUT-INPUT-MOVED** (C-3) — cite it only with that qualifier.
* **Checks now in `just health`:** guard_stacks, status, integrity --quick, audit_flag_consumers (D-339),
  verify_anchor_manifest (ANCHOR-3), verify_declared_inputs (C-3 class).
* **Open bug count:** 71 OPEN / 49 CLOSED of 120 — see
  `governance/SESSION-HANDOFF-2026-09-23.md` (C15 register).

## Session 20 addendum 5 (2026-09-23) — C-3 mitigated, D-340, R3 preflight live
* **D-340 minted** (124 decisions, `--check` in sync): declared stage inputs are immutable; writers
  publish mutation notices. Class fix for C-3/BUG-376.
* **Frozen pair:** `FROZEN-S5-T11-20260922` (7995 = 5023 PASS + 2972 QUARANTINE), manifest
  `governance/FROZEN_S5_T11_20260922.json`, verified by `scripts/verify_frozen_pair.py`. **Owner gate unchanged:**
  `S5 REVERIFY` or cite the frozen pair with the qualifier.
* **Human gates now:** C-3/BUG-376 (S5), BUG-326 (GO), R3 (GO — preflight passes, so it is one command),
  laya (GO), REGISTER FLAGS (proposal ready), F-11 unchanged (REDEFINED, D-337).
* **Open bugs:** 73 OPEN / 51 CLOSED of 124 (see
  `governance/SESSION-HANDOFF-2026-09-23.md`).


## Session 22 addendum (2026-09-23)
D-341 + D-342 minted; evidence receipts + authority markers + 9th health check live; BUG-379/380 FIXED, BUG-381 (HIGH)
+ BUG-382 OPEN. Gate list corrected: **BUG-326 GO withdrawn (not applicable)**. Remaining: BUG-381 vintage call, flags
hygiene, S5 REVERIFY (optional), R3 GO (staged), laya (DEFER), disk. Open bugs: see governance/bug_status.json.

## Session 23 (2026-09-23) — classification regime measured + authority markers enforced
- D-343 (representability regime) + D-344 (authority enforcement) minted. Health = 10 checks.
- Routing table now binding: discipline/domains `classify`; extraction_type `coarsen_or_calibrated_abstention`; content_type + depth `constant_plus_human_queue`.
- Owner gates unchanged and still open: S6 RE-COMMIT/STORE AS IS (BUG-381), R3 GO, FLAGS OFF / WIRE, outlines install, menu coarsen GO.

## Session 23 (2026-09-23, second addendum) — kNN arm REJECTED; flags WIRED
* **D-345:** k-NN arm REJECTED on all three D-343-routed axes vs the frozen 150-row ruler (discipline -26.59 pp,
  content_type -4.67 pp = F-17 again, extraction_type -25.05 pp; 31/150 ties). Representability is necessary but NOT
  sufficient; the incumbent labeler stands; no k-NN arm is built.
* **BUG-385 (MED, FIXED):** the 19 "ON with no verifiable reader" flags all HAVE readers — the prior FLAGS OFF
  recommendation was wrong and would have caused silent capability loss. Wired with symbol-level binding (D-339b).
  **BUG-382** (dotted-key resolution) and **BUG-386** (vec0 shadow reader) FIXED in the same change.
* **BUG-381:** `S6 RE-COMMIT` launched (S5 t11 vintage PASS 5023 / QUARANTINE 2972) under
  `/opt/homebrew/bin/python3` — `just stage6` uses a Python WITHOUT `enable_load_extension` and would silently fail
  all 7995 vector inserts. C13 backup: `maxwell.db.bak_20260923_133729_pre_s6_recommit`.
* **HUMAN GATES:** S6 RE-COMMIT (executing), MENU COARSEN (approved), RERANK WIRE (approved/not executed),
  INSTALL OUTLINES (approved/not executed), FLAGS OFF → **SUPERSEDED by FLAGS WIRE**, R3 GO (DEFER), laya (DEFER),
  `services.omlx.mtp_enabled`.

## 2026-09-23 (session 23, THIRD addendum) - MENU COARSEN enforced; incumbent re-scored

- D-346 MENU COARSEN GO: config/menu_routing.yaml + scripts/verify_menu_routing.py (11th health check),
  5 axes / 23 queued labels / 0 RED. D-347 incumbent re-score: content_type 0.5933 (same human cells) vs
  0.6533 (current truth); discipline 0.5172 / 0.4400; extraction_type 0.7172 unchanged. D-345 stands.
- BUG-387 (HIGH, OPEN) stage6 re-commit DOUBLED the vector store: 15990 vec rows / 7995 orphans; the
  count-only completeness check printed "READY 15990/7995". DO NOT re-run stage6 until the vec path is repaired.
- BUG-388 (MED, OPEN) export_parquet ArrowInvalid: is_summary/is_convergent are bool in 7867 rows and int in
  128 rows -> fbs+vec_fbs committed, parquet snapshot not.
- BUG-389 (MED, FIXED) two verdicts from unresolvable checks: RERANK IS ALREADY WIRED (retrieve.py:35/526 at
  HEAD 0182763) so the standing "RERANK WIRE" task is VOID; and the incumbent baseline was stale.
- CARRY: G4a repoint-the-floors now has a measured reason (the ruler in force changed).
