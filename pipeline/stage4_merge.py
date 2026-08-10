#!/usr/bin/env python3
"""
stage4_merge.py — Merge clusters → Foundation Blocks + multi-label classification.
===================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 4), D1058, D150, D316

Input:  Clusters from Stage 2 + Principles from Stage 2
Output: Foundation Blocks with classified labels, checkpoint at stage4_merge.jsonl

Process:
  1. For each cluster, gather all member principles
  2. Send to Qwen3.6: merge principles → single FB (name + 6 body fields)
  3. Classification: single-pass prompt lists all valid labels inline (D316: discipline singular, domains multi-label)
  4. Pydantic Literal validation catches hallucinated labels at write boundary
  5. Auto-derive context, accessibility, intimacy_boundary, provenance (v1 parity)
  6. Write checkpoint

Generator: Qwen3.6-35B-A3B-4bit (OMLX)
Classifier: Phi-4-mini-instruct-8bit (OMLX) — R5: different family from generator (D2068: fixed on oMLX 0.5.3)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage4_merge.py
    python3 pipeline/stage4_merge.py --cluster 0,1,2   # Process specific clusters
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    GEN_MODEL,
    MAX_DOMAINS_PER_FB,
    S4_DEDUP_COSINE_THRESHOLD,   # D2231: C12 compliance
    S4_GE_OUTPUT,
    S4_MAX_PRINCIPLES,
    S4_PI_OUTPUT,
    S4_PT_OUTPUT,
    S4_SEMANTIC_NEAR_THRESHOLD,  # D2231: C12 compliance
    S4_TI_OUTPUT,
    STAGE2_CHECKPOINT,
    STAGE4_CHECKPOINT,
    VERIFY_MODEL,  # P0.10: imported for R5-compliant SALSA classification
)
from pipeline.schemas import (
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    get_synonym_index,
    is_valid_discipline,
    is_valid_domain,
)
from pipeline.stamp import get_pipeline_commit, get_pipeline_run_id, make_hash_id, stamp_record

# D2226: Merged S4 CRIBS+Classification single-call (D2224)
from pipeline.stage4_merged_call import merged_cribs_classify

# ── Constants ──────────────────────────────────────────────────────────────
MAX_PRINCIPLES_PER_CLUSTER = S4_MAX_PRINCIPLES  # D2080: from config, was hardcoded 20

# ── Prompt templates ───────────────────────────────────────────────────────

# ── CRIBS enrichment (D2137: fills missing fields for single-FB clusters) ──

CRIBS_ENRICHMENT_SYSTEM = """You enrich Foundation Blocks with CRIBS-quality fields. You receive an FB with
name + definition already written. Your job is to ADD the missing fields.

CRITICAL RULES:
- application: Generate ONLY if this principle is prescriptive (actionable technique/method). If descriptive/theoretical, set to null. Format when present: "When [concrete situation] → do [specific action]."
- failure_mode: "The principle fails when [specific condition]." How it breaks — be specific.
- elaboration: 3-5 sentences. Edge cases, non-obvious implications, second-order effects.
- keywords: 3-5 search terms, comma-separated. These are RETRIEVAL labels, not explanations.
- jargon: OMIT this key entirely if no specialized terms exist. Only include when
  a non-expert would not understand specific terms used in the FB.
  ⚠️ NEVER copy keywords into jargon. Jargon is for pedagogy, keywords for search.

Return ONLY a JSON object:
{"application": "...", "failure_mode": "...", "elaboration": "...", "keywords": "...", "jargon": {...} or omit}"""


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

Return ONLY a JSON object: {"discipline": "discipline_name", "domains": ["d1", "d2"], "depth": "universal|cross-domain|domain|specialized", "is_specialized": true/false, "evidence": "..."}"""


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


def load_stage2_fbs_via_clusters() -> tuple[list[dict], dict[str, dict]]:
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

    with open(STAGE2_CHECKPOINT) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            fb = json.loads(line)

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
                "cluster_id": fb_id_val or f"fb_{i}",
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
        with open(STAGE2_SINGLETON_OUTPUT) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                fb = json.loads(line)
                fb_id_val = fb.get("fb_id") or fb.get("principle_id", "")
                if fb_id_val:
                    principles_idx[fb_id_val] = fb

                # Singleton FBs are always: not convergent, not noise, is singleton
                clusters.append({
                    "cluster_id": fb_id_val or f"singleton_{singleton_count}",
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

    # Convert to numpy, normalize
    import numpy as np
    embeddings = np.array([np.array(e, dtype=np.float32) for e in raw_embs if len(e) > 0])
    if len(embeddings) < 2:
        return fbs

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms

    # Compute pairwise cosine similarity (upper triangle only)
    similarity = embeddings @ embeddings.T
    n = len(fbs)
    removed: set[int] = set()
    dupes_found = 0

    for i in range(n):
        if i in removed:
            continue
        for j in range(i + 1, n):
            if j in removed:
                continue
            if similarity[i, j] >= threshold:
                # Keep FB with more source diversity
                books_i = len(fb_source_books(fbs[i]))
                books_j = len(fb_source_books(fbs[j]))
                if books_i >= books_j:
                    removed.add(j)
                else:
                    removed.add(i)
                    break  # i removed, stop checking j against i
                dupes_found += 1

    if dupes_found > 0:
        kept = [fbs[i] for i in range(n) if i not in removed]
        print(f"   🔍 Dedup: {dupes_found} near-duplicate FBs removed "
              f"(cos ≥ {threshold}), {len(kept)} kept")
        return kept

    return fbs


def load_stage2_clusters() -> list[dict]:
    """D2198: Renamed from load_stage3_clusters (Stage 3 removed per D2120).

    Always loads from Stage 2 FBs — Stage 1.5 clustering + Stage 2 convergent
    extraction replaced the old HDBSCAN pipeline. The old function name was
    misleading (it never loaded Stage 3 data, always loaded Stage 2).
    """
    clusters, _ = load_stage2_fbs_via_clusters()
    return clusters


def load_stage2_principles() -> dict[str, dict]:
    """Load principles from Stage 2, indexed by principle_id and fb_id (v2/v3 compat)."""
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found.")
        sys.exit(1)

    principles: dict[str, dict] = {}
    with open(STAGE2_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                p = json.loads(line)
                pid = p.get("principle_id", "")
                fid = p.get("fb_id", "")
                if pid:
                    principles[pid] = p
                if fid and fid != pid:
                    principles[fid] = p
    return principles


def validate_classification(result: dict) -> tuple[bool, list[str]]:
    """Validate multi-label classification output against canonical taxonomy.

    D2066: disciplines is now a list (1-3). D2024 SALSA single-discipline superseded.
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


def normalize_fb_name(name: str, max_words: int = 5) -> str:
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

def compute_fb_relationships(
    fbs: list[dict],
    similarity_threshold: float = S4_SEMANTIC_NEAR_THRESHOLD,  # D2231: from config (was hardcoded 0.80)
) -> list[dict]:
    """Compute FB-to-FB relationships for LightRAG graph foundation.

    D2118, D2120: Relationship edges enable graph-based knowledge retrieval.
    Four relationship types:
      - domain_overlap: FBs sharing ≥1 domain label
      - discipline_overlap: FBs sharing ≥1 discipline (D2066 multi-label)
      - source_crossover: FBs derived from ≥1 shared source book
      - semantic_near: Cosine similarity ≥ threshold on definition embeddings

    Writes `related_fbs` list onto each FB dict (mutates in place).

    Args:
        fbs: List of FB dicts (with domains, disciplines, source_books, definition).
        similarity_threshold: Cosine similarity threshold for semantic_near edges.

    Returns:
        The same fbs list, mutated with `related_fbs` fields.
    """
    if len(fbs) < 2:
        for fb in fbs:
            fb.setdefault("related_fbs", [])
        return fbs

    n: int = len(fbs)
    print(f"\n🔗 Computing FB relationships for {n} FBs...")

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

    # Pre-extract sets for fast comparison
    fb_id_list: list[str] = [fb["fb_id"] for fb in fbs]
    domain_sets: list[set[str]] = [set(fb.get("domains", [])) for fb in fbs]
    # D316: discipline is singular — wrap in set for comparison
    discipline_sets: list[set[str]] = [{fb.get("discipline", "")} if fb.get("discipline") else set() for fb in fbs]
    book_sets: list[set[str]] = [set(fb.get("source_books", [])) for fb in fbs]

    # Initialize related_fbs on all FBs
    for fb in fbs:
        fb["related_fbs"] = []

    edge_counts: dict[str, int] = {"domain_overlap": 0, "discipline_overlap": 0,
                                      "source_crossover": 0, "semantic_near": 0}

    # Pairwise comparison (upper triangle)
    for i in range(n):
        for j in range(i + 1, n):
            relationships: list[str] = []

            # Domain overlap
            if domain_sets[i] & domain_sets[j]:
                relationships.append("domain_overlap")

            # Discipline overlap (D2066 multi-label)
            if discipline_sets[i] & discipline_sets[j]:
                relationships.append("discipline_overlap")

            # Source crossover
            if book_sets[i] & book_sets[j]:
                relationships.append("source_crossover")

            # Semantic similarity
            if has_embeddings and embeddings is not None:
                sim: float = float(np.dot(embeddings[i], embeddings[j]))
                if sim >= similarity_threshold:
                    relationships.append("semantic_near")

            if relationships:
                # Bidirectional edges
                fbs[i]["related_fbs"].append({
                    "fb_id": fb_id_list[j],
                    "relationships": relationships,
                })
                fbs[j]["related_fbs"].append({
                    "fb_id": fb_id_list[i],
                    "relationships": relationships,
                })
                for rel in relationships:
                    edge_counts[rel] = edge_counts.get(rel, 0) + 1

    # Summary
    print(f"   Domain overlap:       {edge_counts['domain_overlap']} edges")
    print(f"   Discipline overlap:   {edge_counts['discipline_overlap']} edges")
    print(f"   Source crossover:     {edge_counts['source_crossover']} edges")
    if has_embeddings:
        print(f"   Semantic near (cos≥{similarity_threshold:.2f}): {edge_counts['semantic_near']} edges")

    total_edges: int = sum(edge_counts.values())
    isolated: int = sum(1 for fb in fbs if not fb["related_fbs"])
    print(f"   Total edges: {total_edges} | Isolated FBs: {isolated}/{n}")

    return fbs


def run_stage4(cluster_ids: list[int | str] | None = None):
    """Run Stage 4: Merge clusters into Foundation Blocks."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    if not check_omlx_health():
        print("❌ OMLX is not running.")
        sys.exit(1)

    clusters = load_stage2_clusters()
    principles_idx = load_stage2_principles()

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

    print(f"🧩 Stage 4: Classify + Format — {len(clusters)} clusters")
    print(f"   Model: {VERIFY_MODEL} | temp=0.0 | SALSA classify")
    print(f"{'='*60}")

    fbs = []
    process_templates = []   # D2072: process templates (repeatable how-to methods)
    process_instances = []   # D2072: concrete case studies
    growth_edges = []        # D2073: speculative insights (pipeline-extracted)
    tool_instructions = []   # D2072: tool-specific commands
    failed = 0
    classification_errors = 0
    name_collisions = 0
    existing_names: set[str] = set()  # D2069: batch-level uniqueness tracking
    pipeline_commit = get_pipeline_commit()
    pipeline_run_id = get_pipeline_run_id()  # BUG-026 FIX: use singleton directly

    for i, cluster in enumerate(clusters, 1):
        cluster_id = cluster["cluster_id"]
        principle_ids = cluster["principle_ids"]
        print(f"  [{i}/{len(clusters)}] Cluster {cluster_id} "
              f"({len(principle_ids)} principles)", end=" ")

        # Gather principles for this cluster, split by content_type (D2072)
        cluster_principles = []
        for pid in principle_ids:
            if pid in principles_idx:
                p = principles_idx[pid]
                ct = p.get("content_type", "principle")
                if ct == "process_template":
                    process_templates.append(p)
                elif ct == "process_instance":
                    process_instances.append(p)
                elif ct == "growth_edge":
                    growth_edges.append(p)
                elif ct == "tool_instruction":
                    tool_instructions.append(p)
                else:
                    cluster_principles.append(p)

        if not cluster_principles:
            skipped_types = []
            if process_templates: skipped_types.append(f"{len(process_templates)} PTs")
            if process_instances: skipped_types.append(f"{len(process_instances)} PIs")
            if tool_instructions: skipped_types.append(f"{len(tool_instructions)} TIs")
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
        # Otherwise use two-call pattern: CRIBS (Qwen) + Classify (Phi-4-mini).
        _skip_llm: bool = os.environ.get("MAXWELL_SKIP_LLM", "") == "1"
        _use_merged: bool = os.environ.get("MAXWELL_MERGED_S4", "") == "1"

        if _skip_llm:
            print("(LLM off — CRIBS enrichment skipped)", flush=True, end=" ")
        elif _use_merged:
            # D2226: Single-call CRIBS + Classification (D2224)
            try:
                merged_result = merged_cribs_classify(fb_data, model=VERIFY_MODEL)
                # Extract CRIBS fields
                for field in ("application", "failure_mode", "elaboration",
                              "keywords", "jargon"):
                    if merged_result.get(field):
                        fb_data[field] = merged_result[field]
                # Stash classification for Phase 2
                fb_data["_merged_classification"] = merged_result
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
                if isinstance(cribs_result, dict):
                    for field in ("application", "failure_mode", "elaboration",
                                  "keywords", "jargon"):
                        if cribs_result.get(field):
                            fb_data[field] = cribs_result[field]
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
                class_data = call_omlx_json(
                    prompt=class_prompt,
                    model=VERIFY_MODEL,
                    system=CLASSIFY_SYSTEM_PROMPT,
                    max_tokens=512,
                )
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
                    "evidence": "cited",
                }
                classification_errors += 1

        # ── Stage 1: Capture raw LLM output (D2138: preserved forever) ──
        domains_raw = list(class_data.get("domains", []))
        discipline_raw_raw = class_data.get("discipline", "")
        if isinstance(discipline_raw_raw, list):
            discipline_raw_raw = discipline_raw_raw[0] if discipline_raw_raw else ""
        discipline_raw = str(discipline_raw_raw) if discipline_raw_raw else ""
        is_specialized = class_data.get("is_specialized", False)
        if not isinstance(is_specialized, bool):
            is_specialized = str(is_specialized).lower() in ("true", "1", "yes")

        # Validate evidence (still LLM-classified)
        if class_data.get("evidence") not in ("cited", "axiomatic"):
            class_data["evidence"] = "cited"

        # ── Stage 2: Map raw → canonical (D2138) ──
        canonical_discipline = map_to_canonical_with_fallback(
            discipline_raw, "discipline", synonym_index, CANONICAL_DISCIPLINES
        )
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
        if raw_depth in VALID_DEPTHS:
            depth_val = raw_depth
        else:
            # Fallback: conservative default. If LLM hallucinates depth, assume domain.
            depth_val = "domain"

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
        for p in cluster_principles:
            for sb in p.get("source_books", []):
                source_books.add(sb)

        # D2069: Name normalization + uniqueness
        name = normalize_fb_name(name, max_words=5)
        if not check_name_unique(name, existing_names):
            name_collisions += 1
            # Append cluster_id to disambiguate
            name = f"{name} (Cluster {cluster_id})"
            print(f"      ⚠️  Name collision, disambiguated: '{name}'")
        existing_names.add(name)

        # ── Auto-derive agentic metadata (D2130) ──────────────────────────
        n_domains = len(class_data.get("domains", []))

        # difficulty_level: derived from depth (discipline is singular, no cardinality check)
        depth_val = class_data.get("depth", "domain")
        if depth_val == "specialized":
            difficulty_level = "expert"
        elif depth_val == "universal":
            difficulty_level = "beginner"  # universal = accessible to all
        elif depth_val == "domain":
            difficulty_level = "expert" if n_domains == 1 else "intermediate"
        else:
            difficulty_level = "intermediate"

        # temporal_scope: heuristic from keywords + definition signals
        def_text = (definition + " " + fb_data.get("elaboration", "")).lower()
        if any(w in def_text for w in ["always", "universal", "fundamental", "any system", "all"]):
            temporal_scope = "timeless"
        elif any(w in def_text for w in ["202", "current", "modern", "recent", "today", "now"]):
            temporal_scope = "contemporary"
        else:
            temporal_scope = "timeless"  # default: principles are timeless unless evidence suggests otherwise

        # ── Auto-derive v1 Anytype properties (context, accessibility, intimacy_boundary) ─
        # context: comma-separated routing hints derived from domain signals
        context_parts: list[str] = []
        business_signals = {"business operations", "business development", "entrepreneurship",
                            "organizational behavior", "marketing"}
        design_signals = {"graphic design", "brand identity", "editorial & advertising",
                          "motion design", "environmental design", "digital product",
                          "illustration", "packaging", "web & ui", "user experience",
                          "creative technology", "data visualization"}
        system_signals = {"systems & frameworks", "code & computation", "engineering practice",
                          "ai & agents", "ai systems", "computational science & physics",
                          "software engineering"}
        academic_signals = {"research & methodology", "semiotics & communication",
                            "computational art", "philosophy"}
        domain_set = set(class_data.get("domains", []))
        if domain_set & business_signals:
            context_parts.append("business")
        if domain_set & design_signals:
            context_parts.append("design")
        if domain_set & system_signals:
            context_parts.append("system")
        if domain_set & academic_signals:
            context_parts.append("academic")
        if not context_parts:
            context_parts.append("personal")
        context_val = ", ".join(sorted(context_parts))

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

        # intimacy_boundary: default public for pipeline FBs (user can override)
        intimacy_val = "public"

        # provenance: pipeline FBs are always llm_extracted_from_source (C29)
        provenance_val = "llm_extracted_from_source"

        # Build FB record (bloat removed per D2130: no s3_original_domain, no classification_method)
        fb = {
            "fb_id": make_hash_id(name, definition),
            "name": name,
            "definition": definition,
            "mechanism": fb_data.get("mechanism", "").strip(),
            "boundary": fb_data.get("boundary", "").strip(),
            "consequence": fb_data.get("consequence", "").strip(),
            "application": fb_data.get("application", "").strip(),
            "failure_mode": fb_data.get("failure_mode", "").strip(),
            "elaboration": fb_data.get("elaboration", "").strip(),
            "keywords": fb_data.get("keywords", "").strip(),
            "domains": class_data["domains"],
            "discipline": class_data.get("discipline", "emerging"),
            "domains_raw": domains_raw,
            "discipline_raw": discipline_raw if discipline_raw else None,
            "depth": depth_val,
            "evidence": class_data.get("evidence", "cited"),
            # ── v1 Anytype properties ──
            "context": context_val,
            "accessibility": accessibility_val,
            "intimacy_boundary": intimacy_val,
            "provenance": provenance_val,
            # ── Agentic metadata ──
            "difficulty_level": difficulty_level,
            "temporal_scope": temporal_scope,
            "prerequisite_fbs": fb_data.get("prerequisite_fbs", []),
            "procedural_skill": fb_data.get("procedural_skill"),
            # ── Provenance (simplified) ──
            "source_clusters": [cluster_id],
            "source_books": sorted(source_books),
            "source_principle_ids": [p.get("principle_id", "") for p in cluster_principles if p.get("principle_id")],
            "evidence_passages": cluster_principles[0].get("evidence_passages", []) if cluster_principles else [],
            "evidence_passages_shown": cluster_principles[0].get("evidence_passages_shown", []) if cluster_principles else [],
            "source_text": _collect_source_text(cluster_principles),
            "classification_errors": errors if errors else None,
            # ── Utilization tracking (initialized at zero) ──
            "usage_count": 0,
            "feedback_score": None,
            "feedback_count": 0,
            "fb_version": 1,
            "classification_status": "CLEAN",  # D2214/F-H16: Pydantic default never applied to dict
        }
        # Only include jargon when specialized terms need explanation
        jargon_val = _serialize_jargon(fb_data.get("jargon"))
        if jargon_val:
            fb["jargon"] = jargon_val
        fb = stamp_record(fb, gen_model=GEN_MODEL)
        fb["pipeline_run_id"] = pipeline_run_id
        fb["pipeline_commit"] = pipeline_commit
        fbs.append(fb)

        elapsed = time.time() - start
        err_str = f" ({len(errors)} label errors)" if errors else ""
        print(f"→ ✅ '{name}'{err_str} ({elapsed:.1f}s)")

    # ── P1.4: Compute FB relationship edges (LightRAG foundation) ────
    if len(fbs) > 1:
        compute_fb_relationships(fbs)

    # Write FB checkpoint
    safe_write(
        STAGE4_CHECKPOINT,
        "\n".join(json.dumps(f, ensure_ascii=False) for f in fbs) + "\n",
    )

    # ── D2073: Save growth edges separately ───────────────────────────
    ge_path = STAGE4_CHECKPOINT.parent / S4_GE_OUTPUT
    if growth_edges:
        seen_ge: set[str] = set()
        deduped_ge = []
        for ge in growth_edges:
            if ge["principle_id"] not in seen_ge:
                seen_ge.add(ge["principle_id"])
                deduped_ge.append(ge)
        safe_write(
            ge_path,
            "\n".join(json.dumps(t, ensure_ascii=False) for t in deduped_ge) + "\n",
        )

    # ── D2072: Save process templates separately ──────────────────────
    pt_path = STAGE4_CHECKPOINT.parent / S4_PT_OUTPUT
    if process_templates:
        seen_pt: set[str] = set()
        deduped_pt = []
        for pt in process_templates:
            if pt["principle_id"] not in seen_pt:
                seen_pt.add(pt["principle_id"])
                deduped_pt.append(pt)
        safe_write(
            pt_path,
            "\n".join(json.dumps(t, ensure_ascii=False) for t in deduped_pt) + "\n",
        )

    # ── D2072: Save process instances separately ──────────────────────
    pi_path = STAGE4_CHECKPOINT.parent / S4_PI_OUTPUT
    if process_instances:
        seen_pi: set[str] = set()
        deduped_pi = []
        for pi in process_instances:
            if pi["principle_id"] not in seen_pi:
                seen_pi.add(pi["principle_id"])
                deduped_pi.append(pi)
        safe_write(
            pi_path,
            "\n".join(json.dumps(t, ensure_ascii=False) for t in deduped_pi) + "\n",
        )

    # ── D2072: Save tool instructions separately ──────────────────────
    ti_path = STAGE4_CHECKPOINT.parent / S4_TI_OUTPUT
    if tool_instructions:
        seen_ti: set[str] = set()
        deduped_ti = []
        for ti in tool_instructions:
            if ti["principle_id"] not in seen_ti:
                seen_ti.add(ti["principle_id"])
                deduped_ti.append(ti)
        safe_write(
            ti_path,
            "\n".join(json.dumps(t, ensure_ascii=False) for t in deduped_ti) + "\n",
        )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ FBs generated:            {len(fbs)}")
    print(f"🔧 Process templates:        {len(process_templates)} (→ {S4_PT_OUTPUT})")
    print(f"📖 Process instances:        {len(process_instances)} (→ {S4_PI_OUTPUT})")
    print(f"🌱 Growth edges:             {len(growth_edges)} (→ {S4_GE_OUTPUT})")
    print(f"🛠️  Tool instructions:        {len(tool_instructions)} (→ {S4_TI_OUTPUT})")
    print(f"❌ Failed clusters:          {failed}")
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


def main():
    parser = argparse.ArgumentParser(description="Stage 4: Merge Clusters → FBs + Multi-label Classification")
    parser.add_argument("--cluster", help="Comma-separated cluster IDs to process (int or string)")
    args = parser.parse_args()

    cluster_ids = None
    if args.cluster:
        raw_ids = [c.strip() for c in args.cluster.split(",")]
        # D2120: Cluster IDs can be hash strings (from Stage 2 FBs) or ints (legacy)
        try:
            cluster_ids = [int(c) for c in raw_ids]
        except ValueError:
            cluster_ids = raw_ids

    run_stage4(cluster_ids=cluster_ids)


if __name__ == "__main__":
    main()
