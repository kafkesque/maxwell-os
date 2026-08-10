#!/usr/bin/env python3
"""D2228: Strip S4 CRIBS enrichment fields from S2 golden set expected_fb.

Removes: application, elaboration, procedural_skill, failure_mode,
         jargon, keywords, prerequisite_fbs, contradicts_fbs,
         related_fbs, evidence.
Keeps:   name, definition, mechanism, boundary, consequence,
         evidence_passages, extraction_type, depth, content_type,
         is_summary, route.
"""

import collections
import sys
from pathlib import Path

import yaml

S4_FIELDS = {
    "application", "elaboration", "procedural_skill", "failure_mode",
    "jargon", "keywords", "prerequisite_fbs", "contradicts_fbs",
    "related_fbs", "evidence",
}


def strip_fb(fb_dict: dict) -> int:
    """Remove S4 fields from a single FB dict. Returns count removed."""
    removed = set(fb_dict.keys()) & S4_FIELDS
    for k in removed:
        del fb_dict[k]
    return len(removed)


def main() -> None:
    gs_path = Path("config/golden/stage2_fewshot_convergent.yaml")
    with open(gs_path) as f:
        gs = yaml.safe_load(f)

    stripped_count = 0
    field_counts: dict[str, int] = collections.Counter()

    for ex in gs.get("examples", []):
        efb = ex.get("expected_fb")
        items: list[dict] = []
        if isinstance(efb, list):
            items = efb
        elif isinstance(efb, dict):
            items = [efb]
        else:
            continue

        for fb_dict in items:
            removed = set(fb_dict.keys()) & S4_FIELDS
            for k in removed:
                field_counts[k] = field_counts.get(k, 0) + 1
                del fb_dict[k]
            stripped_count += len(removed)

        # Also clean root-level S4 fields
        root_stray = set(ex.keys()) & S4_FIELDS
        for k in root_stray:
            del ex[k]

    # Verify
    remaining = 0
    for ex in gs.get("examples", []):
        efb = ex.get("expected_fb")
        items2: list[dict] = []
        if isinstance(efb, list):
            items2 = efb
        elif isinstance(efb, dict):
            items2 = [efb]
        else:
            items2 = []
        for fb_dict in items2:
            stray = set(fb_dict.keys()) & S4_FIELDS
            if stray:
                print(f"❌ {ex['id']}: fields still present: {stray}")
                remaining += 1

    print(f"Stripped {stripped_count} S4 field instances:")
    for k, v in sorted(field_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"Remaining S4 fields in examples: {remaining}")

    # Count remaining fields
    all_remaining: dict[str, int] = collections.Counter()
    for ex in gs.get("examples", []):
        efb = ex.get("expected_fb")
        items3: list[dict] = []
        if isinstance(efb, list):
            items3 = efb
        elif isinstance(efb, dict):
            items3 = [efb]
        else:
            items3 = []
        for fb_dict in items3:
            all_remaining.update(fb_dict.keys())

    print(f"\nRemaining fields (S2 core):")
    for k, v in sorted(all_remaining.items()):
        print(f"  {k}: {v}")

    # Write back
    with open(gs_path, "w") as f:
        yaml.dump(gs, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    print(f"\n✅ Written to {gs_path}")
    print("✅ T-001 COMPLETE: S4 fields stripped from golden set")


if __name__ == "__main__":
    main()
