#!/usr/bin/env python3
"""
taxonomy_manager.py — Dynamic canonical taxonomy with counter table + auto-replacement.
Authority: D2066, CONSTITUTION.md §3

Core mechanism (D2066):
  1. Stage 4 classification is open-set → raw labels accumulate in taxonomy_counts
  2. When count(raw_label) > count(weakest_canonical) × threshold, flag for human review
  3. Human approves → raw promoted to canonical, weakest demoted to displaced
  4. Auto-generates taxonomy_v<N+1>.yaml after approved replacements

Human review gates:
  - C8-G1: After Stage 6, replacement candidates are written to human_review_taxonomy.json
  - C8-G2: Before new taxonomy YAML becomes active, human reviews the generated file
  - C8-G3: Flood detection — if >20% labels are emerging, pauses for batch review
"""

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    DB_PATH,
    PROJECT_ROOT,
    SCHEMA_VERSION,
    TAXONOMY_EMERGING_FREQ,
    TAXONOMY_FLOOD_THRESHOLD,
    TAXONOMY_REPLACEMENT_THRESHOLD,
    TAXONOMY_VERSION,
)
from pipeline.stamp import get_pipeline_commit

# ── Constants (D2231: C12 — read from config via pipeline_paths) ─────────

MAX_DOMAINS: int = 25       # D272
MAX_DISCIPLINES: int = 47   # D272
REPLACEMENT_THRESHOLD_RATIO: float = TAXONOMY_REPLACEMENT_THRESHOLD  # emerging must exceed canonical by 10%
EMERGING_FREQ_THRESHOLD: int = TAXONOMY_EMERGING_FREQ              # raw→emerging promotion threshold
FLOOD_THRESHOLD_RATIO: float = TAXONOMY_FLOOD_THRESHOLD            # >20% unmatched = flood warning (C8-G3)


# ── Path helpers ─────────────────────────────────────────────────────────

def _get_taxonomy_path() -> Path:
    """Return path to current taxonomy YAML (config/taxonomy_v5.yaml)."""
    return PROJECT_ROOT / "config" / "taxonomy_v5.yaml"


def _get_next_taxonomy_path() -> Path:
    """Return path for next-version taxonomy YAML."""
    try:
        major = int(TAXONOMY_VERSION.split('.')[0])
        return PROJECT_ROOT / "config" / f"taxonomy_v{major + 1}.yaml"
    except (ValueError, IndexError):
        return PROJECT_ROOT / "config" / "taxonomy_v6.yaml"


# ── Table initialization ─────────────────────────────────────────────────

def init_taxonomy_counts_table(conn: sqlite3.Connection) -> None:
    """Create the taxonomy_counts accumulation table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS taxonomy_counts (
            label TEXT NOT NULL,
            label_type TEXT NOT NULL CHECK(label_type IN ('domain', 'discipline')),
            count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL CHECK(status IN ('canonical', 'emerging', 'raw', 'displaced')),
            first_seen TEXT,
            last_updated TEXT,
            PRIMARY KEY (label, label_type)
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_taxonomy_counts_type_status
        ON taxonomy_counts(label_type, status);
    """)
    conn.commit()


def seed_from_taxonomy_yaml(conn: sqlite3.Connection) -> int:
    """
    On first run, seed taxonomy_counts from the current taxonomy YAML.
    Returns the number of canonical entries seeded.
    """
    taxonomy_path = _get_taxonomy_path()
    if not taxonomy_path.exists():
        return 0

    with open(taxonomy_path) as f:
        tax = yaml.safe_load(f)

    now = datetime.now(UTC).isoformat()
    count = 0

    for domain_entry in tax.get("domains", []):
        canonical = domain_entry["canonical"]
        conn.execute(
            """INSERT OR IGNORE INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated)
               VALUES (?, 'domain', 0, 'canonical', ?, ?)""",
            (canonical, now, now)
        )
        count += 1
        # Also seed raw aliases as 'raw' status for tracking
        for raw_label in domain_entry.get("raw", []):
            raw_lower = raw_label.lower().strip()
            if raw_lower == canonical:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated)
                   VALUES (?, 'domain', 0, 'raw', ?, ?)""",
                (raw_lower, now, now)
            )

    for disc_entry in tax.get("disciplines", []):
        canonical = disc_entry["canonical"]
        conn.execute(
            """INSERT OR IGNORE INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated)
               VALUES (?, 'discipline', 0, 'canonical', ?, ?)""",
            (canonical, now, now)
        )
        count += 1
        for raw_label in disc_entry.get("raw", []):
            raw_lower = raw_label.lower().strip()
            if raw_lower == canonical:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated)
                   VALUES (?, 'discipline', 0, 'raw', ?, ?)""",
                (raw_lower, now, now)
            )

    conn.commit()
    return count


# ── Count update from committed FBs ─────────────────────────────────────

def update_counts_from_fbs(conn: sqlite3.Connection) -> dict:
    """
    After Stage 6 commit: scan committed FBs' domains/disciplines and update counts.
    Auto-promotes raw→emerging when count ≥ EMERGING_FREQ_THRESHOLD.

    Returns:
        dict with keys 'domain', 'discipline' → {label: new_count} for changed labels,
        plus 'flood_warning': bool if >20% labels are unmatched.
    """
    now = datetime.now(UTC).isoformat()
    changes: dict = {"domain": {}, "discipline": {}, "flood_warning": False}
    total_labels = 0
    unmatched_labels = 0

    rows = conn.execute("""
        SELECT domains, discipline FROM fbs
        WHERE committed_at >= datetime('now', '-24 hours')
    """).fetchall()

    # If no recent FBs, scan all
    if not rows:
        rows = conn.execute("SELECT domains, discipline FROM fbs").fetchall()

    for domains_json, discipline in rows:
        # ── Domain labels ──
        try:
            domain_labels = json.loads(domains_json) if isinstance(domains_json, str) else domains_json
        except (json.JSONDecodeError, TypeError):
            domain_labels = []

        for label in (domain_labels or []):
            label_str = label.lower().strip()
            if not label_str or label_str == "emerging":
                continue
            total_labels += 1

            existing = conn.execute(
                "SELECT count, status FROM taxonomy_counts WHERE label = ? AND label_type = 'domain'",
                (label_str,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE taxonomy_counts SET count = count + 1, last_updated = ? "
                    "WHERE label = ? AND label_type = 'domain'",
                    (now, label_str)
                )
                new_count = existing[0] + 1
            else:
                conn.execute(
                    "INSERT INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated) "
                    "VALUES (?, 'domain', 1, 'raw', ?, ?)",
                    (label_str, now, now)
                )
                new_count = 1
                unmatched_labels += 1

            changes["domain"][label_str] = new_count

        # ── Discipline label ──
        if discipline and discipline != "emerging":
            disc_str = discipline.lower().strip()
            total_labels += 1

            existing = conn.execute(
                "SELECT count, status FROM taxonomy_counts WHERE label = ? AND label_type = 'discipline'",
                (disc_str,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE taxonomy_counts SET count = count + 1, last_updated = ? "
                    "WHERE label = ? AND label_type = 'discipline'",
                    (now, disc_str)
                )
                new_count = existing[0] + 1
            else:
                conn.execute(
                    "INSERT INTO taxonomy_counts (label, label_type, count, status, first_seen, last_updated) "
                    "VALUES (?, 'discipline', 1, 'raw', ?, ?)",
                    (disc_str, now, now)
                )
                new_count = 1
                unmatched_labels += 1

            changes["discipline"][disc_str] = new_count

    # Auto-promote raw → emerging at frequency threshold
    conn.execute(
        "UPDATE taxonomy_counts SET status = 'emerging' WHERE status = 'raw' AND count >= ?",
        (EMERGING_FREQ_THRESHOLD,)
    )

    # Flood detection (C8-G3): >20% labels unmatched
    if total_labels > 0 and (unmatched_labels / total_labels) > FLOOD_THRESHOLD_RATIO:
        changes["flood_warning"] = True

    conn.commit()
    return changes


# ── Replacement detection ─────────────────────────────────────────────────

def check_for_replacements(conn: sqlite3.Connection) -> list[dict]:
    """
    Check if emerging labels exceed the weakest canonical by threshold ratio.

    Returns:
        List of replacement candidate dicts, each with:
        label_type, emerging_label, emerging_count, displace_canonical, displace_count
    """
    candidates: list[dict] = []

    for label_type, _max_count in [("domain", MAX_DOMAINS), ("discipline", MAX_DISCIPLINES)]:
        # Get the weakest canonical (lowest count)
        weakest = conn.execute(
            """SELECT label, count FROM taxonomy_counts
               WHERE label_type = ? AND status = 'canonical'
               ORDER BY count ASC LIMIT 1""",
            (label_type,)
        ).fetchone()

        if not weakest:
            continue

        weakest_label, weakest_count = weakest

        # Get emerging labels exceeding weakest
        emerging = conn.execute(
            """SELECT label, count FROM taxonomy_counts
               WHERE label_type = ? AND status = 'emerging'
               AND count > ?
               ORDER BY count DESC""",
            (label_type, weakest_count)
        ).fetchall()

        # Track the displaced so multiple replacements cascade correctly
        displaced_label = weakest_label
        displaced_count = weakest_count

        for emerging_label, emerging_count in emerging:
            if emerging_count > displaced_count * REPLACEMENT_THRESHOLD_RATIO:
                candidates.append({
                    "label_type": label_type,
                    "emerging_label": emerging_label,
                    "emerging_count": emerging_count,
                    "displace_canonical": displaced_label,
                    "displace_count": displaced_count,
                })
                # The just-displaced becomes the new floor for next comparison
                displaced_label = emerging_label
                displaced_count = emerging_count

    return candidates


# ── Apply human-approved replacements ────────────────────────────────────

def apply_replacements(conn: sqlite3.Connection, approved: list[dict]) -> int:
    """
    Apply approved replacements: promote emerging→canonical, demote displaced→displaced.

    Args:
        approved: list of replacement dicts with 'approved': true

    Returns:
        Number of replacements applied.
    """
    now = datetime.now(UTC).isoformat()
    applied = 0

    for repl in approved:
        conn.execute(
            "UPDATE taxonomy_counts SET status = 'canonical', last_updated = ? "
            "WHERE label = ? AND label_type = ?",
            (now, repl["emerging_label"], repl["label_type"])
        )
        conn.execute(
            "UPDATE taxonomy_counts SET status = 'displaced', last_updated = ? "
            "WHERE label = ? AND label_type = ?",
            (now, repl["displace_canonical"], repl["label_type"])
        )
        applied += 1

    conn.commit()
    return applied


# ── Taxonomy YAML generation ─────────────────────────────────────────────

def generate_taxonomy_yaml(conn: sqlite3.Connection, output_path: Path | None = None) -> Path:
    """
    Auto-generate taxonomy_v<N+1>.yaml from taxonomy_counts table.
    Canonical entries ordered by count descending. Raw aliases preserved from current taxonomy.

    Returns:
        Path to the generated YAML file.
    """
    if output_path is None:
        output_path = _get_next_taxonomy_path()

    current_path = _get_taxonomy_path()
    with open(current_path) as f:
        current_tax = yaml.safe_load(f)

    # ── Canonical entries from DB ──
    canonical_domains = conn.execute(
        "SELECT label, count FROM taxonomy_counts WHERE label_type = 'domain' AND status = 'canonical' ORDER BY count DESC"
    ).fetchall()

    canonical_disciplines = conn.execute(
        "SELECT label, count FROM taxonomy_counts WHERE label_type = 'discipline' AND status = 'canonical' ORDER BY count DESC"
    ).fetchall()

    # ── Raw-to-canonical mapping from current taxonomy ──
    raw_map_domain: dict[str, str] = {}
    raw_map_discipline: dict[str, str] = {}
    canonical_to_group: dict[str, str] = {}

    for entry in current_tax.get("domains", []):
        canonical_to_group[entry["canonical"]] = entry.get("group", "Uncategorized")
        for raw_label in entry.get("raw", []):
            raw_map_domain[raw_label.lower()] = entry["canonical"]

    for entry in current_tax.get("disciplines", []):
        canonical_to_group[entry["canonical"]] = entry.get("group", "Uncategorized")
        for raw_label in entry.get("raw", []):
            raw_map_discipline[raw_label.lower()] = entry["canonical"]

    # ── All raw labels from DB that map to each canonical ──
    all_raw_labels = conn.execute(
        "SELECT label, label_type FROM taxonomy_counts WHERE status IN ('raw', 'emerging')"
    ).fetchall()

    def _build_entries(canonical_list, label_type, raw_map):
        entries = []
        for canonical, _count in canonical_list:
            raw_aliases = [
                label for label, lt in all_raw_labels
                if lt == label_type and raw_map.get(label) == canonical
            ]
            # Add the canonical itself and deduplicate
            raw_set = set(raw_aliases)
            raw_set.add(canonical)
            entries.append({
                "canonical": canonical,
                "group": canonical_to_group.get(canonical, "Uncategorized"),
                "raw": sorted(raw_set),
            })
        return entries

    new_domains = _build_entries(canonical_domains, "domain", raw_map_domain)
    new_disciplines = _build_entries(canonical_disciplines, "discipline", raw_map_discipline)

    # ── Version ──
    try:
        major = int(TAXONOMY_VERSION.split('.')[0])
        new_version = f"{major + 1}.0"
    except (ValueError, IndexError):
        new_version = "6.0"

    # ── Displaced canonicals ──
    displaced = [
        row[0] for row in conn.execute(
            "SELECT label FROM taxonomy_counts WHERE status = 'displaced'"
        ).fetchall()
    ]

    new_taxonomy = {
        "version": new_version,
        "classification_version": f"v{new_version}",
        "auto_generated": datetime.now(UTC).isoformat(),
        "generated_by": "taxonomy_manager.py",
        "pipeline_commit": get_pipeline_commit(),
        "groups": current_tax.get("groups", {}),
        "domains": new_domains,
        "disciplines": new_disciplines,
        "meta": {
            "catch_all_domain": "emerging",
            "catch_all_discipline": "emerging",
            "catch_all_description": current_tax.get("meta", {}).get("catch_all_description", ""),
            "displaced_canonicals": displaced,
        }
    }

    with open(output_path, 'w') as f:
        yaml.dump(new_taxonomy, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return output_path


# ── Full post-commit hook ─────────────────────────────────────────────────

def run_post_commit_taxonomy(conn: sqlite3.Connection, human_review_dir: Path) -> Path | None:
    """
    Full post-commit taxonomy update: ensure table, seed if first run, update counts,
    check replacements. If replacements found, write human_review_taxonomy.json.

    This is the single entry point called from stage6_commit.py after commit.

    Args:
        conn: SQLite connection to maxwell.db
        human_review_dir: Directory to write human_review_taxonomy.json (e.g. stage5_verify/{run_id}/)

    Returns:
        Path to human_review_taxonomy.json if replacements need review, None otherwise.
    """
    # 1. Ensure table exists
    init_taxonomy_counts_table(conn)

    # 2. Seed from taxonomy YAML on first run
    existing_canonical = conn.execute(
        "SELECT COUNT(*) FROM taxonomy_counts WHERE status = 'canonical'"
    ).fetchone()[0]

    if existing_canonical == 0:
        seeded = seed_from_taxonomy_yaml(conn)
        if seeded == 0:
            print("⚠️  WARNING: Could not seed taxonomy_counts — taxonomy YAML not found or empty.")

    # 3. Update counts from committed FBs
    changes = update_counts_from_fbs(conn)

    # 4. Flood warning (C8-G3)
    if changes.get("flood_warning"):
        print("\n⚠️  FLOOD WARNING (C8-G3): >20% of labels are unmatched.")
        print("   Consider batch-reviewing all emerging labels before proceeding.")

    # 5. Check for replacements
    candidates = check_for_replacements(conn)

    if not candidates:
        return None

    # 6. Write human review file
    human_review_dir.mkdir(parents=True, exist_ok=True)
    review_path = human_review_dir / "human_review_taxonomy.json"

    review_data = {
        "review_type": "taxonomy_replacement",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_commit": get_pipeline_commit(),
        "schema_version": SCHEMA_VERSION,
        "flood_warning": changes.get("flood_warning", False),
        "candidates": candidates,
        "instructions": (
            "HUMAN REVIEW REQUIRED (C8-G1): Review each candidate below. "
            "Set 'approved': true to apply the replacement (emerging label promoted to canonical, "
            "weakest canonical demoted to 'displaced'). Set 'approved': false to reject. "
            "After review, run:\n"
            "  python3 pipeline/taxonomy_manager.py --apply <this_file>\n\n"
            "C8-G2: After applying, review the generated taxonomy_v<N+1>.yaml before "
            "updating pipeline_config.yaml's taxonomy_version to point to it."
        ),
    }

    with open(review_path, 'w') as f:
        json.dump(review_data, f, indent=2)

    return review_path


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dynamic Taxonomy Manager (D2066)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize taxonomy_counts table from taxonomy YAML")
    sub.add_parser("check", help="Check for replacement candidates")
    sub.add_parser("generate", help="Generate next-version taxonomy YAML")
    apply_p = sub.add_parser("apply", help="Apply approved replacements from review JSON")
    apply_p.add_argument("review_file", type=str, help="Path to human_review_taxonomy.json")

    args = parser.parse_args()

    db_path = DB_PATH
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        if args.command == "init":
            init_taxonomy_counts_table(conn)
            n = seed_from_taxonomy_yaml(conn)
            print(f"✅ taxonomy_counts initialized: {n} canonical entries seeded from taxonomy_v5.yaml")

        elif args.command == "check":
            init_taxonomy_counts_table(conn)
            existing = conn.execute(
                "SELECT COUNT(*) FROM taxonomy_counts WHERE status = 'canonical'"
            ).fetchone()[0]
            if existing == 0:
                seed_from_taxonomy_yaml(conn)

            changes = update_counts_from_fbs(conn)
            if changes.get("flood_warning"):
                print("⚠️  Flood warning: >20% labels unmatched.")

            candidates = check_for_replacements(conn)
            if candidates:
                print(f"📋 {len(candidates)} replacement candidate(s):")
                for c in candidates:
                    print(f"  {c['label_type']}: '{c['emerging_label']}' "
                          f"(n={c['emerging_count']}) > '{c['displace_canonical']}' "
                          f"(n={c['displace_count']})")
            else:
                print("✅ No replacements needed.")

        elif args.command == "generate":
            path = generate_taxonomy_yaml(conn)
            print(f"✅ Generated: {path}")
            print("   Review it (C8-G2), then update pipeline_config.yaml taxonomy_version if approved.")

        elif args.command == "apply":
            with open(args.review_file) as f:
                review = json.load(f)
            approved = [c for c in review.get("candidates", []) if c.get("approved")]
            if not approved:
                print("No approved candidates (all rejected or none marked 'approved': true).")
                sys.exit(0)

            n = apply_replacements(conn, approved)
            print(f"✅ Applied {n} replacement(s).")

            # Auto-generate updated taxonomy
            new_path = generate_taxonomy_yaml(conn)
            print(f"✅ Generated updated taxonomy: {new_path}")
            print("   C8-G2: Review this file before updating pipeline_config.yaml.")
            print(f"   Then update: taxonomy_version: '{TAXONOMY_VERSION}' → extracted from new file.")

        else:
            parser.print_help()

    finally:
        conn.close()
