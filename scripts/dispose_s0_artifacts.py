#!/usr/bin/env python3
"""dispose_s0_artifacts.py — quarantine the S0 artefacts whose SHAPE is wrong, and repair the checkpoint.

Authority: BUG-918 (S0 converts PDFs into image dumps) / D-3086 (the artefact's shape is declared).

WHAT IT IS FOR. Between 2026-10-17 20:00 and 2026-10-18 00:41 the converter wrote 100 artefacts totalling
2,599.7 MB into the DERIVED tree, because docling's shipped default (`--image-export-mode embedded`) base64-inlines
every figure. 59 of those artefacts carry 5,786 `data:image` blobs between them and 16 are above 30 MB, the largest
895.2 MB for one book. The shape gate now REFUSES such an artefact (`pipeline/stage0_convert.py::verify_artifact`),
but the ones already on disk have to be dealt with, and the CHECKPOINT still says they were converted — so a resume
would SKIP them and the corpus would keep a hole that no later stage could see. That is the future tax this script
pays off: the artefact leaves, and the receipt that described it leaves with it.

FOUR VERDICTS, and why there are four rather than two:

  keep                    conforms to `stage0.artifact` — untouched.
  quarantine_and_reconvert violates the shape AND its container is still on disk — the bytes move to a LOCAL pen,
                          outside Dropbox, and the checkpoint row is dropped so the work is re-converted by the
                          fixed engine. Nothing is `rm`'d: a quarantine is a delete with a receipt and a way back.
  quarantine_refused      violates the shape AND NO container survives anywhere — kept in place and NAMED, because
                          an artefact with no container is the only copy of that text (C23).
  keep_referenced         violates the shape BUT its name is named by a claim in `maxwell.db` — never touched. A
                          defective artefact that already fed the claim store is EVIDENCE, not garbage, and
                          deleting it would destroy the provenance of rows nobody can regenerate cheaply.

WHY A LOCAL PEN AND NOT `pipeline/safe_delete.py`. That guard COPIES into `backup/deletions/` inside the repo, which
is inside the owner's Dropbox: disposing of 2.6 GB of proven-defective derived bytes would upload 2.6 GB and double
it on disk. A backup of garbage is not a backup (D-3034: a declaration must resolve). The bytes here are DERIVED and
re-derivable from a container we hold, so the durable record is the RECEIPT — sha256, size, blob count, container
path — and the bytes rest in a local pen the owner can purge with one command, printed at the end.

Usage:
    python3 scripts/dispose_s0_artifacts.py                 # dry run: write the receipt, move nothing
    python3 scripts/dispose_s0_artifacts.py --apply         # move + repair the checkpoint
    python3 scripts/dispose_s0_artifacts.py --apply --no-checkpoint
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    BOOKS_DIR,
    S0_ARTIFACT_MAX_EMBEDDED_IMAGES,
    S0_ARTIFACT_MAX_MB,
    STAGE0_CHECKPOINT,
)
from pipeline.stage0_convert import EMBEDDED_IMAGE_MARKER

SCHEMA_VERSION = "1.0"
QUARANTINE_ROOT = Path.home() / ".maxwell_quarantine" / "s0_artifacts"
EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "governance" / "evidence"
DB_PATH = Path(__file__).resolve().parent.parent / "knowledge pipeline" / "maxwell.db"


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    """sha256 of a whole file, streamed so a 895 MB artefact does not enter memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def _norm_name(name: str) -> str:
    """Lowercase alphanumerics only — the form two trees can agree on (BUG-800/D-3045: a name is evidence)."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _is_referenced(artefact_name: str, claimed: set[str], prefix: int = 40) -> bool:
    """Is this artefact's name cited by a committed claim?

    MEASURED why exact matching is not enough: `Godel, Escher, Bach-An Eternal Golden Braid (Douglas R. Hofstadter)
    (z-library.sk, 1lib.sk, z-lib.sk).md` is cited by 116 claims, and its name in `primary_source` carries a DIFFERENT
    suffix set than the file on disk — an exact comparison returned False and would have unprotected the most-cited
    book in the corpus. So the comparison is on a normalised PREFIX, and the window is deliberately short: a false
    POSITIVE only leaves a defective artefact in place (cheap, reported), while a false NEGATIVE destroys provenance
    (expensive, irreversible).
    """
    mine = _norm_name(artefact_name)[:prefix]
    return bool(mine) and mine in claimed


def claimed_source_names(db_path: Path) -> set[str]:
    """Normalised prefixes of every book name the CLAIM STORE already cites (D-3034: a name that resolves to a claim
    is evidence, not garbage).

    `fbs.primary_source` is a JSON blob (`{"book": "...md", ...}`), so the name is extracted per row. A malformed blob
    falls back to the raw text rather than being skipped: a parse failure that returned nothing would silently
    UNPROTECT every file it touched.
    """
    if not db_path.exists():
        return set()
    names: set[str] = set()
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for (raw,) in con.execute("select distinct primary_source from fbs where primary_source is not null"):
            if not isinstance(raw, str):
                continue
            book = None
            try:
                parsed = json.loads(raw)
                book = parsed.get("book") if isinstance(parsed, dict) else None
            except (ValueError, TypeError):
                book = None
            for candidate in (book, raw):
                if candidate:
                    norm = _norm_name(Path(str(candidate)).name)[:40]
                    if norm:
                        names.add(norm)
    finally:
        con.close()
    return names


def classify(artefact: Path, container: Path | None, referenced: set[str], since_ts: float,
             native: bool = False) -> dict[str, Any]:
    """One verdict for one artefact, named by a CLOSED vocabulary (the same discipline as the admission door)."""
    size_bytes = artefact.stat().st_size
    text = artefact.read_text(encoding="utf-8", errors="replace")
    blobs = text.count(EMBEDDED_IMAGE_MARKER)
    oversize = size_bytes > S0_ARTIFACT_MAX_MB * 1024 * 1024
    too_many_images = blobs > S0_ARTIFACT_MAX_EMBEDDED_IMAGES
    row: dict[str, Any] = {
        "artefact": str(artefact),
        "artefact_name": artefact.name,
        "size_bytes": size_bytes,
        "embedded_image_blobs": blobs,
        "chars": len(text),
        "native": native,
        "container": str(container) if container else None,
        "container_exists": bool(container and container.exists()),
        "referenced_by_claims": _is_referenced(artefact.name, referenced),
    }
    if not oversize and not too_many_images:
        row.update(verdict="keep", reason="conforms to stage0.artifact")
    elif native:
        #: A native `.md` is the OWNER'S OWN FILE — no engine produced it, so "re-convert" is a word with no referent
        #: (D-3034) and a quarantine would destroy the only copy. MEASURED before the first apply: the checkpoint
        #: holds 940 `format: 'md'` rows beside the converted ones, so this branch is live, not theoretical.
        row.update(
            verdict="keep_native",
            reason="a native .md IS the artefact — there is no container to re-derive it from, so it is never moved",
        )
    elif artefact.stat().st_mtime <= since_ts:
        #: SCOPE BOUNDARY, not a quality judgement. This script's mandate is the artefacts ONE NIGHT produced; a
        #: pre-existing artefact is the PROVENANCE of claims already in `maxwell.db` and is not this act's to remove.
        #: MEASURED the reason this matters: `Godel, Escher, Bach` is 20.62 MB with ZERO image blobs and is cited by
        #: the most claims in the corpus — a name-matching guard had already failed to protect it once. So the
        #: boundary is TIME, which needs no name to resolve.
        row.update(
            verdict="keep_pre_existing",
            reason=(
                "violates the declared shape BUT predates this act's window — reported, never moved, because the "
                "artefact may be the provenance of claims already committed"
            ),
        )
    elif row["referenced_by_claims"]:
        row.update(
            verdict="keep_referenced",
            reason=(
                "violates the declared shape BUT its name is cited by a claim in maxwell.db — the artefact is the "
                "PROVENANCE of that row and is never removed by a shape rule"
            ),
        )
    elif not row["container_exists"]:
        row.update(
            verdict="quarantine_refused",
            reason=(
                "violates the declared shape AND no container survives — this artefact may be the only copy of the "
                "text; refused rather than destroyed (C23), and named here so the owner sees it"
            ),
        )
    else:
        row.update(
            verdict="quarantine_and_reconvert",
            reason=(
                "violates the declared shape and its container is on disk — re-derivable, so the bytes leave the "
                "corpus and the checkpoint row leaves with them"
            ),
        )
    return row


def read_checkpoint(path: Path) -> list[dict]:
    """Read the run-scoped Stage-0 checkpoint, fail-closed on a malformed line (C16)."""
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as exc:
            raise RuntimeError(f"FATAL: {path} line {lineno} is not JSON ({exc}) — refusing to edit a checkpoint "
                               f"this script cannot read") from exc
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine wrong-shaped S0 artefacts and repair the checkpoint")
    parser.add_argument("--apply", action="store_true", help="move the bytes and rewrite the checkpoint")
    parser.add_argument("--no-checkpoint", action="store_true", help="move the bytes but leave the checkpoint alone")
    parser.add_argument("--books-dir", default=None, help="corpus root (default: config books_dir)")
    parser.add_argument(
        "--since-hours",
        type=float,
        default=12.0,
        help="SCOPE: only artefacts written inside this window may be moved (default 12 h). A pre-existing artefact "
             "is the provenance of committed claims and is REPORTED, never moved.",
    )
    args = parser.parse_args()
    since_ts = time.time() - args.since_hours * 3600

    books_dir = Path(args.books_dir) if args.books_dir else BOOKS_DIR
    checkpoint = Path(STAGE0_CHECKPOINT)
    if not checkpoint.exists():
        print(f"FATAL: no Stage-0 checkpoint at {checkpoint} — nothing to reconcile")
        return 2

    print(f"corpus      : {books_dir}")
    print(f"checkpoint  : {checkpoint}")
    print(f"shape rule  : max_artifact_mb={S0_ARTIFACT_MAX_MB}  max_embedded_images={S0_ARTIFACT_MAX_EMBEDDED_IMAGES}")

    records = read_checkpoint(checkpoint)
    print(f"records     : {len(records)}")
    referenced = claimed_source_names(DB_PATH)
    print(f"claim-cited names: {len(referenced)}")

    rows: list[dict] = []
    for rec in records:
        raw = rec.get("output_path")
        if not raw:
            continue
        artefact = Path(raw)
        if not artefact.exists() or artefact.suffix.lower() != ".md":
            continue
        src = rec.get("source_path")
        container = Path(src) if src else None
        native = rec.get("format") == "md" or (src is not None and src == raw)
        row = classify(artefact, container, referenced, since_ts, native=native)
        row["has_receipt"] = True
        rows.append(row)

    # ── AN ARTEFACT WITH NO RECEIPT IS STILL AN ARTEFACT (MEASURED 2026-10-18 01:25) ──────────────────────
    # `run_stage0` writes its checkpoint ONCE, at the END of a run. The applier drives one Stage-0 subprocess per
    # book, so every subprocess the stop killed wrote NO record at all — and the corpus kept its bytes anyway.
    # MEASURED at the first --apply: `Codex Seraphinianus (Luigi Serafini) (Z-Library).md` held 473.5 MB with 721
    # embedded blobs and appeared in NO checkpoint row. A disposition driven by receipts alone would have declared
    # the corpus clean while 473 MB of picture bytes sat in it, which is precisely the blindness this script exists
    # to end. So the corpus is scanned DIRECTLY and a file with no receipt is named as `has_receipt: false`.
    seen = {str(Path(r["artefact"]).resolve()) for r in rows}
    orphans = 0
    for artefact in sorted(books_dir.rglob("*.md")):
        if str(artefact.resolve()) in seen:
            continue
        # no receipt: the container can only be GUESSED by the sibling name, and a guess that fails leaves the file
        # where it is (the `native` branch), so an unidentified artefact is reported and never moved.
        sibling = next((artefact.with_suffix(ext) for ext in (".pdf", ".epub", ".djvu", ".mobi", ".azw3")
                        if artefact.with_suffix(ext).exists()), None)
        row = classify(artefact, sibling, referenced, since_ts, native=sibling is None)
        row["has_receipt"] = False
        row["reason"] = f"{row['reason']} | NO CHECKPOINT RECORD: the artefact has no receipt, container guessed from " \
                        f"the sibling name"
        if row["verdict"] == "quarantine_and_reconvert":
            orphans += 1
        rows.append(row)
    if orphans:
        print(f"orphan artefacts (no checkpoint record) needing quarantine: {orphans}")

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    doomed = [r for r in rows if r["verdict"] == "quarantine_and_reconvert"]
    freed = sum(r["size_bytes"] for r in doomed)
    print(f"\nverdicts    : {json.dumps(counts, sort_keys=True)}")
    print(f"to quarantine: {len(doomed)} artefacts, {freed / 1e6:.1f} MB")

    for r in rows:
        if r["verdict"] != "keep":
            print(f"  [{r['verdict']}] {r['size_bytes'] / 1e6:8.2f} MB blobs={r['embedded_image_blobs']:5d} "
                  f"{r['artefact_name'][:78]}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    receipt = EVIDENCE_DIR / f"S0_ARTIFACT_DISPOSITION_{stamp}.jsonl"

    def build_payload(applied: bool) -> str:
        """The receipt text. Built from `rows` AT THE MOMENT OF WRITING, so an applied receipt carries the sha256 and
        the quarantine destination of every moved artefact — a dry receipt that was copied to the applied path would
        describe an act it never saw."""
        out = [
            {
                "schema_version": SCHEMA_VERSION,
                "gen_model": "none (deterministic)",
                "pipeline_commit": "dispose_s0_artifacts",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "stage0_checkpoint": str(checkpoint),
                "books_dir": str(books_dir),
                "shape_rule": {"max_artifact_mb": S0_ARTIFACT_MAX_MB,
                               "max_embedded_images": S0_ARTIFACT_MAX_EMBEDDED_IMAGES},
                "verdict_counts": counts,
                "applied": applied,
                **r,
            }
            for r in rows
        ]
        return "\n".join(json.dumps(p, ensure_ascii=False) for p in out) + "\n"

    safe_write(receipt, build_payload(False))

    if not args.apply:
        print(f"\nDRY RUN — receipt written: {receipt}")
        print("Nothing moved. Re-run with --apply to quarantine and repair the checkpoint.")
        return 0

    # ── MOVE the bytes (never `rm`: a quarantine is reversible and receipted) ─────────────────────
    moved: list[str] = []
    pen = QUARANTINE_ROOT / stamp
    failures: list[str] = []
    for r in doomed:
        src = Path(r["artefact"])
        rel = src.relative_to(books_dir) if books_dir in src.parents else Path(src.name)
        dest = pen / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        before = sha256_of(src)
        try:
            shutil.move(str(src), str(dest))
        except OSError as exc:
            failures.append(f"{src}: {exc}")
            continue
        if sha256_of(dest) != before:
            failures.append(f"{dest}: digest changed in transit — NOT purged, investigate")
            continue
        moved.append(str(src))
        r["quarantined_to"] = str(dest)
        r["sha256"] = before

    print(f"\nmoved       : {len(moved)}  -> {pen}")
    if failures:
        for f in failures:
            print(f"  FAILED: {f}")

    # ── REPAIR the checkpoint: a record of an artefact that is no longer there is a claim with no referent
    if not args.no_checkpoint and moved:
        archive = checkpoint.with_name(f"{checkpoint.name}.pre_bug918_{stamp}")
        shutil.copy2(checkpoint, archive)
        keep = [rec for rec in records if rec.get("output_path") not in set(moved)]
        dropped = len(records) - len(keep)
        safe_write(
            checkpoint,
            "\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + "\n",
            shrink_guard=False,
        )
        # BUG-614: the sidecar binds this checkpoint to the code that produced it. The remaining rows are unchanged
        # and the removed ones are gone BY RECEIPT, so the sidecar is re-cut to the code that now owns the file —
        # otherwise the next resume refuses for the wrong reason (a fingerprint, not the real state).
        from pipeline.stamp import write_stage_code_fingerprint

        write_stage_code_fingerprint(checkpoint, "stage0")
        print(f"checkpoint  : dropped {dropped} row(s), kept {len(keep)}  (archive: {archive.name})")

    second = EVIDENCE_DIR / f"S0_ARTIFACT_DISPOSITION_{stamp}.applied.jsonl"
    safe_write(second, build_payload(True))
    print(f"receipt     : {receipt}")
    print(f"              {second}")
    print(f"\nPURGE WHEN SATISFIED (nothing in the corpus depends on these bytes):\n  rm -rf {pen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
