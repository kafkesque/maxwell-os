"""
pipeline_paths.py — All paths from config/pipeline_config.yaml. Env vars override.
Each stage/{run_id}/ is self-contained: output + checkpoint + log + meta.
Stage N reads from Stage N-1/{run_id}/.

EXCEPTION (BUG-598, D-2721): Stage 1.3 (S13) is a MUTATING pre-filter, not a self-contained
stage. It rewrites Stage 1/{run_id}/checkpoint.jsonl in place and writes only a completion
flag to S13/{run_id}/checkpoint.jsonl. Downstream S1.5 reads the MUTATED S1 checkpoint, not S13.
"""
import os as _os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

# D2182: Use with-statement to close file handle (was unclosed — Maxwell R2 finding)
_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as _f:
    _CFG = yaml.safe_load(_f)
# D-2982: the `where=` provenance of a loud read is DERIVED from the path constant - a hand-written
# second copy of a path is one more value with two homes (C12/C20).
_CFG_HOME = str(_CFG_PATH.relative_to(_CFG_PATH.parent.parent))


class MissingDeclaredKey(KeyError):
    """A DECLARED config value was absent or unusable at read time - a missing value is an ERROR (C16)."""


def required(doc: Any, *path: str, where: str) -> Any:
    """Return doc[path...] exactly, or fail closed naming the home (D-2982 / C16 / D-2644).

    WHY THIS EXISTS. `receiver.get(key, <literal>)` moves a value's effective setting OUT of config and
    INTO code: a config miss stops being an error and becomes a silent fallback (BUG-504's class - the
    same class `_s6_axis_columns` below already refuses for stage6.s5_axis_columns, whose docstring states
    the rule this function generalises). The gate-bearing instances are worse than untidy, because they
    FAIL OPEN: an absent `serving` block silently emptied the golden-anchoring contract, an absent
    `dedup_gate` block silently disabled a commit gate, an absent `s5_owned_columns` list silently
    emptied a write-ownership contract, and an absent stage4 sidecar name silently made an audit read a
    DIFFERENT file set than the pipeline writes.

    This function cannot express a default - there is no `default` parameter to pass - so using it is the
    cheap way to comply, and only a cheap rule holds (D-2642: the value has ONE home).

    Args:
        doc: the parsed config document, or a declared block of it.
        path: the key path, one segment per positional argument.
        where: the home of the declaration (derive it from the config path constant, never hand-copy it).

    Raises:
        MissingDeclaredKey: a segment is absent. The message names the segment, the home and the remedy.
    """
    node: Any = doc
    for index, segment in enumerate(path):
        if not isinstance(node, Mapping) or segment not in node:
            walked = ".".join(path[: index + 1])
            raise MissingDeclaredKey(
                f"config-read: {where} declares no {walked} - a value read with a code default would move "
                "the setting out of config and into code (D-2644/C12), so this read is fail-closed (C16). "
                f"Declare {walked} in {where} and read it loudly (pipeline/pipeline_paths.required, D-2982)."
            )
        node = node[segment]
    return node


def required_mapping(doc: Any, *path: str, where: str) -> dict[str, Any]:
    """`required`, asserting the value is a MAPPING - an absent block must never read as {} (C16)."""
    value = required(doc, *path, where=where)
    if not isinstance(value, Mapping):
        raise MissingDeclaredKey(
            f"config-read: {where}#{'.'.join(path)} is a {type(value).__name__}, not a block - a block read "
            "that silently degrades to an empty mapping disables every rule underneath it (C16/D-2982)."
        )
    return dict(value)


def required_sequence(doc: Any, *path: str, where: str) -> list[Any]:
    """`required`, asserting the value is a SEQUENCE of items - a bare STRING is not one (C16).

    A str is iterable, so accepting it here would silently split a declared value into characters: the
    caller asks for a list of types and gets ['s','e','m',...]. That is the same fail-open shape in a
    different costume, so it is refused with the key named.
    """
    value = required(doc, *path, where=where)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise MissingDeclaredKey(
            f"config-read: {where}#{'.'.join(path)} is a {type(value).__name__}, not a list - a scalar here "
            "would be iterated as its own characters (C16/D-2982). Declare a YAML list."
        )
    return list(value)
def _env(k, d): return _os.environ.get(f"MAXWELL_{k.upper()}", str(d))

PROJECT_ROOT = Path(_os.environ.get("MAXWELL_PIPELINE_ROOT", str(Path(__file__).resolve().parent.parent)))

def _rid():
    if not hasattr(_rid,"v"): _rid.v = _env("run_id", _CFG["run"]["default_id"])  # type: ignore
    return _rid.v  # type: ignore
def get_run_id(): return _rid()

# ── D-2881: serving-layer canonical run ────────────────────────────────
# Single source of truth: config/anchor_family.yaml store_bridge.canonical_run
# (ratified D-2881). The serving layer (retrieve/query/status/MCP) must NEVER
# surface stale rows from non-canonical runs (t11/e2e/bug198_reinject) that share
# the same fbs table. Env override MAXWELL_CANONICAL_RUN; fallback run default_id.
def _canonical_run() -> str:
    env = _os.environ.get("MAXWELL_CANONICAL_RUN")
    if env:
        return env
    try:
        _anchor = PROJECT_ROOT / "config" / "anchor_family.yaml"
        with open(_anchor) as _af:
            _val = (yaml.safe_load(_af) or {}).get("store_bridge", {}).get("canonical_run")
        if _val:
            return str(_val)
    except Exception:
        pass  # anchor file may be absent in minimal contexts; fall back below
    return str(_CFG["run"]["default_id"])

CANONICAL_RUN: str = _canonical_run()

def canonical_run_clause(alias: str = "") -> str:
    """D-2881: SQL fragment pinning a serving query to the canonical run.

    Callers must append CANONICAL_RUN as the parameter for this clause.
    `alias` prefixes the column for JOINed queries (e.g. ``f.pipeline_run_id``).
    """
    return f"{alias}.pipeline_run_id = ?" if alias else "pipeline_run_id = ?"

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
OMLX_READ_TIMEOUT = int(_CFG.get("services", {}).get("omlx", {}).get("read_timeout", 60))  # BUG-224: per-read socket timeout — bounds a wedged/stalled server (decode collapse) that otherwise hangs beyond default_timeout
OMLX_WEDGE_RECOVERY_SLEEP = int(_CFG.get("services", {}).get("omlx", {}).get("wedge_recovery_sleep", 20))  # BUG-224: recovery sleep after a mid-response wedge (server needs 15-60s to recover)
OMLX_WALL_CLOCK_DEADLINE = int(_CFG.get("services", {}).get("omlx", {}).get("wall_clock_deadline_sec", 180))  # BUG-658: TOTAL wall-clock deadline per request — SSE keepalive resets the per-read timer, so a (connect, read) tuple alone can hang forever
# D2187: OMLX circuit breaker (P1-3) — config-driven, no hardcoding
OMLX_CB_ENABLED = bool(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_enabled", True))
OMLX_CB_FAILURE_THRESHOLD = int(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_failure_threshold", 5))
OMLX_CB_FAILURE_THRESHOLD_FLOOR = int(_CFG.get("services", {}).get("omlx", {}).get("circuit_breaker_failure_threshold_floor", 25))  # D2545: floor was hardcoded max(...,25)
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
RELABEL_MAX_WORKERS=int(_env("relabel_max_workers", _CFG.get("stage2", {}).get("relabel_max_workers", 4)))  # D2434: R1 relabel sweep parallelism
RELABEL_CROSS_FAMILY_MODEL=str(_CFG.get("stage2", {}).get("relabel_cross_family_model", ""))  # P1.3 (D2469): cross-family FLAG judge; "" = disabled
# BUG-263: OUTPUT budget for the FORM judge. call_omlx_json() returns [] rather than raising when a
# response is unparseable, and a Harmony reasoning model spends its budget on the reasoning pass
# before emitting content (measured: 64 -> 0c content, 256 -> 0c, 1024 -> JSON). 64 was hardcoded and
# guaranteed zero labels. Value lives in config (C12), not here.
RELABEL_JUDGE_MAX_TOKENS=int(_env("relabel_judge_max_tokens", _CFG.get("stage2", {}).get("relabel_judge_max_tokens", 1024)))
# BUG-262/263: tell a reasoning-off model to skip the reasoning pass, else the budget above is wasted.
RELABEL_APPLY_REASONING_OFF_PREFIX=str(_env("relabel_apply_reasoning_off_prefix", "1")).lower() in ("1", "true", "yes")
RELABEL_JUDGE_MIN_CONTENT_CHARS=int(_env("relabel_judge_min_content_chars", _CFG.get("stage2", {}).get("relabel_judge_min_content_chars", 2)))
RELABEL_REPORT_DIR=str(_CFG.get("stage2", {}).get("relabel_report_dir", "governance"))  # M2: run artifact dir

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


def _s0_budget(key: str) -> int:
    """Read ONE declared Stage-0 conversion budget value (BUG-897/D-3076).

    An absent or non-integer declaration is FATAL rather than defaulted: a budget that
    silently falls back to a number in the code is exactly the magic constant this
    config block exists to remove (C12/C20).
    """
    block = _CFG.get("stage0", {}).get("conversion_budget") or {}
    if key not in block:
        raise RuntimeError(
            f"FATAL: config/pipeline_config.yaml#stage0.conversion_budget.{key} is not declared — an absent "
            f"budget is refused, never defaulted (C12, BUG-897)"
        )
    try:
        value = int(block[key])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"FATAL: stage0.conversion_budget.{key}={block[key]!r} is not an integer (C12, BUG-897)"
        ) from exc
    if value <= 0:
        #: R5 review catch: a declared 0 was honoured literally, which turns every work into an instant timeout and
        #: reports it as `budget_expired` — a budget that permits NO work is a declaration that does not resolve.
        raise RuntimeError(
            f"FATAL: stage0.conversion_budget.{key}={value} is not a positive number of seconds (C12, BUG-897)"
        )
    return value


S0_BUDGET_BASIS=str(_CFG.get("stage0", {}).get("conversion_budget", {}).get("basis", ""))  # the signal the allowance derives from
S0_PANDOC_TIMEOUT_S=_s0_budget("pandoc_timeout_s")
S0_DOCLING_FLOOR_S=_s0_budget("docling_floor_s")
S0_DOCLING_PER_MB_S=_s0_budget("docling_per_mb_s")
S0_DOCLING_CEILING_S=_s0_budget("docling_ceiling_s")
S0_STAGE_TIMEOUT_S=_s0_budget("stage_timeout_s")
#: D-3034: a declaration must RESOLVE. The applier kills the whole Stage-0 subprocess at stage_timeout_s, so a
#: Docling ceiling at or above it would make the inner budget unreachable — the outer wall would speak instead, and
#: it speaks as `S0 could not be run`, which names neither the work nor the reason. Refused at import.
if S0_STAGE_TIMEOUT_S <= S0_DOCLING_CEILING_S:
    raise RuntimeError(
        f"FATAL: stage0.conversion_budget.stage_timeout_s={S0_STAGE_TIMEOUT_S} must EXCEED docling_ceiling_s="
        f"{S0_DOCLING_CEILING_S} — a ceiling the outer wall can never reach is a declaration with no referent (C12)"
    )
#: BUG-898: the failure vocabulary, declared (not invented in the converter). The meaning is what the owner reads.
S0_FAILURE_CLASSES={str(k): str(v) for k, v in (_CFG.get("stage0", {}).get("failure_classes") or {}).items()}
if not S0_FAILURE_CLASSES:
    raise RuntimeError(
        "FATAL: config/pipeline_config.yaml#stage0.failure_classes is empty — a failure that cannot be named is the "
        "tail again (C12/C16, BUG-898)"
    )


def _s0_artifact_rule() -> dict:
    """Read `config#stage0.artifact` — the DECLARED shape of an S0 artefact (BUG-918/D-3086).

    WHY THE SHAPE IS NOT THE ENGINE'S DEFAULT. Docling ships `--image-export-mode embedded`, so every PDF's
    figures are base64-inlined into the markdown. MEASURED 2026-10-18 on one 4.06 MB library work: 19.371 MB of
    markdown carrying 95 `data:image` blobs, versus 0.538 MB carrying none in `placeholder` mode with the same
    text. A default that multiplies an artefact by 36 is not a shape anyone chose, so it is declared here and
    refused at import when the declaration does not RESOLVE (D-3034): an unknown mode, a non-integer ceiling or
    a ceiling that permits nothing is a declaration with no referent.
    """
    block = _CFG.get("stage0", {}).get("artifact")
    if not isinstance(block, dict) or not block:
        raise RuntimeError(
            "FATAL: config/pipeline_config.yaml#stage0.artifact is not declared — the shape of an S0 artefact is a "
            "DECLARED fact, never the converter's default (C12, BUG-918)"
        )
    allowed_modes = {"placeholder", "embedded", "referenced"}
    mode = str(block.get("image_export_mode", "")).strip().lower()
    if mode not in allowed_modes:
        raise RuntimeError(
            f"FATAL: stage0.artifact.image_export_mode={block.get('image_export_mode')!r} is not one of "
            f"{sorted(allowed_modes)} (docling's own closed vocabulary; C12)"
        )
    out = {"image_export_mode": mode}
    for key, minimum in (("max_embedded_images", 0), ("max_artifact_mb", 1)):
        if key not in block:
            raise RuntimeError(
                f"FATAL: stage0.artifact.{key} is not declared — an absent ceiling is refused, never defaulted "
                f"(C12, BUG-918)"
            )
        try:
            value = int(block[key])
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"FATAL: stage0.artifact.{key}={block[key]!r} is not an integer (C12)") from exc
        if value < minimum:
            raise RuntimeError(
                f"FATAL: stage0.artifact.{key}={value} is below {minimum} — a ceiling that permits nothing is a "
                f"declaration with no referent (D-3034)"
            )
        out[key] = value
    return out


S0_ARTIFACT = _s0_artifact_rule()
S0_ARTIFACT_IMAGE_MODE: str = S0_ARTIFACT["image_export_mode"]
S0_ARTIFACT_MAX_EMBEDDED_IMAGES: int = S0_ARTIFACT["max_embedded_images"]
S0_ARTIFACT_MAX_MB: int = S0_ARTIFACT["max_artifact_mb"]
#: D-3034: the two classes the shape gate emits must EXIST in the declared vocabulary. A code path that can emit a
#: class name the register does not carry is the tail again — the reader gets a word nobody defined.
for _required_class in ("artifact_images_embedded", "artifact_oversize"):
    if _required_class not in S0_FAILURE_CLASSES:
        raise RuntimeError(
            f"FATAL: stage0.failure_classes is missing {_required_class!r} — the shape gate emits it, so the "
            f"vocabulary must carry it (C12/D-3034, BUG-918)"
        )


#: D-3077 — WHICH CONTAINERS THIS STAGE CAN OPEN, DECLARED, ONE LINE PER CONTAINER naming the reader that opens it.
#: The CODE owns which readers EXIST (pipeline/stage0_convert.py::_READERS, where each one is a function); the CONFIG
#: owns which container is read by which of them. Neither may name a reader the other has never heard of, and BOTH
#: directions are refused (stage0_convert.py, at import). MEASURED 2026-10-17: the three-item set literal that used to
#: live in that file is what produced 389 of 626 admission refusals the door could only call "a container the
#: conversion stage cannot read" — 99 .docx, 6 .mobi, 5 .rtf, 4 .pptx among them, all readable on this machine.
def _s0_container_map() -> dict[str, str]:
    """Read `config#stage0.containers` (extension -> reader id), fail-closed on an absent, empty or malformed block."""
    block = _CFG.get("stage0", {}).get("containers")
    if not isinstance(block, dict) or not block:
        raise RuntimeError(
            "FATAL: config/pipeline_config.yaml#stage0.containers is not declared — which containers this stage can "
            "open is a DECLARED fact, never an inference from a literal in code (C12, D-3077)"
        )
    mapping: dict[str, str] = {}
    for raw_ext, raw_reader in block.items():
        ext = str(raw_ext).strip().lower()
        reader = str(raw_reader).strip()
        if len(ext) < 2 or not ext.startswith("."):
            raise RuntimeError(
                f"FATAL: stage0.containers key {raw_ext!r} is not a dotted extension (the shape is '.epub')"
            )
        if not reader:
            raise RuntimeError(
                f"FATAL: stage0.containers[{ext}] names no reader — a container with no engine is exactly the silence "
                f"applied admission could not see through (C12, D-3077)"
            )
        mapping[ext] = reader
    return mapping


S0_CONTAINERS: dict[str, str] = _s0_container_map()
S0_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(S0_CONTAINERS)
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
S2_ACCEPT_CONDITIONAL=bool(_CFG.get("stage2", {}).get("accept_conditional_within_tolerance", False))  # BUG-609: advance when failures are within max_failed_ratio (deterministic failures never clear on re-run)
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
# BUG-397(b)/D-364: the fallback here used to be the literal "data/dspy_mipro_optimized.json" - a path that has
# never existed on disk - so NULLING the config key would not have fixed anything (C12: a hardcoded code default is
# the second defect). There is NO code-level default now: an unset key yields None and the consumer must refuse.
_dspy_program_raw = _CFG.get("s2", {}).get("dspy_program_path")
DSPY_PROGRAM_PATH: Path | None = None
if _dspy_program_raw:
    _dspy_program_p = Path(str(_dspy_program_raw))
    DSPY_PROGRAM_PATH = _dspy_program_p if _dspy_program_p.is_absolute() else PROJECT_ROOT / _dspy_program_p
S2_DSPY_ENABLED=bool(_CFG.get("s2", {}).get("dspy_enabled", False))  # D2482: gate DSPy extraction path in stage2 (default off)

# ── Stage 1.3 settings (D2080: Regex pre-filter) ────────────────────────
S13_MIN_LEN=int(_CFG["stage1_3"]["min_len"]); S13_CITE_DENSITY=float(_CFG["stage1_3"]["cite_density"]); S13_ENABLED=bool(_CFG["stage1_3"]["enabled"])

# ── Stage 3: REMOVED (D2120) — D2178: dead constant purged ─────────────

# ── Stage 4 settings (D2082: Type-aware routing) ───────────────────────
S4_DEDUP_COSINE_THRESHOLD = float(_CFG.get("stage4", {}).get("dedup_cosine_threshold", 0.92))       # D2231: C12 (was hardcoded)
S4_SEMANTIC_NEAR_THRESHOLD = float(_CFG.get("stage4", {}).get("semantic_near_threshold", 0.80))     # D2231: C12 (was hardcoded)
S4_RELATED_FBS_MAX_NEIGHBORS = int(_CFG.get("stage4", {}).get("related_fbs_max_neighbors", 20))       # BUG-188: per-FB related_fbs neighbor cap (was unbounded O(n²) → 32M edges → 2GB truncation)
S4_RELATED_FBS_EXCLUDE_DOMAINS = list(_CFG.get("stage4", {}).get("related_fbs_exclude_domains", ["emerging"]))  # BUG-188: fallback domains excluded from domain_overlap (shared fallback ≠ relationship)
S4_RELATED_FBS_EXCLUDE_DISCIPLINES = list(_CFG.get("stage4", {}).get("related_fbs_exclude_disciplines", ["emerging"]))  # BUG-194: fallback discipline excluded from discipline_overlap (shared placeholder ≠ relationship)
S4_PT_OUTPUT=_CFG["stage4"]["process_template_output"]
S4_PI_OUTPUT=_CFG["stage4"]["process_instance_output"]
S4_GE_OUTPUT=_CFG["stage4"]["growth_edge_output"]
S4_TI_OUTPUT=_CFG["stage4"]["tool_instruction_output"]
S4_QUARANTINE_OUTPUT=_CFG["stage4"]["quarantine_output"]
# D2454 (2026-08-27): config-driven S4 classification golden (config/golden/stage4_golden.yaml).
# Keys existed in pipeline_config.yaml since D2451 but were never consumed — wiring here.
S4_GOLDEN_PATH = _CFG.get("stage4", {}).get("golden_path", "config/golden/stage4_golden.yaml")
S4_GOLDEN_INJECT_ENABLED = bool(_CFG.get("stage4", {}).get("golden_inject_enabled", False))
S4_GOLDEN_MAX_EXAMPLES = int(_CFG.get("stage4", {}).get("golden_max_examples", 4))
# D-325 (2026-09-21): ruled boundary discriminators + default_home tie-breakers (D-324).
S4_BOUNDARY_INJECT_ENABLED = bool(_CFG.get("stage4", {}).get("boundary_inject_enabled", False))
S4_BOUNDARY_PATH = _CFG.get("stage4", {}).get("boundary_path", "config/boundary_discriminators.yaml")
# D-2773 (2026-10-02): closed 62-discipline menu injection (BUG-622 fix, MEASURE-gated).
S4_DISCIPLINE_CLOSED_MENU_ENABLED = bool(_CFG.get("stage4", {}).get("discipline_closed_menu_enabled", False))
S4_DISCIPLINE_NEGATIVE_EXEMPLARS_PATH = _CFG.get("stage4", {}).get("discipline_negative_exemplars_path", "config/golden/discipline_negative_exemplars.yaml")
# D-2814 (2026-10-05): definition-anchored closed menu (label + definition + explicit 'emerging').
# Replaces the free-generation discipline/domains instruction in the merged + direct S4 classify
# prompts. OFF by default; adopt only after R5 review + full-204 A/B (D-2767).
S4_DEFINITION_ANCHORED_MENU_ENABLED = bool(_CFG.get("stage4", {}).get("definition_anchored_menu_enabled", False))
# D-2814/BUG-630: curated same-axis fall-through crosswalk. When a raw label is canonical on the OPPOSITE
# axis, retry a declared SAME-axis home before abstaining (never coerces: only a curated key rescues).
S4_SAME_AXIS_FALLTHROUGH = _CFG.get("stage4", {}).get("same_axis_fallthrough", {}) or {}
S4_MAX_PRINCIPLES=int(_CFG["stage4"]["max_principles_per_cluster"])
# BUG-075/D2247: Depth split into SHORT focused prompt (proven 62.5% vs 38% long combined).
S4_DEPTH_FOCUSED_CLASSIFICATION=bool(_CFG.get("stage4", {}).get("depth_focused_classification", True))
S4_DEPTH_MAX_TOKENS=int(_CFG.get("stage4", {}).get("depth_max_tokens", 1024))  # D2351/BUG-109: 1024 (was 512) — reasoning model needs room to finish CoT + answer
S4_DEPTH_BATCH_SIZE=int(_CFG.get("stage4", {}).get("depth_batch_size", 4))      # D2354: batched focused depth
S4_DEPTH_BATCH_MAX_TOKENS=int(_CFG.get("stage4", {}).get("depth_batch_max_tokens", 2048))  # BUG-184: batch needs > single-FB headroom (truncation)
S4_DEPTH_BATCH_ENABLED=bool(_CFG.get("stage4", {}).get("depth_batch_enabled", False))  # D2477: wire D2354 batch depth into stage4 (quality-neutral — same short prompt, batched transport)
S4_DEPTH_PROMPT_VARIANT=str(_CFG.get("stage4", {}).get("depth_prompt_variant", "baseline"))  # D2483: BUG-185 goldilocks depth-prompt variant ("baseline" default = unchanged)
# D2354 FrugalGPT cascade: GPT-OSS does CRIBS/classification, a cheap model does depth only.
S4_DEPTH_FRUGAL_ENABLED=bool(_CFG.get("stage4", {}).get("depth_frugal_enabled", False))
_S4_DEPTH_MODEL_RAW = _CFG.get("stage4", {}).get("depth_model")  # BUG-403/405 Gate D: config-first, NO code default (the model it named is refuted, D2454->S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md)
S4_DEPTH_MODEL = str(_S4_DEPTH_MODEL_RAW) if _S4_DEPTH_MODEL_RAW else ""  # null/absent -> "" (UNSET), never the literal string "None"
S4_DEPTH_FALLBACK_DEPTH=str(_CFG.get("stage4", {}).get("depth_fallback_depth", "domain"))
# D2607 (C): LLM-hybrid student pre-classifier (ModernBERT student + gpt-oss fallback).
S4_STUDENT_PRECLASSIFIER_ENABLED=bool(_CFG.get("stage4", {}).get("student_preclassifier_enabled", False))
S4_STUDENT_PRECLASSIFIER_CHECKPOINT=str(_CFG.get("stage4", {}).get("student_preclassifier_checkpoint", "knowledge pipeline/classifier_modernbert_p5final"))
S4_STUDENT_PRECLASSIFIER_THRESHOLD=float(_CFG.get("stage4", {}).get("student_preclassifier_threshold", 0.35))
S4_STUDENT_PRECLASSIFIER_COARSE_THRESHOLD=float(_CFG.get("stage4", {}).get("student_preclassifier_coarse_threshold", 0.70))
S4_MAX_FAILED_RATIO=float(_CFG.get("stage4", {}).get("max_failed_ratio", 0.0))  # D2338: fail-closed merge
FB_NAME_MAX_WORDS=int(_CFG.get("stage4", {}).get("fb_name_max_words", 8))  # BUG-149: C12 — name word cap (was hardcoded 5 in normalize_fb_name)
S4_CHECKPOINT_INTERVAL=int(_CFG.get("stage4", {}).get("checkpoint_interval", 5))  # D2370: intra-stage incremental checkpoint cadence
# D2364/C12 (X7): signal sets from config (was hardcoded literals in stage4_merge.py / stage4_merged_call.py)
S4_CONTEXT_SIGNALS=_CFG.get("stage4", {}).get("context_signals", {})        # {context_key: [domain signals]}
S4_TEMPORAL_SIGNALS=_CFG.get("stage4", {}).get("temporal_signals", {})      # {timeless|contemporary: [keywords]}
S4_DIFFICULTY_MAP=dict(_CFG.get("stage4", {}).get("difficulty_map", {}))    # D2410: {depth|domain_single|domain_multi: difficulty} (C12)
S4_UNIVERSAL_SIGNALS=_CFG.get("stage4", {}).get("universal_signals", [])    # [name/mechanism substrings]
S6_MAX_FAILED_RATIO=float(_CFG.get("stage6", {}).get("max_failed_ratio", 0.0))  # D2338: fail-closed commit
# D-2933 (rule V): verification-scoped commit — write ONLY S5-owned provenance columns on an
# existing fb_id, so a stale S5 checkpoint can never regress a ratified S4-owned ontology label
# (BUG-709). C12: the scope and the column set live in config/pipeline_config.yaml:stage6.
# D-2982: read LOUDLY. The code defaults made the stage6 write scope and the write-ownership column set
# values with TWO homes, so the registry could be edited while this module silently kept the old rule -
# and an absent declaration read as "no S5-owned columns", i.e. a contract that empties itself (C16).
S6_COMMIT_SCOPE=str(required(_CFG, "stage6", "commit_scope", where=_CFG_HOME))
S6_S5_OWNED_COLUMNS=tuple(
    str(_column) for _column in required_sequence(_CFG, "stage6", "s5_owned_columns", where=_CFG_HOME)
)
# D-2970 (BUG-745): the DECLARED write axes (config stage6.s5_axis_columns). A group here must be
# written WHOLE - stage6 refuses a scope carrying only part of one (C16), because half an axis is a
# split truth: the store would hold a value its own verification record does not derive.
def _s6_axis_columns() -> dict[str, tuple[str, ...]]:
    """Read the DECLARED write axes from config/pipeline_config.yaml#stage6.s5_axis_columns.

    D-2970/BUG-745 (C12/C16): read LOUDLY - no code default. A missing or empty declaration would
    silently disable the guard that refuses a write scope splitting an axis, which is exactly the
    defect this declaration exists to prevent (the rule BUG-504 applied to the S5 score-axis
    constants: a config miss IS the bug, so it raises instead of defaulting).
    """
    try:
        declared: object = _CFG["stage6"]["s5_axis_columns"]
    except KeyError as exc:
        raise KeyError(
            "config/pipeline_config.yaml#stage6.s5_axis_columns is NOT declared - the stage6 preflight "
            "could not then refuse a write scope that splits an axis (C12/C16, D-2970/BUG-745)"
        ) from exc
    if not isinstance(declared, dict) or not declared:
        raise ValueError(
            "config/pipeline_config.yaml#stage6.s5_axis_columns must declare at least one axis "
            f"(got {declared!r}) - an empty declaration disables the split guard (C16)"
        )
    return {str(_k): tuple(str(_c) for _c in _v) for _k, _v in declared.items()}


S6_S5_AXIS_COLUMNS: dict[str, tuple[str, ...]] = _s6_axis_columns()
# D-2934: columns whose value is DERIVED FROM the taxonomy menu. The taxonomy-skew guard
# refuses a write only when a written column appears here; an empty list means the skew is
# immaterial for this write and is recorded as a loud advisory instead (see stage6_commit).
# D-2982 (C16/D-2644): declared read - an absent list silently meant "no taxonomy skew is material here",
# which is precisely the guard D-2934 exists to apply (an empty declaration is a RULE, not a fallback).
S6_TAXONOMY_DEPENDENT_COLUMNS=frozenset(
    required_sequence(_CFG, "stage6", "taxonomy_dependent_columns", where=_CFG_HOME)
)
# D-2951 (D-2949 prevention half): the commit-time dedup gate. C12 — enabled + mode live in
# config/pipeline_config.yaml:stage6.dedup_gate, never in code. An unknown mode FAILS CLOSED at
# the call site (C16) rather than silently defaulting to a no-op gate.
# D-2982 (C16/D-2644): declared reads. The old `{}` default meant an absent block silently DISABLED a
# commit gate, and the old leaf defaults (`enabled=False`, `mode="report"`) meant an absent KEY disabled it
# while the block still looked present - a gate that fails open is not a gate.
_S6_DEDUP_GATE=required_mapping(_CFG, "stage6", "dedup_gate", where=_CFG_HOME)
S6_DEDUP_GATE_ENABLED=bool(required(_S6_DEDUP_GATE, "enabled", where=_CFG_HOME))
S6_DEDUP_GATE_MODE=str(required(_S6_DEDUP_GATE, "mode", where=_CFG_HOME))

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
S5_NLI_PASS_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_pass_threshold", 0.1))  # D2231/D2556: fallback aligned to config (was stale 0.6 — D2322 recalibrated to 0.1)
S5_NLI_MARGINAL_THRESHOLD=float(_CFG.get("stage5", {}).get("nli_marginal_threshold", 0.1))  # D2231/D2556: fallback aligned to config (was stale 0.3)
S5_NLI_MAX_PREMISE_CHARS=int(_CFG.get("stage5", {}).get("nli_max_premise_chars", 256))  # D2321: premise(evidence) truncation for NLI pairing
S5_NLI_MAX_HYPOTHESIS_CHARS=int(_CFG.get("stage5", {}).get("nli_max_hypothesis_chars", 256))  # D2321: hypothesis(definition) truncation
S5_EVIDENCE_CONTAMINATION_RATIO=float(_CFG.get("stage5", {}).get("evidence_contamination_ratio", 0.15))  # D2545: D2496/BUG-181#1 severe evidence-contamination threshold (was hardcoded 0.15)
# D2310: Confidence weights — NLI is a binary gate, not a score component (C12 config-driven).
def _s5_conf(key: str) -> object:
    """Read an S5 confidence value from config/pipeline_config.yaml#stage5.confidence.

    BUG-504 (C12/C16): this replaced .get(..., <code default>). A silent default lets a typo or a
    rename change the S5 score axis with no error anywhere - the config miss IS the bug. An
    undeclared key now raises, naming the file and the key.
    """
    try:
        return _CFG["stage5"]["confidence"][key]
    except KeyError as exc:
        raise KeyError(
            f"config/pipeline_config.yaml#stage5.confidence.{key} is NOT declared - S5 score-axis "
            f"constants must be DECLARED, never silently defaulted (C12/C16, BUG-504)"
        ) from exc


S5_CONF_MECH_WEIGHT=float(_s5_conf("mechanism_weight"))
S5_CONF_ENRICH_WEIGHT=float(_s5_conf("enrichment_weight"))
S5_CONF_ISOR_WEIGHT=float(_s5_conf("isor_weight"))
S5_QUARANTINE_CONF_CAP=float(_s5_conf("quarantine_cap"))
S5_HUMAN_REVIEW_ISOR=str(_s5_conf("human_review_isor_rating"))
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
TAXONOMY_MAX_DISCIPLINES = int(_CFG.get("taxonomy", {}).get("max_disciplines", 75))  # D2378/D2504: canonical cap (was hardcoded 47; default 72→75 to match live taxonomy.yaml)
D2399_PROMOTIONS_FROZEN = bool(_CFG.get("taxonomy", {}).get("d2399_promotions_frozen", False))          # D2519/D2399 policy A: manual freeze kill-switch
D2399_ALLOW_BOTH_AXES_EMERGING = bool(_CFG.get("taxonomy", {}).get("d2399_allow_both_axes_emerging", False))  # D2519: never promote a both-axes-emerging label
# D2556 (D2547): config-driven per-axis/per-label semantic-error thresholds (retire global 5%).
SEMANTIC_ERROR_RATE = _CFG.get("taxonomy", {}).get("semantic_error_rate_max", {})
SEMANTIC_ERROR_RATE_DEFAULT = float(SEMANTIC_ERROR_RATE.get("default", 0.05))
SEMANTIC_ERROR_RATE_PER_AXIS = dict(SEMANTIC_ERROR_RATE.get("per_axis", {}))
S4_GRAMMAR_DECODING_ENABLED = bool(_CFG.get("stage4", {}).get("grammar_decoding_enabled", False))  # D2556 (D2548): gate OFF until Outlines/XGrammar added

# ── Retrieve settings (D2231: C12 compliance) ─────────────────────────
RETRIEVE_CONFIDENCE_THRESHOLD = float(_CFG.get("retrieval_eval", {}).get("confidence_threshold", 0.85))
RERANK_ENABLED = bool(_CFG.get("rerank", {}).get("enabled", False))   # D2521 (S2): production rerank adoption gate
RETRIEVAL_METHOD = str(_CFG.get("retrieval", {}).get("method", "rrf"))  # D-2724: production retrieval default ('vector' | 'rrf')
# D-2980: the retrieval CANDIDATE-POOL policy reads its ONE home and FAILS CLOSED.
# Deliberately NOT a .get(key, <literal>) read: a code default moves the value out of config
# and into code (D-2644/BUG-504 class), and this is exactly the tuning value C12 requires in
# YAML. A missing block is an error at import, never a silent default (C16).
# D-2982: the same act through the ONE loud-read idiom. The hand-rolled try/except here was the pattern
# `required()` generalises; keeping both would leave two idioms for one rule, which is how a rule rots.
_POOL_CFG: dict = required_mapping(_CFG, "serving", "pool", where=_CFG_HOME)
RERANK_POOL_MULTIPLIER: int = int(_POOL_CFG["rerank_multiplier"])  # served/rerank pool = clamp(limit*mult, floor, cap)
RERANK_POOL_FLOOR: int = int(_POOL_CFG["rerank_floor"])
RERANK_POOL_CAP: int = int(_POOL_CFG["rerank_cap"])
RRF_LEG_POOL_MULTIPLIER: int = int(_POOL_CFG["rrf_leg_multiplier"])  # D2176 leg pool = min(limit*mult, cap)
RRF_LEG_POOL_CAP: int = int(_POOL_CFG["rrf_leg_cap"])
# A2/BUG-274: undirected related_fbs types (reverse adjacency). D-2982 (C16/D-2644): declared read - the
# 4-element code default was a second copy of the config list, so the registry could be edited while the
# reverse-adjacency rule silently kept the old vocabulary.
SYMMETRIC_RELATIONSHIP_TYPES = tuple(
    str(x) for x in required_sequence(_CFG, "retrieval", "symmetric_relationship_types", where=_CFG_HOME)
)
FTS_STOPWORDS = frozenset(_CFG.get("retrieval", {}).get("fts_stopwords", []))  # C12: FTS stopwords from config (D2561)

# D2537/D-2995 (BUG-776): fused quality ranking. The MEASURE the ordering uses has ONE home in config
# (`ranking.quality_field`), read FAIL-CLOSED - a code default here would move the value's effective
# setting out of config and turn a config miss into a silent fallback (D-2982/D-2644, the BUG-504 class).
# The retired `borp_score` scalar is NOT a candidate for either field or fallback (constant 0.0 on
# 7,640/7,640 rows, D-2994): with the fused ranking OFF there is NO declared ordering, and the code
# refuses loudly instead of ranking on a column nothing writes (C16/BUG-511).
RANKING_QUALITY_SCORE_ENABLED = bool(_CFG.get("ranking", {}).get("quality_score_enabled", False))
RANKING_QUALITY_FIELD = str(required(_CFG, "ranking", "quality_field", where=_CFG_HOME))
RANKING_CONFIDENCE_WEIGHT = float(_CFG.get("ranking", {}).get("confidence_weight", 1.0))
RANKING_CONVERGENT_BOOST = float(_CFG.get("ranking", {}).get("convergent_boost", 0.10))
RANKING_DIVERSITY_BOOST = float(_CFG.get("ranking", {}).get("diversity_boost", 0.05))
HYDE_ENABLED = bool(_CFG.get("hyde", {}).get("enabled", False))       # D2521 (S3): HyDE harness gate
HYDE_MODEL = str(_CFG.get("hyde", {}).get("model") or GEN_MODEL)      # D2521 (S3): hypothetical-doc generator model
HYDE_MAX_TOKENS = int(_CFG.get("hyde", {}).get("max_tokens", 256))    # D2521 (S3): hypothesis length cap

# ── Coverage settings (T0.3) ─────────────────────────────────────────
COVERAGE_THRESHOLD = float(_CFG.get("coverage", {}).get("threshold", 0.50))
COVERAGE_FLAG_FRACTION = float(_CFG.get("coverage", {}).get("flag_fraction", 0.30))

# ── E2E validation thresholds (T1.3) ─────────────────────────────────
E2E_BORP_MIN_SOURCES = int(_CFG.get("e2e", {}).get("borp_min_sources", 2))
E2E_MIN_PASS_RATE = float(_CFG.get("e2e", {}).get("min_pass_rate", 0.80))
E2E_MIN_FBS = int(_CFG.get("e2e", {}).get("min_fbs", 30))
E2E_CONVERGENT_RATIO = float(_CFG.get("e2e", {}).get("convergent_ratio", 0.25))
# D2531: corpus-aware verify pass-rate (OPT-IN). See e2e.corpus_aware_pass_rate.
E2E_CORPUS_AWARE_PASS_RATE = bool(_CFG.get("e2e", {}).get("corpus_aware_pass_rate", {}).get("enabled", False))
E2E_CONVERGENT_MIN_PASS_RATE = float(_CFG.get("e2e", {}).get("corpus_aware_pass_rate", {}).get("convergent_min_pass_rate", 0.25))
E2E_SINGLE_SOURCE_MIN_PASS_RATE = float(_CFG.get("e2e", {}).get("corpus_aware_pass_rate", {}).get("single_source_min_pass_rate", 0.20))

# ── Stage 1.5 settings (D2094: FAISS cluster) ─────────────────────────
S15_FAISS_THRESHOLD = float(_CFG.get("stage1_5", {}).get("faiss_threshold", 0.75))
S15_MIN_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("min_cluster_size", 2))
S15_MAX_CLUSTER_SIZE = int(_CFG.get("stage1_5", {}).get("max_cluster_size", 500))
S15_MIN_SOURCE_DIVERSITY = int(_CFG.get("stage1_5", {}).get("min_source_diversity", 2))
S15_NEIGHBOR_K = int(_CFG.get("stage1_5", {}).get("neighbor_k", 150))
S15_EMBED_MODEL = _CFG.get("stage1_5", {}).get("embed_model", "bge-m3")
S15_EMBED_DIM = int(_CFG.get("stage1_5", {}).get("embed_dim", 512))  # D2181: Matryoshka 512d (E7)
S15_EMBED_NATIVE_MRL = bool(_CFG.get("stage1_5", {}).get("embed_native_mrl", False))  # D2551: Ollama 'dimensions' MRL head vs manual 1024→512 truncate
S15_EMBED_BACKEND = _CFG.get("stage1_5", {}).get("embed_backend", "ollama")  # D2190: Ollama stable (MPS deadlocks on bge-m3)
S15_EMBED_MODEL_HF = _CFG.get("stage1_5", {}).get("embed_model_hf", "BAAI/bge-m3")  # D2181: unified
S15_EMBED_CHUNK_SIZE = int(_CFG.get("stage1_5", {}).get("embed_chunk_size", 20000))  # D2189: chunked embedding
S15_EMBED_BATCH_SIZE = int(_CFG.get("stage1_5", {}).get("embed_batch_size", 64))  # D2190: MPS forward batch
S15_MAX_EMBED_DROP_RATE = float(_CFG.get("stage1_5", {}).get("max_embed_drop_rate", 0.005))  # D2275: embed quality gate
S15_EMBED_CHECKPOINT_ENABLED = bool(_CFG.get("stage1_5", {}).get("embed_checkpoint_enabled", True))  # D2409: crash-safe incremental embedding cache

# ── Stage 6 settings (D2084) ────────────────────────────────────────────
S6_COMMIT_NON_FB=bool(_CFG["stage6"]["commit_non_fb_types"])
S6_VEC_REQUIRE = bool(_CFG.get("stage6", {}).get("vec_require", False))  # D-2717: fail-closed vec0 gate (C16)
S6_VEC_PYTHON = str(_CFG.get("stage6", {}).get("vec_python", ""))  # D-2717: vec0-capable interpreter (Homebrew 3.14 verified)

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
# D-2716: MAXWELL_DB_PATH env override for S6 test isolation (C12: config-first, env override mirrors run_id pattern)
DB_PATH = PROJECT_ROOT / Path(_env("db_path", _PATHS.get("db_path", "knowledge pipeline/maxwell.db")))
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
# D2452: deterministic pre-LLM singleton gate (scripts/prefilter_clusters.py).
# Produces {cluster_id -> EXTRACT/SKIP} from config/filtering.yaml thresholds so
# the S2 singleton pass skips noise/junk singletons before any LLM call.
STAGE1_5_SINGLETONS_PREFILTERED = _s15_path("singletons.prefiltered.jsonl")
S2_SINGLETON_PREFILTER_ENABLED = bool(_CFG.get("stage2", {}).get("singleton_prefilter_enabled", False))

# ── Smoke test config (D2120) ────────────────────────────────────────────
SMOKE_PLUMBING_SKIP_LLM = bool(_CFG.get("smoke", {}).get("plumbing", {}).get("skip_llm", True))
SMOKE_FAST_MODEL = _CFG.get("smoke", {}).get("fast", {}).get("fast_model", "Phi-4-mini-instruct-8bit")
SMOKE_FAST_SKIP_GEMMA = bool(_CFG.get("smoke", {}).get("fast", {}).get("skip_gemma_deep_check", True))
SMOKE_MAX_BOOKS = int(_CFG.get("smoke", {}).get("fast", {}).get("max_books", 3))

# ── MCP server delegate_local guard (D2550 / BUG-220-MCP) ─────────────────
MCP_DELEGATE_ALLOWED_MODELS = set(_CFG.get("mcp", {}).get("delegate_local", {}).get("allowed_models", []))
MCP_DELEGATE_MAX_SYSTEM_CHARS = int(_CFG.get("mcp", {}).get("delegate_local", {}).get("max_system_chars", 4000))
MCP_DELEGATE_MAX_FILES = int(_CFG.get("mcp", {}).get("delegate_local", {}).get("max_files", 20))
MCP_DELEGATE_ALLOW_ABSOLUTE_PATHS = bool(_CFG.get("mcp", {}).get("delegate_local", {}).get("allow_absolute_paths", False))
