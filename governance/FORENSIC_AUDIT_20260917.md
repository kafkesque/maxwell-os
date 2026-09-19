# FORENSIC AUDIT — 2026-09-17

> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Part of the 2026-09-17 report set:
> priority -> `PRIORITY_DECISION_20260917.md` | findings -> `FORENSIC_AUDIT_20260917.md` |
> external methods -> `MARKET_RESEARCH_20260917.md` | plan -> `STRATEGIC_PLAN_20260917.md` |
> execution + **human gates** -> `SEQUENCE_STATUS_20260917.md`. Floors + provenance vocabulary:
> `config/eval_integrity.yaml`. Axis values: `config/content_types.yaml`.
> **Do not restate a config value in this file - cite the path.**


**Scope:** the 4-axis ("spotless") adjudication pipeline, the runtime knowledge base, the S2
relabel provenance, the benchmark harness, and the governance mechanisms themselves.
**Method:** every finding below was re-derived from the filesystem, the SQLite runtime DB, or a
live probe today — not from notes. Nothing here is a recollection.
**Verifier:** the checks that are mechanistic are wired into `governance/p0_p1_criteria.yaml`
and re-run by `scripts/drift_monitor.py` (board at the bottom).

---

## Method (what was actually executed)

| Probe | Command / artifact |
|---|---|
| runtime vs adjudicated anchor | new `scripts/audit_runtime_vs_gold.py` (251 gold rows × 4 axes vs `knowledge pipeline/maxwell.db`) |
| axis completeness / sentinel | new `scripts/audit_nonprinciple_axis.py` (7995 rows) |
| relabel provenance | new `scripts/audit_relabel_provenance.py` |
| relabel actually applied? | `checkpoint.jsonl` vs `checkpoint.jsonl.pre_relabel` (8347 common rows) |
| contamination | 1027 train-pool examples vs the 251 gold rows (40-char shingle overlap, text pulled from the DB) |
| orphaned work | `remaining_axes_vote_checkpoint.jsonl` (190 rows) vs the frozen tiers |
| provenance census | `*_source` fields of every gold row |
| harness coverage | `tests/` (47 files) grep for `model_eval_suite` / `bench_preflight` |
| external | live arXiv API, HuggingFace model API, PyPI (see `MARKET_RESEARCH_20260917.md`) |

---

## Findings

### F-01 — CRITICAL — the runtime KB does not carry the adjudicated truth
`governance/gold_4axis.jsonl` (251 rows) is the project's own statement of truth for the four
axes. `maxwell.db` disagrees with it on 3 of 4 axes:

| axis | mismatches | share |
|---|---|---|
| domains | 199 / 251 | **79.3%** |
| discipline | 109 / 251 | **43.4%** |
| depth | 10 / 251 | 4.0% |
| content_type | 0 / 251 | 0.0% |

`scripts/propagate_content_type_decisions.py` (D2598) pushed **content_type only**; nothing ever
propagated depth, discipline or domains. The only 0% axis is the one that was propagated.
**Impact:** the product serves labels the project has already adjudicated as wrong; every
quality/recall claim measured against the DB is measured against rejected labels; the 4-axis
work is invisible to the runtime.
**Class:** silent divergence between eval anchor and runtime truth (no propagation step exists).
**Fix:** one propagation script (axis-by-axis, C13 backup + R14 manifest, authority sets imported
from `pipeline/axis_authority.py`, fail-closed on unknown source); wire the new audit as a
blocking criterion. **Effort ~2h. Now enforced by `AX4.runtime_matches_gold_4axis` (DRIFT).**

### F-02 — HIGH — 4057 machine relabels in production carry ZERO provenance
`checkpoint.jsonl` differs from `checkpoint.jsonl.pre_relabel` in **4057 / 8347** `extraction_type`
cells (`causal_mechanism` 3763 → 487), i.e. the FORM repair *was* applied. But no record carries
a provenance key: the strings `relabel`, `judge`, `budget` appear in **no** row (R14 violation).
**Impact:** which model, at which budget, with which prefix produced any of the 8402 FORM labels is
unknowable; the BUG-263 forensic reconstruction was only possible because stale backups happened
to exist. Retrofitting provenance is impossible for history.
**Class:** R14 / auditability. **Fix:** `scripts/audit_relabel_provenance.py` is now fail-closed
on the *artifact* (newest `relabel_report_*.json` must carry judge/budget/prefix/cross-family and
`cross_attempted > 0`) so no *new* relabel run can be unauditable. **Done today; historical gap
recorded as permanent.**

### F-03 — HIGH — 18.4% of the KB is unreachable by a depth filter, and reads as "failed"
Measured pattern (`depth / discipline / domains`, 7995 rows):

| content_type | pattern | n |
|---|---|---|
| principle | set / set / set | 6525 |
| process_template | **NULL** / set / set | 188 |
| process_instance | **NULL** / set / set | 139 |
| tool_instruction | **NULL** / set / set | 23 |
| growth_edge | **NULL** / set / set | 30 |
| noise_drop | **NULL** / set / set | 1055 |
| quarantine | **NULL** / set / set | 35 |

Only **depth** is affected (this CORRECTS the register's BUG-170 wording, which claims depth +
discipline + domains are empty for the non-principle sidecars). The design is unambiguous —
`pipeline/axis_authority.py` DP_ORIG carries the sentinel `n/a-non-principle` — so the runtime
should hold the sentinel, not NULL.
**Impact:** a depth-filtered retrieval silently drops 1470 rows; NULL is indistinguishable from
"classification failed", which is exactly the failure class this project keeps paying for.
**Class:** design/runtime mismatch + silent exclusion. **Fix:** one deterministic stamping pass
(sentinel value = a recorded decision, so the criterion is `warn`, not `fail`). **Effort ~1h.**

### F-04 — HIGH — the 190-row "remaining axes" vote finished and was never applied; and it proved the pending tier is not votable
`governance/remaining_axes_vote_checkpoint.jsonl`: 190 rows, written 2026-09-15 13:19; log ends
`done 145/145`. Tier files were last written 2026-09-15 00:45. Overlap with the frozen tiers:
0 with `gold_4axis`, 168 with `pending_4axis`, 22 with `silver_4axis`, 88 with
`expansion_queue_108.jsonl`.

The substantive result is the important part:

| axis | agreed | share |
|---|---|---|
| depth | 24 / 190 | 12.6% |
| discipline | 23 / 190 | 12.1% |
| domains | 12 / 190 | 6.3% |
| **all three** | **6 / 190** | **3.2%** |
| `needs_review` | 184 / 190 | 96.8% |

Compare the *principle* set voted on 2026-09-14: discipline unanimous 150/216 (69.4%). The
pending set is the hard tail, and the reliable-pair policy resolves almost **none** of it.
**Impact:** (a) 145 rows of work stranded in a checkpoint (data-loss risk); (b) the plan's
implicit assumption — "vote the rest and the anchor grows" — is falsified. Growth now requires a
human, a third *independent-family* voter, or accepting single-voter-with-confidence.
**Class:** orphaned work + falsified assumption. **Fix:** apply the 6 agreed rows, then record the
169 pending as `pending-by-design` (or adjudicate them in a real annotation tool, see research §A).

### F-05 — MEDIUM-HIGH — the anchor is far less "spotless" than the name implies
Provenance census of the 251 gold rows: `verification_status` = 65 `human-verified` (**25.9%**) +
186 `joint-vote-verified`. Per axis:

| axis | model-vote sources | human sources | single-model |
|---|---|---|---|
| content_type | 202 `joint-vote` | 21 `human` + 7 `frontier69` | **20 `p5:qwen38-ct-D2629`** |
| depth | 81 `joint-vote` | 104 `p5:human-d2615` + 18 `human` + 7 frontier | 20 reliable-pair revote |
| discipline | 142 `p5:reliable-pair-D2618p1` | 60 human-D2618p1 + 18 frontier | — |
| domains | 20 revote | 212 `p5:human-D2618p1` + 16 frontier | — |

Two problems: (1) **content_type — the axis with the worst measured model reliability (16/31 =
48% flips in the D2591 re-sweep) — is 80% model-voted**, and 20 rows come from a *single* model,
`qwen38`, whose family is the same family as the corpus generator (Qwen3-Coder) → not R5/C8
cross-family, admitted into `CT_FILL` by D2631. (2) domains are human but discipline is
majority model-vote, so the three axes have three different trust levels and are reported as one
"spotless" number.
**Class:** quality-gate mismatch / unmitigated R5 exposure. **Fix:** cross-family sample
re-verification of the 202 content_types (n≈50, gemma vs the Qwen-family label) + an
`n/a`/`UNVERIFIED` stamp on the 20 single-model rows.

### F-06 — MEDIUM — the benchmark harness has no test, which is the shared root cause of BUG-262..266
`tests/` holds 47 files; **zero** reference `model_eval_suite` or `bench_preflight`. Every recent
incident was a "harness did not read the answer" defect: no reasoning-off prefix (BUG-262),
budget 64 (BUG-263), poisoned rows never re-measured (BUG-264), native `tool_calls` ignored
(BUG-265), truncation reported as incapability (BUG-266).
**Impact:** the same class will recur the moment a new suite is added.
**Fix:** `tests/test_eval_harness_contract.py` — replay stored rows per suite and assert the
harness verdict matches the gate's rule; plus fake-transport tests for tool_calls-only,
reasoning-only and 400-at-budget responses.

### F-07 — MEDIUM — the R5 review tool was asking every script the wrong question
`scripts/r5_code_review.py` had a hardcoded task string ("repair a benchmark checkpoint by
removing rows measured by a broken harness") and a hardcoded prompt ("Decide whether it is SAFE
to run with --apply"). Reviewing three new audit scripts today, gemma **REJECTED two of them** —
not for a code defect but because it was asked about an `--apply` flag that does not exist.
**Impact:** every verdict in `governance/r5_reviews.jsonl` for a file other than the original
purge script answers the wrong question and must not be quoted as R5 evidence.
**Fix (done today):** prompt is now purpose-agnostic ("judge the code as written against its own
docstring"), the reviewer must answer `INSUFFICIENT` when the source cannot support the question,
and the default task is generic. The two scripts re-reviewed → **APPROVE**.
**Class:** evidence integrity — a verification artifact that looks like evidence and is not.

### F-08 — MEDIUM — disk at 95% (48 GiB free) before a 40–52h full-chain rerun
926 GiB total, 844 GiB used, 48 GiB available; the preflight floor is 15 GiB and
`memory_guard.min_free_gb` is 8. The tree holds 122 `*.bak_*` checkpoints (several 60–68 MB), a
1.2 GB `joint_vote_production_checkpoint`, three 135 MB-class DBs and five parquet snapshots.
**Impact:** an S2→S6 rerun plus backups can breach the floor mid-run; a full disk mid-write is a
data-loss event.
**Fix:** prune superseded backups into `backup/deletions/` and gate any full rerun on ≥150 GiB free.

### F-09 — MEDIUM — the entire corpus, DB and config live inside a third-party synced folder
Working tree = `/Users/barn/Library/CloudStorage/Dropbox/...`. 7995 FBs with `source_text`,
`maxwell.db`, gold labels and `.env` are replicated to Dropbox by the sync client. In tension
with C3 (sovereign / local-first), and it is the mechanism by which the 929-title manifest leaked
(D2441).
**Fix:** recorded decision required — either a documented sovereignty exception, or move the
working tree to a local-only path and sync only redacted exports. At minimum: no secrets and no
raw corpus text inside the synced tree.

### F-10 — MEDIUM — judge-family dependence is measured but not encoded as policy
Today's P0 run: gemma reproduces the stored FORM label 194/200 (**97.0%**, within family);
gpt-oss (independent family) matches 106/200 (**53.0%**, chance = 25%). Six verification scripts
(`dedup_judge.py`, `judge_suffix_duplicates.py`, `reverify_content_type_108.py`,
`classify_promotion_labels.py`, `apply_alias_corrections.py`, `deepseek_frontier_audit.py`) use
**Qwen3.8-27B** as judge while the corpus generator is **Qwen3-Coder** — same family → **none of
those six verifications satisfies R5/C8**, whatever their token budgets.
**Fix:** a rosetta rule in the role registry — every judging role carries (a) a different family
from the generator and (b) a recorded within-family reproducibility number. Then the ~770-call
re-verification pass is a targeted job, not a re-run.

### F-11 — LOW-MEDIUM — silent-empty-answer surfaces remain outside the two fixed paths
`pipeline/omlx_call.py` raises on `content is None` but returns `content.strip()` — silently `''`
— when content is an empty string. Twelve further call sites read
`choices[0].message["content"]` directly (`pipeline/dspy_trainer.py`, `tools/*.py`,
`scripts/*.py`). BUG-265's counterpart in production.
**Fix:** one shared response reader that normalises `tool_calls` / `reasoning_content`, and treat
`''` as retryable exactly like `None`.

### F-12 — LOW — the vote set was drawn from a partition that no longer matches the frozen tiers
The 190-row vote set overlaps `pending_4axis` (168), `silver_4axis` (22) and `expansion_queue_108`
(88) simultaneously. Any merge of its output has to guess provenance.
**Fix:** build verification sets *from the current tier files at run time* and assert membership
before the run (fail-closed).

### F-13 — LOW — accumulated drift in the tree
6 `__pycache__` directories and 122 `*.bak_2026*` files inside the working tree (C19). Cosmetic,
but it is the same "drift accumulates quietly" class as the rest.

---

### F-14 — CRITICAL — the 5th axis (extraction_type / object FORM) exists in TWO generations inside one store, with no provenance
`config/content_types.yaml` names its own axes: **AXIS 1 `content_type` = functional ROLE (what
kind of object: FB/PT/PI/TI/GE)** and **AXIS 2 `extraction_type` = epistemic FORM (how the claim is
justified)**. So "object type" is *already* axis 1. The genuinely un-adjudicated fifth axis is the
**FORM**. It has **no entry in `gold_4axis.jsonl` (0/251)**, **no per-row provenance column in
`fbs`**, and no integrity check until today.

Measured against the relabeled S2 checkpoint (`checkpoint.jsonl`, 8402 records):

| bucket | n | convergent FORM | single-source FORM |
|---|---|---|---|
| traceable to a checkpoint record | 3941 | causal_mechanism **11.1%** | causal_mechanism **4.6%** |
| UNTRACEABLE (no source record) | **4054** | 23.9% | causal_mechanism **56.4%** |

Known post-relabel baselines: convergent ≈11.2%, single-source ≈3.4%. The D2427/D2432 FORM-drift
repair took single-source `causal_mechanism` from ≈65% to ≈4%. The untraceable 3987 single-source
rows still sit at **56.4%** — the pre-repair distribution. Control: only **21 of 4054** untraceable
rows share a *name* with the checkpoint, so these are distinct objects from an earlier S2
generation, not renames.

**Impact:** **3,987 rows = 49.9% of the runtime KB serve the label the repair was built to remove**,
and `classification_status = CLEAN` on all 7995 rows, so nothing flags them. Any epistemically-aware
retrieval or verification that consumes FORM is fed two incompatible distributions at once.
**Class:** version skew + zero provenance + no integrity check. **Fix:** re-derive FORM for the
4054 untraceable rows through the (now fixed, provenance-emitting) relabel path; new
`scripts/audit_form_axis.py` + criterion `AX5.form_axis_traceable` keep it closed.

### F-15 — MEDIUM — the FORM axis has no verification consumer and no anchor, so it is decorative
`content_types.yaml` defines a per-FORM verification standard ("evidence must show the causal
chain", "categories complete + mutually exclusive", "correlation only — flag, do not assert
causation"), yet the W5 drift (documented 2026-08-14) is that **S5 (DeBERTa NLI) does not consume
`extraction_type`**, and the anchor contains no FORM labels. Today's P0 run produced the first
cross-family FORM measurement: 97.0% within gemma-family vs 53.0% against gpt-oss (chance 25%).
**Fix:** (a) a FORM sample anchor (n≈50–100, human, with the judging family recorded); (b) wire the
per-FORM rubric into S5 as a claim-level entailment target, which is what makes the FORM axis earn
its storage cost.

### F-16 — MEDIUM-HIGH — the human-provenance floor is measured with a substring classifier over an ambiguous vocabulary (found while answering the operator's clarification query)

`scripts/audit_eval_integrity.py::_tier()` classifies a provenance string by **substring**:

```python
if "human" in text or "locked" in text:  return "HUMAN"     # checked FIRST
if "reliable-pair" in text or ... :      return "MODEL"
if "frontier" in text:                   return "FRONTIER"  # unreachable for human-frontier*
```

`p5:human-frontier69` therefore classifies as **HUMAN** — 48 cells across the anchor carry it
(7 content_type, 7 depth, 18 discipline, 16 domains) — although the label's own name asserts a
frontier-model component. `FRONTIER` is in practice **unreachable**: a source can only reach it if
it contains `frontier` but neither `human` nor `locked`, and no such source exists in the anchor.

Second, and larger, the vocabulary is ambiguous. The operator confirms that part of the work
recorded under `p5:human-*` was performed by **reviewing a frontier model's proposed label**
(kimi / deepseek / claude), not by independent blind adjudication from the source text. A
see-then-confirm review is subject to **anchoring bias**: it measures "the human accepted the
model" far more often than "the human independently decided". The source string cannot
distinguish the two.

**Impact:** the four published human shares (content_type **0.116**, discipline **0.347**, depth
0.526, domains 0.920) are **upper bounds on an unknown denominator**. They are still the right
*order of magnitude* and they still justify the same priority decision — nothing downstream flips
— but they must not be quoted as if `HUMAN` meant "independently human-decided". The floor gate
`AXB.axis_human_share` is a valid *trigger*, not yet a valid *measurement*.

**Fix (ordered, cheap):** (1) replace the substring test with an **exact-match allow-list read from
config** — C12-clean, and it fails closed on an unknown source instead of silently guessing;
(2) split the vocabulary into `human-blind` / `human-ratified-model` and count **only
`human-blind`** toward the floor; (3) re-measure and re-publish the floors as bounds;
(4) mandate **blind** adjudication for all future human work — the model's proposal is hidden until
the verdict is written. Logged as **BUG-267**.

---

## Positive controls (verified good today — state them, do not re-litigate them)

- **No contamination leak.** 0 / 1027 train-pool examples overlap the 251 gold rows at >40%
  shingle overlap (text pulled from the DB, 4282 shingle universe). The eval anchor is disjoint
  from the training pool.
- **content_type propagation works** — 0 mismatches, the one axis ever propagated.
- **The `|P|` guard IS implemented** — `PEER_GRANULARITY_MAX_RATIO = 1.30` in
  `scripts/aggregate_domain_votes.py` and enforced in `_union_permitted()`; the domain-aggregation
  policy doc's action item is closed.
- **`axis_authority.py` is genuinely single-source** — import-time subset assertions, both
  consumers import it (D2626 holds).
- **Few-shot "empty content_type"** values are documented negatives (`should_extract: False`):
  23/84 convergent, 7/21 single-source. Not a gap. Single-source has the 11 non-principle
  positives the register claims.
- **The NA-as-DRIFT inversion is fixed** — `P1.gate_artifact_fresh` now reports a designed NA cell
  (gpt-oss/toolcalling = NO_JSON) as a named WARN instead of DRIFT, so a designed NA can never
  pressure the operator into weakening the gate.

---

## Drift board after this audit (`python3 scripts/drift_monitor.py --quiet`)

```
[WARN]  P1.gate_artifact_fresh           1 cell NA by design: gpt-oss-20b-MXFP4-Q8/toolcalling=NO_JSON
[WARN]  P1.roles_cited                   19 role(s) uncited — annotate or freeze them as UNVERIFIED
[WARN]  AX4.nonprinciple_axis_invariant  1470 non-principle rows with NULL depth (F-03)
[DRIFT] AX5.form_axis_traceable          4054 row(s) whose FORM is not traceable to a source record (F-14)
```

**F-01 was closed during this audit**: `scripts/propagate_4axis_anchor.py` wrote the adjudicated
labels for the 251 anchor rows (318 cells: 199 domains, 109 discipline, 10 depth) after an R5
review, and `audit_runtime_vs_gold.py` now re-derives 0 mismatches on all four axes.
`AX4.runtime_matches_gold_4axis` reads OK. The single remaining DRIFT is axis 5 (F-14).
