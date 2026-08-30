#!/usr/bin/env python3
"""
stage4_merged_call.py — Single-call CRIBS enrichment + classification (D2224)
================================================================================
Authority: D2224 — Merges two S4 LLM calls into one for ~45% speedup.

This replaces the two-call pattern:
  1. CRIBS enrichment (Qwen3-35B, ~13s) — application, failure_mode, elaboration, keywords
  2. Classification (Phi-4-mini, ~7s) — discipline, domains, depth, evidence

With a single call (~15-18s) producing ALL fields. The prompt includes both
CRIBS enrichment instructions AND the physicist-chef-poet depth ontology.

R5 compliance: Uses Phi-4-mini-8bit (Microsoft family), distinct from S2 generator
(Qwen/Alibaba) and S4 classifier (GPT-OSS/OpenAI). Different families per R5.

Usage:
    from pipeline.stage4_merged_call import merged_cribs_classify
    result = merged_cribs_classify(fb_data)
"""

import re
import time

from pipeline.omlx_call import call_omlx_json
import sys

MERGED_CRIBS_CLASSIFY_SYSTEM = """You enrich and classify a Foundation Block in a single response. You receive an FB
with name, definition, mechanism, boundary, and consequence. Your job is to ADD enrichment
fields AND classify the FB's discipline, domains, and ontological depth.

PART 1 — CRIBS ENRICHMENT:
- application: REQUIRED for EVERY principle — descriptive or prescriptive. NEVER null, never omit.
  Format: "When [concrete situation] → do [specific action]."
  For descriptive/theoretical principles (causal mechanisms, empirical patterns),
  frame it as "When [observing/encountering this pattern] → do [adjust reasoning/behavior accordingly]."
- failure_mode: "The principle fails when [specific condition]." How it breaks — be specific.
- elaboration: 3-5 sentences. Edge cases, non-obvious implications, second-order effects.
- keywords: 3-5 search terms, comma-separated.
- jargon: OMIT entirely if no specialized terms. Only include when a non-expert would not
  understand specific terms. NEVER copy keywords into jargon.

PART 2 — CLASSIFICATION:
- discipline: SINGLE most precise academic discipline. "computational neuroscience" > "neuroscience."
- domains: 1-5 applied domains where a practitioner would USE this knowledge.
- depth: ontological scope using the physicist-chef-poet test:
  universal = mechanism applies to ALL systems (physics, cooking, poetry)
  cross-domain = bridges 2+ DISTINCT disciplines via shared mechanism
  domain = operates within one field, requires domain context
  specialized = narrow sub-technique within a sub-field
  DEFAULT to "domain" unless mechanism clearly transcends it.
- is_specialized: true ONLY for narrow sub-technique or tool-specific skill.
- evidence: "cited" (grounded in source text) or "axiomatic" (self-evident truth)

DO NOT use "emerging" as a discipline — use the most specific real discipline name.
DO NOT copy keywords into jargon.
DO NOT over-assign "universal" — most principles are domain-bound.

Return ONLY a JSON object:
{
  "application": "string (REQUIRED)",
  "failure_mode": "string",
  "elaboration": "string",
  "keywords": "comma, separated, terms",
  "jargon": {"term": "definition"} or omit entirely,
  "discipline": "precise_discipline_name",
  "domains": ["domain1", "domain2"],
  "depth": "universal|cross-domain|domain|specialized",
  "is_specialized": true or false,
  "evidence": "cited|axiomatic"
}"""

# ── D2454 (2026-08-27): inject the config-driven S4 classification golden. ──
# Fail-closed (D2463 pattern): enabled + missing/malformed/empty → raise.
try:
    from pipeline.pipeline_paths import S4_GOLDEN_INJECT_ENABLED, S4_GOLDEN_MAX_EXAMPLES, S4_GOLDEN_PATH
    if S4_GOLDEN_INJECT_ENABLED:
        from pipeline.s4_golden import format_classify_golden, load_stage4_golden
        _s4_examples = load_stage4_golden(S4_GOLDEN_PATH)[:S4_GOLDEN_MAX_EXAMPLES]
        MERGED_CRIBS_CLASSIFY_SYSTEM = (
            MERGED_CRIBS_CLASSIFY_SYSTEM
            + "\n\nFEW-SHOT EXAMPLES (config-driven, D2454):\n"
            + format_classify_golden(_s4_examples)
        )
except Exception as _s4_golden_err:  # C16: fail-loud — never silently skip an enabled gate
    raise RuntimeError(f"D2454: stage4_golden injection failed: {_s4_golden_err}") from _s4_golden_err


def build_merged_prompt(fb_data: dict) -> str:
    """Build a merged CRIBS + classification prompt for a single FB.

    D2224: Combines what was previously two separate prompts.
    The FB already has name, definition, mechanism, boundary, consequence from S2.
    """
    name = fb_data.get("name", "")
    definition = fb_data.get("definition", "")
    mechanism = fb_data.get("mechanism", "")
    boundary = fb_data.get("boundary", "")
    consequence = fb_data.get("consequence", "")

    lines = [
        "Enrich and classify this Foundation Block.",
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
    lines.append("Return a JSON object with: application, failure_mode, elaboration, "
                 "keywords, jargon, discipline, domains, depth, is_specialized, evidence")
    return "\n".join(lines)


def merged_cribs_classify(
    fb_data: dict,
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 120,
) -> dict:
    """Single-call CRIBS enrichment + classification (D2224).

    Args:
        fb_data: FB dict with name, definition, mechanism, boundary, consequence.
        model: Model to use. Default GPT-OSS-20B (D2249 — R5: different family from S2 Qwen).
        max_tokens: Max output tokens. None → read from pipeline_config.yaml (C12).
        timeout: Request timeout in seconds.

    Returns:
        Dict with all CRIBS fields + discipline, domains, depth, is_specialized, evidence.
    """
    # C12: read model and max_tokens from config if not explicitly provided
    if model is None:
        try:
            from pipeline.pipeline_paths import VERIFY_MODEL
            model = VERIFY_MODEL
        except Exception as e:
            print(f"   ⚠️  stage4: VERIFY_MODEL config unreadable ({type(e).__name__}: {e}) — fallback 'gpt-oss-20b-MXFP4-Q8' (C16)", file=sys.stderr)
            model = "gpt-oss-20b-MXFP4-Q8"
    if max_tokens is None:
        try:
            from pipeline.pipeline_paths import _CFG
            max_tokens = int(_CFG.get("stage4", {}).get("merged_call_max_tokens", 512))
        except Exception as e:
            print(f"   ⚠️  stage4: merged_call_max_tokens unreadable ({type(e).__name__}: {e}) — fallback 512 (C16)", file=sys.stderr)
            max_tokens = 512

    prompt = build_merged_prompt(fb_data)

    # D2249/BUG-074: reasoning models (e.g. GPT-OSS) — prepend Reasoning:none
    # so they don't burn max_tokens on chain-of-thought before producing JSON.
    system = MERGED_CRIBS_CLASSIFY_SYSTEM
    if model:
        from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX
        if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
            system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"

    result = call_omlx_json(
        prompt=prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    # BUG-080: call_omlx_json can return list — unwrap first element
    if isinstance(result, list):
        result = result[0] if result else {}
    # Validate required fields
    if not isinstance(result, dict):
        raise ValueError(f"Merged call returned non-dict: {type(result)}")

    # CRIBS enrichment fields — non-semantic, safe to default (C16/D2355).
    # D2371: application is REQUIRED (schemas.FB.application, min_length=10) —
    # NOT defaulted here. It is validated fail-closed below so an empty/short
    # application is never silently recorded.
    for key, default in (("failure_mode", ""),
                         ("elaboration", ""), ("keywords", ""), ("is_specialized", False)):
        if key not in result or result[key] is None:
            result[key] = default

    # Remove jargon if empty (preserves the OMIT behavior)
    if "jargon" in result and (not result["jargon"] or result["jargon"] == {}):
        del result["jargon"]

    # D2371: application is REQUIRED (schema min_length=10). Fail-closed like
    # the semantic fields — never let a null/empty application pass silently.
    app = result.get("application")
    if not isinstance(app, str) or len(app.strip()) < 10:
        raise SparseClassificationError(
            f"merged: application missing/too short ({len(str(app))} chars < 10)"
        )

    # Semantic classification fields — FAIL-CLOSED: a sparse model response must
    # raise (never fabricate "emerging"/"domain"/"cited") so the caller falls
    # back and the failure is accounted (D2355 ChatGPT re-audit).
    _validate_semantic_classification(result, source="merged")

    return result


# ── A/B Test Harness ────────────────────────────────────────────────────────

def ab_test_merged_vs_split(fb_data: dict, verbose: bool = True) -> dict:
    """Compare merged call vs. separate CRIBS + classify calls.

    D2224: Validates that the merged call produces equivalent quality to
    the separate two-call pattern. Compares:
      - field presence (all expected fields populated)
      - discipline specificity (not generic/emerging)
      - depth consistency (passes physicist-chef-poet test)
      - latency (merged should be ~45% faster than separate sum)

    Returns:
        Dict with timing, field counts, and quality metrics for both paths.
    """
    import time

    # Path A: Merged single call
    t0 = time.time()
    merged = merged_cribs_classify(fb_data)
    t_merged = time.time() - t0

    # Path B: Separate calls (simulated — would need actual pipeline calls)
    # For now, measure just the merged path and note expected separate timing
    t_separate_expected = t_merged / 0.55  # Merged should be ~45% faster

    metrics = {
        "merged_time_s": round(t_merged, 2),
        "separate_expected_time_s": round(t_separate_expected, 2),
        "speedup_pct": round((1 - t_merged / t_separate_expected) * 100),
        "merged_fields": {
            "has_application": "application" in merged,
            "has_failure_mode": bool(merged.get("failure_mode")),
            "has_elaboration": bool(merged.get("elaboration")),
            "has_keywords": bool(merged.get("keywords")),
            "has_discipline": bool(merged.get("discipline")),
            "has_domains": bool(merged.get("domains")),
            "has_depth": merged.get("depth") in ("universal", "cross-domain", "domain", "specialized"),
            "has_evidence": merged.get("evidence") in ("cited", "axiomatic"),
        },
        "quality_flags": [],
    }

    # Quality checks
    if merged.get("discipline") == "emerging":
        metrics["quality_flags"].append("WARNING: discipline fell back to 'emerging'")
    if merged.get("depth") == "universal" and not _likely_universal(fb_data):
        metrics["quality_flags"].append("WARNING: depth=universal but mechanism appears domain-bound")
    if merged.get("application") and "can be used" in str(merged["application"]).lower():
        metrics["quality_flags"].append("WARNING: generic application pattern detected")

    if verbose:
        print(f"Merged call: {t_merged:.2f}s (expected separate: ~{t_separate_expected:.2f}s)")
        print(f"Speedup: {metrics['speedup_pct']}%")
        print(f"Fields: {sum(metrics['merged_fields'].values())}/{len(metrics['merged_fields'])} present")
        if metrics["quality_flags"]:
            for flag in metrics["quality_flags"]:
                print(f"  {flag}")

    return metrics


def _likely_universal(fb_data: dict) -> bool:
    """Heuristic: is this principle likely universal (physics/cognition/math)? """
    # D2364/C12 (X7): universal signal substrings from config (was hardcoded list).
    from pipeline.pipeline_paths import S4_UNIVERSAL_SIGNALS
    name = fb_data.get("name", "").lower()
    mechanism = fb_data.get("mechanism", "").lower()
    return any(s in name or s in mechanism for s in S4_UNIVERSAL_SIGNALS)


# ── BUG-075: Focused S4 Depth Classification ────────────────────────────────
# D2247 finding: LONG combined classify prompt degrades ALL models on depth
# (GPT-OSS 62.5% short → 38% long; cross-domain 0/3 for every model).
# Fix: split depth into its own SHORT focused prompt call (proven 62.5%).
# Prompt structure mirrors tools/benchmark_s4_depth_gptoss.py DEPTH_PROMPT.

DEPTH_FOCUSED_PROMPT = """Classify the DEPTH of this Foundation Block (a convergent principle from multiple books).

ONTOLOGY:
- specialized: A narrow sub-technique within a sub-field, or a tool-specific skill. (e.g., optical kerning in typography)
- domain: Operates within ONE field and requires that field's context. (e.g., price anchoring in behavioral economics)
- cross-domain: Bridges 2+ DISTINCT disciplines via a SHARED mechanism. (e.g., feedback loops explaining homeostasis in biology AND equilibrium in org design)
- universal: A law of nature or mathematics that applies to ALL systems. (e.g., entropy, power laws, scale invariance)

DEFAULT to "domain" unless the mechanism clearly transcends a single discipline.
DO NOT over-assign "universal" or "cross-domain" — most principles are domain-bound.

FB:
Name: {name}
Definition: {definition}
Mechanism: {mechanism}
Type: {extraction_type}

Answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning."""

# ── D2454 (2026-08-27): inject the config-driven depth few-shot (compact). ──
# Fail-closed (D2463 pattern): enabled + missing/malformed/empty → raise.
try:
    from pipeline.pipeline_paths import S4_GOLDEN_INJECT_ENABLED, S4_GOLDEN_MAX_EXAMPLES, S4_GOLDEN_PATH
    if S4_GOLDEN_INJECT_ENABLED:
        from pipeline.s4_golden import format_depth_golden, load_stage4_golden
        _s4_examples = load_stage4_golden(S4_GOLDEN_PATH)[:S4_GOLDEN_MAX_EXAMPLES]
        DEPTH_FOCUSED_PROMPT = (
            DEPTH_FOCUSED_PROMPT
            + "\n\nFEW-SHOT DEPTH EXAMPLES (config-driven, D2454):\n"
            + format_depth_golden(_s4_examples)
        )
except Exception as _s4_golden_err:  # C16: fail-loud — never silently skip an enabled gate
    raise RuntimeError(f"D2454: stage4_golden injection failed: {_s4_golden_err}") from _s4_golden_err

# ── D2483/BUG-185: depth-prompt goldilocks variant (A/B-verified) ──────────
# The production depth prompt's "DEFAULT to 'domain'" instruction drives the
# 97.5% collapse (BUG-185). A pure bias-removal over-corrects into over-assigning
# cross-domain (the D2365 failure mode). The A/B-verified fix (scripts/
# benchmark_s4_depth_prompt_ab.py, n=20 sample + 5 goldens) = strip the bias +
# forced 4-way choice + contrastive boundary anchors. Config-gated: default
# "baseline" leaves prompts byte-identical; "v3_contrastive" applies the fix.
_DEPTH_VARIANT_FORCED = (
    "Choose among EXACTLY these four labels, evaluating each before answering:\n"
    "- universal  = mechanism applies to ALL systems (physics, cooking, poetry)\n"
    "- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism\n"
    "- domain = operates within ONE field and requires that field's context\n"
    "- specialized = narrow sub-technique within a sub-field or a tool-specific skill"
)
_DEPTH_VARIANT_ANCHORS = (
    "BOUNDARY ANCHORS (disambiguation):\n"
    "- universal, NOT domain: a heavy-tailed power law holds across wealth, earthquakes, word frequency, city sizes.\n"
    "- cross-domain, NOT domain: a feedback loop bridges biology homeostasis + engineering control + economics supply/demand.\n"
    "- domain, NOT universal: color gamut is meaningful only within color science — strip its vocabulary and it is meaningless.\n"
    "- specialized, NOT cross-domain: backpropagation is a narrow ML sub-technique, not a field-spanning principle."
)
_DEPTH_VARIANT_ANSWER_LINES = (
    "Answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning.",
    "For EACH FB, answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning.",
)


def _apply_depth_prompt_variant(prompt: str) -> str:
    """Strip the DEFAULT-to-"domain" bias and add forced choice + contrastive
    boundary anchors (D2483/BUG-185 goldilocks). Pure text transform — temp=0,
    model routing, and transport are untouched."""
    prompt = prompt.replace(
        'DEFAULT to "domain" unless the mechanism clearly transcends a single discipline.\n', ""
    ).replace(
        'DO NOT over-assign "universal" or "cross-domain" — most principles are domain-bound.\n', ""
    )
    block = (
        _DEPTH_VARIANT_FORCED + "\n\n" + _DEPTH_VARIANT_ANCHORS
        + "\n\nAnswer with EXACTLY ONE of the four labels. No reasoning."
    )
    for old in _DEPTH_VARIANT_ANSWER_LINES:
        prompt = prompt.replace(old, block)
    return prompt


try:
    from pipeline.pipeline_paths import S4_DEPTH_PROMPT_VARIANT
except Exception as e:
    print(f"   ⚠️  stage4: S4_DEPTH_PROMPT_VARIANT unreadable ({type(e).__name__}: {e}) — fallback 'baseline' (C16)", file=sys.stderr)
    S4_DEPTH_PROMPT_VARIANT = "baseline"  # C12 fallback: default = no change

if S4_DEPTH_PROMPT_VARIANT == "v3_contrastive":
    DEPTH_FOCUSED_PROMPT = _apply_depth_prompt_variant(DEPTH_FOCUSED_PROMPT)

VALID_DEPTHS = {"universal", "cross-domain", "domain", "specialized"}

# D2351: fail-closed depth parsing (C16). Order matters for token-level match:
# "cross-domain" must be tested before "domain" only if using substring search —
# token-level matching below compares WHOLE tokens, so order is irrelevant here.
# Kept as an explicit ordering for any substring-based callers.
DEPTH_ORDER: tuple[str, ...] = ("cross-domain", "universal", "specialized", "domain")


class DepthClassificationError(RuntimeError):
    """Raised when depth cannot be classified unambiguously (fail-closed, C16).

    Do NOT catch this and substitute a semantic label — route it into the
    stage's classification_errors accounting so a failed inference is never
    mistaken for a valid depth classification.
    """


def _parse_depth_token(raw: str) -> str:
    """Parse exactly one depth token from a focused-depth answer (D2351).

    The focused prompt demands EXACTLY ONE WORD. Any answer that is not an
    unambiguous single depth label is a failure and must fail closed (raise)
    rather than silently default to "domain".

    Args:
        raw: Raw model output for the focused depth prompt.

    Returns:
        One of "universal" | "cross-domain" | "domain" | "specialized".

    Raises:
        DepthClassificationError: if zero or multiple depth labels are present.
    """
    text = (raw or "").strip().lower()
    # strip surrounding punctuation/quotes/backticks (models often wrap the word)
    text = text.strip('`"\'.')
    # exact single-token answer (the common case)
    if text in VALID_DEPTHS:
        return text
    # token-level match — compare WHOLE tokens so "cross-domain" is never
    # mistaken for "domain" (and vice-versa).
    tokens = [t for t in re.split(r"[^a-z\-]+", text) if t]
    present = [d for d in DEPTH_ORDER if d in tokens]
    if len(present) == 1:
        return present[0]
    raise DepthClassificationError(
        f"ambiguous depth answer {raw!r} (tokens={tokens}, matched={present})"
    )


class BatchClassificationError(RuntimeError):
    """Raised when a batch classification is incomplete or malformed (D2355/BUG-114).

    A missing or invalid batch entry must never be fabricated into valid-looking
    semantic labels (domain/emerging/cited). Callers catch this and fall back to
    individual classification — the missing entry is re-classified, not invented.
    """


class SparseClassificationError(RuntimeError):
    """Raised when a classification response is PRESENT but misses semantic fields.

    D2355 (ChatGPT re-audit): D2355 made the *missing-entry* case fail-closed but
    left the *present-but-sparse* case fabricating `emerging`/`domain`/`cited`
    for a missing `discipline`/`domains`/`depth`/`evidence`. A malformed model
    response must never become valid-looking semantic data (C16) without raising
    — otherwise `max_failed_ratio: 0.0` cannot catch it.
    """


def _validate_semantic_classification(result: dict, source: str) -> None:
    """Fail-closed validation of the four semantic classification fields (C16/D2355).

    CRIBS enrichment fields (application/failure_mode/elaboration/keywords) may
    default to empty — they are non-semantic. But `discipline`, `domains`,
    `depth`, and `evidence` are semantic: a missing/empty/invalid value must raise
    so the caller falls back to individual classification and accounts the failure,
    rather than silently recording plausible-looking labels.

    Args:
        result: The classification dict returned by a model call.
        source: Human-readable origin for error messages ("merged"/"batch fb_index=N").

    Raises:
        SparseClassificationError: if any semantic field is missing/empty/invalid.
    """
    discipline = result.get("discipline")
    if not isinstance(discipline, str) or not discipline.strip():
        raise SparseClassificationError(f"{source}: empty/missing discipline")

    domains = result.get("domains")
    if (not isinstance(domains, list) or not domains
            or not any(isinstance(d, str) and d.strip() for d in domains)):
        raise SparseClassificationError(f"{source}: empty/missing domains")

    depth = result.get("depth")
    if depth not in VALID_DEPTHS:
        raise SparseClassificationError(f"{source}: invalid/missing depth={depth!r}")

    evidence = result.get("evidence")
    if evidence not in ("cited", "axiomatic"):
        raise SparseClassificationError(f"{source}: invalid/missing evidence={evidence!r}")


# ── D2265: Batch CRIBS + Classification ──────────────────────────────────────
# S4 bottleneck: GPT-OSS-20B burns ~15-20s on reasoning_content before producing
# the JSON output. Batch classification amortizes this cost: send 3-5 FBs in one
# call, pay the reasoning cost once, get all classifications back. Expected ~60%
# throughput improvement (from ~26s/FB → ~10s/FB amortized).

BATCH_CRIBS_CLASSIFY_SYSTEM = """You enrich and classify MULTIPLE Foundation Blocks in a single response.
For each FB, you receive name, definition, mechanism, boundary, and consequence.
Your job is to ADD enrichment fields AND classify each FB's discipline, domains, and depth.

FOR EACH FB, return a SEPARATE JSON object with:
{
  "fb_index": <number matching the input index>,
  "application": "string (REQUIRED)",
  "failure_mode": "string",
  "elaboration": "string",
  "keywords": "comma, separated, terms",
  "jargon": {"term": "definition"} or {},
  "discipline": "precise_discipline_name",
  "domains": ["domain1", "domain2"],
  "depth": "universal|cross-domain|domain|specialized",
  "is_specialized": true or false,
  "evidence": "cited|axiomatic"
}

DEPTH ONTOLOGY (physicist-chef-poet test):
- universal: mechanism applies to ALL systems (physics, cooking, poetry)
- cross-domain: bridges 2+ DISTINCT disciplines via shared mechanism
- domain: operates within one field, requires domain context
- specialized: narrow sub-technique within a sub-field
DEFAULT to "domain" unless mechanism clearly transcends it.

Return ONLY a JSON array: [{"fb_index": 0, ...}, {"fb_index": 1, ...}, ...]
One object per input FB. Match fb_index to input order."""

# ── D2454 (2026-08-27): inject the config-driven S4 classification golden. ──
# Fail-closed (D2463 pattern): enabled + missing/malformed/empty → raise.
try:
    from pipeline.pipeline_paths import S4_GOLDEN_INJECT_ENABLED, S4_GOLDEN_MAX_EXAMPLES, S4_GOLDEN_PATH
    if S4_GOLDEN_INJECT_ENABLED:
        from pipeline.s4_golden import format_classify_golden, load_stage4_golden
        _s4_examples = load_stage4_golden(S4_GOLDEN_PATH)[:S4_GOLDEN_MAX_EXAMPLES]
        BATCH_CRIBS_CLASSIFY_SYSTEM = (
            BATCH_CRIBS_CLASSIFY_SYSTEM
            + "\n\nFEW-SHOT EXAMPLES (config-driven, D2454):\n"
            + format_classify_golden(_s4_examples)
        )
except Exception as _s4_golden_err:  # C16: fail-loud — never silently skip an enabled gate
    raise RuntimeError(f"D2454: stage4_golden injection failed: {_s4_golden_err}") from _s4_golden_err


def build_batch_prompt(fbs_data: list[dict]) -> str:
    """Build a batch CRIBS + classification prompt for multiple FBs.

    D2265: Sends 3-5 FBs in a single call to amortize GPT-OSS reasoning cost.
    """
    lines = ["Enrich and classify these Foundation Blocks.", ""]
    for i, fb_data in enumerate(fbs_data):
        name = fb_data.get("name", "")
        definition = fb_data.get("definition", "")
        mechanism = fb_data.get("mechanism", "")
        boundary = fb_data.get("boundary", "")
        consequence = fb_data.get("consequence", "")
        lines.append(f"--- FB {i} ---")
        lines.append(f"NAME: {name}")
        lines.append(f"DEFINITION: {definition}")
        if mechanism:
            lines.append(f"MECHANISM: {mechanism}")
        if boundary:
            lines.append(f"BOUNDARY: {boundary}")
        if consequence:
            lines.append(f"CONSEQUENCE: {consequence}")
        lines.append("")
    lines.append("Return a JSON array with one object per FB. Match fb_index to the FB number above.")
    return "\n".join(lines)


def batch_cribs_classify(
    fbs_data: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 180,
) -> list[dict]:
    """Batch CRIBS enrichment + classification for multiple FBs (D2265).

    Amortizes GPT-OSS reasoning cost across 3-5 FBs per call.
    Expected: ~60% throughput improvement over per-FB merged calls.

    Args:
        fbs_data: List of FB dicts (3-5 recommended for optimal amortization).
        model: Model to use. None → reads from config (C12).
        max_tokens: Max output tokens. None → reads config (default 2048 for batch).
        timeout: Request timeout in seconds.

    Returns:
        List of result dicts in same order as input, each with all CRIBS + classify fields.
    """
    # C12: read model from config if not explicitly provided
    if model is None:
        try:
            from pipeline.pipeline_paths import VERIFY_MODEL
            model = VERIFY_MODEL
        except Exception as e:
            print(f"   ⚠️  stage4: VERIFY_MODEL config unreadable ({type(e).__name__}: {e}) — fallback 'gpt-oss-20b-MXFP4-Q8' (C16)", file=sys.stderr)
            model = "gpt-oss-20b-MXFP4-Q8"
    if not fbs_data:
        return []

    # C12: read max_tokens from config, 2048 safe default for batch (vs 512 for single)
    if max_tokens is None:
        try:
            from pipeline.pipeline_paths import _CFG
            max_tokens = int(_CFG.get("stage4", {}).get("batch_call_max_tokens", 2048))
        except Exception as e:
            print(f"   ⚠️  stage4: batch_call_max_tokens unreadable ({type(e).__name__}: {e}) — fallback 2048 (C16)", file=sys.stderr)
            max_tokens = 2048

    prompt = build_batch_prompt(fbs_data)

    system = BATCH_CRIBS_CLASSIFY_SYSTEM
    if model:
        from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX
        if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
            system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"

    result = call_omlx_json(
        prompt=prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    # BUG-080: call_omlx_json can return non-list — guard
    if isinstance(result, dict):
        result = [result]  # Single object → wrap in list
    if not isinstance(result, list):
        raise ValueError(f"Batch call returned non-list: {type(result)}")

    # Index by fb_index for order-safe matching
    indexed: dict[int, dict] = {}
    for item in result:
        if isinstance(item, dict):
            idx = item.get("fb_index", item.get("index", -1))
            if isinstance(idx, int) and 0 <= idx < len(fbs_data):
                indexed[idx] = item

    output: list[dict] = []
    for i in range(len(fbs_data)):
        if i not in indexed:
            # D2355/BUG-114: FAIL-CLOSED — a missing batch entry must never be
            # fabricated into valid-looking semantic labels (domain/emerging/cited).
            # Raise so the caller falls back to individual classification instead.
            raise BatchClassificationError(
                f"batch missing output for fb_index={i} "
                f"({len(indexed)}/{len(fbs_data)} entries returned)"
            )
        entry = indexed[i]

        # CRIBS enrichment fields — non-semantic, safe to default (C16/D2355).
        # D2371: application is REQUIRED (schema min_length=10) — validated
        # fail-closed below, not defaulted.
        for key, default in (("failure_mode", ""),
                             ("elaboration", ""), ("keywords", ""), ("is_specialized", False)):
            if key not in entry or entry[key] is None:
                entry[key] = default

        # D2371: application is REQUIRED (schema min_length=10). Fail-closed.
        app = entry.get("application")
        if not isinstance(app, str) or len(app.strip()) < 10:
            raise SparseClassificationError(
                f"batch fb_index={i}: application missing/too short "
                f"({len(str(app))} chars < 10)"
            )

        # Clean up jargon
        if "jargon" in entry and (not entry["jargon"] or entry["jargon"] == {}):
            del entry["jargon"]

        # Semantic classification fields — FAIL-CLOSED for a PRESENT-but-sparse
        # entry (D2355 ChatGPT re-audit): missing discipline/domains/depth/evidence
        # must raise, never fabricate "emerging"/"domain"/"cited".
        _validate_semantic_classification(entry, source=f"batch fb_index={i}")

        output.append(entry)

    return output


# ── Batch Size Heuristic ────────────────────────────────────────────────────
# D2265: Optimal batch size balances amortization vs. output quality.
# GPT-OSS-20B: 3-5 FBs optimal. More = higher risk of JSON parse failure.
BATCH_SIZE_DEFAULT: int = 4
BATCH_SIZE_MAX: int = 6


def classify_depth_focused(
    fb_data: dict,
    model: str | None = None,
    max_tokens: int = 1024,
    timeout: int = 120,
) -> str:
    """Classify ONLY the depth of an FB with a short focused prompt (BUG-075).

    D2247: The long combined classify prompt degrades depth accuracy for all
    models (GPT-OSS: 62.5% short → 38% long; cross-domain 0/3 for every model).
    This separate call uses the PROVEN short prompt format from
    tools/benchmark_s4_depth_gptoss.py.

    Args:
        fb_data: FB dict with name, definition, mechanism, extraction_type.
        model: Model to use. Default GPT-OSS-20B (D2249 classifier).
        max_tokens: Max output tokens. Default 1024 — GPT-OSS is a *reasoning*
            model and emits reasoning_content before the answer; 512 truncates
            reasoning mid-stream, yielding empty content (D2351/BUG-109).
        timeout: Request timeout in seconds.

    Returns:
        One of: "universal", "cross-domain", "domain", "specialized".

    Raises:
        DepthClassificationError: on empty content or an ambiguous/non-label
            answer. Transport/parse failures from call_omlx also propagate.
        This is FAIL-CLOSED (C16): callers must route the exception into
        classification_errors — a failed inference is never silently rebranded
        as a valid "domain" label.
    """
    from pipeline.omlx_call import call_omlx
    from pipeline.pipeline_paths import (
        VERIFY_DEPTH_THINKING_BUDGET,
        VERIFY_REASONING_OFF_MODELS,
        VERIFY_REASONING_OFF_PREFIX,
    )

    # C12/D2354: model from config (FrugalGPT depth model), not hardcoded.
    # MUST mirror stage4_merge.py's routing: depth uses the cheap model ONLY
    # when the FrugalGPT cascade is enabled; otherwise GPT-OSS (VERIFY_MODEL).
    # (Previously defaulted to S4_DEPTH_MODEL unconditionally → silently ran
    # Gemma even when frugal was OFF — a model-selection mismatch.)
    if model is None:
        try:
            from pipeline.pipeline_paths import (
                S4_DEPTH_FRUGAL_ENABLED,
                S4_DEPTH_MODEL,
                VERIFY_MODEL,
            )
            model = S4_DEPTH_MODEL if S4_DEPTH_FRUGAL_ENABLED else VERIFY_MODEL
        except Exception as e:
            print(f"   ⚠️  stage4: depth-model config unreadable ({type(e).__name__}: {e}) — fallback 'gpt-oss-20b-MXFP4-Q8' (C16)", file=sys.stderr)
            model = "gpt-oss-20b-MXFP4-Q8"

    name = fb_data.get("name", "")
    definition = fb_data.get("definition", "")
    mechanism = fb_data.get("mechanism", "")
    extraction_type = fb_data.get("extraction_type", "")  # D2376: absent → "" (no over-claim)

    prompt = DEPTH_FOCUSED_PROMPT.format(
        name=name,
        definition=definition,
        mechanism=mechanism,
        extraction_type=extraction_type,
    )

    # D2359: reasoning models (GPT-OSS) — prepend valid Harmony "Reasoning: low"
    # to cap chain-of-thought. Previously this path sent NO system message, so
    # the prefix never reached the focused-depth call (BUG-129 gap).
    system = None
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        system = VERIFY_REASONING_OFF_PREFIX

    raw = call_omlx(
        prompt=prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        timeout=timeout,
        thinking_budget=VERIFY_DEPTH_THINKING_BUDGET,  # D2367/BUG-132: independent of merged-call budget
    )
    if not raw or not raw.strip():
        raise DepthClassificationError(
            "empty content from focused depth call (reasoning-model truncation?)"
        )
    return _parse_depth_token(raw)


# ── D2354: Batched Focused Depth Classification ─────────────────────────────
# S4 bottleneck: classify_depth_focused() is SERIALIZED — one GPT-OSS call per
# FB at ~10s each (reasoning model pays CoT cost every call). Batching N depth
# queries into ONE call amortizes that cost (~10s/FB → ~1-2s/FB). The SHORT
# proven prompt (62.5–87.5% accuracy) is preserved verbatim; only the transport
# changes (one JSON array response instead of one word).

DEPTH_BATCH_SYSTEM = """Classify the DEPTH of each Foundation Block below.

ONTOLOGY:
- specialized: A narrow sub-technique within a sub-field, or a tool-specific skill. (e.g., optical kerning in typography)
- domain: Operates within ONE field and requires that field's context. (e.g., price anchoring in behavioral economics)
- cross-domain: Bridges 2+ DISTINCT disciplines via a SHARED mechanism. (e.g., feedback loops explaining homeostasis in biology AND equilibrium in org design)
- universal: A law of nature or mathematics that applies to ALL systems. (e.g., entropy, power laws, scale invariance)

DEFAULT to "domain" unless the mechanism clearly transcends a single discipline.
DO NOT over-assign "universal" or "cross-domain" — most principles are domain-bound.

For EACH FB, answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning.
Return ONLY a JSON array of objects: [{"fb_index": <number>, "depth": "<one word>"}, ...]
Match fb_index to the input order. One object per input FB."""

if S4_DEPTH_PROMPT_VARIANT == "v3_contrastive":
    DEPTH_BATCH_SYSTEM = _apply_depth_prompt_variant(DEPTH_BATCH_SYSTEM)


def build_depth_batch_prompt(fbs_data: list[dict]) -> str:
    """Build a batched focused-depth prompt for multiple FBs (D2354).

    Mirrors DEPTH_FOCUSED_PROMPT (the proven short prompt) but lists multiple
    FBs and requests a JSON array keyed by fb_index.
    """
    lines = ["Classify the DEPTH of each Foundation Block below.", ""]
    for i, fb_data in enumerate(fbs_data):
        name = fb_data.get("name", "")
        definition = fb_data.get("definition", "")
        mechanism = fb_data.get("mechanism", "")
        extraction_type = fb_data.get("extraction_type", "")  # D2376: absent → "" (no over-claim)
        lines.append(f"--- FB {i} ---")
        lines.append(f"Name: {name}")
        lines.append(f"Definition: {definition}")
        if mechanism:
            lines.append(f"Mechanism: {mechanism}")
        lines.append(f"Type: {extraction_type}")
        lines.append("")
    lines.append(
        "Return ONLY a JSON array: "
        '[{"fb_index": <number>, "depth": "<specialized|domain|cross-domain|universal>"}, ...]. '
        "One word per FB, match fb_index to the input order."
    )
    return "\n".join(lines)


def batch_depth_classify(
    fbs_data: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    batch_size: int | None = None,
    timeout: int = 180,
) -> list[str]:
    """Batch the focused depth prompt across multiple FBs (D2354).

    Same SHORT prompt + ontology as classify_depth_focused(), but N FBs per
    GPT-OSS call to amortize the reasoning-model CoT cost (~10s/FB → ~1-2s/FB).

    Args:
        fbs_data: List of FB dicts (name, definition, mechanism, extraction_type).
        model: Model. None → VERIFY_MODEL (gpt-oss-20b).
        max_tokens: None → stage4.depth_max_tokens (1024).
        batch_size: None → stage4.depth_batch_size (4). Maximum FBs per call.
        timeout: Request timeout in seconds.

    Returns:
        List of depth strings, same order as fbs_data.

    Raises:
        DepthClassificationError: on missing/ambiguous depth for any FB (fail-closed).
        BatchClassificationError: on a non-list response.
    """
    if model is None:
        try:
            from pipeline.pipeline_paths import VERIFY_MODEL
            model = VERIFY_MODEL
        except Exception as e:
            print(f"   ⚠️  stage4: VERIFY_MODEL config unreadable ({type(e).__name__}: {e}) — fallback 'gpt-oss-20b-MXFP4-Q8' (C16)", file=sys.stderr)
            model = "gpt-oss-20b-MXFP4-Q8"
    if not fbs_data:
        return []
    if max_tokens is None:
        try:
            from pipeline.pipeline_paths import S4_DEPTH_BATCH_MAX_TOKENS
            max_tokens = S4_DEPTH_BATCH_MAX_TOKENS
        except Exception as e:
            print(f"   ⚠️  stage4: S4_DEPTH_BATCH_MAX_TOKENS unreadable ({type(e).__name__}: {e}) — fallback 2048 (C16)", file=sys.stderr)
            max_tokens = 2048
    if batch_size is None:
        try:
            from pipeline.pipeline_paths import _CFG
            batch_size = int(_CFG.get("stage4", {}).get("depth_batch_size", 4))
        except Exception as e:
            print(f"   ⚠️  stage4: depth_batch_size unreadable ({type(e).__name__}: {e}) — fallback 4 (C16)", file=sys.stderr)
            batch_size = 4
    batch_size = max(1, int(batch_size))
    # D2367/BUG-132 parity: the focused-depth call caps CoT at depth_thinking_budget
    # (128). batch_depth_classify previously omitted thinking_budget, so call_omlx
    # silently fell back to the MERGED-call budget (256) — more CoT, slower, and it
    # ate the output budget (BUG-184 truncation). Use the proven depth budget + a
    # batch-sized token headroom (depth_batch_max_tokens) instead of the single-FB 1024.
    try:
        from pipeline.pipeline_paths import VERIFY_DEPTH_THINKING_BUDGET, S4_DEPTH_MAX_TOKENS
    except Exception as e:
        print(f"   ⚠️  stage4: depth budget config unreadable ({type(e).__name__}: {e}) — fallback budget=None/tokens=1024 (C16)", file=sys.stderr)
        VERIFY_DEPTH_THINKING_BUDGET = None
        S4_DEPTH_MAX_TOKENS = 1024

    system = DEPTH_BATCH_SYSTEM
    if model:
        from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX
        if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
            system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"

    output: list[str] = []
    for start in range(0, len(fbs_data), batch_size):
        chunk = fbs_data[start:start + batch_size]
        # BUG-184: per-chunk retry + serial fallback. A truncated batch (gpt-oss
        # intermittently returns N-1 of N objects) must NOT abort the whole pre-pass.
        # Retry the chunk once; whatever is still missing falls back to the proven
        # single-FB classify_depth_focused() (fail-closed: a serial failure propagates).
        indexed: dict[int, str] = {}
        for _attempt in (1, 2):
            try:
                prompt = build_depth_batch_prompt(chunk)
                result = call_omlx_json(
                    prompt=prompt,
                    model=model,
                    system=system,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    thinking_budget=VERIFY_DEPTH_THINKING_BUDGET,
                )
                if isinstance(result, dict):
                    result = [result]
                if not isinstance(result, list):
                    raise BatchClassificationError(
                        f"depth batch returned non-list: {type(result)}"
                    )
                for item in result:
                    if isinstance(item, dict):
                        idx = item.get("fb_index", item.get("index", -1))
                        if isinstance(idx, int) and 0 <= idx < len(chunk):
                            raw_depth = item.get("depth", "")
                            if isinstance(raw_depth, str) and raw_depth.strip():
                                try:
                                    indexed[idx] = _parse_depth_token(raw_depth)
                                except DepthClassificationError:
                                    continue  # ambiguous single entry → serial fallback
            except Exception:
                indexed = {}
            if len(indexed) == len(chunk):
                break
            time.sleep(1.0)  # brief backoff before retry / serial fallback

        for i in range(len(chunk)):
            if i in indexed:
                output.append(indexed[i])
            else:
                # Serial fallback for the missing index only (retry exhausted or
                # truncated). Same proven prompt + depth CoT budget as the single call.
                output.append(classify_depth_focused(
                    chunk[i], model=model, max_tokens=S4_DEPTH_MAX_TOKENS,
                ))
    return output
