#!/usr/bin/env python3
"""
stage2_extract.py — Convergent Principle Extraction from Clusters.
==================================================================
Authority: D2094, D2095, D2101 | CONSTITUTION.md §3

Input:  Clusters from Stage 1.5 (FAISS) + raw segments from Stage 1
Output: Convergent Foundation Blocks with mechanism/boundary/consequence

v3.1 UPDATE (D2182): Extracts 1:N principles per cluster — 1:1 extraction was
causing 291:1 compression death spiral. LLM returns JSON array of distinct
atomic causal mechanisms. Principle Discovery Gate (D2163) splits large
low-cohesion clusters via k-means before extraction.

Process:
  1. Load clusters from Stage 1.5 checkpoint
  2. For each convergent cluster (≥2 source books):
     a. Gather 5-15 raw segment texts
     b. Build convergent extraction prompt
     c. Call LLM to extract ALL distinct mechanisms (1:N, array response)
     d. Schema: name, definition, mechanism, boundary, consequence,
        is_summary, evidence_passages
     e. Post-extraction: MinHash 3-gram dedup, gate enforcement
     e. Merged classification: depth, discipline, domain, evidence, route
  3. Gate enforcement, golden few-shot parity, MinHash dedup
  4. Crash-safe incremental checkpoint

Generator: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage2_extract.py --only-convergent  # Skip single-source clusters
    python3 pipeline/stage2_extract.py --provider mlx     # Use MLX instead of OMLX
"""

import argparse
import ast
import json
import os
import random
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    GEN_MODEL,
    S2_GATE_ENABLED,
    S2_GATE_STRICT,
    S2_HIGH_COHESION_THRESHOLD,  # C12: config-driven cohesion tiers
    S2_MED_COHESION_THRESHOLD,   # C12: config-driven cohesion tiers
    S2_GOLDEN_INJECT,
    S2_GOLDEN_MAX,
    S2_GOLDEN_NEGATIVE,
    S2_GOLDEN_PATH,
    S2_GOLDEN_POSITIVE,
    S2_MAX_CLUSTER_SAMPLES,
    S2_MAX_PROBE_SAMPLES,
    S2_MAX_WORKERS,
    S2_MINHASH_NUM_PERM,
    S2_MINHASH_THRESHOLD,
    S2_OMLX_RETRY,
    S2_SPLIT_KMEANS_RANDOM_STATE,
    S2_SPLIT_PROBE_ENABLED,
    S2_SPLIT_PROBE_MAX_COHESION,
    S2_SPLIT_PROBE_MIN_SIZE,
    S15_MIN_SOURCE_DIVERSITY,
    STAGE1_5_CHECKPOINT,
    STAGE1_CHECKPOINT,
    STAGE2_CHECKPOINT,
    STAGE2_PROBE_CACHE,
)
from pipeline.stamp import get_pipeline_commit, make_hash_id, stamp_record

# D2276: Hybrid gate — DSPy-inspired pre-extraction filter (BUG-085 fix)
try:
    from pipeline.hybrid_gate import HybridGate
    from pipeline.hybrid_gate import format_segments_for_gate as _fmt_segs_gate
    _HYBRID_GATE_AVAILABLE: bool = True
except ImportError:
    _HYBRID_GATE_AVAILABLE = False
    HybridGate = None  # type: ignore[assignment]
    _fmt_segs_gate = None  # type: ignore[assignment]

# ── Constants (T0.1: de-hardcoded — sourced from pipeline_config.yaml) ────
MAX_CLUSTER_SAMPLES: int = S2_MAX_CLUSTER_SAMPLES      # Max segments to feed per cluster (from config)
MIN_CONVERGENT_BOOKS: int = S15_MIN_SOURCE_DIVERSITY

# D2180: Minimum viable FB schema for LLM output validation (T2.2)
# Checks structural integrity of LLM JSON output before it enters the pipeline.
# Prevents malformed/missing-field outputs from corrupting downstream stages.
_FB_REQUIRED_FIELDS: dict[str, tuple[type, int]] = {
    "name": (str, 3),                # Must be string, ≥3 chars
    "definition": (str, 30),         # Must be string, ≥30 chars
    "mechanism": (str, 0),           # Must be string (can be empty for non-causal)
    "boundary": (str, 0),            # Must be string
    "consequence": (str, 0),         # Must be string
    "is_summary": (bool, 0),         # Must be boolean
    "extraction_type": (str, -1),     # D2214: optional — Qwen3-Coder doesn't include it; default inserted
    "content_type": (str, -1),       # D2214: optional — classification, not content
    "elaboration": (str, -1),        # D2215: optional — Qwen3-Coder omits entirely; empty string is valid
    "route": (str, 0),               # Must be string
}
_VALID_ROUTES: frozenset[str] = frozenset({"FB", "NULL"})
_VALID_CONTENT_TYPES: frozenset[str] = frozenset({
    "principle", "process_template", "process_instance",
    "growth_edge", "tool_instruction",
})


def validate_fb_output(result: dict) -> tuple[bool, list[str]]:
    """D2180: Validate LLM JSON output against minimum FB schema (T2.2).

    Performs structural validation only — does not check classification
    fields (added in Stage 4). Catches missing fields, wrong types,
    and invalid enum values before data enters the pipeline.

    Args:
        result: Dict from LLM JSON output (single principle).

    Returns:
        (is_valid, error_messages) — is_valid=False means reject this FB.
    """
    errors: list[str] = []

    if not isinstance(result, dict):
        return False, [f"Expected dict, got {type(result).__name__}"]

    # Check required fields
    # D2215: min_len < 0 means optional (field may be absent). min_len >= 0 means required.
    for field, (expected_type, min_len) in _FB_REQUIRED_FIELDS.items():
        if field not in result:
            if min_len < 0:
                continue  # Optional field — absent is fine
            errors.append(f"Missing required field: '{field}'")
            continue

        val = result[field]
        if not isinstance(val, expected_type):
            errors.append(
                f"Field '{field}' type mismatch: expected {expected_type.__name__}, "
                f"got {type(val).__name__}"
            )
            continue

        if expected_type is str and min_len > 0 and len(str(val).strip()) < min_len:
            errors.append(
                f"Field '{field}' too short: {len(str(val).strip())} chars "
                f"(need ≥{min_len})"
            )

    # Validate enum fields if present
    route = str(result.get("route", "")).strip().upper()
    if route and route not in _VALID_ROUTES:
        errors.append(f"Invalid route '{route}': must be FB or NULL")

    ctype = str(result.get("content_type", "")).strip()
    if ctype and ctype not in _VALID_CONTENT_TYPES:
        errors.append(f"Invalid content_type '{ctype}'")

    return len(errors) == 0, errors

# D2163: Principle Discovery Gate — probe thresholds (T0.1: now from config)
# D2176: Lowered MIN_SIZE from 50→20. A 40-segment cluster with 2 distinct
# principles would previously escape the gate and get compressed into ONE FB.
# The 291:1 compression death spiral was partly due to the gate being too conservative.
SPLIT_PROBE_ENABLED: bool = S2_SPLIT_PROBE_ENABLED        # Master switch for the probe (from config)
SPLIT_PROBE_MIN_SIZE: int = S2_SPLIT_PROBE_MIN_SIZE       # Only probe clusters with >N segments (from config)
SPLIT_PROBE_MAX_COHESION: float = S2_SPLIT_PROBE_MAX_COHESION  # Only probe clusters with cohesion below this (from config)
SPLIT_KMEANS_RANDOM_STATE: int = S2_SPLIT_KMEANS_RANDOM_STATE  # Deterministic k-means seed (from config)
# ── Convergent extraction system prompt (v3.0: cluster-before-extract) ────

SYSTEM_PROMPT = """You are a convergent principle extraction engine. You receive multiple related text
passages from DIFFERENT books. Your task is to identify the underlying principle(s)
that transcend any single source — the causal mechanism(s), concept(s), or method(s) that
these passages collectively reveal.

D2182: Changed extraction bias from conservative-merge to aggressive-split.
The 291:1 compression death spiral (323K segments → ~800 FBs) was caused by
forcing one principle per cluster. False splits are recoverable (S4 MinHash dedup).
False merges permanently lose information.

If the passages describe genuinely distinct mechanisms (different cause→effect chains),
extract each as a separate principle. If they describe different facets of ONE mechanism,
merge them into a single principle. When in doubt, SPLIT — it's better to have
two related FBs that Stage 4 can deduplicate than one bloated summary.

A convergent principle is:
- A concise statement of WHY something works, WHEN it applies, and WHAT its limits are
- Synthesized from patterns across ALL provided passages, not just one
- NOT a summary of any single passage
- NOT a list of what each passage says
- NOT a vague generalization that ignores specifics

PRINCIPLE STRUCTURE (required for every extraction):
1. name: 3-7 word concept name (title case, precise)
2. definition: 2-3 CONCISE sentences stating WHAT the principle IS. Be specific, not generic.
   ❌ Do NOT explain HOW it works (that's mechanism).
   ❌ Do NOT describe WHEN it applies/fails (that's boundary).
   ❌ Do NOT state WHAT happens as a result (that's consequence).
   ✅ Just name the phenomenon, pattern, or insight — crisp and scannable.
3. mechanism: "X causes/enables/prevents Y because Z" — the causal chain. HOW it works.
4. boundary: "The principle applies when [condition]. It fails when [counter-condition]."
5. consequence: "Because of this principle, [what follows]."
6. elaboration: 3-5 sentences of deeper nuance — edge cases, exceptions,
   and how the mechanism behaves under different conditions. Empty string
   if the passages genuinely add nothing beyond mechanism/boundary.
7. is_summary: true ONLY if you can only restate the passages without identifying
   a convergent mechanism. Be honest — self-flag if summarizing.
8. extraction_type: "causal_mechanism" if X→Y because Z. "empirical_pattern" if strong
   correlation without proven causal chain. "normative_heuristic" if practical rule of thumb.
   "descriptive_model" if classification system or taxonomy describing WHAT
   categories exist and how they relate — patterns of identity/organization
   rather than causal mechanisms (what type? how organized?).
9. content_type: "principle" (reusable concept), "process_template" (repeatable how-to),
   "process_instance" (case study), "growth_edge" (speculative insight),
   "tool_instruction" (tool-specific command).

EXTRACTION BOUNDARY — extract if and only if:
1. The passages collectively reveal a CAUSAL MECHANISM (X→Y because Z), OR
2. They converge on a CONCEPT with boundary conditions, OR
3. They demonstrate a repeatable METHOD with failure modes

Do NOT extract if passages:
- Share a topic but don't converge on a mechanism
- Only come from ONE book (no cross-source synthesis possible)
- Are about tool-specific features bound to one platform
- State outcomes without mechanisms ("good leadership matters")

EVIDENCE: For every claim in the principle, there must be a verbatim passage that
supports it. Include up to 5 verbatim evidence passages from the source texts.

ROUTING:
- route: "FB" (convergent principle → Stage 4 classifies) |
         "NULL" (no extractable principle — skip cluster)

When in doubt, route NULL. False positives pollute; false negatives leave gaps.
Classification (depth, domains, discipline) is Stage 4's job — do NOT include those fields.
Stage 2 extracts principles; Stage 4 classifies them (D2138/D2139).

Return ONLY a JSON object with these EXACT keys. No markdown, no explanation.

Example output:
{
  "name": "Value-First Demonstration",
  "definition": "Demonstrating concrete value before requesting commitment converts prospects at higher rates than persuasion-first approaches. The principle describes a product-led growth pattern where immediate tangible benefit replaces sales narrative as the primary conversion driver.",
  "mechanism": "Direct experience of value eliminates skepticism toward unverified claims because the prospect's own senses provide the proof, making external persuasion unnecessary.",
  "boundary": "Applies when value is demonstrable within minutes. Fails when value requires long-term usage to perceive (e.g., enterprise infrastructure, health supplements).",
  "consequence": "Products that can demonstrate value immediately grow faster through product-led adoption than those relying on sales narratives.",
  "is_summary": false,
  "extraction_type": "causal_mechanism",
  "content_type": "principle",
  "evidence_passages": [
    "Dropbox used a 3-minute demo video showing file sync... beta signups jumped from 5,000 to 75,000.",
    "The best SaaS companies demonstrate value before asking for money. Slack let users invite teammates before requiring payment."
  ],
  "route": "FB"
}"""


# ── Gate enforcement (D2080, preserved from v2.2) ──────────────────────────

def enforce_gate(extractions: list[dict], strict: bool = True) -> tuple[list[dict], int]:
    """Post-extraction gate enforcement. Forces [] on gate=NO with content."""
    cleaned: list[dict] = []
    violations: int = 0
    for item in extractions:
        if not isinstance(item, dict):
            continue
        gate: str = item.get("gate", "").strip().upper() if "gate" in item else ""
        route: str = item.get("route", "").strip().upper()
        if gate == "NO" or route == "NULL":
            has_content: bool = bool(item.get("text") or item.get("definition") or item.get("name"))
            if has_content:
                violations += 1
            cleaned.append({"route": "NULL"})
        else:
            cleaned.append(item)
    return cleaned, violations


# ── Data loading ───────────────────────────────────────────────────────────

def load_clusters() -> list[dict]:
    """Load clusters from Stage 1.5 checkpoint."""
    if not STAGE1_5_CHECKPOINT.exists():
        # Fallback: try old Stage 3 clusters
        old_path = CHECKPOINT_DIR / "stage3_cluster.jsonl"
        if old_path.exists():
            print("   ⚠️  Stage 1.5 not found, falling back to Stage 3 clusters")
            checkpoint = old_path
        else:
            print("❌ No clusters found. Run stage1_5_embed_cluster.py first.")
            sys.exit(1)
    else:
        checkpoint = STAGE1_5_CHECKPOINT

    clusters: list[dict] = []
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if line:
                clusters.append(json.loads(line))
    return clusters


def load_segments() -> dict[str, dict]:
    """Load segments from Stage 1, indexed by segment_id."""
    if not STAGE1_CHECKPOINT.exists():
        print("❌ Stage 1 checkpoint not found. Run stage1_chunk.py first.")
        sys.exit(1)

    segments: dict[str, dict] = {}
    with open(STAGE1_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seg: dict = json.loads(line)
            seg_id: str = seg.get("segment_id", "")
            if seg_id:
                segments[seg_id] = seg
    return segments


# ── Prompt building ────────────────────────────────────────────────────────

def build_convergent_prompt(
    cluster: dict,
    segments: dict[str, dict],
) -> tuple[str, list[str]]:
    """Build convergent extraction prompt for one cluster.

    Args:
        cluster: Cluster dict with segment_ids, source_books, cohesion.
        segments: Indexed segment dicts by segment_id.

    Returns:
        Tuple of (prompt_text, evidence_passages_for_output).
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    cohesion: float = cluster.get("cohesion", 0.5)

    # Sample segments: fewer for high-cohesion clusters
    # D2215: capped at MAX_CLUSTER_SAMPLES to avoid OMLX memory guard (Qwen3.6 KV cache)
    if cohesion >= S2_HIGH_COHESION_THRESHOLD:
        n_samples: int = min(3, MAX_CLUSTER_SAMPLES)
    elif cohesion >= S2_MED_COHESION_THRESHOLD:
        n_samples: int = min(5, MAX_CLUSTER_SAMPLES)
    else:
        n_samples: int = MAX_CLUSTER_SAMPLES

    # D2161: Stratified sampling by source book — ensures all books represented
    # Group segments by source book
    book_segments: dict[str, list[str]] = {}
    for sid in seg_ids:
        seg: dict | None = segments.get(sid)
        if seg is None:
            continue
        book: str = seg.get("source_book", "unknown")
        book_short: str = book.split("/")[-1].replace(".md", "")[:40] if book else "unknown"
        book_segments.setdefault(book_short, []).append(sid)

    # Sample proportionally: at least 1 from each book, then fill remaining slots
    sampled: list[str] = []
    n_books: int = len(book_segments)
    if n_books == 0:
        sampled = seg_ids[:n_samples]
    else:
        # First pass: take 1 from each book (round-robin through books)
        book_list: list[str] = list(book_segments.keys())
        book_idx: int = 0
        book_consumed: dict[str, int] = {b: 0 for b in book_list}
        while len(sampled) < n_samples:
            book: str = book_list[book_idx % n_books]
            segs: list[str] = book_segments[book]
            pos: int = book_consumed[book]
            if pos < len(segs):
                sampled.append(segs[pos])
                book_consumed[book] = pos + 1
            book_idx += 1
            # Break if all books exhausted
            if all(book_consumed[b] >= len(book_segments[b]) for b in book_list):
                break

    books_seen: set[str] = set()
    texts: list[str] = []
    evidence_passages: list[str] = []

    for i, sid in enumerate(sampled):
        seg: dict | None = segments.get(sid)
        if seg is None:
            continue
        text: str = seg.get("text", "")[:400]
        book: str = seg.get("source_book", "unknown")
        book_short: str = book.split("/")[-1].replace(".md", "")[:40] if book else "unknown"
        books_seen.add(book_short)
        texts.append(f"[{i+1}] ({book_short}): {text}")
        evidence_passages.append(text)

    source_summary: str = ", ".join(sorted(books_seen)[:5])
    # ── Build prompt ─────────────────────────────────────────────────────

    prompt: str = f"""I have {len(sampled)} passages from {len(books_seen)} books: {source_summary}

{"─" * 40}
{" | ".join(texts)}
{"─" * 40}

Extract the convergent principle(s). If genuinely distinct mechanisms exist, return a
JSON array of principle objects. If only ONE mechanism, return a single object.
Each principle must have:
- name, definition, mechanism, boundary, consequence, elaboration (3-5 sentences; empty string if no added nuance), is_summary (bool), evidence_passages (up to 5 verbatim quotes)
- route: "FB" (convergent principle -> Stage 4 classifies) | "NULL" (no principle)

No principle -> {{"route": "NULL"}}

Classification (depth, domains, discipline) happens in Stage 4 -- do NOT include those fields here."""

    return prompt, evidence_passages


# ── Simplified single-source prompt (D2148: tiered extraction) ─────────────

SINGLE_SOURCE_SYSTEM: str = (
    "You extract principles from text passages. "
    "Return a JSON object with these EXACT keys:\n"
    "name, definition, mechanism, boundary, consequence, "
    "is_summary (bool), "
    "extraction_type (\"causal_mechanism\"|\"empirical_pattern\"|\"normative_heuristic\"), "
    "content_type (\"principle\"|\"process_template\"|\"process_instance\"|\"growth_edge\"|\"tool_instruction\"), "
    "route (\"FB\" or \"NULL\").\n"
    "extraction_type=causal_mechanism if clear X\u2192Y because Z. "
    "empirical_pattern if strong correlation without proven causal chain. "
    "normative_heuristic if practical rule of thumb. "
    "content_type=principle for reusable concepts, process_template for repeatable methods, "
    "process_instance for case studies, growth_edge for speculative insights, "
    "tool_instruction for tool-specific commands. "
    "If the passages are just factual descriptions without a principle, "
    'return {{\"route\": \"NULL\"}}.'
)
# ── Singleton extraction prompt (D2149: single-segment, no synthesis) ──────

SINGLETON_SYSTEM: str = (
    "You extract and classify content from a single text passage. "
    "Return a JSON object with these EXACT keys:\n"
    "name, definition, mechanism, boundary, consequence, "
    "is_summary (bool), "
    "extraction_type (\"causal_mechanism\"|\"empirical_pattern\"|\"normative_heuristic\"|\"none\"), "
    "content_type (\"principle\"|\"process_template\"|\"process_instance\"|\"growth_edge\"|\"tool_instruction\"), "
    "route (\"FB\" or \"NULL\").\n"
    "MAPPING RULES:\n"
    "- extraction_type=causal_mechanism + reusable concept → content_type=principle\n"
    "- extraction_type=empirical_pattern (correlation without proven cause) → content_type=growth_edge\n"
    "- extraction_type=normative_heuristic (rule of thumb): → content_type=process_template if a repeatable method, else content_type=principle\n"
    "- Tool-specific commands/features → content_type=tool_instruction\n"
    "- Case studies/specific examples → content_type=process_instance\n"
    "- extraction_type=none + no principle → route=NULL\n"
    "If the passage contains no extractable principle, return {\"route\": \"NULL\"}."
)

def build_single_source_prompt(
    cluster: dict,
    segments: dict[str, dict],
) -> tuple[str, list[str]]:
    """Build simplified prompt for single-source (non-convergent) clusters.

    D2148: Single-source clusters don't need convergence synthesis.
    Simpler prompt → faster extraction (~4s vs ~9s).
    Returns fewer fields (no boundary/consequence/convergence synthesis).
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    sampled: list[str] = seg_ids[:5]  # Fewer segments for single-source
    texts: list[str] = []
    evidence_passages: list[str] = []

    for i, sid in enumerate(sampled):
        seg: dict | None = segments.get(sid)
        if seg is None:
            continue
        text: str = seg.get("text", "")[:300]
        texts.append(f"[{i+1}] {text}")
        evidence_passages.append(text)

    prompt: str = "\n".join(texts)
    return prompt, evidence_passages


# ── Golden few-shot (D2080, preserved from v2.2) ────────────────────────────

def load_golden_parity(
    golden_path: str | None,
    pos_count: int,
    neg_count: int,
    max_total: int,
) -> tuple[list[dict], list[dict], int]:
    """Load golden examples and subsample to parity."""
    if golden_path is None or not os.path.exists(str(golden_path)):
        return [], [], 0

    try:
        import yaml
        with open(str(golden_path)) as f:
            golden = yaml.safe_load(f)
    except Exception:
        return [], [], 0

    examples: list[dict] = golden.get("examples", [])
    all_pos: list[dict] = [e for e in examples if e.get("should_extract") and e.get("id") != "GE-001"]
    all_neg: list[dict] = [e for e in examples if not e.get("should_extract")]
    # D2159: deterministic golden selection (seed 42; TODO: move to config pipeline_config.yaml → stage2.golden_seed)
    random.seed(42)
    random.shuffle(all_pos)
    random.shuffle(all_neg)

    pos: list[dict] = all_pos[:min(pos_count, len(all_pos))]
    neg: list[dict] = all_neg[:min(neg_count, len(all_neg))]
    while len(pos) + len(neg) > max_total:
        if len(pos) > len(neg):
            pos.pop()
        elif neg:
            neg.pop()
        else:
            break

    return pos, neg, len(pos) + len(neg)


# ── MinHash dedup infrastructure ────────────────────────────────────────────

def init_minhash_lsh() -> tuple:
    """Initialize MinHash LSH index for near-dedup."""
    try:
        from datasketch import MinHashLSH
        lsh = MinHashLSH(threshold=S2_MINHASH_THRESHOLD, num_perm=S2_MINHASH_NUM_PERM)
        return lsh, True
    except ImportError as e:
        raise ImportError("datasketch required for MinHash near-dedup. pip install datasketch") from e


def make_minhash(text: str, num_perm: int = S2_MINHASH_NUM_PERM):
    """Create a MinHash signature using 3-gram character shingles.

    D2178: Changed from word-level to 3-gram character shingles.
    Word-level MinHash fails on semantically identical principles with different
    wording (e.g., "Value-First Demonstration" vs "Demonstrate Value Before Asking").
    3-gram character shingles capture sub-word structure and are more robust to
    paraphrasing while still being fast.
    """
    from datasketch import MinHash
    mh = MinHash(num_perm=num_perm)
    text_lower: str = text.lower()
    for i in range(len(text_lower) - 2):
        mh.update(text_lower[i:i + 3].encode("utf-8"))
    return mh


def is_near_duplicate(text: str, lsh, minhash_cache: dict) -> tuple[bool, str | None]:
    """Check if a principle is a near-duplicate of any existing principle."""
    if lsh is None:
        return False, None
    mh = make_minhash(text)
    results = lsh.query(mh)
    if results:
        return True, None
    sig: str = f"mh_{len(minhash_cache)}"
    lsh.insert(sig, mh)
    # D2208: LRU eviction — prevent unbounded cache growth
    if len(minhash_cache) >= 10000:
        oldest_key = next(iter(minhash_cache))
        del minhash_cache[oldest_key]
    minhash_cache[sig] = (text, mh)  # D2152: store MinHash object for jaccard comparison
    return False, sig


# ── LLM calling ─────────────────────────────────────────────────────────────

def call_llm(prompt: str, system: str, model: str, provider: str = "omlx",
             few_shot: str | None = None) -> dict | None:
    """Call LLM for convergent extraction. Returns parsed JSON dict or None.

    Args:
        prompt: The cluster-specific extraction prompt.
        system: The system prompt with schema instructions.
        model: Model name to use.
        provider: 'omlx' or 'mlx'.
        few_shot: Optional formatted few-shot examples to inject into system prompt.
    """
    # Inject golden few-shot examples into system prompt
    if few_shot:
        system = system + "\n\n" + few_shot

    max_tokens: int = 2048

    if provider == "mlx":
        try:
            from pipeline.providers.mlx_provider import get_mlx_provider
            prov = get_mlx_provider(role="generator")
            result = prov.generate_json(prompt=prompt, system=system, max_tokens=max_tokens)
            return json.loads(result.text)
        except Exception as e:
            print(f"      ⚠️  MLX error: {e}, falling back to OMLX")
            # Fall through to OMLX

    # OMLX path
    try:
        from pipeline.omlx_call import CircuitOpenError, call_omlx_json
        return call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=max_tokens)
    except CircuitOpenError:
        # D2211: Circuit breaker open — abort, don't return None
        raise
    except Exception as e:
        print(f"      ❌ LLM error: {e}")
        return None


def format_golden_fewshot(pos_examples: list[dict], neg_examples: list[dict] | None = None) -> str:
    """Format golden examples as few-shot prompt text for LLM injection.

    Args:
        pos_examples: Positive golden examples with expected_fb outputs.
        neg_examples: Optional negative examples (rejection training).

    Returns:
        Formatted few-shot string to append to system prompt.
    """
    if not pos_examples:
        return ""

    parts: list[str] = ["# FEW-SHOT EXAMPLES\n"]
    parts.append("Study these examples of correct convergent principle extraction:\n")

    for i, ex in enumerate(pos_examples[:5], 1):
        fb = ex.get("expected_fb", {})
        # D2206: expected_fb may be a single dict OR a list of dicts (1:N extraction)
        fbs = fb if isinstance(fb, list) else [fb]
        source_books = ex.get("source_books", [])
        rationale = ex.get("rationale", "")

        parts.append(f"## Example {i}: {fbs[0].get('name', 'Untitled')}")
        parts.append(f"Sources: {', '.join(source_books[:3])}")
        for j, fb_item in enumerate(fbs, 1):
            label = "Extracted principle:" if len(fbs) == 1 else f"Extracted principle {j} of {len(fbs)}:"
            parts.append(label)
            parts.append("```json")
            # Build a clean JSON showing only the output fields
            # NOTE: Depth removed from S2 (A-001/D2241). Classified in Stage 4.
            # extraction_type kept — it's a content property, not cross-domain classification.
            output = {
                "name": fb_item.get("name", ""),
                "definition": fb_item.get("definition", ""),
                "mechanism": fb_item.get("mechanism", ""),
                "boundary": fb_item.get("boundary", ""),
                "consequence": fb_item.get("consequence", ""),
                "extraction_type": fb_item.get("extraction_type", "causal_mechanism"),
                "is_summary": fb_item.get("is_summary", False),
                "evidence_passages": fb_item.get("evidence_passages", [])[:2],
                "route": fb_item.get("route", "FB"),
            }
            parts.append(json.dumps(output, indent=2, ensure_ascii=False))
            parts.append("```")
        if rationale:
            # Truncate rationale to 1-2 key sentences
            first_sentence = rationale.strip().split(".")[0] + "."
            parts.append(f"Key insight: {first_sentence}")
        parts.append("")

    if neg_examples:
        parts.append("## REJECTION EXAMPLES")
        parts.append("These clusters should produce route=NULL:\n")
        for i, ex in enumerate(neg_examples[:2], 1):
            source_books = ex.get("source_books", [])
            rationale = ex.get("rationale", "")
            first_sentence = rationale.strip().split(".")[0] + "." if rationale else "No principle found."
            parts.append(f"- Cluster from {', '.join(source_books[:2])}: {first_sentence}")
        parts.append("")

    parts.append("---")
    parts.append("Now apply the same extraction rigor to the cluster below.")
    return "\n".join(parts)


# ── Main stage ─────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════
# D2163: Principle Discovery Gate — 1:N extraction from clusters
# ═══════════════════════════════════════════════════════════════════════════

PRINCIPLE_DISCOVERY_SYSTEM: str = (
    "You are a principle-counting engine. Given passages from a semantic cluster, "
    "determine how many DISTINCT, non-overlapping causal mechanisms or heuristics are present. "
    "Two passages discuss the SAME principle if they describe the same cause→effect chain "
    "or the same decision rule. They are DIFFERENT if they describe different mechanisms "
    "even if the topic is similar. Return ONLY a JSON object."
)

PRINCIPLE_DISCOVERY_PROMPT: str = (
    "Analyze these {n_passages} passages from {n_books} books.\n\n"
    "{passages_text}\n\n"
    "How many DISTINCT, non-overlapping causal mechanisms or heuristics are present here? "
    "Return ONLY: {{\"principle_count\": N}} where N is 0-4.\n"
    "- N=0: no extractable principle (pure description, table of contents, etc.)\n"
    "- N=1: all passages discuss the same underlying mechanism\n"
    "- N=2-4: multiple distinct mechanisms present\n\n"
    "Be CONSERVATIVE — only split when the mechanisms are genuinely distinct, "
    "not just different aspects of the same principle."
)


def discover_principles(
    cluster: dict,
    segments: dict[str, dict],
    provider: str = "maxwell_omlx",
    error_counter: list[int] | None = None,  # D2211: mutable container for nonlocal probe error count
) -> int:
    """Probe a cluster to count distinct principles via Phi-4-mini.

    Only called for convergent clusters above size/cohesion thresholds.
    Returns principle_count (0-4). Returns 1 on any error (fail-safe: don't split).

    Args:
        error_counter: Optional mutable list[int] for tracking probe failures
                       across calls without shared global state. If provided,
                       error_counter[0] is incremented on LLM failures.
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    if not seg_ids:
        return 1

    # D2173: Source-stratified sampling for the discovery probe.
    #
    # OLD: Positional sampling (seg[0], seg[step], seg[2*step]...) — blinded the
    # probe to semantic diversity. If Principle A dominates the first half of a
    # 200-segment cluster and Principle B the second half, the probe might only
    # see A and return principle_count=1, failing to split the cluster.
    #
    # NEW: Round-robin across source books (matching D2161 approach). Ensures
    # every book is represented. If there are distinct principles from different
    # books, the probe sees all of them. Target 12-15 samples with max 2 per book.
    MAX_PROBE_SAMPLES: int = S2_MAX_PROBE_SAMPLES  # T0.1: from config, was 15
    MAX_PER_BOOK: int = 2

    # Group segment IDs by source book
    book_to_segids: dict[str, list[str]] = {}
    for sid in seg_ids:
        seg: dict | None = segments.get(sid)
        if seg is None:
            continue
        book: str = seg.get("source_book", "unknown")
        book_short: str = book.split("/")[-1].replace(".md", "")[:50] if book else "unknown"
        book_to_segids.setdefault(book_short, []).append(sid)

    # Round-robin across books: take 1 from each book per pass, up to MAX_PER_BOOK
    sampled_ids: list[str] = []
    book_lists: list[tuple[str, list[str], int]] = [
        (book, segs, 0) for book, segs in book_to_segids.items()
    ]
    while len(sampled_ids) < MAX_PROBE_SAMPLES:
        added_this_pass: bool = False
        for i, (book, segs, taken) in enumerate(book_lists):
            if taken >= MAX_PER_BOOK or taken >= len(segs):
                continue
            sampled_ids.append(segs[taken])
            book_lists[i] = (book, segs, taken + 1)
            added_this_pass = True
            if len(sampled_ids) >= MAX_PROBE_SAMPLES:
                break
        if not added_this_pass:
            break  # All books exhausted

    # Build passage texts with book labels
    books_seen: set[str] = set()
    passage_texts: list[str] = []
    for sid in sampled_ids:
        seg = segments.get(sid)
        if seg is None:
            continue
        text: str = seg.get("text", "")[:300]
        book: str = seg.get("source_book", "unknown")
        book_short: str = book.split("/")[-1].replace(".md", "")[:30] if book else "unknown"
        books_seen.add(book_short)
        passage_texts.append(f"[{book_short}]: {text}")

    passages_blob: str = "\n\n".join(passage_texts)
    prompt: str = PRINCIPLE_DISCOVERY_PROMPT.format(
        n_passages=len(passage_texts),
        n_books=len(books_seen),
        passages_text=passages_blob,
    )

    # Phi-4-mini probe (fast, ~1.5s) — use VERIFY_MODEL for speed
    # D2209: Route through call_llm to respect --provider flag (was hardcoded OMLX).
    try:
        from pipeline.pipeline_paths import VERIFY_MODEL
        result: dict | None = call_llm(
            prompt=prompt,
            model=VERIFY_MODEL,
            system=PRINCIPLE_DISCOVERY_SYSTEM,
            provider=provider,
        )
        if result is None:
            # D2211: call_llm returned None → LLM infrastructure failure
            if error_counter is not None:
                error_counter[0] += 1
            import sys
            print(f"   ⚠️  Discovery probe: LLM returned None for {cluster.get('cluster_id', '?')}",
                  file=sys.stderr)
            return 1
        if isinstance(result, dict):
            count: int = result.get("principle_count", 1)
            if isinstance(count, int) and 0 <= count <= 4:
                return count
            # D2211: dict returned but count invalid → also a failure
            if error_counter is not None:
                error_counter[0] += 1
    except CircuitOpenError:
        # D2211: Breaker open — abort probe phase entirely
        raise
    except Exception as e:
        # D2177 (C16): Log probe failures — don't silently swallow.
        # Fail-safe: return 1 (don't split), but operator must know.
        import sys
        print(f"   ⚠️  Discovery probe failed for {cluster.get('cluster_id', '?')}: {type(e).__name__}: {e}",
              file=sys.stderr)

    return 1


# D2212: Module-level SentenceTransformer cache (F-H5 fix).
# split_cluster_by_kmeans loads the model on every call (~611 times in probe phase,
# 500MB model × 2-3s per load = ~25 min wasted). Caching eliminates this.
_st_model_cache: dict[str, object] = {}
_st_model_lock: threading.Lock = threading.Lock()  # D2212: atomic first-load (threads can race)
_st_encode_lock: threading.Lock = threading.Lock()  # D2213: MPS not thread-safe — serialize encode()


def _get_st_model(model_name: str, device: str = "mps") -> object:
    """Return cached SentenceTransformer, loading on first call (thread-safe)."""
    if model_name not in _st_model_cache:
        with _st_model_lock:
            # Double-checked: another thread may have loaded it while we waited
            if model_name not in _st_model_cache:
                from sentence_transformers import SentenceTransformer
                _st_model_cache[model_name] = SentenceTransformer(model_name, device=device)
    return _st_model_cache[model_name]


def split_cluster_by_kmeans(
    cluster: dict,
    segments: dict[str, dict],
    n_principles: int,
) -> list[dict]:
    """Split a cluster into N sub-clusters via k-means on segment embeddings.

    Uses bge-small-en-v1.5 on MPS (same model as S1.5) for consistency.
    Each sub-cluster inherits metadata from the parent cluster.
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    if len(seg_ids) < n_principles * 2:
        # Too few segments to split meaningfully
        return [cluster]

    # Load segment texts
    texts: list[str] = []
    valid_ids: list[str] = []
    for sid in seg_ids:
        seg: dict | None = segments.get(sid)
        if seg is None:
            continue
        text: str = seg.get("text", "")
        if len(text) >= 30:
            texts.append(text[:1000])
            valid_ids.append(sid)

    if len(texts) < n_principles * 2:
        return [cluster]

    # Embed segments (same model as S1.5 for consistency)
    try:
        import numpy as np
        from sklearn.cluster import KMeans

        from pipeline.pipeline_paths import S15_EMBED_MODEL_HF

        # D2212: Cached model load (F-H5 fix — was loading 500MB model per call)
        model = _get_st_model(S15_EMBED_MODEL_HF)
        # D2213: MPS not thread-safe — serialize encode() across threads
        with _st_encode_lock:
            embeddings: np.ndarray = model.encode(texts, normalize_embeddings=True,
                                                    show_progress_bar=False)

        # K-means clustering
        kmeans = KMeans(n_clusters=n_principles, random_state=SPLIT_KMEANS_RANDOM_STATE,
                        n_init=10)
        labels: np.ndarray = kmeans.fit_predict(embeddings)

        # Build sub-clusters
        sub_clusters: list[dict] = []
        for label_idx in range(n_principles):
            sub_ids: list[str] = [
                valid_ids[i] for i in range(len(valid_ids))
                if labels[i] == label_idx
            ]
            if len(sub_ids) < 2:
                continue  # Skip degenerate sub-clusters

            # Compute source books for sub-cluster (D2176: canonical source_ids)
            from pipeline.book_metadata import resolve_source_ids
            sub_books: set[str] = set()
            for sid in sub_ids:
                seg = segments.get(sid)
                if seg:
                    sub_books.add(seg.get("source_book", "unknown"))
            sub_source_ids: set[str] = resolve_source_ids(list(sub_books))
            sub_sid_count: int = len(sub_source_ids)

            sub_cluster: dict = dict(cluster)
            sub_cluster["segment_ids"] = sub_ids
            sub_cluster["size"] = len(sub_ids)
            sub_cluster["source_books"] = list(sub_books)
            sub_cluster["source_ids"] = sorted(sub_source_ids)
            sub_cluster["source_diversity"] = sub_sid_count
            sub_cluster["is_convergent"] = sub_sid_count >= 2
            sub_cluster["parent_cluster_id"] = cluster.get("cluster_id", "?")
            sub_cluster["cluster_id"] = f"{cluster.get('cluster_id', '?')}_sub{label_idx}"
            sub_cluster["_is_sub_cluster"] = True
            sub_clusters.append(sub_cluster)

        if len(sub_clusters) >= 2:
            return sub_clusters
    except Exception:
        pass  # Fail-safe: return original cluster if k-means fails

    return [cluster]


def _load_probe_cache(
    convergent: list[dict],
    single_source: list[dict],
    only_convergent: bool,
) -> list[dict] | None:
    """Load cached probe targets when valid; None if absent, stale, or corrupt.

    Crash-resume for the split-probe phase — the one pipeline phase with no
    checkpoint. A crash after 2+ hours of probing previously lost everything.
    Cache key = corpus shape (convergent/single-source counts + mode flag) so a
    stale cache from a different corpus or run mode is ignored.
    """
    if not STAGE2_PROBE_CACHE.exists():
        return None
    try:
        with open(STAGE2_PROBE_CACHE) as f:
            pc: dict = json.load(f)
        # D2215: Always accept cache when corpus counts match, even if mode flag differs.
        # If cache was built without --only-convergent but we're now running with it,
        # load all targets — the caller filters to convergent-only after loading.
        if (
            pc.get("convergent_count") == len(convergent)
            and pc.get("single_source_count") == len(single_source)
        ):
            targets: list[dict] = pc.get("targets", [])
            return targets if targets else None
    except Exception as e:
        print(f"   ⚠️  Probe cache unreadable ({type(e).__name__}: {e}) — re-probing")
    return None


def _write_probe_cache(
    targets: list[dict],
    convergent: list[dict],
    single_source: list[dict],
    only_convergent: bool,
) -> None:
    """Persist probe-expanded targets for crash-resume. Crash-safe via safe_write."""
    try:
        payload: dict = {
            "convergent_count": len(convergent),
            "single_source_count": len(single_source),
            "only_convergent": only_convergent,
            "targets": targets,
        }
        safe_write(str(STAGE2_PROBE_CACHE), json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        print(f"   ⚠️  Probe cache write failed ({type(e).__name__}: {e})")


def run_stage2(
    provider: str = "omlx",
    only_convergent: bool = False,
    gate_enabled: bool = S2_GATE_ENABLED,
    gate_strict: bool = S2_GATE_STRICT,
    hybrid_gate: bool = False,
) -> None:
    """Run Stage 2: Convergent principle extraction from clusters.

    Args:
        provider: "omlx" or "mlx" for LLM inference.
        only_convergent: Skip single-source clusters.
        gate_enabled: Enable gate enforcement.
        gate_strict: Force [] on NULL-route with content.
        hybrid_gate: D2276 — Use DSPy-inspired pre-extraction gate to skip non-principle clusters.
    """
    # D2215: Force write-through logging (tee/nohup/pipe corrupt buffered output on macOS)
    # python3 -u should be enough, but TextIOWrapper on macOS still buffers on
    # non-TTY fds. write_through=True forces every write() to flush immediately.
    import io as _io
    import sys as _sys
    try:
        _sys.stdout = _io.TextIOWrapper(_sys.stdout.buffer, write_through=True, line_buffering=True)
        _sys.stderr = _io.TextIOWrapper(_sys.stderr.buffer, write_through=True, line_buffering=True)
    except (AttributeError, ValueError):
        pass  # already unbuffered or fd redirected

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Load clusters
    clusters: list[dict] = load_clusters()

    # Filter: convergent vs single-source
    convergent: list[dict] = [c for c in clusters if c.get("is_convergent")]
    single_source: list[dict] = [c for c in clusters if not c.get("is_convergent") and not c.get("is_noise", False)]
    noise: list[dict] = [c for c in clusters if c.get("is_noise", False)]

    if only_convergent:
        target_clusters: list[dict] = convergent
    else:
        target_clusters = convergent + single_source

    # Load segments
    segments: dict[str, dict] = load_segments()

    # Golden examples
    golden_path: str | None = S2_GOLDEN_PATH
    if golden_path and not os.path.isabs(str(golden_path)):
        golden_path = str(Path(__file__).resolve().parent.parent / golden_path)
    pos_ex, neg_ex, golden_total = load_golden_parity(
        golden_path, S2_GOLDEN_POSITIVE, S2_GOLDEN_NEGATIVE, S2_GOLDEN_MAX
    )

    # Format golden few-shot examples for LLM injection (D2127r3)
    few_shot_text: str = ""
    if S2_GOLDEN_INJECT and pos_ex:
        few_shot_text = format_golden_fewshot(pos_ex, neg_ex)
        print(f"   🎯 Golden few-shot: {len(pos_ex)} pos + {len(neg_ex)} neg examples ({len(few_shot_text)} chars)")

    # D2211: Health check — use stress_test (real chat requests, not just /v1/models)
    if provider == "omlx":
        from pipeline.omlx_call import CircuitOpenError, stress_test_omlx
        health = stress_test_omlx(verbose=False)
        if not health["healthy"]:
            print(f"❌ OMLX stress test FAILED: {health['verdict']}")
            for r in health["results"]:
                if r.get("error"):
                    print(f"   [{r['size']} chars]: {r['error']}")
            sys.exit(1)

    print(f"🧠 Stage 2: Convergent Extraction — {len(target_clusters)} clusters")
    print(f"   Convergent (≥{MIN_CONVERGENT_BOOKS} books): {len(convergent)}")
    print(f"   Single-source: {len(single_source)} | Noise: {len(noise)}")
    print(f"   Provider: {provider} | Model: {GEN_MODEL} | temp=0.0")
    print(f"   Golden: {golden_total} examples | Gate: {'on' if gate_enabled else 'off'}")
    print(f"   Hybrid Gate (D2276): {'✅ enabled' if hybrid_gate else 'off'} | Split Probe: {'on' if SPLIT_PROBE_ENABLED else 'off'}")
    print(f"{'='*60}")

    # D2276: Initialize hybrid gate if enabled — pre-filters clusters before extraction
    _hybrid_gate = None
    if hybrid_gate:
        if _HYBRID_GATE_AVAILABLE and HybridGate is not None:
            _hybrid_gate = HybridGate(provider=provider)
            print(f"   🚪 Hybrid gate initialized (model={_hybrid_gate._model})")
        else:
            print("   ⚠️  Hybrid gate requested but hybrid_gate.py not available — proceeding without gate")
            hybrid_gate = False

    # Helper: gather cluster segment texts for gate evaluation (D2276)
    def _gather_cluster_segments(cluster: dict, segs: dict) -> list[dict]:
        """Collect segment dicts for a cluster from the segments lookup."""
        member_ids = cluster.get("member_segment_ids", [])
        result = []
        for sid in member_ids:
            if sid in segs:
                result.append(segs[sid])
            if len(result) >= 8:  # Max 8 segments for gate efficiency
                break
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # D2163: Principle Discovery Gate — probe convergent clusters for N>1
    # ═══════════════════════════════════════════════════════════════════════
    split_count: int = 0
    extra_fbs_estimate: int = 0
    cached_targets: list[dict] | None = _load_probe_cache(convergent, single_source, only_convergent)
    if cached_targets is not None:
        target_clusters = cached_targets
        # D2215: If running --only-convergent but cache includes single-source,
        # filter to convergent-only targets. Cache built with full corpus can
        # serve both modes.
        if only_convergent:
            n_before: int = len(target_clusters)
            target_clusters = [t for t in target_clusters if t.get("is_convergent")]
            print(f"   📂 Probe cache loaded: {n_before} targets → {len(target_clusters)} convergent (--only-convergent filter)")
        else:
            print(f"   📂 Probe cache loaded: {len(target_clusters)} extraction targets — re-probe skipped")
    elif SPLIT_PROBE_ENABLED and convergent:
        print(f"\n🔍 Principle Discovery Gate: probing {len(convergent)} convergent clusters...")
        expanded_targets: list[dict] = []
        probes_run: int = 0
        probe_total: float = 0.0

        # Parallel probe (D2xxx): Phi-4 GPU calls + k-means CPU overlap via ThreadPool.
        # Same per-cluster decisions as sequential (kmeans random_state=42, per-cluster
        # independence); results rebuilt in original order for a deterministic cache.
        import concurrent.futures
        _qualifying: list[tuple[int, dict]] = [
            (i, c) for i, c in enumerate(convergent)
            if c.get("size", 0) > SPLIT_PROBE_MIN_SIZE
            and c.get("cohesion", 1.0) < SPLIT_PROBE_MAX_COHESION
        ]

        # D2211: Mutable error counter for nonlocal probe failure tracking
        probe_errors: list[int] = [0]

        def _probe_split(item: tuple[int, dict]) -> tuple[int, list[dict]]:
            """Probe one cluster; return (index, sub_clusters); [] if not split."""
            _i, _c = item
            try:
                _n: int = discover_principles(_c, segments, provider, error_counter=probe_errors)
                if _n > 1:
                    _sub: list[dict] = split_cluster_by_kmeans(_c, segments, _n)
                    if len(_sub) > 1:
                        return _i, _sub
            except CircuitOpenError:
                # D2211: Breaker open during probe — let it propagate
                raise
            except Exception as _e:
                probe_errors[0] += 1
                print(f"   ⚠️  probe worker error ({_c.get('cluster_id', '?')}): {type(_e).__name__}: {_e}")
            return _i, []

        _t0_all: float = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=S2_MAX_WORKERS) as _ex:
            _futures = [_ex.submit(_probe_split, item) for item in _qualifying]
            for _f in concurrent.futures.as_completed(_futures):
                _idx, _subs = _f.result()
                probes_run += 1
                if _subs:
                    _c = convergent[_idx]
                    split_count += 1
                    extra_fbs_estimate += len(_subs) - 1
                    print(f"   ✂️  {_c.get('cluster_id', '?')[:30]}: {_c.get('size', 0)}s/{_c.get('cohesion', 1.0):.3f}coh → {len(_subs)} principles, {len(_subs)} sub-clusters")
        probe_total = time.time() - _t0_all
        # Rebuild in original order (deterministic, cache-friendly)
        _split_map: dict[int, list[dict]] = {}
        for _f in _futures:
            _idx, _subs = _f.result()
            if _subs:
                _split_map[_idx] = _subs
        for _i, _c in enumerate(convergent):
            if _i in _split_map:
                expanded_targets.extend(_split_map[_i])
            else:
                expanded_targets.append(_c)

        # Add single-source clusters unchanged — but ONLY outside --only-convergent
        # (BUG-0XX: this extend previously ran unconditionally, silently defeating
        #  the --only-convergent flag and sending all single-source clusters to extraction)
        if not only_convergent:
            expanded_targets.extend(single_source)
        target_clusters = expanded_targets
        _write_probe_cache(expanded_targets, convergent, single_source, only_convergent)
        print(f"   ✅ Probe: {probes_run} clusters checked in {probe_total:.1f}s")
        print(f"   ✂️  Split: {split_count} clusters → +{extra_fbs_estimate} expected FBs")
        print(f"   📊 Total extraction targets: {len(target_clusters)} (was {len(convergent) + len(single_source)})")

        # D2211: Fail-closed — abort if probe error rate exceeds threshold
        if probes_run > 0 and probe_errors[0] / probes_run > 0.10:
            raise RuntimeError(
                f"❌ PROBE ABORT: {probe_errors[0]}/{probes_run} clusters failed "
                f"({probe_errors[0]/probes_run:.1%}). Aborting before extraction."
            )
        print(f"{'='*60}")

    # Dedup infrastructure
    lsh, minhash_ok = init_minhash_lsh()
    minhash_cache: dict = {}
    dedup_lock: threading.Lock = threading.Lock()  # D2212: thread safety for MinHash (F-H11 fix)
    all_fbs: list[dict] = []
    total_extracted: int = 0
    total_skipped: int = 0
    total_null: int = 0
    total_gate_violations: int = 0
    pipeline_commit: str = get_pipeline_commit()

    # Resume support
    processed_ids: set[str] = set()
    segids_file: str = str(STAGE2_CHECKPOINT) + ".segids"
    if STAGE2_CHECKPOINT.exists() and os.path.exists(segids_file):
        try:
            with open(STAGE2_CHECKPOINT) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_fbs.append(json.loads(line))
            with open(segids_file) as f:
                processed_ids = set(json.load(f))
            # D2215: Detect cluster-ID format mismatch between old segids and current probe cache.
            # Old probe used "cluster_N_subN", new probe uses "cluster_N_sN_subN". Zero overlap
            # means the segids are from a different probe format — discard them to avoid silent reprocessing.
            target_cids: set[str] = {c.get("cluster_id", "") for c in target_clusters}
            if processed_ids and not (processed_ids & target_cids):
                print(f"   ⚠️  Resume segids format mismatch — {len(processed_ids)} old IDs, 0 overlap with {len(target_cids)} targets")
                print("   ⚠️  Starting fresh — all clusters will be processed")
                processed_ids = set()
            else:
                print(f"   📋 Resuming: {len(processed_ids)} clusters processed → {len(all_fbs)} FBs")
                # D2215: CRITICAL — filter targets BEFORE submitting to executor.
                # Without this, workers re-process already-done clusters (~15h wasted)
                # and the main loop silently skips their output via `continue`.
                n_before_resume: int = len(target_clusters)
                target_clusters = [c for c in target_clusters
                                   if c.get("cluster_id") not in processed_ids]
                print(f"   📋 Remaining after resume filter: {len(target_clusters)} clusters "
                      f"(skipped {n_before_resume - len(target_clusters)} already-processed)")
        except Exception as e:
            # D2177 (C16): Don't silently discard all prior work on resume failure.
            # Log the error and start fresh — but the operator must know.
            import traceback
            print(f"   ⚠️  Resume checkpoint corrupted ({type(e).__name__}: {e})")
            print("   ⚠️  Starting fresh — prior progress discarded")
            print(f"   ⚠️  Traceback: {traceback.format_exc()[-300:]}")
            all_fbs = []
            processed_ids = set()

    # ── Worker: process one cluster (D2148: tiered + parallel) ──────────
    def _process_cluster(cluster: dict) -> list[dict]:
        """Process one cluster and return list of FB dicts (empty list if nothing extracted).

        D2178: Return type unified to list[dict] — no more dict|list ambiguity.
        Multi-principle extraction now handled uniformly by the caller loop.
        """
        cid: str = cluster.get("cluster_id", "?")
        is_conv: bool = cluster.get("is_convergent", False)
        # D2176: source_diversity from S1.5 uses canonical source_ids (not filenames).
        # Fallback: if source_ids available, use len(source_ids); else len(source_books).
        book_count: int = cluster.get("source_diversity",
                          len(cluster.get("source_ids", cluster.get("source_books", []))))

        # D2276: Hybrid gate — pre-filter before expensive extraction.
        # The gate is a cheap LLM call (~50 tokens, ~1s) vs full extraction (~28s).
        # From D2250 benchmark: gate is a perfect NEGATIVE filter (rejects 5/6 negatives).
        # Fail-open: gate error → proceed with extraction (prefer false positive to data loss).
        if hybrid_gate and is_conv and _hybrid_gate is not None:
            try:
                # Build compact segment text for gate decision
                raw_segs = _gather_cluster_segments(cluster, segments)
                seg_text = _fmt_segs_gate(raw_segs) if _fmt_segs_gate else "\n".join(
                    s.get("text", "")[:350] for s in raw_segs[:8]
                )
                gate_route = _hybrid_gate.decide(seg_text, cluster.get("source_books", []))
                if gate_route == "NULL":
                    return [{"_null": True, "cluster_id": cid, "_gate_reason": "hybrid-gate-NULL"}]
            except Exception:
                pass  # Gate failure → proceed with extraction (fail-open)

        # Tiered prompt: convergent = full synthesis, single-source = simplified
        # D2231: Removed "or book_count >= 2" — convergence gate is is_convergent
        # flag from S1.5 clustering (which already encodes source diversity).
        # Source count alone must not trigger convergent extraction.
        if is_conv:
            prompt, evidence_passages = build_convergent_prompt(cluster, segments)
            system = SYSTEM_PROMPT
        else:
            prompt, evidence_passages = build_single_source_prompt(cluster, segments)
            system = SINGLE_SOURCE_SYSTEM

        # Call LLM with retry
        result: dict | list | None = None
        for attempt in range(S2_OMLX_RETRY + 1):
            try:
                result = call_llm(
                    prompt, system, GEN_MODEL, provider,
                    few_shot=few_shot_text if few_shot_text and is_conv else None,
                )
                if result is not None:
                    break
            except CircuitOpenError:
                # D2211: Breaker open — abort extraction, preserve checkpoint
                raise
            except Exception:
                if attempt < S2_OMLX_RETRY:
                    time.sleep(2)
                    continue

        if result is None:
            return []

        # D2176: Handle both single-object and array responses.
        # If LLM returns [{...}, {...}], process each as a separate FB.
        # If LLM returns {...}, process as single FB (backward compatible).
        principles: list[dict] = result if isinstance(result, list) else [result]

        # D2178: Always return list — caller loop handles uniform iteration
        fbs: list[dict] = []
        for principle in principles:
            fb = _build_fb_from_result(principle, cluster, evidence_passages, cid)
            if fb:
                fbs.append(fb)
        return fbs


    def _build_fb_from_result(
        result: dict,
        cluster: dict,
        evidence_passages: list[str],
        cid: str,
    ) -> dict | None:
        """D2176: Build an FB record from a single extraction result.

        Extracted from _process_one to support both single and multi-principle returns.
        """
        # Check for NULL route
        route: str = result.get("route", "FB").strip().upper()
        if route == "NULL":
            return {"_null": True, "cluster_id": cid}

        # D2180: Schema validation (T2.2) — catch malformed LLM output before it enters pipeline
        is_valid, schema_errors = validate_fb_output(result)
        if not is_valid:
            # Log schema violations for debugging but don't crash — treat as NULL
            import sys as _sys
            print(f"   ⚠️  Schema validation failed for {cid}: {'; '.join(schema_errors[:3])}",
                  file=_sys.stderr)
            return {"_null": True, "cluster_id": cid, "_schema_errors": schema_errors}

        # Validate required fields — unified reading with fallback for single-source schema
        name: str = result.get("name", "").strip()
        definition: str = result.get("definition", "").strip()
        mechanism: str = result.get("mechanism", "").strip()
        boundary: str = result.get("boundary", result.get("application", "")).strip()
        consequence: str = result.get("consequence", result.get("failure_mode", "")).strip()
        is_summary: bool = result.get("is_summary", False)
        extraction_type: str = result.get("extraction_type", "causal_mechanism").strip()
        content_type: str = result.get("content_type", "principle").strip()

        # D2214: Removed redundant check — validate_fb_output already enforces definition ≥30 chars.
        # Qwen3-Coder produces concise definitions that pass validation but were caught here.
        if not name or not definition:
            return {"_null": True, "cluster_id": cid}

        # Gate: reject summaries
        if is_summary and gate_enabled:
            return {"_gate": True, "cluster_id": cid}

        # Build FB record
        fb_id: str = make_hash_id(name, definition)
        fb: dict = {
            "fb_id": fb_id,
            "name": name,
            "definition": definition,
            "mechanism": mechanism,
            "boundary": boundary,
            "consequence": consequence,
            "elaboration": result.get("elaboration", ""),  # D2215: was silently dropped — LLM produces it, builder discarded it
            "is_summary": is_summary,
            "extraction_type": extraction_type,
            "content_type": content_type,
            "evidence_passages": result.get("evidence_passages", evidence_passages[:5]),
            "evidence_passages_shown": evidence_passages,
            "route": route,
            "source_cluster": cid,
            "source_books": cluster.get("source_books", []),
            "source_ids": cluster.get("source_ids", []),
            "source_segments": cluster.get("segment_ids", []),
            "cluster_cohesion": cluster.get("cohesion", 0.0),
            "cluster_size": cluster.get("size", 0),
            "source_diversity": cluster.get("source_diversity",
                          len(cluster.get("source_ids", cluster.get("source_books", [])))),
            "is_convergent": cluster.get("is_convergent", True),
        }

        # Enrich with author/title/year (BUG-061 FIX)
        src_books_list: list[str] = cluster.get("source_books", [])
        if src_books_list:
            from pipeline.book_metadata import (
                build_citation,
                resolve_book_metadata,
                select_primary_source,
            )
            source_authors: list[dict] = []
            for sb in src_books_list:
                m = resolve_book_metadata(sb)
                source_authors.append({
                    "book": sb, "author": m.get("author", ""),
                    "title": m.get("title", ""), "year": m.get("year", ""),
                })
            fb["source_authors"] = source_authors
            fb["primary_source"] = select_primary_source(src_books_list, evidence_passages)
            prim = fb["primary_source"].get("book", src_books_list[0])
            prim_meta = next(
                (sa for sa in source_authors if sa["book"] == prim),
                {"author": "Unknown Author", "title": "Unknown Title"},
            )
            fb["citation"] = build_citation(
                prim_meta.get("author", ""), prim_meta.get("title", ""), prim,
            )

        fb = stamp_record(fb, gen_model=GEN_MODEL)
        fb["pipeline_commit"] = pipeline_commit

        # Attach minhash sig for dedup (processed post-collection)
        # D2212: Thread-safe — MinHashLSH is NOT thread-safe (F-H11 fix)
        if minhash_ok:
            with dedup_lock:
                _, sig = is_near_duplicate(definition, lsh, minhash_cache)
                if sig:
                    fb["minhash_signature"] = sig

        return fb

    # ── Parallel extraction (D2148: ThreadPool, config-driven) ────────────────
    max_workers: int = S2_MAX_WORKERS
    print(f"⚡ Processing {len(target_clusters)} clusters with {max_workers} parallel workers...")

    import concurrent.futures
    future_results: list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_cluster, c): i
            for i, c in enumerate(target_clusters)
        }
        completed: int = 0
        for future in concurrent.futures.as_completed(futures):
            idx: int = futures[future]
            cluster: dict = target_clusters[idx]
            cid: str = cluster.get("cluster_id", f"cluster_{idx}")
            if cid in processed_ids:
                completed += 1
                continue

            completed += 1
            try:
                fb_results = future.result()
            except CircuitOpenError:
                # D2211: Breaker open — cancel all futures, preserve checkpoint, abort
                print("\n❌ CIRCUIT BREAKER OPEN — aborting run")
                print(f"   Preserving {len(all_fbs)} FBs from {len(processed_ids)} clusters")
                for f in futures:
                    f.cancel()
                # Write checkpoint with current progress before aborting
                safe_write(STAGE2_CHECKPOINT,
                           "\n".join(json.dumps(fb, ensure_ascii=False) for fb in all_fbs) + "\n",
                           force_shrink=True)
                raise  # Abort the run
            except Exception as e:
                print(f"  [{completed}/{len(target_clusters)}] ❌ {cid}: {e}")
                continue

            is_conv: bool = cluster.get("is_convergent", False)
            conv_tag: str = "🌐" if is_conv else "📖"

            # D2178: _process_cluster now always returns list[dict]
            if not fb_results:
                print(f"  [{completed}/{len(target_clusters)}] ❌ {conv_tag} {cid}: LLM failed")
                continue

            for fb in fb_results:
                if fb.get("_null"):
                    total_null += 1
                    print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid}: NULL/skip")
                    continue

                if fb.get("_gate"):
                    total_gate_violations += 1
                    print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid}: summary gated")
                    continue

                # MinHash near-dedup (post-collection) — D2152: fixed jaccard comparison
                # D2212: Thread-safe — minhash_cache shared with worker threads (F-H11 fix)
                definition: str = fb.get("definition", fb.get("name", ""))
                if minhash_ok and fb.get("minhash_signature"):
                    sig: str = fb["minhash_signature"]
                    cur_mh = make_minhash(definition)
                    is_dup: bool = False
                    with dedup_lock:
                        for prev_fb in all_fbs:
                            prev_sig: str = prev_fb.get("minhash_signature", "")
                            if prev_sig and prev_sig in minhash_cache:
                                _, prev_mh = minhash_cache[prev_sig]
                                if cur_mh.jaccard(prev_mh) > S2_MINHASH_THRESHOLD:
                                    is_dup = True
                                    break
                    if is_dup:
                        total_skipped += 1
                        print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid}: near-duplicate")
                        continue

                all_fbs.append(fb)
                total_extracted += 1
            processed_ids.add(cid)
            book_count: int = cluster.get("source_diversity",
                          len(cluster.get("source_ids", cluster.get("source_books", []))))
            fb_names: str = ", ".join(f.get('name', '?')[:30] for f in fb_results[:3])
            if len(fb_results) > 3:
                fb_names += f" +{len(fb_results) - 3} more"
            print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid} "
                  f"({cluster.get('size', 0)} segs, {book_count} books) → {fb_names}")

            # D2154: Incremental checkpoint every 5 clusters (inside for future loop)
            if completed % 5 == 0:
                safe_write(
                    STAGE2_CHECKPOINT,
                    "\n".join(json.dumps(f, ensure_ascii=False) for f in all_fbs) + "\n",
                    force_shrink=True,
                )
                # Atomic segids
                import tempfile
                segids_tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".segids", delete=False,
                    dir=str(STAGE2_CHECKPOINT.parent)
                )
                try:
                    json.dump(list(processed_ids), segids_tmp)
                    segids_tmp.flush()
                    os.fsync(segids_tmp.fileno())
                    segids_tmp.close()
                    os.replace(segids_tmp.name, segids_file)
                except Exception:
                    if os.path.exists(segids_tmp.name):
                        os.unlink(segids_tmp.name)

    # Write final checkpoint
    safe_write(
        STAGE2_CHECKPOINT,
        "\n".join(json.dumps(f, ensure_ascii=False) for f in all_fbs) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Convergent FBs:     {total_extracted}")
    print(f"🚪 Gate violations:    {total_gate_violations} (self-flagged as summary)")
    print(f"⏭️  NULL routes:        {total_null}")
    print(f"🗑️  Near-duplicates:    {total_skipped}")
    print(f"📦 Total FBs:          {len(all_fbs)}")
    if all_fbs:
        from collections import Counter
        depths = Counter(fb.get("depth", "?") for fb in all_fbs)
        print(f"📊 Depths:             {dict(depths)}")
        routes = Counter(fb.get("route", "?") for fb in all_fbs)
        print(f"📊 Routes:             {dict(routes)}")
    print(f"📋 Checkpoint:         {STAGE2_CHECKPOINT}")



# ── Singleton processing (D2149: extract principles from unclustered segments) ──

def process_singletons(
    provider: str = "omlx",
    gate_enabled: bool = True,
    gate_strict: bool = True,
) -> tuple[list[dict], int, int]:
    """Extract principles from singleton segments (D2149).

    Singletons are segments that found zero reciprocal neighbors in the embedding
    space. They may contain unique principles not present in any other book.

    Returns:
        (fbs, total_extracted, total_null) — fbs list, extraction counts.
    """
    from pipeline.pipeline_paths import STAGE1_5_SINGLETONS

    if not STAGE1_5_SINGLETONS.exists():
        print(f"❌ No singletons file at {STAGE1_5_SINGLETONS}")
        return [], 0, 0

    # Load singletons
    singletons: list[dict] = []
    with open(STAGE1_5_SINGLETONS) as f:
        for line in f:
            line = line.strip()
            if line:
                singletons.append(json.loads(line))
    print(f"📂 Loaded {len(singletons)} singletons from S1.5")

    if not singletons:
        return [], 0, 0

    # Load segments for text lookup
    segments = load_segments()

    # D2211: Health check — use stress_test (real chat requests, not just /v1/models)
    if provider == "omlx":
        from pipeline.omlx_call import CircuitOpenError, stress_test_omlx
        health = stress_test_omlx(verbose=False)
        if not health["healthy"]:
            print(f"❌ OMLX stress test FAILED: {health['verdict']}")
            for r in health["results"]:
                if r.get("error"):
                    print(f"   [{r['size']} chars]: {r['error']}")
            sys.exit(1)

    # Init dedup
    lsh, minhash_ok = init_minhash_lsh()
    minhash_cache: dict = {}
    dedup_lock: threading.Lock = threading.Lock()  # D2212: thread safety for MinHash (F-H11 fix)
    all_fbs: list[dict] = []
    total_extracted: int = 0
    total_null: int = 0
    pipeline_commit: str = get_pipeline_commit()

    # Resume support
    processed_ids: set[str] = set()
    from pipeline.pipeline_paths import STAGE2_SINGLETON_OUTPUT
    singleton_segids_file = str(STAGE2_SINGLETON_OUTPUT.parent / "singleton.segids")
    Path(singleton_segids_file).parent.mkdir(parents=True, exist_ok=True)

    # Filter to viable singletons (skip fragments)
    viable: list[dict] = []
    for sn in singletons:
        sid_raw = sn.get("segment_ids", [])
        if isinstance(sid_raw, str):
            try:
                sid_list = ast.literal_eval(sid_raw)
            except Exception:
                sid_list = []
        else:
            sid_list = sid_raw
        for sid in sid_list:
            seg = segments.get(sid)
            if seg and len(seg.get("text", "").strip()) >= 50:
                viable.append({"singleton": sn, "segment_id": sid, "text": seg["text"], "source_book": seg.get("source_book", "?")})
                break  # One FB per singleton

    print(f"   Viable singletons (text >= 50 chars): {len(viable)}/{len(singletons)}")
    print(f"   Provider: {provider} | Model: {GEN_MODEL} | temp=0.0")

    # Process with ThreadPoolExecutor
    import concurrent.futures
    max_workers: int = S2_MAX_WORKERS

    def _process_one(item: dict) -> dict | None:
        prompt = f"Text passage:\n{item['text'][:2000]}\n\nSource: {item['source_book'][:80]}"
        try:
            result = call_llm(prompt, SINGLETON_SYSTEM, GEN_MODEL, provider)
        except Exception:
            return None
        if result is None:
            return None
        route = result.get("route", "FB").strip().upper()
        if route == "NULL":
            return {"_null": True}
        name = result.get("name", "").strip()
        definition = result.get("definition", "").strip()
        if not name or len(definition) < 30:
            return {"_null": True}
        is_summary = result.get("is_summary", False)
        if is_summary and gate_enabled:
            return {"_gate": True}
        extraction_type = result.get("extraction_type", "causal_mechanism").strip()
        content_type = result.get("content_type", "principle").strip()
        return {
            "fb_id": make_hash_id(name, definition),
            "name": name,
            "definition": definition,
            "mechanism": result.get("mechanism", "").strip(),
            "boundary": result.get("boundary", result.get("application", "")).strip(),
            "consequence": result.get("consequence", result.get("failure_mode", "")).strip(),
            "is_summary": is_summary,
            "extraction_type": extraction_type,
            "content_type": content_type,
            "evidence_passages": [item["text"][:500]],
            "route": route,
            "source_cluster": item["singleton"].get("cluster_id", f"singleton_{item['segment_id'][:8]}"),
            "source_books": item["singleton"].get("source_books", [item["source_book"]]),
            "source_ids": item["singleton"].get("source_ids", []),
            "source_segments": [item["segment_id"]],
            "cluster_cohesion": 1.0,
            "cluster_size": 1,
            "source_diversity": 1,
            "is_convergent": False,
            "is_singleton_fb": True,
        }

    print(f"⚡ Processing {len(viable)} singletons with {max_workers} workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_one, item): i for i, item in enumerate(viable)}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                fb = future.result()
            except CircuitOpenError:
                # D2211: Breaker open — cancel all futures, preserve checkpoint, abort
                print("\n❌ CIRCUIT BREAKER OPEN during singleton extraction — aborting")
                print(f"   Preserving {len(all_fbs)} singleton FBs")
                for f in futures:
                    f.cancel()
                STAGE2_SINGLETON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
                safe_write(STAGE2_SINGLETON_OUTPUT,
                           "\n".join(json.dumps(fb, ensure_ascii=False) for fb in all_fbs) + "\n",
                           force_shrink=True)
                raise
            except Exception as e:
                # D2177 (C16): Log singleton extraction failures
                print(f"  [{completed}/{len(viable)}] ⚠️  singleton worker error: {type(e).__name__}: {e}")
                continue
            if fb is None:
                continue
            if fb.get("_null"):
                total_null += 1
                continue
            if fb.get("_gate"):
                continue
            all_fbs.append(fb)
            total_extracted += 1
            if completed % 100 == 0:
                print(f"  [{completed}/{len(viable)}] {total_extracted} extracted, {total_null} NULL")

    # Write output
    from pipeline.pipeline_paths import STAGE2_SINGLETON_OUTPUT
    singleton_output = STAGE2_SINGLETON_OUTPUT
    singleton_output.parent.mkdir(parents=True, exist_ok=True)
    with open(singleton_output, "w") as f:
        for fb in all_fbs:
            f.write(json.dumps(fb) + "\n")

    print("\n✅ Singleton extraction complete:")
    print(f"   Extracted FBs: {total_extracted}")
    print(f"   NULL routes:   {total_null}")
    print(f"   Output:        {singleton_output}")

    # Content type distribution
    from collections import Counter
    ct_dist = Counter(fb.get("content_type", "principle") for fb in all_fbs)
    et_dist = Counter(fb.get("extraction_type", "causal_mechanism") for fb in all_fbs)
    print(f"   Content types:  {dict(ct_dist)}")
    print(f"   Extraction types: {dict(et_dist)}")

    return all_fbs, total_extracted, total_null

def main() -> None:
    """CLI entry point."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stage 2: Convergent principle extraction from clusters"
    )
    parser.add_argument("--only-convergent", action="store_true",
                        help="Skip single-source clusters (extract only from ≥2 book clusters)")
    parser.add_argument("--process-singletons", action="store_true",
                        help="Extract principles from singleton (unclustered) segments (D2149)")
    parser.add_argument("--provider", choices=["omlx", "mlx"], default="omlx",
                        help="LLM provider (default: omlx)")
    parser.add_argument("--no-gate", action="store_true",
                        help="Disable gate enforcement (debug only)")
    parser.add_argument("--hybrid", action="store_true",
                        help="D2276: Enable DSPy-inspired hybrid gate — pre-filter clusters before extraction")
    args: argparse.Namespace = parser.parse_args()

    run_stage2(
        provider=args.provider,
        only_convergent=args.only_convergent,
        gate_enabled=not args.no_gate,
        hybrid_gate=args.hybrid,
    )

    if args.process_singletons:
        print("\\n🧩 ===== PROCESSING SINGLETONS (D2149) =====\\n")
        singleton_fbs, sn_extracted, sn_null = process_singletons(
            provider=args.provider,
            gate_enabled=not args.no_gate,
        )
        print(f"\\n🧩 Singleton pass: {sn_extracted} FBs, {sn_null} NULLs")


if __name__ == "__main__":
    main()
