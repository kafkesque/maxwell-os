"""schema_accessor.py — Typed field accessors for v2.x/v3.0 schema compatibility.

Authority: D2120 | CONSTITUTION.md R14 (schema stamps)

All pipeline stages import from here instead of reaching into dicts with
ad-hoc .get() fallbacks. This provides:
  1. Single migration point — when v2.x support is dropped, delete the fallback
  2. Self-documenting contracts — function name IS the field semantic
  3. Zero overhead — pure functions, no classes, no imports beyond stdlib
  4. Crash-safe — returns safe defaults, never raises KeyError

Usage:
    from pipeline.schema_accessor import fb_definition, fb_id
    definition = fb_definition(fb_dict)
"""

from __future__ import annotations

from typing import Any

# ── Foundation Block (FB) accessors ──────────────────────────────────────

def fb_id(fb: dict[str, Any]) -> str:
    """v3.0: fb_id | v2.x: principle_id"""
    return str(fb.get("fb_id") or fb.get("principle_id", ""))


def fb_definition(fb: dict[str, Any]) -> str:
    """v3.0: definition | v2.x: principle_text"""
    return str(fb.get("definition") or fb.get("principle_text", ""))


def fb_name(fb: dict[str, Any]) -> str:
    """v3.0: name | v2.x: falls back to first 50 chars of definition"""
    name = fb.get("name", "")
    if name:
        return str(name)
    definition = fb_definition(fb)
    return definition[:50] + "..." if len(definition) > 50 else definition


def fb_mechanism(fb: dict[str, Any]) -> str:
    """v3.0: mechanism field. v2.x: not present — returns empty."""
    return str(fb.get("mechanism", ""))


def fb_boundary(fb: dict[str, Any]) -> str:
    """v3.0: boundary field. v2.x: falls back to application."""
    return str(fb.get("boundary") or fb.get("application", ""))


def fb_consequence(fb: dict[str, Any]) -> str:
    """v3.0: consequence field. v2.x: falls back to failure_mode or elaboration."""
    return str(
        fb.get("consequence")
        or fb.get("failure_mode")
        or fb.get("elaboration", "")
    )


def fb_source_texts(fb: dict[str, Any]) -> list[str]:
    """v3.0: evidence_passages | v2.x: source_principles[].principle_text"""
    if "evidence_passages" in fb:
        passages = fb["evidence_passages"]
        if isinstance(passages, list):
            return [str(p) for p in passages]
    source_principles = fb.get("source_principles", [])
    if isinstance(source_principles, list):
        return [
            str(p.get("principle_text", ""))
            for p in source_principles
            if isinstance(p, dict)
        ]
    return []


def fb_source_texts_shown(fb: dict[str, Any]) -> list[str]:
    """v3.0: evidence_passages_shown (subset actually shown to LLM)."""
    shown = fb.get("evidence_passages_shown", [])
    if isinstance(shown, list) and shown:
        return [str(p) for p in shown]
    return fb_source_texts(fb)


def fb_source_text_concat(fb: dict[str, Any]) -> str | None:
    """D2131: Concatenated source paragraph text for fast verification. Single string."""
    return fb.get("source_text")


def fb_source_books(fb: dict[str, Any]) -> list[str]:
    """v2.x/v3.0: source_books or source_clusters[].source_book."""
    books = fb.get("source_books", [])
    if isinstance(books, list) and books:
        return [str(b) for b in books]
    # Fallback: extract from source_clusters
    clusters = fb.get("source_clusters", [])
    if isinstance(clusters, list):
        return list({
            str(c.get("source_book", ""))
            for c in clusters
            if isinstance(c, dict) and c.get("source_book")
        })
    return []


def fb_source_ids(fb: dict[str, Any]) -> list[str]:
    """D2185: Canonical source_ids (SHA-256 author|title) for BORP/epistemic counting.
    
    Prefer source_ids (populated by S2 from S1.5 canonical hashes).
    Fall back to source_books (filenames) for v2.x backward compatibility.
    """
    source_ids = fb.get("source_ids", [])
    if isinstance(source_ids, list) and source_ids:
        return [str(s) for s in source_ids]
    # Fallback: derive from source_books (less accurate — filenames, not canonical)
    return fb_source_books(fb)


def fb_domains(fb: dict[str, Any]) -> list[str]:
    """v3.0: domains list | v2.x: domain string or domains list."""
    domains = fb.get("domains", [])
    if isinstance(domains, list):
        return [str(d) for d in domains]
    domain = fb.get("domain", "")
    return [str(domain)] if domain else []


def fb_discipline(fb: dict[str, Any]) -> str:
    """D316: SINGULAR discipline — always exactly one canonical discipline.

    v3.0 (D2066-amended): discipline is singular. Multi-label applies to domains only.
    Backward compat: if old 'disciplines' list is present, takes first element.
    """
    disc = fb.get("discipline", "")
    if disc:
        return str(disc)
    # Backward compat: old multi-label 'disciplines' list
    disciplines = fb.get("disciplines", [])
    if isinstance(disciplines, list) and disciplines:
        return str(disciplines[0])
    return "emerging"


def fb_disciplines(fb: dict[str, Any]) -> list[str]:
    """Backward compat wrapper: returns single discipline as a 1-element list.

    DEPRECATED: Use fb_discipline() for new code. This exists for callers
    that haven't been updated from the multi-label era.
    """
    disc = fb_discipline(fb)
    return [disc] if disc else []


def fb_discipline_raw(fb: dict[str, Any]) -> str | None:
    """Raw LLM discipline output, before canonical matching. Singular."""
    raw = fb.get("discipline_raw")
    if raw and isinstance(raw, str):
        return raw
    # Backward compat: old list format
    raw_list = fb.get("disciplines_raw", [])
    if isinstance(raw_list, list) and raw_list:
        return str(raw_list[0])
    return None


def fb_disciplines_raw(fb: dict[str, Any]) -> list[str]:
    """Backward compat wrapper: returns raw discipline as 1-element list.

    DEPRECATED: Use fb_discipline_raw() for new code.
    """
    raw = fb_discipline_raw(fb)
    return [raw] if raw else []


def fb_related_fbs(fb: dict[str, Any]) -> list[dict]:
    """P1.4: Related FB edges for LightRAG graph foundation."""
    return list(fb.get("related_fbs", []))


def fb_depth(fb: dict[str, Any]) -> str:
    """v3.0: depth | v2.x: depth (same field name, but v2 may be None)."""
    return str(fb.get("depth", "specialized"))


def fb_evidence_type(fb: dict[str, Any]) -> str:
    """v3.0: evidence | v2.x: evidence (cited/axiomatic)."""
    return str(fb.get("evidence", "cited"))


def fb_context(fb: dict[str, Any]) -> str | None:
    """v1 parity: comma-separated multi-select — business, design, system, academic, personal."""
    return fb.get("context")


def fb_accessibility(fb: dict[str, Any]) -> str | None:
    """v1 parity: self-evident (immediately graspable) | prerequisite (requires prior concept)."""
    return fb.get("accessibility")


def fb_intimacy_boundary(fb: dict[str, Any]) -> str | None:
    """v1 parity: Space routing — public (Knowledge base), selective, private (deathpectation)."""
    return fb.get("intimacy_boundary")


def fb_provenance(fb: dict[str, Any]) -> str:
    """C29: Provenance tier — human_verbatim | llm_extracted_from_source | llm_hypothesis."""
    return str(fb.get("provenance", "llm_extracted_from_source"))


def fb_route(fb: dict[str, Any]) -> str:
    """v3.0: route | v2.x: route or content_type."""
    return str(fb.get("route") or fb.get("content_type", "FB"))


def fb_is_summary(fb: dict[str, Any]) -> bool:
    """v3.0: is_summary self-flag. v2.x: not present — returns False."""
    return bool(fb.get("is_summary", False))


# ── Principle accessors ──────────────────────────────────────────────────

def principle_id(p: dict[str, Any]) -> str:
    """v3.0: fb_id | v2.x: principle_id"""
    return str(p.get("fb_id") or p.get("principle_id", ""))


def principle_text(p: dict[str, Any]) -> str:
    """v3.0: definition | v2.x: principle_text"""
    return str(p.get("definition") or p.get("principle_text", ""))


# ── Segment accessors ────────────────────────────────────────────────────

def segment_id(seg: dict[str, Any]) -> str:
    """Segment identifier."""
    return str(seg.get("segment_id", ""))


def segment_text(seg: dict[str, Any]) -> str:
    """Segment text content."""
    return str(seg.get("text", ""))


def segment_source_book(seg: dict[str, Any]) -> str:
    """Segment source book filename."""
    return str(seg.get("source_book", ""))


# ── Cluster accessors ────────────────────────────────────────────────────

def cluster_id(cluster: dict[str, Any]) -> str:
    """Cluster identifier."""
    return str(cluster.get("cluster_id", ""))

def cluster_segment_ids(cluster: dict[str, Any]) -> list[str]:
    """Segment IDs in a cluster."""
    seg_ids = cluster.get("segment_ids", [])
    return [str(s) for s in seg_ids] if isinstance(seg_ids, list) else []

def cluster_source_books(cluster: dict[str, Any]) -> list[str]:
    """Distinct source books in a cluster."""
    books = cluster.get("source_books", [])
    if isinstance(books, list) and books:
        return [str(b) for b in books]
    # Fallback: extract from segment metadata
    segments = cluster.get("segments", [])
    if isinstance(segments, list):
        return list({
            segment_source_book(s)
            for s in segments
            if isinstance(s, dict) and segment_source_book(s)
        })
    return []

def cluster_is_convergent(cluster: dict[str, Any]) -> bool:
    """Whether cluster has >=2 distinct source books."""
    return bool(cluster.get("is_convergent", False))


# ═══════════════════════════════════════════════════════════════════════════
# D2130: Agentic metadata accessors
# ═══════════════════════════════════════════════════════════════════════════

def fb_difficulty_level(fb: dict[str, Any]) -> str | None:
    """beginner | intermediate | expert — derived from depth + discipline complexity."""
    return fb.get("difficulty_level")


def fb_temporal_scope(fb: dict[str, Any]) -> str | None:
    """timeless | contemporary | era-specific."""
    return fb.get("temporal_scope")


def fb_confidence_score(fb: dict[str, Any]) -> float | None:
    """Aggregated verification confidence from Stage 5."""
    return fb.get("confidence_score")


def fb_prerequisite_fbs(fb: dict[str, Any]) -> list[str]:
    """FB IDs that should be understood before this one."""
    prereqs = fb.get("prerequisite_fbs", [])
    return prereqs if isinstance(prereqs, list) else []


def fb_procedural_skill(fb: dict[str, Any]) -> str | None:
    """Agent tool/function name this FB enables."""
    return fb.get("procedural_skill")


def fb_contradicts_fbs(fb: dict[str, Any]) -> list[str]:
    """FB IDs known to conflict with this one."""
    conflicts = fb.get("contradicts_fbs", [])
    return conflicts if isinstance(conflicts, list) else []


def fb_usage_count(fb: dict[str, Any]) -> int:
    """Times this FB has been retrieved/used."""
    return fb.get("usage_count", 0)


def fb_last_retrieved(fb: dict[str, Any]) -> str | None:
    """ISO timestamp of last retrieval."""
    return fb.get("last_retrieved_at")


def fb_feedback_score(fb: dict[str, Any]) -> float | None:
    """Aggregated agent feedback score 0.0-1.0."""
    return fb.get("feedback_score")


def fb_feedback_count(fb: dict[str, Any]) -> int:
    """Number of feedback ratings received."""
    return fb.get("feedback_count", 0)


def fb_version(fb: dict[str, Any]) -> int:
    """FB version number (increments on significant update)."""
    return fb.get("fb_version", 1)


def fb_source_principle_ids(fb: dict[str, Any]) -> list[str]:
    """Principle IDs from Stage 2 (reference, not embedded text)."""
    ids = fb.get("source_principle_ids", [])
    return ids if isinstance(ids, list) else []


# ── D2283: FB Schema Split — Core vs Enrichment Contract ─────────────────

# Core fields: output by S2 extraction, verified by S5 NLI.
# These are factual claims about the source text — must be evidence-grounded.
FB_CORE_FIELDS: tuple[str, ...] = (
    "name",
    "definition",
    "mechanism",
    "boundary",
    "consequence",
    "evidence_passages",
    "evidence_passages_shown",
    "source_books",
    "source_principles",
    "is_summary",
    "is_convergent",
)

# Enrichment fields: output by S4 classification, NOT verified by S5.
# These are metadata, interpretation aids, and downstream consumption labels.
# S5 must NOT use enrichment fields for verification (D2283: no field substitution).
FB_ENRICHMENT_FIELDS: tuple[str, ...] = (
    "application",
    "failure_mode",
    "elaboration",
    "jargon",
    "domains",
    "depth",
    "discipline",
    "extraction_type",
    "route",
    "confidence",
    "cribs_warnings",
)


def fb_is_core_field(field_name: str) -> bool:
    """D2283: Returns True if field is a core (verified) field."""
    return field_name in FB_CORE_FIELDS


def fb_is_enrichment_field(field_name: str) -> bool:
    """D2283: Returns True if field is an enrichment (unverified) field."""
    return field_name in FB_ENRICHMENT_FIELDS


def fb_core_fields_present(fb: dict[str, Any]) -> dict[str, bool]:
    """D2283: Check which core fields are present and non-empty in an FB.

    Returns a dict of field_name → bool. Used by verification stages
    to ensure core fields exist before NLI checks.
    """
    result: dict[str, bool] = {}
    for field in FB_CORE_FIELDS:
        val = fb.get(field)
        if val is None:
            result[field] = False
        elif isinstance(val, str):
            result[field] = len(val.strip()) > 0
        elif isinstance(val, (list, tuple)):
            result[field] = len(val) > 0
        elif isinstance(val, bool):
            result[field] = True  # booleans are always "present" regardless of value
        else:
            result[field] = val is not None
    return result


# ── D2284: ISOR — Independent Source Support Ratio ───────────────────────

def _extract_author_surname(source_book: str) -> str:
    """Extract author surname from a 'Title — Author Name' source book string.

    Handles: 'Predictably Irrational — Dan Ariely' → 'Ariely'
             'Thinking, Fast and Slow — Daniel Kahneman' → 'Kahneman'
             'Priceless — William Poundstone' → 'Poundstone'
    """
    if " — " in source_book:
        author_part = source_book.split(" — ", 1)[1].strip()
        # Take last word as surname
        parts = author_part.split()
        if parts:
            return parts[-1].lower()
    return source_book.lower()


def isor_score(fb: dict[str, Any]) -> dict[str, Any]:
    """D2284: Compute ISOR (Independent Source Support Ratio) for an FB.

    Beyond simple BORP≥2 count. Evaluates three dimensions:
      1. Author independence: distinct authors / total sources
      2. Domain diversity: distinct domains across sources (proxy for evidence tradition)
      3. Source count: raw distinct source book count

    Returns dict with scores and a composite independence rating.

    Rating scale:
      - "strong": ≥2 authors, ≥2 domains, ≥3 sources
      - "medium": ≥2 authors OR ≥2 domains, ≥2 sources
      - "weak": single author/source
    """
    source_books = fb.get("source_books", [])
    if not isinstance(source_books, list) or len(source_books) == 0:
        return {
            "score": 0.0,
            "rating": "weak",
            "n_sources": 0,
            "n_authors": 0,
            "n_domains": 0,
            "detail": "No source books",
        }

    # 1. Author independence
    authors: set[str] = set()
    for sb in source_books:
        surname = _extract_author_surname(str(sb))
        if surname:
            authors.add(surname)
    n_authors = len(authors)
    author_score = min(n_authors / max(len(source_books), 1), 1.0)

    # 2. Domain diversity (from FB domains field)
    domains = fb.get("domains", [])
    if not isinstance(domains, list):
        domains = [domains] if domains else []
    n_domains = len(set(domains))
    domain_score = min(n_domains / 3.0, 1.0)  # 3+ domains = full score

    # 3. Raw source count
    n_sources = len(set(source_books))
    count_score = min(n_sources / 3.0, 1.0)  # 3+ sources = full score

    # Composite score: weighted average
    composite = round(0.50 * author_score + 0.25 * domain_score + 0.25 * count_score, 3)

    # Rating
    if n_authors >= 2 and n_domains >= 2 and n_sources >= 3:
        rating = "strong"
    elif n_authors >= 2 or n_domains >= 2 and n_sources >= 2:
        rating = "medium"
    else:
        rating = "weak"

    return {
        "score": composite,
        "rating": rating,
        "n_sources": n_sources,
        "n_authors": n_authors,
        "n_domains": n_domains,
        "author_score": round(author_score, 3),
        "domain_score": round(domain_score, 3),
        "count_score": round(count_score, 3),
        "detail": (
            f"ISOR {rating}: {n_authors} authors, {n_domains} domains, "
            f"{n_sources} sources → composite {composite}"
        ),
    }


def isor_rating(fb: dict[str, Any]) -> str:
    """D2284: Shortcut — return just the ISOR rating string (strong/medium/weak)."""
    return str(isor_score(fb).get("rating", "weak"))
