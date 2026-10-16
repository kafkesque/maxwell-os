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

  4. PLACEMENT (T-180/D-3049). The owner asked (2026-10-16) how to keep books and notes in the right folders.
     "Organised" is a judgement until PLACED is declared, so the placement of the two roots is declared in the SAME
     home as everything else here: an AXIS per root (kind for books - format decides how a file is READ - and domain
     for journals:notes, whose vocabulary is read from its ONE materialisation, the corpus home) plus the arrival
     pens. This reading then COUNTS and never moves: the files whose kind the root does not admit, the files loose at
     a root, the subfolders the declared axis does not name, and every declared arrival pen - how much is waiting,
     how old it is, and how much of it the pipeline has NEVER SEEN (the door's own new_file_definition, reused).

Exit: 0 no name debt | 1 FATAL (an unreadable or undeclared root, an unreadable cache, an undeclared placement) |
2 name debt or a waiting arrival present -- loud, owner-owed, never fatal (BUG-457) | --selftest 0/1.
Readings: (default) the name census | --arrangement | --placement | --brief (ONE line for the ladder).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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
    "a_file_the_declared_roots_do_not_admit_is_counted_as_MISPLACED_and_named",
    "a_file_loose_at_a_root_whose_axis_requires_a_subfolder_is_counted",
    "a_subfolder_the_declared_axis_does_not_name_is_counted_as_OUTSIDE_the_declaration",
    "a_file_waiting_in_a_declared_ARRIVAL_PEN_is_counted_while_a_STALE_one_is_counted_apart",
    "the_placement_reader_names_no_root_pen_or_path_of_its_own",
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
        raise CensusError(
            f"FATAL: {path}#source_library is not declared — the roots a census may read are a "
            f"declaration, never a guess (C12)"
        )
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
                raise CensusError(
                    f"FATAL: the declared root {entry.get('id')!r} does not declare {key!r}"
                )
        path = Path(str(entry["path"])).expanduser()
        if not path.exists():
            raise CensusError(
                f"FATAL: the declared root {entry['id']} does not exist: {path} — an absent root is "
                f"a fault, never a count of zero (D-795)"
            )
        out.append(
            {
                "id": str(entry["id"]),
                "path": path,
                "kinds": {f".{str(k).lower().lstrip('.')}" for k in entry["kinds"]},
            }
        )
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
            "author": str(row.get("author") or "").strip(),
            "title": str(row.get("title") or "").strip(),
        }
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
            if (
                not path.is_file()
                or path.suffix.lower() not in root["kinds"]
                or path.name.startswith(".")
            ):
                continue
            key = sanitize_source_book(path.stem).strip().lower()
            resolved = cache.get(key)
            rows.append(
                {
                    "root": root["id"],
                    "name": path.name,
                    "classes": classify(path.name, patterns),
                    "cache_resolved": bool(resolved and resolved["author"] and resolved["title"]),
                    "cache_resolution": resolved or {},
                }
            )
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
        "per_root": {
            root["id"]: sum(1 for row in rows if row["root"] == root["id"]) for root in roots(pol)
        },
        "examples": [row["name"] for row in defective[:8]],
        "rc": RC_OWNER_OWED if defective else RC_OK,
    }


def report(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the census in the units the decision needs (no counts invented, none omitted)."""
    print(
        f"source library: {rep['files']} file(s) in {len(rep['per_root'])} declared root(s) {rep['per_root']}",
        file=stream,
    )
    print(f"  name classes: {rep['classes']} | defective {rep['defective']}", file=stream)
    print(
        f"  identity is CONTENT-derived: {rep['cache_resolved_any']} of {rep['files']} resolve author+title from "
        f"the S0.5 cache ({rep['cache_records']} record(s))",
        file=stream,
    )
    print(
        f"  repair readiness: {rep['free_to_repair']} FREE (no record keyed to the name yet), "
        f"{rep['ingest_coupled']} COUPLED to an ingest (a rename there is a re-ingest act, T-172)",
        file=stream,
    )
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


def arrangement(
    pol: dict[str, Any] | None = None, corpus_root: Path | None = None
) -> dict[str, Any]:
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
        raise CensusError(
            f"FATAL: {POLICY}#source_library.arrangement is not declared - the homes this reading "
            f"compares are a declaration, never a guess (C12)"
        )
    home = str(declared.get("corpus_home") or "")
    if not home:
        raise CensusError(
            f"FATAL: {POLICY}#source_library.arrangement.corpus_home is not declared (C12)"
        )
    corpus = Path(corpus_root) if corpus_root else (_PROJECT_ROOT / home)
    if not corpus.is_dir():
        raise CensusError(
            f"FATAL: the declared corpus home does not exist: {corpus} (D-795: absent is not zero)"
        )

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
            a.suffix.lower() == b.suffix.lower()
            and a.stat().st_size == b.stat().st_size
            and _digest(a) == _digest(b)
            for a in library[key]
            for b in corpora[key]
        )
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
        "rc": (
            RC_OK
            if not different
            else RC_FATAL
            if isinstance(ceiling, int) and len(different) > ceiling
            else RC_OWNER_OWED
        ),
    }


def report_arrangement(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the arrangement reading: two homes, one work, how many files, and how far they have drifted apart."""
    print(
        f"arrangement: {rep['library_files']} library file(s) vs {rep['corpus_files']} in the bytes home "
        f"({rep['corpus_home']})",
        file=stream,
    )
    print(
        f"  the same work in BOTH homes: {rep['keys_in_both']} | agreeing byte-for-byte {rep['byte_equal']} | "
        f"DRIFTED (same kind, different bytes) {rep['byte_different']} (ceiling {rep['drift_ceiling']}) | "
        f"one work in two containers (never byte-equal, NOT drift): {rep['format_pairs_only']}",
        file=stream,
    )
    print(
        f"  one home only: library {rep['library_only']} | corpus {rep['corpus_only']}", file=stream
    )
    print(
        f"  one work as TWO files of the SAME kind: library {rep['same_kind_twice_in_the_library']} | "
        f"corpus {rep['same_kind_twice_in_the_corpus']}  <- this is what a topic COPY would create",
        file=stream,
    )
    for key in rep["drift_examples"]:
        print(f"    e.g. {key[:110]}", file=stream)


def axis_vocabulary(pol: dict[str, Any], corpus_root: Path) -> dict[str, set[str]]:
    """The subfolder names each declared axis ADMITS, read from the homes that already own them (C12, never restated).

    kind   -> the file extensions the DECLARATION admits (roots[].kinds, lower-cased, without the leading dot);
    domain -> the DOMAIN names the CORPUS materialises (its own immediate subdirectories), which is the pipeline's
              ONE materialisation of the topic vocabulary (D-3048) - so this reading keeps no second list of it.
    """
    kinds: set[str] = set()
    for root in roots(pol):
        kinds |= {k.lstrip(".") for k in root["kinds"]}
    domains: set[str] = set()
    if corpus_root.is_dir():
        domains = {
            p.name
            for p in sorted(corpus_root.iterdir())
            if p.is_dir() and not p.name.startswith(".")
        }
    return {"kind": kinds, "domain": domains}


def placement(pol: dict[str, Any] | None = None, corpus_root: Path | None = None) -> dict[str, Any]:
    """The PLACEMENT reading (T-180/D-3049): where a file IS, against where the declaration says it BELONGS.

    A file cannot be MISPLACED until PLACED is declared, so this reader reads its own policy (axes, homes, pens, age
    budgets) from config/ingest_identity_gate.yaml#source_library.placement and reports, with counts and examples:

      * inside each declared root: the files whose KIND the root does not admit, the files LOOSE at the root where
        the declared axis requires a subfolder, and the subfolders the declared axis does not name;
      * every declared ARRIVAL PEN: how many files, how many bytes, how many of a declared kind, the OLDEST age in
        days, how many are past the declared age budget, and how many the S0.5 cache cannot resolve (i.e. the
        pipeline has NEVER SEEN them - the door's own definition of a new file, reused and never restated);
      * the siblings of the declared roots that are neither a root nor a pen: NAMED and never walked, because
        walking one would be this reading quietly widening its own domain, which is the defect it reports.

    It MOVES NOTHING. rc 2 = something waiting or misplaced (loud, owner-owed, BUG-457); 1 = FATAL: an undeclared
    home/axis/pen, a missing age budget, or an absent pen (D-795/D-3034 - absent is never zero).
    """
    doc = pol or policy()
    declared = (doc.get("source_library") or {}).get("placement")
    if not isinstance(declared, dict):
        raise CensusError(
            f"FATAL: {POLICY}#source_library.placement is not declared - a file cannot be MISPLACED "
            f"until PLACED is declared (C12/D-3049)"
        )
    homes, pens = declared.get("homes"), declared.get("pens")
    if not isinstance(homes, dict) or not homes:
        raise CensusError(
            f"FATAL: {POLICY}#source_library.placement.homes must be a non-empty mapping (C16)"
        )
    if not isinstance(pens, dict) or not pens:
        raise CensusError(
            f"FATAL: {POLICY}#source_library.placement.pens must be a non-empty mapping - an "
            f"undeclared arrival pen is a silence, not an empty queue (C12/D-3038)"
        )
    corpus_home = str((doc["source_library"].get("arrangement") or {}).get("corpus_home") or "")
    if not corpus_home:
        raise CensusError(
            f"FATAL: {POLICY}#source_library.arrangement.corpus_home is not declared, so the DOMAIN "
            f"vocabulary has no home to be read from (C12)"
        )
    corpus = Path(corpus_root) if corpus_root else (_PROJECT_ROOT / corpus_home)
    vocab = axis_vocabulary(doc, corpus)
    cache = cache_keys(doc)

    per_root: dict[str, dict[str, Any]] = {}
    misplaced_examples: list[str] = []
    loose_examples: list[str] = []
    undeclared: dict[str, int] = {}
    files = admitted = misplaced = loose = 0
    for root in roots(doc):
        row = homes.get(root["id"])
        if not isinstance(row, dict):
            raise CensusError(
                f"FATAL: the declared root {root['id']!r} has no row under placement.homes - a root "
                f"the declaration does not place cannot be read (D-3034)"
            )
        axis = str(row.get("axis") or "")
        if axis not in vocab:
            raise CensusError(
                f"FATAL: placement.homes.{root['id']}.axis declares {axis!r}, which is neither of "
                f"{sorted(vocab)} (D-3034)"
            )
        if not isinstance(row.get("subfolder_required"), bool):
            raise CensusError(
                f"FATAL: placement.homes.{root['id']} does not declare subfolder_required (C16)"
            )
        counts = {
            "files": 0,
            "admitted": 0,
            "misplaced_kind": 0,
            "loose_at_root": 0,
            "undeclared_subfolders": 0,
        }
        for path in sorted(root["path"].rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            counts["files"] += 1
            if path.suffix.lower() in root["kinds"]:
                counts["admitted"] += 1
            else:
                # A file this root does not admit AT ALL (a cover, a spreadsheet, a stray archive): counted, named,
                # and never touched - the reading reports it and T-180 disposes of it.
                counts["misplaced_kind"] += 1
                if len(misplaced_examples) < 5:
                    misplaced_examples.append(f"{root['id']}/{path.name}"[:90])
            rel = path.relative_to(root["path"]).parts
            if len(rel) == 1:
                counts["loose_at_root"] += 1
                if len(loose_examples) < 5:
                    loose_examples.append(f"{root['id']}/{path.name}"[:90])
            elif rel[0] not in vocab[axis]:
                counts["undeclared_subfolders"] += 1
                undeclared[rel[0]] = undeclared.get(rel[0], 0) + 1
        per_root[root["id"]] = counts
        files += counts["files"]
        admitted += counts["admitted"]
        misplaced += counts["misplaced_kind"]
        loose += counts["loose_at_root"]

    admitted_kinds: set[str] = set()
    for root in roots(doc):
        admitted_kinds |= root["kinds"]
    now = time.time()
    pen_rows: list[dict[str, Any]] = []
    for pid, pen in sorted(pens.items()):
        if not isinstance(pen, dict) or not str(pen.get("path") or ""):
            raise CensusError(f"FATAL: placement.pens.{pid} declares no path (C16)")
        budget = pen.get("staleness_days")
        if not isinstance(budget, int) or isinstance(budget, bool):
            raise CensusError(
                f"FATAL: placement.pens.{pid} declares no integer staleness_days - a queue with no age "
                f"budget can never be stale (C12/D-2644)"
            )
        path = Path(str(pen["path"])).expanduser()
        if not path.is_dir():
            raise CensusError(
                f"FATAL: the declared arrival pen {pid} does not exist: {path} - an absent pen is a "
                f"fault and never a count of zero (D-795)"
            )
        row = {
            "id": pid,
            "path": str(path),
            "files": 0,
            "bytes": 0,
            "books_or_notes": 0,
            "other": 0,
            "oldest_days": 0,
            "stale": 0,
            "unseen": 0,
            "examples": [],
        }
        for entry in sorted(path.rglob("*")):
            if not entry.is_file() or entry.name.startswith("."):
                continue
            info = entry.stat()
            row["files"] += 1
            row["bytes"] += info.st_size
            if entry.suffix.lower() in admitted_kinds:
                row["books_or_notes"] += 1
            else:
                row["other"] += 1
            age = int((now - info.st_mtime) // 86400)
            row["oldest_days"] = max(row["oldest_days"], age)
            if age > budget:
                row["stale"] += 1
            if sanitize_source_book(entry.stem).strip().lower() not in cache:
                row["unseen"] += 1
                if len(row["examples"]) < 3:
                    row["examples"].append(entry.name[:80])
        pen_rows.append(row)

    siblings: list[str] = []
    parents = {root["path"].parent for root in roots(doc)}
    if len(parents) == 1:
        parent = next(iter(parents))
        placed = {root["path"].name for root in roots(doc)}
        placed |= {
            Path(str(p["path"])).expanduser().name for p in pens.values() if isinstance(p, dict)
        }
        siblings = sorted(
            p.name
            for p in parent.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name not in placed
        )
    waiting = sum(row["files"] for row in pen_rows)
    undeclared_files = sum(row["undeclared_subfolders"] for row in per_root.values())
    return {
        "files": files,
        "admitted": admitted,
        "per_root": per_root,
        "misplaced": misplaced,
        "misplaced_examples": misplaced_examples,
        "loose_at_root": loose,
        "loose_examples": loose_examples,
        "undeclared_subfolders": undeclared,
        "undeclared_subfolder_files": undeclared_files,
        "siblings_outside_the_declaration": siblings,
        "pens": pen_rows,
        "waiting": waiting,
        "stale": sum(row["stale"] for row in pen_rows),
        "unseen": sum(row["unseen"] for row in pen_rows),
        "vocabulary": {axis: len(names) for axis, names in vocab.items()},
        "rc": (
            RC_OWNER_OWED
            if (waiting or misplaced or loose or undeclared_files or siblings)
            else RC_OK
        ),
    }


def report_placement(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the placement reading: the roots, the axes, the pens and the folders the declaration does not cover."""
    print(
        f"placement: {rep['files']} file(s) inside the declared roots, {rep['admitted']} of a kind a root admits",
        file=stream,
    )
    for root_id, row in rep["per_root"].items():
        print(
            f"  {root_id}: {row['files']} file(s) | kind the root does not admit {row['misplaced_kind']} | loose at "
            f"the root {row['loose_at_root']} | in a subfolder the declared axis does not name "
            f"{row['undeclared_subfolders']}",
            file=stream,
        )
    for name in rep["misplaced_examples"]:
        print(f"    misplaced e.g. {name}", file=stream)
    for name in rep["loose_examples"]:
        print(f"    loose e.g. {name}", file=stream)
    print(
        f"  the axes admit {rep['vocabulary']} subfolder name(s) - kind from the declaration, domain from the corpus",
        file=stream,
    )
    print("  ARRIVAL PENS (a queue, never a defect):", file=stream)
    for pen in rep["pens"]:
        print(
            f"    {pen['id']}: {pen['files']} file(s), {pen['bytes'] / 1e6:.1f} MB, {pen['books_or_notes']} of a "
            f"declared kind, oldest {pen['oldest_days']}d, {pen['stale']} past the declared age budget, "
            f"{pen['unseen']} the S0.5 cache cannot resolve (never seen by the pipeline)",
            file=stream,
        )
        for name in pen["examples"]:
            print(f"      e.g. {name}", file=stream)
    print(
        f"  OUTSIDE THE DECLARATION (named, never walked): "
        f"{', '.join(rep['siblings_outside_the_declaration']) or 'none'}",
        file=stream,
    )


def brief(rep: dict[str, Any]) -> str:
    """ONE line for the ladder: the notify, without the detail (the full reading is --placement)."""
    pens = " | ".join(
        f"{p['id']}: {p['files']} waiting, oldest {p['oldest_days']}d, {p['stale']} stale, "
        f"{p['unseen']} never seen"
        for p in rep["pens"]
    )
    outside = ", ".join(rep["siblings_outside_the_declaration"]) or "none"
    return (
        f"LIBRARY: pens -> {pens} || misplaced {rep['misplaced']} of {rep['files']} file(s) in the declared roots "
        f"(loose at a root {rep['loose_at_root']}, in a subfolder the axis does not name "
        f"{rep['undeclared_subfolder_files']}) || outside the declaration: {outside} "
        f"|| detail: just placement | names: just source-names"
    )


def selftest() -> int:
    """Known-answer controls over synthetic roots and a synthetic cache in a temp dir (BUG-577)."""
    import tempfile

    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    base = json.loads(
        json.dumps(
            {
                "source_library": {
                    "roots": [{"id": "lib", "path": "", "kinds": ["epub", "pdf"]}],
                    "metadata_cache": "",
                    "marker_pattern": r"(?i)\b(z-lib|annas?-?archive|1lib)\b",
                    "spine_pattern": r"\s--\s|\b[0-9a-f]{16,}\b",
                    "truncation_pattern": r"_$|\($|\band\s*$",
                }
            }
        )
    )
    with tempfile.TemporaryDirectory(prefix="source_names_") as tmp:
        root = Path(tmp) / "lib"
        root.mkdir()
        (root / "A Book (z-lib.org).pdf").write_text("x", encoding="utf-8")
        (root / "Truncated Title and.pdf").write_text("x", encoding="utf-8")
        (root / "Clean Book.epub").write_text("x", encoding="utf-8")
        cache = Path(tmp) / "book_metadata.jsonl"
        cache.write_text(
            json.dumps({"source_book": "A Book.pdf", "author": "Jane Roe", "title": "A Book"})
            + "\n",
            encoding="utf-8",
        )
        pol = base
        pol["source_library"]["roots"][0]["path"] = str(root)
        pol["source_library"]["metadata_cache"] = str(cache)
        rep = census(pol)
        if rep["classes"]["ingest_site_marker"] != 1:
            mark(
                CONTROL_LABELS[0],
                f"marker class counted {rep['classes']['ingest_site_marker']}, expected 1",
            )
        if rep["classes"]["ingest_site_marker"] != 1 or not rep["classes"]["truncation_suspect"]:
            mark(
                CONTROL_LABELS[1],
                "the truncation class was not counted separately from the marker class",
            )
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
            mark(
                CONTROL_LABELS[3],
                f"readiness split was free={rep['free_to_repair']} coupled={rep['ingest_coupled']}, expected 1/1",
            )

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
        (root / "Dup.epub").write_text("x", encoding="utf-8")  # the same work, twice in ONE home
        (root / "sub").mkdir()
        (root / "sub" / "Dup.epub").write_text("x", encoding="utf-8")
        block = pol["source_library"]
        block["arrangement"] = {"corpus_home": "corpus", "drift_ceiling": 0}
        arr = arrangement(pol, corpus_root=corpus_root)
        if arr["byte_different"] != 1 or not arr.get("drift_examples"):
            mark(
                CONTROL_LABELS[5],
                f"drift counted {arr['byte_different']}, expected 1 (and to be named)",
            )
        if arr["byte_equal"] != 1 or arr["format_pairs_only"] != 1:
            mark(
                CONTROL_LABELS[6],
                f"an equal pair counted as drift, or a format pair counted as drift "
                f"(byte_equal={arr['byte_equal']}, format_pairs_only={arr['format_pairs_only']}, "
                f"expected 1/1)",
            )
        if arr["library_only"] < 2 or arr["corpus_only"] != 1:
            mark(
                CONTROL_LABELS[7],
                f"one-sided counts were {arr['library_only']}/{arr['corpus_only']}, expected >=2/1",
            )
        if arr["same_kind_twice_in_the_library"] != 1 or arr["same_kind_twice_in_the_corpus"] != 0:
            mark(
                CONTROL_LABELS[8],
                f"a key materialised twice inside one home was not counted "
                f"({arr['duplicated_within_the_library']}/{arr['duplicated_within_the_corpus']})",
            )
        leaked = [
            tok
            for tok in ("~" + "/Library/CloudStorage", "knowledge " + "pipeline/books")
            if tok in own
        ]
        if leaked:
            mark(CONTROL_LABELS[10], f"the reader restates a home path of its own: {leaked}")

        # (10) the CEILING fires: 1 drifting pair against a ceiling of 0 is FATAL; within its ceiling it is loud
        # and NOT fatal - the same pair of readings BUG-457 draws, seen in BOTH directions.
        if arr["rc"] != RC_FATAL:
            mark(
                CONTROL_LABELS[9],
                f"drift above a ceiling of 0 read rc {arr['rc']}, expected the FATAL code",
            )
        block["arrangement"]["drift_ceiling"] = 5
        within = arrangement(pol, corpus_root=corpus_root)
        if within["rc"] != RC_OWNER_OWED:
            mark(
                CONTROL_LABELS[9],
                f"drift within its ceiling read rc {within['rc']}, expected OWNER-OWED",
            )
        # ── the PLACEMENT reading (T-180/D-3049): where a file IS against where the declaration says it BELONGS ──
        (root / "cover.jpg").write_text("x", encoding="utf-8")  # a kind NO declared root admits
        notes = Path(tmp) / "notes"
        (notes / "DOMAIN 6 AI + Computing").mkdir(parents=True)
        (notes / "random folder").mkdir()
        (notes / "DOMAIN 6 AI + Computing" / "note.md").write_text("x", encoding="utf-8")
        (notes / "random folder" / "note.md").write_text("x", encoding="utf-8")
        (corpus_root / "DOMAIN 6 AI + Computing").mkdir()
        pen = Path(tmp) / "pen"
        pen.mkdir()
        (pen / "Fresh Arrival.epub").write_text("x", encoding="utf-8")
        (pen / "Old Arrival.epub").write_text("x", encoding="utf-8")
        old = time.time() - 40 * 86400
        os.utime(pen / "Old Arrival.epub", (old, old))
        pl = pol["source_library"]
        pl["roots"].append({"id": "notes", "path": str(notes), "kinds": ["md"]})
        pl["placement"] = {
            "homes": {
                "lib": {"axis": "kind", "subfolder_required": True},
                "notes": {"axis": "domain", "subfolder_required": True},
            },
            "pens": {"test_pen": {"path": str(pen), "staleness_days": 30}},
        }
        plc = placement(pol, corpus_root=corpus_root)
        if plc["misplaced"] != 1 or "cover.jpg" not in " ".join(plc["misplaced_examples"]):
            mark(
                CONTROL_LABELS[11],
                f"a file the declared roots do not admit read {plc['misplaced']} and "
                f"{plc['misplaced_examples']}, expected 1 and named",
            )
        if plc["loose_at_root"] < 5:
            mark(
                CONTROL_LABELS[12],
                f"files loose at a root read {plc['loose_at_root']}, expected the fixture's "
                f"root-level files to be counted",
            )
        if plc["undeclared_subfolders"].get("random folder") != 1:
            mark(
                CONTROL_LABELS[13],
                f"a subfolder the declared DOMAIN axis does not name was not counted "
                f"({plc['undeclared_subfolders']})",
            )
        pen_row = plc["pens"][0] if plc["pens"] else {}
        if (
            len(plc["pens"]) != 1
            or pen_row.get("files") != 2
            or pen_row.get("stale") != 1
            or pen_row.get("unseen") != 2
            or plc["rc"] != RC_OWNER_OWED
        ):
            mark(
                CONTROL_LABELS[14],
                f"a waiting pen read {pen_row} with rc {plc['rc']}, expected 2 arrivals, 1 "
                f"stale, 2 never seen, and the OWNER-OWED code",
            )
        needles = [
            "~" + "/Down" + "loads",
            "educa" + "tion/in" + "box",
            "Cal" + "ibre",
            "unsor" + "ted",
        ]
        leaked = [tok for tok in needles if tok in own]
        if leaked:
            mark(
                CONTROL_LABELS[15],
                f"the placement reader restates a root, pen or path of its own: {leaked}",
            )
        if not re.search(r"^def placement\(", own, re.M):
            mark(
                CONTROL_LABELS[15],
                "the placement reader this control is about does not exist in the file",
            )

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
    parser = argparse.ArgumentParser(
        description="The owner's source library, read as a name census (read-only)."
    )
    parser.add_argument(
        "--census", action="store_true", help="the name census (the default reading)"
    )
    parser.add_argument(
        "--arrangement",
        action="store_true",
        help="the ARRANGEMENT reading: one work, how many materialisations, and their drift",
    )
    parser.add_argument(
        "--placement",
        action="store_true",
        help="the PLACEMENT reading: misplaced kinds, files loose at a root, undeclared subfolders "
        "and every declared arrival pen (T-180/D-3049)",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="ONE line: the placement notify the ladder prints on every health run",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    try:
        if args.brief:
            rep = placement()
            print(brief(rep))
            return int(rep["rc"])
        rep = placement() if args.placement else (arrangement() if args.arrangement else census())
    except CensusError as exc:
        print(str(exc), file=sys.stderr)
        return RC_FATAL
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    elif args.placement:
        report_placement(rep)
    elif args.arrangement:
        report_arrangement(rep)
    else:
        report(rep)
    return int(rep["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
