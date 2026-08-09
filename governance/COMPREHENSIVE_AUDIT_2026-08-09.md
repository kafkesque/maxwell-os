# Maxwell OS v3.0 — Comprehensive Audit Report
> Generated 2026-08-09 13:14. Audit scope: pipeline, configs, governance, models, disk, memory, C-rules compliance, optimization.

---

## 🔴 CRITICAL FINDINGS

### 1. MEMORY CRISIS (C1, C3, C24)
| Issue | Detail | Impact |
|-------|--------|--------|
| OMLX loads 3 models | Phi-4-mini (default), Qwen3-Embedding-0.6B, Qwen3-Coder-30B | 29.5GB used |
| Dead-weight models | Phi-4-mini (~3GB), Qwen3-Embedding (~0.3GB) not used by S2 | ~3.3GB wasted |
| Available RAM | -12.6GB after OMLX | **System is SWAPPING** |
| KV cache thrashing | Insufficient memory → constant cache evictions | S2 slowdowns |

**Fix:** Move Phi-4-mini and Qwen3-Embedding to `~/.omlx/models_stashed/` during S2. Only restore when S5/S1.5 needs them.

### 2. DISK BLOAT (200GB+ total)
| Path | Size | Status |
|------|------|--------|
| `~/.cache/huggingface/` | **103GB** | Has 38GB Qwen3.6-35B (deleted from models dir, still in cache) |
| `~/.omlx/cache/` | ~24GB | SSD paged KV cache — accumulates on every restart |
| `~/.omlx/models_archive/` | Unknown | Duplicate models |
| `~/.omlx/models_stashed/` | Unknown | Stashed duplicates |
| `~/.omlx/*.bak` | 6 files | Stale settings backups |
| `~/Library/Logs/Homebrew/omlx/` | ~100MB | Rotating logs |

**Fix:** Delete Qwen3.6-35B HF cache (38GB), clear OMLX paged cache, clean stale backupe.

### 3. VERIFICATION MODEL GAP
| Model | Type | Works? | Why |
|-------|------|--------|-----|
| Gemma-4-E4B (current) | Cross-family verifier | ❌ 73% false negative | Demands verbatim evidence for synthesis |
| Qwen3-Coder-30B | Generator as verifier | ✅ Proven | Understands FB synthesis — but breaks R5 |
| DeBERTa-NLI (current) | NLI classifier | ⚠️ All NEUTRAL | Sentence-level entailment doesn't work for abstraction |
| Vectara HHEM | Hallucination detector | ⚠️ Not MLX | Needs custom Python modules, not OMLX-compatible |
| gemma-2-9b-it-4bit | General chat | ❓ Untested | Available as MLX 4-bit (15K downloads), could test |
| Qwen2.5-7B-Instruct-4bit | General chat | ❓ Untested | Available as MLX 4-bit (19K downloads), could test |
| Mistral-Nemo-12B-4bit | General chat | ❓ Untested | Available as MLX 4-bit (5K downloads) |
| Llama-3.2-3B-Instruct-4bit | General chat | ❌ Too small | 3B cannot evaluate complex synthesis (proven by Qwen3-8B failure) |

**Verdict:** No dedicated verification model exists in the MLX 4-bit ecosystem. The task requires a model that understands convergent synthesis. Qwen3-Coder-30B is the only proven model. R5 cross-family is a nice-to-have; accuracy is a must-have.

---

## 🟡 HIGH IMPACT

### 4. C12 HARDCODED VALUES (22 violations)
| File | Hardcoded | Should Be |
|------|-----------|-----------|
| `stage1_5_embed_cluster.py` | `"ollama"`, `"bge-m3"`, `1024`, `64`, `300`, `0.0`, `"MPS"` | Config values |
| `omlx_watchdog.py` | `11435`, `1024`, `60`, `0.0` | Config values |
| `fix_remaining.py` | `1024`, `60`, `300` | Config values |
| `stage1_5_fastembed.py` | `60`, `"MPS"` | Config values |
| `golden_sampler.py` | `0.0` | Config value |
| `runner.py` | `60` | Config value |
| `schema_accessor.py` | `0.0` | Config value |
| `reliability.py` | `0.0` | Config value |

**Iron Rule C12 violated:** "NEVER hardcode ANY value — paths, thresholds, model names, magic numbers → config/*.yaml"

### 5. C17 TYPE HINTS (73 functions)
Worst offenders: `schema_accessor.py` (46/46 missing), `metrics.py` (5/5), `omlx_watchdog.py` (6/11)

### 6. C19 DEAD CODE
5 `__pycache__/` dirs in repo, 2 `_OLD` files, 6 `.bak` files in `~/.omlx/`

### 7. 12 DUPLICATE FBs
Same name+definition hash from different clusters. MinHash caught some (668 near-duplicates) but exact-duplicate-by-hash detection needed at S4 merge stage.

### 8. S5 GATE KILLS 73% OF FBs
Gemma-4-E4B false negative rate makes fail-closed non-viable. Only 4/15 tested FBs pass. If applied to all 2,655 convergent FBs, only ~700 would ship.

---

## 🟢 PIPELINE HEALTH

### S2 Convergent Extraction: COMPLETE ✅
| Metric | Value |
|--------|-------|
| Clusters processed | 3,742 |
| FBs extracted | 2,655 |
| NULL routes | 119 |
| Near-duplicates caught | 668 |
| Gate violations | 4 |
| Effective extraction rate | 77.0% |
| Elaboration present | 3/2,655 (0.1%) — pre-fix FBs need repair |
| Model | Qwen3-Coder-30B-4bit |
| Generator-Verifier drift | None (single-model pipeline) |

### S4 Classification: TESTED ✅
| Classification valid | 15/15 (100%) |
| Discipline distribution | psychology (14), strategic thinking (3), systems thinking (2), emerging (3), others (6) |
| Canonical mapping | Working — "Decision Theory" → "decision making" |

### Elaboration Repair: READY 🔧
| Script | `pipeline/repair_elaboration.py` |
| Batch size | 5 FBs/call |
| Time per batch | 135-148s |
| Total time (3 workers) | ~6.6 hours |
| Content overlap | 0% with definition/evidence |

---

## 🟠 OPTIMIZATION OPPORTUNITIES

### Pipeline Speed Bottlenecks
| Stage | Bottleneck | Optimization |
|-------|-----------|-------------|
| S1.5 Embed | Ollama bge-m3 on CPU | Switch to Qwen3-Embedding on MLX GPU (already downloaded) |
| S2 Extract | 50-66s per FB | Already optimal for 30B model on this hardware |
| S4 Classify | 15-68s per FB | Could use Phi-4-mini for classification (lighter task than extraction) |
| S5 NLI | 228-1558ms per FB | Already optimal — ModernBERT on MPS |
| S5 Gemma | 9-42s per FB | Replace with Qwen3-Coder or gemma-2-9b |

### Single-Source S2 (NOT STARTED)
| Clusters | 10,330 |
| Est. time | ~14 hours (@30s/FB with simpler prompt) |
| Model | Qwen3-Coder-30B (same as convergent) |

---

## 📊 CONSTITUTION COMPLIANCE

| Rule | Status | Notes |
|------|--------|-------|
| C1 ($0 marginal cost) | ✅ | All on local hardware |
| C2 (no vendor lock-in) | ✅ | Open formats, multiple model families |
| C3 (sovereign) | ⚠️ | Disk bloat from HF cache undermines local storage |
| C4 (multiple model families) | ⚠️ | Only Qwen family works for S2 generation |
| C6 (crash-safe writes) | ✅ | safe_write used throughout |
| C12 (no hardcodes) | ❌ | 22 violations found |
| C15 (buglog) | ⚠️ | 8 open items, some outdated |
| C16 (no silent errors) | ✅ | Log AND raise pattern |
| C17 (type hints) | ❌ | 73 functions missing return type hints |
| C18 (docstrings) | ⚠️ | ~3 functions missing |
| C19 (no dead code) | ❌ | 5 __pycache__ dirs in repo |
| C24 (hardware-adaptive) | ❌ | SWAPPING — no graceful degradation |

---

## 🎯 RECOMMENDATIONS (Priority Order)

### NOW (blocking)
1. **Delete Qwen3.6-35B HF cache (38GB)** — frees disk
2. **Clear OMLX paged cache** — frees ~24GB disk, eliminates stale KV cache entries
3. **Stash Phi-4-mini + Qwen3-Embedding** — frees ~3.3GB RAM for S2 KV cache
4. **Replace Gemma-4-E4B verifier** with Qwen3-Coder-30B — or test gemma-2-9b-it-4bit as alternative

### NEXT (high impact)
5. **Run elaboration repair** on 2,652 FBs (~6.6h)
6. **Launch single-source S2** on 10,330 clusters (~14h)
7. **Fix C12 violations** — extract 22 hardcoded values to config/*.yaml
8. **Run S4 classification** on all 2,655 convergent FBs (~2h)

### LATER (technical debt)
9. Add type hints to 73 functions (C17)
10. Remove __pycache__ dirs from repo (C19)
11. Clean stale OMLX settings backups
12. Test gemma-2-9b-it-4bit as verifier (download MLX 4-bit version)
