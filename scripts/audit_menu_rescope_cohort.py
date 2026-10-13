#!/usr/bin/env python3
"""scripts/audit_menu_rescope_cohort.py — D-2974/BUG-748: the MENU-RE-SCOPE COHORT audit (read-only).

WHAT IT ANSWERS. A menu revision can move a discipline's DEFINITION without moving the ANSWER SPACE
(D-371/D-NEW-1), and the S4 classifier is DEFINITION-ANCHORED (D-2814: the model sees every canonical
label WITH its definition and must answer verbatim), so a definition edit IS an input change. D-2928
minted closed_menu_v10 with exactly that shape — the composite moved be323543... -> cc800a32... while the
answer space stayed e11ac764... — and deliberately did NOT rewrite the frozen rows (I2/D-2896). 177
canonical rows sit ON the moved boundary. A stamp cannot say whether their label still holds,
so this audit asks the question a stamp cannot answer: what does the classifier of record say about those
rows TODAY under the live menu, and what did it say under the revision they were admitted under?

THE ARMS (the differential IS the measurement: ONE arm measures nothing).
  LIVE     — the production path (merged_cribs_classify + the production remap) with the LIVE menu.
  RECORDED — the SAME path with the menu block of the revision the rows carry in their stamp,
             resolved BY CONTENT (a unique composite match, fail-closed). This is the CONTROL: if the
             recorded arm does not reproduce the STORED label either, the delta is instrument
             uncertainty, NOT the re-scope, and the audit reports exactly that.

AUTHORITY (why this script writes NO label). The classifier of record measures kappa ~0.45 against the
human-owner discipline anchor (D-2868/D-2770 class), so a fresh answer is ADVISORY and can never relabel
a canonical row by itself (D-2898: no LLM-applied canonical change; D-2611: never bare accuracy on a
skewed prior). Rows the OWNER has adjudicated are reported SEPARATELY: there the label is a ruling and
the classifier's disagreement is the instrument's error, not the row's.

READ-ONLY + ONE append-only artifact (C6/R14): the DB is opened read-only, every (row, arm) result is
appended to the declared checkpoint (resumable), and each record carries the R14 stamp from its ONE home
(pipeline.stamp), never restated here. No label, config or store byte is written.

Usage:
    python3 scripts/audit_menu_rescope_cohort.py --selftest    # deterministic controls; NO inference
    python3 scripts/audit_menu_rescope_cohort.py --dry-run     # derive the cohort + report; NO inference
    python3 scripts/audit_menu_rescope_cohort.py --limit 5     # live smoke, both arms, first 5 rows
    python3 scripts/audit_menu_rescope_cohort.py               # the full cohort, both arms
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import pipeline.stage4_merged_call as mc  # noqa: E402
from pipeline.closed_menu import (  # noqa: E402
    definition_anchored_block,
    menu_hash,
    render_closed_menu,
)
from pipeline.pipeline_paths import DB_PATH, VERIFY_MODEL  # noqa: E402
from pipeline.schemas import get_synonym_index  # noqa: E402
from pipeline.serving_gate import content_types_without_factual_claim  # noqa: E402
from pipeline.stage4_merge import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    map_to_canonical_with_fallback,
)
from pipeline.stamp import stamp_record  # noqa: E402

_ANCHOR_FAMILY = ROOT / "config" / "anchor_family.yaml"
_VERSION = ROOT / "config" / "version.yaml"
_PIPELINE_CONFIG = ROOT / "config" / "pipeline_config.yaml"
CHECKPOINT = ROOT / "governance" / "menu_rescope_cohort_audit.jsonl"
AUDIT = "D-2974/BUG-748"
LIVE, RECORDED = "live", "recorded"
FB_FIELDS = ("name", "definition", "mechanism", "boundary", "consequence")


def _yaml(path: Path) -> dict:
    """Load a YAML mapping, fail-closed on an unreadable or non-mapping document (C16)."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL-CLOSED (audit): {path.relative_to(ROOT)} is not a mapping (C16)")
    return doc


def _canonical_run() -> str:
    """The canonical pipeline_run_id, from the ONE declared home (anchor_family.store_bridge)."""
    run = (_yaml(_ANCHOR_FAMILY).get("store_bridge") or {}).get("canonical_run")
    if not run:
        raise SystemExit(f"FAIL-CLOSED (audit): {_ANCHOR_FAMILY.relative_to(ROOT)} declares no "
                         "store_bridge.canonical_run — the audit cannot name its subject (C16)")
    return str(run)


def _live_menu_path() -> Path:
    """The declared live menu revision (config/version.yaml#closed_menu)."""
    rel = _yaml(_VERSION).get("closed_menu")
    if not rel:
        raise SystemExit(f"FAIL-CLOSED (audit): {_VERSION.relative_to(ROOT)} declares no closed_menu (C16)")
    return ROOT / str(rel)


def revision_family() -> list[Path]:
    """Every frozen revision file of the LIVE menu's family, DERIVED from the declaration (C12).

    No manifest of menu revisions exists, so the family is read off the declared live path (the
    version-named stem, widened to any revision number) and the match is then made BY CONTENT. A
    revision is identified by the composite its bytes hash to, never by its filename (D-403/BUG-488).
    """
    live = _live_menu_path()
    pattern = re.sub(r"_v\d+(\.[a-z0-9]+)$", "_v*\\1", live.name)
    if pattern == live.name:
        raise SystemExit(f"FAIL-CLOSED (audit): the declared live menu {live.name} carries no revision "
                         "number, so the family cannot be derived (C12/C16)")
    return sorted(live.parent.glob(pattern))


def _menu_of(path: Path) -> dict:
    """Load one frozen menu revision as a menu document (the shape render_closed_menu emits)."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not doc.get("disciplines") or not doc.get("domains"):
        raise SystemExit(f"FAIL-CLOSED (audit): {path.relative_to(ROOT)} is not a menu document (C16)")
    return doc


def resolve_revision(recorded_hash: str) -> tuple[Path, dict]:
    """The revision whose COMPOSITE is the recorded stamp; a unique match or fail closed (D-403)."""
    hits = [(p, m) for p, m in ((p, _menu_of(p)) for p in revision_family())
            if menu_hash(m) == str(recorded_hash)]
    if len(hits) != 1:
        names = [p.name for p, _ in hits]
        raise SystemExit("FAIL-CLOSED (audit): the recorded composite " + str(recorded_hash)[:16]
                         + "... resolves to " + str(len(hits)) + " frozen revision(s) " + str(names)
                         + " — the audit refuses to guess which menu a row was admitted under (C16)")
    return hits[0]


def _definitions(menu: dict) -> dict[str, str]:
    """{discipline value: definition} for a menu document, abstention excluded."""
    return {str(e["value"]): str(e.get("definition") or "") for e in menu["disciplines"]
            if str(e["value"]) != str(menu.get("abstention"))}


def moved_definitions(recorded: dict, live: dict) -> tuple[list[str], list[str], list[str]]:
    """(moved, added, removed) between two menu revisions — the cohort is DERIVED, never typed (C12).

    A definition that differs is a MOVED boundary (D-2928/D-371: the composite moves, the answer space
    need not). A value present in one revision only is an ANSWER-SPACE move and is reported as such: it
    is a different defect class and must never be counted as a moved definition (two faults read as one).
    """
    rec, liv = _definitions(recorded), _definitions(live)
    moved = sorted(v for v in set(rec) & set(liv) if rec[v] != liv[v])
    return moved, sorted(set(liv) - set(rec)), sorted(set(rec) - set(liv))


def subject_stamps(run_id: str, live_hash: str) -> list[str]:
    """Distinct stale composites carried by the audit's SUBJECT — the menu revisions to resolve.

    The subject split is DERIVED (D-2942), so a cohort with no menu BY DESIGN (an absence stamp on a role
    that carries no factual claim) never reaches the revision resolver: it is not a revision, it is a
    declared absence, and resolving it would fail closed on a question nobody asked. An IN-SUBJECT row
    whose menu cannot be identified still fails closed, because that IS a defect.
    """
    outside = sorted(content_types_without_factual_claim())
    marks = ", ".join("?" * len(outside))
    sql = ("SELECT DISTINCT COALESCE(menu_hash, '') FROM fbs WHERE pipeline_run_id = ? "
           "AND COALESCE(menu_hash, '') NOT IN ('', ?) "
           f"AND COALESCE(content_type, '') NOT IN ({marks}) ORDER BY 1")
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        return [str(r[0]) for r in conn.execute(sql, [run_id, live_hash, *outside]).fetchall()]


def cohort(discipline: list[str], run_id: str, live_hash: str) -> list[dict]:
    """Canonical-run rows IN the audit's subject whose stored discipline moved boundary, stamped stale.

    The subject split is DERIVED (D-2942): a role that carries no factual claim was never classified
    against a menu, so no re-scope question can be asked of it. Read-only (BUG-660).
    """
    if not discipline:
        return []
    outside = sorted(content_types_without_factual_claim())
    disc_marks = ", ".join("?" * len(discipline))
    out_marks = ", ".join("?" * len(outside))
    sql = ("SELECT fb_id, " + ", ".join("COALESCE(" + c + ", '')" for c in FB_FIELDS) + ", "
           "COALESCE(discipline, ''), COALESCE(discipline_raw, ''), COALESCE(menu_hash, ''), "
           "COALESCE(taxonomy_version, ''), COALESCE(content_type, '') FROM fbs "
           "WHERE pipeline_run_id = ? AND COALESCE(menu_hash, '') <> ? "
           f"AND COALESCE(content_type, '') NOT IN ({out_marks}) AND discipline IN ({disc_marks}) "
           "ORDER BY discipline, fb_id")
    args = [run_id, live_hash, *outside, *discipline]
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        rows = conn.execute(sql, args).fetchall()
    keys = ("fb_id", *FB_FIELDS, "stored_discipline", "stored_discipline_raw", "stored_menu_hash",
            "stored_taxonomy_version", "stored_content_type")
    return [dict(zip(keys, r, strict=True)) for r in rows]


def _anchor_names() -> set[str]:
    """Normalised names of the OWNER-adjudicated discipline rows — the only HUMAN RULING on this axis.

    Config-first (C12): the anchor's path is the declared stage4.discipline_anchor_path. A missing key or
    an absent file is fatal: an audit that silently ran without the owner's rulings would over-claim.
    """
    s4 = _yaml(_PIPELINE_CONFIG).get("stage4") or {}
    rel = s4.get("discipline_anchor_path")
    if not rel:
        raise SystemExit("FAIL-CLOSED (audit): config/pipeline_config.yaml declares no "
                         "stage4.discipline_anchor_path — the owner's rulings cannot be located (C12/C16)")
    path = ROOT / str(rel)
    if not path.exists():
        raise SystemExit(f"FAIL-CLOSED (audit): the declared owner anchor {rel} does not exist (C16)")
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc if isinstance(doc, list) else (doc.get("rows") or doc.get("anchor") or doc.get("entries") or [])
    if not rows:
        raise SystemExit(f"FAIL-CLOSED (audit): {rel} carries no anchor rows (C16)")
    return {_norm(r.get("name")) for r in rows if isinstance(r, dict) and r.get("name")}


def _norm(x: object) -> str:
    """Collapse a label or name for comparison (case- and whitespace-insensitive)."""
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def _map_discipline(raw: str) -> str:
    """Map a raw classifier label to canonical — the PRODUCTION remap (D2138 two-stage), verbatim."""
    if not str(raw).strip():
        return "emerging"
    return map_to_canonical_with_fallback(str(raw), "discipline", _SYNONYM_INDEX,
                                         CANONICAL_DISCIPLINES)


_SYNONYM_INDEX = get_synonym_index()


def swapped_system(live_block: str, recorded_block: str) -> str:
    """The production system prompt with ONLY the menu block replaced by the recorded revision's.

    Fail-closed (C16): the live block must appear EXACTLY once, so a half-swapped prompt can never be
    sent. Everything else — schema, boundary block, reasoning prefix — is byte-identical to production.
    """
    system = mc.MERGED_CRIBS_CLASSIFY_SYSTEM
    if system.count(live_block) != 1:
        raise SystemExit("FAIL-CLOSED (audit): the live menu block does not appear exactly once in the "
                         "production system prompt — refusing to build a half-swapped control arm (C16)")
    return system.replace(live_block, recorded_block, 1)


def classify_arm(fb: dict, system: str) -> tuple[str, str]:
    """Run ONE arm through the PRODUCTION path; returns (raw label, error). The swap is restored always."""
    original = mc.MERGED_CRIBS_CLASSIFY_SYSTEM
    mc.MERGED_CRIBS_CLASSIFY_SYSTEM = system
    try:
        out = mc.merged_cribs_classify(dict(fb))
        return str(out.get("discipline") or ""), ""
    except Exception as exc:  # C16: a failed arm is RECORDED as failed, never silently dropped
        return "", type(exc).__name__ + ": " + str(exc)[:200]
    finally:
        mc.MERGED_CRIBS_CLASSIFY_SYSTEM = original


def _shard_of(fb_id: str, shards: int) -> int:
    """A deterministic shard for one row: parallel workers partition the cohort by CONTENT (no claims).

    The repo runs the S4 classifier at ~16-30 s per row (tools/benchmark_s4_merged_production.py), so a
    354-call audit is hours in ONE process. Sharding by a hash of the row id lets N workers share the
    work with no coordination and no double-counting, and the append-only checkpoint keeps it RESUMABLE.
    """
    return int(hashlib.sha256(fb_id.encode("utf-8")).hexdigest(), 16) % shards


def _done() -> set[tuple[str, str]]:
    """(fb_id, arm) pairs already in the append-only checkpoint — the run is RESUMABLE (C6)."""
    if not CHECKPOINT.exists():
        return set()
    out: set[tuple[str, str]] = set()
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out.add((str(rec.get("fb_id")), str(rec.get("arm"))))
    return out


def _append(rec: dict) -> None:
    """Append one result, fsync'd (C6): an audit that loses its record is not an audit.

    The R14 stamp comes from the ONE home (pipeline.stamp.stamp_record), never restated here (C12/D-274a);
    it carries the manifest_hash and the run id too, so a record whose verdict is later questioned can name
    the CONFIG state it was measured under.
    """
    line = json.dumps(stamp_record({**rec, "audit": AUDIT}, classify_model=VERIFY_MODEL), sort_keys=True)
    with open(CHECKPOINT, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        import os
        os.fsync(fh.fileno())


def anchor_coverage(anchor: set[str]) -> int:
    """How many anchor rows join THIS store by name — the PREMISE of the owner-ruling flag (BUG-488).

    A join miss is indistinguishable from a fact about the artifact, so the coverage is PRINTED: an audit
    that reported "0 owner-anchored rows" without it would read as "the owner ruled nothing here" when the
    truth may be "the anchor's population is not this corpus".
    """
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        names = {_norm(r[0]) for r in conn.execute("SELECT COALESCE(name, '') FROM fbs").fetchall()}
    return sum(1 for n in anchor if n in names)


def report(rows: list[dict], results: dict[tuple[str, str], dict], live_block: str,
           rec_block: str, anchor: set[str]) -> int:
    """Print the measured differential and the attribution rule; NO verdict is asserted beyond it."""
    def rate(arm: str) -> tuple[int, int, int]:
        ok = bad = err = 0
        for r in rows:
            got = results.get((str(r["fb_id"]), arm))
            if not got or got.get("error"):
                err += 1
            elif _norm(got.get("pred_canonical")) == _norm(r["stored_discipline"]):
                ok += 1
            else:
                bad += 1
        return ok, bad, err

    print("-" * 78)
    print(f"cohort rows        : {len(rows)} (canonical run, in-subject, stored discipline on a moved boundary)")
    print(f"owner anchor       : {len(anchor)} row(s), {anchor_coverage(anchor)} joinable to THIS store "
          f"by name; {sum(1 for r in rows if _norm(r['name']) in anchor)} of the cohort are owner-adjudicated "
          "(there the label is a HUMAN ruling, and a classifier disagreement is the INSTRUMENT's error)")
    live_ok, live_bad, live_err = rate(LIVE)
    rec_ok, rec_bad, rec_err = rate(RECORDED)
    print(f"LIVE     arm: reproduces the stored label {live_ok}/{len(rows)} | differs {live_bad} | failed {live_err}")
    print(f"RECORDED arm: reproduces the stored label {rec_ok}/{len(rows)} | differs {rec_bad} | failed {rec_err}"
          "   <- the CONTROL")
    moved: dict[tuple[str, str], int] = {}
    for r in rows:
        got = results.get((str(r["fb_id"]), LIVE))
        if got and not got.get("error") and _norm(got.get("pred_canonical")) != _norm(r["stored_discipline"]):
            key = (str(r["stored_discipline"]), str(got.get("pred_canonical")))
            moved[key] = moved.get(key, 0) + 1
    print("LIVE-arm movements (stored -> predicted, canonical):")
    for (a, b), n in sorted(moved.items(), key=lambda kv: -kv[1]):
        print(f"   {a:32s} -> {b:32s} {n}")
    if not moved:
        print("   (none)")
    print("-" * 78)
    print("ATTRIBUTION RULE (measured, not asserted): a movement is attributable to the RE-SCOPE only if "
          "the RECORDED arm reproduces the stored label; where the control arm fails too, the difference "
          "is the instrument's uncertainty on this axis and NO relabel follows from it.")
    print("AUTHORITY: the classifier of record is ADVISORY (D-2898). Its fresh label never rewrites a "
          "canonical row; an owner-anchored row's label is a ruling and is never the classifier's to move.")
    return 0


def run(argv: list[str]) -> int:
    """Derive the cohort, run both arms (resumable), and report the measured differential."""
    limit = 0
    shard, shards = 0, 1
    for i, a in enumerate(argv):
        if a == "--limit":
            limit = int(argv[i + 1])
        if a == "--shard":
            shard, shards = (int(x) for x in str(argv[i + 1]).split("/"))
    live_menu = render_closed_menu()
    live_hash = menu_hash(live_menu)
    run_id = _canonical_run()
    live_block = definition_anchored_block()
    stamps = subject_stamps(run_id, live_hash)
    if not stamps:
        print("ok audit: every canonical-run row carries the live composite — nothing to audit.")
        return 0
    for stamp in stamps:
        path, menu = resolve_revision(stamp)
        moved, added, removed = moved_definitions(menu, live_menu)
        rows = cohort(moved, run_id, live_hash)
        print("recorded revision  : " + path.name + "  composite " + stamp[:16] + "...")
        print("moved definitions  : " + (", ".join(moved) if moved else "(none)"))
        print("answer-space moves : added " + str(added) + " removed " + str(removed))
        if not rows:
            print("ok audit: no canonical row sits on a moved boundary for this revision.")
            continue
        if shards > 1:
            rows = [r for r in rows if _shard_of(str(r["fb_id"]), shards) == shard]
        if limit:
            rows = rows[:limit]
        rec_block = definition_anchored_block(menu)
        system = swapped_system(live_block, rec_block)
        anchor = _anchor_names()
        done = _done()
        results: dict[tuple[str, str], dict] = {}
        for r in rows:
            fb = {k: r[k] for k in FB_FIELDS}
            for arm, sysm in ((LIVE, mc.MERGED_CRIBS_CLASSIFY_SYSTEM), (RECORDED, system)):
                key = (str(r["fb_id"]), arm)
                if key in done:
                    continue
                raw, err = classify_arm(fb, sysm)
                rec = {"arm": arm, "fb_id": str(r["fb_id"]), "name": str(r["name"]),
                       "stored_discipline": str(r["stored_discipline"]),
                       "stored_discipline_raw": str(r["stored_discipline_raw"]),
                       "stored_menu_hash": str(r["stored_menu_hash"]),
                       "stored_taxonomy_version": str(r["stored_taxonomy_version"]),
                       "pred_raw": raw, "pred_canonical": "" if err else _map_discipline(raw),
                       "agrees": (not err and _norm(_map_discipline(raw)) == _norm(r["stored_discipline"])),
                       "owner_anchored": _norm(r["name"]) in anchor,
                       "recorded_revision": path.name, "error": err}
                _append(rec)
                results[key] = rec
                print(("  ok  " if not err else "  ERR ") + arm.ljust(8) + " " + str(r["fb_id"])[:12]
                      + " stored=" + str(r["stored_discipline"])[:28]
                      + " -> " + str(rec["pred_canonical"])[:28] + (" | " + err if err else ""), flush=True)
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                results[(str(rec.get("fb_id")), str(rec.get("arm")))] = rec
        report(rows, results, live_block, rec_block, anchor)
    return 0


def _expect(name: str, got: object, want: object, fails: list[str]) -> None:
    """One known-answer control; a failure NAMES itself (BUG-492)."""
    if got == want:
        print("  ok selftest/" + name + ": " + repr(got)[:100])
        return
    print("FAIL selftest/" + name + ": got " + repr(got)[:100] + ", expected " + repr(want)[:100])
    fails.append(name)


def selftest() -> int:
    """Deterministic known-answer controls: the DERIVATIONS must be seen to fire. NO inference, NO DB."""
    fails: list[str] = []
    fam = revision_family()
    _expect("the_revision_family_is_DERIVED_from_the_declaration", len(fam) >= 2, True, fails)
    live_hash = menu_hash(render_closed_menu())
    path, _ = resolve_revision(live_hash)
    _expect("the_LIVE_composite_resolves_to_ONE_revision_by_CONTENT", path == _live_menu_path(), True, fails)
    _expect("a_hash_no_revision_carries_raises", _resolution_is_fail_closed("0" * 64), True, fails)
    rec = {"abstention": "emerging", "disciplines": [
        {"value": "a", "definition": "one"}, {"value": "b", "definition": "two"}]}
    liv = {"abstention": "emerging", "disciplines": [
        {"value": "a", "definition": "one moved"}, {"value": "b", "definition": "two"},
        {"value": "c", "definition": "three"}]}
    _expect("a_MOVED_definition_is_reported_as_moved", moved_definitions(rec, liv)[0], ["a"], fails)
    _expect("a_value_only_in_the_LIVE_menu_is_an_ANSWER_SPACE_move", moved_definitions(rec, liv)[1], ["c"], fails)
    _expect("...and_never_counted_as_a_moved_definition", "c" in moved_definitions(rec, liv)[0], False, fails)
    _expect("the_definition_diff_is_SYMMETRIC", moved_definitions(liv, rec)[0], ["a"], fails)
    _expect("a_block_that_does_not_appear_ONCE_is_refused",
            _swap_is_fail_closed("no such block", "x"), True, fails)
    _expect("label_comparison_normalises_case_and_space", _norm("  Organizational  Theory "),
            "organizational theory", fails)
    _expect("an_empty_raw_label_maps_to_the_abstention",
            _map_discipline("") == render_closed_menu()["abstention"], True, fails)
    if fails:
        print("FAIL menu-rescope audit: " + str(len(fails)) + " control(s) fired: " + ", ".join(fails))
        return 1
    print("ok menu-rescope audit: 10/10 known-answer control(s) fire")
    return 0


def _resolution_is_fail_closed(bogus: str) -> bool:
    """True when resolving an unknown composite refuses instead of inventing a revision."""
    try:
        resolve_revision(bogus)
    except SystemExit:
        return True
    return False


def _swap_is_fail_closed(block: str, replacement: str) -> bool:
    """True when a swap whose anchor is absent refuses instead of sending a half-swapped prompt."""
    try:
        mc.MERGED_CRIBS_CLASSIFY_SYSTEM.replace(block, replacement, 1) and _require_once(block)
    except SystemExit:
        return True
    return False


def _require_once(block: str) -> None:
    """The fail-closed anchor test the swap performs, in isolation (no prompt is built here)."""
    if mc.MERGED_CRIBS_CLASSIFY_SYSTEM.count(block) != 1:
        raise SystemExit("FAIL-CLOSED (audit): anchor absent (control fixture)")


def main(argv: list[str]) -> int:
    """Dispatch: --selftest | --dry-run | the cohort audit. Every mode is read-only on the store."""
    if "--selftest" in argv:
        return selftest()
    if "--dry-run" in argv:
        return dry_run()
    return run(argv)


def dry_run() -> int:
    """Derive the cohort and print its shape WITHOUT inference (the audit's own premise check)."""
    live_menu = render_closed_menu()
    live_hash = menu_hash(live_menu)
    run_id = _canonical_run()
    stamps = subject_stamps(run_id, live_hash)
    print("canonical run     : " + run_id)
    print("live composite    : " + live_hash[:16] + "...")
    print("stale stamps      : " + str(stamps))
    anchor = _anchor_names()
    print("owner anchor rows : " + str(len(anchor)) + " name(s)")
    for stamp in stamps:
        path, menu = resolve_revision(stamp)
        moved, added, removed = moved_definitions(menu, live_menu)
        rows = cohort(moved, run_id, live_hash)
        print("revision " + path.name + " composite " + stamp[:16] + "... -> moved " + str(moved)
              + " | answer-space added " + str(added) + " removed " + str(removed)
              + " | cohort " + str(len(rows)) + " row(s), owner-anchored "
              + str(sum(1 for r in rows if _norm(r["name"]) in anchor)))
        for d in sorted({str(r["stored_discipline"]) for r in rows}):
            print("   " + d + ": " + str(sum(1 for r in rows if str(r["stored_discipline"]) == d)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
