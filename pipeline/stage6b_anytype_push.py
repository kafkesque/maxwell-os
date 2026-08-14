#!/usr/bin/env python3
"""
stage6b_anytype_push.py — Push verified FBs to Anytype with domain subfolders.
================================================================================
Authority: D2135, D2122 | CONSTITUTION.md §3 (Stage 6b — Anytype Knowledge Graph)

Adapted from v1 tools/anytype_write.py (B169, B202, B188, PushLedger).

Input:  Verified FBs from Stage 5 checkpoint (or Stage 6 SQLite)
Output: Anytype objects organized by raw domain subfolders + PushLedger

D2122: Complete payload alignment — all 42 FB fields included.
D2123: Jargon in body only, Citation in Author (Book Title) format.
D2072: PT/PI/GE/TI exported to separate subfolders.

Domain subfolder convention (from v1):
  stage6_commit/anytype_push/{run_id}/
    {raw_domain}/
      {fb_slug}.json           ← full push-ready FB payload (all fields)
      {fb_slug}.md             ← human-readable 3-zone body markdown
    pt/                        ← process templates (D2072)
    pi/                        ← process instances (D2072)
    ge/                        ← growth edges (D2073)
    ti/                        ← tool instructions (D2072)
    domain_index.json           ← domain → FB mapping
    push_ledger.jsonl           ← checkpoint/resume ledger

Usage:
    python3 pipeline/stage6b_anytype_push.py                    # Full push
    python3 pipeline/stage6b_anytype_push.py --dry-run           # Prepare only, no push
    python3 pipeline/stage6b_anytype_push.py --resume            # Resume from ledger
    python3 pipeline/stage6b_anytype_push.py --domain business   # Single domain
    python3 pipeline/stage6b_anytype_push.py --export-only       # Export to .md only
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    S4_GE_OUTPUT,
    S4_PI_OUTPUT,
    S4_PT_OUTPUT,
    S4_TI_OUTPUT,
    S6_DIR,
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    get_run_id,
)
from pipeline.intimacy_lattice import route_space  # W6: private/non-private space routing for MCP push
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
RUN_ID: str = get_run_id()
PUSH_DIR: Path = S6_DIR / RUN_ID / "anytype_push"
LEDGER_PATH: Path = PUSH_DIR / "push_ledger.jsonl"

# D2123: Body-only fields (never in YAML frontmatter, render in body section)
BODY_ONLY_FIELDS: frozenset[str] = frozenset({
    "definition", "application", "failure_mode", "elaboration",
    "keywords", "jargon", "source_text",
    "mechanism", "boundary", "consequence",
})

# D2122: All FB fields included in payload
ALL_FIELDS: list[str] = [
    "fb_id", "name", "fb_version",
    "definition", "application", "failure_mode", "elaboration", "keywords",
    "mechanism", "boundary", "consequence", "is_summary", "evidence_passages",
    "discipline", "discipline_raw", "domains", "domains_raw",
    "depth", "evidence", "is_specialized",
    "source_author", "source_title", "citation",
    "source_books", "source_clusters", "source_paragraph_ids",
    "source_authors", "primary_source",
    "source_principle_ids", "source_text", "grounding_evidence",
    "confidence", "borp_score", "classification_errors",
    "context", "accessibility", "intimacy_boundary", "provenance",
    "difficulty_level", "temporal_scope", "prerequisite_fbs",
    "procedural_skill", "related_fbs", "embodiment_tag",
    "schema_version", "taxonomy_version", "gen_model",
    "pipeline_commit", "pipeline_run_id", "created_at",
    "jargon",  # body-only, included in body rendering
]


def _slugify(name: str) -> str:
    """Convert FB name to filesystem-safe slug matching v1 convention."""
    slug = name.lower().strip()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = slug.replace(" ", "_").replace("-", "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")[:80]


def _raw_domain(canonical_domain: str) -> str:
    """Convert canonical domain to filesystem-safe raw domain label."""
    raw = canonical_domain.lower().strip()
    raw = raw.replace(" & ", "_").replace("&", "_")
    raw = raw.replace(" + ", "_").replace("+", "_")
    raw = raw.replace(" — ", "_").replace("—", "_")
    raw = raw.replace(" / ", "_").replace("/", "_")
    raw = raw.replace(" ", "_")
    raw = "".join(c for c in raw if c.isalnum() or c == "_")
    while "__" in raw:
        raw = raw.replace("__", "_")
    return raw.strip("_")


def _render_jargon_md(jargon_val: Any) -> str:
    """Render jargon dict/string as markdown bullet list."""
    if jargon_val is None:
        return ""
    if isinstance(jargon_val, str):
        if not jargon_val.strip() or jargon_val.strip() in ("{}", "null", "None", ""):
            return ""
        items = jargon_val.split("; ")
    elif isinstance(jargon_val, dict):
        items = [f"{k}: {v}" for k, v in jargon_val.items() if v]
    else:
        return ""

    if not items:
        return ""

    lines = ["", "## Jargon", ""]
    for item in items:
        if ": " in item:
            term, definition = item.split(": ", 1)
            lines.append(f"- **{term.strip()}**: {definition.strip()}")
        else:
            lines.append(f"- {item.strip()}")
    return "\n".join(lines)


def _render_3zone_body(fb: dict) -> str:
    """Render FB as 3-zone body — locked template (RULE 2 / D353 / D2015).

    ZONE 1 - RELATIONS: metadata header (status, discipline, evidence, source)
    ZONE 2 - BODY: DEFINITION 🏛️ → MECHANISM → APPLICATION 🔥 → FAILURE MODE ⚠️ → BOUNDARY → JARGON 🤓
    ZONE 3 - STABLE GATE: EVIDENCE + source footer + reliability stats (dynamic)
    """
    name = fb.get("name", "Untitled")
    definition = fb.get("definition", "")
    mechanism = fb.get("mechanism", "")
    application = fb.get("application", "")
    failure_mode = fb.get("failure_mode", "")
    boundary = fb.get("boundary", "")
    elaboration = fb.get("elaboration", "")
    consequence = fb.get("consequence", "")
    citation = fb.get("citation", "")
    keywords = fb.get("keywords", "")
    jargon_val = fb.get("jargon")
    evidence_type = fb.get("evidence", "cited")
    source_books = fb.get("source_books", [])
    if isinstance(source_books, str):
        try:
            import json
            source_books = json.loads(source_books)
        except Exception:
            source_books = [source_books]
    evidence_passages = fb.get("evidence_passages", [])

    # ── STABLE GATE stats (from feedback / reliability) ──
    fb_id = fb.get("fb_id", "")
    try:
        from pipeline.feedback import get_fb_feedback_stats
        fbs = get_fb_feedback_stats(fb_id) if fb_id else {}
    except Exception:
        fbs = {}
    reliability = fbs.get("avg_rating")
    reliability_count = fbs.get("count", 0)
    usage_count = fb.get("usage_count", 0)

    parts: list[str] = []

    import re  # for body newline cleanup

    # ── ZONE 1 - RELATIONS ── (RULE 2: metadata header)
    zone1_lines = ["---", "ZONE 1 - RELATIONS", ""]
    if evidence_type:
        zone1_lines.append(f"evidence: {evidence_type}")
    if source_books:
        n_books = len(source_books) if isinstance(source_books, list) else 1
        zone1_lines.append(f"sources: {n_books} book{'s' if n_books != 1 else ''}")
    zone1_lines.append("---")
    parts.append("\n".join(zone1_lines))

    # ── ZONE 2 - BODY ── (RULE 2: immutable knowledge)
    zone2_lines = ["---", "ZONE 2 - BODY", ""]

    if definition:
        zone2_lines.append("### DEFINITION")
        zone2_lines.append(f"> \U0001f3db\ufe0f {definition}")
        zone2_lines.append("")

    if mechanism:
        zone2_lines.append("---")
        zone2_lines.append("### MECHANISM")
        zone2_lines.append(f"> 🏛️ {mechanism}")
        zone2_lines.append("")

    if application:
        application = application.lstrip("🔥").lstrip("🏛️").strip()
        zone2_lines.append("---")
        zone2_lines.append("### APPLICATION")
        zone2_lines.append(f"> 🔥 {application}")
        zone2_lines.append("")

    # ── FAILURE MODE + BOUNDARY (as pair, dedup on redundancy)
    if failure_mode or boundary:
        zone2_lines.append("---")
        if failure_mode and boundary:
            zone2_lines.append("### FAILURE MODE")
            zone2_lines.append(f"> ⚠️ {failure_mode}")
            zone2_lines.append(f"> \n> **Applies when:** {boundary}" if boundary else "")
            zone2_lines.append("")
        elif failure_mode:
            zone2_lines.append("### FAILURE MODE")
            zone2_lines.append(f"> ⚠️ {failure_mode}")
            zone2_lines.append("")
        elif boundary:
            zone2_lines.append("### BOUNDARY")
            zone2_lines.append(f"> ⚠️ {boundary}")
            zone2_lines.append("")

    if jargon_val:
        jarg_str = _render_jargon_md(jargon_val)
        if jarg_str:
            zone2_lines.append("---")
            zone2_lines.append("### JARGON")
            if isinstance(jargon_val, str) and jargon_val.strip():
                zone2_lines.append(f"> 🤓 {jargon_val}")
            elif isinstance(jargon_val, dict) and jargon_val:
                for k, v in jargon_val.items():
                    if v:
                        zone2_lines.append(f"> 🤓 **{k}**: {v}")
            zone2_lines.append("")

    parts.append("\n".join(zone2_lines))

    # ── ZONE 3 - STABLE GATE ── (RULE 2 + D2015 dynamic stats)
    zone3_lines = ["---", "ZONE 3 - STABLE GATE", ""]
    zone3_lines.append("### EVIDENCE")

    # Build stable-if line
    stable_parts = [f"Stable if: {evidence_type}"]
    if reliability is not None and reliability_count >= 3:
        stable_parts.append(f"reliability: {reliability:.2f} ({reliability_count} ratings)")
    elif usage_count > 0:
        stable_parts.append(f"retrieved: {usage_count}×")
    zone3_lines.append(f"> ✅ {' · '.join(stable_parts)}")

    # Compact evidence passages (1 per source, ≤2 sentences each)
    if evidence_passages and isinstance(evidence_passages, list):
        zone3_lines.append("")
        for i, passage in enumerate(evidence_passages[:3]):
            if isinstance(passage, str):
                short = passage[:200]
                if len(passage) > 200:
                    short += "…"
                zone3_lines.append(f"> 📄 {short}")
        zone3_lines.append("")

    # Consequence (compact, 1 line)
    if consequence:
        zone3_lines.append(f"\n**CONSEQUENCE**: {consequence[:200]}")
        zone3_lines.append("")

    if elaboration:
        short_elab = elaboration[:300]
        if len(elaboration) > 300:
            short_elab += "…"
        zone3_lines.append(f"\n**ELABORATION**: {short_elab}")
        zone3_lines.append("")

    if keywords:
        if isinstance(keywords, list):
            kw_str = ", ".join(keywords)
        else:
            kw_str = str(keywords)
        zone3_lines.append(f"\n**KEYWORDS**: {kw_str}")
        zone3_lines.append("")

    if citation:
        zone3_lines.append(f"source: {citation}")
        zone3_lines.append("")

    # Stamps
    schema_ver = fb.get("schema_version", "")
    gen_model = fb.get("gen_model", "")
    pipeline_commit = fb.get("pipeline_commit", "")
    if schema_ver:
        zone3_lines.append(f"schema_version: {schema_ver}")

    parts.append("\n".join(zone3_lines))

    body = "\n".join(parts)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body


def _render_3zone_body_old_end(fb):  # replaced above
    pass





def _format_fb_markdown(fb: dict) -> str:
    """Format an FB as human-readable markdown with YAML frontmatter.

    D2123: Body-only fields (definition, application, failure_mode,
    elaboration, keywords, jargon) are in the body section, NOT YAML.
    """
    name = fb.get("name", "Untitled")
    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except (json.JSONDecodeError, TypeError):
            domains = [domains]
    source_books = fb.get("source_books", [])
    if isinstance(source_books, str):
        source_books = [source_books]

    # ── YAML frontmatter (metadata only — D2123: no body fields) ──
    yaml_fields = {
        "fb_id": fb.get("fb_id", ""),
        "discipline": fb.get("discipline", ""),
        "domains": domains,
        "depth": fb.get("depth", ""),
        "evidence": fb.get("evidence", ""),
        "source_books": source_books,
        "citation": fb.get("citation", ""),
        "context": fb.get("context", ""),
        "difficulty_level": fb.get("difficulty_level", ""),
        "temporal_scope": fb.get("temporal_scope", ""),
        "accessibility": fb.get("accessibility", ""),
        "confidence": fb.get("confidence", ""),
        "borp_score": fb.get("borp_score", ""),
        "schema_version": fb.get("schema_version", ""),
        "taxonomy_version": fb.get("taxonomy_version", ""),
    }

    lines = ["---"]
    for k, v in yaml_fields.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v)}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")

    # ── Body section ──
    lines.append(f"# {name}")
    lines.append("")

    citation = fb.get("citation", "")
    if citation:
        lines.append(f"> **Source:** {citation}")
        lines.append("")

    # ZONE 1: Definition
    lines.append("## Definition")
    lines.append("")
    lines.append(fb.get("definition", ""))

    # ZONE 2: Mechanism + Application + Failure Mode + Boundary
    if fb.get("mechanism"):
        lines.extend(["", "## Mechanism", "", fb["mechanism"]])
    if fb.get("application"):
        lines.extend(["", "## Application", "", fb["application"]])
    if fb.get("failure_mode"):
        lines.extend(["", "## Failure Mode", "", fb["failure_mode"]])
    if fb.get("boundary"):
        lines.extend(["", "## Boundary", "", fb["boundary"]])

    # ZONE 3: Elaboration + Keywords + Jargon
    if fb.get("elaboration"):
        lines.extend(["", "## Elaboration", "", fb["elaboration"]])
    if fb.get("consequence"):
        lines.extend(["", "## Consequence", "", fb["consequence"]])
    if fb.get("keywords"):
        lines.extend(["", "## Keywords", "", fb["keywords"]])

    jargon_str = _render_jargon_md(fb.get("jargon"))
    if jargon_str:
        lines.append(jargon_str)

    # Related blocks
    related = fb.get("related_fbs")
    if related and isinstance(related, list) and len(related) > 0:
        lines.extend(["", "## Related", ""])
        for rel in related[:10]:
            if isinstance(rel, dict):
                rid = rel.get("fb_id", "")
                rrels = rel.get("relationships", [])
                lines.append(f"- `{rid[:20]}` ({', '.join(rrels)})")

    return "\n".join(lines)


def _format_fb_payload(fb: dict) -> dict:
    """Format an FB as a complete Anytype-ready JSON payload.

    D2122: Includes ALL 42+ fields. 3-zone body rendering.
    D2123: Jargon in body only, not as separate metadata.
    """
    name = fb.get("name", "Untitled")
    domains = fb.get("domains", [])
    if isinstance(domains, str):
        try:
            domains = json.loads(domains)
        except (json.JSONDecodeError, TypeError):
            domains = [domains]
    source_books = fb.get("source_books", [])
    if isinstance(source_books, str):
        source_books = [source_books]

    body = _render_3zone_body(fb)

    return {
        # ── Identity ──
        "name": name,
        "fb_id": fb.get("fb_id", ""),
        "fb_version": fb.get("fb_version", 1),
        # ── 3-Zone Body (D2122) ──
        "body": body,
        # ── Classification ──
        "discipline": fb.get("discipline", ""),
        "discipline_raw": fb.get("discipline_raw"),
        "domains": domains,
        "domains_raw": fb.get("domains_raw", []),
        "depth": fb.get("depth", ""),
        "evidence": fb.get("evidence", ""),
        "is_specialized": fb.get("is_specialized", False),
        # ── Citation (D2123: Author (Book Title) format) ──
        "source_author": fb.get("source_author"),
        "source_title": fb.get("source_title"),
        "citation": fb.get("citation", ""),
        "source_books": source_books,
        "source_authors": fb.get("source_authors", []),
        "primary_source": fb.get("primary_source"),
        "is_summary": fb.get("is_summary", False),
        "mechanism": fb.get("mechanism", ""),
        "boundary": fb.get("boundary", ""),
        "consequence": fb.get("consequence", ""),
        "evidence_passages": fb.get("evidence_passages", []),
        "source_clusters": fb.get("source_clusters", []),
        "source_paragraph_ids": fb.get("source_paragraph_ids", ""),
        "source_principle_ids": fb.get("source_principle_ids", []),
        "grounding_evidence": fb.get("grounding_evidence", ""),
        # ── Verification ──
        "confidence": fb.get("confidence"),
        "borp_score": fb.get("borp_score"),
        "classification_errors": fb.get("classification_errors"),
        # ── v1 Anytype properties ──
        "context": fb.get("context", "general"),
        "accessibility": fb.get("accessibility", "self-evident"),
        "intimacy_boundary": fb.get("intimacy_boundary", "public"),
        "space": route_space(fb),  # W6: "private" | "non_private" — resolved from intimacy lattice
        "provenance": fb.get("provenance", "llm_extracted_from_source"),
        # ── Agentic metadata ──
        "difficulty_level": fb.get("difficulty_level", "intermediate"),
        "temporal_scope": fb.get("temporal_scope", "timeless"),
        "prerequisite_fbs": fb.get("prerequisite_fbs", []),
        "procedural_skill": fb.get("procedural_skill"),
        "related_fbs": fb.get("related_fbs", []),
        "embodiment_tag": fb.get("embodiment_tag"),
        # ── Stamps ──
        "usage_count": fb.get("usage_count", 0),
        "feedback_score": fb.get("feedback_score"),
        # ── Stamps ──
        "schema_version": fb.get("schema_version", ""),
        "taxonomy_version": fb.get("taxonomy_version", ""),
        "gen_model": fb.get("gen_model", ""),
        "pipeline_commit": fb.get("pipeline_commit", ""),
        "pipeline_run_id": fb.get("pipeline_run_id", ""),
        "created_at": fb.get("created_at", ""),
    }


# ── Push Ledger (D386: Write Path Hardening, adapted from v1) ───────────


class PushLedger:
    """Journals every FB push attempt to push_ledger.jsonl.

    Each line: {"fb_slug": "...", "domain": "...", "status": "attempted|confirmed|failed",
                 "anytype_oid": "...", "timestamp": "..."}

    Before pushing, call confirmed_slugs() to skip already-confirmed FBs.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path: Path = path or LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        """Read all ledger entries."""
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def confirmed_slugs(self) -> set[str]:
        """Return set of FB slugs with 'confirmed' status."""
        return {e["fb_slug"] for e in self._load() if e.get("status") == "confirmed"}

    def record(self, fb_slug: str, domain: str, status: str,
               anytype_oid: str = "", **extra: Any) -> None:
        """Record a push attempt in the ledger."""
        entry: dict[str, Any] = {
            "fb_slug": fb_slug,
            "domain": domain,
            "status": status,
            "anytype_oid": anytype_oid,
            "timestamp": datetime.now(UTC).isoformat(),
            **extra,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())


# ── Main ───────────────────────────────────────────────────────────────────


def load_verified_fbs() -> list[dict]:
    """Load verified FBs from Stage 5 checkpoint."""
    if not STAGE5_CHECKPOINT.exists():
        print("❌ Stage 5 checkpoint not found. Run stage5_verify.py first.")
        sys.exit(1)

    fbs: list[dict] = []
    with open(STAGE5_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                fbs.append(json.loads(line))
    return fbs


def load_non_fb_content() -> dict[str, list[dict]]:
    """Load PT/PI/GE/TI from Stage 4 output files (D2072, D2122).

    Returns dict with keys: pt, pi, ge, ti — each a list of records.
    """
    result: dict[str, list[dict]] = {"pt": [], "pi": [], "ge": [], "ti": []}
    stage4_dir = STAGE4_CHECKPOINT.parent

    mapping = [
        ("pt", S4_PT_OUTPUT),
        ("pi", S4_PI_OUTPUT),
        ("ge", S4_GE_OUTPUT),
        ("ti", S4_TI_OUTPUT),
    ]
    for key, filename in mapping:
        path = stage4_dir / filename
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        result[key].append(json.loads(line))
    return result


def organize_by_domain(fbs: list[dict]) -> dict[str, list[dict]]:
    """Group FBs by their primary (first) raw domain.

    Cross-domain FBs appear in their primary domain folder.
    A secondary 'cross_domain/' folder contains FBs with 3+ domains.
    """
    by_domain: dict[str, list[dict]] = defaultdict(list)

    for fb in fbs:
        domains = fb.get("domains", [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except (json.JSONDecodeError, TypeError):
                domains = [domains]

        if len(domains) >= 3:
            by_domain["cross_domain"].append(fb)

        # Also file under primary domain
        primary = domains[0] if domains else "uncategorized"
        raw = _raw_domain(primary)
        by_domain[raw].append(fb)

    return dict(by_domain)


def write_domain_folders(by_domain: dict[str, list[dict]],
                         non_fb: dict[str, list[dict]] | None = None,
                         export_only: bool = False) -> dict[str, Any]:
    """Write FBs organized by domain into subfolders.

    D2122: Full payload with all fields. PT/PI/GE/TI in separate folders.
    D2123: 3-zone body, jargon in body only.

    Structure:
        anytype_push/{domain}/
            {fb_slug}.json          ← complete push-ready payload
            {fb_slug}.md            ← human-readable 3-zone markdown
        pt/                         ← process templates
        pi/                         ← process instances
        ge/                         ← growth edges
        ti/                         ← tool instructions
        domain_index.json           ← domain → FB mapping
    """
    PUSH_DIR.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {"domains": 0, "fbs_total": 0, "fbs_written": 0,
                              "pt": 0, "pi": 0, "ge": 0, "ti": 0}

    domain_index: dict[str, dict[str, Any]] = {}

    for domain, domain_fbs in sorted(by_domain.items()):
        domain_dir = PUSH_DIR / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        fb_list: list[dict[str, str]] = []
        for fb in domain_fbs:
            name = fb.get("name", "Untitled")
            slug = _slugify(name)
            fb_id = fb.get("fb_id", "")

            # Write markdown (3-zone body, D2122)
            md_path = domain_dir / f"{slug}.md"
            safe_write(str(md_path), _format_fb_markdown(fb) + "\n")

            # Write complete JSON payload (D2122: all fields)
            json_path = domain_dir / f"{slug}.json"
            payload = _format_fb_payload(fb)
            safe_write(str(json_path),
                       json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

            fb_list.append({
                "slug": slug,
                "fb_id": fb_id,
                "name": name,
                "md_path": str(md_path),
                "json_path": str(json_path),
            })
            stats["fbs_written"] += 1

        domain_index[domain] = {
            "count": len(fb_list),
            "fbs": fb_list,
        }
        stats["domains"] += 1

    # ── D2122: Write PT/PI/GE/TI folders ──
    if non_fb:
        for key, label in [("pt", "Process Templates"), ("pi", "Process Instances"),
                           ("ge", "Growth Edges"), ("ti", "Tool Instructions")]:
            items = non_fb.get(key, [])
            if not items:
                continue
            sub_dir = PUSH_DIR / key
            sub_dir.mkdir(parents=True, exist_ok=True)
            for item in items:
                item_name = item.get("name", item.get("principle_text", "unnamed"))[:80]
                slug = _slugify(item_name) if item_name else f"{key}_{uuid4().hex[:8]}"
                # Write JSON
                safe_write(str(sub_dir / f"{slug}.json"),
                           json.dumps(item, indent=2, ensure_ascii=False) + "\n")
                # Write MD
                md_lines = [f"# {item_name}", "",
                            item.get("definition", item.get("principle_text", "")),
                            ""]
                if item.get("application"):
                    md_lines.extend(["## Application", "", item["application"], ""])
                safe_write(str(sub_dir / f"{slug}.md"),
                           "\n".join(md_lines))
            stats[key] = len(items)
            print(f"   📦 {label}: {len(items)} items → {key}/")

    stats["fbs_total"] = sum(len(fbs) for fbs in by_domain.values())

    # Write domain index
    index_path = PUSH_DIR / "domain_index.json"
    safe_write(str(index_path),
               json.dumps(domain_index, indent=2, ensure_ascii=False) + "\n")

    # Write stats
    stats_path = PUSH_DIR / "push_stats.json"
    stamp_record(stats)
    stats["pipeline_commit"] = get_pipeline_commit()
    safe_write(str(stats_path),
               json.dumps(stats, indent=2, ensure_ascii=False) + "\n")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 6b: Push verified FBs to Anytype-ready domain subfolders"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be pushed without writing")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from push ledger (skip confirmed FBs)")
    parser.add_argument("--domain", type=str, default=None,
                        help="Push only a single domain (e.g., 'business')")
    parser.add_argument("--export-only", action="store_true",
                        help="Export to .md only, no JSON payloads")
    parser.add_argument("--all-statuses", action="store_true",
                        help="Include all FBs regardless of verification status")
    parser.add_argument("--include-non-fb", action="store_true",
                        help="Include PT/PI/GE/TI from Stage 4 (D2122)")
    args = parser.parse_args()

    # Load FBs
    fbs = load_verified_fbs()
    print(f"📦 Loaded {len(fbs)} verified FBs")

    # Filter to PASS status only
    if args.all_statuses:
        pass_fbs = fbs
        print(f"   Including ALL statuses: {len(pass_fbs)}")
    else:
        pass_fbs = [fb for fb in fbs if fb.get("status") == "PASS"]
        print(f"   PASS (push): {len(pass_fbs)}")
        flagged = len(fbs) - len(pass_fbs)
        if flagged:
            print(f"   Skipped (FLAG/QUARANTINE): {flagged}")

    if not pass_fbs:
        print("❌ No PASS FBs to push. Run stage5_verify.py with passing results first.")
        sys.exit(1)

    # Organize by domain
    by_domain = organize_by_domain(pass_fbs)

    # Filter to single domain if requested
    if args.domain:
        raw = _raw_domain(args.domain)
        if raw in by_domain:
            by_domain = {raw: by_domain[raw]}
        else:
            print(f"❌ Domain '{args.domain}' not found. Available: {list(by_domain.keys())}")
            sys.exit(1)

    # Resume: skip confirmed
    if args.resume:
        ledger = PushLedger()
        confirmed = ledger.confirmed_slugs()
        if confirmed:
            skipped = 0
            for domain, domain_fbs in by_domain.items():
                before = len(domain_fbs)
                by_domain[domain] = [
                    fb for fb in domain_fbs
                    if _slugify(fb.get("name", "")) not in confirmed
                ]
                skipped += before - len(by_domain[domain])
            print(f"   Resuming: skipping {skipped} already-confirmed FBs")

    # D2122: Load non-FB content
    non_fb: dict[str, list[dict]] | None = None
    if args.include_non_fb:
        non_fb = load_non_fb_content()
        total_non_fb = sum(len(v) for v in non_fb.values())
        if total_non_fb > 0:
            print(f"   PT/PI/GE/TI: {non_fb['pt']} PTs, {non_fb['pi']} PIs, "
                  f"{non_fb['ge']} GEs, {non_fb['ti']} TIs")

    # Dry run
    if args.dry_run:
        total_fbs = sum(len(v) for v in by_domain.values())
        print(f"\n🔍 DRY RUN — {len(by_domain)} domains, {total_fbs} FBs")
        for domain, domain_fbs in sorted(by_domain.items()):
            print(f"\n  {domain}/ ({len(domain_fbs)} FBs)")
            for fb in domain_fbs[:3]:
                print(f"    - {fb.get('name', 'Untitled')[:80]}")
            if len(domain_fbs) > 3:
                print(f"    ... and {len(domain_fbs) - 3} more")
        print(f"\n  Output dir: {PUSH_DIR}")
        return

    # Write domain folders
    stats = write_domain_folders(by_domain, non_fb=non_fb,
                                 export_only=args.export_only)

    print(f"\n{'='*60}")
    print("📊 STAGE 6b — ANYTYPE PUSH PREPARATION (D2122: Complete Payload)")
    print(f"   Domains:        {stats['domains']}")
    print(f"   FBs prepared:   {stats['fbs_written']}")
    if stats.get("pt"):
        print(f"   PT/PI/GE/TI:    {stats['pt']} PT, {stats['pi']} PI, "
              f"{stats['ge']} GE, {stats['ti']} TI")
    print(f"   Output:         {PUSH_DIR}")
    print("\n   Domain folders:")
    for domain in sorted(by_domain.keys()):
        count = len(by_domain[domain])
        print(f"     {domain}/  ({count} FBs)")
    print(f"\n📋 Domain index:   {PUSH_DIR / 'domain_index.json'}")
    print(f"📋 Push stats:     {PUSH_DIR / 'push_stats.json'}")
    print(f"\n💡 Next: Use the JSON payloads in {PUSH_DIR}/{{domain}}/{{fb_slug}}.json")
    print("   to push to Anytype via the Local API or anytype-mcp server.")
    print("   All 42+ fields included per D2122. 3-zone body per D2123.")


if __name__ == "__main__":
    main()
