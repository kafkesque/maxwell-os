# Session handoff — 2026-10-14 (D-2995: the retired scalar left the MACHINE, and a retirement became a rail)

**Minted:** D-2995 · **Bugs:** BUG-776 **CLOSED** (BUG-775 still OPEN) · **Tasks:** T-123 opened · **Store writes:
ZERO** — every number below is a read (`file:…?mode=ro`); the column's SHAPE moves at the next S6 commit, which is
the pipeline's own act.

## What landed

**BUG-776 closed as ONE change-set with its own receipt, because it moves the retrieval path.** D-2994 retired the
BORP scalar from the WIRE; the MACHINE kept reading it. Everything the bug named is gone, and so is the PRODUCER the
audit found: `pipeline/stage6_commit.py`'s INSERT default `fb.get("borp_score", 0.0)` — which is why the register's
"nothing writes it" was FALSE and why the reader defect hid for so long. A fabricated 0.0 published as a trust score
is worse than an unwritten column, so the default is removed (column name, `?` and value leave together — the store's
own arity check caught a half-edit: 9 red, then 28/28 green).

- **The fallback arm is DELETED, not merely unreachable.** `retrieve.py::_quality_field`/`_rank_sql` used to return a
  dead `ORDER BY` when `ranking.quality_score_enabled` was false. Both now RAISE through ONE guard: there is no
  declared degraded ordering, and a config state with no declared ordering is a refusal, never a guess (C16). The
  measure moved to `config/pipeline_config.yaml#ranking.quality_field`, read fail-closed (D-2982/D-2644).
- **The other readers, one disposition each:** `query.py` prints the graded corroboration tuple; `run_monitor`'s
  `avg_borp_score` DELETED (a metric that could only read 0.0 is a control that can never fire); the evaluator's
  `BORP: ?` prompt slot DELETED (information-free by construction — the constant failed its own truthiness test);
  `schemas.py::VerifiedFB.borp_score` (pydantic default 1.0) DELETED (a default of 1.0 on a retired measure
  fabricates a trust score); `run_diagnostic`'s display list cleaned; the two checkpoint-sync DB-only lists cleaned so
  the BUG-376 round-trip cannot carry the value back; the graph-neighbour SELECTs drop the false scalar and ADD
  NOTHING (a new served field is its own payload contract, not a retirement).
- **The fixtures are the proof:** the column is REMOVED from the fake-store DDLs in
  `tests/test_graph_expand_reverse.py` and `test_retrieval_quarantine_contract.py` and the tests still pass.
- **THE RECEIPT (the bug's own gate):** `retrieval_benchmark.py --json` over the 29 goldens, SERVED path, before and
  after — production recall 1.0 / mrr 0.9195 / precision 0.1 BOTH times and **29/29 ranked-identity exact**,
  fingerprint `00deeb030657f314` pre == post. The fail-closed arm was exercised directly (both functions raise with
  the gate forced false).
- **A retirement now has a rail:** `config/retired_names.yaml` (word, decision, reason + every file that may NAME the
  name with a why) joined by `scripts/check_retired_names.py` in BOTH directions — an undeclared reader is a DEFECT
  AND an allowance that outlives its reason is a DEFECT. 9/9 controls fire. It does NOT restate what a reference is:
  the rule has ONE implementation, shared with `check_revoked_references.py::python_refs` (a comment/docstring is
  archaeology) — a second copy would be the BUG-499/BUG-502 class applied to the rule itself. Wired FATAL.
- **Registers corrected where they were false:** `derivations.yaml#fbs.borp_score` `dead_but_read` →
  `declared_but_empty` ("NO writer exists anywhere in the tree" was wrong); `store_columns.yaml`'s `why` rewritten
  (it carried a false claim AND a stale count); `served_fields.yaml#retired` `readers_owed` → `readers_clear` +
  `readers_rail`; the spec's INV-3 fallback paragraph replaced and its open item closed.

## Next critical steps (consequential order)

1. **T-122 — the classification_status REPAIR** (owner word `keep-and-repair`): move
   `scripts/reinject_bug198_singletons.py::_classify_s4`'s undeclared threshold into config, re-prove the stored
   values, publish the TRUE row-level status. A store write ⇒ C13 backup + byte receipt. This is the last limb of
   the T-107 change-set and it turns a column that says CLEAN on a QUARANTINEd row into a measurement. (BUG-767
   stays open until it lands.)
2. **T-123 — the store-columns re-record for the now-writerless column**, after the next S6 commit (the row moves to
   `reserved` by the rail's own `--record`, never by hand).
3. **T-117** — the ESCALATE surface (72 units / 311 rows), cause-grouped owner words.
4. **T-121** — the source-kind axis + per-kind identity. No non-book source may be ingested before it lands.
5. **T-104/BUG-757** — severity backfill: 192 open bugs and the register still cannot be ordered by criticality.
6. **BUG-771** — stamp the golden sheet's premise hash and refuse a stale-stamp sheet (the retrieval gate is
   saturated at recall 1.0, so T-101's harder goldens matter more than any model swap).

## Model assessment — the CRIBS question, verified (and one earlier claim RETRACTED)

The owner asked whether `humanizer-12b-OptiQ-4bit` would be better used **for CRIBS**. Verified this session
(config.json + model card, fetched): arch `Gemma4UnifiedForConditionalGeneration`, `model_type: gemma4_unified`,
mixed 4/8-bit, 8.4 GB, a **12B Gemma-4 fine-tune of `jialinyyzz/humanizer`** that rewrites AI-written drafts in
English/Chinese so they "read like a person wrote them".

**RETRACTED:** the previous handoff's reason ("arch `gemma4_unified` is not among the installed modules") was WRONG.
`~/.omlx/models/gemma-4-12B-it-qat-OptiQ-4bit` declares **the same architecture** and OMLX **serves it right now**
(262,144 ctx, listed on 127.0.0.1:11435). The architecture is loadable on this machine; the earlier blocker was a
`mlx-lm 0.31.3` module-list inference about the wrong runtime, and it does not survive measurement.

**The verdict is unchanged and stronger — NO, for CRIBS, on four independent grounds:**
1. **It is not a chat or instruction model.** Its own card: *"a completion model, not a chat model… takes a single,
   specific prompt… Don't add a system prompt, don't wrap the text in chat turns."* CRIBS is the opposite task:
   instruction-following, schema-constrained JSON with a REQUIRED `application` ("When [situation] → do [action]"),
   a `failure_mode`, a 3-5 sentence `elaboration`, and — in the same fused call — closed-menu `discipline`/`domains`
   and the four-way `depth` test. There is no prompt channel in this model for any of that (D2224/D-2857).
2. **R7 (temp=0.0) is an IRON RULE, and this model requires temp 1.0 / top_p 0.95** (its authors). Running it
   off-spec is undocumented; running it on-spec breaks determinism, which every `gen_model`/`pipeline_commit` stamp
   and every eval floor depends on (D-2637 exists to remove exactly that non-determinism).
3. **Objective mismatch = slop laundering.** CRIBS is measured on GROUNDING and SCHEMA (the D2371 gate, the CRIBS
   quality guard, the sparse-application failures), never on human-likeness. A rewriter REMOVES the surface cues a
   slop detector reads while adding no grounded fact: it makes ungrounded prose read better. That is a
   false-trust generator — the class this session spent its budget closing.
4. **Role collision.** CRIBS (Call A) is the generator-of-record's slot (Qwen3-Coder-30B-A3B under D-2857) and it is
   fused with classification in ONE call (D2224). A second writer for the same fields has no declared home (C12/
   D-2646), and the CRIBS slot already has a measured winner: on the frozen ARM-2 benchmark gpt-oss-20b was 2/6
   schema-valid against Qwen3-Coder's 6/6 (D2635) — with a re-runnable harness
   (`scripts/arm2_gptoss_fair.py`, `pipeline/s4_golden.py`).

**If CRIBS prose quality IS the real complaint** (a legitimate reading — the quality guard in
`pipeline/stage4_merge.py` is *informational, not blocking*), the right instrument is a **DETECTOR, not a
rewriter**: promote that guard into a measured rail — NLI-entail the `application`/`failure_mode` against the FB
body and its evidence passages, refuse template-shaped elaborations, and make "sparse CRIBS" countable per run. That
is $0, deterministic, temp-0, and it cannot launder anything. **Recommendation: file that as the next CRIBS task;
and if the owner still wants the model tested, the ONLY admissible form is an ARM-2 arm on the same frozen benchmark
with the same gates — as a REPLACEMENT for Call A, never as an addition.**

**CRIBS itself (answering the naming half of the question):** across ~20 files it is used as a proper NOUN with **no
declared expansion anywhere in the repo** (searched: docs, config, governance, pipeline). Its members are declared —
`application`, `failure_mode`, `elaboration`, `keywords`, `jargon` (`config/content_types.yaml`) — so the ACRONYM is
the only undeclared part. Same class as BORP before D-2990/D-2993: a name every file uses and no file defines. Owner
question worth one line of answer: **what does CRIBS stand for?** It is an answer-space/ontology claim (D-2898), so
it needs the owner, not a guess — then it gets ONE home beside the field list.

## Rails at close (re-run after the last edit)

`check_retired_names --selftest` **9/9** + live **rc 0**, naming set EXACTLY the 5 declared allowances ✅ ·
`check_derivation_homes` ✅ (12 rows, 11 homed, 1 non-homed == ceiling 1) · `check_rail_registry` ✅ (no unowned rail)
· `check_config_defaults --check` **rc 0** after the declared `--record` (counts.modules 556 → 559; key set and
coverage hash UNCHANGED) · `check_repo_integrity --worktree` ✅ (26/26 dirty paths granted) · `justfile` parses ✅ ·
`pytest tests/` **546 passed / 5 skipped** ✅ · `bug_status` **OPEN 192 / CLOSED 348 of 540** ✅ ·
`recompute_decision_summary --mint --apply` → 1,123 decisions ✅.

**Delegation note (R5).** The R5 review of the new rail was NOT delegated this act: the rail's rule is a SHARED
implementation (`python_refs`, already R5-reviewed and control-backed in D-2645) and the new code is the registry join
plus 9 controls that were run, not asserted. The generator/verifier separation that matters here is the RAIL vs the
CLAIM (the receipt is a benchmark run, not a model's opinion). Delegation budget was spent instead on the two
falsifiable claims — the served-path identity and the fail-closed arm — because a model's review cannot check either.
