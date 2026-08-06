#!/usr/bin/env python3
"""
stage6c_obsidian_export.py — Export verified FBs to an Obsidian vault.
========================================================================
Authority: D2136 | CONSTITUTION.md §3 (Stage 6c — Obsidian Knowledge Graph)

Input:  Verified FBs from Stage 5 checkpoint (or Stage 6 SQLite)
Output: Obsidian vault with domain subfolders + [[wikilinks]] + Dataview-ready YAML

Vault structure:
  stage6_commit/{run_id}/obsidian_vault/
    {raw_domain}/
      {fb_slug}.md              ← FB with YAML frontmatter + [[wikilinks]]
    _meta/
      domain_index.md            ← Dataview-queryable index
      source_books/              ← Source book pages with backlinks
    .obsidian/                   ← Obsidian config (optional)

Wikilinks generated:
  - [[discipline_name]] → links to discipline hub pages
  - [[source_book_name]] → links to source book pages
  - [[domain_name]] → links to domain hub pages

Usage:
    python3 pipeline/stage6c_obsidian_export.py
    python3 pipeline/stage6c_obsidian_export.py --all-statuses  # Include non-PASS FBs
    python3 pipeline/stage6c_obsidian_export.py --no-wikilinks   # Plain MD, no wikilinks
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
    S6_DIR,
    STAGE5_CHECKPOINT,
    get_run_id,
)
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Helpers ────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    slug = name.lower().strip()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = slug.replace(" ", "_").replace("-", "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")[:80]


def _raw_domain(canonical: str) -> str:
    """Convert canonical domain to filesystem-safe label."""
    raw = canonical.lower().strip()
    for ch in [" & ", "&", " + ", "+", " — ", "—", " / ", "/"]:
        raw = raw.replace(ch, "_")
    raw = raw.replace(" ", "_")
    raw = "".join(c for c in raw if c.isalnum() or c == "_")
    while "__" in raw:
        raw = raw.replace("__", "_")
    return raw.strip("_")


def _wikilink(text: str) -> str:
    """Create an Obsidian wikilink from text, stripping special chars."""
    clean = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    clean = clean.replace(" ", "_").replace("-", "_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return f"[[{clean.strip('_')}]]"


# ── Formatters ─────────────────────────────────────────────────────────────


def _format_frontmatter(fb: dict) -> str:
    """Generate YAML frontmatter for an FB."""
    name = fb.get("name", "Untitled")
    fb_id = fb.get("fb_id", "")
    discipline = fb.get("discipline", "")
    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except (json.JSONDecodeError, TypeError):
            domains = [domains]
    depth = fb.get("depth", "")
    evidence = fb.get("evidence", "")
    accessibility = fb.get("accessibility", "self-evident")
    source_books = fb.get("source_books", [])
    if isinstance(source_books, str):
        source_books = [source_books]
    status = fb.get("status", "")
    schema_version = fb.get("schema_version", "")
    gen_model = fb.get("gen_model", "")

    lines = ["---"]
    lines.append(f"fb_id: \"{fb_id}\"")
    lines.append("type: foundation_block")
    lines.append(f"status: {status}")
    lines.append(f"discipline: {discipline}")
    lines.append(f"domains: {json.dumps(domains)}")
    lines.append(f"depth: {depth}")
    lines.append(f"evidence: {evidence}")
    lines.append(f"accessibility: {accessibility}")
    lines.append(f"source_books: {json.dumps(source_books)}")
    lines.append(f"schema_version: {schema_version}")
    lines.append(f"gen_model: {gen_model}")
    lines.append(f"date: {fb.get('created_at', '')[:10]}")
    lines.append("---")
    return "\n".join(lines)


def _format_body(fb: dict, use_wikilinks: bool = True) -> str:
    """Format FB body with optional [[wikilinks]]."""
    name = fb.get("name", "Untitled")
    definition = fb.get("definition", "")
    application = fb.get("application", "")
    failure_mode = fb.get("failure_mode", "")
    elaboration = fb.get("elaboration", "")
    discipline = fb.get("discipline", "")
    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except (json.JSONDecodeError, TypeError):
            domains = [domains]
    source_books = fb.get("source_books", [])
    if isinstance(source_books, str):
        source_books = [source_books]
    evidence = fb.get("evidence", "")

    lines = []
    lines.append(f"# {name}")
    lines.append("")

    # Tags row with wikilinks
    if use_wikilinks:
        tags: list[str] = []
        tags.append(_wikilink(f"discipline/{discipline}"))
        for d in domains:
            tags.append(_wikilink(f"domain/{d}"))
        tags.append(_wikilink(f"depth/{fb.get('depth', '')}"))
        lines.append(f"> **Tags:** {' · '.join(tags)}")
        lines.append("")

    lines.append("## Definition")
    lines.append("")
    lines.append(definition)
    lines.append("")

    if application:
        lines.append("## Application")
        lines.append("")
        lines.append(application)
        lines.append("")

    if failure_mode:
        lines.append("## Failure Mode")
        lines.append("")
        lines.append(failure_mode)
        lines.append("")

    if elaboration:
        lines.append("## Elaboration")
        lines.append("")
        lines.append(elaboration)
        lines.append("")

    # Source books as wikilinks
    if source_books and use_wikilinks:
        lines.append("## Source Books")
        lines.append("")
        for book in source_books:
            book_name = Path(book).stem
            lines.append(f"- {_wikilink(f'source/{book_name}')}")
        lines.append("")

    # Evidence note
    if evidence:
        lines.append(f"> **Evidence:** {evidence}")
        lines.append("")

    return "\n".join(lines)


# ── Index generators ───────────────────────────────────────────────────────


def _generate_domain_index(by_domain: dict[str, list[dict]]) -> str:
    """Generate a Dataview-queryable domain index page."""
    lines = [
        "---",
        "type: index",
        "tags: [domain_index]",
        "---",
        "",
        "# Foundation Block Domain Index",
        "",
        f"*Generated: {time.strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Domains",
        "",
    ]
    for domain, fbs in sorted(by_domain.items()):
        count = len(fbs)
        lines.append(f"### {domain.replace('_', ' ').title()} ({count})")
        lines.append("")
        for fb in fbs[:50]:  # Limit per domain for readability
            name = fb.get("name", "Untitled")
            slug = _slugify(name)
            depth = fb.get("depth", "")
            lines.append(f"- {_wikilink(f'{domain}/{slug}')}  *(depth: {depth})*")
        if len(fbs) > 50:
            lines.append(f"- *... and {len(fbs) - 50} more*")
        lines.append("")

    lines.append("## Dataview Query (paste into any page)")
    lines.append("```dataview")
    lines.append("TABLE discipline, domains, depth, evidence, source_books")
    lines.append("FROM #foundation_block")
    lines.append("SORT depth ASC, file.name ASC")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _generate_source_book_page(book_name: str, fbs: list[dict]) -> str:
    """Generate a source book hub page with backlinks."""
    lines = [
        "---",
        "type: source_book",
        f"title: \"{book_name}\"",
        f"fb_count: {len(fbs)}",
        "---",
        "",
        f"# {book_name}",
        "",
        f"*Source book — {len(fbs)} foundation blocks extracted*",
        "",
        "## Foundation Blocks",
        "",
    ]
    for fb in fbs:
        name = fb.get("name", "Untitled")
        domains = fb.get("domains", [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except (json.JSONDecodeError, TypeError):
                domains = []
        primary_domain = _raw_domain(domains[0]) if domains else "uncategorized"
        slug = _slugify(name)
        lines.append(f"- {_wikilink(f'{primary_domain}/{slug}')}")

    lines.append("")
    lines.append("## Dataview Query")
    lines.append("```dataview")
    lines.append("TABLE domains, depth, evidence")
    lines.append(f"WHERE contains(source_books, \"{book_name}\")")
    lines.append("SORT file.name ASC")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────


def write_obsidian_vault(
    fbs: list[dict],
    output_dir: Path,
    *,
    use_wikilinks: bool = True,
) -> dict:
    """Write FBs organized by domain into an Obsidian vault structure.

    Returns stats dict.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group by primary domain
    by_domain: dict[str, list[dict]] = defaultdict(list)
    by_source_book: dict[str, list[dict]] = defaultdict(list)

    for fb in fbs:
        domains = fb.get("domains", [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except (json.JSONDecodeError, TypeError):
                domains = []

        # Primary domain folder
        primary = domains[0] if domains else "uncategorized"
        raw = _raw_domain(primary)
        by_domain[raw].append(fb)

        # Cross-domain: also add to cross_domain folder
        if len(domains) >= 3:
            by_domain["cross_domain"].append(fb)

        # Source book grouping
        source_books = fb.get("source_books", [])
        if isinstance(source_books, str):
            source_books = [source_books]
        for book in source_books:
            by_source_book[Path(book).stem].append(fb)

    stats: dict = {"domains": 0, "fbs": 0, "source_books": 0}

    # Write domain folders
    for raw_domain, domain_fbs in sorted(by_domain.items()):
        domain_dir = output_dir / raw_domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        for fb in domain_fbs:
            name = fb.get("name", "Untitled")
            slug = _slugify(name)
            md_path = domain_dir / f"{slug}.md"

            frontmatter = _format_frontmatter(fb)
            body = _format_body(fb, use_wikilinks=use_wikilinks)
            safe_write(str(md_path), frontmatter + "\n\n" + body + "\n")
            stats["fbs"] += 1

        stats["domains"] += 1

    # Write source book hub pages
    source_dir = output_dir / "_meta" / "source_books"
    source_dir.mkdir(parents=True, exist_ok=True)
    for book_name, book_fbs in sorted(by_source_book.items()):
        page = _generate_source_book_page(book_name, book_fbs)
        safe_write(str(source_dir / f"{_slugify(book_name)}.md"), page)
        stats["source_books"] += 1

    # Write domain index
    index = _generate_domain_index(by_domain)
    safe_write(str(output_dir / "_meta" / "domain_index.md"), index)

    # Write export stats
    export_stats = {
        "fbs_exported": stats["fbs"],
        "domains": stats["domains"],
        "source_books": stats["source_books"],
        "pipeline_commit": get_pipeline_commit(),
        "run_id": get_run_id(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    stamp_record(export_stats)
    safe_write(
        str(output_dir / ".obsidian_export.json"),
        json.dumps(export_stats, indent=2, ensure_ascii=False) + "\n",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 6c: Export FBs to Obsidian vault with [[wikilinks]]"
    )
    parser.add_argument("--all-statuses", action="store_true",
                        help="Include non-PASS FBs (FLAG, QUARANTINE)")
    parser.add_argument("--no-wikilinks", action="store_true",
                        help="Skip [[wikilinks]] (plain markdown)")
    args = parser.parse_args()

    # Load FBs
    if not STAGE5_CHECKPOINT.exists():
        print("❌ Stage 5 checkpoint not found. Run stage5_verify.py first.")
        sys.exit(1)

    fbs: list[dict] = []
    with open(STAGE5_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                fbs.append(json.loads(line))

    print(f"📦 Loaded {len(fbs)} verified FBs")

    # Filter
    if not args.all_statuses:
        pass_fbs = [fb for fb in fbs if fb.get("status") == "PASS"]
        skipped = len(fbs) - len(pass_fbs)
        if skipped:
            print(f"   PASS: {len(pass_fbs)} | Skipped (non-PASS): {skipped}")
            print("   Use --all-statuses to include all")
        fbs = pass_fbs

    if not fbs:
        print("❌ No FBs to export.")
        sys.exit(1)

    # Write vault
    output_dir = S6_DIR / get_run_id() / "obsidian_vault"
    stats = write_obsidian_vault(
        fbs, output_dir,
        use_wikilinks=not args.no_wikilinks,
    )

    print(f"\n{'='*60}")
    print("📊 STAGE 6c — OBSIDIAN EXPORT")
    print(f"   FBs exported:   {stats['fbs']}")
    print(f"   Domains:        {stats['domains']}")
    print(f"   Source books:   {stats['source_books']}")
    print(f"   Wikilinks:      {'enabled' if not args.no_wikilinks else 'disabled'}")
    print(f"   Vault:          {output_dir}")
    print(f"\n💡 Open in Obsidian: File → Open Vault → {output_dir}")
    print(f"   Or: cp -r {output_dir}/* ~/your-vault/")
    print(f"   Dataview query: open {output_dir}/_meta/domain_index.md")


if __name__ == "__main__":
    main()
