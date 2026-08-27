#!/usr/bin/env python3
"""
s4_golden.py — Config-driven S4 classification golden loader (D2454)
======================================================================
Authority: D2454 (2026-08-27) — wire `config/golden/stage4_golden.yaml`
(authored D2451, test-validated) into the four S4 classification prompts:

  1. CLASSIFY_SYSTEM_PROMPT          (stage4_merge.py — direct classify)
  2. MERGED_CRIBS_CLASSIFY_SYSTEM    (stage4_merged_call.py — merged CRIBS+classify)
  3. BATCH_CRIBS_CLASSIFY_SYSTEM     (stage4_merged_call.py — batched)
  4. DEPTH_FOCUSED_PROMPT            (stage4_merged_call.py — focused 4-way depth)

The golden spans all 4 depth levels (universal/cross-domain/domain/specialized)
with full expected classifications + rationale. Loading is FAIL-CLOSED (D2463
pattern): when injection is enabled and the file is missing/malformed/empty,
the pipeline raises rather than silently degrading to zero-shot.

C12: the loader takes the path from config (pipeline_config.yaml stage4.golden_path)
and the injection flag from config (stage4.golden_inject_enabled) — never hardcoded.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_stage4_golden(path: str | Path | None = None) -> list[dict]:
    """Load `examples` from config/golden/stage4_golden.yaml (fail-closed).

    Args:
        path: Explicit golden path (default: config/golden/stage4_golden.yaml).

    Returns:
        List of golden example dicts.

    Raises:
        FileNotFoundError: if the golden file does not exist.
        ValueError: if the file parses but has no `examples` (or is not a dict).
    """
    golden_path = Path(path) if path is not None else _PROJECT_ROOT / "config" / "golden" / "stage4_golden.yaml"
    if not golden_path.is_absolute():
        golden_path = _PROJECT_ROOT / golden_path
    if not golden_path.exists():
        raise FileNotFoundError(f"D2454: stage4 golden missing: {golden_path}")
    data = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"D2454: stage4 golden must be a YAML mapping: {golden_path}")
    examples = data.get("examples", [])
    if not isinstance(examples, list) or not examples:
        raise ValueError(f"D2454: stage4 golden has no examples: {golden_path}")
    return examples


def _fmt_fb(fb: dict) -> str:
    """Format one golden input_fb into NAME/DEFINITION/MECHANISM/BOUNDARY lines."""
    parts = [f"NAME: {fb.get('name', '')}"]
    if fb.get("definition"):
        parts.append(f"DEFINITION: {fb['definition']}")
    if fb.get("mechanism"):
        parts.append(f"MECHANISM: {fb['mechanism']}")
    if fb.get("boundary"):
        parts.append(f"BOUNDARY: {fb['boundary']}")
    return "\n".join(parts)


def format_classify_golden(examples: list[dict]) -> str:
    """Format golden examples for classification prompts (depth+discipline+domains+evidence).

    Each example renders as an input FB followed by its expected classification
    and the authoring rationale — so the model sees BOTH the label and WHY.
    """
    blocks: list[str] = []
    for i, ex in enumerate(examples, 1):
        cls = ex.get("expected_classification", {}) if isinstance(ex, dict) else {}
        if not isinstance(cls, dict):
            cls = {}
        depth = cls.get("depth", "")
        discipline = cls.get("discipline", "")
        domains = ", ".join(cls.get("domains", []) or [])
        evidence = cls.get("evidence", "")
        spec = cls.get("is_specialized", False)
        rationale = (ex.get("rationale", "") or "").strip()
        blocks.append(
            f"EXAMPLE {i}:\n"
            f"{_fmt_fb(ex.get('input_fb', {}))}\n"
            f"→ depth: {depth} | discipline: {discipline} | domains: [{domains}] "
            f"| evidence: {evidence} | is_specialized: {spec}"
            + (f"\n  rationale: {rationale}" if rationale else "")
        )
    return "\n\n".join(blocks)


def format_depth_golden(examples: list[dict]) -> str:
    """Compact depth-only few-shot for DEPTH_FOCUSED_PROMPT (one answer word)."""
    blocks: list[str] = []
    for i, ex in enumerate(examples, 1):
        cls = ex.get("expected_classification", {}) if isinstance(ex, dict) else {}
        depth = cls.get("depth", "") if isinstance(cls, dict) else ""
        blocks.append(
            f"EXAMPLE {i}:\n{_fmt_fb(ex.get('input_fb', {}))}\nAnswer: {depth}"
        )
    return "\n\n".join(blocks)
