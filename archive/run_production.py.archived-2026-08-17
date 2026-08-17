#!/usr/bin/env python3
"""
run_production.py — Full Pipeline Production Run (Domain-by-Domain).
====================================================================
D2127r5: Skips FAISS (Stage 1.5) bottleneck. Uses per-book extraction
with Stage 4 cross-FB relationship computation. Proven by full_run.py.

Pipeline:
  S1: Already done (289K segments in checkpoint)
  S2: Extract FBs per book via OMLX (with golden few-shot)
  S4: D2138 classify + D2139 depth + compute relationships
  S6b: Export Obsidian + Anytype payloads
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    BOOKS_DIR,
    CHECKPOINT_DIR,
    GEN_MODEL,
)
from pipeline.stage1_chunk import chunk_text, split_on_headings
from pipeline.stage2_extract import (
    S2_GOLDEN_INJECT,
    S2_GOLDEN_MAX,
    S2_GOLDEN_NEGATIVE,
    S2_GOLDEN_PATH,
    S2_GOLDEN_POSITIVE,
    SYSTEM_PROMPT,
    build_convergent_prompt,
    call_llm,
    format_golden_fewshot,
    load_golden_parity,
)

# ── Config ──────────────────────────────────────────────────────────────────

DOMAINS: list[str] = [
    "DOMAIN 2 Design",
    "DOMAIN 6 AI + Computing",
    "DOMAIN 0 Systems + Decision",
    "DOMAIN 4 Business",
    "DOMAIN 1 Substrate — Mind, Math, Meaning",
    "DOMAIN 3 Art + Computational Media",
    "DOMAIN 5 Personal Practice",
    "DOMAIN 7 Influence + Power",
]

OUTPUT_DIR: Path = CHECKPOINT_DIR.parent / "production_run"
MAX_BOOKS_PER_DOMAIN: int | None = 5  # None = all books

# ── Stage 2: Extract FBs per book ───────────────────────────────────────────

def extract_fbs_per_domain(domain: str, few_shot: str) -> list[dict]:
    """Extract FBs from all books in a domain."""
    domain_path = BOOKS_DIR / domain
    md_files = sorted(domain_path.rglob("*.md"))

    if MAX_BOOKS_PER_DOMAIN:
        md_files = md_files[:MAX_BOOKS_PER_DOMAIN]

    print(f"\n{'='*60}")
    print(f"DOMAIN: {domain} ({len(md_files)} books)")
    print(f"{'='*60}")

    all_fbs: list[dict] = []

    for i, md_path in enumerate(md_files, 1):
        book_name = md_path.name
        print(f"  [{i}/{len(md_files)}] {book_name[:60]}...", end=" ", flush=True)

        try:
            with open(md_path, encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"SKIP (read error: {e})")
            continue

        # Chunk into sections
        sections = split_on_headings(text)
        if not sections:
            print("SKIP (no sections)")
            continue

        # Build a synthetic "cluster" per book (single-source, is_convergent=False)
        segments: list[dict] = []
        for heading, body, title in sections:
            if body.strip():
                for chunk_body, _, _ in chunk_text(body):
                    segments.append({"text": chunk_body, "source_book": book_name})

        if len(segments) < 2:
            print("SKIP (too few segments)")
            continue

        cluster = {
            "cluster_id": f"book:{book_name}",
            "segment_ids": [f"{book_name}_p{j}" for j in range(len(segments))],
            "source_books": [book_name],
            "source_diversity": 1,
            "size": len(segments),
            "cohesion": 0.5,
            "is_convergent": False,
        }

        # Build prompt + call LLM
        prompt, evidence = build_convergent_prompt(
            cluster, {s["text"]: s for s in segments}  # simplified
        )

        # Simplified: direct prompt building
        texts_display = "\n | ".join(s["text"][:300] for s in segments[:10])
        prompt = f"""I have {len(segments)} passages from 1 book: {book_name}

{"─" * 40}
{texts_display}
{"─" * 40}

Extract up to 3 convergent principles from this book. Return JSON list: [{{"name":"...", "definition":"...", "mechanism":"...", "boundary":"...", "consequence":"...", "is_summary":false, "evidence_passages":["..."], "route":"FB"}}]

No principle → [{{"route":"NULL"}}]"""

        start = time.time()
        try:
            result = call_llm(prompt, SYSTEM_PROMPT, GEN_MODEL, "omlx",
                            few_shot=few_shot if few_shot else None)
        except Exception as e:
            print(f"LLM FAIL ({e})")
            continue

        elapsed = time.time() - start

        # Parse result
        if result is None:
            print(f"NULL ({elapsed:.1f}s)")
            continue

        if isinstance(result, dict):
            result = [result]

        book_fbs = 0
        for fb in result:
            route = fb.get("route", "FB")
            if route == "NULL" or not fb.get("name"):
                continue
            fb["source_book"] = book_name
            fb["source_cluster"] = cluster["cluster_id"]
            fb["source_segments"] = cluster["segment_ids"]
            fb["source_diversity"] = 1
            fb["is_convergent"] = False
            all_fbs.append(fb)
            book_fbs += 1

        print(f"{book_fbs} FBs ({elapsed:.1f}s)")
        sys.stdout.flush()

    print(f"  TOTAL: {len(all_fbs)} FBs from {len(md_files)} books")
    return all_fbs


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load golden few-shot
    few_shot = ""
    if S2_GOLDEN_INJECT:
        pos, neg, _ = load_golden_parity(S2_GOLDEN_PATH, S2_GOLDEN_POSITIVE,
                                           S2_GOLDEN_NEGATIVE, S2_GOLDEN_MAX)
        if pos:
            few_shot = format_golden_fewshot(pos, neg)
            print(f"🎯 Golden few-shot: {len(pos)} pos + {len(neg)} neg injected")

    # Stage 2: Extract per domain
    all_fbs: list[dict] = []
    for domain in DOMAINS:
        fbs = extract_fbs_per_domain(domain, few_shot)
        all_fbs.extend(fbs)

        # Save intermediate checkpoint
        domain_checkpoint = OUTPUT_DIR / f"fbs_{domain.replace(' ', '_')}.json"
        with open(domain_checkpoint, 'w') as f:
            json.dump(fbs, f, ensure_ascii=False, indent=2)

    # Save all FBs
    all_checkpoint = OUTPUT_DIR / "all_fbs_stage2.json"
    with open(all_checkpoint, 'w') as f:
        json.dump(all_fbs, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"STAGE 2 COMPLETE: {len(all_fbs)} FBs across {len(DOMAINS)} domains")
    print(f"Output: {all_checkpoint}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
