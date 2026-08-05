#!/usr/bin/env python3
"""
stage5_verify.py — Verify FBs via ModernBERT NLI pre-filter + Gemma-4-E4B deep check.
==================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 5), R5, C8, D2069

Input:  FBs from Stage 4 checkpoint (with embedded source_principles)
Output: Verified FBs, checkpoint at stage5_verify.jsonl

Process:
  1. BORP check: verify at least 2 distinct source books per FB
  2. Completeness: all required fields present and non-trivial
  3. DeBERTa NLI entailment: fast entailment check (definition ↔ evidence_passages)
     → ENTAILMENT + ≥0.6 = PASS (skip LLM)
     → CONTRADICTION = FAIL → escalate to Gemma-4-E4B
     → NEUTRAL = FLAG → escalate to Gemma-4-E4B
  4. FAIL-CLOSED (D2093): any check failure → QUARANTINE, never PASS
  5. Assign status: PASS / FLAG / QUARANTINE

R5 compliance (D2069):
  Generator: Qwen3.6-35B (Qwen family) — Stage 2, 4 Phase 1
  Classifier: Phi-4-mini-8bit (Phi family) — Stage 4 Phase 2
  Verifier:   Gemma-4-E4B (Gemma family) — Stage 5
  Three different families. No model reviews its own output.

DeBERTa model: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli (362MB, already on disk)
  Benchmarks: MNLI 90.3%, FEVER 89.1%, ANLI 62.4%
  Speed: ~50ms per sentence pair on CPU (M1 Max)

Usage:
    python3 pipeline/stage5_verify.py
    python3 pipeline/stage5_verify.py --strict   # Quarantine on any failure
    python3 pipeline/stage5_verify.py --skip-nli  # Skip DeBERTa, use LLM for all
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.schema_accessor import (
    fb_boundary,
    fb_consequence,
    fb_definition,
    fb_mechanism,
    fb_name,
    fb_source_books,
    fb_source_texts,
    fb_source_texts_shown,
)
from pipeline.pipeline_paths import (
    BORP_MIN_SOURCES,
    CHECKPOINT_DIR,
    S5_BORP_BYPASS_TYPES,  # D2083: types that skip BORP check
    S5_NLI_ENTAILMENT_THRESHOLD,  # D2119: configurable NLI threshold
    S5_NLI_MODEL,  # D2119: primary NLI model (ModernBERT)
    S5_NLI_MODEL_FALLBACK,  # D2119: fallback NLI model (DeBERTa)
    S5_NLI_PASS_THRESHOLD,  # D2155: NLI score threshold for PASS (skip LLM)
    S5_NLI_MARGINAL_THRESHOLD,  # D2155: NLI score threshold for FLAG (escalate)
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    VERIFY_MODEL_V2,  # D2069: cross-family verifier (Gemma-4-E4B)
)
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
NLI_ENTAILMENT_THRESHOLD: float = S5_NLI_ENTAILMENT_THRESHOLD  # D2119: from config (default 0.6)
NLI_PASS_THRESHOLD: float = S5_NLI_PASS_THRESHOLD  # D2155: from config (default 0.8)
NLI_MARGINAL_THRESHOLD: float = S5_NLI_MARGINAL_THRESHOLD  # D2155: from config (default 0.5)
# ── NLI Model — config-driven with automatic fallback (D2119) ────────────
# Primary: ModernBERT-base-nli (~64ms, 8192 ctx, 90% MNLI accuracy)
# Fallback: DeBERTa-v3-base-mnli-fever-anli (~129ms, 512 ctx, 90% MNLI + FEVER)
# If primary model fails to load (missing, OOM, etc.), falls back automatically.

_nli_pipeline = None
_nli_model_loaded: str = ""


def _get_nli():
    """Lazy-load NLI model for entailment scoring.

    D2119: Switched primary from DeBERTa-v3 to ModernBERT-base-nli.
    ModernBERT is 2× faster (64ms vs 129ms), has 16× larger context (8192 vs 512),
    and achieves equal accuracy (90% on 20-pair manual test).
    DeBERTa kept as automatic fallback if ModernBERT can't load.
    Model configured in pipeline_config.yaml → stage5.nli_model.
    """
    global _nli_pipeline, _nli_model_loaded
    if _nli_pipeline is not None:
        return _nli_pipeline

    from transformers import pipeline

    # Try primary model first
    primary = S5_NLI_MODEL
    fallback = S5_NLI_MODEL_FALLBACK

    try:
        print(f"   🧠 Loading NLI model: {primary}...")
        _nli_pipeline = pipeline(
            "text-classification",
            model=primary,
            device=-1,
        )
        _nli_model_loaded = primary
        print(f"   ✅ NLI: {primary}")
        return _nli_pipeline
    except Exception as e:
        print(f"   ⚠️  Primary NLI model failed: {e}")
        print(f"   🔄 Falling back to: {fallback}...")
        try:
            _nli_pipeline = pipeline(
                "text-classification",
                model=fallback,
                device=-1,
            )
            _nli_model_loaded = fallback
            print(f"   ✅ NLI (fallback): {fallback}")
            return _nli_pipeline
        except Exception as e2:
            raise RuntimeError(
                f"Both NLI models failed to load.\n"
                f"  Primary: {primary} → {e}\n"
                f"  Fallback: {fallback} → {e2}"
            )


def nli_entailment(claim: str, source: str) -> dict:
    """Score entailment: does source text entail the claim?

    Returns {'label': 'ENTAILMENT'|'NEUTRAL'|'CONTRADICTION', 'score': 0.0-1.0}
    """
    nli = _get_nli()
    source = source[:1024] if len(source) > 1024 else source
    # D2151: NLI models require premise/hypothesis PAIR format, not single concatenated string
    result = nli({"text": source, "text_pair": claim})
    top = result[0] if isinstance(result, list) else result
    return {"label": top.get("label", "UNKNOWN").upper(), "score": round(top.get("score", 0.0), 4)}


# ── Prompt templates ───────────────────────────────────────────────────────

FACTUAL_CHECK_SYSTEM = """You are a factual consistency checker for Foundation Blocks.
Compare the FB's definition against its EVIDENCE PASSAGES (verbatim source text).

Check:
1. Does the definition accurately reflect the evidence passages? (not contradict, not fabricate)
2. Are any claims in the definition NOT supported by the evidence passages?
3. Is the definition coherent and logically consistent WITH the evidence?

Return ONLY a JSON object:
{"consistent": true/false, "score": 0.0-1.0, "issues": ["issue1", "issue2"] or []}"""


# ── NLI evidence check (D2093: replaces embedding similarity) ──────────────

def nli_evidence_check(fb: dict) -> tuple[bool, float, str]:
    """DeBERTa NLI entailment: compare FB definition against verbatim evidence passages.

    v3.0 (D2093, D2104): Replaces embedding_similarity_check() which measured
    topical closeness (cosine similarity), not factual entailment. DeBERTa MNLI
    works correctly with verbatim evidence_passages from convergent extraction.

    Returns (passed, confidence, detail).
    """
    # BUG-045 fix: prefer evidence_passages_shown (what LLM actually saw, 5-15 passages)
    # over evidence_passages (what LLM chose to return, up to 5) for NLI verification.
    evidence_passages: list[str] = fb_source_texts_shown(fb)
    if not evidence_passages:
        evidence_passages = fb_source_texts(fb)
    if not evidence_passages:
        # Fallback: try source_principles (v2.2 checkpoint compatibility)
        source_principles: list[dict] = fb.get("source_principles", [])
        if source_principles:
            evidence_passages = [p.get("principle_text", "") for p in source_principles if p.get("principle_text")]
        else:
            return False, 0.0, "No evidence_passages or source_principles — QUARANTINE"

    definition: str = fb_definition(fb)
    if not definition or len(definition) < 20:
        return False, 0.0, "No definition — QUARANTINE"

    try:
        results: list[dict] = []
        for passage in evidence_passages[:8]:  # Max 8 passages for speed
            if not passage.strip():
                continue
            result: dict = nli_entailment(definition, passage)
            results.append(result)

        if not results:
            return False, 0.0, "No valid evidence passages to check — QUARANTINE"

        # Score: % of passages that entail vs contradict the definition.
        # D2094 revised: CONTRADICTION = fail, NEUTRAL = pass-to-LLM, ENTAILMENT = strong pass.
        entailments: int = sum(1 for r in results if r["label"] == "ENTAILMENT" and r["score"] >= 0.6)
        contradictions: int = sum(1 for r in results if r["label"] == "CONTRADICTION" and r["score"] >= 0.6)
        neutrals: int = len(results) - entailments - contradictions

        nli_entail_score: float = entailments / len(results) if results else 0.0
        nli_contra_score: float = contradictions / len(results) if results else 0.0

        if nli_contra_score >= 0.5:
            # Majority contradict → strong failure
            passed: bool = False
            nli_score: float = 0.0
            detail: str = f"NLI FAIL: {contradictions}/{len(results)} contradictions — evidence contradicts claim"
        elif nli_entail_score >= 0.5:
            # Majority entail → strong pass (skip LLM)
            passed = True
            nli_score = nli_entail_score
            detail = f"NLI PASS: {entailments}/{len(results)} entailments (≥0.6 confidence)"
        else:
            # Mixed/neutral → pass to LLM for deeper check (score < 0.5 triggers escalation)
            passed = True
            nli_score = 0.4  # Below 0.5 threshold → triggers LLM escalation in run_stage5
            detail = f"NLI NEUTRAL: {entailments}E/{neutrals}N/{contradictions}C — escalate to LLM"

        return passed, nli_score, detail

    except Exception as e:
        return False, 0.0, f"NLI check error — QUARANTINE: {e}"


# ── Core verification functions ────────────────────────────────────────────

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


def build_factual_prompt(fb: dict) -> str:
    """Build factual consistency prompt using embedded source_principles.

    D2069: Uses fb['source_principles'] directly — no checkpoint lookups needed.
    """
    lines = ["Check if this Foundation Block is factually consistent with its source evidence.\n"]
    lines.append("=== FOUNDATION BLOCK ===")
    lines.append(f"NAME: {fb.get('name', 'N/A')}")
    lines.append(f"DEFINITION: {fb.get('definition', 'N/A')[:600]}")
    lines.append(f"MECHANISM: {fb.get('mechanism', fb.get('application', 'N/A'))[:300]}")
    lines.append(f"BOUNDARY: {fb.get('boundary', fb.get('failure_mode', 'N/A'))[:300]}")
    lines.append(f"CONSEQUENCE: {fb.get('consequence', fb.get('elaboration', 'N/A'))[:300]}")
    lines.append("")
    # D2094: Use evidence_passages (v3.0) or source_principles (v2.x)
    sources: list[str] = []
    if fb.get("evidence_passages"):
        sources = [str(p) for p in fb["evidence_passages"][:10]]
        lines.append("=== EVIDENCE PASSAGES ===")
    else:
        source_principles = fb.get("source_principles", [])
        sources = [p.get('principle_text', '')[:400] for p in source_principles[:10]]
        lines.append("=== SOURCE PRINCIPLES ===")
    for i, src in enumerate(sources, 1):
        lines.append(f"{i}. {str(src)[:400]}")
    lines.append("")
    lines.append("Return JSON: {\"consistent\": bool, \"score\": float, \"issues\": [...]}")
    return "\n".join(lines)


def check_borp(fb: dict, bypass_types: list[str] = S5_BORP_BYPASS_TYPES) -> tuple[bool, float, str]:
    """BORP check: distinct sources ≥ BORP_MIN_SOURCES.

    D2083: Types in bypass_types skip BORP entirely.
    process_template, process_instance, growth_edge, tool_instruction don't need
    cross-source convergence — they're methods, evidence, speculations, and commands.
    """
    content_type = fb.get("content_type", "principle")

    # D2083: Type-aware bypass
    if content_type in bypass_types:
        return True, 1.0, f"BORP bypassed (type={content_type})"

    source_books: list[str] = fb_source_books(fb)
    distinct: int = len(set(source_books))
    score = min(distinct / BORP_MIN_SOURCES, 1.0)
    passed = distinct >= BORP_MIN_SOURCES
    detail = f"{distinct} distinct sources (need ≥{BORP_MIN_SOURCES})"
    return passed, score, detail


def check_completeness(fb: dict) -> tuple[bool, float, str]:
    """Check that all required FB fields are present and non-trivial.

    D2094: Uses v3.0 schema (mechanism/boundary/consequence) or v2.x fallback fields.
    """
    # v3.0 schema fields first, v2.x as fallback
    has_mechanism = bool(fb.get("mechanism") or fb.get("application"))
    has_boundary = bool(fb.get("boundary") or fb.get("failure_mode"))
    has_consequence = bool(fb.get("consequence") or fb.get("elaboration"))

    required_fields: list[tuple[str, int]] = [
        ("name", 3),
        ("definition", 30),
    ]
    missing: list[str] = []
    short: list[str] = []
    for field, min_len in required_fields:
        val = fb.get(field, "")
        if not val:
            missing.append(field)
        elif len(val.strip()) < min_len:
            short.append(f"{field} ({len(val.strip())} < {min_len} chars)")

    # D2094: Check v3.0 structural fields
    if not has_mechanism:
        missing.append("mechanism/application")
    if not has_boundary:
        missing.append("boundary/failure_mode")
    if not has_consequence:
        missing.append("consequence/elaboration")

    total_checks = len(required_fields) + 3  # name + def + 3 structural
    issues = missing + short
    score = max(0.0, 1.0 - (len(issues) / total_checks))
    passed = len(issues) == 0
    detail = ", ".join(issues) if issues else "All fields present"
    return passed, score, detail


def check_factual_llm(fb: dict, model: str) -> tuple[bool, float, str]:
    """Deep factual check using LLM (Gemma-4-E4B, cross-family).

    D2069: Only called when NLI pre-filter fails (~30% of FBs).
    D2094: Uses evidence_passages (v3.0) or source_principles (v2.x) — schema-adaptive.
    """
    source_principles = fb.get("source_principles", [])
    evidence_passages = fb.get("evidence_passages", [])
    if not source_principles and not evidence_passages:
        return False, 0.0, "No source principles or evidence passages — QUARANTINE (D2093: fail-closed)"

    if not check_omlx_health():
        return False, 0.0, "OMLX unavailable — QUARANTINE (D2093: fail-closed)"

    try:
        prompt = build_factual_prompt(fb)
        result = call_omlx_json(
            prompt=prompt,
            model=model,
            system=FACTUAL_CHECK_SYSTEM,
            max_tokens=512,
        )
        if isinstance(result, dict):
            consistent = result.get("consistent", False)
            score = result.get("score", 0.5)
            issues = result.get("issues", [])
            detail = "; ".join(issues) if issues else "LLM: factually consistent"
            return consistent, score, detail
    except Exception as e:
        return False, 0.0, f"LLM factual check error — QUARANTINE (D2093: fail-closed): {e}"

    return False, 0.0, "LLM check could not be completed — QUARANTINE (D2093: fail-closed)"


# ── Main ────────────────────────────────────────────────────────────────────

def run_stage5(strict: bool = False, skip_nli: bool = False):
    """Run Stage 5: Verify FBs with DeBERTa NLI pre-filter + Gemma-4-E4B."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    fbs = load_stage4_fbs()
    total = len(fbs)

    # Check models
    omlx_available = check_omlx_health()

    print(f"🔍 Stage 5: Verify — {total} FBs")
    print(f"   Verifier: {VERIFY_MODEL_V2} (cross-family, R5: Gemma ≠ Phi ≠ Qwen)")
    print(f"   Pre-filter: {'✅ ModernBERT NLI entailment' if not skip_nli else '❌ skipped'} (D2119)")
    print(f"   NLI model: {S5_NLI_MODEL} | Fallback: {S5_NLI_MODEL_FALLBACK}")
    print(f"   OMLX deep check: {'✅ available' if omlx_available else '❌ unavailable'}")
    print(f"   Strict: {strict} | NLI threshold: {NLI_ENTAILMENT_THRESHOLD} | Fail-closed: ✅ (D2093)")
    print(f"{'='*60}")

    verified = []
    stats = {"PASS": 0, "FLAG": 0, "QUARANTINE": 0}
    prefilter_stats = {"passed": 0, "failed": 0, "skipped": 0}
    llm_stats = {"called": 0, "skipped": 0}
    pipeline_commit = get_pipeline_commit()

    for i, fb in enumerate(fbs, 1):
        name = fb.get("name", "unnamed")[:40]
        has_sources = bool(fb.get("source_principles"))
        source_tag = "📦" if has_sources else "⚠️"
        print(f"  [{i}/{total}] {source_tag} {name}", end=" ")

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

        # 3. Factual consistency — DeBERTa NLI pre-filter → LLM deep check (D2093)
        fact_passed: bool = True
        fact_score: float = 1.0
        fact_detail: str = "No verification needed"
        method: str = "none"

        if not skip_nli:
            # D2093: DeBERTa NLI pre-filter (replaces embedding similarity)
            nli_passed, nli_score, nli_detail = nli_evidence_check(fb)
            if nli_passed and nli_score >= NLI_PASS_THRESHOLD:  # D2155: config threshold (default 0.8)
                prefilter_stats["passed"] += 1
                fact_passed = True
                fact_score = nli_score
                fact_detail = f"NLI PASS: {nli_detail}"
                method = "nli"
                llm_stats["skipped"] += 1
            elif nli_passed and nli_score >= NLI_MARGINAL_THRESHOLD:  # D2155: config threshold (default 0.5)
                prefilter_stats["passed"] += 1
                fact_passed = True
                fact_score = nli_score
                fact_detail = f"NLI FLAG (marginal): {nli_detail}"
                method = "nli"
            else:
                prefilter_stats["failed"] += 1
                # Escalate to LLM deep check (Gemma-4-E4B, cross-family)
                if omlx_available:
                    llm_stats["called"] += 1
                    fact_passed, fact_score, fact_detail = check_factual_llm(
                        fb, model=VERIFY_MODEL_V2
                    )
                    fact_detail = f"NLI FAIL → LLM: {fact_detail}"
                    method = "nli+LLM"
                else:
                    # D2093: fail-closed — no LLM available = QUARANTINE
                    fact_passed = False
                    fact_score = nli_score
                    fact_detail = f"NLI FAIL + OMLX unavailable — QUARANTINE: {nli_detail}"
                    method = "nli-only"
        else:
            prefilter_stats["skipped"] += 1
            if omlx_available:
                llm_stats["called"] += 1
                fact_passed, fact_score, fact_detail = check_factual_llm(
                    fb, model=VERIFY_MODEL_V2
                )
                fact_detail = f"LLM (direct, NLI skipped): {fact_detail}"
                method = "LLM"
            else:
                fact_passed = False
                fact_score = 0.0
                fact_detail = "No verification — NLI skipped, OMLX unavailable — QUARANTINE"
                method = "none"

        results.append({
            "check_name": "factual",
            "passed": fact_passed,
            "score": fact_score,
            "detail": fact_detail,
        })

        # Determine status
        all_passed = all(r["passed"] for r in results)
        borp_only_fail = not borp_passed and comp_passed and fact_passed

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

        # ── Compute confidence_score (D2130 fix: was always None) ──────────
        # Weighted average of BORP (20%) + Completeness (10%) + Factual (70%)
        # Factual score carries more weight because it's the hardest check.
        confidence_score = round(
            0.20 * borp_score + 0.10 * comp_score + 0.70 * fact_score, 4
        )

        # Build verified FB
        vfb = dict(fb)
        vfb["verification_results"] = results
        vfb["borp_score"] = borp_score
        vfb["confidence_score"] = confidence_score
        vfb["status"] = status
        vfb["needs_human_review"] = needs_human
        vfb["verifier_model"] = VERIFY_MODEL_V2
        vfb["verification_method"] = method  # D2069: track which path was used

        vfb = stamp_record(vfb, gen_model=fb.get("gen_model"))
        vfb["pipeline_commit"] = pipeline_commit

        verified.append(vfb)

        elapsed = time.time() - start
        status_icon = {"PASS": "✅", "FLAG": "⚠️", "QUARANTINE": "🚫"}[status]
        nli_tag = {"nli": "⚡", "nli+LLM": "🔍", "LLM": "🤖", "none": "·"}[method]
        print(f"→ {status_icon} {status} {nli_tag} ({elapsed:.1f}s)")

    # Write checkpoint
    safe_write(
        STAGE5_CHECKPOINT,
        "\n".join(json.dumps(v, ensure_ascii=False) for v in verified) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print("📊 VERIFICATION RESULTS")
    print(f"   ✅ PASS:         {stats['PASS']}")
    print(f"   ⚠️  FLAG:         {stats['FLAG']}")
    print(f"   🚫 QUARANTINE:   {stats['QUARANTINE']}")
    human_review = stats["FLAG"] + stats["QUARANTINE"]
    if human_review:
        print(f"   👤 Need review:   {human_review}")
    print("")
    print("📊 EMBEDDING PRE-FILTER")
    print(f"   ⚡ NLI passed:    {prefilter_stats['passed']} (skipped LLM)")
    print(f"   🔍 NLI failed:    {prefilter_stats['failed']} (escalated to LLM)")
    print(f"   ·  Skipped:       {prefilter_stats['skipped']}")
    llm_saved = prefilter_stats['passed']
    if total > 0:
        print(f"   💰 LLM calls saved: {llm_saved}/{total} ({100*llm_saved/total:.0f}%)")
    print("")
    print(f"📋 Checkpoint:       {STAGE5_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(
        description="Stage 5: Verify FBs via DeBERTa NLI + Gemma-4-E4B"
    )
    parser.add_argument("--strict", action="store_true",
                        help="Quarantine on any failure (default: flag on BORP-only)")
    parser.add_argument("--skip-nli", action="store_true",
                        help="Skip DeBERTa NLI pre-filter, use LLM for all checks")
    args = parser.parse_args()

    run_stage5(strict=args.strict, skip_nli=args.skip_nli)


if __name__ == "__main__":
    main()
