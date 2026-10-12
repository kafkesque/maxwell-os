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

import argparse
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
        "The canonical classification menu is rendered from `config/taxonomy.yaml` +",
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
        "Any change to `config/taxonomy.yaml` or `config/content_types.yaml` MUST be followed by:",
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
    """Freeze the menu, or MINT a new revision - never rewrite a frozen one in place (D-371, I2).

    MEASURED 2026-09-25: this script used to write config/closed_menu_v5.json unconditionally, so a taxonomy edit
    re-froze the answer space with a NEW menu_hash and NO refusal, while config/artifact_ownership.yaml declared
    the file immutable - the declaration and the mechanism disagreed (BUG-491c). D-371 then ruled the composite
    pin HISTORICAL and the ANSWER SPACE (config/menu_axis_hashes.yaml#answer_space_hash) the pin. Both rules are
    enforced here: an existing revision is never overwritten (a new answer space gets a NEW revision file, I2),
    and the run prints the consumer-repoint obligation, because a revision nobody reads is not a live pin.
    """
    ap = argparse.ArgumentParser(description="Freeze or mint a closed-menu revision (D-279, D-371).")
    ap.add_argument("--mint-version", type=int, default=None,
                    help="mint config/closed_menu_vN.json (+ .sha256) as a NEW revision instead of writing v5")
    a = ap.parse_args()
    menu = render_closed_menu()
    h = menu_hash(menu)
    summary = menu_summary(menu)
    payload = json.dumps(menu, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if a.mint_version is not None:
        target = _ROOT / "config" / ("closed_menu_v%d.json" % a.mint_version)
        target_sha = _ROOT / "config" / ("closed_menu_v%d.sha256" % a.mint_version)
        if target.exists():
            print("REFUSED: " + target.name + " already exists - a revision is minted once and never rewritten "
                  "(I2). Mint the NEXT version number.", file=sys.stderr)
            return 1
        _crash_safe_write_text(target, payload)
        _crash_safe_write_text(target_sha, h + "\n")
        print("minted " + target.name + " (menu_hash " + h[:16] + ")")
        print("REPOINT OBLIGATION (I2, not optional): declare the new revision in config/menu_axis_groups.yaml"
              " + config/menu_axis_hashes.yaml (source:) and repoint every declared live reader; a revision that"
              " no reader reads is not a pin, and a reader on a SUPERSEDED revision stamps labels with a hash the"
              " live config can no longer reproduce (D-277). Run: python3 scripts/menu_axis_hashes.py")
        return 0
    if _MENU_JSON.exists():
        existing = _MENU_JSON.read_text(encoding="utf-8")
        if existing == payload:
            print("ok  " + _MENU_JSON.name + " is already the render of the live config (menu_hash " + h[:16]
                  + ") - nothing to write")
            return 0
        print("REFUSED: " + _MENU_JSON.name + " exists and holds menu_hash "
              + menu_hash(json.loads(existing))[:16] + ", while the live config renders " + h[:16]
              + ". Overwriting it in place would destroy the provenance the frozen revision exists to provide and"
              " would move the stamp every label carrying it was classified against (D-277, D-371: the composite"
              " is HISTORICAL). Mint a NEW revision instead: python3 scripts/render_closed_menu.py --mint-version N"
              " - then repoint the declared readers.", file=sys.stderr)
        return 1
    _crash_safe_write_text(_MENU_JSON, payload)
    _crash_safe_write_text(_MENU_SHA, h + "\n")
    _crash_safe_write_text(_REPORT_MD, _render_report(menu, h, summary))

    print("froze a FIRST revision:")
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
