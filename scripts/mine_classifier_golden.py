#!/usr/bin/env python3
"""Mine convergent FBs into a golden training set for the discipline/domain auto-sorter.

D2577 follow-up. The auto-sorter (scripts/train_discipline_classifier.py) is gated
on MIN_GOLDEN_EXAMPLES=100, but config/golden/stage4_golden.yaml holds only 7
hand-curated few-shot examples (which are WIRED into the S4 prompt and must stay
small). This script mines the production DB's convergent FBs (is_convergent=1,
discipline != 'emerging') and emits them as a SEPARATE classifier training set in
the SAME nested structure as stage4_golden.yaml, stratified by discipline (cap
max-per per discipline so rich disciplines do not dominate) with global cap.

Labels are the gpt-oss TEACHER output (silver-standard), NOT hand-reviewed gold:
    - discipline/domains: ~75-90% accurate (the axes this classifier trains on)
    - depth: KNOWN-weak axis (D2576) — carried through for golden-contract
      conformance only; depth is NOT a classifier target post-D2577.

Deterministic (seeded RNG). Writes a NEW file by default (never overwrites the
curated few-shot golden). Run `--dry-run` first to inspect counts/coverage.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml

# Bootstrap project root so `pipeline` imports resolve when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import MAX_DOMAINS_PER_FB
from pipeline.schemas import CANONICAL_DISCIPLINES, CANONICAL_DOMAINS

# ---------------------------------------------------------------------------
# C20: named constants (no magic numbers)
# ---------------------------------------------------------------------------

DEFAULT_DB: str = "knowledge pipeline/maxwell.db"
DEFAULT_OUT: str = "config/golden/stage4_golden_mined.yaml"
MAX_PER_DISCIPLINE: int = 30
MAX_TOTAL: int = 1000
MIN_PER_DISCIPLINE: int = 5
RANDOM_STATE: int = 42

VALID_DEPTHS = frozenset({"universal", "cross-domain", "domain", "specialized"})
VALID_EVIDENCE = frozenset({"cited", "axiomatic"})
CORE_SKELETON = ("name", "definition", "mechanism", "boundary")


# ---------------------------------------------------------------------------
# C6: crash-safe write
# ---------------------------------------------------------------------------


def safe_write(path: Path, data: bytes) -> None:
    """Write data to path atomically using tempfile, fsync, and os.replace.

    Args:
        path: Destination file path.
        data: Raw bytes to write.

    Raises:
        OSError: If the write or replace operation fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise exc


# ---------------------------------------------------------------------------
# Data loading + filtering
# ---------------------------------------------------------------------------


def fetch_convergent_fbs(db_path: str) -> List[Dict[str, Any]]:
    """Fetch convergent, non-emerging FBs with the S4 core skeleton.

    Args:
        db_path: Path to the production SQLite DB.

    Returns:
        List of FB row dicts with the fields needed to build golden examples.

    Raises:
        FileNotFoundError: If the DB file does not exist.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT fb_id, name, definition, mechanism, boundary,
                   discipline, domains, depth, evidence
            FROM fbs
            WHERE is_convergent = 1
              AND discipline IS NOT NULL
              AND discipline != 'emerging'
            ORDER BY fb_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def fetch_backfill_fbs(db_path: str) -> List[Dict[str, Any]]:
    """Fetch single-source (non-convergent) FBs for sparse-discipline backfill.

    Args:
        db_path: Path to the production SQLite DB.

    Returns:
        List of FB row dicts with the fields needed to build golden examples.

    Raises:
        FileNotFoundError: If the DB file does not exist.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT fb_id, name, definition, mechanism, boundary,
                   discipline, domains, depth, evidence
            FROM fbs
            WHERE is_convergent = 0
              AND discipline IS NOT NULL
              AND discipline != 'emerging'
            ORDER BY fb_id
            """
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def _parse_domains(raw: Any) -> List[str]:
    """Parse the `domains` column (JSON array string) into a list.

    Args:
        raw: Raw domains column value (JSON string or already a list).

    Returns:
        List of domain label strings.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(d) for d in raw]
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(d) for d in parsed]


def filter_valid(
    rows: Sequence[Dict[str, Any]],
    disciplines: Sequence[str],
    domains: Sequence[str],
    max_domains: int,
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Filter rows to those passing the golden-contract ontology checks.

    Args:
        rows: Raw FB rows from the DB.
        disciplines: Canonical discipline set (incl. 'emerging' placeholder).
        domains: Canonical domain set (incl. 'emerging' placeholder).
        max_domains: Max domains per FB (MAX_DOMAINS_PER_FB).

    Returns:
        Tuple of (valid_rows, drop_reason_counts). Valid rows have a non-empty
        core skeleton, non-emerging canonical discipline, 1..max_domains
        non-emerging canonical domains, valid depth, and valid evidence.
    """
    disc_set = set(disciplines) - {"emerging"}
    dom_set = set(domains) - {"emerging"}
    reasons: Dict[str, int] = {}

    def _drop(reason: str) -> None:
        reasons[reason] = reasons.get(reason, 0) + 1

    valid: List[Dict[str, Any]] = []
    for row in rows:
        skeleton_ok = True
        for field in CORE_SKELETON:
            if not (row.get(field) or "").strip():
                _drop(f"empty_{field}")
                skeleton_ok = False
                break
        if not skeleton_ok:
            continue

        if (row.get("discipline") or "").strip() not in disc_set:
            _drop("bad_discipline")
            continue

        doms = _parse_domains(row.get("domains"))
        if not doms or len(doms) > max_domains:
            _drop("bad_domain_count")
            continue
        if any(d not in dom_set for d in doms):
            _drop("bad_domain_label")
            continue

        if (row.get("depth") or "").strip() not in VALID_DEPTHS:
            _drop("bad_depth")
            continue
        if (row.get("evidence") or "").strip() not in VALID_EVIDENCE:
            _drop("bad_evidence")
            continue

        valid.append(row)
    return valid, reasons


# ---------------------------------------------------------------------------
# Stratification + serialization
# ---------------------------------------------------------------------------


def stratify(
    rows: Sequence[Dict[str, Any]],
    max_per: int,
    max_total: int,
    seed: int,
    min_per: int,
) -> List[Dict[str, Any]]:
    """Seeded per-discipline sampling with a floor and fair round-robin top-up.

    Guarantees every discipline with data keeps up to ``min_per`` examples
    (thin disciplines keep all they have) before any discipline gets a second
    top-up toward ``max_per``. Round-robin allocation means no discipline is
    starved by sort order; the global ``max_total`` cap is the only limit.

    Args:
        rows: Valid FB rows.
        max_per: Per-discipline cap.
        max_total: Global output cap.
        seed: RNG seed.
        min_per: Per-discipline floor (thin disciplines keep all below this).

    Returns:
        Sampled FB rows.
    """
    rng = random.Random(seed)
    by_disc: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_disc.setdefault(row["discipline"], []).append(row)

    # Shuffle each pool once (deterministic per seed).
    shuffled: Dict[str, List[Dict[str, Any]]] = {}
    for disc, pool in by_disc.items():
        p = list(pool)
        rng.shuffle(p)
        shuffled[disc] = p

    disc_names = sorted(shuffled)
    taken: Dict[str, int] = {d: 0 for d in disc_names}

    sampled: List[Dict[str, Any]] = []
    # Pass 1: floor — every discipline with data keeps up to min_per examples.
    for disc in disc_names:
        n = min(len(shuffled[disc]), min_per)
        sampled.extend(shuffled[disc][:n])
        taken[disc] = n

    # Pass 2: round-robin top-up toward max_per, within the global budget.
    budget = max_total - len(sampled)
    while budget > 0:
        progressed = False
        for disc in disc_names:
            if budget <= 0:
                break
            if taken[disc] < max_per and taken[disc] < len(shuffled[disc]):
                sampled.append(shuffled[disc][taken[disc]])
                taken[disc] += 1
                budget -= 1
                progressed = True
        if not progressed:
            break

    sampled.sort(key=lambda r: r["fb_id"])
    return sampled


def backfill(
    sampled: Sequence[Dict[str, Any]],
    backfill_rows: Sequence[Dict[str, Any]],
    disciplines: Sequence[str],
    min_per: int,
    seed: int,
) -> tuple[List[Dict[str, Any]], set[Any]]:
    """Top up disciplines below ``min_per`` with single-source (non-convergent) FBs.

    Every canonical discipline (excluding 'emerging') that has fewer than
    ``min_per`` examples in ``sampled`` — including disciplines with ZERO
    examples — is topped up from ``backfill_rows`` (already filtered valid).

    Args:
        sampled: Convergent FB rows after stratification.
        backfill_rows: Valid single-source (non-convergent) FB rows.
        disciplines: Canonical discipline set (incl. 'emerging' placeholder).
        min_per: Minimum examples per discipline to reach.
        seed: RNG seed.

    Returns:
        Tuple of (merged_rows, backfill_fb_ids) — merged rows sorted by fb_id
        and the set of fb_ids that came from the single-source backfill.
    """
    rng = random.Random(seed)
    canon = set(disciplines) - {"emerging"}
    by_disc: Dict[str, List[Dict[str, Any]]] = {}
    for row in sampled:
        by_disc.setdefault(row["discipline"], []).append(row)

    pool: Dict[str, List[Dict[str, Any]]] = {}
    for row in backfill_rows:
        pool.setdefault(row["discipline"], []).append(row)

    additions: List[Dict[str, Any]] = []
    for disc in sorted(canon):
        have = len(by_disc.get(disc, []))
        if have >= min_per:
            continue
        need = min_per - have
        candidates = pool.get(disc, [])
        rng.shuffle(candidates)
        additions.extend(candidates[:need])

    merged = list(sampled) + additions
    merged.sort(key=lambda r: r["fb_id"])
    return merged, {r["fb_id"] for r in additions}


def to_golden_example(row: Dict[str, Any], idx: int, is_backfill: bool = False) -> Dict[str, Any]:
    """Build a nested golden example matching stage4_golden.yaml + contract.

    Args:
        row: Valid FB row.
        idx: Sequential index for the id.

    Returns:
        Nested golden example dict.
    """
    depth = row["depth"]
    source_kind = "single-source (non-convergent) FB" if is_backfill else "convergent FB"
    example = {
        "id": f"S4-GOLD-MINED-{idx:05d}",
        "depth": depth,
        "input_fb": {
            "name": row["name"],
            "definition": row["definition"],
            "mechanism": row["mechanism"],
            "boundary": row["boundary"],
        },
        "expected_classification": {
            "discipline": row["discipline"],
            "domains": _parse_domains(row["domains"]),
            "depth": depth,
            "evidence": row["evidence"],
            "is_specialized": depth == "specialized",
        },
        "rationale": (
            f"Mined from {source_kind} {row['fb_id']}; "
            "gpt-oss teacher labels (discipline/domains/depth). "
            "Silver-standard — NOT hand-reviewed."
        ),
    }
    if is_backfill:
        example["is_backfill"] = True
    return example


def _coverage_report(sampled: Sequence[Dict[str, Any]]) -> str:
    """Build a human-readable coverage report for the sampled rows.

    Args:
        sampled: Sampled FB rows.

    Returns:
        Multi-line coverage string (discipline, depth, evidence counts).
    """
    by_disc: Dict[str, int] = {}
    by_depth: Dict[str, int] = {}
    by_ev: Dict[str, int] = {}
    for r in sampled:
        by_disc[r["discipline"]] = by_disc.get(r["discipline"], 0) + 1
        by_depth[r["depth"]] = by_depth.get(r["depth"], 0) + 1
        by_ev[r["evidence"]] = by_ev.get(r["evidence"], 0) + 1
    n_canon = len(set(CANONICAL_DISCIPLINES) - {"emerging"})
    lines = [
        f"disciplines covered: {len(by_disc)} / {n_canon}",
        f"depth coverage: {by_depth}",
        f"evidence coverage: {by_ev}",
        "per-discipline counts:",
    ]
    for disc in sorted(by_disc):
        lines.append(f"  {disc}: {by_disc[disc]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: fetch, filter, stratify, and write the mined training set."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to production DB")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output golden YAML path")
    parser.add_argument("--max-per", type=int, default=MAX_PER_DISCIPLINE)
    parser.add_argument("--max-total", type=int, default=MAX_TOTAL)
    parser.add_argument("--min-per", type=int, default=MIN_PER_DISCIPLINE)
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    parser.add_argument("--dry-run", action="store_true", help="Report counts, no write")
    parser.add_argument("--no-backfill", action="store_true", help="Skip single-source backfill")
    args = parser.parse_args(argv)

    rows = fetch_convergent_fbs(args.db)
    print(f"fetched {len(rows)} convergent non-emerging FBs")

    valid, reasons = filter_valid(
        rows, CANONICAL_DISCIPLINES, CANONICAL_DOMAINS, MAX_DOMAINS_PER_FB
    )
    print(f"valid: {len(valid)}")
    for reason in sorted(reasons):
        print(f"  dropped ({reason}): {reasons[reason]}")

    sampled = stratify(valid, args.max_per, args.max_total, args.seed, args.min_per)
    print(f"sampled (convergent, thin-preserved): {len(sampled)}")

    backfill_ids: set[Any] = set()
    if not args.no_backfill:
        backfill_rows = fetch_backfill_fbs(args.db)
        backfill_valid, breasons = filter_valid(
            backfill_rows, CANONICAL_DISCIPLINES, CANONICAL_DOMAINS, MAX_DOMAINS_PER_FB
        )
        print(f"backfill valid (single-source): {len(backfill_valid)}")
        for reason in sorted(breasons):
            print(f"  backfill dropped ({reason}): {breasons[reason]}")
        sampled, backfill_ids = backfill(
            sampled, backfill_valid, CANONICAL_DISCIPLINES, args.min_per, args.seed
        )

    print(f"final examples: {len(sampled)} (single-source backfilled: {len(backfill_ids)})")
    print(_coverage_report(sampled))

    if args.dry_run:
        print("dry-run — not writing")
        return 0

    examples = [
        to_golden_example(r, i + 1, r["fb_id"] in backfill_ids)
        for i, r in enumerate(sampled)
    ]
    doc = {
        "meta": {
            "version": "1.0",
            "purpose": "auto-sorter classifier training set (D2577)",
            "source": "scripts/mine_classifier_golden.py",
            "total_examples": len(examples),
            "backfilled_examples": len(backfill_ids),
            "note": (
                "silver-standard — gpt-oss teacher labels, NOT hand-reviewed; "
                "distinct from the hand-curated few-shot stage4_golden.yaml. "
                "Sparse disciplines (< min-per convergent examples) are topped up "
                "with single-source (non-convergent) FBs, flagged is_backfill=true."
            ),
        },
        "examples": examples,
    }
    blob = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)

    out = Path(args.out)
    safe_write(out, blob.encode("utf-8"))
    print(f"wrote {len(examples)} examples to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
