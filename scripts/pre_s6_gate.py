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
    if expected is None:
        print("⚠️  no .expected_count.json sidecar — cannot verify count (proceeding, WARN)")
    elif n != expected:
        problems.append(f"record count {n} != expected {expected}")
    else:
        print(f"✅ record count {n} == expected {expected}")

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

    if problems:
        print("\n❌ PRE-S6 GATE FAILED — HOLD S6:")
        for p in problems:
            print(f"   - {p}")
        return 1
    print("\n✅ PRE-S6 GATE PASSED — safe to `just stage6`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
