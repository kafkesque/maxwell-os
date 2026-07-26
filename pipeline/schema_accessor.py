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


def fb_domains(fb: dict[str, Any]) -> list[str]:
    """v3.0: domains list | v2.x: domain string or domains list."""
    domains = fb.get("domains", [])
    if isinstance(domains, list):
        return [str(d) for d in domains]
    domain = fb.get("domain", "")
    return [str(domain)] if domain else []


def fb_depth(fb: dict[str, Any]) -> str:
    """v3.0: depth | v2.x: depth (same field name, but v2 may be None)."""
    return str(fb.get("depth", "specialized"))


def fb_evidence_type(fb: dict[str, Any]) -> str:
    """v3.0: evidence | v2.x: evidence (cited/axiomatic)."""
    return str(fb.get("evidence", "cited"))


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
