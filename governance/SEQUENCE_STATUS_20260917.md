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
| **G4** | **Blind-label the certified eval core**, n=100-150, concentrated on `content_type` + `discipline` + FORM | sheet to be generated (next) | 6-10 h | **every** model-accuracy claim, the retrain, the role decisions |
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
