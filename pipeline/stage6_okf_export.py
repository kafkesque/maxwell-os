#!/usr/bin/env python3
"""
stage6_okf_export.py — Export verified FBs to Open Knowledge Format (OKF) bundle.
=================================================================================
Authority: D2120 | CONSTITUTION.md §3 (Pipeline Stage 6b — OPTIONAL)

Input:  Verified FBs from Stage 5 checkpoint (or SQLite DB)
Output: .okf/ bundle — one .md per FB, index.md, log.md

Why OKF (D2120):
  - OKF (Google Cloud, Apache 2.0) is an open, agent-readable knowledge format
  - .md files + YAML frontmatter → human-readable, git-diffable, portable
  - Progressive disclosure via index.md → agents load only relevant concepts
  - Interactive graph via `okf server .okf/`
  - CI-gated validation via `okf validate .okf/` + `okf lint .okf/`
  - Does NOT replace Maxwell's canonical format (SQLite/Parquet) — export only

Process:
  1. Load verified FBs from Stage 5 checkpoint (or SQLite)
  2. Write one .md concept file per FB with YAML frontmatter
  3. Generate index.md with domain-driven hierarchy
  4. Generate log.md from FB timestamps
  5. Write .okf/ bundle to stage output directory

Usage:
    python3 pipeline/stage6_okf_export.py
    python3 pipeline/stage6_okf_export.py --source sqlite  # Read from DB instead of checkpoint
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    S5_DIR,
    S6_DIR,
    S6_OKF_EXPORT_ENABLED,
    STAGE5_CHECKPOINT,
)
from pipeline.stamp import get_pipeline_commit

# ── Constants ──────────────────────────────────────────────────────────────
OKF_DIR_NAME: str = ".okf"
MAX_BODY_LEN: int = 5000  # Truncate very long bodies for readability


def _slugify(name: str) -> str:
    """Convert FB name to filesystem-safe slug."""
    slug = name.lower().strip()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = slug.replace(" ", "-").replace("_", "-")
    # Collapse multiple hyphens
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:80]


def _format_frontmatter(fb: dict) -> str:
    """Generate YAML frontmatter from an FB dict."""
    lines = ["---"]
    lines.append(f"type: FoundationBlock")
    lines.append(f"title: {fb.get('name', 'Untitled')}")
    desc = fb.get("definition", "")
    if len(desc) > 160:
        desc = desc[:157] + "..."
    lines.append(f"description: {json.dumps(desc)}")

    # Tags from domains + disciplines
    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except (json.JSONDecodeError, TypeError):
            domains = [domains]
    discipline = fb.get("discipline", "")
    tags = list(domains) if domains else []
    if discipline:
        tags.append(discipline)

    # Add depth and status as tags
    depth = fb.get("depth", "")
    if depth:
        tags.append(depth)
    status = fb.get("status", "")
    if status:
        tags.append(f"status:{status}")

    lines.append(f"tags: {json.dumps(tags)}")
    lines.append(f"timestamp: {fb.get('created_at', '')}")
    lines.append(f"fb_id: {fb.get('fb_id', '')}")

    # Maxwell-specific provenance (extended frontmatter — OKF allows this)
    lines.append(f"schema_version: {fb.get('schema_version', '')}")
    lines.append(f"gen_model: {fb.get('gen_model', '')}")
    lines.append(f"pipeline_commit: {fb.get('pipeline_commit', '')}")
    lines.append(f"status: {status}")
    lines.append(f"evidence: {fb.get('evidence', '')}")

    # Source books (truncated for readability)
    books = fb.get("source_books", [])
    if isinstance(books, str):
        try:
            books = json.loads(books)
        except (json.JSONDecodeError, TypeError):
            books = [books]
    if books:
        # Truncate each book name
        short_books = [b[:80] for b in books[:5]]
        lines.append(f"source_books: {json.dumps(short_books)}")

    # Verification
    vrf = fb.get("verification_results")
    if vrf:
        if isinstance(vrf, str):
            try:
                vrf = json.loads(vrf)
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(vrf, list):
            passed = sum(1 for v in vrf if v.get("passed", False))
            total_v = len(vrf)
            lines.append(f"verification: {passed}/{total_v} checks passed")

    borp = fb.get("borp_score")
    if borp is not None:
        lines.append(f"borp_score: {borp}")

    lines.append("---")
    return "\n".join(lines)


def _format_body(fb: dict) -> str:
    """Generate Markdown body from an FB dict."""
    sections = []

    # Definition
    definition = fb.get("definition", "")
    sections.append(f"# Definition\n\n{definition}\n")

    # Application
    application = fb.get("application", "")
    if application and str(application).lower() != "nan":
        sections.append(f"# Application\n\n{application}\n")

    # Failure Mode
    failure = fb.get("failure_mode", "")
    if failure and str(failure).lower() != "nan":
        sections.append(f"# Failure Mode\n\n{failure}\n")

    # Elaboration
    elaboration = fb.get("elaboration", "")
    if elaboration and str(elaboration).lower() != "nan":
        sections.append(f"# Elaboration\n\n{elaboration}\n")

    # Keywords / Jargon
    keywords = fb.get("keywords", "")
    jargon = fb.get("jargon", "")
    if keywords and str(keywords).lower() != "nan":
        sections.append(f"# Keywords\n\n{keywords}\n")
    if jargon and str(jargon).lower() != "nan":
        sections.append(f"# Jargon\n\n{jargon}\n")

    # Related FBs
    related = fb.get("related_fbs")
    if related:
        if isinstance(related, str):
            try:
                related = json.loads(related)
            except (json.JSONDecodeError, TypeError):
                related = None
        if related and isinstance(related, list) and len(related) > 0:
            sections.append("# Related Foundation Blocks\n")
            for r in related[:10]:
                rid = r.get("fb_id", "") if isinstance(r, dict) else str(r)
                rels = r.get("relationships", []) if isinstance(r, dict) else []
                if isinstance(rels, str):
                    rels = [rels]
                rel_str = ", ".join(str(x) for x in rels) if rels else "related"
                sections.append(f"- [{rel_str}] `{rid[:12]}...`\n")
            sections.append("")

    # Source evidence
    source_text = fb.get("source_text", "")
    if source_text and str(source_text).lower() != "nan":
        truncated = source_text[:MAX_BODY_LEN]
        sections.append(f"# Source Evidence\n\n```\n{truncated}\n```\n")

    return "\n".join(sections)


def _generate_index(fbs_by_domain: dict, fbs: list) -> str:
    """Generate index.md with domain-driven progressive disclosure."""
    lines = [
        "---",
        "type: Index",
        "title: Maxwell OS Foundation Blocks",
        "description: Progressive disclosure map for Maxwell OS knowledge base.",
        f"timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "---",
        "",
        "# Maxwell OS — Foundation Blocks",
        "",
        f"**{len(fbs)} verified Foundation Blocks** extracted from source books.",
        "Each FB is a self-contained principle with definition, application,",
        "failure mode, evidence, and cross-references.",
        "",
        "## Browse by Domain",
        "",
    ]

    for domain, domain_fbs in sorted(fbs_by_domain.items()):
        count = len(domain_fbs)
        slug = domain.lower().replace(" ", "-")
        lines.append(f"### {domain} ({count})")
        for fb in domain_fbs[:20]:  # Limit per domain
            name = fb.get("name", "Untitled")
            fb_id = fb.get("fb_id", "")
            f_slug = _slugify(name)
            lines.append(f"- [{name}](./{f_slug}.md)")
        lines.append("")

    # Add tag cloud
    lines.append("## All Tags")
    all_tags: defaultdict = defaultdict(int)
    for fb in fbs:
        domains = fb.get("domains", [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except (json.JSONDecodeError, TypeError):
                domains = [domains]
        for d in domains:
            all_tags[d] += 1
        disc = fb.get("discipline", "")
        if disc:
            all_tags[disc] += 1
        depth = fb.get("depth", "")
        if depth:
            all_tags[depth] += 1

    lines.append("")
    for tag, count in sorted(all_tags.items(), key=lambda x: -x[1]):
        lines.append(f"- `{tag}` ({count})")

    lines.append("")
    return "\n".join(lines)


def _generate_log(fbs: list) -> str:
    """Generate log.md with chronological FB creation history."""
    lines = [
        "---",
        "type: Log",
        "title: Change History",
        "description: Chronological log of Foundation Block creation and updates.",
        f"timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "---",
        "",
        "# Change Log",
        "",
        f"Generated from {len(fbs)} Foundation Blocks.",
        "",
    ]

    # Sort by created_at
    sorted_fbs = sorted(
        fbs,
        key=lambda fb: fb.get("created_at", ""),
        reverse=True,
    )

    current_date = ""
    for fb in sorted_fbs:
        created = fb.get("created_at", "")[:10]
        if created != current_date:
            current_date = created
            lines.append(f"## {created}")
            lines.append("")

        name = fb.get("name", "Untitled")
        fb_id = fb.get("fb_id", "")
        status = fb.get("status", "")
        f_slug = _slugify(name)
        lines.append(f"- [{name}](./{f_slug}.md) — `{status}` `{fb_id[:12]}`")

    lines.append("")
    return "\n".join(lines)


def export_to_okf(fbs: list, output_dir: Path) -> dict:
    """Export FBs to OKF bundle.

    Args:
        fbs: List of FB dicts from pipeline.
        output_dir: Directory to write .okf/ bundle into.

    Returns:
        Stats dict with counts.
    """
    okf_dir = output_dir / OKF_DIR_NAME
    okf_dir.mkdir(parents=True, exist_ok=True)

    fbs_by_domain: defaultdict = defaultdict(list)
    written = 0
    skipped = 0

    for fb in fbs:
        name = fb.get("name", "")
        if not name:
            skipped += 1
            continue

        slug = _slugify(name)
        if not slug:
            slug = fb.get("fb_id", "unknown")[:20]

        # Group by primary domain
        domains = fb.get("domains", [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except (json.JSONDecodeError, TypeError):
                domains = []
        primary_domain = domains[0] if domains else "uncategorized"
        fbs_by_domain[primary_domain].append(fb)

        # Write concept file
        concept_path = okf_dir / f"{slug}.md"
        frontmatter = _format_frontmatter(fb)
        body = _format_body(fb)

        content = f"{frontmatter}\n\n{body}"
        safe_write(str(concept_path), content)
        written += 1

    # Generate index.md
    index_content = _generate_index(fbs_by_domain, fbs)
    safe_write(str(okf_dir / "index.md"), index_content)

    # Generate log.md
    log_content = _generate_log(fbs)
    safe_write(str(okf_dir / "log.md"), log_content)

    return {
        "fbs_written": written,
        "fbs_skipped": skipped,
        "domains": len(fbs_by_domain),
        "okf_dir": str(okf_dir),
    }


def main() -> None:
    """Main entry point: export FBs to OKF bundle."""
    parser = argparse.ArgumentParser(
        description="Export verified FBs to Open Knowledge Format (OKF) bundle"
    )
    parser.add_argument(
        "--source", choices=["checkpoint", "sqlite"], default="checkpoint",
        help="Source for FBs: checkpoint (Stage 5 jsonl) or sqlite (Stage 6 DB)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for .okf/ bundle (default: stage6_latest)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Stage 6b: OKF Export (D2120)")
    print("=" * 60)

    if not S6_OKF_EXPORT_ENABLED:
        print("  ⏭️  OKF export disabled in config (stage6.okf_export_enabled=false)")
        return

    # Load FBs
    fbs: list = []

    if args.source == "checkpoint":
        ckpt_path = STAGE5_CHECKPOINT
        if not ckpt_path.exists():
            print(f"  ❌ Stage 5 checkpoint not found: {ckpt_path}")
            print(f"  💡 Run Stage 5 first, or use --source sqlite")
            sys.exit(1)

        print(f"  📖 Loading FBs from: {ckpt_path}")
        with open(ckpt_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        fbs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        print(f"     → {len(fbs)} FBs loaded from checkpoint")

    elif args.source == "sqlite":
        import sqlite3
        db_path = S6_DIR / "fbs.db"
        if not db_path.exists():
            print(f"  ❌ SQLite DB not found: {db_path}")
            print(f"  💡 Run Stage 6 first, or use --source checkpoint")
            sys.exit(1)

        print(f"  📖 Loading FBs from: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM fbs WHERE status != 'QUARANTINE'").fetchall()
        fbs = [dict(row) for row in rows]
        conn.close()
        print(f"     → {len(fbs)} verified FBs loaded from SQLite")

    if not fbs:
        print("  ⚠️  No FBs to export")
        return

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Use stage6 output dir as default
        output_dir = S6_DIR / "okf_export"
        output_dir.mkdir(parents=True, exist_ok=True)

    # Export
    print(f"\n  📝 Exporting {len(fbs)} FBs to OKF bundle...")
    start = time.time()
    stats = export_to_okf(fbs, output_dir)
    elapsed = time.time() - start

    print(f"\n  ✅ OKF export complete in {elapsed:.1f}s")
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │ FBs written:  {stats['fbs_written']:>4}                          │")
    print(f"  │ FBs skipped:  {stats['fbs_skipped']:>4}                          │")
    print(f"  │ Domains:      {stats['domains']:>4}                          │")
    print(f"  │ Bundle:       {stats['okf_dir']}")
    print(f"  └─────────────────────────────────────────────┘")
    print(f"\n  Next steps:")
    print(f"    okf validate {stats['okf_dir']}    # Validate OKF conformance")
    print(f"    okf lint {stats['okf_dir']}        # Check curation quality")
    print(f"    okf server {stats['okf_dir']}      # Browse interactive graph")


if __name__ == "__main__":
    main()
