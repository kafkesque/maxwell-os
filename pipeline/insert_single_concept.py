#!/usr/bin/env python3
"""insert_single_concept.py — governed single-concept extraction + insert (D-3130 closer).

WHY (forensic finding 2026-10-23): there is NO governed targeted extract path — stage2 has no
--source filter and stage6 is checkpoint-only. A MATCHed-but-omitted tier-B concept (D-3130)
needs a single FB inserted without re-running a whole cluster (cascade risk vs. the N existing
rows of that source). This is that path, scoped to ONE (source, concept) pair.

PIPELINE-NATIVE, so provenance stays honest (R14):
  generator  = Qwen3-Coder via pipeline.omlx_call.call_omlx  (temp 0.0, R7)
  verifier   = DeBERTa via pipeline.stage5_verify.deberta_check  (R5: different family)
  classifier = deterministic pipeline.schemas.match_to_canonical  (D-2898: no LLM promotion)
  insert     = pipeline.stage6_commit.insert_fb  (all fail-closed guards) + bge-m3 embed

FAIL-CLOSED everywhere (C16): no partial state. A missing dependency or a parse failure
aborts BEFORE any write. The insert is transactional (rollback on error). Backup via
pipeline/backup_guardian.sh is the caller's C13 duty (batch writes only; a single row is not).

usage: python3 pipeline/insert_single_concept.py --source-id <id> --name "<n>" \
         --source-text-file <verbatim-passage.txt> [--discipline <d>] [--domains d1,d2]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _connect(db: Path):
    import sqlite3

    return sqlite3.connect(db)


def dedup_present(db: Path, source_id: str, concept_key: str) -> bool:
    import sqlite3

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("select source_ids, concept_key from fbs").fetchall()
    finally:
        conn.close()
    from pipeline.dedup_identity import source_set

    for sids_json, ck in rows:
        if ck != concept_key:
            continue
        if source_id in source_set(sids_json):
            return True
    return False


_ONTOLOGY_KEYS: tuple[str, ...] = (
    "content_type", "extraction_type", "content_type_source", "extraction_type_source",
    "discipline_source", "depth", "evidence", "context", "accessibility", "intimacy_boundary",
    "difficulty_level", "temporal_scope", "origin",
)


def declared_ontology(cfg: dict, *, where: str = "config/pipeline_config.yaml#single_concept") -> dict[str, str]:
    """Read and VALIDATE the ontology this path declares for every record it writes (C12/C21).

    WHY (BUG-977, MEASURED 2026-10-23). This function used to be ten literal lines inside the record dict —
    `"content_type": "principle"`, `"depth": "domain"`, … — i.e. an ONTOLOGICAL CLAIM typed in code: a value
    that CAN be declared was hardcoded (C12), and a ROLE the tool has no warrant to compute was asserted
    (BUG-712's "asserted, never computed" shape, at a new site). The declaration now lives in
    config/pipeline_config.yaml#single_concept, and this reader refuses a block that is absent, partial, or
    outside a CLOSED vocabulary (D-3034: a declaration must resolve; C16: never silently default).

    NOT routed through stage4_merge._resolve_content_type on purpose: that router CORRECTS an S2 label it was
    given, and this path has no S2 label. Feeding it a synthetic one to launder a literal would recreate the
    drift it exists to prevent. The authorship of the declared label is therefore `deterministic` — the C29
    value for "a deterministic rule authored it, never an LLM" (D-2947/D-343) — and NEVER `human_verbatim`,
    because the tier-B ruling sheet (governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl) carries
    MATCH/NONE only: the owner ruled PRESENCE, not the ROLE (that would be a provenance lie, BUG-742).

    Args:
        cfg: the parsed pipeline config.
        where: the declaration's home, used in every refusal so the message names what is missing.

    Returns:
        The declared ontology, every value validated against its CLOSED home.

    Raises:
        SystemExit: on an absent/partial block, a non-ROLE content_type, or any undeclared value.
    """
    from typing import get_args

    from pipeline.content_types import EXTRACTION_TYPES, leaf_label_fault
    from pipeline.schemas import (
        ACCESSIBILITY_LITERAL,
        CONTEXT_LITERAL,
        DEPTH_LITERAL,
        DIFFICULTY_LITERAL,
        EVIDENCE_LITERAL,
        INTIMACY_LITERAL,
        PROVENANCE_LITERAL,
        TEMPORAL_LITERAL,
    )

    block = cfg.get("single_concept")
    if not isinstance(block, dict) or not block:
        raise SystemExit(
            f"FAIL-CLOSED: {where} is absent — this path's ontology must be DECLARED, never asserted "
            "in code (C12/D-3034)"
        )
    missing = [k for k in _ONTOLOGY_KEYS if not str(block.get(k) or "").strip()]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: {where} is missing {missing} (D-3034: a declaration must resolve)")

    ontology: dict[str, str] = {k: str(block[k]).strip() for k in _ONTOLOGY_KEYS}

    # The ROLE axis has its OWN admission rule (D-2965): a DISPOSITION is not a content_type (BUG-741).
    fault = leaf_label_fault(ontology["content_type"])
    if fault is not None:
        raise SystemExit(
            f"FAIL-CLOSED: {where}.content_type={ontology['content_type']!r} is not an admissible ROLE "
            f"[{fault}] (D-2965/BUG-741)"
        )

    provenance = frozenset(get_args(PROVENANCE_LITERAL))
    closed: dict[str, frozenset[str]] = {
        "extraction_type": EXTRACTION_TYPES,
        "depth": frozenset(get_args(DEPTH_LITERAL)),
        "evidence": frozenset(get_args(EVIDENCE_LITERAL)),
        "context": frozenset(get_args(CONTEXT_LITERAL)),
        "accessibility": frozenset(get_args(ACCESSIBILITY_LITERAL)),
        "intimacy_boundary": frozenset(get_args(INTIMACY_LITERAL)),
        "difficulty_level": frozenset(get_args(DIFFICULTY_LITERAL)),
        "temporal_scope": frozenset(get_args(TEMPORAL_LITERAL)),
        "content_type_source": provenance,
        "extraction_type_source": provenance,
        "discipline_source": provenance,
    }
    undeclared = {k: v for k, v in ontology.items() if k in closed and v not in closed[k]}
    if undeclared:
        raise SystemExit(
            f"FAIL-CLOSED: {where} carries undeclared value(s) {undeclared} — the homes are "
            "pipeline/content_types.py and pipeline/schemas.py (C12/C16)"
        )
    # `origin` is the one axis with no closed home (schemas declares it as a documented str), so it is
    # REQUIRED to be present above but not membership-checked here: minting a second vocabulary for it in
    # this file is exactly what C12 forbids. Declared as a gap, not silently skipped.
    return ontology


def apply_declared_ontology(fb: dict, ontology: dict[str, str], *, committed_at: str,
                            cfg_menu_hash: str | None = None) -> dict:
    """Stamp the declared ontology, every label's AUTHORSHIP, and the row's timestamps onto `fb`.

    WHY (BUG-977, MEASURED 2026-10-23). The one row this path wrote before this function existed carried
    content_type_source / discipline_source / extraction_type_source = '' and created_at = '' while the other
    7,640 rows carry all four. That is the BUG-742 class (a label present, its AUTHORSHIP absent) plus the
    blank time stamp check_store_columns reads as CONSTANT-OR-BLANK on a `value` column (B19 `value` role:
    must vary and be non-blank). Provenance-completeness is therefore BY CONSTRUCTION here, never the
    caller's memory.

    Args:
        fb: the record about to be verified and inserted (mutated in place).
        ontology: the validated declaration (see `declared_ontology`).
        committed_at: ISO-8601 UTC stamp for BOTH created_at and committed_at — on this path the extraction
            and the commit are the same act, and a blank created_at is a hole no rail can distinguish from
            "the producer forgot".

    Returns:
        The same `fb`, stamped.
    """
    fb.update(ontology)
    # D-279/BUG-978: the stamp quartet is ATOMIC (check_label_provenance refuses a partial one as a BROKEN STAMP),
    # and this path applies NO closed menu - so the store's declared absence sentinel is the TRUE value, read from
    # the declaration (C12), never typed here.
    fb["menu_hash"] = str(cfg_menu_hash or "").strip()
    if not fb["menu_hash"]:
        raise SystemExit("FAIL-CLOSED: config/pipeline_config.yaml#single_concept_menu_hash is absent — the D-279\n"
                         "quartet cannot be completed without it (D-3034)")
    fb["created_at"] = fb["committed_at"] = committed_at
    return fb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--source-text-file", required=True)
    ap.add_argument("--discipline", default=None)
    ap.add_argument("--domains", default="")
    ap.add_argument("--db", default="knowledge pipeline/maxwell.db")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import yaml

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    gen_model = cfg.get("models", {}).get("gen_model") or "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
    source_text = Path(args.source_text_file).read_text(encoding="utf-8").strip()
    if not source_text:
        raise SystemExit("FAIL-CLOSED: empty source text (D-3034: a ruling must resolve to real bytes)")

    from pipeline.dedup_identity import concept_key as mint_ck
    from pipeline.omlx_call import call_omlx
    from pipeline.schemas import match_domains_to_canonical, match_to_canonical
    from pipeline.serving_gate import derive_epistemic_status, derive_status
    from pipeline.stage5_verify import deberta_check
    from pipeline.stage6_commit import insert_embedding, insert_fb
    from pipeline.stamp import get_pipeline_commit, make_hash_id

    ck = mint_ck(args.name)
    if dedup_present(PROJECT_ROOT / args.db, args.source_id, ck):
        raise SystemExit(f"ALREADY PRESENT: ({args.source_id}, {ck}) — no insert needed (D-3034)")

    prompt = (
        "Extract ONE knowledge principle from the source passage below. "
        f"Concept name: {args.name!r}.\n"
        "Return ONLY a JSON object with keys: definition (1-2 sentences), application, "
        "failure_mode, elaboration, mechanism, boundary, consequence, discipline (one canonical "
        "label), domains (list of 1-5 labels). No prose, no markdown fences.\n\n"
        f"SOURCE PASSAGE:\n{source_text[:6000]}"
    )
    raw = call_omlx(prompt, model=gen_model, max_tokens=900)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").lstrip("json").strip()
    try:
        g = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL-CLOSED: generator returned unparseable JSON: {e}\n{raw[:400]!r}") from e

    def _req(k):
        v = g.get(k, "")
        if not v:
            raise SystemExit(f"FAIL-CLOSED: generator omitted required field {k!r} (D-3034)")
        return v

    definition = _req("definition")
    discipline_raw = args.discipline or str(g.get("discipline", ""))
    domains_raw = args.domains.split(",") if args.domains else [str(x) for x in g.get("domains", [])]
    discipline = match_to_canonical(discipline_raw, "discipline") or discipline_raw
    domains = match_domains_to_canonical(domains_raw)

    fb = {
        "fb_id": make_hash_id(args.name, definition),
        "name": args.name,
        "definition": definition,
        "application": g.get("application", ""),
        "failure_mode": g.get("failure_mode", ""),
        "elaboration": g.get("elaboration", ""),
        "mechanism": g.get("mechanism", ""),
        "boundary": g.get("boundary", ""),
        "consequence": g.get("consequence", ""),
        "discipline": discipline,
        "discipline_raw": discipline_raw,
        "domains": domains,
        "domains_raw": [str(x) for x in g.get("domains", [])],
        "provenance": "llm_extracted_from_source",
        "source_text": source_text,
        "evidence_passages": [source_text],
        "evidence_passages_shown": [source_text[:6000]],
        "source_ids": [args.source_id],
        "source_books": [],
        "is_summary": 0,
        "is_convergent": 0,
    }

    ontology = declared_ontology(cfg)
    apply_declared_ontology(fb, ontology, committed_at=datetime.now(UTC).isoformat(),
                            cfg_menu_hash=cfg.get("single_concept_menu_hash"))

    passed, score, detail = deberta_check(fb)
    verification_results = json.dumps([{"check_name": "factual", "passed": passed, "score": score, "detail": detail}])
    status, s5_reason = derive_status(verification_results)
    # BUG-978 hole 5 (D-2284/BUG-499): the label is CO-DERIVED from the SAME record that derives `status` -
    # S5 stamps it in stage5_verify.py:1268 and this path bypasses S5, so it must ask the ONE rule itself.
    # `isor` is absent by design here (no ISOR rating is computed for a single insert), and the derivation
    # FAILS CLOSED to the declared fallback rather than inventing a rating.
    fb["epistemic_status"] = derive_epistemic_status(passed, None)
    fb["verification_results"] = verification_results
    fb["verifier_model"] = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (threshold 0.5)"
    fb["confidence_score"] = round(float(score), 4)
    fb["status"] = status
    fb["s5_reason"] = s5_reason
    fb["verification_method"] = "deberta-nli"
    fb["gen_model"] = gen_model
    fb["schema_version"] = "1"
    fb["pipeline_commit"] = get_pipeline_commit()
    fb["needs_human_review"] = 1 if status == "QUARANTINE" else 0

    print(f"verify: passed={passed} score={score:.3f} status={status} reason={s5_reason} discipline={discipline} domains={domains}")
    if args.dry_run:
        print("DRY RUN — no write.")
        return 0

    conn = _connect(PROJECT_ROOT / args.db)
    try:
        from pipeline.sqlite_vec_loader import load_sqlite_vec

        load_sqlite_vec(conn)  # D-2915: vec0 must be loaded before insert_embedding
        ok = insert_fb(conn, fb)
        if not ok:
            raise SystemExit("FAIL-CLOSED: insert_fb refused the row (see ❌ lines above)")
        from pipeline.schema_accessor import fb_id

        rowid = conn.execute("select rowid from fbs where fb_id=?", (fb_id(fb),)).fetchone()
        if rowid is None:
            raise SystemExit("FAIL-CLOSED: row not found after insert (rollback)")
        insert_embedding(conn, rowid[0], fb["definition"])
        conn.commit()
        print(f"✓ inserted {fb_id(fb)} ({args.name!r}) — concept_key {ck}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
