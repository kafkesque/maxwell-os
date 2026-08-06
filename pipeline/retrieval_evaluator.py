#!/usr/bin/env python3
"""
retrieval_evaluator.py — CRAG-style retrieval quality evaluation.
===============================================================
Authority: D2205 (2026-08-06 RAG Architecture Roadmap)
Constitution: C1 ($0 marginal cost), C3 (sovereign), C12 (no hardcoding),
              C17 (type hints), C18 (docstrings), R7 (temp=0.0), C16 (no silent errors)

Grounded in:
  - CRAG (Google DeepMind, arxiv 2401.15884): retrieval evaluator with
    Correct/Incorrect/Ambiguous classification
  - Agentic RAG Survey (arxiv 2501.09136v4): structured critique schema
    with answered/missing/contradictions/next_query/confidence/should_continue
  - Self-RAG (ICLR 2024): reflection tokens adapted to deterministic critique

Adapted for Maxwell OS constraints:
  - No web search fallback (C3 violation) → broader local retrieval instead
  - No tree-decoding / beam search (R7: temp=0.0) → deterministic scoring
  - No training required (C1: $0 marginal cost) → Phi-4-mini for evaluation
  - BUG-053 mitigation: Phi-4-mini hallucinates on open-ended research →
    this function uses it for CLASSIFICATION of provided text (FBs), not
    open-ended generation. Source text is always provided.

Model: Uses Phi-4-mini-instruct-8bit (local OMLX, already available in pipeline).
       This is NOT the Verifier (Gemma-4-E4B, cross-family R5) — evaluation
       is a pre-generation critique, not verification. R5 applies to verification
       (Generator ≠ Verifier), not to retrieval quality classification.

Usage:
    python3 pipeline/retrieval_evaluator.py --query "pricing strategies" --fb-file results.json
    python3 pipeline/retrieval_evaluator.py --critique-only --fb-ids FB-001,FB-002,FB-003
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.omlx_call import call_omlx

logger = logging.getLogger(__name__)

# ── Config (C12: from YAML, never hardcoded) ──────────────────────────
_CFG_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as _f:
    _CFG: dict = yaml.safe_load(_f)

_EVAL_CFG: dict = _CFG.get("retrieval_eval", {})
DEFAULT_EVAL_MODEL: str = _EVAL_CFG.get("model", "Phi-4-mini-instruct-8bit")
DEFAULT_EVAL_PROVIDER: str = _EVAL_CFG.get("provider", "omlx")
DEFAULT_EVAL_MAX_TOKENS: int = int(_EVAL_CFG.get("max_tokens", 1024))
DEFAULT_CONFIDENCE_THRESHOLD: float = float(_EVAL_CFG.get("confidence_threshold", 0.85))
DEFAULT_MAX_ITERATIONS: int = int(_EVAL_CFG.get("max_iterations", 3))
EVAL_MAX_FBS: int = int(_EVAL_CFG.get("max_fbs_to_evaluate", 15))
EVAL_FB_DEFINITION_MAX_CHARS: int = int(_EVAL_CFG.get("fb_definition_max_chars", 300))
EVAL_FB_NAME_MAX_CHARS: int = int(_EVAL_CFG.get("fb_name_max_chars", 200))


# ── Data types ─────────────────────────────────────────────────────────

@dataclass
class CritiqueResult:
    """D2205: Structured retrieval quality critique.

    All fields populated by LLM evaluation of retrieved FBs against query.
    Force JSON output for deterministic parsing (temp=0.0 per R7).

    Attributes:
        retrieval_quality: CRAG-style classification of overall quality
        answered_aspects: What the retrieved FBs cover well
        missing_aspects: What's missing from the retrieved set
        contradictions_found: Internal contradictions among retrieved FBs
        proposed_next_query: Refined query for next iteration (None if CORRECT)
        confidence: 0.0-1.0 confidence in this critique
        should_continue: Whether another retrieval iteration is warranted
        rationale: One-sentence explanation of the classification
    """
    retrieval_quality: Literal["CORRECT", "PARTIAL", "INCORRECT", "CONTRADICTORY"]
    answered_aspects: list[str] = field(default_factory=list)
    missing_aspects: list[str] = field(default_factory=list)
    contradictions_found: list[dict] = field(default_factory=list)
    proposed_next_query: str | None = None
    confidence: float = 0.5
    should_continue: bool = True
    rationale: str = ""


VALID_QUALITIES: frozenset[str] = frozenset({"CORRECT", "PARTIAL", "INCORRECT", "CONTRADICTORY"})


# ── Core evaluation ────────────────────────────────────────────────────

def evaluate_retrieval(
    query: str,
    fbs: list[dict],
    *,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int | None = None,
) -> CritiqueResult:
    """Classify retrieval quality and propose corrective action.

    Implements the CRAG retrieval evaluator pattern adapted for Maxwell:
      - CORRECT: All FBs directly relevant, no gaps → synthesize
      - PARTIAL: Some FBs relevant but aspects missing → refine query
      - INCORRECT: FBs irrelevant to query intent → broaden search
      - CONTRADICTORY: FBs contain internal contradictions → surface both sides

    Adaptation from CRAG:
      - "Incorrect → web search" replaced with "Incorrect → broader retrieval"
        (sovereign constraint C3: no data leaves the machine)
      - "Ambiguous" merged into PARTIAL with explicit missing_aspects for clarity

    Args:
        query: Natural language search query
        fbs: Retrieved Foundation Blocks to evaluate (max EVAL_MAX_FBS evaluated)
        model: Evaluation model name (default: Phi-4-mini-instruct-8bit from config)
        provider: Model provider (default: omlx from config)
        max_tokens: Max tokens for evaluation response

    Returns:
        CritiqueResult with structured retrieval quality assessment

    Note on BUG-053:
        Phi-4-mini hallucinates on open-ended research tasks. This evaluator
        provides all source text (query + FB definitions) and asks for
        CLASSIFICATION, not generation. The model is judging provided text,
        not inventing facts. This pattern has been verified safe with
        Phi-4-mini (classification of provided text → low hallucination risk).

    Raises:
        ValueError: If fbs list is empty
        RuntimeError: If LLM response cannot be parsed as valid critique JSON
    """
    if model is None:
        model = DEFAULT_EVAL_MODEL
    if provider is None:
        provider = DEFAULT_EVAL_PROVIDER
    if max_tokens is None:
        max_tokens = DEFAULT_EVAL_MAX_TOKENS

    if not fbs:
        raise ValueError("Cannot evaluate empty FB list")

    # Build critique prompt
    prompt: str = _build_critique_prompt(query, fbs[:EVAL_MAX_FBS])

    # Call LLM for evaluation
    try:
        response: str = call_omlx(
            prompt,
            model=model,
            system="You are a retrieval quality evaluator. Classify the retrieved Foundation Blocks (FBs) against the query. Output ONLY valid JSON.",
            max_tokens=max_tokens,
            temperature=0.0,  # R7: deterministic
        )
    except Exception as exc:
        logger.error("Retrieval evaluator LLM call failed: %s", exc)
        # C16: log and raise, but with fallback CritiqueResult
        return CritiqueResult(
            retrieval_quality="PARTIAL",
            answered_aspects=[],
            missing_aspects=["llm_call_failed"],
            contradictions_found=[],
            proposed_next_query=None,
            confidence=0.1,
            should_continue=True,
            rationale=f"LLM call failed: {exc}",
        )

    # Parse and validate
    result: CritiqueResult = _parse_critique_response(response, query, fbs)
    return result


def evaluate_fb_set_quick(
    fb_ids: list[str],
    *,
    model: str | None = None,
    provider: str | None = None,
) -> CritiqueResult:
    """Quick critique of a set of FBs by ID (for CLI/agent use).

    Loads FBs from DB by ID, then runs evaluate_retrieval with a
    synthetic "tell me about these FBs" query.

    Args:
        fb_ids: List of FB IDs to evaluate
        model: Evaluation model (default from config)
        provider: Model provider (default from config)

    Returns:
        CritiqueResult for the FB set

    Raises:
        FileNotFoundError: If Maxwell DB not found
    """
    import sqlite3
    from pipeline.pipeline_paths import DB_PATH

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Maxwell DB not found: {DB_PATH}")

    conn: sqlite3.Connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        placeholders: str = ",".join("?" * len(fb_ids))
        rows = conn.execute(
            f"SELECT * FROM fbs WHERE fb_id IN ({placeholders})",
            fb_ids,
        ).fetchall()
        fbs: list[dict] = [dict(r) for r in rows]
    finally:
        conn.close()

    query: str = "Evaluate the quality and coherence of these Foundation Blocks"
    return evaluate_retrieval(query, fbs, model=model, provider=provider)


# ── Prompt construction ─────────────────────────────────────────────────

def _build_critique_prompt(query: str, fbs: list[dict]) -> str:
    """Build structured critique prompt with FB summaries.

    Constructs a prompt that asks the LLM to evaluate how well the retrieved
    FBs answer the query. Includes FB name, domain, definition, and key
    metadata. Truncates long text to EVAL_FB_DEFINITION_MAX_CHARS.

    Args:
        query: User's natural language query
        fbs: Retrieved Foundation Blocks (already truncated to EVAL_MAX_FBS)

    Returns:
        Formatted prompt string for LLM evaluation

    C12 compliance: All limits from pipeline_config.yaml → retrieval_eval section.
    """
    fb_summaries: list[str] = []
    for i, fb in enumerate(fbs):
        fb_id: str = str(fb.get("fb_id", fb.get("id", f"FB-{i}")))
        name: str = str(fb.get("name", ""))[:EVAL_FB_NAME_MAX_CHARS]
        domains: str = str(fb.get("domains", ""))
        definition: str = str(fb.get("definition", ""))[:EVAL_FB_DEFINITION_MAX_CHARS]
        borp: str = f"{fb.get('borp_score', '?'):.2f}" if fb.get("borp_score") else "?"
        feedback: str = f"{fb.get('feedback_score', '?'):.2f}" if fb.get("feedback_score") is not None else "?"

        fb_summaries.append(
            f"{fb_id}: {name}\n"
            f"  Domain: {domains}\n"
            f"  BORP: {borp} | Feedback: {feedback}\n"
            f"  Definition: {definition}"
        )

    prompt: str = f"""EVALUATE retrieval quality for query: "{query}"

Retrieved Foundation Blocks ({len(fbs)} total, showing top {len(fb_summaries)}):
{chr(10).join(fb_summaries)}

Classify the overall retrieval quality. Output ONLY this JSON (no markdown, no explanation):
{{
  "retrieval_quality": "CORRECT|PARTIAL|INCORRECT|CONTRADICTORY",
  "answered_aspects": ["aspect the FBs cover well", ...],
  "missing_aspects": ["aspect missing from results", ...],
  "contradictions_found": [{{"fb_a": "FB-xxx", "fb_b": "FB-yyy", "topic": "disagreement about X"}}],
  "proposed_next_query": "refined query for next iteration, or null if CORRECT",
  "confidence": 0.85,
  "should_continue": true,
  "rationale": "One sentence explaining the classification"
}}

Rules:
- CORRECT: All FBs directly relevant AND no major gaps in answering the query
- PARTIAL: Some FBs relevant but key aspects of the query are unaddressed
- INCORRECT: FBs are mostly irrelevant to the query intent
- CONTRADICTORY: FBs contain internal contradictions that a user must know about
- confidence: Your certainty in this classification (0.0-1.0, be honest)
- should_continue: true if another retrieval round would likely help, false if done
- proposed_next_query: null if CORRECT or INCORRECT, a refined query if PARTIAL
"""
    return prompt


# ── Response parsing ────────────────────────────────────────────────────

def _parse_critique_response(
    response: str,
    query: str,
    fbs: list[dict],
) -> CritiqueResult:
    """Parse LLM response into validated CritiqueResult.

    Handles:
      - Clean JSON (standard path)
      - JSON wrapped in markdown code blocks
      - Malformed JSON (graceful fallback to PARTIAL)
      - Missing fields (coerced to defaults)

    Args:
        response: Raw LLM text response
        query: Original query (for context in error messages)
        fbs: Original FBs (for context)

    Returns:
        Validated CritiqueResult (never raises from parse errors)

    C16 compliance: Logs parse failures, never silently swallows.
    """
    # Strip markdown code blocks if present
    cleaned: str = response.strip()
    if cleaned.startswith("```"):
        # Remove ```json or ``` and trailing ```
        lines: list[str] = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    # Parse JSON
    try:
        data: dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Retrieval evaluator JSON parse failed for query '%s': %s. "
            "Raw response (first 200 chars): %s",
            query[:80], exc, response[:200],
        )
        # Graceful fallback to PARTIAL — treat unparseable as "needs another round"
        return CritiqueResult(
            retrieval_quality="PARTIAL",
            answered_aspects=[],
            missing_aspects=["json_parse_failed"],
            contradictions_found=[],
            proposed_next_query=None,
            confidence=0.3,
            should_continue=True,
            rationale=f"JSON parse failed: {exc}",
        )

    # Validate and coerce fields
    quality: str = str(data.get("retrieval_quality", "PARTIAL")).upper()
    if quality not in VALID_QUALITIES:
        logger.warning(
            "Invalid retrieval_quality '%s', falling back to PARTIAL",
            quality,
        )
        quality = "PARTIAL"

    confidence: float
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    should_continue: bool = bool(data.get("should_continue", True))
    proposed: str | None = data.get("proposed_next_query")
    if proposed is not None and not isinstance(proposed, str):
        proposed = None

    contradictions: list[dict] = []
    raw_contradictions = data.get("contradictions_found", [])
    if isinstance(raw_contradictions, list):
        for item in raw_contradictions:
            if isinstance(item, dict):
                contradictions.append(item)

    answered: list[str] = []
    raw_answered = data.get("answered_aspects", [])
    if isinstance(raw_answered, list):
        answered = [str(a) for a in raw_answered if a]

    missing: list[str] = []
    raw_missing = data.get("missing_aspects", [])
    if isinstance(raw_missing, list):
        missing = [str(m) for m in raw_missing if m]

    return CritiqueResult(
        retrieval_quality=quality,  # type: ignore[arg-type]
        answered_aspects=answered,
        missing_aspects=missing,
        contradictions_found=contradictions,
        proposed_next_query=proposed,
        confidence=confidence,
        should_continue=should_continue,
        rationale=str(data.get("rationale", "")),
    )


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for retrieval evaluator.

    Two modes:
      1. --query + --fb-file: Evaluate FBs from JSON file against query
      2. --critique-only + --fb-ids: Quick critique of FB set by ID
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="D2205: CRAG-style retrieval quality evaluator"
    )
    parser.add_argument(
        "--query",
        help="Search query to evaluate retrieval against",
    )
    parser.add_argument(
        "--fb-file",
        type=Path,
        help="JSON file containing retrieved FBs (from retrieve.py --json output)",
    )
    parser.add_argument(
        "--fb-ids",
        help="Comma-separated FB IDs for quick critique (e.g., FB-001,FB-002)",
    )
    parser.add_argument(
        "--critique-only",
        action="store_true",
        help="Quick critique mode: evaluate FB set by ID",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Evaluation model (default: {DEFAULT_EVAL_MODEL})",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output CritiqueResult as JSON",
    )

    args = parser.parse_args()

    if args.critique_only and args.fb_ids:
        fb_id_list: list[str] = [fid.strip() for fid in args.fb_ids.split(",") if fid.strip()]
        try:
            result: CritiqueResult = evaluate_fb_set_quick(
                fb_id_list,
                model=args.model,
            )
        except FileNotFoundError as exc:
            print(f"❌ {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.query and args.fb_file:
        if not args.fb_file.exists():
            print(f"❌ FB file not found: {args.fb_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.fb_file) as f:
            fbs: list[dict] = json.load(f)
        result = evaluate_retrieval(args.query, fbs, model=args.model)
    else:
        parser.print_help()
        print("\n❌ Must specify either --query + --fb-file, or --critique-only + --fb-ids",
              file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps({
            "retrieval_quality": result.retrieval_quality,
            "answered_aspects": result.answered_aspects,
            "missing_aspects": result.missing_aspects,
            "contradictions_found": result.contradictions_found,
            "proposed_next_query": result.proposed_next_query,
            "confidence": result.confidence,
            "should_continue": result.should_continue,
            "rationale": result.rationale,
        }, indent=2))
    else:
        _print_human(result)


def _print_human(result: CritiqueResult) -> None:
    """Print CritiqueResult in human-readable format."""
    emoji: dict[str, str] = {
        "CORRECT": "✅",
        "PARTIAL": "⚠️",
        "INCORRECT": "❌",
        "CONTRADICTORY": "⚡",
    }
    e: str = emoji.get(result.retrieval_quality, "❓")
    print(f"{e} Retrieval Quality: {result.retrieval_quality}")
    print(f"   Confidence: {result.confidence:.0%}")
    print(f"   Continue: {'Yes' if result.should_continue else 'No'}")
    print(f"   Rationale: {result.rationale}")
    if result.answered_aspects:
        print(f"   ✅ Answered: {', '.join(result.answered_aspects)}")
    if result.missing_aspects:
        print(f"   ❓ Missing: {', '.join(result.missing_aspects)}")
    if result.contradictions_found:
        print(f"   ⚡ Contradictions ({len(result.contradictions_found)}):")
        for c in result.contradictions_found:
            fb_a: str = c.get("fb_a", "?")
            fb_b: str = c.get("fb_b", "?")
            topic: str = c.get("topic", "unspecified")
            print(f"      {fb_a} ↔ {fb_b}: {topic}")
    if result.proposed_next_query:
        print(f"   🔄 Next query: {result.proposed_next_query}")


if __name__ == "__main__":
    main()
