#!/usr/bin/env python3
"""Sync config/decisions.yaml from DECISION-LOG.md — C12 compliant.
Run: python3 tools/sync_decisions.py [--dry-run]

Reads DECISION-LOG.md as the single source of truth.
Updates config/decisions.yaml with any missing decisions.
Tags decisions with auto-detected states (SUPERSEDED if D2104 says so, etc.).
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISION_LOG = ROOT / "DECISION-LOG.md"
DECISIONS_YAML = ROOT / "config" / "decisions.yaml"

CATEGORIES = ["INF", "DAT", "CLS", "QLT", "GOV", "PRD", "RES", "DEF", "VAL"]
STATES = ["PROPOSED", "DRAFT", "ACTIVE", "STALE", "SUPERSEDED", "ARCHIVED", "REJECTED"]


def extract_decisions_from_log() -> dict[str, dict]:
    """Parse DECISION-LOG.md for all D-number references with context."""
    if not DECISION_LOG.exists():
        print(f"ERROR: {DECISION_LOG} not found", file=sys.stderr)
        return {}

    text = DECISION_LOG.read_text(encoding="utf-8")
    decisions: dict[str, dict] = {}

    # Find all D-numbers
    d_ids = set(re.findall(r"D(\d{4})", text))

    for d_id_str in sorted(d_ids):
        d_id = f"D{d_id_str}"

        # D2367 fix: description/category/date must come from the decision's own
        # heading block ("### Dxxxx — Title (date)" + "**Category:** X"), not the
        # line *after* the first D-number mention (which captured the markdown
        # "**Category:** ..." formatting line and produced garbage descriptions).
        heading_m = re.search(rf"(?m)^#{{2,4}}\s+{d_id}\s*—\s*(.+)$", text)
        if heading_m:
            title = heading_m.group(1).strip()
            date_m = re.search(r"\((\d{4}-\d{2}-\d{2})\)\s*$", title)
            created = date_m.group(1) if date_m else "2026-07-26"
            desc = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", title).strip()

            after = text[heading_m.end(): heading_m.end() + 500]
            cat_m = re.search(r"\*\*Category:\*\*\s*(.+?)\s*$", after, re.MULTILINE)
            category = cat_m.group(1).strip() if cat_m else _detect_category(d_id, text)
        else:
            # Referenced only (no heading block) — best-effort fallback.
            pattern = rf"{d_id}[^\n]*\n([^\n]{{10,200}})"
            matches = re.findall(pattern, text)
            desc = matches[0].strip() if matches else "No heading in DECISION-LOG.md"
            created = "2026-07-26"
            category = _detect_category(d_id, text)

        # Auto-detect state
        state = _detect_state(d_id, text)

        decisions[d_id] = {
            "id": d_id,
            "category": category,
            "state": state,
            "description": desc[:200],
            "champion": "auto-sync",
            "target_files": [],
            "created": created,
        }

        # Check for superseded_by
        superseded = re.findall(rf"{d_id}.*?[Ss]uperseded[_ ]by.*?D(\d{{4}})", text)
        if superseded:
            decisions[d_id]["superseded_by"] = f"D{superseded[0]}"
            decisions[d_id]["state"] = "SUPERSEDED"

    return decisions


def _detect_category(d_id: str, text: str) -> str:
    """Auto-detect category from surrounding context."""
    snippet_start = text.find(d_id)
    if snippet_start < 0:
        return "GOV"
    snippet = text[max(0, snippet_start - 200): snippet_start + 500]

    keywords = {
        "INF": ["pipeline", "stage", "cluster", "hdbscan", "faiss", "umap", "embed", "infra"],
        "DAT": ["safety", "delete", "overwrite", "anytype", "safe_delete"],
        "CLS": ["taxonomy", "domain", "discipline", "classif", "label", "multi-label"],
        "QLT": ["quality", "verify", "nli", "deberta", "validation", "golden", "test", "BORP"],
        "GOV": ["constitution", "governance", "decision", "audit", "phantom", "buglog"],
        "RES": ["model", "research", "benchmark", "embedding", "MLX", "Ollama", "Qwen"],
        "DEF": ["defer", "deferred", "phase 2", "future"],
        "VAL": ["E2E", "end-to-end", "validation", "confirmed"],
    }
    for cat, words in keywords.items():
        if any(w in snippet.lower() for w in words):
            return cat
    return "GOV"


def _detect_state(d_id: str, text: str) -> str:
    """Auto-detect state from surrounding context."""
    snippet_start = text.find(d_id)
    if snippet_start < 0:
        return "ACTIVE"
    snippet = text[max(0, snippet_start - 100): snippet_start + 300].lower()

    if any(w in snippet for w in ["supersed", "replaced by", "obsole"]):
        return "SUPERSEDED"
    if any(w in snippet for w in ["reject", "won't implement", "will not"]):
        return "REJECTED"
    if any(w in snippet for w in ["defer", "phase 2", "future", "later"]):
        return "DEFERRED"
    if any(w in snippet for w in ["archiv", "historical"]):
        return "ARCHIVED"
    if any(w in snippet for w in ["fix", "fixed", "done", "implement", "complete"]):
        return "ACTIVE"
    return "ACTIVE"


def sync(decisions_yaml_path: Path, dry_run: bool = False) -> int:
    """Sync decisions.yaml with DECISION-LOG.md."""
    # Load existing
    if decisions_yaml_path.exists():
        existing = yaml.safe_load(decisions_yaml_path.read_text()) or {}
    else:
        existing = {"version": "1.0", "decisions": []}

    existing_ids = {d["id"] for d in existing.get("decisions", []) if isinstance(d, dict)}

    # Extract from log
    from_log = extract_decisions_from_log()
    new_ids = set(from_log.keys()) - existing_ids

    if not new_ids:
        print("✅ decisions.yaml is fully synced — no new decisions found.")
        return 0

    print(f"🔍 Found {len(new_ids)} new decisions: {sorted(new_ids)}")

    # Merge new decisions
    merged = list(existing.get("decisions", []))
    for d_id in sorted(new_ids):
        merged.append(from_log[d_id])

    # Update metadata
    existing["decisions"] = merged
    existing["total_decisions"] = len(merged)
    existing["last_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Recalculate summary
    states = {}
    categories = {}
    for d in merged:
        s = d.get("state", "ACTIVE")
        states[s] = states.get(s, 0) + 1
        c = d.get("category", "GOV")
        categories[c] = categories.get(c, 0) + 1

    existing["summary"] = {
        "total": len(merged),
        **{s.lower(): states.get(s, 0) for s in STATES},
        "by_category": categories,
    }

    if dry_run:
        print(f"DRY RUN: Would add {len(new_ids)} decisions.")
        for d_id in sorted(new_ids):
            d = from_log[d_id]
            print(f"  {d_id}: [{d['category']}] {d['state']} — {d['description'][:80]}")
        return 0

    # Write
    output = yaml.dump(existing, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
    # Preserve the header comment
    header = (
        "# Maxwell OS — Decision Registry\n"
        "# ================================\n"
        "# Authority: governance/decision_lifecycle.yaml §expansion_policy\n"
        "# Auto-synced from DECISION-LOG.md by tools/sync_decisions.py\n"
        f"# Last manual edit: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
        "#\n"
        "# This file tracks the STATE of each decision from DECISION-LOG.md.\n"
        "# DECISION-LOG.md is the source of truth for decision CONTENT.\n"
        "# This file is the operational registry for tooling.\n"
        "#\n"
    )
    decisions_yaml_path.write_text(header + output, encoding="utf-8")
    print(f"✅ Synced: {len(new_ids)} new decisions written to {decisions_yaml_path}")
    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sys.exit(sync(DECISIONS_YAML, dry_run=dry_run))
