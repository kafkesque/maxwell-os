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
    "a_work_in_both_homes_with_DIFFERENT_bytes_is_counted_as_DRIFT",
    "a_work_in_both_homes_with_EQUAL_bytes_is_NOT_drift",
    "a_work_in_ONE_home_only_is_counted_as_one_sided_and_never_as_drift",
    "a_work_materialised_twice_inside_one_home_is_counted_as_a_second_materialisation",
    "drift_ABOVE_the_declared_ceiling_is_FATAL_and_a_reading_within_it_is_loud_NOT_fatal",
    "the_arrangement_reader_names_no_home_path_of_its_own",
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


def _digest(path: Path) -> str:
    """SHA-256 of a file's bytes - computed only where two homes hold the same work at the same size."""
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arrangement(pol: dict[str, Any] | None = None, corpus_root: Path | None = None) -> dict[str, Any]:
    """The ARRANGEMENT reading (T-176/D-3048): one work, how many materialisations, and do they agree?

    This is the reading the owner's question ("do books get copied into the S0 tree, and will sorting them into
    topic folders duplicate them?") can be answered with. It counts, through the DOOR'S OWN comparison key:

      * `library_files` / `corpus_files` - what each home holds, by the declared kinds;
      * `keys_in_both` - works that exist in BOTH homes (a second materialisation);
      * `byte_equal` / `byte_different` - of those, how many agree byte-for-byte and how many DISAGREE (drift);
      * `library_only` / `corpus_only` - the honest one-sided counts (a corpus row with no library twin is not drift);
      * `duplicated_within_a_home` - one key materialised MORE THAN ONCE in the SAME home.

    A work whose bytes disagree between two homes is DRIFT, and it is counted rather than argued (a copy is not a
    view: two files that were equal the day they were made are two files the day after). rc 2 = drift present and
    above the declared ceiling (loud, owner-owed, BUG-457); 1 = FATAL (an undeclared or unreadable home).
    """
    doc = pol or policy()
    declared = (doc.get("source_library") or {}).get("arrangement")
    if not isinstance(declared, dict):
        raise CensusError(f"FATAL: {POLICY}#source_library.arrangement is not declared - the homes this reading "
                          f"compares are a declaration, never a guess (C12)")
    home = str(declared.get("corpus_home") or "")
    if not home:
        raise CensusError(f"FATAL: {POLICY}#source_library.arrangement.corpus_home is not declared (C12)")
    corpus = Path(corpus_root) if corpus_root else (_PROJECT_ROOT / home)
    if not corpus.is_dir():
        raise CensusError(f"FATAL: the declared corpus home does not exist: {corpus} (D-795: absent is not zero)")

    def index(base: Path, kinds: set[str] | None) -> dict[str, list[Path]]:
        out: dict[str, list[Path]] = {}
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            if kinds is not None and path.suffix.lower() not in kinds:
                continue
            out.setdefault(sanitize_source_book(path.stem).strip().lower(), []).append(path)
        return out

    library: dict[str, list[Path]] = {}
    for root in roots(doc):
        for key, paths in index(root["path"], root["kinds"]).items():
            library.setdefault(key, []).extend(paths)
    corpora = index(corpus, None)

    both = sorted(set(library) & set(corpora))
    equal, different, pairs_only = 0, [], 0
    for key in both:
        shared = {p.suffix.lower() for p in library[key]} & {p.suffix.lower() for p in corpora[key]}
        if not shared:
            # The same work in two CONTAINERS (an .epub and the .md converted from it) can never be byte-equal.
            # Counting that as drift would be a false positive of the kind this repository refuses: the two files
            # are not two copies of one artefact, they are one work in two formats (MEASURED 2026-10-16: the naive
            # same-key reading called 826 works drifted, while the kind-matched reading is the number below).
            pairs_only += 1
            continue
        agrees = any(
            a.suffix.lower() == b.suffix.lower() and a.stat().st_size == b.stat().st_size and _digest(a) == _digest(b)
            for a in library[key] for b in corpora[key])
        if agrees:
            equal += 1
        else:
            different.append(key)
    # ONE WORK, HOW MANY FILES: grouped by KIND, because the format axis legitimately holds one file per kind.
    within: dict[str, int] = {}
    for key, paths in library.items():
        seen: dict[str, int] = {}
        for path in paths:
            seen[path.suffix.lower()] = seen.get(path.suffix.lower(), 0) + 1
        within[key] = max(seen.values())
    twice = {k: n for k, n in within.items() if n > 1}
    twice_corpus = {k: len(v) for k, v in corpora.items() if len(v) > 1}
    ceiling = declared.get("drift_ceiling")
    return {
        "library_files": sum(len(v) for v in library.values()),
        "corpus_files": sum(len(v) for v in corpora.values()),
        "corpus_home": str(corpus),
        "keys_in_both": len(both),
        "byte_equal": equal,
        "byte_different": len(different),
        "drift_examples": different[:5],
        "format_pairs_only": pairs_only,
        "library_only": len(set(library) - set(corpora)),
        "corpus_only": len(set(corpora) - set(library)),
        "same_kind_twice_in_the_library": len(twice),
        "same_kind_twice_in_the_corpus": len(twice_corpus),
        "drift_ceiling": ceiling if isinstance(ceiling, int) else None,
        # THE RULING, in one place: no drift is rc 0; drift WITHIN the declared ceiling is rc 2 (owner-owed, loud,
        # NOT fatal - BUG-457); drift ABOVE it is FATAL, because the ceiling is SHRINK-ONLY (D-3023/D-2644) and a
        # reading that grows past it means a disposition REGRESSED. A ceiling that could not fire would be a comment.
        "rc": (RC_OK if not different else
               RC_FATAL if isinstance(ceiling, int) and len(different) > ceiling else
               RC_OWNER_OWED),
    }


def report_arrangement(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the arrangement reading: two homes, one work, how many files, and how far they have drifted apart."""
    print(f"arrangement: {rep['library_files']} library file(s) vs {rep['corpus_files']} in the bytes home "
          f"({rep['corpus_home']})", file=stream)
    print(f"  the same work in BOTH homes: {rep['keys_in_both']} | agreeing byte-for-byte {rep['byte_equal']} | "
          f"DRIFTED (same kind, different bytes) {rep['byte_different']} (ceiling {rep['drift_ceiling']}) | "
          f"one work in two containers (never byte-equal, NOT drift): {rep['format_pairs_only']}", file=stream)
    print(f"  one home only: library {rep['library_only']} | corpus {rep['corpus_only']}", file=stream)
    print(f"  one work as TWO files of the SAME kind: library {rep['same_kind_twice_in_the_library']} | "
          f"corpus {rep['same_kind_twice_in_the_corpus']}  <- this is what a topic COPY would create", file=stream)
    for key in rep["drift_examples"]:
        print(f"    e.g. {key[:110]}", file=stream)


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

        # ── the ARRANGEMENT reading (T-176/D-3048), over two synthetic homes ─────────────────────────────────
        corpus_root = Path(tmp) / "corpus"
        corpus_root.mkdir(parents=True)
        (root / "Same Work.epub").write_text("identical", encoding="utf-8")
        (corpus_root / "Same Work.epub").write_text("identical", encoding="utf-8")
        (root / "Drifted Work.epub").write_text("one version", encoding="utf-8")
        (corpus_root / "Drifted Work.epub").write_text("a DIFFERENT version", encoding="utf-8")
        (root / "Format Pair.epub").write_text("container one", encoding="utf-8")
        (corpus_root / "Format Pair.md").write_text("container two", encoding="utf-8")
        (root / "Library Only.epub").write_text("x", encoding="utf-8")
        (corpus_root / "Corpus Only.md").write_text("x", encoding="utf-8")
        (root / "Dup.epub").write_text("x", encoding="utf-8")           # the same work, twice in ONE home
        (root / "sub").mkdir()
        (root / "sub" / "Dup.epub").write_text("x", encoding="utf-8")
        block = pol["source_library"]
        block["arrangement"] = {"corpus_home": "corpus", "drift_ceiling": 0}
        arr = arrangement(pol, corpus_root=corpus_root)
        if arr["byte_different"] != 1 or not arr.get("drift_examples"):
            mark(CONTROL_LABELS[5], f"drift counted {arr['byte_different']}, expected 1 (and to be named)")
        if arr["byte_equal"] != 1 or arr["format_pairs_only"] != 1:
            mark(CONTROL_LABELS[6], f"an equal pair counted as drift, or a format pair counted as drift "
                                    f"(byte_equal={arr['byte_equal']}, format_pairs_only={arr['format_pairs_only']}, "
                                    f"expected 1/1)")
        if arr["library_only"] < 2 or arr["corpus_only"] != 1:
            mark(CONTROL_LABELS[7], f"one-sided counts were {arr['library_only']}/{arr['corpus_only']}, expected >=2/1")
        if arr["same_kind_twice_in_the_library"] != 1 or arr["same_kind_twice_in_the_corpus"] != 0:
            mark(CONTROL_LABELS[8],
                 f"a key materialised twice inside one home was not counted "
                 f"({arr['duplicated_within_the_library']}/{arr['duplicated_within_the_corpus']})")
        leaked = [tok for tok in ("~" + "/Library/CloudStorage", "knowledge " + "pipeline/books") if tok in own]
        if leaked:
            mark(CONTROL_LABELS[10], f"the reader restates a home path of its own: {leaked}")

        # (10) the CEILING fires: 1 drifting pair against a ceiling of 0 is FATAL; within its ceiling it is loud
        # and NOT fatal - the same pair of readings BUG-457 draws, seen in BOTH directions.
        if arr["rc"] != RC_FATAL:
            mark(CONTROL_LABELS[9], f"drift above a ceiling of 0 read rc {arr['rc']}, expected the FATAL code")
        block["arrangement"]["drift_ceiling"] = 5
        within = arrangement(pol, corpus_root=corpus_root)
        if within["rc"] != RC_OWNER_OWED:
            mark(CONTROL_LABELS[9], f"drift within its ceiling read rc {within['rc']}, expected OWNER-OWED")
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
    """CLI: (default) the name census | --arrangement | --json | --selftest."""
    parser = argparse.ArgumentParser(description="The owner's source library, read as a name census (read-only).")
    parser.add_argument("--census", action="store_true", help="the name census (the default reading)")
    parser.add_argument("--arrangement", action="store_true",
                        help="the ARRANGEMENT reading: one work, how many materialisations, and their drift")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    try:
        rep = arrangement() if args.arrangement else census()
    except CensusError as exc:
        print(str(exc), file=sys.stderr)
        return RC_FATAL
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    elif args.arrangement:
        report_arrangement(rep)
    else:
        report(rep)
    return int(rep["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
