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

from datetime import datetime
from typing import Literal

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

# ── D2073: Growth Edge categories ─────────────────────────────────────
GE_CATEGORY = Literal[
    "personal_idea",              # "I should build X" — user-originated
    "business_idea",              # "A service/product that does X"
    "inspiration",                # "This quote/concept resonated deeply"
    "academic_concept",           # "Needs theoretical investigation"
    "implementation_candidate",   # "This could become a product feature"
    "theoretical_investigation",  # "Does X work differently in context Y?"
    "pipeline_speculative",       # Pipeline-extracted, low-confidence insight
]
GE_STATUS = Literal[
    "open",              # Just captured, not yet evaluated
    "investigating",     # Actively researching/gathering evidence
    "implementing",      # Being built/applied right now
    "promoted",          # Graduated to FB, PT, or Project
    "archived",          # Not relevant now, kept for reference
]

# ═══════════════════════════════════════════════════════════════════════════
# Base — every persistent object carries these stamps (R14, C10)
# ═══════════════════════════════════════════════════════════════════════════

class StampedRecord(BaseModel):
    """Base mixin: every persistent pipeline record carries these stamps."""
    schema_version: str = Field(default="2.0")
    gen_model: str | None = Field(default=None)
    pipeline_commit: str = Field(default="v2.0-init")
    pipeline_run_id: str | None = Field(
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
    content_type: str = Field(
        default="principle",
        description="Type: 'principle' (reusable concept), "
                    "'process_template' (repeatable how-to method), "
                    "'process_instance' (concrete case study of a template in action), "
                    "'tool_instruction' (tool-specific command), "
                    "'fact' (domain factoid), 'meta' (navigation text)"
    )
    source_segments: list[str] = Field(
        description="List of segment_ids that generated this principle"
    )
    source_books: list[str] = Field(
        description="List of source book filenames"
    )
    minhash_signature: str | None = Field(
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
# Stage 4a: Process Template — Repeatable how-to methods (v1 PT schema D782)
# ═══════════════════════════════════════════════════════════════════════════

class ProcessTemplate(StampedRecord):
    """A repeatable step-by-step technique extracted from texts.

    Mirrors v1's PT Anytype schema (D782): trigger, prerequisite, done_condition,
    consulted_fbs, template_source, fb_query_domain, fb_query_intent.

    Distinct from FB: PT answers "how do I?" (procedural), FB answers "why/when?" (conceptual).
    """
    pt_id: str = Field(description="SHA-256 hash of process name + steps summary")
    name: str = Field(description="Concise name for this process", min_length=3)
    steps: str = Field(
        description="Numbered step-by-step method. 3-8 steps, each 1 sentence.",
        min_length=20,
    )
    trigger: str = Field(
        description="What situation or condition activates this process?",
        min_length=5,
    )
    prerequisite: str = Field(
        description="What must be in place before starting? (tools, data, skills, decisions)",
        min_length=3,
    )
    done_condition: str = Field(
        description="How do you know this process is complete? Observable outcome.",
        min_length=5,
    )
    failure_mode: str = Field(
        description="How this process fails or degrades in practice. 1-3 sentences.",
        min_length=10,
    )
    template_source: str = Field(
        description="Which book(s) this template was extracted from"
    )
    consulted_fbs: list[str] = Field(
        default_factory=list,
        description="FB IDs consulted during process execution (for runtime retrieval)"
    )
    fb_query_domain: str = Field(
        default="",
        description="Domain filter for runtime FB retrieval during execution"
    )
    fb_query_intent: str = Field(
        default="",
        description="Intent filter for runtime FB retrieval during execution"
    )

    # ── Classification (shared with FB) ──
    domains: list[DOMAIN_LITERAL] = Field(  # type: ignore[valid-type]
        min_length=1, max_length=5,
        description="1-5 canonical domains"
    )
    discipline: DISCIPLINE_LITERAL = Field(  # type: ignore[valid-type]
        description="Canonical discipline"
    )
    depth: DEPTH_LITERAL = Field(  # type: ignore[valid-type]
        description="universal | cross-domain | domain | specialized"
    )
    evidence: EVIDENCE_LITERAL = Field(  # type: ignore[valid-type]
        description="cited (from source text) | axiomatic (self-evident)"
    )

    # ── Provenance ──
    source_clusters: list[int] = Field(description="Cluster IDs that formed this PT")
    source_books: list[str] = Field(description="Distinct source books")
    source_principles: list[dict] = Field(
        default_factory=list,
        description="Source principles with texts embedded"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4b: Process Instance — Concrete case study of a template in action
# ═══════════════════════════════════════════════════════════════════════════

class ProcessInstance(StampedRecord):
    """A concrete case study documenting a Process Template being applied.

    The template says HOW; the instance proves IT WORKS. Instances are always linked
    to a parent PT and serve as evidence that the template is effective.
    """
    pi_id: str = Field(description="SHA-256 hash of instance text")
    parent_pt_id: str = Field(
        description="ProcessTemplate ID this instance is evidence for"
    )
    instance_text: str = Field(
        description="Concrete narrative: who did what, when, and what happened. 2-5 sentences.",
        min_length=30,
    )
    actors: str = Field(
        description="Who executed this process? (company, person, team)",
        default="",
    )
    outcome_metric: str = Field(
        description="Quantitative result if available: '+12% conversion', 'saved $2M'",
        default="",
    )
    outcome_qualitative: str = Field(
        description="Qualitative result: 'improved team alignment', 'faster decisions'",
        default="",
    )
    domain_context: str = Field(
        description="Industry or situation context for similarity matching",
        default="",
    )
    source_book: str = Field(description="Which book this case study comes from")
    source_segment_id: str = Field(description="Segment ID in source book")

    # ── Links ──
    source_principles: list[dict] = Field(
        default_factory=list,
        description="Source principles that contributed to this instance"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4c: Growth Edge — Speculative idea (pipeline OR human-created)
# ═══════════════════════════════════════════════════════════════════════════

class GrowthEdge(StampedRecord):
    """A speculative idea that may become an FB, PT, or Project.

    Growth Edges are the ONLY object type that can be created manually by the user.
    They serve as an idea inbox — upstream of all verified knowledge. Pipeline-
    extracted speculative insights also land here.

    D2073: GE is a full object type with its own schema, body format, and promotion
    path. It bridges pipeline output and human judgment.
    """
    ge_id: str = Field(description="SHA-256 hash of title + body")
    title: str = Field(
        description="Short, memorable name for this idea. 2-8 words.",
        min_length=3,
        max_length=100,
    )
    body: str = Field(
        description="The idea, insight, or speculation. Flexible format — "
                    "can be a paragraph, a quote, a set of bullet points. "
                    "2-30 sentences.",
        min_length=10,
    )
    source: str = Field(
        default="manual",
        description="Origin: 'manual' (user-created), 'pipeline' (extracted from books), "
                    "'import' (from external source)",
    )
    category: GE_CATEGORY = Field(  # type: ignore[valid-type]
        default="pipeline_speculative",
        description="What kind of idea this is. Determines how it's surfaced to the user."
    )
    actionable: bool = Field(
        default=False,
        description="Can this idea be acted on right now? If true, it appears in "
                    "the implementation queue. If false, it's for later investigation."
    )
    status: GE_STATUS = Field(  # type: ignore[valid-type]
        default="open",
        description="open → investigating → implementing → promoted | archived"
    )

    # ── Links to pipeline objects (if derived from extraction) ──
    parent_fb_ids: list[str] = Field(
        default_factory=list,
        description="FB IDs this GE relates to or was inspired by"
    )
    parent_pt_id: str | None = Field(
        default=None,
        description="PT ID this GE was derived from (if pipeline source)"
    )
    source_segment_id: str | None = Field(
        default=None,
        description="Segment ID if extracted from a book"
    )
    source_book: str = Field(
        default="",
        description="Book this insight came from (if pipeline source)"
    )

    # ── Promotion tracking ──
    promoted_to_type: str | None = Field(
        default=None,
        description="If promoted: 'FB', 'PT', 'Project'. The target object type."
    )
    promoted_to_id: str | None = Field(
        default=None,
        description="ID of the FB/PT/Project this was promoted to"
    )
    promoted_at: str | None = Field(
        default=None,
        description="ISO timestamp of promotion"
    )

    # ── Metadata ──
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags for filtering and discovery"
    )
    domain: str = Field(
        default="",
        description="Domain context for routing (may be empty for personal ideas)"
    )
    discipline: str = Field(
        default="",
        description="Discipline context (may be empty)"
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=5,
        description="User-assigned priority: 0 (uncategorized) to 5 (urgent)"
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
    jargon: str | None = Field(
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
    domains_raw: list[str] | None = Field(
        default=None,
        description="LLM's original domain labels before canonical validation. Preserved for taxonomy expansion."
    )
    discipline_raw: str | None = Field(
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
    source_principles: list[dict] = Field(
        default_factory=list,
        description="Source principles with texts embedded for fast Stage 5 verification. "
                    "Each: {principle_id, principle_text, source_segment_id}. "
                    "D2069: Eliminates 3-checkpoint lookup chain per FB."
    )
    s3_original_domain: str | None = Field(
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
    detail: str | None = Field(default=None, description="Explanation of result")


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
    verifier_model: str | None = Field(
        default=None, description="Model that performed verification"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Stage 6: Commit — SQLite row representation
# ═══════════════════════════════════════════════════════════════════════════

class FBRecord(VerifiedFB):
    """Canonical DB record — VerifiedFB + DB-specific fields."""
    rowid: int | None = Field(default=None, description="SQLite rowid")
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
    from pathlib import Path

    import yaml

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
    from pathlib import Path

    import yaml

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
        for _key, entry in syn_map.get("synonyms", {}).items():
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
