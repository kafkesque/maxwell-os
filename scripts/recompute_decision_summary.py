#!/usr/bin/env python3
"""Recompute the derived fields in config/decisions.yaml — summary, total_decisions, last_sync
and the two integrity stamps (BUG-402, owner-approved 2026-09-23).

The `total_decisions` field, the `summary` block, `last_sync` and the stamp pair
(`decisions_sha256_16`, `written_by`) are REDUNDANT DERIVED DATA: they MUST equal values computed
from the `decisions` list. They were previously hand-maintained (summary) or written by an
INVERTED tool (last_sync, tools/sync_decisions.py) and drifted. This script recomputes them
deterministically from the `decisions` list — the single source of truth WITHIN decisions.yaml —
and writes back ONLY those derived fields. Every decision record is left byte-identical (no
full-file re-dump, so no spurious reformat of hand-curated descriptions).

BUG-402 design note: a timestamp alone is a DECLARATION, not a control — a human can edit it and
no tool can verify it. The stamp is therefore CONTENT-derived: `decisions_sha256_16` is the sha256
(16 hex chars) of the canonical JSON of the `decisions` list, so it proves WHAT was written, not
just WHEN. `--check` fails on a missing or mismatched stamp, which is what lets `just health`
catch drift loudly instead of silently (D-355).

Modes:
    (default)   recompute + surgical write-back in place
    --check     exit 1 if drift detected (no write) — wired into `just health`

IMPORTANT — this is NOT tools/sync_decisions.py. That tool treats DECISION-LOG.md as the source
of truth, which is INVERTED: DECISION-LOG.md has ~154 heading blocks vs 736 decision records here,
so running it would corrupt hand-curated records via its "No heading in DECISION-LOG.md" fallback
and heuristic state/category detection. It is now a hard-fail stub (BUG-402).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
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

WRITTEN_BY: str = "scripts/recompute_decision_summary.py"
STAMP_KEYS: tuple[str, ...] = ("decisions_sha256_16", "written_by")
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def decisions_digest(decisions: list) -> str:
    """Return the 16-hex-char content digest of the decisions list (BUG-402).

    The digest is taken over the RECORDS ONLY, never over the file, so writing the stamp cannot
    change the value it stamps.
    """
    payload = json.dumps(decisions, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def recompute(data: dict) -> tuple[int, dict, str]:
    """Return (total, summary, decisions_digest) computed from data["decisions"]."""
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
    return total, summary, decisions_digest(decisions)


def _diff(data: dict, total: int, summary: dict, digest: str) -> list[str]:
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

    # BUG-402 integrity stamp: a declaration with no writer cannot fail loudly, so it is checked.
    declared_digest = data.get("decisions_sha256_16")
    if declared_digest != digest:
        problems.append(
            f"decisions_sha256_16: declared {declared_digest!r}, actual {digest!r} "
            "(the record set changed or the stamp was hand-edited)"
        )
    if not str(data.get("last_sync") or "").strip():
        problems.append("last_sync: missing or blank (no sanctioned writer ran)")
    if data.get("written_by") != WRITTEN_BY:
        problems.append(
            f"written_by: declared {data.get('written_by')!r}, expected {WRITTEN_BY!r}"
        )
    return problems


def _surgical_write(total: int, summary: dict, digest: str, timestamp: str) -> None:
    """Replace only the derived fields: total_decisions, last_sync, the stamp pair, summary."""
    text = DECISIONS_YAML.read_text(encoding="utf-8")

    text = re.sub(
        r"(?m)^total_decisions:\s*\d+\s*$",
        f"total_decisions: {total}",
        text,
        count=1,
    )

    if re.search(r"(?m)^last_sync:.*$", text):
        text = re.sub(r"(?m)^last_sync:.*$", f"last_sync: '{timestamp}'", text, count=1)
    else:
        text = re.sub(
            r"(?m)^(total_decisions:.*)$",
            lambda m: m.group(1) + f"\nlast_sync: '{timestamp}'",
            text,
            count=1,
        )

    # Drop any existing stamp lines, then re-insert them directly under last_sync (idempotent).
    for key in STAMP_KEYS:
        text = re.sub(rf"(?m)^{key}:.*\n", "", text)
    stamp = "".join(f"{key}: {value}\n" for key, value in
                    (("decisions_sha256_16", digest), ("written_by", WRITTEN_BY)))
    text = re.sub(
        r"(?m)^(last_sync:.*)$",
        lambda m: m.group(1) + "\n" + stamp.rstrip("\n"),
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
    """Recompute (or --check) the derived fields of config/decisions.yaml."""
    check_only = "--check" in argv
    data = yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}
    total, summary, digest = recompute(data)
    problems = _diff(data, total, summary, digest)

    if not problems:
        print(f"✅ decisions.yaml derived fields in sync — {total} decisions, stamp {digest}.")
        return 0

    print(f"⚠️  {len(problems)} drift(s) detected:")
    for p in problems:
        print(f"   - {p}")

    if check_only:
        return 1

    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
    _surgical_write(total, summary, digest, timestamp)
    print(
        f"✅ Recomputed: total={total}, active={summary.get('active')}, "
        f"by_category entries={len(summary.get('by_category', {}))}, "
        f"last_sync={timestamp}, decisions_sha256_16={digest}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
