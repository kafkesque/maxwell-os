"""Guard against drift in config/decisions.yaml's derived summary block.

The `total_decisions` field and `summary` block are redundant derived data: they
must equal counts computed from the `decisions` list. This test independently
recomputes them (deliberately NOT importing the sync script, so it acts as a
second oracle) and fails if they drift — e.g. after a hand-edited decision append
that forgets to bump a category count.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISIONS_YAML = ROOT / "config" / "decisions.yaml"

STATES = [
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


def _load() -> dict:
    assert DECISIONS_YAML.exists(), f"missing {DECISIONS_YAML}"
    return yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}


def _recompute(data: dict) -> tuple[int, dict]:
    decisions = data.get("decisions") or []
    total = len(decisions)

    state_counts: dict[str, int] = {s.lower(): 0 for s in STATES}
    category_counts: dict[str, int] = {}
    for d in decisions:
        state_counts[str(d.get("state") or "ACTIVE").lower()] = (
            state_counts.get(str(d.get("state") or "ACTIVE").lower(), 0) + 1
        )
        category = d.get("category") or "GOV"
        category_counts[category] = category_counts.get(category, 0) + 1

    summary = {
        "total": total,
        **state_counts,
        "by_category": dict(sorted(category_counts.items())),
    }
    return total, summary


def test_total_decisions_matches_decision_count() -> None:
    data = _load()
    total, _ = _recompute(data)
    assert data.get("total_decisions") == total, (
        f"total_decisions={data.get('total_decisions')!r} but len(decisions)={total}. "
        "Run: python3 scripts/recompute_decision_summary.py"
    )


def test_summary_matches_recomputed_counts() -> None:
    data = _load()
    total, expected = _recompute(data)
    declared = data.get("summary") or {}

    assert declared.get("total") == total, (
        f"summary.total={declared.get('total')!r} != {total}. "
        "Run: python3 scripts/recompute_decision_summary.py"
    )

    for key in STATES:
        lk = key.lower()
        assert declared.get(lk) == expected.get(lk), (
            f"summary.{lk}={declared.get(lk)!r} != {expected.get(lk)!r}. "
            "Run: python3 scripts/recompute_decision_summary.py"
        )

    declared_cats = declared.get("by_category") or {}
    assert declared_cats == expected.get("by_category"), (
        "summary.by_category drift:\n"
        f"  declared-only: {set(declared_cats) - set(expected.get('by_category', {}))}\n"
        f"  expected-only: {set(expected.get('by_category', {})) - set(declared_cats)}\n"
        f"  run: python3 scripts/recompute_decision_summary.py"
    )
