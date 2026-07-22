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
Classifier: Same model, SALSA probe (single-token restriction via prompt)
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
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    STAGE2_CHECKPOINT,
    STAGE3_CHECKPOINT,
    STAGE4_CHECKPOINT,
    CHECKPOINT_DIR,
    GEN_MODEL,
    VERIFY_MODEL,  # P0.10: imported for R5-compliant SALSA classification
    MAX_DOMAINS_PER_FB,
)
from pipeline.stamp import stamp_record, make_hash_id, get_pipeline_commit, get_pipeline_run_id
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.io_guard import safe_write
from pipeline.schemas import (
    CANONICAL_DOMAINS,
    CANONICAL_DISCIPLINES,
    is_valid_domain,
    is_valid_discipline,
    match_to_canonical,
    match_domains_to_canonical,
)

# ── Constants ──────────────────────────────────────────────────────────────
MAX_PRINCIPLES_PER_CLUSTER = 20  # Truncate large clusters for prompt

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
        text = p["principle_text"][:500]
        lines.append(f"  {i}. {text}")
    lines.append("")
    lines.append("Return a JSON object:")
    lines.append('{"name": "...", "definition": "...", "application": "...", ')
    lines.append(' "failure_mode": "...", "elaboration": "...", ')
    lines.append(' "keywords": "...", "jargon": "..." or null}')
    return "\n".join(lines)


CLASSIFY_SYSTEM_PROMPT = """You are a precise taxonomy classifier for Foundation Blocks.
You must classify the given FB into EXACTLY ONE discipline and 1-5 domains from the provided lists.

Rules:
- Pick EXACTLY from the lists below. NO invented labels. No "emerging" unless absolutely unavoidable.
- discipline: Pick ONE from the discipline list that best captures the FB's core domain.
- domains: Pick 1-5 from the domain list. Only include domains the principle genuinely spans.
- depth: "universal" (applies everywhere), "cross-domain" (2+ domains), 
         "domain" (specific to one domain), "specialized" (narrow sub-field)
- evidence: "cited" (grounded in source text) or "axiomatic" (self-evident truth)

CLASSIFICATION EXAMPLES:

FB: "The Jagged Frontier of AI Competence" — about AI task performance patterns
-> discipline: "strategic thinking" | depth: "cross-domain" | domains: ["ai & agents", "engineering practice", "business operations"]

FB: "Descriptive References Reduce Fragility" — about code maintainability via named access
-> discipline: "software engineering" | depth: "domain" | domains: ["code & computation", "engineering practice"]

FB: "Design Fiction" — about speculative prototyping for strategy
-> discipline: "design strategy" | depth: "cross-domain" | domains: ["creative technology", "graphic design", "digital product"]

FB: "Cross-Modal Design Amplification" — about multisensory integration in experience design
-> discipline: "design psychology" | depth: "cross-domain" | domains: ["digital product", "creative technology", "user experience"]

Return ONLY a JSON object: {"discipline": "...", "domains": ["d1", "d2"], "depth": "...", "evidence": "..."}"""


def build_classify_prompt(fb_name: str, fb_definition: str,
                          domains: list[str], disciplines: list[str]) -> str:
    """Build the SALSA classification prompt with inline label lists."""
    domain_list = ", ".join(domains)
    discipline_list = ", ".join(disciplines)

    return f"""Classify this Foundation Block:

NAME: {fb_name}
DEFINITION: {fb_definition[:500]}

DISCIPLINES (pick ONE): {discipline_list}

DOMAINS (pick 1-5): {domain_list}

Return JSON:
{{"discipline": "exact_discipline_label", 
  "domains": ["domain1", "domain2"], 
  "depth": "universal|cross-domain|domain|specialized", 
  "evidence": "cited|axiomatic"}}"""


def load_stage3_clusters() -> list[dict]:
    """Load clusters from Stage 3 checkpoint."""
    if not STAGE3_CHECKPOINT.exists():
        print("❌ Stage 3 checkpoint not found. Run stage3_cluster.py first.")
        sys.exit(1)

    clusters = []
    with open(STAGE3_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                clusters.append(json.loads(line))
    return clusters


def load_stage2_principles() -> dict[str, dict]:
    """Load principles from Stage 2, indexed by principle_id."""
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found.")
        sys.exit(1)

    principles = {}
    with open(STAGE2_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                p = json.loads(line)
                principles[p["principle_id"]] = p
    return principles


def validate_classification(result: dict) -> tuple[bool, list[str]]:
    """Validate classification output against canonical taxonomy.

    Returns (is_valid, errors).
    """
    errors = []

    # Validate discipline
    discipline = result.get("discipline", "")
    if not is_valid_discipline(discipline):
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


def _serialize_jargon(jargon_value) -> Optional[str]:
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

    print(f"🧩 Stage 4: Merge + Classify — {len(clusters)} clusters")
    print(f"   Model: {GEN_MODEL} | temp=0.0 | SALSA classify")
    print(f"{'='*60}")

    fbs = []
    failed = 0
    classification_errors = 0
    pipeline_commit = get_pipeline_commit()
    pipeline_run_id = get_pipeline_run_id()  # BUG-026 FIX: use singleton directly

    for i, cluster in enumerate(clusters, 1):
        cluster_id = cluster["cluster_id"]
        principle_ids = cluster["principle_ids"]
        print(f"  [{i}/{len(clusters)}] Cluster {cluster_id} "
              f"({len(principle_ids)} principles)", end=" ")

        # Gather principles for this cluster
        cluster_principles = []
        for pid in principle_ids:
            if pid in principles_idx:
                cluster_principles.append(principles_idx[pid])

        if not cluster_principles:
            print("→ ⚠️  No principles found, skipping")
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
            print(f"→ ⚠️  Non-dict response, skipping")
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
                model=GEN_MODEL,        # P0.10 REVERTED: Phi-4-mini returns empty on short prompts (Goose stress test: 44-389ms)
                system=CLASSIFY_SYSTEM_PROMPT,
                max_tokens=512,
            )
        except Exception as e:
            print(f"→ ⚠️  Classification error: {e}, using 'emerging'")
            class_data = {
                "discipline": "emerging",
                "domains": ["emerging"],
                "depth": "domain",
                "evidence": "cited",
            }

        # Capture raw LLM output BEFORE any validation/replacement.
        # Authority: governance/domain_labelling.md §1 (D1055-FIX Channel B)
        # Raw labels are preserved forever; canonical labels earn their place
        # through accumulation, not through being pre-approved.
        domains_raw = list(class_data.get("domains", []))
        discipline_raw = class_data.get("discipline", "")

        # Phase 2b: Synonym matching before validation.
        # Try to match non-canonical labels via synonym_map.yaml and taxonomy raw aliases.
        # This reduces "emerging" fallbacks without forcing labels that don't fit.
        if not is_valid_discipline(discipline_raw):
            matched = match_to_canonical(discipline_raw, kind="discipline")
            if matched:
                class_data["discipline"] = matched
        matched_domains = match_domains_to_canonical(domains_raw)
        if matched_domains:
            class_data["domains"] = matched_domains

        # Validate classification
        is_valid, errors = validate_classification(class_data)
        if not is_valid:
            classification_errors += 1
            # Fix invalid labels by replacing with 'emerging'
            if not is_valid_discipline(class_data.get("discipline", "")):
                class_data["discipline"] = "emerging"
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
            "discipline": class_data["discipline"],
            "domains_raw": domains_raw,
            "discipline_raw": discipline_raw,
            "depth": class_data["depth"],
            "evidence": class_data["evidence"],
            "source_clusters": [cluster_id],
            "source_books": sorted(source_books),
            "s3_original_domain": s3_original_domain,
            "classification_method": "SALSA",
            "classification_errors": errors,
        }
        fb = stamp_record(fb, gen_model=GEN_MODEL)
        fb["pipeline_run_id"] = pipeline_run_id
        fb["pipeline_commit"] = pipeline_commit
        fbs.append(fb)

        elapsed = time.time() - start
        err_str = f" ({len(errors)} label errors)" if errors else ""
        print(f"→ ✅ '{name}'{err_str} ({elapsed:.1f}s)")

    # Write checkpoint
    safe_write(
        STAGE4_CHECKPOINT,
        "\n".join(json.dumps(f, ensure_ascii=False) for f in fbs) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ FBs generated:        {len(fbs)}")
    print(f"❌ Failed clusters:      {failed}")
    print(f"🏷️  Classification errors: {classification_errors}")
    if fbs:
        depths = {}
        for fb in fbs:
            d = fb["depth"]
            depths[d] = depths.get(d, 0) + 1
        print(f"📊 Depths:               {depths}")
        print(f"📊 Avg domains/FB:       {sum(len(fb['domains']) for fb in fbs) / len(fbs):.1f}")
    print(f"📋 Checkpoint:            {STAGE4_CHECKPOINT}")


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
