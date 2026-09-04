#!/usr/bin/env python3
"""scripts/apply_alias_corrections.py — D2568 alias review apply (Phase 2 result).

Applies the cross-family-AGREED alias corrections from the review pipeline:
  * Phase 1 (Qwen3.8-27B) flagged single-value aliases it judged wrong → temp/alias_review_qwen38.jsonl
  * Phase 2 (DeepSeek-v4-pro, cross-family) independently re-mapped each flag and
    returned an "agree" index set (its mapping == Qwen3.8's correction).

Only the AGREEMENT set is applied (R5). No-op proposals (corrected == current
target) and DeepSeek "disagree"/"other" cases are skipped. Kind-safety is enforced:
a correction must target a canonical of the SAME axis (domain alias -> domain
canonical, discipline alias -> discipline canonical).

Surgical, add-only semantics: existing alias_map entries are UPDATED in place
(single-value only), nothing else is touched. C6/C13: alias_map.yaml is backed up
before the write.

Run:
    python3 scripts/apply_alias_corrections.py            # dry-run
    python3 scripts/apply_alias_corrections.py --apply    # backup + write
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

_ALIAS = _ROOT / "config" / "alias_map.yaml"
_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"
_PROPOSALS = _ROOT / "temp" / "alias_review_qwen38.jsonl"

# DeepSeek verification result (Phase 2, cross-family R5). Module-level data.
_AGREE = frozenset({
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21,
    22, 23, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
    43, 44, 45, 48, 49, 50, 51, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64,
    65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
})
_DISAGREE = frozenset({15, 24, 28, 42, 46, 47, 52, 53, 75})


def _canonicals() -> dict[str, set[str]]:
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    return {
        "domain_aliases": {d["canonical"] for d in tax["domains"]},
        "discipline_aliases": {d["canonical"] for d in tax["disciplines"]},
    }


def _load_proposals() -> list[dict]:
    return [json.loads(l) for l in _PROPOSALS.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write (default = dry-run).")
    args = ap.parse_args()

    proposals = _load_proposals()
    canon = _canonicals()
    alias = yaml.safe_load(open(_ALIAS, encoding="utf-8"))

    corrections: list[dict] = []
    skipped: list[str] = []
    for i, p in enumerate(proposals):
        if i not in _AGREE:
            continue
        kind, raw, target, corrected = p["kind"], p["raw"], p["target"], p["corrected"]
        if corrected == target:
            skipped.append(f"no-op: {raw!r}")
            continue
        if corrected not in canon[kind]:
            skipped.append(f"kind-mismatch: {raw!r} -> {corrected!r}")
            continue
        if kind not in alias:
            alias[kind] = {}
        corrections.append({"kind": kind, "raw": raw, "old": target, "new": corrected})

    print(f"agreed corrections to apply: {len(corrections)}")
    for c in corrections:
        print(f"  [{c['kind'][:8]:8s}] {c['raw']!r}: {c['old']!r} -> {c['new']!r}")
    for s in skipped:
        print(f"  ⚠️  skipped {s}")

    if not args.apply:
        print("\n(dry-run — no write. Re-run with --apply.)")
        return 0

    bak = _ALIAS.with_suffix(_ALIAS.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_alias_review")
    shutil.copy2(str(_ALIAS), str(bak))
    print(f"\n🔒 backup: {bak.name}")

    for c in corrections:
        alias[c["kind"]][c["raw"]] = c["new"]
    with open(_ALIAS, "w", encoding="utf-8") as f:
        yaml.safe_dump(alias, f, sort_keys=False, allow_unicode=True)

    # round-trip validate
    yaml.safe_load(open(_ALIAS, encoding="utf-8"))
    print(f"✅ applied {len(corrections)} alias corrections → {_ALIAS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
