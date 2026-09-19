#!/usr/bin/env python3
"""Guard against surviving harness-artifact rows (BUG-262 class).

WHY: model_eval_suite._done_keys() skips any (model, suite, id) already present in the
checkpoint without err. A row measured while the harness was broken therefore gets skipped
FOREVER: re-running the suite prints '0 new results' and reads as success while the poisoned
row keeps dragging the model's score. Markers live in config/bench_preflight.yaml (C12).

    python3 scripts/check_stale_toolcall_rows.py
Exit 0 clean, 1 stale rows found.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parents[1]
CONFIG: Path = REPO / "config" / "bench_preflight.yaml"


def load_guards() -> dict[str, Any]:
    """Read the stale-row guard policy from config."""
    import yaml

    return (yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}).get("stale_row_guards") or {}


def find_stale(path: Path, markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return checkpoint rows matching any stale marker."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        for m in markers:
            if (str(r.get("model", "")).startswith(str(m["model_prefix"]))
                    and r.get("suite") == m["suite"]
                    and str(m["detail_contains"]).lower() in str(r.get("detail") or "").lower()):
                out.append({**r, "_bug": m.get("bug", "?")})
                break
    return out


def main() -> int:
    """Report surviving harness-artifact rows. Returns the exit code."""
    guards = load_guards()
    markers = list(guards.get("markers") or [])
    if not markers:
        print("no stale_row_guards configured — nothing to check")
        return 0
    stale = find_stale(REPO / str(guards["checkpoint"]), markers)
    if not stale:
        print("clean: no stale harness-artifact rows (" + str(len(markers)) + " marker(s) checked)")
        return 0
    print("STALE HARNESS-ARTIFACT ROWS: " + str(len(stale)))
    for r in stale[:8]:
        print("   " + str(r.get("_bug")) + " " + str(r.get("model")) + " " + str(r.get("id"))
              + " detail=" + str(r.get("detail"))[:60])
    print("   never re-measured (_done_keys skips by key) — purge, then re-run the suite")
    return 1


if __name__ == "__main__":
    sys.exit(main())
