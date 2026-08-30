#!/usr/bin/env python3
"""
route.py — FB folder routing + raw label accumulation counter.
=================================================================
Authority: governance/domain_labelling.md §5, D1055-FIX

Folder routing priority chain (v1-proven, now consolidated into one function):
    1. domain_canonical  (first non-"emerging" validated domain)
    2. domain_raw        (first non-"emerging" raw label — semantic grouping)
    3. "emerging"        (last resort)

The folder name is the human-readable label that tells you what category
the FBs fell into. When domain_raw != domain_canonical, the raw label
accumulates; when enough FBs share the same raw label, it earns a
canonical slot in taxonomy_v5.yaml.

Also provides:
    count_raw_labels(fbs) → {raw_label: count} for taxonomy expansion decisions
    route_fb_folder(fb) → folder name string

Usage:
    from pipeline.route import route_fb_folder, count_raw_labels
"""

import csv
import io
from collections import Counter
from pathlib import Path

from pipeline.io_guard import safe_write  # D2496: C6 crash-safe writes


def route_fb_folder(fb: dict) -> str:
    """Return the folder name for an FB using the priority chain.

    Priority:
        1. First non-emerging canonical domain → safe folder name
        2. First non-emerging raw domain → safe folder name
        3. "emerging"

    Folder names are filesystem-safe: spaces→underscores, &→and,
    lowercase, no special chars.
    """
    def _safe_name(label: str) -> str:
        """Convert a domain label to a filesystem-safe folder name."""
        if not label:
            return ""
        return (label
                .strip()
                .lower()
                .replace(" & ", "_and_")
                .replace("&", "_and_")
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_"))

    # 1. Try canonical domains
    canonical = fb.get("domains", [])
    if canonical and canonical != ["emerging"]:
        first = canonical[0]
        name = _safe_name(first)
        if name and name != "emerging":
            return name

    # 2. Try raw domains
    raw = fb.get("domains_raw", [])
    if raw and raw != ["emerging"]:
        first = raw[0]
        name = _safe_name(first)
        if name and name != "emerging":
            return name

    # 3. Fallback
    return "emerging"


def count_raw_labels(fbs: list[dict]) -> dict[str, int]:
    """Count FBs per raw domain label for taxonomy expansion analysis.

    Returns {raw_label: count} sorted descending.
    Use this to determine when a raw label has accumulated enough
    FBs to earn a canonical slot in taxonomy_v5.yaml.

    Only counts labels that differ from their canonical match
    (i.e., labels that the synonym matcher couldn't resolve).
    """
    counter = Counter()

    for fb in fbs:
        raw = fb.get("domains_raw") or fb.get("discipline_raw")
        if not raw:
            continue

        # Handle list (domains) or string (discipline)
        labels = raw if isinstance(raw, list) else [raw]

        for label in labels:
            label_clean = label.strip()
            if label_clean and label_clean.lower() != "emerging":
                counter[label_clean] += 1

    return dict(counter.most_common())


def route_fbs_to_tree(fbs: list[dict]) -> dict[str, list[dict]]:
    """Group FBs into a folder tree: {folder_name: [fb_dict, ...]}.

    Returns dict sorted by FB count per folder (largest first).
    """
    tree = {}
    for fb in fbs:
        folder = route_fb_folder(fb)
        if folder not in tree:
            tree[folder] = []
        tree[folder].append(fb)

    # Sort by count descending
    return dict(sorted(tree.items(), key=lambda x: len(x[1]), reverse=True))


def export_raw_label_report(fbs: list[dict], output_path: Path):
    """Export a CSV report of raw label accumulation for taxonomy decisions.

    Columns: raw_label, count, %_of_total, matched_canonical
    """
    total = len(fbs)
    counts = count_raw_labels(fbs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _buf = io.StringIO()
    writer = csv.writer(_buf)
    writer.writerow(["raw_label", "count", "pct_of_total", "recommendation"])
    for label, count in counts.items():
        pct = (count / total * 100) if total else 0
        rec = ""
        if pct >= 10:
            rec = "REVIEW — consider adding to taxonomy"
        elif pct >= 5:
            rec = "WATCH — accumulating"
        writer.writerow([label, count, f"{pct:.1f}%", rec])
    safe_write(output_path, _buf.getvalue())  # D2496: C6 crash-safe

    return output_path
