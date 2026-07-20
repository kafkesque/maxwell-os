#!/usr/bin/env python3
"""
validate_book_structure.py — Pre-S1 Structure Validation Gate.
================================================================
Run BEFORE S1 chunking to verify the book library is clean.
Checks:
  1. No nested directories (every book at exactly DOMAIN/cross_domain/book.md)
  2. No empty cross_domain folders
  3. No dual-naming (all folders match domain_anchors.yaml names)
  4. All cross_domain folder names exist in domain_anchors.yaml
  5. No books at root level (unclassified)

All paths from config/pipeline.yaml via pipeline_paths.py.

Usage:
  python3 tools/validate_book_structure.py              # Check all
  python3 tools/validate_book_structure.py --fix-empty  # Remove empty dirs
  python3 tools/validate_book_structure.py --json       # Machine-readable output
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from pipeline_paths import EDUCATION_MD_BOOKS, EDUCATION_EPUB_BOOKS, EDUCATION_PDF_BOOKS, STAGE_PATHS, CONFIG_DIR

PIPELINE_SOURCES = STAGE_PATHS.get("sources", ROOT / "knowledge pipeline" / "input" / "1.sources")


def _canon_to_disk(name: str) -> str:
    """Convert canonical name (with spaces) to disk-safe folder name (with +)."""
    return name.replace(" + ", "+").replace(" ", "+")


def load_domain_anchors(include_subfolders: bool = False):
    """Parse domain_anchors.yaml → set of valid cross_domain folder names.

    Default: canonical cross_domain names only (as disk-safe +-separated paths).
    With include_subfolders=True: also accepts legacy subfolder names.
    """
    anchors_file = CONFIG_DIR / "domain_anchors.yaml"
    if not anchors_file.exists():
        print(f"⚠️  domain_anchors.yaml not found at {anchors_file}")
        return set(), {}, {}

    with open(anchors_file) as f:
        data = yaml.safe_load(f)

    valid_cross_domains = set()
    domain_to_cross_domains = {}
    cross_domain_to_domain = {}

    for anchor in data.get("anchors", []):
        domain_name = anchor["name"]
        cross_domains_list = []
        for cd in anchor.get("cross_domains", []):
            cd_name = cd["name"]
            disk_name = _canon_to_disk(cd_name)
            valid_cross_domains.add(disk_name)
            cross_domains_list.append(disk_name)
            cross_domain_to_domain[disk_name] = domain_name
        domain_to_cross_domains[domain_name] = cross_domains_list

        if include_subfolders:
            for sf in anchor.get("subfolders", []):
                sf_name = sf["name"]
                valid_cross_domains.add(sf_name)
                # Also accept disk-safe variants (underscores, plus signs)
                valid_cross_domains.add(sf_name.replace(" + ", "+").replace(" ", "_"))
                valid_cross_domains.add(sf_name.replace(" + ", "+").replace(" ", "+"))
                cross_domain_to_domain[sf_name] = domain_name

    return valid_cross_domains, domain_to_cross_domains, cross_domain_to_domain


def validate_root(root_path: Path, valid_cds: set, cd_to_domain: dict):
    """Validate one root directory. Returns dict of findings."""
    findings = {
        "root": str(root_path),
        "nested": [],       # books deeper than 2 levels
        "empty_dirs": [],   # empty cross_domain folders
        "unknown_names": [],  # folder names not in domain_anchors
        "root_books": [],    # books at domain root (not in a subfolder)
        "dual_naming": [],   # legacy folder names that should be canonical
        "total_books": 0,
        "total_dirs": 0,
        "pass": True,
    }

    if not root_path.exists():
        findings["pass"] = False
        findings["errors"] = [f"Root not found: {root_path}"]
        return findings

    # Walk the tree using os.walk for cross-version compat
    import os as _os
    for dirpath_str, dirnames, filenames in _os.walk(root_path):
        dp = Path(dirpath_str)
        rel = dp.relative_to(root_path)
        rel_parts = rel.parts if str(rel) != "." else ()
        depth = len(rel_parts)

        # Skip root itself
        if depth == 0:
            findings["total_dirs"] += len(dirnames)
            # Root dirs should be domain folders
            for dn in dirnames:
                if dn == "inbox":
                    continue  # inbox is fine at root
                if not dn.startswith("DOMAIN"):
                    findings["unknown_names"].append(str(dp / dn))
            continue

        # Level 1: domain folder
        if depth == 1:
            domain_name = rel_parts[0]
            findings["total_dirs"] += len(dirnames)
            # Files at domain level = unclassified
            for fn in filenames:
                if fn.endswith(".md"):
                    findings["root_books"].append(str(dp / fn))
                    findings["total_books"] += 1
            # Check subfolder names
            for dn in dirnames:
                if dn not in valid_cds:
                    findings["unknown_names"].append(str(dp / dn))
            continue

        # Level 2: cross_domain folder — should contain books, not dirs
        if depth == 2:
            findings["total_dirs"] += len(dirnames)
            findings["total_books"] += len([f for f in filenames if f.endswith(".md")])

            # Deep nesting detected
            if dirnames:
                for dn in dirnames:
                    findings["nested"].append(str(dp / dn))

            # Empty dir detection
            if not filenames and not dirnames:
                findings["empty_dirs"].append(str(dp))

            continue

        # Level 3+: shouldn't exist
        if depth >= 3:
            findings["nested"].append(str(dp))
            findings["total_books"] += len([f for f in filenames if f.endswith(".md")])

    # Determine pass/fail
    if findings["unknown_names"]:
        findings["pass"] = False
    if findings["root_books"]:
        findings["pass"] = False
    if findings["nested"]:
        findings["pass"] = False
    # empty_dirs is a warning, not a failure

    return findings


def print_findings(findings, json_out=False):
    """Print findings in human-readable or JSON format."""
    if json_out:
        print(json.dumps(findings, indent=2))
        return findings["pass"]

    status = "✅ PASS" if findings["pass"] else "❌ FAIL"
    print(f"\n{'='*70}")
    print(f" {status} — {findings['root']}")
    print(f"{'='*70}")
    print(f"  Books: {findings['total_books']}  |  Dirs: {findings['total_dirs']}")

    if findings["nested"]:
        print(f"\n  ❌ NESTED DIRECTORIES ({len(findings['nested'])}):")
        for n in findings["nested"][:10]:
            print(f"     {n}")
        if len(findings["nested"]) > 10:
            print(f"     ... and {len(findings['nested']) - 10} more")

    if findings["empty_dirs"]:
        print(f"\n  ⚠️  EMPTY DIRECTORIES ({len(findings['empty_dirs'])}):")
        for e in findings["empty_dirs"][:10]:
            print(f"     {e}")
        if len(findings["empty_dirs"]) > 10:
            print(f"     ... and {len(findings['empty_dirs']) - 10} more")

    if findings["unknown_names"]:
        print(f"\n  ❌ UNKNOWN FOLDER NAMES ({len(findings['unknown_names'])}):")
        for u in findings["unknown_names"][:10]:
            print(f"     {u}")
        if len(findings["unknown_names"]) > 10:
            print(f"     ... and {len(findings['unknown_names']) - 10} more")

    if findings["root_books"]:
        print(f"\n  ❌ UNCLASSIFIED BOOKS AT DOMAIN ROOT ({len(findings['root_books'])}):")
        for r in findings["root_books"][:10]:
            print(f"     {r}")
        if len(findings["root_books"]) > 10:
            print(f"     ... and {len(findings['root_books']) - 10} more")

    if not findings["nested"] and not findings["unknown_names"] and not findings["root_books"]:
        print(f"\n  ✅ Structure is clean.")

    return findings["pass"]


def fix_empty_dirs(root_path: Path):
    """Remove empty directories (safe — only removes truly empty dirs)."""
    import os
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        if dirpath == str(root_path):
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed += 1
        except OSError:
            pass
    return removed


def main():
    parser = argparse.ArgumentParser(description="Pre-S1 book structure validation")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--fix-empty", action="store_true", help="Remove empty directories")
    parser.add_argument("--legacy-ok", action="store_true",
                        help="Also accept legacy subfolder names (pre-restructure check)")
    parser.add_argument("--roots", nargs="*", choices=["md", "epub", "pdf", "pipeline"],
                        default=["md", "epub", "pdf", "pipeline"],
                        help="Roots to check (default: all four)")
    args = parser.parse_args()

    valid_cds, domain_to_cds, cd_to_domain = load_domain_anchors(
        include_subfolders=args.legacy_ok
    )
    print(f"Loaded {len(valid_cds)} valid folder names from domain_anchors.yaml"
          f"{' (including legacy subfolders)' if args.legacy_ok else ' (canonical cross-domains only)'}")

    roots = []
    if "md" in args.roots:
        roots.append(("Education MD", EDUCATION_MD_BOOKS))
    if "epub" in args.roots:
        roots.append(("Education EPUB", EDUCATION_EPUB_BOOKS))
    if "pdf" in args.roots:
        roots.append(("Education PDF", EDUCATION_PDF_BOOKS))
    if "pipeline" in args.roots:
        roots.append(("Pipeline 1.sources", PIPELINE_SOURCES))

    all_pass = True
    for name, root_path in roots:
        findings = validate_root(root_path, valid_cds, cd_to_domain)
        passed = print_findings(findings, json_out=args.json)
        all_pass = all_pass and passed

        if args.fix_empty and findings["empty_dirs"]:
            removed = fix_empty_dirs(root_path)
            print(f"\n  🧹 Removed {removed} empty directories")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
