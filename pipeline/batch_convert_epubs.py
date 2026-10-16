#!/usr/bin/env python3
"""
batch_convert_epubs.py — Re-convert the LIBRARY's EPUBs into the corpus MD, BY IDENTITY (D-3050/BUG-865).
==========================================================================================================
Authority: D2134 (the re-conversion) as amended by D-3050 (the bridge is KEYED, PLANNED and never silent).

Declared homes of its facts (never restated here, C12):
    the corpus it writes into   -> config/pipeline_config.yaml#books_dir          (read via pipeline_paths)
    the library it reads        -> config/ingest_identity_gate.yaml#source_library.roots[kind=epub] (via pipeline_paths)
    the flow this step belongs  -> config/ingest_identity_gate.yaml#source_library.flow.transitions.conversion.re_conversion
    the read-back it performs   -> config/silent_repair.yaml (this file READS BACK the md it writes)

WHAT IT DOES
    For each EPUB under the library's epub root: find the ONE corpus .md that is the SAME WORK, convert the EPUB
    with Pandoc, and overwrite that .md in place.

WHAT CHANGED, AND WHY (BUG-865, MEASURED 2026-10-16 — the old shape, recorded so it cannot come back)
    It matched by FILENAME STEM (`epub_path.stem + ".md"`, first `rglob` hit) and it wrote on a bare run.
      * A name is EVIDENCE, never identity (D-3045): a name decided WHICH BYTES the pipeline reads, and `rglob`
        let a hit land in a DOMAIN folder the work's own classification never named (re-routing by accident).
      * The S0.5 metadata cache keys on the door's OWN name, so an in-place overwrite under an unchanged name is
        INVISIBLE to the door (`door.new_file_definition: absent_from_metadata_cache`): the flow's own
        `identity.boundary`. An overwrite there is a RE-INGEST act wearing a repair's clothes (T-172's shape).

    NOW: (1) matches through the DOOR'S OWN comparison key (pipeline.book_metadata.sanitize_source_book), so the
    bridge and the pipeline agree on what one work is; (2) REFUSES an ambiguous key (0 or >1 candidates) and
    COUNTS it - never a first hit; (3) is DRY by default - only `--apply` writes; (4) REFUSES a corpus file the
    S0.5 cache already resolves (`already_ingested`) unless `--allow-ingested` is given explicitly and counted;
    (5) prints the key of every row, so a wrong match is visible BEFORE anything is written.

Usage:
    python3 pipeline/batch_convert_epubs.py                          # PLAN (writes nothing)
    python3 pipeline/batch_convert_epubs.py --apply --max 10         # convert up to 10
    python3 pipeline/batch_convert_epubs.py --selftest               # known-answer controls
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.book_metadata import load_metadata_cache, sanitize_source_book
from pipeline.pipeline_paths import BOOKS_DIR, SOURCE_EPUB_DIR

EPUB_BASE = SOURCE_EPUB_DIR
MD_BASE = BOOKS_DIR

DECISIONS = (
    "convert",            # exactly one candidate and the cache does not resolve it
    "ambiguous_key",      # the door's key resolves to 0 or >1 corpus files: REFUSED, counted
    "already_ingested",   # the S0.5 cache resolves this work: an overwrite here is a re-ingest act
)


def work_key(name: str) -> str:
    """The door's OWN comparison key for a file name (never a second key: C12/D-3045).

    Args:
        name: A file name or a stem; the door's sanitiser is one home for this rule.

    Returns:
        The comparison key the pipeline itself uses when it decides two files are one work.
    """
    return sanitize_source_book(name).strip().lower()


def find_candidates(epub_path: Path, books_dir: Path) -> list[Path]:
    """The corpus .md files that are the SAME WORK as this EPUB, keyed by the door's comparison key.

    Args:
        epub_path: The library EPUB.
        books_dir: The corpus root (the tree S0 reads and the S0.5 cache stamps).

    Returns:
        Every corpus .md whose key equals the EPUB's key - a LIST, because the caller must REFUSE ambiguity
        rather than take the first hit (BUG-865).
    """
    key = work_key(epub_path.stem)
    if not key:
        return []
    return sorted(p for p in Path(books_dir).rglob("*.md") if work_key(p.stem) == key)


def plan_rows(epub_root: Path, books_dir: Path, cache_keys: set[str]) -> list[dict]:
    """The PLAN: one row per library EPUB, decided by identity and never by a first hit. WRITES NOTHING.

    Args:
        epub_root: The library EPUB root.
        books_dir: The corpus root.
        cache_keys: The door's comparison keys the S0.5 metadata cache already resolves.

    Returns:
        A list of dicts with the epub path, the key, the candidate count, the target and the decision.
    """
    rows: list[dict] = []
    for epub_path in sorted(Path(epub_root).rglob("*.epub")):
        key = work_key(epub_path.stem)
        candidates = find_candidates(epub_path, books_dir)
        row = {
            "epub": str(epub_path),
            "key": key,
            "candidates": len(candidates),
            "target": str(candidates[0]) if len(candidates) == 1 else "",
            "decision": "convert",
        }
        if len(candidates) != 1:
            row["decision"] = "ambiguous_key"
        elif key in cache_keys:
            row["decision"] = "already_ingested"
        rows.append(row)
    return rows


def cache_work_keys() -> set[str]:
    """The comparison keys the S0.5 metadata cache already resolves (the door's own definition of KNOWN).

    Returns:
        A set of keys; an empty cache yields an empty set (the door reports that LOUDLY at its own call point,
        which is where an absent cache is a declared degradation - never here).
    """
    keys: set[str] = set()
    try:
        records = load_metadata_cache()
    except Exception as exc:  # noqa: BLE001 - a broken cache is named, never swallowed
        print(f"⚠️  metadata cache unreadable ({type(exc).__name__}: {exc}) - every row reads as NOT ingested")
        return keys
    for name in records:
        keys.add(work_key(str(name)))
    return keys


REPO = Path(__file__).resolve().parent.parent


def read_back(md_path: Path) -> str:
    """Read the corpus .md before overwriting it, through the ONE decode home (scripts/lib/artifact_encoding.py).

    A bare `read_text(errors="replace")` REPAIRS silently: an undecodable byte becomes a character nobody
    declared. That is the class this whole act is about (BUG-866), so the read-back is delegated instead - the
    shared reader JOINS the encoding the artifact declares with the one its bytes declare and fails CLOSED when
    they disagree. A path that is NOT under the repository (a fixture, or --books-dir pointing elsewhere) has no
    declaration to look up, so it is read as strict UTF-8 and an undecodable byte is REPORTED, never invented.

    Args:
        md_path: The corpus .md the conversion would overwrite.

    Returns:
        Its text, decoded by its declaration where one exists.
    """
    try:
        md_path.resolve().relative_to(REPO)
    except ValueError:
        return md_path.read_text(encoding="utf-8")
    from scripts.lib import artifact_encoding  # the ONE place a decode is decided (D-2809/D-2644)

    with artifact_encoding.open_artifact(md_path, REPO) as handle:
        return handle.read()


def count_headers(text: str) -> dict:
    """Count Markdown headers and characters (the conversion quality signal)."""
    lines = text.split("\n")
    return {
        "h1": sum(1 for line in lines if re.match(r"^#\s+\S", line)),
        "h2": sum(1 for line in lines if re.match(r"^##\s+\S", line)),
        "h3": sum(1 for line in lines if re.match(r"^###\s+\S", line)),
        "chars": len(text),
    }


def convert_epub(epub_path: Path) -> str | None:
    """Convert an EPUB to clean Markdown via pypandoc (imported lazily so the PLAN needs no Pandoc)."""
    try:
        import pypandoc

        md_text = pypandoc.convert_file(
            str(epub_path), "markdown", extra_args=["--wrap=none", "--from=epub"]
        )
        return md_text
    except Exception as exc:  # noqa: BLE001 - the failure is printed and counted, never silent
        print(f"    ❌ pypandoc error: {exc}")
        return None


def clean_pandoc_output(text: str) -> str:
    """Strip Pandoc noise: SVG blocks, cover images, empty anchors, raw div wrappers."""
    lines = text.split("\n")
    cleaned = []
    skip_svg = False
    for line in lines:
        stripped = line.strip()

        # Skip SVG blocks
        if "<svg" in stripped.lower() or "viewbox=" in stripped.lower():
            skip_svg = True
            continue
        if skip_svg:
            if "</svg>" in stripped.lower() or stripped == "```":
                skip_svg = False
            continue

        # Skip cover image references
        if re.match(r"^!\[\]\(cover", stripped):
            continue

        # Skip empty anchor tags
        if re.match(r"^\[\]{#", stripped):
            continue

        # Skip raw HTML div wrappers
        if re.match(r"^:::\s*\{", stripped):
            continue
        if stripped == ":::":
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def crash_safe_write(path: Path, content: str) -> None:
    """C6: tempfile → fsync → os.replace."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".md")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def convert_row(row: dict, apply: bool) -> int:
    """Convert one row's EPUB and, only with `apply`, overwrite its keyed target.

    Args:
        row: A plan row with decision `convert`.
        apply: False = PLAN: read back and report, write nothing.

    Returns:
        0 = converted or planned, 1 = failed or refused by the quality check.
    """
    epub_path, md_path = Path(row["epub"]), Path(row["target"])
    name = epub_path.name[:45]
    try:
        old_text = read_back(md_path)
    except Exception as exc:  # noqa: BLE001 - a named failure, never a silent skip
        print(f"    ⚠️  Cannot read {md_path.name}: {exc}")
        old_text = ""
    before = count_headers(old_text)

    pandoc_text = convert_epub(epub_path)
    if pandoc_text is None:
        print(f"  ❌ FAILED: {name}")
        return 1
    cleaned = clean_pandoc_output(pandoc_text)
    after = count_headers(cleaned)
    total_h_before = before["h1"] + before["h2"] + before["h3"]
    total_h_after = after["h1"] + after["h2"] + after["h3"]

    # Reject if Pandoc output is clearly worse (much smaller, fewer headers)
    if after["chars"] < before["chars"] * 0.3 and total_h_after <= total_h_before:
        print(
            f"  ⚠️  DEGRADED: {name} ({before['chars']:,}→{after['chars']:,}c, "
            f"h#{total_h_before}→{total_h_after})"
        )
        return 1

    if apply:
        crash_safe_write(md_path, cleaned)
    h_delta = total_h_after - total_h_before
    flag = "✅" if h_delta > 5 else "📈" if h_delta > 0 else "➡️"
    print(
        f"  {flag} {'WRITTEN' if apply else 'PLANNED'} | h#{total_h_before}→{total_h_after} "
        f"(+{h_delta}) | {before['chars']:,}→{after['chars']:,}c | {name}"
    )
    return 0


def selftest() -> int:
    """Known-answer controls over a synthetic library + corpus (BUG-577: a control nothing runs is a comment)."""
    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    labels = (
        "the_bridge_matches_by_the_DOOR_key_and_not_by_the_raw_stem",
        "an_AMBIGUOUS_key_is_REFUSED_and_counted_never_a_first_hit",
        "a_corpus_file_the_cache_resolves_is_REFUSED_as_a_re_ingest_act",
        "the_PLAN_decides_to_convert_and_still_writes_nothing",
    )
    with tempfile.TemporaryDirectory(prefix="bridge_") as tmp:
        lib = Path(tmp) / "lib"
        lib.mkdir()
        corpus = Path(tmp) / "corpus" / "DOMAIN 6 AI + Computing"
        corpus.mkdir(parents=True)

        # (1) the raw stem of the EPUB is NOT the raw stem of its corpus .md; the KEY is the same.
        (lib / "Mechanical AI (z-library.sk, 1lib.sk).epub").write_text("epub", encoding="utf-8")
        (corpus / "Mechanical AI.md").write_text("old text", encoding="utf-8")
        # (2) one key, two corpus files in two different DOMAIN folders -> ambiguous, refused.
        (lib / "Twin Work.epub").write_text("epub", encoding="utf-8")
        other = Path(tmp) / "corpus" / "DOMAIN 2 Design"
        other.mkdir(parents=True)
        (corpus / "Twin Work.md").write_text("one", encoding="utf-8")
        (other / "Twin Work.md").write_text("two", encoding="utf-8")

        keys = cache_work_keys()
        rows = {Path(r["epub"]).stem: r for r in plan_rows(lib, Path(tmp) / "corpus", keys)}
        mechanical = rows.get("Mechanical AI (z-library.sk, 1lib.sk)", {})
        if mechanical.get("decision") != "convert" or mechanical.get("candidates") != 1:
            mark(
                labels[0],
                f"the key did not join two different raw stems: {mechanical}",
            )
        twin = rows.get("Twin Work", {})
        if twin.get("decision") != "ambiguous_key" or twin.get("target"):
            mark(labels[1], f"an ambiguous key was not refused: {twin}")

        # (3) a key the cache resolves is a re-ingest act, not a repair.
        ingested = plan_rows(lib, Path(tmp) / "corpus", keys | {work_key("Mechanical AI")})
        decided = {Path(r["epub"]).stem: r["decision"] for r in ingested}
        if decided.get("Mechanical AI (z-library.sk, 1lib.sk)") != "already_ingested":
            mark(labels[2], f"an ingested key was not refused: {decided}")

        # (4) the PLAN decides to convert and writes NOTHING (the write is gated behind --apply).
        target = corpus / "Mechanical AI.md"
        before_bytes = target.read_bytes()
        before_mtime = target.stat().st_mtime_ns
        _ = plan_rows(lib, Path(tmp) / "corpus", keys)
        if target.read_bytes() != before_bytes or target.stat().st_mtime_ns != before_mtime:
            mark(labels[3], "the PLAN wrote to the corpus")

    for label in labels:
        failed = {lab for lab, _ in failures}
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    for label, detail in failures:
        print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
    if failures:
        return 1
    print(f"selftest: {len(labels)}/{len(labels)} controls green")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI: PLAN (default) | --apply | --selftest."""
    parser = argparse.ArgumentParser(
        description="Re-convert the library's EPUBs into the corpus MD by IDENTITY (D-3050/BUG-865)"
    )
    parser.add_argument("--apply", action="store_true", help="write the conversions (default: PLAN)")
    parser.add_argument("--dry-run", action="store_true", help="the PLAN, stated explicitly (the default)")
    parser.add_argument("--max", type=int, default=0, help="Max books to convert")
    parser.add_argument(
        "--allow-ingested",
        action="store_true",
        help="also overwrite a corpus file the S0.5 cache resolves (a RE-INGEST act - D-3050)",
    )
    parser.add_argument("--epub-dir", default=None, help="Override the library EPUB root")
    parser.add_argument("--books-dir", default=None, help="Override the corpus root")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    epub_root = Path(args.epub_dir) if args.epub_dir else Path(EPUB_BASE)
    books_dir = Path(args.books_dir) if args.books_dir else Path(MD_BASE)
    apply = bool(args.apply) and not args.dry_run
    if not epub_root.is_dir():
        print(f"❌ the library EPUB root does not exist: {epub_root} (D-795: absent is never zero)")
        return 1
    if not books_dir.is_dir():
        print(f"❌ the corpus root does not exist: {books_dir} (D-795: absent is never zero)")
        return 1

    keys = cache_work_keys()
    rows = plan_rows(epub_root, books_dir, keys)
    by_decision = {d: [r for r in rows if r["decision"] == d] for d in DECISIONS}
    ingestible = by_decision["convert"] + (
        by_decision["already_ingested"] if args.allow_ingested else []
    )

    print(f"📚 {len(rows)} EPUB(s) in the library | corpus: {books_dir}")
    print(
        f"   keyed to ONE corpus file: {len(by_decision['convert'])} | "
        f"key resolves to 0 or >1 (REFUSED): {len(by_decision['ambiguous_key'])} | "
        f"already ingested (REFUSED as a re-ingest act): {len(by_decision['already_ingested'])}"
    )
    print("   the key is the DOOR's own comparison key - a name never decides which bytes are written")
    if by_decision["ambiguous_key"]:
        for row in by_decision["ambiguous_key"][:5]:
            print(f"     ⛔ ambiguous [{row['candidates']} candidates] {Path(row['epub']).name[:60]}")
    if by_decision["already_ingested"] and not args.allow_ingested:
        for row in by_decision["already_ingested"][:5]:
            print(f"     ⛔ already ingested {Path(row['epub']).name[:60]} -> {Path(row['target']).name}")
        print("     (--allow-ingested would write these; that is a RE-INGEST act, not a repair - D-3050)")

    if args.max > 0:
        ingestible = ingestible[: args.max]
    print(f"\n🔄 {'APPLY' if apply else 'PLAN (writes nothing)'}: {len(ingestible)} book(s)")
    print("=" * 70)
    converted = failed = 0
    for row in ingestible:
        if convert_row(row, apply) == 0:
            converted += 1
        else:
            failed += 1
    print("=" * 70)
    print(f"📊 {'converted' if apply else 'would convert'}: {converted} | failed: {failed}")
    if not apply:
        print("   Run with --apply to write. Nothing was written by this run.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
