"""Apply owner-approved menu repair v6 (PART1 A adds) + normalisation map + boundary queue.

Owner decisions (2026-09-21): PART1 A = add the 8 real gap domains; PART1 B = typo/spelling variants
must be normalised onto their existing canonical label; PART2 B = the 16 discipline pairs are genuinely
different concepts and need inclusion/exclusion boundary rules (reviewed one pair at a time).
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TAX = ROOT / "config" / "taxonomy.yaml"
NORM = ROOT / "config" / "normalization_map.yaml"
QUEUE = ROOT / "governance" / "MENU_REPAIR_QUEUE_20260921.md"
MIG = ROOT / "governance" / "TAXONOMY_v6_MIGRATION_20260921.md"
SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_20260920.csv"
KEY = ROOT / "governance" / "ANCHOR2_KEY_20260920.json"

# new domain -> (reference existing domain whose group it inherits, aliases)
ADDS = {
    "systems & frameworks": ("systems thinking", ["Systems & Frameworks", "systems_frameworks", "framework thinking", "systems framework"]),
    "web & ui": ("user experience", ["Web & UI", "web_ui", "ui design", "web design", "interface design"]),
    "social sciences": ("sociology", ["Social Sciences", "social_sciences", "social science", "social science research"]),
    "illustration": ("graphic design", ["Illustration", "illustration practice", "editorial illustration"]),
    "code & computation": ("software engineering", ["Code & Computation", "code_computation", "programming", "computational craft"]),
    "environmental design": ("interior design", ["Environmental Design", "environmental_design", "spatial design"]),
    "motion design": ("motion & time", ["Motion Design", "motion_design", "motion graphics"]),
    "design systems": ("product design", ["Design Systems", "design_systems", "component library", "design tokens"]),
}

NORMALISE = {
    "media & entertainmen": "media & entertainment",
    "product desig": "product design",
    "business operation": "business operations",
    "marketing & communications\"": "marketing & communications",
    "\"leadership\"": "leadership",
    "social science": "social sciences",
    "human-computer interaction": "human computer interaction",
}


def patch_taxonomy() -> list:
    """Append the approved domains, bump the version, and return the list of added canonicals."""
    shutil.copy2(TAX, TAX.with_suffix(".yaml.bak_v5_5"))
    doc = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    by_canonical = {d["canonical"]: d for d in doc["domains"]}
    added = []
    for canon, (ref, aliases) in ADDS.items():
        if canon in by_canonical:
            continue
        group = by_canonical[ref]["group"]
        doc["domains"].append({"canonical": canon, "group": group, "raw": aliases})
        added.append(canon)
    doc["version"] = "v6.0"
    doc["classification_version"] = "v6.0"
    meta = doc.setdefault("meta", {})
    meta["v6_added_domains"] = added
    meta["v6_rationale"] = "owner-approved menu repair 2026-09-21: gaps where the pipeline emitted no matching slot"
    TAX.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return added


def write_support_files(added: list) -> None:
    """Write the normalisation map, the migration record and the boundary-review queue."""
    NORM.write_text(yaml.safe_dump({"version": "v1", "note": "owner-approved 2026-09-21: spelling/surface variants -> existing canonical label",
                                    "domains": NORMALISE}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    MIG.write_text("# Taxonomy v6 migration record (2026-09-21)\n\n"
                   "Trigger: ANCHOR-2 repair triage (owner-approved PART1 A).\n\n"
                   "## Added domains\n" + "".join("- " + a + "\n" for a in added) +
                   "\n## Unchanged\n- every v5.5 canonical is preserved; no slot was removed or renamed,\n"
                   "  so all pre-v6 kappa / contra numbers stay readable.\n\n"
                   "## Normalisation (not menu changes)\n" +
                   "".join("- " + k + " -> " + v + "\n" for k, v in NORMALISE.items()) +
                   "\n## Not yet applied\n- the 16 discipline boundary pairs (PART2 B) are reviewed one at a time;\n"
                   "  see MENU_REPAIR_QUEUE_20260921.md. Pipeline output is unchanged until they are settled.\n",
                   encoding="utf-8")
    key = json.loads(KEY.read_text(encoding="utf-8"))["key"]
    from collections import Counter
    pairs: Counter = Counter()
    with SHEET.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            h = (r.get("discipline_verdict") or "").strip().lower()
            p = ((key.get(r.get("fb_id") or "") or {}).get("pipeline_discipline") or "").strip().lower()
            if h and h != p:
                pairs[(h, p)] += 1
    lines = ["# MENU REPAIR QUEUE - discipline boundary pairs (PART2 B, owner-approved)", "",
             "Review method: I send ONE pair below with a drafted inclusion/exclusion test; you answer",
             "SAME or DIFFERENT with one line of rationale. Nothing is applied to the pipeline until all",
             "pairs are settled, then kappa is re-measured on the 116 labelled ruler rows.", ""]
    for i, ((h, p), n) in enumerate(pairs.most_common(), 1):
        lines.append("%d. %s vs %s (%d rows) - status: PENDING" % (i, h, p, n))
    lines += ["", "## Item 1 - DRAFT for your review", "",
              "Pair: cognitive science vs psychology (3 rows: 1, 7, 59).",
              "Draft boundary test:",
              "- INCLUDE in cognitive science: claims about internal information processing (attention, memory,",
              "  perception, language, decision) where the level of analysis is the mechanism, not the person in context.",
              "- EXCLUDE from cognitive science -> psychology: claims about behaviour, affect, personality, therapy,",
              "  or group/social dynamics, and anything measured only by outcome rather than mechanism.",
              "- Tie-breaker: if the finding is stated as a mechanism of mind and would be published in a cognitive",
              "  science venue, it is cognitive science; otherwise psychology.",
              "Your answer: SAME (alias) or DIFFERENT (accept draft / amend) ->"]
    QUEUE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kappa_effect() -> None:
    """Show the measurable effect of normalisation on the domain axis (micro-kappa)."""
    key = json.loads(KEY.read_text(encoding="utf-8"))["key"]
    rows = []
    with SHEET.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append((r.get("domains_verdict") or "", (key.get(r.get("fb_id") or "") or {}).get("pipeline_domains") or []))
    def kappa(normalise: bool) -> float:
        num = den = n = 0
        for human, pipe in rows:
            hs = {NORMALISE.get(x.strip().lower(), x.strip().lower()) for x in human.split(",") if x.strip()} if normalise else {x.strip().lower() for x in human.split(",") if x.strip()}
            ps = {str(x).strip().lower() for x in pipe}
            for d in hs | ps:
                n += 1
                num += int((d in hs) == (d in ps))
                den += int((d in hs) + (d in ps))
        po = num / n if n else 0.0
        pe = 0.0
        return po
    print("domain axis observed agreement: raw=%.4f normalised=%.4f" % (kappa(False), kappa(True)))
    print("labels added to taxonomy:", len(yaml.safe_load(TAX.read_text(encoding="utf-8"))["domains"]))


def main() -> int:
    """Apply the approved repair, write the artefacts, and report the normalisation effect."""
    added = patch_taxonomy()
    write_support_files(added)
    kappa_effect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
