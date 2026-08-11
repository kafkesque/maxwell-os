# Maxwell OS — Session Handoff (D2254)
> **Created:** 2026-08-10 23:58 | **Updated:** 2026-08-11 12:00 (D2255-D2262 P0 audit fixes applied)
> **From:** D2250-D2253 + D2255-D2262 sessions | **Repo:** main (uncommitted)
> **Next session starts HERE.** Read this first, then the pointer chain below.

---

## 0. PRE-FLIGHT (before any pipeline run)

### 0A. CPU — Goose MacWebContentsOcclusion (D2262)
Goose (Electron) disables rendering when its window is occluded → UI renderer ~25% CPU → steals 2-3 M1 Max cores from OMLX.
**Fix options:**
- Keep Goose window fully visible during long pipeline runs (not minimized, not behind other windows)
- Or: `defaults write com.block.goose NSWindowOcclusionDetectionEnabled -bool false` (restart Goose after)

### 0B. E2E DIAGNOSTIC GATE (D2261) — RUN BEFORE T1.1
The "yield crisis" (0.004%) is from v2.0 pipeline. v3.0 yield has never been measured.
**Command:** `python3 pipeline/run_diagnostic.py --books 100`
**Gate criteria:**
- Yield >1% AND S5 pass rate >40% → APPROVE T1.1 full run
- Yield <0.5% OR S5 pass rate <20% → HALT, diagnose before scaling
- Between → judgment call with real data

---

## 1. WHAT WAS DONE (this session, D2250-D2253 + D2255-D2262)

| Area | Result | Evidence |
|------|--------|----------|
| **S4 depth (BUG-075)** | **87.5% (7/8), cross-domain 3/3** — was 0/3 for all models | `governance/s4_depth_benchmark_focused_prompt.json` |
| **S4 classifier (D2249)** | GPT-OSS-20B-MXFP4-Q8 live; Phi retired (BUG-053) | `config/pipeline_config.yaml` `models.verifier` |
| **S2 (T-007b)** | **Hybrid 0.736** > DSPy 0.672 > Trad 0.591 | `governance/s2_comparison_results.json`, `governance/DSPY_VALIDATION_REPORT.md` |
| **Golden audit** | 0 gaps, 73/73 rationale, 194/194 verbatim, author cap ≤3 | `governance/SESSION_AUDIT_D2250.md` |
| **Author cap** | Christian 4→3 (CONV-012 → *The Age of AI*) | `config/golden/stage2_fewshot_convergent.yaml` |
| **Cost model (D2253)** | Full run = **~21-26h** (not 100h) | `ROUNDTABLE_MASTER_PROMPT.md` §G |
| **Master prompt** | v8 with hybrid + cost model + audit sections | `governance/ROUNDTABLE_MASTER_PROMPT.md` |
| **P0 audit (D2255-D2262)** | DeBERTa FEVER live, golden meta fixed, docstrings fixed, GOLDEN-REVIEW archived, model registry corrected | `governance/COMPREHENSIVE_AUDIT_2026-08-11.md` |

**Commits:** `af09de9` (BUG-075/GPT-OSS/hybrid/audit) → `88fd43f` (T-007b resolution) → `fcf23a9` (validation report) → pending: P0 fixes + governance sync (D2255-D2262).

---

## 2. NEXT ACTIONS (in order)

### 🔴 Action 0: E2E Diagnostic Gate (D2261) — RUN BEFORE T1.1
```
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
python3 pipeline/run_diagnostic.py --books 100
# Wait ~3-6h. Check output: governance/e2e_diagnostic_2026-08-11.json
# Gate: yield >1% + S5 pass >40% → proceed to T1.1
```

### 🔴 Action 1: Launch T1.1 full run (~26h, batch-resume)
```
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
# Verify OMLX healthy first:
curl -s localhost:11435/health
# Launch S2 (12,964 clusters, 3 workers, tiered):
nohup python3 pipeline/stage2_extract.py --only-convergent > /tmp/s2_full_run.log 2>&1 &
# Monitor first hour — expect ≥2× single-thread throughput:
tail -f /tmp/s2_full_run.log
# Then S4 (merged + GPT-OSS + focused depth), S5, S6 — stage by stage.
```
**Checkpoint:** `knowledge pipeline/stage2_extract/latest/checkpoint.jsonl` (resume-aware).
**First-hour gate:** if throughput < 2× single-threaded, check OMLX queue contention →
raise `services.omlx.default_timeout` or drop `stage2.max_workers` to 2.

### 🟠 Action 2: T-007b-v2 (overnight, optional polish)
MIPROv2 re-opt with 3 demos (config already set) to close DSPy gate FN
(CONV-036/043/040). Hybrid works WITHOUT this — do it only if GPU idle:
```
nohup python3 pipeline/dspy_trainer.py --full > /tmp/dspy_mipro_v3.log 2>&1 &
```
⚠️ 4 demos ≈ 20h — do NOT use 4 interactively (D2252).

### 🟠 Action 3: T1.2 yield diagnostic
Re-measure yield on the full run output (was 14 FBs/852 books = 0.004%).
Investigate why convergent yield is so low — check split-probe efficacy + gate strictness.

### 🟡 Action 4: T1.3/T1.4 (pre-S5 quality gates)
- T1.3: NLI calibration on real data (0.5/0.6/0.8 vs bge-m3)
- T1.4: faiss_threshold mismatch (0.75 vs 0.70) — check `config/pipeline_config.yaml`

### 🟡 Action 5: T-015 golden expansion
Fix depth class imbalance (universal=1, specialized=1) + extraction type expansion.
Directly addresses the D2250 audit finding.

---

## 3. KEY CONFIG STATE (verified D2250)

```yaml
models.verifier.model: gpt-oss-20b-MXFP4-Q8   # D2249
models.verifier.reasoning_off_prefix: 'Reasoning: none'  # BUG-074
models.verifier.reasoning_off_models: [gpt-oss-20b-MXFP4-Q8]
models.verifier.max_tokens: 1024
stage4.depth_focused_classification: true     # BUG-075 fix
stage4.depth_max_tokens: 512
s2.max_workers: 3                              # T1.1 parallelism
s2.dspy_max_labeled_demos: 3                   # T-007b-v2 (overnight only)
```

## 4. MODEL REGISTRY

### OMLX models (active pipeline)
- `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` — S2 generator
- `gpt-oss-20b-MXFP4-Q8` — S4 classifier/verifier (replaced Phi-4-mini, D2249/D2250)
- `gemma-4-E4B-it-MLX-4bit` — S5 cross-family deep verifier
- `bge-m3` (Ollama) — embeddings (1024-dim)

### Local HuggingFace models (active pipeline)
- `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` — S5 NLI pre-filter (D2255, FEVER-trained)

### Retired / non-pipeline
- `gemma-4-31B-it-MLX-8bit` — retired from S4 (D2249). Not the same as active gemma-4-E4B.
- `Phi-4-mini-instruct-8bit` — smoke test fast_model only + agent assignments. NO pipeline config role.
  ⚠️ BUG-079: Was claimed as "S5 verify/gates" in prior handoff — incorrect. Config has no S5 role for Phi.

## 5. KNOWN GAPS / BLINDSPOTS (honest)

1. **Golden depth imbalance**: universal=1, specialized=1 (4%) → T-015
2. **DSPy gate FN**: CONV-036/043/040 rejected → T-007b-v2
3. **decisions.yaml historical gaps**: D2210/D2212/D2233-D2239 missing (present in DECISION-LOG.md) → Gov-sync task
4. **Full-run drift**: old S2 checkpoint = v2.3 schema (0 overlap) — fresh run needed (T1.1)
5. **S4 merged-call depth**: long prompt still over-assigns "universal" — focused depth call overrides (verified)

## 6. SAFETY (D2243 panic prevention)

- OMLX-only serving. NEVER direct-load models via mlx_lm while OMLX runs.
- Memory guard: keep ≥5GB free. If eviction races appear (GPT-OSS missing content),
  `omlx_call.py` now retries (C23) — verified.
- `gemma-4-31B` (31GB) retired from S4 — consider `omlx stop` → remove symlink if memory tight.
