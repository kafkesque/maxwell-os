#!/usr/bin/env python3
"""
stage4_merge.py — Merge clusters → Foundation Blocks + SALSA classification.
=============================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 4), D1058, D150

Input:  Clusters from Stage 3 + Principles from Stage 2
Output: Foundation Blocks with SALSA-classified labels, checkpoint at stage4_merge.jsonl

Process:
  1. For each cluster, gather all member principles
  2. Send to Qwen3.6: merge principles → single FB (name + 6 body fields)
  3. SALSA classification: single-pass prompt lists all valid labels inline
  4. Pydantic Literal validation catches hallucinated labels at write boundary
  5. Write checkpoint

Generator: Qwen3.6-35B-A3B-4bit (OMLX)
Classifier: Phi-4-mini-instruct-8bit (OMLX) — R5: different family from generator (D2068: fixed on oMLX 0.5.3)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage4_merge.py
    python3 pipeline/stage4_merge.py --cluster 0,1,2   # Process specific clusters
"""

import argparse
import json
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
    S4_GE_OUTPUT,
    S4_MAX_PRINCIPLES,
    S4_PI_OUTPUT,
    S4_PT_OUTPUT,
    S4_TI_OUTPUT,
    STAGE2_CHECKPOINT,
    STAGE3_CHECKPOINT,
    STAGE4_CHECKPOINT,
    VERIFY_MODEL,  # P0.10: imported for R5-compliant SALSA classification
)
from pipeline.schemas import (
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    is_valid_discipline,
    is_valid_domain,
    match_domains_to_canonical,
    match_to_canonical,
)
from pipeline.stamp import get_pipeline_commit, get_pipeline_run_id, make_hash_id, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
MAX_PRINCIPLES_PER_CLUSTER = S4_MAX_PRINCIPLES  # D2080: from config, was hardcoded 20

# ── Prompt templates ───────────────────────────────────────────────────────

FB_SYSTEM_PROMPT = """You are a Foundation Block generator. You synthesize multiple related principles
into a single, cohesive Foundation Block — a reusable concept that can be applied across contexts.

A Foundation Block has these fields:
- name: 3-7 word concept name (title case, precise — not vague like "Strategic AI Collaboration")
- definition: 3-4 sentences. S1: name it. S2: explain mechanism. S3-4: constraints/consequences.
- application: "When [situation] -> do [action]." One concrete, actionable example.
- failure_mode: "The principle fails when [specific scenario]." How it breaks in practice.
- elaboration: 3-5 sentences. Deeper nuance, edge cases, unexpected implications.
- keywords: 3-5 key terms, comma-separated.
- jargon: Explain any specialized terms in 1-2 plain-language sentences each. Use null if none needed.

CRITICAL RULES:
- Produce a genuine PRINCIPLE, not tool documentation, not syntax lessons, not system design docs
- If the principles are about a specific tool (Altair, Figma, R, etc.), the FB must name the tool explicitly in its title
- A principle answers WHY and WHEN, not just HOW
- Names must be precise: "Narrative Framing in UX" not "Narrative Design Creates Meaning"

GOLDEN EXAMPLES — model your output on these:

EXAMPLE 1 (cross-domain): "The Jagged Frontier of AI Competence"
Definition: "AI capabilities are not uniformly distributed across tasks — they exhibit a jagged frontier where some tasks are performed exceptionally well while closely related tasks fail unexpectedly. Effective human-AI collaboration requires mapping this frontier empirically rather than assuming uniform capability."
Application: "When introducing AI into a workflow -> run a systematic calibration: give the AI 10 representative tasks from your domain, evaluate each output, identify the pattern of successes and failures."
Keywords: "AI collaboration, jagged frontier, task decomposition, empirical calibration"

EXAMPLE 2 (domain-specific): "Descriptive References Reduce Fragility"
Definition: "Descriptive references use named identifiers instead of positional indices to create more robust and maintainable code. This approach leverages human-readable labels to access data elements, making code less susceptible to breaking when underlying data structures change."
Application: "When writing data processing code that accesses structured information -> use named column references or descriptive variable names instead of positional indices."
Keywords: "named references, positional indices, code maintainability, magic numbers"

ANTI-PATTERNS — never produce these:
- "Altair Annotation and Emphasis Techniques" — this is tool documentation renamed
- "Function Parameters Control Behavior" — this is syntax, not a principle
- "R Workspace Hygiene" — this is a language-specific workflow guide
- "Event-Driven Retail Inventory Architecture" — this is a system design document
- Definitions stuffed with unrelated jargon from multiple domains
- Names that sound profound but mean nothing specific

Synthesize the principles into one block. Don't just pick one — merge the insights.
Return ONLY a JSON object with these exact keys."""


def build_fb_prompt(principles: list[dict]) -> str:
    """Build the FB generation prompt from cluster principles."""
    lines = ["Synthesize these related principles into ONE Foundation Block.\n"]
    lines.append("PRINCIPLES TO MERGE:")
    for i, p in enumerate(principles, 1):
        text = (p.get("definition") or p.get("principle_text", ""))[:500]
        lines.append(f"  {i}. {text}")
    lines.append("")
    lines.append("Return a JSON object:")
    lines.append('{"name": "...", "definition": "...", "application": "...", ')
    lines.append(' "failure_mode": "...", "elaboration": "...", ')
    lines.append(' "keywords": "...", "jargon": "..." or null}')
    return "\n".join(lines)


CLASSIFY_SYSTEM_PROMPT = """You are a precise taxonomy classifier for Foundation Blocks.
You must classify the given FB into 1-3 disciplines and 1-5 domains from the provided lists.

Rules:
- Pick EXACTLY from the lists below. NO invented labels. No "emerging" unless absolutely unavoidable.
- disciplines: Pick 1-3 from the discipline list that capture the FB's intellectual foundations.
                Multi-disciplinary FBs are EXPECTED and valuable. Only pick ONE if truly single-discipline.
- domains: Pick 1-5 from the domain list. Only include domains the principle genuinely spans.
- depth: "universal" (applies everywhere), "cross-domain" (2+ domains),
         "domain" (specific to one domain), "specialized" (narrow sub-field)
- evidence: "cited" (grounded in source text) or "axiomatic" (self-evident truth)

CLASSIFICATION EXAMPLES:

FB: "The Jagged Frontier of AI Competence" — about AI task performance patterns
-> disciplines: ["strategic thinking", "ai engineering"] | depth: "cross-domain" | domains: ["ai & agents", "engineering practice", "business operations"]

FB: "Descriptive References Reduce Fragility" — about code maintainability via named access
-> disciplines: ["software engineering"] | depth: "domain" | domains: ["code & computation", "engineering practice"]

FB: "Design Fiction" — about speculative prototyping for strategy
-> disciplines: ["design strategy", "strategic thinking"] | depth: "cross-domain" | domains: ["creative technology", "graphic design", "digital product"]

FB: "Cross-Modal Design Amplification" — about multisensory integration in experience design
-> disciplines: ["design psychology", "user research"] | depth: "cross-domain" | domains: ["digital product", "creative technology", "user experience"]

Return ONLY a JSON object: {"disciplines": ["d1", "d2"], "domains": ["d1", "d2"], "depth": "...", "evidence": "..."}"""


def build_classify_prompt(fb_name: str, fb_definition: str,
                          domains: list[str], disciplines: list[str]) -> str:
    """Build the multi-label classification prompt with inline label lists.
    
    D2066: Open-set depth-based multi-label classification.
    disciplines: 1-3 labels (was single-discipline SALSA, D2024 — superseded).
    """
    domain_list = ", ".join(domains)
    discipline_list = ", ".join(disciplines)

    return f"""Classify this Foundation Block:

NAME: {fb_name}
DEFINITION: {fb_definition[:500]}

DISCIPLINES (pick 1-3): {discipline_list}

DOMAINS (pick 1-5): {domain_list}

Return JSON:
{{"disciplines": ["discipline1", "discipline2"],
  "domains": ["domain1", "domain2"],
  "depth": "universal|cross-domain|domain|specialized",
  "evidence": "cited|axiomatic"}}"""


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
            is_convergent = fb.get("is_convergent", False)
            clusters.append({
                "cluster_id": fb_id_val or f"fb_{i}",
                "principle_ids": [fb_id_val] if fb_id_val else [f"fb_{i}"],
                "source_books": fb.get("source_books", []),
                "is_convergent": is_convergent,
                "is_noise": not is_convergent,
                "source": "stage2_fb",  # Mark as directly from Stage 2
            })

    print(f"   📂 Loaded {len(clusters)} FBs from Stage 2 (Stage 3 bypassed per D2120)")
    return clusters, principles_idx


def dedup_fbs_by_cosine(
    fbs: list[dict],
    threshold: float = 0.92,
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


def load_stage3_clusters() -> list[dict]:
    """DEPRECATED by D2120. Use load_stage2_fbs_via_clusters() instead.

    Kept as compatibility shim that falls back to the old Stage 3 checkpoint
    if it exists, otherwise wraps Stage 2 FBs.
    """
    # Try old Stage 3 checkpoint first (backward compat)
    if STAGE3_CHECKPOINT.exists():
        print("   📂 Loading from Stage 3 checkpoint (legacy path)")
        clusters = []
        with open(STAGE3_CHECKPOINT) as f:
            for line in f:
                line = line.strip()
                if line:
                    clusters.append(json.loads(line))
        return clusters

    # D2120: Wrap Stage 2 FBs as clusters
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

    # Validate disciplines (multi-label, 1-3)
    disciplines = result.get("disciplines", [])
    if isinstance(disciplines, str):
        # Backward compat: single string → wrap in list
        disciplines = [disciplines]
    if not isinstance(disciplines, list):
        errors.append(f"Disciplines is not a list: {type(disciplines)}")
    else:
        if len(disciplines) < 1:
            errors.append("At least 1 discipline required")
        if len(disciplines) > 3:
            errors.append(f"Too many disciplines: {len(disciplines)} > 3")
        for d in disciplines:
            if not is_valid_discipline(d):
                errors.append(f"Invalid discipline: '{d}'")

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


def _serialize_jargon(jargon_value) -> str | None:
    """Convert jargon (string or dict) to a string.

    LLM sometimes returns jargon as {"term": "explanation"} dict.
    Flatten to "term: explanation" format per jargon key.
    """
    if jargon_value is None:
        return None
    if isinstance(jargon_value, str):
        return jargon_value.strip() or None
    if isinstance(jargon_value, dict):
        parts = []
        for term, explanation in jargon_value.items():
            if explanation:
                parts.append(f"{term}: {explanation}")
            else:
                parts.append(term)
        return "; ".join(parts) if parts else None
    if isinstance(jargon_value, list):
        return "; ".join(str(item) for item in jargon_value if item) or None
    return str(jargon_value) if jargon_value else None


# ── P1.4: FB Relationship Edge Detection ──────────────────────────────────

def compute_fb_relationships(
    fbs: list[dict],
    similarity_threshold: float = 0.80,
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
    discipline_sets: list[set[str]] = [set(fb.get("disciplines", [])) for fb in fbs]
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


def run_stage4(cluster_ids: list[int] = None):
    """Run Stage 4: Merge clusters into Foundation Blocks."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    if not check_omlx_health():
        print("❌ OMLX is not running.")
        sys.exit(1)

    clusters = load_stage3_clusters()
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
            deduped_fbs = dedup_fbs_by_cosine(cluster_fbs, threshold=0.92)
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

        # Phase 1: Generate FB
        try:
            prompt = build_fb_prompt(cluster_principles)
            fb_data = call_omlx_json(
                prompt=prompt,
                model=GEN_MODEL,
                system=FB_SYSTEM_PROMPT,
                max_tokens=2048,
            )
        except Exception as e:
            print(f"→ ❌ Generation error: {e}")
            failed += 1
            continue

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

        # Phase 2: SALSA classify
        try:
            class_prompt = build_classify_prompt(
                name, definition,
                domains=CANONICAL_DOMAINS,
                disciplines=CANONICAL_DISCIPLINES,
            )
            class_data = call_omlx_json(
                prompt=class_prompt,
                model=VERIFY_MODEL,     # D2068: Phi-4-mini fixed on oMLX 0.5.3 (R5 restore)
                system=CLASSIFY_SYSTEM_PROMPT,
                max_tokens=512,
            )
        except Exception as e:
            print(f"→ ⚠️  Classification error: {e}, using 'emerging'")
            class_data = {
                "disciplines": ["emerging"],
                "domains": ["emerging"],
                "depth": "domain",
                "evidence": "cited",
            }

        # Capture raw LLM output BEFORE any validation/replacement.
        # Authority: governance/domain_labelling.md §1 (D1055-FIX Channel B)
        # Raw labels are preserved forever; canonical labels earn their place
        # through accumulation, not through being pre-approved.
        domains_raw = list(class_data.get("domains", []))
        disciplines_raw_raw = class_data.get("disciplines", [])
        if isinstance(disciplines_raw_raw, str):
            disciplines_raw_raw = [disciplines_raw_raw]
        disciplines_raw = list(disciplines_raw_raw)

        # Phase 2b: Synonym matching before validation.
        # Try to match non-canonical labels via synonym_map.yaml and taxonomy raw aliases.
        # This reduces "emerging" fallbacks without forcing labels that don't fit.
        matched_disciplines = []
        for d in disciplines_raw:
            if is_valid_discipline(d):
                matched_disciplines.append(d)
            else:
                matched = match_to_canonical(d, kind="discipline")
                matched_disciplines.append(matched if matched else d)
        class_data["disciplines"] = matched_disciplines

        matched_domains = match_domains_to_canonical(domains_raw)
        if matched_domains:
            class_data["domains"] = matched_domains

        # Validate classification
        is_valid, errors = validate_classification(class_data)
        if not is_valid:
            classification_errors += 1
            # Fix invalid labels by replacing with 'emerging'
            fixed_disciplines = []
            for d in class_data.get("disciplines", []):
                if is_valid_discipline(d):
                    fixed_disciplines.append(d)
            if not fixed_disciplines:
                fixed_disciplines = ["emerging"]
            class_data["disciplines"] = fixed_disciplines
            fixed_domains = []
            for d in class_data.get("domains", []):
                if is_valid_domain(d):
                    fixed_domains.append(d)
            if not fixed_domains:
                fixed_domains = ["emerging"]
            class_data["domains"] = fixed_domains
            if class_data.get("depth") not in ("universal", "cross-domain", "domain", "specialized"):
                class_data["depth"] = "domain"
            if class_data.get("evidence") not in ("cited", "axiomatic"):
                class_data["evidence"] = "cited"

        # Collect source books
        source_books = set()
        for p in cluster_principles:
            for sb in p.get("source_books", []):
                source_books.add(sb)

        # Derive crawl provenance from source book paths
        # e.g., "DOMAIN 4 Business/some_book.md" → "DOMAIN 4 Business"
        s3_original_domain = None
        if source_books:
            first_book = sorted(source_books)[0]
            parts = first_book.replace("\\", "/").split("/")
            if len(parts) >= 2:
                s3_original_domain = parts[0]  # Top-level domain folder

        # D2069: Name normalization + uniqueness
        name = normalize_fb_name(name, max_words=5)
        if not check_name_unique(name, existing_names):
            name_collisions += 1
            # Append cluster_id to disambiguate
            name = f"{name} (Cluster {cluster_id})"
            print(f"      ⚠️  Name collision, disambiguated: '{name}'")
        existing_names.add(name)

        # D2069: Embed source principle texts for fast Stage 5 verification.
        # Eliminates the 3-checkpoint lookup chain (Stage5→Stage3→Stage2).
        source_principles_embedded = []
        for p in cluster_principles:
            source_principles_embedded.append({
                "principle_id": p.get("principle_id", ""),
                "principle_text": (p.get("definition") or p.get("principle_text", ""))[:500],
                "source_segment_id": p.get("source_segments", [""])[0] if p.get("source_segments") else "",
            })

        # Build FB record
        fb = {
            "fb_id": make_hash_id(name, definition),
            "name": name,
            "definition": definition,
            "application": fb_data.get("application", "").strip(),
            "failure_mode": fb_data.get("failure_mode", "").strip(),
            "elaboration": fb_data.get("elaboration", "").strip(),
            "keywords": fb_data.get("keywords", "").strip(),
            "jargon": _serialize_jargon(fb_data.get("jargon")),
            "domains": class_data["domains"],
            "disciplines": class_data["disciplines"],       # D2066: multi-label (1-3)
            "domains_raw": domains_raw,
            "disciplines_raw": disciplines_raw,             # D2066: raw LLM output preserved
            "depth": class_data["depth"],
            "evidence": class_data["evidence"],
            "source_clusters": [cluster_id],
            "source_books": sorted(source_books),
            "source_principles": source_principles_embedded,
            "s3_original_domain": s3_original_domain,
            "classification_method": "multi-label",  # D2066: was SALSA (D2024 superseded)
            "classification_errors": errors,
        }
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
    parser = argparse.ArgumentParser(description="Stage 4: Merge Clusters → FBs + SALSA Classification")
    parser.add_argument("--cluster", help="Comma-separated cluster IDs to process")
    args = parser.parse_args()

    cluster_ids = None
    if args.cluster:
        cluster_ids = [int(c.strip()) for c in args.cluster.split(",")]

    run_stage4(cluster_ids=cluster_ids)


if __name__ == "__main__":
    main()
