# Session handoff — 2026-10-14 (D-2993 + D-2994: the corroboration falsifier FIRED, and the retired scalar left the wire)

**Minted:** D-2993, D-2994 · **Bugs:** BUG-775, BUG-776 (both OPEN) · **Store writes: ZERO** — every number below is
a read (`file:…?mode=ro`), and the one behaviour-sensitive path (the serving prior) was verified UNCHANGED at 0.5.

## What landed, in two acts

**D-2993 — the falsifier, run read-only, and the T-118 word joined.** `P(n_voices ≥ 2 | is_convergent = 1)` measured
**1,393/1,393 = 1.0000** against a counterfactual of **0/6,247 = 0.0000**. The falsifier D-2992 attached to its own
ruling **FIRED**: `is_convergent` ⟺ `source_diversity ≥ 2` ⟺ `|source_ids| ≥ 2` on 7,640/7,640 rows (**three
columns, ONE bit**, BUG-775). The re-counting engine T-120 was scoped to build would re-derive a number the row
already states — **not built, on purpose**. The information is the INDEPENDENCE axis (`isor`: weak 5,212 / medium
969 / strong 410; 35 of the 938 served count-corroborated rows are WEAK). Landed: `config/served_fields.yaml#tier_policy`
(owner word `tier`, GRANTED) joined by **INV-10** — the declared tier vocabulary is asserted against the string
constants of the measure's own function, so a tier defined only in config is refused. New parity rail
`scripts/check_corroboration_bit.py` (6/6 controls, live 7,640/7,640 exact) + the two derivation rows
(`fbs.is_convergent`, `fbs.source_diversity`, home `stage1_5_embed_cluster.py::build_clusters`).

**D-2994 — the owner unblocked the T-107 change-set, and it landed.** `borp_score: retire` executed on **all three
surfaces** (MCP payload, OKF export, Anytype push) and machine-proven by the rail's AST scan of the payload's own
keys (INV-12); the **graded corroboration tuple** replaces it everywhere, assembled in **ONE builder**
(`pipeline/corroboration.py`) whose keys are asserted against the declaration (INV-11); the **feedback absence is now
explicit** (`{score, count, state, prior, effective}`, `state ∈ {measured, no_feedback}`) with the same one-home
treatment in `config/feedback.yaml#wire`; and the four neutral-prior literals in `pipeline/retrieve.py` moved onto
`config/feedback.yaml#serving.neutral_prior` (value 0.5 → served ordering byte-identical). The debt ceiling was
**lowered 3 → 2** (shrink-only, D-2644); `classification_status: keep-and-repair` is recorded with its repair act
named; `retired:` is checked in BOTH directions so a completed word cannot be prose.

## Next critical steps (consequential order)

1. **BUG-776** — the retired scalar's INTERNAL readers (`retrieve.py::_quality_field` fallback, two SELECT lists,
   `query.py` print, `run_monitor` constant metric, `retrieval_evaluator` format, the dead `ALL_FIELDS`). Owed as ONE
   change-set **with a retrieval-measurement receipt**, because it moves served ordering.
2. **classification_status repair** (keep-and-repair) — move `_classify_s4`'s undeclared threshold into config,
   re-prove the stored values, publish the row-level status the payload already carries (store write → C13 backup).
3. **T-117** — the ESCALATE surface (72 units / 311 rows), cause-grouped words on
   `governance/canonical_relabel_review_20261014.csv`.
4. **T-121** — the source-kind axis + per-kind identity (`config/source_kind.yaml` vocabulary, then the resolver).
   No non-book source may be ingested before it lands (BUG-774).
5. **T-104/BUG-757** — severity backfill (193 open bugs, no severity token → the register cannot be ordered).
6. **BUG-771** — stamp the golden sheet's premise hash and refuse a stale-stamp sheet.

## Hardware / models

- `Qwen3.8-Flash-Next` (any quant) — **do not download**: 360 GB bf16 base, ~125 GB community 4-bit, and `mlx-lm
  0.31.3` ships **no `qwen4_exp` module**. Two independent blockers (memory, runtime).
- `mlx-community/humanizer-12b-OptiQ-4bit` — **no**: arch `gemma4_unified` is not among the installed modules
  (`gemma4`, `gemma4_text` only), and its function (paraphrase/style transfer) is orthogonal to every stage and
  **dangerous on the record** — rewriting bodies would break the `gen_model`/`pipeline_commit` stamps and the
  no-mutation rule. If de-slopping is wanted, build a **violation detector** (a rail), never a rewriter.
- Already local and runnable: `~/.omlx/models/Qwen3.8-27B-MLX-4bit` (15 GB, `qwen3_5`). MTP buys nothing here
  (D-293: 0.98× on this exact machine). OMLX serves on **127.0.0.1:11435** with API key `sk-maxwell-local`.

## Rails at close (all re-run after the last edit)

`check_served_fields --selftest` **24/24** ✅ · live rail **rc 2**, 0 undeclared, 0 stale, **debt 2 == ceiling 2** ✅ ·
`check_corroboration_bit --selftest` 6/6 + live **7,640/7,640 exact** ✅ · `check_derivation_homes` ✅ (12 rows, 11
homed, 1 declared ceiling) · `check_rail_registry` ✅ (no unowned rail) · `tests/test_served_fields_spec.py`
**20 passed** ✅ · `gov_sync --apply` ✅ (1,122 decisions / 540 bugs / 17 open tasks) · bug census **OPEN 193 / CLOSED
347 of 540**.

**Delegation used (R5):** the new parity rail was reviewed by **gemma-4-E4B-it-MLX-4bit** over OMLX (one-shot,
temp 0.0, 3,540 prompt tokens). One finding was ACCEPTED (`main`'s hit/miss arm could miscount an unreadable
evidence set), the rest were rejected with reasons: `None → 0 works` for a NULL/empty `source_ids` is a TRUE value
(the evidence set really is empty), and only MALFORMED JSON is unreadable — those rows are reported as faults and
the rail exits 1.
