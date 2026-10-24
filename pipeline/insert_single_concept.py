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


def _decode(cell):
    """Return a stored TEXT cell in the SHAPE it was written with (list/dict/str), else the raw string.

    The store keeps structured cells as JSON TEXT. Reproducing a cell must preserve its shape, or a new row
    differs from its siblings in a way no rail can distinguish from a defect (BUG-990).
    """
    if not isinstance(cell, str):
        return cell
    try:
        return json.loads(cell)
    except json.JSONDecodeError:
        return cell


def served_run(conn) -> str:
    """The `pipeline_run_id` the store SERVES — DERIVED from the store, refused when ambiguous (D-2881).

    WHY (BUG-990, MEASURED 2026-10-24). Retrieval is pinned to ONE run, and the single row this path had
    written (`f523504e…`) carried `pipeline_run_id = ''`: it is **1 of 7,635** rows in that state, so no
    serving predicate could ever reach it. An insert that cannot be served is not a record of anything, and
    the recall rail would have gone GREEN on a row the owner's own query could never return — the vacuous-pass
    class BUG-967 records. Deriving the run (rather than declaring a second home for it) means the path
    follows the store automatically; refusing on MORE THAN ONE run id means it never guesses which corpus
    an inserted row joins (D-3034).
    """
    rows = conn.execute(
        "select pipeline_run_id, count(*) n from fbs where status='PASS' and coalesce(pipeline_run_id,'')<>'' "
        "group by 1 order by n desc").fetchall()
    if not rows:
        raise SystemExit("FAIL-CLOSED: no PASS row carries a pipeline_run_id — the served run cannot be "
                         "derived, so an inserted row would be unreachable (BUG-990/C16)")
    if len(rows) > 1:
        raise SystemExit(f"FAIL-CLOSED: the store serves {len(rows)} run ids {[r[0] for r in rows]} — an "
                         "insert must not CHOOSE a corpus (D-3034)")
    return str(rows[0][0])


def source_provenance(conn, source_id: str) -> dict:
    """The book identity for `source_id`, READ from the store's own PASS rows for that source (never typed).

    WHY (BUG-990). The row this path had written carried `source_books = []`, `primary_source = NULL` and
    `citation = ''` while every other row of its source carries all three — **1 of 7,635** on each axis. A
    row with no book cannot be attributed, cannot be audited against the source, and scores 0 on the
    author axis of ISOR (`n_authors 0`), i.e. the provenance hole propagates into ranking.
    """
    rows = conn.execute(
        "select source_books, primary_source, citation from fbs where status='PASS' "
        "and source_ids like ? and coalesce(citation,'')<>'' limit 1", (f"%{source_id}%",)).fetchall()
    if not rows:
        raise SystemExit(f"FAIL-CLOSED: no PASS row for source {source_id} — its book identity cannot be "
                         "derived, and a guessed one is a fabricated provenance (D-3034)")
    books, primary, citation = rows[0]
    decoded = {"source_books": _decode(books), "primary_source": _decode(primary), "citation": citation}
    blank = [k for k, v in decoded.items()
             if v in (None, "", [], {}) or (isinstance(v, str) and not v.strip())]
    if blank:
        raise SystemExit(f"FAIL-CLOSED: source {source_id} carries a blank {blank} in the store — copying "
                         "it forward would mint the same hole (BUG-990)")
    return decoded


_IDENTITY_AXES: tuple[str, ...] = ("pipeline_run_id", "source_books", "primary_source", "citation", "gen_model")


def identity_gaps(fb: dict) -> list[str]:
    """The identity axes a record MUST carry before it may be written (empty list = admissible).

    WHY (BUG-990). Six axes made the one row this path wrote a 1-of-7,635 singleton; five of them are
    checkable here without a DB, so the check runs on the DICT (before any write) and names every gap at
    once instead of failing one at a time.
    """
    gaps: list[str] = []
    for axis in _IDENTITY_AXES:
        v = fb.get(axis)
        if v in (None, "", [], {}) or (isinstance(v, str) and not v.strip()):
            gaps.append(axis)
    if not str(fb.get("taxonomy_version") or "").strip():
        gaps.append("taxonomy_version")
    return gaps


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


def selftest() -> int:
    """Known-answer controls for the identity gate (BUG-990): no store, no model, no write."""
    checks: list[tuple[str, bool]] = []
    good = {"pipeline_run_id": "run-x", "source_books": ["b.md"], "primary_source": {"book": "b.md"},
            "citation": "Author (Book)", "gen_model": "m", "taxonomy_version": "v9"}
    checks.append(("a fully identified record has NO gap", identity_gaps(good) == []))
    holes = dict(good, pipeline_run_id="", source_books=[])
    checks.append(("a blank run id and an empty book list are BOTH named at once",
                   identity_gaps(holes) == ["pipeline_run_id", "source_books"]))
    checks.append(("a whitespace-only citation is a hole, not a value",
                   identity_gaps(dict(good, citation="  ")) == ["citation"]))
    checks.append(("a missing taxonomy_version is a hole",
                   identity_gaps(dict(good, taxonomy_version="")) == ["taxonomy_version"]))
    checks.append(("_decode restores a stored list", _decode('["a","b"]') == ["a", "b"]))
    checks.append(("_decode restores a bare string", _decode("plain text") == "plain text"))
    import sqlite3

    amb = sqlite3.connect(":memory:")
    amb.execute("create table fbs (status text, pipeline_run_id text)")
    amb.executemany("insert into fbs values ('PASS', 'r1'), ('PASS', 'r1'), ('PASS', 'r2')", [])
    try:
        served_run(amb)
        checks.append(("two served run ids REFUSE the insert", False))
    except SystemExit:
        checks.append(("two served run ids REFUSE the insert", True))
    one = sqlite3.connect(":memory:")
    one.execute("create table fbs (status text, pipeline_run_id text)")
    one.execute("insert into fbs values ('PASS', 'r1')")
    checks.append(("one served run id is DERIVED", served_run(one) == "r1"))
    bad = 0
    for label, ok in checks:
        print(("  ✓ " if ok else "  ✗ ") + label)
        bad += 0 if ok else 1
    if bad:
        print(f"FAIL: {bad} control(s) failed")
        return 1
    print(f"✅ insert_single_concept selftest passed: {len(checks)} controls")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    # NOT argparse-required: --selftest must reach the controls without the three production arguments
    # (argparse refuses first, which made the control unreachable — the BUG-445 shape: a control that can
    # never RUN is not a control). They are enforced immediately after the selftest branch instead.
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--source-text-file", default=None)
    ap.add_argument("--discipline", default=None)
    ap.add_argument("--domains", default="")
    ap.add_argument("--db", default="knowledge pipeline/maxwell.db")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    import yaml

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    # C12c (BUG-990): the generator identity was read with a CODE default here while
    # config/pipeline_config.yaml#models.gen_model was None — so the R14 stamp on the row named a model the
    # declaration never mentioned. A stamp whose value has two homes is not a stamp.
    # ONE HOME (C12): the declared generator identity is models.generator.model — the value this path used to
    # supply from a literal had no home at all in this file's reader, so the stamp and the declaration could
    # disagree silently.
    gen_model = str(((cfg.get("models") or {}).get("generator") or {}).get("model") or "").strip()
    if not gen_model:
        raise SystemExit("FAIL-CLOSED: config/pipeline_config.yaml#models.generator.model is absent — the "
                         "generator identity may not come from a code default (C12c/R14)")
    for flag, val in (("--source-id", args.source_id), ("--name", args.name),
                      ("--source-text-file", args.source_text_file)):
        if not str(val or "").strip():
            raise SystemExit(f"FAIL-CLOSED: {flag} is required (pass --selftest for the controls)")
    source_text = Path(args.source_text_file).read_text(encoding="utf-8").strip()
    if not source_text:
        raise SystemExit("FAIL-CLOSED: empty source text (D-3034: a ruling must resolve to real bytes)")

    from pipeline.dedup_identity import concept_key as mint_ck
    from pipeline.omlx_call import call_omlx
    from pipeline.schemas import match_domains_to_canonical, match_to_canonical
    from pipeline.stage6_commit import insert_embedding, insert_fb
    from pipeline.stamp import get_pipeline_commit, make_hash_id, SCHEMA_VERSION

    ck = mint_ck(args.name)
    if dedup_present(PROJECT_ROOT / args.db, args.source_id, ck):
        raise SystemExit(f"ALREADY PRESENT: ({args.source_id}, {ck}) — no insert needed (D-3034)")

    # BUG-990: derive the three identity axes the one row this path had written did NOT carry. Each is READ from
    # the store (measured), never declared in a second home, and each REFUSES rather than guessing.
    conn = _connect(PROJECT_ROOT / args.db)
    try:
        run_id = served_run(conn)
        provenance = source_provenance(conn, args.source_id)
        tax = conn.execute(
            "select taxonomy_version, count(*) n from fbs where status='PASS' and source_ids like ? "
            "and coalesce(taxonomy_version,'')<>'' group by 1 order by n desc limit 1",
            (f"%{args.source_id}%",)).fetchall()
        if not tax:
            raise SystemExit(f"FAIL-CLOSED: source {args.source_id} carries no taxonomy_version — the inserted "
                             "row would be the store's only blank on that axis (BUG-990)")
        taxonomy_version = str(tax[0][0])
    finally:
        conn.close()

    # D-3140 (T-197/BUG-991): the single-concept prompt was a DRIFTED SECOND HOME for the extraction
    # contract (the D-3136 shape) — it named `mechanism` with no register/length guidance, so the generator
    # returned a sub-floor one-liner and S5 quarantined it downstream (BUG-991). The floor and the register
    # are read from their ONE homes (stage5.mechanism_min_length via the verifier's own constant, and
    # single_concept.extraction_type), never typed here (C12c).
    from pipeline.stage5_verify import MECHANISM_MIN_LENGTH, mechanism_floor_check

    mech_min = MECHANISM_MIN_LENGTH
    sc = cfg.get("single_concept") or {}
    extraction_type = str(sc.get("extraction_type") or "")
    if not extraction_type:
        raise SystemExit("FAIL-CLOSED: config/pipeline_config.yaml#single_concept.extraction_type is absent (C12)")
    prompt = (
        "Extract ONE knowledge principle from the source passage below. "
        f"Concept name: {args.name!r}.\n"
        "Return ONLY a JSON object with keys: definition (1-2 sentences), application, "
        "failure_mode, elaboration, mechanism, boundary, consequence, discipline (one canonical "
        "label), domains (list of 1-5 labels). No prose, no markdown fences.\n\n"
        "MECHANISM (the field that carries HOW the concept works — a causal/associative chain, never a "
        f"restatement of the definition): write 2-3 full sentences, at least {mech_min} characters, in the "
        f"declared epistemic register {extraction_type!r}. A mechanism shorter than {mech_min} characters, "
        "or one that merely restates the definition, is rejected and the whole extraction is discarded.\n\n"
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
        "source_books": provenance["source_books"],
        "primary_source": provenance["primary_source"],
        "citation": provenance["citation"],
        "pipeline_run_id": run_id,
        "taxonomy_version": taxonomy_version,
        "gen_model": gen_model,
        "is_summary": 0,
        "is_convergent": 0,
    }

    # BUG-990: the identity gate runs on the DICT, before verify and before any write, and names EVERY gap at
    # once. Six axes made the one row this path had written a 1-of-7,635 singleton in the store.
    gaps = identity_gaps(fb)
    if gaps:
        raise SystemExit(f"FAIL-CLOSED: the record is missing identity axis/axes {gaps} — writing it would mint "
                         "a row no serving predicate can reach or no audit can attribute (BUG-990)")

    ontology = declared_ontology(cfg)
    apply_declared_ontology(fb, ontology, committed_at=datetime.now(UTC).isoformat(),
                            cfg_menu_hash=cfg.get("single_concept_menu_hash"))

    # D-3140 (T-197/BUG-991): enforce the mechanism floor AT THE GENERATOR, reusing the ONE HOME
    # (check_mechanism_quality) instead of letting S5 quarantine an unservable row downstream. One targeted
    # retry — temp=0.0, so a sterner prompt is a DIFFERENT input, not a re-roll of the same answer.
    ok_mech, mech_detail = mechanism_floor_check(fb)
    if not ok_mech:
        repair_prompt = (
            "Your mechanism for this concept was rejected by the quality gate:\n"
            f"{mech_detail}\n\n"
            "Rewrite ONLY the mechanism field as a JSON object {\"mechanism\": \"...\"} of at least "
            f"{mech_min} characters, as a complete causal/associative chain in the {extraction_type!r} register, "
            "never a restatement of the definition.\n\n"
            f"SOURCE PASSAGE:\n{source_text[:6000]}"
        )
        repair_raw = call_omlx(repair_prompt, model=gen_model, max_tokens=500).strip()
        if repair_raw.startswith("```"):
            repair_raw = repair_raw.strip("`").lstrip("json").strip()
        try:
            repaired_mech = str(json.loads(repair_raw).get("mechanism", "") or "").strip()
        except json.JSONDecodeError:
            repaired_mech = ""
        if repaired_mech:
            fb["mechanism"] = repaired_mech
        ok_mech, mech_detail = mechanism_floor_check(fb)
        if not ok_mech:
            raise SystemExit(
                f"FAIL-CLOSED: generator mechanism still rejected after one retry — {mech_detail}. "
                "Refusing to write an unservable row (BUG-967/D-3140)"
            )

    # T-196/D-3136 (MEASURED 2026-10-23): this path used to RESTATE S5's per-record sequence, and the copy had
    # drifted: no ISOR at all (the store's only blank `isor` cell), a label derived from `None`, and a hardcoded
    # verifier identity. The sequence now has ONE home, and a writer asks it rather than remembering it.
    from pipeline.verify_record import verify_one_record

    outcome = verify_one_record(fb)
    # `checkpoint_cells()` is the NATIVE face (list/dict/bool); insert_fb serialises it into the store's TEXT
    # columns itself (pipeline/stage6_commit.py::_safe_json), so the writer never re-types a cell.
    fb.update(outcome.checkpoint_cells())
    fb["schema_version"] = SCHEMA_VERSION  # R14/C12: read the declared '3.0' (ONE home), never a code literal "1"
    fb["pipeline_commit"] = get_pipeline_commit()

    print(f"verify: passed={outcome.fact_passed} score={outcome.fact_score:.3f} status={outcome.status} "
          f"reason={outcome.s5_reason} method={outcome.verification_method} discipline={discipline} domains={domains}")
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
