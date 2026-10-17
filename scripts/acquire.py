#!/usr/bin/env python3
"""scripts/acquire.py — THE ACQUISITION LANE'S ONE ENTRY POINT (D-3078).

The knowledge layer detects that it cannot back a claim, a gap is named, a market-research act asks the
resolvers who has written about it, and a fetch moves the bytes into the owner's INBOX and stops there.

    python3 scripts/acquire.py gap                     # what is missing, in the three declared classes
    python3 scripts/acquire.py map --gap "colour theory"   # ranked manifest of resolver-returned works
    python3 scripts/acquire.py map --census --limit 1      # map the worst measured starvation gap
    python3 scripts/acquire.py fetch --manifest <json>     # lawful rungs only: OA + Gutenberg + Standard Ebooks
    python3 scripts/acquire.py fetch --manifest <json> --allow-shadow "<the owner's word>"
    python3 scripts/acquire.py status                  # where the lane stands: mirror cache, index, inbox
    python3 scripts/acquire.py mirrors --refresh       # which domains are VALIDATED today, and which were refused
    python3 scripts/acquire.py --selftest              # the control: every declared invariant, one receipt

WHAT IT WILL NOT DO: write `knowledge pipeline/books`, create an `.md`, sign an acceptance, or convert a
container. The acquirer's receipt is a file in a pen, never a row in the corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.acquisition import adapters, config, downloader, gaps, mirrors, net, resolvers, sources  # noqa: E402


def _print(payload: dict[str, Any], as_json: bool) -> None:
    """One reading, human first, JSON on demand — the repository's two-voice convention."""
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_sources(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """The research-source register: what a market-research pass may read, and whether that is still true."""
    document = sources.load()
    faults, notes = sources.check(document)
    rows = sources.rank(str(args.task), document) if args.task else []
    reading: dict[str, Any] = {
        "act": "research_sources",
        "authority": "D-3080",
        "register": str(sources.REGISTER.relative_to(sources.ROOT)),
        "sources": len(sources.entries(document)),
        "faults": faults,
        "notes": notes,
    }
    if rows:
        reading["task"] = args.task
        reading["ranked"] = [
            {"id": row["id"], "tier": row.get("tier"), "access": row.get("access"),
             "signal": row.get("signal"), "answers": row.get("answers")}
            for row in rows
        ]
    if args.json:
        print(json.dumps(reading, indent=2))
    else:
        print(f"register: {reading['register']} — {reading['sources']} declared source(s)")
        for note in notes:
            print(f"  NOTE  {note}")
        for fault in faults:
            print(f"  FAULT {fault}")
        for row in reading.get("ranked", []):
            limbs = ",".join(row["signal"] or []) or "no signal limb"
            print(f"  [{row['tier']}] {row['id']:<20} {row['access']:<10} {limbs:<38} {row['answers']}")
        if not notes and not faults:
            print("ok every declared source resolves and is measured")
    return 1 if faults else 0


def cmd_gap(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """The gap reading: three classes, each with the state of its own measurement."""
    payload = gaps.read_all(cfg, args.limit)
    payload["pen"] = config.land_pen(cfg).name
    _print(payload, args.json)
    return 0


def cmd_map(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """Turn ONE gap into a manifest. `--census` takes the worst measured starvation gap instead of a name."""
    gap: dict[str, Any] | None = None
    if args.census:
        found = gaps.starvation_gaps(cfg)
        if not found:
            print("no measured starvation gap — the census is absent or empty", file=sys.stderr)
            return 2
        gap = found[int(args.index)]
    else:
        gap = {"gap_id": f"manual:{args.gap}", "class": "manual", "discipline": args.gap}
    manifest = resolvers.build_manifest(gap, cfg, args.limit)
    path = resolvers.write_manifest(manifest, cfg)
    summary = {
        "manifest": str(path),
        "gap": gap,
        "queries": manifest["queries"],
        "counts": manifest["counts"],
        "top": [
            {"rank": rank + 1, "title": row["title"], "year": row["year"], "cited_by": row["cited_by"],
             "score": row["score"], "oa_pdf": bool(row["oa_pdf"]), "doi": row["canonical_id"]}
            for rank, row in enumerate(manifest["candidates"][: int(args.show)])
        ],
    }
    _print(summary, args.json)
    return 0


def cmd_fetch(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """Execute a manifest into the INBOX. `--allow-shadow` carries the owner's word and is recorded verbatim."""
    result = downloader.fetch_manifest(
        Path(args.manifest).expanduser(),
        cfg,
        allow_shadow=bool(args.allow_shadow),
        owner_word=args.allow_shadow,
        limit=args.limit,
        dry_run=bool(args.dry_run),
    )
    _print(result, args.json)
    return 0 if not result["counts"].get("refused_no_adapter_served") else 2


def cmd_mirrors(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """Which domains are VALIDATED for each family, and which were refused with their reason."""
    reading: dict[str, Any] = {"tracker": (cfg.get("mirrors") or {}).get("source"), "families": {}}
    for family in ("annas", "libgen"):
        try:
            reading["families"][family] = {
                "validated": mirrors.live_domains(cfg, family, refresh=bool(args.refresh))
            }
        except config.AcquisitionError as refusal:
            reading["families"][family] = {"validated": [], "refusal": str(refusal)}
    cache = Path((cfg.get("mirrors") or {}).get("cache") or "")
    if cache.exists():
        reading["cache"] = json.loads(cache.read_text(encoding="utf-8"))
    _print(reading, args.json)
    return 0


def cmd_status(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    """Where the lane stands: its pen, what the index remembers, what the ladder enables."""
    pen = config.land_pen(cfg)
    index = downloader.load_index(cfg)
    states: dict[str, int] = {}
    for row in index.values():
        states[str(row.get("state"))] = states.get(str(row.get("state")), 0) + 1
    reading = {
        "schema_version": "1.0",
        "act": "acquisition_status",
        "authority": config.load_config().get("authority"),
        "pen": {"name": pen.name, "path": str(pen.path), "why": pen.why},
        "probe_map": config.probe_map(),
        "adapters": {
            name: {
                "enabled": bool((cfg["adapters"].get(name) or {}).get("enabled")),
                "licence_class": (cfg["adapters"].get(name) or {}).get("licence_class"),
                "state": (cfg["adapters"].get(name) or {}).get("state", "declared"),
            }
            for name in (cfg["adapters"].get("order") or [])
        },
        "index": {"rows": len(index), "states": states, "path": str(downloader._index_path(cfg))},
        "inbox": sorted(path.name for path in pen.path.glob("*") if path.is_file())[:20],
    }
    _print(reading, args.json)
    return 0


def _fixture_manifest(tmp: Path, title: str, authors: list[str], year: int, oa_pdf: str | None) -> Path:
    """A manifest with ONE candidate — for the selftest, never for a run."""
    payload = {
        "schema_version": "1.0",
        "gen_model": "deterministic",
        "gap": {"gap_id": "selftest", "class": "manual", "discipline": "selftest"},
        "candidates": [
            {
                "canonical_id": "doi:10.0000/selftest",
                "title": title,
                "authors": authors,
                "year": year,
                "venue": "selftest",
                "kind": "book",
                "cited_by": 1,
                "oa_pdf": oa_pdf,
                "landing": None,
                "licence_class": "open_access",
                "resolved_by": ["selftest"],
                "score": 1.0,
                "why_ranked": [],
            }
        ],
        "counts": {"candidates": 1},
    }
    path = tmp / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def selftest() -> int:
    """Every declared invariant, checked against FIXTURES so the control cannot pass by coincidence.

    The shape of each check is: mutate one thing, require the refusal by NAME, then require the green case. A
    control that only asserts the happy path is the defect BUG-907 was (a fact printed, never tested).
    """
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append((name, bool(passed), detail))

    cfg = config.load_config()
    pen = config.land_pen(cfg)
    gate_pens = config.walk_pointer(config.gate_document(), "source_library.placement.pens")
    check("the land pen IS the inbox the door declares",
          str(pen.path) == str(Path(gate_pens["education_inbox"]["path"]).expanduser()),
          f"{pen.name} → {pen.path}")
    check("the land pen exists on disk", pen.path.is_dir(), str(pen.path))

    # A pen name the door does not declare must refuse BY NAME.
    try:
        config.resolve_pen("not_a_declared_pen")
        check("an undeclared pen is refused", False, "it resolved")
    except config.AcquisitionError as refusal:
        check("an undeclared pen is refused", "not_a_declared_pen" in str(refusal), str(refusal)[:120])

    # probes: the map must be the door's, and every declared container kind must have a token.
    probes = config.probe_map()
    check("the probe map comes from the door (module + probes)", "epub" in probes and "pdf" in probes, str(sorted(probes)))
    check("every probed token is in the module's CLOSED vocabulary",
          set(probes.values()) <= {"zip", "pdf", "mobi", "ole", "none"}, str(sorted(set(probes.values()))))

    # the name: template applied, sanitised, and free of every pattern the door refuses.
    template = config.name_template()
    candidate = resolvers.Candidate(
        canonical_id="doi:10.0000/x",
        title="Colour: A  Survey/Reader",
        authors=("Josef Albers", "Anni Albers"),
        year=1963,
        venue="",
        kind="book",
        cited_by=0,
        oa_pdf=None,
        landing=None,
        licence_class="publisher_licensed",
    )
    name = downloader.render_name(candidate, "epub", template)
    check("the name follows the owner's template", name == "Josef Albers; Anni Albers - Colour A Survey Reader - 1963.epub", name)
    check("the name carries no door-refused marker", not any(token in name.lower() for token in ("z-lib", "libgen", "1lib", "annas-archive")), name)
    check("the name carries no spine signature", " -- " not in name and not __import__("re").search(r"[0-9a-f]{16,}", name), name)
    check("a missing year omits the segment", "None" not in downloader.render_name(
        resolvers.Candidate("doi:1", "T", ("A",), None, "", "book", 0, None, None, "x"), "pdf", template), "")

    # extension: BODY first, then hint, then URL — and never a kind the door does not probe.
    delivery = adapters.Delivery("open_access", "https://example.org/x.pdf", "open_access", content_hint=None)
    check("the content type decides the suffix", downloader._extension(delivery, "application/pdf", probes) == "pdf")
    check("an unknown suffix is refused, never guessed",
          _raises(lambda: downloader._extension(adapters.Delivery("a", "https://x/y.rar", "open_access"), "application/x-rar", probes)))

    # the ladder: shadow is OFF without a word, ON with one, and a disabled rung never appears.
    lawful = [adapter.id for adapter in adapters.ladder(cfg, allow_shadow=False)]
    with_word = [adapter.id for adapter in adapters.ladder(cfg, allow_shadow=True)]
    lawful_expected = [name for name in ("open_access", "gutenberg", "standardebooks", "arxiv") if name in lawful]
    check("the lawful rungs are enabled in the declared order", lawful == lawful_expected, str(lawful))
    check("no shadow rung is reachable without an owner word",
          not set(lawful) & {"libgen", "annas", "zlibrary", "scihub"}, str(lawful))
    check("the owner's word ADDS every shadow rung that is built",
          {"libgen", "annas", "zlibrary", "scihub"} <= set(with_word), str(with_word))
    check("the ladder puts every lawful rung before every shadow rung",
          max(lawful.index(name) for name in lawful) < min(with_word.index(name) for name in set(with_word) - set(lawful)),
          str(with_word))

    # Two-gate honesty: a shadow rung that needs a credential says WHICH credential, by name (D-3034).
    check("zlibrary names the missing credential instead of pretending the book is absent",
          "ZLIB_DOMAIN" in _refusal(lambda: adapters.ZlibraryAdapter().locate(candidate, cfg)))
    not_a_doi = resolvers.Candidate("openalex:W123", "T", ("A",), 2000, "", "book", 0, None, None, "x")
    check("scihub refuses a candidate that is not a DOI, by name",
          "not one" in _refusal(lambda: adapters.ScihubAdapter().locate(not_a_doi, cfg)))
    engine_ok, engine_why = adapters.browser.available()
    check("the browser engine either exists or NAMES its remedy",
          engine_ok or "pip install playwright" in engine_why, engine_why)
    check("annas declares the engine it needs instead of claiming the source is dead",
          adapters.AnnasAdapter.STATE == "browser_engine" and cfg["adapters"]["annas"]["engine"] == "browser",
          adapters.AnnasAdapter.STATE)

    # libgen rows: the parser is pinned to a FIXTURE so a site redesign fails a test, not a download.
    fixture = (
        '<tr><td>1</td><td><a href="edition.php?id=42">Generative Art Theory</a></td>'
        '<td><a href="ads.php?md5=53EA92403D513C35327558C57FC8C3BB">GET</a></td><td>epub</td><td>2.4 MB</td></tr>'
    )
    rows = adapters.parse_libgen_rows(fixture)
    check("a libgen row yields md5 + title + extension",
          len(rows) == 1 and rows[0]["md5"] == "53ea92403d513c35327558c57fc8c3bb" and rows[0]["title"] == "Generative Art Theory"
          and rows[0]["extension"] == "epub", str(rows))
    check("a row without an md5 is not a row", adapters.parse_libgen_rows("<tr><td>no link</td></tr>") == [])
    #: THE MEASURED SHAPE (BUG-910): libgen.li puts a `>` INSIDE the title anchor's tooltip attribute, which made
    #: every book title invisible to the first parser; and a decoy row whose recall is 1.0 must still be refused.
    measured = (
        '<tr><td><a title="Add/Edit : 2017-10-04; ID: 93129822<br>Emotional Design - Donald A. Norman" '
        'href="edition.php?id=137898842">Emotional Design: Why We Love (or Hate) Everyday Things <i>1</i></a></td>'
        '<td>Don Norman</td><td>Basic Books</td><td><nobr>2005</nobr></td><td>English</td><td>0 / 272</td>'
        '<td><nobr><a href="/file.php?id=93129822">985 kB</a></nobr></td><td>epub</td>'
        '<td><a href="/ads.php?md5=76CF57A9D4F5E87FA92A85E31F9DC3F2"><span>1</span></a></td></tr>'
    )
    measured_rows = adapters.parse_libgen_rows(measured)
    check("a title survives a `>` inside its own tooltip attribute (BUG-910)",
          len(measured_rows) == 1 and measured_rows[0]["title"].startswith("Emotional Design"), str(measured_rows))
    check("a real title matches the work it names",
          adapters._title_match("Emotional Design: Why We Love (or Hate) Everyday Things",
                                measured_rows[0]["title"], cfg)[0], measured_rows[0]["title"])
    check("a decoy with FULL token recall is still refused (precision over recall)",
          not adapters._title_match("The Design of Everyday Things",
                                    "Design Your Life: The Pleasures and Perils of Everyday Things", cfg)[0])

    # mirrors: the regex recognises the families and a 200 with no marker is NOT usable (the parked-domain case).
    check("the tracker parse finds annas domains", bool(mirrors.FAMILY_PATTERN["annas"].findall("x annas-archive.gd y")))
    check("the tracker parse finds libgen domains", bool(mirrors.FAMILY_PATTERN["libgen"].findall("x libgen.bz y")))

    # the research-source register (D-3080): a declaration that cannot be checked is a prose list.
    register = sources.load()
    faults, _notes = sources.check(register)
    check("every declared research source resolves (access vocabulary, api_url, env name, reason, measurement)",
          not faults, "; ".join(faults[:3]))
    ranked_books = sources.rank("books", register)
    check("the book ranking puts an integrable source before a manual one",
          [row["access"] in {"api", "scrape", "browser", "credential", "captcha"} for row in ranked_books]
          == sorted((row["access"] in {"api", "scrape", "browser", "credential", "captcha"} for row in ranked_books), reverse=True),
          str([(row["id"], row["access"]) for row in ranked_books]))
    check("a review site that cannot be reached is declared, not dropped",
          any(row["id"] == "the_storygraph" and row["access"] == "manual" for row in ranked_books))
    check("an unknown task is refused by name", _raises(lambda: sources.rank("vibes", register)))

    # the gap reader: a real census, and every unmeasured class NAMED.
    reading = gaps.read_all(cfg, 5)
    check("the starvation class reads the measured census", reading["reading"]["discipline_starvation"]["rows"] > 0, str(reading["reading"]["discipline_starvation"]))
    check("every gap carries its class and its trigger",
          all(gap.get("class") and gap.get("trigger") for gap in reading["gaps"]), str(len(reading["gaps"])))

    # the ranking: citations must not swamp the ranking, overlap must be able to refuse a row.
    cfg_copy = json.loads(json.dumps(cfg))
    check("the resolver answers in relevance order, not citation order",
          "sort=" not in resolvers.OPENALEX_SEARCH and (cfg_copy["cartography"].get("resolver_order") == "relevance"),
          resolvers.OPENALEX_SEARCH)
    high = resolvers.score(resolvers.Candidate("d1", "colour theory and practice", ("a",), 2001, "", "book", 100000, "u", None, "open_access"), "colour theory", cfg_copy)
    low = resolvers.score(resolvers.Candidate("d2", "colour theory and practice", ("a",), 2001, "", "book", 10, "u", None, "open_access"), "colour theory", cfg_copy)
    off = resolvers.score(resolvers.Candidate("d3", "quantum chromodynamics", ("a",), 2001, "", "book", 10, "u", None, "open_access"), "colour theory", cfg_copy)
    check("a better-cited work ranks higher", high.score > low.score, f"{high.score:.3f} > {low.score:.3f}")
    check("an off-topic title is refused by overlap", off.score == 0.0, str(off.why_ranked[-2:]))
    check("the rank keeps its arithmetic", all("=" in reason for reason in high.why_ranked), str(high.why_ranked))

    # a manifest that names no discipline is refused, not defaulted.
    check("a gap with no discipline is refused", _raises(lambda: resolvers.build_manifest({"gap_id": "x"}, cfg_copy), config.AcquisitionError))

    # the downloader: idempotency reads an index, and a second identical name gets a distinct path.
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        manifest = _fixture_manifest(tmp, "Selftest Book", ["A. Author"], 2020, None)
        loaded = json.loads(manifest.read_text(encoding="utf-8"))
        rebuilt = resolvers.Candidate(**{key: value for key, value in loaded["candidates"][0].items()
                                         if key in resolvers.Candidate.__dataclass_fields__})
        check("a manifest row rebuilds into a Candidate", rebuilt.canonical_id == "doi:10.0000/selftest")
        first = tmp / "Book.epub"
        first.write_bytes(b"x")
        check("a colliding name gets a distinct path", downloader._unique_path(tmp, "Book.epub").name == "Book (2).epub")
        check("the index is empty for a fresh id", "doi:10.0000/selftest" not in downloader.load_index({**cfg, "pens": {**cfg["pens"], "index": str(tmp / "index.jsonl")}}))

        # R5 CONTROL (D-3079): A SOURCE THAT REFUSES IS NOT A RUN THAT ENDS. Two candidates, one adapter whose
        # locate() refuses with AcquisitionError (the shape `no VALIDATED mirror for libgen` has in production).
        # The run must attempt BOTH and record two named refusals — before the R5 finding it attempted ONE and
        # raised out of the loop, so a saturated mirror could end a ten-candidate manifest at the first row.
        class _Fault(adapters.Adapter):
            id = "fault"
            licence_class = "open_access"

            def locate(self, candidate, cfg_inner):  # noqa: ARG002 - the fault IS the behaviour
                raise config.AcquisitionError("no VALIDATED mirror for `fault` (selftest)")

        adapters.REGISTRY["fault"] = _Fault
        fault_cfg = json.loads(json.dumps(cfg))
        fault_cfg["adapters"]["fault"] = {"enabled": True, "licence_class": "open_access", "requires_owner_word": False}
        fault_cfg["adapters"]["order"] = ["fault"]
        fault_cfg["pens"]["index"] = str(tmp / "fault-index.jsonl")
        fault_cfg["pens"]["evidence"] = str(tmp / "evidence")
        two = json.loads(manifest.read_text(encoding="utf-8"))
        two["candidates"].append({**two["candidates"][0], "canonical_id": "doi:10.0000/selftest-two"})
        two_path = tmp / "manifest-two.json"
        two_path.write_text(json.dumps(two), encoding="utf-8")
        result = downloader.fetch_manifest(two_path, fault_cfg)
        check("a refusing source does not end the run (two attempted, both named)",
              len(result["outcomes"]) == 2 and all(
                  any(attempt.get("failure_class") == "adapter_error" for attempt in outcome["attempts"])
                  for outcome in result["outcomes"]),
              json.dumps(result["counts"]))
        adapters.REGISTRY.pop("fault", None)

    # the receipt vocabulary: a shadow run without a word is refused BEFORE any network call.
    check("allow_shadow without an owner word is refused",
          _raises(lambda: downloader.fetch_manifest(Path("/nonexistent.json"), cfg, allow_shadow=True), config.AcquisitionError))

    failed = [name for name, passed, _ in checks if not passed]
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}" + (f" — {detail}" if detail and not passed else ""))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks green")
    return 0 if not failed else 1


def _refusal(call) -> str:
    """The refusal's own words — so a control can assert WHAT a miss says, not only that it refused."""
    try:
        call()
    except BaseException as error:  # noqa: BLE001 - the control asserts the message, never re-raises
        return str(error)
    return ""


def _raises(call, expected: type[BaseException] | None = None) -> bool:
    """True when the call refuses with the expected class (or any refusal when none is named)."""
    try:
        call()
    except BaseException as error:  # noqa: BLE001 - the control asserts the refusal, not its plumbing
        return isinstance(error, expected) if expected else True
    return False


def main(argv: list[str] | None = None) -> int:
    """Parse argv, load the declaration, dispatch one act."""
    parser = argparse.ArgumentParser(description="The acquisition lane: gap → manifest → bytes in the INBOX (D-3078)")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--selftest", action="store_true", help="run the declared controls and exit")
    subparsers = parser.add_subparsers(dest="command")

    gap_parser = subparsers.add_parser("gap", help="what the knowledge layer cannot back")
    gap_parser.add_argument("--limit", type=int, default=None)

    map_parser = subparsers.add_parser("map", help="a gap → a ranked manifest of resolver-returned works")
    map_parser.add_argument("--gap", type=str, default=None)
    map_parser.add_argument("--census", action="store_true", help="use the worst MEASURED starvation gap")
    map_parser.add_argument("--index", type=int, default=0)
    map_parser.add_argument("--limit", type=int, default=None)
    map_parser.add_argument("--show", type=int, default=10)

    fetch_parser = subparsers.add_parser("fetch", help="execute a manifest into the INBOX")
    fetch_parser.add_argument("--manifest", required=True)
    fetch_parser.add_argument("--limit", type=int, default=None)
    fetch_parser.add_argument("--dry-run", action="store_true")
    fetch_parser.add_argument("--allow-shadow", type=str, default=None, metavar="OWNER_WORD")

    subparsers.add_parser("status", help="the lane's own state")

    sources_parser = subparsers.add_parser("sources", help="the research-source register (D-3080)")
    sources_parser.add_argument("--check", action="store_true", help="verify every declaration resolves (the default reading)")
    sources_parser.add_argument("--task", choices=["books", "papers", "shadow", "all"], default="")
    sources_parser.add_argument("--json", action="store_true")
    mirrors_parser = subparsers.add_parser("mirrors", help="which mirror domains are validated today")
    mirrors_parser.add_argument("--refresh", action="store_true")

    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.command:
        parser.print_help()
        return 2
    cfg = config.load_config()
    handlers = {"gap": cmd_gap, "map": cmd_map, "fetch": cmd_fetch, "status": cmd_status,
                "mirrors": cmd_mirrors, "sources": cmd_sources}
    try:
        return handlers[args.command](args, cfg)
    except config.AcquisitionError as refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
