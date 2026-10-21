#!/usr/bin/env python3
"""store-authority: exactly ONE governed store, and every other store DECLARED with a status and a reason.

WHY THIS EXISTS (BUG-524, MEASURED 2026-09-26). Eight audit axes were counted and six had NO machine. The six
findings that closed that gap all came from the two axes with none: STORES and COLUMNS. This is the STORES one.
Measured by hand on this machine: THREE sqlite stores (`knowledge pipeline/maxwell.db` 156,622,848 bytes;
`knowledge pipeline/diagnostic_diagnostic_20260811_232853.db` 4,964,352; `data/maxwell.db` 131,072) plus 31
parquet snapshots in THREE directories -- and until 2026-09-26 NOTHING in the repo could answer "which of these is
the truth?" `data/maxwell.db` carries the SAME table name (`fbs`, 19 rows) as the authoritative store (7995 rows),
so a consumer pointed at the wrong path gets a plausible-looking answer set that is 0.24% of the truth. That is a
silent wrong answer, not a crash -- the BUG-511 class applied to a store.

THE RULE (one rule, one home -- D-2646)
  * every store found under the declared scan roots must have a declaration;
  * EXACTLY ONE declaration may be `authoritative` (zero or two fail CLOSED);
  * a non-authoritative store that shares a TABLE name with the authoritative one must declare that sharing
    (`shares_tables:` + `shares_why:`) -- declared, never tolerated silently;
  * a declaration whose `path` escapes the repo is refused (an undeclared authority is the defect);
  * a store file inside a DECLARED deletion pre-image region (`preimage_regions:`) is a TOMBSTONE, not a candidate
    truth: it must still be a readable sqlite store with >= 1 table, and it is COUNTED in the verdict. Declared,
    never tolerated silently; a region may not cover a declared store and may not cover the repo (BUG-549);
  * a store file carrying ZERO tables (or 0 bytes) is reported EMPTY-STORE -- the fingerprint of a
    `sqlite3.connect()` on a path that did not exist, which CREATES the file. A read-only probe that writes is
    the defect, so the rail NAMES the cause instead of filing it under UNDECLARED-STORE (BUG-549).
  * a declared store that is ABSENT is STALE (a declaration that cannot be checked is not a check);
  * `status` outside the declared vocabulary, or a missing/short `why`, fails CLOSED.

BOUNDARY (a rail's blindness IS its boundary -- BUG-521): the walk is depth-bounded (`max_depth` in the register)
and prunes `SKIP_DIRS`. A store deeper than that bound is NOT seen. That boundary is declared, not hidden.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

PREFIX = "store-authority"
ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "config" / "store_authority.yaml"
RAIL_REL = "scripts/check_store_authority.py"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2

STATUSES = ("authoritative", "derived", "archive", "stale", "synthetic")
SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")
PARQUET_SUFFIXES = (".parquet",)
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
MIN_WHY = 20
PREIMAGE_KEY = "preimage_regions"


def find_stores(root: Path, scan_roots: list[str], max_depth: int,
                prune_dirs: set[str] | None = None) -> dict[str, str]:
    """Return {rel_path: kind} for every store under `scan_roots` within `max_depth`.

    kind is "sqlite" for a store file, "parquet_collection" for a directory of parquet snapshots.

    `prune_dirs` (D-3125) are DECLARED directory NAMES of machine-generated transient tool state (a browser
    profile, e.g.) that is NOT a store; they are pruned the same way SKIP_DIRS is, by NAME, so the CLASS is
    declared once and every future instance is pruned too (config-first, C12).
    """
    root = root.resolve()
    skip = SKIP_DIRS | (prune_dirs or set())
    found: dict[str, str] = {}
    for scan in scan_roots:
        base = (root / scan).resolve()
        if not base.is_dir():
            continue
        base_depth = len(base.parts)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.startswith("."))
            if len(Path(dirpath).parts) - base_depth >= max_depth:
                dirnames[:] = []
            rel_dir = Path(dirpath).resolve().relative_to(root).as_posix()
            if rel_dir == ".":
                rel_dir = ""
            parquet = sorted(f for f in filenames if f.endswith(PARQUET_SUFFIXES))
            for name in filenames:
                if name.endswith(SQLITE_SUFFIXES):
                    key = (rel_dir + "/" + name) if rel_dir else name
                    found[key] = "sqlite"
            if parquet:
                found[rel_dir if rel_dir else "."] = "parquet_collection"
    return found


def sqlite_tables(path: Path) -> set[str]:
    """Return the TABLE names of a sqlite store, or raise SystemExit naming the artifact (C16 - no bare error)."""
    import sqlite3

    try:
        con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): cannot open " + str(path) + " as a sqlite store: "
                         + str(exc)) from exc
    try:
        rows = con.execute("select name from sqlite_master where type='table'").fetchall()
    except sqlite3.Error as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): cannot read sqlite_master of " + str(path) + ": "
                         + str(exc)) from exc
    finally:
        con.close()
    return {str(r[0]) for r in rows if not str(r[0]).startswith("sqlite_")}


def _probe_shape(path: Path) -> tuple[str, set[str]]:
    """Return ("tables", names) | ("empty", set()) | ("unreadable", set()) - never raises (a rail must not abort)."""
    import sqlite3

    try:
        if path.stat().st_size == 0:
            return "empty", set()
        con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    except (OSError, sqlite3.Error):
        return "unreadable", set()
    try:
        rows = con.execute("select name from sqlite_master where type='table'").fetchall()
    except sqlite3.Error:
        return "unreadable", set()
    finally:
        con.close()
    tables = {str(r[0]) for r in rows if not str(r[0]).startswith("sqlite_")}
    return ("tables", tables) if tables else ("empty", set())


def _size_of(path: Path) -> str:
    """Byte size of a file as text, or "unknown" if it vanished mid-scan (TOCTOU - never raise)."""
    try:
        return str(path.stat().st_size)
    except OSError:
        return "unknown"


def _preimage_regions(root: Path, reg: dict[str, Any]) -> dict[str, Any]:
    """Declared deletion pre-image regions: a TOMBSTONE home, measured and bounded, never a blanket excuse."""
    out: dict[str, Any] = {"paths": [], "faults": []}
    entries = reg.get(PREIMAGE_KEY) or []
    if not isinstance(entries, list):
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): `" + PREIMAGE_KEY + ":` must be a list of paths.")
    for entry in entries:
        if not isinstance(entry, dict) or "path" not in entry:
            raise SystemExit("FAIL-CLOSED (" + PREFIX + "): a `" + PREIMAGE_KEY + "` entry has no `path`: "
                             + repr(entry))
        rel = str(entry["path"]).strip().rstrip("/")
        why = str(entry.get("why") or "").strip()
        if rel in ("", "."):
            out["faults"].append("REGION-BLINDS-REPO: a pre-image region declared as " + repr(rel) + " covers the "
                                 "whole repo - that is not a region, it is a blindfold on every store.")
            continue
        if rel in out["paths"]:
            out["faults"].append("DOUBLE-DECLARED: pre-image region " + rel + " is declared twice; one region has "
                                 "ONE declaration home (D-2649).")
        if len(why) < MIN_WHY:
            out["faults"].append("MISSING-WHY: pre-image region " + rel + " declares no adequate `why` (got "
                                 + str(len(why)) + " chars, want >= " + str(MIN_WHY) + ") - a region without a "
                                 "reason is a hiding place.")
        base = root / rel
        if not base.is_dir():
            out["faults"].append("DEAD-REGION: " + rel + " is declared a pre-image region but is NOT a directory "
                                 "on disk - a declaration that cannot be measured is not a check.")
            continue
        out["paths"].append(rel)
    return out


def _declared(reg: dict[str, Any]) -> list[dict[str, Any]]:
    entries = reg.get("stores")
    if not isinstance(entries, list):
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): " + str(REGISTER.name) + " declares no `stores:` list - "
                         "a register with no declarations cannot check anything (C12).")
    out = []
    for entry in entries:
        if not isinstance(entry, dict) or "path" not in entry:
            raise SystemExit("FAIL-CLOSED (" + PREFIX + "): a `stores:` entry has no `path`: " + repr(entry))
        out.append(entry)
    return out


def audit(root: Path, reg: dict[str, Any], note: dict[str, Any] | None = None) -> list[str]:
    """Return DRIFT faults; an empty list means the declaration and the disk agree.

    `note` is an optional out-parameter: the caller gets the COUNTS (declared / on_disk / tombstones / regions)
    so the verdict can state the boundary it measured instead of hiding it (BUG-521).
    """
    faults: list[str] = []
    scan_roots = [str(s) for s in (reg.get("scan_roots") or ["."])]
    max_depth = int(reg.get("max_depth") or 4)
    prune_dirs = {str(d) for d in (reg.get("prune_dirs") or [])}
    declared = _declared(reg)
    on_disk = find_stores(root, scan_roots, max_depth, prune_dirs)

    authoritative = [d for d in declared if str(d.get("status")) == "authoritative"]
    if len(authoritative) != 1:
        faults.append("TWO-AUTHORITY: " + str(len(authoritative)) + " store(s) declare status `authoritative` "
                      "(" + ", ".join(str(d.get("path")) for d in authoritative) + ") - exactly ONE store may be "
                      "the truth; a second authority is a silent wrong answer, not a redundant copy.")

    by_path: dict[str, dict[str, Any]] = {}
    for d in declared:
        rel = str(d["path"])
        if rel.startswith("/") or ".." in Path(rel).parts:
            faults.append("ESCAPES-REPO: declaration path " + repr(rel) + " is not relative to the repo - an "
                          "artifact outside the repo has no declaration home (C3).")
            continue
        if rel in by_path:
            faults.append("DOUBLE-DECLARED: " + rel + " is declared twice; one artifact has ONE declaration home "
                          "(D-2649).")
        by_path[rel] = d
        if str(d.get("status")) not in STATUSES:
            faults.append("UNKNOWN-STATUS: " + rel + " declares status " + repr(d.get("status"))
                          + " which is not one of " + ", ".join(STATUSES) + " - a status outside the vocabulary "
                          "cannot be reasoned about.")
        why = str(d.get("why") or "").strip()
        if len(why) < MIN_WHY:
            faults.append("MISSING-WHY: " + rel + " declares no adequate `why` (got " + str(len(why))
                          + " chars, want >= " + str(MIN_WHY) + ") - a status without a reason is a convenience, "
                          "not a declaration.")
        if rel not in on_disk and rel not in ("", "."):
            faults.append("STALE: " + rel + " is declared but NOT on disk - a declaration that cannot be checked "
                          "is not a check.")

    regions = _preimage_regions(root, reg)
    faults.extend(regions["faults"])
    region_paths: list[str] = regions["paths"]
    for name in region_paths:
        for rel in sorted(by_path):
            if rel == name or rel.startswith(name + "/"):
                faults.append("REGION-SHADOWS-DECLARATION: pre-image region " + name + " covers the DECLARED store "
                              + rel + " - a tombstone region may not cover a declaration; an exclusion is not a "
                              "hiding place.")

    tombstones: list[str] = []
    for rel in sorted(on_disk):
        kind = on_disk[rel]
        inside = next((p for p in region_paths if rel == p or rel.startswith(p + "/")), None)
        if kind == "sqlite":
            shape, _tables = _probe_shape(root / rel)
            if shape != "tables":
                head = "EMPTY-STORE" if shape == "empty" else "UNREADABLE-STORE"
                why_shape = ("carries NO table - the fingerprint of `sqlite3.connect()` on a path that did not "
                             "exist, which CREATES the file (BUG-549). A read-only probe may not write: remove it "
                             "or declare what it is."
                             if shape == "empty" else
                             "cannot be read as a sqlite store - its shape cannot be established, so it is a "
                             "store nobody can reason about.")
                faults.append(head + ": " + rel + " (" + _size_of(root / rel) + " bytes) " + why_shape)
                continue
        if inside is not None:
            tombstones.append(rel)
            continue
        if rel not in by_path:
            faults.append("UNDECLARED-STORE: " + rel + " (" + kind + ") exists and is declared NOWHERE - "
                          "an undeclared store is an undeclared authority.")

    if len(authoritative) == 1:
        auth_rel = str(authoritative[0]["path"])
        auth_path = root / auth_rel
        if auth_path.is_file():
            auth_tables = sqlite_tables(auth_path)
            for rel, entry in sorted(by_path.items()):
                if rel == auth_rel:
                    continue
                path = root / rel
                if not path.is_file():
                    continue
                shared = sorted(sqlite_tables(path) & auth_tables)
                declares = entry.get("shares_tables") is True
                if shared and not declares:
                    faults.append("SHARED-TABLE: " + rel + " (status " + str(entry.get("status")) + ") carries "
                                  "table(s) " + ", ".join(shared) + " that also exist in the authoritative "
                                  "store " + auth_rel + " - a consumer pointed here gets a plausible answer "
                                  "set that is not the truth; declare `shares_tables: true` + `shares_why:` "
                                  "or remove it.")
                elif declares and not shared:
                    faults.append("STALE-SHARING: " + rel + " declares `shares_tables: true` but shares NO "
                                  "table name with " + auth_rel + " - a declaration that cannot be measured "
                                  "is not a check.")
                elif declares:
                    why = str(entry.get("shares_why") or "").strip()
                    if len(why) < MIN_WHY:
                        faults.append("MISSING-WHY: " + rel + " declares `shares_tables: true` with no "
                                      "adequate `shares_why`.")
    if note is not None:
        note.update({"declared": len(declared), "on_disk": len(on_disk), "tombstones": len(tombstones),
                     "regions": list(region_paths), "faults": len(faults)})
    return faults


def _seed_repo(base: Path, files: dict[str, list[str]]) -> None:
    """Create synthetic sqlite stores {rel: [table names]} under `base` (controls only)."""
    import sqlite3

    for rel, tables in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(path))
        try:
            for table in tables:
                con.execute('create table "%s" (fb_id text primary key)' % table)
            con.commit()
        finally:
            con.close()


def controls() -> list[tuple[str, Callable[[], bool]]]:
    """Known-answer controls (BUG-492): each is handed a THUNK and must be able to FAIL."""
    import tempfile

    def _case(reg: dict[str, Any], expect: str, forbid: str = "") -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"], "data/maxwell.db": ["fbs"]})
            reg = dict(reg)
            reg.setdefault("scan_roots", ["."])
            reg.setdefault("max_depth", 4)
            faults = audit(base, reg)
            hit = any(f.startswith(expect) for f in faults)
            clean = not any(f.startswith(forbid) for f in faults) if forbid else True
            if not hit or not clean:
                print("      faults: " + " | ".join(faults))
            return hit and clean

    def c01_clean() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            reg = {"scan_roots": ["."], "max_depth": 4, "stores": [
                {"path": "gov/maxwell.db", "status": "authoritative",
                 "why": "the governed store for this synthetic control case"}]}
            faults = audit(base, reg)
            if faults:
                print("      faults: " + " | ".join(faults))
            return not faults

    def c02_undeclared() -> bool:
        return _case({"stores": [{"path": "gov/maxwell.db", "status": "authoritative",
                                  "why": "the governed store for this synthetic control case"}]}, "UNDECLARED-STORE")

    def c03_two_authority() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "primary synthetic governed store here"},
            {"path": "data/maxwell.db", "status": "authoritative", "why": "second synthetic authority here"}]},
            "TWO-AUTHORITY")

    def c04_unknown_status() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "the governed store for this control"},
            {"path": "data/maxwell.db", "status": "probably-fine",
             "why": "a status outside the declared vocabulary must fail closed"}]}, "UNKNOWN-STATUS")

    def c05_missing_why() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "the governed store for this control"},
            {"path": "data/maxwell.db", "status": "stale", "why": "short"}]}, "MISSING-WHY")

    def c06_shared_table_undeclared() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "the governed store for this control"},
            {"path": "data/maxwell.db", "status": "stale",
             "why": "a legacy export that carries the same table name as the truth"}]}, "SHARED-TABLE")

    def c07_shared_table_declared() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"], "data/maxwell.db": ["fbs"]})
            reg = {"scan_roots": ["."], "max_depth": 4, "stores": [
                {"path": "gov/maxwell.db", "status": "authoritative",
                 "why": "the governed store for this synthetic control case"},
                {"path": "data/maxwell.db", "status": "stale", "shares_tables": True,
                 "shares_why": "declared: a synthetic legacy export deliberately kept for this control case",
                 "why": "a legacy export kept beside the governed store for reproducibility"}]}
            faults = audit(base, reg)
            if faults:
                print("      faults: " + " | ".join(faults))
            return not faults

    def c08_stale_declaration() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "the governed store for this control"},
            {"path": "data/maxwell.db", "status": "stale",
             "why": "a legacy export that carries the same table name as the truth"},
            {"path": "gov/ghost.db", "status": "archive",
             "why": "declared but deliberately absent - must be reported STALE"}]}, "STALE")

    def c09_escapes_repo() -> bool:
        return _case({"stores": [
            {"path": "gov/maxwell.db", "status": "authoritative", "why": "the governed store for this control"},
            {"path": "data/maxwell.db", "status": "stale", "shares_tables": True,
             "shares_why": "declared: a 19-row legacy export deliberately kept for reproducibility",
             "why": "a legacy export kept beside the governed store for reproducibility"},
            {"path": "../outside/maxwell.db", "status": "archive",
             "why": "a path outside the repo has no declaration home at all"}]}, "ESCAPES-REPO")

    GOV = {"path": "gov/maxwell.db", "status": "authoritative",
           "why": "the governed store for this synthetic control case"}
    TOMB = {"path": "backup/deletions", "why": "sanctioned deletion pre-images: a reversible copy, never truth"}

    def c10_tombstone_counted() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"], "backup/deletions/20260101_000000/maxwell.db": ["fbs"]})
            note: dict = {}
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                                  "preimage_regions": [dict(TOMB)]}, note)
            if faults or note.get("tombstones") != 1:
                print("      faults: " + " | ".join(faults) + " tombstones=" + str(note.get("tombstones")))
            return not faults and note.get("tombstones") == 1

    def c11_empty_store_named() -> bool:
        import sqlite3

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            (base / "scratch").mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(base / "scratch" / "typo.db"))  # CREATES a real 0-byte file
            con.close()
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [
                dict(GOV), {"path": "scratch/typo.db", "status": "archive",
                            "why": "a 0-byte file created by connecting to a path that did not exist"}]})
            if not any(f.startswith("EMPTY-STORE") for f in faults) or any(f.startswith("UNDECLARED") for f in faults):
                print("      faults: " + " | ".join(faults))
            return (any(f.startswith("EMPTY-STORE") for f in faults)
                    and not any(f.startswith("UNDECLARED") for f in faults))

    def c12_empty_region_is_healthy() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            (base / "backup" / "deletions").mkdir(parents=True, exist_ok=True)
            note: dict = {}
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                                  "preimage_regions": [dict(TOMB)]}, note)
            if faults or note.get("tombstones") != 0:
                print("      faults: " + " | ".join(faults))
            return not faults and note.get("tombstones") == 0

    def c13_dead_region() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                                  "preimage_regions": [dict(TOMB)]})
            if not any(f.startswith("DEAD-REGION") for f in faults):
                print("      faults: " + " | ".join(faults))
            return any(f.startswith("DEAD-REGION") for f in faults)

    def c14_region_shadows_declaration() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [
                dict(GOV), {"path": "gov/legacy.db", "status": "archive",
                            "why": "a declared legacy store used by this control case"}],
                "preimage_regions": [{"path": "gov",
                                      "why": "a region that would swallow declared stores, which is refused"}]})
            if not any(f.startswith("REGION-SHADOWS-DECLARATION") for f in faults):
                print("      faults: " + " | ".join(faults))
            return any(f.startswith("REGION-SHADOWS-DECLARATION") for f in faults)

    def c15_region_blinds_repo() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"]})
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                                  "preimage_regions": [{"path": ".",
                                                        "why": "a region over the whole repo is a blindfold"}]})
            if not any(f.startswith("REGION-BLINDS-REPO") for f in faults):
                print("      faults: " + " | ".join(faults))
            return any(f.startswith("REGION-BLINDS-REPO") for f in faults)

    def c16_region_does_not_loosen() -> bool:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"], "elsewhere/real.db": ["fbs"]})
            (base / "backup" / "deletions").mkdir(parents=True, exist_ok=True)
            faults = audit(base, {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                                  "preimage_regions": [dict(TOMB)]})
            if not any(f.startswith("UNDECLARED-STORE") for f in faults):
                print("      faults: " + " | ".join(faults))
            return any(f.startswith("UNDECLARED-STORE") for f in faults)

    def c17_prune_dirs_is_declared_boundary() -> bool:
        """D-3125: a DECLARED transient dir (browser profile) is pruned by NAME, and prunes nothing outside it."""
        import sqlite3

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed_repo(base, {"gov/maxwell.db": ["fbs"], "elsewhere/real.db": ["fbs"]})
            # a machine-generated browser profile carrying a Chrome feature DB is NOT a store:
            prof = base / "acq" / "browser-profile" / "Default"
            prof.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(prof / "declarative_performance_observer.db"))
            con.execute("create table meta (k text primary key, v text)")
            con.commit(); con.close()
            reg = {"scan_roots": ["."], "max_depth": 4, "stores": [dict(GOV)],
                   "prune_dirs": ["browser-profile"]}
            faults = audit(base, reg)
            # the transient dir's DB is pruned, but `elsewhere/real.db` is still UNDECLARED-STORE (no loosening):
            return (not any("browser-profile" in f for f in faults)
                    and any(f.startswith("UNDECLARED-STORE") for f in faults)
                    and any("elsewhere/real.db" in f for f in faults))

    return [
        ("c01 a single authoritative store with no siblings is CLEAN", c01_clean),
        ("c02 an undeclared store is UNDECLARED-STORE", c02_undeclared),
        ("c03 two authorities fail CLOSED", c03_two_authority),
        ("c04 a status outside the vocabulary fails", c04_unknown_status),
        ("c05 a status without an adequate why fails", c05_missing_why),
        ("c06 an undeclared shared table name fails CLOSED", c06_shared_table_undeclared),
        ("c07 a DECLARED shared table name is tolerated and checked", c07_shared_table_declared),
        ("c08 a declared-but-absent store is STALE", c08_stale_declaration),
        ("c09 a declaration escaping the repo is refused", c09_escapes_repo),
        ("c10 a tombstone in a DECLARED pre-image region is tolerated AND counted", c10_tombstone_counted),
        ("c11 a 0-byte file (connect() on a missing path) is EMPTY-STORE, not UNDECLARED-STORE",
         c11_empty_store_named),
        ("c12 an EMPTY declared region is the healthy state (0 tombstones, no fault)", c12_empty_region_is_healthy),
        ("c13 a region that is not a directory is DEAD-REGION", c13_dead_region),
        ("c14 a region covering a DECLARED store is refused", c14_region_shadows_declaration),
        ("c15 a region covering the whole repo is refused", c15_region_blinds_repo),
        ("c16 a declared region does NOT loosen the rule elsewhere", c16_region_does_not_loosen),
        ("c17 a DECLARED transient dir (browser profile) is pruned by name, nothing outside it",
         c17_prune_dirs_is_declared_boundary),
    ]


def run_controls() -> int:
    """Run every known-answer control; a control that cannot fail is reported, not passed (BUG-492)."""
    ok = 0
    for name, thunk in controls():
        try:
            good = bool(thunk())
        except Exception as exc:  # C16: report, never swallow
            good = False
            print("  FAIL " + name + " -> raised " + type(exc).__name__ + ": " + str(exc))
            continue
        print(("  ok   " if good else "  FAIL ") + name)
        ok += 1 if good else 0
    total = len(controls())
    print(("ok " if ok == total else "FAIL ") + PREFIX + ": " + str(ok) + "/" + str(total)
          + " known-answer control(s) fire")
    return EXIT_CLEAN if ok == total else EXIT_DRIFT


def main(argv: list[str]) -> int:
    """Entry point: exactly ONE mode is required (C16 - an ambiguous invocation must not silently scan)."""
    modes = [a for a in argv if a in ("--selftest", "--check", "--list")]
    if len(argv) != 1 or len(modes) != 1:
        raise SystemExit("FAIL " + PREFIX + ": exactly ONE of --selftest | --check | --list is required (C16); "
                         "got " + repr(argv))
    if modes[0] == "--selftest":
        return run_controls()
    reg = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    if modes[0] == "--list":
        on_disk = find_stores(ROOT, [str(s) for s in (reg.get("scan_roots") or ["."])],
                              int(reg.get("max_depth") or 4))
        declared = {str(d.get("path")): str(d.get("status")) for d in _declared(reg)}
        for rel in sorted(on_disk):
            print("  " + rel.ljust(58) + on_disk[rel].ljust(20) + declared.get(rel, "UNDECLARED"))
        print(PREFIX + ": " + str(len(on_disk)) + " store(s) on disk, " + str(len(declared)) + " declared")
        return EXIT_CLEAN
    note: dict[str, Any] = {}
    faults = audit(ROOT, reg, note)
    for fault in faults:
        print("  DRIFT " + fault)
    print(("FAIL " if faults else "ok ") + PREFIX + ": " + str(note.get("declared", 0)) + " store(s) declared | "
          + str(note.get("tombstones", 0)) + " tombstone(s) in " + str(len(note.get("regions", [])))
          + " declared pre-image region(s) | " + str(len(faults)) + " fault(s)")
    return EXIT_DRIFT if faults else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
