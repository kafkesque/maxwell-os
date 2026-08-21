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

from pipeline.io_guard import load_jsonl, safe_write
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    GEN_MODEL,
    S2_GATE_ENABLED,
    S2_GATE_STRICT,
    S2_GEN_MAX_TOKENS,  # D2381: S2 output budget (was hardcoded 2048)
    S2_GEN_MAX_TOKENS_RETRY,  # D2381: JSON-failure fallback budget
    S2_HIGH_COHESION_THRESHOLD,  # C12: config-driven cohesion tiers
    S2_MED_COHESION_THRESHOLD,   # C12: config-driven cohesion tiers
    S2_GOLDEN_INJECT,
    S2_GOLDEN_MAX,
    S2_GOLDEN_NEGATIVE,
    S2_GOLDEN_PATH,
    S2_GOLDEN_POSITIVE,
    S2_GOLDEN_SEED,  # D2377: config-driven stratified few-shot seed
    S2_GOLDEN_SINGLE_SOURCE_INJECT,  # BUG-152: balanced single-source golden
    S2_GOLDEN_SINGLE_SOURCE_MAX,
    S2_GOLDEN_SINGLE_SOURCE_NEGATIVE,
    S2_GOLDEN_SINGLE_SOURCE_PATH,
    S2_SINGLETON_BATCH_SIZE,                 # D2xxx: batched singleton extraction
    S2_SINGLETON_BATCH_MAX_TOKENS_PER_ITEM,  # D2xxx: per-item output budget in a batch call
    S2_MAX_CLUSTER_SAMPLES,
    S2_MAX_FAILED_RATIO,   # D2331: fail-closed cluster-extraction tolerance
    S2_MAX_PROBE_PER_BOOK,  # D2357: per-book probe sample cap (was literal MAX_PER_BOOK=2)
    S2_MAX_PROBE_SAMPLES,
    S2_MAX_WORKERS,
    S2_MINHASH_NUM_PERM,
    S2_MINHASH_THRESHOLD,
    S2_OMLX_RETRY,
    S2_ROUTE_VALUES,  # D2323/C12: S2 route gate (config-driven)
    S2_SPLIT_KMEANS_RANDOM_STATE,
    S2_SPLIT_PROBE_ENABLED,
    S2_SPLIT_PROBE_MAX_COHESION,
    S2_SPLIT_PROBE_MIN_SIZE,
    S2_EXTRACTION_TYPE_DOMINANCE_WARN_RATIO,  # D2376: extraction_type over-claim canary
    S15_MIN_SOURCE_DIVERSITY,
    STAGE1_5_CHECKPOINT,
    STAGE1_CHECKPOINT,
    STAGE2_CHECKPOINT,
    STAGE2_PROBE_CACHE,
)
from pipeline.stamp import get_pipeline_commit, make_hash_id, stamp_record
from pipeline.content_types import (  # D2323: config-first enum source (C12)
    CONTENT_TYPES,
    EXTRACTION_TYPES,
    EXTRACTION_TYPE_ENUM,
    CONTENT_TO_EXTRACTION_TYPE,  # D2417: conflation-rescue mapping (BUG-145)
    S2_BODY_FIELDS,  # P2-1: type-specific body fields (BUG-152 follow-up)
)

# D2276: Hybrid gate — DSPy-inspired pre-extraction filter (BUG-085 fix)
try:
    from pipeline.hybrid_gate import HybridGate
    from pipeline.hybrid_gate import format_segments_for_gate as _fmt_segs_gate
    _HYBRID_GATE_AVAILABLE: bool = True
except ImportError:
    _HYBRID_GATE_AVAILABLE = False
    HybridGate = None  # type: ignore[assignment]
    _fmt_segs_gate = None  # type: ignore[assignment]


def _write_checkpoint_jsonl(path, records: list[dict], *, force_shrink: bool = False) -> None:
    """Write a compact JSONL checkpoint and self-verify (BUG-106).

    The S2 checkpoint MUST be one-JSON-object-per-line. A pretty-printed /
    multi-line fragment silently corrupts resume (load_jsonl fail-closed raises
    at resume time, discarding hours of prior work). Self-verify immediately
    after write so corruption is loud at write time, not resume time.
    """
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    safe_write(path, content, force_shrink=force_shrink)
    load_jsonl(path, context="S2 checkpoint self-check")  # raises if corrupt


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
_VALID_ROUTES: frozenset[str] = S2_ROUTE_VALUES  # D2323/C12: config-driven route gate
# D2323: enums sourced from config/content_types.yaml (C12 config-first),
# never re-declared here. extraction_type is also validated (was previously
# unvalidated — any string passed through, defaulting to "causal_mechanism").
_VALID_CONTENT_TYPES: frozenset[str] = CONTENT_TYPES
_VALID_EXTRACTION_TYPES: frozenset[str] = EXTRACTION_TYPES


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

    # D2323: validate extraction_type against the config-sourced enum.
    # Was previously unvalidated — any string (or a typo) passed through and
    # silently defaulted to "causal_mechanism" downstream.
    etype = str(result.get("extraction_type", "")).strip()
    if etype and etype not in _VALID_EXTRACTION_TYPES:
        errors.append(f"Invalid extraction_type '{etype}'")

    return len(errors) == 0, errors


def _normalize_role_fields(result: dict) -> dict:
    """D2417 (BUG-145): repair extraction_type/content_type conflation.

    The model occasionally writes a content_type ROLE (tool_instruction,
    process_template, process_instance, growth_edge, principle) into the
    extraction_type FORM field. This is the 183-cluster failure in T1.1.

    Rather than fail-closed (discarding a correctly-identified object), trust
    the role and default the FORM to the weakest-honest epistemic register for
    that role (CONTENT_TO_EXTRACTION_TYPE). S4 may re-derive the form.

    Handles both directions:
      - extraction_type holds a ROLE value  → move it to content_type, default the form
      - content_type holds a FORM value      → move it to extraction_type

    Mutates and returns `result`.
    """
    etype: str = str(result.get("extraction_type", "")).strip()
    ctype: str = str(result.get("content_type", "")).strip()

    # Direction 1: role leaked into the FORM field (the T1.1 failure mode).
    if etype and etype in CONTENT_TYPES and etype not in EXTRACTION_TYPES:
        result["content_type"] = etype
        result["extraction_type"] = CONTENT_TO_EXTRACTION_TYPE.get(
            etype, "descriptive_model"
        )

    # Direction 2: FORM leaked into the role field.
    elif ctype and ctype in EXTRACTION_TYPES and ctype not in CONTENT_TYPES:
        result["extraction_type"] = ctype
        result["content_type"] = "principle"

    return result


def _warn_extraction_type_dominance(dist: "Counter[str]", *, total: int, where: str) -> None:
    """D2376: over-claim canary — flag a lopsided extraction_type distribution.

    `causal_mechanism` is the STRONGEST epistemic claim (verified X→Y because Z).
    If a single extraction_type dominates output above the config threshold, it
    usually means the prompt/golden bias is silently over-claiming descriptive or
    normative material as causal. Warn loudly (do not fail — the operator may be
    running a genuinely causal corpus) so the imbalance is never invisible.

    Args:
        dist: Counter of extraction_type → count.
        total: Total number of FBs (denominator).
        where: Label for the log line (convergent | singleton).
    """
    if total <= 0 or not dist:
        return
    top_type, top_count = dist.most_common(1)[0]
    ratio = top_count / total
    if ratio > S2_EXTRACTION_TYPE_DOMINANCE_WARN_RATIO:
        print(
            f"⚠️  EXTRACTION-TYPE DOMINANCE ({where}): '{top_type}' = {top_count}/{total} "
            f"({ratio:.1%}) > {S2_EXTRACTION_TYPE_DOMINANCE_WARN_RATIO:.0%} — possible over-claim "
            f"(causal_mechanism is the strongest epistemic form). Rebalance golden set/prompt if "
            f"the corpus is not genuinely dominated by one form."
        )


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
that transcend any single source — the mechanism(s), concept(s), method(s), or
pattern(s) that these passages collectively reveal.

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
3. mechanism: HOW the principle works — written in the SAME epistemic register as
   extraction_type (field 8). The two MUST agree:
   - causal_mechanism    → "X causes Y because Z" (a demonstrated cause→effect chain)
   - empirical_pattern   → "X and Y are observed to co-occur/co-vary" (association only, no cause claimed)
   - normative_heuristic → "doing X tends to produce Y" (prescription + intended effect)
   - descriptive_model   → "categories relate as follows" (structure, not causation)
   ⚠️ Do NOT write causal language ("causes", "because", "enables", "leads to") for a
   non-causal claim. A mechanism that says "X causes Y" forces extraction_type to be
   causal_mechanism — if the passages do not demonstrate a cause→effect chain, write the
   mechanism in the weaker register and label it honestly.
4. boundary: "The principle applies when [condition]. It fails when [counter-condition]."
5. consequence: "Because of this principle, [what follows]."
6. elaboration: 3-5 sentences of deeper nuance — edge cases, exceptions,
   and how the mechanism behaves under different conditions. ALWAYS provide
   elaboration (never empty). If the passages add no explicit nuance, DERIVE
   it from the implications of mechanism + boundary + consequence (how the
   principle behaves at its limits, what it implies but does not state). Do
   not invent new factual claims — elaborate within what mechanism/boundary/
   consequence already support.
7. is_summary: true ONLY if you can only restate the passages without identifying
   a convergent mechanism. Be honest — self-flag if summarizing.
8. extraction_type: the EPISTEMIC FORM — how strongly justified the claim is. Choose
   HONESTLY. The strongest form (causal_mechanism) is NOT the default: claim it only
   when the passages actually DEMONSTRATE the cause→effect chain, never as a fallback.
   - "causal_mechanism": X→Y because Z — a VERIFIED cause→effect chain (chain shown).
   - "empirical_pattern": a strong correlation WITHOUT a proven causal chain. If the
     passages only show "X goes with Y" but never WHY, this is the honest label.
   - "normative_heuristic": a practical rule of thumb or repeatable method ("do X to
     achieve Y") — prescriptive advice, not an explanation of why something happens.
   - "descriptive_model": a taxonomy/classification of WHAT categories exist and how
     they relate (what type? how organized?) — identity/organization, not causation.
   CALIBRATION: In a typical convergent corpus only ~1 in 3 principles is a verified
   causal_mechanism. Most passages show association, advice, or taxonomy. If there is no
   verbatim "X causes/leads to Y" chain in the evidence, the honest label is
   empirical_pattern, normative_heuristic, or descriptive_model. Do NOT upgrade a
   correlation or rule of thumb to causal_mechanism just because it has an explanation.
9. content_type: "principle" (reusable concept), "process_template" (repeatable how-to),
   "process_instance" (case study), "growth_edge" (speculative insight),
   "tool_instruction" (tool-specific command).

EXTRACTION BOUNDARY — extract if and only if the passages collectively reveal one of:
1. A VERIFIED CAUSAL MECHANISM (X→Y because Z — the chain is demonstrated), OR
2. A STRONG EMPIRICAL PATTERN (consistent correlation without a proven cause), OR
3. A NORMATIVE HEURISTIC (a repeatable rule/method with failure modes), OR
4. A DESCRIPTIVE MODEL (a taxonomy of categories and how they relate)

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
}

Example output (a NON-causal principle — note extraction_type is NOT causal_mechanism):
{
  "name": "Progressive Disclosure",
  "definition": "Show only the controls relevant to the current task; reveal advanced functionality progressively as the user requests it. This reduces the cognitive load of a dense interface.",
  "mechanism": "This is a practical heuristic, not a causal mechanism: limiting the interface to the current task reduces the working-memory load on the user, but the passages prescribe the practice without isolating a single proven cause→effect chain.",
  "boundary": "Applies to interfaces where beginners and experts share the same surface. Fails when hiding controls makes critical actions undiscoverable or slower than showing them.",
  "consequence": "Interfaces that stage complexity progressively support faster onboarding and lower error rates than those that expose every control at once.",
  "is_summary": false,
  "extraction_type": "normative_heuristic",
  "content_type": "principle",
  "evidence_passages": [
    "Progressive disclosure is the practice of showing only the essential controls."
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
    # D2215: capped at MAX_CLUSTER_SAMPLES to avoid OMLX memory guard (Qwen3-Coder KV cache)
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
- name, definition, mechanism, boundary, consequence, elaboration (3-5 sentences; ALWAYS filled — derive from mechanism/boundary implications if the passage adds no explicit nuance), is_summary (bool), evidence_passages (up to 5 verbatim quotes)
- route: "FB" (convergent principle -> Stage 4 classifies) | "NULL" (no principle)

No principle -> {{"route": "NULL"}}

Classification (depth, domains, discipline) happens in Stage 4 -- do NOT include those fields here."""

    return prompt, evidence_passages


# ── Simplified single-source prompt (D2148: tiered extraction) ─────────────

def _build_body_schema_text() -> str:
    """P2-1 (BUG-152 follow-up): type-specific body field instruction, from config.

    The single-source/singleton prompt must emit type-specific body fields BEYOND
    the shared core_body. Field names are sourced from `s2_body_fields` in
    content_types.yaml (C12) so prompt, golden, and builder never re-declare them.
    """
    lines: list[str] = [
        "BODY SCHEMA BY content_type — emit the body fields for the role you choose:",
        "- principle: name, definition, mechanism, boundary, consequence, elaboration",
    ]
    for role in ("process_template", "tool_instruction", "process_instance", "growth_edge"):
        fields = S2_BODY_FIELDS.get(role, [])
        if fields:
            lines.append(f"- {role}: {', '.join(fields)}")
    lines.append(
        "  (steps/actors/parameters are JSON arrays; every other field is a string. "
        "elaboration is REQUIRED for principle — never leave it empty: write 3-5 "
        "sentences of deeper nuance; if the passage adds no explicit nuance, DERIVE it "
        "from the implications of mechanism + boundary + consequence. Other fields may "
        "be left empty only when the passage does not provide them.)"
    )
    return "\n".join(lines)


_S2_BODY_SCHEMA: str = _build_body_schema_text()


def _capture_type_specific_fields(result: dict, content_type: str) -> dict:
    """P2-1: capture type-specific body fields from a single-source result.

    Returns a dict of non-empty type-specific fields (sourced from `S2_BODY_FIELDS`),
    preserving JSON arrays (steps/actors/parameters) as lists. Empty/absent fields
    are omitted so the FB record stays lean and the shared core_body is not duplicated.
    """
    out: dict = {}
    for field in S2_BODY_FIELDS.get(content_type, []):
        val = result.get(field)
        if val is None:
            continue
        if isinstance(val, str):
            val = val.strip()
            if val:
                out[field] = val
        elif isinstance(val, list):
            if val:
                out[field] = val
        elif isinstance(val, (dict, int, float, bool)):
            out[field] = val
    return out


SINGLE_SOURCE_SYSTEM: str = (
    "You extract knowledge objects from text passages. "
    "Return a JSON object with these EXACT keys:\n"
    "name, definition, mechanism, boundary, consequence, elaboration, "
    "is_summary (bool), "
    "extraction_type (\"causal_mechanism\"|\"empirical_pattern\"|\"normative_heuristic\"|\"descriptive_model\"), "
    "content_type (\"principle\"|\"process_template\"|\"process_instance\"|\"growth_edge\"|\"tool_instruction\"), "
    "route (\"FB\" or \"NULL\").\n"
    "⚠️ extraction_type and content_type are TWO DIFFERENT axes — never swap them:\n"
    "- extraction_type = the EPISTEMIC FORM (how strongly justified): causal_mechanism, "
    "empirical_pattern, normative_heuristic, descriptive_model. It is NEVER "
    "\"tool_instruction\", \"process_template\", \"process_instance\", \"growth_edge\", or \"principle\".\n"
    "- content_type = the functional ROLE (what kind of object): principle, "
    "process_template, process_instance, growth_edge, tool_instruction. It is NEVER "
    "a form word like \"causal_mechanism\" or \"descriptive_model\".\n"
    "Choose extraction_type HONESTLY (do NOT default to causal_mechanism): "
    "causal_mechanism only when the passages DEMONSTRATE a cause→effect chain (X→Y because Z). "
    "empirical_pattern for correlation WITHOUT a proven cause. "
    "normative_heuristic for a rule of thumb or method. "
    "descriptive_model for a taxonomy/classification of categories. "
    "content_type=principle for reusable concepts, process_template for repeatable methods, "
    "process_instance for case studies, growth_edge for speculative insights, "
    "tool_instruction for tool-specific commands. "
    "⚠️ process_template vs tool_instruction: a process_template is a REPEATABLE HUMAN "
    "METHOD with steps a person follows (a how-to, workflow, checklist, or protocol). "
    "A tool_instruction is a COMMAND/API/ALGORITHM for a specific tool or code (a function, "
    "syntax, library call, or code snippet). Code snippets, API descriptions, and algorithms "
    "are tool_instruction — NOT process_template. "
    "is_summary=true ONLY if the passage is a PURE factual description with NO extractable "
    "object of any kind (no principle, no method, no case study, no tool command). "
    "A tool command, repeatable method, or concrete case study IS an extractable object "
    "— set is_summary=false for it. "
    "If the passages are just factual descriptions without any extractable object, "
    'return {{\"route\": \"NULL\"}}.'
) + "\n" + _S2_BODY_SCHEMA
# ── Singleton extraction prompt (D2149: single-segment, no synthesis) ──────

SINGLETON_SYSTEM: str = (
    "You extract and classify content from a single text passage. "
    "Return a JSON object with these EXACT keys:\n"
    "name, definition, mechanism, boundary, consequence, elaboration, "
    "is_summary (bool), "
    "extraction_type (\"causal_mechanism\"|\"empirical_pattern\"|\"normative_heuristic\"|\"descriptive_model\"|\"none\"), "
    "content_type (\"principle\"|\"process_template\"|\"process_instance\"|\"growth_edge\"|\"tool_instruction\"), "
    "route (\"FB\" or \"NULL\").\n"
    "⚠️ extraction_type and content_type are TWO DIFFERENT axes — never swap them:\n"
    "- extraction_type = EPISTEMIC FORM only: causal_mechanism, empirical_pattern, "
    "normative_heuristic, descriptive_model, none. It is NEVER \"tool_instruction\", "
    "\"process_template\", \"process_instance\", \"growth_edge\", or \"principle\".\n"
    "- content_type = functional ROLE only: principle, process_template, process_instance, "
    "growth_edge, tool_instruction. It is NEVER a form word like \"causal_mechanism\".\n"
    "Choose extraction_type HONESTLY (do NOT default to causal_mechanism): "
    "causal_mechanism only when the passage DEMONSTRATES a cause→effect chain. "
    "empirical_pattern for correlation WITHOUT a proven cause. "
    "normative_heuristic for a rule of thumb. "
    "descriptive_model for a taxonomy of categories. "
    "MAPPING RULES:\n"
    "- extraction_type=causal_mechanism + reusable concept → content_type=principle\n"
    "- extraction_type=empirical_pattern (correlation without proven cause) → content_type=growth_edge\n"
    "- extraction_type=normative_heuristic (rule of thumb): → content_type=process_template if a repeatable method, else content_type=principle\n"
    "- Tool-specific commands/features → content_type=tool_instruction\n"
    "⚠️ process_template vs tool_instruction: a process_template is a REPEATABLE HUMAN "
    "METHOD with steps a person follows (how-to, workflow, checklist). A tool_instruction is "
    "a COMMAND/API/ALGORITHM for a specific tool or code (function, syntax, library call, "
    "code snippet). Code snippets and API/algorithm descriptions are tool_instruction — NOT "
    "process_template.\n"
    "- Case studies/specific examples → content_type=process_instance\n"
    "- extraction_type=none + no principle → route=NULL\n"
    "is_summary=true ONLY if the passage is a PURE factual description with NO extractable "
    "object of any kind (no principle, no method, no case study, no tool command). "
    "If the passage contains no extractable object, return {\"route\": \"NULL\"}."
) + "\n" + _S2_BODY_SCHEMA

# D2xxx (option-1 speedup): batched singleton extraction — ONE LLM call per batch of N
# passages returns a JSON ARRAY (one object per passage, in order). Built from
# SINGLETON_SYSTEM by swapping the single-object instruction for the array instruction;
# every other rule (two-axis, content_type guidance, body schema) is inherited.
SINGLETON_BATCH_SYSTEM: str = (
    SINGLETON_SYSTEM.replace(
        "Return a JSON object with these EXACT keys:",
        "Return a JSON ARRAY — exactly ONE object per passage, in the SAME ORDER as "
        "the numbered passages (each object includes \"index\": N matching its passage "
        "number). Each object has these EXACT keys:",
    )
    + "\nFormat example (2 passages):\n"
    '[{"index": 1, "name": "...", "definition": "...", "mechanism": "...", "'
    '"boundary": "...", "consequence": "...", "elaboration": "...", "is_summary": false, "'
    '"extraction_type": "normative_heuristic", "content_type": "process_template", "route": "FB"}, "'
    '{"index": 2, "route": "NULL"}]'
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

def _golden_primary_type(example: dict) -> str:
    """Return the primary extraction_type of a golden example (first FB's type)."""
    fb = example.get("expected_fb", {})
    fbs = fb if isinstance(fb, list) else [fb]
    for item in fbs:
        t = str(item.get("extraction_type", "")).strip()
        if t:
            return t
    return ""


def _golden_depth(example: dict) -> str:
    """Return the primary depth of a golden example (first FB's depth)."""
    fb = example.get("expected_fb", {})
    fbs = fb if isinstance(fb, list) else [fb]
    for item in fbs:
        d = str(item.get("depth", "")).strip()
        if d:
            return d
    return ""


def _stratified_positive_sample(
    all_pos: list[dict], pos_count: int, seed: int
) -> list[dict]:
    """Deterministically select positives maximizing extraction_type AND depth coverage.

    D2377: golden few-shot bias — a plain shuffle can sample only causal_mechanism
    examples (e.g. seed-42 with pos_count=1 picks one type and the model never sees
    descriptive/normative/empirical few-shots). Group by extraction_type and
    round-robin so the injected few-shot spans as many epistemic forms as possible.
    D2425: within each round, prefer the example whose depth is least represented
    among already-picked examples, so the few-shot also spans depth levels
    (universal/cross-domain/domain/specialized). This wires the T-015 depth-bias
    correction into selection itself (previously depth was ignored — adding
    universal/specialized examples to the golden set did NOT guarantee they reached
    the model's few-shot prompt).
    """
    if pos_count <= 0 or not all_pos:
        return []
    rng = random.Random(seed)
    # Global depth frequency: used only as a tie-breaker so a minority universal/
    # specialized example is surfaced even when its group is dominated by cross-domain.
    depth_freq: dict[str, int] = {}
    for e in all_pos:
        d = _golden_depth(e)
        if d:
            depth_freq[d] = depth_freq.get(d, 0) + 1
    groups: dict[str, list[dict]] = {}
    for e in all_pos:
        groups.setdefault(_golden_primary_type(e), []).append(e)
    # Deterministic shuffle within each group (iterate sorted keys, not dict order).
    for key in sorted(groups.keys()):
        rng.shuffle(groups[key])
    # Canonical epistemic order (strongest→weakest) so ties resolve consistently.
    canonical = ("causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern")
    order = [t for t in canonical if t in groups]
    order += sorted(t for t in groups if t not in order)
    picked: list[dict] = []
    picked_depths: dict[str, int] = {}
    while len(picked) < pos_count and any(groups[t] for t in order):
        progressed = False
        for t in order:
            if groups[t] and len(picked) < pos_count:
                # Prefer the depth least-picked so far (diversity — span all 4 depths
                # before repeating), then the globally-rarest (bias correction — surface
                # universal/specialized over cross-domain). Ties break by shuffle order.
                best = min(groups[t], key=lambda e: (
                    picked_depths.get(_golden_depth(e), 0),
                    depth_freq.get(_golden_depth(e), 0),
                ))
                groups[t].remove(best)
                picked.append(best)
                d = _golden_depth(best)
                if d:
                    picked_depths[d] = picked_depths.get(d, 0) + 1
                progressed = True
        if not progressed:
            break
    return picked


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
    # D2159/D2377: deterministic selection from config (stage2.golden_seed).
    # Positives are STRATIFIED by extraction_type (D2377) so few-shot spans
    # epistemic forms instead of accidentally sampling only causal_mechanism.
    pos: list[dict] = _stratified_positive_sample(all_pos, pos_count, S2_GOLDEN_SEED)
    rng = random.Random(S2_GOLDEN_SEED)
    rng.shuffle(all_neg)
    neg: list[dict] = all_neg[:min(neg_count, len(all_neg))]
    while len(pos) + len(neg) > max_total:
        if len(pos) > len(neg):
            pos.pop()
        elif neg:
            neg.pop()
        else:
            break

    return pos, neg, len(pos) + len(neg)


def load_golden_single_source(
    golden_path: str | None,
    neg_count: int,
    max_total: int,
) -> tuple[list[dict], list[dict], int]:
    """Load a role-balanced single-source golden set (BUG-152).

    Single-source/singleton extraction needs few-shot spanning ALL 5 content_type
    roles (principle, process_template, tool_instruction, process_instance,
    growth_edge) plus hard negatives — otherwise the model inherits the convergent
    100%-principle bias and re-labels non-principle objects as principle.

    Selection is deterministic: one positive per role (in canonical order), then
    `neg_count` negatives (seeded shuffle). No stratification by extraction_type
    here — the axis we need to span is the functional ROLE (content_type), not the
    epistemic FORM.
    """
    if golden_path is None or not os.path.exists(str(golden_path)):
        return [], [], 0

    try:
        import yaml
        with open(str(golden_path)) as f:
            golden = yaml.safe_load(f)
    except Exception:
        return [], [], 0

    examples: list[dict] = golden.get("examples", [])
    # Collect ALL positives, grouped by role in deterministic order. A single
    # example per role is NOT enough for contrastive disambiguation — e.g. the
    # tool_instruction role needs BOTH a clear library call AND the ambiguous
    # "algorithm described as steps" case (BUG-147) to teach PT-vs-TI.
    by_role: dict[str, list[dict]] = {}
    for e in examples:
        if not e.get("should_extract"):
            continue
        fb = e.get("expected_fb", {})
        fbs = fb if isinstance(fb, list) else [fb]
        role: str = str(fbs[0].get("content_type", "principle")).strip() or "principle"
        by_role.setdefault(role, []).append(e)

    role_order: tuple[str, ...] = (
        "principle", "process_template", "tool_instruction",
        "process_instance", "growth_edge",
    )
    pos: list[dict] = []
    for r in role_order:
        pos.extend(by_role.get(r, []))

    rng = random.Random(S2_GOLDEN_SEED)
    neg: list[dict] = [e for e in examples if not e.get("should_extract")]
    rng.shuffle(neg)
    neg = neg[:min(neg_count, len(neg))]

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
    # BUG-154 (2026-08-21): the old counter scheme `f"mh_{len(minhash_cache)}"`
    # collides on resume — the D2382 rebuild inserts stored signatures ("mh_0"…
    # "mh_2642") with a GAP (a near-duplicate/other FB consumed a slot without
    # persisting), so `len(minhash_cache)` lands on an already-occupied index and
    # `lsh.insert` raises "The given key already exists" for every FB-producing
    # cluster (run-killer). Find the next FREE index instead.
    idx: int = len(minhash_cache)
    while f"mh_{idx}" in minhash_cache:
        idx += 1
    sig: str = f"mh_{idx}"
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

    max_tokens: int = S2_GEN_MAX_TOKENS  # D2381: config-driven (was hardcoded 2048)

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
        result = call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=max_tokens)
        # D2381: parse_json_robust() returns [] on JSON failure — call_omlx_json does
        # NOT raise for this case (its ValueError branch is unreachable: isinstance([],
        # list) is True). Detect the empty list and retry ONCE with a higher budget
        # (truncation at max_tokens → invalid JSON) so persistent clusters recover.
        if isinstance(result, list) and not result and max_tokens < S2_GEN_MAX_TOKENS_RETRY:
            print(f"      🔁 Empty JSON result — retrying max_tokens={S2_GEN_MAX_TOKENS_RETRY}")
            result = call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=S2_GEN_MAX_TOKENS_RETRY)
        return result
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
                "is_summary": fb_item.get("is_summary", False),
                # D2376: no silent causal_mechanism default — an example that lacks
                # extraction_type shows "" (honest), never over-claims the strongest
                # epistemic form. Schema default is "" (schemas.py).
                "extraction_type": fb_item.get("extraction_type", ""),
                # D2334: model content_type in few-shot (was silently omitted — the
                # system prompt requires it, but examples didn't show it → temp=0.0
                # would deterministically drop it). Matches field #9 in the prompt.
                "content_type": fb_item.get("content_type", "principle"),
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


def format_golden_fewshot_single_source(
    pos_examples: list[dict],
    neg_examples: list[dict] | None = None,
) -> str:
    """Format a role-balanced single-source few-shot block (BUG-152).

    Differs from `format_golden_fewshot` (convergent) in three ways:
      1. Intro frames multi-type knowledge-object extraction (not "principle").
      2. Output shows the single-source schema (NO evidence_passages — the
         SINGLE_SOURCE_SYSTEM/SINGLETON_SYSTEM prompts do not request it).
      3. The example header names the content_type so the model sees all 5 roles.
    """
    if not pos_examples:
        return ""

    parts: list[str] = ["# FEW-SHOT EXAMPLES (knowledge objects)\n"]
    parts.append("Study these examples of correct knowledge-object extraction:\n")

    for i, ex in enumerate(pos_examples, 1):
        fb = ex.get("expected_fb", {})
        fbs = fb if isinstance(fb, list) else [fb]
        name = fbs[0].get("name", "Untitled")
        role = fbs[0].get("content_type", "principle")
        rationale = ex.get("rationale", "")

        parts.append(f"## Example {i}: {name}  → content_type = {role}")
        for fb_item in fbs:
            parts.append("```json")
            output = {
                "name": fb_item.get("name", ""),
                "definition": fb_item.get("definition", ""),
                "mechanism": fb_item.get("mechanism", ""),
                "boundary": fb_item.get("boundary", ""),
                "consequence": fb_item.get("consequence", ""),
                "is_summary": fb_item.get("is_summary", False),
                "extraction_type": fb_item.get("extraction_type", ""),
                "content_type": fb_item.get("content_type", "principle"),
                "route": fb_item.get("route", "FB"),
            }
            # P2-1: surface type-specific body fields in the few-shot so the model
            # sees the correct shape for PT/TI/PI/GE (steps, syntax, instance_text…).
            for _field in S2_BODY_FIELDS.get(role, []):
                if _field in fb_item:
                    output[_field] = fb_item[_field]
            parts.append(json.dumps(output, indent=2, ensure_ascii=False))
            parts.append("```")
        if rationale:
            first_sentence = rationale.strip().split(".")[0] + "."
            parts.append(f"Key insight: {first_sentence}")
        parts.append("")

    if neg_examples:
        parts.append("## REJECTION EXAMPLES")
        parts.append("These passages should produce route=NULL (NO extractable object):\n")
        for i, ex in enumerate(neg_examples[:3], 1):
            segs = ex.get("cluster_segments", [])
            text = segs[0].get("text", "").strip()[:220] if segs else ""
            rationale = ex.get("rationale", "")
            parts.append(f"### Rejection {i}")
            if text:
                parts.append(f"PASSAGE: {text}")
            first_sentence = rationale.strip().split(".")[0] + "." if rationale else "No extractable object."
            parts.append(f"REJECT: {first_sentence}")
            parts.append("")
        parts.append("")

    parts.append("---")
    parts.append("Now apply the same extraction rigor to the passage below.")
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
    MAX_PER_BOOK: int = S2_MAX_PROBE_PER_BOOK  # D2357: from config, was 2

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

    # Phi-4-mini probe (fast, ~1.5s) — D2319: use VERIFY_MODEL_V2 (Phi-4-mini),
    # NOT VERIFY_MODEL (GPT-OSS). GPT-OSS is a reasoning model: during cold
    # reload it emits only reasoning_content → "content missing" → call_llm
    # returns None → probe failure >10% → PROBE ABORT. Phi-4-mini is
    # non-reasoning and JSON-mode safe for principle counting (with source text).
    # D2209: Route through call_llm to respect --provider flag (was hardcoded OMLX).
    try:
        from pipeline.pipeline_paths import VERIFY_MODEL_V2
        result: dict | None = call_llm(
            prompt=prompt,
            model=VERIFY_MODEL_V2,
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
    except Exception as _split_err:
        # Fail-safe: return the original cluster if k-means fails (prefer a
        # coarser extraction to data loss) — but NEVER silent (C16).
        print(f"   ⚠️  k-means split failed for cluster "
              f"{cluster.get('cluster_id', '?')!r}: {type(_split_err).__name__}: {_split_err}",
              flush=True)

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


def _validate_mode_flags(
    only_convergent: bool,
    only_single_source: bool,
    reset_single_source: bool,
) -> None:
    """Fail fast on contradictory/unsafe mode-flag combinations (P2-1 / BUG-152).

    Guards against a silent data-loss footgun: --reset-single-source drops old
    single-source FBs, so it must never run while convergent clusters are also
    being extracted (only_single_source=False). And the two mode-selector flags
    are mutually exclusive by construction.
    """
    if only_convergent and only_single_source:
        raise ValueError("--only-convergent and --only-single-source are mutually exclusive")
    if reset_single_source and not only_single_source:
        raise ValueError("--reset-single-source requires --only-single-source")


def run_stage2(
    provider: str = "omlx",
    only_convergent: bool = False,
    only_single_source: bool = False,
    reset_single_source: bool = False,
    gate_enabled: bool = S2_GATE_ENABLED,
    gate_strict: bool = S2_GATE_STRICT,
    hybrid_gate: bool = False,
    reprocess_gated: bool = False,
) -> None:
    """Run Stage 2: Convergent principle extraction from clusters.

    Args:
        provider: "omlx" or "mlx" for LLM inference.
        only_convergent: Skip single-source clusters.
        only_single_source: Extract ONLY single-source clusters (skip convergent).
            P2-1 / BUG-152 follow-up — re-extract the single-source phase with the
            balanced golden + per-type body schemas while leaving the already-correct
            convergent FBs untouched. Mutually exclusive with only_convergent.
        reset_single_source: On resume, drop OLD single-source FBs (is_convergent=False)
            and un-mark single-source cluster IDs so they are RE-extracted (the pre-fix
            single-source FBs were re-labelled as principle and lacked type-specific
            body fields — BUG-152). Convergent FBs are preserved. Only meaningful with
            only_single_source.
        gate_enabled: Enable gate enforcement.
        gate_strict: Force [] on NULL-route with content.
        hybrid_gate: D2276 — Use DSPy-inspired pre-extraction gate to skip non-principle clusters.
        reprocess_gated: D2421 — Re-process clusters summary-gated (is_summary=true) on resume.
            Un-marks gated IDs from processed_ids so they re-enter extraction with the
            content_type-aware gate (D2417). Requires a prior run's .gated_ids sidecar.
            A cluster that clears the gate on a reprocess pass is pruned from gated_ids
            (D2421-fix), so a second --reprocess-gated run does not re-extract it.
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
    _validate_mode_flags(only_convergent, only_single_source, reset_single_source)

    convergent: list[dict] = [c for c in clusters if c.get("is_convergent")]
    single_source: list[dict] = [c for c in clusters if not c.get("is_convergent") and not c.get("is_noise", False)]
    noise: list[dict] = [c for c in clusters if c.get("is_noise", False)]

    if only_convergent:
        target_clusters: list[dict] = convergent
    elif only_single_source:
        target_clusters: list[dict] = single_source
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

    # BUG-152: balanced single-source golden — inject into single-source/singleton
    # extraction (previously zero few-shot there, causing re-labelling + over-fire).
    ss_golden_path: str | None = S2_GOLDEN_SINGLE_SOURCE_PATH
    if ss_golden_path and not os.path.isabs(str(ss_golden_path)):
        ss_golden_path = str(Path(__file__).resolve().parent.parent / ss_golden_path)
    ss_pos, ss_neg, ss_golden_total = load_golden_single_source(
        ss_golden_path, S2_GOLDEN_SINGLE_SOURCE_NEGATIVE, S2_GOLDEN_SINGLE_SOURCE_MAX
    )
    ss_few_shot_text: str = ""
    if S2_GOLDEN_SINGLE_SOURCE_INJECT and ss_pos:
        ss_few_shot_text = format_golden_fewshot_single_source(ss_pos, ss_neg)
        ss_roles = [str(e.get("expected_fb", {}).get("content_type", "principle")) for e in ss_pos]
        print(f"   🎯 Single-source golden few-shot: {len(ss_pos)} pos (roles={ss_roles}) "
              f"+ {len(ss_neg)} neg ({len(ss_few_shot_text)} chars)")

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
    cached_targets: list[dict] | None = None
    if not only_single_source:
        cached_targets = _load_probe_cache(convergent, single_source, only_convergent)
    if only_single_source:
        # Single-source-only: the split-probe only ever sub-divides CONVERGENT
        # clusters, so it is irrelevant here. target_clusters already == single_source.
        cached_targets = None
        print(f"   🎯 Single-source-only: {len(single_source)} clusters (convergent skipped)")
    elif cached_targets is not None:
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

        # BUG-107: a k-means sub-cluster of a convergent parent can drop below the
        # ≥2-source bar (is_convergent=False). Under --only-convergent those
        # single-source sub-clusters must NOT be extracted. Filter the extraction
        # targets only — the cache keeps the UNFILTERED list so a later run without
        # --only-convergent can still recover them (cache is mode-agnostic).
        target_clusters = expanded_targets
        if only_convergent:
            target_clusters = [t for t in target_clusters if t.get("is_convergent")]
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
    failed_clusters: int = 0  # D2331: terminal LLM failures (silent-skip audit)
    pipeline_commit: str = get_pipeline_commit()

    # Resume support
    processed_ids: set[str] = set()
    gated_ids: set[str] = set()  # D2421: cluster IDs gated by is_summary (reprocessable)
    segids_file: str = str(STAGE2_CHECKPOINT) + ".segids"
    gated_ids_file: str = str(STAGE2_CHECKPOINT) + ".gated_ids"
    if STAGE2_CHECKPOINT.exists() and os.path.exists(segids_file):
        try:
            # D2332: fail-closed JSONL read — a pretty-printed/multi-line checkpoint
            # must raise (caught below → fresh start), never silently subset-parse.
            all_fbs.extend(load_jsonl(STAGE2_CHECKPOINT, context="S2 checkpoint"))
            with open(segids_file) as f:
                processed_ids = set(json.load(f))
            # D2421: load gated cluster IDs (is_summary-gated) for optional re-processing.
            if os.path.exists(gated_ids_file):
                try:
                    with open(gated_ids_file) as f:
                        gated_ids = set(json.load(f))
                except Exception:
                    gated_ids = set()
            if reprocess_gated and gated_ids:
                processed_ids -= gated_ids
                print(f"   ♻️  Reprocessing {len(gated_ids)} previously-gated clusters (--reprocess-gated)")
            # P2-1 / BUG-152: --reset-single-source — replace the pre-fix single-source
            # FBs (re-labelled as principle, missing type-specific body fields) with a
            # clean re-extraction. Drop OLD is_convergent=False FBs from the checkpoint
            # and un-mark single-source cluster IDs so they re-enter extraction. The
            # already-correct convergent FBs (is_convergent=True) are preserved verbatim.
            if reset_single_source:
                ss_cids: set[str] = {c.get("cluster_id", "") for c in single_source}
                kept: list[dict] = [fb for fb in all_fbs if fb.get("is_convergent")]
                n_dropped: int = len(all_fbs) - len(kept)
                all_fbs[:] = kept
                n_unmarked: int = len(processed_ids & ss_cids)
                processed_ids -= ss_cids
                gated_ids -= ss_cids
                print(f"   ♻️  Reset single-source: dropped {n_dropped} old single-source FBs, "
                      f"un-marked {n_unmarked} single-source cluster IDs for re-extraction")
            # D2215: Detect cluster-ID format mismatch between old segids and current probe cache.
            # Old probe used "cluster_N_subN", new probe uses "cluster_N_sN_subN". Zero overlap
            # means the segids are from a different probe format — discard them to avoid silent reprocessing.
            # NOTE: compare against the FULL corpus (convergent + single_source), not the
            # mode-filtered target_clusters — in --only-single-source mode the convergent IDs
            # in processed_ids are intentionally absent from target_clusters, which must not
            # be misread as a format mismatch (that would discard the preserved convergent FBs).
            all_cids: set[str] = {c.get("cluster_id", "") for c in (convergent + single_source)}
            if processed_ids and not (processed_ids & all_cids):
                print(f"   ⚠️  Resume segids format mismatch — {len(processed_ids)} old IDs, 0 overlap with {len(all_cids)} corpus clusters")
                print("   ⚠️  Starting fresh — all clusters will be processed")
                processed_ids = set()
                all_fbs = []  # D2317: discard stale FBs from a different run's checkpoint
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
                # D2382: rebuild dedup infra from checkpoint FBs. Resume loaded
                # all_fbs but left minhash_cache + lsh EMPTY — the post-collection
                # dedup then assigned each new FB a counter sig ("mh_0") that collides
                # with the first checkpoint FB's stored sig, so every new FB was
                # compared against ITSELF (jaccard=1.0) and rejected as near-duplicate.
                if minhash_ok:
                    for _fb in all_fbs:
                        _sig = _fb.get("minhash_signature")
                        _def = _fb.get("definition", _fb.get("name", ""))
                        if not _sig or not _def:
                            continue
                        _mh = make_minhash(_def)
                        minhash_cache[_sig] = (_def, _mh)
                        if lsh is not None:
                            lsh.insert(_sig, _mh)
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
            except Exception as _gate_err:
                # Fail-open by design (prefer false-positive extraction to data loss),
                # but NEVER silent (C16): the gate is a cheap negative filter — its
                # failure must be observable, not swallowed.
                print(f"   ⚠️  Hybrid gate error (proceeding fail-open): "
                      f"{type(_gate_err).__name__}: {_gate_err}", flush=True)

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
                    few_shot=(
                        few_shot_text if (few_shot_text and is_conv)
                        else (ss_few_shot_text if (ss_few_shot_text and not is_conv) else None)
                    ),
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

        # BUG-157: non-object LLM responses (bare string/number) from
        # parse_json_robust. Retry ONCE with an explicit object-only instruction;
        # if still non-object, fail closed (D2331) — no opaque AttributeError.
        if not isinstance(result, (dict, list)):
            print(f"      ⚠️  Non-object result ({type(result).__name__}) for {cid} — "
                  f"retrying with JSON-only repair", flush=True)
            try:
                result = call_llm(
                    prompt + "\n\nReturn ONLY a single JSON object. No prose, no quotes wrapping the object.",
                    system, GEN_MODEL, provider,
                    few_shot=None,
                )
            except CircuitOpenError:
                raise
            except Exception as _repair_err:
                print(f"      ⚠️  repair retry failed for {cid}: "
                      f"{type(_repair_err).__name__}: {_repair_err}", flush=True)
        # Normalize: drop non-dict elements from an array response (the model
        # emitting a bare list of strings — e.g. obeying instructions embedded in
        # a prompt-engineering source passage). Collapse to a SINGLE cluster
        # failure if nothing extractable remains — never N per-element failures.
        if isinstance(result, list):
            result = [x for x in result if isinstance(x, dict)]
        if not isinstance(result, dict) and not (isinstance(result, list) and result):
            return [{"_failed": True, "cluster_id": cid,
                     "_schema_errors": [f"non-object result: {type(result).__name__}"]}]

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
        # BUG-157: parse_json_robust can return a bare JSON string (the model
        # emitted a string literal like "null" or prose instead of an object).
        # Guard BEFORE any .get() — otherwise AttributeError crashes the worker
        # with an opaque message instead of the fail-closed (D2331) schema path.
        if not isinstance(result, dict):
            return {"_failed": True, "cluster_id": cid,
                    "_schema_errors": [f"non-object result: {type(result).__name__}"]}

        # Check for NULL route
        route: str = result.get("route", "FB").strip().upper()
        if route == "NULL":
            return {"_null": True, "cluster_id": cid}

        # D2417 (BUG-145): repair extraction_type/content_type conflation BEFORE
        # validation, so a role leaked into the FORM field is rescued rather than
        # rejected (the 183-cluster T1.1 failure).
        result = _normalize_role_fields(result)

        # D2180: Schema validation (T2.2) — catch malformed LLM output before it enters pipeline
        is_valid, schema_errors = validate_fb_output(result)
        if not is_valid:
            # D2403: schema/inference failure is NOT a semantic NULL — mark FAILED so the
            # caller counts it in failed_clusters (D2331 gate) and does NOT mark it processed.
            import sys as _sys
            print(f"   ⚠️  Schema validation failed for {cid}: {'; '.join(schema_errors[:3])}",
                  file=_sys.stderr)
            return {"_failed": True, "cluster_id": cid, "_schema_errors": schema_errors}

        # Validate required fields — unified reading with fallback for single-source schema
        name: str = result.get("name", "").strip()
        definition: str = result.get("definition", "").strip()
        mechanism: str = result.get("mechanism", "").strip()
        boundary: str = result.get("boundary", result.get("application", "")).strip()
        consequence: str = result.get("consequence", result.get("failure_mode", "")).strip()
        is_summary: bool = result.get("is_summary", False)
        extraction_type: str = result.get("extraction_type", "").strip()  # D2376: absent → "" (no over-claim)
        content_type: str = result.get("content_type", "principle").strip()

        # D2214: Removed redundant check — validate_fb_output already enforces definition ≥30 chars.
        # Qwen3-Coder produces concise definitions that pass validation but were caught here.
        if not name or not definition:
            return {"_null": True, "cluster_id": cid}

        # Gate: reject summaries (D2417/BUG-146: content_type-aware).
        # is_summary=true means "pure restatement, no extractable object". But a
        # non-principle role (process_template/process_instance/growth_edge/
        # tool_instruction) IS an extractable object — the model often flags
        # is_summary=true for single-source method/tool/case content because the
        # convergent prompt ties is_summary to "no convergent mechanism" (which is
        # structurally always-true for single-source). Only gate when the object is
        # (or defaults to) a principle — i.e. a genuine restatement.
        non_principle_roles: frozenset[str] = CONTENT_TYPES - {"principle"}
        if is_summary and gate_enabled and content_type not in non_principle_roles:
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

        # P2-1: capture type-specific body fields (PT steps/trigger, TI syntax/
        # parameters, PI instance_text, GE body, etc.) beyond the shared core_body.
        fb.update(_capture_type_specific_fields(result, content_type))

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
                _write_checkpoint_jsonl(STAGE2_CHECKPOINT, all_fbs, force_shrink=True)
                raise  # Abort the run
            except Exception as e:
                failed_clusters += 1  # D2331: terminal worker failure
                print(f"  [{completed}/{len(target_clusters)}] ❌ {cid}: {e}")
                continue

            is_conv: bool = cluster.get("is_convergent", False)
            conv_tag: str = "🌐" if is_conv else "📖"

            # D2178: _process_cluster now always returns list[dict]
            if not fb_results:
                failed_clusters += 1  # D2331: terminal LLM failure (call_llm returned None)
                print(f"  [{completed}/{len(target_clusters)}] ❌ {conv_tag} {cid}: LLM failed")
                continue

            added_names: list[str] = []
            cluster_failed = False
            # D2421-fix: clear any stale gated entry at the start of this pass. If the
            # cluster is still summary-gated below, gated_ids.add(cid) re-adds it; if it
            # now yields a valid FB (or NULL/near-dup), it correctly leaves the reprocess
            # pool. Without this, successfully-reprocessed clusters are re-extracted on
            # every subsequent --reprocess-gated run (unbounded wasted LLM calls).
            gated_ids.discard(cid)
            for fb in fb_results:
                if fb.get("_failed"):
                    failed_clusters += 1
                    cluster_failed = True
                    print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid}: schema FAILED")
                    continue

                if fb.get("_null"):
                    total_null += 1
                    print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid}: NULL/skip")
                    continue

                if fb.get("_gate"):
                    total_gate_violations += 1
                    gated_ids.add(cid)  # D2421: persist gated IDs for --reprocess-gated
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
                added_names.append(fb.get('name', '?')[:30])
            if not cluster_failed:
                processed_ids.add(cid)
            book_count: int = cluster.get("source_diversity",
                          len(cluster.get("source_ids", cluster.get("source_books", []))))
            if added_names:
                fb_names: str = ", ".join(added_names[:3])
                if len(added_names) > 3:
                    fb_names += f" +{len(added_names) - 3} more"
                print(f"  [{completed}/{len(target_clusters)}] {conv_tag} {cid} "
                      f"({cluster.get('size', 0)} segs, {book_count} books) → {fb_names}")

            # D2154: Incremental checkpoint every 5 clusters (inside for future loop)
            if completed % 5 == 0:
                _write_checkpoint_jsonl(STAGE2_CHECKPOINT, all_fbs, force_shrink=True)
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
                except Exception as e:
                    # D2383 (C16): never swallow silently — a segids write failure only
                    # means those clusters get re-processed on resume (safe), but it
                    # MUST be observable.
                    print(f"   ⚠️  segids checkpoint write failed: {type(e).__name__}: {e}", flush=True)
                    if os.path.exists(segids_tmp.name):
                        os.unlink(segids_tmp.name)
                # D2421: persist gated IDs alongside segids (atomic, crash-safe).
                gated_tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".gated_ids", delete=False,
                    dir=str(STAGE2_CHECKPOINT.parent)
                )
                try:
                    json.dump(list(gated_ids), gated_tmp)
                    gated_tmp.flush()
                    os.fsync(gated_tmp.fileno())
                    gated_tmp.close()
                    os.replace(gated_tmp.name, gated_ids_file)
                except Exception as e:
                    print(f"   ⚠️  gated_ids checkpoint write failed: {type(e).__name__}: {e}", flush=True)
                    if os.path.exists(gated_tmp.name):
                        os.unlink(gated_tmp.name)

    # Write final checkpoint (BUG-106: self-verifying JSONL)
    _write_checkpoint_jsonl(STAGE2_CHECKPOINT, all_fbs)
    # D2421: final atomic write of gated IDs (incremental write fires only every 5 clusters).
    import tempfile as _tmp_final
    try:
        _gated_final = _tmp_final.NamedTemporaryFile(mode="w", suffix=".gated_ids", delete=False,
                                                     dir=str(STAGE2_CHECKPOINT.parent))
        json.dump(list(gated_ids), _gated_final)
        _gated_final.flush(); os.fsync(_gated_final.fileno()); _gated_final.close()
        os.replace(_gated_final.name, gated_ids_file)
    except Exception as e:
        print(f"   ⚠️  final gated_ids write failed: {type(e).__name__}: {e}", flush=True)

    # BUG-156: final segids write. The incremental segids write fires only every
    # 5 clusters (completed % 5 == 0), so the trailing <5 clusters were
    # checkpointed but never marked processed — a resume would re-extract them
    # and produce duplicate FBs (same fb_id). Mirror the gated_ids final write.
    try:
        _segids_final = _tmp_final.NamedTemporaryFile(mode="w", suffix=".segids", delete=False,
                                                      dir=str(STAGE2_CHECKPOINT.parent))
        json.dump(list(processed_ids), _segids_final)
        _segids_final.flush(); os.fsync(_segids_final.fileno()); _segids_final.close()
        os.replace(_segids_final.name, segids_file)
    except Exception as e:
        print(f"   ⚠️  final segids write failed: {type(e).__name__}: {e}", flush=True)

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
        _et_dist = Counter(fb.get("extraction_type", "") for fb in all_fbs)  # D2376
        _warn_extraction_type_dominance(_et_dist, total=len(all_fbs), where="convergent")
    print(f"📋 Checkpoint:         {STAGE2_CHECKPOINT}")

    # ── D2331: fail-closed cluster extraction ───────────────────────────────
    # call_llm() returns None on terminal LLM failure and the worker skips the
    # cluster — previously this wrote a "successful" checkpoint with missing FBs.
    # Now we count terminal failures and refuse to advance silently.
    total_attempted: int = len(target_clusters)
    print(f"❌ Failed clusters:     {failed_clusters}/{total_attempted}")
    if total_attempted > 0:
        failure_ratio: float = failed_clusters / total_attempted
        if failure_ratio > S2_MAX_FAILED_RATIO:
            print(f"❌ Stage 2 FAILED: {failed_clusters}/{total_attempted} clusters failed extraction "
                  f"({failure_ratio:.1%} > max_failed_ratio={S2_MAX_FAILED_RATIO}). "
                  f"Missing clusters = missing FBs — do NOT advance to S4.")
            sys.exit(1)
        if failed_clusters > 0:
            print(f"⚠️  Stage 2 CONDITIONAL_SUCCESS: {failed_clusters} cluster(s) failed within "
                  f"tolerance ({failure_ratio:.1%} ≤ {S2_MAX_FAILED_RATIO}). Re-run to retry failed "
                  f"clusters before advancing to S4.")
            sys.exit(2)  # non-zero → runner does NOT auto-advance to S4



# ── Singleton processing (D2149: extract principles from unclustered segments) ──

def _singleton_result_to_fb(result: dict, item: dict, gate_enabled: bool) -> dict | None:
    """Convert one singleton LLM result into an FB record (D2xxx).

    Shared by the per-singleton and batched paths. Returns
    None / {"_null": True} / {"_gate": True} / the FB dict.
    """
    route: str = result.get("route", "FB").strip().upper()
    if route == "NULL":
        return {"_null": True}
    # D2417 (BUG-145): repair extraction_type/content_type conflation.
    result = _normalize_role_fields(result)
    name: str = result.get("name", "").strip()
    definition: str = result.get("definition", "").strip()
    if not name or len(definition) < 30:
        return {"_null": True}
    is_summary: bool = result.get("is_summary", False)
    extraction_type: str = result.get("extraction_type", "").strip()  # D2376
    content_type: str = result.get("content_type", "principle").strip()
    non_principle_roles: frozenset[str] = CONTENT_TYPES - {"principle"}
    if is_summary and gate_enabled and content_type not in non_principle_roles:
        return {"_gate": True}
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
        **_capture_type_specific_fields(result, content_type),  # P2-1
    }


def _map_batch_results(raw: object, n: int) -> list[dict | None]:
    """Map a batched LLM response (JSON array) to per-passage results (D2xxx).

    Prefers embedded "index" (1..N) alignment; falls back to positional order;
    a position with no object -> None (the caller then falls back to a
    per-singleton call so no singleton is dropped).
    """
    results: list[dict | None] = [None] * n
    if isinstance(raw, list):
        indexed: dict[int, dict] = {}
        positional: list[dict] = []
        for obj in raw:
            if not isinstance(obj, dict):
                continue
            idx = obj.get("index")
            if isinstance(idx, int) and 1 <= idx <= n:
                indexed[idx] = obj
            elif len(positional) < n:
                positional.append(obj)
        for i in range(n):
            results[i] = indexed.get(i + 1) if (i + 1) in indexed else (
                positional[i] if i < len(positional) else None
            )
    elif isinstance(raw, dict):
        results[0] = raw
    return results


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

    # BUG-152 fix (2026-08-21): load the balanced single-source golden for the
    # singleton path. `ss_few_shot_text` was previously referenced here but only
    # defined in run_stage2 — a latent NameError that would crash the first
    # singleton extraction. Load it independently (process_singletons is standalone).
    ss_golden_path: str | None = S2_GOLDEN_SINGLE_SOURCE_PATH
    if ss_golden_path and not os.path.isabs(str(ss_golden_path)):
        ss_golden_path = str(Path(__file__).resolve().parent.parent / ss_golden_path)
    _ss_pos, _ss_neg, _ = load_golden_single_source(
        ss_golden_path, S2_GOLDEN_SINGLE_SOURCE_NEGATIVE, S2_GOLDEN_SINGLE_SOURCE_MAX
    )
    ss_few_shot_text: str = ""
    if S2_GOLDEN_SINGLE_SOURCE_INJECT and _ss_pos:
        ss_few_shot_text = format_golden_fewshot_single_source(_ss_pos, _ss_neg)
        print(f"   🎯 Singleton golden few-shot: {len(_ss_pos)} pos + {len(_ss_neg)} neg "
              f"({len(ss_few_shot_text)} chars)")

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
            result = call_llm(prompt, SINGLETON_SYSTEM, GEN_MODEL, provider,
                              few_shot=ss_few_shot_text if ss_few_shot_text else None)
        except Exception:
            return None
        if result is None:
            return None
        return _singleton_result_to_fb(result, item, gate_enabled)

    def _build_batch_prompt(batch: list[dict]) -> str:
        parts: list[str] = []
        for i, item in enumerate(batch, 1):
            parts.append(f"[{i}] Text passage:\n{item['text'][:2000]}\n\nSource: {item['source_book'][:80]}")
        return "\n\n".join(parts)

    def _process_batch(batch: list[dict]) -> list[dict]:
        """D2xxx: process a batch of singletons in ONE LLM call (option-1 speedup).

        One call returns a JSON ARRAY aligned to the numbered passages; positions the
        batched call failed to return fall back to a per-singleton call so no singleton
        is silently dropped. Returns one result marker per item (None / {"_null": True}
        / {"_gate": True} / FB dict) in batch order.
        """
        n: int = len(batch)
        try:
            from pipeline.omlx_call import call_omlx_json
            batch_system: str = SINGLETON_BATCH_SYSTEM
            if ss_few_shot_text:
                batch_system = batch_system + "\n\n" + ss_few_shot_text
            raw = call_omlx_json(
                prompt=_build_batch_prompt(batch),
                model=GEN_MODEL,
                system=batch_system,
                max_tokens=n * S2_SINGLETON_BATCH_MAX_TOKENS_PER_ITEM,
            )
        except CircuitOpenError:
            raise
        except Exception:
            raw = None
        results: list[dict | None] = _map_batch_results(raw, n)
        out: list[dict] = []
        for i, item in enumerate(batch):
            r = results[i]
            if r is None:
                out.append(_process_one(item))  # fallback: never drop a singleton
            else:
                out.append(_singleton_result_to_fb(r, item, gate_enabled))
        return out

    print(f"⚡ Processing {len(viable)} singletons with {max_workers} workers "
          f"in batches of {S2_SINGLETON_BATCH_SIZE}...")
    batches: list[list[dict]] = [
        viable[i:i + S2_SINGLETON_BATCH_SIZE]
        for i in range(0, len(viable), S2_SINGLETON_BATCH_SIZE)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_batch, b): i for i, b in enumerate(batches)}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                batch_out: list[dict] = future.result()
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
                print(f"  [{completed}/{len(batches)}] ⚠️  batch worker error: {type(e).__name__}: {e}")
                continue
            for fb in batch_out:
                if fb is None:
                    continue
                if fb.get("_null"):
                    total_null += 1
                    continue
                if fb.get("_gate"):
                    continue
                all_fbs.append(fb)
                total_extracted += 1
            if completed % 50 == 0:
                print(f"  [{completed}/{len(batches)}] {total_extracted} extracted, {total_null} NULL")

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
    et_dist = Counter(fb.get("extraction_type", "") for fb in all_fbs)  # D2376: absent → "" (no over-claim)
    print(f"   Content types:  {dict(ct_dist)}")
    print(f"   Extraction types: {dict(et_dist)}")
    _warn_extraction_type_dominance(et_dist, total=len(all_fbs), where="singleton")

    return all_fbs, total_extracted, total_null

def main() -> None:
    """CLI entry point."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stage 2: Convergent principle extraction from clusters"
    )
    parser.add_argument("--only-convergent", action="store_true",
                        help="Skip single-source clusters (extract only from ≥2 book clusters)")
    parser.add_argument("--only-single-source", action="store_true",
                        help="P2-1/BUG-152: extract ONLY single-source clusters (skip convergent)")
    parser.add_argument("--reset-single-source", action="store_true",
                        help="P2-1/BUG-152: on resume, drop old single-source FBs + re-extract them (use with --only-single-source)")
    parser.add_argument("--process-singletons", action="store_true",
                        help="Extract principles from singleton (unclustered) segments (D2149)")
    parser.add_argument("--provider", choices=["omlx", "mlx"], default="omlx",
                        help="LLM provider (default: omlx)")
    parser.add_argument("--no-gate", action="store_true",
                        help="Disable gate enforcement (debug only)")
    parser.add_argument("--hybrid", action="store_true",
                        help="D2276: Enable DSPy-inspired hybrid gate — pre-filter clusters before extraction")
    parser.add_argument("--reprocess-gated", action="store_true",
                        help="D2421: Re-process clusters that were summary-gated (is_summary=true) on resume")
    args: argparse.Namespace = parser.parse_args()

    run_stage2(
        provider=args.provider,
        only_convergent=args.only_convergent,
        only_single_source=args.only_single_source,
        reset_single_source=args.reset_single_source,
        gate_enabled=not args.no_gate,
        hybrid_gate=args.hybrid,
        reprocess_gated=args.reprocess_gated,
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
