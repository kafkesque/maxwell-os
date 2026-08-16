#!/usr/bin/env python3
"""
query.py — Simple CLI browser for Foundation Blocks.
========================================================
Authority: CONSTITUTION.md §2.3

Interactive FB browser. View, search, and explore FBs.

Usage:
    python3 pipeline/query.py                          # Interactive mode
    python3 pipeline/query.py --show fb_abc123         # Show specific FB
    python3 pipeline/query.py --stats                  # DB statistics
    python3 pipeline/query.py --export > fbs.jsonl     # Export all FBs
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH


def get_conn() -> sqlite3.Connection:
    """Get a read-only connection."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run stage6_commit.py first.")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def show_fb(conn: sqlite3.Connection, fb_id: str) -> dict | None:
    """Show a specific FB by ID (full or partial match)."""
    # Try exact match first
    row = conn.execute(
        "SELECT * FROM fbs WHERE fb_id = ?", (fb_id,)
    ).fetchone()

    if not row:
        # Try partial match on name
        rows = conn.execute(
            "SELECT * FROM fbs WHERE name LIKE ? LIMIT 10",
            (f"%{fb_id}%",),
        ).fetchall()
        if not rows:
            print(f"❌ No FB found matching: {fb_id}")
            return None
        if len(rows) > 1:
            print(f"Found {len(rows)} matches:")
            for r in rows:
                print(f"  {r['fb_id'][:12]}... | {r['name']} | {r['discipline']}")
            print()
        row = rows[0]

    fb = dict(row)
    _print_fb_full(fb)
    return fb


def show_stats(conn: sqlite3.Connection):
    """Show database statistics."""
    total = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    by_status = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM fbs GROUP BY status"
    ).fetchall()
    by_depth = conn.execute(
        "SELECT depth, COUNT(*) as cnt FROM fbs GROUP BY depth"
    ).fetchall()
    by_discipline = conn.execute(
        "SELECT discipline, COUNT(*) as cnt FROM fbs GROUP BY discipline "
        "ORDER BY cnt DESC LIMIT 15"
    ).fetchall()

    print("\n╔══════════════════════════════════════╗")
    print("║   Maxwell OS — FB Database Stats     ║")
    print("╚══════════════════════════════════════╝")
    print(f"  Total FBs: {total}")
    print()
    print("  By Status:")
    for r in by_status:
        print(f"    {r['status']:15s} {r['cnt']:>6}")
    print()
    print("  By Depth:")
    for r in by_depth:
        print(f"    {r['depth']:15s} {r['cnt']:>6}")
    print()
    print("  Top Disciplines:")
    for r in by_discipline:
        print(f"    {r['discipline']:30s} {r['cnt']:>6}")


def export_all(conn: sqlite3.Connection):
    """Export all FBs as JSONL to stdout."""
    rows = conn.execute("SELECT * FROM fbs ORDER BY name").fetchall()
    for row in rows:
        d = dict(row)
        for field in ["domains", "source_clusters", "source_books", "source_ids",
                      "verification_results", "classification_errors"]:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    pass
        print(json.dumps(d, ensure_ascii=False))


def _get_query_version() -> str:
    """Read banner version from config/version.yaml (D2169: single source of truth)."""
    try:
        import yaml
        vcfg = yaml.safe_load(Path("config/version.yaml").read_text())
        return str(vcfg.get("query_banner_version", "3.0"))
    except Exception:
        return "3.0"


def interactive(conn: sqlite3.Connection):
    """Simple interactive browser loop."""
    banner_v: str = _get_query_version()
    print("\n╔══════════════════════════════════════════╗")
    print(f"║   Maxwell OS v{banner_v} — FB Browser          ║")
    print("╚══════════════════════════════════════════╝")
    print("  Type 'help' for commands, 'quit' to exit.")
    print()

    while True:
        try:
            cmd = input("fb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action in ("quit", "exit", "q"):
            break
        elif action in ("help", "h"):
            print("  Commands:")
            print("    show <id|name>  — Display a specific FB")
            print("    list [N]        — List recent FBs (default 10)")
            print("    search <query>  — Full-text search")
            print("    stats           — Database statistics")
            print("    domains         — List distinct domains")
            print("    disciplines     — List distinct disciplines")
            print("    help            — This help")
            print("    quit            — Exit")
        elif action in ("show", "view"):
            if not arg:
                print("  Usage: show <fb_id or name>")
            else:
                show_fb(conn, arg)
        elif action in ("list", "ls"):
            n = int(arg) if arg.isdigit() else 10
            rows = conn.execute(
                "SELECT fb_id, name, discipline, depth, status "
                "FROM fbs ORDER BY created_at DESC LIMIT ?", (n,)
            ).fetchall()
            print(f"\n  Recent {len(rows)} FBs:\n")
            for r in rows:
                icon = {"PASS": "✅", "FLAG": "⚠️", "QUARANTINE": "🚫"}.get(r["status"], "❓")
                print(f"  {icon} {r['fb_id'][:12]} | {r['name'][:40]:40s} | {r['discipline']:25s} | {r['depth']}")
            print()
        elif action in ("search", "find", "s"):
            if not arg:
                print("  Usage: search <query>")
            else:
                try:
                    rows = conn.execute(
                        "SELECT * FROM fbs WHERE fbs_fts MATCH ? ORDER BY rank LIMIT 10",
                        (arg,),
                    ).fetchall()
                except sqlite3.OperationalError:
                    like = f"%{arg}%"
                    rows = conn.execute(
                        "SELECT * FROM fbs WHERE name LIKE ? OR definition LIKE ? "
                        "ORDER BY borp_score DESC LIMIT 10",
                        (like, like),
                    ).fetchall()
                print(f"\n  Found {len(rows)} results for '{arg}':\n")
                for i, r in enumerate(rows, 1):
                    icon = {"PASS": "✅", "FLAG": "⚠️", "QUARANTINE": "🚫"}.get(r["status"], "❓")
                    print(f"  {icon} {i}. {r['name']}")
                    print(f"     {r['definition'][:150]}...")
                    print(f"     fb_id: {r['fb_id'][:16]}...")
                    print()
        elif action == "stats":
            show_stats(conn)
        elif action == "domains":
            rows = conn.execute(
                "SELECT domains FROM fbs WHERE status = 'PASS'"
            ).fetchall()
            domain_counts = {}
            for r in rows:
                try:
                    domains = json.loads(r["domains"])
                    for d in domains:
                        domain_counts[d] = domain_counts.get(d, 0) + 1
                except json.JSONDecodeError:
                    pass
            print(f"\n  Domains ({len(domain_counts)}):\n")
            for d, c in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"    {d:35s} {c:>5}")
            print()
        elif action == "disciplines":
            rows = conn.execute(
                "SELECT discipline, COUNT(*) as cnt FROM fbs "
                "WHERE status = 'PASS' GROUP BY discipline ORDER BY cnt DESC"
            ).fetchall()
            print(f"\n  Disciplines ({len(rows)}):\n")
            for r in rows:
                print(f"    {r['discipline']:35s} {r['cnt']:>5}")
            print()
        else:
            print(f"  Unknown command: {action}. Type 'help'.")

    conn.close()
    print("  Bye.")


def _print_fb_full(fb: dict):
    """Pretty-print a full FB."""
    print(f"\n{'='*60}")
    print(f"📌 {fb.get('name', 'unnamed')}")
    print(f"{'='*60}")
    print(f"  ID:          {fb.get('fb_id', 'N/A')}")
    print(f"  Discipline:  {fb.get('discipline', 'N/A')}")
    print(f"  Depth:       {fb.get('depth', 'N/A')}")
    print(f"  Evidence:    {fb.get('evidence', 'N/A')}")
    print(f"  Status:      {fb.get('status', 'N/A')}")
    print(f"  BORP Score:  {fb.get('borp_score', 'N/A')}")

    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except json.JSONDecodeError:
            domains = [domains]
    print(f"  Domains:     {', '.join(domains)}")

    print("\n  ── DEFINITION ──")
    print(f"  {fb.get('definition', 'N/A')}")
    print("\n  ── APPLICATION ──")
    print(f"  {fb.get('application', 'N/A')}")
    print("\n  ── FAILURE MODE ──")
    print(f"  {fb.get('failure_mode', 'N/A')}")
    print("\n  ── ELABORATION ──")
    print(f"  {fb.get('elaboration', 'N/A')}")

    if fb.get("keywords"):
        print("\n  ── KEYWORDS ──")
        print(f"  {fb.get('keywords')}")
    if fb.get("jargon"):
        print("\n  ── JARGON ──")
        print(f"  {fb.get('jargon')}")

    print("\n  ── STAMPS ──")
    print(f"  Schema: {fb.get('schema_version')} | "
          f"Model: {fb.get('gen_model')} | "
          f"Commit: {fb.get('pipeline_commit')}")
    print(f"  Created: {fb.get('created_at')} | "
          f"Committed: {fb.get('committed_at')}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="FB CLI browser")
    parser.add_argument("--show", help="Show a specific FB by ID or name")
    parser.add_argument("--stats", action="store_true", help="Show DB statistics")
    parser.add_argument("--export", action="store_true", help="Export all FBs as JSONL")
    args = parser.parse_args()

    conn = get_conn()

    if args.show:
        show_fb(conn, args.show)
    elif args.stats:
        show_stats(conn)
    elif args.export:
        export_all(conn)
    else:
        interactive(conn)


if __name__ == "__main__":
    main()
