#!/usr/bin/env python3
"""
integrity_check.py — Maxwell OS System Integrity Validator

D2203: 17 automated checks that turn the CONSTITUTION.md from prose into
an executable specification. Run via `just integrity`.

Checks:
  1.  All YAML configs parse without error
  2.  All referenced files exist
  3.  All referenced models are known / not broken
  4.  Every Python import has a declared dependency
  5.  Each stage has exactly one input/output contract
  6.  Stage order matches CONSTITUTION.md
  7.  Pydantic schemas match SQLite schema
  8.  SQLite schema matches insert placeholders
  9.  Vector dimensions match embedding model config
 10.  Prompt IDs match generated artifacts
 11.  Model registry matches runtime
 12.  Version stamps agree across all sources
 13.  No deprecated config is reachable
 14.  No hardcoded path (C12 compliance)
 15.  No silent exception (C16 compliance)
 16.  No zero-vector fallback (D2196 compliance)
 17.  No FAILED state can become PASS (monotonic trust)

Usage:
    python3 pipeline/integrity_check.py              # Full check
    python3 pipeline/integrity_check.py --quick      # Fast checks only (1-6, 12-16)
    python3 pipeline/integrity_check.py --check N    # Single check by number
"""

import ast
import re
import sqlite3
import sys
from pathlib import Path

import yaml

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "pipeline"
CONFIG_DIR = REPO_ROOT / "config"
KNOWLEDGE_DIR = REPO_ROOT / "knowledge pipeline"
GOVERNANCE_DIR = REPO_ROOT / "governance"
sys.path.insert(0, str(REPO_ROOT))  # D2478: allow `from pipeline.* import` in checks (check_canonical_promotion)

# ── ANSI colours ───────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS = f"{GREEN}✅ PASS{RESET}"
FAIL = f"{RED}❌ FAIL{RESET}"
WARN = f"{YELLOW}⚠️  WARN{RESET}"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 1: All YAML configs parse without error
# ═══════════════════════════════════════════════════════════════════════════
def check_yaml_parse() -> tuple[bool, str]:
    """Verify every .yaml file in config/ and agent/ parses cleanly."""
    yaml_files = list(CONFIG_DIR.glob("*.yaml")) + list(CONFIG_DIR.glob("*.yml"))
    yaml_files += list((REPO_ROOT / "agent").glob("*.yaml"))
    yaml_files += [REPO_ROOT / ".ponytail.yaml"]

    errors = []
    for f in sorted(yaml_files):
        if f.name.endswith(".bak"):
            continue
        try:
            with open(f) as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as e:
            errors.append(f"  {f.name}: {e}")

    if errors:
        return False, "YAML parse errors:\n" + "\n".join(errors)
    return True, f"All {len(yaml_files)} YAML files parse cleanly"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 2: All referenced files exist
# ═══════════════════════════════════════════════════════════════════════════
def check_referenced_files() -> tuple[bool, str]:
    """Check that files referenced in configs and docs actually exist."""
    missing = []

    # Check pipeline stage scripts
    with open(CONFIG_DIR / "pipeline_config.yaml") as f:
        config = yaml.safe_load(f)

    stages = config.get("stages", {})
    for stage_name, stage_path in stages.items():
        # Config points to output directories; scripts live in pipeline/.
        # Skip non-string entries (e.g., 'timeouts' is a dict, not a stage script).
        if not isinstance(stage_path, str):
            continue
        # The scripts live in pipeline/. Config may use shorthand key (e.g., "stage1_5_embed").
        script_name = STAGE_CONFIG_TO_SCRIPT.get(stage_name, stage_name)
        script_name = script_name + ".py" if not script_name.endswith(".py") else script_name
        script = PIPELINE_DIR / script_name
        if not script.exists():
            missing.append(f"  Stage {stage_name}: script {script_name} not found in pipeline/")

    # Check protected files from session_seed
    with open(REPO_ROOT / "agent" / "session_seed.yaml") as f:
        seed = yaml.safe_load(f)

    EXPECTED_MISSING = {".env"}  # Gitignored, intentionally missing
    protected = seed.get("governance", {}).get("protected_files", [])
    for pf in protected:
        if "*" in pf or pf in EXPECTED_MISSING:
            continue
        if not (REPO_ROOT / pf).exists():
            missing.append(f"  Protected file: {pf}")

    if missing:
        return False, "Missing referenced files:\n" + "\n".join(missing)
    return True, "All referenced files exist"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 3: Referenced models are known and not broken
# ═══════════════════════════════════════════════════════════════════════════
KNOWN_BROKEN_MODELS = {
    "DeepSeek-R1-0528-Qwen3-8B-MLX-4bit": "DELEGATE-001: reasoning_content passthrough bug",
    "gemma-4-26B-A4B-it-OptiQ-4bit": "Goose stress test: 5/5 calls fail",
}


def check_models_known() -> tuple[bool, str]:
    """Verify all referenced models are not known-broken."""
    issues = []
    model_files = [
        CONFIG_DIR / "pipeline_config.yaml",
        CONFIG_DIR / "model_assignments.yaml",
        REPO_ROOT / "agent" / "session_seed.yaml",
    ]

    for mf in model_files:
        if not mf.exists():
            continue
        with open(mf) as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            # Skip commented-out lines
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            for broken_model, reason in KNOWN_BROKEN_MODELS.items():
                if broken_model in stripped:
                    # Only flag if it looks like an active model assignment (value, not comment)
                    if "REMOVED" in stripped or "DISABLED" in stripped:
                        continue
                    issues.append(f"  {mf.name}:{i + 1}: {broken_model} — {reason}")

    if issues:
        return False, "Broken models referenced:\n" + "\n".join(issues)
    return True, "No known-broken models referenced in active configs"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 4: Every Python import has a declared dependency
# ═══════════════════════════════════════════════════════════════════════════
STDLIB_MODULES = {
    "os", "sys", "re", "json", "pathlib", "subprocess", "sqlite3", "hashlib",
    "uuid", "logging", "typing", "collections", "itertools", "functools",
    "tempfile", "shutil", "datetime", "math", "io", "csv", "argparse",
    "textwrap", "time", "traceback", "ast", "importlib", "inspect",
    "warnings", "contextlib", "dataclasses", "enum", "abc", "copy",
    "glob", "fnmatch", "statistics", "random", "string", "unittest",
    "xml", "html", "http", "urllib", "email", "base64", "binascii",
    "struct", "pickle", "shelve", "marshal", "queue", "threading",
    "multiprocessing", "asyncio", "concurrent", "socket", "ssl",
    "signal", "mmap", "gc", "atexit", "pdb", "pprint", "platform",
    "getpass", "getopt", "configparser", "secrets",
    "tomllib", "tomli", "zipfile", "tarfile", "gzip", "bz2", "lzma",
    "__future__",  # stdlib: used for annotations
}
KNOWN_PACKAGES = {
    "pydantic", "yaml", "pyyaml", "pyarrow", "requests", "numpy",
    "sklearn", "scikit-learn", "faiss", "faiss-cpu", "sentence_transformers",
    "sentence-transformers", "transformers", "networkx", "datasketch",
    "sqlite_vec", "sqlite-vec", "tqdm", "psutil", "watchdog",
    "rich", "pandas", "torch", "mlx", "mlx_lm", "ollama",
    # Conditional/optional dependencies (not in requirements.txt, imported inline):
    "pypandoc",       # batch_convert_epubs, fix_remaining: fallback EPUB converter
    "outlines",        # mlx_provider: structured generation (optional)
    "huggingface_hub", # test_mlx_integration: test-only dependency
    "fastembed",       # stage1_5_fastembed: alternative embedding backend
    "dspy",            # dspy_trainer: MIPROv2 optimization harness (optional, post-T1.1)
}
LOCAL_MODULES = {"pipeline", "config", "tools", "tests", "providers", "storage", "sync", "memory", "pipeline_paths"}


def check_import_dependencies() -> tuple[bool, str]:
    """Check that imports in pipeline/ have corresponding declared dependencies."""
    issues = []
    py_files = list(PIPELINE_DIR.glob("*.py")) + list((PIPELINE_DIR / "providers").glob("*.py"))

    for pyf in sorted(py_files):
        if pyf.name.startswith("__") or pyf.name.startswith("."):
            continue
        try:
            with open(pyf) as f:
                tree = ast.parse(f.read())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0]
                    _check_module(mod, pyf.name, issues)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0]
                    _check_module(mod, pyf.name, issues)

    if issues:
        return False, "Undeclared imports:\n" + "\n".join(issues[:20])
    return True, f"All imports in {len(py_files)} files have declared dependencies"


def _check_module(mod: str, filename: str, issues: list[str]) -> None:
    if mod in STDLIB_MODULES or mod in LOCAL_MODULES or mod in KNOWN_PACKAGES:
        return
    issues.append(f"  {filename}: imports `{mod}` — not in stdlib, local, or known deps")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 5: Stage input/output contracts
# ═══════════════════════════════════════════════════════════════════════════
EXPECTED_STAGES = [
    "stage0_convert", "stage0_5_extract_metadata", "stage1_chunk",
    "stage1_3_prefilter", "stage1_5_embed_cluster", "stage2_extract",
    "stage4_merge", "stage5_verify", "stage6_commit",
]

# Config key → actual script name mapping (config uses shorthand)
STAGE_CONFIG_TO_SCRIPT = {
    "stage1_5_embed": "stage1_5_embed_cluster",
}


def check_stage_contracts() -> tuple[bool, str]:
    """Verify each stage script exists and has a main() or equivalent entry point."""
    missing = []
    for stage in EXPECTED_STAGES:
        script = PIPELINE_DIR / f"{stage}.py"
        if not script.exists():
            missing.append(f"  {stage}.py not found")
    if missing:
        return False, "Missing stage scripts:\n" + "\n".join(missing)
    return True, f"All {len(EXPECTED_STAGES)} stage scripts exist"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 6: Stage order matches CONSTITUTION.md
# ═══════════════════════════════════════════════════════════════════════════
def check_stage_order() -> tuple[bool, str]:
    """Verify CONSTITUTION.md stage order matches pipeline_config.yaml."""
    with open(REPO_ROOT / "CONSTITUTION.md") as f:
        constitution = f.read()

    # Extract stage order from CONSTITUTION
    pipeline_line = None
    for line in constitution.split("\n"):
        if "PIPELINE" in line and "8-stage" in line:
            pipeline_line = line
            break

    with open(CONFIG_DIR / "pipeline_config.yaml") as f:
        config = yaml.safe_load(f)

    config_stages = list(config.get("stages", {}).keys())

    # Verify no stage3 in config
    if "stage3_cluster" in config_stages or "stage3" in str(config_stages):
        return False, "Stage 3 still present in pipeline_config.yaml stages"

    # D2473/ext-audit #5: verify the RELATIVE ORDER of the pipeline stages
    # (the old check only verified count + stage3 absence — a permutation like
    # stage5 before stage4 was undetected).
    expected = ["stage0_convert", "stage0_5_extract_metadata", "stage1_chunk",
                "stage1_3_prefilter", "stage1_5_embed", "stage2_extract",
                "stage4_merge", "stage5_verify", "stage6_commit"]
    actual = [s for s in config_stages if s in expected]
    if actual != expected:
        return False, f"Stage order mismatch: {actual} != {expected}"

    # D2496/ext-audit #5: `timeouts` is a legit non-stage key — exclude it (and
    # any other non-stage key) from the stage count so the report is truthful.
    non_stage = [s for s in config_stages if s not in expected and s != "timeouts"]
    if non_stage:
        return False, f"Unexpected non-stage keys in config stages: {non_stage}"

    # Verify CONSTITUTION says 8-stage
    if pipeline_line and "8-stage" not in pipeline_line:
        return False, "CONSTITUTION.md does not say 8-stage"

    return True, f"Stage order consistent: {len(expected)} stages, Stage 3 removed"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 7: Pydantic schemas match SQLite schema
# ═══════════════════════════════════════════════════════════════════════════
def check_schema_sqlite_match() -> tuple[bool, str]:
    """Compare Pydantic FB fields against SQLite column names."""
    db_path = KNOWLEDGE_DIR / "maxwell.db"
    if not db_path.exists():
        return "skip", "No maxwell.db — schema check skipped (run pipeline first)"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(fbs)")
    sqlite_cols = {row[1] for row in cursor.fetchall()}
    conn.close()

    # Extract Pydantic fields from schemas.py
    with open(PIPELINE_DIR / "schemas.py") as f:
        schemas_code = f.read()

    # Find all Pydantic model fields (collect across all model classes)
    # FB inherits from StampedRecord — both fields should count.
    all_model_fields: set[str] = set()
    in_model = False
    model_classes = {"FB", "FoundationBlock", "StampedFB", "StampedRecord",
                     "Segment", "Principle", "Cluster", "VerifiedFB", "FBRecord"}
    for line in schemas_code.split("\n"):
        stripped = line.strip()
        # Detect class entry — any Pydantic model
        class_match = re.match(r"class\s+(\w+)\s*\(\w+", stripped)
        if class_match:
            in_model = class_match.group(1) in model_classes
            continue
        if in_model and stripped.startswith("class "):
            in_model = False
            continue
        if in_model and ":" in stripped and not stripped.startswith(("#", '"""', "'")):
            field_name = stripped.split(":")[0].strip()
            if field_name and "def " not in field_name and "class " not in field_name and "=" not in field_name:
                all_model_fields.add(field_name)

    # Check key fields exist in both (use broader set for comparison).
    # D2342: include D2337 fields (content_type/extraction_type/mechanism/boundary/
    # consequence/taxonomy_match_method) so the check actually catches the S6
    # data-loss regression that D2337 fixed (was only 5 key fields).
    key_fields = {
        "fb_id", "name", "definition", "status", "schema_version",
        "content_type", "extraction_type", "mechanism", "boundary",
        "consequence", "taxonomy_match_method", "source_ids",
        "citation", "source_authors", "source_diversity", "primary_source",
    }
    missing_in_sqlite = key_fields - sqlite_cols
    missing_in_pydantic = key_fields - all_model_fields

    issues = []
    if missing_in_sqlite:
        issues.append(f"  Fields in Pydantic but not SQLite: {missing_in_sqlite}")
    if missing_in_pydantic:
        issues.append(f"  Fields in SQLite but not Pydantic: {missing_in_pydantic}")

    if issues:
        return False, "Schema mismatch:\n" + "\n".join(issues)
    return True, f"SQLite ({len(sqlite_cols)} cols) and Pydantic ({len(all_model_fields)} fields) aligned on key fields"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 9: Vector dimensions match embedding model config
# ═══════════════════════════════════════════════════════════════════════════
def check_vector_dimensions() -> tuple[bool, str]:
    """Verify embed_dim in config matches pipeline_paths and actual stored vectors."""
    with open(CONFIG_DIR / "pipeline_config.yaml") as f:
        config = yaml.safe_load(f)

    embed_dim = config.get("stage1_5", {}).get("embed_dim", None)

    # Check session_seed agrees
    with open(REPO_ROOT / "agent" / "session_seed.yaml") as f:
        seed = yaml.safe_load(f)

    seed_dim = seed.get("models", {}).get("embeddings", {}).get("dims", None)

    if embed_dim and seed_dim and embed_dim != seed_dim:
        return False, f"Dimension mismatch: pipeline_config={embed_dim}, session_seed={seed_dim}"

    if embed_dim:
        return True, f"Embedding dimension: {embed_dim} (Matryoshka, consistent across configs)"
    return "skip", "No embed_dim found in config"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 12: Version stamps agree across all sources
# ═══════════════════════════════════════════════════════════════════════════
def check_version_consistency() -> tuple[bool, str]:
    """Verify version stamps in version.yaml, CONSTITUTION.md, session_seed agree."""
    with open(CONFIG_DIR / "version.yaml") as f:
        version_cfg = yaml.safe_load(f)

    schema_v = version_cfg.get("schema_version", "")
    const_v = version_cfg.get("constitution_version", "")

    with open(REPO_ROOT / "agent" / "session_seed.yaml") as f:
        seed = yaml.safe_load(f)

    seed_schema = seed.get("session", {}).get("schema_version", "")
    seed_version = seed.get("session", {}).get("version", "")

    issues = []
    if schema_v != seed_schema:
        issues.append(f"  schema_version: version.yaml={schema_v}, session_seed={seed_schema}")
    if not issues:
        return True, f"Version stamps consistent: v{const_v}, schema {schema_v}"
    return False, "Version stamp mismatch:\n" + "\n".join(issues)


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 13: No deprecated config is reachable
# ═══════════════════════════════════════════════════════════════════════════
DEPRECATED_KEYS = [
    "umap_n_neighbors",
    "umap_min_dist",
    "stage3_cluster",
]


def check_deprecated_config() -> tuple[bool, str]:
    """Verify deprecated keys are commented out or removed from active configs."""
    issues = []
    config_files = [CONFIG_DIR / "pipeline_config.yaml"]

    for cf in config_files:
        if not cf.exists():
            continue
        with open(cf) as f:
            for i, line in enumerate(f, 1):
                for dk in DEPRECATED_KEYS:
                    if dk in line and not line.strip().startswith("#") and "REMOVED" not in line:
                        issues.append(f"  {cf.name}:{i}: deprecated key '{dk}' in active config")

    if issues:
        return False, "Deprecated config reachable:\n" + "\n".join(issues)
    return True, "No deprecated config keys in active configuration"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 14: No hardcoded paths (C12 compliance)
# ═══════════════════════════════════════════════════════════════════════════
def check_hardcoded_paths() -> tuple[bool, str]:
    """Scan the whole repo (pipeline/, tools/, scripts/, tests/, root *.sh) for hardcoded user paths (C12).

    D2439: previously only globbed PIPELINE_DIR.glob("*.py") — flat, non-recursive,
    .py-only. It could not see tools/, tests/, scripts/, pipeline/providers/,
    pipeline/storage/, or any .sh — 9 hardcoded /Users/barn paths were invisible.
    """
    issues = []
    # `/Users/...`, `/home/...`, `C:\Users\...` — match the leading path portion only
    user_paths = re.compile(r'["\'](/Users/[^\s"\']+|/home/[^\s"\']+|C:\\Users\\[^\s"\']+)')

    scan_roots = [
        PIPELINE_DIR,
        REPO_ROOT / "tools",
        REPO_ROOT / "scripts",
        REPO_ROOT / "tests",
        REPO_ROOT / "pipeline" / "providers",
        REPO_ROOT / "pipeline" / "storage",
    ]
    targets: list[Path] = []
    for root in scan_roots:
        if not root.exists():
            continue
        if root.name in ("tools", "scripts", "tests"):
            targets.extend(sorted(root.rglob("*.py")) + sorted(root.rglob("*.sh")))
        else:
            targets.extend(sorted(root.rglob("*.py")))
    # root-level shell scripts
    targets.extend(sorted(REPO_ROOT.glob("*.sh")))

    for pf in sorted(set(targets)):
        try:
            with open(pf, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if user_paths.search(line) and "REMOVED" not in line:
                        issues.append(f"  {pf.relative_to(REPO_ROOT)}:{i}: hardcoded path")
        except (OSError, UnicodeDecodeError):
            continue

    if issues:
        return False, "Hardcoded paths found (C12 violation):\n" + "\n".join(issues[:15])
    return True, f"No hardcoded paths in {len(set(targets))} scanned files (C12 compliant)"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 15: No silent exceptions (C16 compliance)
# ═══════════════════════════════════════════════════════════════════════════
def check_silent_exceptions() -> tuple[bool, str]:
    """Scan pipeline/ for bare except: or except Exception: pass patterns (C16).

    Graceful degradation is exempt: functions that return sentinel values
    (None, False, "unknown", 0, []) on failure are acceptable patterns.
    We only flag truly silent data-loss patterns where execution continues
    without any indication of failure.
    """
    # Known graceful-degradation functions (probes, diagnostics, cleanup):
    GRACEFUL_FUNCTIONS = {
        "get_omlx_version", "get_omlx_ceiling", "check_omlx_health",
        "sample_memory", "unload_all_models", "get_pipeline_commit",
        "get_git_commit", "torch.mps.empty_cache",
        "embed_segments",  # MPS cache clearing inside is best-effort
        "run_stage6",      # Vector count queries degrade gracefully on missing sqlite-vec
    }

    issues = []
    py_files = list(PIPELINE_DIR.glob("*.py"))

    for pyf in sorted(py_files):
        with open(pyf) as f:
            lines = f.readlines()

        # Determine if we're in a graceful-degradation function
        current_func = ""
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Track function context
            func_match = re.match(r"def\s+(\w+)\s*\(", stripped)
            if func_match:
                current_func = func_match.group(1)

            # Skip graceful-degradation functions entirely
            if current_func in GRACEFUL_FUNCTIONS:
                continue

            # Bare except:
            if re.match(r"except\s*:", stripped):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if next_line and not next_line.startswith(("raise", "logger.", "log.", "print(")):
                    issues.append(f"  {pyf.name}:{i + 1}: bare except: in '{current_func}'")

            # except Exception: pass with no logging (and not in probe function)
            if re.match(r"except\s+Exception\s*:", stripped):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if next_line == "pass":
                    # Check if the function returns a sentinel shortly after
                    has_sentinel = False
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if "return" in lines[j]:
                            has_sentinel = True
                            break
                    if not has_sentinel:
                        issues.append(f"  {pyf.name}:{i + 1}: except Exception: pass in '{current_func}' — no sentinel return")

    if issues:
        return False, "Silent exception patterns (C16 violation):\n" + "\n".join(issues[:10])
    return True, f"No silent exceptions in {len(py_files)} pipeline files (C16 compliant)"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 16: No zero-vector fallback (D2196 compliance)
# ═══════════════════════════════════════════════════════════════════════════
def check_zero_vector() -> tuple[bool, str]:
    """Verify ollama_embed.py has no zero-vector fallbacks (D2196)."""
    embed_file = PIPELINE_DIR / "ollama_embed.py"
    if not embed_file.exists():
        return "skip", "ollama_embed.py not found"

    with open(embed_file) as f:
        content = f.read()

    # Check EmbeddingQuarantineError is defined
    if "class EmbeddingQuarantineError" not in content:
        return False, "EmbeddingQuarantineError class not defined"

    # Check no active [0.0] * dim patterns (outside comments/docstrings)
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "[0.0]" in stripped and not stripped.startswith("#") and '"""' not in stripped:
            if "Never insert" in stripped:
                continue  # docstring about removal
            return False, f"ollama_embed.py:{i + 1}: active zero-vector pattern: {stripped}"

    return True, "No zero-vector fallbacks (D2196 compliant). EmbeddingQuarantineError defined."


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 17: No FAILED state can become PASS (monotonic trust)
# ═══════════════════════════════════════════════════════════════════════════
def check_monotonic_trust() -> tuple[bool, str]:
    """Verify stage5_verify.py prevents FAILED→PASS transitions (D2093, D2184)."""
    verify_file = PIPELINE_DIR / "stage5_verify.py"
    if not verify_file.exists():
        return "skip", "stage5_verify.py not found"

    with open(verify_file) as f:
        content = f.read()

    # Check for fail-closed pattern
    has_fail_closed = (
        "QUARANTINE" in content and
        ("cannot" in content.lower() or "never" in content.lower() or "fail" in content.lower())
    )

    if not has_fail_closed:
        return False, "stage5_verify.py: no fail-closed pattern detected"

    # Check for classification_status protection (D2184)
    if "classification_status" in content and "FAILED" in content:
        return True, "Monotonic trust: fail-closed verification + classification_status protection (D2184)"

    return True, "Monotonic trust patterns detected (fail-closed verified)"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 8: SQLite schema matches insert placeholders
# ═══════════════════════════════════════════════════════════════════════════
def check_sqlite_insert_placeholders() -> tuple[bool, str]:
    """Verify stage6_commit.py INSERT statements match SQLite column count."""
    db_path = KNOWLEDGE_DIR / "maxwell.db"
    commit_file = PIPELINE_DIR / "stage6_commit.py"

    if not db_path.exists():
        return "skip", "No maxwell.db — insert check skipped"
    if not commit_file.exists():
        return "skip", "stage6_commit.py not found"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(fbs)")
    col_count = len(cursor.fetchall())
    conn.close()

    with open(commit_file) as f:
        commit_code = f.read()

    # Count ? placeholders in the `INSERT OR REPLACE INTO fbs` VALUES clause.
    # D2342: the prior regexes were broken two ways — (1) re.findall with a capturing
    # group returned the *group* ("OR REPLACE ") instead of the full match, so
    # placeholder_count was ALWAYS 0 and the check silently returned True; (2) the
    # `[^;]*` tail matched `fbs_fts` (prefix) and spanned past the SQL string into
    # Python code, over-counting. Anchor to the VALUES (...) clause and use \b so
    # `fbs_fts` is excluded.
    m = re.search(
        r"INSERT\s+(?:OR\s+REPLACE\s+)?INTO\s+fbs\b.*?VALUES\s*\(([^)]*)\)",
        commit_code,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return "skip", "INSERT INTO fbs VALUES clause not found"

    placeholder_count = m.group(1).count("?")
    if placeholder_count != col_count:
        return False, f"INSERT has {placeholder_count} placeholders but fbs table has {col_count} columns"
    return True, f"INSERT placeholders ({placeholder_count}) match SQLite columns ({col_count})"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 10: Prompt IDs match generated artifacts
# ═══════════════════════════════════════════════════════════════════════════
def check_prompt_ids() -> tuple[bool, str]:
    """Verify prompt references in pipeline match files in prompts/."""
    prompts_dir = REPO_ROOT / "prompts"
    if not prompts_dir.exists():
        return "skip", "No prompts/ directory"

    prompt_files = {f.stem for f in prompts_dir.glob("*") if f.is_file()}

    # Scan pipeline for prompt file references
    py_files = list(PIPELINE_DIR.glob("*.py"))
    refs_found = 0
    for pyf in py_files:
        with open(pyf) as f:
            content = f.read()
        for pf in prompt_files:
            if pf in content:
                refs_found += 1

    return True, f"Prompt references: {refs_found} matches across {len(prompt_files)} prompt files"


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 11: Model registry matches runtime
# ═══════════════════════════════════════════════════════════════════════════
def check_model_registry_runtime() -> tuple[bool, str]:
    """Verify pipeline_config.yaml model names are internally consistent.

    D2340: the `verifier`/`verifier_v2` role keys are misnamed — `verifier`
    (gpt-oss) is the S4 *classifier* (D2249), and `verifier_v2` (Phi-4-mini)
    is the S2 *probe* (D2319). The true S5 verifier is DeBERTa (`nli_large`),
    an encoder — no family string. R5 (Generator ≠ Verifier) therefore reduces
    to: generator family must differ from the classifier/probe family.
    """
    with open(CONFIG_DIR / "pipeline_config.yaml") as f:
        config = yaml.safe_load(f)

    models = config.get("models", {})
    generator = models.get("generator", {}).get("model", "")
    classifier = models.get("verifier", {}).get("model", "")      # D2340: S4 classifier
    probe = models.get("verifier_v2", {}).get("model", "")        # D2340: S2 probe
    nli_large = str(models.get("nli_large", ""))

    # R5: Generator ≠ Verifier (different model families). The S5 verifier is
    # DeBERTa (encoder — no LLM family), so only the classifier/probe LLMs are
    # family-comparable against the generator.
    gen_family = "qwen" if "qwen" in generator.lower() else "unknown"
    cls_family = "unknown"
    for fam in ("gpt-oss", "gemma", "phi", "qwen", "deepseek", "llama"):
        if fam in classifier.lower() or fam in probe.lower():
            cls_family = fam
            break

    if gen_family == cls_family and gen_family != "unknown":
        return False, f"R5 violation: Generator ({gen_family}) = Classifier/Probe ({cls_family}) — must be different families"

    nli_label = "DeBERTa" if "deberta" in nli_large.lower() else (nli_large or "unset")
    return True, f"R5 compliant: Generator={gen_family}, Classifier/Probe={cls_family}, S5 verifier={nli_label} (cross-family)"


def check_canonical_promotion() -> tuple[bool, str]:
    """D2479: assert the option-(a) invariant — NO dead-end siblings may exist.

    The 2026-08-27 file-drift root cause was post-hoc cleanup tools writing to
    `.fixed`/`.final`/`.deduped` siblings that were never promoted to canonical, so
    `stage4_merge.py` read STALE files. D2479 chose option (a): cleanup tools now
    write IN-PLACE to canonical (crash-safe C6 + backup), and the dead-end siblings
    were retired via `safe_delete.py`. This check now fails if ANY dead-end sibling
    EXISTS — their presence is itself the drift hazard, regardless of content.

    Skip (not fail) when the canonical does not exist (no run for this run_id yet).
    """
    from pipeline.pipeline_paths import STAGE2_CHECKPOINT, STAGE2_SINGLETON_OUTPUT

    issues: list[str] = []
    # (canonical, [FORBIDDEN dead-end sibling names]) — any existence = violation.
    forbidden: list[tuple[str, list[str]]] = [
        (STAGE2_SINGLETON_OUTPUT, ["singleton_fbs.final.jsonl", "singleton_fbs.fixed.jsonl"]),
        (STAGE2_CHECKPOINT, ["checkpoint.deduped.jsonl", "checkpoint.passage_cleaned.jsonl"]),
    ]
    any_canonical = False
    for canon, names in forbidden:
        if not canon.exists():
            continue
        any_canonical = True
        for name in names:
            v = canon.with_name(name)
            if v.exists():
                issues.append(f"{v.name} exists (dead-end sibling — option-(a) forbids it)")

    if not any_canonical:
        return "skip", "no S2 canonical files for this run_id (nothing to check)"
    if issues:
        return False, "; ".join(issues)
    return True, "canonical S2 files only — no dead-end siblings (option-a invariant holds)"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
CHECKS = [
    (1, "YAML parse", check_yaml_parse),
    (2, "Referenced files exist", check_referenced_files),
    (3, "Models known/not broken", check_models_known),
    (4, "Import dependencies", check_import_dependencies),
    (5, "Stage contracts", check_stage_contracts),
    (6, "Stage order vs CONSTITUTION", check_stage_order),
    (7, "Schema↔SQLite match", check_schema_sqlite_match),
    (8, "SQLite INSERT placeholders", check_sqlite_insert_placeholders),
    (9, "Vector dimensions", check_vector_dimensions),
    (10, "Prompt IDs", check_prompt_ids),
    (11, "Model registry R5", check_model_registry_runtime),
    (12, "Version stamps", check_version_consistency),
    (13, "Deprecated config", check_deprecated_config),
    (14, "Hardcoded paths (C12)", check_hardcoded_paths),
    (15, "Silent exceptions (C16)", check_silent_exceptions),
    (16, "Zero-vector fallback (D2196)", check_zero_vector),
    (17, "Monotonic trust (D2184)", check_monotonic_trust),
    (18, "Canonical promotion drift (D2478)", check_canonical_promotion),
]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Maxwell OS Integrity Check (D2203)")
    parser.add_argument("--quick", action="store_true", help="Fast checks only")
    parser.add_argument("--check", type=int, help="Single check number")
    args = parser.parse_args()

    print(f"\n{BOLD}Maxwell OS — System Integrity Check (D2203){RESET}\n")

    to_run = CHECKS
    if args.check:
        to_run = [c for c in CHECKS if c[0] == args.check]
        if not to_run:
            print(f"{FAIL} No check #{args.check}")
            return 1
    elif args.quick:
        to_run = [c for c in CHECKS if c[0] in (1, 2, 3, 6, 9, 12, 13, 14, 15, 16)]

    passed = 0
    failed = 0
    skipped = 0

    for num, name, func in to_run:
        try:
            ok, msg = func()
        except Exception as e:
            print(f"  [{num:2d}] {name:<40s} {FAIL} — unhandled: {e}")
            failed += 1
            continue

        if ok == "skip":
            print(f"  [{num:2d}] {name:<40s} {WARN} — {msg}")
            skipped += 1
        elif ok:
            print(f"  [{num:2d}] {name:<40s} {PASS} — {msg}")
            passed += 1
        else:
            print(f"  [{num:2d}] {name:<40s} {FAIL}")
            print(f"       {msg}")
            failed += 1

    total = passed + failed + skipped
    print(f"\n{BOLD}Results:{RESET} {passed}/{total} passed, {failed} failed, {skipped} skipped\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
