# Session Handoff — 2026-08-23 — P1.2 relabel + P1.3 human verdicts + OMLX fixes

> **Purpose:** resume the Maxwell OS 2.0 S2 `extraction_type` FORM-drift repair from a new session.
> **Decisions landed:** D2434 (P1.2), D2435 (P1.3), D2436 (OMLX). Registry `config/decisions.yaml` up to D2436.
> **Working tree:** changes are UNCOMMITTED — commit when satisfied.

---

## 1. What was DONE this session

### P1.2 — extraction_type relabel sweep (D2434) — ✅ DONE + PROMOTED
- **Judge = gemma-4-E4B** (`S4_DEPTH_MODEL`), not Qwen3 (R5 cross-family).
- Relabeled single-source/singleton `extraction_type` only: **3,412 changed / 1,348 unchanged / 1 failed**.
- The 1 failed record (`#5563 Dialectal Convergence Analysis`) was manually fixed to `normative_heuristic`.
- **Promoted to production** `knowledge pipeline/stage2_extract/t11/checkpoint.jsonl`.

### P1.3 — human-adjudicated verdicts (D2435) — ✅ DONE
- 49/58 verdicts adjudicated; **14 records corrected** to human label (35 already matched gemma).
- 9 NONE (USER-FLAG content_type) records → quarantined to `relabel_work/quarantine_none_records.jsonl`.
- Verified: **0 mismatches** remaining; only `extraction_type` touched; fb_id order preserved.

### OMLX server (D2436) — ✅ DONE
- `--memory-guard safe` (was `--memory-guard-gb 55` → eviction was disabled).
- `--no-cache` (killed 185GB paged-SSD cache thrash; dispatch 9.8s → 2–7ms).

---

## 2. Final data state

| File | Role |
|------|------|
| `checkpoint.jsonl` | **LIVE** — relabel + #5563 + 14 human corrections |
| `checkpoint.jsonl.pre_relabel` | pristine pre-relabel backup, md5 `fc17b4ee4c4634d66988524ceff5bb9b` |
| `checkpoint.jsonl.pre_p13` | gemma-relabeled, pre-human-verdict backup |
| `relabel_work/checkpoint_gemma.jsonl` | relabeled working copy |
| `relabel_work/quarantine_none_records.jsonl` | 9 NONE/USER-FLAG records for review |

**Final `extraction_type` distribution (8,410 records):**

| Label | Pristine | After relabel | After P1.3 |
|---|---|---|---|
| descriptive_model | 1,447 | 3,877 | **3,874** |
| empirical_pattern | 1,630 | 2,075 | **2,069** |
| normative_heuristic | 1,562 | 1,969 | **1,976** |
| causal_mechanism | 3,771 (44.8%) | 488 (5.8%) | **491 (5.84%)** |

- Causal share corrected from ~45% (drifted) to ~5.8% (true rate, matches the sanity-pass estimate of ~5–6%).

---

## 3. Key revelations (session learnings)

1. **Judge choice:** gemma-4-E4B agrees with human **73%** on the hardest 49 records; Qwen3 original labels only **8%**. gemma ~3s/call vs Qwen 15–20s/call.
2. **Ladder tightening HURTS** — current `_DECISION_ORDER` 49% → tightened 45% human agreement. Rejected.
3. **Mechanism-field poisoning:** when the prompt includes `mechanism`/`boundary`/`consequence`, Qwen3 over-claims causal (11% agreement). Dropping those fields raises Qwen to 41% but **hurts gemma** (73%→69%). → gemma + full prompt is best; no prompt change.
4. **Few-shot hurts gemma** — leave-one-out few-shot degraded gemma 73%→59%; self-reported confidence was flat/uninformative.
5. **Convergent cluster healthy** — 11.3% causal, gemma×Qwen agreement 75%; NOT relabeled.
6. **No MLX upgrade available** — gemma-4-31B too large (57G), gpt-oss-20b broken, Phi-4-mini hallucinates; HF trending is abliterated/GGUF noise.
7. **gemma-4-E4B prefill slowness** — 256 `head_dim` forces a slow SDPA path (~72 tok/s on 700-token prompts); not config-fixable.
8. **BUG-164** — 3 duplicate fb_ids (6 records) are **pre-existing** (in pristine backup too), not introduced by this session.

---

## 4. Remaining tasks — most critical first

### 🔴 P0 — data recovery / structural
1. **P0.x — recover ~5,500–6,000 summary-gated objects (D2418/BUG-146).** Code is DONE (D2417/D2421). Run is pending:
   ```bash
   # 1. reconstruct the FULL gated set (current .gated_ids has only 158; the full log has 9,950 "summary gated" lines)
   python3 scripts/seed_gated_ids.py \
     --log "knowledge pipeline/runner_t11_v3.log" \
     --validate-segids "knowledge pipeline/stage2_extract/t11/checkpoint.jsonl.segids"
   # 2. re-extract gated clusters with the content_type-aware gate (recover PT/PI/TI/GE)
   python3 pipeline/stage2_extract.py --reprocess-gated
   # 3. then route recovered objects through S4 -> S5 -> S6
   ```
   Multi-hour LLM job — verify OMLX is up (`just health`) before launching.
2. **BUG-150 — S4 discipline `emerging` 38.4%.** Promote canonical disciplines (`graphic design`, `data visualization`, `organizational behavior`, `design thinking`, `product design`, `ux design`). Biggest classification-quality gap.

### 🟠 P1 — high quality
3. **BUG-149 — S4 name truncation** (`max_words=5` hardcoded, 176 FBs). Wire config `fb_name_max_chars`/new key into `normalize_fb_name`.
4. **P1.3 (residual) — wire gpt-oss as a cross-family disagreement FLAG** (not owner). Human verdicts already applied.
5. **R1.3 — "the passage" meta-commentary** (1,036 records) prompt fix + sweep.
6. **R1.4 — near-dup dedup** (38 name groups/~80 records) — now also covers the 3 duplicate fb_ids (BUG-164).
7. **BUG-151 — taxonomy overlap** (`education` dual-listed + 267 aliases).
8. **BUG-148 — stale `route="FB"`** (remove or derive from content_type).

### 🟡 P2 — medium
9. **BUG-159 — prompt-injection hardening** + contamination canary (cluster_11649).
10. **BUG-145 — extraction_type/content_type conflation** (128 targets) 1-line prompt fix.
11. **BUG-160 — evidence-passage relevance** (D2428; add topical-relevance check).
12. **R1.5 — content_type instability** monitor. **R1.6 — third independent pass** (optional).

### ⏸ After S4–S6
13. **R2 — FORM axis refactor** (justification × modality, D2427) — must land before anything consumes FORM.

### 🧹 Housekeeping
14. Review the 9 quarantined records (`quarantine_none_records.jsonl`).
15. DECISION-LOG.md lags decisions.yaml (D2422 vs D2436) — backfill or re-sync.

---

## 5. Rollback

- To pristine pre-relabel state: restore `checkpoint.jsonl.pre_relabel` → `checkpoint.jsonl`.
- To gemma-relabel (pre-human-verdict) state: restore `checkpoint.jsonl.pre_p13` → `checkpoint.jsonl`.

---

## 6. Session decisions summary

| Decision | What | Status |
|---|---|---|
| D2434 | P1.2 relabel with gemma judge + promote | ✅ done |
| D2435 | P1.3 human verdicts applied + quarantine | ✅ done |
| D2436 | OMLX memory-guard + no-cache | ✅ done |
| P0.x | content_type-aware gate + `--reprocess-gated` (D2417/D2421) | ✅ code done, 🔴 run pending |
