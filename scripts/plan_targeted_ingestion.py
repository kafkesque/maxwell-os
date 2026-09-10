#!/usr/bin/env python3
"""plan_targeted_ingestion.py — D2607 (D): identify starved disciplines and
produce a targeted source-ingestion manifest.

The fine 61-way discipline head (and the ~dead 43-way domain head) are
DATA-LIMITED: 18/61 disciplines have <10 golden examples, and the convergent pool
(the mining source) is even MORE starved for those same disciplines (design
psychology=1, ecology=1, computational theory=2, game design=2, generative
design=2 convergent FBs). Bare S2 re-runs were rejected (D2607): same corpus ->
same skew. The ONLY lever is bringing in NEW source content for these disciplines.

This script deterministically computes the starved set + target counts from the
golden set (config/golden/stage4_golden_mined.yaml) and the convergent pool
(maxwell.db is_convergent=1), and writes the manifest (JSON + Markdown).

Run:  python3 scripts/plan_targeted_ingestion.py [--apply]
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# R14 stamps (single source of truth: pipeline_paths).
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# C12: paths overridable via env (same convention as train_discipline_classifier).
GOLDEN = Path(os.environ.get("GOLDEN_YAML", ROOT / "config" / "golden" / "stage4_golden_mined.yaml"))
DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_JSON = ROOT / "governance" / "targeted_ingestion_plan.json"
OUT_MD = ROOT / "governance" / "targeted_ingestion_plan.md"

MIN_GOLDEN_TARGET: int = 10   # D2607: 18/61 < 10 golden is the starvation threshold
MIN_CONVERGENT_TARGET: int = 20  # D2607: 29/61 < 20 convergent
CRITICAL_CONVERGENT: int = 3     # convergent <= 3 = source-starved (cannot even mine)
HIGH_CONVERGENT: int = 10        # convergent 4-10 = high priority


def _golden_counts() -> Counter:
    try:
        data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.error("Failed to read golden set %s: %s", GOLDEN, exc)
        raise ValueError(f"Golden set {GOLDEN} unreadable: {exc}") from exc
    c: Counter = Counter()
    for ex in data.get("examples", []):
        ec = ex.get("expected_classification") or {}
        if ec.get("discipline"):
            c[ec["discipline"]] += 1
    return c


def _convergent_counts() -> Counter:
    try:
        con = sqlite3.connect(str(DB))
        cur = con.cursor()
        rows = cur.execute(
            "SELECT discipline, COUNT(*) FROM fbs "
            "WHERE is_convergent=1 AND discipline IS NOT NULL AND discipline != '' "
            "AND discipline != 'emerging' GROUP BY discipline"
        ).fetchall()
        con.close()
    except sqlite3.Error as exc:
        logger.error("Failed to query convergent pool %s: %s", DB, exc)
        raise ValueError(f"Convergent pool query failed on {DB}: {exc}") from exc
    return Counter({d: c for d, c in rows})


def _tier(conv: int) -> str:
    if conv <= CRITICAL_CONVERGENT:
        return "CRITICAL"
    if conv <= HIGH_CONVERGENT:
        return "HIGH"
    return "MODERATE"


def build_manifest() -> Dict[str, Any]:
    golden = _golden_counts()
    conv = _convergent_counts()
    starved = sorted(
        (d for d, g in golden.items() if g < MIN_GOLDEN_TARGET),
        key=lambda d: (conv.get(d, 0), golden.get(d, 0)),
    )
    entries: List[Dict[str, Any]] = []
    for d in starved:
        g = golden.get(d, 0)
        c = conv.get(d, 0)
        entries.append({
            "discipline": d,
            "golden_count": g,
            "convergent_count": c,
            "tier": _tier(c),
            "convergent_shortfall": max(0, MIN_CONVERGENT_TARGET - c),
            "golden_shortfall": max(0, MIN_GOLDEN_TARGET - g),
        })
    return {
        "generated_from": {
            "golden": str(GOLDEN),
            "db": str(DB),
            "min_golden_target": MIN_GOLDEN_TARGET,
            "min_convergent_target": MIN_CONVERGENT_TARGET,
        },
        "n_starved": len(entries),
        "n_critical": sum(1 for e in entries if e["tier"] == "CRITICAL"),
        "n_high": sum(1 for e in entries if e["tier"] == "HIGH"),
        "n_moderate": sum(1 for e in entries if e["tier"] == "MODERATE"),
        # R14 stamps (persistent artifact traceability; deterministic — no LLM).
        "schema_version": SCHEMA_VERSION,
        "gen_model": "deterministic",
        "pipeline_commit": PIPELINE_COMMIT,
        "created": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


def _md(manifest: Dict[str, Any]) -> str:
    lines = [
        "# Targeted Source Ingestion Plan (D2607 option D)",
        "",
        f"> Generated by `scripts/plan_targeted_ingestion.py` — {manifest['n_starved']} starved disciplines "
        f"({manifest['n_critical']} CRITICAL / {manifest['n_high']} HIGH / {manifest['n_moderate']} MODERATE).",
        "> The fine 61-way head is data-limited: these disciplines have <10 golden examples AND a convergent "
        "pool too thin to mine up from. Bare S2 re-runs rejected (same corpus -> same skew).",
        "",
        "| Tier | Discipline | Golden | Convergent | Convergent shortfall |",
        "|---|---|---|---|---|",
    ]
    for e in manifest["entries"]:
        lines.append(
            f"| {e['tier']} | {e['discipline']} | {e['golden_count']} | "
            f"{e['convergent_count']} | {e['convergent_shortfall']} |"
        )
    lines += [
        "",
        "## How to ingest",
        "",
        "1. Source content per discipline (textbooks/papers/practitioner articles) into the input corpus.",
        "2. Run the pipeline (S0 convert -> S1 chunk -> S1.5 cluster -> S2 extract) over ONLY the new sources.",
        "3. Mine the new convergent FBs via `scripts/mine_classifier_golden.py` (stratified: min 10/max 30 per discipline).",
        "4. Re-run `scripts/train_hierarchical_classifier.py` + measure the fine-head macro-F1 lift.",
        "",
        "## Priority rationale",
        "",
        f"- **CRITICAL** (convergent <= {CRITICAL_CONVERGENT}): the source corpus has essentially NO convergent signal "
        f"for these — even a perfect miner cannot reach {MIN_GOLDEN_TARGET} golden. New source is mandatory.",
        f"- **HIGH** (convergent {CRITICAL_CONVERGENT + 1}-{HIGH_CONVERGENT}): thin but present; targeted sources close the gap.",
        "- **MODERATE**: closest to target; lowest-effort wins.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = build_manifest()
    print(json.dumps({
        "n_starved": manifest["n_starved"],
        "critical": [e["discipline"] for e in manifest["entries"] if e["tier"] == "CRITICAL"],
        "high": [e["discipline"] for e in manifest["entries"] if e["tier"] == "HIGH"],
        "moderate": [e["discipline"] for e in manifest["entries"] if e["tier"] == "MODERATE"],
    }, indent=2))

    if "--apply" not in os.sys.argv:
        print("\nDRY-RUN — re-run with --apply to write governance/targeted_ingestion_plan.{json,md}")
        return

    def _atomic(path: Path, text: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=path.suffix)
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    _atomic(OUT_JSON, json.dumps(manifest, indent=2) + "\n")
    _atomic(OUT_MD, _md(manifest))
    print(f"\n✅ wrote {OUT_MD.name} + {OUT_JSON.name}")


if __name__ == "__main__":
    main()
