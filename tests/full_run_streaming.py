#!/usr/bin/env python3
"""
FULL PIPELINE RUN v4 — STREAMING PER-BOOK (D2129)
====================================================================
Memory-safe production runner for the 922-book corpus.

D2129: Never hold all segments in RAM. Process ONE book at a time:
    chunk → extract → classify → build FB → append → free.

Resume: processed books tracked in a checkpoint JSONL; re-running
skips completed books and continues where it left off.

C12: all configurable values from config/pipeline_config.yaml → test.full_run.
No hardcoded paths, model names, thresholds, or magic numbers.
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# ── Paths from config (C12) ──
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
OUT_DIR = ROOT / _CFG["stages"]["stage6_commit"] / "full-run-streaming"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESUME_FILE = CHECKPOINT_DIR / "streaming_resume.jsonl"
QUARANTINE_FILE = CHECKPOINT_DIR / "streaming_quarantine.jsonl"

os.environ["MAXWELL_BORP_MIN_SOURCES"] = "1"

# ── Metadata cache (author + title lookup) ──
# BUG-061 FIX: use shared pipeline/book_metadata.py resolver. The old
# loader keyed by d.get("file") which never exists in the records
# (they use source_book) → cache was empty → fragile filename parsing
# produced swapped author/title (e.g., "(Title)" parsed as author).
from pipeline.book_metadata import (  # noqa: E402
    build_citation as _build_citation_shared,
    load_metadata_cache as _load_metadata_shared,
    resolve_book_metadata as _resolve_book_metadata_shared,
)

metadata_cache: dict[str, dict[str, str]] = _load_metadata_shared()


def get_meta(filename: str) -> dict[str, str]:
    """Look up author/title: 1) metadata cache 2) robust filename heuristic.

    BUG-061 FIX: delegates to pipeline.book_metadata.resolve_book_metadata —
    cache is keyed by source_book (was broken: keyed by "file"), and the
    filename fallback handles leading-paren filenames (previously swapped
    title↔author).
    """
    return _resolve_book_metadata_shared(filename)


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


def _load_resume() -> set[str]:
    """Load set of completed source filenames from resume checkpoint."""
    done: set[str] = set()
    if RESUME_FILE.exists():
        with open(RESUME_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)["source_file"])
                except (json.JSONDecodeError, KeyError):
                    # Torn/partial line from an interrupted write — skip (crash-safe)
                    continue
    return done


def _append_resume(source_file: str, fb_count: int, elapsed_s: float,
                   error: str | None = None) -> None:
    """Append one book's result to the resume checkpoint (crash-safe)."""
    record = {
        "source_file": source_file,
        "fb_count": fb_count,
        "elapsed_s": round(elapsed_s, 1),
        "error": error,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    # Append + fsync (C6 crash-safe). A torn final line is tolerated by the
    # resume loader's json.loads guard (skips malformed lines).
    with open(RESUME_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _quarantine(source_file: str, reason: str) -> None:
    """Log a book that cannot be processed (0-byte, unreadable)."""
    record = {"source_file": source_file, "reason": reason,
              "ts": datetime.now(timezone.utc).isoformat()}
    with open(QUARANTINE_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def process_book(path: Path, extract_model: str, extract_max_tokens: int,
                 extract_system: str, top_n: int, combined_chars: int,
                 prompt_limit: int, classify_model: str, classify_max_tokens: int,
                 syn_idx: dict, run_id: str, few_shot: str = "") -> tuple[list[dict], list[dict]]:
    """Process ONE book: chunk → extract → classify → FBs.

    Returns (fbs, principles). Memory is freed on return.
    """
    from pipeline.stage1_chunk import chunk_text, split_on_headings
    from pipeline.omlx_call import call_omlx_json
    from pipeline.stage4_merge import (
        CLASSIFY_SYSTEM_PROMPT, build_classify_prompt,
        map_to_canonical_with_fallback, _serialize_jargon, normalize_fb_name,
    )
    from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES
    from pipeline.stamp import make_hash_id

    source_fn = path.name
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return [], []

    sections = split_on_headings(text)
    # D2137: drop publisher boilerplate segments (config-driven)
    import re as _re
    _boiler = (_CFG.get("stage1_3", {}) or {}).get("drop_patterns_extra", []) or []
    _boiler_re = _re.compile("|".join(_re.escape(b) for b in _boiler), _re.I) if _boiler else None

    segs: list[dict] = []
    for heading, body, title in sections:
        for c in chunk_text(body):
            if _boiler_re and _boiler_re.search(c):
                continue
            segs.append({"text": c, "heading": heading, "title": title,
                         "source_file": str(path)})
    if not segs:
        return [], []

    # ── Extract 1-3 principles from top-N longest segments (proven path) ──
    segs_sorted = sorted(segs, key=lambda s: len(s.get("text", "")), reverse=True)[:top_n]
    combined = "\n\n---\n\n".join(
        s.get("text", "")[:combined_chars] for s in segs_sorted)
    prompt = f"Extract 1-3 principles:\n\n{combined[:prompt_limit]}"
    system = extract_system
    if few_shot:
        # D2123/calibrated golden few-shot (3 pos + 1 neg, Kimi-reviewed) —
        # injected exactly like stage2_extract.call_llm does
        system = system + "\n\n" + few_shot
    try:
        result = call_omlx_json(prompt=prompt, model=extract_model,
                                system=system, max_tokens=extract_max_tokens)
    except Exception as e:
        print(f"    ⚠️  extraction error: {e}")
        return [], []
    if result is None:
        # C16/D2134: fail-visible — a None return is a silent-failure class bug
        print(f"    ⚠️  extraction returned None (JSON parse failed?) — 0 principles")
        return [], []

    items = result if isinstance(result, list) else [result]
    principles = []
    for p in items:
        if isinstance(p, dict):
            r = str(p.get("route", "FB")).upper()
            if r == "NULL":
                continue  # gate: LLM flagged non-principle (matches stage2)
            p["source_book"] = source_fn
            principles.append(p)

    # ── Classify + build FBs (mirrors full_run.py Stage 4, D2138 two-stage) ──
    fbs: list[dict] = []
    for i, p in enumerate(principles):
        name = p.get("name", f"Principle {i+1}")
        definition = p.get("definition", "")
        if not definition or len(definition) < 20:
            continue
        mechanism = str(p.get("mechanism", "") or "").strip()
        boundary = str(p.get("boundary", "") or "").strip()
        consequence = str(p.get("consequence", "") or "").strip()
        is_summary = bool(p.get("is_summary", False))
        evidence_passages = list(p.get("evidence_passages", []) or [])
        meta = get_meta(source_fn)

        cp = build_classify_prompt(name, definition)
        classify_error: str | None = None
        try:
            cd = call_omlx_json(prompt=cp, model=classify_model,
                                system=CLASSIFY_SYSTEM_PROMPT,
                                max_tokens=classify_max_tokens)
        except Exception as e:
            # D2134: fail-visible — flag the error on the FB (no silent "emerging")
            print(f"    ⚠️  classify error: {e}")
            cd = {"discipline": "", "domains": [], "is_specialized": False,
                  "evidence": "cited"}
            classify_error = str(e)[:200]

        disc_raw = str(cd.get("discipline", "")) if cd.get("discipline") else ""
        domains_raw = list(cd.get("domains", []))
        is_spec = cd.get("is_specialized", False)
        if not isinstance(is_spec, bool):
            is_spec = str(is_spec).lower() in ("true", "1", "yes")
        evidence = cd.get("evidence", "cited")
        if evidence not in ("cited", "axiomatic"):
            evidence = "cited"

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

        # ── D2139 depth derivation — MUST mirror stage4_merge.py exactly ──
        n_canonical = len([d for d in canon_doms if d != "emerging"])
        has_emerging = "emerging" in canon_doms
        if is_spec:
            # Specialized: canonical-only count. 0 real domains → "domain" (conservative).
            if n_canonical >= 2:
                depth = "domain"
            elif n_canonical == 1:
                depth = "specialized"
            else:
                depth = "domain"
        else:
            effective_n = n_canonical + (1 if has_emerging else 0)
            if effective_n >= 3:
                depth = "universal"
            elif effective_n == 2:
                depth = "cross-domain"
            elif effective_n == 1:
                depth = "domain"
            else:
                depth = "domain"

        domain_set = set(canon_doms)
        context_val = _resolve_context(domain_set)
        difficulty_level = DIFFICULTY_MAP.get(depth, "intermediate")
        def_text = (definition + " " + p.get("elaboration", "")).lower()
        temporal_scope = _resolve_temporal_scope(def_text)

        fb_app = p.get("application", "").strip()
        fb_fail = p.get("failure_mode", "").strip()
        fb_elab = p.get("elaboration", "").strip()
        fb_kw = p.get("keywords", "").strip()
        jargon_val = _serialize_jargon(p.get("jargon"))

        author = meta.get("author", "")
        book_title = meta.get("title", "")
        citation = _build_citation_shared(author, book_title, source_fn)

        source_para_ids = f"{Path(source_fn).stem[:20]}_p1"

        fb: dict = {
            "fb_id": make_hash_id(name, definition),
            "name": normalize_fb_name(name),
            "fb_version": 1,
            "definition": definition,
            "application": fb_app,
            "failure_mode": fb_fail,
            "elaboration": fb_elab,
            "mechanism": mechanism,
            "boundary": boundary,
            "consequence": consequence,
            "is_summary": is_summary,
            "evidence_passages": evidence_passages,
            "keywords": fb_kw,
            "discipline": canon_disc,
            "discipline_raw": disc_raw if disc_raw else None,
            "domains": canon_doms,
            "domains_raw": domains_raw,
            "depth": depth,
            "evidence": evidence,
            "is_specialized": is_spec,
            "source_author": author if author else None,
            "source_title": book_title if book_title else None,
            "citation": citation,
            "source_books": [source_fn],
            "primary_source": {"book": source_fn, "reason": "single source"},
            "source_clusters": [f"book:{source_fn}"],
            "source_paragraph_ids": source_para_ids,
            "source_principle_ids": [],
            "source_text": definition[:500],
            "grounding_evidence": DEFAULTS["grounding_evidence"],
            "confidence": DEFAULTS["confidence"],
            "borp_score": DEFAULTS["borp_score"],
            "classification_errors": ([classify_error] if classify_error else None),
            "context": context_val,
            "accessibility": DEFAULTS["accessibility"],
            "intimacy_boundary": DEFAULTS["intimacy_boundary"],
            "provenance": DEFAULTS["provenance"],
            "difficulty_level": difficulty_level,
            "temporal_scope": temporal_scope,
            "prerequisite_fbs": [],
            "procedural_skill": None,
            "related_fbs": [],
            "embodiment_tag": None,
            "schema_version": TEST_CFG["schema_version"],
            "taxonomy_version": TEST_CFG["taxonomy_version"],
            "gen_model": classify_model,
            "pipeline_commit": TEST_CFG["pipeline_commit"],
            "pipeline_run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if jargon_val:
            fb["jargon"] = jargon_val
        fbs.append(fb)

    return fbs, principles


def main() -> None:
    # ── Resolve book paths (D2439: config manifest redacted — derive at runtime) ──
    selected: list[Path] = []
    skipped = 0
    if TEST_CFG.get("books"):
        for book_rel in TEST_CFG["books"]:
            p = BOOKS_DIR / book_rel
            if p.exists():
                selected.append(p)
            else:
                skipped += 1
    else:
        selected = sorted(BOOKS_DIR.rglob("*.md"))
    print(f"✅ {len(selected)} books found in {BOOKS_DIR} ({skipped} config paths missing)")

    from pipeline.omlx_call import check_omlx_health
    assert check_omlx_health(), "OMLX not running"

    from pipeline.schemas import get_synonym_index
    from pipeline.stage4_merge import compute_fb_relationships

    # Golden few-shot (D2123): load calibrated examples, format for injection
    from pipeline.stage2_extract import load_golden_parity, format_golden_fewshot
    golden_path = str(ROOT / _CFG["stage2"]["golden_path"])
    golden_on = bool(_CFG["stage2"].get("golden_inject_enabled", False))
    few_shot = ""
    if golden_on:
        pos, neg, n_ex = load_golden_parity(
            golden_path,
            int(_CFG["stage2"]["golden_positive"]),
            int(_CFG["stage2"]["golden_negative"]),
            int(_CFG["stage2"]["golden_max_examples"]),
        )
        few_shot = format_golden_fewshot(pos, neg) if pos else ""
        print(f"Golden few-shot: {n_ex} examples injected "
              f"({'ON' if few_shot else 'OFF — none found'})")

    syn_idx = get_synonym_index()
    run_id = f"full-run-stream-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    EXTRACT_MODEL = TEST_CFG["extract_model"]
    EXTRACT_MAX_TOKENS = TEST_CFG["extract_max_tokens"]
    EXTRACT_SYSTEM = TEST_CFG["extract_system_prompt"]
    TOP_N = TEST_CFG["extraction_top_n"]
    COMBINED_CHARS = TEST_CFG["extraction_combined_chars"]
    PROMPT_LIMIT = TEST_CFG["extraction_prompt_limit"]
    CLASSIFY_MODEL = TEST_CFG["classify_model"]
    CLASSIFY_MAX_TOKENS = TEST_CFG["classify_max_tokens"]

    # ── Resume ──
    done = _load_resume()
    todo = [p for p in selected if p.name not in done]
    print(f"Resume: {len(done)} books already processed, {len(todo)} remaining")

    fbs: list[dict] = []
    t_start = time.time()
    quarantined: list[str] = []

    for idx, path in enumerate(todo, 1):
        t0 = time.time()
        size = path.stat().st_size
        if size == 0:
            _quarantine(path.name, "zero-byte file")
            _append_resume(path.name, 0, 0.0, "zero-byte")
            quarantined.append(path.name)
            print(f"  [{idx}/{len(todo)}] ⚠️  {path.name[:50]} → 0 bytes (quarantined)")
            continue

        try:
            book_fbs, principles = process_book(
                path, EXTRACT_MODEL, EXTRACT_MAX_TOKENS, EXTRACT_SYSTEM,
                TOP_N, COMBINED_CHARS, PROMPT_LIMIT,
                CLASSIFY_MODEL, CLASSIFY_MAX_TOKENS, syn_idx, run_id, few_shot)
        except Exception as e:
            print(f"  [{idx}/{len(todo)}] ❌ {path.name[:50]} → {e}")
            _append_resume(path.name, 0, time.time() - t0, str(e)[:200])
            continue

        fbs.extend(book_fbs)
        elapsed = time.time() - t0
        _append_resume(path.name, len(book_fbs), elapsed)
        print(f"  [{idx}/{len(todo)}] {path.name[:55]:55s} "
              f"→ {len(book_fbs)} FB  ({elapsed:.1f}s)")

        # Memory safety: segments/principles already freed by process_book scope
        if idx % 25 == 0:
            rate = (time.time() - t_start) / idx
            remain = len(todo) - idx
            print(f"      … {idx} books | {len(fbs)} FBs | "
                  f"{rate:.1f}s/book | ETA {remain*rate/60:.0f} min")

    # ── Relationships (small: FB definitions only) ──
    print(f"\n{'='*60}\nCOMPUTING FB RELATIONSHIPS (D2123)\n{'='*60}")
    if len(fbs) > 1:
        compute_fb_relationships(fbs)
        rel = sum(1 for fb in fbs if fb.get("related_fbs"))
        print(f"  ✅ {rel}/{len(fbs)} FBs have related_fbs")
    else:
        print(f"  ⚠️  Only {len(fbs)} FB — skipping")

    # ── Exports (same format as full_run.py) ──
    print(f"\n{'='*60}\nEXPORT: {len(fbs)} FBs\n{'='*60}")
    (OUT_DIR / "fbs_complete.json").write_text(
        json.dumps(fbs, indent=2, ensure_ascii=False))

    per_fb_dir = OUT_DIR / "per_fb"
    per_fb_dir.mkdir(exist_ok=True)
    for fb in fbs:
        slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
        (per_fb_dir / f"{slug}.json").write_text(
            json.dumps(fb, indent=2, ensure_ascii=False))

    obsidian_dir = OUT_DIR / "obsidian_vault"
    obsidian_dir.mkdir(exist_ok=True)
    for fb in fbs:
        slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
        domains = fb.get("domains", ["emerging"])
        fm = ["---"]
        for k, v in fb.items():
            if k in BODY_ONLY_FIELDS or v is None:
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
        fm.append("")  # D2123: blank line required — YAML frontmatter must not
        # glue the closing --- to the body heading or Obsidian won't parse it.
        body = [f"# {fb['name']}", ""]
        cit = fb.get("citation", "")
        if cit:
            body.append(f"> **Source:** {cit}")
            body.append("")
        body.extend(["## Definition", "", fb.get("definition", "")])
        if fb.get("mechanism"):
            body.extend(["", "## Mechanism", "", fb["mechanism"]])
        if fb.get("boundary"):
            body.extend(["", "## Boundary", "", fb["boundary"]])
        if fb.get("consequence"):
            body.extend(["", "## Consequence", "", fb["consequence"]])
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

    anytype_dir = OUT_DIR / "anytype_push"
    anytype_dir.mkdir(exist_ok=True)
    for fb in fbs:
        slug = fb["name"].lower().replace(" ", "_").replace("'", "")[:80]
        for domain in fb.get("domains", ["emerging"]):
            dd = anytype_dir / domain
            dd.mkdir(exist_ok=True)
            (dd / f"{slug}.json").write_text(
                json.dumps(fb, indent=2, ensure_ascii=False))

    # ── Summary ──
    total_s = time.time() - t_start
    print(f"\n{'='*70}")
    print(f"STREAMING RUN COMPLETE — {len(fbs)} FBs from {len(todo)} books")
    print(f"  elapsed: {total_s/60:.1f} min | quarantined: {len(quarantined)}")
    print(f"  output: {OUT_DIR}")
    print(f"  resume: {RESUME_FILE} (re-run to continue)")
    print(f"{'='*70}")
    all_keys = sorted(set().union(*(fb.keys() for fb in fbs))) if fbs else []
    for key in all_keys:
        present = sum(1 for fb in fbs
                      if fb.get(key) is not None and fb.get(key) != "" and fb.get(key) != [])
        bar = "█" * min(present, 25)
        print(f"  {key:30s} {present}/{len(fbs):>2d} {bar}")


if __name__ == "__main__":
    main()
