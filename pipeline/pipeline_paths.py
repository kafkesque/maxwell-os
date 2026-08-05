"""
pipeline_paths.py — All paths from config/pipeline_config.yaml. Env vars override.
Each stage/{run_id}/ is self-contained: output + checkpoint + log + meta.
Stage N reads from Stage N-1/{run_id}/.
"""
import os as _os
from pathlib import Path

import yaml

_CFG = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"))
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
S2_DIR=_sdir(S2); S3_DIR=_sdir(S2); S4_DIR=_sdir(S4); S5_DIR=_sdir(S5); S6_DIR=_sdir(S6)  # D2120: S3 removed, S3_DIR→S2 fallback

# ── Self-contained stage paths: {stage}/{run_id}/{file} ─────────────────
def _sp(stage_dir, file_key):
    p = stage_dir / _rid() / _CFG["stage_files"][file_key]
    p.parent.mkdir(parents=True, exist_ok=True); return p

STAGE1_OUTPUT       = _sp(S1_DIR, "stage1")
STAGE2_OUTPUT       = _sp(S2_DIR, "stage2")
STAGE3_OUTPUT       = _sp(S3_DIR, "stage3")
STAGE3_QUALITY      = _sp(S3_DIR, "stage3_quality")
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
STAGE3_CHECKPOINT=_ckpt(S3_DIR,3); STAGE4_CHECKPOINT=_ckpt(S4_DIR,4); STAGE5_CHECKPOINT=_ckpt(S5_DIR,5)
STAGE6_CHECKPOINT=_ckpt(S6_DIR,6)
# D2120: Stage 3 removed. 8 stages (0-2, 4-6).
STAGE_CHECKPOINTS={0:STAGE0_CHECKPOINT,1:STAGE1_CHECKPOINT,2:STAGE2_CHECKPOINT,4:STAGE4_CHECKPOINT,5:STAGE5_CHECKPOINT,6:STAGE6_CHECKPOINT}

def stage_log(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["log"]
def stage_meta(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["meta"]

# ── Source books ───────────────────────────────────────────────────────
BOOKS_DIR = PROJECT_ROOT / _CFG["books_dir"]
SOURCE_EPUB_DIR = Path(_env("source_epub_dir", _CFG.get("source_epub_dir", str(BOOKS_DIR))))
SOURCE_PDF_DIR = Path(_env("source_pdf_dir", _CFG.get("source_pdf_dir", str(BOOKS_DIR))))

# ── Global ─────────────────────────────────────────────────────────────
GLOBAL_LOG = PROJECT_ROOT / _CFG["global_log"]
ARCHIVE_DIR = PROJECT_ROOT / _CFG["archive_dir"]

# ── Services ───────────────────────────────────────────────────────────
OLLAMA_HOST=_env("ollama_host",_CFG["services"]["ollama"]["host"]); OLLAMA_PORT=int(_env("ollama_port",_CFG["services"]["ollama"]["port"]))
OMLX_HOST=_env("omlx_host",_CFG["services"]["omlx"]["host"]); OMLX_PORT=int(_env("omlx_port",_CFG["services"]["omlx"]["port"]))
OLLAMA_URL=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"; OMLX_URL=f"http://{OMLX_HOST}:{OMLX_PORT}"
OMLX_API_KEY=_env("omlx_api_key",_CFG["services"]["omlx"]["api_key"])

# ── Models ─────────────────────────────────────────────────────────────
GEN_MODEL=_env("gen_model",_CFG["models"]["generator"]["model"]); GEN_PROVIDER=_CFG["models"]["generator"]["provider"]
GEN_TEMPERATURE=_CFG["models"]["generator"]["temperature"]; GEN_MAX_TOKENS=_CFG["models"]["generator"]["max_tokens"]
VERIFY_MODEL=_env("verify_model",_CFG["models"]["verifier"]["model"]); VERIFY_PROVIDER=_CFG["models"]["verifier"]["provider"]
VERIFY_TEMPERATURE=_CFG["models"]["verifier"]["temperature"]
VERIFY_MODEL_V2=_env("verify_model_v2",_CFG["models"]["verifier_v2"]["model"])  # D2069: cross-family (Gemma)
EMBED_MODEL=_env("embed_model",_CFG["models"]["embeddings"]["model"]); EMBED_PROVIDER=_CFG["models"]["embeddings"]["provider"]

# ── Settings ───────────────────────────────────────────────────────────
SCHEMA_VERSION=_CFG["pipeline"]["schema_version"]; PIPELINE_COMMIT=_CFG["pipeline"]["commit"]
TAXONOMY_VERSION=_CFG["pipeline"]["taxonomy_version"]; MAX_DOMAINS_PER_FB=_CFG["pipeline"]["max_domains_per_fb"]
CHUNK_SIZE_WORDS=_CFG["pipeline"]["chunk_size_words"]; CHUNK_OVERLAP_WORDS=_CFG["pipeline"]["chunk_overlap_words"]
HDBSCAN_MIN_CLUSTER_SIZE=_CFG["pipeline"]["hdbscan_min_cluster_size"]; BORP_MIN_SOURCES=int(_env("borp_min_sources",_CFG["pipeline"]["borp_min_sources"])); SMOKE_BOOK_LIMIT=int(_CFG["pipeline"]["smoke_book_limit"])
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
S2_GATE_ENABLED=bool(_CFG["stage2"]["gate_enabled"])
S2_GATE_STRICT=bool(_CFG["stage2"]["gate_strict"])
S2_EVIDENCE_TRACKING=bool(_CFG["stage2"]["evidence_tracking"])
S2_SOURCE_BOOK_MATCH=_CFG["stage2"]["source_book_match"]
S2_OMLX_RETRY=int(_CFG["stage2"]["omlx_retry_attempts"])
S2_BATCH_POSITION_MONITOR=bool(_CFG["stage2"]["batch_position_monitor"])

# ── Stage 1.3 settings (D2080: Regex pre-filter) ────────────────────────
S13_MIN_LEN=int(_CFG["stage1_3"]["min_len"]); S13_CITE_DENSITY=float(_CFG["stage1_3"]["cite_density"]); S13_ENABLED=bool(_CFG["stage1_3"]["enabled"])

# ── Stage 3 settings (D2081: Bug fixes) ────────────────────────────────
S3_UMAP_N_NEIGHBORS=int(_CFG["stage3"]["umap_n_neighbors"])
S3_UMAP_N_COMPONENTS=int(_CFG["stage3"]["umap_n_components"])
S3_UMAP_MIN_DIST=float(_CFG["stage3"]["umap_min_dist"])
S3_UMAP_METRIC=_CFG["stage3"]["umap_metric"]
S3_ALLOW_SINGLE_CLUSTER=bool(_CFG["stage3"]["hdbscan_allow_single_cluster"])
S3_KEEP_NOISE=bool(_CFG["stage3"]["keep_noise"])
S3_NOISE_OUTPUT=_CFG["stage3"]["noise_output"]
S3_NORMALIZE_CENTROID=bool(_CFG["stage3"]["normalize_centroid"])

# ── Stage 4 settings (D2082: Type-aware routing) ───────────────────────
S4_PT_OUTPUT=_CFG["stage4"]["process_template_output"]
S4_PI_OUTPUT=_CFG["stage4"]["process_instance_output"]
S4_GE_OUTPUT=_CFG["stage4"]["growth_edge_output"]
S4_TI_OUTPUT=_CFG["stage4"]["tool_instruction_output"]
S4_MAX_PRINCIPLES=int(_CFG["stage4"]["max_principles_per_cluster"])

# ── Stage 5 settings (D2083: Type-aware BORP) ──────────────────────────
S5_BORP_BYPASS_TYPES=list(_CFG["stage5"]["borp_bypass_types"])
S5_FACTSCORE_ENABLED=bool(_CFG["stage5"]["factscore_enabled"])
S5_NLI_MODEL=_CFG.get("stage5", {}).get("nli_model", "tasksource/ModernBERT-base-nli")  # D2119
S5_NLI_MODEL_FALLBACK=_CFG.get("stage5", {}).get("nli_model_fallback", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")  # D2119
S5_NLI_ENTAILMENT_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_entailment_threshold", 0.6))  # D2119
S5_NLI_PASS_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_pass_threshold", 0.8))  # D2155: configurable
S5_NLI_MARGINAL_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_marginal_threshold", 0.5))  # D2155: configurable
S6_OKF_EXPORT_ENABLED=bool(_CFG.get("stage6", {}).get("okf_export_enabled", True))  # D2120

# ── Stage 1.5 settings (D2094: FAISS cluster) ─────────────────────────
S15_FAISS_THRESHOLD = float(_CFG.get("stage1_5", {}).get("faiss_threshold", 0.75))
S15_MIN_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("min_cluster_size", 2))
S15_MAX_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("max_cluster_size", 500))
S15_MIN_SOURCE_DIVERSITY = int(_CFG.get("stage1_5", {}).get("min_source_diversity", 2))
S15_NEIGHBOR_K = int(_CFG.get("stage1_5", {}).get("neighbor_k", 150))
S15_EMBED_MODEL = _CFG.get("stage1_5", {}).get("embed_model", "bge-m3")
S15_EMBED_DIM = int(_CFG.get("stage1_5", {}).get("embed_dim", 512))  # E7: Matryoshka truncation
S15_EMBED_BACKEND = _CFG.get("stage1_5", {}).get("embed_backend", "ollama")
S15_EMBED_MODEL_HF = _CFG.get("stage1_5", {}).get("embed_model_hf", "BAAI/bge-small-en-v1.5")

# ── Stage 6 settings (D2084) ────────────────────────────────────────────
S6_COMMIT_NON_FB=bool(_CFG["stage6"]["commit_non_fb_types"])

def ensure_dirs():
    for d in [S0_DIR,S1_DIR,S13_DIR,S15_DIR,S2_DIR,S3_DIR,S4_DIR,S5_DIR,S6_DIR,ARCHIVE_DIR,BOOKS_DIR]:
        d.mkdir(parents=True,exist_ok=True)

VERSION="3.0.0"; BUILD_DATE="2026-07-26"

# ── Paths (D2115: C12 compliant — from config, not hardcoded) ──────────
_PATHS = _CFG.get("paths", {})
CHECKPOINT_DIR = PROJECT_ROOT / _PATHS.get("checkpoint_dir", "knowledge pipeline/checkpoints")
DB_PATH = PROJECT_ROOT / _PATHS.get("db_path", "knowledge pipeline/maxwell.db")
PARQUET_DIR = PROJECT_ROOT / _PATHS.get("parquet_dir", "knowledge pipeline/parquet")
DATA_DIR = PROJECT_ROOT / _PATHS.get("data_dir", "knowledge pipeline")
OMLX_BIN = _CFG["services"]["omlx"]["bin"]                             # omlx binary path

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
