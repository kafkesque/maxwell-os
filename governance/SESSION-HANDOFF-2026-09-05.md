# Session Handoff — 2026-09-05 (Auto-sorter training + Track B re-launch + BUG-224 mitigation)

> **Phase:** v3.0 auto-sorter (discipline/domain classifier) + label-quality pipeline
> **Current time:** 2026-09-05 23:17 +02:00
> **Working tree:** UNCOMMITTED (see §6) — decisions D2578→D2583 pending commit
> **Supersedes:** SESSION-HANDOFF-2026-08-24.md (and the D2567/D2572-D2574 work logged since)

---

## 0. TL;DR — where we are

The **auto-sorter** (a local ModernBERT-base classifier replacing the gpt-oss-20b
generative S4 teacher for discipline/domain) has been trained once, found
**data-limited not model-limited**, and its training set has been backfilled and
repaired. The **label-quality** blockers ahead of it are now unblocked:

1. **BUG-224 (OMLX wedge) — MITIGATED** (D2581): `call_omlx` now bounds reads and
   sleeps on wedge instead of hammering. This unblocks the 3-model vote + depth
   classifier.
2. **3-model label vote — SCAFFOLDED** (D2582): `scripts/label_vote.py` +
   `label_vote` config, aggregation logic unit-verified.
3. **Track B re-launch — COMPLETE** (D2583): 661 empty-raw emerging FBs → 195
   resolved + 466 raw-corrected. **Zero empty-raw emerging remain.**

The **immediate next action** is `bug197_kind_swap` to move the Track B-harvested
DOMAIN raw labels to the domain axis (~75% of that population are domain topics).

---

## 1. What was done (this session — D2577 → D2583)

| Decision | State | What |
|---|---|---|
| **D2577** | RESOLVED | Auto-sorter architecture revision: swap deberta-v3-base → **answerdotai/ModernBERT-base** (139M, 8192 ctx), **drop LoRA** (peft dep + invalid q_proj/value_proj no-op), depth → dedicated 4-way classifier (separate head). |
| **D2578** | RESOLVED | **Training run #1**: discipline macro-F1 **0.2621** (target 0.75), domain F1 ~0.0000. Root cause = **DATA** (silver labels ~75-90% + ~16-20 ex/discipline), NOT model selection. 7 blockers fixed en route. |
| **D2579** | RESOLVED | **Single-source backfill + stratification fix**: mined set 1000→**1026** examples, disciplines **61/61 covered**, trainable 50→58; the `stratify()` truncation bug (sorted-then-slice) fixed with floor + round-robin. 3 disciplines remain DATA-ABSENT (computational theory, ecology, robotics). |
| **D2580** | RESOLVED | Discipline stays **SINGULAR** (multi-label rejected); domain **ordering rejected** (sigmoid gives free rank); depth↔domain-count = **soft band**; 3-model vote must flag missing-close-domains + catch-all disciplines. |
| **D2581** | RESOLVED | **BUG-224 wedge-recovery**: `read_timeout=60` + `wedge_recovery_sleep=20`; `call_omlx` uses `timeout=(connect, read)` and distinguishes `ReadTimeout` (wedge → 20s sleep) from `ConnectTimeout`/normal backoff. |
| **D2582** | ACTIVE | **3-model vote scaffold** (`scripts/label_vote.py` + `label_vote` config): 3 cross-family voters, majority >=2/3 fail-closed, D2580 flags, single-FB calls, checkpointed/resumable. |
| **D2583** | RESOLVED | **Track B re-launch complete**: 661 empty-raw emerging → **195 resolved + 466 raw-corrected, 0 failed**; net emerging 956→761; 0 empty-raw remaining. |

---

## 2. Current system state (verified 23:17)

- **DB:** `knowledge pipeline/maxwell.db` — discipline=emerging **761**, empty-raw emerging **0**.
- **Decisions registry:** total **559**, active **460**, resolved **47** — `test_decision_summary_sync.py` exit 0.
- **OMLX:** healthy, v0.6.4 (health check passed during Track B).
- **Track B artifacts:** harvest `temp/trackb_full_20260905.jsonl` (661 corrected raw labels); log `temp/trackb_full_20260905.log`; backup `knowledge pipeline/maxwell.db.bak_20260905_202311_pre_reclassify`.

---

## 3. Next critical steps (priority order)

1. **`bug197_kind_swap`** on the Track B harvest — move the ~75% of raw labels that
   are DOMAIN topics (marketing/visual arts/graphic design) to the domain axis
   (the documented post-Track-B step; preflight found only ~25% are disciplines).
2. **Generate FBs for the 3 data-absent disciplines** — computational theory (4),
   ecology (4), robotics (1) cannot reach 5 examples even with full backfill;
   need NEW FB generation / targeted curation.
3. **Run the 3-model vote** — `python3 scripts/label_vote.py --run` over the mined
   golden set (`config/golden/stage4_golden_mined.yaml`, 1026 ex) to lift
   silver-label quality before re-training. Use small single-FB Qwen3.8 calls.
4. **Re-train auto-sorter** — longer epochs + hparam/label-smoothing sweep;
   hold macro-F1 >= 0.75 (current 0.2621 is the data-limited baseline).
5. **Stand up the 4-way depth classifier** (ModernBERT) + A/B vs gpt-oss on the
   held-out 50-FB frontier sample (gate macro-F1 >= 0.85).

---

## 4. Open decisions / questions

- **Third-voter policy (D2582 TODO #3):** default is Phi-4-mini-instruct-8bit
  (local); D2577 specified DeepSeek-v4-pro but it is CLOUD (C1/C3) + DELEGATE-001
  bug. Confirm before wiring the vote into the training refresh.
- **Missing-close-domain metric (D2582 TODO #1):** currently "any-absent"; upgrade
  to bge-m3 embedding-similarity closeness.
- **BUG-224 full verification:** the wedge-recovery is applied but UNVERIFIED under
  a live sustained-load wedge — needs a re-run of the Qwen3.8 bulk audit.

---

## 5. Known issue (latent, self-healed)

The 661 Track B FBs carried `taxonomy_match_method='emerging_real'` with **empty**
`discipline_raw` (self-contradictory — `emerging_real` means "real raw present").
Track B re-set both fields, so the population is now clean. **Root cause is
latent:** the kind-swap/demotion relabel scripts (`apply_d2399_user_decisions.py`,
`bug197_kind_swap.py`) clear `discipline_raw` without resetting
`taxonomy_match_method` → `emerging_unmapped`. Worth a low-severity bug + fix next
session (see also BUG-223's `'[]'` empty-raw hygiene).

---

## 6. Uncommitted working tree

**Modified:**
`DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `config/decisions.yaml`,
`config/pipeline_config.yaml`, `governance/buglog.md`, `pipeline/omlx_call.py`,
`pipeline/pipeline_paths.py`, `pipeline/schemas.py`, `scripts/train_discipline_classifier.py`

**Untracked (new):**
`config/golden/stage4_golden_mined.yaml` (1026-ex training set),
`scripts/mine_classifier_golden.py`, `scripts/label_vote.py`

---

## 7. Open bugs (12 total — appended per C15)

| Bug | Severity | Issue |
|---|---|---|
| BUG-224 | SHOULD | OMLX wedge under sustained load — **mitigated D2581**, unverified live |
| BUG-222 | SHOULD | goose `active_provider=custom_deepseek` → C1/C3 violation (D2560) |
| BUG-151 | SHOULD | taxonomy structural overlap (`education` dual-listed + 267 raw aliases) |
| BUG-148 | SHOULD | S2 `route` field stale/uniform (`route="FB"` on all 2,878) |
| BUG-182 | SHOULD | 48 singleton empty-shells re-return empty after S2 rerun |
| BUG-170 | SHOULD | non-principle types (PT/PI/TI/GE) not classified/enriched |
| BUG-159 | SHOULD | prompt-injection contamination (cluster_11649, 0.007%) |
| BUG-168 | SHOULD | `dspy_trainer.py` built-not-wired (wire OR archive) |
| BUG-160 | SHOULD | evidence-passage topical relevance unverified (1/30 drift) |
| BUG-223 | WORTH | `'[]'` literal-array raw hygiene (54 FBs); correct empty-test |
| BUG-169 | WORTH | TI `parameters` empty on 31+100 technique-type FBs |
| BUG-099 | WORTH | model registry drift (gpt-oss/Phi misnamed "verifier") |

> Full open-bug detail: `governance/buglog.md`. No open MUST-severity bugs.
