#!/usr/bin/env python3
"""discipline_macro_classify.py — Condition C: DEDICATED 3-way MACRO discipline classifier.

WHAT THIS MEASURES (BUG-622 fix path, D-2792/D-2793/D-2795/D-2796/D-2797)
-------------------------------------------------------------------------
The discipline axis is measurement-design-bound, not model-bound. Inter-rater
ceilings (owner re-label, 30 anchors): FINE 62-way 0.581 / COARSE 9-way 0.728 /
MACRO 3-way 0.766. The operative floor 0.800 is HUMAN-UNREACHABLE on this taxonomy,
so the gate is re-targeted to HUMAN PARITY (~0.73-0.77).

Two competing Condition arms are measured:
  Condition A (collapse): take the committed fine classifier (fbs.discipline) and
      deterministically collapse fine -> 10-group -> 3-way macro. Measured kappa 0.553
      (D-2797) — BELOW the ~0.65 ship threshold, dominated by 16 off-menu 'emerging'
      abstentions that a fine-axis remap can never recover.
  Condition C (this script): a DEDICATED classifier that predicts the 3-way macro
      bucket DIRECTLY (no fine-axis pass, no emerging remap). Ship iff kappa >= ~0.65.

SOURCE OF TRUTH (C12 — no hardcoded ontology)
---------------------------------------------
- Macro scheme + buckets:  config/discipline_macro_groups.yaml (3-way primary)
- Discipline -> group:     config/closed_menu_v8.json (disciplines[].group)
- Model + anchor + floor:  config/pipeline_config.yaml stage4.discipline_*
- Bucket -> members:       derived from closed_menu_v8.json via the macro group map

MODES (mirrors discipline_conformance_gate.py)
----------------------------------------------
  --dry-run   load + collapse + report bucket coverage; NO inference
  --selftest  verify the macro collapse + parse on fixed cases; NO inference
  --limit N   run only the first N anchor FBs (live smoke)
  --gate      exit 1 when macro kappa is below the human-parity floor
"""
from __future__ import annotations

import argparse
import json
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
    REPORTING_FLOOR,
    cohen_kappa,
    load_anchor,
    per_class_metrics,
)

# D-2884(a): fine->macro collapse lives in ONE home (C21) — this module is a consumer.
from pipeline.discipline_macro import load_macro, to_macro  # noqa: E402

# C20: named constants (no magic numbers).
DEFAULT_ANCHOR = "governance/discipline_anchor_rederived_v8_20261007.json"
DEFAULT_MENU = "config/closed_menu_v8.json"
DEFAULT_MACRO_GROUPS = "config/discipline_macro_groups.yaml"
# BUG-622/D-2797 (2026-10-03): gpt-oss-20b-MXFP4-Q8 is a HARMONY reasoning model.
# Its chain-of-thought is billed against max_tokens (reasoning + content share the
# budget). At 256 the ~380-token classification prompt leaves the model still in its
# reasoning phase when the budget is exhausted (finish_reason='length'), so `content`
# is never emitted and call_omlx misreports it as a cold-reload ("content missing").
# Measured: 256 -> content=None; 512/1024 -> correct content. 1024 matches
# models.verifier.max_tokens and gives headroom for occasional long reasoning.
MACRO_MAX_TOKENS: int = 1024
EMERGING_BUCKET: str = "emerging"  # explicit routing bucket, never a macro bucket


def load_config() -> tuple[str, str, float]:
    """Read stage4 discipline config keys from config (C12)."""
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    s4 = cfg.get("stage4", {})
    model = str(s4.get("discipline_model", "gpt-oss-20b-MXFP4-Q8"))
    anchor = str(s4.get("discipline_anchor_path", DEFAULT_ANCHOR))
    macro_floor = float(s4.get("discipline_macro_kappa_floor", 0.73))
    return model, anchor, macro_floor


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
        lines.append(f"SOURCE TEXT: {src[:600]}")
    return lines


def build_macro_prompt(fb: dict[str, Any], bucket_members: dict[str, list[str]]) -> str:
    """Prompt: pick exactly one of the macro buckets (3-way) or 'emerging'."""
    lines = [
        "Classify this foundation block into EXACTLY ONE academic discipline cluster.",
        "",
        "CLUSTERS:",
    ]
    for bucket, members in bucket_members.items():
        lines.append(f"- {bucket}: {', '.join(members)}")
    lines += [
        f"- {EMERGING_BUCKET}: use only if the block fits NONE of the above clusters",
        "",
    ]
    lines += _fb_block(fb)
    lines += [
        "",
        'Return a JSON object: {"macro": "<exact cluster name>"}',
    ]
    return "\n".join(lines)


def _norm(s: str) -> str:
    """Normalize a bucket string for comparison: collapse ws, casefold, fold '&'<->'and'."""
    return " ".join((s or "").replace("&", " and ").split()).casefold()


def canonical_bucket(raw: str, buckets: list[str]) -> str:
    """Map a raw model bucket string to a canonical bucket (exact -> substring)."""
    r = _norm(raw)
    if r == "":
        return EMERGING_BUCKET
    for b in buckets:
        if _norm(b) == r:
            return b
    for b in buckets:
        nb = _norm(b)
        if nb in r or r in nb:
            return b
    return EMERGING_BUCKET


def run_inference(examples: list[dict], model: str, bucket_members: dict[str, list[str]]) -> list[str]:
    """Classify each FB directly into the 3-way macro bucket (dedicated, no fine pass)."""
    from pipeline.omlx_call import call_omlx_json
    from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX

    system = "You are a precise JSON generator. Return ONLY valid JSON. No markdown, no explanation."
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"

    buckets = list(bucket_members.keys()) + [EMERGING_BUCKET]
    out: list[str] = []
    for e in examples:
        fb = {
            "name": e["name"],
            "definition": e["definition"],
            "mechanism": e["mechanism"],
            "boundary": e["boundary"],
            "consequence": e.get("consequence", ""),
            "source_text": e.get("source_text", ""),
        }
        prompt = build_macro_prompt(fb, bucket_members)
        res = call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=MACRO_MAX_TOKENS)
        if isinstance(res, list):
            res = res[0] if res else {}
        raw = res.get("macro", "") if isinstance(res, dict) else ""
        out.append(canonical_bucket(str(raw), buckets))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()

    model, cfg_anchor, macro_floor = load_config()
    anchor_path = args.anchor or cfg_anchor
    scheme, bucket_members, disc_to_bucket = load_macro()

    if args.selftest:
        cases = [
            ("machine learning", "Technical"),
            ("typography", "Technical"),
            ("neuroscience", "Human & Design"),
            ("strategic thinking", "Method & Business"),
            ("emerging", EMERGING_BUCKET),
            ("bogus-discipline", EMERGING_BUCKET),
        ]
        ok = True
        for disc, want in cases:
            got = to_macro(disc, disc_to_bucket)
            ok &= got == want
            print(f"  {'OK' if got == want else 'FAIL'} collapse {disc!r} -> {got!r} (want {want!r})")
        # parse canonicalization
        parse_cases = [("Technical", "Technical"), ("human and design", "Human & Design"), ("", EMERGING_BUCKET)]
        buckets = list(bucket_members.keys()) + [EMERGING_BUCKET]
        for raw, want in parse_cases:
            got = canonical_bucket(raw, buckets)
            ok &= got == want
            print(f"  {'OK' if got == want else 'FAIL'} parse {raw!r} -> {got!r} (want {want!r})")
        return 0 if ok else 1

    examples = load_anchor(anchor_path)
    if args.limit is not None:
        examples = examples[: args.limit]

    gold = [to_macro(e["discipline"], disc_to_bucket) for e in examples]
    print(f"discipline MACRO classifier (Condition C): scheme={scheme}  model={model}")
    print(f"  N = {len(examples)}   anchor = {anchor_path}")
    print(f"  buckets = {sorted(set(gold))}   (human 3-way ceiling 0.766, D-2796)")
    print(f"  macro floor (human parity) = {macro_floor}")

    if args.dry_run:
        print("  gold bucket distribution:", dict(Counter(gold)))
        print("  DRY-RUN (no inference). live run: python3 scripts/discipline_macro_classify.py [--gate] [--limit N]")
        return 0

    pred = run_inference(examples, model, bucket_members)
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    pc = per_class_metrics(gold, pred)

    print(f"  raw agreement (accuracy): {acc:.4f}   (reported, NOT gated)")
    print(f"  Cohen's kappa:            {kappa:.4f}   (vs 0.766 human ceiling)")
    print("  per-bucket P/R/F1:")
    for b in sorted(pc):
        m = pc[b]
        print(f"    {b[:24]:<24} P={m['precision']} R={m['recall']} F1={m['f1']} (gold n={m['n_gold']})")

    if args.gate and kappa < macro_floor:
        print(f"FAIL-CLOSED: macro kappa {kappa:.4f} < human-parity floor {macro_floor}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
