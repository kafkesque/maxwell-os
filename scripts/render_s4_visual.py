#!/usr/bin/env python3
"""Render an S4 output directory into a human-readable Markdown report.

The S4 checkpoint is a JSONL blob (millions of bytes, one giant line per FB) —
not something a human can eyeball. This renders each FB (and the PT/PI/GE/TI
routing sidecars) into a compact visual summary so a reviewer can inspect the
actual knowledge content, classification, and provenance without parsing JSON.

D2323 content-type-aware rendering: each content_type renders its OWN body
fields (tool_instruction → description/output/example/caveats; process_template →
trigger/prerequisite/steps; growth_edge → body/category/…), not the one-size
principle core body. Field names mirror config/content_types.yaml s2_body_fields.

Usage:
    python3 scripts/render_s4_visual.py \
        --in-dir "knowledge pipeline/stage4_merge/smoke_real" \
        --out "knowledge pipeline/stage4_merge/smoke_real/visual.md"

Deterministic, no LLM, no network. Reads checkpoint.jsonl + the four
content-type sidecars (process_templates / process_instances / growth_edges /
tool_instructions) when present.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


# D2323: shared skeleton — S2 emits these for EVERY content_type, so render them
# first. Then the type-specific body renders for its content_type below.
_SHARED_BODY: tuple[str, ...] = ("definition", "mechanism", "boundary", "consequence")

# Per-content-type body fields — mirrors config/content_types.yaml s2_body_fields
# + principle CRIBS fields. Keep in sync with the ontology (C12).
_TYPE_BODY: dict[str, tuple[str, ...]] = {
    "principle": ("application", "failure_mode", "elaboration", "jargon"),
    "process_template": ("trigger", "prerequisite", "steps", "done_condition", "failure_mode"),
    "process_instance": ("instance_text", "actors", "outcome_metric", "outcome_qualitative", "domain_context"),
    "tool_instruction": ("tool_name", "platform", "description", "syntax", "parameters", "output", "example", "caveats"),
    "growth_edge": ("body", "category", "actionable", "status", "priority"),
}


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


def _load_records(path: Path) -> list[dict[str, Any]]:
    """Load a checkpoint/sidecar as JSONL, falling back to whole-doc JSON.

    S4 writes JSONL (one object per line), but older/pretty-printed sidecars
    (whole-doc JSON with newlines inside a single object) also occur. Handle both.
    """
    txt = path.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    except json.JSONDecodeError:
        obj = json.loads(txt)
        return obj if isinstance(obj, list) else [obj]


def render_record(idx: int, r: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    name = _s(r.get("name")) or "(unnamed)"
    lines.append(f"## {idx}. {name}")
    lines.append("")
    status = _s(r.get("classification_status")) or "?"
    depth = _s(r.get("depth"))
    disc = _s(r.get("discipline"))
    doms = ", ".join(_s(d) for d in (r.get("domains") or [])) or "—"
    content_type = _s(r.get("content_type"))
    extraction_type = _s(r.get("extraction_type"))
    evidence = _s(r.get("evidence"))
    lines.append(
        f"**status:** {status}  ·  **depth:** {depth}  ·  **discipline:** {disc}"
    )
    lines.append(f"**domains:** {doms}")
    lines.append(
        f"**content_type:** {content_type}  ·  **extraction_type:** {extraction_type}"
        f"  ·  **evidence:** {evidence}"
    )
    prov = f"  ·  **sources:** {len(r.get('source_books') or [])} books / {len(r.get('source_ids') or [])} ids"
    lines.append(f"**accessibility:** {_s(r.get('accessibility'))}  ·  "
                 f"**intimacy:** {_s(r.get('intimacy_boundary'))}  ·  "
                 f"**difficulty:** {_s(r.get('difficulty_level'))}  ·  "
                 f"**temporal:** {_s(r.get('temporal_scope'))}{prov}")
    lines.append("")
    # D2323: shared skeleton + type-specific body, in order.
    for f in _SHARED_BODY + _TYPE_BODY.get(content_type, ()):
        v = _s(r.get(f))
        if v:
            lines.append(f"**{f}:** {v}")
            lines.append("")
    return lines


def render_file(title: str, path: Path) -> list[str]:
    if not path.exists():
        return []
    rows = _load_records(path)
    if not rows:
        return []
    lines: list[str] = [f"# {title} ({len(rows)})", ""]
    for i, r in enumerate(rows, 1):
        lines.extend(render_record(i, r))
        lines.append("---")
        lines.append("")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    d = Path(args.in_dir)
    sections: list[str] = [
        f"# Stage 4 — Visual Summary",
        "",
        f"> `{d.resolve()}`",
        "",
    ]
    sections.extend(render_file("Foundation Blocks (checkpoint)", d / "checkpoint.jsonl"))
    sections.extend(render_file("Process Templates", d / "process_templates.jsonl"))
    sections.extend(render_file("Process Instances", d / "process_instances.jsonl"))
    sections.extend(render_file("Growth Edges", d / "growth_edges.jsonl"))
    sections.extend(render_file("Tool Instructions", d / "tool_instructions.jsonl"))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {out} ({len(sections)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
