# Forensic Audit — OMLX 0.7.0 + Goose 1.52.0 update (2026-10-02)

## Scope
Owner updated OMLX (`0.7.0.dev2` → `0.7.0` release, build 2987) and Goose (→ `1.52.0`).
Audit asks: (1) is the current config most suitable; (2) is there a better gpt-oss setup via
OMLX dedicated features; (3) do the new versions/settings improve latency/quality/cost; (4) do any
dependencies benefit from updates. This audit precedes ANY serious implementation (no break, cascade,
drift, blindspot, gap, conflict, bug, hidden failure, error leak, mismatch, bloat).

## Evidence gathered
- `omlx /health` → `{"status":"healthy","default_model":"Ornith-1.5-35B-A3B-REAP-19B","engine_pool":{"model_count":7,"loaded_count":1}}`
- `omlx /v1/models` (API-key auth) → 7 models: Phi-4-mini-8bit, Qwen3-Coder-30B-A3B-4bit, Qwen3.8-27B-4bit,
  gemma-4-E4B-4bit, gpt-oss-20b-MXFP4-Q8, Ornith-1.5-35B-A3B-REAP-19B, Ornith-1.5-9B-8bit
- `/Applications/oMLX.app/Contents/Info.plist` → `CFBundleShortVersionString = 0.7.0`, `CFBundleVersion = 2987`
- `pipeline/status.py` → `OMLX 0.7.0`, `Ollama 0.34.4`
- `config/pipeline_config.yaml` → `pinned_version: 0.7.0.dev2`, `mtp_enabled: false`, `min_version: 0.4.0`
- `~/.omlx/model_settings.json` gpt-oss → `mtp_enabled: false`, `dflash_enabled: false`, `specprefill_enabled: false`,
  `turboquant_kv_enabled: false`, `quant_variant: None`
- `requirements.lock` (uv) → `transformers==5.14.1`, `sentence-transformers==5.7.0`, `torch==2.13.0`
- `goose --version` → `1.52.0`

## Findings

### F1 — OMLX version drift: config pin stale (FIXED this audit)
`pinned_version: 0.7.0.dev2` (D-291 rationale: dev4 failed to start with API-key auth disabled) is superseded by
the now-running, healthy `0.7.0` release. `pinned_version` has NO runtime consumer — `monitor_stacks.py::_verdict`
gates on `min_version` (0.4.0) only; the pin is a spec/intent field. Syncing to `0.7.0` is a zero-risk C12 correctness
repair (no cascade).

### F2 — MTP / speculative / DFlash for gpt-oss: NOT applicable (no change)
gpt-oss-20b is a DENSE transformer with NO MTP heads (MTP is Qwen3/Qwen3.8 arch). D-293 already measured MTP
NEUTRAL (0.98x) on Qwen3-Coder; mlx-dspark#38 + D-332 measured speculative decode as a NET LOSS on M1 Max; and
D-2768 ruled Splash (DFlash2 drafts are per-architecture) does NOT cover gpt-oss. The live settings are already
`mtp_enabled: false`, `dflash_enabled: false`, `specprefill_enabled: false`. **Verdict: no better OMLX dedicated
MTP/speculative setup exists for gpt-oss; current config is correct.**

### F3 — The genuine gpt-oss latency lever: `turboquant_kv_enabled` (MEASURE-gated, NOT applied)
S4 discipline/depth classification is long-context and bandwidth-bound; KV-cache quantization
(`turboquant_kv_enabled`, currently `false`) is the top bandwidth lever, and `quant_variant: Q4` is present in
settings but not symlinked (needs download). Both are `measure`-class in `config/omlx_m1_best_config.yaml` — D-332
adopts ONLY on a measured WIN on THIS hardware. Neither is auto-applied by `scripts/omlx_apply_best_m1_config.py`.
**Next: a controlled gpt-oss S4-classify latency A/B (turboquant_kv off vs on) before any adoption.** Do NOT toggle
blindly (would reload OMLX and evict the loaded model — cascade risk).

### F4 — Goose 1.52.0: no Maxwell drift (no change)
`~/.config/goose/config.yaml` is the agent harness config, not the pipeline runtime. Extensions: `code_execution`
enabled (token-saving), `summarize`/`orchestrator`/`memory`/`chatrecall`/`apps` disabled. No Maxwell coupling.
No config change required.

### F5 — Dependency drift (BLINDSPOT — smoke-test flagged, not yet a bug)
`requirements.txt` uses lower-bound-only pins (`transformers>=4.40`, `sentence-transformers>=2.2`); the uv lock has
`transformers==5.14.1` and `sentence-transformers==5.7.0` — MAJOR-version jumps over the declared floor. Pipeline
consumers: `AutoModelForSequenceClassification`/`AutoTokenizer`/`pipeline("zero-shot-classification")` (stage5_verify.py,
rerank.py, student_classifier.py, bakeoff_typed_decision.py) and `SentenceTransformer(..., device="mps")`
(stage1_5_embed_cluster.py, stage2_extract.py, coverage_check.py). These are NOT smoke-tested under the 5.x major
versions. Separately, `requests 2.32.5` emits `RequestsDependencyWarning` (urllib3 2.7.0 / chardet 7.4.3 /
charset_normalizer 3.4.9 "doesn't match a supported version") — loud, not silent, indicating a partial `pip` upgrade.
**No dependency change is made here (avoids cascade); the S5-NLI + S1.5-embedding smoke test is queued as a TASK.**

## No-break / no-cascade / no-drift assessment
- Pin sync (F1) is spec-only → no runtime cascade.
- No MTP/speculative change (F2) → already correct.
- No dependency change (F5) → flagged only, avoids a partial-upgrade cascade.
- OMLX healthy, 7 models known / 1 loaded; pipeline runner NOT active (`.pipeline_runner.lock` PID 60572 is dead/stale).

## Ruling
Pin `pinned_version` → `0.7.0` (D-2772). MTP/speculative for gpt-oss = settled NO. `turboquant_kv` = MEASURE A/B
pending. Dependency smoke-test = TASK (not yet a bug — no confirmed failure).
