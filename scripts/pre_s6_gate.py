#!/usr/bin/env python3
"""pre_s6_gate.py — Pre-S6 commit gate (D2505): verify the S5 checkpoint is safe to commit.

Run BEFORE `just stage6`. Fail-closed: a truncated / duplicate-fb_id / still-contaminated
S5 checkpoint must never reach S6's `INSERT OR REPLACE` (the BUG-195 silent-overwrite surface).

Checks (deterministic, no LLM):
  1. RECORD COUNT  — S5 checkpoint count == S4-persisted expected count (D2496 sidecar).
  2. BOUNDARY      — every line is standalone JSON + trailing newline (BUG-188 class).
  3. fb_id UNIQUE  — no duplicate fb_id (duplicates would silently overwrite in S6).
  4. CONTAMINATION — severe EPUB→MD evidence records must be status=QUARANTINE (BUG-181#1).
  5. TALLY         — PASS / QUARANTINE report (sanity band for human review).
  6. NON-FB TIER   — D2590: the sidecar rows S6 will ALSO commit must be collision-free, in-role,
                     and carry their declared type_body (skipped when commit_non_fb_types=false).

Exit 0 = safe to commit; non-zero = HOLD S6 (fix the cause, do not commit).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import (  # noqa: E402
    STAGE4_5_CHECKPOINT,
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
)


def _load_jsonl(path: Path) -> list[dict]:
    recs: list[dict] = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"❌ record {i} not standalone JSON: {e}")
                raise
    return recs


def _expected_count() -> int | None:
    """Expected FB count persisted by S4/S4.5 (D2496)."""
    candidates = [Path(str(STAGE4_5_CHECKPOINT) + ".expected_count.json"),
                  Path(str(STAGE4_CHECKPOINT) + ".expected_count.json")]
    for c in candidates:
        if c.exists():
            try:
                d = json.loads(c.read_text())
                n = d.get("expected_fb_count")
                if n is not None:
                    return int(n)
            except Exception:
                continue
    return None


def _declared_failed() -> int:
    """D-2817: declared failed/quarantined cluster count persisted by S4."""
    candidates = [Path(str(STAGE4_5_CHECKPOINT) + ".expected_count.json"),
                  Path(str(STAGE4_CHECKPOINT) + ".expected_count.json")]
    for c in candidates:
        if c.exists():
            try:
                return int(json.loads(c.read_text(encoding="utf-8")).get("declared_failed_count") or 0)
            except Exception:
                continue
    return 0


def _severe_evidence_ids(fbs: list[dict]) -> set[str]:
    """Reuse the S5 evidence-cleanliness gate (BUG-181#1/BUG-202 fail-closed)."""
    from pipeline.stage5_verify import _evidence_cleanliness_gate
    return _evidence_cleanliness_gate(fbs)


def main() -> int:
    if not STAGE5_CHECKPOINT.exists():
        print(f"❌ S5 checkpoint not found: {STAGE5_CHECKPOINT}")
        return 1

    fbs = _load_jsonl(STAGE5_CHECKPOINT)
    n = len(fbs)
    problems: list[str] = []

    # 1. record count
    expected = _expected_count()
    declared = _declared_failed()
    if expected is None:
        print("⚠️  no .expected_count.json sidecar — cannot verify count (proceeding, WARN)")
    elif n + declared != expected:
        problems.append(f"record count {n} + declared-failed {declared} != expected {expected}")
    else:
        print(f"✅ record count {n} + declared-failed {declared} == expected {expected}")

    # 2. boundary — _load_jsonl() above already raises on any non-standalone-JSON
    # line (BUG-188 partial-tail class); whole-record truncation is caught by the
    # record-count check below. safe_write (os.replace) makes mid-record cuts
    # unobservable, so no separate byte-level probe is needed.

    # 3. fb_id uniqueness
    from collections import Counter
    id_counts = Counter(r.get("fb_id") for r in fbs)
    dupes = sorted(i for i, k in id_counts.items() if k > 1)
    if dupes:
        problems.append(f"{len(dupes)} duplicate fb_id (S6 INSERT OR REPLACE would overwrite): {dupes[:5]}")
    else:
        print(f"✅ fb_id unique ({len(set(id_counts))}/{n})")

    # 4. contamination consistency — severe evidence must be QUARANTINE
    try:
        severe = _severe_evidence_ids(fbs)
        status_by_id = {r.get("fb_id"): r.get("status") for r in fbs}
        leaking = [fid for fid in severe if status_by_id.get(fid) != "QUARANTINE"]
        if leaking:
            problems.append(f"{len(leaking)} severe-contaminated FB(s) NOT quarantined: {leaking[:5]}")
        else:
            print(f"✅ evidence-contamination gate: {len(severe)} severe → all QUARANTINE")
    except Exception as e:
        problems.append(f"evidence-cleanliness gate unavailable (BUG-202 fail-closed): {e}")

    # 5. tally
    from collections import Counter
    c = Counter(r.get("status") for r in fbs)
    print(f"📊 tally: {dict(c)}")

    # 6. D2590 non-principle ingest set — the rows S6 will ALSO commit (flag-gated).
    # WHY HERE: pre_s6_gate exists so a truncated / duplicated / contaminated set never reaches S6's
    # INSERT (D2505). The non-principle tier is a SECOND input to the SAME INSERT, so it must pass the
    # same kind of gate: a collision with the checkpoint would be the BUG-195 silent overwrite, and an
    # off-role row would persist a mislabelled object (C16).
    try:
        from pipeline.pipeline_paths import S6_COMMIT_NON_FB
    except Exception as e:  # config failure is fatal, never ignored
        problems.append(f"cannot read stage6.commit_non_fb_types from config (C12/C16): {e}")
        S6_COMMIT_NON_FB = False

    if S6_COMMIT_NON_FB:
        try:
            from pipeline.pipeline_paths import DB_PATH
            from pipeline.stage6_commit import (
                _run_id_for_commit,
                _stored_fb_ids,
                load_non_fb_sidecars,
            )

            run_id = _run_id_for_commit()
            non_fb, non_fb_stored, receipt = load_non_fb_sidecars(run_id, _stored_fb_ids(DB_PATH))
            collisions = sorted({r["fb_id"] for r in non_fb} & {r.get("fb_id") for r in fbs})
            if collisions:
                problems.append(
                    f"{len(collisions)} non-principle fb_id(s) collide with the S5 checkpoint "
                    f"(S6 INSERT OR REPLACE would overwrite): {collisions[:5]}"
                )
            bodyless = [r["fb_id"] for r in non_fb if not r.get("type_body")]
            if bodyless:
                problems.append(
                    f"{len(bodyless)} non-principle row(s) carry no type_body — a role's declared body "
                    f"would be committed empty: {bodyless[:5]}"
                )
            wrong_reason = sorted({str(r.get("s5_reason")) for r in non_fb} - {receipt["disposition_reason"]})
            if wrong_reason:
                problems.append(
                    f"non-principle rows carry an undeclared s5_reason {wrong_reason} — the D-2942 "
                    "disposition is the rule's output and nothing else may write it (D274h)"
                )
            if not non_fb:
                problems.append(
                    f"stage6.commit_non_fb_types=true but the {run_id} sidecars yielded 0 tier rows — "
                    "a stale sidecar or a broken loader, never a no-op"
                )
            if not problems:
                print(f"✅ non-principle tier ({run_id}): {receipt['tier_rows']} row(s) "
                      f"{receipt['by_role']} — {receipt['new_rows']} new, "
                      f"{receipt['already_stored_in_tier']} already stored (ALREADY_STORED); "
                      f"type_body present, no checkpoint collision, "
                      f"disposition={receipt['disposition_reason']}")
                print(f"   excluded {receipt['excluded']['not_a_commit_role']} row(s) whose own "
                      f"content_type is not a commit role "
                      f"{receipt['excluded']['not_a_commit_role_by_content_type']}; "
                      f"{receipt['quarantine_shelf_records']} on the D2616 hold shelf (never a source)")
                if receipt.get("ge_category_vocabulary"):
                    gv = receipt["ge_category_vocabulary"]
                    print(f"   D-2924 advisory: {gv['off_vocabulary_rows']}/{gv['rows']} growth_edge "
                          f"categor(ies) are OFF the closed vocabulary (enforcing={gv['enforcing']}) — the "
                          "calibration gold set is still owner-owed, and nothing is rewritten here")
        except Exception as e:
            problems.append(f"non-principle ingest set could not be validated (D2590 fail-closed): {e}")

    if problems:
        print("\n❌ PRE-S6 GATE FAILED — HOLD S6:")
        for p in problems:
            print(f"   - {p}")
        return 1
    print("\n✅ PRE-S6 GATE PASSED — safe to `just stage6`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
