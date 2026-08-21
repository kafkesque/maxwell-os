"""
pipeline_paths.py — All paths from config/pipeline_config.yaml. Env vars override.
Each stage/{run_id}/ is self-contained: output + checkpoint + log + meta.
Stage N reads from Stage N-1/{run_id}/.
"""
import os as _os
from pathlib import Path

import yaml

# D2182: Use with-statement to close file handle (was unclosed — Maxwell R2 finding)
_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as _f:
    _CFG = yaml.safe_load(_f)
def _env(k, d): return _os.environ.get(f"MAXWELL_{k.upper()}", str(d))

PROJECT_ROOT = Path(_os.environ.get("MAXWELL_PIPELINE_ROOT", str(Path(__file__).resolve().parent.parent)))

def _rid():
    if not hasattr(_rid,"v"): _rid.v = _env("run_id", _CFG["run"]["default_id"])  # type: ignore
    return _rid.v  # type: ignore
def get_run_id(): return _rid()

# ── Stage dirs ─────────────────────────────────────────────────────────
S0=_CFG["stages"]["stage0_convert"]; S1=_CFG["stages"]["stage1_chunk"]
S13=_CFG["stages"]["stage1_3_prefilter"]; S15=_CFG["stages"]["stage1_5_embed"]
S2=_CFG["stages"]["stage2_extract"]; S4=_CFG["stages"]["stage4_merge"]; S5=_CFG["stages"]["stage5_verify"]  # D2120: Stage 3 removed
S6=_CFG["stages"]["stage6_commit"]

def _sdir(name): return PROJECT_ROOT / name
S0_DIR=_sdir(S0); S1_DIR=_sdir(S1); S13_DIR=_sdir(S13); S15_DIR=_sdir(S15)
S2_DIR=_sdir(S2); S4_DIR=_sdir(S4); S5_DIR=_sdir(S5); S6_DIR=_sdir(S6)  # D2177: S3_DIR removed (dead, D2120)

# ── Self-contained stage paths: {stage}/{run_id}/{file} ─────────────────
def _sp(stage_dir, file_key):
    p = stage_dir / _rid() / _CFG["stage_files"][file_key]
    p.parent.mkdir(parents=True, exist_ok=True); return p

STAGE1_OUTPUT       = _sp(S1_DIR, "stage1")
STAGE2_OUTPUT       = _sp(S2_DIR, "stage2")
# D2177: STAGE3_OUTPUT/STAGE3_QUALITY removed (Stage 3 dead, D2120)
STAGE4_OUTPUT       = _sp(S4_DIR, "stage4")
STAGE5_OUTPUT       = _sp(S5_DIR, "stage5")
STAGE5_HUMAN_REVIEW = _sp(S5_DIR, "stage5_human_review")
STAGE6_DB           = _sp(S6_DIR, "stage6_db")
STAGE6_PARQUET      = _sp(S6_DIR, "stage6_parquet")

# ── Checkpoints/logs/meta — nested inside each stage/{run_id}/ ───────────
def _ckpt(stage_dir, n):
    p = stage_dir / _rid() / _CFG["stage_files"]["checkpoint"]
    p.parent.mkdir(parents=True, exist_ok=True); return p

STAGE0_CHECKPOINT=_ckpt(S0_DIR,0); STAGE1_CHECKPOINT=_ckpt(S1_DIR,1); STAGE2_CHECKPOINT=_ckpt(S2_DIR,2)
# D2177: STAGE3_CHECKPOINT removed (Stage 3 dead, D2120)
STAGE4_CHECKPOINT=_ckpt(S4_DIR,4); STAGE5_CHECKPOINT=_ckpt(S5_DIR,5)
STAGE6_CHECKPOINT=_ckpt(S6_DIR,6)
# D2120: Stage 3 removed. 8 stages (0-2, 4-6).
# D2211: Scoped by run_id for cross-run isolation (was flat S2_DIR)
STAGE2_SINGLETON_OUTPUT = S2_DIR / _rid() / "singleton_fbs.jsonl"   # D2176: singleton FB integration
STAGE2_PROBE_CACHE      = S2_DIR / _rid() / "probe_targets.jsonl"   # D2xxx: resumable probe cache (crash-safe)

STAGE_CHECKPOINTS={0:STAGE0_CHECKPOINT,1:STAGE1_CHECKPOINT,2:STAGE2_CHECKPOINT,4:STAGE4_CHECKPOINT,5:STAGE5_CHECKPOINT,6:STAGE6_CHECKPOINT}

def stage_log(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["log"]
def stage_meta(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["meta"]

# ── Source books ───────────────────────────────────────────────────────
BOOKS_DIR = PROJECT_ROOT / _CFG["books_dir"]
_epub_cfg = _CFG.get("source_epub_dir") or ""
_pdf_cfg = _CFG.get("source_pdf_dir") or ""
SOURCE_EPUB_DIR = Path(_env("source_epub_dir", _epub_cfg) or str(BOOKS_DIR / "epub"))
SOURCE_PDF_DIR = Path(_env("source_pdf_dir", _pdf_cfg) or str(BOOKS_DIR / "pdf"))

# ── Global ─────────────────────────────────────────────────────────────
GLOBAL_LOG = PROJECT_ROOT / _CFG["global_log"]
ARCHIVE_DIR = PROJECT_ROOT / _CFG["archive_dir"]

# ── Services ───────────────────────────────────────────────────────────
OLLAMA_HOST=_env("ollama_host",_CFG["services"]["ollama"]["host"]); OLLAMA_PORT=int(_env("ollama_port",_CFG["services"]["ollama"]["port"]))
OMLX_HOST=_env("omlx_host",_CFG["services"]["omlx"]["host"]); OMLX_PORT=int(_env("omlx_port",_CFG["services"]["omlx"]["port"]))
OLLAMA_URL=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"; OMLX_URL=f"http://{OMLX_HOST}:{OMLX_PORT}"
OMLX_API_KEY=_env("omlx_api_key",_CFG["services"]["omlx"]["api_key"])

# ── Service-level tuning (T0.2, T0.4) ────────────────────────────────
OMLX_DEFAULT_TIMEOUT = int(_CFG.get("services", {}).get("omlx", {}).get("default_timeout", 180))
OMLX_MAX_RETRIES = int(_CFG.get("services", {}).get("omlx", {}).get("max_retries", 3))
OMLX_RETRY_DELAY = int(_CFG.get("services", {}).get("omlx", {}).get("retry_delay", 5))
OMLX_COLD_RELOAD_DELAY = int(_CFG.get("services", {}).get("omlx", {}).get("cold_reload_delay", 45))  # D2301: reasoning-model cold reload wait
# D2187: OMLX circuit breaker (P1-3) — config-driven, no hardcoding
OMLX_CB_ENABLED = bool(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_enabled", True))
OMLX_CB_FAILURE_THRESHOLD = int(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_failure_threshold", 5))
OMLX_CB_COOLDOWN_SECONDS = float(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_cooldown_seconds", 60))
OLLAMA_EMBED_MAX_CHARS = int(_CFG.get("services", {}).get("ollama", {}).get("embed_max_chars", 4000))
OLLAMA_BATCH_SIZE = int(_CFG.get("services", {}).get("ollama", {}).get("batch_size", 100))
OLLAMA_EMBED_TIMEOUT = int(_CFG.get("services", {}).get("ollama", {}).get("embed_timeout", 60))  # D2348: config-driven (BUG-105)
OLLAMA_EMBED_KEEP_ALIVE = _CFG.get("services", {}).get("ollama", {}).get("embed_keep_alive", -1)  # D2348: pin in VRAM (BUG-105)

# ── Models ─────────────────────────────────────────────────────────────
GEN_MODEL=_env("gen_model",_CFG["models"]["generator"]["model"]); GEN_PROVIDER=_CFG["models"]["generator"]["provider"]
GEN_TEMPERATURE=_CFG["models"]["generator"]["temperature"]; GEN_MAX_TOKENS=_CFG["models"]["generator"]["max_tokens"]
VERIFY_MODEL=_env("verify_model",_CFG["models"]["verifier"]["model"]); VERIFY_PROVIDER=_CFG["models"]["verifier"]["provider"]
VERIFY_TEMPERATURE=_CFG["models"]["verifier"]["temperature"]
# D2249/BUG-074: GPT-OSS reasoning models burn max_tokens on CoT. Config-driven prefix + token budget.
VERIFY_REASONING_OFF_PREFIX=_CFG["models"]["verifier"].get("reasoning_off_prefix", "")
VERIFY_REASONING_OFF_MODELS=set(_CFG["models"]["verifier"].get("reasoning_off_models", []))  # D2249/C12: no hardcoded names
# D2359: oMLX silently drops top-level reasoning_effort/enable_thinking (pydantic extra='ignore').
# Correct levers are chat_template_kwargs (dict) + thinking_budget (int), both oMLX-native.
VERIFY_CHAT_TEMPLATE_KWARGS=_CFG["models"]["verifier"].get("chat_template_kwargs", None) or {}
VERIFY_THINKING_BUDGET=_CFG["models"]["verifier"].get("thinking_budget", None)  # merged CRIBS call (D2359/X8 candidate)
VERIFY_DEPTH_THINKING_BUDGET=_CFG["models"]["verifier"].get("depth_thinking_budget", None)  # focused depth call (D2367/BUG-132)
VERIFY_MAX_TOKENS=int(_CFG["models"]["verifier"].get("max_tokens", 1024))
VERIFY_MODEL_V2=_env("verify_model_v2",_CFG["models"]["verifier_v2"]["model"])  # D2264: cross-family verifier (Phi-4-mini)
EMBED_MODEL=_env("embed_model",_CFG["models"]["embeddings"]["model"]); EMBED_PROVIDER=_CFG["models"]["embeddings"]["provider"]

# ── Settings ───────────────────────────────────────────────────────────
SCHEMA_VERSION=_CFG["pipeline"]["schema_version"]; PIPELINE_COMMIT=_CFG["pipeline"]["commit"]
TAXONOMY_VERSION=_CFG["pipeline"]["taxonomy_version"]; MAX_DOMAINS_PER_FB=_CFG["pipeline"]["max_domains_per_fb"]
CHUNK_SIZE_WORDS=_CFG["pipeline"]["chunk_size_words"]; CHUNK_OVERLAP_WORDS=_CFG["pipeline"]["chunk_overlap_words"]
MIN_CHUNK_WORDS=int(_CFG.get("pipeline", {}).get("min_chunk_words", 10))              # T1.1: preserve short aphoristic principles
ENHANCE_MIN_HEADER_GAP_CHARS=int(_CFG.get("pipeline", {}).get("enhance_min_header_gap_chars", 3000))  # T1.2: min chars between headers
# D2183: HDBSCAN ghost config removed (D2120/D2183). Retained as 0 for backward compat only.
# No pipeline stage imports this — safe to remove entirely in v3.2.
BORP_MIN_SOURCES=int(_env("borp_min_sources",_CFG["pipeline"]["borp_min_sources"])); SMOKE_BOOK_LIMIT=int(_CFG["pipeline"]["smoke_book_limit"])
S0_MAX_FAILED_RATIO=float(_CFG.get("stage0", {}).get("max_failed_ratio", 0.0))  # D2326: fail-closed ingestion tolerance
INTENT_TOP_K_RATIO=float(_env("intent_top_k",_CFG["pipeline"]["intent_top_k_ratio"]))
INTENT_THRESHOLD=float(_env("intent_threshold",_CFG["pipeline"]["intent_threshold"]))

# ── Stage 2 settings (D2080: Gate-Fix + Evidence + Routing) ────────────
S2_BATCH_SIZE=int(_CFG["stage2"]["batch_size"])
S2_MINHASH_THRESHOLD=float(_CFG["stage2"]["minhash_threshold"])
S2_MINHASH_NUM_PERM=int(_CFG["stage2"]["minhash_num_perm"])
S2_GOLDEN_PATH=_CFG["stage2"]["golden_path"]
S2_GOLDEN_POSITIVE=int(_CFG["stage2"]["golden_positive"])
S2_GOLDEN_NEGATIVE=int(_CFG["stage2"]["golden_negative"])
S2_GOLDEN_MAX=int(_CFG["stage2"]["golden_max_examples"])
S2_GOLDEN_INJECT=_CFG["stage2"].get("golden_inject_enabled", False)
S2_GOLDEN_SEED=int(_CFG["stage2"].get("golden_seed", 42))  # D2377: deterministic stratified few-shot seed
# BUG-152 (2026-08-20): balanced single-source/singleton golden (all 5 roles + negatives).
S2_GOLDEN_SINGLE_SOURCE_PATH=_CFG["stage2"].get("golden_single_source_path")
S2_GOLDEN_SINGLE_SOURCE_INJECT=bool(_CFG["stage2"].get("golden_single_source_inject_enabled", False))
S2_GOLDEN_SINGLE_SOURCE_NEGATIVE=int(_CFG["stage2"].get("golden_single_source_negative", 2))
S2_GOLDEN_SINGLE_SOURCE_MAX=int(_CFG["stage2"].get("golden_single_source_max", 7))
S2_GATE_ENABLED=bool(_CFG["stage2"]["gate_enabled"])
S2_GATE_STRICT=bool(_CFG["stage2"]["gate_strict"])
S2_EVIDENCE_TRACKING=bool(_CFG["stage2"]["evidence_tracking"])
S2_HIGH_COHESION_THRESHOLD=float(_CFG.get("stage2", {}).get("high_cohesion_threshold", 0.90))  # C12
S2_MED_COHESION_THRESHOLD=float(_CFG.get("stage2", {}).get("med_cohesion_threshold", 0.75))    # C12
S2_SOURCE_BOOK_MATCH=_CFG["stage2"]["source_book_match"]
S2_OMLX_RETRY=int(_CFG["stage2"]["omlx_retry_attempts"])
S2_GEN_MAX_TOKENS=int(_CFG.get("stage2", {}).get("gen_max_tokens", 3072))  # D2381: S2 output budget (was hardcoded 2048)
S2_GEN_MAX_TOKENS_RETRY=int(_CFG.get("stage2", {}).get("gen_max_tokens_retry", 4096))  # D2381: JSON-failure fallback budget
S2_BATCH_POSITION_MONITOR=bool(_CFG["stage2"]["batch_position_monitor"])
S2_MAX_CLUSTER_SAMPLES=int(_CFG.get("stage2", {}).get("max_cluster_samples", 15))       # T0.1
S2_MAX_PROBE_SAMPLES=int(_CFG.get("stage2", {}).get("max_probe_samples", 15))           # T0.1
S2_MAX_PROBE_PER_BOOK=int(_CFG.get("stage2", {}).get("max_probe_per_book", 2))          # D2357 (was literal MAX_PER_BOOK=2)
S2_MAX_WORKERS=int(_CFG.get("stage2", {}).get("max_workers", 3))                     # T0.2 (C12)
S2_SINGLETON_BATCH_SIZE=int(_CFG.get("stage2", {}).get("singleton_batch_size", 4))                 # D2xxx: batched singleton extraction (option-1 speedup)
S2_SINGLETON_BATCH_MAX_TOKENS_PER_ITEM=int(_CFG.get("stage2", {}).get("singleton_batch_max_tokens_per_item", 1000))
S2_SPLIT_KMEANS_RANDOM_STATE=int(_CFG.get("stage2", {}).get("split_probe_kmeans_random_state", 42))  # T0.1
S2_SPLIT_PROBE_ENABLED=bool(_CFG.get("stage2", {}).get("split_probe_enabled", True))     # D2163: gate master switch
S2_SPLIT_PROBE_MIN_SIZE=int(_CFG.get("stage2", {}).get("split_probe_min_size", 20))      # D2163: min cluster size for gate
S2_SPLIT_PROBE_MAX_COHESION=float(_CFG.get("stage2", {}).get("split_probe_max_cohesion", 0.85))  # D2163: max cohesion for gate
S2_MAX_FAILED_RATIO=float(_CFG.get("stage2", {}).get("max_failed_ratio", 0.0))  # D2331: fail-closed cluster-extraction tolerance
S2_ROUTE_VALUES=frozenset(_CFG.get("stage2", {}).get("route_values", ["FB", "NULL"]))  # D2323/C12: S2 route gate
S2_EXTRACTION_TYPE_DOMINANCE_WARN_RATIO=float(_CFG.get("stage2", {}).get("extraction_type_dominance_warn_ratio", 0.95))  # D2376: over-claim canary
WATCHDOG_INTERVAL_SECS=int(_CFG.get("watchdog", {}).get("interval_secs", 60))  # D2384: S2 watchdog poll interval
WATCHDOG_STALL_CHECKS=int(_CFG.get("watchdog", {}).get("stall_checks", 3))  # D2384: stall polls before flagging
WATCHDOG_CAUSAL_WARN_RATIO=float(_CFG.get("watchdog", {}).get("causal_warn_ratio", 0.5))  # D2384: causal drift warn
WATCHDOG_CAUSAL_HALT_RATIO=float(_CFG.get("watchdog", {}).get("causal_halt_ratio", 0.9))  # D2384: causal bias halt
# D2304: DSPy optimized-program persistence path (C12). Was hardcoded /tmp/dspy_mipro_optimized.json.
# NOTE: the `s2` key (lowercase) holds DSPy training settings; `stage2` holds pipeline extraction settings.
_dspy_program_raw = _CFG.get("s2", {}).get("dspy_program_path", "data/dspy_mipro_optimized.json")
_dspy_program_p = Path(str(_dspy_program_raw))
DSPY_PROGRAM_PATH = _dspy_program_p if _dspy_program_p.is_absolute() else PROJECT_ROOT / _dspy_program_p

# ── Stage 1.3 settings (D2080: Regex pre-filter) ────────────────────────
S13_MIN_LEN=int(_CFG["stage1_3"]["min_len"]); S13_CITE_DENSITY=float(_CFG["stage1_3"]["cite_density"]); S13_ENABLED=bool(_CFG["stage1_3"]["enabled"])

# ── Stage 3: REMOVED (D2120) — D2178: dead constant purged ─────────────

# ── Stage 4 settings (D2082: Type-aware routing) ───────────────────────
S4_DEDUP_COSINE_THRESHOLD = float(_CFG.get("stage4", {}).get("dedup_cosine_threshold", 0.92))       # D2231: C12 (was hardcoded)
S4_SEMANTIC_NEAR_THRESHOLD = float(_CFG.get("stage4", {}).get("semantic_near_threshold", 0.80))     # D2231: C12 (was hardcoded)
S4_PT_OUTPUT=_CFG["stage4"]["process_template_output"]
S4_PI_OUTPUT=_CFG["stage4"]["process_instance_output"]
S4_GE_OUTPUT=_CFG["stage4"]["growth_edge_output"]
S4_TI_OUTPUT=_CFG["stage4"]["tool_instruction_output"]
S4_MAX_PRINCIPLES=int(_CFG["stage4"]["max_principles_per_cluster"])
# BUG-075/D2247: Depth split into SHORT focused prompt (proven 62.5% vs 38% long combined).
S4_DEPTH_FOCUSED_CLASSIFICATION=bool(_CFG.get("stage4", {}).get("depth_focused_classification", True))
S4_DEPTH_MAX_TOKENS=int(_CFG.get("stage4", {}).get("depth_max_tokens", 1024))  # D2351/BUG-109: 1024 (was 512) — reasoning model needs room to finish CoT + answer
S4_DEPTH_BATCH_SIZE=int(_CFG.get("stage4", {}).get("depth_batch_size", 4))      # D2354: batched focused depth
# D2354 FrugalGPT cascade: GPT-OSS does CRIBS/classification, a cheap model does depth only.
S4_DEPTH_FRUGAL_ENABLED=bool(_CFG.get("stage4", {}).get("depth_frugal_enabled", False))
S4_DEPTH_MODEL=str(_CFG.get("stage4", {}).get("depth_model", "gemma-4-E4B-it-MLX-4bit"))
S4_DEPTH_FALLBACK_DEPTH=str(_CFG.get("stage4", {}).get("depth_fallback_depth", "domain"))
S4_MAX_FAILED_RATIO=float(_CFG.get("stage4", {}).get("max_failed_ratio", 0.0))  # D2338: fail-closed merge
FB_NAME_MAX_WORDS=int(_CFG.get("stage4", {}).get("fb_name_max_words", 8))  # BUG-149: C12 — name word cap (was hardcoded 5 in normalize_fb_name)
S4_CHECKPOINT_INTERVAL=int(_CFG.get("stage4", {}).get("checkpoint_interval", 5))  # D2370: intra-stage incremental checkpoint cadence
# D2364/C12 (X7): signal sets from config (was hardcoded literals in stage4_merge.py / stage4_merged_call.py)
S4_CONTEXT_SIGNALS=_CFG.get("stage4", {}).get("context_signals", {})        # {context_key: [domain signals]}
S4_TEMPORAL_SIGNALS=_CFG.get("stage4", {}).get("temporal_signals", {})      # {timeless|contemporary: [keywords]}
S4_DIFFICULTY_MAP=dict(_CFG.get("stage4", {}).get("difficulty_map", {}))    # D2410: {depth|domain_single|domain_multi: difficulty} (C12)
S4_UNIVERSAL_SIGNALS=_CFG.get("stage4", {}).get("universal_signals", [])    # [name/mechanism substrings]
S6_MAX_FAILED_RATIO=float(_CFG.get("stage6", {}).get("max_failed_ratio", 0.0))  # D2338: fail-closed commit

# ── Stage 5 settings (D2083: Type-aware BORP) ──────────────────────────
S5_BORP_BYPASS_TYPES=list(_CFG["stage5"]["borp_bypass_types"])
S5_FACTSCORE_ENABLED=bool(_CFG["stage5"]["factscore_enabled"])
# D2216 (2026-08-09): DeBERTa FEVER primary. ModernBERT is fallback.
# DeBERTa FEVER: 5.8× more discriminative than ModernBERT on convergent FBs.
# FEVER + ANLI training = purpose-built for claim-evidence verification.
# See governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md
S5_NLI_MODEL=_CFG.get("stage5", {}).get("nli_model", "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli")  # D2298: DeBERTa-v3-large sole verifier
S5_NLI_MODEL_FALLBACK=_CFG.get("stage5", {}).get("nli_model_fallback", "")  # D2298: fallback removed (was ModernBERT-base-nli)
S5_NLI_MODEL_LARGE=_CFG["models"]["nli_large"]  # D2298: DeBERTa-v3-large (435M) sole NLI verifier
# S5_NLI_MODEL_CROSS removed (D2298): RoBERTa-large added zero signal on paraphrase evidence (D2227).
S5_NLI_ENTAILMENT_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_entailment_threshold", 0.5))  # D2231: fallback matches config
S5_NLI_PASS_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_pass_threshold", 0.6))  # D2231: fallback matches config
S5_NLI_MARGINAL_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_marginal_threshold", 0.3))  # D2231: fallback matches config
S5_NLI_MAX_PREMISE_CHARS=int(_CFG.get("stage5", {}).get("nli_max_premise_chars", 256))  # D2321: premise(evidence) truncation for NLI pairing
S5_NLI_MAX_HYPOTHESIS_CHARS=int(_CFG.get("stage5", {}).get("nli_max_hypothesis_chars", 256))  # D2321: hypothesis(definition) truncation
# D2310: Confidence weights — NLI is a binary gate, not a score component (C12 config-driven).
S5_CONF_MECH_WEIGHT=float(_CFG.get("stage5", {}).get("confidence", {}).get("mechanism_weight", 0.35))
S5_CONF_ENRICH_WEIGHT=float(_CFG.get("stage5", {}).get("confidence", {}).get("enrichment_weight", 0.25))
S5_CONF_ISOR_WEIGHT=float(_CFG.get("stage5", {}).get("confidence", {}).get("isor_weight", 0.40))
S5_QUARANTINE_CONF_CAP=float(_CFG.get("stage5", {}).get("confidence", {}).get("quarantine_cap", 0.25))
S5_HUMAN_REVIEW_ISOR=str(_CFG.get("stage5", {}).get("confidence", {}).get("human_review_isor_rating", "strong"))
S5_CHECKPOINT_INTERVAL=int(_CFG.get("stage5", {}).get("checkpoint_interval", 50))  # D2409: intra-stage incremental checkpoint cadence (FBs)

# ── NLI threshold sanity check (D2185: T1.4 — catch misconfigured thresholds) ──
def _validate_nli_thresholds():
    """Warn if NLI thresholds are misordered or out of range."""
    issues = []
    for name, val in [("nli_marginal", S5_NLI_MARGINAL_THRESHOLD),
                       ("nli_entailment", S5_NLI_ENTAILMENT_THRESHOLD),
                       ("nli_pass", S5_NLI_PASS_THRESHOLD)]:
        if not (0 <= val <= 1):
            issues.append(f"  {name}={val} is out of range [0,1]")
    # D2293: Single-threshold mode — all thresholds equal is valid for DeBERTa-only architecture
    _single_threshold = (S5_NLI_MARGINAL_THRESHOLD == S5_NLI_ENTAILMENT_THRESHOLD == S5_NLI_PASS_THRESHOLD)
    if not _single_threshold:
        if S5_NLI_MARGINAL_THRESHOLD >= S5_NLI_ENTAILMENT_THRESHOLD:
            issues.append(f"  marginal ({S5_NLI_MARGINAL_THRESHOLD}) >= entailment ({S5_NLI_ENTAILMENT_THRESHOLD}) — should be lower")
        if S5_NLI_ENTAILMENT_THRESHOLD >= S5_NLI_PASS_THRESHOLD:
            issues.append(f"  entailment ({S5_NLI_ENTAILMENT_THRESHOLD}) >= pass ({S5_NLI_PASS_THRESHOLD}) — should be lower")
    if issues:
        msg = "NLI threshold misconfiguration:\n" + "\n".join(issues)
        msg += f"\n   Expected: 0 ≤ marginal({S5_NLI_MARGINAL_THRESHOLD}) < entailment({S5_NLI_ENTAILMENT_THRESHOLD}) < pass({S5_NLI_PASS_THRESHOLD}) ≤ 1"
        raise ValueError(f"FATAL: {msg}")
_validate_nli_thresholds()
S6_OKF_EXPORT_ENABLED=bool(_CFG.get("stage6", {}).get("okf_export_enabled", True))  # D2120

# ── Stage 4.5 (F1/D2400): post-S4 enrichment — orphan-field producers ──
# prerequisite_fbs / contradicts_fbs / procedural_skill are schema-declared and
# committed by S6 but had NO producer (F1 finding). This enrichment is a
# SEPARATE post-S4 stage — NOT inline-S4 (the ~39h bottleneck) and NOT S6
# (persistence-only). Gated behind stage4_5.enabled (default false for T1.1).
STAGE4_5_CHECKPOINT = S4_DIR / _rid() / "checkpoint_enriched.jsonl"
S4_5_ENABLED = bool(_CFG.get("stage4_5", {}).get("enabled", False))
S4_5_MODEL = str(_CFG.get("stage4_5", {}).get("model") or VERIFY_MODEL)
S4_5_PROCEDURAL_ENABLED = bool(_CFG.get("stage4_5", {}).get("procedural_skill_enabled", True))
S4_5_EDGE_ENABLED = bool(_CFG.get("stage4_5", {}).get("edge_enabled", True))
S4_5_EDGE_CANDIDATE_THRESHOLD = float(_CFG.get("stage4_5", {}).get("edge_candidate_threshold", S4_SEMANTIC_NEAR_THRESHOLD))
S4_5_EDGE_MAX_CANDIDATES_PER_FB = int(_CFG.get("stage4_5", {}).get("edge_max_candidates_per_fb", 10))
S4_5_EDGE_MAX_TOKENS = int(_CFG.get("stage4_5", {}).get("edge_max_tokens", 512))
S4_5_PROCEDURAL_MAX_TOKENS = int(_CFG.get("stage4_5", {}).get("procedural_skill_max_tokens", 256))
S4_5_MAX_FAILED_RATIO = float(_CFG.get("stage4_5", {}).get("max_failed_ratio", 0.01))
S4_5_CHECKPOINT_INTERVAL = int(_CFG.get("stage4_5", {}).get("checkpoint_interval", 5))

# ── Reliability settings (D2231: C12 compliance) ──────────────────────
RELIABILITY_STABLE_THRESHOLD = float(_CFG.get("reliability", {}).get("stable_threshold", 0.85))
RELIABILITY_WATCH_THRESHOLD = float(_CFG.get("reliability", {}).get("watch_threshold", 0.50))
RELIABILITY_GARBAGE_THRESHOLD = float(_CFG.get("reliability", {}).get("garbage_threshold", 0.20))

# ── Taxonomy thresholds (D2231: C12 compliance) ───────────────────────
TAXONOMY_FLOOD_THRESHOLD = float(_CFG.get("taxonomy", {}).get("flood_threshold_ratio", 0.20))
TAXONOMY_REPLACEMENT_THRESHOLD = float(_CFG.get("taxonomy", {}).get("replacement_threshold_ratio", 1.1))
TAXONOMY_EMERGING_FREQ = int(_CFG.get("taxonomy", {}).get("emerging_freq_threshold", 10))
TAXONOMY_MAX_DOMAINS = int(_CFG.get("taxonomy", {}).get("max_domains", 35))      # D2378: canonical cap (was hardcoded 25 in taxonomy_manager.py)
TAXONOMY_MAX_DISCIPLINES = int(_CFG.get("taxonomy", {}).get("max_disciplines", 72))  # D2378: canonical cap (was hardcoded 47)

# ── Retrieve settings (D2231: C12 compliance) ─────────────────────────
RETRIEVE_CONFIDENCE_THRESHOLD = float(_CFG.get("retrieval_eval", {}).get("confidence_threshold", 0.85))

# ── Coverage settings (T0.3) ─────────────────────────────────────────
COVERAGE_THRESHOLD = float(_CFG.get("coverage", {}).get("threshold", 0.50))
COVERAGE_FLAG_FRACTION = float(_CFG.get("coverage", {}).get("flag_fraction", 0.30))

# ── E2E validation thresholds (T1.3) ─────────────────────────────────
E2E_BORP_MIN_SOURCES = int(_CFG.get("e2e", {}).get("borp_min_sources", 2))
E2E_MIN_PASS_RATE = float(_CFG.get("e2e", {}).get("min_pass_rate", 0.80))
E2E_MIN_FBS = int(_CFG.get("e2e", {}).get("min_fbs", 30))
E2E_CONVERGENT_RATIO = float(_CFG.get("e2e", {}).get("convergent_ratio", 0.25))

# ── Stage 1.5 settings (D2094: FAISS cluster) ─────────────────────────
S15_FAISS_THRESHOLD = float(_CFG.get("stage1_5", {}).get("faiss_threshold", 0.75))
S15_MIN_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("min_cluster_size", 2))
S15_MAX_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("max_cluster_size", 500))
S15_MIN_SOURCE_DIVERSITY = int(_CFG.get("stage1_5", {}).get("min_source_diversity", 2))
S15_NEIGHBOR_K = int(_CFG.get("stage1_5", {}).get("neighbor_k", 150))
S15_EMBED_MODEL = _CFG.get("stage1_5", {}).get("embed_model", "bge-m3")
S15_EMBED_DIM = int(_CFG.get("stage1_5", {}).get("embed_dim", 512))  # D2181: Matryoshka 512d (E7)
S15_EMBED_BACKEND = _CFG.get("stage1_5", {}).get("embed_backend", "ollama")  # D2190: Ollama stable (MPS deadlocks on bge-m3)
S15_EMBED_MODEL_HF = _CFG.get("stage1_5", {}).get("embed_model_hf", "BAAI/bge-m3")  # D2181: unified
S15_EMBED_CHUNK_SIZE = int(_CFG.get("stage1_5", {}).get("embed_chunk_size", 20000))  # D2189: chunked embedding
S15_EMBED_BATCH_SIZE = int(_CFG.get("stage1_5", {}).get("embed_batch_size", 64))  # D2190: MPS forward batch
S15_MAX_EMBED_DROP_RATE = float(_CFG.get("stage1_5", {}).get("max_embed_drop_rate", 0.005))  # D2275: embed quality gate
S15_EMBED_CHECKPOINT_ENABLED = bool(_CFG.get("stage1_5", {}).get("embed_checkpoint_enabled", True))  # D2409: crash-safe incremental embedding cache

# ── Stage 6 settings (D2084) ────────────────────────────────────────────
S6_COMMIT_NON_FB=bool(_CFG["stage6"]["commit_non_fb_types"])

def ensure_dirs():
    # D2178: S3_DIR removed (D2120/D2177) — no longer referenced
    for d in [S0_DIR,S1_DIR,S13_DIR,S15_DIR,S2_DIR,S4_DIR,S5_DIR,S6_DIR,ARCHIVE_DIR,BOOKS_DIR]:
        d.mkdir(parents=True,exist_ok=True)


def check_books_source() -> tuple[bool, str]:
    """D2178/D2180: Validate book source directories — EPUB/PDF for S0, MD for S1.

    Two-phase check:
    1. If MD files already exist in BOOKS_DIR, S0 is already done.
    2. If no MDs, check for EPUB/PDF source files to convert.

    Returns (ok, message) where ok=False means no books found at all.
    Called by preflight/smoke to catch empty source before pipeline runs.
    """
    # Phase 1: Check for already-converted MD files (S0 done, ready for S1)
    md_files: list[Path] = list(BOOKS_DIR.glob("**/*.md")) if BOOKS_DIR.exists() else []
    if md_files:
        domains: dict[str, int] = {}
        for f in md_files:
            d = f.parent.name
            domains[d] = domains.get(d, 0) + 1
        domain_summary = ", ".join(f"{d}: {c}" for d, c in sorted(domains.items()))
        return True, (
            f"✅ {len(md_files)} MD files across {len(domains)} domains (S0 done)\n"
            f"   {domain_summary}"
        )

    # Phase 2: No MDs — check for EPUB/PDF source files
    epub_dir = SOURCE_EPUB_DIR.resolve() if SOURCE_EPUB_DIR else None
    pdf_dir = SOURCE_PDF_DIR.resolve() if SOURCE_PDF_DIR else None

    epubs: list[Path] = []
    pdfs: list[Path] = []

    if epub_dir and epub_dir.exists():
        epubs = list(epub_dir.glob("**/*.epub"))
    if pdf_dir and pdf_dir.exists():
        pdfs = list(pdf_dir.glob("**/*.pdf"))

    total = len(epubs) + len(pdfs)
    if total == 0:
        return False, (
            f"No books found (no MDs, no EPUBs, no PDFs):\n"
            f"  MD dir: {BOOKS_DIR} ({'exists' if BOOKS_DIR.exists() else 'MISSING'})\n"
            f"  EPUB:   {epub_dir} ({'exists' if epub_dir and epub_dir.exists() else 'MISSING'})\n"
            f"  PDF:    {pdf_dir} ({'exists' if pdf_dir and pdf_dir.exists() else 'MISSING'})\n"
            f"Place source EPUB/PDF in 1.sources/ or set SOURCE_EPUB_DIR/SOURCE_PDF_DIR."
        )
    return True, f"✅ {len(epubs)} EPUBs + {len(pdfs)} PDFs = {total} source books (needs S0)"


def check_pipeline_state() -> str:
    """D2180: Comprehensive pipeline state report for preflight.

    Reports stage-by-stage checkpoint status, record counts,
    embedding model consistency, and bloat detection.
    Used by `just preflight` for self-learning and debugging.
    """
    lines: list[str] = []
    stages: list[tuple[str, Path, str]] = [
        ("S0  (convert)",   S0_DIR / get_run_id(), "MD files"),
        ("S1  (chunk)",     S1_DIR / get_run_id(), "segments"),
        ("S1.3(prefilter)", S13_DIR / get_run_id(), "filtered segments"),
        ("S1.5(embed)",     S15_DIR / get_run_id(), "clusters"),
        ("S2  (extract)",   S2_DIR / get_run_id(), "FBs"),
        ("S4  (merge)",     S4_DIR / get_run_id(), "classified FBs"),
        ("S5  (verify)",    S5_DIR / get_run_id(), "verified FBs"),
        ("S6  (commit)",    S6_DIR / get_run_id(), "DB records"),
    ]

    any_done = False
    lines.append("Pipeline stage status:")
    for name, stage_dir, unit in stages:
        if not stage_dir.exists():
            lines.append(f"  ⬜ {name}: not run")
            continue
        checkpoints = list(stage_dir.glob("checkpoint*.jsonl"))
        if checkpoints:
            count = sum(1 for _ in open(checkpoints[0]))
            lines.append(f"  ✅ {name}: {count} {unit}")
            any_done = True
        else:
            segids = list(stage_dir.glob("*.segids"))
            if segids:
                lines.append(f"  ⚠️  {name}: segids only (partial)")
            else:
                lines.append(f"  ⬜ {name}: dir exists, no data")

    if not any_done:
        lines.append("  ⚠️  No stages have been run — run `just triad` to start")

    # Embedding model consistency check
    s15_model = _CFG.get("stage1_5", {}).get("embed_model_hf", "?")
    s15_dim = _CFG.get("stage1_5", {}).get("embed_dim", "?")
    s4_model = _CFG.get("models", {}).get("embeddings", {}).get("model", "?")
    if "bge-small" in str(s15_model).lower() and "bge-m3" in str(s4_model).lower():
        lines.append(f"  ⚠️  Embed model mismatch: S1.5={s15_model} ({s15_dim}d) vs S4={s4_model} (T1.2)")
    elif "bge-m3" in str(s15_model).lower() and "bge-m3" in str(s4_model).lower():
        lines.append("  ✅ Embed models aligned: both bge-m3")
    else:
        lines.append(f"  ℹ️  Embed: S1.5={s15_model} ({s15_dim}d), S4={s4_model}")

    # Version consistency
    ver = _CFG.get("pipeline", {}).get("schema_version", "?")
    commit = _CFG.get("pipeline", {}).get("commit", "?")
    lines.append(f"  ℹ️  Schema v{ver} | Commit: {commit}")

    return "\n".join(lines)

VERSION="3.0.0"; BUILD_DATE="2026-07-26"

# ── Paths (D2115: C12 compliant — from config, not hardcoded) ──────────
_PATHS = _CFG.get("paths", {})
CHECKPOINT_DIR = PROJECT_ROOT / _PATHS.get("checkpoint_dir", "knowledge pipeline/checkpoints")
DB_PATH = PROJECT_ROOT / _PATHS.get("db_path", "knowledge pipeline/maxwell.db")
PARQUET_DIR = PROJECT_ROOT / _PATHS.get("parquet_dir", "knowledge pipeline/parquet")
DATA_DIR = PROJECT_ROOT / _PATHS.get("data_dir", "knowledge pipeline")
# D2184: Dynamic OMLX binary resolution (was hardcoded /Applications/...)
_omlx_bin_cfg = _CFG["services"]["omlx"].get("bin")
if _omlx_bin_cfg and Path(_omlx_bin_cfg).exists():
    OMLX_BIN: str = _omlx_bin_cfg
else:
    import shutil as _shutil
    _found = _shutil.which("omlx-cli")
    if _found:
        OMLX_BIN = _found
    else:
        # Platform fallbacks
        _candidates = [
            "/Applications/oMLX.app/Contents/MacOS/omlx-cli",
            "/usr/local/bin/omlx-cli",
            str(Path.home() / ".local/bin/omlx-cli"),
        ]
        _found = None
        for _c in _candidates:
            if Path(_c).exists():
                _found = _c
                break
        OMLX_BIN = _found or ""  # Empty → watchdog will fail with clear diagnostic

# ── Stage 1.5 checkpoints (D2094: self-contained stage dir, D2134 fix) ──
def _s15_path(filename: str) -> Path:
    """Create a path within S15_DIR/{run_id}/ — self-contained like all other stages."""
    p = S15_DIR / _rid() / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

STAGE1_5_CHECKPOINT = _s15_path("checkpoint.jsonl")
STAGE1_5_SINGLETONS = _s15_path("singletons.jsonl")

# ── Smoke test config (D2120) ────────────────────────────────────────────
SMOKE_PLUMBING_SKIP_LLM = bool(_CFG.get("smoke", {}).get("plumbing", {}).get("skip_llm", True))
SMOKE_FAST_MODEL = _CFG.get("smoke", {}).get("fast", {}).get("fast_model", "Phi-4-mini-instruct-8bit")
SMOKE_FAST_SKIP_GEMMA = bool(_CFG.get("smoke", {}).get("fast", {}).get("skip_gemma_deep_check", True))
SMOKE_MAX_BOOKS = int(_CFG.get("smoke", {}).get("fast", {}).get("max_books", 3))
