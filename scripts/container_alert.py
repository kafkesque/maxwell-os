#!/usr/bin/env python3
"""container_alert.py — WHICH ARRIVALS CANNOT BE READ, AND WHICH ARE STILL ARRIVING (READ-ONLY, D-3075).

THE OWNER'S ASK (2026-10-17, verbatim in spirit): "do not process those books in the knowledge pipeline that are
truncated or just half downloaded — rather alert me about it so I can re-download them manually." The first half
was already true and is NOT re-implemented here: the ADMISSION DOOR refuses an unreadable container
(`plan_admission.py --refused_container_corrupt`, D-3071/D-3073) and the applier never converts a refused row.
What did not exist is the SECOND half: a reading that NAMES the unreadable files, says what is wrong with each,
and says which of them are not even finished arriving.

WHY A SEPARATE READING rather than a fourth flag on the plan: the plan answers "what may be admitted" over the
declared KIND ROOTS only, and it writes a plan for the owner's word. This answers "what on this disk cannot be
opened", over the kind roots AND the declared arrival PENS (`source_library.placement.pens` — the inbox the owner
downloads into), and it writes NOTHING. A half-downloaded book sits in the pen for days before it is ever a plan
row, so a reading that begins at the plan can never report it in time.

THE THREE WORDS, and why ARRIVING is its own word (D-3034: a declaration must resolve; a verdict must name what
the file needs):
  * READABLE — the declared probe opens it. Nothing owed;
  * ARRIVING — the name carries a declared in-flight suffix, or the file is younger than the declared settle
    window, or a `.part` sibling sits beside it. A download that has not finished is NOT a damaged book, and
    telling the owner to "re-download" a transfer that is still running is the same fault as telling them a
    truncated file is fine. Nothing to repair: let it finish, then re-read;
  * DAMAGED — the probe refuses it and it is OLDER than the settle window with no transfer in flight, so the
    bytes will not change by themselves. The declared DEFECT is named and so is its declared REMEDY.

NOTHING IS MOVED, RENAMED, DELETED OR CONVERTED. The probe is the door's own (`pipeline/container_integrity.py`)
and both the probe table and the defect vocabulary are READ from `config/ingest_identity_gate.yaml` — never
restated here, so the alert and the door can never disagree about what "readable" means (the same rule D-3074
set for the fetcher, kept now that the fetcher is retired).

Exit: 0 clean | 2 something is damaged or still arriving (loud, owner-owed, BUG-457) | 1 FATAL (an undeclared
probe, defect or pen — an absent declaration is never a zero, D-795).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import census_source_names as census  # noqa: E402 — the roots resolver: never restate where the library IS

from pipeline.container_integrity import (  # noqa: E402 — BUG-886/D-3071: the DOOR'S probes, not a second copy
    defects_from,
    diagnose,
    is_readable,
    probes_from,
)

POLICY = _PROJECT_ROOT / "config" / "ingest_identity_gate.yaml"
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

#: The three words this reading is allowed to say. A fourth would need a declaration, not a branch.
READABLE, ARRIVING, DAMAGED = "READABLE", "ARRIVING", "DAMAGED"

DEFAULT_PART_SUFFIXES = (".part", ".crdownload", ".download", ".opdownload", ".tmp")
DEFAULT_SETTLE_MINUTES = 15


class AlertError(SystemExit):
    """A declaration this reading cannot resolve is FATAL, never a silent zero (D-795)."""


def policy(path: Path = POLICY) -> dict[str, Any]:
    """The one declaration: roots, pens and the container-integrity block all live in it."""
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except OSError as exc:
        raise AlertError(f"FATAL: cannot read the declaration {path} ({exc})") from None


def arriving_policy(admission: dict[str, Any]) -> dict[str, Any]:
    """When an unreadable container is still ARRIVING rather than DAMAGED — declared, never a constant (C12)."""
    block = (admission or {}).get("container_integrity")
    if not isinstance(block, dict):
        raise AlertError(
            "FATAL: source_library.admission.container_integrity is not declared — which probe reads which "
            "container kind is a declared fact, never an inference (C12)"
        )
    declared = block.get("arriving")
    if not isinstance(declared, dict):
        raise AlertError(
            "FATAL: container_integrity.arriving is not declared — without it an unfinished download and a "
            "truncated book are the same verdict, and the owner is told to re-fetch a transfer that is still "
            "running (C12/D-3034)"
        )
    suffixes = declared.get("part_suffixes")
    settle = declared.get("settle_minutes")
    if not isinstance(suffixes, list) or not suffixes:
        raise AlertError("FATAL: container_integrity.arriving.part_suffixes must be a non-empty list (C12)")
    if not isinstance(settle, (int, float)) or settle < 0:
        raise AlertError("FATAL: container_integrity.arriving.settle_minutes must be a non-negative number (C12)")
    return {"part_suffixes": {str(s).lower() for s in suffixes}, "settle_minutes": float(settle)}


def pens(pol: dict[str, Any]) -> list[dict[str, Any]]:
    """The declared arrival pens, each validated: a pen that does not exist is a fault, not an empty queue."""
    declared = ((pol.get("source_library") or {}).get("placement") or {}).get("pens")
    if not isinstance(declared, dict) or not declared:
        raise AlertError("FATAL: source_library.placement.pens is not declared (C12/D-3038)")
    out: list[dict[str, Any]] = []
    for name, row in declared.items():
        if not isinstance(row, dict) or "path" not in row:
            raise AlertError(f"FATAL: the declared pen {name!r} does not declare 'path'")
        path = Path(str(row["path"])).expanduser()
        if not path.is_dir():
            raise AlertError(
                f"FATAL: the declared pen {name} does not exist: {path} — an absent pen is a fault, "
                f"never a count of zero (D-795)"
            )
        out.append({"id": str(name), "path": path})
    return out


def targets(pol: dict[str, Any]) -> list[dict[str, Any]]:
    """Every place an arrival may land: the declared kind roots, then the declared pens."""
    out = [{"id": r["id"], "path": r["path"], "where": "root"} for r in census.roots(pol)]
    out += [{"id": p["id"], "path": p["path"], "where": "pen"} for p in pens(pol)]
    return out


def verdict(
    path: Path, probes: dict[str, str], defects: dict[str, Any], arriving: dict[str, Any], now: float,
) -> dict[str, Any]:
    """One file, one word: READABLE, ARRIVING or DAMAGED — with the declared defect and remedy when damaged.

    The ORDER of the questions is the whole point: "is a transfer still in flight" is asked BEFORE "what is
    wrong with these bytes", because a half-written file is not wrong, it is unfinished.
    """
    name = path.name.lower()
    in_flight = next((s for s in arriving["part_suffixes"] if name.endswith(s)), None)
    age_min = max(0.0, (now - path.stat().st_mtime) / 60.0)
    if in_flight:
        return {
            "word": ARRIVING, "path": str(path), "bytes": path.stat().st_size, "age_min": round(age_min, 1),
            "why": f"the name carries the in-flight suffix {in_flight!r}: this is a download that has not "
                   f"finished, not a book — let it complete, then re-read (nothing to repair)",
        }
    probe = probes.get(path.suffix.lower())
    if probe is None:
        #: NO CLAIM IS MADE HERE. A declared kind with no probe (`.mobi`, `.azw3`, `.djvu`) is not a readability
        #: question at all - no conversion stage reads it - and the class that answers it is the plan's own
        #: `refused_container_no_stage_reads_it`. Counting it as readable would be this reader answering a
        #: question it was never given (D-3034).
        return {"word": READABLE, "probed": False, "path": str(path), "bytes": path.stat().st_size,
                "age_min": round(age_min, 1),
                "why": "no container probe is declared for this kind, so this reading makes NO claim about it "
                       "(the plan's refused_container_no_stage_reads_it class is the one that answers it)"}
    if is_readable(path, probe):
        return {"word": READABLE, "path": str(path), "bytes": path.stat().st_size, "age_min": round(age_min, 1),
                "why": f"the declared {probe!r} probe opens it"}
    part_beside = [s for s in arriving["part_suffixes"] if path.with_name(path.name + s).exists()]
    if age_min < arriving["settle_minutes"] or part_beside:
        return {
            "word": ARRIVING, "path": str(path), "bytes": path.stat().st_size, "age_min": round(age_min, 1),
            "why": (
                f"written {age_min:.0f} min ago (settle window {arriving['settle_minutes']:.0f} min)"
                if age_min < arriving["settle_minutes"]
                else f"a partial download sits beside it ({part_beside[0]!r})"
            ) + ": the bytes are still changing, so the probe's answer is not yet evidence — re-read later",
        }
    defect = diagnose(path, probe, defects)
    row: dict[str, Any] = {
        "word": DAMAGED, "path": str(path), "bytes": path.stat().st_size, "age_min": round(age_min, 1),
        "defect": defect, "remedy": str((defects.get(defect) or {}).get("remedy") or "").strip(),
        "meaning": str((defects.get(defect) or {}).get("meaning") or "").strip(),
    }
    if not row["remedy"]:
        raise AlertError(f"FATAL: the defect {defect!r} declares no remedy (C12) — a refusal nobody can act on")
    return row


def alert(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The whole reading: every container in the declared roots and pens, one word each. Moves nothing."""
    doc = pol or policy()
    admission = ((doc.get("source_library") or {}).get("admission")) or {}
    probes = probes_from(admission, AlertError)
    defects = defects_from(admission, AlertError)
    arriving = arriving_policy(admission)
    now = datetime.now(UTC).timestamp()
    rows: list[dict[str, Any]] = []
    places: list[dict[str, Any]] = []
    for place in targets(doc):
        found = [p for p in place["path"].rglob("*") if p.is_file() and not p.name.startswith(".")]
        places.append({"id": place["id"], "where": place["where"], "path": str(place["path"]),
                       "files": len(found)})
        for path in found:
            row = verdict(path, probes, defects, arriving, now)
            row.update(place=place["id"], where=place["where"])
            rows.append(row)
    damaged = [r for r in rows if r["word"] == DAMAGED]
    in_flight = [r for r in rows if r["word"] == ARRIVING]
    #: A file whose kind declares NO probe is neither readable nor damaged by this reading's lights: it is
    #: UNPROBED, counted on its own line so "1,240 readable" can never mean "1,240 checked" when it does not.
    unprobed = [r for r in rows if r.get("probed") is False]
    by_defect: dict[str, int] = {}
    for row in damaged:
        by_defect[row["defect"]] = by_defect.get(row["defect"], 0) + 1
    return {
        "places": places,
        "files": len(rows),
        "readable": len([r for r in rows if r["word"] == READABLE and r.get("probed") is not False]),
        "unprobed": len(unprobed),
        "damaged": damaged,
        "arriving": in_flight,
        "by_defect": dict(sorted(by_defect.items())),
        "settle_minutes": arriving["settle_minutes"],
        "rc": RC_OWNER_OWED if (damaged or in_flight) else RC_OK,
    }


def report(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print every damaged row in full (its defect and its remedy), then every unfinished transfer."""
    print(f"CONTAINER ALERT — {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}", file=stream)
    for place in rep["places"]:
        print(f"  {place['where']:4s} {place['id']}: {place['files']} file(s)  {place['path']}", file=stream)
    print(f"  {rep['readable']} of {rep['files']} readable | {len(rep['damaged'])} DAMAGED | "
          f"{len(rep['arriving'])} ARRIVING | {rep['unprobed']} unprobed (no probe declared for that kind)",
          file=stream)
    if rep["damaged"]:
        print(f"\nDAMAGED ({len(rep['damaged'])}) — refused at the door, so NOT processed. Each needs its own act:",
              file=stream)
        for row in rep["damaged"]:
            print(f"  ✗ {row['path']}", file=stream)
            print(f"      {row['bytes']:,} bytes | {row['age_min']:.0f} min old | defect: {row['defect']}",
                  file=stream)
            print(f"      remedy: {row['remedy']}", file=stream)
    if rep["arriving"]:
        print(f"\nARRIVING ({len(rep['arriving'])}) — a transfer that has not finished. Nothing to repair:",
              file=stream)
        for row in rep["arriving"]:
            print(f"  … {row['path']}  ({row['bytes']:,} bytes, {row['age_min']:.0f} min old)", file=stream)
            print(f"      {row['why']}", file=stream)
    if not rep["damaged"] and not rep["arriving"]:
        print("\nNothing unreadable and nothing in flight.", file=stream)


def brief(rep: dict[str, Any]) -> str:
    """ONE line for the ladder: the counts, the defect vocabulary, and the word that decides the rc."""
    if rep["rc"] == RC_OK:
        return f"container-alert: {rep['files']} file(s) probed, 0 damaged, 0 arriving"
    defects = ", ".join(f"{k} {v}" for k, v in rep["by_defect"].items()) or "none"
    return (f"container-alert: {rep['files']} probed, {len(rep['damaged'])} DAMAGED ({defects}), "
            f"{len(rep['arriving'])} ARRIVING — the door refuses them, nothing is processed; "
            f"`just admit-alert` names each remedy")


def selftest() -> int:
    """Known-answer controls on a FIXTURE tree: the three words, and the order they are asked in.

    A control nothing runs is a comment (BUG-492), and this reading's whole value is one distinction — ARRIVING
    is not DAMAGED — so the distinction is proved on bytes rather than asserted in prose. No library file, no pen
    and no real receipt is touched: the fixture is built in a temporary directory and the declared policy is the
    live one with only its paths swapped, so the probes and the defect vocabulary under test are the REAL ones.
    """
    import tempfile
    import time
    import zipfile

    controls: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root, pen = Path(tmp) / "books" / "epub", Path(tmp) / "inbox"
        root.mkdir(parents=True)
        pen.mkdir()
        with zipfile.ZipFile(root / "A Work.epub", "w") as archive:
            archive.writestr("mimetype", "application/epub+zip")
        truncated = root / "Truncated.epub"
        truncated.write_bytes(b"PK\x03\x04" + b"\x00" * 64)
        old = time.time() - 86_400
        os_utime = (old, old)
        import os as _os
        _os.utime(truncated, os_utime)
        fresh = pen / "Still Arriving.epub"
        fresh.write_bytes(b"PK\x03\x04" + b"\x00" * 64)          # the same bytes, only the AGE differs
        partial = pen / "Half.epub.part"
        partial.write_bytes(b"PK\x03\x04" + b"\x00" * 64)
        pol = policy()
        pol["source_library"]["roots"] = [{"id": "books", "path": str(root.parent), "kinds": ["epub", "pdf", "md"]}]
        pol["source_library"]["placement"]["pens"] = {"education_inbox": {"path": str(pen), "staleness_days": 30,
                                                                         "why": "fixture"}}
        before = sorted(p.name for p in list(root.parent.rglob("*")) + list(pen.rglob("*")))
        rep = alert(pol)
        after = sorted(p.name for p in list(root.parent.rglob("*")) + list(pen.rglob("*")))
        words = {Path(r["path"]).name: r for r in rep["damaged"] + rep["arriving"]
                 if r["word"] != READABLE}
        controls.append(("a readable container is READABLE", rep["readable"] == 1))
        controls.append((
            "truncated AND older than the settle window is DAMAGED, with the declared defect named",
            words.get("Truncated.epub", {}).get("word") == DAMAGED
            and words["Truncated.epub"].get("defect") == "truncated_zip_no_central_directory"
            and bool(words["Truncated.epub"].get("remedy")),
        ))
        controls.append((
            "the SAME bytes inside the settle window are ARRIVING, never DAMAGED (a transfer may be running)",
            words.get("Still Arriving.epub", {}).get("word") == ARRIVING,
        ))
        controls.append(("an in-flight suffix is ARRIVING without being probed at all",
                         words.get("Half.epub.part", {}).get("word") == ARRIVING))
        controls.append(("the reading MOVES nothing and writes nothing (the tree is byte-for-byte the same)",
                         before == after))
        controls.append(("rc is OWNER-OWED (2) while anything is damaged or arriving", rep["rc"] == RC_OWNER_OWED))
    failed = [name for name, ok in controls if not ok]
    for name, ok in controls:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    print(f"{len(controls) - len(failed)}/{len(controls)} controls green")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Print the reading. Writes nothing, moves nothing, converts nothing."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--brief", action="store_true", help="ONE line (for the ladder)")
    parser.add_argument("--json", action="store_true", help="the whole reading as JSON")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls on a fixture tree")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    rep = alert()
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    elif args.brief:
        print(brief(rep))
    else:
        report(rep)
    return int(rep["rc"])


if __name__ == "__main__":
    sys.exit(main())
