# Session Handoff — 2026-08-16 (Canary completion → grammar/depth/taxonomy/integrity)

> **State at handoff:** S4→S5→S6 canary completed (279→278 FBs, 235 PASS, 278 committed).
> Grammar A/B resolved (D2392). Depth skew fixed (D2393). Taxonomy synonym bug + discipline
> alias expansion done (D2394). Integrity 17/17 + audit green after dropping a dead legacy
> column (D2395). Working tree has uncommitted changes across decisions/governance/pipeline/config.

---

## 1. What this session established (decisions D2391–D2395)

- **D2391** — S6 schema-migration gap (`is_summary` + `classification_status` missing) fixed → 278 committed cleanly.
- **D2392** — **Grammar A/B RESOLVED.** 0.6.0 bundles xgrammar 0.2.3 and it *works* (Phi-4-mini
  returns clean JSON, no `warning` header), but `response_format=json_object` + gpt-oss-20b
  → **empty content** (xgrammar collides with the Harmony reasoning protocol). OFF (0.5.1) = 30/30
  valid JSON. **Decision: keep grammar OFF; leave the 0.5.1 server on 11435.**
- **D2393** — **Depth skew fixed.** Tightened `DEPTH_FOCUSED_PROMPT` + `DEPTH_BATCH_SYSTEM`
  (cross-domain = 2+ DISTINCT disciplines via shared mechanism; DEFAULT to domain). Re-measure on next S4 run.
- **D2394** — **Taxonomy: two fixes.** (1) `pipeline/schemas.py` synonym-index kind-filter bug
  (domain synonyms leaked into the discipline index). (2) discipline raw-alias expansion in
  `config/taxonomy_v5.yaml`. Result: discipline `emerging` **32.0% → 15.5%**. Domain `emerging`
  93.9% is a *structural* gap (design-centric taxonomy vs business corpus) → deferred to governance review.
- **D2395** — **Integrity fix.** Dropped dead legacy `s3_original_domain` column (DB 61→60 cols).
  `just integrity` now 17/17; `just audit` green (config-audit strict PASS, delegate-safety PASS).
  `ruff` = 200 pre-existing style findings (non-blocking backlog, E402 import-placement etc.).

---

## 2. Two questions answered (senior-level)

### Q1 — "Should we downgrade to 0.5.1 just for grammar? Won't that slow S2/S4?"

**We are NOT downgrading.** 0.5.1 is the *installed server* (Homebrew + launchd on 11435); only
the GUI app was updated to 0.6.0. "Keep 0.5.1" = status quo, not a downgrade.

Grammar and speed are **orthogonal**:
- **Grammar:** our pipeline sends `response_format={"type":"json_object"}` (`pipeline/omlx_call.py:383`).
  On 0.5.1 that's *soft* (prompt injection → 100% valid JSON). On 0.6.0 it triggers xgrammar →
  **breaks gpt-oss-20b**. To use 0.6.0 safely we'd have to **strip `response_format`** from the
  pipeline (grammar off) — a code change, not a flag.
- **Speed:** 0.6.0's headline wins are **concurrent prefill** (1.6–43×) and better memory
  reclamation. Our S2/S4 are **largely serialized** (one cluster/FB at a time; S4 depth batches of 4),
  so the concurrency win is marginal. Single-request generation time (the dominant cost) is
  model-bound, not concurrency-bound.

**Recommendation:** stay on 0.5.1 through T1.1. Re-evaluate 0.6.0 *after* T1.1 as a dedicated
speed task with a proper latency A/B — and if adopted, do it by stripping `response_format`
(grammar off), never by "keeping grammar and breaking gpt-oss". 0.6.0 also has a C3 sovereignty
risk (opt-in `omlx.ai` benchmark upload) and unverified model-format changes (re-detects some
models as VLM with different sizes).

### Q2 — "Does `emerging` stay within the agreed canonical cap (35 domains / 72 disciplines)?"

**Yes, and the system already enforces it.** Caps are `config/pipeline_config.yaml` →
`taxonomy.max_domains: 35` / `max_disciplines: 72` (D2378). `emerging` is a *fallback marker*,
NOT a canonical — it never counts toward the cap.

- The **discipline** fix added raw *aliases* to *existing* canonicals (72 unchanged) → no cap growth.
- The **domain** fix (93.9% emerging) needs *new* canonical domains → would exceed 35 → requires
  **promote-with-demote** (taxonomy_manager `check_for_replacements`) + human review. **Not auto-applied.**

---

## 3. Priority order for next session

| # | Pri | Task | Notes |
|---|---|---|---|
| 1 | **P0** | **DB reset decision** — `maxwell.db` = 676 rows / 5 run_ids (canary 557 = old 279 + new 278). Pick fresh-DB or run-specific-DB policy before final T1.1. 5-min decision. | G8 |
| 2 | **P1** | **Run T1.1 full** — S1.5→S6 on the full library. Canary already validated S2→S6 (279→278 FBs, 235 PASS, 278 committed). This is the main multi-day run. | blocking only on #1 |
| 3 | **P1** | **Domain taxonomy promotion** (D2394) — human-review top ~15 domain labels (risk management 31, behavioral economics 18, psychology 16, operations research 10, change management 9, …), promote + demote unused design domains, re-map, re-measure. Highest-leverage *quality* fix. | G3 |
| 4 | **P2** | **Vector (sqlite-vec) remediation** — via Homebrew Python (`brew install python@3.12`) if vector search is a T1.1 requirement. FTS + Parquet already serve retrieval. | G9 |
| 5 | **P2** | **Depth re-measure** (D2393) — confirm cross-domain→domain shift after prompt tightening on the next S4 run. | G4 |
| 6 | **P3** | **`is_specialized` persistence** — parsed-but-not-persisted (None × 278). | G5 |
| 7 | **P3** | **0.6.0 speed eval** (post-T1.1) — latency A/B with `response_format` stripped. | G6 / D2390 |

---

## 4. Files changed this session (uncommitted)

**Code / config:**
- `pipeline/stage4_merged_call.py` — depth prompt tightening (D2393)
- `pipeline/schemas.py` — synonym-index kind-filter fix (D2394)
- `pipeline/stage6_commit.py` — `_migrate_drop_column` + drop `s3_original_domain` (D2395)
- `config/taxonomy_v5.yaml` — discipline raw-alias expansion (D2394)

**Governance / decisions:**
- `DECISION-LOG.md` — D2392–D2395 appended
- `config/decisions.yaml` — synced (383 → 384 decisions)
- `governance/buglog.md` — BUG-134 (synonym kind-filter), BUG-135 (dead column), header
- `governance/aggregated_remaining_tasks.md` — header + G2/G3/G4/G6 statuses
- `agent/session_seed.yaml` — header, phase.completed, phase.pending

**Artifacts:** `ab_off.json`, `ab_on.json` (grammar A/B). DB backup: `/tmp/maxwell.db.bak_d2395`.

**Note:** many other files show as `M` in git status from *prior* sessions (config/golden/*,
pipeline/bridge_s2_to_s4.py, etc.) — not touched this session.

---

## 5. Key files to read first on resume

- `governance/SESSION-HANDOFF-2026-08-16.md` — this file
- `DECISION-LOG.md` — D2391–D2395 (top of file)
- `governance/aggregated_remaining_tasks.md` — §#0.8 table (G1–G9 status)
- `pipeline/stage6_commit.py` — `init_db()` migrations (D2395 drop at the end)
- `pipeline/schemas.py` — `_build_synonym_index()` step-2 kind filter (D2394)

---

## 6. Suggested commit message

```
fix(pipeline): grammar A/B off + depth prompt + taxonomy synonyms + dead column drop (D2392-D2395)
```
