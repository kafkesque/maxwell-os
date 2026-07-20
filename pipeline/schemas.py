"""
schemas.py — Pydantic v2 boundary contracts for Maxwell OS v2.0 pipeline.
=========================================================================
Authority: CONSTITUTION.md §3, §4

Every pipeline stage reads/writes typed objects.
Pydantic Literal types make invalid labels structurally impossible (C10, D1058).

Inter-stage contracts (6 stages):
    Segment   — Stage 1 output: text chunk + provenance
    Principle — Stage 2 output: Qwen3.6-extracted principle
    Cluster   — Stage 3 output: HDBSCAN cluster of principles
    FB        — Stage 4 output: Merged Foundation Block
    VerifiedFB— Stage 5 output: FB + verification result
    FBRecord  — Stage 6 output: Canonical DB row

All objects stamped: schema_version, gen_model, pipeline_commit (R14).
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

# ═══════════════════════════════════════════════════════════════════════════
# Taxonomy Literal Types — extracted from config/taxonomy_v5.yaml
# Invalid labels are structurally impossible at the Pydantic boundary.
# ═══════════════════════════════════════════════════════════════════════════

DOMAIN_LITERAL = Literal[
    "graphic design",
    "brand identity",
    "editorial & advertising",
    "motion design",
    "environmental design",
    "digital product",
    "data visualization",
    "creative technology",
    "web & ui",
    "user experience",
    "illustration",
    "packaging",
    "business operations",
    "business development",
    "entrepreneurship",
    "organizational behavior",
    "ai & agents",
    "ai systems",
    "engineering practice",
    "computational art",
    "code & computation",
    "computational science & physics",
    "systems & frameworks",
    "semiotics & communication",
    "research & methodology",
    "emerging",  # catch-all for unclassified
]

DISCIPLINE_LITERAL = Literal[
    "visual perception",
    "visual semiotics",
    "cultural design",
    "semiotics",
    "multimodal metaphor",
    "typography",
    "color theory",
    "composition & layout",
    "geometry & proportion",
    "motion & time",
    "iconography",
    "design psychology",
    "information architecture",
    "narrative design",
    "design systems",
    "design strategy",
    "creative process",
    "cognitive science",
    "behavioral economics",
    "decision making",
    "psychology",
    "linguistics",
    "leadership",
    "strategic thinking",
    "project management",
    "risk management",
    "personal productivity",
    "marketing",
    "systems thinking",
    "complex adaptive systems",
    "systems engineering",
    "research methodology",
    "operations research",
    "prompt engineering",
    "agentic architecture",
    "machine learning",
    "generative ai",
    "software engineering",
    "creative coding",
    "generative design",
    "computational physics & simulation",
    "computational geometry",
    "game design",
    "social engineering",
    "political economy",
    "privacy & surveillance",
    "philosophy",
    "emerging",  # catch-all
]

DEPTH_LITERAL = Literal["universal", "cross-domain", "domain", "specialized"]
EVIDENCE_LITERAL = Literal["cited", "axiomatic"]
VERIFICATION_STATUS = Literal["PASS", "FLAG", "QUARANTINE", "PENDING"]

# ═══════════════════════════════════════════════════════════════════════════
# Base — every persistent object carries these stamps (R14, C10)
# ═══════════════════════════════════════════════════════════════════════════

class StampedRecord(BaseModel):
    """Base mixin: every persistent pipeline record carries these stamps."""
    schema_version: str = Field(default="2.0")
    gen_model: Optional[str] = Field(default=None)
    pipeline_commit: str = Field(default="v2.0-init")
    pipeline_run_id: Optional[str] = Field(
        default=None,
        description="UUID identifying a single pipeline run. All records from the same run share this ID."
    )
    taxonomy_version: str = Field(default="v5.0")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: Chunk — MD text → Segments
# ═══════════════════════════════════════════════════════════════════════════

class Segment(StampedRecord):
    """A single text chunk from a markdown book, with SHA-256 dedup."""
    segment_id: str = Field(description="SHA-256 hash of text (dedup key)")
    text: str = Field(description="The chunk text", min_length=20)
    source_book: str = Field(description="Source book filename or path")
    char_start: int = Field(description="Character offset start in source")
    char_end: int = Field(description="Character offset end in source")
    word_count: int = Field(description="Word count of this segment", ge=0)

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Segment text must not be empty")
        return v.strip()

    @field_validator("segment_id")
    @classmethod
    def segment_id_is_hex(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError(f"segment_id must be 64-char SHA-256 hex, got {len(v)}")
        return v.lower()


# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: Extract — Segments → Principles (Qwen3.6)
# ═══════════════════════════════════════════════════════════════════════════

class Principle(StampedRecord):
    """A single principle extracted by Qwen3.6 from one or more segments."""
    principle_id: str = Field(description="SHA-256 hash of principle text (dedup key)")
    principle_text: str = Field(description="The extracted principle")
    source_segments: list[str] = Field(
        description="List of segment_ids that generated this principle"
    )
    source_books: list[str] = Field(
        description="List of source book filenames"
    )
    minhash_signature: Optional[str] = Field(
        default=None, description="MinHash signature for near-dedup (hex)"
    )

    @field_validator("principle_text")
    @classmethod
    def principle_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Principle text must not be empty")
        return v.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: Cluster — Principles → Clusters (HDBSCAN)
# ═══════════════════════════════════════════════════════════════════════════

class Cluster(StampedRecord):
    """A semantic cluster of related principles (HDBSCAN output)."""
    cluster_id: int = Field(description="Sequential cluster ID")
    principle_ids: list[str] = Field(description="Principle IDs in this cluster")
    centroid_text: str = Field(description="Most central principle text")
    cohesion: float = Field(
        description="Mean pairwise cosine similarity", ge=0.0, le=1.0
    )
    size: int = Field(description="Number of principles in cluster", ge=1)
    distinct_books: int = Field(
        description="Number of distinct source books", ge=1
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: Merge + Classify — Clusters → FBs (Qwen3.6 + SALSA)
# ═══════════════════════════════════════════════════════════════════════════

class FB(StampedRecord):
    """A Foundation Block: merged principles + classification.

    Classification fields use Pydantic Literal types — hallucinated labels
    are structurally impossible (caught at construction, not post-hoc).
    """
    fb_id: str = Field(description="SHA-256 hash of name + definition")
    name: str = Field(description="Canonical concept name", min_length=3)
    definition: str = Field(
        description="3-4 sentence definition. S1: name+what. S2: mechanism. S3-4: constraint.",
        min_length=30,
    )
    application: str = Field(
        description="When [situation] → do [action]. One concrete example.",
        min_length=10,
    )
    failure_mode: str = Field(
        description="How this principle fails in practice. 1-3 sentences.",
        min_length=10,
    )
    elaboration: str = Field(
        description="Deeper explanation with edge cases and nuance. 3-5 sentences.",
        min_length=20,
    )
    keywords: str = Field(description="3-5 key terms, comma-separated")
    jargon: Optional[str] = Field(
        default=None,
        description="Specialized terminology explanation. None if no jargon.",
    )

    # ── Classification (Literal types enforce validity at construction) ──
    domains: list[DOMAIN_LITERAL] = Field(  # type: ignore[valid-type]
        description="1-5 canonical domains (D150: max 5). Validated via synonym matching; 'emerging' if no match.",
        min_length=1,
        max_length=5,
    )
    discipline: DISCIPLINE_LITERAL = Field(  # type: ignore[valid-type]
        description="Canonical discipline from 47-discipline taxonomy. Validated; 'emerging' if no match."
    )

    # ── Raw classification — LLM output preserved FOREVER (never overwritten) ──
    # Authority: governance/domain_labelling.md §1 (D1055-FIX Channel B)
    # These are the LLM's actual labels before validation/synonym-matching.
    # When canonical ≠ raw, the raw label accumulates; when it crosses a threshold,
    # it earns a canonical slot in taxonomy_v5.yaml.
    domains_raw: Optional[list[str]] = Field(
        default=None,
        description="LLM's original domain labels before canonical validation. Preserved for taxonomy expansion."
    )
    discipline_raw: Optional[str] = Field(
        default=None,
        description="LLM's original discipline before canonical validation. Preserved for taxonomy expansion."
    )

    depth: DEPTH_LITERAL = Field(  # type: ignore[valid-type]
        description="universal | cross-domain | domain | specialized"
    )
    evidence: EVIDENCE_LITERAL = Field(  # type: ignore[valid-type]
        description="cited (from source text) | axiomatic (self-evident)"
    )

    # ── Provenance ──
    source_clusters: list[int] = Field(description="Cluster IDs that formed this FB")
    source_books: list[str] = Field(description="Distinct source books")
    s3_original_domain: Optional[str] = Field(
        default=None,
        description="Crawl provenance: which domain folder the source books came from (e.g., 'DOMAIN 4 Business'). Immutable."
    )
    classification_method: str = Field(
        default="SALSA", description="SALSA | FastFit | manual"
    )

    @field_validator("domains")
    @classmethod
    def domains_unique_and_sorted(cls, v: list) -> list:
        seen = set()
        unique = []
        for d in v:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        return sorted(unique)


# ═══════════════════════════════════════════════════════════════════════════
# Stage 5: Verify — FBs → Verified FBs (Phi-4-mini + BORP)
# ═══════════════════════════════════════════════════════════════════════════

class VerificationResult(BaseModel):
    """Result of a single verification check."""
    check_name: str = Field(description="Name of the check (e.g., 'BORP', 'factual')")
    passed: bool = Field(description="Did the check pass?")
    score: float = Field(description="Score 0.0-1.0", ge=0.0, le=1.0)
    detail: Optional[str] = Field(default=None, description="Explanation of result")


class VerifiedFB(FB):
    """An FB after verification — adds verification results."""
    verification_results: list[VerificationResult] = Field(
        default_factory=list, description="All verification check results"
    )
    borp_score: float = Field(
        description="BORP score: distinct_sources / min_required",
        ge=0.0,
        le=1.0,
        default=1.0,
    )
    status: VERIFICATION_STATUS = Field(  # type: ignore[valid-type]
        default="PENDING",
        description="PASS | FLAG | QUARANTINE | PENDING",
    )
    needs_human_review: bool = Field(
        default=False, description="True if FLAG or QUARANTINE"
    )
    verifier_model: Optional[str] = Field(
        default=None, description="Model that performed verification"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 6: Commit — SQLite row representation
# ═══════════════════════════════════════════════════════════════════════════

class FBRecord(VerifiedFB):
    """Canonical DB record — VerifiedFB + DB-specific fields."""
    rowid: Optional[int] = Field(default=None, description="SQLite rowid")
    committed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helper: Load taxonomy canonical values for runtime validation
# ═══════════════════════════════════════════════════════════════════════════

def load_taxonomy():
    """Load taxonomy from config/taxonomy_v5.yaml.

    Returns (domains: list[str], disciplines: list[str], domain_to_group: dict).
    """
    import yaml
    from pathlib import Path

    config_path = Path(__file__).resolve().parent.parent / "config" / "taxonomy_v5.yaml"
    with open(config_path) as f:
        taxa = yaml.safe_load(f)

    domains = [d["canonical"] for d in taxa.get("domains", [])]
    disciplines = [d["canonical"] for d in taxa.get("disciplines", [])]
    domain_to_group = {d["canonical"]: d.get("group", "") for d in taxa.get("domains", [])}

    domains.append("emerging")
    disciplines.append("emerging")

    return domains, disciplines, domain_to_group


# Cache at import time
CANONICAL_DOMAINS, CANONICAL_DISCIPLINES, DOMAIN_TO_GROUP = load_taxonomy()


def is_valid_domain(domain: str) -> bool:
    """Check if a domain label is canonical (including 'emerging')."""
    return domain in CANONICAL_DOMAINS


def is_valid_discipline(discipline: str) -> bool:
    """Check if a discipline label is canonical (including 'emerging')."""
    return discipline in CANONICAL_DISCIPLINES


# ═══════════════════════════════════════════════════════════════════════════
# Synonym Index — built from taxonomy_v5.yaml raw aliases + synonym_map.yaml
# Used by stage4 to match LLM labels to canonical labels before falling back
# to "emerging". Reduces data loss and provides richer raw label accumulation.
# ═══════════════════════════════════════════════════════════════════════════

_SYNONYM_INDEX = None  # Lazy-built cache


def _build_synonym_index():
    """Build {synonym_lower: canonical} lookup from taxonomy + synonym_map."""
    import yaml
    from pathlib import Path

    config_root = Path(__file__).resolve().parent.parent / "config"
    lookup = {}

    # 1. Taxonomy raw aliases (both domains and disciplines)
    tax_path = config_root / "taxonomy_v5.yaml"
    if tax_path.exists():
        with open(tax_path) as f:
            taxa = yaml.safe_load(f)
        for entry in taxa.get("domains", []) + taxa.get("disciplines", []):
            canonical = entry["canonical"].strip()
            lookup[canonical.lower()] = canonical
            for raw in entry.get("raw", []):
                raw_clean = raw.strip()
                if raw_clean:
                    lookup[raw_clean.lower()] = canonical

    # 2. Synonym_map.yaml (domain synonyms, keywords, patterns)
    syn_path = config_root / "synonym_map.yaml"
    if syn_path.exists():
        with open(syn_path) as f:
            syn_map = yaml.safe_load(f)
        for key, entry in syn_map.get("synonyms", {}).items():
            canonical = entry.get("canonical", "").strip()
            if canonical:
                lookup[canonical.lower()] = canonical
            for syn in entry.get("synonyms", []):
                syn_clean = syn.strip()
                if syn_clean:
                    lookup[syn_clean.lower()] = canonical
            # keywords are also useful for matching
            for kw in entry.get("keywords", []):
                kw_clean = kw.strip()
                if kw_clean and kw_clean.lower() not in lookup:
                    lookup[kw_clean.lower()] = canonical

    return lookup


def get_synonym_index():
    """Return the cached synonym → canonical lookup dict."""
    global _SYNONYM_INDEX
    if _SYNONYM_INDEX is None:
        _SYNONYM_INDEX = _build_synonym_index()
    return _SYNONYM_INDEX


def match_to_canonical(label: str, kind: str = "domain") -> str | None:
    """Try to match a label to a canonical taxonomy label via synonyms.

    Args:
        label: The label string from the LLM (e.g., "Visual Communication")
        kind: "domain" or "discipline" — constrains which canonical list to check against

    Returns:
        Canonical label string if matched, None otherwise.
    """
    if not label or not label.strip():
        return None

    label_lower = label.strip().lower()
    canonical_list = CANONICAL_DOMAINS if kind == "domain" else CANONICAL_DISCIPLINES

    # 1. Direct canonical match (case-insensitive)
    for c in canonical_list:
        if label_lower == c.lower():
            return c

    # 2. Synonym index lookup
    synonym_index = get_synonym_index()
    matched = synonym_index.get(label_lower)
    if matched:
        # Verify matched canonical is in the right list
        matched_lower = matched.lower()
        for c in canonical_list:
            if matched_lower == c.lower():
                return c
        # Matched a canonical from the wrong list (e.g., matched a domain
        # when looking for a discipline). Don't return it; let caller fall back.
        return None

    return None


def match_domains_to_canonical(labels: list[str]) -> list[str]:
    """Match a list of domain labels to canonical via synonyms.

    Returns list of canonical labels. Unmatched labels are omitted.
    """
    results = []
    for label in labels:
        matched = match_to_canonical(label, kind="domain")
        if matched:
            results.append(matched)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique
