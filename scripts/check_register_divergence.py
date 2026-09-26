#!/usr/bin/env python3
"""check_register_divergence.py - a bug closed in PROSE but still counted OPEN is RED (BUG-481).

WHY. scripts/bug_status.py folds STATUS EVENTS, and a status event is a HEADER. A closure written as a body
paragraph is invisible, so the machine register over-reports: MEASURED 2026-09-25, 8 ids carry an explicit
`**Status:** FIXED|RESOLVED|CLOSED` in the body while their last header classifies OPEN. The register said
"114 open" and the C15 handoff rule was driven by that phantom count.

check_bug_status.py CANNOT catch this: it re-derives the register from the same headers and byte-compares, so
it certifies the PARSER, never the LOG (the BUG-467 class - a rail whose evidence is the same source as the
artifact it checks).

THE RULE: one fact has one HOME (the header event). The other place is made LOUD. The declared list in
config/register_divergence.yaml is SHRINK-ONLY: an id listed there that is no LONGER divergent is itself a
failure, so the list can only be emptied by promoting each closure to a header event or re-opening the bug.
Fail closed (C16).
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUGLOG = REPO / "governance" / "buglog.md"
CONFIG = REPO / "config" / "register_divergence.yaml"
HEADER_RE = re.compile(r"^#{2,3}\s+(BUG-\d+)\b[\s:—‑-]*(.*)$")
# An EXPLICIT status field, not prose: `**Status:** FIXED`, `**status**: FIXED`, `**Status: RESOLVED**`.
STATUS_FIELD_RE = re.compile(
    r"\*\*\s*status\s*:?\s*\*\*\s*:?\s*(FIXED|RESOLVED|CLOSED|INVALID|RETRACTED)", re.I)


def _load_parser():
    """Import scripts/bug_status.py so this rail cannot drift from the register's own classifier."""
    spec = importlib.util.spec_from_file_location("bug_status_rail", REPO / "scripts" / "bug_status.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def divergent_ids(lines: list[str]) -> dict[str, str]:
    """Return {bug_id: evidence} where the last header says OPEN but the body asserts a closure."""
    parser = _load_parser()
    spans: dict[str, list[int]] = {}
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if m:
            spans.setdefault(m.group(1), []).append(i)
    out: dict[str, str] = {}
    for bid, idxs in spans.items():
        last = idxs[-1]
        end = len(lines)
        for j in range(last + 1, len(lines)):
            if HEADER_RE.match(lines[j]):
                end = j
                break
        state = parser.classify(parser.status_slot(HEADER_RE.match(lines[last]).group(2).strip()))
        if state != "open":
            continue
        body = "\n".join(lines[last + 1:end])
        m = STATUS_FIELD_RE.search(body)
        if m:
            out[bid] = f"header is OPEN but the body asserts **Status: {m.group(1).upper()}**"
    return out


def main() -> int:
    """Compare the live divergence with the declared, shrink-only list. Require exact agreement."""
    import yaml
    ap = argparse.ArgumentParser()
    ap.parse_args()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    declared = {e["id"] for e in (cfg.get("declared_divergent") or [])}
    live = divergent_ids(BUGLOG.read_text(encoding="utf-8").splitlines())
    declared_max = int(cfg.get("declared_max", 0))

    new = sorted(set(live) - declared, key=lambda b: int(b[4:]))
    stale = sorted(declared - set(live), key=lambda b: int(b[4:]))
    bad = []
    if new:
        bad.append(f"UNDECLARED divergence ({len(new)}): " + ", ".join(f"{b} ({live[b]})" for b in new))
    if stale:
        bad.append(f"STALE declaration ({len(stale)}): {', '.join(stale)} - no longer divergent; the list is "
                   f"SHRINK-ONLY, remove the entry (BUG-481)")
    if len(declared) > declared_max:
        bad.append(f"declared {len(declared)} exceeds declared_max {declared_max} - raising the ceiling "
                   f"requires a declared decision, not an edit")
    if bad:
        print("FAIL register divergence (BUG-481):")
        for b in bad:
            print("  !!", b)
        print("  a closure belongs in the HEADER, where the register can see it; the body is made loud, not "
              "silent. Reconcile governance/buglog.md, then re-run scripts/bug_status.py.")
        return 1
    print(f"ok register divergence: {len(live)} declared, all still divergent; ceiling {declared_max} "
          f"(shrink-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
