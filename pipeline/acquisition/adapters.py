"""The adapters: ONE protocol, N sources, in a DECLARED ladder (C21).

Every adapter only LOCATES a byte-stream (a URL, a referer, a name). Moving the bytes, naming the file, probing
it with the door's own test and landing it in a pen is the downloader's single job — so there is exactly one
place in this lane that can write to the owner's disk, and a new source cannot invent a second one.

THE LADDER IS LAWFUL-FIRST and a shadow rung is OFF until an owner word names it in the run (D-3078). Each
adapter carries its own measurement in a docstring, because the difference between "unimplemented" and
"unreachable" is a fact about today, not a matter of taste. Both are declared (D-3038).
"""

from __future__ import annotations

import html as html_module
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable

from . import mirrors, net
from .config import AcquisitionError
from .resolvers import Candidate, content_words

MIRROR_EXTENSIONS = ("epub", "pdf", "mobi", "azw3", "djvu", "fb2", "txt")
ROW = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
ANCHOR = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
SIZE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:kB|KB|MB|GB)\b")
MD5 = re.compile(r"md5=([a-fA-F0-9]{32})")


class AdapterMiss(AcquisitionError):
    """This adapter cannot serve this candidate. A miss is expected; it is not a fault."""


@dataclass(frozen=True)
class Delivery:
    """Where the bytes are, and under what terms — everything the downloader needs and nothing it must guess."""

    adapter: str
    url: str
    licence_class: str
    referer: str | None = None
    content_hint: str | None = None


class Adapter:
    """The protocol. `id` and `licence_class` are declaration; `locate` is behaviour."""

    id = "abstract"
    licence_class = "unknown"

    def enabled(self, cfg: dict[str, Any]) -> bool:
        """Whether the declaration enables this adapter at all."""
        block = ((cfg.get("adapters") or {}).get(self.id) or {})
        return bool(block.get("enabled"))

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        """Return a Delivery for this candidate, or raise AdapterMiss with the reason."""
        raise NotImplementedError


def _overlap(query: str, title: str) -> float:
    """Fraction of the query's content words the title carries — the one matching measure this lane uses."""
    asked = content_words(query)
    if not asked:
        return 0.0
    return len(asked & content_words(title)) / len(asked)


class OpenAccessAdapter(Adapter):
    """The lawful first rung: a DOI that already has an open-access copy, as OpenAlex reports it.

    MEASURED 2026-10-17: OpenAlex `best_oa_location.pdf_url` resolves to a publisher PDF or an arXiv PDF for a
    large share of works; no key, no login, no shadow rung. This is the rung that should answer most paper gaps.
    """

    id = "open_access"
    licence_class = "open_access"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        if not candidate.oa_pdf:
            raise AdapterMiss(f"{candidate.canonical_id} has no open-access copy reported by its resolver")
        return Delivery(
            adapter=self.id,
            url=candidate.oa_pdf,
            licence_class=self.licence_class,
            content_hint="pdf" if candidate.oa_pdf.lower().split("?")[0].endswith(".pdf") else None,
        )


class GutenbergAdapter(Adapter):
    """Project Gutenberg, public domain only.

    Its catalogue is a PREFIX of any research question: it answers "the canonical text of X" and never "the 2019
    survey of X". Declared as such so a gap that finds nothing here is not read as a broken adapter.
    """

    id = "gutenberg"
    licence_class = "public_domain"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        query = " ".join(candidate.title.split()[:8])
        api = str(block.get("metadata_api") or "https://gutendex.com/books?search={query}")
        try:
            payload = net.read_json(api.format(query=net.quote(query)), cfg)
            best: tuple[float, str] | None = None
            for book in payload.get("results") or []:
                title = str(book.get("title") or "")
                overlap = _overlap(candidate.title, title)
                formats = book.get("formats") or {}
                epub = formats.get("application/epub+zip")
                if not epub:
                    continue
                if best is None or overlap > best[0]:
                    best = (overlap, str(epub))
            if best and best[0] >= 0.5:
                return Delivery(self.id, best[1], self.licence_class, content_hint="epub")
        except net.NetworkRefused:
            pass
        # Fallback: Gutenberg's own search page, then its own epub path (MEASURED 200 application/epub+zip).
        search = "https://www.gutenberg.org/ebooks/search/?query=" + net.quote(query)
        body = net.read_text(search, cfg)
        ids = re.findall(r"/ebooks/(\d+)", body)
        if not ids:
            raise AdapterMiss(f"Gutenberg returned no volume for `{query}`")
        return Delivery(
            self.id, f"https://www.gutenberg.org/ebooks/{ids[0]}.epub.noimages", self.licence_class, content_hint="epub"
        )


class StandardEbooksAdapter(Adapter):
    """Standard Ebooks: public domain, hand-transcribed EPUB. The highest-fidelity free source for a classic."""

    id = "standardebooks"
    licence_class = "public_domain"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        search = str(block.get("search") or "https://standardebooks.org/ebooks?query={query}")
        body = net.read_text(search.format(query=net.quote(" ".join(candidate.title.split()[:6]))), cfg)
        links = [
            href
            for href, text in ANCHOR.findall(body)
            if href.startswith("/ebooks/") and _overlap(candidate.title, text) >= 0.5
        ]
        for href in dict.fromkeys(links):
            page = net.read_text("https://standardebooks.org" + href, cfg)
            epub = re.findall(r'href="([^"]+/downloads/[^"]+\.epub)"', page)
            if epub:
                target = epub[0]
                if target.startswith("/"):
                    target = "https://standardebooks.org" + target
                return Delivery(self.id, target, self.licence_class, content_hint="epub")
        raise AdapterMiss(f"Standard Ebooks has no volume matching `{candidate.title[:60]}`")


def parse_libgen_rows(body: str) -> list[dict[str, Any]]:
    """Parse a LibGen result table into {md5, title, extension, size} rows.

    MEASURED 2026-10-17 on libgen.li: a result row carries `ads.php?md5=<md5>` and its title in an anchor to
    `edition.php?id=`. The parser is deliberately tolerant of which cell holds what — the fixture in --selftest
    pins the shape so a site redesign fails a TEST rather than a download.
    """
    rows: list[dict[str, Any]] = []
    for block in ROW.findall(body):
        md5_match = MD5.search(block)
        if not md5_match:
            continue
        anchors = [(href, html_module.unescape(re.sub(r"<[^>]+>", " ", text)).strip()) for href, text in ANCHOR.findall(block)]
        titled = [text for href, text in anchors if "edition.php" in href and text]
        title = titled[0] if titled else max((text for _, text in anchors), key=len, default="")
        extension = ""
        for token in MIRROR_EXTENSIONS:
            if re.search(rf"[>\s]{token}<", block, re.I):
                extension = token
                break
        size = SIZE.search(html_module.unescape(re.sub(r"<[^>]+>", " ", block)))
        rows.append(
            {"md5": md5_match.group(1).lower(), "title": title, "extension": extension, "size": size.group(0) if size else ""}
        )
    return rows


class LibgenAdapter(Adapter):
    """LibGen — the shadow rung that ACTUALLY WORKS from this machine, and is OFF without an owner word.

    MEASURED 2026-10-17: `libgen.li/index.php?req=<q>` (200, 9.3 s) → row `ads.php?md5=<md5>` → that page holds
    exactly one `get.php?md5=<md5>&key=<KEY>` link → 307 → node. `libgen.is` timed out, `libgen.gs`/`library.lol`
    do not resolve, and `libgen.vg` did not answer — which is why the domain is resolved from the tracker and
    validated by marker, never typed here.
    """

    id = "libgen"
    licence_class = "shadow"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        template = str(block.get("search") or "https://{mirror}/index.php?req={query}")
        query = " ".join(candidate.title.split()[:10])
        best: tuple[float, str, str] | None = None
        reasons: list[str] = []
        for domain in mirrors.live_domains(cfg, "libgen"):
            url = template.format(mirror=domain, query=net.quote(query))
            try:
                body = net.read_text(url, cfg, float((cfg.get("download") or {}).get("timeout_s") or 180))
            except net.NetworkRefused as refusal:
                reasons.append(f"{domain}:{refusal.failure.class_}")
                continue
            for row in parse_libgen_rows(body):
                if row["extension"] not in MIRROR_EXTENSIONS:
                    continue
                overlap = _overlap(candidate.title, row["title"])
                if best is None or overlap > best[0]:
                    best = (overlap, domain, row["md5"] + "|" + row["extension"])
            if best and best[0] >= 0.5:
                break
        if not best or best[0] < 0.5:
            raise AdapterMiss(f"LibGen refused/found nothing usable for `{query}`: {reasons or 'no rows'}")
        _, domain, stamp = best
        md5, extension = stamp.split("|", 1)
        ads = f"https://{domain}/ads.php?md5={md5}"
        page = net.read_text(ads, cfg)
        links = [href for href in re.findall(r'href="([^"]+)"', page) if "get.php" in href]
        if not links:
            raise AdapterMiss(f"LibGen md5 {md5} lists no download link (the mirror may be re-indexing)")
        target = html_module.unescape(links[0])
        if target.startswith("/"):
            target = f"https://{domain}{target}"
        elif not target.startswith("http"):
            target = f"https://{domain}/{target}"
        return Delivery(self.id, target, self.licence_class, referer=ads, content_hint=extension)


class AnnasAdapter(Adapter):
    """Anna's Archive — DECLARED UNREACHABLE BY SCRAPING, on measurement, not on taste.

    MEASURED 2026-10-17: `.org` resolves to nothing; `.li` answers 200 with a PARKED-DOMAIN for-sale page;
    `.gd/.gl/.pk` answer 200 but every search redirects into a DDoS-Guard JS challenge, which a plain HTTP client
    cannot pass. The lawful route to the same index is its official API key (paid) or its bulk torrents, so this
    adapter states the missing thing (a key) instead of pretending to scrape.
    """

    id = "annas"
    licence_class = "shadow"
    STATE = "unreachable_by_scraping"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        raise AdapterMiss(
            "Anna's Archive cannot be reached by a plain HTTP client from this machine: the search endpoint is"
            " behind a DDoS-Guard JS challenge and one mirror is a parked domain answering 200 (MEASURED"
            " 2026-10-17). Route to `libgen` (same index, scrapeable) or declare an official API key."
        )


class ZlibraryAdapter(Adapter):
    """Z-Library — DECLARED NOT IMPLEMENTED: it needs a personal login, a credential this repo must not hold."""

    id = "zlibrary"
    licence_class = "shadow"
    STATE = "not_implemented"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        raise AdapterMiss("Z-Library needs a personal login; this lane holds no credential and must not (D-3078)")


REGISTRY: dict[str, Callable[[], Adapter]] = {
    "open_access": OpenAccessAdapter,
    "gutenberg": GutenbergAdapter,
    "standardebooks": StandardEbooksAdapter,
    "annas": AnnasAdapter,
    "libgen": LibgenAdapter,
    "zlibrary": ZlibraryAdapter,
}


def ladder(cfg: dict[str, Any], allow_shadow: bool) -> list[Adapter]:
    """The declared order, filtered by what is ENABLED and by whether the owner word covers the shadow rung.

    TWO GATES, TWO MEANINGS: `enabled` is build-level (the adapter exists and is declared), `requires_owner_word`
    is run-level (this particular run carries the owner's word). A shadow adapter that is built but unworded is
    skipped here and recorded by the caller as `adapter_disabled`, so the hole is visible (D-3038).
    """
    order = [str(item) for item in ((cfg.get("adapters") or {}).get("order") or list(REGISTRY))]
    assembled: list[Adapter] = []
    for name in order:
        factory = REGISTRY.get(name)
        if factory is None:
            raise AcquisitionError(f"adapters.order names `{name}`, which no adapter implements (a declaration with no referent)")
        adapter = factory()
        block = (cfg["adapters"].get(name) or {})
        if not block.get("enabled"):
            continue
        if bool(block.get("requires_owner_word")) and not allow_shadow:
            continue
        assembled.append(adapter)
    return assembled
