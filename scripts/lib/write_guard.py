#!/usr/bin/env python3
"""write_guard - the ONLY sanctioned way to write an artifact that holds cells you do not own.

WHY (RC-1, D-401). The register's most destructive class is "one artifact, many writers, no ownership
partition": a writer regenerates its own columns and rewrites the whole file, and another owner's cells are
collateral. BUG-478 blanked 148 owner cells this way; BUG-443, BUG-433, BUG-460, BUG-406, BUG-409 are the
same mechanism. Two scripts in this repo already implement the correct discipline by hand
(scripts/ingest_panel_column.py, scripts/normalize_owner_workbook.py) - this module is that discipline as a
mechanism, so the next script cannot forget it.

THE INVARIANT: a writer may change only the cells it declares it owns. If any OTHER cell would change, the
write is REFUSED and nothing is written. Not a warning - a refusal, because the failure it prevents is
silent and unrecoverable (an owner's typed answer, gone).

Every write also: backs up the pre-image (byte-exact) -> writes a temp file in the same directory ->
flush + os.fsync -> os.replace (C6, crash-safe) -> re-reads and re-measures what actually changed ->
appends a mutation record to the journal. Nothing lands without a receipt.

Usage:
    from scripts.lib.write_guard import write_rows, append_rows, WriteRefused, OWNED_ANY
    report = write_rows(path, rows, owned_keys={"depth_final"}, writer="scripts/foo.py", mode="merge")
    report = append_rows(path, new_rows, owned_keys={"machine_depth"}, writer="scripts/foo.py")  # additions only
    report = append_lines(path, ["a,b,c"], writer="scripts/foo.py")  # a LEDGER: suffix-only, pre-image bytes preserved

Self-test (runs in CI, asserts the refusals it claims):  python3 scripts/lib/write_guard.py --selftest
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import hashlib
import io
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO / "backups"
JOURNAL = REPO / "governance" / "MUTATION_JOURNAL.jsonl"
OWNERSHIP = REPO / "config" / "artifact_ownership.yaml"
#: The guard's public call sites. A mention of the module is not a call: an import with no call is a script
#: that DECLARES the discipline and does not apply it (D-401/I1).
GUARD_CALLS = ("write_rows", "append_rows", "append_lines", "write_document", "plan")

#: Sentinel for a legitimate whole-file regeneration (a fresh derived artifact). It is EXPLICIT because
#: "I own everything" must be a declared decision, never a default that silently skips the guard.
OWNED_ANY = "*"


class WriteRefused(SystemExit):
    """Raised when a write would touch a cell the caller does not own. Fail closed (C16)."""


def _label(path: Path) -> str:
    """Return a repo-relative label when possible, else the absolute path (a tmp path is not an error)."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _stamp() -> str:
    """Return a filesystem-safe UTC timestamp for backup names and journal records."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha16(path: Path) -> str:
    """Return the first 16 hex chars of a file's sha256, or 'absent' when it does not exist."""
    if not path.exists():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def read_rows(path: Path, encoding: str = "utf-8") -> list[dict[str, str]]:
    """Read a CSV artifact as a list of dicts. A missing file reads as an empty artifact.

    encoding is DECLARED, not a constant (C12): a human_authored workbook may be cp1252/mac_roman, and a guard
    that cannot read the artifact it protects fails closed on the wrong thing.
    """
    if not path.exists():
        return []
    with path.open("r", encoding=encoding, newline="") as fh:
        return list(csv.DictReader(fh))


def _cell_diff(before: dict[str, str], after: dict[str, str]) -> set[str]:
    """Return the keys whose value differs between two records (blank-insensitive on missing keys)."""
    keys = set(before) | set(after)
    return {k for k in keys if (before.get(k) or "") != (after.get(k) or "")}


def supplied_offences(rows: list[dict[str, str]], before: list[dict[str, str]], owned_keys: set[str],
                      id_column: str) -> list[str]:
    """Return offences in the CALLER'S OWN rows: an edit to a cell it does not own must be refused, never
    silently dropped by a merge. Masking an illegal edit is not enforcing the invariant."""
    if owned_keys == {OWNED_ANY}:
        return []
    b_by_id = {r[id_column]: r for r in before}
    bad = []
    for rec in rows:
        base = b_by_id.get(rec.get(id_column, ""))
        if base is None:
            continue
        for k, v in rec.items():
            if k in owned_keys or k == id_column:
                continue
            if k in base and (v or "") != (base[k] or ""):
                bad.append(f"row {rec.get(id_column)!r}: caller supplied a change to {k!r}, which it does "
                           f"not own ({base[k]!r} -> {v!r})")
    return bad


def plan(before: list[dict[str, str]], after: list[dict[str, str]],
         owned_keys: set[str], id_column: str) -> tuple[set[str], list[str]]:
    """
    Return (touched_keys, offences).

    touched = every column that would change, anywhere in the artifact.
    offence = a touched column the caller does not own; also row-count change, unless OWNED_ANY.
    """
    touched: set[str] = set()
    b_by_id = {r[id_column]: r for r in before}
    a_by_id = {r[id_column]: r for r in after}
    if len(before) != len(after):
        return set(), [f"row count would change: {len(before)} -> {len(after)}"]
    if owned_keys == {OWNED_ANY}:
        return set().union(*[set(r) for r in after]) if after else set(), []
    for key in a_by_id:
        if key not in b_by_id:
            return set(), [f"row {key!r} would be ADDED - additions are not a cell edit; "
                           f"declare OWNED_ANY for a regeneration"]
    for key, rec in a_by_id.items():
        touched |= _cell_diff(b_by_id[key], rec)
    offences = sorted(touched - owned_keys)
    return touched, [f"cell outside the declared ownership set would change: {c!r}" for c in offences]


def plan_append(before: list[dict[str, str]], after: list[dict[str, str]],
                owned_keys: set[str], id_column: str) -> list[str]:
    """Return the offences in an APPEND - what must hold for an ADDITION to be legal (D-401, mode='append').

    plan() cannot judge an addition: it refuses any row-count change, which is why two writers kept the ownership
    discipline in their own hands. MEASURED 2026-09-25 (BUG-491c class): the declared exemption said an ingestor's
    job IS to add rows, while the ingestor PRESERVES the row count and merges one column - a rationale that did
    not match its mechanism, exactly as with the closed-menu writer.

    The declared append invariant, judged on the whole artifact:
      1. every pre-image row survives UNCHANGED at its original position (the pre-image is a PREFIX of the
         post-image) - an edit, a reorder or a truncation is a REFUSAL, not an append;
      2. an added row may only populate columns the caller declares it owns (plus the id);
      3. an added row may not reuse an existing id - that is an edit wearing an addition's clothes.
    """
    if len(after) < len(before):
        return ["truncation: " + str(len(before)) + " -> " + str(len(after)) + " row(s) - an append may never "
                "remove a row (R-D410: a removed record cannot be audited)"]
    bad: list[str] = []
    seen = {r.get(id_column, "") for r in before}
    for i, (old, new) in enumerate(zip(before, after)):
        changed = sorted(_cell_diff(old, new))
        if changed:
            bad.append("pre-existing row " + str(i) + " (" + str(old.get(id_column, "?")) + ") would CHANGE "
                       + str(changed) + " - an append may not edit the pre-image (the BUG-478 class: the owner's "
                       "typed cell is the collateral); a superseding pass needs its own declaration")
    for rec in after[len(before):]:
        rid = rec.get(id_column, "")
        if not str(rid).strip():
            bad.append("an added row carries no " + id_column + " - an unaddressable row cannot be audited")
        elif rid in seen:
            bad.append("added row " + repr(rid) + " reuses an existing " + id_column + " - that is an EDIT, "
                       "not an addition")
        seen.add(rid)
        for k, v in rec.items():
            if k in owned_keys or k == id_column:
                continue
            if str(v or "").strip():
                bad.append("added row " + repr(rid) + " populates " + repr(k) + ", which the caller does not own "
                           "- a row with no pre-image may only fill its own columns (declare OWNED_ANY to own the "
                           "whole artifact)")
    return bad


@dataclass
class WriteReport:
    """Receipt for one guarded write: what moved, and the evidence that nothing else did."""
    path: str
    writer: str
    mode: str
    owned_keys: list[str]
    touched: list[str]
    rows: int
    #: rows ADDED by a declared append (mode='append'): a receipt that cannot say how many rows it added cannot be
    #: told apart from a regeneration, and the count IS part of what moved (BUG-491 class).
    added: int = 0
    backup: str | None = None
    pre_sha16: str = "absent"
    post_sha16: str = "absent"
    kind: str = "cells"
    #: 1.1 (2026-09-25): added arrived with the declared APPEND mode - a deliberate bump (R14), so that a record
    #: with no added field is VISIBLY a pre-append receipt instead of defaulting a missing count to zero.
    schema_version: str = "1.1"
    stamp: str = field(default_factory=_stamp)

    def record(self) -> None:
        """Append the receipt to the mutation journal (append-only, C13/R-D410)."""
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(self.__dict__, sort_keys=True) + "\n")


def pre_image_faults(path: Path) -> list[str]:
    """PURE: a pre-image is evidence of an artifact of the AUDITED tree, and of nothing else (BUG-560 class).

    `backups/` is the ONE store an auditor reads to reconstruct what a writer replaced (C13/R-D410), and a
    pre-image's name carries the artifact's STEM only - so a copy taken from a path OUTSIDE the tree is
    indistinguishable from the pre-image of a same-named tracked artifact. MEASURED 2026-09-27 (BUG-560/D-2685):
    the owner-ruling applier's own `--selftest` built its fixture under temp/ and called write_rows with the
    DEFAULT backup=True, leaving five throwaway pre-images (`wb.PRE_apply_workbook_rulings_*.csv`, 81-83 bytes
    each) in the live backups/ - the CONTROL run polluted the evidence of the tree it audits, and nothing in the
    store said which artifact they addressed. A pre-image of a fixture is evidence of nothing; the whole declared
    selftest set was then scanned (33 declared commands, 2026-09-27) and this was the only deposit, so the rule
    lands as CONTAINMENT - the mechanism that produced it - rather than as a per-run observation.
    """
    resolved = path.resolve()
    if resolved != REPO and REPO not in resolved.parents:
        return ["the artifact at " + str(resolved) + " lies OUTSIDE the audited tree " + str(REPO)
                + ": its pre-image is evidence of nothing and would be stored under " + str(BACKUP_DIR)
                + " beside the pre-images of the tree's own artifacts, indistinguishable from them (BUG-560). "
                  "A caller whose artifact is not the tree's owns no pre-image to keep: pass backup=False."]
    return []


def _backup(path: Path, writer: str) -> Path | None:
    """Byte-exact pre-image copy under backups/ (C13/R-D410), or None when the artifact does not exist yet.

    ONE home for the backup rule: three writers each copying the pre-image their own way is the same class of
    defect as one fact living in two homes (BUG-491).
    """
    if not path.exists():
        return None
    _faults = pre_image_faults(path)
    if _faults:
        print("REFUSED pre-image of " + _label(path) + " for " + writer)
        for _f in _faults:
            print("  !! " + _f)
        raise WriteRefused(1)
    BACKUP_DIR.mkdir(exist_ok=True)
    bp = BACKUP_DIR / f"{path.stem}.PRE_{Path(writer).stem}_{_stamp()}{path.suffix}"
    bp.write_bytes(path.read_bytes())
    return bp


def _write_csv_atomic(path: Path, rows: list[dict[str, str]], fieldnames: list[str], *, encoding: str,
                      lineterminator: str) -> None:
    """Write a row artifact crash-safely (C6: tempfile -> fsync -> os.replace). ONE home for how it is written.

    lineterminator is DECLARED, never inherited from csv's CRLF default: silently re-terminating the lines of a
    human_authored artifact rewrites every line of a file the writer does not own - a whole-file byte change
    disguised as a one-cell edit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".wg_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
            w.writeheader()
            w.writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _require_id_column(fieldnames: list[str], id_column: str, path: Path, writer: str) -> None:
    """Refuse a write whose fieldnames do not carry the DECLARED id column (D-401, fail closed).

    MEASURED 2026-09-25 (BUG-492): config/artifact_ownership.yaml declared `id_column: row` for an artifact whose
    header is item_id,name,why,... and carries no `row` at all. Every row then reads as unaddressable, so the
    append invariant's third clause (an added row may not reuse an existing id) is VACUOUS - it cannot refuse
    anything, while the artifact LOOKS guarded and receipted. An id column that does not exist in the artifact it
    addresses is a declaration that cannot be falsified; and a writer that passes `columns` without it would drop
    the id column silently, un-addressing every row it touches.
    """
    if id_column not in fieldnames:
        print("REFUSED write to " + _label(path) + " by " + writer)
        print("  !! the declared id_column " + repr(id_column) + " is not among the fieldnames " + str(fieldnames)
              + " - an id column that does not exist cannot address a row, so the ownership invariant would be "
              "judged over a column of blanks (BUG-492). Nothing was written.")
        raise WriteRefused(1)


def write_rows(path: Path, rows: list[dict[str, str]], *, owned_keys: set[str], writer: str,
               id_column: str = "item_id", mode: str = "merge", columns: list[str] | None = None,
               encoding: str = "utf-8", lineterminator: str = "\n",
               backup: bool = True, journal: bool = True) -> WriteReport:
    """
    Write `rows` to `path` under the ownership invariant, or refuse.

    mode='merge' keeps a cell that the caller does not own at its pre-image value; the guard refuses only
    when a merge cannot produce a legal result. The caller never gets to "just write it anyway".
    Raises WriteRefused (a SystemExit subclass) on any offence - nothing is written.
    """
    before = read_rows(path, encoding)
    merged: list[dict[str, str]] = []
    if mode == "merge" and owned_keys != {OWNED_ANY}:
        b_by_id = {r[id_column]: r for r in before}
        for rec in rows:
            base = dict(b_by_id.get(rec.get(id_column, ""), {}))
            base.update({k: v for k, v in rec.items() if k in owned_keys or k not in base})
            merged.append(base)
    else:
        merged = [dict(r) for r in rows]

    _require_id_column(columns or (list(merged[0]) if merged else []), id_column, path, writer)

    offences = supplied_offences(rows, before, owned_keys, id_column)
    touched, structural = plan(before, merged, owned_keys, id_column)
    offences = offences + structural
    if offences:
        print(f"REFUSED write to {_label(path)} by {writer}")
        for o in offences:
            print(f"  !! {o}")
        print("  the ownership set is in config/artifact_ownership.yaml; a writer may not change a cell "
              "it does not own (D-401). Nothing was written.")
        raise WriteRefused(1)

    if journal:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = _backup(path, writer) if backup else None

    # measured BEFORE the write: a receipt that records the post-image as the pre-image audits nothing (BUG-491 class)
    pre16 = _sha16(backup_path) if backup_path else _sha16(path)
    fieldnames = columns or (list(merged[0]) if merged else [])
    _write_csv_atomic(path, merged, fieldnames, encoding=encoding, lineterminator=lineterminator)

    after = read_rows(path, encoding)
    residual, offences2 = plan(merged, after, {OWNED_ANY}, id_column)
    if offences2:
        raise WriteRefused(f"FAIL-CLOSED: post-write verification failed for {path}: {offences2}")

    rep = WriteReport(path=str(path), writer=writer, mode=mode, owned_keys=sorted(owned_keys),
                      touched=sorted(touched), rows=len(after), pre_sha16=pre16, post_sha16=_sha16(path),
                      backup=str(backup_path) if backup_path else None)
    if journal:
        rep.record()
    return rep


def append_rows(path: Path, rows: list[dict[str, str]], *, owned_keys: set[str], writer: str,
                id_column: str = "item_id", columns: list[str] | None = None,
                encoding: str = "utf-8", lineterminator: str = "\n",
                backup: bool = True, journal: bool = True) -> WriteReport:
    """APPEND rows to path under the declared append invariant, or refuse (D-401, mode='append').

    The WHOLE artifact is judged, not the supplied rows: every pre-image row must survive unchanged and in place,
    and an added row may only fill the caller's own columns (plan_append). The pre-image is backed up, the write
    is crash-safe, the post-image is re-read and re-judged, and the receipt records how many rows were added.
    """
    before = read_rows(path, encoding)
    after = before + [dict(r) for r in rows]
    _require_id_column(columns or (list(after[0]) if after else []), id_column, path, writer)

    offences = plan_append(before, after, owned_keys, id_column)
    if offences:
        print("REFUSED append to " + _label(path) + " by " + writer)
        for o in offences:
            print("  !! " + o)
        print("  the ownership set is in config/artifact_ownership.yaml; an append may ADD rows, never edit or "
              "remove one (D-401). Nothing was written.")
        raise WriteRefused(1)

    if journal:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = _backup(path, writer) if backup else None
    pre16 = _sha16(backup_path) if backup_path else _sha16(path)
    fieldnames = columns or (list(after[0]) if after else [])
    _write_csv_atomic(path, after, fieldnames, encoding=encoding, lineterminator=lineterminator)

    on_disk = read_rows(path, encoding)
    offences2 = plan_append(before, on_disk, owned_keys, id_column)
    if offences2:
        raise WriteRefused("FAIL-CLOSED: post-write verification failed for " + str(path) + ": " + str(offences2))

    rep = WriteReport(path=str(path), writer=writer, mode="append", owned_keys=sorted(owned_keys), touched=[],
                      rows=len(on_disk), added=len(rows),
                      backup=str(backup_path) if backup_path else None, pre_sha16=pre16, post_sha16=_sha16(path))
    if journal:
        rep.record()
    return rep


def suffix_faults(pre: bytes, post: bytes, suffix: bytes) -> list[str]:
    """PURE: the SUFFIX-ONLY verdict over three byte strings (BUG-560/D-2685).

    Every input is a PARAMETER, so the controls that drive this are synthetic and this repository's own bytes can
    never make one pass (BUG-492). It states the only thing an appender to a ledger has to prove: the bytes that
    were there are STILL there, unchanged and in place, and everything after them is what the writer declared.
    """
    faults: list[str] = []
    if post[: len(pre)] != pre:
        faults.append("the write CHANGED bytes before the append point (the pre-image is not a prefix of the "
                      "post-image - an append may never rewrite a line it does not own)")
    if post[len(pre):] != suffix:
        faults.append("the bytes past the pre-image are not the lines this writer declared ("
                      + repr(post[len(pre):][:80]) + " != " + repr(suffix[:80]) + ")")
    return faults


def append_lines(path: Path, lines: list[str], *, writer: str, encoding: str = "utf-8",
                 lineterminator: str = "\n", backup: bool = False, journal: bool = True) -> WriteReport:
    """APPEND whole lines to a LEDGER under the SUFFIX-ONLY invariant, or refuse (BUG-560/D-2685).

    WHY A SECOND APPEND API: append_rows judges CELLS and then regenerates every pre-image line's bytes through
    csv.DictWriter - MEASURED on the owner's fixlog (14 CRLF and 9 LF lines), a declared append that way would
    re-terminate 23 lines of a ledger whose bytes the appender does not own, which is the whole-file byte change
    disguised as an addition that _write_csv_atomic's own docstring warns about. An append that only ever ADDS a
    suffix cannot destroy a foreign cell, so it needs no ownership arbitration - it needs a PROOF of that shape:
    suffix_faults() is checked on the composed bytes BEFORE the write and on the artifact AFTER it (C16).

    backup defaults to False, for write_document's reason: an append does not destroy the pre-image that R-D410
    exists to preserve, and the receipt still records the digest it replaced.
    """
    pre = path.read_bytes()
    if pre and not pre.endswith((b"\n", b"\r")):
        print("REFUSED append to " + _label(path) + " by " + writer)
        print("  !! the ledger does not END with a line terminator, so an append would JOIN its last line - repair "
              "the artifact, never the appender (C16). Nothing was written.")
        raise WriteRefused(1)
    if not lines:
        print("REFUSED append to " + _label(path) + " by " + writer)
        print("  !! no lines were declared: an append with nothing to add cannot leave a receipt that says "
              "anything (C16). Nothing was written.")
        raise WriteRefused(1)
    for ln in lines:
        if "\n" in ln or "\r" in ln:
            print("REFUSED append to " + _label(path) + " by " + writer)
            print("  !! a 'line' carries its own terminator " + repr(ln) + " - a terminator smuggled inside a line "
                  "is a rewrite of the ledger's convention wearing an append's clothes (C16). Nothing was written.")
            raise WriteRefused(1)
    suffix = "".join(ln + lineterminator for ln in lines).encode(encoding)
    pre16 = _sha16(path)
    backup_path: Path | None = _backup(path, writer) if backup else None
    if journal:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".wg_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(pre + suffix)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    on_disk = path.read_bytes()
    faults = suffix_faults(pre, on_disk, suffix)
    if faults:
        raise WriteRefused("FAIL-CLOSED: append_lines post-write verification failed for " + str(path) + ": "
                           + str(faults))
    rep = WriteReport(path=str(path), writer=writer, mode="append_lines", owned_keys=[], touched=[], added=len(lines),
                      rows=len(on_disk.decode(encoding, "replace").splitlines()), kind="lines",
                      backup=str(backup_path) if backup_path else None, pre_sha16=pre16, post_sha16=_sha16(path))
    if journal:
        rep.record()
    return rep


def write_document(path: Path, text: str, *, writer: str, owned_keys: set[str],
                   backup: bool = False, journal: bool = True) -> WriteReport:
    """Write a WHOLE-DOCUMENT artifact (JSON/YAML/text) crash-safely, or refuse (D-401/I1).

    A document has no cells, so the cell invariant cannot be applied to it: the only legal declaration is a
    whole-file regeneration, and anything else is REFUSED - "the guard ran" must never be readable as "every
    writer's cells were protected". `backup` defaults to False because a DERIVED artifact's pre-image is
    regenerable by definition: evidence keeps its backups (R-D410), derived output does not need one - while the
    receipt still records the pre-image it replaced.
    """
    if owned_keys != {OWNED_ANY}:
        print("REFUSED document write to " + _label(path) + " by " + writer)
        print("  !! a document is not cell-partitioned, so owned_keys=" + str(sorted(owned_keys)) + " cannot be "
              "honoured (D-401); declare OWNED_ANY for a whole-file regeneration")
        raise WriteRefused(1)
    pre16 = _sha16(path)
    backup_path: Path | None = _backup(path, writer) if backup else None
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".wg_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if path.read_text(encoding="utf-8") != text:
        raise WriteRefused("FAIL-CLOSED: post-write verification failed for " + str(path)
                           + ": the bytes on disk are not the bytes written (C6)")
    rep = WriteReport(path=str(path), writer=writer, mode="regenerate", owned_keys=sorted(owned_keys),
                      touched=[], rows=0, kind="document",
                      backup=str(backup_path) if backup_path else None,
                      pre_sha16=pre16, post_sha16=_sha16(path))
    if journal:
        rep.record()
    return rep


def declared_writers() -> tuple[dict[str, list[tuple[str, str]]], dict]:
    """Map every declared writer_of_record to its (artifact, guard_exemption) pairs + the coverage ceiling."""
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    import yaml
    if not OWNERSHIP.exists():
        raise SystemExit("FAIL-CLOSED (D-401): config/artifact_ownership.yaml is absent - the ownership "
                         "declaration is the ONLY source for who writes what, so nothing can be audited")
    doc = yaml.safe_load(OWNERSHIP.read_text(encoding="utf-8")) or {}
    out: dict[str, list[tuple[str, str]]] = {}
    for name, spec in (doc.get("artifacts") or {}).items():
        w = str((spec or {}).get("writer_of_record") or "")
        if w:
            out.setdefault(w, []).append((str(name), str((spec or {}).get("guard_exemption") or "")))
    return out, dict(doc.get("guard_coverage") or {})


def guard_call_sites(path: Path) -> tuple[bool, str]:
    """AST-scan a script for a REAL guard call site: an import PLUS a call, never a mention.

    A grep for the module name matches a comment or a string; an import with no call is a script that declares
    the discipline and does not apply it - the exact state in which BUG-478 blanked 148 owner cells.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return False, "unparseable (" + type(exc).__name__ + ")"
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.endswith("write_guard"):
                names |= {a.asname or a.name for a in node.names}
            else:
                # `from lib import write_guard` is the repo's OWN idiom and was INVISIBLE here (BUG-492, measured
                # 2026-09-25): the audit reported DRIFT for two writers that genuinely CALL the guard, and a false
                # DRIFT teaches the owner to ignore the rail exactly as a false OK does.
                names |= {a.asname or a.name for a in node.names if a.name == "write_guard"}
        elif isinstance(node, ast.Import):
            names |= {a.asname or a.name.split(".")[0] for a in node.names if a.name.endswith("write_guard")}
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        fn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        root = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
        # A guard call must be BOUND by an import above: `write_guard.x(...)` with no import of write_guard is
        # not a call site, it is an unfalsifiable mention (BUG-492). The former `or root == "write_guard"` clause
        # accepted it, which made the rail's own OK unauditable.
        if fn in GUARD_CALLS and (fn in names or root in names):
            calls.append(fn)
    if not names:
        return False, "never imports the guard"
    if not calls:
        return False, "imports the guard but CALLS nothing (" + ", ".join(sorted(names)) + ")"
    return True, "calls " + ", ".join(sorted(set(calls)))


def audit() -> int:
    """Join the DECLARED writer_of_record set to reality (D-401/I1): who actually goes through the guard.

    MEASURED 2026-09-25: 0 of 6 declared script writers imported this module, so the ownership invariant that
    exists to prevent BUG-478 was DECLARED and UNENFORCED. A writer with no call site is therefore either DRIFT
    (nobody declared why) or a DECLARED, REASONED exemption counted against a SHRINK-ONLY ceiling - the debt is
    loud, joined to reality, and cannot grow by edit. Tri-state (BUG-457): 0 all guarded | 1 drift | 2 owed.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from lib.measure import emit_metric
    writers, cov = declared_writers()
    guarded: list[str] = []
    unguarded: list[str] = []
    non_code: list[str] = []
    drift: list[str] = []
    for w, pairs in sorted(writers.items()):
        reasons = [r for _, r in pairs if r]
        if not w.endswith(".py"):
            if reasons:
                non_code.append(w + " (declared non-script: " + reasons[0][:100] + ")")
            else:
                drift.append("writer_of_record " + w + " is not a script and declares no guard_exemption - the "
                             "guard's jurisdiction is code, and that has to be SAID, not assumed")
            continue
        p = REPO / w
        if not p.exists():
            drift.append("declared writer_of_record " + w + " does not exist (declared by "
                         + ", ".join(a for a, _ in pairs) + ") - a writer nobody can inspect enforces nothing")
            continue
        ok, detail = guard_call_sites(p)
        if ok:
            guarded.append(w + " (" + detail + ")")
        elif reasons:
            unguarded.append(w + " (" + detail + "; declared exemption: " + reasons[0][:130] + ")")
        else:
            drift.append("declared writer_of_record " + w + " " + detail + " and declares no guard_exemption - "
                         "the D-401 ownership invariant is unenforced for it (BUG-478 class)")
    ceiling = int(cov.get("max_unguarded", -1))
    if not cov:
        drift.append("config/artifact_ownership.yaml declares no guard_coverage.max_unguarded - an unguarded "
                     "writer count with no ceiling can grow silently (BUG-491 class)")
    elif ceiling < 0:
        drift.append("guard_coverage declares max_unguarded with no numeric max - a ceiling with no number is a "
                     "comment")
    elif len(unguarded) > ceiling:
        drift.append("guard coverage: " + str(len(unguarded)) + " declared script writer(s) do not call the "
                     "guard, above the SHRINK-ONLY ceiling " + str(ceiling) + " - the audit is not a formality, "
                     "and an exemption may never RAISE this number (that is a decision, not an edit)")
    total = len(guarded) + len(unguarded)
    emit_metric("guard_writers_guarded", float(len(guarded)),
                population="every script declared as writer_of_record in config/artifact_ownership.yaml",
                denominator=total, ruler="config/artifact_ownership.yaml",
                note=str(len(unguarded)) + " unguarded (declared debt, ceiling " + str(ceiling) + "); "
                     + str(len(non_code)) + " declared non-script writer(s)")
    for g in guarded:
        print("  ok  guarded: " + g[:150])
    for u in unguarded:
        print("  ->  UNGUARDED (declared debt): " + u[:230])
    for n in non_code:
        print("  ok  not code: " + n[:150])
    if drift:
        print("FAIL write_guard audit (D-401/I1):")
        for d in drift:
            print("  !!", d)
        return 1
    if unguarded:
        print("owner-owed (loud, NOT fatal - BUG-457): " + str(len(guarded)) + "/" + str(total) + " declared "
              "script writer(s) call the guard; the shrink-only ceiling is " + str(ceiling) + " - routing one "
              "through the guard LOWERS it")
        return 2
    print("ok write_guard audit: all " + str(total) + " declared script writer(s) call the guard (D-401/I1)")
    return 0


def _selftest_counts() -> tuple[int, int]:
    """The two counts the selftest's verdict PRINTS, DERIVED from the selftest that just ran (BUG-492 class).

    MEASURED 2026-09-27: the verdict claimed "13 invariants ... the 5 expected refusals" while the body held 10
    numbered invariants and 6 refusal sites, and HEAD claimed "10 ... the 5" before the append_lines work. A
    number in prose that nothing measures is the defect BUG-582 names, one level down: it drifts the moment an
    invariant is added, and the verdict is the one line a reader trusts. So both are READ off the source of the
    function that just ran - the numbered `# N.` invariants and the `except WriteRefused` refusal sites - and
    counting beats transcribing (the session_seed rule: a derived count is never restated).
    """
    import inspect as _inspect
    import re as _re

    src = _inspect.getsource(selftest)
    # a numbered comment may DECLARE A RANGE ("# 11-13." tells the reader three invariants), so the count is
    # the SIZE of the spans the author wrote, not the number of comments - and it is the author's own claim.
    spans = _re.findall(r"^\s+# (\d+)(?:-(\d+))?\.", src, _re.M)
    invariants = sum((int(hi) - int(lo) + 1) if hi else 1 for lo, hi in spans)
    return invariants, src.count("except WriteRefused")


def selftest() -> int:
    """Assert the refusals this module claims, on a throwaway artifact. A guard nobody tested is a hope.

    The EXPECTED refusals are asserted with their output captured: printing them with the same `!!` token a real
    offence carries made `just health` show FAIL-looking lines that were not failures (hygiene, 2026-09-25).
    """
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        p = Path(td) / "a.csv"
        base = [{"item_id": "R001", "mine": "x", "owner": "KEEP"}]
        p.write_text("item_id,mine,owner\nR001,x,KEEP\n", encoding="utf-8")
        # 1. an owned edit lands and preserves the foreign cell
        rep = write_rows(p, [{"item_id": "R001", "mine": "y"}],
                         owned_keys={"mine"}, writer="selftest", backup=False, journal=False)
        got = read_rows(p)[0]
        assert got["mine"] == "y" and got["owner"] == "KEEP", f"merge failed: {got}"
        assert rep.touched == ["mine"], f"touched={rep.touched}"
        # 2. an edit to a foreign cell is REFUSED, and nothing is written
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                write_rows(p, [{"item_id": "R001", "mine": "y", "owner": "DESTROYED"}],
                           owned_keys={"mine"}, writer="selftest", backup=False, journal=False)
            raise AssertionError("a foreign-cell edit was NOT refused")
        except WriteRefused:
            pass
        assert read_rows(p)[0]["owner"] == "KEEP", "a refused write still mutated the artifact"
        # 3. a row-count change is refused unless OWNED_ANY is declared
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                write_rows(p, [], owned_keys={"mine"}, writer="selftest", backup=False, journal=False)
            raise AssertionError("a row-count change was NOT refused")
        except WriteRefused:
            pass
        # 4. OWNED_ANY is honoured (a declared regeneration)
        rep = write_rows(p, [{"item_id": "R001", "mine": "z", "owner": "REGEN"}],
                         owned_keys={OWNED_ANY}, writer="selftest", backup=False, journal=False)
        assert rep.touched and read_rows(p)[0]["owner"] == "REGEN"
        # 5. a DOCUMENT write without OWNED_ANY is REFUSED (a document has no cells to arbitrate)
        d = Path(td) / "d.json"
        d.write_text('{"a": 1}' + chr(10), encoding="utf-8")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                write_document(d, '{"a": 2}' + chr(10), writer="selftest", owned_keys={"a"},
                               backup=False, journal=False)
            raise AssertionError("a cell-scoped document write was NOT refused")
        except WriteRefused:
            pass
        assert d.read_text(encoding="utf-8") == '{"a": 1}' + chr(10), "a refused document write still mutated it"
        # 6. an OWNED_ANY document write lands, and its receipt carries the PRE-image it replaced
        rep = write_document(d, '{"a": 2}' + chr(10), writer="selftest", owned_keys={OWNED_ANY},
                             backup=False, journal=False)
        assert rep.kind == "document" and rep.pre_sha16 != rep.post_sha16, rep
        assert d.read_text(encoding="utf-8") == '{"a": 2}' + chr(10), "the document write did not land"
        # 7. a declared APPEND lands: the pre-image survives byte-for-byte and the lines keep their terminator
        a = Path(td) / "j.csv"
        a.write_text("item_id,mine,owner\nR001,x,KEEP\n", encoding="utf-8")
        rep = append_rows(a, [{"item_id": "R002", "mine": "new"}], owned_keys={"mine"}, writer="selftest",
                          backup=False, journal=False)
        assert rep.mode == "append" and rep.added == 1 and rep.touched == [], rep
        body = a.read_text(encoding="utf-8")
        assert body == "item_id,mine,owner\nR001,x,KEEP\nR002,new,\n", repr(body)
        assert "\r" not in body, "the append re-terminated lines it does not own (CRLF)"
        # 8. the append INVARIANT: an edited/blanked pre-image row is an offence (the BUG-478 class), and the API
        #    cannot be used to smuggle it, because an added row may not reuse an existing id
        off = plan_append([{"item_id": "R001", "mine": "x", "owner": "KEEP"}],
                          [{"item_id": "R001", "mine": "x", "owner": "BLANKED"}], {"mine"}, "item_id")
        assert off and "would CHANGE" in off[0], off
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                append_rows(a, [{"item_id": "R001", "mine": "smuggled"}], owned_keys={"mine"}, writer="selftest",
                            backup=False, journal=False)
            raise AssertionError("an id-reusing append was NOT refused")
        except WriteRefused:
            pass
        # 9. an added row may not populate a column the caller does not own
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                append_rows(a, [{"item_id": "R003", "mine": "y", "owner": "I/O"}], owned_keys={"mine"},
                            writer="selftest", backup=False, journal=False)
            raise AssertionError("an append writing a foreign column was NOT refused")
        except WriteRefused:
            pass
        # 10. truncation is an offence, and a refused append wrote nothing
        off = plan_append([{"item_id": "R001", "mine": "x"}], [], {"mine"}, "item_id")
        assert off and "truncation" in off[0], off
        assert a.read_text(encoding="utf-8") == body, "a refused append still mutated the artifact"
        # 11-13. the SUFFIX-ONLY append rule (BUG-560/D-2685): printed BY NAME, because a mutation is SEEN through
        #    its own marker (D-2676(iv)) and an assert names a line, not a control.
        _ctl = [("suffix_only_append_reports_a_changed_pre_image", bool(suffix_faults(b"a\n", b"z\n", b"")), True),
                ("suffix_only_append_reports_bytes_the_writer_did_not_declare",
                 bool(suffix_faults(b"a\n", b"a\nx\n", b"")), True),
                ("suffix_only_append_is_silent_for_the_declared_suffix",
                 bool(suffix_faults(b"a\n", b"a\nb\n", b"b\n")), False)]
        for _n, _got, _want in _ctl:
            print(("ok   selftest/" if _got == _want else "FAIL selftest/") + _n)
        if any(_got != _want for _n, _got, _want in _ctl):
            return 1
        led = Path(td) / "led.csv"
        led.write_text("a,b\r\nc,d\n", encoding="utf-8")   # a MIXED-terminator ledger (the MEASURED fixlog shape)
        _pre = led.read_bytes()
        _rep = append_lines(led, ["e,f"], writer="selftest", lineterminator="\n", journal=False)
        _post = led.read_bytes()
        assert _post[:_pre.__len__()] == _pre, "the append changed the pre-image bytes"
        assert _post[_pre.__len__():] == b"e,f\n", repr(_post[_pre.__len__():])
        assert _rep.added == 1 and _rep.mode == "append_lines", _rep
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                append_lines(led, ["g,h\n"], writer="selftest", journal=False)
            raise AssertionError("a line carrying its own terminator was NOT refused")
        except WriteRefused:
            pass
        assert led.read_bytes() == _post, "a refused append still mutated the ledger"
        # 14-16. the PRE-IMAGE STORE'S CONTAINMENT rule (BUG-560 class): the artifact whose pre-image a writer
        #    keeps must BE an artifact of the audited tree, or the store an auditor reads cannot be read.
        _outside = Path(td) / "a.csv"                       # a system-temp fixture: OUTSIDE the audited tree
        _deposits = sorted(q.name for q in BACKUP_DIR.iterdir()) if BACKUP_DIR.is_dir() else []
        _pre_rows = read_rows(_outside)
        _refused = False
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                write_rows(_outside, [{"item_id": "R001", "mine": "z2", "owner": "REGEN"}], owned_keys={OWNED_ANY},
                           writer="selftest", journal=False)   # backup=DEFAULT True on purpose: the leak's own call
        except WriteRefused:
            _refused = True
        _post = sorted(q.name for q in BACKUP_DIR.iterdir()) if BACKUP_DIR.is_dir() else []
        _ctl2 = [
            ("an_out_of_tree_artifact_is_reported_where_its_pre_image_would_land", bool(pre_image_faults(_outside)), True),
            ("an_artifact_of_the_tree_owns_its_pre_image",
             pre_image_faults(REPO / "config" / "artifact_ownership.yaml"), []),
            ("the_pre_image_store_refuses_an_out_of_tree_artifact", _refused, True),
            ("a_refused_pre_image_deposits_nothing_and_writes_nothing",
             _post == _deposits and read_rows(_outside) == _pre_rows, True),
        ]
        for _n, _got, _want in _ctl2:
            print(("ok   selftest/" if _got == _want else "FAIL selftest/") + _n)
        if any(_got != _want for _n, _got, _want in _ctl2):
            return 1
    _inv, _ref = _selftest_counts()
    print("ok write_guard selftest: " + str(_inv) + " invariants hold (own-cell edit lands, foreign-cell edit refused, row-count "
          "change refused, OWNED_ANY honoured, cell-scoped DOCUMENT write refused, document pre-image receipted, a "
          "declared APPEND lands without re-terminating lines, an edit to the pre-image is an offence, a foreign "
          "column in an added row is refused, truncation is refused and a refused append writes nothing, a SUFFIX-ONLY append to a mixed-terminator ledger leaves the pre-image bytes as a prefix of the post-image, and a terminator smuggled inside a line is refused); the " + str(_ref) + " "
          "expected refusals are asserted with their output captured, and a PRE-IMAGE IS KEPT ONLY FOR AN "
          "ARTIFACT OF THE AUDITED TREE (a fixture's pre-image would land in the ONE store "
          "an auditor reads, BUG-560)")
    return 0


def main() -> int:
    """CLI: --selftest asserts the guard's own refusals before anything trusts it."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.audit:
        return audit()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
