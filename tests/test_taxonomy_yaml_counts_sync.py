#!/usr/bin/env python3
"""D2512 — Taxonomy drift guards: YAML↔counts sync (Drift B) + cross-axis raw-alias coercion (Drift D).

Two independent, previously-UNLOCKED drift classes, found in a forensic audit:

  Drift B (BUG-208): `taxonomy_v5.yaml` canonicals and `taxonomy_counts` canonical
    status drift apart because seed_from_taxonomy_yaml() only INSERT-OR-IGNOREs
    and only runs on an empty table. Labels promoted in YAML after the first seed
    stay `emerging`/`raw` in the counts table, so D2399's check_for_replacements()
    competes garbage against a stale canonical set. `reconcile_canonical_status()`
    is the fix; this test proves it re-syncs deterministically.

  Drift D (BUG-210): 231 raw aliases appear in BOTH a discipline entry and a
    domain entry. The kind-scoped matcher (D2500) already resolves each per-axis
    with 0 cross-kind coercion — this test LOCKS that invariant so a future
    taxonomy edit that re-introduces coercion fails CI.

No live DB required: Drift B is tested against an in-memory SQLite replica of the
taxonomy_counts schema + the real YAML; Drift D reads the real config + schemas.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.schemas import (
    CANONICAL_DOMAINS,
    CANONICAL_DISCIPLINES,
    match_to_canonical,
)
from pipeline.taxonomy_manager import reconcile_canonical_status

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAX_PATH = PROJECT_ROOT / "config" / "taxonomy_v5.yaml"


def _make_counts_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE taxonomy_counts (
            label TEXT NOT NULL, label_type TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL, first_seen TEXT, last_updated TEXT,
            PRIMARY KEY (label, label_type)
        )
    """)
    return conn


def test_reconcile_promotes_yaml_canonicals() -> None:
    """Drift B: reconcile_canonical_status() must flip a stale non-canonical row
    (label present in YAML as canonical) to status='canonical'."""
    tax = yaml.safe_load(TAX_PATH.read_text(encoding="utf-8"))

    # Find a discipline canonical that is a good test subject (any canonical).
    disc_canon = tax["disciplines"][0]["canonical"]
    dom_canon = tax["domains"][0]["canonical"]

    conn = _make_counts_db()
    # Simulate the drift: canonical label parked at 'emerging' + 'raw'.
    conn.execute(
        "INSERT INTO taxonomy_counts (label, label_type, count, status) VALUES (?, 'discipline', 108, 'emerging')",
        (disc_canon,),
    )
    conn.execute(
        "INSERT INTO taxonomy_counts (label, label_type, count, status) VALUES (?, 'domain', 5, 'raw')",
        (dom_canon,),
    )
    conn.commit()

    reconcile_canonical_status(conn)

    got_disc = conn.execute(
        "SELECT status FROM taxonomy_counts WHERE label = ? AND label_type = 'discipline'",
        (disc_canon,),
    ).fetchone()["status"]
    got_dom = conn.execute(
        "SELECT status FROM taxonomy_counts WHERE label = ? AND label_type = 'domain'",
        (dom_canon,),
    ).fetchone()["status"]
    assert got_disc == "canonical", f"{disc_canon} still {got_disc}"
    assert got_dom == "canonical", f"{dom_canon} still {got_dom}"


def test_reconcile_demotes_removed_canonical() -> None:
    """Drift B (reverse): a DB-canonical label NOT in YAML must be demoted, so a
    removed canonical can't stay privileged in the counts table."""
    conn = _make_counts_db()
    conn.execute(
        "INSERT INTO taxonomy_counts (label, label_type, count, status) VALUES ('defunct label', 'discipline', 999, 'canonical')"
    )
    conn.commit()
    reconcile_canonical_status(conn)
    got = conn.execute(
        "SELECT status FROM taxonomy_counts WHERE label = 'defunct label'"
    ).fetchone()["status"]
    assert got != "canonical", f"defunct label still canonical: {got}"


def test_yaml_canonicals_all_present_after_reconcile() -> None:
    """Drift B: after reconcile, EVERY YAML canonical must be status='canonical'."""
    tax = yaml.safe_load(TAX_PATH.read_text(encoding="utf-8"))
    conn = _make_counts_db()
    reconcile_canonical_status(conn)
    for key, axis in (("domains", "domain"), ("disciplines", "discipline")):
        for entry in tax[key]:
            row = conn.execute(
                "SELECT status FROM taxonomy_counts WHERE label = ? AND label_type = ?",
                (entry["canonical"], axis),
            ).fetchone()
            assert row is not None, f"missing {axis} canonical {entry['canonical']!r} after reconcile"
            assert row["status"] == "canonical", f"{entry['canonical']!r} is {row['status']}"


def test_update_counts_is_idempotent() -> None:
    """Drift F (BUG-211): update_counts_from_fbs() must be an idempotent full
    recount — a second call must not change any count/status. The prior full-scan
    fallback incremented on top of existing counts (≈3x inflation observed live:
    "marketing & advertising" = 360 in taxonomy_counts vs 120 in the DB)."""
    from pipeline.taxonomy_manager import update_counts_from_fbs

    conn = _make_counts_db()
    conn.execute("""
        CREATE TABLE fbs (
            domains TEXT, domains_raw TEXT, discipline TEXT, discipline_raw TEXT,
            committed_at TEXT
        )
    """)
    # Long-tail raw domain (never canonical/synonym) + a canonical domain.
    conn.execute(
        "INSERT INTO fbs (domains, domains_raw, discipline, discipline_raw) VALUES (?,?,?,?)",
        ('["marketing & communications"]', '["zz-marketing & zz-advertising"]', "psychology", "zz-cog-sci"),
    )
    conn.execute(
        "INSERT INTO fbs (domains, domains_raw, discipline, discipline_raw) VALUES (?,?,?,?)",
        ('["marketing & communications"]', '["zz-marketing & zz-advertising"]', "psychology", None),
    )
    conn.commit()

    def _snapshot() -> dict:
        return {
            (r["label"], r["label_type"]): (r["count"], r["status"])
            for r in conn.execute(
                "SELECT label, label_type, count, status FROM taxonomy_counts"
            )
        }

    update_counts_from_fbs(conn)
    first = _snapshot()
    update_counts_from_fbs(conn)
    second = _snapshot()

    # The synthetic long-tail raw domain must be counted exactly once (2 FBs).
    key = ("zz-marketing & zz-advertising", "domain")
    assert first.get(key) == (2, "raw") or first.get(key) == (2, "emerging"), first.get(key)
    assert first == second, "update_counts_from_fbs() is NOT idempotent"


def test_no_cross_kind_coercion_from_overlapping_raw_aliases() -> None:
    """Drift D (BUG-210): every raw alias present in BOTH a discipline and a
    domain entry must resolve to a same-kind canonical (or None), NEVER coerce
    cross-kind. Locks the 231-overlap invariant verified at D2512 (0 coercions)."""
    tax = yaml.safe_load(TAX_PATH.read_text(encoding="utf-8"))
    disc_raw: set[str] = set()
    dom_raw: set[str] = set()
    for e in tax["disciplines"]:
        disc_raw.update(r.lower() for r in e.get("raw", []))
    for e in tax["domains"]:
        dom_raw.update(r.lower() for r in e.get("raw", []))

    overlap = disc_raw & dom_raw
    disc_canon = {c.lower() for c in CANONICAL_DISCIPLINES}
    dom_canon = {c.lower() for c in CANONICAL_DOMAINS}

    coercions: list[tuple[str, str, str]] = []
    for k in overlap:
        d = match_to_canonical(k, "discipline")
        dm = match_to_canonical(k, "domain")
        if d and d.lower() not in disc_canon:
            coercions.append((k, "discipline", d))
        if dm and dm.lower() not in dom_canon:
            coercions.append((k, "domain", dm))
    assert not coercions, f"cross-kind coercions from overlapping raw aliases: {coercions[:20]}"


if __name__ == "__main__":
    test_reconcile_promotes_yaml_canonicals()
    test_reconcile_demotes_removed_canonical()
    test_yaml_canonicals_all_present_after_reconcile()
    test_no_cross_kind_coercion_from_overlapping_raw_aliases()
    test_update_counts_is_idempotent()
    print("✅ D2512 taxonomy drift guards passed")
