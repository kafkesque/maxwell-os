#!/usr/bin/env python3
"""Recompute the derived `summary` + `total_decisions` fields in config/decisions.yaml.

The `total_decisions` field and the `summary` block are REDUNDANT DERIVED DATA:
they MUST equal counts computed from the `decisions` list. They were previously
hand-maintained and drifted (e.g. `summary.by_category["QLT / AUDIT"]` declared 7
vs 14 actual). This script recomputes them deterministically from the `decisions`
list — the single source of truth WITHIN decisions.yaml — and writes back ONLY
those derived fields. Every decision record is left byte-identical (no full-file
re-dump, so no spurious reformat of hand-curated descriptions).

Modes:
    (default)   recompute + surgical write-back in place
    --check     exit 1 if drift detected (no write) — for CI / tests

IMPORTANT — this is NOT tools/sync_decisions.py. That tool treats DECISION-LOG.md
as the source of truth, which is INVERTED: DECISION-LOG.md has ~237 heading blocks
vs 434 decisions here, so running it would corrupt hand-curated records via its
"No heading in DECISION-LOG.md" fallback and heuristic state/category detection.
This script only recomputes the derived summary from the already-authoritative
decisions list. Fixing/retiring sync_decisions.py is a separate task.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISIONS_YAML = ROOT / "config" / "decisions.yaml"

# Canonical state keys (lowercased in the summary block), in stable order so the
# summary renders consistently and future diffs are minimal.
STATES: list[str] = [
    "PROPOSED",
    "DRAFT",
    "ACTIVE",
    "STALE",
    "SUPERSEDED",
    "ARCHIVED",
    "REJECTED",
    "DEFERRED",
    "RESOLVED",
    "PLANNED",
]


def recompute(data: dict) -> tuple[int, dict]:
    """Return (total, summary) computed from data["decisions"]."""
    decisions = data.get("decisions") or []
    total = len(decisions)

    state_counts: dict[str, int] = {s.lower(): 0 for s in STATES}
    category_counts: dict[str, int] = {}
    for d in decisions:
        state = str(d.get("state") or "ACTIVE").lower()
        state_counts[state] = state_counts.get(state, 0) + 1
        category = d.get("category") or "GOV"
        category_counts[category] = category_counts.get(category, 0) + 1

    summary: dict = {
        "total": total,
        **state_counts,
        "by_category": dict(sorted(category_counts.items())),
    }
    return total, summary


def _diff(data: dict, total: int, summary: dict) -> list[str]:
    """Return a list of human-readable drift descriptions (empty = in sync)."""
    problems: list[str] = []
    if data.get("total_decisions") != total:
        problems.append(
            f"total_decisions: declared {data.get('total_decisions')!r}, actual {total}"
        )
    declared = data.get("summary") or {}
    for key, actual in summary.items():
        if key == "by_category":
            declared_cats = declared.get("by_category") or {}
            all_keys = sorted(set(declared_cats) | set(actual))
            for ck in all_keys:
                if declared_cats.get(ck) != actual.get(ck):
                    problems.append(
                        f"summary.by_category[{ck!r}]: declared "
                        f"{declared_cats.get(ck)!r}, actual {actual.get(ck)!r}"
                    )
        elif declared.get(key) != actual:
            problems.append(
                f"summary.{key}: declared {declared.get(key)!r}, actual {actual!r}"
            )
    return problems


def _surgical_write(total: int, summary: dict) -> None:
    """Replace only `total_decisions` and the trailing `summary:` block."""
    text = DECISIONS_YAML.read_text(encoding="utf-8")

    text = re.sub(
        r"(?m)^total_decisions:\s*\d+\s*$",
        f"total_decisions: {total}",
        text,
        count=1,
    )

    marker = "\nsummary:"
    idx = text.rfind(marker)
    if idx == -1:
        raise SystemExit("ERROR: top-level `summary:` key not found — aborting (no write).")

    head = text[: idx + 1]  # everything through the newline before `summary:`
    body = yaml.dump(
        summary,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    # Indent the dumped mapping by 2 spaces under the `summary:` key.
    block = "summary:\n" + "".join(
        ("  " + line + "\n") if line.strip() else "\n" for line in body.splitlines()
    )
    DECISIONS_YAML.write_text(head + block, encoding="utf-8")


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    data = yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}
    total, summary = recompute(data)
    problems = _diff(data, total, summary)

    if not problems:
        print(f"✅ decisions.yaml summary is in sync — {total} decisions.")
        return 0

    print(f"⚠️  {len(problems)} drift(s) detected:")
    for p in problems:
        print(f"   - {p}")

    if check_only:
        return 1

    _surgical_write(total, summary)
    print(
        f"✅ Recomputed: total={total}, active={summary.get('active')}, "
        f"by_category entries={len(summary.get('by_category', {}))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
