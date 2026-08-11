#!/usr/bin/env python3
"""
stage5_verify.py — Verify FBs via DeBERTa FEVER NLI pre-filter + Phi-4-mini deep check (D2264).
==================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 5), R5, C8, D2069, D2255

Input:  FBs from Stage 4 checkpoint (with embedded source_principles)
Output: Verified FBs, checkpoint at stage5_verify.jsonl

Process:
  1. BORP check: verify at least 2 distinct source books per FB
  2. Completeness: all required fields present and non-trivial
  3. DeBERTa FEVER NLI entailment: fast claim-evidence verification (definition ↔ evidence_passages)
     D2255 (2026-08-11): DeBERTa FEVER is now PRIMARY (was ModernBERT).
     DeBERTa FEVER is 5.8× more discriminative on convergent FBs.
     ModernBERT returned NEUTRAL for all synthesized FBs — non-functional as pre-filter.
     → ENTAILMENT + ≥0.6 = PASS (skip LLM)
     → CONTRADICTION = FAIL → escalate to Phi-4-mini (D2264: 67% acc vs Gemma 33%)
     → NEUTRAL = FLAG → escalate to Phi-4-mini (D2264: 67% acc vs Gemma 33%)
  4. FAIL-CLOSED (D2093): any check failure → QUARANTINE, never PASS
  5. Assign status: PASS / FLAG / QUARANTINE

R5 compliance (D2069, D2250):
  Generator:  Qwen3-Coder-30B (Qwen/Alibaba) — Stage 2
  Classifier: GPT-OSS-20B (OpenAI) — Stage 4 (replaced Phi-4-mini per D2249/D2250)
  Verifier:   Gemma-4-E4B (Gemma/Google) — Stage 5 deep check
  NLI:        DeBERTa FEVER (Microsoft/FAIR) — Stage 5 pre-filter
  Four distinct families. No model reviews its own output.

DeBERTa FEVER model: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli (362MB)
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
from pipeline.pipeline_paths import (
    BORP_MIN_SOURCES,
    CHECKPOINT_DIR,
    S5_BORP_BYPASS_TYPES,  # D2083: types that skip BORP check
    S5_NLI_ENTAILMENT_THRESHOLD,  # D2119: configurable NLI threshold
    S5_NLI_MARGINAL_THRESHOLD,  # D2155: NLI score threshold for FLAG (escalate)
    S5_NLI_MODEL,  # D2119: primary NLI model (ModernBERT)
    S5_NLI_MODEL_FALLBACK,  # D2119: fallback NLI model (DeBERTa)
    S5_NLI_PASS_THRESHOLD,  # D2155: NLI score threshold for PASS (skip LLM)
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    VERIFY_MODEL_V2,  # D2069: cross-family verifier (Gemma-4-E4B)
)
from pipeline.schema_accessor import (
    fb_definition,
    fb_source_books,
    fb_source_ids,  # D2185: canonical SHA-256 author|title source_ids for BORP
    fb_source_texts,
    fb_source_texts_shown,
)
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
NLI_ENTAILMENT_THRESHOLD: float = S5_NLI_ENTAILMENT_THRESHOLD  # D2119: from config (default 0.5)
NLI_PASS_THRESHOLD: float = S5_NLI_PASS_THRESHOLD  # D2155: from config (default 0.6)
# D2226 (Kimi audit fix): Was hardcoded 0.8 in nli_evidence_check, now reads from config.
# Config declares 0.6 pass / 0.5 entailment / 0.3 marginal. Hardcoded 0.8 overrode
# the more permissive config, forcing unnecessary LLM escalation.
NLI_MARGINAL_THRESHOLD: float = S5_NLI_MARGINAL_THRESHOLD  # D2155: from config (default 0.3)
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

    import torch
    from transformers import pipeline

    # D2178: Auto-detect device — MPS (Apple Silicon), CUDA, or CPU fallback.
    # Previously hardcoded device=-1 (CPU only). MPS provides 5-10× speedup
    # for NLI inference on Apple Silicon (C24: Hardware-Adaptive).
    if torch.backends.mps.is_available():
        nli_device: int | str = "mps"
        device_label: str = "MPS (Apple Silicon GPU)"
    elif torch.cuda.is_available():
        nli_device = 0
        device_label = "CUDA GPU"
    else:
        nli_device = -1
        device_label = "CPU"

    # Try primary model first
    primary = S5_NLI_MODEL
    fallback = S5_NLI_MODEL_FALLBACK

    try:
        print(f"   🧠 Loading NLI model: {primary} on {device_label}...")
        _nli_pipeline = pipeline(
            "text-classification",
            model=primary,
            device=nli_device,
        )
        _nli_model_loaded = primary
        print(f"   ✅ NLI: {primary} ({device_label})")
        return _nli_pipeline
    except Exception as e:
        print(f"   ⚠️  Primary NLI model failed: {e}")
        print(f"   🔄 Falling back to: {fallback}...")
        try:
            _nli_pipeline = pipeline(
                "text-classification",
                model=fallback,
                device=nli_device,
            )
            _nli_model_loaded = fallback
            print(f"   ✅ NLI (fallback): {fallback} ({device_label})")
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

        # Score: MAX-entailment — strongest signal wins (D2215: DeBERTa FEVER factuality).
        # D2226 (Kimi audit fix): Thresholds now config-driven, not hardcoded 0.8.
        # A single strong contradiction (≥NLI_PASS_THRESHOLD) fails regardless of other passages.
        # A single strong entailment (≥NLI_PASS_THRESHOLD) passes without escalation.
        max_entail: float = max((r["score"] for r in results if r["label"] == "ENTAILMENT"), default=0.0)
        max_contra: float = max((r["score"] for r in results if r["label"] == "CONTRADICTION"), default=0.0)

        if max_contra >= NLI_PASS_THRESHOLD:
            # Strong contradiction → fail-closed (D2093)
            passed: bool = False
            nli_score: float = 0.0
            detail: str = f"NLI FAIL: max contradiction {max_contra:.2f} — evidence contradicts claim"
        elif max_entail >= NLI_PASS_THRESHOLD:
            # Strong entailment → strong pass (skip LLM)
            passed = True
            nli_score = max_entail
            detail = f"NLI PASS: max entailment {max_entail:.2f} (strong signal)"
        else:
            # Weak/mixed signals → escalate to LLM
            passed = True
            nli_score = 0.4  # Below 0.5 threshold → triggers LLM escalation in run_stage5
            detail = f"NLI NEUTRAL: max_entail={max_entail:.2f} max_contra={max_contra:.2f} — escalate to LLM"

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

    source_books: list[str] = fb_source_ids(fb)  # D2185: canonical SHA-256 author|title (was fb_source_books)
    if not source_books:
        source_books = fb_source_books(fb)  # fallback: filenames (v2.x backward compat)
    distinct: int = len(set(source_books))
    score = min(distinct / BORP_MIN_SOURCES, 1.0)
    passed = distinct >= BORP_MIN_SOURCES
    detail = f"{distinct} distinct canonical sources (need ≥{BORP_MIN_SOURCES})"
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
    """Deep factual check using LLM (Phi-4-mini, cross-family).

    D2069: Only called when NLI pre-filter fails (~30% of FBs).
    D2094: Uses evidence_passages (v3.0) or source_principles (v2.x) — schema-adaptive.
    BUG-053 (D2268): Phi-4-mini hallucinates on open-ended tasks. STRICT guard:
    source text MUST be provided. Without it, auto-QUARANTINE (fail-closed).
    """
    source_principles = fb.get("source_principles", [])
    evidence_passages = fb.get("evidence_passages", [])

    # BUG-053 guard: Phi-4-mini MUST have source text to avoid hallucination
    has_source_text = bool(source_principles or evidence_passages)
    if not has_source_text:
        return False, 0.0, (
            "BUG-053 guard: No source text provided — Phi-4-mini requires "
            "evidence_passages or source_principles to avoid hallucination. "
            "QUARANTINE (D2093: fail-closed)."
        )

    # BUG-053 guard: verify source text has actual content (not just placeholders)
    all_text = ""
    for sp in (source_principles or []):
        all_text += str(sp.get("principle_text", sp if isinstance(sp, str) else ""))
    for ep in (evidence_passages or []):
        all_text += str(ep)
    if len(all_text.strip()) < 50:
        return False, 0.0, (
            f"BUG-053 guard: Source text too short ({len(all_text.strip())} chars). "
            "Phi-4-mini requires substantial source text to ground verification. "
            "QUARANTINE (D2093: fail-closed)."
        )

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


# ── Mechanism quality pre-filter (D2220: guards against citation echo gaming NLI) ──

# D2220: Citation echo detection thresholds — configurable via pipeline_config.yaml
# fallback defaults if config keys not present
MECHANISM_MIN_LENGTH: int = 150  # Minimum mechanism character length
CITATION_ECHO_SOURCE_THRESHOLD: int = 20  # Source count triggering citation echo check
BANNED_MECHANISM_PREFIXES: tuple[str, ...] = (
    "because it enables",
    "because it allows",
    "because it helps",
    "because it provides",
    "because it makes",
    "because it can",
)


def check_mechanism_quality(fb: dict) -> tuple[bool, float, str]:
    """Pre-filter: check mechanism quality before NLI to prevent citation echo gaming.

    D2220: When source count is high, MAX-entailment NLI is vulnerable to
    "at least one passage matches" — any vague mechanism with 20+ sources has
    a high probability of at least one passage having high entailment, creating
    false positives. This pre-filter catches low-quality mechanisms before they
    reach NLI.

    Checks:
      1. Mechanism minimum length (prevents vacuous one-liners)
      2. Non-tautological "because" clause (prevents definitional restatements)
      3. Citation echo override: high source count + axiomatic evidence = escalate

    Returns:
        (passed, score, detail). score=0.0 means auto-quarantine. score=0.5 means
        escalate to LLM regardless of NLI outcome.
    """
    mechanism = fb.get("mechanism", "").strip()
    source_books = fb.get("source_books", [])
    n_sources = len(source_books) if isinstance(source_books, list) else 0
    evidence = fb.get("evidence", "cited")

    # 1. Minimum mechanism length
    if len(mechanism) < MECHANISM_MIN_LENGTH:
        return False, 0.0, (
            f"Mechanism too short ({len(mechanism)} chars < {MECHANISM_MIN_LENGTH}) — "
            "likely vacuous. QUARANTINE."
        )

    # 2. Tautological "because" detection
    mech_lower = mechanism.lower()
    for banned_prefix in BANNED_MECHANISM_PREFIXES:
        if mech_lower.startswith(banned_prefix) or banned_prefix in mech_lower:
            # Check if the because-clause is the ONLY content
            # "X works because it enables X" is tautological
            return False, 0.0, (
                f"Mechanism contains tautological pattern '{banned_prefix}' — "
                "restates definition rather than explaining causal chain. QUARANTINE."
            )

    # 3. Citation echo override: high source count + axiomatic evidence
    if n_sources > CITATION_ECHO_SOURCE_THRESHOLD and evidence == "axiomatic":
        return True, 0.5, (
            f"Citation echo risk: {n_sources} sources + axiomatic evidence. "
            "Escalate to LLM deep check regardless of NLI outcome."
        )

    return True, 1.0, "Mechanism quality OK"


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

        # 2.5 Mechanism quality pre-filter (D2220: guards citation echo gaming NLI)
        mech_passed, mech_score, mech_detail = check_mechanism_quality(fb)
        results.append({
            "check_name": "mechanism_quality",
            "passed": mech_passed,
            "score": mech_score,
            "detail": mech_detail,
        })

        # 3. Factual consistency — DeBERTa NLI pre-filter → LLM deep check (D2093)
        fact_passed: bool = True
        fact_score: float = 1.0
        fact_detail: str = "No verification needed"
        method: str = "none"

        # D2220: Mechanism quality pre-filter gates NLI shortcuts.
        # If mechanism_quality score = 0.0: auto-quarantine, skip NLI + LLM entirely
        # If mechanism_quality score = 0.5: citation echo risk → always escalate to LLM
        if not mech_passed:
            # Mechanism quality failed → auto-quarantine, no NLI needed
            fact_passed = False
            fact_score = 0.0
            fact_detail = f"MECH FAIL: {mech_detail}"
            method = "mech_quality"
            prefilter_stats["mech_fail"] = prefilter_stats.get("mech_fail", 0) + 1
        elif not skip_nli:
            # D2093: DeBERTa NLI pre-filter (replaces embedding similarity)
            nli_passed, nli_score, nli_detail = nli_evidence_check(fb)

            # D2220: Citation echo override — if mechanism is flagged, NLI pass is unreliable
            force_llm = (mech_score <= 0.5)

            if force_llm:
                # D2220: Citation echo risk — NLI alone is unreliable. Always escalate to LLM.
                prefilter_stats["echo_escalated"] = prefilter_stats.get("echo_escalated", 0) + 1
                if omlx_available:
                    llm_stats["echo_llm"] = llm_stats.get("echo_llm", 0) + 1
                    fact_passed, fact_score, fact_detail = check_factual_llm(
                        fb, model=VERIFY_MODEL_V2
                    )
                    fact_detail = f"NLI {nli_score:.2f} + CITATION-ECHO → LLM: {fact_detail}"
                    method = "nli+LLM-echo"
                else:
                    fact_passed = False
                    fact_score = nli_score
                    fact_detail = f"NLI {nli_score:.2f} + CITATION-ECHO + OMLX unavailable — QUARANTINE: {mech_detail}"
                    method = "nli-echo"
            elif nli_passed and nli_score >= NLI_PASS_THRESHOLD:  # D2226: config threshold (default 0.6)
                prefilter_stats["passed"] += 1
                fact_passed = True
                fact_score = nli_score
                fact_detail = f"NLI PASS: {nli_detail}"
                method = "nli"
                llm_stats["skipped"] += 1
            elif nli_passed and nli_score >= NLI_MARGINAL_THRESHOLD:  # D2155: config threshold (default 0.5)
                # D2176: Marginal NLI (0.3–0.6) must escalate to LLM deep check.
                # OLD: fact_passed=True on marginal — treated weak evidence as confirmed.
                # NEW: marginal → UNKNOWN → escalate to LLM verifier (Gemma cross-family).
                # This is epistemically correct: "maybe" is not "yes."
                prefilter_stats["marginal"] = prefilter_stats.get("marginal", 0) + 1
                if omlx_available:
                    llm_stats["escalated_marginal"] = llm_stats.get("escalated_marginal", 0) + 1
                    fact_passed, fact_score, fact_detail = check_factual_llm(
                        fb, model=VERIFY_MODEL_V2
                    )
                    fact_detail = f"NLI MARGINAL → LLM: {fact_detail}"
                    method = "nli+LLM"
                else:
                    # Fail-closed: no LLM available for escalation → UNKNOWN
                    fact_passed = False
                    fact_score = nli_score
                    fact_detail = f"NLI MARGINAL + OMLX unavailable — UNKNOWN: {nli_detail}"
                    method = "nli-only"
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

        # D2184: Monotonic trust — classification FAILED cannot become PASS
        # The FB must stay QUARANTINED until classification is re-evaluated.
        if fb.get("classification_status") == "FAILED":
            status = "QUARANTINE"
            needs_human = True
            results.append({
                "check_name": "classification_status",
                "passed": False,
                "score": 0.0,
                "detail": "Classification FAILED — cannot pass verification. Re-classify first."
            })
        else:
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

        # D2176: Derive epistemic_status — what kind of knowledge claim this is.
        # BORP = corroboration (not truth), NLI = source-support (not proof).
        # These are epistemic categories, not verification pass/fail states.
        source_count: int = len(fb.get("source_books", []))
        is_singleton: bool = fb.get("is_singleton_fb", False) or fb.get("is_singleton", False)

        if borp_passed and fact_passed:
            epistemic_status = "corroborated"
        elif borp_passed and not fact_passed:
            epistemic_status = "cross-source-unverified"
        elif not borp_passed and fact_passed:
            epistemic_status = "source-supported"
        elif source_count >= 2:
            epistemic_status = "contested"
        elif is_singleton:
            epistemic_status = "singleton-unverified"
        else:
            epistemic_status = "speculative"
        vfb["epistemic_status"] = epistemic_status

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
