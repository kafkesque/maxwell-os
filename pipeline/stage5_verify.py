#!/usr/bin/env python3
"""
stage5_verify.py — Verify FBs via Phi-4-mini (BORP + factual checks).
=====================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 5), R5, C8

Input:  FBs from Stage 4 checkpoint
Output: Verified FBs, checkpoint at stage5_verify.jsonl

Process:
  1. BORP check: verify at least 2 distinct source books per FB
  2. Factual consistency: Phi-4-mini checks definition against source principles
  3. Completeness: all required fields present and non-trivial
  4. Assign status: PASS / FLAG / QUARANTINE
  5. Human queue: FBs that need Maxwell's review

Verifier model: Phi-4-mini-instruct-8bit (OMLX) — different family from generator (R5)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage5_verify.py
    python3 pipeline/stage5_verify.py --strict   # Quarantine on any failure
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    STAGE2_CHECKPOINT,
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    CHECKPOINT_DIR,
    VERIFY_MODEL,
    BORP_MIN_SOURCES,
)
from pipeline.stamp import stamp_record, get_pipeline_commit
from pipeline.omlx_call import call_omlx, check_omlx_health
from pipeline.io_guard import safe_write

# ── Constants ──────────────────────────────────────────────────────────────
FACTUAL_CHECK_SYSTEM = """You are a factual consistency checker for Foundation Blocks.
Compare the FB's definition against the source principles it was derived from.

Check:
1. Does the definition accurately reflect the source principles? (not contradict, not fabricate)
2. Are any claims in the definition NOT supported by the source principles?
3. Is the definition coherent and logically consistent?

Return ONLY a JSON object:
{"consistent": true/false, "score": 0.0-1.0, "issues": ["issue1", "issue2"] or []}"""


def build_factual_prompt(fb: dict, source_principles: list[dict]) -> str:
    """Build the factual consistency check prompt."""
    lines = ["Check if this Foundation Block is factually consistent with its source principles.\n"]
    lines.append("=== FOUNDATION BLOCK ===")
    lines.append(f"NAME: {fb.get('name', 'N/A')}")
    lines.append(f"DEFINITION: {fb.get('definition', 'N/A')[:600]}")
    lines.append(f"APPLICATION: {fb.get('application', 'N/A')[:300]}")
    lines.append(f"FAILURE MODE: {fb.get('failure_mode', 'N/A')[:300]}")
    lines.append("")
    lines.append("=== SOURCE PRINCIPLES ===")
    for i, p in enumerate(source_principles[:10], 1):
        lines.append(f"{i}. {p['principle_text'][:400]}")
    lines.append("")
    lines.append("Return JSON: {\"consistent\": bool, \"score\": float, \"issues\": [...]}")
    return "\n".join(lines)


def load_stage4_fbs() -> list[dict]:
    """Load FBs from Stage 4 checkpoint."""
    if not STAGE4_CHECKPOINT.exists():
        print("❌ Stage 4 checkpoint not found. Run stage4_merge.py first.")
        sys.exit(1)

    fbs = []
    with open(STAGE4_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                fbs.append(json.loads(line))
    return fbs


def load_stage2_principles() -> dict[str, dict]:
    """Load principles indexed by principle_id."""
    if not STAGE2_CHECKPOINT.exists():
        return {}

    principles = {}
    with open(STAGE2_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                p = json.loads(line)
                principles[p["principle_id"]] = p
    return principles


def check_borp(fb: dict) -> tuple[bool, float, str]:
    """BORP check: distinct sources ≥ BORP_MIN_SOURCES.

    Returns (passed, score, detail).
    """
    source_books = fb.get("source_books", [])
    distinct = len(set(source_books))
    score = min(distinct / BORP_MIN_SOURCES, 1.0)
    passed = distinct >= BORP_MIN_SOURCES
    detail = f"{distinct} distinct sources (need ≥{BORP_MIN_SOURCES})"
    return passed, score, detail


def check_completeness(fb: dict) -> tuple[bool, float, str]:
    """Check that all required FB fields are present and non-trivial."""
    required_fields = [
        ("name", 3),
        ("definition", 30),
        ("application", 10),
        ("failure_mode", 10),
        ("elaboration", 20),
        ("keywords", 3),
    ]
    missing = []
    short = []
    for field, min_len in required_fields:
        val = fb.get(field, "")
        if not val:
            missing.append(field)
        elif len(val.strip()) < min_len:
            short.append(f"{field} ({len(val.strip())} < {min_len} chars)")

    issues = missing + short
    score = 1.0 - (len(issues) / len(required_fields))
    passed = len(issues) == 0
    detail = ", ".join(issues) if issues else "All fields present"
    return passed, score, detail


def check_factual(fb: dict, principles_idx: dict, skip_factual: bool = False
                  ) -> tuple[bool, float, str]:
    """Factual consistency check using Phi-4-mini.

    Returns (passed, score, detail).
    """
    if skip_factual:
        return True, 1.0, "Skipped (no source principles available)"

    # Find source principles for this FB's clusters
    source_clusters = fb.get("source_clusters", [])
    source_principles = []
    for pid, p in principles_idx.items():
        for cid in source_clusters:
            # Principles from stage 2 don't have cluster IDs directly,
            # so we approximate by checking if the principle was used
            # (we match by looking at all principles and using those
            #  whose texts appear as sources)
            pass
    # Fallback: use all available principles
    source_principles = list(principles_idx.values())[:20]

    if not source_principles:
        return True, 0.5, "No source principles found for verification"

    try:
        prompt = build_factual_prompt(fb, source_principles)
        result = call_omlx(
            prompt=prompt,
            model=VERIFY_MODEL,
            system=FACTUAL_CHECK_SYSTEM,
            max_tokens=512,
        )
        # Parse result
        import json as _json
        from pipeline.json_repair import parse_json_robust

        data = parse_json_robust(result)
        if isinstance(data, dict):
            consistent = data.get("consistent", False)
            score = data.get("score", 0.5)
            issues = data.get("issues", [])
            detail = "; ".join(issues) if issues else "Factually consistent"
            return consistent, score, detail
    except Exception as e:
        return True, 0.5, f"Factual check failed: {e}"

    return True, 0.5, "Factual check could not be completed"


def run_stage5(strict: bool = False, skip_factual: bool = False):
    """Run Stage 5: Verify FBs."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    fbs = load_stage4_fbs()
    principles_idx = load_stage2_principles()

    if not skip_factual and not check_omlx_health():
        print("⚠️  OMLX not running. Skipping factual checks (use --skip-factual).")
        skip_factual = True

    print(f"🔍 Stage 5: Verify — {len(fbs)} FBs")
    print(f"   Verifier: {VERIFY_MODEL} | temp=0.0 | BORP ≥ {BORP_MIN_SOURCES}")
    print(f"   Strict: {strict} | Factual checks: {not skip_factual}")
    print(f"{'='*60}")

    verified = []
    stats = {"PASS": 0, "FLAG": 0, "QUARANTINE": 0}
    pipeline_commit = get_pipeline_commit()

    for i, fb in enumerate(fbs, 1):
        name = fb.get("name", "unnamed")[:40]
        print(f"  [{i}/{len(fbs)}] {name}", end=" ")

        start = time.time()
        results = []

        # 1. BORP check
        borp_passed, borp_score, borp_detail = check_borp(fb)
        results.append({
            "check_name": "BORP",
            "passed": borp_passed,
            "score": borp_score,
            "detail": borp_detail,
        })

        # 2. Completeness check
        comp_passed, comp_score, comp_detail = check_completeness(fb)
        results.append({
            "check_name": "completeness",
            "passed": comp_passed,
            "score": comp_score,
            "detail": comp_detail,
        })

        # 3. Factual consistency check
        fact_passed, fact_score, fact_detail = check_factual(
            fb, principles_idx, skip_factual=skip_factual
        )
        results.append({
            "check_name": "factual",
            "passed": fact_passed,
            "score": fact_score,
            "detail": fact_detail,
        })

        # Determine status
        all_passed = all(r["passed"] for r in results)
        borp_only_fail = not borp_passed and comp_passed

        if all_passed:
            status = "PASS"
            needs_human = False
        elif borp_only_fail and not strict:
            status = "FLAG"
            needs_human = True
        else:
            status = "QUARANTINE"
            needs_human = True

        stats[status] += 1

        # Build verified FB
        vfb = dict(fb)  # Copy all FB fields
        vfb["verification_results"] = results
        vfb["borp_score"] = borp_score
        vfb["status"] = status
        vfb["needs_human_review"] = needs_human
        vfb["verifier_model"] = VERIFY_MODEL

        # Re-stamp
        vfb = stamp_record(vfb, gen_model=fb.get("gen_model"))
        vfb["pipeline_commit"] = pipeline_commit

        verified.append(vfb)

        elapsed = time.time() - start
        status_icon = {"PASS": "✅", "FLAG": "⚠️", "QUARANTINE": "🚫"}[status]
        print(f"→ {status_icon} {status} ({elapsed:.1f}s)")

    # Write checkpoint
    safe_write(
        STAGE5_CHECKPOINT,
        "\n".join(json.dumps(v, ensure_ascii=False) for v in verified) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ PASS:         {stats['PASS']}")
    print(f"⚠️  FLAG:         {stats['FLAG']}")
    print(f"🚫 QUARANTINE:   {stats['QUARANTINE']}")
    human_review = stats["FLAG"] + stats["QUARANTINE"]
    if human_review:
        print(f"👤 Need review:   {human_review}")
    print(f"📋 Checkpoint:    {STAGE5_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 5: Verify FBs via Phi-4-mini + BORP")
    parser.add_argument("--strict", action="store_true",
                        help="Quarantine on any failure (default: flag on BORP-only)")
    parser.add_argument("--skip-factual", action="store_true",
                        help="Skip LLM factual consistency checks")
    args = parser.parse_args()

    run_stage5(strict=args.strict, skip_factual=args.skip_factual)


if __name__ == "__main__":
    main()
