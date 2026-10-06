#!/usr/bin/env python3
"""build_taxonomy_v7.py — build a MECE-pure taxonomy_v7 from the live v5 source (D-2856).

Deterministic, review-then-apply. This does NOT touch the live file; it writes
config/taxonomy_v7.yaml + governance/taxonomy_v7_migration.json. After the partition validator
(scripts/validate_taxonomy_partition.py) reports CLEAN on the v7 output, a SEPARATE apply step
backs up v5, promotes v7, bumps config/version.yaml, freezes closed_menu_v7.json and re-pins
config/menu_axis_hashes.yaml.

Transforms applied, each documented in the migration report:
  1. OPAQUE ID   — every entry gets a stable `id` (disc-001.. / dom-001..) assigned by file order.
  2. RAW HYGIENE — raw lists are deduped (case/punctuation-insensitive, first occurrence kept).
  3. MECE        — every raw synonym that maps to >1 entry is assigned EXACTLY ONE owner:
                    (a) exact-canonical match wins; (b) else the entry with the FEWEST raw
                    synonyms (most specific / least overloaded) wins; (c) tie -> discipline axis;
                    (d) tie -> lexicographic. Non-owners DROP the raw string.
  4. DISCRIMINATOR— organizational theory vs business administration get explicit differentia
                    (explanatory-positive vs prescriptive-normative) and cross-exclude each other.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "config" / "taxonomy_v5.yaml"
OUT = ROOT / "config" / "taxonomy_v7.yaml"
MIG = ROOT / "governance" / "taxonomy_v7_migration.json"


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


#: Cross-axis canonical NORMALISED collisions that D-2853 ruled to rename to axis-scoped labels.
#: The domain carries the APPLIED-PRACTICE side; the discipline keeps the academic-method name.
_CANONICAL_RENAMES: dict[str, dict[str, str]] = {
    "domains": {"research & methodology": "research practice"},
}


def _apply_renames(tax: dict) -> list[str]:
    """Rename cross-axis normalised-canonical collisions to axis-scoped labels (D-2853)."""
    log: list[str] = []
    for axis, mapping in _CANONICAL_RENAMES.items():
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            old = e.get("canonical")
            if old in mapping:
                e["canonical"] = mapping[old]
                log.append(f"rename: {axis} {old!r} -> {mapping[old]!r}")
    return log


def _assign_ids(tax: dict) -> None:
    """Assign stable opaque ids by file order. Preserves any pre-existing id (idempotent re-run)."""
    next_disc = 1
    next_dom = 1
    for axis in ("disciplines", "domains"):
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            if str(e.get("id") or "").strip():
                continue  # already minted — never renumber (stability)
            if axis == "disciplines":
                e["id"] = f"disc-{next_disc:03d}"
                next_disc += 1
            else:
                e["id"] = f"dom-{next_dom:03d}"
                next_dom += 1


def _dedup_raw(tax: dict) -> list[str]:
    """Dedupe each raw list (case/punctuation-insensitive, first occurrence kept). Returns log lines."""
    log: list[str] = []
    for axis in ("disciplines", "domains"):
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            raw = e.get("raw")
            if not isinstance(raw, list):
                continue
            seen: dict[str, str] = {}
            deduped: list[str] = []
            for r in raw:
                rs = str(r).strip()
                if not rs:
                    continue
                key = _norm(rs)
                if key in seen:
                    log.append(f"dedup: {axis} {e.get('canonical')!r} dropped dup raw {rs!r} "
                               f"(kept {seen[key]!r})")
                    continue
                seen[key] = rs
                deduped.append(rs)
            e["raw"] = deduped
    return log


def _raw_owners(tax: dict) -> dict[str, list[dict]]:
    """Index every normalized raw string -> its owning entries (axis, id, canonical, raw_count)."""
    idx: dict[str, list[dict]] = {}
    for axis in ("disciplines", "domains"):
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            raw = e.get("raw")
            if not isinstance(raw, list):
                continue
            for r in raw:
                idx.setdefault(_norm(r), []).append({
                    "axis": axis,
                    "id": str(e.get("id") or "?"),
                    "canonical": str(e.get("canonical") or "?"),
                    "raw_count": len(raw),
                    "raw": str(r),
                })
    return idx


def _resolve(owners: list[dict]) -> tuple[dict, str]:
    """Choose the single owner for a collided raw string. Deterministic + documented."""
    key = _norm(owners[0]["raw"])
    exact = [o for o in owners if _norm(o["canonical"]) == key]
    if len(exact) == 1:
        return exact[0], "exact-canonical-match"
    if len(exact) > 1:
        # raw == canonical of several entries — impossible for distinct canonicals, but prefer
        # the entry where it IS the canonical label (all exact here), tie-break by fewest raws.
        return min(exact, key=lambda o: (o["raw_count"], _axis_rank(o["axis"]), o["canonical"])), \
            "exact-canonical-tie"
    # No exact match: most-specific entry (fewest raw synonyms) wins; discipline on tie.
    best = min(owners, key=lambda o: (o["raw_count"], _axis_rank(o["axis"]), o["canonical"]))
    return best, "fewest-raws-most-specific"


def _axis_rank(axis: str) -> int:
    return 0 if axis == "disciplines" else 1


def _resolve_partition(tax: dict) -> list[dict]:
    """Assign every collided raw string to exactly one owner; drop it from non-owners."""
    owners = _raw_owners(tax)
    log: list[dict] = []
    # Build a lookup of raw key -> set of entry (axis,id) so we can strip non-owners.
    for key, olist in owners.items():
        uniq = {(o["axis"], o["id"]) for o in olist}
        if len(uniq) <= 1:
            continue
        owner, reason = _resolve(olist)
        dropped = [o for o in olist if (o["axis"], o["id"]) != (owner["axis"], owner["id"])]
        for d in dropped:
            for e in tax.get(d["axis"], []):
                if isinstance(e, dict) and str(e.get("id")) == d["id"]:
                    e["raw"] = [r for r in e.get("raw", []) if _norm(r) != key]
        log.append({
            "raw": olist[0]["raw"],
            "owner_axis": owner["axis"],
            "owner_id": owner["id"],
            "owner_canonical": owner["canonical"],
            "reason": reason,
            "dropped_from": [
                {"axis": d["axis"], "id": d["id"], "canonical": d["canonical"]} for d in dropped
            ],
        })
    return log


def _apply_discriminators(tax: dict) -> list[str]:
    """org-theory vs business-administration differentia + cross-exclusion (D-NEXT-1)."""
    log: list[str] = []
    disc = {e.get("canonical"): e for e in tax.get("disciplines", []) if isinstance(e, dict)}
    ot = disc.get("organizational theory")
    ba = disc.get("business administration")
    if ot is not None:
        ot["differentia"] = (
            "EXPLANATORY/POSITIVE lens: the organization is the OBJECT of inquiry — how formal "
            "organizations are structured, coordinate, and change. Asks 'how do they work?', never "
            "'how should I steer one?'"
        )
        ot["exclude"] = ["sociology", "strategic thinking", "business administration"]
        log.append("organizational theory: discriminator set (explanatory lens; excludes BA)")
    if ba is not None:
        ba["differentia"] = (
            "PRESCRIPTIVE/NORMATIVE lens: the managerial FUNCTION is the OBJECT — how to steer an "
            "organization toward objectives under resource constraints (strategy, operations, HR, "
            "organizational design). Asks 'how should I run it?', never 'how does it naturally work?'"
        )
        ba["exclude"] = ["organizational theory", "strategic thinking", "decision making",
                         "risk management"]
        log.append("business administration: discriminator set (prescriptive lens; excludes OT)")
    return log


def _crash_safe_write(path: Path, text: str) -> None:
    import os
    import tempfile
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


def main() -> int:
    tax = load(SRC)
    rename_log = _apply_renames(tax)
    _assign_ids(tax)
    dedup_log = _dedup_raw(tax)
    part_log = _resolve_partition(tax)
    disc_log = _apply_discriminators(tax)

    # bump the internal version stamps to v7.
    tax["version"] = "v7"
    tax["classification_version"] = "v7"

    _crash_safe_write(OUT, yaml.safe_dump(tax, sort_keys=False, allow_unicode=True))
    report = {
        "source": str(SRC),
        "output": str(OUT),
        "schema": "taxonomy v7",
        "disciplines": len(tax.get("disciplines", [])),
        "domains": len(tax.get("domains", [])),
        "deduped_raw": len(dedup_log),
        "partition_resolutions": len(part_log),
        "canonical_renames": rename_log,
        "discriminator_edits": disc_log,
        "partition_log": part_log,
    }
    _crash_safe_write(MIG, json.dumps(report, indent=2, ensure_ascii=False))

    # Self-validate the output MUST be clean before anyone considers applying it.
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_taxonomy_partition import check_partition  # noqa: E402
    problems = check_partition(tax)
    print(f"built {OUT}")
    print(f"deduped_raw={len(dedup_log)} partition_resolutions={len(part_log)} "
          f"violations_after={len(problems)}")
    for p in problems:
        print("  STILL-VIOLATES: " + p)
    print(f"migration report: {MIG}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
