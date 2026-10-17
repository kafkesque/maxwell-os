#!/usr/bin/env python3
"""container_integrity.py — are these BYTES a container the stage that will read them can OPEN? (BUG-886)

THE DEFECT THIS ANSWERS (MEASURED 2026-10-17, the owner's first real admit tranche): the admission gate refuses
"a container the conversion stage cannot read", and then decided that question by the file's SUFFIX alone. The
tenth of ten signed rows was a 137,319,019-byte `.epub` whose bytes are a TRUNCATED DOWNLOAD — a valid
`PK\\x03\\x04` header and NO end-of-central-directory record anywhere in it — so the plan called it an ADMISSION
CANDIDATE, the applier copied 137 MB into the corpus, and S0 failed. A suffix is a CLAIM made by a name; the
bytes are the FACT. MEASURED over the declared library roots the same day: 1,289 containers, 1,286 open, 3 do
not (2 `.epub`, 1 `.pdf`) — and all three read as ordinary candidates.

WHY THIS IS ITS OWN MODULE. Two readers need the same answer and neither may own it twice (C12): the PLAN
decides which rows an owner may sign, and the APPLIER decides whether to spend a 137 MB copy plus an S0 run on
those bytes. It imports only the standard library and reads a BOUNDED TAIL, so pricing the whole library costs
0.33 s MEASURED — which is why it can sit in front of a dry run without becoming BUG-882 again (a dry run that
hashed 8,271.5 MiB to price the plan and stalled past 300 s).

WHAT IT IS NOT: it does not parse the container (that is S0's job), it is not a promise that conversion
SUCCEEDS, and it repairs nothing. It answers one question — would the declared stage be able to OPEN this — and
the probe a kind uses is DECLARED per kind in the gate
(`source_library.admission.container_integrity.probes`), so a newly accepted container kind cannot be admitted
without a declared probe: a missing probe is FATAL, never a default (D-3034/C12).
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, Callable

#: How far from the END a trailer marker may sit. Named, because "how much tail is enough" is a judgement a
#: reader must be able to see and argue with (C20). A zip's end-of-central-directory is within the last 64 KiB
#: by construction; a PDF's `%%EOF` is the last thing a well-formed file carries, and readers tolerate a little
#: trailing junk, so 4 KiB is generous in both directions.
TAIL_BYTES = 4096

#: A PDF's two ends. The magic alone is NOT enough: MEASURED 2026-10-17, the corrupt `.pdf` in the library fails
#: the magic outright, but a TRUNCATED pdf keeps its `%PDF-` header and loses its trailer — the exact shape a
#: suffix cannot see.
PDF_MAGIC = b"%PDF-"
PDF_TRAILER = b"%%EOF"


def _zip_readable(path: Path) -> bool:
    """True when a zip reader can find this file's END-OF-CENTRAL-DIRECTORY record.

    `zipfile.is_zipfile` reads the TAIL, so it answers the truncation question that `file(1)` and a suffix both
    miss: MEASURED 2026-10-17, the 137 MB library source reported `EPUB document` by magic and `BadZipFile` by
    structure, because its last 64 bytes carry none of `PK\\x05\\x06`.
    """
    return zipfile.is_zipfile(path)


def _pdf_readable(path: Path) -> bool:
    """True when the file OPENS with the PDF magic AND still carries a trailer marker near its end."""
    try:
        with Path(path).open("rb") as handle:
            if handle.read(len(PDF_MAGIC)) != PDF_MAGIC:
                return False
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - TAIL_BYTES))
            return PDF_TRAILER in handle.read()
    except OSError:
        return False


def _always_readable(_path: Path) -> bool:
    """A kind whose readability IS its name (plain text, markdown): DECLARED as `none`, never defaulted.

    A silent default here would let a future container kind be admitted unchecked the day it is added to the
    conversion transition — the failure mode this module exists to close, one level up.
    """
    return True


#: The CLOSED probe vocabulary. A declaration names one of these tokens; a token outside it is FATAL.
PROBES: dict[str, Callable[[Path], bool]] = {
    "zip": _zip_readable,
    "pdf": _pdf_readable,
    "none": _always_readable,
}


def is_readable(path: str | Path, probe: str) -> bool:
    """Would the declared stage be able to OPEN this file, judged by the declared probe for its kind?

    An undeclared probe token is FATAL rather than False: a check that cannot say what it tests must not answer
    "unreadable" and send an owner to re-download a work that is fine (C16).
    """
    try:
        check = PROBES[str(probe)]
    except KeyError:
        raise ValueError(
            f"FATAL: the declared probe {probe!r} is outside the declared vocabulary {sorted(PROBES)} — a "
            f"readability test nobody can name is not a test (D-3034)"
        ) from None
    return bool(check(Path(path)))


def probes_from(admission: dict[str, Any], error: type[Exception] = ValueError,
                accepted: set[str] | None = None) -> dict[str, str]:
    """The probe declared for each container kind, as `{'.epub': 'zip', ...}` in ONE spelling (dot, lowercase).

    `accepted` is the conversion stage's own set. When it is given, every accepted kind must declare a probe:
    a kind the stage reads and no probe covers is the silent gap this module exists to remove, so it is FATAL
    (C12 — an absent declaration is never a zero). The gate's own controls read this the same way.
    """
    block = (admission or {}).get("container_integrity")
    if not isinstance(block, dict):
        raise error(
            f"FATAL: container_integrity is not declared beside the admission policy — which probe reads which "
            f"container kind is a declared fact, never an inference (C12)"
        )
    declared = block.get("probes")
    if not isinstance(declared, dict) or not declared:
        raise error("FATAL: container_integrity.probes must be a non-empty mapping of kind -> probe token")
    probes: dict[str, str] = {}
    for kind, token in declared.items():
        probes[f".{str(kind).lower().lstrip('.')}"] = str(token)
    for kind, token in probes.items():
        if token not in PROBES:
            raise error(
                f"FATAL: the kind {kind} declares the probe {token!r}, which is outside the declared vocabulary "
                f"{sorted(PROBES)} (D-3034)"
            )
    if accepted:
        missing = sorted(kind for kind in accepted if kind not in probes)
        if missing:
            raise error(
                f"FATAL: the conversion stage accepts {missing} and no readability probe is declared for "
                f"{'them' if len(missing) > 1 else 'it'} — an accepted kind nobody checks is admitted on its "
                f"suffix alone, which is exactly BUG-886 (C12)"
            )
    return probes


# ---------------------------------------------------------------------------------------------------------------------
# WHY the bytes are not openable — a REFUSAL MUST NAME ITS OWN REMEDY (BUG-893/D-3073)
# ---------------------------------------------------------------------------------------------------------------------
#: MEASURED 2026-10-17 over the declared library roots the day the first tranche ran: the 5 unopenable containers
#: are NOT one defect, and one of them is not a container at all —
#:   2 `.epub`  truncated downloads (a valid `PK\x03\x04` head, no end-of-central-directory anywhere; one is
#:              30,408,704 bytes = exactly 29 MiB, cut at a chunk boundary);
#:   1 `.pdf`   all ZERO bytes (5,244,077 of `\x00`): a failed write, not a work;
#:   1 `.pdf`   an Apple FINDER ALIAS — 880 bytes carrying the bookmark magic `book\x00\x00\x00\x00mark` and the
#:              path `/Applications/Adobe After Effects 2024/Plug-ins/Effects/Keylight/docs/Keylight_1.2_AE.pdf`.
#:              Retyping `.pdf` on an alias cannot make it a PDF, and the work it POINTS AT already exists on this
#:              machine: its remedy is to resolve a POINTER, not to download anything.
#: The class says "the bytes are not openable"; the DEFECT says what to DO about it. Both are needed, because a
#: refusal whose only advice is "it is corrupt" leaves an owner to re-download a file they already have.
APPLE_BOOKMARK_MAGIC = b"book\x00\x00\x00\x00mark"  #: a macOS alias/Finder bookmark (NOT an archive)
ZIP_LOCAL_HEADER = b"PK\x03\x04"                    #: a zip that STARTED and never finished
HEAD_BYTES = 512                                    #: enough to hold either magic and to see a run of zeros


def _head(path: Path, size: int = HEAD_BYTES) -> bytes:
    """The first `size` bytes — the only region a DEFECT diagnosis needs, so it never reads a whole 137 MB file."""
    with Path(path).open("rb") as handle:
        return handle.read(size)


def diagnose(path: str | Path, probe: str, defects: dict[str, Any],
             error: type[Exception] = ValueError) -> str:
    """Name WHY a container the probe refused cannot be opened, in the DECLARED defect vocabulary.

    The detection is here and the vocabulary (with each defect's remedy) is config, because a remedy is a
    declaration about the world rather than a branch in a reader (C12). An unrecognised shape is its own DECLARED
    token rather than a silent `unknown`: a defect nobody named is a worklist row nobody can action (D-3034).
    """
    if not isinstance(defects, dict) or not defects:
        raise error(
            "FATAL: container_integrity.defects is not declared — a refusal whose reason nobody can name leaves "
            "the owner to guess the remedy (C12)"
        )
    head = _head(path)
    token: str | None = None
    if not head.strip(b"\x00"):  # a file that is nothing but zeros never held a byte of the work
        token = "null_bytes"
    elif head.startswith(APPLE_BOOKMARK_MAGIC):
        token = "apple_bookmark"
    elif probe == "zip":
        token = "truncated_zip_no_central_directory" if head.startswith(ZIP_LOCAL_HEADER) else None
    elif probe == "pdf":
        token = "truncated_pdf_no_trailer" if head.startswith(PDF_MAGIC) else "no_magic"
    token = token or "unrecognised"
    if token not in defects:
        raise error(
            f"FATAL: the defect {token!r} is outside the declared vocabulary {sorted(defects)} — the reader "
            f"detected a shape the declaration does not describe (D-3034)"
        )
    return token


def defects_from(admission: dict[str, Any], error: type[Exception] = ValueError) -> dict[str, Any]:
    """The declared defect vocabulary, in ONE spelling — read beside `probes`, from the same block."""
    block = (admission or {}).get("container_integrity")
    if not isinstance(block, dict):
        raise error("FATAL: container_integrity is not declared beside the admission policy (C12)")
    declared = block.get("defects")
    if not isinstance(declared, dict) or not declared:
        raise error("FATAL: container_integrity.defects must be a non-empty mapping of defect -> {meaning, remedy}")
    for token, body in declared.items():
        if not isinstance(body, dict) or not str(body.get("remedy", "")).strip():
            raise error(
                f"FATAL: the defect {token!r} declares no `remedy` — a defect with no act attached is a word, "
                f"not a worklist entry (D-3034)"
            )
    return declared
