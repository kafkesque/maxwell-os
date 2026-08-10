# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-10 18:45 | **Source:** D2240-D2243 (panic investigation + depth removal + S4 benchmark)
> **P0:** 8/8 DONE ✅ | **P1:** 7/8 (T-009 partial) | **P2:** 4/4 DONE ✅
> **Golden set:** v4.4 (73 examples, 50 FBs, 52 pos / 21 neg)
> **Models:** Qwen3-Coder-30B (S2 gen), Phi-4-mini-8bit (S4 cls), Gemma-4-31B-8bit (NEW, S5/R5 verifier)
> **Panic:** D2243 — IOGPUMemory underflow from dual GPU clients. Prevention in place.

---

## 🔴 P0 — COMPLETE (8/8)

| ID | Task | Status |
|----|------|--------|
| T-001 | Strip S4 CRIBS fields (169 instances) | ✅ |
| T-002 | sqlite-vec 1024→512 | ✅ |
| T-003 | Evidence 190/190 verbatim | ✅ |
| T-004 | extraction_type in GoldenFB | ✅ |
| T-005 | Convergence routing fix | ✅ |
| T-006 | 6 C12 thresholds → config | ✅ |
| T-007 | DSPy harness + MIPROv2 pilot | ✅ Pilot: best 44.75% (2 eval FBs) |
| T-007b | json_repair name collision (D2240) | ✅ → json_fixer.py |

---

## 🟡 P1 — QUALITY BLOCKERS

| ID | Task | Status |
|----|------|--------|
| T-008 | Depth misclassifications ×3 | ✅ |
| **T-009** | **Author cap ≤3** — Griffiths (5), Meadows (4) exceed. 89 unique authors. Swap 3 books w/o breaking evidence verbatim. | ⚠️ 2 offenders remain |
| T-010 | NLI inversion (ModernBERT primary) | ✅ |
| T-011 | NLI fallback defaults | ✅ |
| T-012 | Taxonomy v5.1 aligned | ✅ |
| T-013 | Golden version 4.2→4.4 | ✅ |
| T-014 | CONV-035/037 false convergence | ✅ |
| T-015 | Type expansion (CM/NH/DM/EP) | ✅ |

---

## 🟢 P2 — COMPLETE (4/4)

T-016 EMBED_MAX_CHARS ✅ | T-017 HDBSCAN removal ✅ | T-018 schemas v3.0 ✅ | T-019 MISSION v3.0 ✅

---

## 🔵 POST-AUDIT FINDINGS (D2241-D2243)

| ID | Finding | Priority | Status |
|----|---------|----------|--------|
| A-001 | **Remove depth from S2** (D2242) | P0 | ✅ DONE — Signature, metric, few-shot all cleaned. Metric rebalanced to 1.00. |
| A-002 | Traditional S2 data leakage (few-shot = test dist) | P1 | ⏳ TODO — author-disjoint split needed |
| A-003 | MIPROv2 pilot — crashed on json_repair.loads | P0 | ✅ FIXED (D2240) — best score 44.75% |
| A-004 | N=6 comparison insufficient (need ≥20-30) | P1 | ⏳ TODO |
| A-005 | **Gemma-4-31B S4/S5 benchmark** | P1 | ✅ DONE (D2244) — Gemma 50% vs Phi 37.5%. Both fail cross-domain. |
| A-006 | Dead `score += 0.0` in metric | P2 | ✅ REMOVED with A-001 |
| A-007 | **Kernel panic D2243** — dual GPU clients (mlx_lm + OMLX) | P0 | ✅ MITIGATED — OMLX-only for all models, memory guard 55GB |

---

## ⚠️ D2243 — KERNEL PANIC ROOT CAUSE & PREVENTION

**Symptom:** `panic: "completeMemory() prepare count underflow" @IOGPUMemory.cpp:492` — Apple M1 Max GPU driver

**Root cause chain:**
1. Loaded Gemma-4-31B-it-MLX-8bit (31GB) via `mlx_lm` (direct Metal client)
2. OMLX server already serving Qwen3-Coder-30B-4bit (~15GB) + Phi-4-mini (~4GB) as a **second Metal client**
3. Unified memory: 64GB total, ~50GB+ committed across both clients + macOS
4. Two concurrent Metal GPU memory allocators under pressure → IOGPUFamily memory prepare count underflow → kernel panic (pid 31888: Python)

**Why it happened now (not before):** Gemma-8bit is 31GB — 2× the size of any previously loaded model. Crossing ~50GB of concurrent GPU-committed memory triggered the driver bug.

**Prevention (mandatory):**
- 🚫 NEVER load models via mlx_lm directly while OMLX is serving (one GPU client at a time)
- ✅ Serve ALL models through OMLX API (port 11435) — memory guard `--memory-guard-gb 55` + eviction
- ✅ Check memory headroom before any large model load: `vm_stat` → available > model_size + 10GB
- ✅ Gemma-4-31B registered in OMLX via symlink (not HF cache direct)

**Verified post-panic:** OMLX loaded Gemma-4-31B safely (30.73GB, total 38.09GB), completed classification calls (108s/call, 2.9-3.9 tok/s reasoning model).

---

## 📋 REMAINING EXECUTION ORDER

```
DONE   → A-005 benchmark: Gemma 50% vs Phi 37.5% (D2244). Cross-domain 0% both.
NEXT   → Post-A001 S2 comparison rerun (Traditional vs DSPy — no depth now)
NEXT   → A-002 author-disjoint few-shot split for fair comparison
P1     → T-009 replace Griffiths×2 + Meadows×1 (careful, evidence-safe)
P1     → A-004 expand test set to 20+ examples
P2     → Configure Gemma as S5 verifier (R5) once S4 role decided
```

## STATUS SUMMARY

```
P0: ████████████████████ 8/8  (100%)
P1: ████████████████░░░░ 7/8  (87%) — T-009: 2 author offenders
P2: ████████████████████ 4/4  (100%)
NEW: ████████████░░░░░░░░ 4/7  (57%) — A-001/003/006/007 done, A-005 running
────────────────────────────────────
TOTAL: ██████████████████░░ 23/27 (85%)
```
