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
