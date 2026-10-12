#!/usr/bin/env python3
"""scripts/fix_bug310_domains.py — apply the 37 BUG-310 domain cross-listing rulings.

User approved all 37 "keep X / drop Y" rulings (governance/bug310_domain_crosslistings.md).
This script removes each cross-listed raw alias from its "drop" domain (case-insensitive
match within that domain's `raw:` section only — never `exclude:`), leaving each string
under exactly one domain. Surgical + section-aware, crash-safe write (C6) + backup (C13).
"""
from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TAX = _ROOT / "config" / "taxonomy.yaml"

# lowercased raw string -> domain to DROP it from (keep it in the other domain).
DROP: dict[str, str] = {
    "creative technology": "code & computation",
    "design system": "digital product",
    "advertising": "marketing & communications",
    "art education": "arts & culture",
    "brand strategy": "marketing & communications",
    "control systems engineering": "engineering & infrastructure",
    "design operations": "digital product",
    "design research": "digital product",
    "design research investigation": "digital product",
    "e-commerce": "finance & investment",
    "front-end": "creative technology",
    "human resources": "leadership",
    "information design": "data visualization",
    "interaction design": "digital product",
    "market research": "research & methodology",
    "marketing strategy": "business development",
    "network engineering": "engineering & infrastructure",
    "operations management": "project management",
    "organizational design": "leadership",
    "organizational leadership": "organizational behavior",
    "personal development": "business operations",
    "phenomenology": "semiotics & communication",
    "product development": "project management",
    "product management": "project management",
    "product strategy": "business operations",
    "programming": "engineering practice",
    "sales": "marketing & communications",
    "sales communication": "marketing & communications",
    "sales psychology": "marketing & communications",
    "service design": "digital product",
    "software development": "engineering practice",
    "team dynamics": "leadership",
    "ui design": "digital product",
    "ui/ux": "digital product",
    "ux design": "digital product",
    "web design": "digital product",
    "web navigation": "web & ui",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    lines = open(_TAX, encoding="utf-8").readlines()
    # group drop targets by domain (lowercased key -> set of lowercased raw strings)
    drop_by_domain: dict[str, set[str]] = {}
    for raw, dom in DROP.items():
        drop_by_domain.setdefault(dom, set()).add(raw)

    out: list[str] = []
    log: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("- canonical: "):
            canon = line[len("- canonical: "):].strip()
            start = i
            i += 1
            while i < len(lines) and not lines[i].startswith("- canonical: "):
                i += 1
            block = lines[start:i]
            drops = drop_by_domain.get(canon, set())
            new_block: list[str] = []
            in_raw = False
            for bl in block:
                s = bl.strip()
                if s == "raw:":
                    in_raw = True
                    new_block.append(bl)
                    continue
                if in_raw and s.startswith(("group:", "definition:", "exclude:", "disposition:")):
                    in_raw = False
                if in_raw and s.startswith("- ") and s[2:].strip().lower() in drops:
                    log.append(f"  - {canon!r}: removed {s[2:].strip()!r}")
                    continue
                new_block.append(bl)
            out.extend(new_block)
        else:
            out.append(line)
            i += 1

    print(f"planned changes ({len(log)} removals):")
    for l in log:
        print(l)
    if not args.apply:
        print("\n(dry-run — re-run with --apply)")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = _TAX.with_name(f"taxonomy.yaml.bak_{ts}_pre_bug310")
    os.replace(_TAX, bak)
    fd, tmp = tempfile.mkstemp(dir=str(_TAX.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("".join(out))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _TAX)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f"   ✅ wrote {_TAX.name} (backup: {bak.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
