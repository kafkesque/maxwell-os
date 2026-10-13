# SESSION HANDOFF — 2026-10-13 · D-2988 · T-103 executed: the LICENSED store write

**Commit:** (this act) · **Authority:** D-2988 · **Closes:** T-103 · **Files the owner may want:** `governance/golden_reanchor_instructions.md` (T-101), `governance/canonical_relabel_review_20261014.md` (T-117's surface)

## 1. THE ASK, AND THE LEVERAGE CALL

The owner gave TWO answers in one message: **(a) "T-103 approve your recommendation"** — the licence — and **(b) a
challenge to T-107**: *"why is BORP score dead and why do you want to drop both feedback score won't be utilized
soon as the primitive or the non-principles get used?"*

**The owner's challenge was RIGHT and the first recommendation was WRONG.** Re-measured over the whole store, the two
fields are different defects, not one: `borp_score` is not-null on every row with exactly ONE distinct value (0.0)
and `config/derivations.yaml` registers it `dead_but_read` (home null, parity rail null). `feedback_score` is
populated on NO row — and the SAME registry names a WRITER for it (`pipeline/feedback.py::_update_fb_aggregates`)
with status `declared_but_empty`. It is UNPOPULATED, not retired; the serving path already ranks on it through a
declared neutral prior. **DROP borp_score; KEEP feedback_score** and make its absence explicit (null + a declared
state, the prior moved out of SQL into config, C12) with the parity rail its registry row still lacks. T-107's
register row now carries the measurement and the licence it is waiting for.

Leverage call: the OWNER LANE still led. T-103 was the only gate that could be CLOSED BY AN ACT (T-101 needs the
owner's hand on 30 cells; T-107 needs one word), and the licence turned a ruling into 163 served labels.

## 2. WHAT WAS BUILT (and why no existing writer could be reused)

The plan applier records CORRECT/ABSTAIN as OWED to a store write and never performs it (D-2898). The repo carries
twenty-odd ad-hoc `UPDATE fbs SET discipline` sites and NO instrument that could execute a ruling under a licence,
with a scope, a ceiling, a backup and a receipt. D-2988 adds exactly one:

* `config/relabel_rulings.yaml#store_write_license` — the ONE home of the owner word (decision, granted, LICENSED
  unit_keys, SHRINK-ONLY row cap, C29 tier, the receipt path). No licence → refuse, nothing written.
* `scripts/apply_relabel_store_write.py` — the writer. Its authority is that it **copies the PRODUCTION MAPPER's own
  answer** (the ONE home, `_map_discipline`) into the store for rows an owner ruling already reaches, so every row
  is TRIPLY agreed: mapper(raw) == owner target == the packet's recorded `live_mapper_says`. Four columns and only
  four (`discipline`, `discipline_macro` via `macro_for`, `discipline_source`, `taxonomy_match_method`); the raw
  is never touched; **scope is by fb_id, never by a predicate** — the difference between executing a decision and
  minting one. Six refusals, each NAMED: `scope/not-licensed`, `scope/not-ruled`, `target/disagreement`,
  `surface/stale`, `cap/exceeded`, `tier/undeclared`.
* `specs/label_store_write.spec.md` + `tests/test_label_store_write_spec.py` — INV-1..INV-8, 9/9 green (the receipt
  test re-reads every written row in the live store).
* `config/rail_mutations.yaml` — TWO new locks (the scope guard, the target-agreement guard), floor 41 → 43, both
  SEEN to red; `config/rail_registry.yaml#writers` declares the remedy; `justfile` runs its `--selftest` (12 known
  answers) and the registry audit reports every declared writer's remedy proven.

## 3. MEASUREMENT OF RECORD (before → after, same instruments, one difference)

| instrument | before | after |
|---|---|---|
| plan applier (`apply_relabel_rulings.py`) | CORRECT 4 / ABSTAIN 1 | **CORRECT 0 / ABSTAIN 0** |
| reference sheet subject line (queue B re-derivation gap) | 457 rows (6.9%) of 6,587 | **294 rows (4.5%)** (457 − 163) |
| queue B decision units | 60 | 55 |
| store | — | `marketing` 259→358 · `entrepreneurship studies` 1→5 · `software engineering` 167→107 · `emerging` +60 · `discipline_source='deterministic'` on the 163 written rows · `taxonomy_counts` recounted through its own home |

Receipt `config/label_store_write_receipt.json`: **changed=163 verified=163 planned=163**, every input hashed, the
store's `menu_hash` SET byte-identical before/after, backup `maxwell.db.bak_20261013_203654_pre_relabel_store_write`
(219,467,776 bytes) taken after a PRAGMA integrity gate. R5 gate: syntax PASS, lint PASS, C11/C12 PASS, reviewer
gemma-4-E4B-it-MLX-4bit **APPROVE**.

**A PROSE DEFECT CLOSED WITH IT.** The previous BUG-749 section's REMAINING list summed to 467 while the gap it names
is 457: the 10 `DEFINITION-RE-SCOPE` rows are QUEUE A (the D-2974 re-scope differential), not the re-derivation gap.
The sheet's header names the two subjects separately; the prose mixed them. The number of record is now the
instrument's own.

## 4. FORENSIC AUDIT (what the act checked before it wrote)

* **Cascade**: `taxonomy_counts` (10,091 label rows) would have gone stale the moment 163 rows moved — the writer
  calls `update_counts_from_fbs` (its ONE home) inside the same transaction. `store_columns.yaml` declared
  `discipline_source.distinct = 1`; the write makes it 2 — re-recorded through the rail that owns that block
  (`--record`, backup `store_columns.PRE_...yaml`).
* **No second home**: driver = the packet's own mapper; macro = `macro_for`; tier = `PROVENANCE_LITERAL`; counts =
  `taxonomy_manager`; the method rule mirrors stage4's declared rule (three lines, cited). No target, count or
  vocabulary is restated.
* **Pins / provenance**: `verify_recalibration_pins` 6 pinned 0 DRIFT; `check_label_provenance` 7,640 stamped, 0
  missing; `check_derivation_homes` clean; `check_repo_integrity` clean; `check_bug_status` clean;
  `gov_sync --check` and `check_governance_faces` green after the re-cut.
* **Mutation fixture**: the new selftest is HERMETIC (proven by running it in a scripts/+config/-only tree), so its
  two mutation locks red for the MUTATION's reason, never because the fixture lacked `pipeline/` (the BUG-527 class).

## 5. RESIDUALS (declared, not fixed) and the NEXT CRITICAL STEP

1. **T-117 (NEW, MUST, owner)** — the ESCALATE surface: the 72 units / 311 rows no ruling reaches. One owner word
   per unit on `governance/canonical_relabel_review_20261014.md`. This is the residual BUG-749 now carries.
2. **BUG-766 (NEW, MED, OPEN)** — `check_store_columns --check` is rc=1 on 6 POPULATION-SHAPE drifts (six columns
   declare `outside: absent`=NULL while 1,049 sidecar rows hold a NON-NULL blank) — **measured pre-existing**: the
   ladder receipt of commit 673a457 at 18:33 already records rc=1 on that line. Fix: reshape to TRUE NULL, then
   `--record`.
3. **T-104 / BUG-757 (MUST, pipeline)** — 101 of 185 open bugs carry NO severity token; unchanged this act, and now
   one bug larger. **The next critical step of the pipeline lane.**
4. **`fbs.discipline` is NOT in `config/derivations.yaml`** — the value the licensed write just moved has no
   registered home and no parity rail, while twenty-plus call sites write it. That registration is the natural
   follow-up to D-2988 (ONE DERIVED VALUE, ONE HOME, D-2646).
5. The `ratified` ontology question from D-2987 (is it distinct from `active`?) is still the owner's, now signed ⚖.

## 6. OWNER LANE (what only the owner can do)

| id | one thing | the file |
|---|---|---|
| T-101 | write `anchor` on ONE row per query + a signature (30 cells, not 150) | `governance/golden_reanchor_instructions.md` + the candidates CSV |
| T-117 | one word per unit: CONFIRM / CORRECT + home / ABSTAIN / LEAVE | `governance/canonical_relabel_review_20261014.md` |
| T-107 | DROP borp_score? KEEP feedback_score (with the absence made explicit)? | this handoff §1 + the register row |
| D-2987 | is `ratified` a distinct state or a synonym of `active`? | `config/gov_sync.yaml` |

## 7. DELEGATION (honest)

No ad-hoc delegate: this act is ONE rule whose writer, spec, test, mutation lock and receipt are the same subject —
splitting it would create two writers of one rule (the D-2984 lesson). The local-LLM call was the ratified R5 gate
on the new script (gemma-4-E4B-it-MLX-4bit, APPROVE).
