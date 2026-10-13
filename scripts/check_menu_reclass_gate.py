#!/usr/bin/env python3
"""scripts/check_menu_reclass_gate.py — BUG-693 step 4: the menu-widening re-classification gate.

WHY (root cause, not symptom). The canonical run rechunk-v4-20260929 was classified under taxonomy
v5.6 (menu_hash 99e1df82...), but the live menu is v10 (composite cc800a32...). The menu widened
(v5 -> v8: +3 Business & Management disciplines, D-2815) AFTER classification and the rows were never
re-classified — that is the whole of BUG-693: 1779 'emerging' rows that were never given a chance to
land in the widened menu. The fix is not a prompt tweak; it is a rail that makes "menu changed after
classification" IMPOSSIBLE to miss.

WHAT WAS WRONG (D-2973/BUG-747, MEASURED 2026-10-13). Two defects, both measured, neither visible:
  (i)  IT COULD NOT FIRE. No ladder recipe invoked this rail: reach reported "1 uninvoked of 125
       reachable check script(s)" (debt_max 0, SHRINK-ONLY) and check_rail_registry.py reported
       "(i) a rail NOTHING RUNS: scripts/check_menu_reclass_gate.py ... declared dormant nowhere -
       a control that cannot fire (BUG-492)". From the day it was written (D-2894) it could not fire.
  (ii) ITS IDENTITY CONTRADICTED A RATIFIED RULE. The verdict keyed on the COMPOSITE menu_hash. The
       registry declares (config/menu_axis_hashes.yaml#note, D-285/D-321/D-371/D-NEW-1) that the
       composite is HISTORICAL: a wording edit moves the composite and NOT the answer space,
       while taxonomy_version advances when the ANSWER SPACE moves. D-2928 (owner-approved,
       RATIFIED) moved the composite v9 -> v10 and recorded what follows: the frozen provenance
       records what the rows WERE adjudicated against, and "rewriting them would falsify history"
       (I2 / D-2896 raw-invariance). Wired as written, this rail would have imported the refused
       doctrine into the ladder's verdict and demanded exactly that falsifying rewrite.

THE MODEL (REPAIRED). Every arm is DERIVED from a declared home; no value is hardcoded (C12):
  SUBJECT  a row whose role carries NO factual claim is OUTSIDE this gate's subject: no menu was ever
           run for it, so its menu_hash is a declared ABSENCE, and refreshing it is the BUG-737 debt,
           never a re-classification. The set is read from config/serving_gate.yaml
           (content_types_without_factual_claim, D-2942/D2590) through its ONE home, which FAILS
           CLOSED on a missing key (C16) — an empty set would silently re-subject 1,049 rows.
  GREEN    in-subject, and the recorded identity EQUALS the live identity.
  RED      in-subject, and the recorded taxonomy_version DIFFERS from the live one: the ANSWER SPACE
           moved since classification (D-371/D-NEW-1), so the stored labels are not traceable to the
           served menu and a re-classification pass is MANDATORY. This is the BUG-693 root cause
           (v5.6 -> v9), and the only arm that may block the canonical run.
  OWED     in-subject, version EQUAL, composite different: WORDING moved (D-2928/D-371). The answer
           space is intact, so no label set is invalidated and the recorded composite is HISTORICAL
           (never rewritten: I2/D-2896). What remains is the owner-gated AUDIT of the re-scope's
           affected cohort (the D-2905 class) — LOUD and NON-FATAL (rc 2, the ladder's declared-debt
           convention), never a rewrite.

Config-first (C12): the DB path, the canonical run id, the live identity and the subject set are all
DERIVED from config, never hardcoded. Read-only: no DB or config writes (C16, BUG-491/BUG-660 class).

Usage:
    python3 scripts/check_menu_reclass_gate.py             # tri-state: 0 fresh | 1 ANSWER-SPACE move
                                                           # (MANDATORY) | 2 OWNER-OWED (wording-only
                                                           # composite move, or a no-menu cohort)
    python3 scripts/check_menu_reclass_gate.py --report    # informational (exit 0), always prints per-run
    python3 scripts/check_menu_reclass_gate.py --selftest  # known-answer controls (BUG-492: a control
                                                           # nothing runs is a comment)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.closed_menu import menu_hash  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.serving_gate import content_types_without_factual_claim  # noqa: E402

_ANCHOR_FAMILY = ROOT / "config" / "anchor_family.yaml"
_VERSION = ROOT / "config" / "version.yaml"

#: The tri-state vocabulary. A verdict is a claim about a SUBJECT, so the exit code is derived from it in
#: ONE place (EXIT_FOR) rather than re-stated per branch (C12/D-274a).
GREEN, RED, OWED = "GREEN", "RED", "OWED"
EXIT_FOR: dict[str, int] = {GREEN: 0, RED: 1, OWED: 2}
_ORDER: dict[str, int] = {GREEN: 0, OWED: 1, RED: 2}


def _canonical_run_id() -> str:
    """The canonical pipeline_run_id, from the ONE declared home (anchor_family.store_bridge.canonical_run)."""
    doc = yaml.safe_load(_ANCHOR_FAMILY.read_text(encoding="utf-8")) or {}
    run_id = (doc.get("store_bridge") or {}).get("canonical_run")
    if not run_id:
        raise SystemExit(f"FAIL-CLOSED: {_ANCHOR_FAMILY.relative_to(ROOT)} declares no "
                         "store_bridge.canonical_run - the gate cannot name the run it protects (C16)")
    return str(run_id)


def _live_taxonomy_version() -> str:
    """The live taxonomy version, from config/version.yaml (the same home apply_taxonomy_v8.py promotes)."""
    doc = yaml.safe_load(_VERSION.read_text(encoding="utf-8")) or {}
    ver = doc.get("taxonomy_version")
    if not ver:
        raise SystemExit(f"FAIL-CLOSED: {_VERSION.relative_to(ROOT)} declares no taxonomy_version (C16)")
    return str(ver)


def _run_identity() -> list[dict]:
    """Per recorded identity, the row counts SPLIT into this gate's SUBJECT and OUTSIDE it.

    The split is DERIVED (D-2942): a role that carries no factual claim was never classified against a
    menu, so no freshness claim about it can be true or false — it is counted, printed, and immune.
    Read-only (BUG-660): the connection is opened in read-only URI mode, so a rail built to REPORT can
    never become a rail that repairs what it reports.
    """
    outside = sorted(content_types_without_factual_claim())
    marks = ", ".join("?" * len(outside))
    sql = ("SELECT pipeline_run_id, COALESCE(menu_hash, ''), COALESCE(taxonomy_version, ''), "
           f"SUM(CASE WHEN content_type IN ({marks}) THEN 1 ELSE 0 END), COUNT(*) "
           "FROM fbs GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        rows = conn.execute(sql, tuple(outside)).fetchall()
    return [{"run_id": str(r[0]), "menu_hash": str(r[1]), "taxonomy_version": str(r[2]),
             "outside": int(r[3]), "total": int(r[4]), "in_subject": int(r[4]) - int(r[3])}
            for r in rows]


def classify(rec_hash: str, rec_ver: str, live_hash: str, live_ver: str,
             in_subject: int, outside: int) -> tuple[str, str]:
    """Map one recorded identity to (verdict, reason) — the declared arms, in precedence order.

    The FIRST arm is the subject itself: a cohort with no menu BY DESIGN is not a stale cohort, and a
    gate that cannot tell those apart reports the BUG-737 debt as a re-classification demand (BUG-747).
    """
    if in_subject == 0:
        return OWED, (f"OUTSIDE this gate's subject: {outside} row(s) of a role that carries no factual "
                      "claim were never classified against a menu (D-2942), so their stamp is a declared "
                      "ABSENCE - refreshing it is the BUG-737 debt, never a re-classification")
    if not str(rec_hash).strip():
        return OWED, ("UNSTAMPED: no menu provenance at all (pre-D-279), so freshness cannot be asked - "
                      "loud, never fatal, and not this gate's to clear")
    if str(rec_ver) != str(live_ver):
        return RED, (f"the ANSWER SPACE moved: classified under taxonomy {rec_ver}, live is {live_ver} "
                     "(D-371/D-NEW-1) - the stored labels are not traceable to the served menu, so a "
                     "re-classification pass is MANDATORY")
    if str(rec_hash) != str(live_hash):
        return OWED, (f"WORDING moved: the recorded composite is {str(rec_hash)[:16]}..., live is "
                      f"{str(live_hash)[:16]}..., while the answer space is {live_ver} on both sides "
                      "(D-2928/D-371). The labels are NOT invalidated and the frozen composite is "
                      "HISTORICAL - it is never rewritten (I2/D-2896); what remains is the owner-gated "
                      "AUDIT of the re-scope's affected cohort (D-2905 class)")
    return GREEN, "fresh: classified against the live menu"


def main(argv: list[str]) -> int:
    """Compare every run's recorded menu identity against the live one; tri-state on the canonical run."""
    if "--selftest" in argv:
        return selftest()
    report_only = "--report" in argv
    live_hash: str = menu_hash()
    live_ver: str = _live_taxonomy_version()
    canonical: str = _canonical_run_id()

    print(f"live menu_hash  : {live_hash}")
    print(f"live taxonomy   : {live_ver}   (the ANSWER SPACE identity, D-371/D-NEW-1)")
    print(f"canonical run   : {canonical}")
    print("-" * 78)

    canonical_verdict = GREEN
    other_flagged = False
    for g in _run_identity():
        verdict, reason = classify(g["menu_hash"], g["taxonomy_version"], live_hash, live_ver,
                                   g["in_subject"], g["outside"])
        mark = {GREEN: "ok ", RED: "RED", OWED: "OWD"}[verdict]
        print(f"{mark} {g['run_id']:22s} rows={g['total']:6d} subject={g['in_subject']:6d} "
              f"outside={g['outside']:6d} menu_hash={g['menu_hash'][:16] or '(empty)':16s} "
              f"tax={g['taxonomy_version'] or '(empty)':6s} {reason}")
        if g["run_id"] == canonical:
            if _ORDER[verdict] > _ORDER[canonical_verdict]:
                canonical_verdict = verdict
        elif verdict != GREEN:
            other_flagged = True

    print("-" * 78)
    if canonical_verdict == RED:
        print("FAIL-CLOSED: the CANONICAL run's ANSWER SPACE has moved since classification - the stored "
              "labels are not traceable to the served menu (D-371/D-NEW-1). This is the BUG-693 root "
              "cause, and the re-classification pass must run before the canonical run can be trusted.")
    elif canonical_verdict == OWED or other_flagged:
        print("OWNER-OWED (loud, NOT fatal): nothing blocks serving. A wording-only move leaves the ANSWER "
              "SPACE intact, so the label set is not invalidated and the recorded composite is HISTORICAL "
              "- never rewritten (I2/D-2896; D-2928). The open act is the owner-gated AUDIT of the "
              "re-scoped definitions' affected cohort (D-2905 class); a cohort with no menu by design is "
              "the BUG-737 debt.")
    else:
        print("ok: the canonical run is fresh against the live menu (no menu-widening drift).")

    if report_only:
        return 0
    rank = max([_ORDER[canonical_verdict]] + ([_ORDER[OWED]] if other_flagged else []))
    for verdict, order in _ORDER.items():
        if order == rank:
            return EXIT_FOR[verdict]
    return EXIT_FOR[canonical_verdict]


def _expect(name: str, got: object, want: object, fails: list[str]) -> None:
    """One known-answer control, both directions asserted; a failure NAMES itself through its own marker."""
    if got == want:
        print("  ok selftest/" + name + ": " + repr(got)[:100])
        return
    print("FAIL selftest/" + name + ": got " + repr(got)[:100] + ", expected " + repr(want)[:100])
    fails.append(name)


def selftest() -> int:
    """Known-answer controls for the REPAIRED identity (BUG-492/BUG-747) - the arms must be SEEN to fire.

    The LIVE identities are read, so a control cannot agree with a fixture the rail invented; the stamps
    are in-memory only (no DB read, no write: BUG-491 class).
    """
    live_hash = menu_hash()
    live_ver = _live_taxonomy_version()
    other_hash = ("0" if live_hash[0] != "0" else "1") + "0" * 63
    other_ver = live_ver + "-fixture"
    fails: list[str] = []

    _expect("a_fresh_identity_is_GREEN", classify(live_hash, live_ver, live_hash, live_ver, 10, 0)[0],
            GREEN, fails)
    moved_space = classify(other_hash, other_ver, live_hash, live_ver, 10, 0)
    _expect("an_ANSWER_SPACE_move_is_RED", moved_space[0], RED, fails)
    _expect("...and_says_MANDATORY", "re-classification pass is MANDATORY" in moved_space[1], True, fails)
    _expect("...even_when_the_composite_MATCHES",
            classify(live_hash, other_ver, live_hash, live_ver, 10, 0)[0], RED, fails)
    wording = classify(other_hash, live_ver, live_hash, live_ver, 10, 0)
    _expect("a_wording_only_move_is_OWED", wording[0], OWED, fails)
    _expect("...and_never_demands_a_re_classification", "MANDATORY" not in wording[1], True, fails)
    _expect("...and_names_the_frozen_provenance_rule", "D-2896" in wording[1], True, fails)
    absent = classify(other_hash, other_ver, live_hash, live_ver, 0, 1049)
    _expect("a_cohort_with_no_menu_BY_DESIGN_is_outside_the_subject", absent[0], OWED, fails)
    _expect("...and_is_never_a_re_classification", "MANDATORY" not in absent[1], True, fails)
    _expect("...and_names_its_OWN_debt", "BUG-737" in absent[1], True, fails)
    _expect("an_unstamped_IN_SUBJECT_row_is_OWED_never_RED",
            classify("", live_ver, live_hash, live_ver, 1, 0)[0], OWED, fails)
    _expect("the_exit_map_is_tri_state", [EXIT_FOR[GREEN], EXIT_FOR[OWED], EXIT_FOR[RED]], [0, 2, 1], fails)
    subject = content_types_without_factual_claim()
    _expect("the_subject_split_is_DERIVED_and_cannot_collapse_to_empty", bool(subject), True, fails)

    if fails:
        print("FAIL menu-reclass-gate: " + str(len(fails)) + " control(s) fired: " + ", ".join(fails))
        return 1
    print("ok menu-reclass-gate: 13/13 known-answer control(s) fire")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
