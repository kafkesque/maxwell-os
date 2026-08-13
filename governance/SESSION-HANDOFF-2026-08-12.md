# Maxwell OS — Session Handoff (2026-08-12)

> **Author:** goose (AAIF) — senior RAG engineer session
> **Purpose:** Continue from here in the next session. This is the canonical resume point.
> **Decisions:** D2000-D2307 (282) | **Buglog:** BUG-001…BUG-086 (see below)
> **Git:** last pushed `5c3256c` (batch CRIBS + cold-reload + S5 checkpoint + probe). **D2300-D2307 changes NOT yet committed.**

---

## ⚠️ FIRST ACTION (uncommitted work)

The following work is **complete but NOT committed/pushed**. Commit before continuing:

```bash
git add -A
git commit -m "D2300-D2307: DSPy tier-aware split + program load, InferenceProvider/OllamaEmbeddingProvider protocols, recall measurement, governance sync (282 decisions)"
git push
```

**Changed files:**
- `pipeline/dspy_trainer.py` — tier-aware split (GOLD-A→train/B→dev/CHALLENGE→test), `load_optimized_program()`, `--split {tier,random}`, `--load`
- `pipeline/pipeline_paths.py` — `DSPY_PROGRAM_PATH` (config-driven)
- `pipeline/providers/omlx_provider.py` — **NEW** `OMLXInferenceProvider` (InferenceProvider protocol)
- `pipeline/providers/ollama_provider.py` — **NEW** `OllamaEmbeddingProvider` (EmbeddingProvider protocol)
- `pipeline/providers/__init__.py` — exports new providers
- `pipeline/recall_measure.py` — **NEW** golden-set recall measurement
- `config/pipeline_config.yaml` — `s2.dspy_program_path`
- `config/decisions.yaml` — D2300-D2307 added; summary block re-synced (282 total / 240 active)
- `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `AGENTS.md`, `governance/aggregated_remaining_tasks.md`, `governance/buglog.md` (BUG-086)

---

## WHAT WAS DONE THIS SESSION

### Code (verified working)
1. **DSPy tier-aware split (D2304)** — `tier_aware_split()` enforces D2286: GOLD-A(49)→train, GOLD-B(3)→dev, CHALLENGE(21)→test. Default split is now `tier` (was random, which leaked CHALLENGE hard negatives into train).
2. **DSPy program load (D2304)** — `load_optimized_program()` + config-driven `DSPY_PROGRAM_PATH` (was hardcoded `/tmp`). `--load` CLI evaluates a persisted program on the test split.
3. **InferenceProvider protocol (D2306)** — `OMLXInferenceProvider` + `OllamaEmbeddingProvider` implement D2055 protocols, delegate to `omlx_call`/`ollama_embed` (single HTTP path).
4. **Recall measurement (D2307)** — `pipeline/recall_measure.py`: golden-set recall via deterministic name token-overlap (no LLM, R7-safe), per-tier breakdown (D2286).

### Governance (synced)
- `config/decisions.yaml` summary block was **stale** (claimed 225 active, actual 240; missing deferred/planned/resolved states). Fixed. Schema drift documented: 34 entries use `status` not `state`, case drift `ACTIVE` vs `active`.
- `AGENTS.md` knowledge sources updated (282 decisions, D2000-D2307).
- `governance/buglog.md` — **BUG-086** logged (S4 batch CRIBS silently ignored).

### Already done earlier (pushed at `5c3256c`)
- FIX-1 batch CRIBS wiring, FIX-2 cold-reload (45s), FIX-3 S5 checkpoint serialize.

---

## DSPy THREE GAPS (D2302) — STATUS

| # | Gap | Status |
|---|-----|--------|
| GAP-1 | `dspy_trainer.py` NOT wired into `stage2_extract.py` (hybrid gate is hand-written stopgap) | ⏳ **T1.2** — needs tier-aware training run + production wiring |
| GAP-2 | Stale Stage 3a artifacts (`prompts/s3a_optimized.txt`, `prompts/frozen/s3a_system_v1.txt`) | ⏳ **T1.2** — delete or archive (Stage 3a removed in D2120) |
| GAP-3 | Trainer used random split (ignored `tier` field) | ✅ **DONE (D2304)** |

---

## REMAINING / NEXT STEPS

### Immediately actionable (post-commit)
1. **Delete stale Stage 3a artifacts** — `prompts/s3a_optimized.txt` + `prompts/frozen/s3a_system_v1.txt` (GAP-2). Verify no code references (only `json_fixer.py:320` comment + `protect.py:37` `.s3a_checkpoint.json` name — both benign, verify before deleting).
2. **Roundtable evaluation** — share `governance/ROUNDTABLE_HANDOFF_PROBE_2026-08-12.md` + `probe_output/stage{2,4,5}_fbs.jsonl` with Kimi/Claude/DeepSeek/Qwen for independent quality/classification/factuality audit + golden example identification.
3. **T1.1 full run** (Option B = fresh S2 with hybrid gate) — using 12,964 clusters.

### Post-T1.1
4. **GAP-1** — wire DSPy trained program into S2 (run `python3 pipeline/dspy_trainer.py --full` then `--load` to validate; then wire `load_optimized_program()` into stage2_extract).
5. **StorageBackend protocol (D2300)** — stage6 SQLite hardcoded; last remaining modularity gap.
6. **End-to-end latency SLA (D2305)** — measure S0→S6 wall-clock.

---

## KEY FACTS (verify, don't assume)

- **Models:** Qwen3-Coder-30B (S2 gen) | GPT-OSS-20B (S4 classify) | DeBERTa-v3-large (S5 NLI) | bge-m3 (Emb). Gemma/RoBERTa/Phi-4-mini all removed from S5.
- **S5:** DeBERTa-only, threshold 0.10, P=1.000 R=0.556 F1=0.714. No human adjudication.
- **S4 bottleneck FIXED:** batch CRIBS ~19.4s/FB vs ~61s/FB (~3×). Root cause was orphaned `merged_call_enabled` config.
- **Golden set:** 73 examples → 75 dspy.Examples (49 GOLD-A / 3 GOLD-B / 21 CHALLENGE). Tiers now drive the split.
- **Recall:** `pipeline/recall_measure.py --golden config/golden/stage2_fewshot_convergent.yaml --output <stageN/output.jsonl>`
- **Hybrid gate:** `--hybrid` flag in stage2_extract.py (D2276), +0.145 quality.

## COMMANDS

```bash
# Validate DSPy split (no training):
python3 pipeline/dspy_trainer.py --dry-run              # tier-aware (default)
python3 pipeline/dspy_trainer.py --dry-run --split random

# Recall measurement:
python3 pipeline/recall_measure.py --golden config/golden/stage2_fewshot_convergent.yaml --output probe_output/stage2_fbs.jsonl --verbose

# Full pipeline (T1.1):
python3 pipeline/runner.py --hybrid --only-convergent
```

## VERIFICATION CHECKLIST (all passed)

- ✅ `decisions.yaml` summary = actual data (282/240/…/by_category sums to 282)
- ✅ `dspy_trainer.py --dry-run` tier 49/5/21 (note: GOLD-B expands to 5 dspy.Examples from 3 golden entries due to 1:N)
- ✅ `dspy_trainer.py --dry-run --split random` 51/11/13
- ✅ `recall_measure.py` runs on probe output (recall 0.019 — expected, probe didn't sample golden principles)
- ✅ `ruff` clean on 3 new files; YAML valid
- ✅ providers import cleanly (OMLX→Qwen3-Coder, Ollama→bge-m3)
