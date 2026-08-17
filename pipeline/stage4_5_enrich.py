#!/usr/bin/env python3
"""
stage4_5_enrich.py — Post-S4 enrichment (F1 / D2400)
================================================================================
Authority: CONSTITUTION.md §3 (pipeline), D2400 (field-production contract)

D2400 established that `related_fbs` is produced at S4 (`compute_fb_relationships`),
but three schema-declared fields have NO producer anywhere in the pipeline:
  - `prerequisite_fbs`  — directed dependency edges (FB A must be understood first)
  - `contradicts_fbs`   — bidirectional conflict edges (anti-pattern pairs)
  - `procedural_skill`  — per-FB: an executable tool/technique name (Layer-2 value)

Contract (D2400):
  * S6 is persistence-only — it must never derive/classify.
  * S4 is the ~39h bottleneck — this enrichment must NOT be inlined into S4.
  * Therefore this is a SEPARATE post-S4 stage, gated behind `stage4_5.enabled`.

Design:
  * Phase 1 — `procedural_skill`: one LLM call per FB (like depth/domains).
  * Phase 2 — `prerequisite_fbs` + `contradicts_fbs`: candidate FB pairs are
    proposed cheaply via definition cosine similarity (reusing the same signal
    as `compute_fb_relationships`), then ONE LLM call classifies the directed
    dependency and/or conflict. This avoids the infeasible O(n^2) LLM pass.

Model: `stage4_5.model` (default = the S4 classifier gpt-oss-20b) — R5: a
different family from the S2 generator (qwen). temp=0.0 (R7).

Usage:
    python3 pipeline/stage4_5_enrich.py
    python3 pipeline/stage4_5_enrich.py --model <name> --no-edges

Reads:  STAGE4_CHECKPOINT   (classified FBs, already carrying related_fbs)
Writes: STAGE4_5_CHECKPOINT (enriched FBs — S5's loader prefers this when present)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write  # D2332: fail-closed JSONL boundary + C6 atomic write
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.pipeline_paths import (
    S4_5_CHECKPOINT_INTERVAL,
    S4_5_EDGE_CANDIDATE_THRESHOLD,
    S4_5_EDGE_ENABLED,
    S4_5_EDGE_MAX_CANDIDATES_PER_FB,
    S4_5_EDGE_MAX_TOKENS,
    S4_5_ENABLED,
    S4_5_MAX_FAILED_RATIO,
    S4_5_MODEL,
    S4_5_PROCEDURAL_ENABLED,
    S4_5_PROCEDURAL_MAX_TOKENS,
    STAGE4_5_CHECKPOINT,
    STAGE4_CHECKPOINT,
    VERIFY_REASONING_OFF_MODELS,
    VERIFY_REASONING_OFF_PREFIX,
)
from pipeline.stamp import get_pipeline_commit

# ── Prompts ─────────────────────────────────────────────────────────────────
# Convention (matches stage4_merged_call.py): natural-language prompt templates
# live as module constants; every numeric/flag/model value lives in config/*.yaml
# (C12). Prompts are "logic", not "values".
PROCEDURAL_SKILL_SYSTEM = (
    "You classify whether a Foundation Block (FB) describes a PROCEDURAL SKILL: a "
    "repeatable technique or tool that an agent could execute as a named function. "
    "Most FBs are DECLARATIVE knowledge (facts, models, heuristics), NOT procedural "
    'skills. Return ONLY a JSON object: {"procedural_skill": "<snake_case_name or empty>"}.\n'
    "If the FB is declarative (no executable procedure), return an empty string. "
    "If it IS a procedure, return a concise snake_case function name "
    "(e.g. frame_price_as_loss_avoidance). Do not emit reasoning."
)

PROCEDURAL_SKILL_PROMPT = (
    "Foundation Block:\n"
    "name: {name}\n"
    "definition: {definition}\n"
    "mechanism: {mechanism}\n"
    "application: {application}\n"
    "extraction_type: {extraction_type}\n"
    "\n"
    "Does this FB describe a procedural skill (an executable technique/tool)? "
    'Return ONLY JSON: {{"procedural_skill": "snake_case_name_or_empty"}}.'
)

EDGE_SYSTEM = (
    "You classify the RELATIONSHIP between two Foundation Blocks (A and B). "
    'Return ONLY a JSON object: {{"prerequisite": "<none|A_requires_B|B_requires_A>", '
    '"contradicts": <true|false>}}.\n'
    "prerequisite: A_requires_B means A depends on B (B must be understood FIRST). "
    "B_requires_A means B depends on A. Use none when there is no clear dependency.\n"
    "contradicts: true only when the two FBs make logically conflicting or mutually "
    "incompatible claims; otherwise false.\n"
    "Be conservative — only assert a dependency/conflict when the two definitions "
    "clearly support it. Do not emit reasoning."
)

EDGE_PROMPT = (
    "FB A:\n"
    "name: {name_a}\n"
    "definition: {definition_a}\n"
    "mechanism: {mechanism_a}\n"
    "\n"
    "FB B:\n"
    "name: {name_b}\n"
    "definition: {definition_b}\n"
    "mechanism: {mechanism_b}\n"
    "\n"
    'Return ONLY JSON: {{"prerequisite": "none|A_requires_B|B_requires_A", '
    '"contradicts": false}}.'
)

# ── Validators / normalizers ────────────────────────────────────────────────
_SNAKE_RE = re.compile(r"[^a-z0-9]+")


def _normalize_snake_case(raw: str | None) -> str:
    """Normalize a model-returned label to a safe snake_case identifier (or "")."""
    if not isinstance(raw, str):
        return ""
    cleaned = _SNAKE_RE.sub("_", raw.lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    if cleaned and not cleaned[0].isalpha():
        cleaned = f"f_{cleaned}"
    return cleaned


def _reasoning_off_system(base: str, model: str) -> str:
    """Prepend the Harmony reasoning-off prefix for reasoning models (D2249)."""
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        return f"{VERIFY_REASONING_OFF_PREFIX}\n\n{base}"
    return base


# ── Phase 1: procedural_skill ───────────────────────────────────────────────
def classify_procedural_skill(
    fb: dict,
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 120,
) -> str:
    """Classify whether an FB is a procedural skill (returns snake_case name or "").

    Args:
        fb: FB dict with name, definition, mechanism, application, extraction_type.
        model: Model to use. None → `stage4_5.model` (default S4 classifier).
        max_tokens: Output token budget. None → `stage4_5.procedural_skill_max_tokens`.
        timeout: Request timeout in seconds.

    Returns:
        A snake_case function name, or "" when the FB is declarative knowledge.

    Raises:
        ValueError: on a non-dict result or a missing `procedural_skill` key
            (C16 — a malformed response is a failure, never a silent "").
    """
    if model is None:
        model = S4_5_MODEL
    if max_tokens is None:
        max_tokens = S4_5_PROCEDURAL_MAX_TOKENS

    prompt = PROCEDURAL_SKILL_PROMPT.format(
        name=fb.get("name", ""),
        definition=fb.get("definition", ""),
        mechanism=fb.get("mechanism", ""),
        application=fb.get("application", ""),
        extraction_type=fb.get("extraction_type", ""),
    )
    system = _reasoning_off_system(PROCEDURAL_SKILL_SYSTEM, model)

    result = call_omlx_json(prompt=prompt, model=model, system=system,
                            max_tokens=max_tokens, timeout=timeout)
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict):
        raise ValueError(f"procedural_skill call returned non-dict: {type(result)}")
    if "procedural_skill" not in result:
        raise ValueError("procedural_skill call returned no 'procedural_skill' key")
    return _normalize_snake_case(result.get("procedural_skill"))


# ── Phase 2: prerequisite/contradicts edges ─────────────────────────────────
def classify_fb_edge(
    fb_a: dict,
    fb_b: dict,
    model: str | None = None,
    max_tokens: int | None = None,
    timeout: int = 120,
) -> dict:
    """Classify the directed relationship between two FBs (A=fb_a, B=fb_b).

    Args:
        fb_a: FB dict for "A".
        fb_b: FB dict for "B".
        model: Model. None → `stage4_5.model`.
        max_tokens: Output budget. None → `stage4_5.edge_max_tokens`.
        timeout: Request timeout in seconds.

    Returns:
        `{"prerequisite": "none"|"A_requires_B"|"B_requires_A", "contradicts": bool}`.

    Raises:
        ValueError: on a malformed/ambiguous result (C16 — never silently drop).
    """
    if model is None:
        model = S4_5_MODEL
    if max_tokens is None:
        max_tokens = S4_5_EDGE_MAX_TOKENS

    prompt = EDGE_PROMPT.format(
        name_a=fb_a.get("name", ""),
        definition_a=fb_a.get("definition", ""),
        mechanism_a=fb_a.get("mechanism", ""),
        name_b=fb_b.get("name", ""),
        definition_b=fb_b.get("definition", ""),
        mechanism_b=fb_b.get("mechanism", ""),
    )
    system = _reasoning_off_system(EDGE_SYSTEM, model)

    result = call_omlx_json(prompt=prompt, model=model, system=system,
                            max_tokens=max_tokens, timeout=timeout)
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict):
        raise ValueError(f"edge call returned non-dict: {type(result)}")

    prerequisite = result.get("prerequisite")
    if prerequisite not in ("none", "A_requires_B", "B_requires_A"):
        raise ValueError(f"edge call returned invalid prerequisite={prerequisite!r}")

    contradicts = result.get("contradicts")
    if not isinstance(contradicts, bool):
        raise ValueError(f"edge call returned invalid contradicts={contradicts!r}")
    return {"prerequisite": prerequisite, "contradicts": contradicts}


def _candidate_pairs(
    fbs: list[dict],
    threshold: float,
    max_per_fb: int,
) -> list[tuple[int, int]]:
    """Propose candidate FB pairs via definition cosine similarity (no LLM).

    Mirrors the semantic-near signal in `compute_fb_relationships` (S4), but
    returns an index-pair list for the enrichment LLM pass. Candidates are the
    upper-triangle pairs whose cosine similarity >= threshold, capped per FB to
    prevent a dense hub from generating O(n) LLM calls.

    Args:
        fbs: FB dicts (each with a `definition`).
        threshold: Minimum cosine similarity to propose a pair.
        max_per_fb: Maximum candidate pairs proposed per FB.

    Returns:
        List of (i, j) index pairs (i < j), deduplicated, capped per FB.
    """
    n = len(fbs)
    if n < 2:
        return []

    try:
        import numpy as np

        from pipeline.embeddings import embed_texts_bge_m3

        definitions: list[str] = [fb.get("definition", "")[:500] for fb in fbs]
        embeddings: np.ndarray = embed_texts_bge_m3(definitions)
        norms: np.ndarray = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        embeddings = embeddings / norms
        sim: np.ndarray = embeddings @ embeddings.T  # n×n cosine matrix
    except Exception as e:
        print(f"   ⚠️  Embedding failed ({e}) — no edge candidates proposed")
        return []

    pairs: list[tuple[int, int]] = []
    for i in range(n):
        row = [(float(sim[i, j]), j) for j in range(i + 1, n) if float(sim[i, j]) >= threshold]
        row.sort(reverse=True)
        for _s, j in row[:max_per_fb]:
            pairs.append((i, j))
    return pairs


# ── Orchestration ───────────────────────────────────────────────────────────
def _write_enriched_checkpoint(
    fbs: list[dict],
    procedural_done: set[str],
    edge_pairs_done: set[str],
    state_path: str,
) -> None:
    """C6 atomic write of the enriched checkpoint + resume sidecar."""
    safe_write(
        STAGE4_5_CHECKPOINT,
        "\n".join(json.dumps(fb, ensure_ascii=False) for fb in fbs) + "\n",
        force_shrink=False,
    )
    state = {
        "procedural_done": sorted(procedural_done),
        "edge_pairs_done": sorted(edge_pairs_done),
    }
    safe_write(state_path, json.dumps(state), force_shrink=False)


def _apply_edge_relation(fbs: list[dict], i: int, j: int, rel: dict) -> None:
    """Apply a classified edge relation to two FBs (mutates in place).

    Semantics match `retrieve.py` graph_expand:
      * `prerequisite_fbs` is directed upstream (FB → its prerequisites).
        "A_requires_B" → B is a prerequisite of A → A.prerequisite_fbs += B.
      * `contradicts_fbs` is bidirectional (both sides get the counterpart).
    """
    if rel["prerequisite"] == "A_requires_B":
        fbs[i].setdefault("prerequisite_fbs", []).append(fbs[j]["fb_id"])
    elif rel["prerequisite"] == "B_requires_A":
        fbs[j].setdefault("prerequisite_fbs", []).append(fbs[i]["fb_id"])
    if rel["contradicts"]:
        fbs[i].setdefault("contradicts_fbs", []).append(fbs[j]["fb_id"])
        fbs[j].setdefault("contradicts_fbs", []).append(fbs[i]["fb_id"])


def _same_fb_id_multiset(a: list[dict], b: list[dict]) -> bool:
    """True when two FB lists carry the same fb_id multiset (resume safety)."""
    return sorted(fb.get("fb_id", "") for fb in a) == sorted(fb.get("fb_id", "") for fb in b)


def run_stage4_5(
    model: str | None = None,
    do_procedural: bool | None = None,
    do_edges: bool | None = None,
) -> list[dict]:
    """Run the post-S4 enrichment (F1/D2400).

    Args:
        model: Enrichment model override (None → `stage4_5.model`).
        do_procedural: Override the procedural_skill phase (None → config flag).
        do_edges: Override the edge phase (None → config flag).

    Returns the enriched FB list. Writes STAGE4_5_CHECKPOINT atomically and
    exits non-zero on a fail-closed ratio breach (C16/D2338 semantics).
    """
    if not S4_5_ENABLED:
        print("ℹ️  Stage 4.5 enrichment DISABLED (stage4_5.enabled=false). Nothing to do.")
        return []

    if not check_omlx_health():
        print("❌ OMLX is not running.")
        sys.exit(1)

    if not STAGE4_CHECKPOINT.exists():
        print("❌ Stage 4 checkpoint not found. Run stage4_merge.py first.")
        sys.exit(1)

    model = model or S4_5_MODEL
    procedural_enabled = S4_5_PROCEDURAL_ENABLED if do_procedural is None else do_procedural
    edges_enabled = S4_5_EDGE_ENABLED if do_edges is None else do_edges

    fbs: list[dict] = load_jsonl(STAGE4_CHECKPOINT, context="S4 checkpoint")
    n = len(fbs)
    print(f"🧩 Stage 4.5: Post-S4 enrichment — {n} FBs (F1/D2400)")
    print(f"   Model: {model} (R5: cross-family from S2 generator)")
    print(f"   procedural_skill={procedural_enabled} edges={edges_enabled}")

    state_path = str(STAGE4_5_CHECKPOINT) + ".state.json"
    procedural_done: set[str] = set()
    edge_pairs_done: set[str] = set()

    # ── Resume (mirrors D2370 intra-stage checkpoint pattern) ───────────────
    if STAGE4_5_CHECKPOINT.exists() and os.path.exists(state_path):
        try:
            resume_fbs = load_jsonl(STAGE4_5_CHECKPOINT, context="S4.5 checkpoint")
            with open(state_path) as sf:
                resume_state = json.load(sf)
            # Guard: a stale enriched checkpoint from a different S4 run must not
            # silently resume — require identical fb_id multisets.
            if _same_fb_id_multiset(resume_fbs, fbs):
                fbs = resume_fbs
                procedural_done = set(resume_state.get("procedural_done", []))
                edge_pairs_done = set(resume_state.get("edge_pairs_done", []))
                print(f"   📋 Resuming: {len(procedural_done)} procedural done, "
                      f"{len(edge_pairs_done)} edge pairs done")
            else:
                print("   ⚠️  S4.5 checkpoint fb_ids mismatch S4 — starting fresh")
        except Exception as e:
            print(f"   ⚠️  S4.5 resume checkpoint corrupt ({type(e).__name__}: {e}) — starting fresh")
            procedural_done = set()
            edge_pairs_done = set()

    procedural_total = 0
    procedural_failed = 0
    edge_total = 0
    edge_failed = 0

    # ── Phase 1: procedural_skill (per-FB) ──────────────────────────────────
    if procedural_enabled:
        for i, fb in enumerate(fbs, 1):
            fb_id = fb.get("fb_id", "")
            if fb_id and fb_id in procedural_done:
                continue
            try:
                fb["procedural_skill"] = classify_procedural_skill(fb, model)
                procedural_total += 1
            except Exception as e:
                procedural_total += 1
                procedural_failed += 1
                fb["procedural_skill"] = ""
                fb["procedural_skill_error"] = f"{type(e).__name__}: {e}"[:200]
                print(f"   ⚠️  procedural_skill failed for '{fb.get('name', '')[:30]}': {e}")
            if fb_id:
                procedural_done.add(fb_id)
            if S4_5_CHECKPOINT_INTERVAL > 0 and i % S4_5_CHECKPOINT_INTERVAL == 0:
                _write_enriched_checkpoint(fbs, procedural_done, edge_pairs_done, state_path)

    # ── Phase 2: prerequisite/contradicts edges ─────────────────────────────
    if edges_enabled:
        for fb in fbs:
            fb.setdefault("prerequisite_fbs", [])
            fb.setdefault("contradicts_fbs", [])
        pairs = _candidate_pairs(fbs, S4_5_EDGE_CANDIDATE_THRESHOLD, S4_5_EDGE_MAX_CANDIDATES_PER_FB)
        print(f"   Edge candidates: {len(pairs)} pairs")
        for (i, j) in pairs:
            key = f"{i}:{j}"
            if key in edge_pairs_done:
                continue
            try:
                rel = classify_fb_edge(fbs[i], fbs[j], model)
                edge_total += 1
                _apply_edge_relation(fbs, i, j, rel)
            except Exception as e:
                edge_total += 1
                edge_failed += 1
                print(f"   ⚠️  edge classification failed for pair ({i},{j}): {e}")
            edge_pairs_done.add(key)
            if S4_5_CHECKPOINT_INTERVAL > 0 and edge_total % S4_5_CHECKPOINT_INTERVAL == 0:
                _write_enriched_checkpoint(fbs, procedural_done, edge_pairs_done, state_path)

    # ── Provenance (R14): record enrichment model + commit, keep S2 gen_model ──
    commit = get_pipeline_commit()
    for fb in fbs:
        fb["enrichment_model"] = model
        fb["enrichment_pipeline_commit"] = commit

    # Final atomic write + clear resume sidecar semantics (completed run)
    _write_enriched_checkpoint(fbs, procedural_done, edge_pairs_done, state_path)

    print(f"   procedural_skill: {procedural_total - procedural_failed}/{procedural_total} ok")
    print(f"   edges:            {edge_total - edge_failed}/{edge_total} ok")
    print(f"📋 Enriched checkpoint: {STAGE4_5_CHECKPOINT}")

    total_ops = procedural_total + edge_total
    total_failed = procedural_failed + edge_failed
    if total_ops > 0:
        ratio = total_failed / total_ops
        if ratio > S4_5_MAX_FAILED_RATIO:
            print(f"❌ Stage 4.5 FAILED: {total_failed}/{total_ops} enrichment ops failed "
                  f"({ratio:.1%} > max_failed_ratio={S4_5_MAX_FAILED_RATIO})")
            sys.exit(1)
        if total_failed > 0:
            print(f"⚠️  Stage 4.5 CONDITIONAL_SUCCESS: {total_failed} op(s) within "
                  f"tolerance ({ratio:.1%} ≤ {S4_5_MAX_FAILED_RATIO})")
            sys.exit(2)
    return fbs


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4.5: post-S4 enrichment (F1/D2400)")
    parser.add_argument("--model", default=None, help="Override enrichment model (default: stage4_5.model)")
    parser.add_argument("--no-procedural", action="store_true", help="Skip procedural_skill phase")
    parser.add_argument("--no-edges", action="store_true", help="Skip prerequisite/contradicts phase")
    args = parser.parse_args()

    run_stage4_5(
        model=args.model,
        do_procedural=(False if args.no_procedural else None),
        do_edges=(False if args.no_edges else None),
    )


if __name__ == "__main__":
    main()
