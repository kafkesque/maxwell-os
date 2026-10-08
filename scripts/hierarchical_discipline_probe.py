#!/usr/bin/env python3
"""hierarchical_discipline_probe.py — generative two-stage discipline classifier probe (BUG-622).

WHAT IT MEASURES
----------------
Whether TWO-STAGE generative classification — (1) coarse group (~9 from the
taxonomy `group` field) then (2) fine discipline within the predicted group's
SMALL menu — beats the flat single-shot production classifier of record for S4
discipline conformance against the human-owner discipline anchor
(governance/discipline_anchor_rederived_v8_20261007.json, 204 owner-finalized rows).

RATIONALE (D-2775): the D-2774 closed-62-menu injection was NEGATIVE (0.344 vs
0.452 baseline) — the binding constraint is gpt-oss-20b's discrimination QUALITY
across the 62-label space. Hierarchical decomposition shrinks the per-decision
confusion set from 61 -> <=11 (stage 1 picks 1 of 9 groups; stage 2 picks 1 of
<=11 labels within that group), which is the D-2775-recommended future-proof fix
that has NOT yet been measured on the production generative classifier.

STATISTIC (D-2611): Cohen's kappa (chance-corrected), never bare accuracy, on the
49-class skewed prior. Reports coarse-group accuracy + fine kappa + fallback count.

CLASSIFIER OF RECORD (D-2770): the FLAT baseline arm mirrors production exactly —
merged_cribs_classify then map_to_canonical_with_fallback. The HIERARCHICAL arm
is the probe under test; it is NOT production and must NOT be wired in until it
clears the operative floor.

MODES
-----
  --dry-run       load + join + report group coverage; NO inference
  --mode flat     production baseline only (merged_cribs_classify + remap)
  --mode coarse   coarse-only (9-way group) measure-gate (D-2790)
  --mode hier     two-stage hierarchical only
  --mode both     both arms on the SAME rows (head-to-head A/B)
  --gate          exit 1 when coarse kappa is below the coarse floor (D-2790)
  --limit N       run only the first N anchor FBs (default: full 204)
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for p in (str(REPO), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Reuse the production conformance gate's load/join + statistics (no drift).
from discipline_conformance_gate import (  # noqa: E402
    OPERATIVE_FLOOR,
    REPORTING_FLOOR,
    cohen_kappa,
    load_anchor,
    per_class_metrics,
)

# C20: named constants (no magic numbers).
SOURCE_TRUNC: int = 600
FALLBACK_MODEL: str = "gpt-oss-20b-MXFP4-Q8"
FALLBACK_MAX_TOKENS: int = 2048
COARSE_FLOOR: float = 0.90  # D-2790: coarse (9-way) kappa gate; two-stage viable only if >= this

# C12: paths overridable via env (same convention as train_hierarchical_classifier.py).
TAXONOMY = Path(os.environ.get("TAXONOMY_YAML", REPO / "config" / "taxonomy_v5.yaml"))
ANCHOR = Path(
    os.environ.get(
        "DISCIPLINE_ANCHOR",
        REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json",
    )
)


def load_config() -> tuple[str, str, int, float]:
    """Read stage4 discipline conformance keys from config (C12)."""
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    s4 = cfg.get("stage4", {})
    model = str(s4.get("discipline_model", FALLBACK_MODEL))
    anchor = str(s4.get("discipline_anchor_path", str(ANCHOR)))
    max_tokens = int(s4.get("merged_call_max_tokens", FALLBACK_MAX_TOKENS))
    coarse_floor = float(s4.get("discipline_coarse_kappa_floor", COARSE_FLOOR))
    return model, anchor, max_tokens, coarse_floor


def load_taxonomy() -> tuple[dict[str, list[str]], dict[str, list[tuple[str, str]]], dict[str, str]]:
    """Load the 9-group coarse taxonomy + per-discipline definitions.

    Returns:
        groups: group name -> [discipline canonical names]
        defs:   group name -> [(canonical, definition)]
        gold_to_group: canonical discipline -> group (for coarse-accuracy scoring)
    """
    import yaml

    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = {}
    defs: dict[str, list[tuple[str, str]]] = {}
    gold_to_group: dict[str, str] = {}
    for d in tax.get("disciplines", []):
        gname = d["group"]
        canon = d["canonical"]
        definition = d.get("definition", "")
        groups.setdefault(gname, []).append(canon)
        defs.setdefault(gname, []).append((canon, definition))
        gold_to_group[canon] = gname
    return groups, defs, gold_to_group


def _fb_block(fb: dict[str, Any]) -> list[str]:
    """Render the shared foundation-block text block for a prompt."""
    lines = [
        "FOUNDATION BLOCK:",
        f"NAME: {fb['name']}",
        f"DEFINITION: {fb['definition']}",
    ]
    for key in ("mechanism", "boundary", "consequence"):
        if fb.get(key):
            lines.append(f"{key.upper()}: {fb[key]}")
    src = fb.get("source_text", "")
    if src:
        lines.append(f"SOURCE TEXT: {src[:SOURCE_TRUNC]}")
    return lines


def build_coarse_prompt(fb: dict[str, Any], groups: dict[str, list[str]]) -> str:
    """Stage 1 prompt: pick exactly one of the 9 coarse groups."""
    lines = [
        "Classify this foundation block into EXACTLY ONE of the following academic discipline groups.",
        "",
        "GROUPS:",
    ]
    for gname, members in groups.items():
        lines.append(f"- {gname}: {', '.join(members)}")
    lines.append("")
    lines += _fb_block(fb)
    lines += [
        "",
        'Return a JSON object: {"group": "<exact group name>"}',
    ]
    return "\n".join(lines)


def build_fine_prompt(
    fb: dict[str, Any], gname: str, disciplines: list[tuple[str, str]]
) -> str:
    """Stage 2 prompt: pick exactly one discipline from the predicted group's small menu."""
    lines = [
        f"Classify this foundation block into EXACTLY ONE of the following disciplines "
        f"(all belong to the group '{gname}').",
        "",
        "DISCIPLINES:",
    ]
    for canon, definition in disciplines:
        lines.append(f"- {canon}: {definition}")
    lines.append("")
    lines += _fb_block(fb)
    lines += [
        "",
        'Return a JSON object: {"discipline": "<exact discipline name>"}',
    ]
    return "\n".join(lines)


def _system(model: str) -> str:
    """Classifier system message, mirroring production reasoning-off handling (D2249)."""
    from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX

    msg = "You are a precise classifier. Return ONLY valid JSON — no markdown, no explanation."
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        msg = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{msg}"
    return msg


def _parse(result: Any) -> str:
    """Unwrap list/dict JSON result to a stripped string (BUG-080 guards)."""
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict):
        return ""
    return str(result.get("group", result.get("discipline", "")) or "").strip()


def classify_hier(
    fb: dict[str, Any],
    model: str,
    groups: dict[str, list[str]],
    defs: dict[str, list[tuple[str, str]]],
    system: str,
    max_tokens: int,
) -> tuple[str, str | None]:
    """Two-stage classification. Returns (discipline_raw, coarse_group_or_None).

    A `None` coarse group means stage 1 returned an off-menu group; the caller
    must fall back (never silently commit an off-menu discipline — C16).
    max_tokens mirrors production merged_call_max_tokens so gpt-oss's reasoning
    budget (VERIFY_THINKING_BUDGET) has room before the JSON content (D2359).
    """
    from pipeline.omlx_call import call_omlx_json

    r1 = call_omlx_json(
        prompt=build_coarse_prompt(fb, groups),
        model=model,
        system=system,
        max_tokens=max_tokens,
    )
    group = _parse(r1)
    if group not in groups:
        return "", None

    r2 = call_omlx_json(
        prompt=build_fine_prompt(fb, group, defs[group]),
        model=model,
        system=system,
        max_tokens=max_tokens,
    )
    return _parse(r2), group


def classify_coarse(
    fb: dict[str, Any],
    model: str,
    groups: dict[str, list[str]],
    system: str,
    max_tokens: int,
) -> str:
    """Coarse-only (9-way group) classification (D-2790 measure-gate).

    Uses the SAME stage-1 prompt the two-stage would use, so the measured coarse
    kappa is a faithful predictor of two-stage stage-1 error propagation. Returns
    the predicted group name, or "" when the model returns an off-menu group
    (fail-closed — never silently accept an off-menu group).
    """
    from pipeline.omlx_call import call_omlx_json

    r1 = call_omlx_json(
        prompt=build_coarse_prompt(fb, groups),
        model=model,
        system=system,
        max_tokens=max_tokens,
    )
    group = _parse(r1)
    return group if group in groups else ""


def classify_flat(fb: dict[str, Any], model: str) -> str:
    """Production baseline: merged_cribs_classify + map_to_canonical_with_fallback."""
    from pipeline.stage4_merge import CANONICAL_DISCIPLINES, map_to_canonical_with_fallback
    from pipeline.stage4_merged_call import merged_cribs_classify
    from pipeline.schemas import get_synonym_index

    synonym_index = get_synonym_index("discipline")
    res = merged_cribs_classify(fb, model=model)
    if isinstance(res, list):
        res = res[0] if res else {}
    raw = res.get("discipline", "") if isinstance(res, dict) else ""
    return map_to_canonical_with_fallback(raw, "discipline", synonym_index, CANONICAL_DISCIPLINES)


def _remap(raw: str) -> str:
    from pipeline.stage4_merge import CANONICAL_DISCIPLINES, map_to_canonical_with_fallback
    from pipeline.schemas import get_synonym_index

    return map_to_canonical_with_fallback(
        raw, "discipline", get_synonym_index("discipline"), CANONICAL_DISCIPLINES
    )


def _report(tag: str, gold: list[str], pred: list[str]) -> float:
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    print(f"  [{tag}] N={len(gold)}  raw agreement={acc:.4f}  Cohen kappa={kappa:.4f}")
    return kappa


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default=None)
    ap.add_argument("--mode", choices=["flat", "coarse", "hier", "both"], default="hier")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    model, cfg_anchor, max_tokens, coarse_floor = load_config()
    anchor_path = args.anchor or cfg_anchor
    groups, defs, gold_to_group = load_taxonomy()
    examples = load_anchor(anchor_path)
    if args.limit is not None:
        examples = examples[: args.limit]

    gold = [e["discipline"] for e in examples]
    gold_groups = [gold_to_group.get(g, "?") for g in gold]
    print(f"hierarchical discipline probe: {anchor_path}")
    print(f"  N = {len(examples)}   model = {model}   mode = {args.mode}")
    print(f"  coarse groups = {len(groups)}   gold distinct disciplines = {len(set(gold))}")
    uncovered = sorted(set(gold) - set(gold_to_group))
    if uncovered:
        print(f"  ⚠️  gold disciplines with NO group: {uncovered}")
    print(f"  floors: reporting {REPORTING_FLOOR} / operative {OPERATIVE_FLOOR}")

    if args.dry_run:
        print("  DRY-RUN (no inference): group coverage ok; aborting before inference.")
        return 0

    system = _system(model)

    if args.mode in ("flat", "both"):
        flat_pred = [classify_flat(e, model) for e in examples]
        _report("flat (production baseline)", gold, flat_pred)

    if args.mode == "coarse":
        coarse_pred: list[str] = []
        offmenu = 0
        for e in examples:
            g = classify_coarse(e, model, groups, system, max_tokens)
            if g == "":
                offmenu += 1
            coarse_pred.append(g)
        kappa = cohen_kappa(gold_groups, coarse_pred)
        acc = sum(1 for gp, gg in zip(coarse_pred, gold_groups) if gp == gg) / len(examples)
        print(f"  [coarse-only (9-way)] N={len(examples)}  raw agreement={acc:.4f}  "
              f"Cohen kappa={kappa:.4f}  off-menu={offmenu}")
        verdict = "ADOPT two-stage" if kappa >= coarse_floor else "DO NOT build two-stage"
        print(f"  coarse gate floor = {coarse_floor}  -> {verdict}")
        if args.gate:
            return 0 if kappa >= coarse_floor else 1
        return 0

    if args.mode in ("hier", "both"):
        hier_pred: list[str] = []
        coarse_pred: list[str] = []
        fallback = 0
        for e in examples:
            raw, group = classify_hier(e, model, groups, defs, system, max_tokens)
            if group is None:
                # Stage 1 off-menu -> degenerate to production baseline (report + count).
                fallback += 1
                hier_pred.append(classify_flat(e, model))
                coarse_pred.append("")
            else:
                coarse_pred.append(group)
                hier_pred.append(_remap(raw))
        _report("hier (two-stage)", gold, hier_pred)
        coarse_correct = sum(1 for gp, gg in zip(coarse_pred, gold_groups) if gp == gg)
        n_nonfallback = len(examples) - fallback
        print(f"  coarse-group accuracy: {coarse_correct}/{n_nonfallback} "
              f"({coarse_correct / n_nonfallback:.4f}) on {n_nonfallback} non-fallback rows; "
              f"fallback (stage-1 off-menu) = {fallback}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
