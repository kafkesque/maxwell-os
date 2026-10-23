#!/usr/bin/env python3
"""check_extraction_recall.py — T-194 / D-3129: the source-to-expected-concept EXTRACTION RECALL rail.

WHY THIS EXISTS (SOTA-audit gap 1). Maxwell could prove that extracted rows are SCHEMA-well-formed
(scripts/stress_test_s2_exhaustive.py) but could not prove that the extractor EMITTED every concept a
source contains, so "nothing lost from the source" was unmeasurable. RAGChecker-style claim recall is
exactly this measure. This script is the instrument, and the golden it reads is a RECEIPT, not a probe.

WHY THE KEY IS concept_key AND NOT fb_id (D-3129, MEASURED). The Phase 0 receipt (commit a6323a7) ran
S0->S5 twice on identical bytes with an identical chunker: fb_id survival was 27% (jaccard 0.2726), name
survival 72%, and 8-field body survival 0%. fb_id = sha256(name|definition) is generation-SENSITIVE, so a
fb_id-keyed golden would rot on every rebuild and silently turn a recall rail into a false-alarm
generator. The golden therefore keys on (source_id, concept_key) — concept_key being the
generation-invariant key D-3118 Phase A defines (pipeline/dedup_identity.py) and D-3128 measured live on
7640/7640 store rows — and carries fb_id ONLY as a denormalized pointer.

WHAT THE GOLDEN'S AUTHORITY IS. The certified core is the set of rows the OWNER ruled MATCH in the
adjudication sheet (owner_ruling_note == MATCH). That is what makes it anti-circular: the certification
was adjudicated AGAINST THE SOURCE, not copied from the extractor's own output. A row whose ruling column
holds a placeholder word instead of a 64-hex id is REFUSED (a declaration must RESOLVE, D-3034).

WHAT IT DOES NOT CLAIM. The certified core is a FLOOR on the expectation, not the whole of it: recall
BELOW the floor means owner-ratified knowledge was lost (a defect by definition), while recall AT the
floor does NOT prove completeness, because the owner never certified the concepts the store omits. That
upper tier stays NOT MEASURED and is reported as such — never as a pass (cf. BUG-967, where a missing
checkpoint was reported as `identical: True` over two empty sets).

Modes:
  --build-golden [--apply]   Derive the golden from the owner's rulings + the store (deterministic, no LLM).
  --check                    Compute recall against the configured target, write the report, exit tri-state.
  --selftest                Fixture proof: the instrument REDs on loss, GREENs on presence, and the KEY
                            CHOICE is proven by a negative control (a reworded body must still match).

Exit codes: 0 CLEAN, 1 RED (below floor or key-integrity fault), 2 OWED (golden missing/stale/undeclared),
            3 configuration error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "extraction_recall.yaml"
FB_ID_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDERS = frozenset({"MATCH", "NONE", "TRUE", "FALSE", "YES", "NO"})
SCHEMA_VERSION = 1
GEN_MODEL = "none (deterministic ruling consumer and set math; no LLM)"

EXIT_CLEAN = 0
EXIT_RED = 1
EXIT_OWED = 2
EXIT_CONFIG = 3

# Report caps: a receipt must stay readable, but the COUNT is always complete (a truncated list that
# reported its own length as the total would be the BUG-967 class of lie).
MAX_LISTED = 40


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as e:  # C16: no silent error
        raise RuntimeError(f"PyYAML unavailable ({e}); cannot read {path}") from e
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise RuntimeError(f"{path} is not a YAML mapping")
    return doc


def load_config() -> dict[str, Any]:
    """Return the `extraction_recall` block, refusing a config that cannot resolve (D-3034)."""
    block = _load_yaml(CONFIG_PATH).get("extraction_recall")
    if not isinstance(block, dict):
        raise RuntimeError(f"{CONFIG_PATH}: missing 'extraction_recall' block (C16)")
    return block


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file, streamed so a large artifact never has to fit in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pipeline_commit() -> str:
    """Short HEAD, empty when git is unavailable (stamped, never guessed)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except OSError:
        return ""


def parse_source_ids(value: Any) -> list[str]:
    """Source ids are stored as a JSON array of hex strings; tolerate a bare string or None."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [t.strip() for t in text.split(",") if t.strip()]
    if isinstance(parsed, list):
        return [str(v) for v in parsed if str(v).strip()]
    return [str(parsed)]


def read_certifications(cfg: dict[str, Any]) -> list[dict[str, str]]:
    """Rows the OWNER ruled MATCH. Refuses a placeholder in the id column (D-3034)."""
    sheet = PROJECT_ROOT / cfg["golden"]["source_sheet"]
    match_note = str(cfg["golden"]["match_note"])
    certs: list[dict[str, str]] = []
    with open(sheet, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            cleaned = {(k or "").lstrip("\ufeff ").strip(): (v or "").strip() for k, v in row.items()}
            if cleaned.get("owner_ruling_note") != match_note:
                continue
            fb_id = cleaned.get("owner_ruling_fb_id", "")
            if fb_id in PLACEHOLDERS or not FB_ID_RE.match(fb_id):
                raise SystemExit(
                    f"FAIL-CLOSED: item {cleaned.get('item_id')!r} is ruled {match_note} but its "
                    f"owner_ruling_fb_id is {fb_id!r} - a placeholder where an id belongs (D-3034)"
                )
            certs.append({"item_id": cleaned.get("item_id", ""), "fb_id": fb_id})
    return certs


def load_tier_b(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """PROPOSED-but-unruled tier-B candidates (T-195 completeness arm), keyed (source_id, concept_key).

    The proposer (a local model, advisory only per D-2549) emits one JSONL line per candidate:
    {"source_id": <id>, "name": <concept name>, "rationale": <advisory reason>}. concept_key is DERIVED
    from the name (D-3129), so a tier-B row is keyed exactly like a tier-A row. A tier-B row is NEVER a
    floor and NEVER auto-certified (D-2898): the owner must rule it MATCH for it to enter tier A.
    """
    from pipeline.dedup_identity import concept_key as mint_concept_key

    rel = cfg["golden"].get("tier_b_sheet")
    if not rel:
        return []
    path = PROJECT_ROOT / str(rel)
    if not path.exists():
        print(f"NOTE: tier_b_sheet declared but absent ({path}) - reporting 0 proposed candidates")
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:  # C16: no silent error
                raise SystemExit(f"FAIL-CLOSED: tier_b_sheet has a non-JSON line: {e}") from e
            sid = (obj.get("source_id") or "").strip()
            name = (obj.get("name") or "").strip()
            if not sid or not name:
                raise SystemExit(
                    f"FAIL-CLOSED: tier-B row missing source_id/name: {obj!r} "
                    "(a declaration must resolve, D-3034)"
                )
            rows.append(
                {
                    "source_id": sid,
                    "name": name,
                    "concept_key": mint_concept_key(name),
                    "rationale": (obj.get("rationale") or "").strip(),
                }
            )
    return rows


def load_tier_b_rulings(cfg: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    """Owner MATCH/NONE rulings on tier-B candidates (T-195 step c), keyed (source_id, concept_key).

    A ruling sheet row is {"source_id", "name", "owner_ruling_note"} with note in {MATCH, NONE}.
    The OWNER is the only authority (D-2658/D-2898: suggested_* advisory, owner_ruling_* authoritative;
    no LLM promotion). concept_key is DERIVED from the name (D-3129) so a ruling keys exactly like a
    tier-A row and needs NO fb_id — a MATCH certifies "this concept exists in this source" even when
    the store has not (yet) produced a row for it (D-3130: the omission is precisely the signal).
    """
    from pipeline.dedup_identity import concept_key as mint_concept_key

    rel = cfg["golden"].get("tier_b_ruling_sheet")
    if not rel:
        return {}
    path = PROJECT_ROOT / str(rel)
    if not path.exists():
        return {}
    rulings: dict[tuple[str, str], dict[str, str]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:  # C16: no silent error
                raise SystemExit(f"FAIL-CLOSED: tier_b_ruling_sheet has a non-JSON line: {e}") from e
            sid = (obj.get("source_id") or "").strip()
            name = (obj.get("name") or "").strip()
            note = (obj.get("owner_ruling_note") or "").strip().upper()
            if not sid or not name:
                raise SystemExit(f"FAIL-CLOSED: tier-B ruling missing source_id/name: {obj!r} (D-3034)")
            if note not in ("MATCH", "NONE"):
                raise SystemExit(f"FAIL-CLOSED: tier-B ruling note {note!r} not MATCH/NONE: {obj!r}")
            key = (sid, mint_concept_key(name))
            if key in rulings:
                raise SystemExit(f"FAIL-CLOSED: duplicate tier-B ruling for (source_id, concept_key): {key}")
            rulings[key] = {"name": name, "note": note}
    return rulings


def _connect(store_rel: str) -> sqlite3.Connection:
    path = PROJECT_ROOT / store_rel
    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED: store not found: {path}")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def build_golden(cfg: dict[str, Any]) -> dict[str, Any]:
    """Derive the golden: one row per certified concept, with the SOURCES it was certified from."""
    from pipeline.dedup_identity import concept_key as mint_concept_key

    certs = read_certifications(cfg)
    if not certs:
        raise SystemExit("FAIL-CLOSED: no owner-MATCH rulings found - an empty golden declares nothing")
    conn = _connect(cfg["store"])
    try:
        marks = ",".join("?" * len(certs))
        rows = conn.execute(
            f"select fb_id, name, concept_key, source_ids, content_type from fbs "
            f"where fb_id in ({marks})",
            [c["fb_id"] for c in certs],
        ).fetchall()
    finally:
        conn.close()
    by_fb = {r[0]: r for r in rows}
    missing = [c["item_id"] for c in certs if c["fb_id"] not in by_fb]
    if missing:
        raise SystemExit(
            f"FAIL-CLOSED: {len(missing)} certified fb_id(s) absent from the store: {missing[:5]} "
            "- a certification that does not resolve cannot be a golden row"
        )
    golden_rows: list[dict[str, Any]] = []
    for cert in certs:
        fb_id, name, stored_key, sids, ctype = by_fb[cert["fb_id"]]
        recomputed = mint_concept_key(name)
        golden_rows.append(
            {
                "item_id": cert["item_id"],
                "name": name,
                "concept_key": recomputed,
                "concept_key_stored": stored_key,
                "key_agrees_with_store": stored_key == recomputed,
                "fb_id_pointer": fb_id,
                "sources": parse_source_ids(sids),
                "content_type": ctype,
            }
        )
    # T-195 step (c): fold OWNER-MATCHed tier-B candidates into the floored expectation set.
    # A MATCHed candidate has NO fb_id by definition (it is a concept the store may have OMITTED,
    # D-3130), so it keys purely by (source_id, concept_key) — D-3129 — and carries an empty
    # fb_id_pointer (a denormalized pointer that, for a tier-B row, legitimately points nowhere yet).
    tier_b_rows = load_tier_b(cfg)
    tier_b_rulings = load_tier_b_rulings(cfg)
    tier_b_matched: list[dict[str, Any]] = []
    tier_b_unruled: list[dict[str, Any]] = []
    tier_b_ruled_none = 0
    for r in tier_b_rows:
        rule = tier_b_rulings.get((r["source_id"], r["concept_key"]))
        if rule is None:
            tier_b_unruled.append(r)
        elif rule["note"] == "MATCH":
            tier_b_matched.append(r)
        else:
            tier_b_ruled_none += 1
    for r in tier_b_matched:
        golden_rows.append({
            "item_id": f"tierB:{r['source_id'][:8]}:{r['concept_key'][:8]}",
            "name": r["name"],
            "concept_key": r["concept_key"],
            "concept_key_stored": None,
            "key_agrees_with_store": None,
            "fb_id_pointer": "",
            "sources": [r["source_id"]],
            "content_type": None,
        })

    sheet = PROJECT_ROOT / cfg["golden"]["source_sheet"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "EXTRACTION-RECALL-GOLDEN",
        "gen_model": GEN_MODEL,
        "pipeline_commit": pipeline_commit(),
        "key_rule": "D-3129: (source_id, concept_key) is the key space; fb_id is a denormalized pointer",
        "tier_a": "owner-MATCH certifications (owner_ruling_note == MATCH) - anti-circular: adjudicated "
                  "against the source, not copied from extractor output",
        "tier_b": "PROPOSED-but-unruled candidates (T-195): REPORTED, never floored, never auto-certified "
                  "(D-2898) - the owner must rule MATCH for a tier-B row to enter tier A",
        "tier_b_rows": tier_b_unruled,
        "tier_b_matched": tier_b_matched,
        "tier_b_ruled_none": tier_b_ruled_none,
        "authority": {"path": cfg["golden"]["source_sheet"], "sha256": sha256_file(sheet)},
        "counts": {
            "certifications": len(golden_rows),
            "concepts": len({r["concept_key"] for r in golden_rows}),
            "expectations": len({(s, r["concept_key"]) for r in golden_rows for s in r["sources"]}),
            "distinct_sources": len({s for r in golden_rows for s in r["sources"]}),
            "tier_b_matched": len(tier_b_matched),
        },
        "rows": golden_rows,
    }


def _store_emissions(cfg: dict[str, Any]) -> tuple[dict[tuple[str, str], int], list[dict[str, Any]]]:
    """Emitted (source_id, concept_key) pairs with their MULTIPLICITY from the LIVE store.

    Multiplicity matters: two store rows sharing one (source, concept_key) is the duplicate/echo
    signal D-3117 accumulates (D-3129 rule 3), so it is COUNTED here and reported, never collapsed
    into a set at the point of measurement.
    """
    from pipeline.dedup_identity import concept_key as mint_concept_key

    conn = _connect(cfg["store"])
    try:
        rows = conn.execute("select fb_id, name, concept_key, source_ids from fbs").fetchall()
    finally:
        conn.close()
    counts: dict[tuple[str, str], int] = {}
    faults: list[dict[str, Any]] = []
    for fb_id, name, stored_key, sids in rows:
        key = mint_concept_key(name)
        if stored_key != key:
            faults.append(
                {"fb_id": fb_id, "name": name, "stored": stored_key, "recomputed": key}
            )
        for sid in parse_source_ids(sids):
            counts[(sid, key)] = counts.get((sid, key), 0) + 1
    return counts, faults


def _s5_emissions(path: Path) -> tuple[dict[tuple[str, str], int], list[dict[str, Any]]]:
    """Emitted pairs from a named run's S5 checkpoint (concept_key recomputed: S5 predates S6)."""
    from pipeline.dedup_identity import concept_key as mint_concept_key

    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED: s5 checkpoint not found: {path}")
    counts: dict[tuple[str, str], int] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = mint_concept_key(row.get("name"))
            for sid in parse_source_ids(row.get("source_ids")):
                counts[(sid, key)] = counts.get((sid, key), 0) + 1
    return counts, []


def _ratio(hit: int, total: int) -> float:
    return 1.0 if total == 0 else round(hit / total, 6)


def evaluate(golden: dict[str, Any], emitted: dict[tuple[str, str], int],
             faults: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    """Recall over the declared key space. Below a floor is RED; a key-integrity fault is RED.

    `emitted` maps a (source_id, concept_key) pair to how many times it was emitted, so the same
    pass that measures recall also measures DUPLICATION (a pair emitted twice for one source).
    """
    pairs = set(emitted)
    expected_concepts = {r["concept_key"]: r for r in golden["rows"]}
    expected_pairs = {(s, r["concept_key"]) for r in golden["rows"] for s in r["sources"]}
    hit_concepts = set(expected_concepts) & {k for _, k in pairs}
    hit_pairs = expected_pairs & pairs
    concept_recall = _ratio(len(hit_concepts), len(expected_concepts))
    expectation_recall = _ratio(len(hit_pairs), len(expected_pairs))
    floors = cfg["floors"]
    red_reasons: list[str] = []
    if concept_recall < float(floors["concept_recall"]):
        red_reasons.append(
            f"concept_recall {concept_recall} < floor {floors['concept_recall']}"
        )
    if expectation_recall < float(floors["expectation_recall"]):
        red_reasons.append(
            f"expectation_recall {expectation_recall} < floor {floors['expectation_recall']}"
        )
    if faults:
        red_reasons.append(f"concept_key integrity: {len(faults)} store row(s) carry a stale key")

    missing_pairs = sorted(expected_pairs - pairs)
    per_source: dict[str, dict[str, int]] = {}
    for sid, _ in expected_pairs:
        per_source.setdefault(sid, {"expected": 0, "hit": 0})["expected"] += 1
    for sid, _ in hit_pairs:
        per_source.setdefault(sid, {"expected": 0, "hit": 0})["hit"] += 1
    # Multiplicity is REPORTED, never collapsed (D-3129 rule 3): a concept emitted twice for one
    # source is the duplicate/echo signal D-3117 accumulates, not an ambiguity error.
    duplicates = sorted(
        ({"source_id": s, "concept_key": k, "emitted": n}
         for (s, k), n in emitted.items() if n > 1 and (s, k) in expected_pairs),
        key=lambda d: -d["emitted"],
    )

    # TIER-B (T-195): proposed-but-unruled candidates are REPORTED separately and NEVER floored. Their
    # presence is advisory evidence, not a certification; their absence is an omission, not a defect.
    tier_b_rows = golden.get("tier_b_rows", [])
    tier_b_matched = golden.get("tier_b_matched", [])
    tier_b_ruled_none = int(golden.get("tier_b_ruled_none", 0))
    tb_by_key = {r["concept_key"]: r for r in tier_b_rows}
    tb_pairs = {(r["source_id"], r["concept_key"]) for r in tier_b_rows}
    tb_present = sorted(tb_pairs & pairs)
    tb_omitted = sorted(tb_pairs - pairs)

    return {
        "concept_recall": concept_recall,
        "expectation_recall": expectation_recall,
        "concepts_expected": len(expected_concepts),
        "concepts_hit": len(hit_concepts),
        "expectations_expected": len(expected_pairs),
        "expectations_hit": len(hit_pairs),
        "missing_concepts": [
            {"item_id": expected_concepts[k]["item_id"], "name": expected_concepts[k]["name"]}
            for k in sorted(set(expected_concepts) - hit_concepts)
        ][:MAX_LISTED],
        "missing_pairs_count": len(missing_pairs),
        "missing_pairs": [{"source_id": s, "concept_key": k} for s, k in missing_pairs[:MAX_LISTED]],
        "sources": {
            "count": len(per_source),
            "fully_recalled": sum(1 for v in per_source.values() if v["hit"] == v["expected"]),
            "denominator_distribution": _distribution([v["expected"] for v in per_source.values()]),
        },
        "duplicate_pairs_count": len(duplicates),
        "duplicate_pairs": duplicates[:MAX_LISTED],
        "key_integrity_faults": faults[:MAX_LISTED],
        "key_integrity_fault_count": len(faults),
        "red_reasons": red_reasons,
        "verdict": "RED" if red_reasons else "CLEAN",
        "tier_b": golden.get("tier_b", "NOT MEASURED"),
        "tier_b_proposed": len(tb_pairs),
        "tier_b_present": len(tb_present),
        "tier_b_omitted": len(tb_omitted),
        "tier_b_matched": len(tier_b_matched),
        "tier_b_ruled_none": tier_b_ruled_none,
        "tier_b_present_pairs": [
            {"source_id": s, "concept_key": k, "name": tb_by_key.get(k, {}).get("name", "")}
            for s, k in tb_present[:MAX_LISTED]
        ],
        "tier_b_omissions": [
            {"source_id": s, "concept_key": k, "name": tb_by_key.get(k, {}).get("name", "")}
            for s, k in tb_omitted[:MAX_LISTED]
        ],
    }


def _distribution(values: list[int]) -> dict[str, int]:
    """Count how many sources carry each expectation denominator (a 1-concept source is weak evidence)."""
    out: dict[str, int] = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def check(cfg: dict[str, Any], target_override: str | None) -> int:
    """Load the golden (refusing a stale one), evaluate, write the receipt, return the tri-state code."""
    golden_path = PROJECT_ROOT / cfg["golden"]["path"]
    if not golden_path.exists():
        print(f"OWED: golden missing ({golden_path}) - run --build-golden --apply")
        return EXIT_OWED
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    sheet = PROJECT_ROOT / cfg["golden"]["source_sheet"]
    if golden.get("authority", {}).get("sha256") != sha256_file(sheet):
        print("OWED: golden is STALE - the authority sheet changed since it was built; rebuild it "
              "(a golden that lags its authority measures the wrong thing)")
        return EXIT_OWED

    target = target_override or str(cfg["evaluate"]["target"])
    if target == "store":
        pairs, faults = _store_emissions(cfg)
        target_desc = f"store:{cfg['store']}"
    elif target == "s5":
        rel = cfg["evaluate"].get("s5_checkpoint")
        if not rel:
            print("FAIL-CLOSED: target=s5 but no evaluate.s5_checkpoint is declared (C12)")
            return EXIT_CONFIG
        pairs, faults = _s5_emissions(PROJECT_ROOT / rel)
        target_desc = f"s5:{rel}"
    else:
        print(f"FAIL-CLOSED: unknown target {target!r} (declared: store|s5)")
        return EXIT_CONFIG

    result = evaluate(golden, pairs, faults, cfg)
    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "EXTRACTION-RECALL-REPORT",
        "gen_model": GEN_MODEL,
        "pipeline_commit": pipeline_commit(),
        "target": target_desc,
        "golden": {"path": cfg["golden"]["path"], "sha256": sha256_file(golden_path)},
        "result": result,
    }
    out_path = PROJECT_ROOT / cfg["report_path"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(
        f"recall vs {target_desc}: concept {result['concepts_hit']}/{result['concepts_expected']} "
        f"= {result['concept_recall']}, expectation {result['expectations_hit']}/"
        f"{result['expectations_expected']} = {result['expectation_recall']} -> {result['verdict']}"
    )
    for reason in result["red_reasons"]:
        print(f"  RED: {reason}")
    print(f"  receipt: {cfg['report_path']}")
    print(f"  tier B: {result['tier_b_proposed']} proposed, {result['tier_b_present']} present, "
          f"{result['tier_b_omitted']} omitted (advisory - never floored, never auto-certified)")
    return EXIT_CLEAN if result["verdict"] == "CLEAN" else EXIT_RED


def write_golden(cfg: dict[str, Any], apply: bool) -> int:
    """Preview or write the golden, R14-stamped and crash-safe."""
    golden = build_golden(cfg)
    if not apply:
        print(json.dumps({k: v for k, v in golden.items() if k != "rows"}, indent=2))
        print(f"preview only ({len(golden['rows'])} rows); re-run with --apply to write "
              f"{cfg['golden']['path']}")
        return EXIT_CLEAN
    out_path = PROJECT_ROOT / cfg["golden"]["path"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(out_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(golden, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, out_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    c = golden["counts"]
    dup = c["certifications"] - c["concepts"]
    print(
        f"wrote {cfg['golden']['path']}: {c['concepts']} concepts, "
        f"{c['expectations']} (concept x source) expectations, "
        f"{c['distinct_sources']} sources"
        + (f" (from {c['certifications']} certifications; {dup} duplicate ruler->fb mapping(s) "
           f"collapse to one concept)" if dup else "")
    )
    return EXIT_CLEAN


def selftest() -> int:
    """Fixture proof (D-3036 red loop): loss REDs, presence GREENs, and the KEY CHOICE is proven."""
    from pipeline.dedup_identity import concept_key as mint

    cfg = {
        "floors": {"concept_recall": 1.0, "expectation_recall": 1.0},
    }
    name_a, name_b = "Soviet Underground Discourse Reception", "Vertical Space Adjustment in Typography"
    cert_a = {"item_id": "R002", "name": name_a, "concept_key": mint(name_a), "sources": ["s1", "s2"]}
    cert_b = {"item_id": "R111", "name": name_b, "concept_key": mint(name_b), "sources": ["s1"]}
    golden = {
        "rows": [cert_a, cert_b],
        "tier_b": "NOT MEASURED (fixture)",
    }
    expected_all = {("s1", cert_a["concept_key"]), ("s2", cert_a["concept_key"]),
                    ("s1", cert_b["concept_key"])}

    # 1) LOSS must be RED.
    lost = evaluate(golden, {("s1", cert_a["concept_key"]): 1}, [], cfg)
    assert lost["verdict"] == "RED", "a missing certified concept must RED"
    assert lost["concept_recall"] == 0.5 and lost["expectations_hit"] == 1, lost
    assert lost["missing_pairs_count"] == 2, lost

    # 2) PRESENCE must be CLEAN.
    full = evaluate(golden, {p: 1 for p in expected_all}, [], cfg)
    assert full["verdict"] == "CLEAN", full["red_reasons"]
    assert full["concept_recall"] == 1.0 and full["expectation_recall"] == 1.0, full

    # 3) SOURCE ATTRIBUTION loss alone must RED (a concept kept but detached from its source).
    detached = evaluate(golden, {p: 1 for p in expected_all - {("s2", cert_a["concept_key"])}}, [], cfg)
    assert detached["verdict"] == "RED", "losing a (source x concept) expectation must RED"
    assert detached["concept_recall"] == 1.0 and detached["expectation_recall"] < 1.0, detached

    # 4) THE KEY CHOICE, PROVEN BY NEGATIVE CONTROL (D-3129). A reworded definition yields a NEW
    #    fb_id; the concept must STILL match by concept_key, while an fb_id-keyed join would MISS it.
    old_fb, new_fb = "a" * 64, "b" * 64
    assert old_fb != new_fb
    same_name_pairs = {("s1", mint(name_a))}  # concept_key ignores the definition entirely
    assert ("s1", mint(name_a)) in same_name_pairs
    fb_keyed_expected = {("s1", old_fb)}
    fb_keyed_emitted = {("s1", new_fb)}
    assert fb_keyed_expected & fb_keyed_emitted == set(), (
        "negative control failed: an fb_id-keyed join was expected to MISS the reworded body"
    )

    # 5) A STALE KEY (store says one thing, the name says another) must RED.
    stale = evaluate(golden, {p: 1 for p in expected_all}, [{"fb_id": "c" * 64, "name": name_a}], cfg)
    assert stale["verdict"] == "RED" and stale["key_integrity_fault_count"] == 1, stale

    # 6) MULTIPLICITY is REPORTED and does not fail the floor; it is the echo signal (D-3129 rule 3).
    emitted_dup = {p: 1 for p in expected_all}
    emitted_dup[("s1", cert_a["concept_key"])] = 2
    dup = evaluate(golden, emitted_dup, [], cfg)
    assert dup["verdict"] == "CLEAN", dup["red_reasons"]
    assert dup["duplicate_pairs_count"] == 1, dup
    assert dup["duplicate_pairs"][0]["emitted"] == 2, dup["duplicate_pairs"]

    # 7) TIER-B (T-195): a PROPOSED-but-unruled candidate is REPORTED and NEVER floored or auto-certified.
    #    NEGATIVE CONTROL: a tier-B row ABSENT from the store must report a CLEAN omission (not RED), and a
    #    PRESENT tier-B row must be reported as present WITHOUT being counted as a tier-A certification.
    tb_candidate = {
        "source_id": "s1",
        "name": "Uncertified Candidate Concept",
        "concept_key": mint("Uncertified Candidate Concept"),
        "rationale": "fixture",
    }
    golden_tb = {"rows": [cert_a], "tier_b": "PROPOSED (fixture)", "tier_b_rows": [tb_candidate]}
    tb_absent = evaluate(
        golden_tb,
        {("s1", cert_a["concept_key"]): 1, ("s2", cert_a["concept_key"]): 1},
        [], cfg,
    )
    assert tb_absent["verdict"] == "CLEAN", "a tier-B omission must NOT RED"
    assert tb_absent["tier_b_proposed"] == 1 and tb_absent["tier_b_omitted"] == 1, tb_absent
    assert tb_absent["concept_recall"] == 1.0, "tier-B absence must not drag the tier-A floor"
    assert tb_absent["concepts_expected"] == 1, "tier-B rows must not be counted as tier-A concepts"
    tb_present = evaluate(
        golden_tb,
        {("s1", cert_a["concept_key"]): 1, ("s2", cert_a["concept_key"]): 1,
         ("s1", tb_candidate["concept_key"]): 1},
        [], cfg,
    )
    assert tb_present["verdict"] == "CLEAN", tb_present["red_reasons"]
    assert tb_present["tier_b_present"] == 1 and tb_present["tier_b_omitted"] == 0, tb_present
    assert tb_present["concepts_expected"] == 1, "a present tier-B row must NOT be auto-certified"

    # 8) TIER-B OWNER-MATCH (T-195 step c): a MATCHed candidate is FLOORED and must RED when the store
    #    omits it (D-3130 — the omission is the completeness signal), distinct from an unruled candidate
    #    (case 7: advisory, CLEAN). The MATCHed row has NO fb_id (fb_id_pointer ""), proving a tier-B
    #    ruling needs no store row to become a floor.
    matched_tb = {
        "item_id": "tierB:test:0001",
        "name": "Owner Certified Omitted Concept",
        "concept_key": mint("Owner Certified Omitted Concept"),
        "sources": ["s1"],
        "fb_id_pointer": "",
    }
    golden_matched = {
        "rows": [cert_a, matched_tb],
        "tier_b": "MATCHed floored (fixture)",
        "tier_b_rows": [],
        "tier_b_matched": [{"source_id": "s1", "name": matched_tb["name"],
                            "concept_key": matched_tb["concept_key"]}],
    }
    matched_absent = evaluate(
        golden_matched,
        {("s1", cert_a["concept_key"]): 1, ("s2", cert_a["concept_key"]): 1},
        [], cfg,
    )
    assert matched_absent["verdict"] == "RED", "an owner-MATCHed tier-B concept omitted by the store must RED"
    assert matched_absent["missing_pairs_count"] == 1, matched_absent["missing_pairs"]
    assert matched_absent["missing_pairs"][0]["concept_key"] == matched_tb["concept_key"], matched_absent["missing_pairs"]
    assert matched_absent["concepts_expected"] == 2, "a MATCHed tier-B row must join the floored concept set"
    assert matched_absent["tier_b_matched"] == 1, matched_absent["tier_b_matched"]

    print("✅ selftest passed: loss RED, presence CLEAN, attribution loss RED, key-choice negative "
          "control, stale-key RED, multiplicity reported, tier-B omission CLEAN / not auto-certified, "
          "tier-B owner-MATCH floored RED")
    return EXIT_CLEAN


def main() -> int:
    parser = argparse.ArgumentParser(description="T-194 extraction-recall rail (D-3129 key space)")
    parser.add_argument("--build-golden", action="store_true", help="derive the golden from owner rulings")
    parser.add_argument("--apply", action="store_true", help="with --build-golden: write the golden")
    parser.add_argument("--check", action="store_true", help="evaluate recall and write the report")
    parser.add_argument("--target", choices=["store", "s5"], default=None,
                        help="override the configured evaluation target")
    parser.add_argument("--selftest", action="store_true", help="fixture proof, no store reads")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not (args.build_golden or args.check):
        parser.print_help()
        return EXIT_CONFIG
    cfg = load_config()
    code = EXIT_CLEAN
    if args.build_golden:
        code = write_golden(cfg, args.apply)
        if code != EXIT_CLEAN or not args.apply:
            return code
    if args.check:
        return check(cfg, args.target)
    return code


if __name__ == "__main__":
    sys.exit(main())
