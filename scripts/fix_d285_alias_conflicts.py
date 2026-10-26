#!/usr/bin/env python3
"""scripts/fix_d285_alias_conflicts.py — surgical D-285 alias + definition fix.

Forensic audit (2026-09-20) found the D-285 discipline boundaries were NOT fully
swept into taxonomy.yaml. Two coupled problems:

  1. RAW-ALIAS CROSS-LISTINGS — a raw alias must map to AT MOST ONE canonical
     (pipeline/schemas.py's synonym index is last-write-wins, so cross-listings
     are an ordering-dependent drift hazard). D-285 mutual-exclusivity fixes:
       cognitive ergonomics  -> cognitive science  (remove from design psychology)
       cognitive psychology  -> cognitive science  (remove from psychology)
       behavioral psychology -> psychology         (remove from behavioral economics)
       persuasion            -> design psychology  (move from behavioral economics)
       creative psychology   -> psychology         (remove from cognitive science + creative process)
       psychology of creativity -> psychology      (remove from creative process)
       problem solving       -> cognitive science  (remove from decision making)
     Canonical-name self-collision + exclude-contradiction:
       color theory          -> color theory       (remove from visual perception)
       economics             -> economics          (remove from political economy)
       clinical psychology   -> psychology         (remove from health & medicine)

  2. DEFINITION DRIFT — taxonomy.yaml's 5-core discipline definitions are the
     UN-strengthened base text; r5_slot_repair.yaml holds the ratified D-285
     strengthened text (extra discriminator sentences). Fold the strengthened
     text into the canonical definitions so the two sources agree.

SURGICAL: operates on raw text lines (preserves original single-line formatting),
never a yaml.safe_dump round-trip (which re-wraps the whole file). Crash-safe
write (C6) after a timestamped backup (C13). --apply commits; default is dry-run.
"""
from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TAX = _ROOT / "config" / "taxonomy.yaml"

# (canonical, exact-raw-line) to REMOVE.
REMOVE: list[tuple[str, str]] = [
    ("design psychology", "cognitive ergonomics"),
    ("design psychology", "Cognitive Ergonomics"),
    ("psychology", "Cognitive Psychology"),
    ("psychology", "cognitive psychology"),
    ("behavioral economics", "behavioral psychology"),
    ("behavioral economics", "Persuasion"),
    ("behavioral economics", "persuasion"),
    ("cognitive science", "Creative Psychology"),
    ("cognitive science", "creative psychology"),
    ("creative process", "Creative Psychology"),
    ("creative process", "Psychology of Creativity"),
    ("decision making", "Problem Solving"),
    ("visual perception", "Color Theory"),
    ("visual perception", "color theory"),
    ("political economy", "economics"),
    ("political economy", "Economics"),
    ("health & medicine", "clinical psychology"),
]

# (canonical, exact-raw-line) to ADD (dedupe-safe).
ADD: list[tuple[str, str]] = [
    ("design psychology", "Persuasion"),
    ("design psychology", "persuasion"),
    ("psychology", "Creative Psychology"),
    ("psychology", "creative psychology"),
]

# (canonical, old-definition-exact, new-definition-exact) replacements.
DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "design psychology",
        "The exploitation of cognitive science's known loopholes — biases, heuristics, and predictable errors of human thinking — to externally affect, persuade, or manipulate a user's or consumer's decision-making, and designing for those biases.",
        "The exploitation of cognitive science's known loopholes — biases, heuristics, and predictable errors of human thinking — to externally affect, persuade, or manipulate a user's or consumer's decision-making, and designing for those biases. It is applied persuasion psychology, not the study of cognition itself.",
    ),
    (
        "cognitive science",
        "The interdisciplinary study of how the mind works — perception, memory, attention, reasoning, language, and learning — as pure cognition, with no design, persuasion, or economic-application intent.",
        "The interdisciplinary study of how the mind works — perception, memory, attention, reasoning, language, and learning — as pure cognition, with no design, persuasion, or economic-application intent. The default home for any claim about how thinking or a cognitive process functions in itself.",
    ),
    (
        "behavioral economics",
        "The descriptive study of how psychological factors and biases cause systematic deviations from rational choice in economic decision-making and market behavior.",
        "The descriptive study of how psychological factors and cognitive biases cause systematic deviations from rational choice in economic decision-making and market behavior — where heuristics, framing, and affect change what people choose (prices, incentives, markets). It describes the bias; it does not exploit it to design persuasion.",
    ),
    (
        "psychology",
        "The empirical study of mind and behavior in individuals and groups — emotion, personality, development, social behavior, and mental health — beyond the computational modelling of cognition.",
        "The empirical study of mind and behavior in individuals and groups — emotion, personality, development, social behavior, and mental health — beyond the computational modelling of cognition. Broader and more behavioral than cognitive science, which models mental processes as computation.",
    ),
]


def _apply_to_blocks(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split into `- canonical:` blocks, apply REMOVE/ADD/DEFINITIONS, reassemble."""
    log: list[str] = []
    # Build maps keyed by canonical.
    remove_by_canon: dict[str, list[str]] = {}
    for c, r in REMOVE:
        remove_by_canon.setdefault(c, []).append(r)
    add_by_canon: dict[str, list[str]] = {}
    for c, r in ADD:
        add_by_canon.setdefault(c, []).append(r)
    defn_by_canon: dict[str, tuple[str, str]] = {c: (o, n) for c, o, n in DEFINITIONS}

    out: list[str] = []
    i = 0
    n = len(lines)
    # Pass 1: walk and emit, transforming each block in place.
    idx = 0
    while idx < n:
        line = lines[idx]
        if line.startswith("- canonical: "):
            canon = line[len("- canonical: "):].strip()
            # collect this block up to (but excluding) the next "- canonical:"
            block_start = idx
            idx += 1
            while idx < n and not lines[idx].startswith("- canonical: "):
                idx += 1
            block = lines[block_start:idx]
            new_block, block_log = _transform_block(canon, block,
                                                    remove_by_canon.get(canon, []),
                                                    add_by_canon.get(canon, []),
                                                    defn_by_canon.get(canon))
            log.extend(block_log)
            out.extend(new_block)
        else:
            out.append(line)
            idx += 1
    return out, log


def _transform_block(canon: str, block: list[str], removes: list[str],
                     adds: list[str], defn: tuple[str, str] | None) -> tuple[list[str], list[str]]:
    log: list[str] = []
    new: list[str] = []
    removed: set[str] = set()
    in_raw = False

    # 1. remove raw lines — ONLY within the `raw:` section (never exclude/definition)
    for line in block:
        stripped = line.strip()
        if stripped == "raw:":
            in_raw = True
            new.append(line)
            continue
        if in_raw and stripped.startswith(("group:", "definition:", "exclude:", "disposition:")):
            in_raw = False
        if in_raw and stripped.startswith("- ") and stripped[2:].strip() in removes:
            raw = stripped[2:].strip()
            if raw in removed:
                # duplicate within raw (case variant) — keep removal idempotent
                log.append(f"  - {canon!r}: (dup) {raw!r}")
                continue
            removed.add(raw)
            log.append(f"  - {canon!r}: removed {raw!r}")
            continue
        new.append(line)

    # 2. add raw lines (insert before the `definition:` line, or append at end)
    missing_adds = [a for a in adds if a not in {l.strip()[2:].strip() for l in new if l.strip().startswith("- ")}]
    if missing_adds:
        insert_at = len(new)
        for j, l in enumerate(new):
            if l.strip().startswith("definition:"):
                insert_at = j
                break
        for a in missing_adds:
            new.insert(insert_at, f"  - {a}\n")
            insert_at += 1
            log.append(f"  + {canon!r}: added {a!r}")

    # 3. replace definition line
    if defn is not None:
        old, newdef = defn
        hit = False
        for j, l in enumerate(new):
            if l.strip() == f"definition: {old}":
                new[j] = f"  definition: {newdef}\n"
                hit = True
                log.append(f"  ~ {canon!r}: definition strengthened")
                break
        if not hit:
            log.append(f"  ✗ {canon!r}: definition NOT matched (no change)")

    return new, log


def verify(lines: list[str]) -> int:
    """Re-parse the written text and check the 5-core disciplines are cross-listing-free."""
    import yaml
    from collections import defaultdict
    tax = yaml.safe_load("".join(lines)) or {}
    core = {"design psychology", "cognitive science", "behavioral economics", "psychology", "design thinking"}
    owner: dict[str, set[str]] = defaultdict(set)
    for d in tax.get("disciplines", []):
        canon = d.get("canonical")
        for r in (d.get("raw") or []):
            if r.strip():
                owner[r.strip().lower()].add(canon)
    bad = {k: v for k, v in owner.items() if len(v) > 1 and (v & core)}
    if bad:
        print("❌ remaining core cross-listings:")
        for k in sorted(bad):
            print(f"   {k!r} -> {sorted(bad[k])}")
        return 1
    print("✅ no cross-listings among the 5 core disciplines")
    return 0


def write(lines: list[str], ts: str) -> None:
    bak = _TAX.with_name(f"taxonomy.yaml.bak_{ts}_pre_d285_alias_fix")
    os.replace(_TAX, bak)
    text = "".join(lines)
    fd, tmp = tempfile.mkstemp(dir=str(_TAX.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    lines = open(_TAX, encoding="utf-8").readlines()
    new_lines, log = _apply_to_blocks(lines)
    print("planned changes:")
    for line in log:
        print(line)
    rc = verify(new_lines)
    if not args.apply:
        print("\n(dry-run — no write. re-run with --apply)")
        return rc
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    write(new_lines, ts)
    print("\npost-write verification:")
    return verify(open(_TAX, encoding="utf-8").readlines())


if __name__ == "__main__":
    raise SystemExit(main())
