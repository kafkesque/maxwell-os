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
    """Load clusters from Stage 3 checkpoint, including noise-preserved singletons.

    D2093/D2081 fix: Noise points written to cluster_noise.jsonl by Stage 3
    are loaded alongside main clusters. Previously orphaned — written but never read.
    """
    clusters = []

    # Main clusters
    if not STAGE3_CHECKPOINT.exists():
        print("❌ Stage 3 checkpoint not found. Run stage3_cluster.py first.")
        sys.exit(1)

    with open(STAGE3_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                clusters.append(json.loads(line))

    # D2093/D2081: Load noise-preserved singletons
    noise_path = STAGE3_CHECKPOINT.parent / "cluster_noise.jsonl"
    if noise_path.exists():
        noise_count = 0
        with open(noise_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    # Convert noise entry to cluster-like format for downstream processing
                    entry["is_noise"] = True
                    entry["is_convergent"] = False
                    clusters.append(entry)
                    noise_count += 1
        if noise_count > 0:
            print(f"   🔈 Loaded {noise_count} noise-preserved singletons from cluster_noise.jsonl")

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
                pid = p.get("principle_id", "")
                fid = p.get("fb_id", "")
                if pid:
                    principles[pid] = p
                if fid and fid != pid:
                    principles[fid] = p
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
            "discipline": class_data["discipline"],
            "domains_raw": domains_raw,
            "discipline_raw": discipline_raw,
            "depth": class_data["depth"],
            "evidence": class_data["evidence"],
            "source_clusters": [cluster_id],
            "source_books": sorted(source_books),
            "source_principles": source_principles_embedded,
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
