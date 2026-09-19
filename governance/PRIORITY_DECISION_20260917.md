# PRIORITY DECISION — 2026-09-17

> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Part of the 2026-09-17 report set:
> priority -> `PRIORITY_DECISION_20260917.md` | findings -> `FORENSIC_AUDIT_20260917.md` |
> external methods -> `MARKET_RESEARCH_20260917.md` | plan -> `STRATEGIC_PLAN_20260917.md` |
> execution + **human gates** -> `SEQUENCE_STATUS_20260917.md`. Floors + provenance vocabulary:
> `config/eval_integrity.yaml`. Axis values: `config/content_types.yaml`.
> **Do not restate a config value in this file - cite the path.**


**Question (user):** before executing the proposed next critical task, decide as a senior RAG /
systems engineer which work is top priority — the one that lets everything else benefit or
leverage it **without being blocked by the remaining tasks**.

**Candidates on the table:** (A) finish P2–P3 model assignments · (B) consolidate the anchor
sample (usable as golden *and* as fine-tune base) · (C) fix S0–S6 scripts/configs + consolidate
ModernBERT/DSPy · (D) rerun a stage · (E) integrate the market-research recommendations ·
(F) anything the audit revealed that was not on the list.

---

## 1. The lever test

A task is top priority if doing it makes the *other* tasks cheaper or measurable. Applying that to
every candidate:

| candidate | what it unblocks | blocked by |
|---|---|---|
| A. P2–P3 assignments | nothing about data; P2 removes governance churn; **P3's R5 re-verification is itself label-base repair** (6 decision lists) | nothing |
| B. anchor consolidation | retrain, pipe_* suites, ensemble choice, Ragas/retrieval metrics, S5 FORM rubric, every "is it better?" | human hours |
| C. S0–S6 + ModernBERT/DSPy | the pipeline build | **B** (see §2) — a retrain measured on circular labels is uninterpretable |
| D. stage rerun | the corpus | **B and C**; also 40–52h and 48 GiB free disk |
| E. market research | the pipeline's quality | **B** for every *consumer* item (A5/A6/A12); the *enabler* items are part of B |
| F. audit items | correctness of the runtime KB | nothing (mostly cheap and deterministic) |

**Only B unblocks others. A and F are cheap; C, D, E-consumers are downstream of B.**

## 2. The measurement that decides it (why "not yet" for the retrain/rerun)

Per-axis provenance tier of the 251-row anchor (today) and the measured consequence:

| axis | human share | tiers | measured reliability |
|---|---|---|---|
| content_type | **0.116** | 222 MODEL / 29 HUMAN | 48% flip on the D2591 re-sweep; 20 rows from a *single* model |
| discipline | **0.347** | 164 MODEL / 87 HUMAN | the voting pair that produced 164 labels scores 0.709 against them — but 0.437 on the 87 human-contested rows |
| depth | 0.526 | 132 / 102 / 17 n/a | mixed |
| domains | 0.920 | 231 / 20 | strongest; union aggregation hurts (D2633 v2) |
| extraction_type (axis 5) | **0.000** | — | no anchor at all; 3,987 KB rows still pre-repair (F-14) |

Two consequences decide the priority:

1. **Circularity.** The two weakest axes are exactly the two the pipeline's LLM roles are chosen
   against. Retraining ModernBERT now trains a student to imitate the judge that produced the
   labels and then evaluates it against that judge's output. "The student beats the teacher" would
   be an artefact, not a result. The same circularity makes `pipe_s4_classify`,
   `pipe_s4_content_type` and `pipe_voting` unscoreable today.
2. **Disjointness must be preserved, not assumed.** The anchor is BOTH the eval set and the
   candidate fine-tune base. Overlap is currently **0/1027** (verified) — that is the discipline
   that must be kept: the eval slice stays frozen and human; the training pool grows separately.
   Now enforced by `config/eval_integrity.yaml` + `scripts/audit_eval_integrity.py`
   (`AXB.train_eval_disjoint` = fail, `AXB.axis_human_share` = warn).

## 3. DECISION

> **PRIORITY 1 — consolidate the verified label base, de-circularised, focused on
> `content_type` + `discipline` + the missing axis 5 (`extraction_type`).**
>
> Everything else is either *cheap and rides along* (P2 freeze, F-03/F-11/F-06), *part of Priority
> 1* (P3's R5 re-verification, market enablers A1/A2/A3/A7), or *deferred because it would be
> unmeasurable or done twice* (ModernBERT, DSPy, stage rerun, market consumers A5/A6/A12).

The single sentence form: **stop choosing models and stop rerunning stages until the ruler is
fixed; fix the ruler first, and spend human hours only on the two axes that are actually broken.**

## 4. Ranking of the candidates (verdicts)

| rank | work | verdict | why |
|---|---|---|---|
| **1** | **Anchor de-circularisation** (B, redefined: content_type + discipline + axis 5, with a frozen human held-out slice) | **DO NOW** | keystone; unblocks retrain, pipe_*, ensembles, retrieval metrics |
| 2 | **Cheap deterministic repairs** (F-14 FORM re-derivation = only DRIFT, F-03 sentinel, F-11 shared reader, F-06 harness test) | **DO NOW (rides along)** | removes version skew and silent-failure surfaces *before* they contaminate a measurement; ~5h, no human |
| 3 | **P2 freeze** (19 uncited roles: 4 DECISION / 4 measurable / 11 stamp UNVERIFIED) | **DO NOW (1h, clear the desk)** | removes a recurring governance tax; Tier-A evidence is label-free so it is not blocked by Priority 1 |
| 4 | **R5 re-verification of the 6 same-family decision lists** (~770 calls, 30–45 min) | **PULL INTO PRIORITY 1** | those decisions (dedup 299 / merge 209 / content-type 108 / frontier 69 / alias 76 / promotion 8) are already in the corpus and were made by Qwen judging Qwen → they are label-base defects, and they must be settled *before* any rerun |
| 5 | **ModernBERT retrain + ARM-3 abstention + domain via the A5 bake-off** (C, build half) | **DEFER — gated** | gate = human held-out slice + floors met + beats the teacher on it + abstention arm chosen |
| 6 | **DSPy consolidation + S2→S6 full-chain rerun** (C/D) | **DEFER — gated** | forces a 40–52h rerun; unmeasurable on circular labels; also needs disk freed (F-08) and provenance stamped |
| 7 | **Market consumers** (A5 domain bake-off done early, A6 Ragas, A12 FORM rubric) | **A5 early, A6/A12 after Priority 1** | you cannot price a retrieval gain with a broken ruler; A5 is 1 hour and feeds the classifier decision |
| 8 | **P3 refinement** (native-tools gpt-oss trial, BUG-257 niah close-out) | **DEFER** | genuinely optional capability refinement; no other task depends on it |

## 5. What the list missed (the two most important things)

1. **Anchor circularity** (§2.1). Not a bug in a script — a property of the eval set. It is the
   reason "consolidate the anchor" is not merely useful but *blocking* for anything that selects or
   trains a model.
2. **One artifact cannot be both the golden eval set and the fine-tune base.** The user's framing
   ("anchor sample that can be used for golden sample and for fine tuning") would create leakage by
   construction. The correct shape is one *programme*, two *disjoint artifacts*: a small frozen
   human **held-out eval slice** (never trained on) and a larger growing **train/prompt pool**.
   Overlap is 0 today and is now a blocking criterion.

Also from the audit and still open: F-09 (the whole corpus + DB + `.env` inside Dropbox — a C3
tension and the D2441 leak vector; needs a decision, not work) and F-08 (48 GiB free — must be
fixed *before* the rerun, not during).

## 6. The ordered programme

| step | work | cost | gate / artifact |
|---|---|---|---|
| 1.1 | Instrument: Krippendorff α per axis, per-axis provenance floors, judge datasheet, per-suite `n_min` + stop rule | ~3h, 0 human, 0 model | `audit_eval_integrity.py` + α report |
| 1.2 | Cheap deterministic repairs: F-14 FORM for the 4,054 untraceable rows (**provenance on**), F-03 sentinel, F-11 shared reader, F-06 harness test | ~5h (2.5–3h model) | `audit_form_axis.py` exit 0 · guard test green |
| 1.3 | P2 freeze: 4 roles stamped DECISION, 4 measured, 11 stamped UNVERIFIED | 1h | `validate_role_claims.py` → 0 uncited |
| 1.4 | Targeted adjudication in Argilla (α live): content_type 222 model rows (sample-verify + the 20 single-model rows), discipline 164 circular rows (stratified sample) → freeze `anchor_v2_heldout` (human, n≈100–150, never trained on) | 2 resumable sessions | floors met per `config/eval_integrity.yaml` |
| 1.5 | R5 re-verification of the 6 decision lists with an independent family | ~770 calls, 30–45 min | per-list verdict artifact |
| 1.6 | S5 FORM rubric wired (the axis stops being decorative) + A5 domain bake-off | ~2h | S5 consumption test + bake-off report |
| 2.x | **Only then:** ModernBERT retrain (gated) → DSPy consolidation → full-chain rerun (disk freed, provenance on) → P3 refinement → market consumers | days | each with its own artifact + criterion |

## 7. Do-not (so the decision does not erode)

- Do not retrain, do not swap a role, do not rerun S2–S6 while an axis floor is unmet.
- Do not grow the anchor uniformly: domains (0.920) and depth (0.526) do not need human hours;
  content_type (0.116) and discipline (0.347) do.
- Do not train on the eval slice, ever. Disjointness is a blocking criterion now.
- Do not treat a model's agreement with a label that the same model produced as accuracy.
- Do not let the dropbox path (F-09) or the disk headroom (F-08) be discovered mid-rerun.

---

## 8. R5 status of the new mechanism (honest, not "approved")

`scripts/audit_eval_integrity.py` was reviewed by two independent families
(`governance/r5_reviews.jsonl`, append-only). Three rounds produced **two real defects, both fixed**:

1. md5 for shingles → replaced with blake2b (R5 flagged a broken primitive).
2. `sqlite3.connect()` on a missing DB **creates an empty file** and the failure surfaces later as a
   confusing "no such table" → the script now fails closed on a missing DB, a missing table, a
   missing anchor, and an empty anchor.

Residual: the last round objected that the docstring restated the floor numbers and could drift from
the config — resolved by referencing `config/eval_integrity.yaml` instead of copying it. Two earlier
rounds also returned `UNPARSED` / `INSUFFICIENT`, which exposed **a defect in the R5 tool itself**:
it wrapped verdicts in markdown fences, its naive `find('{')/rfind('}')` slice mangled long
verdicts, its reviewer budget was a hardcoded 700, and it asked every script the purge-specific
question. All four are fixed (`extract_verdict()` brace-depth parser, `--max-tokens`, generic
question, `--context-file`, and `INSUFFICIENT`/`UNPARSED` now exit 2 and are never recorded as
approval).

**Position on the residual:** for a *deterministic* audit script the executable evidence outranks an
LLM opinion — the criterion runs on every drift check, and the numbers reconcile with two
independent derivations (the audit and the propagation script). The R5 verdicts are recorded as-is,
including the rejections.
4. `check_disjoint` returned OK when the train pool was absent ("unverifiable") — fixed to fail
   closed; an unverified invariant is never OK.
