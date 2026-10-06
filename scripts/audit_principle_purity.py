#!/usr/bin/env python3
"""audit_principle_purity.py — deterministic principle-purity triage (D275b).

Purpose
-------
Audit the S2 checkpoint for `content_type: principle` records that are NOT
actually self-contained transferable rules (KNOW/APPLY) per D275b. This is a
READ-ONLY triage — it emits a versioned candidate list for OWNER adjudication.
It does NOT reclassify and does NOT write to pipeline output (C6-safe: tempfile
+ os.replace; the artifact is a fresh file, never an in-place overwrite).

Why deterministic (D-343)
-------------------------
content_type LLM classification measured -2.98pp vs a constant-answer baseline.
So we never call a model here. The signals below are high-precision TRIAGE
filters: they isolate the small candidate set the owner must judge, NOT an
auto-classifier. The D275b discriminator (EXECUTE vs KNOW/APPLY) is semantic and
cannot be closed by regex alone — the residual boundary is owner-adjudicated.

Signals (first-match-wins, priority = strongest evidence):
  1. definitional_definitional_no_prescriptive -> candidate noise_drop
  2. definitional_definitional_with_prescriptive -> candidate quarantine
  3. procedure_definition                       -> candidate process_template
  4. open_tension_definition                    -> candidate growth_edge
  5. exact_dup_definition                       -> dedup leak (report only)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── Named signal patterns (audit tool; not pipeline logic, so kept here) ──
# DEFINITIONAL: the definition asserts "X is / describes / involves / refers to"
# a concept — i.e. it DEFINES what something is rather than prescribing a rule.
DEFINITIONAL_START = re.compile(
    r"^(this (principle|pattern|approach|method|model|framework|concept|insight|"
    r"idea|phenomenon|law|rule|strategy|heuristic|tendency|effect|technique|process|"
    r"dynamic|trajectory|mechanism|practice|phenomenon)\b"
    r"|the (principle|pattern|approach|method|model|framework|concept|phenomenon|law|"
    r"rule|strategy|tendency|effect|technique|process|practice)\b"
    r"|[a-z][a-z -]{2,40} (describes|refers to|is (a|an|the) |means|involves|represents|"
    r"functions as|operates as|constitutes)\b)",
    re.IGNORECASE,
)

# PRESCRIPTIVE: a transferable rule must tell you to do/avoid something.
PRESCRIPTIVE = re.compile(
    r"\b(should|must|ought|requires?|demands|necessitates|"
    r"to (achieve|avoid|maximize|minimize|improve|prevent|build|design|create|ensure|"
    r"reduce|increase|optimize|mitigate|detect|identify|leverage|maintain|sustain|"
    r"encourage|discourage|select|prioritize|reject|accept|adopt|isolate|reframe|"
    r"validate|frame|elicit|structure)\b)",
    re.IGNORECASE,
)

# PROCEDURE: ordinal step language (D275b: procedural INTENT, but step-count is
# NEVER the sole discriminator — pair with a done-condition).
PROCEDURE_STEPS = re.compile(
    r"\b(first|second|third|fourth|finally|next|then|subsequently|thereafter)\b[^.]*\b(then|next|finally|until|once|repeat)\b"
    r"|\b(step|stage|phase)\s*[1-9]",
    re.IGNORECASE,
)
DONE_CONDITION = re.compile(
    r"\b(until|once .{0,40} (then|stop|complete|done)|repeat until|keep .{0,20} until|"
    r"iterate .{0,20} (until|converge)|gate|exit condition|termination)\b",
    re.IGNORECASE,
)

# OPEN TENSION: the record articulates a contested/unverified correlation.
OPEN_TENSION = re.compile(
    r"\b(contested|contradict|contradictory|disputed|unverified|unresolved|open question|"
    r"debated|not (yet )?(established|verified|proven)|unknown whether|correlation .{0,20} unproven)\b",
    re.IGNORECASE,
)


def _text(*fields: str | None) -> str:
    """Join non-empty fields into one lowercased haystack."""
    return " ".join(f for f in fields if f and str(f).strip()).lower()


def _is_definitional(definition: str) -> bool:
    return bool(DEFINITIONAL_START.search(definition or ""))


def _is_prescriptive(*fields: str | None) -> bool:
    return bool(PRESCRIPTIVE.search(_text(*fields)))


def triage(fb: dict) -> list[str]:
    """Return the list of signals a principle record fires (priority order)."""
    definition = str(fb.get("definition") or "")
    body_fields = [
        fb.get("definition"),
        fb.get("mechanism"),
        fb.get("consequence"),
        fb.get("elaboration"),
    ]
    signals: list[str] = []
    if _is_definitional(definition):
        if not _is_prescriptive(*body_fields):
            signals.append("definitional_no_prescriptive")   # -> noise_drop
        else:
            signals.append("definitional_with_prescriptive")  # -> quarantine
    if PROCEDURE_STEPS.search(definition) and DONE_CONDITION.search(definition):
        signals.append("procedure")                          # -> process_template
    if OPEN_TENSION.search(_text(*body_fields)):
        signals.append("open_tension")                       # -> growth_edge
    return signals


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic principle-purity triage.")
    ap.add_argument("checkpoint", help="Path to the S2 checkpoint.jsonl")
    ap.add_argument(
        "--out",
        default="temp/principle_purity_triage.json",
        help="Output JSON path (written atomically).",
    )
    args = ap.parse_args()

    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        print(f"checkpoint not found: {checkpoint}", file=sys.stderr)
        return 2

    principles: list[dict] = []
    with checkpoint.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            fb = json.loads(line)
            if fb.get("content_type") == "principle":
                principles.append(fb)

    defs: dict[str, int] = {}
    for fb in principles:
        d = str(fb.get("definition") or "")
        defs[d] = defs.get(d, 0) + 1

    flagged: list[dict] = []
    for fb in principles:
        signals = triage(fb)
        if not signals:
            continue
        definition = str(fb.get("definition") or "")
        dup = defs.get(definition, 1) > 1
        if dup and "exact_dup" not in signals:
            signals.append("exact_dup")
        flagged.append(
            {
                "fb_id": fb.get("fb_id"),
                "name": fb.get("name"),
                "definition": definition[:300],
                "extraction_type": fb.get("extraction_type"),
                "signals": signals,
                "exact_dup": dup,
            }
        )

    out = {
        "schema_version": "1.0",
        "generated_from": str(checkpoint),
        "n_principles": len(principles),
        "n_flagged": len(flagged),
        "note": (
            "DETERMINISTIC TRIAGE for OWNER ADJUDICATION (D-343: no LLM). "
            "Signals are evidence, not a final ruling — the D275b discriminator "
            "(EXECUTE vs KNOW/APPLY) is semantic and closed only by owner ratification."
        ),
        "rows": flagged,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(out, indent=2), encoding="utf-8")
    tmp.replace(out_path)  # atomic

    from collections import Counter

    signal_counts = Counter(s for r in flagged for s in r["signals"])
    print(f"principles        : {len(principles)}")
    print(f"flagged (any signal): {len(flagged)} ({100*len(flagged)/max(len(principles),1):.1f}%)")
    for sig, n in signal_counts.most_common():
        print(f"  {sig:32s} {n}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
