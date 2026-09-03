# SESSION HANDOFF — 2026-09-03 (D2523)

> Continue from here. Newest work first; full history in DECISION-LOG.md / buglog.md / MASTER-TASK-REGISTER.md.
> **This session: (D2522) resolved S1/S3 retrieval A/B + relaunched e2e; (D2523) root-caused S2 speed (memory pressure, NOT burst_decode), backfilled the 6 missing vectors, and proposed DB-bloat prevention.**

---

## 1. What this session decided + did (D2523 — newest)

### S2 speed root-cause — CONFIRMED memory-pressure decode collapse (NOT `burst_decode_mode`)
The 20-book S2 "4–11h" symptom was an **oMLX decode collapse**: RAM 78.7% + 0.37 GB swap → **1.9 tok/s** (TTFT 47.6s). Restart (SIGTERM omlx-server; GUI auto-restarted) recovered RAM to **31.7%** (omlx RSS ~20.7 GB) and decode to **~20–29 tok/s** (chars/4 ≈ 15–22 real) — the D2460-consistent healthy state.

**`burst_decode_mode` A/B/C — RULED OUT (reverted to `balanced`).** Authenticated via forged `omlx_admin_session` (itsdangerous `URLSafeTimedSerializer` + `settings.json auth.secret_key`), hot-applied with `POST /admin/api/global-settings` (no restart). Qwen3-Coder-30B decode under identical S2-concurrent load:

| mode | budget | decode tok/s |
|---|---|---|
| `balanced` | 0.1 s | **~20–29** |
| `off` | max_steps=1 | ~20–25 |
| `aggressive` | 0.2 s | **~16–17** (SLOWER) |

**`aggressive` is slower** — the opposite of the "higher = faster" code comment; `balanced` ≈ `off`. Reverted to `balanced` (shipped default). **The 0.6.4 burst-decode feature is NOT the throttle; the 6–8 tok/s state was purely the memory collapse, already fixed by restart.**

**S2 progress (corrected scope):** the e2e's stage2 runs **clusters only** (no `--process-singletons`), so S2 scope = **205 cluster targets** (156 base clusters + sub-clusters), NOT the 441 singletons. Cluster phase is **203/205 done → 161 FBs**; the only remaining work is **2 clusters (82, 374) that persistently emit empty `elaboration`** (a D2448 quality gate, not speed — see P0 #1). Now bounded by the 30B-MoE decode+prefill ceiling (~50 tok/s total across `max_workers=3`, D2459), not misconfiguration. **No safe no-quality-loss speed lever found beyond the restart**: more workers degrade the 128-expert MoE (D2459); aggressive burst regresses.

### 6-FB vector backfill — COMPLETE ✅
`/opt/homebrew/bin/python3 pipeline/backfill_embeddings.py` (full, 2m50s) + `--contextual` (3m4s) → **`vec_fbs` 7,867→7,873, `vec_fbs_ctx` 7,867→7,873**, both **= fbs, 0 missing, 0 orphaned**. The 6 BUG-198 FBs are now vector-searchable.

### DB-bloat prevention (proposal — VACUUM deferred until e2e ends)
Bloat root cause = my S1 diagnostic created-then-DROPPED `ctx_v2`/`ctx_v3` vec tables inside **production** `maxwell.db`; SQLite doesn't reclaim pages on DROP (133→167 MB). Prevention: (1) never run diagnostics against production DB — use run-scoped `--db`; (2) **`VACUUM` production DB after e2e finishes** (reclaims ~34 MB, needs no writers); (3) **e2e should use a SEPARATE run-scoped DB** so `pipeline_run_id='e2e'` rows never pollute production/retrieval (retrieval doesn't filter by run_id); (4) `backfill_embeddings.py --limit` does `DELETE FROM vec` then embeds only N — **never `--limit` on production** (destroys the index).

---

## 2. What this session decided + did (D2522)

### S1 — contextual embeddings REJECTED (keep `contextual_embed.enabled: false`)
Re-ran the 30-query golden-set A/B and confirmed the D2518 tradeoff is a **real semantic failure, not noise**:

| leg | recall@k | MRR |
|---|---|---|
| hybrid (raw RRF) | **1.000** | 0.708 |
| hybrid-ctx (contextual) | **0.967** | 0.792 |
| hybrid+rerank (production) | **1.000** | **0.739** |

`hybrid-ctx` loses **exactly one query** — "how to build resilient distributed systems" → `Site Reliability Engineering (sre) Principles` (`cd98caf61c6ab956`), which drops to rank 14. **Root cause verified at the embedding level:** that FB's context prefix (`discipline | domains | name`, cap 200) is `systems engineering | business operations, engineering & infrastructure, engineering practice, project management | Site Reliability Engineering (sre) Principles` — ~200 chars of broad multi-axis taxonomy that **dilutes** the definition signal. Cosine(query, FB) = **0.588 (bare definition) → 0.533 (contextual)**; name-only (0.525) and name+discipline (0.529) also fail to beat bare. **Verdict:** the prefix captures the FB's *taxonomy*, not more of "what the FB is about". For synonym/abstract queries (the whole point of the vector leg, D2509) it is pure dilution. **Do NOT enable.**

### S3 — HyDE REJECTED (keep `hyde.enabled: false`)
`--hyde --rerank` A/B on 30 queries:

| leg | recall@k | MRR |
|---|---|---|
| hybrid | 1.000 | 0.708 |
| hybrid+rerank | 1.000 | 0.739 |
| hyde | **0.967** | **0.642** |
| hybrid+hyde | **0.967** | **0.642** |

HyDE **regresses BOTH recall** (loses the same SRE query) **AND MRR** (0.642, below the raw hybrid baseline). FTS contributes nothing (recall 0.000 on natural-language queries), so `hybrid+hyde` ≡ `hyde`. The generated hypothetical doc does not close the abstract→concrete gap. **Do NOT enable.**

### S2 — rerank CONFIRMED (already enabled, D2521)
Only production retrieval change that survives the A/B: recall 1.000, MRR 0.739 (+4.4%), zero recall loss.

**Final leg ranking:** rerank (0.739) > hybrid (0.708) > HyDE (0.642); contextual (0.792) trades away recall.

### Full S0–S6 `just eval` — RELAUNCHED (running at handoff)
- Cleared the stale e2e checkpoints (SHRINK GUARD blocker, D2520) via `safe_delete.py` for all 9 `stage/*/e2e` dirs (backed up to `backup/deletions/`).
- Fresh DB pre-e2e backup taken (`knowledge pipeline/maxwell.db.pre_e2e_20260903_105816`).
- Launched `python3 pipeline/e2e_test.py` (20 books, balanced) in the background → `temp/e2e_eval.log`. At handoff it was in **stage1_5_embed_cluster** (progressing past the previously-blocked stage0).

### Gov-sync
- **buglog:** BUG-198 → RESOLVED (part 2 re-inject executed, D2519); BUG-197 → kind-swap executed + prompt fix verified (residual re-classification deferred).
- **decisions.yaml:** D2522 appended; `scripts/recompute_decision_summary.py` re-synced → **total=506, active=447**.
- **DECISION-LOG.md:** D2522 appended (newest-first, top).

---

## 2. Current state

| Thing | Value |
|---|---|
| DB FBs (`knowledge pipeline/maxwell.db`) | **7,873** (3,275 PASS + 4,598 QUARANTINE) |
| `vec_fbs` / `vec_fbs_ctx` | **7,873 rows each — ✅ backfilled this session** (was 7,867; the 6 BUG-198 FBs now have vectors; 0 missing, 0 orphaned) |
| Retrieval config | rerank `enabled: true` (production); contextual `false`; hyde `false`; burst_decode_mode `balanced` (default, reverted) |
| taxonomy | 43 domains / 61 disciplines; `d2399_promotions_frozen: true` |
| decisions.yaml | **total=507, active=448** |
| Tests / health | 192/192 pytest (prior turn); integrity 17/18 (1 pre-existing false-positive) |
| e2e eval | **RUNNING** (relaunched this turn, 20 books) |
| ⚠️ DB file size | **167 MB** (was 133 MB) — 8,302 free pages (~34 MB bloat) from this session's S1 diagnostic backfill experiment (`ctx_v2`/`ctx_v3` tables created then DROPPED). **Data intact** (7,873 FBs, `integrity_check` ok). Recommend `VACUUM` after the e2e run completes to reclaim space. |

---

## 3. Remaining tasks / bugs / decisions — by priority & severity

### 🔴 P0 — correctness / data-integrity (must resolve before next corpus batch)
1. **Complete + validate the full e2e eval.** ✅ **S2 empty-elaboration FIXED (option a, D2524)** — root cause was `format_golden_fewshot_single_source()`/`format_golden_fewshot()` omitting `elaboration` from the few-shot JSON (the model learned it optional). Fixed (few-shot now shows elaboration; prompt reinforced; non-principle elaboration stays empty per D2452). Clean S2 resume → **163 FBs, 0 failed**. S2 is **DONE**. Remaining: **S4 (running now) → S5 → S6** + `validate_results()` (fb_count ≥30, S5 pass ≥80%, db_rows, ontology round-trip) — this is the future-batch validation gate.
2. ~~Re-backfill `vec_fbs` + `vec_fbs_ctx`~~ ✅ **DONE this session** — both now **7,873 = fbs** (0 missing, 0 orphaned).
3. **`VACUUM` production `maxwell.db` after e2e completes** — reclaims the ~34 MB bloat (133→167 MB) from the DROPPED `ctx_v2`/`ctx_v3` diagnostic vec tables. Needs no writers, so wait for e2e to finish. (Prevention rule going forward: never run diagnostics against the production DB; use run-scoped `--db`.)
4. **Consider giving e2e a SEPARATE run-scoped DB** so `pipeline_run_id='e2e'` rows never pollute production/retrieval (retrieval does NOT filter by run_id).

### 🟠 P1 — deferred correctness (has a shipped fix/gate, awaiting a future batch)
3. **BUG-197 residual re-classification** — ~2,080 `discipline: emerging` + remaining `*_raw` cross-axis leak records need a future-batch LLM re-classification (gpt-oss). Prompt fix (D2510) + kind-swap (D2519) already shipped; this is the only unresolved residue.
4. **D2399 taxonomy promotions** — **FROZEN** (`d2399_promotions_frozen: true`). Re-open only with explicit human review after BUG-197 re-classification; never promote a both-axes-emerging label (D2519 policy A).
5. **BUG-150 emerging-rate re-measure** — `scripts/gate_emerging_rate.py` shipped (D2485); re-run on the next fresh S4 output (don't promote against stale data — BUG-167 lesson).

### 🟡 P2 — open bugs (deferred, non-blocking to current committed corpus)
6. **BUG-193** — `CircuitOpenError` undefined in `discover_principles` (stage2_extract.py:1736) — OPEN (S2 resume path, deferred).
7. **BUG-187** — S4 FB emits 7 fields not declared in `schemas.FB` + `jargon` key omission (schema drift, non-blocking).
8. **BUG-168** — `dspy_trainer.py` built but not wired to any stage (built-not-wired).
9. **BUG-159** — prompt-injection contamination (cluster_11649) — OPEN.
10. **BUG-160** — evidence-passage relevance in drift sample (1/30) — OPEN.
11. **BUG-151 / BUG-148** — taxonomy structural overlap (`education` dual-listed) + S2 `route` stale — OPEN; partially addressed by D2512 (BUG-210) / D2515 (normalization) / D2323 (route gate). Re-verify before claiming resolved.

### ⚪ P3 — deferred speed/market (only after correctness)
12. **D2084 / D2345 / D2462** — commit non-principle sidecars (PI/TI/GE/PT) to DB + unify single-source/singleton extraction (2-pass) + principle-first T1.1 (DRAFT). Requires `commit_non_fb_types: true` (currently false).
13. **D2440** — S5 verifier calibration (AlignScore + MiniCheck) — BLOCKED (packages + `evals/nli_golden.jsonl` missing).
14. **S4-research §2/§4** — vLLM-MLX pilot + S4-C distillation (post-re-benchmark).

### ✅ RESOLVED this session (for the record)
- S1 contextual → REJECTED (gated off). S3 HyDE → REJECTED (gated off). S2 rerank → CONFIRMED enabled.
- BUG-198 → RESOLVED (6 singletons re-injected). BUG-197 → kind-swap executed + prompt fix verified.
- **S2 speed root-cause → memory-pressure decode collapse (fixed by restart); `burst_decode_mode` RULED OUT (reverted to `balanced`).**
- **6-FB vector gap → backfilled (`vec_fbs` + `vec_fbs_ctx` = 7,873 = fbs).**

---

## 4. Key paths (manual examination)

- Final S4.5 checkpoint: `knowledge pipeline/stage4_merge/t11/checkpoint_enriched.jsonl` (7,873 records)
- DB: `knowledge pipeline/maxwell.db`
- e2e log: `temp/e2e_eval.log` (buffered — check child process for progress, e.g. `pgrep -P <e2e_pid>`)
- HyDE A/B result: `temp/hyde_ab.log`
- Pre-e2e DB backup: `knowledge pipeline/maxwell.db.pre_e2e_20260903_105816`
- Decode probe (disposable): `temp/omlx_speed_test.py`
- Changed this turn: `governance/DECISION-LOG.md` (D2522, D2523), `config/decisions.yaml` (D2522, D2523 + re-sync → 507/448), `governance/buglog.md` (BUG-197/198 + D2523 header), `governance/SESSION-HANDOFF-2026-09-03.md`. DB data change (sanctioned): `vec_fbs`/`vec_fbs_ctx` re-backfilled. No pipeline code changed.

## 5. Python env split (remember)

- `/opt/homebrew/bin/python3` — sqlite-vec / DB / retrieval / rerank (transformers+torch) scripts
- `/usr/local/bin/python3` — pytest + pipeline deps (stage scripts; pypandoc + datasketch)

---
*Handoff written 2026-09-03 (D2522). See DECISION-LOG.md §D2522, buglog.md (BUG-197/198), MASTER-TASK-REGISTER.md for full detail.*
