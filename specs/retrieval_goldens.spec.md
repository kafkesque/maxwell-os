# SPEC — the retrieval GOLDEN SET's re-anchor gate (`scripts/reanchor_retrieval_goldens.py`)

> **Paired contract:** `tests/test_retrieval_goldens_spec.py` (spec-first: D-2978 — one spec per governed surface,
> paired 1:1 with a pytest).
> **Authority:** D-2939 (an anchor is an owner-signed NAME), D-2898 (a guess is not a label), D-2991 (an anchor is a
> SET, and *which* one is DECLARED), D-2987 (the review vocabulary has ONE home), T-101 (harden the ruler).
> **The surface:** the ONLY path from a reviewed sheet to `config/golden/retrieval_queries.yaml`.

## Why this spec exists now (measured, not asserted)

The applier shipped with **no spec, no pytest and no ladder pin**, and it carried the SAME judgment in two places
(`--check` and `--apply`). MEASURED 2026-10-13 on the owner's 150-cell review
(`governance/golden_reanchor_candidates_20261011.reviewed.csv`, 30 queries × 5 candidates):

* `--check` reported **48 faults** — 19 rows carried the misspelling `ambigouos` (a token read by **nothing**), and
  29 queries carried **more than one** `anchor`;
* the rule that failed them ("exactly ONE anchor per query") is a rule about the **sheet**, but the harness it feeds
  (`_recall_at_k`) is **micro over a set** and the format (`expected_names`) is **a list** — so the owner's richer
  mark was refused by a limit that the ledger it writes never had;
* every one of the **116 distinct anchored NAMES resolves uniquely** in the served run (`chosen anchor does not
  resolve` would have fired otherwise) — the refusals were all **semantic**, not data.

Two of those three faults are *the same defect* this OS keeps paying for: a token/format whose meaning lives in its
reader instead of in a declared home (D-2987's lesson, repeated one field over).

## Invariants

### INV-1 — The review vocabulary has ONE home, and the applier refuses to guess it
`config/pipeline_config.yaml → retrieval_benchmark.reanchor.decisions`. An empty vocabulary is a **fail-closed
startup error**, never a default (C16). The checker **names** an offending token and prints the allowed set, and
offers a *near-miss suggestion* — but never accepts one: **a token the reader guesses is a token the writer cannot
trust**.
*Correct:* `ambigouos` → refusal + `did you mean 'ambiguous'?`.
*Wrong:* `ambigouos` silently normalised to `ambiguous`.

### INV-2 — The anchor is the NAME; the id is a POINTER (D-2939)
An anchored name is resolved in the serving scope at apply time and the resolved ids are recorded as the verified
snapshot. A chosen name that does not resolve **refuses the whole write** (a silently dropped query would fall out
of the denominator later, BUG-710).

### INV-3 — Exactly one owner-signed anchor per query, OR a DECLARED set
`reanchor.anchor_mode` is declared in config and is one of:
* **`single`** (the v2 rule): exactly ONE `anchor` row per query; more than one is a **refusal**.
* **`set`**: every `anchor` row for the query **is** the query's expected set, ordered by rank.

The mode is **never inferred from the sheet**. An inferred mode is a metric whose meaning depends on the data it
was computed from — the definition of a metric that cannot be trusted across runs.

### INV-4 — The expected SET is what recall is measured over (the only reason a set is allowed)
`pipeline/retrieval_benchmark.py::_recall_at_k` is **micro over `expected`** (`hits / len(expected)`), and
`pipeline/golden.py::resolve_golden_anchors` resolves **every** `expected_names` entry. Therefore enlarging a
query's expected set makes the ruler **stricter**, not looser — which is T-101's whole purpose (a saturated metric
cannot gate an improvement). A set that made recall *easier* would be a defect, not a feature.

### INV-5 — An abstention is declared, excluded and COUNTED; an unjudged query refuses the write
A row marked `ambiguous` means *"I looked and I cannot tell"*: that candidate is **excluded from the set** and
**counted** in the report (never silently dropped — D-2957's discipline applied to a judgment). A query with **no**
anchor and no `retire-query`/`rewrite-query` verdict is **UNREVIEWED** and refuses the apply: a guess is not a
label. Consequence: `ambiguous` on *every* row of a query **parks that query** and blocks the write.

### INV-6 — ONE judgment, TWO callers
`judge_review(rows, queries, mode, signature_required, live)` is **pure and store-free**, and is called by BOTH
`--check` and `--apply`. Two implementations of one rule drift, and the drift is invisible in exactly the direction
that hurts: a pre-flight that passes a sheet the writer refuses (the D-2642 class, in a control instead of a value).

### INV-7 — A dropped query is dropped on purpose; an added one is DECLARED
`retire-query` and `rewrite-query` drop the query from the set (reported). A draft query that is **not** in the live
set is reported as an **ADD** before the write: adding is legitimate and is half of what T-101 asks, but it must be
a deliberate act, never the side effect of an apply (D-2987).

### INV-8 — Nothing is written without a C13 backup
The live golden file is copied to `<name>.bak_<STAMP>` before the write (C13).

### INV-9 — The pre-flight writes NOTHING, touches NO store, and reads its inputs from config
`--check` returns `1` on any fault (loud, C16) and `0` when the sheet is appliable; it never opens the store and
never writes a file.

### INV-10 — The judgment is proven by known-answer controls, run by the ladder
`--selftest` evaluates the controls in `controls()` and prints `ok reanchor --selftest: N/M known-answer
control(s) fire`; a failing control prints `  !!  <label>` (the marker the mutation gate looks for). A guard that has
never been SEEN failing is a comment (BUG-492).

## Evidence of record at birth (2026-10-13)

| measurement | value |
|---|---|
| the owner's reviewed sheet | 150 rows · 30 queries · 5 candidates each |
| `anchor` marks | 120 (29 queries) · `rewrite-query` 11 · `ambigouos` 19 (one misspelling, 19 rows) |
| its verdict under `anchor_mode: single` | **REFUSED** — 48 faults |
| its verdict under `anchor_mode: set` (after the typo) | appliable — 29 queries, 116 anchor names, 0 unresolved |
| names that resolve uniquely in `rechunk-v4-20260929` | **116 / 116** |
| the live set before this pass | 29 queries, 1 expected name each, `recall@10 = 1.000` (saturated) |

## What this spec does NOT claim

It does not claim the candidate pool is unbiased: the generator draws candidates from the **production leg's own
top-N**, so a leg's recall on a set built from its own pool is **self-referential** (BUG-717 recorded the same
asymmetry for rank-1). Measuring legs against a pooled candidate list is the next instrument, not this one.

### INV-11 — A live query absent from the draft is a REMOVAL nobody judged (BUG-968, T-116)

`--apply` writes the golden file from the **draft alone**. Before this invariant, a live query the draft did not
carry was deleted by the write with **no verdict, no fault and no report** — the C13 `.bak` was the only trace.

*Correct:* `judge_review` reports the omitted live queries in `dropped_by_omission` and raises one fault per query;
`--check` (rc 1) and `--apply` (rc 2) both refuse, because both call the one judgment (INV-6).
*Wrong:* an apply that silently shrinks the owner-signed ruler.

The rule has **no config knob**: a retirement is already declarable in the sheet (`retire-query`/`rewrite-query`,
INV-5), so a flag beside it would be a second way to say the same thing (C12). A query the sheet reviews but the
draft does not carry is `orphan_reviewed_rows` — **reported, never a fault**: MEASURED 2026-10-23, the declared
sheet carries exactly one such query (the one v5 retired on purpose), so faulting there would refuse the very
sheet that produced the live set.

**Declared fail-open:** the guard is defeated when a caller omits `live` (`live_set` becomes empty). Both
production callers pass `live=sorted(live)` — MEASURED 2026-10-23, 2 of 2 call sites, pinned by
`test_inv11_both_production_callers_measure_the_live_set` — and both compute it from the golden file with an
`else set()` branch, so the omission case coincides with *no golden file exists*, where nothing can be deleted.

**R5 (2026-10-23):** gemma-4-E4B-it-MLX-4bit returned SHIP on all five questions, and its Q2 justification
described this fail-open correctly while labelling it OK — the author trace is what pinned the caller count.
An R5 SHIP is a smoke test, not a proof.

### INV-12 — The stored snapshot is EVIDENCE, never an AUTHORITY (BUG-969, 2026-10-23)
`resolve_golden_anchors` used to `ids.extend(q["expected"])` **unconditionally**, so the receipt of the last apply
sat in the denominator beside the names — a **second authority** in a metric (the BUG-548 shape: *the record is not
the rule*). Consequence when armed: after a rebuild, ids minted by an earlier corpus are dead, `_resolvability`
fails the whole run (rc 2) **though every NAME resolved**, and `--allow-unresolvable` would deflate recall against
dead ids — the BUG-710 inversion reached through a flag.
*Correct:* the snapshot is the **legacy fallback** for a query that carries no `expected_names` (and for the legacy
`id` anchor mode). Where names exist they are the ruler, and what was ignored is reported as `snapshot_ignored`.
*Wrong:* a stored id that keeps a query measurable after the owner-signed name stopped resolving — an unresolvable
name must EXCLUDE the query (an unreported stale id masks exactly the fact the rail exists to print).

**Measured live (2026-10-23):** 29 of 29 queries carry both names and a snapshot, the name-resolved set equals the
snapshot set (116 distinct ids, 0 resolved-only, 0 snapshot-only), and the per-query expected sets are **identical**
before and after the change — the fix is a live no-op that removes the armed harm, not a metric shift.

### INV-13 — A duplicated label ENLARGES a set-valued ruler, never excludes the query (BUG-970, 2026-10-23)
An `AMBIGUOUS` label (>1 PASS row) used to EXCLUDE the whole query from the denominator. In a **set-valued** ruler
that makes the metric **looser** — the direction INV-4 forbids (*enlarging a query's expected set makes the ruler
stricter*). The refusal is correct only for a **single-answer join**, where choosing one of two rows is a coin flip.
*Correct:* in `anchor_mode: set`, every PASS row sharing the label is in the expected set and the multiplicity is
reported (`report["multiplicity"]`, printed by the benchmark); in `anchor_mode: single` the refusal stands.
*Wrong:* one duplicated label silently dropping 116 owner-signed anchors from the measurement.

The **mode is not a second knob**: the resolver reads the ONE declaration the applier already obeys
(`retrieval_benchmark.reanchor.anchor_mode`), fail-closed on an absent block or an unknown token (C12).
**Measured live (2026-10-23):** 0 PASS names are duplicated in the canonical run and 0 across all runs, so this
rail is *armed, not exercised* — it is armed by T-116's pooled candidate pool, and the store already holds 5
duplicate `concept_key`s across 7,640 rows (D-3129: report them, never collapse them).

**Proof (both invariants):** `python3 pipeline/golden.py --selftest` — 5/5 known-answer controls. The controls were
run against the resolver **as it was at HEAD** first (`RED LOOP`, D-3036): 1 of 4 predicates held — the dead id was
unioned in, a dead name was rescued by a stale id, and a duplicated label excluded the query. Paired tests:
`tests/test_retrieval_goldens_spec.py` (`test_inv12_*`, `test_inv13_*`).
