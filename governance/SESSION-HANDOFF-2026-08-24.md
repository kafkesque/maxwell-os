# Session Handoff — 2026-08-24 (Stack cleanup + forensic audit complete → S2 singleton run READY)

> **Phase:** Phase 1 (v3.0 architecture validation) — **NEXT ACTION: launch `just s2-singletons`** (operator go/no-go required after 100% verification)
> **Branch:** `main` | last commit: `3a4b0e9` (S2 singleton readiness + crash-safety, D2451-D2453)
> **Working tree:** UNCOMMITTED (D2455 + D2456 governance sync pending commit — see §5)
> **Supersedes:** SESSION-HANDOFF-2026-08-23.md
> **Current time:** 2026-08-24 23:43

---

## 0. TL;DR — where we are

Two sequential goals completed this session:
1. **D2455** — killed the OMLX "two-version clusterfuck" (homebrew 0.5.1 vs app 0.6.2).
2. **D2456** — forensic audit found **Ollama had the IDENTICAL clusterfuck** (homebrew 0.30.0 vs app 0.32.15), fixed it, and generalized the guard to ALL stacks + added one-panel version monitoring.

**Both inference stacks are now single-source, healthy, and version-pinned. Pipeline verified unbroken (126/126 tests). The next move is the S2 singleton extraction run that was being prepared before this detour.**

---

## 1. What was done this session

### D2455 — OMLX single-source-of-truth
| Item | State |
|---|---|
| Root cause: homebrew `omlx` 0.5.1 + app 0.6.2 both claimed port 11435 + rewrote settings.json | ✅ diagnosed |
| `brew uninstall omlx` (0.5.1, 1.6GB) + orphaned `python@3.11` dep | ✅ removed |
| 6 stale launchd plists (`com.maxwell.omlx` ×4, `homebrew.mxcl.omlx` ×2) | ✅ archived → `~/.omlx/archive-single-source-20260824-230352/` |
| `scripts/guard_omlx_single_source.py` (fail-loud, config-first) wired into `just health` + `just preflight` | ✅ created |
| Quality verdict: `max_concurrent_requests` batching byte-identical to solo (temp=0.0 greedy) | ✅ empirical |

### D2456 — Forensic audit + Ollama clusterfuck + stack generalization
| Item | State |
|---|---|
| **Ollama had the SAME clusterfuck**: homebrew `ollama` 0.30.0 (`homebrew.mxcl.ollama` crash-looping `bind: address already in use`) vs app `Ollama.app` 0.32.15 serving 11434 | ✅ found + fixed |
| `brew unpin ollama` + `brew uninstall ollama` (0.30.0) | ✅ removed |
| Orphaned brew `mlx`/`mlx-c` (were ollama deps) | ✅ autoremoved (verified: pipeline uses pip `mlx`, untouched) |
| Stale `homebrew.mxcl.ollama.plist` | ✅ archived → `~/.omlx/archive-ollama-20260824-232229/` |
| **Blindspot 1**: `status.py` reported "UP" but never checked VERSIONS (drift silent) | ✅ fixed — now prints `Versions: OMLX 0.6.2 | Ollama 0.32.15` |
| **Blindspot 2**: `get_omlx_version()` existed but unwired; no `get_ollama_version()` | ✅ `get_ollama_version()` added, both wired |
| **Blindspot 3**: guard was OMLX-only | ✅ generalized → `scripts/guard_stacks_single_source.py` (iterates ALL services with `single_source_guard`) |
| **False-positive fix**: app 0.6.2 writes its OWN CLI shim `/opt/homebrew/bin/omlx` → `~/.omlx/bin/omlx` → `omlx-cli`. Guard now distinguishes `forbidden_bins` (unambiguous Cellar/opt) from `shim_paths` (flag only if resolving into Cellar/opt) | ✅ A/B tested 3 ways |
| **ONE panel**: `scripts/monitor_stacks.py` (`just stacks`) — status + version + min_version drift + single-source guard | ✅ created, wired into `just preflight` |
| `min_version` pins: omlx 0.4.0, ollama 0.32.0 (new) | ✅ added to config |

### Forensic audit — other findings (non-breaking, documented)
- **`pip check` conflicts are ALL third-party noise** (gpt-researcher / marker-pdf / surya-ocr / prawcore / opentelemetry — 0 pipeline refs). Only `dspy` touches pipeline, and `dspy_trainer.py` is already unwired (BUG-168).
- **node 26 vs 24 drift** — node is NOT a pipeline dep (false grep hits on "graph nodes").
- **Orphaned brew `python@3.11` (2 versions) + `python@3.14` (4 versions)** — bloat, non-blocking.
- **Leftover zombie `oMLX --help` (PID 44261) + bash 44258** from earlier diagnostic — killed.
- **OMLX did a GRACEFUL shutdown at 23:23:11 mid-audit** (clean "Engine pool shutdown", RAM 91% free, NOT a crash; `crash.log` entries are stale Aug 6-7 from removed homebrew builds). Recovered via `open -a oMLX` — **no data loss, settings preserved** (`max_concurrent_requests=6`). Worth watching; not actionable yet.

---

## 2. Current system state (verified 23:43)

```
One-panel monitor (just stacks):
  ollama     ✅  v0.32.15  (min 0.32.0)  ✅
  omlx       ✅  v0.6.2   (min 0.4.0)   ✅
  Single-source guard: ✅ PASS

Integrity:     10/10
Tests:         126 passed (121 + 5 new guard tests)
Config audit:  clean (strict)
Decision sync: in-sync (443 decisions)
OMLX settings: max_concurrent_requests=6, chunked_prefill=False
OMLX health:   healthy, loaded_count=2
```

**Single source of truth:** OMLX = `oMLX.app` 0.6.2 (PID app-managed), Ollama = `Ollama.app` 0.32.15. **No homebrew `omlx`/`ollama`/`mlx`/`mlx-c` remain** (all app-managed).

---

## 3. Next action — S2 singleton extraction (`just s2-singletons`)

This is the run that was being prepared before the stack-cleanup detour. **READY TO LAUNCH** once the operator confirms 100% verification.

### Pre-run facts (verified)
- `singletons.prefiltered.jsonl` exists: **35,122 singletons → 6,317 EXTRACT / 28,805 SKIP** (deterministic pre-LLM gate, D2437/D2452).
- Prior attempt stopped cleanly: `singleton_run.log` shows it loaded 6,317 viable, started "3 workers in batches of 4" — but **no checkpoint files created** (`singleton_fbs.jsonl` / `singleton.segids` absent), so it resumes from batch 0. PID 41569 is DEAD.
- `singleton_run.pid` = 41569 (stale, harmless).
- Runtime estimate at 0.303 batch/s: **~1.45h** (post-`max_concurrent_requests=6`).

### Resume commands
```bash
# Preflight (now includes stack monitor + single-source guard)
just preflight

# Run (checkpoint/resume built in — D2453: writes every 25 batches, crash-safe)
just s2-singletons

# Tail progress
just s2-singletons-status   # (if target exists) OR:
tail -f "knowledge pipeline/stage2_extract/t11/singleton_run.log"
```

### Standing user gates (from earlier sessions — STILL ACTIVE)
1. "dont start anything till you hundred 100% verified everything"
2. No extraction-quality/accuracy sacrifice (temp=0.0, golden intact).
3. Must be checkpointable/pauseable/resumable (D2453 ✅ done).
4. Monitor closely until 100% verified no crash/hidden failure/leak/contamination/memory-throttle/drift.

---

## 4. Remaining tasks (most-critical-first)

### 🔴 CRITICAL PATH — S4 → S5 → S6 rerun (after singletons)
1. **S2 singleton extraction FIRST** (`just s2-singletons`) — 6,317 EXTRACT singletons, so S4 runs ONCE on the complete frontier (convergent + single-source + singletons).
2. **D2454 — wire S4 classification golden** (`config/golden/stage4_golden.yaml` AUTHORED + test-validated but NOT injected into the 4 S4 prompts). Needs live smoke before BUG-165 (touches S4 hot path).
3. **BUG-165 — S4→S5→S6 rerun ONCE** on finalized S2 (8,410, or the 4,892 keep-list). S6 EMPTY; S4/S5 stale at 2,830. **THE product build.**
4. **D2440 — S5 verifier calibration** (AlignScore + MiniCheck vs DeBERTa) BEFORE the S5 leg; gate F1 > 0.484 + fail-closed (D2093).

### 🟠 P1/P2 — correctness & hardening
5. **BUG-150** — re-measure discipline `emerging` on FRESH S4 (was stale 2,830); promote only after. ⚠️ premature promotion REVERTED (broke D2422 disjointness).
6. **P1.3** — gpt-oss cross-family FLAG in `stage2_relabel_extraction_type.py` (0 refs today).
7. **BUG-148** — `route="FB"` vestigial; derive-from-content_type or remove.
8. **BUG-168** — `dspy_trainer.py` wire-or-archive (exists-but-unwired).
9. **Task #20** — `check_stage_order()` doesn't verify sequence (ext-audit #5).
10. **Task #21** — `model_lazyload.py --status` reads `/v1/models` catalog not `loaded_count` (ext-audit #14).

### 🟡 P2 / post-rerun
11. **Non-principle commit (Path A, D2448)** — S6 non-principle tables (TI/PT/PI/GE) + wire `commit_non_fb_types` (dead) + non-principle cross-ref producer + non-principle S5 verification + BUG-170 enrichment.
12. **BUG-169** — TI `parameters` missing (verify full 143-TI corpus during BUG-165).
13. **BUG-170** — non-principle classification (latent until `commit_non_fb_types`).
14. **D2439 accept-defer** — Leiden swap / contextual retrieval / cross-encoder reranker / DuckDB (P2).
15. **BUG-149** — dead `max_words=5` default in `normalize_fb_name`.
16. **BUG-151** — taxonomy 269 raw-alias overlaps (CI test now EXISTS + GREEN).
17. **DECISION-LOG backfill** — D2423–D2438 (15+ decisions).
18. **D2445 verdict** — core-body type-specificity refactor (post-BUG-165, golden-gated).

> Full list with statuses: `governance/aggregated_remaining_tasks.md` (items 1-21).

---

## 5. Uncommitted working tree (needs commit)

```
 M DECISION-LOG.md                              (D2455 + D2456 entries)
 M agent/session_seed.yaml                      (D2455/D2456 headers)
 M config/decisions.yaml                        (D2455 + D2456; total 443, active 385)
 M config/pipeline_config.yaml                  (ollama+omlx single_source_guard blocks, min_version pins)
 M governance/aggregated_remaining_tasks.md     (stack single-source section)
 M governance/buglog.md                         (D2455 + D2456 headers)
 M justfile                                     (just stacks, monitor in preflight/health)
 M pipeline/status.py                           (get_ollama_version, version display)
 M tools/ab_test_grammar.py                     (stale brew comment fixed)
?? scripts/guard_stacks_single_source.py        (renamed from guard_omlx_single_source.py)
?? scripts/monitor_stacks.py                    (one-panel monitor)
?? tests/test_stack_guard_d2456.py              (5 tests)
```

**Recommended commit message:**
```
OPS: OMLX+Ollama single-source + one-panel stack monitor (D2455-D2456)

- Uninstall stale homebrew omlx 0.5.1 + ollama 0.30.0 (app = single source of truth)
- Archive 7 stale launchd plists; autoremove orphaned brew mlx/mlx-c
- guard_stacks_single_source.py: generalize guard to all stacks, fix app-shim false positive
- monitor_stacks.py: one-panel status+version+drift monitor (just stacks, in preflight)
- status.py: report OMLX/Ollama versions (drift was silent)
- 126/126 tests, 10/10 integrity, config audit clean
```

---

## 6. Key revelations / decisions to carry forward

1. **"Sync both versions up to date" is the WRONG goal.** Two installs of the same server — even identical versions — still fight over the port and race on config. The correct invariant is **exactly ONE canonical install per stack**. This is now enforced by the guard.

2. **App-managed tools must NEVER be mixed with homebrew.** The app (oMLX/Ollama) writes its own CLI shims (`/opt/homebrew/bin/omlx` → `~/.omlx/bin/omlx`). Homebrew formulas fighting the app for the same port/settings was the root cause of BOTH clusterfucks. **Update strategy: monitor from ONE panel (`just stacks`), but update each stack through its OWN native updater.**

3. **Version drift was invisible because nothing checked versions.** `status.py` only reported UP/DOWN. Now `min_version` pins + the monitor catch drift loudly. The `max_concurrent_requests` A/B tuning (3→6) was byte-identical on quality (temp=0.0 greedy) — a pure scheduling win, no accuracy cost.

4. **The guard's first version false-positived on the app's own shim.** Lesson: a bare "path exists → fail" check is too blunt for app-managed installs that legitimately write shims into `/opt/homebrew/bin`. Resolve the symlink and check the *target* (Cellar/opt = homebrew, anything else = app).

5. **DSPy/`pip check` noise is not drift.** `pip check` flags are from third-party research tools (gpt-researcher, marker-pdf, etc.) with zero pipeline references. Don't let them distract from real drift.

---

## 7. How to resume from a fresh session

1. `just preflight` — verifies stack single-source + versions + integrity + golden hash + config audit (fails loud on any regression).
2. `just stacks` — one-panel view of OMLX + Ollama versions/drift.
3. **Launch `just s2-singletons`** (after the operator's 100%-verification go-ahead).
4. Monitor `tail -f "knowledge pipeline/stage2_extract/t11/singleton_run.log"`.
5. After singletons: D2454 (wire S4 golden) → BUG-165 (S4→S5→S6) → D2440 (S5 calibration) → commit.
