#!/usr/bin/env python3
"""scripts/render_closed_menu.py — Freeze the R1 closed menu + menu_hash (D-279).

Reads the config-derived closed menu from pipeline/closed_menu.py and freezes it
to config/closed_menu_v5.json (the canonical menu) + config/closed_menu_v5.sha256
(the provenance hash). Also writes a human-readable governance report.

The frozen `menu_hash` is the value that pipeline/stage4_merge.py stamps onto
every classified FB (D-279). Regenerating this file after ANY taxonomy or
content-type change is how a label stays traceable to the menu it was classified
against (the `min_human_share` prerequisite, F-44).

Read-only w.r.t. the DB. Crash-safe write (tempfile → fsync → os.replace, C6).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.closed_menu import canonical_json, menu_hash, menu_summary, render_closed_menu  # noqa: E402

_MENU_JSON = _ROOT / "config" / "closed_menu_v5.json"
_MENU_SHA = _ROOT / "config" / "closed_menu_v5.sha256"
_REPORT_MD = _ROOT / "governance" / "r1_closed_menu_20260920.md"


def _crash_safe_write_text(path: Path, text: str) -> None:
    """Write text crash-safely (C6): tempfile → fsync → os.replace, same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _render_report(menu: dict, h: str, summary: dict) -> str:
    lines: list[str] = [
        "# R1 — Closed menu frozen (D-279, 2026-09-20)",
        "",
        "The canonical classification menu is rendered from `config/taxonomy_v5.yaml` +",
        "`config/content_types.yaml` by `pipeline/closed_menu.py`, with `none` as a FIRST-CLASS",
        "abstention value (D-275b/D-277). A label is only trustworthy if it is traceable to the",
        "exact menu it was classified against — that trace is the `menu_hash`.",
        "",
        f"- **menu_hash (sha256):** `{h}`",
        f"- content_types: {summary['content_types']} (5 roles + 2 dispositions + `none`)",
        f"- extraction_types: {summary['extraction_types']}",
        f"- disciplines: {summary['disciplines']} (61 canonicals + `emerging`)",
        f"- domains: {summary['domains']} (43 canonicals + `emerging`)",
        f"- abstention value: `{summary['abstention']}`",
        "",
        "## Artifacts",
        "",
        "- `config/closed_menu_v5.json` — the frozen menu (canonical JSON).",
        "- `config/closed_menu_v5.sha256` — the provenance hash stamped onto every FB.",
        "- `pipeline/closed_menu.py` — the renderer (single source of truth).",
        "",
        "## Content types",
        "",
        "| value | description |",
        "|---|---|",
    ]
    for e in menu["content_types"]:
        desc = e["description"].replace("\n", " ").replace("|", "\\|")[:120]
        lines.append(f"| `{e['value']}` | {desc} |")

    lines += [
        "",
        "## Regeneration",
        "",
        "Any change to `config/taxonomy_v5.yaml` or `config/content_types.yaml` MUST be followed by:",
        "",
        "```",
        "python3 scripts/render_closed_menu.py",
        "```",
        "",
        "and the new `menu_hash` must be carried into the next pipeline run (stamped by `stage4_merge.py`).",
        "Labels stamped with an OLD menu_hash are traceable to the OLD menu and must be re-derived (D-277:",
        "re-derive from source, never trust the old post-hoc stamps).",
        "",
        f"*Generated {datetime.now(UTC).isoformat()}.*",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    menu = render_closed_menu()
    h = menu_hash(menu)
    summary = menu_summary(menu)

    _crash_safe_write_text(_MENU_JSON, json.dumps(menu, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
    _crash_safe_write_text(_MENU_SHA, h + "\n")
    _crash_safe_write_text(_REPORT_MD, _render_report(menu, h, summary))

    print(f"✅ closed menu frozen:")
    print(f"   menu_hash = {h}")
    print(f"   content_types={summary['content_types']} extraction_types={summary['extraction_types']} "
          f"disciplines={summary['disciplines']} domains={summary['domains']}")
    print(f"   -> {_MENU_JSON.name}, {_MENU_SHA.name}, {_REPORT_MD.name}")

    # self-verify: recompute the hash of the frozen JSON and assert it matches
    frozen = json.loads(_MENU_JSON.read_text(encoding="utf-8"))
    recomputed = hashlib.sha256(canonical_json(frozen).encode("utf-8")).hexdigest()
    if recomputed != h:
        print(f"❌ integrity FAIL: frozen json sha256 {recomputed} != {h}", file=sys.stderr)
        return 1
    print("   ✅ integrity: frozen json sha256 == menu_hash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
