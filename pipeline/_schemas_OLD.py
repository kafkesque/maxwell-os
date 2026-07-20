#!/usr/bin/env python3
"""
schemas.py — Pydantic boundary contracts for the Maxwell OS knowledge pipeline.
(Guard V2 A2 — L1 deterministic floor)

Pipeline inter-stage models (Guard V2):
    Candidate          — S1 paragraph with embedding + provenance
    Cluster            — S1.5 FAISS cluster with member_indices + cohesion
    ConvergedPrinciple — S3a convergence output (principle + classification)
    FB                 — S5 generation output (6 body fields + classification)

Final output model (legacy, existing):
    FoundationBlock    — S6+ canonical FB with all 29 fields

Quality constraints built into validators:
    - Cluster: MAX_CLUSTER_SIZE ≤ 500, cohesion ≥ 0.85 (exempt cross-domain)
    - ConvergedPrinciple: distinct_sources ≥ 2 where applicable (BORP)
    - FB: definition, application, failure_mode, elaboration, keywords, jargon

Usage:
    from tools.schemas import Candidate, Cluster, ConvergedPrinciple, FB

    # Validate on read
    cluster = Cluster.model_validate_json(clusters_json)

    # Validate on write — raises ValidationError on violation
    principle = ConvergedPrinciple(principle="...", depth="universal", ...)
"""

from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Schema version (bump on every schema-affecting decision) ──────────────────
# D1030: Umbrella version — bumped when ANY stage schema changes.
# Used for backward-compat checks and as default for objects that pre-date
# the per-stage version system.
CURRENT_SCHEMA_VERSION = "2026-06-21.D597"

# ── Per-stage schema versions (D1030) ─────────────────────────────────────────
# Each stage tracks its own version independently. When a change affects only
# S3a (e.g., evidence prompt), ONLY the s3a version is bumped — S5/S6 FBs
# from the same run do NOT get a new version. This enables selective reruns:
# S6's --filter-stale can check stage_versions.s6 instead of a monolithic version.
STAGE_VERSIONS = {
    "s1_extract": "2026-06-21.D597",
    "s1p5_cluster": "2026-07-15.D1024",
    "s3a_converge": "2026-07-16.D1021",
    "s3c_verify": "2026-07-16.D1026",
    "s5_generate": "2026-06-21.D597",
    "s6_validate": "2026-07-16.D1026",
    "s7_export": "2026-07-16.D1025",
    "s8_push": "2026-06-21.D597",
}


# ── Enums ─────────────────────────────────────────────────────────────────────


class Evidence(str, Enum):
    cited = "cited"
    axiomatic = "axiomatic"


class Depth(str, Enum):
    universal = "universal"
    cross_domain = "cross-domain"
    domain = "domain"
    specialized = "specialized"


class AccessibilityType(str, Enum):
    self_evident = "self-evident"
    prerequisite = "prerequisite"


class IntimacyBoundary(str, Enum):
    public = "public"
    selective = "selective"
    private = "private"


# ── FoundationBlock ───────────────────────────────────────────────────────────


class FoundationBlock(BaseModel):
    """Complete FB schema. All 20 fields, typed and validated.

    Outlines guarantees every generated FB conforms to this schema —
    no regex parsing, no format failures, no field-level errors.
    """

    name: str = Field(description="Exact concept name — do not modify")
    discipline: str = Field(
        description="Canonical discipline label from 4-tier taxonomy (ACTIVE/STAGED/ROGUE/PROPOSED)"
    )
    evidence: Evidence
    depth: Depth
    definition: str = Field(
        description="3-4 sentence definition. S1: name+what. S2: mechanism. S3-4: constraint/consequence."
    )
    application: str = Field(
        description='Lines: "🔥 When [situation] → do [action]. Design/Business examples."'
    )
    failure_mode: str = Field(
        description='Must start lowercase: "the principle fails because [internal mechanism]". '
        "Never capitalize the FB name. Never use FB title as proper noun."
    )
    jargon: Optional[str] = Field(
        default=None,
        description="Specialized terminology explanation. Explain any term a general reader "
        "outside this domain would pause on. Never NULL if the domain has specialized language.",
    )
    accessibility: AccessibilityType = Field(
        description="self-evident: immediately graspable. prerequisite: requires prior concept."
    )
    context: Optional[str] = Field(
        default=None,
        description="Comma-separated multi-select: business, design, system, academic, personal. "
        "Or NULL. Never free text.",
    )
    domains: str = Field(
        description="Domain values from ACTIVE DOMAIN TABLE, comma-separated. "
        "STAGED domains must include [STAGED] flag."
    )
    source: str = Field(
        description='Format: "CONFIRMED BY [Author (Book Title)]" or author-map canonical'
    )
    related_blocks: Optional[str] = Field(
        default=None, description="Comma-separated related FB names, or blank"
    )
    embodiment_tag: Optional[str] = Field(
        default=None,
        description="Sensory anchor or concrete experience reference, or blank",
    )
    intimacy_boundary: IntimacyBoundary
    why_this_matters_to_me: Optional[str] = Field(
        default=None,
        description="Personal significance of this principle, or NULL",
    )
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score 0.0-1.0, or NULL"
    )
    version: str = Field(default="1.0", description="FB version")
    superseded_by: Optional[str] = Field(
        default=None, description="FB name that replaces this one, or NULL"
    )
    intent_tags: Optional[str] = Field(
        default=None, description="Comma-separated routing intent tags, or NULL"
    )
    prerequisites: Optional[str] = Field(
        default=None, description="Comma-separated prerequisite concept names, or NULL"
    )
    contradictions: Optional[str] = Field(
        default=None,
        description="Comma-separated concept names this contradicts, or NULL",
    )
    source_paragraph_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated paragraph IDs that support this definition, "
        "e.g. 'thinking_in_systems_p42,thinking_in_systems_p45'",
    )
    grounding_evidence: Optional[str] = Field(
        default=None, description="kb | web | source_text"
    )
    citations: Optional[str] = Field(
        default=None,
        description="Sentence-number format citations, or NULL if source paragraph unavailable",
    )
    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Schema version at generation time — bump on schema-affecting decisions",
    )
    gen_model: Optional[str] = Field(
        default=None,
        description="Model ID that generated this FB (e.g. gemma-4-26b-a4b-it-4bit)",
    )
    pipeline_commit: Optional[str] = Field(
        default=None,
        description="git commit hash at generation time (git rev-parse --short HEAD)",
    )
    # D34-R13: S6 verification metadata — optional confidence scores for self-calibration
    t2_confidence: Optional[int] = Field(
        default=None, ge=0, le=100,
        description="T2 semantic overlap confidence 0-100% (Phi-4 LLM)",
    )
    t3_confidence: Optional[int] = Field(
        default=None, ge=0, le=100,
        description="T3 decision-boundary confidence 0-100% (Phi-4 LLM)",
    )
    t30_confidence: Optional[int] = Field(
        default=None, ge=0, le=100,
        description="30s mechanical test score 0-100% (deterministic)",
    )
    t2_result: Optional[str] = Field(
        default=None, description="T2 semantic result: PASS/FAIL/FLAG/SKIPPED",
    )
    t3_result: Optional[str] = Field(
        default=None, description="T3 decision-boundary result: PASS/FAIL/FLAG/SKIPPED",
    )
    anchoring_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Key-claim anchoring score 0.0-1.0 (cosine similarity to source)",
    )
    s3_original_domain: Optional[str] = Field(
        default=None,
        description="Crawl provenance domain (e.g., domain_5_self_help) — immutable birth certificate",
    )
    domain_raw: Optional[str] = Field(
        default=None,
        description="Model's original domain classification label (preserved even when non-canonical)",
    )
    domain_canonical: Optional[str] = Field(
        default=None,
        description="Validated canonical taxonomy domain or 'emerging'",
    )

    def to_markdown(self) -> str:
        """Convert to canonical FB markdown format.

        Deterministic conversion — no template strings, no format drift.
        Every FB has identical structure regardless of which model generated it.
        """
        lines = [
            "**FB START**",
            f"**NAME:** {self.name}",
            f"**DISCIPLINE:** {self.discipline}",
            f"**EVIDENCE:** {self.evidence.value}",
            f"**DEPTH:** {self.depth.value}",
            f"**RELATED BLOCKS:** {self.related_blocks or ''}",
            f"**DEFINITION:** {self.definition}",
            f"**APPLICATION:** {self.application}",
            f"**FAILURE MODE:** {self.failure_mode}",
            f"**JARGON:** {self.jargon or ''}",
            f"**ACCESSIBILITY:** {self.accessibility.value}",
            f"**CONTEXT:** {self.context or 'NULL'}",
            f"**DOMAINS:** {self.domains}",
            f"**SOURCE:** {self.source}",
            f"**EMBODIMENT_TAG:** {self.embodiment_tag or ''}",
            f"**INTIMACY_BOUNDARY:** {self.intimacy_boundary.value}",
            f"**WHY_THIS_MATTERS_TO_ME:** {self.why_this_matters_to_me or 'NULL'}",
            f"**CONFIDENCE:** {_fmt_confidence(self.confidence)}",
            f"**VERSION:** {self.version}",
            f"**SUPERSEDED_BY:** {self.superseded_by or 'NULL'}",
            f"**INTENT_TAGS:** {self.intent_tags or 'NULL'}",
            f"**PREREQUISITES:** {self.prerequisites or 'NULL'}",
            f"**CONTRADICTIONS:** {self.contradictions or 'NULL'}",
            f"**SOURCE_PARAGRAPH_IDS:** {self.source_paragraph_ids or ''}",
            f"**GROUNDING_EVIDENCE:** {self.grounding_evidence or ''}",
            f"**CITATIONS:** {self.citations or ''}",
            f"**SCHEMA_VERSION:** {self.schema_version}",
            f"**GEN_MODEL:** {self.gen_model or ''}",
            f"**PIPELINE_COMMIT:** {self.pipeline_commit or ''}",
            "---FB END---",
        ]
        return "\n".join(lines)


def _fmt_confidence(val: Optional[float]) -> str:
    """Format confidence as string — keeps NULL semantics."""
    if val is None:
        return "NULL"
    return f"{val:.1f}"


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Inter-Stage Boundary Contracts (Guard V2 A2)
# These are the L1 deterministic floor — validation at every read/write boundary.
# Violation raises pydantic.ValidationError → pipeline halts.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Contract constants (sourced from constitution III.A, IV.A) ──
MAX_CLUSTER_SIZE = 500
COHESION_FLOOR = 0.85
MIN_DISTINCT_SOURCES = 2


# ── Pipeline enums ──


class Route(str, Enum):
    FB = "FB"
    PT = "PT"
    GROWTH_EDGE = "GROWTH EDGE"
    NULL = "NULL"
    SINGLETON = "SINGLETON"


class Tier(str, Enum):
    tier1 = "tier1"  # cross-domain: universal + cross-domain only
    tier2 = "tier2"  # per-domain: domain + specialized only


# ── Run ID generation (D1030: unique per pipeline execution) ──


def generate_run_id(domain: str = "", stage: str = "") -> str:
    """Generate a unique run identifier for this pipeline execution.

    Format: YYYYMMDD_HHMM_{domain}_{stage}_{uuid8}
    Deterministic enough for traceability, unique enough for isolation.

    Usage:
        run_id = generate_run_id("domain_0_framework", "s3a")
        # → "20260716_1050_domain_0_framework_s3a_a1b2c3d4"
    """
    import uuid
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    domain_slug = domain.replace(" ", "_").replace("/", "_")[:30] if domain else "all"
    stage_slug = stage[:20] if stage else "full"
    short_uuid = uuid.uuid4().hex[:8]
    return f"{ts}_{domain_slug}_{stage_slug}_{short_uuid}"


# ── Pipeline stamp mixin (R6+R14: every persistent object is stamped) ──


class PipelineStamp(BaseModel):
    """Provenance + version stamp required on all pipeline output.

    D1030: Added run_id (isolates batches across executions)
           and stage_version (per-stage schema tracking, enables selective reruns).
    """

    schema_version: str = Field(default=CURRENT_SCHEMA_VERSION)
    gen_model: Optional[str] = Field(default=None)
    pipeline_commit: Optional[str] = Field(default=None)
    run_id: Optional[str] = Field(
        default=None,
        description="Unique pipeline execution ID for batch isolation (D1030)",
    )
    stage_version: Optional[str] = Field(
        default=None,
        description="Per-stage schema version at generation time (D1030). "
        "Enables selective --filter-stale by stage.",
    )


# ── Candidate (S1 paragraph) ──


class Candidate(BaseModel):
    """An S1 extracted paragraph candidate with embedding."""

    model_config = {"extra": "allow"}  # v2 stores additional metadata

    text: str = Field(description="The paragraph text")
    embedding: list[float] = Field(description="768-dim nomic embedding")
    source_path: Optional[str] = Field(
        default=None, description="Source book file path"
    )
    para_idx: Optional[int] = Field(
        default=None, description="Paragraph index within source"
    )
    source_hash: Optional[str] = Field(
        default=None, description="Content hash for cache invalidation"
    )
    epoch_id: Optional[str] = Field(
        default=None, description="Extraction epoch identifier"
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Candidate text must not be empty")
        return v


# ── Cluster (S1.5 FAISS cluster) ──


class Cluster(BaseModel):
    """S1.5 FAISS cluster with member indices and coherence metrics."""

    model_config = {"extra": "allow"}

    member_indices: list[int] = Field(
        description="Array indices into candidate list", min_length=1
    )
    cohesion: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean pairwise cosine similarity within cluster",
    )
    size: Optional[int] = Field(
        default=None, description="Number of members (derived from member_indices)"
    )
    discipline: Optional[str] = Field(
        default=None,
        description="Optional for cross-domain; required for per-domain clusters",
    )
    distinct_sources: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of distinct source books in the cluster",
    )
    threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Threshold used to form this cluster"
    )
    domain_track: Optional[list[str]] = Field(
        default=None,
        description="Domain origin per member (cross-domain only)",
    )

    @model_validator(mode="after")
    def check_coherence(self):
        """Enforce D506 coherence contract: size ≤ 500, cohesion ≥ 0.85.

        Cross-domain clusters are exempt from the 0.85 floor
        (accepted cohesion ~0.69 per D507).
        """
        size = self.size or len(self.member_indices)

        # Size cap — universal
        if size > MAX_CLUSTER_SIZE:
            raise ValueError(
                f"Cluster size {size} exceeds max {MAX_CLUSTER_SIZE} "
                f"(D506 coherence contract)"
            )

        # Cohesion floor — exempt cross-domain
        if self.cohesion is not None and self.cohesion < COHESION_FLOOR:
            # Check if this is a cross-domain cluster (discipline is None or 'cross-domain')
            if self.discipline is None or self.discipline == "cross-domain":
                # Cross-domain: cohesion ~0.69 is accepted (D507)
                pass
            elif size > 100:
                # Blob signature: large + low cohesion → BLOCKING
                raise ValueError(
                    f"Blob signature: size={size} > 100, cohesion={self.cohesion:.4f} "
                    f"< {COHESION_FLOOR} (D506 coherence contract)"
                )

        # Distinct sources (BORP — warn, not block at cluster level)
        if self.distinct_sources is not None and self.distinct_sources < 2:
            # Single-source clusters → route to singleton ledger (D396)
            if self.distinct_sources == 1:
                raise ValueError(
                    f"Single-source cluster ({self.distinct_sources} distinct source). "
                    f"Route to singleton ledger (D396 + D403)."
                )

        return self


# ── ConvergedPrinciple (S3a convergence output) ──


class ConvergedPrinciple(PipelineStamp):
    """S3a convergence output — one principle extracted per cluster."""

    model_config = {"extra": "allow"}

    principle: str = Field(description="The extracted principle text")
    depth: Depth = Field(
        description="Tier-appropriate depth: tier1→universal|cross-domain, tier2→domain|specialized"
    )
    discipline: Optional[str] = Field(
        default=None,
        description="Canonical discipline label or 'emerging [PROPOSED]'",
    )
    domain: Optional[str] = Field(
        default=None, description="Domain value (free text from S3a — D270)"
    )
    evidence: Evidence = Field(description="cited or axiomatic")
    route: Route = Field(
        description="Routing decision: FB|PT|GROWTH EDGE|NULL|SINGLETON"
    )
    cluster_id: Optional[str] = Field(default=None, description="Source cluster ID")
    distinct_sources: Optional[int] = Field(
        default=None,
        ge=2,
        description="Number of distinct source books (≥2 for FB route, D396)",
    )
    sources: Optional[list[str]] = Field(
        default=None, description="Source file paths (for traceability)"
    )
    member_indices: Optional[list[int]] = Field(
        default=None, description="Indices into candidate list (for traceability)"
    )
    cohesion: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Cluster cohesion (for adaptive sampling)",
    )

    @model_validator(mode="after")
    def check_borp(self):
        """BORP ground truth: FB-route principles must have ≥2 distinct sources.

        Warns (does not block) because S3a is classification, not generation.
        Blocking occurs at S5/S6 generation boundary (IV.A).
        """
        if self.route == Route.FB and self.distinct_sources is not None:
            if self.distinct_sources < MIN_DISTINCT_SOURCES:
                raise ValueError(
                    f"FB-route principle has {self.distinct_sources} distinct sources "
                    f"(< {MIN_DISTINCT_SOURCES}). Route to singleton ledger (D396)."
                )
        return self

    @field_validator("principle")
    @classmethod
    def principle_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Principle text must not be empty")
        return v


# ── FB (S5 generation output — 6 body fields + classification) ──


class FB(PipelineStamp):
    """S5 generation output — 6 body fields + mechanically-merged classification.

    Classification fields (depth, discipline, domain, evidence, source) are
    merged mechanically from S3a bridge input (D370/N2), not generated by LLM.
    PRINCIPLE field is the principle text from S3a convergence.
    """

    model_config = {"extra": "allow"}

    # ── 6 body fields generated by LLM (D285) ──
    definition: str = Field(
        description="3-4 sentences. S1=what, S2=mechanism, S3-4=constraint."
    )
    application: str = Field(
        description="When (situation) → (action). One concrete example."
    )
    failure_mode: str = Field(
        description="The principle fails because (specific failure scenario). 1-3 sentences."
    )
    elaboration: str = Field(
        description="3-5 sentences. Deeper explanation with edge cases and nuance."
    )
    keywords: str = Field(description="3-5 key terms, comma-separated.")
    jargon: Optional[str] = Field(
        default=None,
        description="Explain specialized terminology. NULL only if zero specialized language.",
    )

    # ── Classification fields (mechanically merged from S3a bridge input) ──
    principle: str = Field(
        description="The S3a-converged principle text (PRINCIPLE field for S6 L2d grounding)"
    )
    depth: Depth = Field(description="From S3a convergence")
    discipline: Optional[str] = Field(default=None, description="From S3a convergence")
    domain: Optional[str] = Field(default=None, description="From S3a convergence")
    evidence: Evidence = Field(description="From S3a convergence")
    source: Optional[str] = Field(default=None, description="From S3a convergence")

    # ── Optional: provenance chain fields ──
    source_path: Optional[str] = Field(
        default=None, description="Source book path (for traceability)"
    )
    para_idx: Optional[int] = Field(
        default=None, description="Paragraph index (for traceability)"
    )
    grounding_count: Optional[int] = Field(
        default=None, description="Number of grounding paragraphs"
    )

    @field_validator("definition", "application", "failure_mode", "elaboration")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("FB body field must not be empty")
        return v


# ── Convenience: domain whitelist loader ──


def load_domain_disciplines() -> dict[str, list[str]]:
    """Load per-domain discipline whitelist from config/domain_disciplines.yaml.

    Returns {domain_key: [discipline_names...]}. Falls back to empty dict.
    """
    try:
        import yaml

        config_path = (
            Path(__file__).resolve().parent.parent
            / "config"
            / "domain_disciplines.yaml"
        )
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# Inter-Stage Contract Validation (D1030 — P0.3)
# Fail-closed: refuse to process input that doesn't match expected schema.
# ═══════════════════════════════════════════════════════════════════════════════

from collections.abc import Sequence

# Required fields for each stage's INPUT (what the downstream stage expects)
STAGE_INPUT_CONTRACTS = {
    "s5": {  # S5 expects these keys in every .s5_input.json item
        "required": ["principle", "source_path"],
        "optional": [
            "depth", "discipline", "domain", "evidence", "route",
            "source_paragraph_ids", "grounding_count", "total_paragraphs",
            "s3_original_domain", "domain_raw", "domain_canonical",
            "domain_canonical_multi", "discipline_canonical", "discipline_raw",
            "text", "run_id", "stage_version",
            "cluster_id", "distinct_sources", "sources", "cohesion",
            # D1058: bridge-classified fields — deterministic, no LLM
            "_classified_evidence", "_classified_context",
            "_classified_intimacy", "_classified_accessibility",
        ],
        # No Pydantic model check at this boundary — S5 input is bridge data,
        # which may have partial fields. Schema validation happens at S3a output.
    },
    "s6": {  # S6 expects these keys in every parsed FB
        "required": ["DEFINITION", "DEPTH", "EVIDENCE"],
        "optional": [
            "NAME", "DISCIPLINE", "DOMAINS", "DOMAIN", "APPLICATION",
            "FAILURE MODE", "ELABORATION", "KEYWORDS", "JARGON",
            "SOURCE", "SCHEMA_VERSION", "GEN_MODEL", "PIPELINE_COMMIT",
            "STAGE_VERSION", "RUN_ID", "CONFIDENCE", "STATUS",
            "RELATED BLOCKS", "SOURCE_PARAGRAPH_IDS",
        ],
    },
    "s3a": {  # S3a expects these keys in each cluster
        "required": ["member_indices"],
        "optional": [
            "cohesion", "size", "discipline", "distinct_sources",
            "domain_track", "threshold",
        ],
    },
}


class ContractViolation(Exception):
    """Raised when stage input doesn't match expected contract (D1030)."""
    pass


def validate_stage_input(
    data: Sequence[dict],
    stage: str,
    strict: bool = False,
) -> tuple[int, int, list[str]]:
    """Validate input data against the stage's expected contract.

    Args:
        data: List of dict items (principles, clusters, FBs)
        stage: Stage name ("s3a", "s5", "s6")
        strict: If True, raise ContractViolation on first mismatch

    Returns:
        (total_items, violations, violation_details)

    Raises:
        ContractViolation: If strict=True and validation fails

    Usage:
        from tools.schemas import validate_stage_input, ContractViolation
        violations, _, details = validate_stage_input(principles, "s5", strict=True)
    """
    contract = STAGE_INPUT_CONTRACTS.get(stage)
    if contract is None:
        # Unknown stage — skip validation (not a contract we've defined yet)
        return len(data), 0, []

    required = set(contract["required"])
    allowed = required | set(contract.get("optional", []))

    violations = 0
    details = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            violations += 1
            msg = f"[{stage}] item {i}: not a dict (got {type(item).__name__})"
            details.append(msg)
            if strict:
                raise ContractViolation(msg)
            continue

        item_keys = set(item.keys())

        # ── Check required fields ──
        missing = required - item_keys
        if missing:
            violations += 1
            msg = f"[{stage}] item {i}: missing required fields: {sorted(missing)}"
            details.append(msg)
            if strict:
                raise ContractViolation(msg)

        # ── Check unknown fields (warn, don't block) ──
        unknown = item_keys - allowed
        if unknown and len(unknown) > 3:  # tolerate ≤3 unknown fields (extra_allow)
            violations += 1
            msg = f"[{stage}] item {i}: {len(unknown)} unknown fields: {sorted(list(unknown))[:5]}..."
            details.append(msg)
            if strict:
                raise ContractViolation(msg)

        # ── Full Pydantic validation if model is specified ──
        model_name = contract.get("model")
        if model_name:
            try:
                model_cls = globals().get(model_name)
                if model_cls:
                    model_cls.model_validate(item)
            except Exception as e:
                violations += 1
                msg = f"[{stage}] item {i}: {model_name} validation failed: {str(e)[:120]}"
                details.append(msg)
                if strict:
                    raise ContractViolation(msg)

    return len(data), violations, details


def validate_stage_input_or_halt(
    data: Sequence[dict],
    stage: str,
    label: str = "",
) -> None:
    """Validate and HALT on any violation (fail-closed).

    Prints summary and exits with code 1 on any mismatch.
    """
    total, violations, details = validate_stage_input(data, stage, strict=False)
    domain_label = f" ({label})" if label else ""

    if violations == 0:
        print(f"   ✅ CONTRACT [{stage}]{domain_label}: {total} items pass input validation")
        return

    print(f"\n{'='*60}")
    print(f"🛑 CONTRACT VIOLATION [{stage}]{domain_label}")
    print(f"   {violations}/{total} items failed input validation")
    print(f"{'='*60}")
    for detail in details[:15]:
        print(f"   {detail}")
    if len(details) > 15:
        print(f"   ... and {len(details)-15} more violations")
    print(f"\n   Fix the input data or update STAGE_INPUT_CONTRACTS in tools/schemas.py")
    print(f"   This is a FAIL-CLOSED gate (D1030). Pipeline halts.")
    import sys
    sys.exit(1)
