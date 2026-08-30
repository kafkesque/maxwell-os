# LLM Roundtable — BUG-188 Post-Mortem Forensic Audit (2026-08-30)

> **Purpose:** Exhaust remaining silent-failure / blind-spot / gap / conflict / mismatch
> risks in the S4→S5→S6 write/read boundary BEFORE committing ~35–52h of compute to the
> S4 re-run. This is a multi-role cross-examination. Append-only. Newest first.

---

## 0. The situation (what we are auditing)

- **BUG-188:** `stage4_merge.py` built ONE giant `"\n".join(json.dumps(f) for f in fbs)` string,
  and `safe_write` ignored `os.write`'s return value. macOS `write(2)` caps a single call at
  **2³¹−1 bytes**, so the S4 checkpoint was silently truncated at 2,147,483,647 bytes and ended
  mid-record. **~5,322 of 7,874 FBs lost (~68%)**, yet the process printed `CONDITIONAL_SUCCESS`.
- **Why prior audits missed it:** the audits verified *per-record content correctness* (fields,
  stamps, classification) at small scale (45/279/2,545 FBs). They never verified the *file
  boundary at full scale* — "does the final checkpoint contain all N complete JSON lines and
  end cleanly?" The failure was (a) silent (no exception), (b) scale-dependent (quadratic
  `related_fbs` only explodes at full corpus), (c) at the I/O boundary (invisible to record audits).
- **Fix applied (D2487):** `safe_write` fail-loud (partial-write loop + size assertion);
  new `safe_write_jsonl` (stream + byte/record-count verify); `compute_fb_relationships` bounded
  to O(n·k) (per-FB top-k cap + `emerging` excluded from `domain_overlap`). Full-scale dry-run:
  7,874 FBs → **34.7 MB (62× under 2GB)**, exact round-trip.

---

## 1. Roles

| Role | Stance | Focus |
|------|--------|-------|
| **Adversarial Reviewer** | Assume the fix is wrong | Find a way to still truncate/corrupt a checkpoint |
| **Storage/Durability Expert** | OS-level | fsync, atomic rename, partial-write, page-cache, 2³¹−1 caps |
| **Pipeline Architect** | End-to-end | Every write→read boundary across S0…S6 |
| **S5/S6 Consumer** | Downstream | What happens if a checkpoint IS truncated on read |
| **Data-Integrity Auditor** | Cross-cutting | checksums, record counts, sha256, drift, C12/C16 violations |

---

## 2. Forensic questions (to exhaust)

1. **Remaining silent-write sites:** besides `stage4_merge.py`, which other files build a single
   large string and write it without post-write size/byte verification? (delegate #1)
2. **Remaining silent-exception swallows:** which `except … : pass` blocks hide a real failure (C16)?
   (delegate #2)
3. **Checkpoint read fail-closed:** for each S0…S6 checkpoint write→read pair, is a BUG-188-style
   truncation DETECTED on read, or silently accepted? (delegate #3)
4. **Post-write verification coverage:** does every `safe_write`/`safe_write_jsonl` caller now benefit
   from the fail-loud size assertion? Are there callers bypassing `io_guard` entirely (raw `open().write`)?
5. **`related_fbs` semantic change:** the cap changed the graph from dense→sparse ranked. Does any
   downstream consumer (S6, `retrieve.py`, `stage4_5_enrich`, LightRAG) assume the dense domain_overlap
   graph and now silently degrade?
6. **Depth pre-pass loss:** `.depth.json` is deleted at completion (line 2042). Is the ~4h depth phase
   genuinely unrecoverable, or is depth cached elsewhere (`.cribs.json`, FB records, embeddings)?
7. **Determinism/contamination on re-run:** is the re-run truly a fresh regeneration from S2 (temp=0.0,
   fb_id fixed at S2 per D2350), with the corrupt checkpoint superseded and never read? Any resume path
   that could re-read the truncated `checkpoint.jsonl`?
8. **Emerging-rate gate ordering:** `scripts/gate_emerging_rate.py` must run on the COMPLETE checkpoint
   (fail-closed). With the re-run, does the gate run before S5 consumes the checkpoint?

---

## 3. Findings so far (pre-roundtable)

- **F1 — test isolation bug (FIXED this session):** `tests/test_checkpoint_resume_d2409.py` monkeypatched
  `STAGE5_CHECKPOINT` but not `S5_INPUT_FINGERPRINT_PATH` (a module constant), so the D2485 fingerprint
  test read/wrote the REAL `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl.input_fingerprint.json`
  and hashed the real 2GB S4 checkpoint — order-dependent and self-polluting. Fixed: isolate `STAGE4_CHECKPOINT`,
  `STAGE4_5_CHECKPOINT`, and `S5_INPUT_FINGERPRINT_PATH` to `tmp_path` + write the fingerprint before resume.
  Now deterministic (0.3s vs 2.7s) and no live-dir pollution. **148/148 tests green.**
- **F2 — depth pre-pass NOT reusable (correction):** `.depth.json` is unlinked at completion, so the ~4h
  depth phase is lost with the truncated checkpoint. Re-run is a FULL ~40–52h, not ~35h.
- **F3 — `related_fbs` O(n²) is the root-size cause:** 32,335,994 edges (ubiquitous `emerging` domain).
  Now capped to 20/FB → ~34.7MB at 7,874 FBs.

## 4. Delegate audit results (3 read-only forensic subagents, 2026-08-30)

### 4a. Silent-exception audit (C16) — 4 HIGH + pervasive config-fallback pattern
- **HIGH (data corruption/loss, BUG-188 analog):** `stage1_5_intent.py:60` (embedding failure → empty vector consumed as real data); `stage2_extract.py:2999` (malformed segment_ids → silently dropped); `stage6_okf_export.py:396` (bad line → silently skipped, count under-reports); `stage2_extract.py:3028` (LLM crash vs no-result indistinguishable).
- **Pervasive C12+C16 pattern:** config-read failures return hardcoded fallbacks with no log — `stage4_merged_call.py:140/146/574/584/717/837/845/851/861`, `stamp.py:58` (git → `"unknown"`, breaks R14), `stamp.py:112`, `stage1_3_prefilter.py:77`, `stage2_extract.py:694`, `hybrid_gate.py:46`, `runner.py:329`, `stage6_commit.py:310`, `config_audit.py:143/187`, `model_lazyload.py:109`.
- ~18 minor C16 (state/status/DB/provenance silent degradation).

### 4b. Checkpoint write→read boundary audit
- **1 true silent-acceptance reader:** `stage0_convert.py:160-162` `load_existing_checkpoint` (`except JSONDecodeError: continue`) — S0 resume silently skips corrupt lines.
- **2 non-atomic writers bypassing io_guard:** `stage1_5_fastembed.py:214`, `stage1_5_domain_cluster.py:236-239` (plain `open(...,"w")` loop). **NOT on the active path** — `justfile stage1_5` uses `stage1_5_embed_cluster.py` (safe_write).
- **Universal blind spot:** clean record-boundary truncation (whole trailing records dropped at a `\n`) is undetectable at every read boundary — only `_write_s4_checkpoint` does a write-side record-count self-check. No downstream reader validates against an expected total.

### 4c. Silent-truncation audit (BUG-188 class)
- **TIER 1 (non-atomic `open(...,"w")` checkpoint writes):** `bridge_s2_to_s4.py:68` (writes the S4 checkpoint, but it's a standalone one-off converter, NOT the active `stage4_merge.py` path); `stage1_5_fastembed.py:214/219`; `stage1_5_domain_cluster.py:236/239`; `probe_run.py:264/123`; `stage0_5_extract_metadata.py:400`; `golden_sampler.py:264`; `run_diagnostic.py:348`.
- **TIER 2 (missing fsync before replace, D2177):** `scripts/benchmark_s4_depth_prompt_ab.py:142-147`.
- **TIER 3 (giant `"\n".join` + buffered write, no byte/record verify — defense-in-depth):** `scripts/fix_residual_violations.py:112/119`, `fix_singleton_48_posthoc.py:183/201`, `fix_singleton_quality.py:170`, `fix_s2_posthoc.py:95`, `rerun_s2_targeted.py:194/211/157`.

### 4d. Verdict for the S4 re-run
The active S2→S4→S5→S6 path is **fail-closed** (fixed `safe_write`/`safe_write_jsonl` + `load_jsonl` readers). The findings above are **real but mostly off the active path** (alternate S1.5 impls, one-off scripts, post-hoc fixers, latent config-read fallbacks). Priority for follow-up (MUST before next full corpus pass, not blocking the S4 re-run): convert the 7 Tier-1 non-atomic writers to `safe_write_jsonl`; fix the 1 S0 silent-resume reader; add fsync to the benchmark script; add a record-count/trailing-record verification to the universal read-side blind spot.
