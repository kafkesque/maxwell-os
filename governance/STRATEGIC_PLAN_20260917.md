# STRATEGIC PLAN — 2026-09-17 (5-axis, post-P0/P1, post-audit)

> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Part of the 2026-09-17 report set:
> priority -> `PRIORITY_DECISION_20260917.md` | findings -> `FORENSIC_AUDIT_20260917.md` |
> external methods -> `MARKET_RESEARCH_20260917.md` | plan -> `STRATEGIC_PLAN_20260917.md` |
> execution + **human gates** -> `SEQUENCE_STATUS_20260917.md`. Floors + provenance vocabulary:
> `config/eval_integrity.yaml`. Axis values: `config/content_types.yaml`.
> **Do not restate a config value in this file - cite the path.**


**Inputs:** `FORENSIC_AUDIT_20260917.md` (F-01…F-13) · `MARKET_RESEARCH_20260917.md` (A1…A11) ·
`SYNC_20260917.md` · `p0_p1_contract.md` · drift board `drift_report_20260917_131612.json`.
**Rule for this document:** every phase ends in an **artifact with a re-derivable row count** and a
criterion in `governance/p0_p1_criteria.yaml`. If a phase has no criterion, it is not a phase — it
is a wish.

---

## 1. WHERE WE ARE — the 4-axis "spotless" process

### 1.1 The tiers (frozen, immutable by design — D2618 P0)

| tier | rows | role |
|---|---|---|
| `gold_4axis.jsonl` | **251** | the eval/measurement anchor (234 principle + 9 noise_drop + 3 quarantine + 3 process_template + 1 tool_instruction + 1 growth_edge) |
| `pending_4axis.jsonl` | **169** | the hard tail — not yet resolvable |
| `silver_4axis.jsonl` | **23** | train-only, never eval |
| `expansion_queue_108.jsonl` | **108** | D2619 d2615-principles — content_type re-verify first, never folded into the anchor |
| `verified_core.jsonl` | 443 | the pre-tier source (251+169+23 = 443 ✓ consistent) |

### 1.2 What the anchor actually guarantees (measured, not claimed)

| axis | verified by | level |
|---|---|---|
| content_type | 202 model joint-vote + 21 human + 20 **single model** (`p5:qwen38-ct-D2629`) + 7 frontier | **weakest** — 80% model, and this is the axis with the worst measured model reliability (48% flips, D2591) |
| depth | 104 human-d2615 + 81 joint-vote + 20 revote + 18 human + 7 frontier | mixed |
| discipline | 142 reliable-pair + 60 human + 18 frontier | majority model |
| domains | 212 human + 20 revote + 16 frontier | strongest |

Overall: 65/251 human-verified (**25.9%**), 186 joint-vote-verified. "Spotless" is currently a
*process* claim, not a measured one — see plan phase 1.

### 1.3 Where the process stopped, and why

| date | event |
|---|---|
| Sep 13–14 | D2618-P0 executed (tiers split, 1750 pair-agreed rows re-PASSed) · D2619 merge (443 → anchor 216 + queue 108) · D2623 straggler re-vote · D2625/2626 authority-set consolidation + guard wiring · D2632 ARM-1 (flat beats hierarchical) · D2633 domain policy (overlap→union) · D2634 **accuracy is training-data-limited, not anchor-limited** |
| Sep 15 10:53 | ARM-2 CRIBS benchmark → D2635: **gpt-oss retired as S2 generator** (6/6 empty under `response_format=json_object`) |
| Sep 15 11:19 | D2636: reranker domain-threshold sweep = **dead end**; zero-shot bge-m3 path still unbenchmarked |
| Sep 15 13:19 | **190-row "remaining axes" vote finished 145/145** → 6/190 full agreement, 184 need review |
| Sep 15 19:26 | `benchmark_plan_v2.md` written → **model-portfolio consolidation (D-2637) takes over** |
| Sep 16–17 | bug hunt: BUG-262…266, preflight gate M1, drift monitor M3, P0 fix, P1 role assignment |

**The 4-axis work was interrupted 1 hour after the last vote finished, and its output was never
merged.** That is the whole story of "where we are".

### 1.4 Critical tasks that were live at the interruption (verified against artifacts)

| # | task | status at interruption | now |
|---|---|---|---|
| 1 | merge the 190-row vote into `verified_core` | **never done** (tier files 12h older than the vote) | F-04 — and the result says it cannot close the tier |
| 2 | apply the `\|P\|` guard to domain aggregation | policy-doc action item | **verified done** (`PEER_GRANULARITY_MAX_RATIO = 1.30`, enforced) |
| 3 | ARM-3 abstention (raw vs conformal vs SetFit calibration) | never run | open — gates the classifier replacement |
| 4 | domain axis → training-free taxonomy match | reranker dead (D2636); zero-shot path unbenchmarked | open — plan A5 (1-hour bake-off) |
| 5 | classifier accuracy | **blocked**: trains on a 1027-example pool that is 93.3% unverified; 18/61 disciplines <10 examples | open — phase 3 |
| 6 | verified core → runtime DB | only content_type ever propagated | **F-01, the DRIFT on the board today** |
| 7 | Tier3 boundary corpus | 9 seed cases of a 150–250 target | open |
| 8 | 52 frontier objects (DeepSeek-proposal-only) | not human-confirmed | open |
| 9 | extraction_type sweep | locked behind content_type (order frozen in the register) | open |
| 10 | D2454 wire `stage4_golden.yaml` into the 4 S4 prompts | authored + test-validated, never injected | open |

### 1.5 Honest status of the earlier P0→P3

| item | status |
|---|---|
| P0 (BUG-263 fix) | **DONE** — artifact `relabel_report_20260917_123804.json`: 200 candidates, changed 1, failed 0, `cross_attempted 200`, `cross_failed 0`; probe artifact shows 64 → 0/4 JSON, 1024 → 4/4 |
| P1 (roles from evidence) | **DONE** — TOOL_CALLING_AGENT → Qwen3-Coder (n=20, 0.70); PLANNER retained (n=24, inside the pre-committed 1-item band); PLANNER_FALLBACK → REAP (evidence added today) |
| P2 (freeze) | **NOT DONE** — 19 roles uncited, in three non-homogeneous categories (§4) |
| P3 | **NOT STARTED** — native-tools trial for gpt-oss, niah ceiling close-out, 6 R5 re-verifications (~770 calls) |
| carry-over bugs | the false DRIFT (NA-as-drift) is **fixed today**; the 20→19 uncited roles is the only P2 blocker |

---

### 1.6 AXIS 5 — object type / extraction_type (added on request, 2026-09-17)

**Naming, settled from the schema's own words** (`config/content_types.yaml`): *AXIS 1
`content_type` = functional ROLE (what kind of object: FB / PT / PI / TI / GE)*, *AXIS 2
`extraction_type` = epistemic FORM (how the claim is justified)*. "What kind of object it is" is
therefore **already axis 1**; the fifth axis that has never been adjudicated is the **FORM**.

| axis | in the anchor (`gold_4axis`) | in the runtime DB | provenance |
|---|---|---|---|
| 1 content_type (object role) | 251/251 | 7995/7995 | per-row `*_source`, 80% model-vote (F-05) |
| 2 depth | 251/251 (17 n/a-design) | 6525 set + 1470 NULL (F-03) | per-row `depth_source` |
| 3 discipline | 251/251 | 7995/7995 | per-row `discipline_source` |
| 4 domains (43-way multi-label) | 251/251 | 7995/7995 | per-row `domains_source` |
| **5 extraction_type (FORM)** | **0/251** | 7995/7995 but **two generations** | **none — no column, no flag** |

Measured (F-14): traceable rows 3941 → convergent 11.1% / single 4.6% `causal_mechanism`;
**untraceable 4054 → convergent 23.9% / single 56.4%**, against post-repair baselines of 11.2% /
3.4%. `classification_status = CLEAN` on all 7995 rows. Control: only 21/4054 untraceable rows
share a name with the checkpoint → distinct objects from an earlier S2 generation, not renames.

So the honest 5-axis statement: **4 axes are adjudicated and now propagated; the 5th is
un-adjudicated, split across two generations, unprovidenced, and unconsumed by any verifier (W5
drift).** `AX5.form_axis_traceable` is the one remaining DRIFT on the board.

## 2. NEXT CRITICAL TASK (one, singular)

> **DONE 2026-09-17 — propagate the adjudicated 4-axis labels into the runtime KB.**
> `scripts/propagate_4axis_anchor.py` (R5-approved, dry-run→apply) wrote **318 cells** —
> 199 domains, 109 discipline, 10 depth — for the 251 anchor rows, after a C13 backup
> (`backup/deletions/20260917_131815/maxwell.db`) and with an R14 manifest
> (`governance/axis_propagation_manifest_20260917_131815.json`). `audit_runtime_vs_gold.py`
> independently re-derives **0 mismatches on all four axes**. `AX4.runtime_matches_gold_4axis` = OK.

> **NOW — re-derive the 5th axis (FORM) for the 4,054 untraceable rows, with provenance on.**
> 3,987 of them are single-source rows carrying 56.4% `causal_mechanism` against a 3.4–4.6%
> post-repair baseline: **half the KB serves the label the D2427/D2432 repair removed** (F-14).
> The mechanism is already fixed and proven — the P0 work gave the relabel path a config budget
> (1024), the reasoning-off prefix, `JudgeEmptyResponse` fail-closed, and a provenance artifact —
> so this is a re-run, not new engineering. ~4,054 calls at ~8s / 4 workers ≈ **2.5–3h**, and it
> must emit `judge_model` / budget / cross-family counts so `AX5.form_axis_traceable` goes green.
> Two design decisions travel with it: (a) FORM is **family-dependent** (97% within gemma-family vs
> 53% against gpt-oss), so the FORM anchor must fix and record its judging family; (b) wire the
> per-FORM verification standard into S5 so the axis stops being decorative (F-15).

Why the propagation was the right first move (kept as the template for the FORM job):

1. It is the **only DRIFT on the board**, and it is a *product* defect: `maxwell.db` serves 199
   wrong domain sets and 109 wrong disciplines on the 251 best-verified rows in the project.
2. Everything downstream that claims quality — retrieval filters, discipline-scoped recall, the
   classifier's own inputs, any "the KB is spotless" statement — is currently measured against
   labels the project has already rejected.
3. It is **deterministic and LLM-free** (~2h), so it cannot fail on model behaviour, and it is
   exactly the kind of task that gets skipped because it is not interesting.
4. It creates the propagation *mechanism* the project lacks (per-axis, authority-set driven,
   C13 backup + R14 manifest), so the next adjudication wave lands in minutes instead of never.

**Definition of done:** `python3 scripts/audit_runtime_vs_gold.py --max-mismatch 0` exits 0, the
DB backup exists under `backup/deletions/`, a manifest records the per-axis row counts, and
`AX4.runtime_matches_gold_4axis` reads OK on the next drift run.

---

## 3. THE PLAN

### Phase 0 — close the truth gaps (deterministic, ~5h, 0 model calls, 0 oMLX contention)

| step | action | artifact / criterion |
|---|---|---|
| 0.1 | **F-01 — DONE 2026-09-17** propagate depth/discipline/domains for the 251 gold rows into `maxwell.db` (318 cells; backup + manifest) | `audit_runtime_vs_gold.py` exit 0 · `AX4.runtime_matches_gold_4axis` OK ✅ |
| 0.7 | **F-14 (axis 5)** re-derive FORM for the 4,054 untraceable rows through the fixed, provenance-emitting relabel path | `audit_form_axis.py` exit 0 · `AX5.form_axis_traceable` OK · relabel report carries judge/budget/cross-family |
| 0.8 | **F-15 (axis 5)** build the FORM sample anchor (n≈50–100 human, judging family recorded) and wire the per-FORM rubric into S5 | anchor file + S5 consumption test |
| 0.2 | **F-03** stamp the documented sentinel (`n/a-non-principle`) on the 1470 non-principle rows' `depth` (or record the decision not to) | `audit_nonprinciple_axis.py` exit 0 |
| 0.3 | **F-04** apply the 6 fully-agreed vote rows; write `pending_4axis` status = `pending-by-design` with the measured evidence (3.2% agreement) so no future session re-runs it blindly | manifest + register entry |
| 0.4 | **F-02** keep the new provenance criterion green; write the historical gap (4057 unauditable relabels) into the buglog as *accepted and closed with cause* | `audit_relabel_provenance.py` exit 0 |
| 0.5 | **F-08** prune superseded backups; assert ≥150 GiB free | disk check |
| 0.6 | **F-11/F-06** one shared response reader + the harness contract test | `tests/test_eval_harness_contract.py` green |

### Phase 1 — give "spotless" a number (~3h, 0 model calls)

| step | action | decided by |
|---|---|---|
| 1.1 | **A2** Krippendorff α per axis over `gold_4axis` (nominal + multi-label variants), reported with n per class | α number; which axes are actually stable |
| 1.2 | **A3** judge datasheet (within-family reproducibility, cross-family agreement, abstain rate, position-swap) for gemma + gpt-oss + Qwen3.8 | datasheet JSON bound to the role registry |
| 1.3 | **A1** per-suite `n_min` + sequential stop rule for the benchmark suites; re-check the P1 decisions under it | do any role assignments flip? |
| 1.4 | **F-05** cross-family sample re-verify of the 202 model-voted content_types (n≈50, gemma) + stamp the 20 single-model rows | disagreement rate; decide whether the content_type tier needs a re-sweep |

### Phase 2 — the hard tail, bounded (~1 session of human time)

| step | action |
|---|---|
| 2.1 | **A7** stand up Argilla (or Label Studio) locally; import `pending_4axis.jsonl` (169) with 4 axes + confidence; compute α live |
| 2.2 | Adjudicate in priority order: rows the classifier will *train* on first, then eval-only rows |
| 2.3 | Rebuild tiers → `gold_4axis` v2 with an α-stamped provenance block; **never re-merge tiers** (D2618 P0) |
| 2.4 | **Tier3** populate the boundary corpus 9 → 150+ with the existing 2-of-3 adjudication schema |

### Phase 3 — the classifier, gated (~1–2 days, the only phase with real model time)

Per D2634 the root cause is **label quality + class starvation**, not architecture:

| step | action | gate |
|---|---|---|
| 3.1 | targeted ingestion for the 18 starved disciplines (9 CRITICAL + 8 HIGH + 1 MODERATE per D2607-D) | per-class support ≥10 before retraining |
| 3.2 | clean the silver training pool (reliable-pair relabel or weak-sup seeded from the verified core) | non-inferiority on the frozen `gold_4axis` split |
| 3.3 | retrain ModernBERT flat (ARM-1 winner) on cleaned labels | must beat the gpt-oss teacher on the 60-row gold (0.350 disc / 0.320 domain-F1) |
| 3.4 | **ARM-3** abstention arm chosen (raw 0.35/0.70 vs conformal/selective vs SetFit calibration) | coverage@precision curve, not accuracy alone |
| 3.5 | domain: adopt the **A5** bake-off winner; **drop the 43-way head** | macro-F1 vs the `taxonomy_match` baseline |
| 3.6 | only then replace gpt-oss as teacher | teacher swap is a role change → role registry + evidence |

### Phase 4 — wire the knowledge back into the pipeline

| step | action |
|---|---|
| 4.1 | **D2454** inject `config/golden/stage4_golden.yaml` into the 4 S4 classification prompts (live smoke first — it touches the S4 hot path) |
| 4.2 | `commit_non_fb_types` v2: ingest PT/PI/GE/TI sidecars **with** depth sentinel + discipline/domains, so the 18.4% becomes fully addressable |
| 4.3 | S0.5 metadata fix (pair_hit 0.58 / title_side 0.33 — verify the grader before blaming the model) and S4_5 enrich fix (0/12 procedural_skill) |
| 4.4 | S4 DEPTH: fix the **prompt+gold** (no model predicts `none`: 0/60 with 5 gold rows `none`, everything caps at 0.917). Do NOT enable `depth_frugal_enabled` |
| 4.5 | Rerun matrix (§5) executed for whichever of 4.1–4.4 changes consumer-visible output |

### Phase 5 — runtime recall/quality measurement (first time, ~1 day)

| step | action |
|---|---|
| 5.1 | **A6** Ragas locally with gemma as judge over a frozen query set; report as a trend line with its judge caveats |
| 5.2 | Publish the recall decomposition (context recall / claim recall / faithfulness / noise sensitivity) per pipeline version |
| 5.3 | Only now evaluate A5's structure question (`2609.18099`): does any graph expansion pay for itself? |

---

## 4. P2 CLOSURE (the freeze) — 19 uncited roles, three categories

| category | roles | action |
|---|---|---|
| **DECISION, not measurement** (4) | S4_DOMAIN_FALLBACK, S5_VERIFIER, NLI_VERIFIER, S6_VALIDATOR | stamp `DECISION` + rationale; stamping these `UNVERIFIED` would be false (they are deterministic/choice-driven, not measured) |
| **measurable now** (4) | S2_RELABEL_CROSS_FAMILY (today's P0 run **is** its evidence: 200/200 judged, 0 failures), S4_5_ENRICH, HYDE, RETRIEVAL_EVAL | run the suite or point at the existing artifact |
| **no evidence yet** (11) | S2_GENERATOR, S2_PROBE, S2_DSPY_TARGET, CONTEXT_CLASS, DRAFT_TRIAGE, CODING_COMPLEX_VALUE, CODING_LIGHT, CODING_DRAFT, CODING_CLEAN, EMBEDDINGS, RERANK | derive from existing suites where possible, else stamp `UNVERIFIED` **honestly** |

**Freeze gate (unchanged):** `scripts/validate_role_claims.py` reports 0 uncited, or every
remainder is explicitly stamped. Then freeze the three files (config, assignments draft,
CONSTITUTION §2) and their dependents in one commit with a manifest.

## 5. RERUN MATRIX (what forces what)

| change | forced rerun |
|---|---|
| runtime anchor propagation (phase 0) | **none** — DB label update only; no pipeline stage reads it at extraction time |
| Phase 2 tier rebuild | classifier eval split only |
| **FORM re-derivation (axis 5)** | S5/S6 for the affected rows **once the per-FORM rubric is wired**; today S5 does not read FORM, so the re-derivation is label-only |
| FORM anchor + rubric wired into S5 | S5 → S6 for the anchor rows (first time the FORM axis has a verification consumer) |
| **S2 DSPy consolidation** | **FULL CHAIN** S2 → S4 merge/classify → S5 verify → S6 commit, **plus** the FORM relabel and the 2641 never-relabeled convergent records |
| **S4 finetuned student** | **LABEL-ONLY**: S4 classify → S4_5 → S6 → domain aggregation → taxonomy promotion |
| S4 classifier swap (architecture) | label-only **+** the 60-row gold eval + ARM-3 |
| R5 re-verification of the 6 Qwen-family judges | the ~770-call decision lists only (299 dedup pairs + 209 merge groups + 108 content-type + 69 frontier + 76 aliases + 8 promotions), ~30–45 min at 4 workers |
| embedding change | S1.5 + all FAISS indexes + retrieval eval + HyDE + contextual embed |
| NLI change | S5 + S6 |
| portfolio/role change | benchmark suites only |
| prompt change inside S2/S4 | that stage + everything downstream of its output |

## 6. ANTI-DRIFT MECHANISM (why this plan cannot quietly rot)

1. **`scripts/drift_monitor.py` is the arbiter.** 24 criteria, exit 1 on any DRIFT. Any claim of
   "done" that the monitor contradicts is void. Today: 1 DRIFT (F-01) + 3 WARN.
2. **NA is never 0, and a designed NA is never DRIFT** — fixed today, so the gate can never be
   weakened to make a board green.
3. **No artifact, no claim** — every phase above names its artifact and its re-derivable count.
4. **Adjudication pre-committed** — tie within 1 item keeps the incumbent; a win on suspect gold
   counts for nothing (and now: no role decision on a suite below `n_min` — A1).
5. **R5/C8 by family, with a datasheet** — and the review tool itself was asking the wrong
   question until today (F-07).
6. **Timebox + kill criteria** — each step above is ≤1 session; if a step exceeds its box, it is
   reported as blocked with its artifact, never silently extended.
7. **One oMLX client at a time** (BUG-255: a reload evicts the single resident model). Phases 0, 1
   and 2 need **zero** model calls; only phase 3 does, and it will own the server.

## 7. DO-NOT LIST (the drift traps, written down so they stay closed)

- Do not re-verify domain before content_type (order locked, D2593).
- Do not bulk-reclassify ~10k rows; do not add a 6th content type; do not widen
  `content_to_extraction_type` to many-to-many.
- Do not A/B the correctness prerequisites (they are deterministic, D2618).
- Do not train a 43-way domain head; do not enable `depth_frugal_enabled`.
- Do not vote-populate the anchor; 3.2% agreement is the measurement that closed that door.
- Do not run two oMLX clients; do not use a frontier API as a judge.
- Do not declare any step done from stdout — artifact + row count only.
- Do not re-open DSPy before the D2594 gate (Tier1 + Tier2 + Tier3) is met.
- Do not call the store "spotless" while axis 5 is split across two generations (F-14), and do
  not write FORM labels without provenance — the 4,057 unprovidenced relabels are exactly why
  this defect took a forensic audit to find.
- Do not present a FORM judgement from a single family as objective: it is family-dependent
  (97% within / 53% across). Record the judging family wherever FORM is adjudicated.
