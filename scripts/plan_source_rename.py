#!/usr/bin/env python3
"""plan_source_rename.py — the OWNER-LANE rename plan for the source library (READ-ONLY, T-176/D-3048).

THE OWNER WORD THIS ACT CARRIES (verbatim, 2026-10-16): "yes I would prefer rename to only include
author - title - year format". That word is the narrow YES D-3045 left room for, and this reader is the
PLAN-FIRST limb its gate demands: it writes no name to disk, it renames nothing, and a bare run writes
no file at all.

WHAT THIS ACT IS ALLOWED TO DO, and nothing else:
  * derive a new name ONLY from the file's OWN embedded metadata, in the DECLARED priority order
    (`source_library.name_policy.metadata_priority`: epub OPF, then the PDF info dictionary) - never from
    the filename, because the filename IS the defective handle this act exists to repair;
  * rename ONLY a row that carries NO reference yet (the census's FREE class: no S0.5 cache record is
    keyed to the name), because a rename after the first reference is a CASCADE (BUG-800: 37 corpus stems
    referenced 2,952 times inside 13 run receipts);
  * REFUSE, WITH A PRINTED REASON, every row it may not touch - a coupled name, a metadata-less file, an
    author field that names a tool rather than a person, a name already taken, a declared surface that
    names the file, a kind with no declared metadata source. Every refusal is COUNTED (D-3038: an
    exclusion that is a silence is a defect).

WHY IT REUSES TWO READERS INSTEAD OF WRITING ITS OWN (D-2646, C12): the library walk, the name classes
and the FREE/COUPLED split are `scripts/census_source_names.py`'s subject, and the reference census over
the declared surfaces (sibling files, stage trees, derived artifacts, the store, the metadata cache) is
`scripts/normalise_corpus_names.py`'s subject. This act LOADS both and adds only the name. It restates no
path, pattern, template or threshold of its own, and a control proves that against its own bytes.

Exit: 0 nothing eligible (nothing owed) | 2 ELIGIBLE ROWS the owner may rename (loud, owner-owed - a plan
is a proposal, BUG-457) | 1 FATAL (an unreadable declaration, root, or a plan that would land on a file).
`--plan` writes the plan (a READ of the library plus ONE written file); `--selftest` runs the controls.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import census_source_names as census  # noqa: E402 — the library reader (roots, classes, FREE/COUPLED split)
import normalise_corpus_names as ncn  # noqa: E402 — the declared reference census over the surfaces

from pipeline.book_metadata import (  # noqa: E402 — the door's own comparison key
    sanitize_source_book,
)

POLICY = census.POLICY
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

CONTROL_LABELS = (
    "a_marker_named_file_carrying_author_title_year_of_its_own_is_PLANNED_in_the_owner_format",
    "a_name_the_cache_already_resolves_is_REFUSED_and_its_reason_is_the_T-172_cascade",
    "a_file_with_no_author_or_no_title_in_any_declared_source_is_REFUSED_and_never_named_from_its_filename",
    "an_author_that_is_a_tool_or_a_scanner_is_REFUSED",
    "a_row_whose_proposed_name_is_already_taken_on_disk_is_REFUSED",
    "a_kind_with_no_declared_metadata_source_is_REFUSED_by_name",
    "a_year_absent_from_the_metadata_omits_the_segment_and_is_COUNTED",
    "a_bare_run_writes_NOTHING_and_only_--plan_writes_the_plan",
    "the_planner_names_no_path_pattern_template_or_refusal_of_its_own",
    "the_declared_sanitiser_decodes_an_entity_and_trims_a_dangling_separator",
    "the_planners_readiness_split_equals_the_census_readers_over_the_same_library",
)


class PlanError(SystemExit):
    """Fail-closed: an unreadable declaration or a plan that would land on a file is a fault (C16)."""


def name_policy(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The ONE home of this act's policy (C12): `source_library.name_policy`, read through the census loader."""
    doc = pol or census.policy(POLICY)
    block = (doc.get("source_library") or {}).get("name_policy")
    if not isinstance(block, dict):
        raise PlanError(f"FATAL: {POLICY}#source_library.name_policy is not declared - this act has no declared "
                        f"scope, template or refusal vocabulary (C12)")
    for key in ("template", "metadata_priority", "kind_sources", "sanitiser", "refusals",
                "implausible_author_pattern", "plan_prefix"):
        if key not in block:
            raise PlanError(f"FATAL: {POLICY}#source_library.name_policy.{key} is not declared - an absent key is a "
                            f"fault, never a default (C12/C16)")
    return block


def pattern(declared: dict[str, Any], key: str) -> re.Pattern[str]:
    """Compile a DECLARED pattern; an absent or uncompilable one is fatal rather than skipped (C16)."""
    raw = str(declared.get(key) or "")
    if not raw:
        raise PlanError(f"FATAL: {POLICY} does not declare {key} - a pattern is never invented here (C12)")
    try:
        return re.compile(raw)
    except re.error as exc:
        raise PlanError(f"FATAL: the declared {key} does not compile ({exc})") from exc


def sanitise(text: str, san: dict[str, Any]) -> str:
    """Apply the DECLARED sanitiser to one name segment: NFC, entities, declared chars, collapse, trim, cap."""
    out = unicodedata.normalize(str(san.get("unicode_form") or "NFC"), str(text))
    if san.get("decode_html_entities"):
        out = unescape(out)
    for ch in san.get("drop_characters") or []:
        out = out.replace(str(ch), " ")
    if san.get("collapse_whitespace", True):
        out = re.sub(r"\s+", " ", out)
    sep = str(san.get("separator") or "")
    if sep and san.get("collapse_repeated_separators"):
        # MEASURED 2026-10-16 (the first live plan): an OPF carried "A;; B" - a run of separators is a run, not a
        # list of empty authors, so it collapses to ONE separator, spaced by the declared rule below.
        out = re.sub(rf"{re.escape(sep)}\s*(?:{re.escape(sep)}\s*)+", f"{sep} ", out)
    if sep and san.get("separator_spacing"):
        out = re.sub(rf"{re.escape(sep)}\s*", f"{sep} ", out)
    out = out.strip().strip(str(san.get("trim_trailing") or " "))
    cap = int(san.get("max_segment_chars") or 0)
    if cap and len(out) > cap:
        out = out[:cap].rstrip()
    return out


def epub_metadata(path: Path) -> dict[str, str]:
    """The file's OWN container metadata: the OPF's dc:creator / dc:title / dc:date (no model, no guess)."""
    with zipfile.ZipFile(path) as zf:
        opf = [n for n in zf.namelist() if n.lower().endswith(".opf")]
        if not opf:
            return {}
        doc = zf.read(opf[0]).decode("utf-8", "replace")

    def tag(name: str) -> str:
        hit = re.search(rf"<dc:{name}[^>]*>(.*?)</dc:{name}>", doc, re.S | re.I)
        return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", hit.group(1))).strip() if hit else ""

    creators = re.findall(r"<dc:creator[^>]*>(.*?)</dc:creator>", doc, re.S | re.I)
    authors = "; ".join(a for a in (re.sub(r"\s+", " ", re.sub("<[^>]+>", "", c)).strip() for c in creators) if a)
    date = tag("date")
    year = (re.search(r"(1[5-9]\d{2}|20\d{2})", date) or [""])[0] if date else ""
    return {"author": authors, "title": tag("title"), "year": year}


def pdf_metadata(path: Path) -> dict[str, str]:
    """The file's OWN container metadata: the PDF Info dictionary (author / title / date).

    An unreadable, encrypted or absent dictionary returns {} and the row is REFUSED by name - never renamed
    from what the filename suggests (MEASURED 2026-10-16: 8 of 25 sampled free PDFs carry an EMPTY author and
    title, and one carried the scanning tool's name as its author).
    """
    import fitz  # declared here, not at import time: a missing reader makes ONE kind unreadable, not the act

    with fitz.open(str(path)) as doc:
        info = doc.metadata or {}
    stamp = str(info.get("creationDate") or info.get("modDate") or "")
    year = (re.search(r"(1[5-9]\d{2}|20\d{2})", stamp) or [""])[0] if stamp else ""
    return {"author": str(info.get("author") or "").strip(), "title": str(info.get("title") or "").strip(),
            "year": year}


READERS = {"epub_opf": epub_metadata, "pdf_info": pdf_metadata}


def derive(path: Path, kind: str, policy: dict[str, Any]) -> tuple[dict[str, str], str, str]:
    """The first DECLARED source that supplies both an author and a title, with the source that supplied it.

    Returns (metadata, source_name, refusal_reason). A source that raises is a source this act cannot read:
    it is reported as a refusal WITH its exception, never as an empty row (D-795: absent is not zero).
    """
    source = (policy.get("kind_sources") or {}).get(kind)
    if not source:
        return {}, "", "kind_has_no_declared_metadata_source"
    if str(source) not in (policy.get("metadata_priority") or []):
        raise PlanError(f"FATAL: kind_sources.{kind} names {source!r}, which metadata_priority does not declare - "
                        f"a source outside the declared order is a second policy (C12)")
    reader = READERS.get(str(source))
    if reader is None:
        raise PlanError(f"FATAL: kind_sources.{kind} names {source!r}, which no reader in this act implements")
    try:
        meta = reader(path)
    except Exception as exc:  # noqa: BLE001 — any failure is "this source could not be read", never a guess
        print(f"  note: {path.name[:70]}: {source} unreadable ({type(exc).__name__}) - the row is refused",
              file=sys.stderr)
        return {}, str(source), "no_metadata_in_a_declared_source"
    if meta.get("author") and meta.get("title"):
        return meta, str(source), ""
    return {}, str(source), "no_metadata_in_a_declared_source"


def propose(meta: dict[str, str], policy: dict[str, Any]) -> str:
    """The name the declared template produces from the metadata, sanitiser applied per segment."""
    san = policy.get("sanitiser") or {}
    parts = {"author": sanitise(meta.get("author", ""), san), "title": sanitise(meta.get("title", ""), san),
             "year": sanitise(meta.get("year", ""), san)}
    out = str(policy["template"]).format(**parts)
    out = re.sub(r"\s*-\s*(?=-|$)", "", out)  # a segment the template omitted leaves no dangling separator
    out = re.sub(r"\s{2,}", " ", out).strip().strip("- ").strip()
    cap = int(san.get("max_name_bytes") or 0)
    if cap:
        while len(out.encode("utf-8")) > cap and len(out) > 1:
            out = out[:-1]
        out = out.rstrip()
    return out


def rows_for(pol: dict[str, Any]) -> list[dict[str, Any]]:
    """Every DEFECTIVE library file, with its name classes and its FREE/COUPLED verdict (the census's own)."""
    declared = pol["source_library"]
    patterns = {
        "ingest_site_marker": pattern(declared, "marker_pattern"),
        "spine_or_hash_name": pattern(declared, "spine_pattern"),
        "truncation_suspect": pattern(declared, "truncation_pattern"),
    }
    cache = census.cache_keys(pol)
    rows: list[dict[str, Any]] = []
    for root in census.roots(pol):
        for path in sorted(root["path"].rglob("*")):
            if not path.is_file() or path.suffix.lower() not in root["kinds"] or path.name.startswith("."):
                continue
            classes = census.classify(path.name, patterns)
            if not classes:
                continue
            key = sanitize_source_book(path.stem).strip().lower()
            record = cache.get(key) or {}
            rows.append({
                "path": str(path), "parent": str(path.parent), "name": path.name, "root": root["id"],
                "kind": path.suffix.lower().lstrip("."), "classes": classes,
                "stem_before": path.stem, "key": key, "suffix": path.suffix,
                "coupled": bool(record.get("author") and record.get("title")),
            })
    return rows


def build(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The plan: every eligible row with its derived name, and every refusal with its declared reason."""
    doc = pol or census.policy(POLICY)
    policy = name_policy(doc)
    bad_author = pattern(policy, "implausible_author_pattern")
    rows = rows_for(doc)
    refusals: dict[str, int] = {}
    planned: list[dict[str, Any]] = []
    no_year = 0
    taken: set[str] = set()

    def refuse(declared_reason: str) -> None:
        if declared_reason not in policy["refusals"]:
            raise PlanError(f"FATAL: this act refused a row with reason {declared_reason!r}, which "
                            f"name_policy.refusals does not declare - an undeclared reason is a message, not a "
                            f"policy (C12)")
        refusals[declared_reason] = refusals.get(declared_reason, 0) + 1

    for row in rows:
        if row["coupled"]:
            refuse("already_resolved_by_an_ingest")  # T-172 shape: no file is opened for a coupled row
            continue
        meta, source, reason = derive(Path(row["path"]), row["kind"], policy)
        if reason:
            refuse(reason)
            continue
        if bad_author.search(meta.get("author", "")):
            refuse("author_is_not_an_author")
            continue
        stem = propose(meta, policy)
        if not stem:
            refuse("no_metadata_in_a_declared_source")
            continue
        target = Path(row["parent"]) / (stem + row["suffix"])
        if target.exists() or target.name in taken:
            refuse("proposed_name_already_exists")
            continue
        if not meta.get("year"):
            no_year += 1
        taken.add(target.name)
        planned.append({**row, "stem_after": stem, "target": str(target), "source": source,
                        "author": meta.get("author", ""), "title": meta.get("title", ""),
                        "year": meta.get("year", ""), "bytes": Path(row["path"]).stat().st_size})

    # The REFERENCES limb is the corpus-name act's own census over the SAME declared surfaces (D-2646). It runs
    # last and only over the rows that would otherwise be renamed: a reference in a surface this act cannot rewrite
    # refuses the row (a rename that leaves a dangling reference is a cascade, BUG-798).
    eligible = [{"path": r["path"], "parent": r["parent"], "stem_before": r["stem_before"]} for r in planned]
    refs = {r["path"]: r for r in ncn.references(eligible, ncn._policy(doc))} if eligible else {}
    kept: list[dict[str, Any]] = []
    for row in planned:
        block = refs.get(row["path"]) or {}
        named = {k: (v or {}).get("count") for k, v in block.items()
                 if isinstance(v, dict) and isinstance((v or {}).get("count"), int) and (v or {}).get("count") > 0}
        if named:
            refuse("referenced")
            print(f"  note: {row['name'][:60]} is named by {named} - the row is refused", file=sys.stderr)
            continue
        kept.append(row)

    return {
        "act": "T-176 source-library rename plan",
        "authority": "D-3048",
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner_word": policy.get("owner_word"),
        "template": policy["template"],
        "defective": len(rows),
        "coupled": sum(1 for r in rows if r["coupled"]),
        "eligible": len(kept),
        "planned_rows_without_a_year": no_year,
        "refusals": dict(sorted(refusals.items())),
        "rows": kept,
        "rc": RC_OWNER_OWED if kept else RC_OK,
    }


def render(plan: dict[str, Any]) -> str:
    """The plan as a human reads it: the eligible rows, then every refusal with its declared reason."""
    lines = [
        f"# SOURCE-LIBRARY RENAME PLAN — {plan['generated']}",
        "",
        f"> Authority **D-3048** (owner word {plan['owner_word']}). Template `{plan['template']}`. This file is a",
        "> **plan**: it renames nothing, and the act that applies it is separate, owner-worded and plan-first.",
        "",
        "## What this plan may touch, and what it may not",
        "",
        f"- defective names in the library: **{plan['defective']}**",
        f"- COUPLED to an ingest (a rename here is a re-ingest act, T-172): **{plan['coupled']}**",
        f"- ELIGIBLE now (no reference yet, metadata derived from the file's own container): **{plan['eligible']}**",
        f"- eligible rows whose metadata carries NO year (the year segment is omitted, never invented): "
        f"**{plan['planned_rows_without_a_year']}**",
        "",
        "## Every refusal, with the reason it was declared under",
        "",
        "| reason | rows | what it means |",
        "|---|---|---|",
    ]
    for reason, count in plan["refusals"].items():
        lines.append(f"| `{reason}` | {count} | {reason.replace('_', ' ')} |")
    lines += ["", "## The eligible rows", "",
              "| current name | proposed name | metadata source | bytes |", "|---|---|---|---|"]
    for row in plan["rows"]:
        lines.append(f"| `{row['name']}` | `{row['stem_after']}{row['suffix']}` | {row['source']} | {row['bytes']} |")
    if not plan["rows"]:
        lines.append("| — | — | — | — |")
    lines += ["", "## What this plan does NOT do", "",
              "- it does not rename anything, and it does not write to the library (a bare run writes no file);",
              "- it does not propose a name for a row whose own metadata carries no author or no title;",
              "- it does not touch a COUPLED name: those ride the next ingest window (T-172) or not at all;",
              "- it does not derive a name from a filename, from a model or from a guess.", ""]
    return "\n".join(lines)


def write_plan(plan: dict[str, Any], policy: dict[str, Any], root: Path = _PROJECT_ROOT) -> list[Path]:
    """Write the plan beside its declared prefix: one human file and one machine file (a plan is a READ)."""
    stamp = plan["generated"][:10].replace("-", "")
    prefix = root / str(policy["plan_prefix"])
    md, js = Path(f"{prefix}{stamp}.md"), Path(f"{prefix}{stamp}.json")
    md.write_text(render(plan), encoding="utf-8")
    js.write_text(json.dumps(plan, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return [md, js]


def selftest() -> int:
    """Known-answer controls over a synthetic library, cache and plan (BUG-577/D-492)."""
    import tempfile

    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    def control(label: str, ok: bool, detail: str = "") -> None:
        if not ok:
            mark(label, detail or "control failed")

    base = json.loads(json.dumps(census.policy(POLICY)))
    block = base["source_library"]
    with tempfile.TemporaryDirectory(prefix="source_rename_") as tmp:
        root = Path(tmp) / "lib"
        root.mkdir()
        for name in ("Clean Book.epub", "Tool Author (z-lib.org).epub", "Nameless (z-lib.org).epub",
                     "Coupled (z-lib.org).epub", "Notes (z-lib.org).md", "Taken (z-lib.org).epub",
                     "Out Of Order (z-lib.org).epub"):
            (root / name).write_text("x", encoding="utf-8")
        # a synthetic EPUB carrying its own OPF, and one carrying none
        import zipfile as _zip

        with _zip.ZipFile(root / "Good (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata>"
                                         "<dc:creator>Jane Roe</dc:creator><dc:title>A Good Book</dc:title>"
                                         "<dc:date>2019-04-01</dc:date></metadata></package>")
        with _zip.ZipFile(root / "Coupled (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata>"
                                         "<dc:creator>Jane Roe</dc:creator><dc:title>Coupled</dc:title>"
                                         "</metadata></package>")
        with _zip.ZipFile(root / "Tool Author (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata>"
                                         "<dc:creator>bsmoter</dc:creator><dc:title>Scanned</dc:title>"
                                         "</metadata></package>")
        with _zip.ZipFile(root / "Nameless (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata><dc:title>No Author</dc:title></metadata></package>")
        with _zip.ZipFile(root / "Taken (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata><dc:creator>Jane Roe</dc:creator>"
                                         "<dc:title>A Good Book</dc:title><dc:date>2019</dc:date>"
                                         "</metadata></package>")
        with _zip.ZipFile(root / "Out Of Order (z-lib.org).epub", "w") as zf:
            zf.writestr("META-INF/container.xml", "<container/>")
            zf.writestr("OEBPS/book.opf", "<package><metadata><dc:creator>Jim Poe</dc:creator>"
                                         "<dc:title>No Year</dc:title></metadata></package>")
        cache = Path(tmp) / "book_metadata.jsonl"
        cache.write_text(json.dumps({"source_book": "Coupled.epub", "author": "Jane Roe", "title": "Coupled"}) + "\n",
                         encoding="utf-8")
        block["roots"] = [{"id": "lib", "path": str(root), "kinds": ["epub", "md"]}]
        block["metadata_cache"] = str(cache)
        # The REFERENCE limb belongs to the corpus-name act (whose own selftest exercises it); here the declared
        # surfaces are emptied so this act's controls read the real library never, and the artifacts never.
        base["name_normalisation"]["surfaces"] = {"stage_dir_attrs": [], "artifact_dir_attrs": [],
                                                  "store_db_attrs": [], "store_columns": [], "artifact_suffixes": []}
        plan = build(base)

        by_current = {Path(r["path"]).name: r for r in plan["rows"]}
        good = by_current.get("Good (z-lib.org).epub")
        control(CONTROL_LABELS[0], bool(good) and good["stem_after"] == "Jane Roe - A Good Book - 2019",
                f"planned name was {good and good['stem_after']!r}, expected 'Jane Roe - A Good Book - 2019'")
        control(CONTROL_LABELS[1], plan["refusals"].get("already_resolved_by_an_ingest") == 1
                and "Coupled (z-lib.org).epub" not in by_current,
                "a name the cache resolves was not refused as ingest-coupled")
        control(CONTROL_LABELS[2], "Nameless (z-lib.org).epub" not in by_current
                and plan["refusals"].get("no_metadata_in_a_declared_source", 0) >= 1,
                "a row with no author in any declared source was not refused")
        control(CONTROL_LABELS[3], plan["refusals"].get("author_is_not_an_author") == 1,
                "an author that is a scanner/tool name was not refused")
        control(CONTROL_LABELS[4], plan["refusals"].get("proposed_name_already_exists") == 1,
                "a plan that would land on an existing file was not refused")
        control(CONTROL_LABELS[5], plan["refusals"].get("kind_has_no_declared_metadata_source") == 1,
                "a kind with no declared metadata source was not refused by name")
        control(CONTROL_LABELS[6], plan["planned_rows_without_a_year"] == 1
                and "No Year" in str(by_current.get("Out Of Order (z-lib.org).epub", {}).get("stem_after")),
                "an absent year did not omit the segment, or was not counted")

        # (8) a bare run writes NOTHING: the write has exactly ONE call site, and it is behind --plan. Read from this
        # file's own bytes, and built from pieces so this control cannot match ITS OWN needles (BUG-492's shape: a
        # control that hardcodes the name it forbids matches itself).
        own_lines = Path(__file__).resolve().read_text(encoding="utf-8").splitlines()
        needle = "paths = write_" + "plan("
        calls = [i for i, line in enumerate(own_lines) if needle in line]
        branch = next((i for i, line in enumerate(own_lines) if line.strip().startswith("elif args.plan:")), None)
        control(CONTROL_LABELS[7], len(calls) == 1 and branch is not None and calls[0] > branch,
                f"a bare run could write a plan: call site(s) {calls} vs the --plan branch at {branch}")

        # (9) C12: this act restates no path, template or pattern of its own. The needles are assembled from pieces
        # so this control cannot match its own source (a control that hardcodes what it forbids matches itself).
        own = Path(__file__).resolve().read_text(encoding="utf-8")
        needles = ["~" + "/Library/CloudStorage", "{author} - " + "{title} - {year}", "z-" + "?lib",
                   "annas" + "?-?archive"]
        leaks = [tok for tok in needles if tok in own]
        control(CONTROL_LABELS[8], not leaks, f"the planner restates {leaks} - it names no path, template or "
                                              f"pattern of its own (C12)")

        # (10) the split this act plans on IS the census reader's split over the same library
        rep = census.census(base)
        control(CONTROL_LABELS[10],
                rep["free_to_repair"] == plan["defective"] - plan["coupled"]
                and rep["ingest_coupled"] == plan["coupled"],
                f"the planner's split {plan['defective'] - plan['coupled']}/{plan['coupled']} differs from the "
                f"census reader's {rep['free_to_repair']}/{rep['ingest_coupled']}")

        # (11) the DECLARED sanitiser, seen on the two shapes the live library produced: an HTML entity in the OPF
        # title and an author list whose join left a dangling separator (MEASURED 2026-10-16, the first live plan).
        san = block["name_policy"]["sanitiser"]
        got = sanitise("Bremer, Nadieh; Wu, Shirley; ", san)
        got_title = sanitise("HTML &amp; CSS", san)
        got_run = sanitise("Mustafa Suleyman;Michael Bhaskar;; Michael Bhaskar", san)
        control(CONTROL_LABELS[9],
                got == "Bremer, Nadieh; Wu, Shirley" and got_title == "HTML & CSS"
                and got_run == "Mustafa Suleyman; Michael Bhaskar; Michael Bhaskar",
                f"the sanitiser produced {got!r} / {got_title!r} / {got_run!r}")

    failed = {label for label, _ in failures}
    for label in CONTROL_LABELS:
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    for label, detail in failures:
        print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
    if failures:
        return RC_FATAL
    print(f"selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} controls green")
    return RC_OK


def main(argv: list[str] | None = None) -> int:
    """CLI: (default) the reading | --plan (writes the plan) | --json | --selftest."""
    parser = argparse.ArgumentParser(description="The owner-lane rename plan for the source library (READ-ONLY).")
    parser.add_argument("--plan", action="store_true", help="write the plan (one .md and one .json) - a READ + 1 file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    plan = build()
    policy = name_policy()
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=False))
    elif args.plan:
        paths = write_plan(plan, policy)
        print(f"plan written: {', '.join(str(p) for p in paths)}")
    else:
        print(f"source-rename plan: {plan['defective']} defective | {plan['coupled']} coupled to an ingest | "
              f"{plan['eligible']} ELIGIBLE | {plan['planned_rows_without_a_year']} without a year")
        for reason, count in plan["refusals"].items():
            print(f"  refused {count:5d}  {reason}")
        for row in plan["rows"][:12]:
            print(f"  plan    {row['name'][:58]:58s} -> {row['stem_after'][:54]}{row['suffix']}")
        if len(plan["rows"]) > 12:
            print(f"  ... {len(plan['rows']) - 12} more (--plan writes the full table, --json the machine form)")
    return int(plan["rc"])


if __name__ == "__main__":
    sys.exit(main())
