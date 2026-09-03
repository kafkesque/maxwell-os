#!/usr/bin/env python3
"""scripts/reinject_bug198_singletons.py — D2519 (BUG-198 part 2 of 2).

Targeted S4→S5→S6 mini-run for the 6 recovered singleton principles that BUG-198
dropped at S4 (application=None → D2371 fail-closed drop). Part 1 (recover_bug198_singletons.py)
already backfilled the single missing `application` field cross-family via gemma and
wrote `stage2_extract/t11/recovered_singletons.jsonl`.

This script reuses the REAL pipeline functions — NOT a reimplementation — so the
6 re-injected FBs are byte-compatible with a full S0-S6 run:
  * S4 classify:  merged_cribs_classify() + classify_depth_focused() + the exact
                  raw→canonical mapping from stage4_merge (map_to_canonical_with_fallback
                  + split_compound + emerging_real/emerging_unmapped taxonomy_match_method)
  * S5 verify:    check_mechanism_quality() + _check_enrichment_quality() + deberta_check()
                  + isor_score() → PASS/QUARANTINE + confidence_score
  * S6 commit:    insert_fb() (SQLite + FTS trigger)

Safety (C6 / C13):
  * DB backed up before the first write (shutil.copy2 → <db>.bak_<ts>).
  * Single transaction for the 6 INSERTs.
  * Idempotent: skips fb_ids already present in fbs (re-run = 0 inserts).
  * taxonomy_counts reconciled + recounted (same path as S6 post-commit).

Run:
    /opt/homebrew/bin/python3 scripts/reinject_bug198_singletons.py --dry-run
    /opt/homebrew/bin/python3 scripts/reinject_bug198_singletons.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    GEN_MODEL,
    S4_DEPTH_FOCUSED_CLASSIFICATION,
    S4_DEPTH_MAX_TOKENS,
    S4_TEMPORAL_SIGNALS,
    S5_CONF_ENRICH_WEIGHT,
    S5_CONF_ISOR_WEIGHT,
    S5_CONF_MECH_WEIGHT,
    S5_HUMAN_REVIEW_ISOR,
    S5_QUARANTINE_CONF_CAP,
    VERIFY_MODEL,
    VERIFY_REASONING_OFF_MODELS,
    VERIFY_REASONING_OFF_PREFIX,
)
from pipeline.omlx_call import call_omlx  # noqa: E402
from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    get_synonym_index,
    split_compound,
)
from pipeline.stage4_merge import (  # noqa: E402
    _collect_source_text,
    _derive_difficulty_level,
    _serialize_jargon,
    _temporal_signal_hit,
    map_to_canonical_with_fallback,
)
from pipeline.stage4_merged_call import (  # noqa: E402
    MERGED_CRIBS_CLASSIFY_SYSTEM,
    SparseClassificationError,
    _validate_semantic_classification,
    build_merged_prompt,
    classify_depth_focused,
)
from pipeline.intimacy_lattice import derive_context, resolve_intimacy  # noqa: E402
from pipeline.stamp import stamp_record  # noqa: E402
from pipeline.stage5_verify import (  # noqa: E402
    _check_enrichment_quality,
    _load_dual_encoders,
    check_mechanism_quality,
    deberta_check,
)
from pipeline.schema_accessor import isor_score  # noqa: E402
from pipeline.stage6_commit import init_db, insert_fb  # noqa: E402

RECOVERED = Path("knowledge pipeline/stage2_extract/t11/recovered_singletons.jsonl")
RUN_ID = "bug198_reinject"
VALID_DEPTHS = {"universal", "cross-domain", "domain", "specialized"}


def _clean_latex_json(text: str) -> str:
    """Repair LaTeX escapes that break strict JSON parsing (gpt-oss emits math).

    Backslash-paren/bracket sequences (LaTeX math delimiters) are invalid JSON
    escape sequences (D2408-adjacent model artifact). The intent is the bare bracket.
    """
    for a, b in ((r"\(", "("), (r"\)", ")"), (r"\[", "["), (r"\]", "]")):
        text = text.replace(a, b)
    return text


def _parse_model_json(raw: str) -> dict:
    """Parse a raw model response into a dict, tolerating LaTeX math escapes."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    cleaned = _clean_latex_json(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def _backup_db(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak_{stamp}")
    shutil.copy2(db_path, backup)
    return backup


def _classify_s4(fb_data: dict) -> dict:
    """Run the S4 classification (merged CRIBS + focused depth + canonical mapping).

    Returns the assembled S4 record (pre-S5, pre-stamp). Raises on sparse/failed
    classification so the caller records a FAILED record (fail-closed, C16).
    """
    synonym_index = get_synonym_index()

    # D2226 merged CRIBS+classification (gpt-oss-20b — R5 different family from S2 Qwen).
    # Called via call_omlx_json directly (NOT merged_cribs_classify) because that
    # wrapper fail-closes on `application` (D2371), but these 6 records already carry
    # a valid cross-family `application` (part 1 gemma backfill) — we must NOT let the
    # re-derived application gate the classification. Semantic fields are still
    # validated fail-closed via _validate_semantic_classification().
    system = MERGED_CRIBS_CLASSIFY_SYSTEM
    if VERIFY_MODEL in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"

    merged: dict = {}
    last_err: Exception | None = None
    import time as _time
    for attempt in range(6):
        try:
            raw = call_omlx(
                prompt=build_merged_prompt(fb_data),
                model=VERIFY_MODEL,
                system=system,
                max_tokens=1024,
                timeout=180,
            )
            merged = _parse_model_json(raw)
            # D2408: gpt-oss occasionally returns empty content (Harmony conflict);
            # an empty dict means the semantic fields are absent → treat as sparse.
            _validate_semantic_classification(merged, source="merged")
            last_err = None
            break
        except SparseClassificationError as e:
            last_err = e
            print(f"     ⚠️ merged semantic sparse (attempt {attempt + 1}): {e}")
        except Exception as e:
            last_err = e
            print(f"     ⚠️ merged call failed (attempt {attempt + 1}): {type(e).__name__}: {e}")
        _time.sleep(2.0)
    if last_err is not None:
        raise last_err

    # CRIBS fields from merged (application/elaboration are KEPT from the S2 record —
    # application was backfilled cross-family in part 1; do NOT re-derive it).
    failure_mode = merged.get("failure_mode") or ""
    keywords = merged.get("keywords") or ""
    jargon = merged.get("jargon")

    domains_raw = list(merged.get("domains") or [])
    discipline_raw_raw = merged.get("discipline") or ""
    if isinstance(discipline_raw_raw, list):
        discipline_raw_raw = discipline_raw_raw[0] if discipline_raw_raw else ""
    discipline_raw = str(discipline_raw_raw) if discipline_raw_raw else ""

    # ── Stage 2: raw → canonical (D2138) ──
    taxonomy_match_method: str | None = None
    if not discipline_raw or not discipline_raw.strip():
        canonical_discipline = "emerging"
        taxonomy_match_method = "emerging_unmapped"
    else:
        canonical_discipline = map_to_canonical_with_fallback(
            discipline_raw, "discipline", synonym_index, CANONICAL_DISCIPLINES
        )
        if canonical_discipline == "emerging":
            taxonomy_match_method = "emerging_real"
        elif canonical_discipline.lower() == discipline_raw.lower():
            taxonomy_match_method = "exact"
        else:
            taxonomy_match_method = "synonym"

    canonical_domains: list[str] = []
    seen_canonical: set[str] = set()
    for d in domains_raw:
        mapped = map_to_canonical_with_fallback(d, "domain", synonym_index, CANONICAL_DOMAINS)
        if mapped != "emerging":
            if mapped not in seen_canonical:
                seen_canonical.add(mapped)
                canonical_domains.append(mapped)
            continue
        parts = split_compound(d)
        decomposed_any = False
        if len(parts) > 1:
            for part in parts:
                pm = map_to_canonical_with_fallback(part, "domain", synonym_index, CANONICAL_DOMAINS)
                if pm != "emerging":
                    decomposed_any = True
                    if pm not in seen_canonical:
                        seen_canonical.add(pm)
                        canonical_domains.append(pm)
        if not decomposed_any:
            if "emerging" not in seen_canonical:
                seen_canonical.add("emerging")
                canonical_domains.append("emerging")
    if not canonical_domains:
        canonical_domains = ["emerging"]

    # ── Stage 3: depth (D2220 semantic; BUG-075 focused short prompt) ──
    if S4_DEPTH_FOCUSED_CLASSIFICATION:
        depth_val = classify_depth_focused(fb_data, model=VERIFY_MODEL, max_tokens=S4_DEPTH_MAX_TOKENS)
    else:
        raw_depth = merged.get("depth", "")
        depth_val = raw_depth if raw_depth in VALID_DEPTHS else "domain"

    evidence = merged.get("evidence") if merged.get("evidence") in ("cited", "axiomatic") else "cited"

    # ── Agentic metadata derivation (matches stage4_merge) ──
    name = (fb_data.get("name") or "").strip()
    definition = (fb_data.get("definition") or "").strip()
    n_domains = len(canonical_domains)
    difficulty_level = _derive_difficulty_level(depth_val, n_domains)

    def_text = (definition + " " + (fb_data.get("elaboration") or "")).lower()
    if _temporal_signal_hit(def_text, S4_TEMPORAL_SIGNALS.get("contemporary", [])):
        temporal_scope = "contemporary"
    elif _temporal_signal_hit(def_text, S4_TEMPORAL_SIGNALS.get("timeless", [])):
        temporal_scope = "timeless"
    else:
        temporal_scope = "timeless"

    context_val = derive_context({"domains": canonical_domains})

    prereqs = fb_data.get("prerequisite_fbs", [])
    if prereqs and isinstance(prereqs, list) and len(prereqs) > 0:
        accessibility_val = "prerequisite"
    elif difficulty_level == "expert" and len(definition) > 200:
        accessibility_val = "prerequisite"
    else:
        accessibility_val = "self-evident"

    intimacy_val, _rule = resolve_intimacy({
        "context": context_val,
        "discipline": canonical_discipline,
        "domains": canonical_domains,
        "discipline_raw": discipline_raw,
        "domains_raw": domains_raw,
    })

    source_text = _collect_source_text([fb_data])

    # D2488: failure_mode is REQUIRED for principles (min 10 chars). A short/empty
    # failure_mode → classification FAILED → S5 quarantines (skip NLI). Faithful to
    # the S4 gate (never silently flow a hollow principle into SQLite).
    fm_len = len(failure_mode.strip())
    classification_status = "CLEAN" if fm_len >= 10 else "FAILED"
    classification_error = None if fm_len >= 10 else f"failure_mode too short ({fm_len} chars < 10)"

    return {
        "fb_id": fb_data.get("fb_id"),
        "name": name,
        "definition": definition,
        "mechanism": (fb_data.get("mechanism") or "").strip(),
        "boundary": (fb_data.get("boundary") or "").strip(),
        "consequence": (fb_data.get("consequence") or "").strip(),
        "content_type": (fb_data.get("content_type") or "principle").strip(),
        "extraction_type": (fb_data.get("extraction_type") or "").strip(),
        "application": (fb_data.get("application") or "").strip(),
        "failure_mode": failure_mode.strip(),
        "elaboration": (fb_data.get("elaboration") or "").strip(),
        "keywords": keywords.strip(),
        "domains": canonical_domains,
        "discipline": canonical_discipline,
        "domains_raw": domains_raw,
        "discipline_raw": discipline_raw if discipline_raw else None,
        "depth": depth_val,
        "is_specialized": depth_val == "specialized",
        "evidence": evidence,
        "context": context_val,
        "accessibility": accessibility_val,
        "intimacy_boundary": intimacy_val,
        "provenance": "llm_extracted_from_source",
        "is_convergent": bool(fb_data.get("is_convergent", False)),
        "origin": "singleton",
        "difficulty_level": difficulty_level,
        "temporal_scope": temporal_scope,
        "prerequisite_fbs": fb_data.get("prerequisite_fbs", []),
        "procedural_skill": fb_data.get("procedural_skill"),
        "source_clusters": [fb_data.get("source_cluster") or ""],
        "source_books": sorted(fb_data.get("source_books", []) or []),
        "source_ids": sorted(fb_data.get("source_ids", []) or []),
        "citation": fb_data.get("citation"),
        "source_authors": fb_data.get("source_authors"),
        "source_diversity": fb_data.get("source_diversity"),
        "primary_source": fb_data.get("primary_source"),
        "source_principle_ids": [fb_data.get("fb_id")],
        "source_segments": list(fb_data.get("source_segments", []) or []),
        "evidence_passages": fb_data.get("evidence_passages", []) or [],
        "evidence_passages_shown": fb_data.get("evidence_passages_shown", []) or [],
        "source_text": source_text,
        "is_summary": bool(fb_data.get("is_summary", False)),
        "classification_errors": None,
        "usage_count": 0,
        "feedback_score": None,
        "feedback_count": 0,
        "fb_version": 1,
        "classification_status": classification_status,
        "classification_error": classification_error,
        "taxonomy_match_method": taxonomy_match_method,
        "jargon": _serialize_jargon(jargon),
    }


def _verify_s5(fb: dict) -> dict:
    """Run the S5 verification (mechanism + enrichment + DeBERTa NLI + ISOR).

    Mirrors the stage5_verify.py per-FB loop body exactly. Returns the verified FB.
    """
    results = []

    mech_passed, mech_score_float, mech_detail = check_mechanism_quality(fb)
    results.append({"check_name": "mechanism_quality", "passed": mech_passed, "score": mech_score_float, "detail": mech_detail})

    fact_passed: bool
    fact_score: float
    fact_detail: str
    method: str = "deberta-nli"

    if fb.get("classification_status") == "FAILED":
        fact_passed = False
        fact_score = 0.0
        fact_detail = f"S4 classification FAILED: {str(fb.get('classification_error', 'unknown'))[:120]}"
        method = "classification_failed"
    elif not mech_passed:
        fact_passed = False
        fact_score = 0.0
        fact_detail = f"MECH FAIL: {mech_detail}"
        method = "mech_quality"
    else:
        try:
            fact_passed, fact_score, fact_detail = deberta_check(fb)
            method = "deberta-nli"
        except Exception as e:
            fact_passed = False
            fact_score = 0.0
            fact_detail = f"Dual-encoder error — QUARANTINE: {e}"

    results.append({"check_name": "factual", "passed": fact_passed, "score": fact_score, "detail": fact_detail})

    enrich_passed, enrich_score, enrich_detail = _check_enrichment_quality(fb)
    if not enrich_passed:
        results.append({"check_name": "enrichment_quality", "passed": enrich_passed, "score": enrich_score, "detail": enrich_detail})

    status = "PASS" if fact_passed else "QUARANTINE"
    needs_human = False

    isor = isor_score(fb)
    isor_composite = float(isor.get("score", 0.0))

    confidence_score = round(
        S5_CONF_MECH_WEIGHT * mech_score_float
        + S5_CONF_ENRICH_WEIGHT * enrich_score
        + S5_CONF_ISOR_WEIGHT * isor_composite,
        4,
    )
    if not fact_passed:
        confidence_score = min(confidence_score, S5_QUARANTINE_CONF_CAP)
    if not fact_passed and isor.get("rating") == S5_HUMAN_REVIEW_ISOR:
        needs_human = True

    vfb = dict(fb)
    vfb["verification_results"] = results
    vfb["confidence_score"] = confidence_score
    vfb["status"] = status
    vfb["needs_human_review"] = needs_human
    vfb["verifier_model"] = "DeBERTa-v3-large (D2322 calibrated, threshold 0.10)"
    vfb["verification_method"] = method

    if isor["rating"] == "strong" and fact_passed:
        epistemic_status = "corroborated"
    elif isor["rating"] in ("strong", "medium") and not fact_passed:
        epistemic_status = "cross-source-unverified"
    elif fact_passed:
        epistemic_status = "source-supported"
    else:
        epistemic_status = "speculative"
    vfb["epistemic_status"] = epistemic_status
    vfb["isor"] = isor
    return vfb


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="classify+verify but do NOT write")
    ap.add_argument("--apply", action="store_true", help="classify + verify + commit (backs up DB first)")
    args = ap.parse_args()

    if not RECOVERED.exists():
        print(f"❌ recovered singletons not found: {RECOVERED}")
        return 1

    records = [json.loads(l) for l in RECOVERED.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"📦 {len(records)} recovered singleton(s) to re-inject")

    db = Path(DB_PATH)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    existing = {r["fb_id"] for r in conn.execute("SELECT fb_id FROM fbs").fetchall()}
    todo = [r for r in records if r["fb_id"] not in existing]
    skipped = len(records) - len(todo)
    if skipped:
        print(f"⏭️  {skipped} already committed — skipping (idempotent)")
    if not todo:
        conn.close()
        print("✅ nothing to do (all 6 already committed)")
        return 0

    print(f"🔍 Classifying + verifying {len(todo)} FB(s) via gpt-oss-20b (S4) + DeBERTa (S5)…")
    _load_dual_encoders()  # preload DeBERTa once

    verified = []
    for i, rec in enumerate(todo, 1):
        name = rec.get("name", "unnamed")[:40]
        print(f"  [{i}/{len(todo)}] {name}")
        s4 = _classify_s4(rec)
        s4 = stamp_record(s4, gen_model=GEN_MODEL, classify_model=VERIFY_MODEL)
        s4["pipeline_run_id"] = RUN_ID
        vfb = _verify_s5(s4)
        print(f"     → {vfb['status']} (depth={vfb['depth']}, discipline={vfb['discipline']}, "
              f"domains={vfb['domains']}, conf={vfb['confidence_score']})")
        verified.append(vfb)

    if args.dry_run:
        conn.close()
        print(f"🔍 --dry-run: classified+verified {len(verified)} FB(s); NO writes.")
        return 0

    # ── Apply: backup + single-transaction commit ──
    backup = _backup_db(db)
    print(f"💾 DB backed up → {backup.name}")

    committed = 0
    try:
        for vfb in verified:
            if insert_fb(conn, vfb):
                committed += 1
            else:
                print(f"  ❌ insert_fb failed for {vfb.get('fb_id', '?')[:16]}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ commit aborted: {e}")
        conn.close()
        return 1

    # Recount taxonomy_counts (same path as S6 post-commit)
    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    conn.close()

    print(f"\n✅ committed {committed}/{len(verified)} FB(s)")
    print(f"   fbs count now: {total} (expected 7867 → 7873)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
