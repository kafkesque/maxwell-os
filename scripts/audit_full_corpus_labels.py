#!/usr/bin/env python3
"""D2541: Full-corpus deterministic label audit (structural/axis errors).

Checks EVERY FB for the BUG-197 / D2422 / D2378 class of label errors — WITHOUT an
LLM (deterministic `match_to_canonical` on both axes). This is the "correctly
labelled" check at the structural level: axis leakage, empty raw, both-axes, and
unknown labels. It does NOT re-judge semantic correctness (that is a ~22h LLM pass,
effectively re-running S4) — it flags the mechanical/axis defects that are the known
failure class.

Read-only. Reports counts + distinct offender labels.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    match_to_canonical,
    normalize_label,
)


def _to_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [v]
    return list(v)


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT discipline, discipline_raw, domains, domains_raw FROM fbs").fetchall()
    conn.close()

    disc_canon = {normalize_label(c) for c in CANONICAL_DISCIPLINES}
    dom_canon = {normalize_label(c) for c in CANONICAL_DOMAINS}

    leak_domain_in_disc_raw = Counter()      # domain label leaked into discipline_raw
    leak_disc_in_domains_raw = Counter()     # discipline label leaked into domains_raw
    emerging_empty_raw = 0                   # discipline=emerging + empty raw (reclass target)
    canonical_empty_raw = 0                  # canonical discipline + empty raw (D2378)
    both_axes = Counter()                    # same label on both axes
    unknown_discipline = Counter()           # discipline not canonical & not emerging
    unknown_domain = Counter()               # domain not canonical
    emerging_nonempty_raw = Counter()        # emerging + non-empty raw (BUG-150 gap)
    empty_domains = 0                        # domains empty / ['emerging']

    for r in rows:
        disc = (r["discipline"] or "").strip()
        disc_raw = (r["discipline_raw"] or "").strip()
        doms = _to_list(r["domains"])
        doms_raw = _to_list(r["domains_raw"])

        # 1. cross-axis leak: discipline_raw holds a DOMAIN label (and not a discipline)
        if disc_raw:
            if match_to_canonical(disc_raw, "domain") and not match_to_canonical(disc_raw, "discipline"):
                leak_domain_in_disc_raw[disc_raw] += 1
        for l in doms_raw:
            if l and match_to_canonical(l, "discipline") and not match_to_canonical(l, "domain"):
                leak_disc_in_domains_raw[l] += 1

        # 2. empty raw
        if disc == "emerging":
            if not disc_raw:
                emerging_empty_raw += 1
            else:
                emerging_nonempty_raw[disc_raw] += 1
        else:
            if not disc_raw:
                canonical_empty_raw += 1

        # 3. both-axes (same normalized label in domains_raw AND discipline_raw)
        if disc_raw:
            n = normalize_label(disc_raw)
            if any(normalize_label(x) == n for x in doms_raw):
                both_axes[disc_raw] += 1

        # 4. unknown labels
        if disc and disc != "emerging" and normalize_label(disc) not in disc_canon:
            unknown_discipline[disc] += 1
        for d in doms:
            d = (d or "").strip()
            if d and d != "emerging" and normalize_label(d) not in dom_canon:
                unknown_domain[d] += 1

        # 5. empty domains
        if not doms or doms == ["emerging"]:
            empty_domains += 1

    total = len(rows)
    print(f"📊 Full-corpus label audit — {total} FBs")
    print(f"\n🔴 AXIS LEAKS (BUG-197 class — deterministic, fixable by kind-swap):")
    print(f"   domain label in discipline_raw:  {sum(leak_domain_in_disc_raw.values())} FBs ({len(leak_domain_in_disc_raw)} labels)")
    for l, c in leak_domain_in_disc_raw.most_common(10):
        print(f"      {c:4}  {l}")
    print(f"   discipline label in domains_raw: {sum(leak_disc_in_domains_raw.values())} FBs ({len(leak_disc_in_domains_raw)} labels)")
    for l, c in leak_disc_in_domains_raw.most_common(10):
        print(f"      {c:4}  {l}")

    print(f"\n🟡 RAW-LABEL VIOLATIONS:")
    print(f"   emerging + EMPTY discipline_raw (reclass target): {emerging_empty_raw}")
    print(f"   canonical + EMPTY discipline_raw (D2378):         {canonical_empty_raw}")
    print(f"   emerging + non-empty raw (BUG-150 taxonomy gap):  {sum(emerging_nonempty_raw.values())} ({len(emerging_nonempty_raw)} labels)")

    print(f"\n🟠 BOTH-AXES (same label both axes): {sum(both_axes.values())} FBs ({len(both_axes)} labels)")
    for l, c in both_axes.most_common(10):
        print(f"      {c:4}  {l}")

    print(f"\n🟣 UNKNOWN LABELS (not in taxonomy):")
    print(f"   unknown discipline: {sum(unknown_discipline.values())} FBs ({len(unknown_discipline)} labels)")
    for l, c in unknown_discipline.most_common(10):
        print(f"      {c:4}  {l}")
    print(f"   unknown domain:     {sum(unknown_domain.values())} FBs ({len(unknown_domain)} labels)")
    for l, c in unknown_domain.most_common(10):
        print(f"      {c:4}  {l}")

    print(f"\n⚪ empty/['emerging'] domains: {empty_domains} FBs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
