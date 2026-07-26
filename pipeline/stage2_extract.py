#!/usr/bin/env python3
"""
stage2_extract.py — Convergent Principle Extraction from Clusters.
==================================================================
Authority: D2094, D2095, D2101 | CONSTITUTION.md §3

Input:  Clusters from Stage 1.5 (FAISS) + raw segments from Stage 1
Output: Convergent Foundation Blocks with mechanism/boundary/consequence

v3.0 REWRITE (D2094): Extracts ONE principle per CLUSTER (5-15 segments, ≥2 books).
Replaces per-segment extraction which produced summaries, not principles.

Process:
  1. Load clusters from Stage 1.5 checkpoint
  2. For each convergent cluster (≥2 source books):
     a. Gather 5-15 raw segment texts
     b. Build convergent extraction prompt
     c. Call LLM to extract ONE principle per cluster
     d. Schema: name, definition, mechanism, boundary, consequence,
        is_summary, evidence_passages
     e. Merged classification: depth, discipline, domain, evidence, route
  3. Gate enforcement, golden few-shot parity, MinHash dedup
  4. Crash-safe incremental checkpoint

Generator: Qwen3.6-35B-A3B-4bit (OMLX or MLX)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage2_extract.py --only-convergent  # Skip single-source clusters
    python3 pipeline/stage2_extract.py --provider mlx     # Use MLX instead of OMLX
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    GEN_MODEL,
    S2_GATE_ENABLED,
    S2_GATE_STRICT,
    S2_GOLDEN_MAX,
    S2_GOLDEN_NEGATIVE,
    S2_GOLDEN_PATH,
    S2_GOLDEN_POSITIVE,
    S2_MINHASH_NUM_PERM,
    S2_MINHASH_THRESHOLD,
    S2_OMLX_RETRY,
    S15_MIN_SOURCE_DIVERSITY,
    STAGE1_5_CHECKPOINT,
    STAGE1_CHECKPOINT,
    STAGE2_CHECKPOINT,
)
from pipeline.stamp import get_pipeline_commit, make_hash_id, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
MAX_CLUSTER_SAMPLES: int = 15  # Max segments to feed per cluster
MIN_CONVERGENT_BOOKS: int = S15_MIN_SOURCE_DIVERSITY
NON_FB_TYPES: set[str] = {"process_template", "process_instance", "growth_edge", "tool_instruction"}

# ── Convergent extraction system prompt (v3.0: cluster-before-extract) ────

SYSTEM_PROMPT = """You are a convergent principle extraction engine. You receive multiple related text
passages from DIFFERENT books. Your task is to identify the ONE underlying principle
that transcends any single source — the causal mechanism, concept, or method that
these passages collectively reveal.

A convergent principle is:
- A concise statement of WHY something works, WHEN it applies, and WHAT its limits are
- Synthesized from patterns across ALL provided passages, not just one
- NOT a summary of any single passage
- NOT a list of what each passage says
- NOT a vague generalization that ignores specifics

PRINCIPLE STRUCTURE (required for every extraction):
1. name: 3-7 word concept name (title case, precise)
2. definition: 3-4 sentences. S1: name the principle. S2: explain the causal mechanism.
   S3-4: describe boundary conditions and consequences.
3. mechanism: "X causes/enables/prevents Y because Z" — the causal chain
4. boundary: "The principle applies when [condition]. It fails when [counter-condition]."
5. consequence: "Because of this principle, [what follows]."
6. is_summary: true ONLY if you can only restate the passages without identifying
   a convergent mechanism. Be honest — self-flag if summarizing.

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

CLASSIFICATION (merged — classify as part of extraction):
- depth: "universal" (applies across all domains) | "cross-domain" (2+ unrelated fields) |
         "domain" (specific to one field — DEFAULT) | "specialized" (narrow tool/method)
- discipline: Pick from the provided discipline list
- domain: Pick 1-3 from the provided domain list
- evidence: "cited" (verbatim support exists) | "axiomatic" (logically follows)
- route: "FB" (convergent principle) | "PT" (process template/steps) |
         "GE" (growth edge/speculative) | "NULL" (no extractable principle)

When in doubt, route NULL. False positives pollute; false negatives leave gaps.

Return ONLY a JSON object with these EXACT keys. No markdown, no explanation.

Example output:
{
  "name": "Value-First Demonstration",
  "definition": "Demonstrating concrete value before requesting commitment converts prospects because direct experience of benefit bypasses skepticism toward unverified claims. The principle holds when the value is demonstrable within minutes of first exposure.",
  "mechanism": "Direct experience of value eliminates skepticism toward unverified claims because the prospect's own senses provide the proof, making external persuasion unnecessary.",
  "boundary": "Applies when value is demonstrable within minutes. Fails when value requires long-term usage to perceive (e.g., enterprise infrastructure, health supplements).",
  "consequence": "Products that can demonstrate value immediately grow faster through product-led adoption than those relying on sales narratives.",
  "is_summary": false,
  "evidence_passages": [
    "Dropbox used a 3-minute demo video showing file sync... beta signups jumped from 5,000 to 75,000.",
    "The best SaaS companies demonstrate value before asking for money. Slack let users invite teammates before requiring payment."
  ],
  "depth": "cross-domain",
  "discipline": "marketing",
  "domain": ["business operations", "digital product"],
  "evidence": "cited",
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
    taxonomy_disciplines: list[str],
    taxonomy_domains: list[str],
) -> tuple[str, list[str]]:
    """Build convergent extraction prompt for one cluster.

    Args:
        cluster: Cluster dict with segment_ids, source_books, cohesion.
        segments: Indexed segment dicts by segment_id.
        taxonomy_disciplines: Canonical discipline labels.
        taxonomy_domains: Canonical domain labels.

    Returns:
        Tuple of (prompt_text, evidence_passages_for_output).
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    cohesion: float = cluster.get("cohesion", 0.5)

    # Sample segments: fewer for high-cohesion clusters
    if cohesion >= 0.90:
        n_samples: int = 5
    elif cohesion >= 0.75:
        n_samples: int = 8
    else:
        n_samples: int = MAX_CLUSTER_SAMPLES

    sampled: list[str] = seg_ids[:n_samples]
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
    discipline_list: str = ", ".join(taxonomy_disciplines[:30])
    domain_list: str = ", ".join(taxonomy_domains[:30])

    prompt: str = f"""I have {len(sampled)} passages from {len(books_seen)} books: {source_summary}

{"─" * 40}
{" | ".join(texts)}
{"─" * 40}

Extract ONE convergent principle. Return JSON with:
- name, definition, mechanism, boundary, consequence, is_summary (bool), evidence_passages (up to 5 verbatim quotes)
- depth (universal|cross-domain|domain|specialized), discipline ({discipline_list}), domain ({domain_list}), evidence (cited|axiomatic), route (FB|PT|GE|NULL)

No principle → {{"route": "NULL"}}"""

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
    """Create a MinHash for a text string."""
    from datasketch import MinHash
    mh = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        mh.update(word.encode("utf-8"))
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
    minhash_cache[sig] = text
    return False, sig


# ── LLM calling ─────────────────────────────────────────────────────────────

def call_llm(prompt: str, system: str, model: str, provider: str = "omlx") -> dict | None:
    """Call LLM for convergent extraction. Returns parsed JSON dict or None."""
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
        from pipeline.omlx_call import call_omlx_json
        return call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=max_tokens)
    except Exception as e:
        print(f"      ❌ LLM error: {e}")
        return None


# ── Main stage ─────────────────────────────────────────────────────────────

def run_stage2(
    provider: str = "omlx",
    only_convergent: bool = False,
    gate_enabled: bool = S2_GATE_ENABLED,
    gate_strict: bool = S2_GATE_STRICT,
) -> None:
    """Run Stage 2: Convergent principle extraction from clusters.

    Args:
        provider: "omlx" or "mlx" for LLM inference.
        only_convergent: Skip single-source clusters.
        gate_enabled: Enable gate enforcement.
        gate_strict: Force [] on NULL-route with content.
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Load taxonomy
    try:
        from pipeline.schemas import CANONICAL_DISCIPLINES, CANONICAL_DOMAINS
        disciplines: list[str] = list(CANONICAL_DISCIPLINES)
        domains: list[str] = list(CANONICAL_DOMAINS)
    except ImportError:
        disciplines = ["strategic thinking", "marketing", "design strategy", "software engineering",
                       "economics", "psychology", "business operations"]
        domains = ["business operations", "digital product", "marketing", "strategic thinking",
                   "engineering practice", "user experience", "creative technology"]

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

    # Health check
    if provider == "omlx":
        from pipeline.omlx_call import check_omlx_health
        if not check_omlx_health():
            print("❌ OMLX server is not responding.")
            sys.exit(1)

    print(f"🧠 Stage 2: Convergent Extraction — {len(target_clusters)} clusters")
    print(f"   Convergent (≥{MIN_CONVERGENT_BOOKS} books): {len(convergent)}")
    print(f"   Single-source: {len(single_source)} | Noise: {len(noise)}")
    print(f"   Provider: {provider} | Model: {GEN_MODEL} | temp=0.0")
    print(f"   Golden: {golden_total} examples | Gate: {'on' if gate_enabled else 'off'}")
    print(f"{'='*60}")

    # Dedup infrastructure
    lsh, minhash_ok = init_minhash_lsh()
    minhash_cache: dict = {}
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
            print(f"   📋 Resuming: {len(processed_ids)} clusters processed → {len(all_fbs)} FBs")
        except Exception:
            all_fbs = []
            processed_ids = set()

    # Process clusters
    for i, cluster in enumerate(target_clusters, 1):
        cid: str = cluster.get("cluster_id", f"cluster_{i}")
        if cid in processed_ids:
            continue

        is_conv: bool = cluster.get("is_convergent", False)
        book_count: int = cluster.get("source_diversity", len(cluster.get("source_books", [])))
        conv_tag: str = "🌐" if is_conv else "📖"
        print(f"  [{i}/{len(target_clusters)}] {conv_tag} {cid} "
              f"({cluster.get('size', 0)} segments, {book_count} books)", end=" ")

        start: float = time.time()

        # Build prompt
        prompt, evidence_passages = build_convergent_prompt(
            cluster, segments, disciplines, domains
        )

        # Call LLM with retry
        result: dict | None = None
        for attempt in range(S2_OMLX_RETRY + 1):
            try:
                result = call_llm(prompt, SYSTEM_PROMPT, GEN_MODEL, provider)
                if result is not None:
                    break
            except Exception as e:
                if attempt < S2_OMLX_RETRY:
                    time.sleep(2)
                    continue
                print(f"→ ❌ Failed after {S2_OMLX_RETRY + 1} attempts: {e}")

        if result is None:
            continue

        # Check for NULL route
        route: str = result.get("route", "FB").strip().upper()
        if route == "NULL":
            total_null += 1
            print(f"→ ⏭️  NULL ({time.time() - start:.1f}s)")
            processed_ids.add(cid)
            continue

        # Validate required fields
        name: str = result.get("name", "").strip()
        definition: str = result.get("definition", "").strip()
        mechanism: str = result.get("mechanism", "").strip()
        boundary: str = result.get("boundary", "").strip()
        consequence: str = result.get("consequence", "").strip()
        is_summary: bool = result.get("is_summary", False)

        if not name or not definition or len(definition) < 30:
            print(f"→ ⚠️  Incomplete (name={bool(name)}, def_len={len(definition)})")
            total_null += 1
            processed_ids.add(cid)
            continue

        # Gate: reject summaries
        if is_summary and gate_enabled:
            total_gate_violations += 1
            print("→ 🚫 Self-flagged as summary, skipping")
            processed_ids.add(cid)
            continue

        # Build FB record
        fb_id: str = make_hash_id(name, definition)
        fb: dict = {
            "fb_id": fb_id,
            "name": name,
            "definition": definition,
            "mechanism": mechanism,
            "boundary": boundary,
            "consequence": consequence,
            "is_summary": is_summary,
            "evidence_passages": result.get("evidence_passages", evidence_passages[:5]),
            "evidence_passages_shown": evidence_passages,  # BUG-045 fix: what LLM actually saw (5-15), not all cluster segments
            "depth": result.get("depth", "domain"),
            "discipline": result.get("discipline", "emerging"),
            "domain": result.get("domain", ["emerging"]),
            "evidence": result.get("evidence", "cited"),
            "route": route,
            "source_cluster": cid,
            "source_books": cluster.get("source_books", []),
            "source_segments": cluster.get("segment_ids", []),
            "cluster_cohesion": cluster.get("cohesion", 0.0),
            "cluster_size": cluster.get("size", 0),
            "source_diversity": book_count,
            "is_convergent": is_conv,
        }
        fb = stamp_record(fb, gen_model=GEN_MODEL)
        fb["pipeline_commit"] = pipeline_commit

        # MinHash near-dedup
        if minhash_ok:
            is_dup, sig = is_near_duplicate(definition, lsh, minhash_cache)
            if is_dup:
                total_skipped += 1
                print("→ 🗑️  Near-duplicate, skipping")
                processed_ids.add(cid)
                continue
            fb["minhash_signature"] = sig

        all_fbs.append(fb)
        total_extracted += 1
        processed_ids.add(cid)

        elapsed: float = time.time() - start
        depth_tag: str = result.get("depth", "?")[:1].upper()
        sum_tag: str = "⚠️SUM" if is_summary else ""
        print(f"→ ✅ '{name[:40]}' {depth_tag} {sum_tag} ({elapsed:.1f}s)")

        # Incremental checkpoint every 5 clusters
        if i % 5 == 0 or i == len(target_clusters):
            safe_write(
                STAGE2_CHECKPOINT,
                "\n".join(json.dumps(f, ensure_ascii=False) for f in all_fbs) + "\n",
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


def main() -> None:
    """CLI entry point."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stage 2: Convergent principle extraction from clusters"
    )
    parser.add_argument("--only-convergent", action="store_true",
                        help="Skip single-source clusters (extract only from ≥2 book clusters)")
    parser.add_argument("--provider", choices=["omlx", "mlx"], default="omlx",
                        help="LLM provider (default: omlx)")
    parser.add_argument("--no-gate", action="store_true",
                        help="Disable gate enforcement (debug only)")
    args: argparse.Namespace = parser.parse_args()

    run_stage2(
        provider=args.provider,
        only_convergent=args.only_convergent,
        gate_enabled=not args.no_gate,
    )


if __name__ == "__main__":
    main()
