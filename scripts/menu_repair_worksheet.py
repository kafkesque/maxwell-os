"""Build the CORRECTED menu-repair re-issue (BUG-348 fix).

Defect fixed (BUG-348): the first generator compared the human `domains_verdict` cell to the
pipeline's emitted domains with a bare `.lower()` and no quote/whitespace stripping, then
printed the top-16 of that raw counter. Three consequences:

  1. sheet artifacts (a stray `"`) were reported as MENU GAPS ("marketing & communications\"",
     "\"leadership\"") - they are neither gaps nor variants;
  2. surface variants truncated by hand ("media & entertainmen", "product desig",
     "business operation") were reported as MENU GAPS;
  3. the single alias layer that already exists in this repo was never consulted, so the
     generator grew a SECOND, weaker matching path (the BUG-346 "two truth paths" class).

This generator has exactly one resolver: `pipeline.schemas.match_to_canonical` (kind-aware,
D2133) over `config/taxonomy_v5.yaml` canonical + `raw` aliases, plus the owner-approved
`config/normalization_map.yaml` surface variants (D-307, domain axis only - BUG-325).
A near-match is REPORTED, never silently resolved (D2422 spirit).

Buckets for PART 1 (the three failure classes):
  ARTIFACT           - resolves only after quote/whitespace hygiene; the slot is emitted anyway
  ALIAS_RESOLVED     - resolves via an alias/surface variant to a slot the pipeline DID emit
  UNEMITTED_EXISTING - slot exists in the menu and the pipeline NEVER emitted it (Emission class)
  NOVEL              - no slot and no near-match: a genuine ontology gap (Absence class)
  NEAR_MISS          - unresolved but >=0.9 similar to a menu slot: needs an alias ruling

Every artifact is stamped with the pins it was generated against (D-318).
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # single resolver lives in the package, not in this script
    sys.path.insert(0, str(ROOT))
SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_20260920.csv"
KEY = ROOT / "governance" / "ANCHOR2_KEY_20260920.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
NORM_MAP = ROOT / "config" / "normalization_map.yaml"
MENU = ROOT / "config" / "closed_menu_v5.json"
OUT = ROOT / "governance" / "PART1_PART2_REISSUE_20260921.md"
NEAR_MATCH_CUTOFF = 0.9
CATCH_ALL = "emerging"  # canonical on BOTH axes (meta.catch_all_domain/_discipline)
QUOTES = '"' + "\u201c\u201d" + "'"


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file's bytes (pin for D-318)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_quotes(s: str) -> str:
    """Remove any quote characters anywhere in a cell token (sheet hygiene)."""
    return "".join(ch for ch in (s or "") if ch not in QUOTES).strip()


def surface_aliases() -> dict:
    """Return the owner-approved surface-variant map (DOMAIN axis only, BUG-325)."""
    import yaml

    if not NORM_MAP.exists():
        return {}
    doc = yaml.safe_load(NORM_MAP.read_text(encoding="utf-8")) or {}
    return {strip_quotes(k).lower(): v for k, v in (doc.get("domains") or {}).items()}


def load_rows() -> list:
    """Return the adjudication sheet rows joined to the pipeline labels of ANCHOR-2 key."""
    key = json.loads(KEY.read_text(encoding="utf-8"))["key"]
    rows = []
    with SHEET.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if not (r.get("row") or "").strip():
                continue
            kid = r.get("fb_id") or ""
            rows.append({"row": r["row"], "name": r["name"], "fb_id": kid,
                         "definition": (r.get("definition") or "").strip(),
                         "human_disc": (r.get("discipline_verdict") or "").strip(),
                         "human_domains": (r.get("domains_verdict") or "").strip(),
                         "pipe_disc": (key.get(kid) or {}).get("pipeline_discipline", ""),
                         "pipe_domains": (key.get(kid) or {}).get("pipeline_domains") or []})
    return rows


def classify_token(tok: str, menu_dom: list, emitted: set, alias: dict) -> tuple:
    """Return (bucket, resolved_canonical, near_miss_candidates) for one human domain token."""
    from pipeline.schemas import match_to_canonical

    clean = strip_quotes(tok).lower()
    if not clean:
        return ("EMPTY", "", [])
    # `tok` is the CATCH-ALL and is canonical on BOTH axes, so the opposite-axis guard in
    # match_to_canonical rejects it (BUG-354). A catch-all is never a repair item anyway.
    if clean == CATCH_ALL:
        return ("CONSISTENT", CATCH_ALL, [])
    resolved = match_to_canonical(clean, "domain") or alias.get(clean)
    if resolved:
        hygiene_only = clean != (tok or "").strip().lower()  # a quote/space was removed
        if hygiene_only:
            return ("ARTIFACT", resolved, [])
        if clean not in {strip_quotes(m).lower() for m in menu_dom}:
            return ("ALIAS_RESOLVED", resolved, [])
        if resolved.lower() in emitted:
            return ("CONSISTENT", resolved, [])
        return ("UNEMITTED_EXISTING", resolved, [])
    near = difflib.get_close_matches(clean, [m.lower() for m in menu_dom], n=2,
                                     cutoff=NEAR_MATCH_CUTOFF)
    if near:
        return ("NEAR_MISS", "", near)
    return ("NOVEL", "", [])


def main() -> int:
    """Write the re-issue and print the corrected PART 1 / PART 2 lists."""
    from pipeline.closed_menu import menu_hash

    rows = load_rows()
    menu = json.loads(MENU.read_text(encoding="utf-8"))
    menu_dom = [d["value"] for d in menu["domains"]]
    alias = surface_aliases()
    emitted = {strip_quotes(str(d)).lower() for r in rows for d in r["pipe_domains"]}

    buckets: dict = defaultdict(list)
    for r in rows:
        for tok in [x for x in r["human_domains"].split(",") if x.strip()]:
            bucket, resolved, near = classify_token(tok, menu_dom, emitted, alias)
            buckets[bucket].append({"tok": tok, "row": r["row"], "resolved": resolved, "near": near})

    unem: Counter = Counter()
    unem_rows: dict = defaultdict(list)
    for e in buckets["UNEMITTED_EXISTING"]:
        unem[e["resolved"]] += 1
        unem_rows[e["resolved"]].append(e["row"])

    lines = [
        "# MENU REPAIR - PART 1 / PART 2 RE-ISSUE - 2026-09-21",
        "",
        "Supersedes the PART 1 / PART 2 of `MENU_REPAIR_WORKSHEET_20260921.md` only as a CORRECTED",
        "READING. The owner's rulings in that worksheet stand; this file fixes what was shown to them",
        "(BUG-348). Regenerating the ruled worksheet is forbidden (R-D410: a published artifact is evidence).",
        "",
        "## Pins this artifact was generated against (D-318)",
        "",
        "| input | sha256 |",
        "|---|---|",
        "| governance/ANCHOR2_BLIND_SHEET_20260920.csv | `%s` |" % sha256_file(SHEET),
        "| governance/ANCHOR2_KEY_20260920.json | `%s` |" % sha256_file(KEY),
        "| config/taxonomy_v5.yaml | `%s` |" % sha256_file(TAXONOMY),
        "| config/closed_menu_v5.json (bytes) | `%s` |" % sha256_file(MENU),
        "| config/closed_menu_v5.json (menu_hash) | `%s` |" % menu_hash(menu),
        "| config/normalization_map.yaml | `%s` |" % (sha256_file(NORM_MAP) if NORM_MAP.exists() else "n/a"),
        "",
        "## PART 1 (RE-ISSUED) - the four failure classes",
        "",
        "| class | n | meaning |",
        "|---|---|---|",
        "| ARTIFACT | %d | sheet hygiene only (a stray quote); slot exists AND was emitted - NOT a menu item |" % len(buckets["ARTIFACT"]),
        "| ALIAS_RESOLVED | %d | a surface variant of a slot the pipeline DID emit - spelling, not ontology |" % len(buckets["ALIAS_RESOLVED"]),
        "| UNEMITTED_EXISTING | %d | slot EXISTS in the menu, pipeline NEVER emitted it - EMISSION class (the real defect) |" % len(buckets["UNEMITTED_EXISTING"]),
        "| NOVEL | %d | no slot, no near-match - genuine ontology gap (Absence class) |" % len(buckets["NOVEL"]),
        "| NEAR_MISS | %d | unresolved but >=%.2f similar to a slot - needs an explicit alias ruling |" % (len(buckets["NEAR_MISS"]), NEAR_MATCH_CUTOFF),
        "",
        "### 1a. UNEMITTED_EXISTING - slots the menu offers and the pipeline never selects",
        "",
        "| # | slot | human uses | rows |",
        "|---|---|---|---|",
    ]
    for i, (d, n) in enumerate(unem.most_common(), 1):
        lines.append("| %d | %s | %d | %s |" % (i, d, n, ", ".join(unem_rows[d])))
    for title, key_ in (("1b. ARTIFACT - sheet hygiene, no action", "ARTIFACT"),
                        ("1c. ALIAS_RESOLVED - already covered by an alias", "ALIAS_RESOLVED"),
                        ("1d. NEAR_MISS - needs an alias ruling", "NEAR_MISS"),
                        ("1e. NOVEL - genuine ontology gap", "NOVEL")):
        lines += ["", "### %s" % title, ""]
        if not buckets[key_]:
            lines.append("_none_")
        else:
            lines += ["| raw cell token | row | resolves to | nearest |", "|---|---|---|---|"]
            for e in buckets[key_]:
                lines.append("| `%s` | %s | %s | %s |"
                             % (e["tok"], e["row"], e["resolved"] or "-", ", ".join(e["near"]) or "-"))

    # ── PART 2: all disagreeing pairs, with the source excerpt ──
    def nrm(s: str) -> str:
        return strip_quotes(s).lower()

    pairs: Counter = Counter()
    for r in rows:
        h, p = nrm(r["human_disc"]), nrm(r["pipe_disc"])
        if h and h != p:
            pairs[(h, p)] += 1
    lines += ["", "## PART 2 (RE-ISSUED) - all %d disagreeing discipline pairs, with excerpts" % len(pairs),
              "",
              "Column 4 is the excerpt the first issue left EMPTY: the generator read `row`/`name` but never the",
              "`definition` column that carries the text the label was derived from. Read it before ruling.",
              "",
              "| # | your label | stored label | n | rows | excerpt (first 200 chars of the definition) |",
              "|---|---|---|---|---|---|"]
    for i, ((h, p), n) in enumerate(pairs.most_common(), 1):
        rs = [r for r in rows if nrm(r["human_disc"]) == h and nrm(r["pipe_disc"]) == p]
        ex = (rs[0]["definition"] if rs else "")[:200].replace("|", "/").replace("\n", " ")
        lines.append("| %d | %s | %s | %d | %s | %s |"
                     % (i, h, p, n, ", ".join(r["row"] for r in rs), ex + ("..." if len(ex) >= 200 else "")))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PART1 | ARTIFACT=%d ALIAS_RESOLVED=%d UNEMITTED_EXISTING=%d NOVEL=%d NEAR_MISS=%d"
          % (len(buckets["ARTIFACT"]), len(buckets["ALIAS_RESOLVED"]),
             len(buckets["UNEMITTED_EXISTING"]), len(buckets["NOVEL"]), len(buckets["NEAR_MISS"])))
    print("ARTIFACT:", sorted({e["tok"] for e in buckets["ARTIFACT"]}))
    print("ALIAS_RESOLVED:", sorted({(e["tok"], e["resolved"]) for e in buckets["ALIAS_RESOLVED"]}))
    print("UNEMITTED:", list(unem.most_common()))
    print("NEAR_MISS:", sorted({(e["tok"], tuple(e["near"])) for e in buckets["NEAR_MISS"]}))
    print("NOVEL:", sorted({e["tok"] for e in buckets["NOVEL"]}))
    print("PART2 pairs:", len(pairs), "rows:", sum(pairs.values()))
    print("wrote", OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
