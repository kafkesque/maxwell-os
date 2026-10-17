#!/usr/bin/env python3
"""
stage0_convert.py — Convert EPUB/PDF to Markdown via Pandoc/Docling.
====================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 0)

Input:  EPUB/PDF files from books/ directory
Output: Clean .md files, checkpoint at data/checkpoints/stage0_convert.jsonl

Uses Pandoc for EPUB, Docling for PDF, each inside a DECLARED time budget derived from the work itself
(BUG-897/D-3076). There is deliberately NO Pandoc fallback for PDF: Pandoc has no PDF reader, so a
fallback could only ever produce a guaranteed second failure reported as the first (BUG-896).
Every failed conversion is named by a DECLARED failure_class and its full tail is kept beside the
checkpoint, so a receipt carries the DIAGNOSIS and not just the last three lines (BUG-898).

Usage:
    python3 pipeline/stage0_convert.py                          # Convert all books
    python3 pipeline/stage0_convert.py --book "some_book.epub"  # Convert single book
    python3 pipeline/stage0_convert.py --force                  # Reconvert existing
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import ingest_gate  # D-2997/BUG-781: the INGEST DOOR (delta-scoped; never re-classifies an ingested file)
from pipeline.io_guard import load_jsonl, safe_write  # D2332 fail-closed read + D2487 atomic write
from pipeline.pipeline_paths import (
    BOOKS_DIR,
    CHECKPOINT_DIR,
    S0_BUDGET_BASIS,
    S0_CONTAINERS,
    S0_DOCLING_CEILING_S,
    S0_DOCLING_FLOOR_S,
    S0_DOCLING_PER_MB_S,
    S0_FAILURE_CLASSES,
    S0_MAX_FAILED_RATIO,
    S0_PANDOC_TIMEOUT_S,
    SMOKE_BOOK_LIMIT,
    STAGE0_CHECKPOINT,
)
from pipeline.stamp import check_stage_code_fingerprint, get_pipeline_commit, get_pipeline_run_id, stamp_record, write_stage_code_fingerprint
from pipeline.text_cleaner import check_conversion_quality

# ── Constants ──────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = set(S0_CONTAINERS)
#: D-3077 — WHY THIS IS NO LONGER A LITERAL IN THIS FILE. It was `{".epub", ".pdf", ".md"}`, and MEASURED 2026-10-17
#: that three-item set is what produced 389 of 626 admission refusals that the door could only describe as "a
#: container the conversion stage cannot read": 99 .docx, 6 .mobi, 5 .rtf, 4 .pptx — every one of them readable, on
#: this machine, by the pandoc and KindleUnpack steps below. The container axis is now DECLARED, one line per
#: container naming its reader (config/pipeline_config.yaml#stage0.containers), and this set DERIVES from it.
MD_EXTENSION = ".md"
MIN_OUTPUT_BYTES = 100  # C20: a converter that "succeeded" into <100 bytes wrote a receipt, not a work
#: BUG-898: where the FULL tail of a failed conversion rests. Derived from the checkpoint it belongs to, so no new
#: path has to be declared, and NOT the checkpoint itself: the checkpoint's keys are what a resume SKIPS, so a
#: failure written there would never be retried (the failure would become permanent by accident).
S0_FAILURE_LEDGER = Path(str(STAGE0_CHECKPOINT) + ".failures.jsonl")


def _ok() -> dict[str, Any]:
    """A conversion that produced a work."""
    return {"ok": True, "failure_class": None, "meaning": "", "detail": ""}


def _failure(failure_class: str, detail: str) -> dict[str, Any]:
    """A conversion that did NOT produce a work, named by a DECLARED class (BUG-898/C12).

    The class is checked against `config/pipeline_config.yaml#stage0.failure_classes` rather than accepted
    from the caller: a class invented at the call site is a word nobody declared, which is the tail again.
    """
    if failure_class not in S0_FAILURE_CLASSES:
        raise ValueError(
            f"FATAL: {failure_class!r} is not a declared failure_class "
            f"(config/pipeline_config.yaml#stage0.failure_classes, C12)"
        )
    return {
        "ok": False,
        "failure_class": failure_class,
        "meaning": S0_FAILURE_CLASSES[failure_class],
        "detail": " ".join(str(detail).split())[:3000],
    }


def docling_budget_s(pdf_path: Path) -> int:
    """The DECLARED time allowance for THIS work (BUG-897/D-3076).

    WHY IT IS DERIVED FROM THE WORK AND NOT A CEILING. A flat 180 s refused Wim Wenders — The Logic of
    Images, a whole 119-page photo-heavy volume that converts rc=0 in 287.28 s. A flat ceiling therefore
    discriminates against long, scanned, image-heavy works FIRST — exactly the part of a library that
    costs most to replace — and it reports the refusal in the vocabulary of a defect ("failed"), which
    sends the owner after a new copy instead of after more time. Two books in one evening were refused
    this way and the bytes were never the problem.
    """
    if S0_BUDGET_BASIS != "bytes":
        raise RuntimeError(
            f"FATAL: stage0.conversion_budget.basis={S0_BUDGET_BASIS!r} is not implemented — only 'bytes' is "
            f"(C12: an unimplemented basis is a declaration with no referent)"
        )
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    allowance = S0_DOCLING_FLOOR_S + int(S0_DOCLING_PER_MB_S * size_mb)
    return int(min(S0_DOCLING_CEILING_S, max(S0_DOCLING_FLOOR_S, allowance)))


def find_books(books_dir: Path, subdir: str | None = None) -> list[Path]:
    """Find all supported files recursively in the books directory.

    Args:
        books_dir: Root books directory.
        subdir: Optional relative subdirectory to restrict the search (D2316:
            domain-coherent e2e sampling — avoids the alphabetical grab-bag that
            produced 3% convergence).
    """
    search_root = books_dir / subdir if subdir else books_dir
    if subdir and not search_root.is_dir():
        return []
    books = []
    for ext in SUPPORTED_EXTENSIONS:
        books.extend(search_root.rglob(f"*{ext}"))
    return sorted(books, key=lambda p: p.name)


def _pandoc_reader(source_path: Path, output_path: Path, from_fmt: str | None, what: str) -> dict[str, Any]:
    """One pandoc invocation, inside the DECLARED Pandoc budget, mapped onto the declared failure classes.

    Args:
        source_path: the file pandoc reads (an epub, a .docx, or the html/epub KindleUnpack produced).
        output_path: where the markdown lands.
        from_fmt: pandoc's `-f` value; None lets pandoc infer the reader from the suffix — correct for .epub,
            .docx, .pptx and .rtf, and WRONG for .txt, where the default reader escapes markdown syntax
            (MEASURED: `-\\> Under \\$500`), which is why `.txt` declares `pandoc_plain`.
        what: how a failure should NAME the work. Never a bare filename: when the reader is a temporary unpack the
            owner never asked for, the receipt must still name the container they own.
    """
    argv = ["pandoc", str(source_path), "-t", "markdown", "--wrap=none", "-o", str(output_path)]
    if from_fmt:
        argv.extend(["-f", from_fmt])
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=S0_PANDOC_TIMEOUT_S,
        )
    except FileNotFoundError:
        return _failure("converter_absent", "pandoc is not installed on this machine (brew install pandoc)")
    except subprocess.TimeoutExpired:
        return _failure(
            "budget_expired",
            f"Pandoc did not finish inside its declared {S0_PANDOC_TIMEOUT_S}s budget on {what} — "
            f"a timeout is MORE TIME, never a new copy",
        )
    if result.returncode != 0:
        return _failure(
            "container_unreadable",
            f"Pandoc rc={result.returncode} refused {what}: {result.stderr.strip()[:800]}",
        )
    if not output_path.exists() or output_path.stat().st_size <= MIN_OUTPUT_BYTES:
        written = output_path.stat().st_size if output_path.exists() else 0
        return _failure(
            "no_output",
            f"Pandoc rc=0 and wrote {written} bytes of markdown for {what} "
            f"(below the {MIN_OUTPUT_BYTES}-byte floor)",
        )
    return _ok()


def convert_epub(epub_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert EPUB to Markdown with Pandoc.

    An epub that fails Pandoc is CONTAINER-UNREADABLE in the honest sense: the zip is intact (the plan's own probe
    passed it), and the work's spine/manifest is what refuses — MEASURED 2026-10-17 on two of them:
    `No entry on path: OEBPS/cover.xhtml` (the zip stores Cover.xhtml: a case-only mismatch) and
    `Unable to find element: QName ... manifest` (the content.opf carries no manifest at all).
    """
    return _pandoc_reader(epub_path, output_path, None, f"{epub_path.name}'s container")


def convert_document(source_path: Path, output_path: Path, from_fmt: str | None) -> dict[str, Any]:
    """Convert a word-processor / presentation container (.docx, .pptx, .rtf) or plain text (.txt) with Pandoc."""
    return _pandoc_reader(source_path, output_path, from_fmt, source_path.name)


def convert_native_text(source_path: Path, output_path: Path) -> dict[str, Any]:
    """A .txt is ALREADY text: normalise its line endings and write it. No converter, and that is the point.

    MEASURED 2026-10-17: there is no `plain` reader in `pandoc --list-input-formats` (v3.9), so delegating a .txt to
    pandoc forces `-f markdown`, which ESCAPES the text — the sample file came back as `-\\> Under \\$500 1. Give them a
    call`. An engine that damages the bytes it was handed is not an engine this stage should use.
    """
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return _failure("container_unreadable", f"the file could not be read: {type(exc).__name__}: {exc}")
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    output_path.write_text(text, encoding="utf-8")
    if output_path.stat().st_size <= MIN_OUTPUT_BYTES:
        return _failure(
            "no_output",
            f"the text held {len(text)} characters for {source_path.name} (below the {MIN_OUTPUT_BYTES}-byte floor)",
        )
    return _ok()


def convert_doc(source_path: Path, output_path: Path) -> dict[str, Any]:
    """A Word 97-2003 `.doc` (an OLE Compound Document) to Markdown, via the renderer this host already ships.

    WHY NOT PANDOC AND NOT DOCLING (both MEASURED 2026-10-17): `pandoc --list-input-formats` (v3.9) has no `doc`
    reader at all, and docling ACCEPTS the container and then fails on this library's own files (`failed to convert`,
    rc=0, no output) — a `.doc` row priced for docling is a row that can only fail, and `max_failed_ratio` is 0.0.
    `textutil` ships with macOS: it renders the SAME bytes to text with zero new dependencies (MEASURED on the
    library's own file: 6,397 characters from a 244 KB Word 97 document). On a host without it the row fails as
    `converter_absent` with that word — never as a silent skip (C22 hybrid sovereignty: local-first, and the absence
    of the local tool is NAMED rather than papered over by a cloud call).
    """
    renderer = shutil.which("textutil")
    if renderer is None:
        return _failure(
            "converter_absent",
            "`textutil` is not on PATH — the .doc reader is the macOS renderer this stage declares "
            "(config/pipeline_config.yaml#stage0.containers); the work is whole and nothing was tried against it",
        )
    try:
        done = subprocess.run(
            [renderer, "-convert", "txt", "-stdout", str(source_path)],
            capture_output=True,
            timeout=S0_PANDOC_TIMEOUT_S,  # the same declared renderer budget: one document, one bound
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _failure("container_unreadable", f"textutil could not run on {source_path.name}: {type(exc).__name__}: {exc}")
    if done.returncode != 0:
        tail = done.stderr.decode("utf-8", errors="replace").strip()[:300]
        return _failure("container_unreadable", f"textutil rc={done.returncode} on {source_path.name}: {tail}")
    text = done.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    output_path.write_text(text, encoding="utf-8")
    if output_path.stat().st_size <= MIN_OUTPUT_BYTES:
        return _failure(
            "no_output",
            f"the renderer returned {len(text)} characters for {source_path.name} (below the "
            f"{MIN_OUTPUT_BYTES}-byte floor) — a Word container that renders to nothing is a book whose text is in "
            f"objects the renderer cannot reach",
        )
    return _ok()


def convert_kindle(source_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert a Kindle container (.mobi/.azw/.azw3) to Markdown: KindleUnpack first, then the SAME pandoc step.

    WHY THIS SHAPE (D-3077, MEASURED 2026-10-17). Nothing reads MOBI and writes GOOD markdown in one step: pandoc
    has no MOBI reader at all (`pandoc --list-input-formats`, v3.9, read on this machine), and the only single-step
    writer — calibre's `ebook-convert --txt-output-formatting markdown` — is a ~1 GB Qt application that performs the
    same reconstruction behind a GUI stack. KindleUnpack IS that reconstruction, and it is pure Python. MEASURED on
    the owner's own 36.7 MB book: unpack 0.21 s -> book.html (756,715 B) + 435 extracted images, then pandoc 1.93 s
    -> 576,244 B of markdown. One small dependency, and NO new output dialect: a .mobi converges on the same pandoc
    step an .epub takes, so two containers of one work are converted by one engine.

    A MOBI is one of three KINDS and KindleUnpack returns whichever applies: an epub, an html, or a pdf. A pdf goes
    to the PDF reader — never to pandoc, which has no PDF reader (BUG-896, the accepted negative).
    """
    try:
        import mobi  # KindleUnpack's library fork; imported here so the stage runs without it installed
    except ImportError:
        return _failure(
            "converter_absent",
            "the `mobi` package (a KindleUnpack fork, pure python) is not installed on this machine — "
            "`pip install mobi`; the work is whole and nothing was tried against it",
        )
    unpack_dir = ""
    try:
        try:
            unpack_dir, produced = mobi.extract(str(source_path))
        except Exception as exc:  # KindleUnpack raises per defect; the class we report is OUR declared one
            return _failure(
                "container_unreadable",
                f"KindleUnpack refused the container of {source_path.name}: {type(exc).__name__}: {exc}",
            )
        produced_path = Path(produced)
        if produced_path.suffix.lower() == ".pdf":
            return convert_pdf(produced_path, output_path)
        from_fmt = None if produced_path.suffix.lower() == ".epub" else "html"
        return _pandoc_reader(
            produced_path, output_path, from_fmt, f"{source_path.name} (via KindleUnpack's {produced_path.name})"
        )
    finally:
        #: KindleUnpack unpacks into its OWN temp tree; the extracted images are referenced by the markdown but not
        #: materialised beside it, which is exactly what the epub path already does (MEASURED: the corpus's epub
        #: markdown carries `![](images/00003.jpg)` with no image bytes beside it).
        if unpack_dir:
            shutil.rmtree(unpack_dir, ignore_errors=True)


def convert_pdf(pdf_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert PDF to Markdown with Docling, inside a budget derived from THIS work's size.

    THE PANDOC FALLBACK IS GONE — an ACCEPTED NEGATIVE, registered rather than silently dropped (BUG-896/D-3038).
    `pandoc` has no PDF READER. MEASURED, verbatim: "Pandoc error: Unknown input format pdf / Pandoc can convert
    to PDF, but not from PDF." So every Docling failure used to earn a GUARANTEED second failure, and the owner was
    told "conversion failed" with no alternative tried and no way to tell a timeout from a defective file. A
    fallback that cannot read its own input is not a fallback; it is a second failure wearing the first one's name,
    and it cost the diagnosis of every real failure behind it.
    """
    budget = docling_budget_s(pdf_path)
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    try:
        result = subprocess.run(
            ["docling", str(pdf_path), "--to", "md", "--output", str(output_path.parent)],
            capture_output=True,
            text=True,
            timeout=budget,
        )
    except FileNotFoundError as exc:
        return _failure("converter_absent", f"docling is not installed on this machine ({exc})")
    except subprocess.TimeoutExpired:
        return _failure(
            "budget_expired",
            f"Docling did not finish inside the {budget}s allowance declared for this {size_mb:.1f} MiB work "
            f"(floor {S0_DOCLING_FLOOR_S}s + {S0_DOCLING_PER_MB_S}s/MiB, ceiling {S0_DOCLING_CEILING_S}s) — "
            f"THIS IS A TIMEOUT: raise stage0.conversion_budget if the work is worth the time, and do NOT fetch it again",
        )
    if result.returncode != 0:
        return _failure(
            "container_unreadable",
            f"Docling rc={result.returncode}: {(result.stderr or result.stdout).strip()[:800]}",
        )
    docling_output = output_path.parent / f"{pdf_path.stem}.md"
    if not docling_output.exists():
        return _failure(
            "no_output",
            f"Docling rc=0 and wrote no markdown for {pdf_path.name} — the RECEIPT is defective, not the book",
        )
    if docling_output != output_path:
        docling_output.rename(output_path)
    if output_path.stat().st_size <= MIN_OUTPUT_BYTES:
        return _failure(
            "no_output",
            f"Docling rc=0 and wrote {output_path.stat().st_size} bytes of markdown for {pdf_path.name} "
            f"(below the {MIN_OUTPUT_BYTES}-byte floor)",
        )
    return _ok()


#: D-3077: the READERS this stage owns, keyed by the id `config#stage0.containers` names. `native_md` is the one
#: container that needs no reader at all (an .md IS the artifact) and is handled by the caller before dispatch.
_READERS: dict[str, Any] = {
    "pandoc_epub": convert_epub,
    "docling_pdf": convert_pdf,
    "kindleunpack_pandoc": convert_kindle,
    "pandoc_docx": lambda src, out: convert_document(src, out, None),
    "pandoc_pptx": lambda src, out: convert_document(src, out, None),
    "pandoc_rtf": lambda src, out: convert_document(src, out, None),
    "textutil_doc": convert_doc,
    "native_text": convert_native_text,
}
_NATIVE_READER = "native_md"
#: D-3034 — a container whose reader does not exist is a work silently skipped; a reader no container names is dead
#: code (C19). Both directions are refused AT IMPORT, so a config edit cannot quietly unsupport a book.
_UNDECLARED_READERS = set(S0_CONTAINERS.values()) - {_NATIVE_READER} - set(_READERS)
_UNUSED_READERS = set(_READERS) - set(S0_CONTAINERS.values())
if _UNDECLARED_READERS or _UNUSED_READERS:
    raise RuntimeError(
        f"FATAL: config/pipeline_config.yaml#stage0.containers and this stage's readers disagree — "
        f"declared but unimplemented {sorted(_UNDECLARED_READERS)}, implemented but named by no container "
        f"{sorted(_UNUSED_READERS)} (C12/C19, D-3077)"
    )


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def load_existing_checkpoint() -> dict[str, dict]:
    """Load already-converted books from checkpoint (fail-closed, D2332).

    Previously swallowed json.JSONDecodeError — a truncated/corrupt S0 line was
    silently skipped, dropping that book from the resume set (C16 violation).
    load_jsonl raises on any unparseable non-empty line so a corrupt checkpoint
    is loud, not silent.
    """
    existing: dict[str, dict] = {}
    if STAGE0_CHECKPOINT.exists():
        for rec in load_jsonl(STAGE0_CHECKPOINT, context="S0 checkpoint"):
            src = rec.get("source_file")
            if src:
                existing[src] = rec
    return existing


def apply_ingest_door(books: list[Path], books_dir: Path) -> list[Path]:
    """The INGEST DOOR: drop the DELTA candidates an unresolved identity defers. Nothing ingested is touched.

    WHY (D-2997/BUG-781, measured 2026-10-14). The identity machinery was never missing — its enforcement
    point was: the D-2736/37/38 chain produced ONE owner ledger holding 59 adjudicable pairs with
    `adjudicated: 0` from 2026-09-30, and NOTHING IN THE INGEST PATH READ IT (the gate is declared POST-RUN
    only). BUG-780 then measured what a fortnight of that costs: 530 of the 1,393 rows the store certifies as
    corroborated are ONE TEXT under TWO NAMES (84 pairs), 369 of them served. This call is that missing point.

    DELTA-SCOPED (the cascade rule, pipeline/ingest_gate.py): a file the metadata cache already knows is never
    a candidate, so no existing row, checkpoint, source_id or count can move because of this call. A deferred
    candidate is skipped IN PLACE — never deleted (R-D410) — named loudly, and receipted under the declared
    runtime path. A missing cache degrades LOUDLY when the policy says so (a first run has none: S0.5 writes
    it) and never silently (C16).

    Args:
        books: The candidate files found on disk.
        books_dir: Corpus root, for the report and the receipt.

    Returns:
        A pair: the books that may be converted (the input minus the deferred candidates, subject to
        `door.action`), and the deferred candidates as NAMED non-admissions carrying the declared
        `deferred_for_identity` class (BUG-898: a silently dropped candidate made S0 exit 0 having
        converted nothing, and the applier then recorded `S0 rc=0, markdown absent` about a whole book).
    """
    if not books:
        return books, []
    policy = ingest_gate.load_policy()
    degrade = str(policy["door"].get("on_missing_cache", "abort")) == "degrade_loud"
    try:
        report = ingest_gate.preflight(books_dir=books_dir, run_id=get_pipeline_run_id() or "",
                                       allow_missing_cache=degrade)
    except ingest_gate.GateInputError as exc:
        print(f"❌ INGEST DOOR: {exc}")
        print("   refusing to convert: an identity decision taken BLIND is the defect this door exists for (C16)")
        sys.exit(1)
    deferred = {str(Path(item["path"]).resolve()) for item in report["deferrals"]}
    for item in report["deferrals"]:
        print(f"   ⛔ DEFERRED [{item['defer_reason']}] {item['name']} — collides with {item['matched']} "
              f"(canonical name: {item['canonical_name']})")
    if not report["identity_available"]:
        print("   ⚠️  INGEST DOOR degraded LOUDLY: no metadata cache yet, so identity is FILENAME-ONLY at this "
              "point (receipted as identity_available=false; the door re-runs stronger after S0.5)")
    if not deferred:
        return books, []
    action = "report" if report["override"] else str(report["action"])
    print(f"   ingest door: {len(deferred)} candidate(s) deferred | action={action} | receipt={report['receipt']}")
    if action == "abort":
        print("   action=abort: refusing to convert while identity is unresolved (D-2997)")
        sys.exit(1)
    if action == "report":
        print("   action=report: converting anyway — the deferrals are NAMED above and receipted, never silent")
        return books, []
    #: BUG-898 FAMILY, MEASURED 2026-10-17: a deferred candidate was silently DROPPED from the candidate list, so
    #: S0 exited 0 having converted nothing, and the applier recorded `S0 rc=0, markdown absent` — a receipt that
    #: names neither the door nor the collision, about a book whose bytes are fine. A deferral is NOT an admission
    #: and must say so: it is returned as a NAMED non-admission carrying its class, the work it collides with and
    #: the reason, so it lands on the summary line the applier keeps in its receipt.
    #: SCOPE, AND WHY IT IS THE WHOLE DEFECT (measured 2026-10-17 18:05Z, 88 rows in 45 s, ZERO applied). The door's
    #: deferral list is CORPUS-WIDE: it names every pair the corpus already holds (today 66, all of them an admitted
    #: work's own container and the .md S0 wrote beside it). Handing that list back as this run's failures made EVERY
    #: row exit 1 having converted nothing, and the applier quarantined each copy as `markdown absent`. A deferral is a
    #: non-admission of THIS run only when the deferred file is one of THIS run's candidates; the rest is the door's
    #: standing state, which the census reports and this reader must not restate (D-2942: one fact, one home).
    candidate_paths = {str(book.resolve()) for book in books}
    named = [
        {
            "file": str(item.get("name") or Path(str(item.get("path", ""))).name),
            "format": Path(str(item.get("path", ""))).suffix.lower(),
            "failure_class": "deferred_for_identity",
            "meaning": S0_FAILURE_CLASSES["deferred_for_identity"],
            "detail": f"the ingest door deferred this work ({item.get('defer_reason')}) — it collides with "
                      f"{item.get('matched')} (canonical name: {item.get('canonical_name')}); it needs an OWNER "
                      f"WORD on identity, and it was NOT deleted (R-D410)",
            "elapsed_s": 0.0,
            "bytes": Path(str(item.get("path", ""))).stat().st_size if Path(str(item.get("path", ""))).exists() else 0,
            "source_path": str(item.get("path", "")),
        }
        for item in report["deferrals"]
        if str(Path(str(item.get("path", ""))).resolve()) in candidate_paths
    ]
    return [book for book in books if str(book.resolve()) not in deferred], named


def record_failures(failed: list[dict[str, Any]], pipeline_commit: str) -> None:
    """Append every failed conversion, with its FULL tail, beside the checkpoint (BUG-898).

    WHY A SEPARATE LEDGER, AND NOT THE CHECKPOINT. The checkpoint's keys are what a resume SKIPS, so a failed
    book written there would never be retried — the failure would become permanent by accident. This file skips
    nothing and is read by nothing in the pipeline: it is the evidence a later run, or the owner, reads INSTEAD
    of re-running conversions by hand. MEASURED cost of not having it: 4 failures in one apply printed the same
    sentence structure, and the real causes (an epub parse error, a budget expiry, a void fallback) were
    unrecoverable without re-converting each by hand.
    """
    if not failed:
        return
    S0_FAILURE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for item in failed:
        rec = stamp_record(
            {
                "source_file": item["file"],
                "source_path": item["source_path"],
                "format": item["format"],
                "bytes": item["bytes"],
                "elapsed_s": item["elapsed_s"],
                "failure_class": item["failure_class"],
                "meaning": item["meaning"],
                "detail": item["detail"],
            },
            gen_model="pandoc/docling",
        )
        rec["pipeline_commit"] = pipeline_commit
        payload.append(json.dumps(rec, ensure_ascii=False))
    with open(S0_FAILURE_LEDGER, "a", encoding="utf-8") as fh:  # append: each run's evidence is kept, none overwrites
        fh.write("\n".join(payload) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def run_stage0(
    books_dir: Path = None, force: bool = False, single_book: str = None, limit: int = None
):
    """Run Stage 0: Convert all books to Markdown.

    Args:
        books_dir: Directory containing source books.
        force: Reconvert already-converted books.
        single_book: Convert only the named book.
        limit: Maximum number of books to process (applied after finding all books).
               If None and MAXWELL_RUN_ID=smoke, defaults to 3.
    """
    if books_dir is None:
        books_dir = BOOKS_DIR

    # ── Auto-limit for smoke tests + runner --books flag ────────────────
    if limit is None:
        if os.environ.get("MAXWELL_RUN_ID") == "smoke":
            limit = SMOKE_BOOK_LIMIT
        else:
            env_limit = os.environ.get("MAXWELL_BOOK_LIMIT", "")
            if env_limit.isdigit():
                limit = int(env_limit)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Find books
    if single_book:
        book_path = books_dir / single_book
        if not book_path.exists():
            # Try recursive search
            candidates = list(books_dir.rglob(single_book))
            if candidates:
                book_path = candidates[0]
            else:
                print(f"❌ Book not found: {single_book}")
                sys.exit(1)
        books = [book_path]
    else:
        # D2316: domain-coherent sampling — restrict to a subdirectory when
        # MAXWELL_BOOK_SUBDIR is set (e.g. e2e test).
        subdir = os.environ.get("MAXWELL_BOOK_SUBDIR", "").strip() or None
        books = find_books(books_dir, subdir=subdir)

    # ── Apply limit ─────────────────────────────────────────────────────
    if limit is not None and limit > 0:
        books = books[:limit]

    if not books:
        print("📭 No EPUB or PDF files found in books/")
        return

    # ── The INGEST DOOR (D-2997/BUG-781) ────────────────────────────────
    # Delta-scoped: only files the metadata cache does NOT know can be deferred; a deferred file stays on disk.
    books, deferred_named = apply_ingest_door(books, books_dir)  # BUG-898: a deferral is a NAMED non-admission

    print(f"📚 Stage 0: Convert — {len(books)} books found")
    if limit:
        print(f"   (limited to first {limit})")
    print(f"{'=' * 60}")

    # ── Checkpoint handling ──────────────────────────────────────────────
    # When a limit is active (e.g. smoke test), don't load accumulated
    # checkpoints from prior full runs — they pollute the limited run.
    if limit is not None and limit > 0 and not force:
        existing = {}  # Fresh checkpoint for limited runs
    else:
        if not force:
            # BUG-614: refuse to resume a checkpoint produced by a different code version.
            check_stage_code_fingerprint(STAGE0_CHECKPOINT, "stage0")
        existing = load_existing_checkpoint() if not force else {}
    converted = []
    failed = list(deferred_named)  # the door's refusals are failures with a declared class
    skipped = 0

    pipeline_commit = get_pipeline_commit()

    for i, book_path in enumerate(books, 1):
        book_key = book_path.name
        if book_key in existing and not force:
            skipped += 1
            continue

        ext = book_path.suffix.lower()
        md_dir = book_path.parent
        md_path = md_dir / f"{book_path.stem}.md"

        print(f"  [{i}/{len(books)}] {book_path.name} ({ext})", end=" ")

        # .md books are already converted — just record them
        if ext == ".md":
            md_path = book_path
            if book_path.stat().st_size > 100:
                sha = compute_sha256(book_path)
                size_kb = book_path.stat().st_size / 1024
                rec = stamp_record(
                    {
                        "source_file": book_path.name,
                        "source_path": str(book_path),
                        "output_path": str(md_path),
                        "format": "md",
                        "sha256": sha,
                        "size_kb": round(size_kb, 1),
                        "elapsed_s": 0.0,
                    },
                    gen_model="pandoc/docling",
                )
                rec["pipeline_commit"] = pipeline_commit
                converted.append(rec)
                print(f"→ ✅ {size_kb:.0f}KB (native MD)")
            else:
                print(f"→ ⏭️  Too small ({book_path.stat().st_size} bytes)")
            continue

        start = time.time()
        reader = _READERS.get(S0_CONTAINERS.get(ext, ""))
        if reader is None:
            #: D-3077/C16: a skip printed as a skip is STILL a silence — the work vanishes between the door and the
            #: corpus and nothing downstream can tell it from a book nobody offered. A container this stage has no
            #: reader for is a NAMED failure now, and it is a DOOR/PLAN fault: the door should never have handed it on.
            outcome = _failure(
                "unsupported_format",
                f"{ext or '(no suffix)'} is not a container this stage declares "
                f"(config/pipeline_config.yaml#stage0.containers)",
            )
        else:
            outcome = reader(book_path, md_path)

        elapsed = time.time() - start

        if outcome["ok"]:
            size_kb = md_path.stat().st_size / 1024
            sha = compute_sha256(md_path)
            # ── H4: Post-conversion quality check (D2326: tri-state, never silent) ──
            quality_warnings = []
            quality_status = "passed"
            try:
                with open(md_path, encoding="utf-8") as _qf:
                    q_result = check_conversion_quality(_qf.read(), book_path.name)
                if not q_result["ok"]:
                    print(f"→ ⚠️  {q_result['error']}")
                    quality_warnings.append(q_result["error"])
                    quality_status = "failed"
                for w in q_result.get("warnings", []):
                    print(f"   ⚠️  {w}")
                    quality_warnings.append(w)
            except Exception as e:
                # D2326/C16: the checker is a verification step, not best-effort —
                # a broken checker is indistinguishable from success unless recorded.
                quality_status = "unavailable"
                msg = f"quality check raised: {type(e).__name__}: {e}"
                quality_warnings.append(msg)
                print(f"   ⚠️  {msg}")

            rec = stamp_record(
                {
                    "source_file": book_path.name,
                    "source_path": str(book_path),
                    "output_path": str(md_path),
                    "format": ext,
                    "sha256": sha,
                    "size_kb": round(size_kb, 1),
                    "elapsed_s": round(elapsed, 1),
                    "quality_warnings": quality_warnings,
                    "quality_status": quality_status,
                },
                gen_model="pandoc/docling",
            )
            rec["pipeline_commit"] = pipeline_commit
            converted.append(rec)
            print(f"→ ✅ {size_kb:.0f}KB ({elapsed:.1f}s)")
        else:
            failed.append(
                {
                    "file": book_path.name,
                    "format": ext,
                    "failure_class": outcome["failure_class"],
                    "meaning": outcome["meaning"],
                    "detail": outcome["detail"],
                    "elapsed_s": round(elapsed, 1),
                    "bytes": book_path.stat().st_size,
                    "source_path": str(book_path),
                }
            )
            print(f"→ ❌ {outcome['failure_class']}")

    # Write checkpoint
    all_records = list(existing.values()) + converted
    safe_write(
        STAGE0_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_records) + "\n",
    )
    write_stage_code_fingerprint(STAGE0_CHECKPOINT, "stage0")  # BUG-614: bind checkpoint to producing code
    record_failures(failed, pipeline_commit)  # BUG-898: the DIAGNOSIS and the full tail, beside the receipt

    # Summary
    print(f"\n{'=' * 60}")
    print(f"✅ Converted: {len(converted)}")
    print(f"⏭️  Skipped:   {skipped}")
    print(f"❌ Failed:    {len(failed)}")
    if failed:
        #: BUG-898: this line is ONE of the three the applier carries into its receipt (`tail[-3:]`), so the CLASS
        #: has to be ON IT. A summary that names only the file leaves the receipt naming only the file.
        for f in failed:
            print(f"     - {f['file']} [{f['failure_class']}] {f['detail'][:200]}")
    print(f"📋 Checkpoint: {STAGE0_CHECKPOINT}")

    # D2326: fail-closed ingestion — a failed conversion must not look like success.
    # Return (failed_count, converted_count) so the caller (main) can enforce the
    # config-defined tolerance stage0.max_failed_ratio.
    return len(failed), len(converted)


def main():
    parser = argparse.ArgumentParser(description="Stage 0: Convert EPUB/PDF → Markdown")
    parser.add_argument("--book", help="Convert a single book (filename only)")
    parser.add_argument("--force", action="store_true", help="Reconvert already-converted books")
    parser.add_argument("--books-dir", help="Override books directory")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max books to process (auto: 3 when MAXWELL_RUN_ID=smoke)",
    )
    args = parser.parse_args()

    books_dir = Path(args.books_dir) if args.books_dir else BOOKS_DIR
    result = run_stage0(books_dir=books_dir, force=args.force, single_book=args.book, limit=args.limit)

    # D2326: fail-closed — exit non-zero when the conversion failure ratio exceeds
    # the operator-approved tolerance (config stage0.max_failed_ratio).
    if result is None:
        sys.exit(0)  # no books found — nothing to do, not a failure
    failed_count, converted_count = result
    total_attempted = failed_count + converted_count
    if total_attempted == 0:
        sys.exit(0)
    failure_ratio = failed_count / total_attempted
    if failure_ratio > S0_MAX_FAILED_RATIO:
        print(
            f"❌ Stage 0 FAILED: {failed_count}/{total_attempted} book(s) failed conversion "
            f"({failure_ratio:.1%} > max_failed_ratio={S0_MAX_FAILED_RATIO})"
        )
        sys.exit(1)
    if failed_count > 0:
        print(f"⚠️  Stage 0: {failed_count} book(s) failed — within operator tolerance ({failure_ratio:.1%} ≤ {S0_MAX_FAILED_RATIO})")


if __name__ == "__main__":
    main()
