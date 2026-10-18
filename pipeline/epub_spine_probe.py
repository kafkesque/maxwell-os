"""BUG-900 — the declared EPUB SPINE probe (probe name: ``zip_spine``).

A ``.epub`` can be a perfectly valid ZIP — the only question the ``zip`` probe asks — and
still be unconvertible, because a reader must follow the book's OWN spine:
``META-INF/container.xml`` → the OPF package document → its ``<manifest>`` → its ``<spine>``.
Two authoring defects survive the ``zip`` probe and fail Stage 0 on every future run
(BUG-900): a manifest item whose ``href`` resolves to no entry in the ZIP (HBR carries
``id="cover" href="cover.xhtml"`` while the ZIP stores ``OEBPS/Cover.xhtml`` — case), and
an OPF that carries no ``<manifest>`` at all (Generating Sound). This probe asks the
reader's own question, so the door can refuse the row at PLAN time.

RED LOOP (D-3036) — one command that is RED on both named EPUBs and GREEN on a
convertible one::

    python3 -m pipeline.epub_spine_probe <epub> [<epub> ...]

The function is deliberately self-contained (only stdlib) and takes the path it is given —
no config, no hardcoded roots (C12/C20).
"""

from __future__ import annotations

import posixpath
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Final

#: The one entry every EPUB must carry; its ``rootfile`` names the package document.
CONTAINER_XML: Final = "META-INF/container.xml"


def _local(tag: str) -> str:
    """Drop the ``{namespace}`` prefix so OPF 2.0/3.0 and container.xml all match."""
    return tag.rsplit("}", 1)[-1]


def _first(elem: ET.Element, name: str) -> ET.Element | None:
    """First descendant (or self) whose local name is ``name``; namespace-agnostic."""
    for node in elem.iter():
        if _local(node.tag) == name:
            return node
    return None


def _all(elem: ET.Element, name: str) -> list[ET.Element]:
    """Every descendant (or self) whose local name is ``name``; namespace-agnostic."""
    return [node for node in elem.iter() if _local(node.tag) == name]


def probe_epub_spine(path: str | Path) -> tuple[bool, str]:
    """Return ``(ok, reason)``; ``ok=False`` names the first defect a reader would hit.

    The probe passes only when every local manifest ``href`` resolves to an EXACT
    (case-sensitive) entry in the ZIP and every spine ``itemref`` names a manifest item.
    """
    p = Path(path)
    try:
        archive = zipfile.ZipFile(p)
    except (zipfile.BadZipFile, OSError) as exc:
        return False, f"not a readable zip: {exc}"

    with archive:
        names = set(archive.namelist())
        #: NFC-normalised view so an NFD-stored entry (a macOS-built zip) is not a false defect.
        #: CASE is deliberately NOT folded: the HBR defect IS a case-only mismatch and must stay RED.
        names_nfc = {unicodedata.normalize("NFC", name) for name in names}

        # 1. the container must point at the package document, and it must exist.
        if CONTAINER_XML not in names:
            return False, f"no {CONTAINER_XML} entry"
        try:
            container = ET.fromstring(archive.read(CONTAINER_XML))
        except ET.ParseError as exc:
            return False, f"unparseable {CONTAINER_XML}: {exc}"
        rootfile = _first(container, "rootfile")
        if rootfile is None or not rootfile.get("full-path"):
            return False, f"{CONTAINER_XML} declares no rootfile full-path"
        opf_path = rootfile.get("full-path")
        if opf_path not in names:
            return False, f"rootfile {opf_path!r} is not an entry in the zip"

        # 2. the package document must carry a manifest and a spine.
        try:
            opf = ET.fromstring(archive.read(opf_path))
        except ET.ParseError as exc:
            return False, f"unparseable {opf_path}: {exc}"
        manifest = _first(opf, "manifest")
        if manifest is None:
            return False, f"{opf_path} carries NO <manifest> element"
        spine = _first(opf, "spine")
        if spine is None:
            return False, f"{opf_path} carries NO <spine> element"

        # 3. every LOCAL manifest href must resolve to an EXACT entry (case-sensitive).
        base = posixpath.dirname(opf_path)
        manifest_ids: set[str] = set()
        for item in _all(manifest, "item"):
            href = item.get("href")
            if not href:
                continue
            item_id = item.get("id")
            if item_id:
                manifest_ids.add(item_id)
            if "://" in href or href.startswith(("data:", "//")):
                continue  # external (absolute or protocol-relative) or inline resource
            raw = urllib.parse.unquote(href.split("#", 1)[0])
            target = posixpath.normpath(posixpath.join(base, raw))
            if unicodedata.normalize("NFC", target) not in names_nfc:
                return False, (
                    f"{opf_path} manifest item {item_id or '?'!r} href {href!r} resolves to "
                    f"{target!r}, which is NOT an entry in the zip"
                )

        # 4. every spine itemref must name a manifest item.
        itemrefs = _all(spine, "itemref")
        for itemref in itemrefs:
            idref = itemref.get("idref")
            if idref and idref not in manifest_ids:
                return False, f"{opf_path} spine itemref {idref!r} names no manifest item"

        return True, (
            f"{len(manifest_ids)} manifest items and {len(itemrefs)} spine items all resolve"
        )


def _main(argv: list[str]) -> int:
    """RED-loop runner: print ``GREEN``/``RED`` per path; rc 1 if any input is RED."""
    if not argv:
        print("usage: python3 -m pipeline.epub_spine_probe <epub> [<epub> ...]")
        return 2
    red = 0
    for raw in argv:
        ok, reason = probe_epub_spine(raw)
        print(f"{'GREEN' if ok else 'RED  '} {Path(raw).name}: {reason}")
        red += 0 if ok else 1
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
