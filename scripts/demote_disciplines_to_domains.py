#!/usr/bin/env python3
"""
scripts/demote_disciplines_to_domains.py — Drift C (D2512) migration.
======================================================================
Moves 9 applied-practice labels from DISCIPLINE canonicals → DOMAIN canonicals
(ontological audit verdict, D2512 BUG-209):

  DEMOTE (discipline → domain):
    marketing            → MERGE into existing domain 'marketing & communications'
    product design       → new domain
    design strategy      → new domain
    project management   → new domain
    leadership           → new domain
    personal productivity→ new domain
    industrial design    → new domain
    information architecture → new domain
    design systems       → new domain

  KEEP as discipline (user call):
    typography, creative process, design thinking

Deterministic + crash-safe (C6): every file edited is backed up first
(.bak_<ts>), then written via tempfile→fsync→replace. Idempotent: re-running
detects already-demoted labels and reports 0 changes.

Edits:
  1. config/taxonomy_v5.yaml   — remove 9 discipline entries; add 8 new domain
                                  entries (marketing merges into the existing
                                  'marketing & communications' domain = union of
                                  raw aliases); bump version v5.1 → v6.0.
  2. config/alias_map.yaml     — remove 14 discipline-alias entries whose target
                                  was a demoted discipline (their target no
                                  longer exists as a discipline).
  3. config/pipeline_config.yaml — max_domains 35→43, max_disciplines 75→66,
                                  taxonomy_version v5.1→v6.0 (3 places).

Usage:
    python3 scripts/demote_disciplines_to_domains.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TAX_PATH = ROOT / "config" / "taxonomy_v5.yaml"
ALIAS_PATH = ROOT / "config" / "alias_map.yaml"
CFG_PATH = ROOT / "config" / "pipeline_config.yaml"

DEMOTE = [
    "marketing",
    "product design",
    "design strategy",
    "project management",
    "leadership",
    "personal productivity",
    "industrial design",
    "information architecture",
    "design systems",
]
# marketing merges into the EXISTING domain; the rest become new domains.
MERGE_INTO_EXISTING = {"marketing": "marketing & communications"}

NEW_DOMAIN_GROUPS = {
    "product design": "Digital & Interactive",
    "design strategy": "Business & Strategy",
    "project management": "Business & Strategy",
    "leadership": "Business & Strategy",
    "personal productivity": "Business & Strategy",
    "industrial design": "Illustration & Craft",
    "information architecture": "Digital & Interactive",
    "design systems": "Digital & Interactive",
}

KEEP_AS_DISCIPLINE = {"typography", "creative process", "design thinking"}


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_write(path: Path, text: str, dry_run: bool) -> None:
    """Crash-safe write: backup → tempfile → fsync → replace (C6)."""
    if dry_run:
        print(f"  [dry-run] would write {path.name}")
        return
    backup = path.with_suffix(path.suffix + f".bak_{_ts()}")
    import shutil
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with open(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        import os
        os.fsync(f.fileno())
    os.replace(tmp, path)
    print(f"  ✅ wrote {path.name} (backup {backup.name})")


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def migrate_taxonomy(tax: dict) -> tuple[dict, int]:
    """Move demoted disciplines → domains in the taxonomy dict. Returns (tax, changes)."""
    disciplines = tax.get("disciplines", [])
    domains = tax.get("domains", [])
    demoted_entries: dict[str, dict] = {}
    changes = 0

    # 1. Pull demoted entries out of disciplines.
    kept_disciplines = []
    for entry in disciplines:
        name = entry.get("canonical")
        if name in DEMOTE:
            demoted_entries[name] = entry
            changes += 1
        else:
            kept_disciplines.append(entry)
    tax["disciplines"] = kept_disciplines

    # 2. For each demoted label: merge into existing domain, or add new domain.
    for name in DEMOTE:
        entry = demoted_entries.get(name)
        if entry is None:
            print(f"  ⚠️  demote target {name!r} not found in disciplines — skipping")
            continue
        target_domain = MERGE_INTO_EXISTING.get(name)
        if target_domain:
            # Merge raw aliases into the existing domain entry.
            merged = False
            for d in domains:
                if d.get("canonical") == target_domain:
                    existing_raw = {r.lower() for r in d.get("raw", [])}
                    for r in entry.get("raw", []):
                        if r.lower() not in existing_raw:
                            d.setdefault("raw", []).append(r)
                    merged = True
                    changes += 1
                    break
            if not merged:
                raise RuntimeError(
                    f"merge target domain {target_domain!r} not found — cannot merge {name!r}"
                )
        else:
            # New domain entry: keep canonical + raw aliases; assign a group.
            new_domain = {
                "canonical": name,
                "group": NEW_DOMAIN_GROUPS.get(name, "Business & Strategy"),
                "raw": entry.get("raw", []),
            }
            domains.append(new_domain)
            changes += 1

    tax["domains"] = domains

    # 3. Bump version (MINOR only: v5.1 → v5.2 — the file stays taxonomy_v5.yaml;
    #    _get_taxonomy_path()/schemas.py/doc_guard.py hardcode that filename).
    old_version = tax.get("version", "v5.1")
    tax["version"] = "v5.2"
    changes += 1
    print(f"  taxonomy version: {old_version} → v5.2")
    return tax, changes


def migrate_alias_map(alias: dict) -> tuple[dict, int]:
    """Remove discipline-alias entries whose target was demoted. Returns (alias, changes)."""
    aliases = alias.get("discipline_aliases", {})
    removed = []
    for key, target in list(aliases.items()):
        if target in DEMOTE:
            removed.append(key)
            del aliases[key]
    alias["discipline_aliases"] = aliases
    if removed:
        print(f"  removed {len(removed)} alias_map entries targeting demoted disciplines: {removed}")
    return alias, len(removed)


def migrate_config(cfg: dict) -> tuple[dict, int]:
    """Update max_domains/max_disciplines caps + taxonomy_version (3 places)."""
    changes = 0

    # taxonomy.max_domains / max_disciplines
    tx = cfg.setdefault("taxonomy", {})
    old_dom = tx.get("max_domains")
    old_disc = tx.get("max_disciplines")
    if old_dom is not None:
        tx["max_domains"] = 43
        changes += 1
    if old_disc is not None:
        tx["max_disciplines"] = 66
        changes += 1
    cfg["taxonomy"] = tx

    # taxonomy_version in 3 places: pipeline_manifest, pipeline, test.full_run
    for loc in ("pipeline_manifest",):
        if loc in cfg and "taxonomy_version" in cfg[loc]:
            cfg[loc]["taxonomy_version"] = "v5.2"
            changes += 1
    if "pipeline" in cfg and "taxonomy_version" in cfg["pipeline"]:
        cfg["pipeline"]["taxonomy_version"] = "v5.2"
        changes += 1
    if "test" in cfg and "full_run" in cfg["test"] and "taxonomy_version" in cfg["test"]["full_run"]:
        cfg["test"]["full_run"]["taxonomy_version"] = "v5.2"
        changes += 1

    print(f"  max_domains {old_dom}→43, max_disciplines {old_disc}→66, taxonomy_version→v5.2")
    return cfg, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Drift C: demote 9 disciplines → domains (D2512)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total = 0

    # 1. taxonomy_v5.yaml
    with open(TAX_PATH) as f:
        tax = yaml.safe_load(f)
    tax, n = migrate_taxonomy(tax)
    total += n
    _safe_write(TAX_PATH, _dump(tax), args.dry_run)

    # 2. alias_map.yaml
    with open(ALIAS_PATH) as f:
        alias = yaml.safe_load(f)
    alias, n = migrate_alias_map(alias)
    total += n
    _safe_write(ALIAS_PATH, _dump(alias), args.dry_run)

    # 3. pipeline_config.yaml
    with open(CFG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg, n = migrate_config(cfg)
    total += n
    _safe_write(CFG_PATH, _dump(cfg), args.dry_run)

    print(f"\n  Drift C migration: {total} change(s) {'(dry-run)' if args.dry_run else 'APPLIED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
