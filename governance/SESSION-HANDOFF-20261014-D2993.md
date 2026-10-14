# Session handoff — 2026-10-14 (D-2993: the corroboration falsifier FIRED; T-118 `tier` landed)

**Minted:** D-2993 · **Bugs:** BUG-775 OPEN · **Store writes: ZERO** (every number in this session is a read).
**Landed:** `config/served_fields.yaml#tier_policy` (T-118 GRANTED word, joined by INV-10),
`specs/served_fields.spec.md` INV-10, `scripts/check_served_fields.py` (+`tier_faults`, 7 new controls, 17/17 fire),
`tests/test_served_fields_spec.py` (+INV-10 test, 17 passed), `config/pipeline_config.yaml` (T-101 `anchor_mode: set`),
`governance/T120_S1_RECON_20261014.md`, `governance/buglog.md` (BUG-775), `config/task_register.yaml` (T-118 done).

## The one measurement that matters (T-120 step 0, read-only, D-2993)

`P(n_voices ≥ 2 | is_convergent = 1) = 1,393/1,393 = 1.0000` vs `P(… | is_convergent = 0) = 0/6,247 = 0.0000`,
0 NULL `source_ids`, on the declared population (CANONICAL_RUN `rechunk-v4-20260929`, 7,640 rows).

**The falsifier D-2992 wrote into its own ruling FIRED.** `is_convergent` ⟺ `source_diversity ≥ 2` ⟺
`|source_ids| ≥ 2` — three columns, ONE bit, no declared derivation (BUG-775). Consequences, in order of weight:

1. The expensive half of the T-120 mechanism (re-cluster `source_segments`, NLI-confirm a second voice) would
   **re-derive a number the row already states**. It is documentation on this corpus, exactly as the ruling said it
   would be if the falsifier fired. **Do not build it.** T-119 stays a cheap read-only delta.
2. The information is on the **independence axis** — `isor` (D2284/D2309; weak 5,212 / medium 969 / strong 410), where
   35 of the 938 served count-corroborated rows are WEAK, 148 carry ONE author and 170 ONE domain. That is the
   signal to publish, and the healthy signal is advertised by NO surface.
3. `borp_score = 0.0 on 7,640/7,640 rows` **while 1,393 rows are corroborated and 938 are served** — a false trust
   claim on 100% of rows, published to agents and written into two exports (BUG-767). Retire it; publish the tier.

## Forensic negatives cleared (do not re-investigate)

- `status` +1,049 QUARANTINE rows between the 2026-10-12 and 2026-10-13 pre-images: **0 rows changed status**; the row
  set grew by exactly the D-2590 non-FB sidecar tier. Not drift.
- `classification_status = 'CLEAN'` on all 7,640: the PRE-image of the relabel store write is identical. The axis was
  already uniform; the write did not flatten it.
- `fb_feedback` absent from the store: `CREATE TABLE IF NOT EXISTS` (`pipeline/feedback.py:118`) has never run because
  no rating was ever recorded; the cache NULL/0 is the DECLARED absence shape (D-2957). **The loop is correct today**;
  the risk starts at the first rating — land the wire shape (`{score, count, state, prior, effective}`) and move the
  `pipeline/retrieve.py` neutral-prior literal into `config/feedback.yaml` BEFORE that.
- Dedup: `0` duplicate `fb_id`, `0` `duplicate_of` markers, 3 name-collision groups / 6 rows — **all six in
  QUARANTINE, zero served**; 2 of the 3 groups are the same-source class. Corroboration was never the dedup
  guarantee and does not need to be.

## Next critical steps (consequential order)

1. **T-107 change-set** (the act T-118 and BUG-767 both wait on): stop publishing `borp_score` on the three surfaces
   (`maxwell_mcp_server.py`, `pipeline/stage6_okf_export.py`, `pipeline/stage6b_anytype_push.py`), publish
   `{sources, convergent, independence, independence_score, home}`, move the four neutral-prior reads onto
   `config/feedback.yaml#serving.neutral_prior`. Needs the owner word for `borp_score` (`retire`) and
   `classification_status` (`keep-and-repair`) — still PENDING in `config/served_fields.yaml#declared`.
2. **BUG-775** — declare the one bit in `config/derivations.yaml` with a parity rail that re-derives it from
   `source_ids` (same change-set as 1, so the wire cannot publish a tier that disagrees with the store).
3. **T-117** — the ESCALATE surface (72 units / 311 rows): cause-grouped words on
   `governance/canonical_relabel_review_20261014.csv` (DRS → CONFIRM; ALIAS-LAYER-RETIRED → CONFIRM; PROVENANCE-
   UNRESOLVED → CORRECT+home / ABSTAIN / LEAVE). Owner-ratified; each unit still needs its own word (D-2898).
4. **T-121** — the source-kind axis + per-kind identity (`config/source_kind.yaml` vocabulary, then the resolver).
   **No non-book source may be ingested before it lands** (BUG-774).
5. **T-104/BUG-757** — the severity backfill (192 open, no severity token → the register cannot be ordered).
6. **BUG-771** — stamp the golden-sheet premise hash and refuse a stale-stamp sheet.

## Hardware / models (asked this session, answered from the machine)

- `Qwen3.8-Flash-Next` (any quant) is **NOT runnable here**: the official base is 360 GB bf16, the community 4-bit
  MLX quant is ~125 GB (oQ4e/mix6 by `umixer`, 741 downloads), and the installed `mlx-lm 0.31.3` has **no
  `qwen4_exp` module** (it ships qwen3/qwen3_5/qwen3_5_moe/qwen3_next/qwen3_vl). Two independent blockers: memory and
  runtime. **Do not download.**
- Already local and runnable: `~/.omlx/models/Qwen3.8-27B-MLX-4bit` (15 GB, arch `qwen3_5` — present on disk).
- MTP variants buy nothing on this machine (D-293 A/B: 0.98× neutral on M1 Max; `mtp_enabled: false`).
- The only model work worth a slot is an **A/B** (D-332 measure-gated) of a candidate on the S2 extraction task — not
  a download for its own sake.

## Rails at close

`recompute_decision_summary --check` ✅ (1,121 decisions) · `gov_sync --apply` ✅ (4 faces equal their re-derivation;
1,121 decisions / 539 bugs / 17 open tasks) · `check_served_fields --selftest` **17/17** ✅ · live rail **rc 2**, 0
defects (the T-107 words are still owed) · `tests/test_served_fields_spec.py` **17 passed** ✅ · bug census
**OPEN 192 / CLOSED 347 of 539**.
