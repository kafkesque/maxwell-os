# Session Handoff — 2026-08-17-FINAL (R3 canary rerun complete → T1.1 READY)

> **Phase:** Phase 1 (v3.0 architecture validation) — **T1.1 GO / READY FOR LAUNCH** (operator go/no-go required)
> **Branch:** `main` | prior commits today: `793fd26` → `fcca197` → `47e0f99` → `4b55797` → `0bf8877` → `7aa6ea9` → `32a0f09` → **this governance sync commit**
> **Supersedes:** `SESSION-HANDOFF-2026-08-17.md` (morning half: D2396–D2400). This file covers the evening half: D2406–D2408 + R3 canary S4→S6 rerun + governance sync.

---

## 1. What was done this session (evening continuation)

| Item | State |
|---|---|
| D2406 — `agent/session_seed.yaml` YAML parse break (boot/integrity blocker) | ✅ FIXED (2 scalars quoted; 12/12 YAML parse) |
| D2407 — dead-code purge (`run_production.py` → `archive/`) + 9 fail-closed regression tests (`tests/test_fail_closed_d2402_2405.py`) | ✅ DONE (34-test suite green) |
| D2408 — `response_format={"type":"json_object"}` → EMPTY gpt-oss-20b content (xgrammar/Harmony conflict, same family as D2392) | ✅ FIXED (`pipeline/omlx_call.py:381` — skip for `VERIFY_REASONING_OFF_MODELS`, config-first) |
| **R3 canary S4→S6 rerun** (`tools/canary_rerun_s4onward.sh`, `MAXWELL_RUN_ID=canary`) | ✅ **COMPLETE 2026-08-17 19:22:39 (~87 min)** — see §2 |
| Governance sync (this file + DECISION-LOG D2402–D2408 + decisions.yaml 397 + MTR + aggregated + buglog + session_seed) | ✅ DONE + committed/pushed |
| Post-canary validation: golden hash re-check, DB row audit, 34 tests, integrity 17/17, health 10/10, config audit strict | ✅ ALL GREEN |

## 2. R3 canary S4→S6 rerun — results

| Stage | Duration | Result |
|---|---|---|
| S4 merge/classify | 17:55:35 → 19:20:20 (~85 min) | **279/279 FBs**, 0 failed clusters, 0 quarantines, **52,911 relationship edges**, 0 isolated |
| S5 verify | 19:20:20 → 19:21:38 (~78 s) | **236 PASS / 43 QUARANTINE / 0 FLAG** |
| S6 commit | 19:21:38 → 19:22:39 (~61 s) | **279 rows → SQLite (`pipeline_run_id=canary`)**, FTS 279, Parquet `fbs_snapshot_20260817_192235.parquet` (4482.4 KB), 0 taxonomy replacements |

- **Regression check:** 236/43 ≈ prior canary 235/43 → D2402–D2405 + D2408 produced **no behavioral drift**.
- **Resume/fail-closed paths NOT exercised in-vivo** (0 failures — good for output, but the kill/restart resume path remains unit-tested only; optional failure-injection pass before T1.1).
- **Environment:** `caffeinate -disu` active throughout; OMLX lazy-loaded (only Phi-4-mini + gpt-oss-20b resident; ~69% mem free at end); `com.maxwell.omlx` launchd crash loop (double-bind port 11435 vs oMLX.app server) unloaded — CPU churn gone.
- **Known degraded (non-blocking, BUG-104):** `vec_fbs` absent (python.org Python 3.12 lacks `enable_load_extension`) → vector search DEGRADED, FTS fallback works. Action: Homebrew Python.

## 3. Canary fixes → valid for the pipeline? — VERIFIED ✅

The R3 canary ran the **exact same stage modules** the production runner executes (`pipeline/stage4_merge.py`, `stage5_verify.py`, `stage6_commit.py` — confirmed in `tools/canary_rerun_s4onward.sh`; runner `STAGE_ORDER = ["0","0.5","1","1.3","1.5","2","4","5","6","6b","6c"]` maps to the same scripts). Every fix is in the production path:

| Fix | Where (file:line) | Production-path proof |
|---|---|---|
| D2402 S4 timeout `'4': 3600 → null` | `config/pipeline_config.yaml:33` | config read by runner per-stage timeout |
| D2403 S2 3-state FB/NULL/FAILED | `pipeline/stage2_extract.py:1540,1674-1715` | `_failed` → `cluster_failed` → NOT in `processed_ids` |
| D2404 S4 FAILED not processed | `pipeline/stage4_merge.py:1215+` | FAILED clusters excluded from `processed_ids` (retry on resume) |
| D2405 S4 no fabricated `evidence="cited"` + S5 FAILED→QUARANTINE | `stage4_merge.py` sentinels; `stage5_verify.py:428` (`method="classification_failed"`) | live S5 0 QUARANTINE-by-classification in R3 |
| D2406 session_seed YAML | `agent/session_seed.yaml` | integrity [1] 12/12 YAML parse PASS |
| D2407 dead code + tests | `archive/run_production.py.archived-2026-08-17`; `tests/test_fail_closed_d2402_2405.py` | 34/34 pytest PASS |
| D2408 response_format skip | `pipeline/omlx_call.py:381` (guarded by `VERIFY_REASONING_OFF_MODELS`, defined config-first `pipeline/pipeline_paths.py:105` ← `models.verifier.reasoning_off_models`) | R3 S4 ran 279/279 with gpt-oss-20b full responses — **validated live** |

**Conclusion:** No fix is canary-only. All are in the shared modules/config the T1.1 run will use. No re-work of the fixes needed.

## 4. T1.1 launch — do we start from S0? → **YES, fresh full run S0→S6. Here's why**

**Short answer:** Launch T1.1 as a **fresh full run from S0** (`python3 pipeline/runner.py --run-id t11`) after archiving/resetting the DB (D2396). It is **not** "start from scratch because the code changed" — it's required because **T1.1 is a different run than the canary**, and one reusable artifact is stale.

**Detailed reasoning:**

1. **The canary covered only a corpus SUBSET.** R3 re-ran S4→S6 on the canary's ~279-FB cluster set. T1.1 is the FULL corpus: 12,964 clusters (`knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl` — 12,964 lines). S2 has never run on the full corpus with the D2403 fail-closed code → S2 must run fresh regardless (that's the ~25–40h long pole).
2. **D2396 fresh-DB policy.** Current `maxwell.db` holds exactly 279 rows, all `pipeline_run_id=canary` (R3 rerun). T1.1 must start from an empty DB — archive/reset at launch (G10 run-specific DB is post-T1.1, P2).
3. **New run-id ⇒ runner recomputes everything anyway.** `runner.py --run-id t11` (D2339 pre-parse; per-run resume markers D2329/D2370) has no COMPLETE checkpoints for `t11` → all stages run fresh. No cross-run contamination.
4. **The one artifact you might have reused is stale:** the full-corpus S1.5 `latest` checkpoint is dated **2026-08-12 17:02** — it was computed with **pre-D2348 embedding settings** (BUG-105: 60s timeout + keep_alive default caused read timeouts / ~3% embed drops under 4-worker load). D2348 (timeout 180s + keep_alive=-1) landed **mid-canary on 2026-08-14**. Re-running S1.5 with current settings removes all doubt about embedding stability in the 12,964-cluster set.
5. **S0–S1.3 are deterministic + cheap** (Pandoc convert → chunk → regex prefilter) and untouched by any canary fix — re-running them is harmless insurance, not waste. Relative to the ~39h S2/S4 runtime (D2365/D2366), the S0→S1.5 wall time is minor.

**What "not from scratch" means:** you do NOT need to re-do the canary fixes, re-audit the frontier reports, re-validate the golden set (hash PASS re-verified), or re-verify governance — those all carry forward. The code is launch-ready; the run itself starts clean from S0.

### T1.1 launch checklist (operator go/no-go — multi-day ~39h run)

```bash
# 0. Preconditions
pgrep -f 'caffeinate -disu' || caffeinate -disu &        # keep machine awake
python3 tools/verify_golden_hash.py                       # expect PASS (verified this session)
just integrity                                            # 17/17 (verified this session)
python3 pipeline/config_audit.py --check-unchecked --strict

# 1. Fresh DB per D2396 (archive the 279-row canary DB, then start empty)
#    (D2396 precedent: archived to maxwell.db.pre_t11_20260816.bak — do the same for the canary DB)

# 2. Launch full run from S0
python3 pipeline/runner.py --run-id t11                   # S0→S6 (+6b/6c push/export stages)

# 3. Monitor
tail -f "knowledge pipeline/runner_$(date +%Y%m%d).log"   # or the runner's log path
python3 pipeline/status.py                                # per-stage progress
# Watch: S4 FAILED gate (D2338), S5 classification_failed→QUARANTINE (D2405), S6 INSERTED counts
# Resume after crash: python3 pipeline/runner.py --run-id t11 --resume-from stage2 (or any stage)
```

## 5. Remaining / next-session priorities (unchanged, non-blocking)

1. **T1.1 full launch** — the only thing left is the operator go/no-go.
2. **G3 domain promotion** (post-T1.1 **+ D2345**, D2399) — full-corpus `taxonomy_counts`, NOT canary. Also investigate the `legal & public policy` double-count/normalization flag.
3. **D2345** — single-source non-type second pass (`stage2_extract_nontype.py`, reuse S1.5 clusters).
4. **BUG-104 (action)** — Homebrew Python (`brew install python@3.12`) to enable sqlite-vec/`vec_fbs`; FTS fallback works meanwhile.
5. **G10 (P2)** — run-specific DB scoping by run_id + active-KB pointer.
6. **Failure-injection pass (optional, pre-T1.1)** — kill/restart on a real cluster to exercise D2370/D2403/D2404 resume in-vivo (canary had 0 failures; unit tests cover the decision logic only).
7. **B15 (P2)** — schema corrections (three-axis status, typed edges, TI class, feedback config-first).
8. Post-T1.1 hardening log: MPS renormalization, K-means degraded-marker, probe-cache fingerprint, canonical source_id sampling, verbatim evidence verification, S4.5 runner registration, NLI calibration-data commit.

## 6. Key facts for the next session

- **Head:** `32a0f09` + this governance commit (push to `origin/main`).
- **Models (OMLX :11435):** Qwen3-Coder-30B (S2 gen) | gpt-oss-20b (S4 classifier) | DeBERTa-v3-large (S5 NLI, in-process) | bge-m3 (Ollama, 512-dim Matryoshka) | Phi-4-mini (pinned probe).
- **Config-first (C12):** thresholds/models/timeouts in `config/pipeline_config.yaml`; `VERIFY_REASONING_OFF_MODELS` from `models.verifier.reasoning_off_models` (pipeline_paths.py:105).
- **OMLX 0.6.0 traps:** never use `response_format=json_object` with gpt-oss-20b (D2408); grammar/xgrammar OFF (D2392); CoT levers = `chat_template_kwargs.enable_thinking=false` + `thinking_budget`.
- **Canary tooling:** `tools/canary_rerun_s4onward.sh` (S4→S6, fail-stop wrapper, log `knowledge pipeline/canary_rerun_<TS>.log`); `tools/canary_rerun_s2onward.sh` (S2→S6 pattern).
- **DB:** `knowledge pipeline/maxwell.db` = 279 rows `pipeline_run_id=canary` (archive before T1.1).

## Resume seed
- This file · `governance/aggregated_remaining_tasks.md` (R3 → ✅ DONE) · `MASTER-TASK-REGISTER.md` (D2408/R3 notes) · `agent/session_seed.yaml` (status/completed updated) · `governance/buglog.md` (🟢 R3 entry + BUG-142) · `DECISION-LOG.md` (D2402–D2408) · `config/decisions.yaml` (397).
