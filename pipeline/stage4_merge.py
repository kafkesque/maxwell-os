#!/usr/bin/env python3
"""
stage4_merge.py — Merge clusters → Foundation Blocks + multi-label classification.
===================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 4), D1058, D150, D316

Input:  Clusters from Stage 2 + Principles from Stage 2
Output: Foundation Blocks with classified labels, checkpoint at stage4_merge.jsonl

Process:
  1. For each cluster, gather all member principles
  2. Send to Qwen3-Coder-30B: merge principles → single FB (name + 6 body fields)
  3. Classification: single-pass prompt lists all valid labels inline (D316: discipline singular, domains multi-label)
  4. Pydantic Literal validation catches hallucinated labels at write boundary
  5. Auto-derive context, accessibility, intimacy_boundary, provenance (v1 parity)
  6. Write checkpoint

Generator: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)
Classifier: gpt-oss-20b-MXFP4-Q8 (OMLX) — R5: different family from generator (D2249)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage4_merge.py
    python3 pipeline/stage4_merge.py --cluster 0,1,2   # Process specific clusters
"""

import argparse
import heapq
import json
import os
import re
import signal
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# C12: Load pipeline config (needed for batch settings)
import yaml as _yaml

_CFG_PATH_S4 = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(_CFG_PATH_S4) as _f:
    _PIPELINE_CFG = _yaml.safe_load(_f)

from pipeline.io_guard import load_jsonl, safe_write, safe_write_jsonl  # D2332 fail-closed + BUG-188 streaming/fail-loud writer
from pipeline.content_types import (  # D2323: config-first enum source (C12)
    CONTENT_TYPES,
    DEFAULT_CONTENT_TYPE,
    ROUTE_TO_CONTENT_TYPE,
)
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    GEN_MODEL,
    MAX_DOMAINS_PER_FB,
    FB_NAME_MAX_WORDS,  # BUG-149: C12 — name word cap (was hardcoded 5)
    S4_CHECKPOINT_INTERVAL,  # D2370: intra-stage incremental checkpoint cadence (clusters)
    S4_DEDUP_COSINE_THRESHOLD,  # D2231: C12 compliance
    S4_DEPTH_FALLBACK_DEPTH,  # BUG-075: conservative default when depth call fails
    S4_DEPTH_BATCH_ENABLED,  # D2477: wire D2354 batch depth into stage4
    S4_DEPTH_BATCH_SIZE,  # D2477: batch depth chunk size
    S4_DEPTH_FOCUSED_CLASSIFICATION,  # BUG-075: split depth into short prompt
    S4_DEPTH_FRUGAL_ENABLED,  # D2354: FrugalGPT cascade (cheap depth model)
    S4_DEPTH_MAX_TOKENS,  # BUG-075: depth-only call token budget
    S4_DEPTH_MODEL,  # D2354: frugal depth model (Gemma)
    S4_DIFFICULTY_MAP,  # D2410/C12: depth→difficulty mapping (config-first)
    S4_GE_OUTPUT,
    S4_MAX_FAILED_RATIO,  # D2338: fail-closed merge tolerance
    S4_MAX_PRINCIPLES,
    S4_PI_OUTPUT,
    S4_PT_OUTPUT,
    S4_RELATED_FBS_EXCLUDE_DOMAINS,  # BUG-188: fallback domains excluded from domain_overlap
    S4_RELATED_FBS_MAX_NEIGHBORS,  # BUG-188: per-FB related_fbs neighbor cap (bounds graph to O(n·k))
    S4_SEMANTIC_NEAR_THRESHOLD,  # D2231: C12 compliance
    S4_TEMPORAL_SIGNALS,  # D2364/C12 (X7): temporal_scope keyword heuristics (was hardcoded)
    S4_TI_OUTPUT,
    STAGE2_CHECKPOINT,
    STAGE4_CHECKPOINT,
    VERIFY_MAX_TOKENS,  # D2249: GPT-OSS needs ≥1024 (BUG-074)
    VERIFY_MODEL,  # P0.10: imported for R5-compliant CRIBS classification (D2249: GPT-OSS-20B)
    VERIFY_REASONING_OFF_MODELS,  # D2249: models needing Reasoning:none prefix
    VERIFY_REASONING_OFF_PREFIX,  # D2249: GPT-OSS CoT suppression
)
from pipeline.schemas import (
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    get_synonym_index,
    is_valid_discipline,
    is_valid_domain,
)

# D2226: Merged S4 CRIBS+Classification single-call (D2224)
# D2265: Batch CRIBS+Classification — amortizes GPT-OSS reasoning cost
# BUG-075: classify_depth_focused — split depth into SHORT prompt (D2247)
from pipeline.stage4_merged_call import (
    BATCH_SIZE_DEFAULT,
    SparseClassificationError,  # D2357: fail-closed semantic validation (all classification paths)
    batch_depth_classify,  # D2477: batch the focused depth call (quality-neutral)
    batch_cribs_classify,
    classify_depth_focused,
    merged_cribs_classify,
)
from pipeline.intimacy_lattice import derive_context, resolve_intimacy  # W6/D369/D2375: v1 intimacy lattice + shared context derivation
from pipeline.stamp import get_pipeline_commit, get_pipeline_run_id, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
MAX_PRINCIPLES_PER_CLUSTER = S4_MAX_PRINCIPLES  # D2080: from config, was hardcoded 20

# D2410: temporal-signal match cache (compiled regexes keyed by lowercased signal).
_TEMPORAL_SIGNAL_RE_CACHE: dict[str, "re.Pattern[str]"] = {}


# ── Graceful pause/resume (SIGINT/SIGTERM) ──────────────────────────────────
# A hard Ctrl-C previously lost ≤ S4_CHECKPOINT_INTERVAL clusters of LLM work
# (no signal handler). The handler only SETS a flag; the main loop / depth
# pre-pass checks it at a safe boundary (between clusters / chunks) and calls
# _write_s4_checkpoint() + _write_depth_checkpoint() before exiting. Loss is
# capped at 0 clusters (the in-flight call is allowed to complete first).
_INTERRUPT_REQUESTED: bool = False


def _signal_handler(signum: int, frame) -> None:
    global _INTERRUPT_REQUESTED
    _INTERRUPT_REQUESTED = True
    print(f"\n⚠️  Signal {signum} received — finishing current unit, then checkpointing...", flush=True)


# ── BUG-183: stale-resume guard ─────────────────────────────────────────────
# Cluster IDs are STABLE across corpus changes (a relabeled S2 keeps the same
# hash-based IDs), so the D2424 "0-overlap → discard" guard never fires and a
# stale completed checkpoint would silently skip ~all clusters on resume.
# Fingerprint the ACTUAL S2 input (run_id + file size + mtime_ns) — any S2
# regeneration changes size/mtime_ns, so a mismatch = stale checkpoint.
_S2_INPUT_FINGERPRINT: str | None = None


def _s2_input_fingerprint(run_id: str) -> str:
    """BUG-183/D2491: content-hash the S4 input corpus, not size/mtime.

    The prior fingerprint used (run_id + file size + mtime_ns). That is fragile:
    Dropbox sync, `touch`, or `mv` can change mtime (or size reporting) without
    changing content, so a stale checkpoint could be silently accepted or a fresh
    one falsely rejected. Hashing the BYTE CONTENT of the S2 checkpoints plus the
    pipeline identity (schema, taxonomy, commit, manifest, model lineup) binds the
    S4 checkpoint to the exact input it merged — any regeneration OR config/model
    drift is detected fail-closed.
    """
    import hashlib
    from pipeline.pipeline_paths import (
        SCHEMA_VERSION,
        STAGE2_SINGLETON_OUTPUT,
        TAXONOMY_VERSION,
    )
    from pipeline.stamp import get_manifest_hash

    parts: list[str] = [
        f"run_id={run_id or ''}",
        f"schema_version={SCHEMA_VERSION}",
        f"taxonomy_version={TAXONOMY_VERSION}",
        f"pipeline_commit={get_pipeline_commit()}",
        f"manifest_hash={get_manifest_hash()}",
        f"gen_model={GEN_MODEL}",
        f"classify_model={VERIFY_MODEL}",
    ]
    for _p in (STAGE2_CHECKPOINT, STAGE2_SINGLETON_OUTPUT):
        try:
            h = hashlib.sha256()
            with open(_p, "rb") as _fh:
                for _chunk in iter(lambda: _fh.read(1 << 20), b""):
                    h.update(_chunk)
            parts.append(f"{_p.name}:sha256:{h.hexdigest()}")
        except OSError:
            parts.append(f"{_p.name}:missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _temporal_signal_hit(text: str, signals: list[str]) -> bool:
    """Boundary-aware temporal-signal match (D2410).

    Numeric signals (e.g. ``"202"``) match as a plain substring so a year
    prefix like "2024" is caught. Word signals use lookaround boundaries so a
    signal like "now" cannot false-match inside "knowledge", or "all" inside
    "allocation". Returns True on the first hit.
    """
    for raw in signals or []:
        sig = (raw or "").strip().lower()
        if not sig:
            continue
        if sig.isdigit():
            if sig in text:
                return True
            continue
        pattern = _TEMPORAL_SIGNAL_RE_CACHE.get(sig)
        if pattern is None:
            pattern = re.compile(rf"(?<![a-z0-9]){re.escape(sig)}(?![a-z0-9])")
            _TEMPORAL_SIGNAL_RE_CACHE[sig] = pattern
        if pattern.search(text):
            return True
    return False


def _derive_difficulty_level(depth: str, n_domains: int) -> str:
    """Map depth → difficulty via config (D2410/C12).

    ``domain`` is cardinality-aware: a single-domain FB is deep specialization
    ("expert") while a multi-domain FB is breadth ("intermediate"). Unknown
    depths fall back to "intermediate" (conservative, no over-claim).
    """
    if depth == "domain":
        key = "domain_single" if n_domains == 1 else "domain_multi"
        return S4_DIFFICULTY_MAP.get(key, "intermediate")
    return S4_DIFFICULTY_MAP.get(depth, "intermediate")


# D2323: non-principle role names sourced from config (C12) — routing dispatch
# references these, never re-declares the literal enum values.
_ROLE_PROCESS_TEMPLATE: str = ROUTE_TO_CONTENT_TYPE["PT"]
_ROLE_PROCESS_INSTANCE: str = ROUTE_TO_CONTENT_TYPE["PI"]
_ROLE_GROWTH_EDGE: str = ROUTE_TO_CONTENT_TYPE["GE"]
_ROLE_TOOL_INSTRUCTION: str = ROUTE_TO_CONTENT_TYPE["TI"]


def _resolve_content_type(fb: dict) -> str:
    """Resolve a principle's content_type, honoring the D2128 route→content_type fallback.

    D2128: S2's legacy `route` field (FB/PT/PI/GE/TI) was silently ignored by S4 —
    route=PT/GE outputs were never routed to their non-FB output files. When a
    record lacks an explicit content_type, fall back to the route mapping;
    otherwise trust the model's explicit content_type.

    Args:
        fb: A Stage 2 principle/FB record dict.

    Returns:
        A valid content_type role name (one of CONTENT_TYPES).
    """
    ct: str = (fb.get("content_type") or "").strip()
    if ct:
        return ct
    route: str = (fb.get("route") or "").strip().upper()
    return ROUTE_TO_CONTENT_TYPE.get(route, DEFAULT_CONTENT_TYPE)

# ── Prompt templates ───────────────────────────────────────────────────────

# ── CRIBS enrichment (D2137: fills missing fields for single-FB clusters) ──

CRIBS_ENRICHMENT_SYSTEM = """You enrich Foundation Blocks with CRIBS-quality fields. You receive an FB with
name + definition already written. Your job is to ADD the missing fields.

CRITICAL RULES:
- application: REQUIRED for EVERY principle — descriptive or prescriptive. NEVER null, never omit.
  REQUIRED FORMAT: "When [concrete situation], [specific action] because [reason]."
  For descriptive/theoretical principles (causal mechanisms, empirical patterns),
  frame it as "When [observing this pattern], [adjust reasoning/behavior] because [reason]."
  Example: "When launching a product in a crowded market, identify an underserved niche
  and dominate it before expanding, because concentrated resources create defensible momentum."
  ❌ ANTI-PATTERNS (DO NOT OUTPUT):
    - Domain names: "Marketing and negotiation tactics" ❌
    - Noun phrases: "Strategic decision making" ❌
    - Vague categories: "time resource management" ❌
    - Single-word: "Leadership" ❌

- failure_mode: REQUIRED FORMAT: "The principle fails when [specific condition]. [Why it breaks].
  [What happens instead]."
  Example: "The principle fails when the niche is too small to sustain a business. The
  concentration of resources creates overhead that can't be recovered, and competitors
  ignore the market entirely because there's nothing worth competing for."
  ❌ ANTI-PATTERNS:
    - Noun phrases: "Confirmation bias" ❌
    - Generic: "when conditions change" ❌
    - Circular: "when the principle doesn't apply" ❌

- elaboration: 3-5 substantive sentences. Include edge cases, non-obvious implications,
  second-order effects, and counterarguments. DO NOT restate the definition.
  ❌ ANTI-PATTERN: "This principle is important because it helps organizations..." ❌

- keywords: 3-5 specific search terms, comma-separated. RETRIEVAL labels, not explanations.
- jargon: OMIT this key entirely if no specialized terms exist. Only include when
  a non-expert would not understand specific terms used in the FB.
  ⚠️ NEVER copy keywords into jargon. Jargon is for pedagogy, keywords for search.

Return ONLY a JSON object:
{"application": "REQUIRED — never null", "failure_mode": "...", "elaboration": "...", "keywords": "...", "jargon": {...} or omit}"""


def _build_cribs_enrichment_prompt(fb_data: dict) -> str:
    """Build a lightweight CRIBS enrichment prompt for a single-FB cluster.

    Only asks for the fields stage2 doesn't produce: application, failure_mode,
    elaboration, keywords, jargon. The name + definition are already set.
    """
    name: str = fb_data.get("name", "")
    definition: str = fb_data.get("definition", "")
    mechanism: str = fb_data.get("mechanism", "")
    boundary: str = fb_data.get("boundary", "")
    consequence: str = fb_data.get("consequence", "")

    lines: list[str] = [
        "Add CRIBS-quality enrichment fields to this Foundation Block.",
        "",
        f"NAME: {name}",
        f"DEFINITION: {definition}",
    ]
    if mechanism:
        lines.append(f"MECHANISM: {mechanism}")
    if boundary:
        lines.append(f"BOUNDARY: {boundary}")
    if consequence:
        lines.append(f"CONSEQUENCE: {consequence}")
    lines.append("")
    lines.append("Return ONLY a JSON object with: application, failure_mode, elaboration, keywords, jargon")
    return "\n".join(lines)


CLASSIFY_SYSTEM_PROMPT = """You are a scientific taxonomy classifier. Your job is to identify
what discipline, domains, and ontological depth a Foundation Block genuinely belongs to,
using your full knowledge of academic fields and applied domains.

CRITICAL: Classify based on what the principle IS, not what label fits best from a predefined list.
Use precise, scientifically accurate names. If the principle is about "neuroaesthetics", say
"neuroaesthetics" — do not round it off to "design psychology" or "cognitive science".
If it's about "thermo-economics", say "thermo-economics" — not "economics".

Rules:
- discipline: The SINGLE academic/intellectual discipline this FB belongs to.
  Be specific. "computational neuroscience" > "neuroscience" > "cognitive science".
  D316: discipline is ALWAYS singular — pick the ONE discipline the FB fundamentally
  belongs to, even if it spans multiple domains.
- domains: 1-5 applied domains/fields/industries where this principle is relevant.
  Think: where would a practitioner USE this knowledge? What fields does it span?
- is_specialized: true ONLY if this is a narrow sub-technique within a sub-field.
  "Kerning Pair Adjustment" → true. "Design Strategy" → false. "Color harmony in brand" → true.
  "Strategic positioning" → false. Most FBs are NOT specialized. Default to false unless
  the principle is clearly a narrow technique, tool-specific skill, or sub-field detail.
- evidence: "cited" (grounded in source text) or "axiomatic" (self-evident truth)

DEPTH CLASSIFICATION — ONTOLOGICAL, NOT STRUCTURAL:
Depth describes how BROADLY the principle's CAUSAL MECHANISM applies across reality.
This is a SEMANTIC judgment about the mechanism's scope, NOT about how many domains
are listed. Use the PHYSICIST-CHEF-POET TEST:

  universal:     The mechanism applies to ALL systems — physical, biological, social, cognitive.
                 Test: Would a physicist, a chef, AND a poet each encounter this mechanism
                 in their own domain, WITHOUT borrowing domain-specific vocabulary?
                 Examples: "Iterative refinement improves outcomes" (feedback→correction
                 applies to physics experiments, recipes, AND poem revisions).
                 "Irrevocable choices foreclose alternatives" (true in thermodynamics,
                 cooking substitutions, AND narrative structure).

  cross-domain:  The mechanism CONNECTS two or more DISTINCT disciplines via a shared
                 causal structure. Must explicitly bridge domains that are normally separate.
                 Test: Does this reveal a structural isomorphism between Domain A and Domain B?
                 Examples: "Path dependency in technology adoption mirrors developmental
                 canalization in biology" (economics ↔ biology via irreversibility).

  domain:        The mechanism applies within ONE professional field or cluster of related
                 fields. Requires domain-specific vocabulary or context to understand.
                 Test: If you strip ALL domain jargon, does the mechanism become meaningless?
                 Examples: "Color contrast creates visual hierarchy" (requires understanding
                 of graphic design, visual perception in that context).
                 "Strategic positioning requires customer insight" (requires markets, brands).

  specialized:   The mechanism applies to a narrow sub-technique, tool-specific skill,
                 or niche methodology within a single sub-field.
                 Test: Would most practitioners IN the parent domain understand this?
                 Examples: "Kerning pair adjustment improves readability" (typography sub-field).
                 "Anchor point control in vector graphics" (graphics software feature).

CRITICAL: depth is NOT domain count. A design principle that spans 5 design-adjacent
domains (graphic design, UX, branding, editorial, packaging) is STILL domain, NOT universal.
The test is: can this mechanism be stated WITHOUT any domain-specific concepts?

DO NOT:
- Force-fit into generic categories
- Simplify complex disciplines into broad buckets
- Use "emerging" as a label — the pipeline decides that, not you
- Use placeholder labels like "other", "miscellaneous", "general"
- Use vague labels like "design" when "interaction design" or "speculative design" is more precise
- Over-assign "universal" — most principles are domain-bound. Default to "domain" unless
  the mechanism demonstrably crosses into physics, biology, or pure mathematics.

FEW-SHOT EXAMPLES (D2245 — cross-domain anchors):
1) FB "Feedback Loops Stabilize or Destabilize Systems":
   mechanism: "A feedback loop occurs when the output of a process feeds back as input,
   either dampening (negative feedback: thermostat, homeostasis, market correction) or
   amplifying (positive feedback: population growth, viral spread, bank runs). The same
   causal structure operates in biology (homeostasis), engineering (control systems),
   economics (speculative bubbles), and social systems (polarization)."
   → depth: "cross-domain" (mechanism bridges biology, engineering, economics via a
   shared causal structure — the feedback topology itself).

2) FB "The default option disproportionately persists":
   mechanism: "When a pre-selected option exists, decision-makers stick with it because
   opting out requires active effort and the default becomes the loss-reference point."
   → depth: "domain" (behavioral economics/decision science — requires that field's
   vocabulary; does not structurally connect distinct disciplines).

3) FB "Hierarchical taxonomy of human needs":
   mechanism: "Human needs are organized into ranked tiers (survival, safety, social,
   esteem, self-actualization); lower tiers dominate until satisfied, then higher tiers
   emerge. This descriptive structure is applied identically in consumer marketing
   (segmenting by need state), management (motivating teams), and clinical psychology
   (understanding deprivation), because it classifies a universal psychological
   structure that each field then operationalizes."
   → depth: "cross-domain" (a descriptive taxonomy whose classificatory structure is
   shared across psychology, management, and marketing — the same hierarchy is applied
   in each field without field-specific vocabulary).

4) FB "Attribute substitution under pressure":
   mechanism: "When the target question is hard, intuitive judgment substitutes an
   easier question ('how dangerous does this person seem?' for 'what sentence is
   legally correct?'). This substitution operates identically in judicial sentencing,
   medical diagnosis, and financial risk assessment — professionals in each field
   answer a proxy question under cognitive load."
   → depth: "cross-domain" (the same cognitive mechanism structurally bridges law,
   medicine, and finance via shared substitutability).

Return ONLY a JSON object: {"discipline": "discipline_name", "domains": ["d1", "d2"], "depth": "universal|cross-domain|domain|specialized", "is_specialized": true/false, "evidence": "..."}"""

# ── D2454 (2026-08-27): inject the config-driven S4 classification golden. ──
# The golden (config/golden/stage4_golden.yaml, authored D2451) replaces the
# hardcoded inline depth anchors above with a versioned, test-validated set.
# Fail-closed (D2463 pattern): enabled + missing/malformed/empty → raise, so the
# pipeline never silently degrades to zero-shot. Gate: `stage4.golden_inject_enabled`.
try:
    from pipeline.pipeline_paths import S4_GOLDEN_INJECT_ENABLED, S4_GOLDEN_MAX_EXAMPLES, S4_GOLDEN_PATH
    if S4_GOLDEN_INJECT_ENABLED:
        from pipeline.s4_golden import format_classify_golden, load_stage4_golden
        _s4_examples = load_stage4_golden(S4_GOLDEN_PATH)[:S4_GOLDEN_MAX_EXAMPLES]
        _s4_golden_block = "\n\nFEW-SHOT EXAMPLES (config-driven, D2454):\n" + format_classify_golden(_s4_examples)
        CLASSIFY_SYSTEM_PROMPT = CLASSIFY_SYSTEM_PROMPT + _s4_golden_block
except Exception as _s4_golden_err:  # C16: fail-loud — never silently skip an enabled gate
    raise RuntimeError(f"D2454: stage4_golden injection failed: {_s4_golden_err}") from _s4_golden_err


def build_classify_prompt(
    fb_name: str,
    fb_definition: str,
    mechanism: str = "",
    boundary: str = "",
) -> str:
    """Build a FREE scientific classification prompt — no canonical lists.

    D2138: Two-stage classification. Stage 1: LLM classifies freely using its
    full scientific knowledge (produces raw labels). Stage 2: pipeline maps
    raw labels to canonical taxonomy, using 'emerging' as fallback.

    D2220: DEPTH is now LLM-classified semantically (not derived from domain count).
    The LLM applies the physicist-chef-poet test to determine ontological scope.
    This replaces the structural derivation that caused 55% depth error rate.

    D2226 (Kimi audit fix): Now receives mechanism + boundary alongside name + definition.
    The physicist-chef-poet test REQUIRES the mechanism to assess ontological scope —
    classification without mechanism produces depth errors. Previously only name +
    definition were passed, causing input-starvation and misclassification.

    This preserves ontological accuracy — raw labels capture what the principle
    genuinely IS, while canonical labels organize it within our taxonomy.
    """
    lines: list[str] = [
        "Classify this Foundation Block scientifically.",
        "",
        f"NAME: {fb_name}",
        f"DEFINITION: {fb_definition[:800]}",
    ]
    if mechanism:
        lines.append(f"MECHANISM: {mechanism[:600]}")
    if boundary:
        lines.append(f"BOUNDARY: {boundary[:300]}")
    lines.extend([
        "",
        "Identify:",
        "1. What academic/intellectual discipline does this principle fundamentally belong to?",
        "   (Use the most precise discipline name you know — not generic buckets)",
        "2. What applied domains/fields/industries does this principle span?",
        "   (1-5 domains where a practitioner would apply this knowledge)",
        "3. DEPTH (ontological scope): universal, cross-domain, domain, or specialized?",
        "   Apply the physicist-chef-poet test. Does the mechanism apply across ALL reality",
        "   (universal), bridge two distinct disciplines via shared structure (cross-domain),",
        "   operate within one field (domain), or describe a narrow sub-technique (specialized)?",
        "   DEFAULT to \"domain\" unless the mechanism clearly transcends it.",
        "4. Is this a NARROW sub-technique or sub-field detail? (is_specialized: true/false)",
        "   - true = narrow technique, tool-specific skill, sub-field detail (e.g., \"Kerning Pair Adjustment\")",
        "   - false = broad principle applicable across the domain (e.g., \"Design Strategy\")",
        "   - Default to false unless clearly narrow.",
    ])
    return "\n".join(lines)


def map_to_canonical_with_fallback(raw_label: str, kind: str,
                                     synonym_index: dict[str, str],
                                     canonical_list: list[str]) -> str:
    """Map a raw scientific label to canonical taxonomy. Returns 'emerging' if no match.

    D2138: Two-stage classification. The raw label is the LLM's free scientific
    classification — it captures what the principle genuinely IS. The canonical
    label maps it into our taxonomy for organization.

    When raw == canonical (exact match), the principle pragmatically and ontologically
    falls under that canonical label 100%. When no match exists, canonical = 'emerging'
    and the raw label is preserved forever — enabling future taxonomy expansion via
    re-mapping without re-running the pipeline.

    Args:
        raw_label: The LLM's free classification (e.g., "neuroaesthetics")
        kind: "discipline" or "domain" (constrains canonical list)
        synonym_index: Pre-built synonym map (lowercase raw → canonical)
        canonical_list: The full canonical list for this kind

    Returns:
        Canonical label string, or "emerging" if nothing matches.
    """
    if not raw_label or not raw_label.strip():
        return "emerging"

    raw_lower = raw_label.strip().lower()

    # 1. Exact canonical match (case-insensitive) — principle fits 100%
    for c in canonical_list:
        if c.lower() == raw_lower:
            return c  # Return canonical casing

    # 2. Synonym index match (e.g., "visual communication" → "graphic design")
    matched = synonym_index.get(raw_lower)
    if matched:
        matched_lower = matched.lower()
        for c in canonical_list:
            if matched_lower == c.lower():
                return c
        # Flat index may have resolved to the wrong KIND (D2133: e.g. raw
        # "cloud computing" → discipline "software engineering" when we need a
        # domain). Retry with the kind-constrained index before giving up.
        from pipeline.schemas import get_synonym_index as _get_kind_syn
        kind_matched = _get_kind_syn(kind).get(raw_lower)
        if kind_matched:
            for c in canonical_list:
                if kind_matched.lower() == c.lower():
                    return c

    # 3. No match — genuinely novel. Raw label preserved; canonical = "emerging"
    return "emerging"


def _load_fb_id_allowlist(path: str | None) -> set[str] | None:
    """Load an fb_id allow-list from a JSONL file (each line {"fb_id": ...}).

    Fail-closed (C16/D2332): a missing or empty allow-list exits with an error —
    never silently falls back to processing the full corpus when a filter was requested.
    """
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        print(f"❌ --only-fb-ids allow-list not found: {path}")
        sys.exit(1)
    rows = load_jsonl(p, context="--only-fb-ids allow-list")
    ids: set[str] = {r["fb_id"] for r in rows if isinstance(r, dict) and r.get("fb_id")}
    if not ids:
        print(f"❌ --only-fb-ids allow-list is empty or has no fb_id field: {path}")
        sys.exit(1)
    return ids


def load_stage2_fbs_via_clusters(only_fb_ids: set[str] | None = None) -> tuple[list[dict], dict[str, dict]]:
    """D2120: Load FBs from Stage 2, wrapping each as a single-FB cluster.

    Stage 3 (HDBSCAN dedup) has been REMOVED — architecturally redundant in
    cluster-before-extract (D2094). Each Stage 2 FB becomes its own ''cluster''
    for downstream Stage 4 processing (classification + formatting).

    Returns:
        Tuple of (clusters: list[dict], principles_idx: dict[str, dict]).
        Each cluster wraps a single FB: {cluster_id, principle_ids: [fb_id], ...}
    """
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found. Run stage2_extract.py first.")
        sys.exit(1)

    clusters: list[dict] = []
    principles_idx: dict[str, dict] = {}

    # D2332: fail-closed JSONL load — a pretty-printed checkpoint must raise, not silently drop records.
    s2_records: list[dict] = load_jsonl(STAGE2_CHECKPOINT, context="S2 checkpoint")
    if only_fb_ids is not None:
        _before = len(s2_records)
        s2_records = [
            fb for fb in s2_records
            if (fb.get("fb_id") or fb.get("principle_id", "")) in only_fb_ids
        ]
        if not s2_records:
            print(f"❌ --only-fb-ids matched 0 records (allow-list={len(only_fb_ids)} ids). Refusing empty run.")
            sys.exit(1)
        print(f"ℹ️  --only-fb-ids filter: {_before} → {len(s2_records)} S2 records")
    for i, fb in enumerate(s2_records, 1):
        # Index by both fb_id and principle_id (v2.x/v3.0 compat)
        fb_id_val = fb.get("fb_id") or fb.get("principle_id", "")
        pid_val = fb.get("principle_id", "")
        if fb_id_val:
            principles_idx[fb_id_val] = fb
        if pid_val and pid_val != fb_id_val:
            principles_idx[pid_val] = fb

        # Wrap as a single-FB cluster
        # D2176: Preserve is_noise/is_singleton semantics from S1.5/S2.
        # OLD: is_noise = not is_convergent — treated ALL single-source and
        # singleton FBs as noise, overwriting the S1.5 fix (D2171).
        # NEW: is_noise is an independent quality state. A single-source FB
        # or singleton is NOT noise — it just has weaker corroboration.
        # origin field tracks the structural provenance independently.
        is_convergent: bool = fb.get("is_convergent", False)
        is_singleton: bool = fb.get("is_singleton_fb", False) or fb.get("is_singleton", False)
        is_noise: bool = fb.get("is_noise", False)  # Only True if S1.5/S2 explicitly marked noise

        # Derive origin from structural properties
        if is_singleton:
            origin: str = "singleton"
        elif is_convergent:
            origin: str = "convergent"
        else:
            origin: str = "single_source"

        clusters.append({
            # D2350: preserve the REAL S2 cluster id (e.g. "cluster_48_s1_sub1"),
            # NOT the fb_id. Previously fb_id_val was used here, which caused
            # `source_clusters` in S4/DB to store an fb_id instead of a cluster id,
            # breaking cluster→segment provenance tracing.
            "cluster_id": fb.get("source_cluster") or fb_id_val or f"fb_{i}",
            "principle_ids": [fb_id_val] if fb_id_val else [f"fb_{i}"],
            "source_books": fb.get("source_books", []),
            "is_convergent": is_convergent,
            "is_noise": is_noise,
            "is_singleton": is_singleton,
            "origin": origin,
            "source": "stage2_fb",  # Mark as directly from Stage 2
        })

    # D2176: Also load singleton FBs. Stage 2 writes convergent + single-source FBs
    # to STAGE2_CHECKPOINT and singleton FBs to a separate file. Previously
    # Stage 4 only read the main checkpoint — singletons were silently dropped.
    # Now we merge both sources into a single canonical principle index.
    from pipeline.pipeline_paths import STAGE2_SINGLETON_OUTPUT
    singleton_count: int = 0
    if STAGE2_SINGLETON_OUTPUT.exists():
        for fb in load_jsonl(STAGE2_SINGLETON_OUTPUT, context="S2 singleton checkpoint"):
            fb_id_val = fb.get("fb_id") or fb.get("principle_id", "")
            if fb_id_val:
                principles_idx[fb_id_val] = fb

            # Singleton FBs are always: not convergent, not noise, is singleton
            clusters.append({
                # D2350: preserve the REAL singleton cluster id (S2 emits
                # `source_cluster` = "singleton_xxx") instead of fb_id.
                "cluster_id": fb.get("source_cluster") or fb_id_val or f"singleton_{singleton_count}",
                "principle_ids": [fb_id_val] if fb_id_val else [f"singleton_{singleton_count}"],
                "source_books": fb.get("source_books", []),
                "is_convergent": False,
                "is_noise": False,
                "is_singleton": True,
                "origin": "singleton",
                "source": "stage2_singleton",
            })
            singleton_count += 1
        print(f"   📂 Loaded {len(clusters) - singleton_count} FBs from Stage 2 + {singleton_count} singletons (Stage 3 bypassed per D2120)")
    else:
        print(f"   📂 Loaded {len(clusters)} FBs from Stage 2 (Stage 3 bypassed per D2120)")

    return clusters, principles_idx


def dedup_fbs_by_cosine(
    fbs: list[dict],
    threshold: float = S4_DEDUP_COSINE_THRESHOLD,  # D2231: from config (was hardcoded 0.92)
    model: str = "bge-m3",
) -> list[dict]:
    """D2120: Lightweight FB dedup replacing removed Stage 3 HDBSCAN.

    Embeds FB definitions via bge-m3, computes pairwise cosine similarity,
    and removes near-duplicates. Keeps the FB with higher source diversity
    (more source_books) as the winner.

    Args:
        fbs: List of FB dicts from Stage 2.
        threshold: Cosine similarity above which FBs are considered duplicates.
        model: Embedding model for semantic comparison.

    Returns:
        Deduplicated list of FBs (order preserved, duplicates removed).
    """
    from pipeline.ollama_embed import batch_embed
    from pipeline.schema_accessor import fb_definition, fb_source_books

    if len(fbs) < 2:
        return fbs

    definitions = [fb_definition(fb) for fb in fbs]
    raw_embs = batch_embed(definitions, model=model)

    import numpy as np

    # D2490: align embeddings to fbs by index. An empty embedding (embedding
    # failure) maps to None and is excluded from dedup rather than silently
    # dropping the row — the old code filtered empty rows but kept n=len(fbs),
    # so `similarity[i, j]` IndexError'd whenever any FB failed to embed.
    aligned: list[np.ndarray | None] = [
        np.asarray(e, dtype=np.float32) if e is not None and len(e) > 0 else None
        for e in raw_embs
    ]
    valid = [i for i, e in enumerate(aligned) if e is not None]
    if len(valid) < 2:
        return fbs

    embs = np.stack([aligned[i] for i in valid]).astype(np.float32, copy=False)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embs = embs / norms

    m = len(valid)
    removed: set[int] = set()  # indices into `valid`

    # D2490: chunk the cosine matrix so peak memory is O(chunk·m), not O(m²).
    _DEDUP_CHUNK = 512
    for i_start in range(0, m, _DEDUP_CHUNK):
        i_end = min(i_start + _DEDUP_CHUNK, m)
        sim_chunk = embs[i_start:i_end] @ embs.T  # (chunk, m)
        for i in range(i_start, i_end):
            if i in removed:
                continue
            for j in range(i + 1, m):
                if j in removed:
                    continue
                if float(sim_chunk[i - i_start, j]) >= threshold:
                    # Keep FB with more source diversity
                    books_i = len(fb_source_books(fbs[valid[i]]))
                    books_j = len(fb_source_books(fbs[valid[j]]))
                    if books_i >= books_j:
                        removed.add(j)
                    else:
                        removed.add(i)
                        break  # i removed, stop checking j against i

    if removed:
        removed_orig = {valid[k] for k in removed}
        kept = [fbs[i] for i in range(len(fbs)) if i not in removed_orig]
        print(f"   🔍 Dedup: {len(removed_orig)} near-duplicate FBs removed "
              f"(cos ≥ {threshold}), {len(kept)} kept")
        return kept

    return fbs


def validate_classification(result: dict) -> tuple[bool, list[str]]:
    """Validate multi-label classification output against canonical taxonomy.

    D2066: disciplines is now a list (1-3). D2024 single-discipline approach superseded.
    Returns (is_valid, errors).
    """
    errors: list[str] = []

    # D316: discipline is SINGULAR — validate as string
    discipline = result.get("discipline", "")
    if isinstance(discipline, list):
        # Backward compat: if LLM returns old list format, take first element
        discipline = discipline[0] if discipline else ""
        result["discipline"] = discipline
    if not discipline:
        errors.append("Discipline is required (D316: singular)")
    elif not isinstance(discipline, str):
        errors.append(f"Discipline is not a string: {type(discipline)}")
    elif not is_valid_discipline(discipline):
        errors.append(f"Invalid discipline: '{discipline}'")

    # Validate domains
    domains = result.get("domains", [])
    if not isinstance(domains, list):
        errors.append(f"Domains is not a list: {type(domains)}")
    else:
        if len(domains) < 1:
            errors.append("At least 1 domain required")
        if len(domains) > MAX_DOMAINS_PER_FB:
            errors.append(f"Too many domains: {len(domains)} > {MAX_DOMAINS_PER_FB}")
        for d in domains:
            if not is_valid_domain(d):
                errors.append(f"Invalid domain: '{d}'")

    # Validate depth
    depth = result.get("depth", "")
    if depth not in ("universal", "cross-domain", "domain", "specialized"):
        errors.append(f"Invalid depth: '{depth}'")

    # Validate evidence
    evidence = result.get("evidence", "")
    if evidence not in ("cited", "axiomatic"):
        errors.append(f"Invalid evidence: '{evidence}'")

    return len(errors) == 0, errors


def normalize_fb_name(name: str, max_words: int = FB_NAME_MAX_WORDS) -> str:
    """Normalize FB name: title case, word count enforcement, strip punctuation.

    D2069: Ensures consistent, searchable, non-sentence-style names.
    """
    import re
    name = name.strip().strip('"').strip("'")
    # Remove trailing periods, colons
    name = re.sub(r'[.:;]+$', '', name)
    # Title case: capitalize first letter of each word, except articles/prepositions
    minor_words = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'nor', 'with', 'by'}
    words = name.split()
    if not words:
        return name
    normalized = []
    for i, w in enumerate(words):
        if i == 0 or i == len(words) - 1 or w.lower() not in minor_words:
            normalized.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
        else:
            normalized.append(w.lower())
    name = ' '.join(normalized)
    # Word count enforcement: truncate if too long
    if max_words and len(words) > max_words:
        name = ' '.join(words[:max_words])
        print(f"      ⚠️  Name truncated to {max_words} words: '{name}'")
    return name


def check_name_unique(name: str, existing_names: set[str]) -> bool:
    """Check if FB name is unique against existing names in this batch.

    D2069: Prevents cross-cluster name collisions within a single pipeline run.
    Cross-run uniqueness is enforced at Stage 6 commit via DB unique constraint.
    """
    return name not in existing_names


def _collect_source_text(principles: list[dict]) -> str | None:
    """Collect source text from cluster principles for verification.

    Concatenates principle_text fields with source attribution.
    Returns None if no text available.
    """
    texts: list[str] = []
    for p in principles:
        pt = (p.get("definition") or p.get("principle_text", "")).strip()
        if pt:
            source = p.get("source", p.get("source_books", ["unknown"])[0] if p.get("source_books") else "unknown")
            texts.append(f"[{source}] {pt}")
    return "\n\n".join(texts) if texts else None


def _serialize_jargon(jargon_value) -> str | None:
    """Convert jargon (dict or string) to flat string. Returns None if empty/absent.

    LLM sometimes returns jargon as {"term": "explanation"} dict.
    When no specialized terms exist, jargon should be absent — return None
    so the FB record omits the field entirely.
    """
    if jargon_value is None:
        return None
    if isinstance(jargon_value, str):
        stripped = jargon_value.strip()
        if not stripped or stripped in ("{}", "null", "None", ""):
            return None
        return stripped
    if isinstance(jargon_value, dict):
        if not jargon_value:
            return None
        parts = []
        for term, explanation in jargon_value.items():
            if explanation:
                parts.append(f"{term}: {explanation}")
            else:
                parts.append(term)
        return "; ".join(parts) if parts else None
    if isinstance(jargon_value, list):
        result = "; ".join(str(item) for item in jargon_value if item)
        return result if result else None
    return None


# ── P1.4: FB Relationship Edge Detection ──────────────────────────────────

# BUG-188: relationship-type priority for the per-FB neighbor cap.
# Lower priority = more informative edge = retained first when an FB has more
# than S4_RELATED_FBS_MAX_NEIGHBORS candidates. semantic_near (cosine) is the
# strongest signal; bare domain_overlap (esp. the ubiquitous "emerging" fallback)
# is the weakest and is capped away first.
_RELATIONSHIP_PRIORITY: dict[str, int] = {
    "semantic_near": 0,
    "source_crossover": 1,
    "discipline_overlap": 2,
    "domain_overlap": 3,
}


def _push_neighbor(heap: list, k: int, entry: tuple) -> None:
    """Keep the top-k entries by goodness in a bounded min-heap (BUG-188).

    entry = (goodness, neighbor_index, relationships) where goodness is the
    comparable tuple `(-priority, similarity)` — larger is better. A min-heap
    exposes the WORST kept entry at index 0, so when full we replace it only
    if the candidate is better. Bounds memory to O(n·k) regardless of graph
    density (the old unbounded O(n²) adjacency blew the checkpoint past 2GB).
    """
    if k <= 0:
        return
    if len(heap) < k:
        heapq.heappush(heap, entry)
    elif entry[0] > heap[0][0]:
        heapq.heapreplace(heap, entry)


def compute_fb_relationships(
    fbs: list[dict],
    similarity_threshold: float = S4_SEMANTIC_NEAR_THRESHOLD,  # D2231: from config (was hardcoded 0.80)
    max_neighbors: int = S4_RELATED_FBS_MAX_NEIGHBORS,  # BUG-188: per-FB cap
    exclude_domains: set[str] | frozenset[str] | None = None,
) -> list[dict]:
    """Compute FB-to-FB relationships for LightRAG graph foundation.

    D2118, D2120: Relationship edges enable graph-based knowledge retrieval.
    Four relationship types:
      - domain_overlap: FBs sharing ≥1 domain label
      - discipline_overlap: FBs sharing ≥1 discipline (D2066 multi-label)
      - source_crossover: FBs derived from ≥1 shared source book
      - semantic_near: Cosine similarity ≥ threshold on definition embeddings

    BUG-188: the graph is bounded to O(n·k) edges — each FB keeps at most
    `max_neighbors` neighbours, ranked semantic_near > source_crossover >
    discipline_overlap > domain_overlap, with cosine similarity as tiebreak.
    Fallback domains (e.g. "emerging") are excluded from domain_overlap because
    a shared *fallback* label is not a meaningful relationship and previously
    fabricated a near-complete graph (32M edges) that truncated the checkpoint.

    Writes `related_fbs` list onto each FB dict (mutates in place).

    Args:
        fbs: List of FB dicts (with domains, disciplines, source_books, definition).
        similarity_threshold: Cosine similarity threshold for semantic_near edges.
        max_neighbors: Hard cap on related_fbs neighbours per FB (BUG-188).
        exclude_domains: Fallback domains excluded from domain_overlap. Defaults
                         to config `related_fbs_exclude_domains`.

    Returns:
        The same fbs list, mutated with `related_fbs` fields.
    """
    if len(fbs) < 2:
        for fb in fbs:
            fb.setdefault("related_fbs", [])
        return fbs

    if exclude_domains is None:
        exclude_domains = frozenset(S4_RELATED_FBS_EXCLUDE_DOMAINS)

    n: int = len(fbs)
    print(f"\n🔗 Computing FB relationships for {n} FBs (cap {max_neighbors}/FB, excluding fallback domains {sorted(exclude_domains)})...")

    # Embed definitions for semantic similarity
    try:
        import numpy as np

        from pipeline.embeddings import embed_texts_bge_m3

        definitions: list[str] = [fb.get("definition", "")[:500] for fb in fbs]
        embeddings: np.ndarray = embed_texts_bge_m3(definitions)
        # Normalize for cosine
        norms: np.ndarray = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)  # Avoid div-by-zero
        embeddings = embeddings / norms
        has_embeddings: bool = True
    except Exception as e:
        print(f"   ⚠️  Embedding failed ({e}), skipping semantic edges")
        has_embeddings = False
        embeddings = None

    # Pre-extract sets for fast comparison — strip fallback domains (e.g. "emerging")
    # so a shared fallback label no longer fabricates a dense domain_overlap graph.
    fb_id_list: list[str] = [fb["fb_id"] for fb in fbs]
    domain_sets: list[set[str]] = [set(fb.get("domains", [])) - exclude_domains for fb in fbs]
    # D316: discipline is singular — wrap in set for comparison
    discipline_sets: list[set[str]] = [{fb.get("discipline", "")} if fb.get("discipline") else set() for fb in fbs]
    book_sets: list[set[str]] = [set(fb.get("source_books", [])) for fb in fbs]

    # Initialize related_fbs on all FBs
    for fb in fbs:
        fb["related_fbs"] = []

    # Bounded per-FB neighbour heaps (BUG-188: O(n·k) memory, not O(n²))
    heaps: list[list] = [[] for _ in range(n)]

    edge_counts: dict[str, int] = {"domain_overlap": 0, "discipline_overlap": 0,
                                      "source_crossover": 0, "semantic_near": 0}

    # D2490: chunk the pairwise cosine matrix so peak memory is O(chunk·n), not
    # O(n²). Also guard against embeddings that don't align 1:1 with fbs (an
    # embedding failure) so semantic access can never IndexError.
    _REL_CHUNK = 512
    _emb_ok = has_embeddings and embeddings is not None and embeddings.shape[0] == n
    if has_embeddings and embeddings is not None and not _emb_ok:
        print(f"   ⚠️  Embedding count {embeddings.shape[0]} != FB count {n} — skipping semantic edges")
        has_embeddings = False
        embeddings = None

    # Pairwise comparison (upper triangle) → bounded per-FB neighbour heaps.
    for i_start in range(0, n, _REL_CHUNK):
        i_end = min(i_start + _REL_CHUNK, n)
        sim_chunk = embeddings[i_start:i_end] @ embeddings.T if _emb_ok else None
        for i in range(i_start, i_end):
            for j in range(i + 1, n):
                relationships: list[str] = []

                # Domain overlap (fallback domains already stripped)
                if domain_sets[i] & domain_sets[j]:
                    relationships.append("domain_overlap")

                # Discipline overlap (D2066 multi-label)
                if discipline_sets[i] & discipline_sets[j]:
                    relationships.append("discipline_overlap")

                # Source crossover
                if book_sets[i] & book_sets[j]:
                    relationships.append("source_crossover")

                # Semantic similarity
                if sim_chunk is not None:
                    if float(sim_chunk[i - i_start, j]) >= similarity_threshold:
                        relationships.append("semantic_near")

                if not relationships:
                    continue

                # BUG-188: keep only the top-k most informative neighbours per FB.
                priority = min(_RELATIONSHIP_PRIORITY[r] for r in relationships)
                sim = float(sim_chunk[i - i_start, j]) if sim_chunk is not None else 0.0
                goodness = (-priority, sim)  # larger = better
                _push_neighbor(heaps[i], max_neighbors, (goodness, j, relationships))
                _push_neighbor(heaps[j], max_neighbors, (goodness, i, relationships))

    # Materialize bounded neighbour lists onto each FB.
    for i in range(n):
        for goodness, j, relationships in sorted(heaps[i], key=lambda x: x[0], reverse=True):
            fbs[i]["related_fbs"].append({
                "fb_id": fb_id_list[j],
                "relationships": relationships,
            })
            for rel in relationships:
                edge_counts[rel] = edge_counts.get(rel, 0) + 1

    # Summary (edge_counts are bidirectional stored entries — halve for undirected edges)
    print(f"   Domain overlap:       {edge_counts['domain_overlap'] // 2} edges")
    print(f"   Discipline overlap:   {edge_counts['discipline_overlap'] // 2} edges")
    print(f"   Source crossover:     {edge_counts['source_crossover'] // 2} edges")
    if has_embeddings:
        print(f"   Semantic near (cos≥{similarity_threshold:.2f}): {edge_counts['semantic_near'] // 2} edges")

    total_edges: int = sum(edge_counts.values()) // 2
    isolated: int = sum(1 for fb in fbs if not fb["related_fbs"])
    print(f"   Total edges: {total_edges} | Isolated FBs: {isolated}/{n}")

    return fbs




# ── CRIBS Quality Guard (D2293) ──────────────────────────────────────────

def _validate_cribs_quality(fb_data: dict) -> dict:
    """D2293: Post-generation CRIBS quality check. Flags short/vague enrichment fields.

    Returns dict with 'cribs_warnings': list[str] for logging.
    Does NOT block FB creation — enrichment is best-effort. Warnings are informational.
    """
    warnings = []
    app = str(fb_data.get("application", "")).strip()
    fm = str(fb_data.get("failure_mode", "")).strip()
    elab = str(fb_data.get("elaboration", "")).strip()

    # Application: must be full sentence with situation→action, or null
    if app and len(app) < 50:
        warnings.append(f"CRIBS-SHORT-APP ({len(app)}c): '{app[:80]}'")
    if app and not any(kw in app.lower() for kw in ("when ", "→", "because")):
        warnings.append(f"CRIBS-FORMAT-APP: missing 'When X → do Y' pattern: '{app[:80]}'")

    # Failure mode: must describe specific failure condition
    if fm and len(fm) < 60:
        warnings.append(f"CRIBS-SHORT-FM ({len(fm)}c): '{fm[:80]}'")
    if fm and "fails when" not in fm.lower() and "principle fails" not in fm.lower():
        warnings.append(f"CRIBS-FORMAT-FM: missing 'fails when' pattern: '{fm[:80]}'")

    # Elaboration: should be multiple sentences
    if elab and len(elab) < 80:
        warnings.append(f"CRIBS-SHORT-ELAB ({len(elab)}c)")

    return {"cribs_warnings": warnings}


def _log_cribs_warnings(fb_data: dict) -> None:
    """D2293: Log CRIBS quality warnings. Prints summary, stashes detail in fb_data."""
    quality = _validate_cribs_quality(fb_data)
    warnings = quality.get("cribs_warnings", [])
    if warnings:
        fb_data["cribs_warnings"] = warnings
        # Print abbreviated warning
        fb_name = str(fb_data.get("name", "?"))[:40]
        print(f"⚠️CRIBS({len(warnings)})", flush=True, end=" ")

def _write_sidecar_json(data: dict, path: Path) -> None:
    """BUG-184/D2481: crash-safe incremental pre-pass sidecar checkpoint.

    The D2477 depth / D2265 CRIBS pre-passes previously lived ONLY in in-memory
    dicts (``_pre_depth`` / ``_pre_classified``) — a mid-pre-pass kill lost them
    all. Persist the cluster_id→result map atomically (tempfile → fsync →
    os.replace, C6) after every chunk so a resume skips already-classified
    clusters and only re-runs the remainder.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir=str(path.parent)
    )
    try:
        json.dump(data, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, str(path))
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def _write_depth_checkpoint(pre_depth: dict, path: Path) -> None:
    """Compatibility alias for ``_write_sidecar_json`` (depth pre-pass)."""
    _write_sidecar_json(pre_depth, path)


def _write_s4_checkpoint(fbs: list[dict], processed_ids: set[str], scalar_state: dict) -> None:
    """D2370: crash-safe intra-stage S4 checkpoint (mirrors S2's D2154 pattern).

    The long serial S4 stage (~39h on ~3,556 FBs) previously wrote its checkpoint
    ONCE at the end — a mid-run kill lost every FB processed so far. This writes an
    incremental snapshot, atomically (tempfile → fsync → os.replace, C6), of:

      1. STAGE4_CHECKPOINT — the FB JSONL so far (self-verified, BUG-106 parity).
      2. <checkpoint>.segids — processed cluster IDs (skip-on-resume).
      3. <checkpoint>.state.json — counters not recoverable from FB records
         (classification_errors / name_collisions) so the D2338 fail-closed gate
         stays correct across a resume. `failed` is deliberately NOT persisted:
         failed (no-FB) clusters are not marked processed, so they are retried on
         resume and re-counted (temp=0.0 makes a stale persisted count a double-count).

    Args:
        fbs: Accumulated FB records (partial).
        processed_ids: Cluster IDs already appended (successful + quarantined-classification).
        scalar_state: dict of {classification_errors, name_collisions}.
    """
    # BUG-188: stream + verify byte/record count instead of building one multi-GB join string.
    safe_write_jsonl(STAGE4_CHECKPOINT, fbs, force_shrink=True)
    loaded = load_jsonl(STAGE4_CHECKPOINT, context="S4 checkpoint self-check")  # raises if corrupt
    if len(loaded) != len(fbs):
        raise IOError(
            f"S4 checkpoint record-count mismatch: wrote {len(fbs)} FBs but read "
            f"{len(loaded)} — partial write/truncation, refusing to continue"
        )

    segids_file = str(STAGE4_CHECKPOINT) + ".segids"
    segids_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".segids", delete=False, dir=str(STAGE4_CHECKPOINT.parent)
    )
    try:
        json.dump(sorted(processed_ids), segids_tmp)
        segids_tmp.flush()
        os.fsync(segids_tmp.fileno())
        segids_tmp.close()
        os.replace(segids_tmp.name, segids_file)
    except Exception:
        if os.path.exists(segids_tmp.name):
            os.unlink(segids_tmp.name)
        raise  # C16: sidecar write failure must be loud (stale resume state = silent corruption)

    state_file = str(STAGE4_CHECKPOINT) + ".state.json"
    state_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".state", delete=False, dir=str(STAGE4_CHECKPOINT.parent)
    )
    try:
        # BUG-183: persist the S2-input fingerprint alongside the counters so a
        # resume can detect a stale checkpoint (S2 corpus regenerated in place).
        _state = dict(scalar_state)
        if _S2_INPUT_FINGERPRINT is not None:
            _state["s2_input_fingerprint"] = _S2_INPUT_FINGERPRINT
        _state["record_count"] = len(fbs)  # D2487: asserted on resume (clean-cut truncation guard)
        json.dump(_state, state_tmp)
        state_tmp.flush()
        os.fsync(state_tmp.fileno())
        state_tmp.close()
        os.replace(state_tmp.name, state_file)
    except Exception:
        if os.path.exists(state_tmp.name):
            os.unlink(state_tmp.name)
        raise  # C16: sidecar write failure must be loud (stale resume state = silent corruption)


def _stamp_sidecar(rec: dict, pipeline_run_id: str, pipeline_commit: str) -> dict:
    """R14 + BUG-170: re-stamp a routed non-principle sidecar with S4 run traceability.

    Non-principle records (PT/PI/TI/GE) pass through S4 UNCHANGED — their content is
    still S2's extraction. So we must NOT overwrite `gen_model` / `created_at` (S2
    content provenance). We only refresh the run-traceability stamps so the sidecar is
    attributable to the S4 run that wrote it (previously it carried only S2's
    `pipeline_run_id`, making it untraceable — the "stale stamps" finding).
    """
    rec["pipeline_run_id"] = pipeline_run_id
    rec["pipeline_commit"] = pipeline_commit
    rec["routed_by_stage"] = "stage4_merge"
    return rec


def run_stage4(cluster_ids: list[int | str] | None = None, only_fb_ids: set[str] | None = None,
               depth_only: bool = False):
    """Run Stage 4: Merge clusters into Foundation Blocks.

    depth_only (D2497): run ONLY the D2477 batched depth pre-pass, checkpoint it,
    then exit 0 BEFORE the main serial classify loop. The .depth.json sidecar
    survives so a subsequent full run resumes the pre-pass instead of re-running it.
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Graceful pause/resume: install SIGINT/SIGTERM handlers so a Ctrl-C or
    # `kill` checkpoints at the next safe boundary instead of dropping in-flight
    # work. Handler only sets _INTERRUPT_REQUESTED (no work in signal context).
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, OSError):
        pass  # non-main thread / restricted platform — checkpointing still works

    if not check_omlx_health():
        print("❌ OMLX is not running.")
        sys.exit(1)

    # D2353/BUG-113: reuse the principles_idx returned by load_stage2_fbs_via_clusters()
    # (which merges STAGE2_CHECKPOINT + STAGE2_SINGLETON_OUTPUT) instead of re-loading
    # via load_stage2_principles() — which reads ONLY the checkpoint and silently drops
    # singleton FBs. Singleton clusters were loaded but their principle_ids never resolved.
    clusters, principles_idx = load_stage2_fbs_via_clusters(only_fb_ids=only_fb_ids)

    if cluster_ids:
        clusters = [c for c in clusters if c["cluster_id"] in cluster_ids]
        if not clusters:
            print(f"❌ No clusters found with IDs: {cluster_ids}")
            sys.exit(1)

    # D2120: Pre-merge lightweight dedup (replaces removed Stage 3 HDBSCAN)
    if len(clusters) > 1:
        cluster_fbs = []
        for c in clusters:
            for pid in c.get("principle_ids", []):
                if pid in principles_idx:
                    cluster_fbs.append(principles_idx[pid])
        if len(cluster_fbs) > 1:
            deduped_fbs = dedup_fbs_by_cosine(cluster_fbs)  # D2231: uses config default S4_DEDUP_COSINE_THRESHOLD
            # Rebuild clusters from deduped list
            valid_ids = {
                p.get("fb_id") or p.get("principle_id", "")
                for p in deduped_fbs
            }
            clusters = [
                c for c in clusters
                if any(pid in valid_ids for pid in c.get("principle_ids", []))
            ]

    # D2370: capture the pre-resume cluster total BEFORE filtering. The D2338
    # fail-closed gate must divide failures by the FULL cluster count, not the
    # remaining-after-resume subset (which would understate the failure ratio).
    total_clusters: int = len(clusters)
    # D2496: authoritative expected FB count (S2-derived) — the number of principle
    # clusters S4 MUST turn into FBs. Computed pre-resume (full corpus) so a resume
    # cannot understate the expectation, and INDEPENDENT of the on-disk record_count
    # so S5 can detect a silent S4-side drop (clusters skipped, not truncated).
    expected_fb_count: int = sum(
        1
        for _c in clusters
        if len([_pid for _pid in _c.get("principle_ids", [])
                if _pid in principles_idx
                and _resolve_content_type(principles_idx[_pid]) == DEFAULT_CONTENT_TYPE]) == 1
    )

    # ── D2370: intra-stage resume (crash recovery for the long serial S4) ──
    # Mirrors S2's D2154 resume block: reload the partial checkpoint + segids and
    # skip already-processed clusters instead of re-running hours of LLM work.
    fbs: list[dict] = []
    processed_ids: set[str] = set()
    _scalar_state: dict = {"classification_errors": 0, "name_collisions": 0}
    _segids_file: str = str(STAGE4_CHECKPOINT) + ".segids"
    _state_file: str = str(STAGE4_CHECKPOINT) + ".state.json"
    _depth_file: str = str(STAGE4_CHECKPOINT) + ".depth.json"
    _cribs_file: str = str(STAGE4_CHECKPOINT) + ".cribs.json"
    # BUG-183: compute provenance BEFORE the resume block so the stale-checkpoint
    # guard can compare it against the checkpoint's own stamped provenance.
    pipeline_commit = get_pipeline_commit()
    pipeline_run_id = get_pipeline_run_id()  # BUG-026 FIX: use singleton directly
    global _S2_INPUT_FINGERPRINT
    _S2_INPUT_FINGERPRINT = _s2_input_fingerprint(pipeline_run_id)
    if STAGE4_CHECKPOINT.exists():
        try:
            fbs.extend(load_jsonl(STAGE4_CHECKPOINT, context="S4 checkpoint"))
            if os.path.exists(_segids_file):
                with open(_segids_file) as _sf:
                    processed_ids = set(json.load(_sf))
            else:
                # D2424: a completed run deletes .segids (below). Reconstruct the
                # already-processed cluster set from checkpoint provenance so a
                # `--cluster <delta>` merge can skip prior work without discarding it.
                processed_ids = {
                    str(sc)
                    for _fb in fbs
                    for sc in (_fb.get("source_clusters") or [])
                    if sc
                }
            if os.path.exists(_state_file):
                with open(_state_file) as _stf:
                    _scalar_state = json.load(_stf)
            # BUG-183: stale-resume guard — discard a checkpoint whose S2 input
            # fingerprint differs from the current S2 corpus (relabeled/regenerated
            # in place). This catches the case D2424's cluster-ID-overlap guard
            # misses (stable IDs across corpus changes). Guard ONLY on full-run
            # resume; a --cluster delta-merge keeps its own provenance handling.
            _saved_fp = _scalar_state.get("s2_input_fingerprint") if isinstance(_scalar_state, dict) else None
            if (not cluster_ids) and _saved_fp and _saved_fp != _S2_INPUT_FINGERPRINT:
                print(f"   ⚠️  S4 resume S2-input mismatch — checkpoint fingerprint {_saved_fp!r} != current {_S2_INPUT_FINGERPRINT!r}")
                print("   ⚠️  Starting fresh — stale S4 progress discarded (BUG-183 guard)")
                processed_ids = set()
                fbs = []
                _scalar_state = {"classification_errors": 0, "name_collisions": 0}
                for _stale_sidecar in (_depth_file, _cribs_file):  # stale pre-pass sidecars are also invalid
                    if os.path.exists(_stale_sidecar):
                        os.unlink(_stale_sidecar)
            # D2487: record-count guard — a checkpoint truncated at a `\n` boundary
            # (whole records dropped, every remaining line valid JSON) is invisible to
            # load_jsonl. Assert on-disk count matches the count recorded at the last
            # checkpoint write, else the truncation is silent.
            _expected_count = _scalar_state.get("record_count") if isinstance(_scalar_state, dict) else None
            if (not cluster_ids) and _expected_count is not None and len(fbs) != _expected_count:
                print(f"   ⚠️  S4 resume record-count mismatch — checkpoint has {len(fbs)} FBs but .state.json recorded {_expected_count} (clean-cut truncation)")
                print("   ⚠️  Starting fresh — prior S4 progress discarded")
                processed_ids = set()
                fbs = []
                _scalar_state = {"classification_errors": 0, "name_collisions": 0}
                for _stale_sidecar in (_depth_file, _cribs_file):
                    if os.path.exists(_stale_sidecar):
                        os.unlink(_stale_sidecar)
            # D2215-style format guard: zero overlap with current targets means the
            # sidecar belongs to a different corpus/probe format — discard, don't
            # silently re-process or silently skip the wrong clusters. D2424: this guard
            # applies ONLY to a full-run resume. An explicit --cluster delta-merge is
            # EXPECTED to have zero/partial overlap with prior processed_ids and must
            # NOT discard the preserved checkpoint FBs.
            target_cids: set[str] = {c.get("cluster_id", "") for c in clusters}
            if (not cluster_ids) and processed_ids and not (processed_ids & target_cids):
                print(f"   ⚠️  S4 resume segids mismatch — {len(processed_ids)} old IDs, 0 overlap with {len(target_cids)} targets")
                print("   ⚠️  Starting fresh — prior S4 progress discarded")
                processed_ids = set()
                fbs = []
                _scalar_state = {"classification_errors": 0, "name_collisions": 0}
                for _stale_sidecar in (_depth_file, _cribs_file):  # stale pre-pass sidecars are also invalid
                    if os.path.exists(_stale_sidecar):
                        os.unlink(_stale_sidecar)
            else:
                _n_remaining = sum(1 for c in clusters if c.get("cluster_id") not in processed_ids)
                print(f"   📋 S4 resuming: {len(fbs)} FBs from {len(processed_ids)} clusters done — {_n_remaining} remaining")
                clusters = [c for c in clusters if c.get("cluster_id") not in processed_ids]
        except Exception as e:
            # D2177 (C16): log + fresh start — never silently discard or silently trust
            import traceback
            print(f"   ⚠️  S4 resume checkpoint corrupted ({type(e).__name__}: {e})")
            print("   ⚠️  Starting fresh — prior S4 progress discarded")
            print(f"   ⚠️  Traceback: {traceback.format_exc()[-300:]}")
            fbs = []
            processed_ids = set()
            _scalar_state = {"classification_errors": 0, "name_collisions": 0}
            for _stale_sidecar in (_depth_file, _cribs_file):  # stale pre-pass sidecars are also invalid
                if os.path.exists(_stale_sidecar):
                    os.unlink(_stale_sidecar)

    print(f"🧩 Stage 4: Classify + Format — {len(clusters)} clusters"
          + (f" (resuming: {len(fbs)} FBs already done)" if processed_ids else ""))
    print(f"   Model: {VERIFY_MODEL} | temp=0.0 | CRIBS classify")
    print(f"{'='*60}")

    process_templates = []   # D2072: process templates (repeatable how-to methods)
    process_instances = []   # D2072: concrete case studies
    growth_edges = []        # D2073: speculative insights (pipeline-extracted)
    tool_instructions = []   # D2072: tool-specific commands
    failed = 0  # D2370: failed clusters are NOT marked processed → retried on resume (re-counted, not restored)
    # D2404: classification failures are now retried on resume (like `failed`) — re-count per run
    classification_errors = 0
    name_collisions = int(_scalar_state.get("name_collisions", 0))
    # D2069: rebuild the name-uniqueness set from the partial FBs (names already
    # normalized + disambiguated, so the set is exactly the taken names).
    existing_names: set[str] = {fb.get("name", "") for fb in fbs}
    pipeline_commit = get_pipeline_commit()
    pipeline_run_id = get_pipeline_run_id()  # BUG-026 FIX: use singleton directly

    # ── D2265: Batch pre-classification ─────────────────────────────────
    # Collect all FB data from clusters, batch classify with GPT-OSS-20B,
    # then use pre-classified results in the main loop. Amortizes reasoning cost.
    _BATCH_ENABLED = bool(_PIPELINE_CFG.get("stage4", {}).get("batch_enabled", False))
    _BATCH_SIZE = int(_PIPELINE_CFG.get("stage4", {}).get("batch_size", BATCH_SIZE_DEFAULT))
    _pre_classified: dict[int | str, dict] = {}  # cluster_id → merged classification
    _batch_used: bool = False

    if _BATCH_ENABLED and not os.environ.get("MAXWELL_SKIP_LLM"):
        # D2481: load the incremental CRIBS checkpoint so a resume skips already-
        # classified clusters instead of re-running the whole pre-pass.
        if os.path.exists(_cribs_file):
            try:
                with open(_cribs_file) as _cf:
                    _loaded_cribs = json.load(_cf)
                if isinstance(_loaded_cribs, dict):
                    _pre_classified.update(_loaded_cribs)
                    print(f"   📋 CRIBS resume: {len(_pre_classified)} clusters already classified")
            except Exception as _e:
                print(f"   ⚠️  CRIBS checkpoint corrupt ({type(_e).__name__}: {_e}) — restarting CRIBS pre-pass")
                _pre_classified = {}

        # Collect all fb_data without making LLM calls
        _pending: list[tuple[int | str, list[dict], dict]] = []  # (cluster_id, cluster_principles, fb_data)
        for cluster in clusters:
            cid = cluster["cluster_id"]
            pids = cluster.get("principle_ids", [])
            cluster_principles = []
            for pid in pids:
                if pid in principles_idx:
                    p = principles_idx[pid]
                    ct = _resolve_content_type(p)
                    if ct == DEFAULT_CONTENT_TYPE:
                        cluster_principles.append(p)
            if len(cluster_principles) != 1:
                continue  # skip non-principle clusters in batch pre-pass
            if cid in _pre_classified:
                continue  # D2481 resume: already classified in a prior run
            fb_data = dict(cluster_principles[0])
            fb_data["_gen_skipped"] = True
            _pending.append((cid, cluster_principles, fb_data))

        if _pending:
            print(f"   ⚡ D2265: Batch pre-classifying {len(_pending)} FBs (batch_size={_BATCH_SIZE})...")
            _batch_start_time = time.time()
            _batch_total = 0
            for _batch_start in range(0, len(_pending), _BATCH_SIZE):
                if _INTERRUPT_REQUESTED:
                    print(f"\n   🛑 Interrupt during CRIBS pre-pass — {_batch_total}/{len(_pending)} classified; resume will continue from here")
                    _write_sidecar_json(_pre_classified, Path(_cribs_file))
                    sys.exit(130)
                _batch = _pending[_batch_start:_batch_start + _BATCH_SIZE]
                _batch_fbs = [fb for _, _, fb in _batch]
                try:
                    _results = batch_cribs_classify(_batch_fbs, model=VERIFY_MODEL)
                    for (cid, _, _), result in zip(_batch, _results):
                        _pre_classified[cid] = result
                    _batch_total += len(_batch)
                    print(f"      Batch {_batch_start // _BATCH_SIZE + 1}: "
                          f"{len(_batch)} FBs classified (total: {_batch_total}/{len(_pending)})")
                except Exception as e:
                    print(f"      ⚠️ Batch {_batch_start // _BATCH_SIZE + 1} FAILED: {e}")
                    # Fall back: let main loop handle these individually
                _write_sidecar_json(_pre_classified, Path(_cribs_file))
            _batch_elapsed = time.time() - _batch_start_time
            _per_fb = _batch_elapsed / max(_batch_total, 1)
            print(f"   ✅ Batch pre-classification: {_batch_total} FBs in {_batch_elapsed:.1f}s "
                  f"({_per_fb:.1f}s/FB amortized — vs ~26s/FB unbatched)")
            _batch_used = True

    # ── D2477: Batched focused depth (D2354) — wire the otherwise-unused batch ──
    # classify_depth_focused() is serialized (~10s/FB — reasoning-model CoT cost on
    # every call). batch_classify_depth() amortizes that (~1-2s/FB) using the SAME
    # short proven prompt, only the transport changes (JSON array response). Gated on
    # S4_DEPTH_BATCH_ENABLED so it is independently A/B-able from batch CRIBS.
    _pre_depth: dict[int | str, str] = {}
    _depth_batch_used: bool = False
    _depth_pending: list[tuple[int | str, dict]] = []  # D2497: defined at top so --depth-only can report it even if the batch gate is off
    _depth_ok: int = 0  # D2497: same — avoids NameError in the --depth-only summary when the gate never ran
    if (S4_DEPTH_BATCH_ENABLED and S4_DEPTH_FOCUSED_CLASSIFICATION
            and not os.environ.get("MAXWELL_SKIP_LLM")):
        # BUG-184: load the incremental depth checkpoint so a resume skips already-
        # classified clusters instead of re-running the whole ~1-2h pre-pass.
        if os.path.exists(_depth_file):
            try:
                with open(_depth_file) as _df:
                    _loaded_depth = json.load(_df)
                if isinstance(_loaded_depth, dict):
                    _pre_depth.update(_loaded_depth)
                    print(f"   📋 Depth resume: {len(_pre_depth)} clusters already classified")
            except Exception as _e:
                print(f"   ⚠️  Depth checkpoint corrupt ({type(_e).__name__}: {_e}) — restarting depth pre-pass")
                _pre_depth = {}

        _depth_pending: list[tuple[int | str, dict]] = []  # (cluster_id, fb_data)
        for cluster in clusters:
            cid = cluster["cluster_id"]
            pids = cluster.get("principle_ids", [])
            _depth_principles = []
            for pid in pids:
                if pid in principles_idx:
                    p = principles_idx[pid]
                    if _resolve_content_type(p) == DEFAULT_CONTENT_TYPE:
                        _depth_principles.append(p)
            if len(_depth_principles) != 1:
                continue  # non-principle clusters have no depth classification
            if cid in _pre_depth:
                continue  # BUG-184 resume: already classified in a prior run
            _depth_pending.append((cid, dict(_depth_principles[0])))

        if _depth_pending:
            print(f"   🧠 D2477: Batch pre-classifying depth for {len(_depth_pending)} FBs "
                  f"(batch_size={S4_DEPTH_BATCH_SIZE})...")
            _depth_start = time.time()
            _depth_ok = 0
            # BUG-184: chunk-iterate + checkpoint incrementally so a mid-pre-pass
            # kill resumes instead of losing the whole pre-pass. batch_depth_classify
            # is itself truncation-resilient (retry + per-chunk serial fallback).
            for _ci in range(0, len(_depth_pending), S4_DEPTH_BATCH_SIZE):
                if _INTERRUPT_REQUESTED:
                    print(f"\n   🛑 Interrupt during depth pre-pass — {_depth_ok}/{len(_depth_pending)} classified; resume will continue from here")
                    _write_depth_checkpoint(_pre_depth, Path(_depth_file))
                    sys.exit(130)
                _chunk = _depth_pending[_ci:_ci + S4_DEPTH_BATCH_SIZE]
                _chunk_fbs = [fb for _, fb in _chunk]
                try:
                    _vals = batch_depth_classify(_chunk_fbs, model=VERIFY_MODEL,
                                                 batch_size=S4_DEPTH_BATCH_SIZE)
                    for (cid, _), dv in zip(_chunk, _vals):
                        _pre_depth[cid] = dv
                        _depth_ok += 1
                except Exception as e:
                    # Transport-level failure on the whole chunk — leave these
                    # clusters unclassified; the main loop classifies them serially.
                    print(f"      ⚠️ Depth chunk [{_ci}-{_ci + len(_chunk)}) FAILED: {e} — main loop will fall back to serial")
                _write_depth_checkpoint(_pre_depth, Path(_depth_file))
            _depth_elapsed = time.time() - _depth_start
            if _depth_ok:
                print(f"   ✅ Batch depth pre-classification: {_depth_ok} FBs in "
                      f"{_depth_elapsed:.1f}s ({_depth_elapsed / _depth_ok:.2f}s/FB amortized)")
            _depth_batch_used = _depth_ok > 0

    # D2497: --depth-only pauses here (before the main serial loop). The depth
    # sidecar is already written incrementally above; the full run resumes from it.
    if depth_only:
        _write_depth_checkpoint(_pre_depth, Path(_depth_file))
        print(f"\n🛑 --depth-only: depth pre-pass complete ({_depth_ok}/{len(_depth_pending)} FBs classified).")
        print(f"   Depth checkpoint: {_depth_file}")
        print(f"   Paused BEFORE main classify loop. Resume with `python3 pipeline/stage4_merge.py`.")
        sys.exit(0)

    for i, cluster in enumerate(clusters, 1):
        # Graceful pause: a SIGINT/SIGTERM sets _INTERRUPT_REQUESTED; the in-flight
        # cluster completes, then we checkpoint here and exit cleanly (0-cluster loss).
        if _INTERRUPT_REQUESTED:
            print(f"\n🛑 Interrupt requested — checkpointing at cluster {i - 1}/{total_clusters}...")
            _write_s4_checkpoint(fbs, processed_ids, {
                "classification_errors": classification_errors,
                "name_collisions": name_collisions,
            })
            _write_depth_checkpoint(_pre_depth, Path(_depth_file))
            print("   ✅ Checkpoint written — resume with the same command to continue.")
            sys.exit(130)
        cluster_id = cluster["cluster_id"]
        principle_ids = cluster["principle_ids"]
        print(f"  [{i}/{len(clusters)}] Cluster {cluster_id} "
              f"({len(principle_ids)} principles)", end=" ")

        # Gather principles for this cluster, split by content_type (D2072)
        cluster_principles = []
        # D2438: report THIS cluster's routing split (per-cluster), not the
        # running totals — the old message showed cumulative PT/PI/TI counts
        # across all prior clusters, misleading readers into thinking one
        # cluster dropped many types when it dropped one.
        _cluster_split: dict[str, int] = {}
        for pid in principle_ids:
            if pid in principles_idx:
                p = principles_idx[pid]
                ct = _resolve_content_type(p)
                if ct == _ROLE_PROCESS_TEMPLATE:
                    process_templates.append(p)
                elif ct == _ROLE_PROCESS_INSTANCE:
                    process_instances.append(p)
                elif ct == _ROLE_GROWTH_EDGE:
                    growth_edges.append(p)
                elif ct == _ROLE_TOOL_INSTRUCTION:
                    tool_instructions.append(p)
                else:
                    cluster_principles.append(p)
                _cluster_split[ct] = _cluster_split.get(ct, 0) + 1

        if not cluster_principles:
            skipped_types = [f"{n} {ct}" for ct, n in _cluster_split.items()]
            print(f"→ ⏭️  Non-principle cluster ({', '.join(skipped_types) if skipped_types else 'empty'})")
            continue

        # Truncate if too many
        if len(cluster_principles) > MAX_PRINCIPLES_PER_CLUSTER:
            cluster_principles = cluster_principles[:MAX_PRINCIPLES_PER_CLUSTER]

        start = time.time()

        # Phase 1: Generate FB — D2120: cluster-before-extract guarantees 1 principle per cluster.
        # All generation happens via CRIBS enrichment on the single principle.
        assert len(cluster_principles) == 1, \
            f"UNREACHABLE: cluster {cluster_id} has {len(cluster_principles)} principles (cluster-before-extract invariant violated)"
        fb_data = dict(cluster_principles[0])  # shallow copy
        fb_data["_gen_skipped"] = True
        print("→ ⚡ GEN skipped (single-FB)", flush=True, end=" ")
        # ── D2137: CRIBS enrichment for single-FB clusters ──────────
        # Stage2 produces name+definition+mechanism+boundary but NOT
        # application, failure_mode, elaboration, jargon, keywords.
        #
        # D2226: MERGED S4 CALL (D2224) — When MAXWELL_MERGED_S4=1, use single
        # Phi-4-mini call for BOTH CRIBS enrichment + classification (~61% faster).
        # Otherwise use two-call pattern: CRIBS (Qwen) + Classify (GPT-OSS).
        _skip_llm: bool = os.environ.get("MAXWELL_SKIP_LLM", "") == "1"
        # D2263/D2301: merged S4 call — env var overrides config (C12).
        # BUG-FIX: config merged_call_enabled was orphaned (never read).
        _use_merged: bool = (
            os.environ.get("MAXWELL_MERGED_S4", "") == "1"
            or bool(_PIPELINE_CFG.get("stage4", {}).get("merged_call_enabled", False))
        )

        if _skip_llm:
            print("(LLM off — CRIBS enrichment skipped)", flush=True, end=" ")
        elif cluster_id in _pre_classified:
            # D2265: Use batch pre-classified result (no LLM call needed).
            # BUG-FIX: previously gated on _use_merged, so batch results were
            # silently ignored and the slow 2-call path ran (~61s/FB).
            merged_result = _pre_classified[cluster_id]
            if isinstance(merged_result, list):
                merged_result = merged_result[0] if merged_result else {}
            if isinstance(merged_result, dict):
                for field in ("application", "failure_mode", "elaboration",
                              "keywords", "jargon"):
                    if merged_result.get(field):
                        fb_data[field] = merged_result[field]
                fb_data["_merged_classification"] = merged_result
                _log_cribs_warnings(fb_data)
                print("⚡batch", flush=True, end=" ")
            else:
                print("⚠️batch-bad", flush=True, end=" ")
        elif _use_merged:
            # D2226: Single-call CRIBS + Classification (D2224) — fallback when no pre-classified
            try:
                merged_result = merged_cribs_classify(fb_data, model=VERIFY_MODEL)
                # BUG-080: guard against list return from call_omlx_json
                if isinstance(merged_result, list):
                    merged_result = merged_result[0] if merged_result else {}
                # Extract CRIBS fields
                for field in ("application", "failure_mode", "elaboration",
                              "keywords", "jargon"):
                    if merged_result.get(field):
                        fb_data[field] = merged_result[field]
                # Stash classification for Phase 2
                fb_data["_merged_classification"] = merged_result
                _log_cribs_warnings(fb_data)
                print("⚡merged", flush=True, end=" ")
            except Exception as e:
                fb_data["enrichment_status"] = "FAILED"
                fb_data["enrichment_error"] = f"merged_call: {e}"[:200]
                print("⚠️merged", flush=True, end=" ")
        else:
            # Original two-call path: CRIBS enrichment (Qwen) + separate classify
            try:
                cribs_prompt = _build_cribs_enrichment_prompt(fb_data)
                cribs_result = call_omlx_json(
                    prompt=cribs_prompt,
                    model=GEN_MODEL,
                    system=CRIBS_ENRICHMENT_SYSTEM,
                    max_tokens=1024,
                )
                # BUG-080: call_omlx_json can return list or str — unwrap/guard
                if isinstance(cribs_result, list):
                    cribs_result = cribs_result[0] if cribs_result else {}
                if isinstance(cribs_result, dict):
                    for field in ("application", "failure_mode", "elaboration",
                                  "keywords", "jargon"):
                        if cribs_result.get(field):
                            fb_data[field] = cribs_result[field]
                    _log_cribs_warnings(fb_data)
                    print("+CRIBS", flush=True, end=" ")
            except Exception as e:
                # D2160: enrichment is best-effort but must be observable (C16)
                fb_data["enrichment_status"] = "FAILED"
                fb_data["enrichment_error"] = str(e)[:200]
                print("⚠️CRIBS", flush=True, end=" ")

        if not isinstance(fb_data, dict):
            print("→ ⚠️  Non-dict response, skipping")
            failed += 1
            continue

        name = fb_data.get("name", "").strip()
        definition = fb_data.get("definition", "").strip()
        if not name or not definition or len(definition) < 20:
            print(f"→ ⚠️  Incomplete FB (name={bool(name)}, def_len={len(definition)})")
            failed += 1
            continue

        # D2371: application is REQUIRED (schemas.FB.application, min_length=10).
        # Fail-closed at the FB level: an empty/short application must quarantine
        # the FB (failed → retried on resume, consistent with D2338 max_failed_ratio: 0.0),
        # never flow silently into SQLite. This is the enforcement the schema declares
        # but the pipeline previously skipped (enrichment exception was swallowed).
        _app = str(fb_data.get("application") or "").strip()
        if len(_app) < 10:
            print(f"→ ❌ Empty/short application ({len(_app)} chars < 10) — FB QUARANTINED (D2371)")
            failed += 1
            continue

        # D2488: failure_mode is REQUIRED for every principle (schemas.FB.failure_mode,
        # min_length=10; CRIBS prompt "REQUIRED FORMAT"). D2371 enforced application but
        # failure_mode had no runtime gate — an empty/short failure_mode flowed silently
        # into S5/S6. Fail-closed parity with D2371: quarantine + retry on resume.
        _fm = str(fb_data.get("failure_mode") or "").strip()
        if len(_fm) < 10:
            print(f"→ ❌ Empty/short failure_mode ({len(_fm)} chars < 10) — FB QUARANTINED (D2488)")
            failed += 1
            continue

        # Phase 2: TWO-STAGE classification (D2138) + semantic depth (D2220)
        # D2226: When merged S4 call produced classification, use it directly.
        # Otherwise fall back to separate classify call (original two-call path).
        # Stage 1: FREE scientific classification — LLM uses full knowledge,
        # unrestricted by canonical lists. Produces ontologically accurate raw labels,
        # is_specialized flag, AND semantic depth via physicist-chef-poet test.
        # Stage 2: CANONICAL MAPPING — pipeline maps raw labels to taxonomy.
        # Stage 3: DEPTH — LLM-classified semantically (D2220), not derived from domain count.
        synonym_index = get_synonym_index()
        merged_classification = fb_data.pop("_merged_classification", None)

        if merged_classification is not None:
            # D2226: Classification already done by merged S4 call — skip second LLM call
            class_data = merged_classification
            print("(classify:merged)", flush=True, end=" ")
        else:
            try:
                mechanism = fb_data.get("mechanism", "")
                boundary = fb_data.get("boundary", "")
                class_prompt = build_classify_prompt(name, definition, mechanism, boundary)
                # D2249/BUG-074: reasoning models (e.g. GPT-OSS) need Reasoning:none
                # prefix (otherwise they burn max_tokens on CoT → empty content)
                _classify_system = CLASSIFY_SYSTEM_PROMPT
                if (VERIFY_REASONING_OFF_PREFIX
                        and VERIFY_MODEL in VERIFY_REASONING_OFF_MODELS):
                    _classify_system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{_classify_system}"
                class_data = call_omlx_json(
                    prompt=class_prompt,
                    model=VERIFY_MODEL,
                    system=_classify_system,
                    max_tokens=VERIFY_MAX_TOKENS,
                )
                # BUG-080: call_omlx_json can return list or str (GPT-OSS
                # occasionally wraps response in array or returns raw text).
                # Guard: unwrap list, reject non-dict types.
                if isinstance(class_data, list):
                    class_data = class_data[0] if class_data else {}
                if not isinstance(class_data, dict):
                    class_data = {}
                # D2357 (ChatGPT re-audit HIGH #9): the legacy direct path must be
                # fail-closed too — a sparse classify response (missing
                # discipline/domains/evidence) must never fabricate emerging/cited.
                # depth is intentionally NOT checked here: it is overridden by the
                # focused depth call below (BUG-075).
                if (not class_data.get("discipline")
                        or not class_data.get("domains")
                        or class_data.get("evidence") not in ("cited", "axiomatic")):
                    raise SparseClassificationError(
                        "direct-classify: sparse semantic fields "
                        "(discipline/domains/evidence)"
                    )
            except SparseClassificationError as e:
                print(f"→ ❌ Classification sparse: {e} — FB QUARANTINED")
                class_data = {
                    "discipline": "unclassified",
                    "domains": ["unclassified"],
                    "is_specialized": False,
                    "classification_status": "FAILED",
                    "classification_error": str(e)[:200],
                    "evidence": None,
                }
                classification_errors += 1
            except Exception as e:
                import traceback
                print(f"→ ❌ Classification FAILED: {e} — FB QUARANTINED")
                print(f"   Traceback: {traceback.format_exc()[-300:]}")
                class_data = {
                    "discipline": "unclassified",
                    "domains": ["unclassified"],
                    "is_specialized": False,
                    "classification_status": "FAILED",
                    "classification_error": str(e)[:200],
                    "evidence": None,
                }
                classification_errors += 1

        # ── Stage 1: Capture raw LLM output (D2138: preserved forever) ──
        domains_raw = list(class_data.get("domains", []))
        discipline_raw_raw = class_data.get("discipline", "")
        if isinstance(discipline_raw_raw, list):
            discipline_raw_raw = discipline_raw_raw[0] if discipline_raw_raw else ""
        discipline_raw = str(discipline_raw_raw) if discipline_raw_raw else ""
        # BUG-186 (D2485): is_specialized is NOT LLM-classified anymore. It is derived
        # deterministically from depth (depth == "specialized") at FB assembly below,
        # so it can never silently default to False for a specialized FB (the old
        # class_data.get("is_specialized", False) was never persisted and always False).

        # Validate evidence (still LLM-classified) — D2405: never fabricate "cited" on FAILED
        if class_data.get("classification_status") != "FAILED":
            if class_data.get("evidence") not in ("cited", "axiomatic"):
                class_data["evidence"] = "cited"

        # ── Stage 2: Map raw → canonical (D2138) ──
        # D2485: distinguish a genuine taxonomy gap (emerging_real) from an
        # empty/invalid raw label that would otherwise FABRICATE the semantic
        # label "emerging" (emerging_unmapped). An unmapped label is NOT a
        # promotion signal — only emerging_real counts toward the post-S4
        # emerging-rate gate (BUG-167 lesson).
        class_data["discipline_raw"] = discipline_raw
        if not discipline_raw or not discipline_raw.strip():
            # Empty/garbage raw discipline → "emerging" is fabricated here, so
            # mark it unmapped. The raw label was never a real scientific term.
            canonical_discipline = "emerging"
            class_data["taxonomy_match_method"] = "emerging_unmapped"
        else:
            canonical_discipline = map_to_canonical_with_fallback(
                discipline_raw, "discipline", synonym_index, CANONICAL_DISCIPLINES
            )
            # D2310: Preserve raw label + record match method (diagnose "emerging" over-firing, BUG-083).
            # The raw label was previously discarded after mapping — losing the signal needed to
            # expand the taxonomy. match_method: "exact" | "synonym" | "emerging_real".
            if canonical_discipline == "emerging":
                class_data["taxonomy_match_method"] = "emerging_real"
            elif canonical_discipline.lower() == discipline_raw.lower():
                class_data["taxonomy_match_method"] = "exact"
            else:
                class_data["taxonomy_match_method"] = "synonym"
        canonical_domains: list[str] = []
        seen_canonical: set[str] = set()
        for d in domains_raw:
            mapped = map_to_canonical_with_fallback(
                d, "domain", synonym_index, CANONICAL_DOMAINS
            )
            if mapped not in seen_canonical:
                seen_canonical.add(mapped)
                canonical_domains.append(mapped)
        if not canonical_domains:
            canonical_domains = ["emerging"]

        # ── Stage 3: USE LLM-CLASSIFIED DEPTH (D2220: semantic, not structural) ──
        # D2220: Depth is now classified by the LLM using the physicist-chef-poet
        # test (see CLASSIFY_SYSTEM_PROMPT). This replaces the structural derivation
        # from domain count, which had a ~55% error rate (over-assigned "universal").
        # The LLM judges ontological scope — whether the mechanism applies across all
        # reality (universal), bridges two disciplines (cross-domain), operates within
        # one field (domain), or is a narrow sub-technique (specialized).
        raw_depth = class_data.get("depth", "")
        VALID_DEPTHS = {"universal", "cross-domain", "domain", "specialized"}
        # ── BUG-075: Focused depth call (D2247) ──
        # The LONG combined classify prompt degrades depth accuracy for ALL models
        # (GPT-OSS: 62.5% short → 38% long; cross-domain 0/3 everywhere).
        # When enabled (default), run a SEPARATE short focused depth prompt and
        # OVERRIDE the depth from the long classify call. Cost: +1 fast call/FB.
        if S4_DEPTH_FOCUSED_CLASSIFICATION and not _skip_llm:
            # D2351/BUG-108: FAIL-CLOSED depth. classify_depth_focused() now RAISES
            # on transport failure, empty content, or an ambiguous answer instead of
            # silently returning "domain". An inference failure must never become a
            # valid-looking semantic label (C16). Count it → max_failed_ratio gate.
            try:
                # D2477: use the batched depth result when the pre-pass produced one
                # (quality-neutral — same short prompt, only transport batched).
                if cluster_id in _pre_depth:
                    depth_val = _pre_depth[cluster_id]
                    print(f"(depth:{depth_val})", flush=True, end=" ")
                else:
                    # D2354 FrugalGPT cascade: GPT-OSS does CRIBS/classification;
                    # depth may route to a cheap third-family model (Gemma) when
                    # enabled. Default (flag off) = GPT-OSS (VERIFY_MODEL).
                    depth_model = S4_DEPTH_MODEL if S4_DEPTH_FRUGAL_ENABLED else VERIFY_MODEL
                    depth_val = classify_depth_focused(
                        fb_data,
                        model=depth_model,
                        max_tokens=S4_DEPTH_MAX_TOKENS,
                    )
                    print(f"(depth:{depth_val})", flush=True, end=" ")
            except Exception as e:
                depth_val = S4_DEPTH_FALLBACK_DEPTH
                class_data["classification_status"] = "FAILED"
                class_data["classification_error"] = f"depth_focused: {e}"[:200]
                classification_errors += 1
                print(f"(depth:FAILED {type(e).__name__})", flush=True, end=" ")
        elif raw_depth in VALID_DEPTHS:
            # D2365/X10 coupling note: this fallback reads `raw_depth` from the merged/batch/
            # direct classify prompt (which STILL requests `depth`). If `depth` is ever removed
            # from those prompts (the X10 waste-elimination), this branch silently becomes dead
            # and depth falls through to S4_DEPTH_FALLBACK_DEPTH below. That is the *only* safe
            # behaviour for a disabled focused call — but it must be intentional, not accidental.
            # Keep this branch + remove the prompt field TOGETHER, or leave both.
            depth_val = raw_depth
        else:
            # Fallback: conservative default. If LLM hallucinates depth, assume domain.
            # D2493: mark the fallback so a hallucinated/invalid depth is NEVER
            # indistinguishable from a confident "domain" classification (C16).
            # (The depth-call-FAILURE path above sets status=FAILED; this path covers
            # an invalid raw_depth that never raised.)
            depth_val = S4_DEPTH_FALLBACK_DEPTH
            class_data["classification_status"] = "FALLBACK"
            class_data["classification_error"] = f"depth: invalid raw_depth {raw_depth!r}"[:200]

        # ── Assemble class_data with CANONICAL labels + semantic depth ──
        class_data["discipline"] = canonical_discipline
        class_data["domains"] = canonical_domains
        class_data["depth"] = depth_val

        # Validate canonical labels (safety net — mapper should only return valid labels)
        is_valid, errors = validate_classification(class_data)
        if not is_valid:
            classification_errors += 1
            if not class_data.get("discipline") or not is_valid_discipline(class_data["discipline"]):
                class_data["discipline"] = "emerging"
            fixed_domains = []
            for d in class_data.get("domains", []):
                if is_valid_domain(d):
                    fixed_domains.append(d)
            if not fixed_domains:
                fixed_domains = ["emerging"]
            class_data["domains"] = fixed_domains

        # Collect source books
        source_books = set()
        source_ids = set()  # D2376: canonical source identity (D2176) — was dropped at S4
        for p in cluster_principles:
            for sb in p.get("source_books", []):
                source_books.add(sb)
            for sid in p.get("source_ids", []) or []:
                source_ids.add(sid)
        # D2376: fall back to the S1.5 cluster's canonical hashes, then derive from
        # filenames. Prefer the canonical hash set — it is edition/filename invariant.
        if not source_ids:
            for sid in cluster.get("source_ids", []) or []:
                source_ids.add(sid)
        if not source_ids and source_books:
            from pipeline.book_metadata import resolve_source_ids
            source_ids = resolve_source_ids(list(source_books))

        # D2069: Name normalization + uniqueness
        name = normalize_fb_name(name, max_words=FB_NAME_MAX_WORDS)
        if not check_name_unique(name, existing_names):
            name_collisions += 1
            # D2350: short numeric suffix (was "(Cluster <64-char-hash>)" which
            # polluted human-readable names). Probe until unique.
            base = name
            suffix = 2
            while not check_name_unique(f"{base} ({suffix})", existing_names):
                suffix += 1
            name = f"{base} ({suffix})"
            print(f"      ⚠️  Name collision, disambiguated: '{name}'")
        existing_names.add(name)

        # ── Auto-derive agentic metadata (D2130) ──────────────────────────
        n_domains = len(class_data.get("domains", []))

        # difficulty_level: derived from depth via config map (D2410/C12).
        depth_val = class_data.get("depth", "domain")
        difficulty_level = _derive_difficulty_level(depth_val, n_domains)

        # temporal_scope: heuristic from keywords + definition signals (D2364/C12:
        # config-driven). D2410: boundary-aware matching (no stopword-like "all"
        # or substring "now" false-hits) + contemporary-first ordering (a decay
        # signal is stronger than a timeless signal — "always now" → contemporary).
        def_text = (definition + " " + fb_data.get("elaboration", "")).lower()
        if _temporal_signal_hit(def_text, S4_TEMPORAL_SIGNALS.get("contemporary", [])):
            temporal_scope = "contemporary"
        elif _temporal_signal_hit(def_text, S4_TEMPORAL_SIGNALS.get("timeless", [])):
            temporal_scope = "timeless"
        else:
            temporal_scope = "timeless"  # default: principles are timeless unless evidence suggests otherwise

        # ── Auto-derive v1 Anytype properties (context, accessibility, intimacy_boundary) ─
        # context: derive via the shared lattice helper (D2375) so S4/S6b/S6c never
        # drift. D2373: unmatched domains → "general" (neutral), never "personal".
        context_val = derive_context({"domains": class_data.get("domains", [])})

        # accessibility: derived from prerequisite_fbs and difficulty
        # D2132: expert→prerequisite is a default, not a law.
        # The golden set shows many expert FBs (L06, F02, K02, C02) are self-evident
        # when the core claim is intuitive even if application details require expertise.
        # Override: no prereqs AND definition < 200 chars → self-evident regardless of difficulty.
        prereqs = fb_data.get("prerequisite_fbs", [])
        if prereqs and isinstance(prereqs, list) and len(prereqs) > 0:
            accessibility_val = "prerequisite"
        elif difficulty_level == "expert" and len(definition) > 200:
            accessibility_val = "prerequisite"
        else:
            accessibility_val = "self-evident"

        # intimacy_boundary: restore the v1 lattice (D369/D383) instead of a
        # hardcoded "public". Resolves private/selective/public from three
        # 2.0-native signals: field routing (source) + topic sensitivity +
        # context (personal-only → private, mixed → selective).
        # D2372: pass RAW labels too — the intimacy lattice must consult the
        # accurate raw discipline/domains, not only the canonical mapping. When
        # discipline collapses to "emerging" (taxonomy gap, BUG-083), the topic-
        # sensitivity signal would otherwise be lost and sensitive FBs degrade
        # to "public".
        intimacy_val, _intimacy_rule = resolve_intimacy({
            "context": context_val,
            "discipline": canonical_discipline,
            "domains": canonical_domains,
            "discipline_raw": discipline_raw,
            "domains_raw": domains_raw,
        })

        # provenance: pipeline FBs are always llm_extracted_from_source (C29)
        provenance_val = "llm_extracted_from_source"

        # Build FB record (bloat removed per D2130: no s3_original_domain, no classification_method)
        # D2350 (ChatGPT re-audit): fb_id MUST come from S2 (identity fixed at
        # extraction time). A missing fb_id is a malformed/legacy record — never
        # re-hash from the normalized name (it would drift from S2's hash and
        # break the D2350 identity invariant). Fail loudly instead.
        fb_id_val = fb_data.get("fb_id")
        if not fb_id_val:
            print(f"→ ❌ FB missing fb_id (name={name!r}) — QUARANTINED (D2350 invariant)")
            failed += 1
            continue

        fb = {
            # D2350: preserve S2's fb_id (identity is fixed at extraction time).
            # Previously re-hashed here AFTER name title-casing, so 67 records
            # drifted to a new fb_id between S2→S4, breaking source_clusters
            # provenance and FB identity across stages.
            "fb_id": fb_id_val,
            "name": name,
            "definition": definition,
            "mechanism": fb_data.get("mechanism", "").strip(),
            "boundary": fb_data.get("boundary", "").strip(),
            "consequence": fb_data.get("consequence", "").strip(),
            # D2337: persist D2323 two-axis ontology (was dropped at S4→S6)
            "content_type": (fb_data.get("content_type") or DEFAULT_CONTENT_TYPE).strip(),
            "extraction_type": (fb_data.get("extraction_type") or "").strip(),
            "application": fb_data.get("application", "").strip(),
            "failure_mode": fb_data.get("failure_mode", "").strip(),
            "elaboration": fb_data.get("elaboration", "").strip(),
            "keywords": fb_data.get("keywords", "").strip(),
            "domains": class_data["domains"],
            "discipline": class_data.get("discipline", "emerging"),
            "domains_raw": domains_raw,
            "discipline_raw": discipline_raw if discipline_raw else None,
            "depth": depth_val,
            # BUG-186 (D2485): is_specialized derived deterministically from depth,
            # NOT LLM-classified. Anytype consumer (stage6b) reads this — it must
            # never be a silently-false dead field.
            "is_specialized": depth_val == "specialized",
            "evidence": class_data.get("evidence", "cited"),
            # ── v1 Anytype properties ──
            "context": context_val,
            "accessibility": accessibility_val,
            "intimacy_boundary": intimacy_val,
            "provenance": provenance_val,
            # D2439: structural evidence tier — carried from the S4 cluster wrapper
            # (convergent/single_source/singleton) so it survives into the DB and
            # retrieval can tier "2+ sources agree" vs "1 source asserts". Without
            # this the keep-list strategy's convergent/single-source distinction is
            # silently forfeited at S4→S6.
            "is_convergent": bool(cluster.get("is_convergent", False)),
            "origin": cluster.get("origin", "single_source"),
            # ── Agentic metadata ──
            "difficulty_level": difficulty_level,
            "temporal_scope": temporal_scope,
            "prerequisite_fbs": fb_data.get("prerequisite_fbs", []),
            "procedural_skill": fb_data.get("procedural_skill"),
            # ── Provenance (simplified) ──
            "source_clusters": [cluster_id],
            "source_books": sorted(source_books),
            "source_ids": sorted(source_ids),  # D2376: canonical hashes (D2176) — restore provenance
            # F1: S2 provenance carry-through — citation/source_authors/
            # source_diversity/primary_source were emitted by S2 but dropped at S4,
            # losing bibliographic + epistemic-diversity provenance from the DB.
            "citation": fb_data.get("citation"),
            "source_authors": fb_data.get("source_authors"),
            "source_diversity": fb_data.get("source_diversity"),
            "primary_source": fb_data.get("primary_source"),
            # D2350 (ChatGPT re-audit): S2 v3 records emit `fb_id`, NOT `principle_id`.
            # Reading only `principle_id` left source_principle_ids empty for every
            # normal v3 FB. Use fb_id first, retain principle_id as legacy fallback.
            "source_principle_ids": [
                (p.get("fb_id") or p.get("principle_id", ""))
                for p in cluster_principles
                if (p.get("fb_id") or p.get("principle_id"))
            ],
            # D2352/BUG-110: carry segment-level provenance (declared in metadata.provenance, was dropped at S4)
            "source_segments": list(fb_data.get("source_segments", []) or []),
            "evidence_passages": cluster_principles[0].get("evidence_passages", []) if cluster_principles else [],
            "evidence_passages_shown": cluster_principles[0].get("evidence_passages_shown", []) if cluster_principles else [],
            "source_text": _collect_source_text(cluster_principles),
            # D2352/BUG-112: persist the summary/principle gate (S2 emits it, S4 dropped it)
            "is_summary": bool(fb_data.get("is_summary", False)),
            "classification_errors": errors if errors else None,
            # ── Utilization tracking (initialized at zero) ──
            "usage_count": 0,
            "feedback_score": None,
            "feedback_count": 0,
            "fb_version": 1,
            # D2351: reflect depth/classification failure instead of always CLEAN
            "classification_status": class_data.get("classification_status", "CLEAN"),
            # D2351: preserve the failure reason when present (C16 observability)
            "classification_error": class_data.get("classification_error"),
            # D2337: surface taxonomy match method (D2310 diagnostic, was computed then discarded)
            "taxonomy_match_method": class_data.get("taxonomy_match_method"),
        }
        # D2496/BUG-187: always emit jargon — omit-when-empty was the schema-drift
        # source (key absent vs key present-empty). None when no specialized terms.
        fb["jargon"] = _serialize_jargon(fb_data.get("jargon"))
        fb = stamp_record(fb, gen_model=GEN_MODEL, classify_model=VERIFY_MODEL)  # D2476
        fb["pipeline_run_id"] = pipeline_run_id
        fb["pipeline_commit"] = pipeline_commit
        if class_data.get("classification_status") == "FAILED":
            # D2404: failed classification must be retried on resume — do not checkpoint as done.
            print(f"→ ❌ '{name}' classification FAILED — will retry on resume")
        else:
            fbs.append(fb)
            processed_ids.add(cluster_id)
            elapsed = time.time() - start
            err_str = f" ({len(errors)} label errors)" if errors else ""
            print(f"→ ✅ '{name}'{err_str} ({elapsed:.1f}s)")

        # D2370: incremental checkpoint every N clusters (mirrors S2 D2154)
        if S4_CHECKPOINT_INTERVAL > 0 and len(processed_ids) % S4_CHECKPOINT_INTERVAL == 0:
            _write_s4_checkpoint(fbs, processed_ids, {
                "classification_errors": classification_errors,
                "name_collisions": name_collisions,
            })

    # ── P1.4: Compute FB relationship edges (LightRAG foundation) ────
    if len(fbs) > 1:
        compute_fb_relationships(fbs)

    # Write FB checkpoint — BUG-188: stream + verify count (no multi-GB join string)
    safe_write_jsonl(STAGE4_CHECKPOINT, fbs)

    # D2496: persist the authoritative expected count so S5's preflight can assert
    # on-disk == S2-derived expectation (catches a silent S4-side record DROP).
    # Written AFTER the checkpoint and NOT deleted below (survives completion).
    _expected_count_path = str(STAGE4_CHECKPOINT) + ".expected_count.json"
    safe_write(_expected_count_path, json.dumps({
        "expected_fb_count": expected_fb_count,
        "s2_input_fingerprint": _S2_INPUT_FINGERPRINT,
        "pipeline_run_id": pipeline_run_id,
        "written_at": time.time(),
    }, indent=2))

    # D2370: clear resume sidecars — a completed run must not read as a partial resume
    for _sidecar in (str(STAGE4_CHECKPOINT) + ".segids", str(STAGE4_CHECKPOINT) + ".state.json",
                     str(STAGE4_CHECKPOINT) + ".depth.json", str(STAGE4_CHECKPOINT) + ".cribs.json"):
        if os.path.exists(_sidecar):
            os.unlink(_sidecar)

    # ── D2073: Save growth edges separately ───────────────────────────
    ge_path = STAGE4_CHECKPOINT.parent / S4_GE_OUTPUT
    if growth_edges:
        seen_ge: set[str] = set()
        deduped_ge = []
        for ge in growth_edges:
            _k = ge.get("fb_id") or ge.get("principle_id", "")  # D2320: v3.0 fb_id / v2.x principle_id
            if _k and _k not in seen_ge:
                seen_ge.add(_k)
                deduped_ge.append(_stamp_sidecar(ge, pipeline_run_id, pipeline_commit))
        safe_write_jsonl(ge_path, deduped_ge)  # D2487: stream, no single-join string

    # ── D2072: Save process templates separately ──────────────────────
    pt_path = STAGE4_CHECKPOINT.parent / S4_PT_OUTPUT
    if process_templates:
        seen_pt: set[str] = set()
        deduped_pt = []
        for pt in process_templates:
            _k = pt.get("fb_id") or pt.get("principle_id", "")  # D2320: v3.0 fb_id / v2.x principle_id
            if _k and _k not in seen_pt:
                seen_pt.add(_k)
                deduped_pt.append(_stamp_sidecar(pt, pipeline_run_id, pipeline_commit))
        safe_write_jsonl(pt_path, deduped_pt)  # D2487: stream, no single-join string

    # ── D2072: Save process instances separately ──────────────────────
    pi_path = STAGE4_CHECKPOINT.parent / S4_PI_OUTPUT
    if process_instances:
        seen_pi: set[str] = set()
        deduped_pi = []
        for pi in process_instances:
            _k = pi.get("fb_id") or pi.get("principle_id", "")  # D2320: v3.0 fb_id / v2.x principle_id
            if _k and _k not in seen_pi:
                seen_pi.add(_k)
                deduped_pi.append(_stamp_sidecar(pi, pipeline_run_id, pipeline_commit))
        safe_write_jsonl(pi_path, deduped_pi)  # D2487: stream, no single-join string

    # ── D2072: Save tool instructions separately ──────────────────────
    ti_path = STAGE4_CHECKPOINT.parent / S4_TI_OUTPUT
    if tool_instructions:
        seen_ti: set[str] = set()
        deduped_ti = []
        for ti in tool_instructions:
            _k = ti.get("fb_id") or ti.get("principle_id", "")  # D2320: v3.0 fb_id / v2.x principle_id
            if _k and _k not in seen_ti:
                seen_ti.add(_k)
                deduped_ti.append(_stamp_sidecar(ti, pipeline_run_id, pipeline_commit))
        safe_write_jsonl(ti_path, deduped_ti)  # D2487: stream, no single-join string

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ FBs generated:            {len(fbs)}")
    print(f"🔧 Process templates:        {len(process_templates)} (→ {S4_PT_OUTPUT})")
    print(f"📖 Process instances:        {len(process_instances)} (→ {S4_PI_OUTPUT})")
    print(f"🌱 Growth edges:             {len(growth_edges)} (→ {S4_GE_OUTPUT})")
    print(f"🛠️  Tool instructions:        {len(tool_instructions)} (→ {S4_TI_OUTPUT})")
    print(f"❌ Failed clusters:          {failed}")
    if _batch_used:
        print(f"⚡ Batch classified:          {len(_pre_classified)} FBs (D2265)")
    if _pre_depth:
        print(f"🧠 Depth pre-classified:      {len(_pre_depth)} FBs (D2477)")
    print(f"🏷️  Classification errors:     {classification_errors}")
    if name_collisions:
        print(f"🔤 Name collisions:          {name_collisions} (auto-disambiguated)")
    if fbs:
        depths = {}
        for fb in fbs:
            d = fb["depth"]
            depths[d] = depths.get(d, 0) + 1
        print(f"📊 Depths:                   {depths}")
        print(f"📊 Avg domains/FB:           {sum(len(fb['domains']) for fb in fbs) / len(fbs):.1f}")
    print(f"📋 FB Checkpoint:            {STAGE4_CHECKPOINT}")
    if process_templates:
        print(f"📋 PT Checkpoint:            {pt_path}")
    if process_instances:
        print(f"📋 PI Checkpoint:            {pi_path}")
    if growth_edges:
        print(f"📋 GE Checkpoint:            {ge_path}")
    if tool_instructions:
        print(f"📋 TI Checkpoint:            {ti_path}")

    # ── D2338: fail-closed merge ─────────────────────────────────────────────
    # S4 previously printed `failed`/`classification_errors` but exited 0, so a
    # partial merge fed a reduced dataset to S5 ("missing knowledge looks like
    # valid absence"). Now a partial merge never looks like success.
    # D2370: total_clusters was captured BEFORE the resume filter (see above) —
    # the gate must divide failures by the full cluster count, not the
    # remaining-after-resume subset.
    if total_clusters > 0:
        combined_failures: int = failed + classification_errors
        failure_ratio: float = combined_failures / total_clusters
        if failure_ratio > S4_MAX_FAILED_RATIO:
            print(f"❌ Stage 4 FAILED: {failed} failed clusters + {classification_errors} classification "
                  f"errors = {combined_failures}/{total_clusters} "
                  f"({failure_ratio:.1%} > max_failed_ratio={S4_MAX_FAILED_RATIO}). "
                  f"Missing FBs = permanent data loss — do NOT advance to S5.")
            sys.exit(1)
        if combined_failures > 0:
            print(f"⚠️  Stage 4 CONDITIONAL_SUCCESS: {combined_failures} failure(s) within "
                  f"tolerance ({failure_ratio:.1%} ≤ {S4_MAX_FAILED_RATIO}). Re-run to retry failed clusters.")
            sys.exit(2)  # non-zero → runner does NOT auto-advance to S5


def main():
    parser = argparse.ArgumentParser(description="Stage 4: Merge Clusters → FBs + Multi-label Classification")
    parser.add_argument("--cluster", help="Comma-separated cluster IDs to process (int or string)")
    parser.add_argument("--only-fb-ids", help="Path to a JSONL allow-list of fb_ids (e.g. value_keep_ids.jsonl); fail-closed")
    parser.add_argument("--depth-only", action="store_true",
                        help="D2497: run only the batched depth pre-pass, checkpoint, then pause before the main loop")
    args = parser.parse_args()

    cluster_ids = None
    if args.cluster:
        raw_ids = [c.strip() for c in args.cluster.split(",")]
        # D2120: Cluster IDs can be hash strings (from Stage 2 FBs) or ints (legacy)
        try:
            cluster_ids = [int(c) for c in raw_ids]
        except ValueError:
            cluster_ids = raw_ids

    only_fb_ids = _load_fb_id_allowlist(args.only_fb_ids) if args.only_fb_ids else None
    run_stage4(cluster_ids=cluster_ids, only_fb_ids=only_fb_ids, depth_only=args.depth_only)


if __name__ == "__main__":
    main()
