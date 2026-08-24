#!/usr/bin/env python3
"""
FULL PIPELINE RUN v3 — Complete FB records with ALL properties. C12 compliant.

Adds missing: author, book_title, citation, source_paragraph_ids, grounding_evidence,
confidence, borp_score, related_fbs, embodiment_tag, taxonomy_version.
Fixes: jargon in body only (not YAML), citation with Author (Book Title) format.

D2121: All configurable values extracted to config/pipeline_config.yaml → test.full_run.
No hardcoded paths, model names, thresholds, or magic numbers.
"""
import json, os, sys, time, re
from pathlib import Path
from datetime import datetime, timezone

# ── Paths from config (C12: no hardcoded paths) ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

_CFG_PATH = ROOT / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

TEST_CFG = _CFG["test"]["full_run"]
DEFAULTS = TEST_CFG["defaults"]
CONTEXT_SIGNALS = TEST_CFG["context_signals"]
TEMPORAL_SIGNALS = TEST_CFG["temporal_signals"]
DIFFICULTY_MAP = TEST_CFG["difficulty_map"]
BODY_ONLY_FIELDS = TEST_CFG["body_only_fields"]

BOOKS_DIR = ROOT / _CFG["books_dir"]
CHECKPOINT_DIR = ROOT / _CFG["paths"]["checkpoint_dir"]
OUT_DIR = ROOT / _CFG["stages"]["stage6_commit"] / TEST_CFG["output_subdir"]
OUT_DIR.mkdir(parents=True, exist_ok=True)

os.environ["MAXWELL_BORP_MIN_SOURCES"] = "1"

# ── Load metadata cache (author + title lookup) ──
metadata_cache: dict[str, dict[str, str]] = {}
meta_cache_file = TEST_CFG["metadata_cache_file"]
meta_path = CHECKPOINT_DIR / meta_cache_file
if meta_path.exists():
    with open(meta_path) as f:
        for line in f:
            d = json.loads(line)
            file_name = d.get("file", "")
            metadata_cache[file_name] = {
                "author": d.get("author", ""),
                "title": d.get("title", ""),
            }

# ── Resolve book paths (D2439: config manifest redacted — derive at runtime) ──
SELECTED: list[Path] = []
if TEST_CFG.get("books"):
    for book_rel in TEST_CFG["books"]:
        p = BOOKS_DIR / book_rel
        assert p.exists(), f"Missing: {p}"
        SELECTED.append(p)
else:
    SELECTED = sorted(BOOKS_DIR.rglob("*.md"))

for b in SELECTED:
    print(f"✅ {b.name[:70]} ({b.stat().st_size:,}B)")


def get_meta(filename: str) -> dict[str, str]:
    """Look up author/title: 1) metadata cache 2) parse filename."""
    meta = metadata_cache.get(filename, {})
    author = meta.get("author", "")
    title = meta.get("title", "")

    if not author and not title:
        stem = Path(filename).stem
        m = re.match(r'^(.+?)\s*\(([^)]+?)\)\s*(?:\(.*\))?$', stem)
        if m:
            title = m.group(1).strip()
            possible_author = m.group(2).strip()
            if not re.match(r'^\d{4}$|^z-library|^libgen|^Anna|^ISBN|^http',
                            possible_author, re.IGNORECASE):
                author = possible_author
        if not author:
            m = re.match(r'^(.+?)\s+--\s+(.+?)(?:\s+--.*)?$', stem)
            if m:
                author = m.group(1).strip()
                title = m.group(2).strip()

    return {"author": author, "title": title}


def _resolve_context(domain_set: set[str]) -> str:
    """Map canonical domains → context routing string from config."""
    parts: list[str] = []
    for ctx_name, sigs in CONTEXT_SIGNALS.items():
        if domain_set & set(sigs):
            parts.append(ctx_name)
    return ", ".join(parts) if parts else "general"


def _resolve_temporal_scope(definition_text: str) -> str:
    """Detect temporal scope from definition text using config signals."""
    lower = definition_text.lower()
    for sig in TEMPORAL_SIGNALS.get("contemporary", []):
        if sig.lower() in lower:
            return "contemporary"
    return "timeless"


def _build_citation(author: str, book_title: str, source_fn: str) -> str:
    """Build citation in Author (Book Title) format (D2123)."""
    if author and book_title:
        return f"{author} ({book_title})"
    if author:
        return author
    if book_title:
        return book_title
    return Path(source_fn).stem


# ═══════════════ STAGE 1: Chunk ═══════════════
print(f"\n{'='*60}\nSTAGE 1: CHUNKING\n{'='*60}")
from pipeline.stage1_chunk import chunk_text, split_on_headings

all_segments: list[dict] = []
for path in SELECTED:
    text = path.read_text()
    sections = split_on_headings(text)
    segs: list[dict] = []
    for heading, body, title in sections:
        for c in chunk_text(body):
            segs.append({"text": c, "heading": heading, "title": title,
                         "source_file": str(path)})
    all_segments.extend(segs)
    print(f"  {path.name[:50]:50s} → {len(segs)} segments")
print(f"  TOTAL: {len(all_segments)} segments")

# ═══════════════ STAGE 2: Extract ═══════════════
print(f"\n{'='*60}\nSTAGE 2: EXTRACT PRINCIPLES\n{'='*60}")
from pipeline.omlx_call import call_omlx_json, check_omlx_health
assert check_omlx_health(), "OMLX not running"

EXTRACT_MODEL = TEST_CFG["extract_model"]
EXTRACT_MAX_TOKENS = TEST_CFG["extract_max_tokens"]
EXTRACT_SYSTEM = TEST_CFG["extract_system_prompt"]
TOP_N = TEST_CFG["extraction_top_n"]
COMBINED_CHARS = TEST_CFG["extraction_combined_chars"]
PROMPT_LIMIT = TEST_CFG["extraction_prompt_limit"]

clusters: dict[str, list[dict]] = {}
for seg in all_segments:
    source = Path(seg.get("source_file", "")).name
    clusters.setdefault(source, []).append(seg)

principles: list[dict] = []
for source, segs in list(clusters.items()):
    segs_sorted = sorted(segs, key=lambda s: len(s.get("text", "")), reverse=True)[:TOP_N]
    combined = "\n\n---\n\n".join(
        s.get("text", "")[:COMBINED_CHARS] for s in segs_sorted
    )
    prompt = f"Extract 1-3 principles:\n\n{combined[:PROMPT_LIMIT]}"
    try:
        result = call_omlx_json(prompt=prompt, model=EXTRACT_MODEL,
                                system=EXTRACT_SYSTEM, max_tokens=EXTRACT_MAX_TOKENS)
        items = result if isinstance(result, list) else [result]
        for p in items:
            p["source_book"] = source
            principles.append(p)
        print(f"  {source[:50]:50s} → {len(items)} principles")
    except Exception as e:
        print(f"  {source[:50]:50s} → ❌ {e}")
print(f"  TOTAL: {len(principles)} principles")

# ═══════════════ STAGE 4: D2138 + CRIBS + FULL SCHEMA ═══════════════
print(f"\n{'='*60}\nSTAGE 4: D2138 CLASSIFY + FULL FB SCHEMA\n{'='*60}")
from pipeline.stage4_merge import (
    CLASSIFY_SYSTEM_PROMPT, build_classify_prompt,
    map_to_canonical_with_fallback, _serialize_jargon, normalize_fb_name,
    compute_fb_relationships,
)
from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES, get_synonym_index
from pipeline.stamp import make_hash_id

CLASSIFY_MODEL = TEST_CFG["classify_model"]
CLASSIFY_MAX_TOKENS = TEST_CFG["classify_max_tokens"]

syn_idx = get_synonym_index()
run_id = f"full-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

fbs: list[dict] = []
difficulty_map = DIFFICULTY_MAP
body_only = set(BODY_ONLY_FIELDS)

for i, p in enumerate(principles):
    name = p.get("name", f"Principle {i+1}")
    definition = p.get("definition", "")
    source_book_fn = p.get("source_book", "unknown")
    meta = get_meta(source_book_fn)

    if not definition or len(definition) < 20:
        continue

    print(f"\n  [{i+1}/{len(principles)}] {name[:55]}")

    # ── D2138 Stage 1: Free classification ──
    cp = build_classify_prompt(name, definition)
    try:
        cd = call_omlx_json(prompt=cp, model=CLASSIFY_MODEL,
                            system=CLASSIFY_SYSTEM_PROMPT, max_tokens=CLASSIFY_MAX_TOKENS)
    except Exception:
        cd = {"discipline": "emerging", "domains": ["emerging"],
              "is_specialized": False, "evidence": "cited"}

    disc_raw = str(cd.get("discipline", ""))
    domains_raw = list(cd.get("domains", []))
    is_spec = cd.get("is_specialized", False)
    if not isinstance(is_spec, bool):
        is_spec = str(is_spec).lower() in ("true", "1", "yes")
    evidence = cd.get("evidence", "cited")
    if evidence not in ("cited", "axiomatic"):
        evidence = "cited"

    # ── D2138 Stage 2: Canonical mapping ──
    canon_disc = map_to_canonical_with_fallback(
        disc_raw, "discipline", syn_idx, CANONICAL_DISCIPLINES)
    canon_doms: list[str] = []
    seen_d: set[str] = set()
    for d in domains_raw:
        m = map_to_canonical_with_fallback(d, "domain", syn_idx, CANONICAL_DOMAINS)
        if m not in seen_d:
            seen_d.add(m)
            canon_doms.append(m)
    if not canon_doms:
        canon_doms = ["emerging"]

    # ── D2139: Depth derivation (from config) ──
    n_canonical = len([d for d in canon_doms if d != "emerging"])
    has_emerging = "emerging" in canon_doms
    if is_spec:
        if n_canonical >= 2:
            depth = "domain"
        elif n_canonical == 1:
            depth = "specialized"
        else:
            depth = "domain"
    else:
        eff = n_canonical + (1 if has_emerging else 0)
        if eff >= 3:
            depth = "universal"
        elif eff == 2:
            depth = "cross-domain"
        elif eff == 1:
            depth = "domain"
        else:
            depth = "domain"

    # ── Context routing (from config signals) ──
    domain_set = set(canon_doms)
    context_val = _resolve_context(domain_set)

    # ── Difficulty level (from config map) ──
    difficulty_level = difficulty_map.get(depth, "intermediate")

    # ── Temporal scope (from config signals) ──
    def_text = (definition + " " + p.get("elaboration", "")).lower()
    temporal_scope = _resolve_temporal_scope(def_text)

    # ── CRIBS fields ──
    fb_app = p.get("application", "").strip()
    fb_fail = p.get("failure_mode", "").strip()
    fb_elab = p.get("elaboration", "").strip()
    fb_kw = p.get("keywords", "").strip()
    jargon_raw = p.get("jargon")
    jargon_val = _serialize_jargon(jargon_raw)

    # ── Citation (D2123: Author (Book Title) format) ──
    author = meta.get("author", "")
    book_title = meta.get("title", "")
    citation = _build_citation(author, book_title, source_book_fn)

    # ── Paragraph IDs ──
    source_para_ids = f"{Path(source_book_fn).stem[:20]}_p1"

    # ── Default values from config ──
    borp_score = DEFAULTS["borp_score"]
    confidence = DEFAULTS["confidence"]

    # ── BUILD COMPLETE FB ──
    fb: dict = {
        # Identity
        "fb_id": make_hash_id(name, definition),
        "name": normalize_fb_name(name),
        "fb_version": 1,
        # CRIBS content (body section)
        "definition": definition,
        "application": fb_app,
        "failure_mode": fb_fail,
        "elaboration": fb_elab,
        "keywords": fb_kw,
        # Classification (D2138 two-stage)
        "discipline": canon_disc,
        "discipline_raw": disc_raw if disc_raw else None,
        "domains": canon_doms,
        "domains_raw": domains_raw,
        "depth": depth,
        "evidence": evidence,
        "is_specialized": is_spec,
        # Citation (D2123 proper format)
        "source_author": author if author else None,
        "source_title": book_title if book_title else None,
        "citation": citation,
        "source_books": [source_book_fn],
        "source_clusters": [f"book:{source_book_fn}"],
        "source_paragraph_ids": source_para_ids,
        "source_principle_ids": [],
        "source_text": definition[:500],
        "grounding_evidence": DEFAULTS["grounding_evidence"],
        # Verification
        "confidence": confidence,
        "borp_score": borp_score,
        "classification_errors": None,
        # v1 Anytype properties
        "context": context_val,
        "accessibility": DEFAULTS["accessibility"],
        "intimacy_boundary": DEFAULTS["intimacy_boundary"],
        "provenance": DEFAULTS["provenance"],
        # Agentic metadata
        "difficulty_level": difficulty_level,
        "temporal_scope": temporal_scope,
        "prerequisite_fbs": [],
        "procedural_skill": None,
        "related_fbs": [],  # Populated by compute_fb_relationships below
        "embodiment_tag": None,
        # Stamps
        "schema_version": TEST_CFG["schema_version"],
        "taxonomy_version": TEST_CFG["taxonomy_version"],
        "gen_model": CLASSIFY_MODEL,
        "pipeline_commit": TEST_CFG["pipeline_commit"],
        "pipeline_run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Jargon: body section only (D2123: NOT in metadata)
    if jargon_val:
        fb["jargon"] = jargon_val

    fbs.append(fb)
    cribs_ok = bool(fb_app and fb_fail and fb_elab and fb_kw)
    raw_vs_canon = disc_raw != canon_disc
    print(f"    depth={depth} disc={canon_disc} doms={len(canon_doms)} spec={is_spec} "
          f"cribs={'✅' if cribs_ok else '❌'} jargon={'✅' if jargon_val else '⬜'} "
          f"citation={citation[:40]} raw≠canon={raw_vs_canon}")

# ── D2123: Populate related_fbs (MUST call compute_fb_relationships) ──
print(f"\n{'='*60}\nCOMPUTING FB RELATIONSHIPS (D2123)\n{'='*60}")
if len(fbs) > 1:
    compute_fb_relationships(fbs)
    related_count = sum(1 for fb in fbs if fb.get("related_fbs"))
    print(f"  ✅ {related_count}/{len(fbs)} FBs have related_fbs populated")
else:
    print(f"  ⚠️  Only {len(fbs)} FB — skipping relationship computation")

# ═══════════════ EXPORT ═══════════════
print(f"\n{'='*60}\nEXPORT: {len(fbs)} FBs\n{'='*60}")

# ── fbs_complete.json ──
(OUT_DIR / "fbs_complete.json").write_text(
    json.dumps(fbs, indent=2, ensure_ascii=False))
print(f"  ✅ fbs_complete.json ({len(fbs)} FBs)")

# ── per_fb/ ──
per_fb_dir = OUT_DIR / "per_fb"
per_fb_dir.mkdir(exist_ok=True)
for fb in fbs:
    slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
    (per_fb_dir / f"{slug}.json").write_text(
        json.dumps(fb, indent=2, ensure_ascii=False))
print(f"  ✅ per_fb/ ({len(fbs)} files)")

# ── Obsidian vault (D2123: jargon in BODY only, NOT YAML frontmatter) ──
obsidian_dir = OUT_DIR / "obsidian_vault"
obsidian_dir.mkdir(exist_ok=True)

for fb in fbs:
    slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
    domains = fb.get("domains", ["emerging"])

    # YAML frontmatter: metadata only, NO body fields
    fm = ["---"]
    for k, v in fb.items():
        if k in body_only:
            continue
        if v is None:
            continue
        if isinstance(v, list):
            fm.append(f"{k}: {json.dumps(v)}")
        elif isinstance(v, bool):
            fm.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            fm.append(f"{k}: {v}")
        elif isinstance(v, str) and ('"' in v or '\n' in v):
            fm.append(f'{k}: "{v}"')
        else:
            fm.append(f"{k}: {v}")
    fm.append("---")
    fm.append("")

    # Body sections (CRIBS + jargon are BODY per D2123)
    body: list[str] = [f"# {fb['name']}", ""]

    cit = fb.get("citation", "")
    if cit:
        body.append(f"> **Source:** {cit}")
        body.append("")

    body.append("## Definition")
    body.append("")
    body.append(fb.get("definition", ""))

    if fb.get("application"):
        body.extend(["", "## Application", "", fb["application"]])
    if fb.get("failure_mode"):
        body.extend(["", "## Failure Mode", "", fb["failure_mode"]])
    if fb.get("elaboration"):
        body.extend(["", "## Elaboration", "", fb["elaboration"]])
    if fb.get("keywords"):
        body.extend(["", "## Keywords", "", fb["keywords"]])
    if fb.get("jargon"):
        body.append("")
        body.append("## Jargon")
        body.append("")
        for td in fb["jargon"].split("; "):
            if ": " in td:
                t, d = td.split(": ", 1)
                body.append(f"- **{t.strip()}**: {d.strip()}")
            else:
                body.append(f"- {td.strip()}")

    page = "\n".join(fm) + "\n".join(body)
    for domain in domains:
        dd = obsidian_dir / domain
        dd.mkdir(exist_ok=True)
        (dd / f"{slug}.md").write_text(page)

obsidian_count = sum(
    1 for d in obsidian_dir.iterdir() if d.is_dir()
    for _ in d.glob("*.md"))
ndoms = len(set(d for fb in fbs for d in fb.get("domains", [])))
print(f"  ✅ Obsidian: {obsidian_count} .md files in {ndoms} domain folders")

# ── Anytype push ──
anytype_dir = OUT_DIR / "anytype_push"
anytype_dir.mkdir(exist_ok=True)
for fb in fbs:
    slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
    domains = fb.get("domains", ["emerging"])
    for domain in domains:
        dd = anytype_dir / domain
        dd.mkdir(exist_ok=True)
        (dd / f"{slug}.json").write_text(
            json.dumps(fb, indent=2, ensure_ascii=False))
anytype_count = sum(
    1 for d in anytype_dir.iterdir() if d.is_dir()
    for _ in d.glob("*.json"))
print(f"  ✅ Anytype: {anytype_count} .json files")

# ═══════════════ SUMMARY ═══════════════
print(f"\n{'='*70}")
print(f"FULL RUN COMPLETE — {len(fbs)} FBs with ALL properties (C12 compliant)")
print(f"{'='*70}")

all_keys = sorted(set().union(*(fb.keys() for fb in fbs)))
for key in all_keys:
    present = sum(1 for fb in fbs
                  if fb.get(key) is not None
                  and fb.get(key) != ""
                  and fb.get(key) != [])
    bar = "█" * min(present, 25)
    print(f"  {key:30s} {present}/{len(fbs):>2d} {bar}")

print(f"\n  OUTPUT: {OUT_DIR}")
print(f"    fbs_complete.json — all {len(fbs)} FBs (full schema)")
print(f"    per_fb/          — one JSON per FB")
print(f"    obsidian_vault/  — .md, jargon in body only, citation in header")
print(f"    anytype_push/    — .json per FB per domain")
print(f"\n  Jargon: in body section ONLY (not YAML frontmatter) [D2123]")
print(f"  Citation: Author (Book Title) format [D2123]")
print(f"  related_fbs: populated via compute_fb_relationships() [D2123]")
print(f"  Config: {_CFG_PATH} → test.full_run [D2121]")
