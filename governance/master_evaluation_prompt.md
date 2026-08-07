# Maxwell OS v3.0 — Independent Evaluation Prompt
## For an S-Tier Senior RAG & Software Engineer LLM

**Generated:** 2026-08-07 22:18 UTC
**Git commit:** HEAD at time of writing
**Purpose:** A fresh, independent audit of the entire Maxwell OS v3.0 pipeline after
12 hours of cascading production failures. Your job is to find what the original
engineers missed — blindspots, gaps, conflicts, hidden failures, contamination,
memory leaks, bottlenecks, bloat, risks, mismatches, inconsistencies.

---

## I. WHAT MAXWELL OS IS

Maxwell OS is a sovereign (local-first, zero-vendor-lock-in) knowledge extraction
pipeline that converts EPUB/PDF books into structured Foundation Blocks (FBs) —
verified, convergent, executable knowledge units. It runs entirely on local hardware
(Apple Silicon, 68.7GB RAM). The current run is extracting from a corpus of ~12,964
clusters from hundreds of books (Psychology, Economics, Design, etc).

**Pipeline (8 active stages):**
```
S0   → EPUB/PDF → Markdown
S0.5 → Extract metadata (author/title)
S1   → Chunk text
S1.3 → Regex pre-filter (drop citations, boilerplate, short segments)
S1.5 → Embed (bge-m3) + FAISS clustering → 12,964 clusters + 35,239 singletons
S2   → Convergent extraction (Qwen3.6-35B-4bit) + Phi-4-mini probe
S4   → Classify + CRIBS enrichment
S5   → NLI (DeBERTa) + cross-family Gemma verification (BORP)
S6   → Commit to SQLite (sqlite-vec) + Parquet
```

S3 (HDBSCAN) was removed per D2120 — cluster-before-extract architecture.

**Key principles:** $0 marginal cost (local GPU), sovereign data, BORP (Book of
Record Principle — ≥2 independent sources for convergence), temp=0.0, config-first
(C12 — no hardcoded values), crash-safe writes, different model families for
generator vs verifier (R5).

---

## II. THE FAILURE: 12 hours, 5 runs, 0 usable results

The S2 stage has been attempted 5 times tonight (2026-08-07, 17:45–now). All five
failed or produced garbage output.

**Run 1 (17:45, PID 13137):** Probe completed successfully (2h39m, 611 Phi-4 calls,
565 splits, +1,209 expected FBs). At probe→extraction handoff, crashed with
`NameError: name 'S2_MAX_WORKERS' is not defined` at line 1167. Root cause:
`S2_MAX_WORKERS` was added to `pipeline/pipeline_paths.py` (line 131) and used at
`stage2_extract.py` line 1167, but NEVER added to the import list (commit 107b1c3).
Probe results were in-memory only — 2h39m lost. [BUG-059]

**Run 2 (21:09, PID 41646):** Launched after fixing the import. Stalled for 4+
minutes at startup with 0% CPU, 247-byte log. Killed as stalled. Root cause
suspected: Dropbox FileProvider mount I/O (731.9MB segment store on synced
directory; U-state uninterruptible I/O known issue).

**Run 3 (21:14, PID 42080):** Skiped the probe entirely — found a probe cache
written to the real path by the verification preflight that forgot to monkeypatch
`STAGE2_PROBE_CACHE`. Extracted 10 clusters before being killed. Contamination. [BUG-061]

**Run 4 (21:23, PID 42206):** Parallel probe code applied. Killed at 21:16 (see
run 5 for rationale). 0 usable output.

**Run 5 (21:23, PID 42647):** Parallel probe + unbuffered logging. Probe FAILED
SILENTLY — all 611 qualifying clusters hit OMLX prefill guard rejections (400),
the `_probe_split` except caught all failures silently → probe "completed" in 7
minutes with 0 splits. Extraction began on 2,634 unsplit clusters. At cluster #57,
the circuit breaker opened at threshold 5 (NOT the intended 25!) → 2,577 remaining
clusters fast-failed. OMLX performed an autonomous deep reset at 21:38, unloading
Qwen3.6 mid-extraction (RSS 52.5GB → 4.1GB). Run "completed" cleanly with 9 FBs
and 0 splits — garbage output. [3856 error lines in log]

---

## III. KNOWN ISSUES (starting points for your audit)

### Code-level bugs found and fixed (but verify the fixes):
1. **BUG-059:** S2_MAX_WORKERS missing import → NameError (FIXED: import added)
2. **BUG-060:** --only-convergent silently defeated by probe block's unconditional
   `expanded_targets.extend(single_source)` — would have processed 14,173 targets
   instead of ~3,200 (FIXED: guarded with `if not only_convergent:`)
3. **BUG-061:** Verification preflight polluted real probe cache (FIXED: both
   checkpoints now monkeypatched; real cache purged)
4. **Circuit breaker threshold:** Intended to be max(CFG, 25) but run log proves
   it's still at 5 → opens after 5 failures in a 3-worker pool = ~2-3 seconds

### Systemic issues (open):
5. **OMLX BUG-017:** Wired memory leak — RSS inflated from ~27GB to 52.5GB over
   ~15 min of extraction. Mitigated (restart OMLX between runs) but never root-caused.
6. **OMLX autonomous deep reset:** At 21:38, OMLX independently unloaded Qwen3.6
   mid-extraction. Pipeline has zero awareness or coordination.
7. **Silent probe failure:** `_probe_split` except catches all, prints warning,
   returns [] — the entire probe can fail with zero visible signal. C16 violation.
8. **Pre-launch gate is mocked-to-/tmp only:** No live OMLX health check before
   launching a 9-hour run.
9. **Probe cache writes only at probe END:** If the probe runs 2.5h and crashes
   at 2.4h → 0 progress persisted. No per-cluster checkpoint.
10. **Watchdog phase detection:** Uses cp_lines>0 → "EXTRACTION" but can't
    distinguish "probe skipped" from "probe completed."
11. **Dropbox mount fragility:** 731.9MB segment store on CloudStorage mount;
    intermittent U-state stalls from FileProvider processes even after app quit.
12. **Config dead weight:** `S2_BATCH_SIZE` defined in pipeline_paths.py but never
    used in stage2_extract.py — batch mode was deferred (T9) and never ported.
13. **Probe % metric broken** by parallel probe (out-of-order completion).

### Cross-file mismatches known:
14. `pipeline/pipeline_paths.py` defines S2_MAX_WORKERS (line 131) — must be
    imported by stage2_extract.py. VERIFY the import is present.
15. `pipeline/pipeline_paths.py` defines SPLIT probe constants (S2_SPLIT_PROBE_*)
    — are the same names used in stage2_extract.py? Check for silent NameErrors.
16. `config/pipeline_config.yaml` stage2.batch_size=10 — dead config, never read.
17. `config/decisions.yaml` lists 229 decisions vs DECISION-LOG.md 161 — known
    sync gap.
18. `governance/buglog.md` footer says "Open: 2" after BUG-059/060 — verify all
    open bugs are accurate.

---

## IV. YOUR TASK: SYSTEMATIC AUDIT

You are an S-tier senior RAG and software engineer. Conduct a thorough independent
audit of Maxwell OS v3.0. Do NOT trust any of the above — verify everything.

### Phase 1 — Structural audit (read-only)
1. Read `CONSTITUTION.md` — the single source of truth.
2. Read `DECISION-LOG.md` — trace all architectural decisions D2000+.
3. Read `governance/buglog.md` — current bug register.
4. Read `config/pipeline_config.yaml` — full configuration.
5. Read `config/decisions.yaml` — decision registry.
6. Read `agent/session_seed.yaml` — session configuration.

### Phase 2 — Code audit (read-only)
For EACH of these files, examine:
- `pipeline/stage2_extract.py` (the extraction core — most changed tonight)
- `pipeline/omlx_call.py` (circuit breaker, retry logic, memory guard handling)
- `pipeline/pipeline_paths.py` (all config-driven constants — C12 violations?)
- `pipeline/memory_guard.py` (memory reporting — known false alarm history)
- `pipeline/stage1_5_embed_cluster.py` (singleton generation, cluster structure)
- `pipeline/stage1_3_prefilter.py` (regex pre-filter — D2080)
- `pipeline/n2_watchdog.py` (monitoring — hardcoded PID history, argv fix)
- `pipeline/io_guard.py` (safe_write — crash-safety)

For each file identify:
- Hardcoded values that should be in config (C12 violations)
- Silent error handlers that should raise (C16 violations)
- Missing type hints (C17) or docstrings (C18)
- Dead code or dead config paths
- Race conditions or thread safety issues (especially in parallel probe code)
- Import mismatches (X defined in pipeline_paths but not imported in consumer)
- Any exception handler that could swallow a critical failure silently

### Phase 3 — Configuration audit
- Cross-reference every `config/pipeline_config.yaml` key against pipeline_paths.py
  imports and actual usage in stage files. Flag dead keys.
- Check OMLX configuration: `~/Library/LaunchAgents/com.maxwell.omlx.plist`,
  `~/.omlx/settings.json` — verify `--memory-guard-gb`, `--max-concurrent-requests`.
- Check template files in `pipeline/` for plist correctness.

### Phase 4 — Root cause analysis
For the 12-hour failure cascade specifically:
- Why did the OMLX prefill guard reject prompts at the start of Run 5?
- Why did the circuit breaker open at 5 failures instead of 25?
- Why did the probe fail silently instead of aborting?
- Why did OMLX autonomously unload Qwen3.6 mid-extraction?
- What defense-in-depth measures would have caught each failure earlier?
- Are there additional root causes NOT listed in Section III?

### Phase 5 — Remediation plan
- List fixes ordered by impact (what prevents the next 9-hour waste)
- Classify each as: one-line patch, small refactor (<50 lines), architectural change
- Identify which fixes can be done safely without a full pipeline restart
- Identify gaps that NEED re-engineering (not patchable)

---

## V. REQUIRED OUTPUT FORMAT

For each finding, use this template:
```
### FINDING-XXX: [short title]
- **Category:** BUG | GAP | BLINDSPOT | CONFLICT | HIDDEN_FAILURE |
  CONTAMINATION | MEMORY_LEAK | BOTTLENECK | BLOAT | RISK | MISMATCH | INCONSISTENCY
- **Location:** [file:line]
- **Evidence:** [what you observed in code/config/logs]
- **Impact:** [what breaks, when]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **Fix:** [specific code/config change]
```

Then a summary ranked by severity.

---

## VI. KEY COMMIT HASH

`HEAD` at time of writing. The most relevant commit is `107b1c3` ("D2208/D2209:
N1 yield diagnostic pass + P0/P1/P2 fix pass") which introduced S2_MAX_WORKERS in
pipeline_paths.py but forgot the import in stage2_extract.py.

