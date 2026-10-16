#!/usr/bin/env python3
"""census_source_names.py — the OWNER's source library, read as a census (READ-ONLY, owner lane).

THE QUESTION THIS ANSWERS (owner, 2026-10-16): "in EPUB or PDF or any other format, before S0, if there are
duplicates but with a truncated name missing author or title (or both) while the file TEXT contains it — would it
be easier before conversion, or should books and journal filenames be normalised in the attached folder so we
avoid a future tax and do not overcomplicate S0?"

THE ANSWER THIS MEASUREMENT SUPPORTS, in three parts:
  1. A NAME IS EVIDENCE, NEVER IDENTITY. The pipeline already derives author/title from the FILE'S OWN TEXT at S0.5
     (`pipeline/stage0_5_extract_metadata.py`, cached in the checkpoint metadata JSONL) and the door compares names
     through `sanitize_source_book().strip().lower()` (pipeline/book_metadata.py). MEASURED 2026-10-16: 952 of 962
     cached records carry BOTH author and title, including 104 whose file names are mirror-spelled spines. So a
     truncated or mirror-spelled name costs NO identity: it is a human HANDLE, and S0 does not need a renamer.
  2. A RENAME IS CHEAPEST BEFORE THE FIRST REFERENCE. A name repaired before the file is ingested has ZERO
     references to carry; the same repair AFTER ingest is a cascade — MEASURED 2026-10-15 (BUG-800): 37 defective
     corpus stems were referenced 2,952 times inside 13 already-written run receipts, which is why the approved
     repair (T-172) must ride a re-ingest. So: repair at the SOURCE, and only while the file is un-ingested.
  3. THEREFORE THE RECOMMENDATION IS NOT "normalise the library by hand". It is: (a) keep the name authority where
     it is (content-derived metadata + the door key), (b) treat any source-side rename as a PLAN-FIRST, owner-lane
     act that REFUSES on an already-ingested name, and (c) never let a name become a key by accident. This census
     produces the three numbers that decision needs: what the name defects are, how many are still repairable for
     free (no corpus/cache counterpart yet), and how many are already coupled to an ingest.

WHAT IT READS (all declared, C12): `config/ingest_identity_gate.yaml#source_library` names the roots, the file
kinds and the cache it joins against; every path is written '~...' and never mirrored (D-3034). It writes NOTHING.

Exit: 0 no name debt | 1 FATAL (an unreadable or undeclared root, an unreadable cache) | 2 name debt present --
loud, owner-owed, never fatal (BUG-457) | --selftest 0/1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.book_metadata import sanitize_source_book  # noqa: E402 — the door's own key (D-2176)

POLICY = Path("config/ingest_identity_gate.yaml")
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

CONTROL_LABELS = (
    "a_mirror_marker_name_is_counted_in_the_marker_class",
    "a_truncated_name_is_NOT_counted_as_a_marker",
    "an_unreadable_root_is_FATAL_and_never_a_zero",
    "a_name_that_the_cache_already_resolves_is_counted_as_ingest_coupled",
    "the_census_reads_its_roots_from_the_declaration_and_names_none_of_its_own",
)


class CensusError(SystemExit):
    """Fail-closed: an unreadable declaration or root is a fault, never a silent zero (C16/D-795)."""


def policy(path: Path = POLICY) -> dict[str, Any]:
    """Read the one home. Unreadable is FATAL (C16); nothing is defaulted."""
    import yaml

    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — any failure means this census cannot know anything
        raise CensusError(f"FATAL: {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(doc, dict) or "source_library" not in doc:
        raise CensusError(f"FATAL: {path}#source_library is not declared — the roots a census may read are a "
                          f"declaration, never a guess (C12)")
    return doc


def roots(pol: dict[str, Any]) -> list[dict[str, Any]]:
    """The declared roots, each validated: an undeclared or unreadable root is FATAL (D-795)."""
    declared = pol["source_library"].get("roots")
    if not isinstance(declared, list) or not declared:
        raise CensusError(f"FATAL: {POLICY}#source_library.roots must be a non-empty list")
    out: list[dict[str, Any]] = []
    for entry in declared:
        for key in ("id", "path", "kinds"):
            if key not in entry:
                raise CensusError(f"FATAL: the declared root {entry.get('id')!r} does not declare {key!r}")
        path = Path(str(entry["path"])).expanduser()
        if not path.exists():
            raise CensusError(f"FATAL: the declared root {entry['id']} does not exist: {path} — an absent root is "
                              f"a fault, never a count of zero (D-795)")
        out.append({"id": str(entry["id"]), "path": path,
                    "kinds": {f".{str(k).lower().lstrip('.')}" for k in entry["kinds"]}})
    return out


def cache_keys(pol: dict[str, Any]) -> dict[str, dict[str, str]]:
    """The S0.5 metadata cache, keyed by the door's OWN comparison key, with its derived author/title.

    This join is the whole answer to "the name is truncated but the text has it": if the cache already resolves a
    record for that file, the content-derived identity EXISTS and the name carries nothing the pipeline needs.
    """
    rel = str(pol["source_library"].get("metadata_cache") or "")
    if not rel:
        raise CensusError(f"FATAL: {POLICY}#source_library.metadata_cache is not declared (C12)")
    path = Path(rel)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    if not path.exists():
        raise CensusError(f"FATAL: the declared metadata cache does not exist: {path} (C16)")
    out: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = str(row.get("source_book") or row.get("source_file") or "")
        if not name:
            continue
        out[sanitize_source_book(Path(name).stem).strip().lower()] = {
            "author": str(row.get("author") or "").strip(), "title": str(row.get("title") or "").strip()}
    return out


def classify(name: str, patterns: dict[str, re.Pattern[str]]) -> list[str]:
    """Every declared name class this stem matches, by the DECLARED patterns (never a pattern of our own)."""
    stem = Path(name).stem
    return sorted(label for label, pattern in patterns.items() if pattern.search(stem))


def census(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """Walk the declared roots and return the class counts, the join against the cache, and the readiness split."""
    pol = pol or policy()
    declared = pol["source_library"]
    marker = re.compile(str(declared["marker_pattern"]))
    patterns = {
        "ingest_site_marker": marker,
        "spine_or_hash_name": re.compile(str(declared["spine_pattern"])),
        "truncation_suspect": re.compile(str(declared["truncation_pattern"])),
    }
    cache = cache_keys(pol)
    rows: list[dict[str, Any]] = []
    for root in roots(pol):
        for path in sorted(root["path"].rglob("*")):
            if not path.is_file() or path.suffix.lower() not in root["kinds"] or path.name.startswith("."):
                continue
            key = sanitize_source_book(path.stem).strip().lower()
            resolved = cache.get(key)
            rows.append({
                "root": root["id"], "name": path.name,
                "classes": classify(path.name, patterns),
                "cache_resolved": bool(resolved and resolved["author"] and resolved["title"]),
                "cache_resolution": resolved or {},
            })
    classes: dict[str, int] = {label: 0 for label in patterns}
    for row in rows:
        for label in row["classes"]:
            classes[label] += 1
    defective = [row for row in rows if row["classes"]]
    return {
        "files": len(rows),
        "classes": classes,
        "defective": len(defective),
        # FREE TO REPAIR: defective, and the cache cannot resolve its identity yet -> a rename here carries no
        # reference. COUPLED: the cache already holds a record keyed to this name, so a rename is a re-ingest act
        # (T-172's shape: the references already exist downstream).
        "free_to_repair": sum(1 for row in defective if not row["cache_resolved"]),
        "ingest_coupled": sum(1 for row in defective if row["cache_resolved"]),
        "cache_resolved_any": sum(1 for row in rows if row["cache_resolved"]),
        "cache_records": len(cache),
        "per_root": {root["id"]: sum(1 for row in rows if row["root"] == root["id"]) for root in roots(pol)},
        "examples": [row["name"] for row in defective[:8]],
        "rc": RC_OWNER_OWED if defective else RC_OK,
    }


def report(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the census in the units the decision needs (no counts invented, none omitted)."""
    print(f"source library: {rep['files']} file(s) in {len(rep['per_root'])} declared root(s) {rep['per_root']}",
          file=stream)
    print(f"  name classes: {rep['classes']} | defective {rep['defective']}", file=stream)
    print(f"  identity is CONTENT-derived: {rep['cache_resolved_any']} of {rep['files']} resolve author+title from "
          f"the S0.5 cache ({rep['cache_records']} record(s))", file=stream)
    print(f"  repair readiness: {rep['free_to_repair']} FREE (no record keyed to the name yet), "
          f"{rep['ingest_coupled']} COUPLED to an ingest (a rename there is a re-ingest act, T-172)", file=stream)
    for name in rep["examples"]:
        print(f"    e.g. {name[:110]}", file=stream)


def selftest() -> int:
    """Known-answer controls over synthetic roots and a synthetic cache in a temp dir (BUG-577)."""
    import tempfile

    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    base = json.loads(json.dumps({
        "source_library": {
            "roots": [{"id": "lib", "path": "", "kinds": ["epub", "pdf"]}],
            "metadata_cache": "",
            "marker_pattern": r"(?i)\b(z-lib|annas?-?archive|1lib)\b",
            "spine_pattern": r"\s--\s|\b[0-9a-f]{16,}\b",
            "truncation_pattern": r"_$|\($|\band\s*$",
        }}))
    with tempfile.TemporaryDirectory(prefix="source_names_") as tmp:
        root = Path(tmp) / "lib"
        root.mkdir()
        (root / "A Book (z-lib.org).pdf").write_text("x", encoding="utf-8")
        (root / "Truncated Title and.pdf").write_text("x", encoding="utf-8")
        (root / "Clean Book.epub").write_text("x", encoding="utf-8")
        cache = Path(tmp) / "book_metadata.jsonl"
        cache.write_text(json.dumps({"source_book": "A Book.pdf", "author": "Jane Roe", "title": "A Book"}) + "\n",
                         encoding="utf-8")
        pol = base
        pol["source_library"]["roots"][0]["path"] = str(root)
        pol["source_library"]["metadata_cache"] = str(cache)
        rep = census(pol)
        if rep["classes"]["ingest_site_marker"] != 1:
            mark(CONTROL_LABELS[0], f"marker class counted {rep['classes']['ingest_site_marker']}, expected 1")
        if rep["classes"]["ingest_site_marker"] != 1 or not rep["classes"]["truncation_suspect"]:
            mark(CONTROL_LABELS[1], "the truncation class was not counted separately from the marker class")
        if rep["classes"]["truncation_suspect"] < 1:
            mark(CONTROL_LABELS[1], "a truncated name was not counted at all")
        if rep["classes"].get("ingest_site_marker", 0) > 1:
            mark(CONTROL_LABELS[1], "the truncation fixture leaked into the marker class")

        gone = json.loads(json.dumps(pol))
        gone["source_library"]["roots"][0]["path"] = str(Path(tmp) / "nope")
        try:
            census(gone)
            mark(CONTROL_LABELS[2], "an ABSENT root did not raise (a blind census read as clean)")
        except CensusError:
            pass

        if rep["ingest_coupled"] != 1 or rep["free_to_repair"] != 1:
            mark(CONTROL_LABELS[3],
                 f"readiness split was free={rep['free_to_repair']} coupled={rep['ingest_coupled']}, expected 1/1")

        own = Path(__file__).resolve().read_text(encoding="utf-8")
        if re.search(r"['\"]~/", own):
            mark(CONTROL_LABELS[4], "the census restates a root path of its own")
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
    """CLI: (default) the census | --json | --selftest."""
    parser = argparse.ArgumentParser(description="The owner's source library, read as a name census (read-only).")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    try:
        rep = census()
    except CensusError as exc:
        print(str(exc), file=sys.stderr)
        return RC_FATAL
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        report(rep)
    return int(rep["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
