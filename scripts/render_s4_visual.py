#!/usr/bin/env python3
"""Render an S4 output directory into a human-readable Markdown report.

The S4 checkpoint is a JSONL blob (millions of bytes, one giant line per FB) —
not something a human can eyeball. This renders each FB (and the PT/PI/GE/TI
routing sidecars) into a compact visual summary so a reviewer can inspect the
actual knowledge content, classification, and provenance without parsing JSON.

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


FIELDS = (
    "definition", "mechanism", "boundary", "consequence",
    "application", "failure_mode", "elaboration", "jargon",
)


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


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
    for f in FIELDS:
        v = _s(r.get(f))
        if v:
            lines.append(f"**{f}:** {v}")
            lines.append("")
    return lines


def render_file(title: str, path: Path) -> list[str]:
    if not path.exists():
        return []
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
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
