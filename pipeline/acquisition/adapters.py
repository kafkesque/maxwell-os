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
from dataclasses import dataclass
from typing import Any, Callable

from . import browser, mirrors, net
from .config import AcquisitionError
from .resolvers import Candidate, content_words

MIRROR_EXTENSIONS = ("epub", "pdf", "mobi", "azw3", "djvu", "fb2", "txt")
ROW = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
#: A quote-aware anchor: `[^>]*` alone stops at a `>` sitting INSIDE an attribute (libgen.li writes
#: `title="Add/Edit : …<br>Emotional Design - Donald A. Norman"`), which made every book title invisible to
#: the parser and every LibGen candidate score 0 — MEASURED 2026-10-17 (BUG-910).
ANCHOR = re.compile(r'<a\b(?:(?:"[^"]*"|\'[^\']*\'|[^\'">])*)href="([^"]+)"'
                    r'(?:(?:"[^"]*"|\'[^\']*\'|[^\'">])*)>(.*?)</a>', re.S | re.I)
SIZE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:kB|KB|MB|GB)\b")
MD5 = re.compile(r"md5=([a-fA-F0-9]{32})")
CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
#: A label that is NOT a title: a mirror name, the `GET` button, a `DOI:` line, a size token.
NOISE_ANCHOR = re.compile(r"(?i)^(?:doi\s*:|get$|libgen|sci-?hub|z-?lib|anna)")
EXT_TOKEN = re.compile(r"^(?:%s)$" % "|".join(MIRROR_EXTENSIONS), re.I)


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
    #: WHICH route inside the adapter served it (`oa_pdf` / `unpaywall` / `europepmc` / `slow_download` …). An
    #: adapter with a fallback chain that does not record the rung would make "it worked" unreadable (D-3034).
    via: str | None = None


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


def _plain(fragment: str) -> str:
    """Visible text of an HTML fragment: tags stripped, entities decoded, whitespace collapsed."""
    return re.sub(r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", fragment))).replace("\xa0", " ").strip()


def _title_match(wanted: str, found: str, cfg: dict[str, Any]) -> tuple[bool, float]:
    """Is `found` the SAME WORK as `wanted`? Two limbs, both declared — precision is the point, not recall.

    MEASURED 2026-10-17: token-recall alone is not enough. Searching a shadow catalogue for
    `The Design of Everyday Things` returns `Design Your Life: The Pleasures and Perils of Everyday Things`,
    whose recall against the query is **1.0** — every word the owner asked for is in it. Downloading that would
    put the WRONG BYTES IN THE INBOX UNDER THE RIGHT NAME, which is the one failure this lane exists to prevent
    (the name comes from the manifest candidate, so a mismatched file is a silent corruption, not a near miss).
    A character-level ratio separates them (see `matcher` in config/acquisition.yaml for the measured pair).

    Returns `(accepted, recall)` so a refusal can print the number it refused on.
    """
    import difflib

    asked, got = content_words(wanted), content_words(found)
    if not asked or not got:
        return False, 0.0
    recall = len(asked & got) / len(asked)
    ratio = difflib.SequenceMatcher(None, _plain(wanted).lower(), _plain(found).lower()).ratio()
    block = (cfg.get("matcher") or {})
    return (recall >= float(block.get("min_token_recall", 0.6))
            and ratio >= float(block.get("min_title_ratio", 0.62))), recall


def _doi(canonical_id: str) -> str | None:
    """The DOI inside a resolver identity (`doi:10.3389/...`), or None.

    A DOI route may only be tried on a DOI: asking Unpaywall about `openalex:W123` would return a 404 that reads
    like an outage, which is exactly how an adapter's own limitation gets misread as a fact about the work.
    """
    prefix, _, value = str(canonical_id or "").partition(":")
    return value.strip() if prefix.lower() == "doi" and value.strip() else None


class OpenAccessAdapter(Adapter):
    """The lawful first rung: an open-access copy, resolved in a DECLARED order of routes.

    MEASURED 2026-10-17: OpenAlex `best_oa_location.pdf_url` resolves for a large share of works; when it is
    absent the work is often still open elsewhere, and two keyless resolvers answer for a DOI —
    `api.unpaywall.org/v2/<doi>` (200, `best_oa_location.url_for_pdf`) and Europe PMC's REST search (200,
    `fullTextUrlList`). A rung that only read the resolver's field refused every work whose OA copy OpenAlex had
    not indexed, which is a REFUSAL ABOUT THE ADAPTER misread as a refusal about the work (D-3034).

    The order is declaration, not taste: the resolver's own field first (it is already in hand and needs no
    network call), then the two DOI resolvers, and each route records itself in `Delivery.via`.
    """

    id = "open_access"
    licence_class = "open_access"
    ROUTES = ("oa_pdf", "unpaywall", "europepmc")

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        wanted = [str(route) for route in (block.get("routes") or self.ROUTES)]
        unknown = [route for route in wanted if route not in self.ROUTES]
        if unknown:
            raise AcquisitionError(f"adapters.open_access.routes names {unknown}, which this adapter cannot serve")
        tried: list[str] = []
        for route in wanted:
            try:
                delivery = getattr(self, f"_{route}")(candidate, cfg, block)
            except net.NetworkRefused as refusal:
                tried.append(f"{route}:{refusal.failure.class_}")
                continue
            if delivery is not None:
                return delivery
            tried.append(f"{route}:absent")
        raise AdapterMiss(f"no open-access copy for {candidate.canonical_id} on any lawful route ({', '.join(tried)})")

    # -- routes -----------------------------------------------------------------------------------------
    def _oa_pdf(self, candidate: Candidate, cfg: dict[str, Any], block: dict[str, Any]) -> Delivery | None:
        """The resolver's own field — no extra call, and the reason this rung is first."""
        if not candidate.oa_pdf:
            return None
        return Delivery(
            adapter=self.id,
            url=candidate.oa_pdf,
            licence_class=self.licence_class,
            content_hint="pdf" if candidate.oa_pdf.lower().split("?")[0].endswith(".pdf") else None,
            via="oa_pdf",
        )

    def _unpaywall(self, candidate: Candidate, cfg: dict[str, Any], block: dict[str, Any]) -> Delivery | None:
        """Unpaywall: one DOI in, the best lawful PDF out. MEASURED 200 keyless with a contact email."""
        doi = _doi(candidate.canonical_id)
        if not doi:
            return None
        email = str(block.get("unpaywall_email") or "").strip()
        if not email:
            raise AcquisitionError("adapters.open_access.unpaywall_email is not declared (Unpaywall requires one)")
        payload = net.read_json(f"https://api.unpaywall.org/v2/{net.quote(doi)}?email={net.quote(email)}", cfg)
        best = payload.get("best_oa_location") or {}
        for key in ("url_for_pdf", "url"):
            url = str(best.get(key) or "").strip()
            if url:
                return Delivery(self.id, url, self.licence_class,
                                content_hint="pdf" if url.lower().split("?")[0].endswith(".pdf") else None,
                                via="unpaywall")
        return None

    def _europepmc(self, candidate: Candidate, cfg: dict[str, Any], block: dict[str, Any]) -> Delivery | None:
        """Europe PMC: a DOI in, the open full text out (life sciences; `fullTextUrlList` names the PDF)."""
        doi = _doi(candidate.canonical_id)
        if not doi:
            return None
        query = net.quote(f'DOI:"{doi}"')
        payload = net.read_json(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&resultType=core", cfg
        )
        for result in ((payload.get("resultList") or {}).get("result") or []):
            for entry in ((result.get("fullTextUrlList") or {}).get("fullTextUrl") or []):
                url = str(entry.get("url") or "").strip()
                style = str(entry.get("documentStyle") or "").lower()
                availability = str(entry.get("availabilityCode") or "").upper()
                if url and (style == "pdf" or url.lower().split("?")[0].endswith(".pdf")) and availability in {"OA", "F"}:
                    return Delivery(self.id, url, self.licence_class, content_hint="pdf", via="europepmc")
        return None


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


class ArxivAdapter(Adapter):
    """arXiv — the lawful rung a paper gap needs and the ladder did not have.

    MEASURED 2026-10-17: `export.arxiv.org/api/query?search_query=ti:"..."` answers 200 with an Atom feed
    (keyless, no quota beyond politeness) and each entry carries an `abs` id that resolves to
    `https://arxiv.org/pdf/<id>`. This is the rung that answers "the 2025 survey of X" — the shape Gutenberg and
    Standard Ebooks structurally cannot serve.
    """

    id = "arxiv"
    licence_class = "open_access"
    ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)
    ID = re.compile(r"<id>\s*(https?://arxiv\.org/abs/[^<\s]+)\s*</id>")
    TITLE = re.compile(r"<title>(.*?)</title>", re.S)

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        template = str(block.get("search") or 'https://export.arxiv.org/api/query?search_query=ti:"{query}"&max_results=5')
        query = " ".join(candidate.title.split()[:16])
        body = net.read_text(template.format(query=net.quote(query)), cfg)
        best: tuple[float, str] | None = None
        for entry in self.ENTRY.findall(body):
            id_match = self.ID.search(entry)
            title_match = self.TITLE.search(entry)
            if not id_match or not title_match:
                continue
            title = html_module.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
            overlap = _overlap(candidate.title, title)
            if best is None or overlap > best[0]:
                best = (overlap, id_match.group(1).replace("/abs/", "/pdf/"))
        if not best or best[0] < 0.5:
            raise AdapterMiss(f"arXiv has no preprint matching `{query}` (best overlap {best[0] if best else 0.0:.2f})")
        return Delivery(self.id, best[1], self.licence_class, content_hint="pdf", via="arxiv_api")


def parse_libgen_rows(body: str) -> list[dict[str, Any]]:
    """Parse a LibGen result table into {md5, title, extension, size} rows.

    MEASURED 2026-10-17 on `libgen.li/index.php?req=`: the result table has `<tr>` rows of `<td>` cells and the
    md5 lives in a mirror anchor (`ads.php?md5=<md5>`). The FIRST parser read the first `edition.php` anchor as
    the title — which on a scimag row is the JOURNAL NAME and on a book row can be empty — so titles came back as
    `Journal of Design History` and `985 kB`, every overlap scored 0, and every LibGen candidate was refused as
    `no rows`. That is an ADAPTER defect misread as an absent book (BUG-910), so the rule is now:
    the title is the LONGEST anchor label in the row that is not a mirror / `GET` / `DOI:` / size token.

    The fixture in `--selftest` pins both shapes (a book row and a scimag row) so a redesign fails a TEST.
    """
    rows: list[dict[str, Any]] = []
    for block in ROW.findall(body):
        md5_match = MD5.search(block)
        if not md5_match:
            continue
        title = ""
        for href, text in ANCHOR.findall(block):
            label = _plain(text)
            if len(label) < 3 or NOISE_ANCHOR.search(label) or SIZE.fullmatch(label):
                continue
            if any(token in href for token in ("ads.php", "get.php", "file.php")):
                continue
            if len(label) > len(title):
                title = label
        extension = ""
        size = ""
        for cell in CELL.findall(block):
            plain = _plain(cell)
            if EXT_TOKEN.match(plain):
                extension = plain.lower()
            if "file.php" in cell and not size:
                found = SIZE.search(plain)
                if found:
                    size = found.group(0)
        if not size:
            found = SIZE.search(_plain(block))
            size = found.group(0) if found else ""
        rows.append({"md5": md5_match.group(1).lower(), "title": title, "extension": extension, "size": size})
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
                accepted, recall = _title_match(candidate.title, row["title"], cfg)
                if accepted and (best is None or recall > best[0]):
                    best = (recall, domain, row["md5"] + "|" + row["extension"])
            if best:
                break
        if not best:
            raise AdapterMiss(
                f"LibGen found no row that IS `{query}` on {len(mirrors.live_domains(cfg, 'libgen'))} validated"
                f" mirror(s) ({reasons or 'rows read, none matched the title on BOTH limbs'})"
            )
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
    """Anna's Archive — reachable ONLY through a browser engine, and that is a MEASUREMENT, not a preference.

    MEASURED 2026-10-17, five readings on the same URL (`/search?q=design+of+everyday+things&content=book_any`):
      `urllib` + browser headers     -> 403, 902 B, `DDoS-Guard`
      Playwright HEADLESS Chrome     -> 403, 1,896 B, `DDoS-Guard`
      Playwright HEADED Chrome       -> challenge runs, the page RELOADS, 14 s later 693,342 B, **116 /md5/ rows**
      `/md5/<hash>`                  -> 16 `slow_download` + 105 `fast_download` links
      `/slow_download/<hash>/0/0`    -> 24 s later a direct node URL carrying a real `.epub`

    So the old declaration ("unreachable by scraping") was TRUE OF AN HTTP CLIENT and FALSE OF A BROWSER. The
    adapter now states the engine it needs, and an absent engine is a MISS that names the remedy. Search and
    download-link shapes are taken from the community MCP `iosifache/annas-mcp`, whose README states search needs
    no key and DOWNLOADS need a donation-granted key — so the key is an accelerator, never a precondition for
    finding the book.

    A shadow rung: OFF until the owner word names it in the run (D-3078).
    """

    id = "annas"
    licence_class = "shadow"
    STATE = "browser_engine"
    ROW = re.compile(r'href="(/md5/[a-f0-9]{32})"', re.I)
    ROW_TITLED = re.compile(r'<a\b[^>]*href="(/md5/[a-f0-9]{32})"[^>]*>(.*?)</a>', re.S | re.I)
    SLOW = re.compile(r'href="(/slow_download/[^"]+)"')
    FILE = re.compile(r'href="(https?://[^"]+\.(?:pdf|epub|mobi|azw3)(?:\?[^"]*)?)"', re.I)

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        block = (cfg["adapters"].get(self.id) or {})
        if str(block.get("engine") or "browser") != "browser":
            raise AcquisitionError("adapters.annas.engine must be `browser`: no other engine passes the challenge")
        ok, why = browser.available()
        if not ok:
            raise AdapterMiss(f"Anna's Archive needs a browser engine and this machine has none: {why}")
        query = " ".join(candidate.title.split()[:12])
        search = str(block.get("search") or "https://{mirror}/search?q={query}&content=book_any")
        with browser.Browser(cfg) as engine:
            domain = (mirrors.live_domains(cfg, "annas") or ["annas-archive.gl"])[0]
            body = engine.get(search.format(mirror=domain, query=net.quote(query)), settled=self.ROW)
            hits = list(dict.fromkeys(self.ROW.findall(body)))
            if not hits:
                raise AdapterMiss(f"Anna's Archive returned no row for `{query}` ({len(body)} B settled)")
            chosen, recall = hits[0], 0.0
            for href, label in self.ROW_TITLED.findall(body):
                accepted, this_recall = _title_match(candidate.title, _plain(label), cfg)
                if accepted and this_recall > recall:
                    chosen, recall = href, this_recall
            page = engine.get(f"https://{domain}{chosen}", settled=self.SLOW)
            slow = self.SLOW.findall(page)
            if not slow:
                raise AdapterMiss(f"Anna's Archive md5 {chosen.rsplit('/', 1)[-1]} lists no download link "
                                  f"(chosen from {len(hits)} row(s), recall {recall:.2f})")
            wait = float(block.get("slow_wait_s") or 60)
            landing = engine.get(f"https://{domain}{slow[0]}", settled=self.FILE, wait_s=wait)
            files = self.FILE.findall(landing)
            if not files:
                raise AdapterMiss("Anna's Archive slow-download settled without a file link (quota or a captcha)")
            hint = files[0].lower().split("?")[0].rsplit(".", 1)[-1]
            return Delivery(
                self.id,
                files[0],
                self.licence_class,
                referer=f"https://{domain}{slow[0]}",
                content_hint=hint if hint in MIRROR_EXTENSIONS else None,
                via="slow_download",
            )


class ZlibraryAdapter(Adapter):
    """Z-Library — DECLARED `credential_required`. It is not a code problem, and pretending otherwise would be.

    MEASURED 2026-10-17 from this machine: every published front answers a guard, not a catalogue —
    `z-lib.gd` 503 (9.5 KB `Checking your browser`), `z-library.qa`/`-gy` 503, `z-library.sk` no DNS,
    `z-lib.fm`/`-im`/`-sk` 307 redirects; and the community CLI `heartleo/zlib` (993 stars, pushed 2026-10-07)
    documents the same reality: it needs a PERSONAL DOMAIN plus a LOGIN, with `proxy & custom domain` support
    for restricted networks.

    So the missing thing is one credential this repo must not hold (D-3078). The owner's one action is either
      `brew install heartleo/tap/zlib && zlib login`   (the CLI keeps the session itself), or
      `export ZLIB_DOMAIN=… ZLIB_COOKIE=…`             (in the shell that runs `acquire.py`).
    Until one exists this rung REFUSES BY NAME: "you have not given me the key" is a fact, while a 503 dressed as
    "no such book" is a lie (D-3034).
    """

    id = "zlibrary"
    licence_class = "shadow"
    STATE = "credential_required"

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        import os

        block = (cfg["adapters"].get(self.id) or {})
        domain = os.environ.get(str(block.get("domain_env") or "ZLIB_DOMAIN"), "").strip().rstrip("/")
        cookie = os.environ.get(str(block.get("cookie_env") or "ZLIB_COOKIE"), "").strip()
        if not domain or not cookie:
            raise AdapterMiss(
                "Z-Library needs the owner's own session: set ZLIB_DOMAIN and ZLIB_COOKIE, or install the"
                " community CLI (`brew install heartleo/tap/zlib` then `zlib login`). Every public front answers"
                " a browser check (503 / 307 / no DNS), MEASURED 2026-10-17."
            )
        query = " ".join(candidate.title.split()[:10])
        body = net.read_text(f"{domain}/s/{net.quote(query)}", cfg)
        best: tuple[float, str] | None = None
        for href, text in ANCHOR.findall(body):
            overlap = _overlap(candidate.title, _plain(text))
            if "/book/" in href and (best is None or overlap > best[0]):
                best = (overlap, href)
        if not best or best[0] < 0.5:
            raise AdapterMiss(f"Z-Library session returned no book matching `{query}` (best {best[0] if best else 0.0:.2f})")
        page = net.read_text(best[1] if best[1].startswith("http") else f"{domain}{best[1]}", cfg)
        links = [href for href in re.findall(r'href="([^"]+)"', page) if "/dl/" in href]
        if not links:
            raise AdapterMiss("Z-Library book page lists no download link (quota reached, or the session expired)")
        target = links[0] if links[0].startswith("http") else f"{domain}{links[0]}"
        return Delivery(self.id, target, self.licence_class, referer=best[1], via="session_cookie")


class ScihubAdapter(Adapter):
    """Sci-Hub — a PAPER rung, shadow, and the honest state today is `captcha`.

    MEASURED 2026-10-17: `sci-hub.ru` and `sci-hub.st` answer `HTTP 200` with a body carrying `captcha` (7.3 KB
    and 26 KB) — a wall, not an article; `sci-hub.se` does not resolve. So the mirrors are tried in declared
    order and a captcha is a MISS WITH THAT NAME, never a silent refusal of the work.

    The second route is the one that works: Anna's Archive indexes Sci-Hub at `/scidb/<doi>`, and that page is
    reachable through the SAME browser engine (it is 403 by plain HTTP, like every Anna's page — MEASURED).
    """

    id = "scihub"
    licence_class = "shadow"
    FILE = re.compile(r'(?:src|href)="([^"]+\.pdf[^"]*)"', re.I)
    CAPTCHA = re.compile(r"(?i)captcha")

    def locate(self, candidate: Candidate, cfg: dict[str, Any]) -> Delivery:
        doi = _doi(candidate.canonical_id)
        if not doi:
            raise AdapterMiss(f"Sci-Hub keys on a DOI; {candidate.canonical_id} is not one")
        block = (cfg["adapters"].get(self.id) or {})
        reasons: list[str] = []
        for mirror in (block.get("mirrors") or ["sci-hub.ru", "sci-hub.st"]):
            try:
                body = net.read_text(f"https://{mirror}/{doi}", cfg)
            except net.NetworkRefused as refusal:
                reasons.append(f"{mirror}:{refusal.failure.class_}")
                continue
            if self.CAPTCHA.search(body):
                reasons.append(f"{mirror}:captcha")
                continue
            found = self.FILE.findall(body)
            if found:
                url = found[0] if found[0].startswith("http") else f"https://{mirror}/{found[0].lstrip('/')}"
                return Delivery(self.id, url, self.licence_class, content_hint="pdf", via=f"{mirror}_page")
            reasons.append(f"{mirror}:no_pdf_link")
        if bool(block.get("scidb_via_browser", True)) and browser.available()[0]:
            try:
                domain = (mirrors.live_domains(cfg, "annas") or ["annas-archive.gl"])[0]
                with browser.Browser(cfg) as engine:
                    page = engine.get(f"https://{domain}/scidb/{doi}", settled=self.FILE)
                found = self.FILE.findall(page)
                if found:
                    return Delivery(self.id, found[0], self.licence_class, content_hint="pdf", via="annas_scidb")
                reasons.append("scidb:no_file_link")
            except AcquisitionError as error:
                reasons.append(f"scidb:{type(error).__name__}")
        raise AdapterMiss(f"Sci-Hub served no PDF for {doi} ({', '.join(reasons) or 'no route'})")


REGISTRY: dict[str, Callable[[], Adapter]] = {
    "open_access": OpenAccessAdapter,
    "gutenberg": GutenbergAdapter,
    "standardebooks": StandardEbooksAdapter,
    "arxiv": ArxivAdapter,
    "annas": AnnasAdapter,
    "libgen": LibgenAdapter,
    "zlibrary": ZlibraryAdapter,
    "scihub": ScihubAdapter,
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
