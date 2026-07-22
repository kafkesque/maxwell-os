"""
pipeline_paths.py — All paths from config/pipeline_config.yaml. Env vars override.
Each stage/{run_id}/ is self-contained: output + checkpoint + log + meta.
Stage N reads from Stage N-1/{run_id}/.
"""
from pathlib import Path
import os as _os, yaml

_CFG = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"))
def _env(k, d): return _os.environ.get(f"MAXWELL_{k.upper()}", str(d))

PROJECT_ROOT = Path(_os.environ.get("MAXWELL_PIPELINE_ROOT", str(Path(__file__).resolve().parent.parent)))

def _rid():
    if not hasattr(_rid,"v"): _rid.v = _env("run_id", _CFG["run"]["default_id"])  # type: ignore
    return _rid.v  # type: ignore
def get_run_id(): return _rid()

# ── Stage dirs ─────────────────────────────────────────────────────────
S0=_CFG["stages"]["stage0_convert"]; S1=_CFG["stages"]["stage1_chunk"]; S2=_CFG["stages"]["stage2_extract"]
S3=_CFG["stages"]["stage3_cluster"]; S4=_CFG["stages"]["stage4_merge"]; S5=_CFG["stages"]["stage5_verify"]
S6=_CFG["stages"]["stage6_commit"]

def _sdir(name): return PROJECT_ROOT / name
S0_DIR=_sdir(S0); S1_DIR=_sdir(S1); S2_DIR=_sdir(S2); S3_DIR=_sdir(S3)
S4_DIR=_sdir(S4); S5_DIR=_sdir(S5); S6_DIR=_sdir(S6)

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
STAGE_CHECKPOINTS={0:STAGE0_CHECKPOINT,1:STAGE1_CHECKPOINT,2:STAGE2_CHECKPOINT,3:STAGE3_CHECKPOINT,4:STAGE4_CHECKPOINT,5:STAGE5_CHECKPOINT,6:STAGE6_CHECKPOINT}

def stage_log(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["log"]
def stage_meta(stage_dir): return stage_dir / _rid() / _CFG["stage_files"]["meta"]

# ── Source books ───────────────────────────────────────────────────────
BOOKS_DIR = PROJECT_ROOT / _CFG["books_dir"]

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
EMBED_MODEL=_env("embed_model",_CFG["models"]["embeddings"]["model"]); EMBED_PROVIDER=_CFG["models"]["embeddings"]["provider"]

# ── Settings ───────────────────────────────────────────────────────────
SCHEMA_VERSION=_CFG["pipeline"]["schema_version"]; PIPELINE_COMMIT=_CFG["pipeline"]["commit"]
TAXONOMY_VERSION=_CFG["pipeline"]["taxonomy_version"]; MAX_DOMAINS_PER_FB=_CFG["pipeline"]["max_domains_per_fb"]
CHUNK_SIZE_WORDS=_CFG["pipeline"]["chunk_size_words"]; CHUNK_OVERLAP_WORDS=_CFG["pipeline"]["chunk_overlap_words"]
HDBSCAN_MIN_CLUSTER_SIZE=_CFG["pipeline"]["hdbscan_min_cluster_size"]; BORP_MIN_SOURCES=_CFG["pipeline"]["borp_min_sources"]
INTENT_TOP_K_RATIO=float(_env("intent_top_k",_CFG["pipeline"]["intent_top_k_ratio"]))
INTENT_THRESHOLD=float(_env("intent_threshold",_CFG["pipeline"]["intent_threshold"]))

def ensure_dirs():
    for d in [S0_DIR,S1_DIR,S2_DIR,S3_DIR,S4_DIR,S5_DIR,S6_DIR,ARCHIVE_DIR,BOOKS_DIR]:
        d.mkdir(parents=True,exist_ok=True)

VERSION="2.1.0"; BUILD_DATE="2026-07-21"

# ── Legacy aliases (required by pipeline stage imports) ────────────────
CHECKPOINT_DIR = PROJECT_ROOT / "knowledge pipeline" / "checkpoints"  # flat checkpoint dir (stages 0-4)
DB_PATH = PROJECT_ROOT / "knowledge pipeline" / "maxwell.db"           # canonical DB (stage6, query, retrieve)
PARQUET_DIR = PROJECT_ROOT / "knowledge pipeline" / "parquet"        # Parquet snapshots (stage6 --export-only)
DATA_DIR = PROJECT_ROOT / "knowledge pipeline"                       # data directory (stage6 DB path)
OMLX_BIN = _CFG["services"]["omlx"]["bin"]                             # omlx binary path
