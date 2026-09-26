#!/usr/bin/env python3
"""artifact_encoding.py - the ONE home for "read an artifact in the encoding it DECLARES" (D-2644/D-2649).

WHY (D-2644). MEASURED 2026-09-26: two independent readers (scripts/reconcile.py, scripts/depth_pass_agreement.py)
each opened an OWNER-DROPPED CSV as strict UTF-8 and CRASHED on 0xCA/0xD1 - MacRoman bytes, because Excel on macOS
wrote the workbook. A bare UnicodeDecodeError names no artifact, so the defect reads as a bug in the reader: an error
leak (C16). An artifact's encoding is a FACT about the artifact - declared next to it, never guessed by the reader.

D-2649 (BUG-510): the DECLARATION has ONE home per artifact. declared() joins every declaration home and FAILS
CLOSED when two homes disagree - a reader that silently picks one of two contradictory declarations is the read-side
twin of a guessed encoding. MEASURED 2026-09-26: scripts/reconcile.py carried a SECOND copy of this reader; it was
deleted, and this module is the only implementation of the rule (D-2646).

MEASURED, the cost of the guess this replaces (scripts/audit_human_verification.py reads
governance/s4_domain_review_sheet.csv as cp1252): 0xD1 is an em dash in MacRoman and 'N-tilde' in cp1252, so a
guessed encoding does NOT crash - it silently changes text two readers then compare (BUG-511).

SCOPE (stated, because an unstated scope reads as coverage): this module decides HOW to decode bytes, and proves a
declaration EXISTS and is a real codec. It does NOT prove the declaration is TRUE - an artifact declared wrong
decodes wrongly, loudly and identically for every reader, which is the strongest claim available without a byte-level
provenance stamp.

CLI: python3 scripts/lib/artifact_encoding.py --selftest   (BUG-492 known-answer controls)
"""
from __future__ import annotations

import codecs
import tempfile
from pathlib import Path

import yaml

HOMES: tuple[str, ...] = ("config/reconciliation.yaml", "config/cohort_declaration.yaml")
KEYS: tuple[str, ...] = ("about", "measured_from", "path")
PREFIX = "artifact-encoding"
EXIT_CLEAN, EXIT_DRIFT = 0, 1


def _pairs(node: object, out: dict[str, str], origin: dict[str, str], home: str,
           conflicts: list[str]) -> None:
    """Collect {artifact path: declared encoding} from any YAML shape, naming the home that declared it.

    Shape-blind ON PURPOSE: a declaration is found by the KEYS it uses, not by the nesting an author chose, so a
    new cohort/manifest shape cannot silently escape the join (C16). Two homes disagreeing about one artifact is
    recorded, never resolved by picking one.
    """
    if isinstance(node, dict):
        target = ""
        for key in KEYS:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                target = value.split("#")[0].strip()
                break
        enc = node.get("encoding")
        if target and isinstance(enc, str) and enc.strip():
            enc = enc.strip()
            previous = out.get(target)
            if previous is not None and previous != enc:
                conflicts.append(target + ": " + origin[target] + " declares " + repr(previous)
                                 + " while " + home + " declares " + repr(enc))
            else:
                out[target] = enc
                origin[target] = home
        for value in node.values():
            _pairs(value, out, origin, home, conflicts)
    elif isinstance(node, list):
        for value in node:
            _pairs(value, out, origin, home, conflicts)


def _join(repo: Path) -> tuple[dict[str, str], dict[str, str]]:
    """The ONE implementation of the declaration join: {artifact: encoding} plus {artifact: declaring home}.

    A declaration home that does not exist here is skipped, not faked (C16): an absent file is not an empty join.
    """
    out: dict[str, str] = {}
    origin: dict[str, str] = {}
    conflicts: list[str] = []
    for home in HOMES:
        path = repo / home
        if path.exists():
            _pairs(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, out, origin, home, conflicts)
    if conflicts:
        raise SystemExit(
            "FAIL-CLOSED (" + PREFIX + "): " + "; ".join(conflicts) + " - an artifact has ONE declared encoding "
            "(D-2649). Two homes that disagree are a DEFECT: a reader that picks one silently is the read-side twin "
            "of a guessed encoding (D-2644). Fix the declaration; do not pick.")
    return out, origin


def declared(repo: Path) -> dict[str, str]:
    """Every declared artifact encoding, joined across the declaration homes; a DISAGREEMENT fails closed."""
    return _join(repo)[0]


def _measured(raw: bytes) -> str:
    """The encoding the BYTES themselves declare, or '' when the bytes are not UTF-8 at all.

    MEASURED 2026-09-26 (audit of this module): the BOM is a declaration carried IN the artifact - a BOM-led file
    read as plain `utf-8` leaks U+FEFF into the first CSV header, so `row.get("item_id")` silently returns None
    and rows vanish (the BUG-511 class: no crash, changed meaning). So the byte-level declaration is measured,
    never assumed, and it is compared against the config declaration rather than overridden by it.
    """
    if raw.startswith(codecs.BOM_UTF8):
        try:
            raw.decode("utf-8-sig")
            return "utf-8-sig"
        except UnicodeDecodeError:
            return ""
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return ""


def read_encoding(path: Path, repo: Path) -> str:
    """The DECLARED encoding of an artifact, and the encoding the BYTES declare - joined, never guessed.

    D-2644/D-2649, widened 2026-09-26: an artifact has two possible homes for this fact - the configuration that
    describes it and the bytes themselves (a UTF-8 BOM, or plain valid UTF-8). They are JOINED:
      * no declaration -> the bytes decide (utf-8 / utf-8-sig); bytes that are not UTF-8 fail CLOSED;
      * a declaration -> it WINS, and is verified: a declared codec that cannot decode its own artifact fails
        CLOSED (a false declaration must not become a mojibake downstream, nor a bare UnicodeDecodeError that
        names no artifact - C16);
      * both homes present -> when they decode to the SAME text they AGREE (an ASCII artifact declared mac_roman
        is tolerated, not presumed); when the text differs the join fails CLOSED naming the artifact, both
        encodings, both homes and the first character where they diverge. A reader never picks a side.
    """
    raw = path.read_bytes()
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError as exc:
        # MEASURED 2026-09-26: a caller passing a RELATIVE path got relative_to()'s ValueError, which names no
        # rule and blames pathlib - an error leak (C16). A relative path resolves against the process cwd, which
        # is NOT the repo, so there is no honest guess to make: refuse and say exactly what is wanted.
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): read_encoding()/open_artifact() need an artifact path "
                         "UNDER the repo (got " + repr(str(path)) + " for repo " + repr(str(repo)) + "). A "
                         "relative path resolves against the process cwd, not against the repo - pass "
                         "repo / 'rel/path' so the declaration can be looked up.") from exc
    encodings, homes = _join(repo)
    enc = encodings.get(rel, "")
    measured = _measured(raw)
    if not enc:
        if measured:
            return measured
        raise SystemExit(
            "FAIL-CLOSED: " + rel + " is not valid UTF-8 and its encoding is NOT declared - declare `encoding:` "
            "beside it in " + " or ".join(HOMES) + ". An artifact's encoding is a fact about the artifact, not a "
            "guess the reader makes; a bare UnicodeDecodeError blames the reader (C16).")
    try:
        codecs.lookup(enc)
    except LookupError as exc:
        raise SystemExit("FAIL-CLOSED: " + rel + " declares encoding " + repr(enc) + " which is not a known "
                         "codec - a misspelled declaration is not a fallback (D-2644).") from exc
    try:
        text_declared = raw.decode(enc)
    except UnicodeDecodeError as exc:
        raise SystemExit(
            "FAIL-CLOSED: " + rel + " declares encoding " + repr(enc) + " (home: " + homes.get(rel, "?") + ") "
            "which CANNOT decode it (first bad byte at offset " + str(exc.start) + ": "
            + hex(raw[exc.start]) + ") - a declaration that cannot read its own artifact is a DEFECT to fix, "
            "never a fallback to take (D-2644).") from exc
    if not measured or measured == enc:
        return enc
    text_measured = raw.decode(measured)
    if text_measured == text_declared:
        return enc
    where = next((i for i, (a, b) in enumerate(zip(text_measured, text_declared)) if a != b), 0)
    raise SystemExit(
        "FAIL-CLOSED: " + rel + " has TWO homes that DISAGREE about its encoding (D-2649): the bytes declare "
        + repr(measured) + " (home: the artifact itself) while " + homes.get(rel, "the declaration")
        + " declares " + repr(enc) + ". They decode to different text - at character " + str(where) + " the bytes "
        "give " + repr(text_measured[where:where + 1]) + " and the declaration gives "
        + repr(text_declared[where:where + 1]) + ". Two homes that disagree are a DEFECT: fix the declaration; "
        "a reader never picks a side.")


def open_artifact(path: Path, repo: Path, **kwargs: object):
    """Open an artifact for reading with its DECLARED encoding, failing closed when it is undeclared."""
    return path.open("r", encoding=read_encoding(path, repo), newline="", **kwargs)


# ── known-answer controls (BUG-492) ─────────────────────────────────────────────────────────────────
MACROMAN_EM_DASH = b"h\n\xd1\n"          # 0xD1 is an em dash in MacRoman, 'N-tilde' in cp1252 (BUG-511)


def _fixture(repo: Path, artifacts: dict[str, bytes], recon: object = None, cohort: object = None) -> Path:
    """A minimal repo: the artifacts under test plus whichever declaration homes the control needs."""
    (repo / "config").mkdir(parents=True, exist_ok=True)
    for rel, raw in artifacts.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    for home, doc in ((HOMES[0], recon), (HOMES[1], cohort)):
        if doc is not None:
            (repo / home).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return repo


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls: every refusal below is a case this module must be SEEN to fire on (BUG-492)."""

    def refused(thunk) -> bool:
        # MEASURED 2026-09-26 in scripts/lib/yaml_guard.py: the call must be handed as a THUNK. With
        # `refused(read_encoding(...))` the argument is evaluated BEFORE refused() can catch anything, so the
        # SystemExit escapes the control list and the selftest dies instead of reporting.
        try:
            thunk()
            return False
        except SystemExit:
            return True

    rows: list[tuple[str, bool]] = []

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"a.csv": b"h\n1\n"})
        rows.append(("a UTF-8 artifact needs no declaration at all",
                     read_encoding(repo / "a.csv", repo) == "utf-8"))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"b.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "b", "about": "b.csv", "encoding": "mac_roman"}]})
        rows.append(("a declared non-UTF-8 artifact is read in the DECLARED encoding",
                     read_encoding(repo / "b.csv", repo) == "mac_roman"))
        rows.append(("open_artifact decodes the declared bytes (0xD1 -> em dash)",
                     open_artifact(repo / "b.csv", repo).read() == "h\n\u2014\n"))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"c.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "c", "about": "c.csv"}]})
        rows.append(("an UNDECLARED non-UTF-8 artifact fails CLOSED (no guessed fallback)",
                     refused(lambda: read_encoding(repo / "c.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"d.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "d", "about": "d.csv", "encoding": "not_a_codec"}]})
        rows.append(("a declaration naming a non-codec fails CLOSED (a typo is not a fallback)",
                     refused(lambda: read_encoding(repo / "d.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"e.csv": MACROMAN_EM_DASH},
                        cohort={"cohorts": [{"measured_from": "e.csv", "encoding": "mac_roman"}]})
        rows.append(("a declaration is found by KEY, at any nesting (a cohort shape cannot escape the join)",
                     read_encoding(repo / "e.csv", repo) == "mac_roman"))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"f.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "f", "about": "f.csv", "encoding": "mac_roman"}]},
                        cohort={"cohorts": [{"measured_from": "f.csv", "encoding": "cp1252"}]})
        rows.append(("two homes DISAGREEING about one artifact fail CLOSED (never pick one, D-2649)",
                     refused(lambda: read_encoding(repo / "f.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"g.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "g", "about": "g.csv", "encoding": "mac_roman"}]},
                        cohort={"cohorts": [{"measured_from": "g.csv", "encoding": "mac_roman"}]})
        rows.append(("two homes AGREEING is not a conflict (a duplicate is checked, not presumed)",
                     read_encoding(repo / "g.csv", repo) == "mac_roman"))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"h.csv": codecs.BOM_UTF8 + b"item_id\n1\n"},
                        recon={"entries": [{"id": "h", "about": "h.csv", "encoding": "utf-8-sig"}]})
        rows.append(("a BOM-led artifact declared utf-8-sig is read as declared (the BOM is stripped)",
                     read_encoding(repo / "h.csv", repo) == "utf-8-sig"
                     and open_artifact(repo / "h.csv", repo).read().startswith("item_id")))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"i.csv": codecs.BOM_UTF8 + b"item_id\n1\n"},
                        recon={"entries": [{"id": "i", "about": "i.csv", "encoding": "utf-8"}]})
        rows.append(("the bytes' BOM and a declaration of plain utf-8 DISAGREE -> CLOSED (D-2649)",
                     refused(lambda: read_encoding(repo / "i.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"j.csv": "caf\u00e9 \u2014 x\n".encode("utf-8")},
                        recon={"entries": [{"id": "j", "about": "j.csv", "encoding": "cp1252"}]})
        rows.append(("a declaration that would MOJIBAKE valid UTF-8 bytes fails CLOSED, not silently",
                     refused(lambda: read_encoding(repo / "j.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"k.csv": b"item_id,note\n1,plain ascii\n"},
                        recon={"entries": [{"id": "k", "about": "k.csv", "encoding": "mac_roman"}]})
        rows.append(("two homes that decode to the SAME text AGREE (ASCII declared mac_roman is tolerated)",
                     read_encoding(repo / "k.csv", repo) == "mac_roman"))

    with tempfile.TemporaryDirectory() as td:
        repo = _fixture(Path(td).resolve(), {"l.csv": MACROMAN_EM_DASH},
                        recon={"entries": [{"id": "l", "about": "l.csv", "encoding": "utf-8"}]})
        rows.append(("a declaration that CANNOT decode its own artifact fails CLOSED (not a fallback)",
                     refused(lambda: read_encoding(repo / "l.csv", repo))))

    with tempfile.TemporaryDirectory() as td:
        outside = Path(td).resolve() / "m.csv"
        outside.write_bytes(b"item_id\n1\n")          # exists, decodes, but is NOT under the repo
        repo = (Path(td) / "repo").resolve()
        rows.append(("an artifact OUTSIDE the repo is REFUSED naming the rule, not pathlib's ValueError (C16)",
                     refused(lambda: read_encoding(outside, repo))))

    return rows


def main(argv: list[str]) -> int:
    """Run the known-answer controls; `--selftest` is the only accepted argument."""
    unknown = [a for a in argv if a != "--selftest"]
    if unknown:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): unknown argument(s) " + str(unknown)
                         + " - this module's only CLI is --selftest")
    rows = controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [name for name, ok in rows if not ok]
    if failed:
        print("FAIL " + PREFIX + ": " + str(len(failed)) + " of " + str(len(rows))
              + " known-answer control(s) did not fire")
        return EXIT_DRIFT
    print("ok " + PREFIX + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
    return EXIT_CLEAN


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
