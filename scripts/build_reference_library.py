#!/usr/bin/env python3
"""build_reference_library.py — turn config/references.yaml into a verifiable bibliography.

WHY: the forensic reports cite ~40 works inline, and a frontier LLM (or a human auditor) cannot
resolve or check them without chasing prose. This script emits a single source of truth in three
formats from one curated list:

    governance/REFERENCE_LIBRARY_20260919.md    readable, grouped by the claim it supports
    governance/references_20260919.bib          BibTeX, importable
    governance/references_20260919.json         the resolved metadata snapshot (doubles as the cache)

DESIGN (C12 / C16 / no-silent-errors):
  * config/references.yaml holds the CURATED part (id, doi, url, role, bears, used_in).
  * the SCRIPT FETCHES title/year/venue/citation-count from OpenAlex by DOI, so a mistyped year,
    venue or citation count cannot survive a rebuild -- the numbers in the library are fetched
    evidence, not assertions.
  * a DOI that fails to resolve is REPORTED and marked UNVERIFIED; it is never silently dropped.
  * items with no DOI (W3C SKOS/PROV-O/SHACL, a book, an ICML proceedings entry) are emitted with their URL
    STANDARD, because the specification body is the authority, not a paper.
  * --cached re-renders from the JSON snapshot with no network, so the library is reproducible offline.

Usage:
  python3 scripts/build_reference_library.py             # fetch metadata for every DOI, then render
  python3 scripts/build_reference_library.py --cached     # re-render from the JSON snapshot only
  python3 scripts/build_reference_library.py --check      # fetch and report, write nothing
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "references.yaml"
OUT_MD = REPO / "governance" / "REFERENCE_LIBRARY_20260919.md"
OUT_BIB = REPO / "governance" / "references_20260919.bib"
OUT_JSON = REPO / "governance" / "references_20260919.json"

OPENALEX = "https://api.openalex.org/works/doi:"
TIMEOUT = 25


def load_config() -> list[dict[str, Any]]:
    """Load the curated reference list.

    Returns:
        The list of reference records under the `references` key.

    Raises:
        SystemExit: if the file is missing or has no `references` list.
    """
    if not CFG.exists():
        print("FAIL-CLOSED: no %s" % CFG)
        sys.exit(1)
    data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    refs = data.get("references")
    if not isinstance(refs, list) or not refs:
        print("FAIL-CLOSED: %s has no `references` list" % CFG)
        sys.exit(1)
    return refs


def fetch(doi: str) -> dict[str, Any] | None:
    """Fetch one work's metadata from OpenAlex by DOI.

    Uses curl rather than urllib: this machine's Python 3.12 lacks a CA bundle for urllib, and a
    silent certificate failure would be indistinguishable from a bad DOI (C16).

    Args:
        doi: the DOI to resolve.

    Returns:
        The OpenAlex work record, or None when it could not be fetched (never raises).
    """
    url = OPENALEX + doi
    try:
        proc = subprocess.run(
            ["curl", "-sS", "--max-time", str(TIMEOUT), "-H", "Accept: application/json", url],
            capture_output=True, text=True, timeout=TIMEOUT + 5,
        )
    except Exception as exc:  # network/tooling failure must be visible, not swallowed
        print("  ! curl failed for %s: %s: %s" % (doi, type(exc).__name__, exc))
        return None
    body = (proc.stdout or "").strip()
    if not body or body.startswith("{"):
        try:
            data = json.loads(body)
        except ValueError:
            return None
        # OpenAlex returns {"error": ...} with HTTP 404 for an unknown DOI
        if "error" in data:
            return None
        return data
    return None


def resolved(work: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    """Reduce an OpenAlex record to the fields the library needs.

    Args:
        work: the OpenAlex work record.
        rec: the curated reference record.

    Returns:
        A flat metadata dict, with the curated fields preserved.
    """
    src = ((work.get("primary_location") or {}).get("source") or {})
    authors = [a.get("author", {}).get("display_name", "") for a in (work.get("authorships") or [])]
    return {
        "id": rec["id"],
        "doi": rec.get("doi") or "",
        "url": rec.get("url") or (work.get("doi") or ""),
        "title": work.get("display_name") or work.get("title") or "",
        "year": work.get("publication_year"),
        "venue": src.get("display_name") or "",
        "cited_by": work.get("cited_by_count"),
        "type": work.get("type") or "",
        "authors": [a for a in authors if a][:6],
        "role": rec.get("role", ""),
        "bears": rec.get("bears", ""),
        "used_in": list(rec.get("used_in") or []),
        "verification": "OPENALEX_DOI_FETCH",
        "note": rec.get("note", ""),
    }


def bib_key(rec: dict[str, Any]) -> str:
    """Build a stable BibTeX key from the id.

    Args:
        rec: a resolved metadata record.

    Returns:
        A BibTeX-safe citation key.
    """
    return re.sub(r"[^A-Za-z0-9_:-]", "", str(rec["id"]))


def render_bib(records: list[dict[str, Any]]) -> str:
    """Render the BibTeX file.

    Args:
        records: resolved metadata records.

    Returns:
        The .bib file contents.
    """
    out = ["% Maxwell OS reference library -- generated by scripts/build_reference_library.py",
           "% DO NOT hand-edit: edit config/references.yaml and rebuild.", ""]
    for r in records:
        kind = "misc" if r["verification"] != "OPENALEX_DOI_FETCH" else (
            "article" if r.get("type") == "article" else "inproceedings")
        out.append("@%s{%s," % (kind, bib_key(r)))
        if r.get("title"):
            out.append('  title = {%s},' % str(r["title"]).replace("{", "").replace("}", ""))
        if r.get("authors"):
            out.append("  author = {%s}," % " and ".join(r["authors"]))
        if r.get("year"):
            out.append("  year = {%s}," % r["year"])
        if r.get("venue"):
            out.append("  journal = {%s}," % str(r["venue"]).replace("{", "").replace("}", ""))
        if r.get("doi"):
            out.append("  doi = {%s}," % r["doi"])
        if r.get("url"):
            out.append("  url = {%s}," % r["url"])
        out.append("  note = {%s}" % str(r.get("role", ""))[:240].replace("{", "").replace("}", ""))
        out.append("}")
        out.append("")
    return "\n".join(out)


def render_md(records: list[dict[str, Any]], missing: list[str]) -> str:
    """Render the readable markdown library.

    Args:
        records: resolved metadata records.
        missing: ids whose DOI could not be resolved.

    Returns:
        The markdown file contents.
    """
    ok = [r for r in records if r["verification"] == "OPENALEX_DOI_FETCH"]
    std = [r for r in records if r["verification"] != "OPENALEX_DOI_FETCH"]
    md = [
        "# REFERENCE LIBRARY — Maxwell OS ontology / retrieval programme",
        "",
        "**Generated** by `scripts/build_reference_library.py` from `config/references.yaml`.",
        "**DO NOT hand-edit** — edit the config and rebuild, so a mistyped year, venue or DOI cannot survive.",
        "",
        "**Metadata for every DOI below was FETCHED from OpenAlex by DOI** (title, year, venue, citation count),",
        "not typed by a human. That is the point of this file: a claim you cannot resolve is a claim you cannot",
        "check, and the whole forensic programme rests on being checkable.",
        "",
        "| | count |",
        "|---|---|",
        "| entries | %d |" % len(records),
        "| DOI-resolved and verified | **%d** |" % len(ok),
        "| no DOI (URL only) | %d |" % len(std),
        "| **unverified (DOI did not resolve — reported, never dropped)** | **%d** |" % len(missing),
        "",
        "Machine-readable companions: `governance/references_20260919.bib` (BibTeX) and",
        "`governance/references_20260919.json` (resolved metadata snapshot; also the offline cache).",
        "",
        "---",
        "",
        "## What each entry supports",
        "",
        "The `bears` column ties a reference to the specific finding or repair it justifies, so a reviewer can",
        "start from a defect and land on the literature (or vice versa).",
        "",
    ]
    if missing:
        md += ["> **UNVERIFIED ENTRIES — action required.** These identifiers did not resolve against OpenAlex",
               "> and are therefore NOT evidence. Either the DOI is wrong or the work is not indexed:",
               "> " + ", ".join("`%s`" % m for m in missing), ""]

    for group_title, rows in (("Verified (DOI resolves)", ok), ("No DOI resolved (URL only -- book, proceedings or W3C standard; the item itself is the authority)", std)):
        if not rows:
            continue
        md += ["### %s" % group_title, "",
               "| id | year | cites | title | venue | DOI | bears |",
               "|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda x: (-(x.get("cited_by") or 0))):
            md.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (
                r["id"], r.get("year") or "n.d.", r.get("cited_by") if r.get("cited_by") is not None else "—",
                str(r.get("title") or "")[:96], str(r.get("venue") or "—")[:38],
                ("[%s](https://doi.org/%s)" % (r["doi"], r["doi"])) if r.get("doi") else "[link](%s)" % r.get("url", ""),
                str(r.get("bears") or "")[:60],
            ))
        md.append("")

    md += ["---", "", "## Full entries (role reproduced verbatim from the config)", ""]
    for r in records:
        md.append("**`%s`** — %s%s" % (
            r["id"],
            "<%s>" % r["url"] if r.get("url") and not r.get("doi") else
            ("https://doi.org/%s" % r["doi"] if r.get("doi") else ""),
            " · cited %s×" % r["cited_by"] if r.get("cited_by") is not None else ""))
        md.append("")
        md.append("- **%s** (%s). %s" % (r.get("title") or "(unresolved)", r.get("year") or "n.d.",
                                         str(r.get("venue") or "").strip()))
        md.append("- *why:* %s" % r.get("role", ""))
        md.append("- *bears:* %s" % r.get("bears", ""))
        if r.get("used_in"):
            md.append("- *cited in:* %s" % ", ".join("`%s`" % u for u in r["used_in"]))
        if r.get("note"):
            md.append("- *note:* %s" % r["note"])
        if r["verification"] != "OPENALEX_DOI_FETCH":
            md.append("- **verification: %s** — no DOI resolved for this item; the linked document is the authority" % r["verification"])
        md.append("")

    md += ["---", "",
           "## How to reproduce", "",
           "```bash",
           "python3 scripts/build_reference_library.py            # fetch every DOI from OpenAlex, then render",
           "python3 scripts/build_reference_library.py --cached    # re-render from the JSON snapshot (offline)",
           "python3 scripts/build_reference_library.py --check     # fetch and report, write nothing",
           "```", ""]
    return "\n".join(md)


def main() -> int:
    """Fetch/verify the reference list and write the three artifacts."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="re-render from the JSON snapshot, no network")
    ap.add_argument("--check", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args()

    refs = load_config()
    records: list[dict[str, Any]] = []
    missing: list[str] = []

    snapshot: dict[str, Any] = {}
    if args.cached:
        if not OUT_JSON.exists():
            print("FAIL-CLOSED: --cached needs %s, which does not exist yet" % OUT_JSON.name)
            return 1
        snapshot = {r["id"]: r for r in json.loads(OUT_JSON.read_text(encoding="utf-8"))["references"]}
        print("cached mode: re-rendering %d entries from %s" % (len(snapshot), OUT_JSON.name))

    for rec in refs:
        doi = (rec.get("doi") or "").strip()
        if args.cached:
            prev = snapshot.get(rec["id"])
            if not prev:
                missing.append(rec["id"])
                continue
            records.append({**prev, **{k: rec.get(k, prev.get(k)) for k in ("role", "bears", "used_in")}})
            continue

        if not doi:
            records.append({
                "id": rec["id"], "doi": "", "url": rec.get("url", ""), "title": rec.get("title", ""),
                "year": rec.get("year"), "venue": rec.get("venue", ""), "cited_by": rec.get("cited_by"),
                "type": "standard", "authors": rec.get("authors", []), "role": rec.get("role", ""),
                "bears": rec.get("bears", ""), "note": rec.get("note", ""),
                "used_in": list(rec.get("used_in") or []), "verification": "URL_ONLY",
            })
            continue

        work = fetch(doi)
        if not work:
            print("  ✗ UNRESOLVED: %s (%s)" % (rec["id"], doi))
            missing.append(rec["id"])
            records.append({
                "id": rec["id"], "doi": doi, "url": "https://doi.org/" + doi, "title": rec.get("title", ""),
                "year": None, "venue": "", "cited_by": None, "type": "", "authors": [],
                "role": rec.get("role", ""), "bears": rec.get("bears", ""),
                "used_in": list(rec.get("used_in") or []), "verification": "UNVERIFIED",
            })
            continue

        m = resolved(work, rec)
        records.append(m)
        print("  ✓ %-34s %s  cites=%-6s %s" % (rec["id"], m["year"], m["cited_by"], str(m["title"])[:62]))

    if args.check:
        print("\n--check: %d entries, %d unresolved, nothing written" % (len(records), len(missing)))
        return 1 if missing else 0

    OUT_JSON.write_text(json.dumps(
        {"generated_by": "scripts/build_reference_library.py", "source": "config/references.yaml",
         "verification_method": "OpenAlex DOI fetch (title/year/venue/citation count fetched, not typed)",
         "unresolved": missing, "references": records}, indent=1), encoding="utf-8")
    OUT_BIB.write_text(render_bib(records), encoding="utf-8")
    OUT_MD.write_text(render_md(records, missing), encoding="utf-8")
    print("\nwrote %s, %s and %s" % (OUT_MD.name, OUT_BIB.name, OUT_JSON.name))
    print("entries %d | DOI-verified %d | URL-only %d | UNRESOLVED %d"
          % (len(records), sum(1 for r in records if r["verification"] == "OPENALEX_DOI_FETCH"),
             sum(1 for r in records if r["verification"] == "URL_ONLY"), len(missing)))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
