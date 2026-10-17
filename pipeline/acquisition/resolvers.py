"""Resolver-first cartography: a gap becomes a RANKED MANIFEST of works that a resolver has returned.

THE DESIGN CLAIM (D-3078 invariant 2): a candidate that does not RESOLVE at OpenAlex or Crossref never enters a
manifest. There is no code path that writes a title from a model into a manifest — which is the mechanism, not a
promise, that keeps this lane free of the fabricated-citation class this repository already paid for twice.

The LLM is NOT the ranker. A ranker that reads a citation graph is cheaper, reproducible, and audit-able; the
local model, when it is used at all, only EXPANDS a query (declared in cartography.query_templates here, and in
`--expand` at the CLI, which is OFF by default).
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import net
from .config import ROOT, AcquisitionError, pipeline_commit

OPENALEX_SEARCH = "https://api.openalex.org/works?search={query}&per-page={rows}"
CROSSREF_SEARCH = "https://api.crossref.org/works?query={query}&rows={rows}"

STOPWORDS = frozenset(
    "a an and the of for in on to with from by at as is are its their this that these those "
    "handbook foundations survey introduction to".split()
)
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]+")


@dataclass
class Candidate:
    """One resolvable work. `canonical_id` is the resolver's own identity — never a title."""

    canonical_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str
    kind: str
    cited_by: int
    oa_pdf: str | None
    landing: str | None
    licence_class: str
    resolved_by: tuple[str, ...] = ()
    score: float = 0.0
    why_ranked: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "venue": self.venue,
            "kind": self.kind,
            "cited_by": self.cited_by,
            "oa_pdf": self.oa_pdf,
            "landing": self.landing,
            "licence_class": self.licence_class,
            "resolved_by": list(self.resolved_by),
            "score": round(self.score, 4),
            "why_ranked": list(self.why_ranked),
        }


def content_words(text: str) -> set[str]:
    """The words that carry a query's meaning, with the vocabulary of asking removed."""
    return {word.lower() for word in WORD.findall(text) if word.lower() not in STOPWORDS and len(word) > 2}


def _doi_of(record: dict[str, Any]) -> str | None:
    """Normalise any resolver's DOI spelling to `doi:<lowercase>`."""
    raw = record.get("doi")
    if not raw:
        return None
    text = str(raw).strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
    return f"doi:{text.lower()}" if text else None


def _as_candidate_openalex(work: dict[str, Any]) -> Candidate | None:
    """Turn one OpenAlex work into a Candidate, or None when it carries no resolver identity."""
    doi = _doi_of(work)
    openalex_id = str(work.get("id") or "").rsplit("/", 1)[-1]
    canonical = doi or (f"openalex:{openalex_id}" if openalex_id else None)
    if not canonical:
        return None
    location = work.get("best_oa_location") or {}
    access = work.get("open_access") or {}
    venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    authors = tuple(
        entry.get("author", {}).get("display_name", "")
        for entry in (work.get("authorships") or [])
        if entry.get("author", {}).get("display_name")
    )
    return Candidate(
        canonical_id=canonical,
        title=str(work.get("title") or work.get("display_name") or "").strip(),
        authors=authors,
        year=work.get("publication_year"),
        venue=str(venue),
        kind=str(work.get("type") or "unknown"),
        cited_by=int(work.get("cited_by_count") or 0),
        oa_pdf=location.get("pdf_url") or access.get("oa_url"),
        landing=location.get("landing_page_url") or work.get("id"),
        licence_class="open_access" if access.get("is_oa") else "publisher_licensed",
        resolved_by=("openalex",),
    )


def _as_candidate_crossref(item: dict[str, Any]) -> Candidate | None:
    """Turn one Crossref item into a Candidate; a DOI is Crossref's own identity, so it always has one."""
    canonical = _doi_of(item)
    if not canonical:
        return None
    title = " ".join(item.get("title") or []).strip()
    authors = tuple(
        " ".join(part for part in (entry.get("given"), entry.get("family")) if part).strip()
        for entry in (item.get("author") or [])
    )
    year = None
    for key in ("published-print", "published-online", "issued"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break
    return Candidate(
        canonical_id=canonical,
        title=title,
        authors=tuple(author for author in authors if author),
        year=year,
        venue=" ".join(item.get("container-title") or []) or str(item.get("publisher") or ""),
        kind=str(item.get("type") or "unknown"),
        cited_by=int(item.get("is-referenced-by-count") or 0),
        oa_pdf=None,
        landing=str(item.get("URL") or "") or None,
        licence_class=("open_access" if (item.get("license") or []) else "publisher_licensed"),
        resolved_by=("crossref",),
    )


def search_openalex(query: str, cfg: dict[str, Any]) -> list[Candidate]:
    """One OpenAlex search in the resolver's own RELEVANCE order; refused (not emptied) on a transport failure.

    The URL carries NO `sort=`: topical relevance is the search engine's job, reading order is `score`'s
    (config/acquisition.yaml#cartography.resolver_order — a defect the first live run measured, not a taste).
    """
    policy = cfg["cartography"]
    url = OPENALEX_SEARCH.format(query=net.quote(query), rows=int(policy.get("rows_per_query") or 20))
    payload = net.read_json(url, cfg, float((cfg.get("download") or {}).get("timeout_s") or 180))
    found = []
    for work in payload.get("results") or []:
        candidate = _as_candidate_openalex(work)
        if candidate:
            found.append(candidate)
    return found


def search_crossref(query: str, cfg: dict[str, Any]) -> list[Candidate]:
    """One Crossref search, used as the fallback resolver and as a second opinion."""
    policy = cfg["cartography"]
    url = CROSSREF_SEARCH.format(query=net.quote(query), rows=int(policy.get("rows_per_query") or 20))
    payload = net.read_json(url, cfg, float((cfg.get("download") or {}).get("timeout_s") or 180))
    items = (payload.get("message") or {}).get("items") or []
    return [candidate for candidate in (_as_candidate_crossref(item) for item in items) if candidate]


def merge(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Merge two resolvers' answers by canonical id, keeping every resolver that named the work."""
    merged: dict[str, Candidate] = {}
    for candidate in candidates:
        held = merged.get(candidate.canonical_id)
        if held is None:
            merged[candidate.canonical_id] = candidate
            continue
        held.resolved_by = tuple(dict.fromkeys(held.resolved_by + candidate.resolved_by))
        held.oa_pdf = held.oa_pdf or candidate.oa_pdf
        held.landing = held.landing or candidate.landing
        held.year = held.year or candidate.year
        held.venue = held.venue or candidate.venue
        held.cited_by = max(held.cited_by, candidate.cited_by)
        if held.licence_class != "open_access" and candidate.licence_class == "open_access":
            held.licence_class = candidate.licence_class
    return list(merged.values())


def score(candidate: Candidate, query: str, cfg: dict[str, Any]) -> Candidate:
    """Rank by a DECLARED weighted sum and keep the arithmetic that produced the rank on the row.

    The weights are in config/acquisition.yaml#cartography.score. `why_ranked` exists so a reader can disagree
    with the ranking on the evidence rather than on suspicion.
    """
    policy = cfg["cartography"]
    weights = policy["score"]
    filters = policy["filters"]
    this_year = _dt.date.today().year
    saturation = float(weights.get("citation_log_saturation") or 10000)
    citation = min(1.0, math.log10(1 + max(0, candidate.cited_by)) / math.log10(1 + saturation))
    floor = int(filters.get("min_year") or 1950)
    span = max(1, this_year - floor)
    recency = min(1.0, max(0.0, ((candidate.year or floor) - floor) / span))
    access = 1.0 if candidate.oa_pdf else 0.0
    is_book = 1.0 if candidate.kind in {"book", "book-chapter", "dissertation"} else 0.0
    total = (
        float(weights.get("citation_weight") or 1.0) * citation
        + float(weights.get("recency_weight") or 0.0) * recency
        + float(weights.get("oa_bonus") or 0.0) * access
        + float(weights.get("book_bonus") or 0.0) * is_book
    )
    candidate.score = total
    candidate.why_ranked = [
        f"citation={citation:.3f}({candidate.cited_by})",
        f"recency={recency:.3f}({candidate.year})",
        f"oa={'yes' if access else 'no'}",
        f"kind={candidate.kind}",
    ]
    asked = content_words(query)
    held = content_words(candidate.title)
    overlap = (len(asked & held) / len(asked)) if asked else 1.0
    candidate.why_ranked.append(f"query_overlap={overlap:.2f}")
    if asked and overlap < float(filters.get("min_query_token_overlap") or 0.0):
        candidate.score = 0.0
        candidate.why_ranked.append("refused_query_overlap")
    return candidate


def build_manifest(gap: dict[str, Any], cfg: dict[str, Any], limit: int | None = None) -> dict[str, Any]:
    """Turn ONE gap into a manifest: ask, merge, filter, rank, keep the refusals with their reasons.

    A gap names a `discipline` (or an explicit `query`); the query templates translate a census entry into
    askable questions. Every candidate keeps the resolver that answered it, so the manifest is evidence rather
    than a wish-list.
    """
    policy = cfg["cartography"]
    gap_id = str(gap.get("gap_id") or gap.get("discipline") or "unnamed")
    discipline = str(gap.get("discipline") or gap.get("query") or "").strip()
    if not discipline:
        raise AcquisitionError(f"gap `{gap_id}` names no discipline and no query")
    templates = [str(item) for item in policy.get("query_templates") or ["{discipline}"]]
    queries = [template.format(discipline=discipline) for template in templates[: int(policy.get("max_queries_per_gap") or 1)]]
    collected: list[Candidate] = []
    failures: list[dict[str, Any]] = []
    for query in queries:
        try:
            collected.extend(search_openalex(query, cfg))
        except net.NetworkRefused as refusal:
            failures.append(refusal.failure.as_dict())
            try:
                collected.extend(search_crossref(query, cfg))
            except net.NetworkRefused as second:
                failures.append(second.failure.as_dict())
    if not collected and failures:
        raise AcquisitionError(f"gap `{gap_id}`: neither resolver answered — {failures[0]['failure_class']}")
    filters = policy["filters"]
    minimum_year = int(filters.get("min_year") or 1950)
    allowed = set(filters.get("kinds") or [])
    ranked: list[Candidate] = []
    refused: list[dict[str, Any]] = []
    for candidate in merge(collected):
        if not candidate.title:
            refused.append({"canonical_id": candidate.canonical_id, "why": "no_title"})
            continue
        if allowed and candidate.kind not in allowed:
            refused.append({"canonical_id": candidate.canonical_id, "why": f"kind_{candidate.kind}_not_declared"})
            continue
        if candidate.year and candidate.year < minimum_year:
            refused.append({"canonical_id": candidate.canonical_id, "why": f"year_{candidate.year}_before_floor"})
            continue
        scored = score(candidate, queries[0], cfg)
        if scored.score <= 0.0:
            refused.append({"canonical_id": candidate.canonical_id, "why": ";".join(scored.why_ranked[-1:])})
            continue
        ranked.append(scored)
    ranked.sort(key=lambda item: (item.score, item.cited_by), reverse=True)
    if limit:
        ranked = ranked[: int(limit)]
    return {
        "schema_version": "1.0",
        "gen_model": "deterministic",
        "pipeline_commit": pipeline_commit(),
        "generated": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "act": "reading_cartography",
        "authority": "D-3078",
        "gap": gap,
        "queries": queries,
        "resolver_failures": failures,
        "candidates": [candidate.as_dict() for candidate in ranked],
        "refused": refused,
        "counts": {"queries": len(queries), "candidates": len(ranked), "refused": len(refused)},
    }


def write_manifest(manifest: dict[str, Any], cfg: dict[str, Any], name: str | None = None) -> Path:
    """Write a manifest as an evidence artefact — never into the corpus."""
    directory = ROOT / str((cfg.get("cartography") or {}).get("manifest_dir") or "governance/evidence")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name or str((manifest.get("gap") or {}).get("gap_id") or "gap"))[:60]
    target = directory / f"ACQ_MANIFEST_{safe}_{stamp}.json"
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
