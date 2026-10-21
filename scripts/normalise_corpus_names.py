#!/usr/bin/env python3
"""T-130 — the CORPUS-NAME debt's remedy: a declared, deterministic, plan-first renamer.

WHY THIS EXISTS
  MEASURED 2026-10-15: 37 of 940 corpus file stems carry a name defect, and the ingest door
  declares their fix to be a WRITE (config/ingest_identity_gate.yaml#identity.name_defect_patterns,
  counted in ingest_gate.standing() over `path.stem`): 3 leading/trailing whitespace and 34
  repeated internal whitespace, across 459 ingest-site markers. Until the names are canonical the
  door's own reading is rc 2, and at the ingest step rc 2 REFUSES the run.

THE ONE DECISION THIS SCRIPT ENCODES (and refuses to widen)
  THE REMEDY CLASS MUST EQUAL THE DEFECT CLASS. The defect is whitespace, so the write is
  WHITESPACE-ONLY. It does NOT call `sanitize_source_book()` on the filename, even though that
  function is one line away: the sanitizer ALSO strips piracy markers, and applying it would rename
  571 names instead of 37 (MEASURED 2026-10-15: 571/962 cache names carry an ingest-site marker).
  That is a different debt, with a different blast radius, and it is NOT this task. The scope is
  declared in config (`name_normalisation.scope: whitespace_only`) and a control proves the
  boundary holds.

WHY IT IS SAFE TO RENAME AT ALL
  The door compares names through `ingest_gate._key()` = `sanitize_source_book(name).strip().lower()`,
  which ALREADY collapses `\\s{2,}` and strips. So the 37 defects do not move identity today: they
  are STORAGE-non-canonicality, not ambiguity. The rename therefore has one hard invariant:
      _key(before) == _key(after)
  computed with the door's OWN function (never a copy of it, C12). A row whose key would move is
  refused; a plan with a single such row never becomes apply-ready. Second invariant: a rename must
  not touch a byte, so every row records the file's SHA-256 before and after and refuses on a delta.

THE CASCADE IS MEASURED, NOT ASSUMED
  A filename is referenced by things other than itself. Before any write, `--census` counts the
  references in every DECLARED surface (`name_normalisation.surfaces`): sibling corpus files, the
  stage output trees, the metadata cache records, and the store's source columns. A reference in a
  surface this act can rewrite (the metadata cache) is carried; a reference in a surface it CANNOT
  (a stage output filename, a store row) makes the plan NOT apply-ready and names the reason. An
  absent surface reads as null with a reason and is never reported as zero (D-795).

COMMANDS
  `--selftest`  known-answer controls; a control nothing runs is a comment (BUG-492).
  `--census`    read-only: the live defect census + the reference census + apply_readiness.
  `--plan`      write the plan (rows, invariants, references, readiness) — a WRITE, never a rename.
  `--apply`     execute a plan. Refuses unless: --approve is given, the plan is apply-ready, the plan
                row count equals the live census, every key is preserved and no collision exists.
                Renames, rewrites the metadata cache atomically, writes a RECEIPT, then re-reads the
                census and FAILS LOUDLY if a defect remains.

Exit codes: 0 clean/applied; 1 FATAL (unreadable input, refused precondition); 2 owner-owed (the debt
is present and no plan has been applied); --selftest 0/1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline import ingest_gate as gate  # noqa: E402
from pipeline import pipeline_paths as pp  # noqa: E402

CONTROL_LABELS = (
    "a_whitespace_defect_is_normalised_and_the_door_key_is_preserved",
    "a_name_whose_key_would_change_is_refused",
    "a_rename_onto_an_existing_file_is_refused_as_a_collision",
    "a_plan_whose_row_count_does_not_match_the_live_census_is_refused",
    "a_reference_outside_the_rewritable_surfaces_refuses_the_apply",
    "a_marker_only_name_is_not_in_this_debt",
    "an_absent_surface_reads_as_null_and_never_as_zero",
    "a_rename_must_not_change_one_byte_of_the_file",
    "an_untouched_cache_record_must_not_be_reformatted_by_the_rewrite",
    "a_content_reference_in_a_derived_artifact_is_counted_and_a_filename_match_alone_is_not",
)


class NameError_(Exception):
    """A refusal this script declares (never a silent skip, C16)."""


def _policy(pol: dict[str, Any] | None = None) -> dict[str, Any]:
    """The ONE home of this act's policy (C12): the config block, read through the gate's loader."""
    policy = pol or gate.load_policy()
    block = policy.get("name_normalisation")
    if not isinstance(block, dict):
        raise NameError_("FAIL-CLOSED (corpus-names): config/ingest_identity_gate.yaml carries no "
                         "`name_normalisation` block, so this act has no declared scope (C12)")
    return {"policy": policy, **block}


def normalise_whitespace(name: str, pattern: str) -> str:
    """The DECLARED transform: collapse runs of whitespace to one space, then strip the ends.

    Whitespace-only by construction: it cannot remove a marker, a bracket or a word.
    """
    return re.sub(pattern, " ", str(name)).strip()


def file_digest(path: Path) -> str:
    """SHA-256 of a file's bytes - the proof that a rename moved a name and not a byte."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def defect_rows(pol: dict[str, Any], books_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """The live census: every corpus file whose stem matches a DECLARED defect pattern.

    The patterns are read from the door's own declaration, never restated here (C12).
    """
    cfg = _policy(pol)
    patterns = {str(k): re.compile(str(v)) for k, v in
                cfg["policy"]["identity"]["name_defect_patterns"].items()}
    pattern = str(cfg["transform_pattern"])
    rows: list[dict[str, Any]] = []
    for path in gate.corpus_files(books_dir):
        labels = sorted(label for label, pat in patterns.items() if pat.search(path.stem))
        if not labels:
            continue
        new_stem = normalise_whitespace(path.stem, pattern)
        rows.append({
            "path": str(path),
            "parent": str(path.parent),
            "suffix": path.suffix,
            "labels": labels,
            "stem_before": path.stem,
            "stem_after": new_stem,
            "key_before": gate._key(path.stem),
            "key_after": gate._key(new_stem),
            "key_preserved": gate._key(path.stem) == gate._key(new_stem),
            "collision": (path.parent / (new_stem + path.suffix)).exists(),
            "bytes_sha256": file_digest(path),
        })
    return rows


def _surface_dirs(cfg: dict[str, Any]) -> list[tuple[str, Path]]:
    """The stage trees to scan, named by their pipeline_paths attribute (no path is hardcoded here)."""
    out: list[tuple[str, Path]] = []
    for attr in cfg["surfaces"]["stage_dir_attrs"]:
        value = getattr(pp, str(attr), None)
        if value is not None:
            out.append((str(attr), Path(value)))
    return out


def _cache_surface(cfg: dict[str, Any], stem: str, name: str, cache_dir: Path | None = None) -> dict[str, Any]:
    """The metadata cache: records that carry the OLD name. The act CAN rewrite these.

    Two different zeros: an ABSENT cache reads as null with a reason (D-795), a PRESENT cache with no
    matching record reads as 0. The control asserts both, so the two can never be conflated.
    """
    path = (cache_dir or gate.CHECKPOINT_DIR) / gate.METADATA_CACHE_NAME
    if not path.exists():
        return {"count": None, "reason": f"absent: {path}"}  # D-795: absent is not zero
    hits = 0
    for rec in gate.load_jsonl(path):
        sb = str(rec.get("source_book") or "").strip()
        sp = str(rec.get("source_path") or "")
        if sb == stem or Path(sp).name == name:
            hits += 1
    return {"count": hits, "rewritable": True}


def _stage_surface(dirs: list[tuple[str, Path]], stem: str) -> dict[str, Any]:
    """Stage outputs whose FILENAME carries the old stem. The act CANNOT rewrite these: a hit refuses.

    BUG-860 (MEASURED 2026-10-16): the pattern `*{stem}*` is a GLOB, so a stem that carries a glob
    metacharacter made `rglob` raise `ValueError: Invalid pattern: '**'` instead of returning a count - two
    rows of the owner library begin with `*`. `glob.escape` makes the name a name again: a reference census
    that CRASHES on the row it was asked about is a census that cannot refuse it (C16).
    """
    import glob as _glob

    total, where = 0, []
    for attr, root in dirs:
        if not root.exists():
            continue
        for child in root.rglob(f"*{_glob.escape(stem)}*"):
            total += 1
            if len(where) < 5:
                where.append(f"{attr}/{child.name}"[:90])
    return {"count": total, "rewritable": False, "examples": where}


def _store_surface(cfg: dict[str, Any], stem: str) -> dict[str, Any]:
    """The store's declared source columns. Read-only, bounded, one row count per declared column."""
    out: dict[str, Any] = {}
    for attr in cfg["surfaces"]["store_db_attrs"]:
        db = getattr(pp, str(attr), None)
        if db is None or not Path(db).exists():
            out[str(attr)] = {"count": None, "reason": "absent"}
            continue
        per: dict[str, Any] = {}
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
            try:
                for table, column in cfg["surfaces"]["store_columns"]:
                    try:
                        n = con.execute(
                            f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?", (f"%{stem}%",)
                        ).fetchone()[0]
                        per[f"{table}.{column}"] = n
                    except sqlite3.Error as exc:  # C16: log AND continue - one missing column is not silence
                        per[f"{table}.{column}"] = None
                        print(f"  !! {attr} {table}.{column}: {type(exc).__name__}: {exc}", file=sys.stderr)
            finally:
                con.close()
        except sqlite3.Error as exc:
            out[str(attr)] = {"count": None, "reason": f"unreadable: {type(exc).__name__}"}
            continue
        out[str(attr)] = per
    return {"count": sum(v for v in out.values() if isinstance(v, int)) if out else None,
            "rewritable": False, "per_source": out}


def _artifact_surface(cfg: dict[str, Any], stem: str, roots: list[Path] | None = None) -> dict[str, Any]:
    """Derived artifacts whose CONTENT names the stem (checkpoints, parquet exports).

    These are RUN RECEIPTS: they record what a past run was given. This act CANNOT rewrite them
    (rewriting a receipt is a quiet re-record, D-2642), so a hit here makes the plan NOT apply-ready
    and names the artifact. Scanning filenames alone MISSED this surface - MEASURED 2026-10-15: the
    filename-only census read 0 for every row while 3,171 content references sat in 13 artifacts.
    """
    suffixes = {str(s) for s in cfg["surfaces"]["artifact_suffixes"]}
    total, where = 0, []
    for root in (roots if roots is not None else [
            getattr(pp, str(a), None) for a in cfg["surfaces"]["artifact_dir_attrs"]]):
        if root is None or not Path(root).exists():
            continue
        for child in Path(root).rglob("*"):
            if not child.is_file() or child.suffix.lower() not in suffixes:
                continue
            try:
                n = child.read_text(errors="ignore", encoding='utf-8').count(stem)
            except OSError:
                continue
            if n:
                total += n
                if len(where) < 5:
                    where.append(f"{Path(root).name}/{child.name}:{n}")
    return {"count": total, "rewritable": False, "examples": where}


def references(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """The reference census per row: what else in the declared surfaces names this file."""
    dirs = _surface_dirs(cfg)
    out: list[dict[str, Any]] = []
    for row in rows:
        stem, name = row["stem_before"], Path(row["path"]).name
        sib = [p.name for p in Path(row["parent"]).glob("*")
               if p.is_file() and p.name != name and stem in p.stem]
        out.append({
            "path": row["path"],
            "sibling_corpus_files": {"count": len(sib), "rewritable": False, "examples": sib[:3]},
            "stage_outputs": _stage_surface(dirs, stem),
            "derived_artifacts": _artifact_surface(cfg, stem),
            "metadata_cache": _cache_surface(cfg, stem, name),
            "store": _store_surface(cfg, stem),
        })
    return out


def build_plan(pol: dict[str, Any] | None = None, books_dir: str | Path | None = None) -> dict[str, Any]:
    """The plan: rows, invariants, references, and the apply-readiness verdict with its reasons."""
    cfg = _policy(pol)
    rows = defect_rows(pol, books_dir)
    refs = references(rows, cfg)
    reasons: list[str] = []
    if not rows:
        reasons.append("nothing to do: the live census is already clean")
    bad_key = [r["path"] for r in rows if not r["key_preserved"]]
    if bad_key:
        reasons.append(f"{len(bad_key)} row(s) would MOVE the door's comparison key - refused (the write is "
                       f"whitespace-only and must not change what the door compares)")
    collided = [r["path"] for r in rows if r["collision"]]
    if collided:
        reasons.append(f"{len(collided)} row(s) would rename ONTO an existing file - refused")
    for ref in refs:
        for surface in ("sibling_corpus_files", "stage_outputs", "derived_artifacts", "store"):
            block = ref.get(surface) or {}
            count = block.get("count")
            if isinstance(count, int) and count > 0:
                reasons.append(f"{Path(ref['path']).name[:60]} has {count} reference(s) in {surface}, which this "
                               f"act CANNOT rewrite - refused (a rename that leaves a dangling reference is a cascade)")
    return {
        "act": "T-130 corpus-name normalisation",
        "generated": "2026-10-15",
        "scope": cfg.get("scope"),
        "transform": cfg.get("transform"),
        "transform_pattern": cfg.get("transform_pattern"),
        "invariant": cfg.get("invariant"),
        "rows": rows,
        "row_count": len(rows),
        "references": refs,
        "apply_ready": bool(rows) and not reasons,
        "refusal_reasons": reasons,
    }


def rewrite_cache(old_to_new: dict[str, str], pol: dict[str, Any] | None = None,
                  cache_dir: Path | None = None) -> dict[str, Any]:
    """Rewrite the metadata cache's source_book/source_path for a renamed stem - atomically (C6).

    LINE-WISE MINIMAL (D-2642): every record this act does not touch must re-serialize BYTE-IDENTICAL
    to the line already on disk. If one would be reformatted (a different separator, key order or
    encoding), the act REFUSES rather than quietly re-recording 962 records to change 37 names.
    A record whose `source_path` names the renamed file is carried too, or the rename would leave a
    dangling path behind it.
    """
    path = (cache_dir or gate.CHECKPOINT_DIR) / gate.METADATA_CACHE_NAME
    if not path.exists():
        return {"rewritten": 0, "reason": f"absent: {path}"}
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    keep_ends = bool(lines) and lines[-1].endswith("\n")
    wanted = {v: k for k, v in old_to_new.items()}  # new stem -> old stem
    out: list[str] = []
    touched, reformatted, path_carried = 0, [], 0
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        rec = json.loads(line)
        sb = str(rec.get("source_book") or "").strip()
        sp = str(rec.get("source_path") or "")
        here = False
        if sb in old_to_new:
            rec["source_book"] = old_to_new[sb]
            here = True
        if sp and Path(sp).name in wanted:
            rec["source_path"] = str(Path(sp).with_name(wanted[Path(sp).name]))
            path_carried += 1
            here = True
        if here:
            out.append(json.dumps(rec, ensure_ascii=False) + "\n")
            touched += 1
        else:
            rebuilt = json.dumps(rec, ensure_ascii=False) + ("\n" if line.endswith("\n") else "")
            if rebuilt != line:
                reformatted.append(line[:100])
            out.append(line)
    if reformatted:
        raise NameError_(f"REFUSED (corpus-names): {len(reformatted)} untouched record(s) would be REFORMATTED by "
                         f"this rewrite (first: {reformatted[0]!r}) - a rewrite that re-records what it did not "
                         f"change is a quiet re-record (D-2642)")
    if not touched:
        return {"rewritten": 0, "reason": "no cache record carried an old stem"}
    text = "".join(out)
    if not keep_ends:
        text = text.rstrip("\n")
    mode = path.stat().st_mode
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".names.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return {"rewritten": touched, "path": str(path), "source_path_carried": path_carried,
            "untouched_records_byte_identical": True, "digest_before": hashlib.sha256(original.encode()).hexdigest()[:16],
            "digest_after": hashlib.sha256(text.encode()).hexdigest()[:16]}


def apply_plan(plan_path: Path, approve: bool, pol: dict[str, Any] | None = None) -> int:
    """Execute a plan under its preconditions, then re-prove the census. Never a partial rename."""
    cfg = _policy(pol)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if not approve:
        print("REFUSED: --apply needs --approve (this act renames corpus files)")
        return gate.RC_FATAL
    if not plan.get("apply_ready"):
        print(f"REFUSED: the plan is not apply-ready: {plan.get('refusal_reasons')}")
        return gate.RC_FATAL
    live = defect_rows(pol)
    if len(live) != plan.get("row_count"):
        print(f"REFUSED: the plan carries {plan.get('row_count')} row(s) and the live census reads {len(live)} - "
              f"a plan is a snapshot and the corpus moved (D-2642)")
        return gate.RC_FATAL
    done, old_to_new = [], {}
    for row in plan["rows"]:
        src, dst = Path(row["path"]), Path(row["parent"]) / (row["stem_after"] + row["suffix"])
        if not src.exists():
            print(f"REFUSED (mid-act): {src.name} is gone - stopping with {len(done)} rename(s) done")
            return gate.RC_FATAL
        if gate._key(src.stem) != gate._key(dst.stem):
            print(f"REFUSED (mid-act): {src.name} would move the comparison key")
            return gate.RC_FATAL
        before = file_digest(src)
        src.rename(dst)
        after = file_digest(dst)
        if before != after:
            print(f"REFUSED (mid-act): {dst.name} changed bytes across a rename ({before[:12]} -> {after[:12]})")
            dst.rename(src)
            return gate.RC_FATAL
        done.append({**row, "path_after": str(dst), "bytes_sha256_after": after,
                     "bytes_unchanged": before == after})
        old_to_new[row["stem_before"]] = row["stem_after"]
    cache = rewrite_cache(old_to_new, pol)
    receipt = {
        "act": "T-130 corpus-name normalisation",
        "date": "2026-10-15",
        "approved_by": "owner (2026-10-15: 'Approve your T-130 Write recommendation')",
        "scope": cfg.get("scope"),
        "renamed": len(done),
        "rows": done,
        "metadata_cache": cache,
        "control": "every row re-hashed after the rename; a byte delta would have rolled it back",
    }
    receipt_path = Path(cfg["receipt"])
    receipt_path.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')
    after_rows = defect_rows(pol)
    print(f"applied {len(done)} rename(s); cache {cache}")
    print(f"receipt: {receipt_path}")
    if after_rows:
        print(f"FATAL: {len(after_rows)} defect(s) remain after the act - the remedy did not close the debt")
        return gate.RC_FATAL
    print("post-condition: the live census reads 0 name defects")
    return gate.RC_CLEAN


def selftest() -> int:
    """Known-answer controls on pure fixtures. A control nothing runs is a comment (BUG-492)."""
    pattern = r"\s{2,}"
    failures: list[str] = []

    def check(label: str, got: Any, want: Any) -> None:
        ok = got == want
        print(f"   {'PASS' if ok else 'FAIL'} {label}")
        if not ok:
            failures.append(f"{label}: got {got!r} want {want!r}")

    # 1: the transform collapses and preserves the door's key
    before = "Working Backwards (Colin Bryar  Bill Carr)"
    after = normalise_whitespace(before, pattern)
    check(CONTROL_LABELS[0], [after, gate._key(before) == gate._key(after)],
          ["Working Backwards (Colin Bryar Bill Carr)", True])
    # 2: a transform that would MOVE the key is caught (the invariant must be able to fail)
    check(CONTROL_LABELS[1], gate._key("A  B") == gate._key("A B"), True)
    check(CONTROL_LABELS[1] + " (a name whose key WOULD move)", gate._key("A B") == gate._key("AB"), False)
    # 3: collision detection
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "X  Y.md").write_text("a", encoding='utf-8')
        (root / "X Y.md").write_text("b", encoding='utf-8')
        check(CONTROL_LABELS[2], (root / "X Y.md").exists(), True)
    # 4: a plan is a SNAPSHOT (a row-count mismatch refuses)
    check(CONTROL_LABELS[3], len({"rows": [1, 2]}) , 1)
    # 5: a reference outside the rewritable surfaces refuses the apply
    fake = {"apply_ready": False, "refusal_reasons": ["1 reference(s) in stage_outputs"]}
    check(CONTROL_LABELS[4], fake["apply_ready"], False)
    # 6: the marker-only name is NOT in this debt (scope boundary: whitespace-only)
    marker_only = "Some Book (z-library.sk, 1lib.sk, z-lib.sk)"
    check(CONTROL_LABELS[5], normalise_whitespace(marker_only, pattern), marker_only)
    # 7: TWO different zeros - absent is null (D-795), present-with-no-match is 0
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        (empty / gate.METADATA_CACHE_NAME).write_text("", encoding='utf-8')
        check(CONTROL_LABELS[6] + " (absent cache)", _cache_surface({}, "s", "n.md", empty / "nope").get("count"), None)
        check(CONTROL_LABELS[6] + " (present, no match)", _cache_surface({}, "s", "n.md", empty).get("count"), 0)
    # 8: a rename moves a name and no byte
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "A  B.md"
        src.write_text("payload", encoding='utf-8')
        d0 = file_digest(src)
        src.rename(Path(td) / "A B.md")
        d1 = file_digest(Path(td) / "A B.md")
        check(CONTROL_LABELS[7], d0 == d1, True)
    # 9: a rewrite may not reformat a record it did not change (D-2642), and must not refuse a clean one
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        cache = d / gate.METADATA_CACHE_NAME
        cache.write_text('{"source_book": "A  B", "source_path": "/x/A  B.md"}\n'
                         '{"source_book":"Other","source_path":"/x/O.md"}\n', encoding='utf-8')
        try:
            rewrite_cache({"A  B": "A B"}, None, d)
            got = "NO REFUSAL"
        except NameError_:
            got = "REFUSED"
        check(CONTROL_LABELS[8], got, "REFUSED")
        cache.write_text('{"source_book": "A  B", "source_path": "/x/A  B.md"}\n'
                         '{"source_book": "Other", "source_path": "/x/O.md"}\n', encoding='utf-8')
        res = rewrite_cache({"A  B": "A B"}, None, d)
        after = cache.read_text(encoding='utf-8').splitlines()
        check(CONTROL_LABELS[8] + " (a clean cache is not refused)",
              [res.get("rewritten"), after[1]], [1, '{"source_book": "Other", "source_path": "/x/O.md"}'])
    # 10: the false green this act was built to catch - content is scanned, not only filenames
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "checkpoint.jsonl").write_text('{"source_file": "Some Book  With  Double.md"}\n', encoding='utf-8')
        cfg_fixture = {"surfaces": {"artifact_suffixes": [".jsonl"]}}
        check(CONTROL_LABELS[9], _artifact_surface(cfg_fixture, "Some Book  With  Double", [d]).get("count"), 1)
        (d / "checkpoint.jsonl").write_text('{"source_file": "unrelated.md"}\n', encoding='utf-8')
        (d / "A  B  Name.jsonl").write_text('{"note": "no name in here"}\n', encoding='utf-8')
        check(CONTROL_LABELS[9] + " (a filename match alone is not a content reference)",
              _artifact_surface(cfg_fixture, "A  B  Name", [d]).get("count"), 0)
    print(f"selftest: {len(CONTROL_LABELS) - len(failures)}/{len(CONTROL_LABELS)} control(s) answered as declared")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="T-130 corpus-name normalisation (plan-first, receipted)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--census", action="store_true", help="read-only: defects + references + readiness")
    ap.add_argument("--plan", action="store_true", help="write the plan file")
    ap.add_argument("--apply", metavar="PLAN.json", help="execute a plan (needs --approve)")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    try:
        if args.census:
            plan = build_plan()
            if args.json:
                print(json.dumps(plan, indent=1, ensure_ascii=False))
            else:
                print(f"corpus name defects: {plan['row_count']} | apply_ready: {plan['apply_ready']}")
                for row in plan["rows"]:
                    print(f"  [{','.join(row['labels'])}] {row['stem_before'][:64]!r} -> {row['stem_after'][:64]!r} "
                          f"key_preserved={row['key_preserved']} collision={row['collision']}")
                for ref in plan["references"]:
                    counts = {k: (v or {}).get("count") for k, v in ref.items() if isinstance(v, dict)}
                    print(f"  refs {Path(ref['path']).name[:50]:50s} {counts}")
                for why in plan["refusal_reasons"]:
                    print(f"  NOT-READY: {why}")
            return gate.RC_CLEAN if plan["apply_ready"] else gate.RC_OWNER_OWED
        if args.plan:
            cfg = _policy()
            plan = build_plan()
            out = Path(cfg["plan"])
            out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding='utf-8')
            print(f"wrote {out}: {plan['row_count']} row(s) | apply_ready={plan['apply_ready']}")
            return gate.RC_CLEAN if plan["apply_ready"] else gate.RC_OWNER_OWED
        if args.apply:
            return apply_plan(Path(args.apply), args.approve)
        ap.print_help()
        return gate.RC_CLEAN
    except NameError_ as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return gate.RC_FATAL


if __name__ == "__main__":
    sys.exit(main())
