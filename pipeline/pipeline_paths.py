"""
pipeline_paths.py — v2.0 Single source of truth for all I/O paths.
===============================================================
Authority: CONSTITUTION.md §7
Every pipeline script imports from here. NEVER hardcode paths inline.

v2.0: Simplified. Flat data/ structure. No knowledge pipeline/ tree.
"""

from pathlib import Path
import os as _os

# ── Project root (derived, not hardcoded) ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Top-level directories ─────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
PIPELINE_DIR = PROJECT_ROOT / "pipeline"
BOOKS_DIR = Path(_os.environ.get("MAXWELL_BOOKS_DIR", str(PROJECT_ROOT / "books")))
TEMP_DIR = PROJECT_ROOT / "temp"
RESEARCH_DIR = PROJECT_ROOT / "research"
HANDOFF_DIR = PROJECT_ROOT / "handoff"
GOVERNANCE_DIR = PROJECT_ROOT / "governance"

# ── Data subdirectories ───────────────────────────────────────────────────
DB_PATH = DATA_DIR / "maxwell.db"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
LOGS_DIR = DATA_DIR / "logs"
PARQUET_DIR = DATA_DIR / "parquet"

# ── Pipeline checkpoint paths (one JSONL per stage) ───────────────────────
STAGE0_CHECKPOINT = CHECKPOINT_DIR / "stage0_convert.jsonl"
STAGE1_CHECKPOINT = CHECKPOINT_DIR / "stage1_chunk.jsonl"
STAGE2_CHECKPOINT = CHECKPOINT_DIR / "stage2_extract.jsonl"
STAGE3_CHECKPOINT = CHECKPOINT_DIR / "stage3_cluster.jsonl"
STAGE4_CHECKPOINT = CHECKPOINT_DIR / "stage4_merge.jsonl"
STAGE5_CHECKPOINT = CHECKPOINT_DIR / "stage5_verify.jsonl"
STAGE6_CHECKPOINT = CHECKPOINT_DIR / "stage6_commit.jsonl"

STAGE_CHECKPOINTS = {
    0: STAGE0_CHECKPOINT,
    1: STAGE1_CHECKPOINT,
    2: STAGE2_CHECKPOINT,
    3: STAGE3_CHECKPOINT,
    4: STAGE4_CHECKPOINT,
    5: STAGE5_CHECKPOINT,
    6: STAGE6_CHECKPOINT,
}

# ── Service hosts and ports ────────────────────────────────────────────────
OLLAMA_HOST = _os.environ.get("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(_os.environ.get("OLLAMA_PORT", "11434"))
OMLX_HOST = _os.environ.get("OMLX_HOST", "localhost")
OMLX_PORT = int(_os.environ.get("OMLX_PORT", "11435"))

OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
OMLX_URL = f"http://{OMLX_HOST}:{OMLX_PORT}"

# ── API keys ────────────────────────────────────────────────────────────────
OMLX_API_KEY = _os.environ.get("OMLX_API_KEY", "sk-maxwell-local")

# ── Model configuration (from CONSTITUTION.md §2.2) ────────────────────────
GEN_MODEL = _os.environ.get("MAXWELL_GEN_MODEL", "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
GEN_PROVIDER = _os.environ.get("MAXWELL_GEN_PROVIDER", "omlx")
GEN_TEMPERATURE = 0.0  # R7 — enforced at call site
GEN_MAX_TOKENS = int(_os.environ.get("MAXWELL_GEN_MAX_TOKENS", "4096"))

VERIFY_MODEL = _os.environ.get("MAXWELL_VERIFY_MODEL", "Phi-4-mini-instruct-8bit")
VERIFY_PROVIDER = _os.environ.get("MAXWELL_VERIFY_PROVIDER", "omlx")
VERIFY_TEMPERATURE = 0.0

EMBED_MODEL = _os.environ.get("MAXWELL_EMBED_MODEL", "nomic-embed-text")
EMBED_PROVIDER = _os.environ.get("MAXWELL_EMBED_PROVIDER", "ollama")

# Minimum OMLX version required (checked by preflight)
OMLX_MIN_VERSION = _os.environ.get("MAXWELL_OMLX_MIN_VERSION", "0.4.0")

# OMLX binary path (configurable for non-brew installs)
OMLX_BIN = _os.environ.get("MAXWELL_OMLX_BIN", "/opt/homebrew/opt/omlx/bin/omlx")

# ── Pipeline settings ──────────────────────────────────────────────────────
SCHEMA_VERSION = "2.0"
PIPELINE_COMMIT = "v2.0-init"  # Updated on git commit
TAXONOMY_VERSION = "v5.0"

# D150: Max 5 domains per FB
MAX_DOMAINS_PER_FB = 5

# Chunking
CHUNK_SIZE_WORDS = 300
CHUNK_OVERLAP_WORDS = 50

# Clustering
CLUSTER_MIN_SIZE = 3
CLUSTER_MIN_SAMPLES = 2
HDBSCAN_MIN_CLUSTER_SIZE = 3

# Verification
BORP_MIN_SOURCES = 2  # Minimum distinct sources for a valid FB

# ── Convenience: ensure dirs exist ─────────────────────────────────────────
def ensure_dirs():
    """Create all required directories if they don't exist."""
    for d in [DATA_DIR, CHECKPOINT_DIR, LOGS_DIR, PARQUET_DIR, TEMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── Version stamp ──────────────────────────────────────────────────────────
VERSION = "2.0.0"
BUILD_DATE = "2026-07-18"
