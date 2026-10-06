#!/usr/bin/env python3
"""verify_duplicate_gate.py — fail-closed rail for the owner-gate dedup ledger (D-2738).

Two jobs:

1. STRUCTURAL (default, wired into `just health`): validate the adjudication ledger
   (schema, deterministic pair_ids, no self-map, no invalid verdict, no duplicate ids).
   PENDING is a valid state (owner gating is a human step), so a structurally-sound
   ledger exits 0 regardless of how many pairs are still PENDING.

2. APPLY GATE (`--gate`, called by the POST-RUN apply step, NOT health): fail-closed
   guarantee that NO duplicate is ever merged without an explicit owner verdict. Exits
   2 if any pair at/above `apply_threshold` is still PENDING.

Exit codes: 0 = clean; 1 = ledger read/structure error; 2 = selftest or gate failure.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

CONFIG_REL = "config/eval_integrity.yaml"
_DEFAULTS: dict[str, Any] = {
    "ledger_file": "governance/duplicate_adjudication.json",
    "apply_threshold": 0.50,
}
_VALID_VERDICTS = ("PENDING", "MERGE", "KEEP_SEPARATE")


def _load_config() -> dict[str, Any]:
    cfg_path = _PROJECT_ROOT / CONFIG_REL
    if not cfg_path.exists():
        return dict(_DEFAULTS)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    block = data.get("duplicate_gate") or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in block.items() if k in _DEFAULTS})
    return merged


def _pair_id(a_id: str, b_id: str) -> str:
    lo, hi = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
    return hashlib.sha256(f"{lo}|{hi}".encode("utf-8")).hexdigest()[:16]


def validate_ledger(ledger: dict[str, Any]) -> list[str]:
    """Return a list of structural problems (empty == sound)."""
    problems: list[str] = []
    pairs = ledger.get("pairs")
    if not isinstance(pairs, list):
        return ["ledger missing 'pairs' list"]
    seen: set[str] = set()
    for i, p in enumerate(pairs):
        pid = p.get("pair_id")
        a_id = p.get("a_id")
        b_id = p.get("b_id")
        verdict = p.get("verdict")
        if not pid or not a_id or not b_id:
            problems.append(f"pair[{i}] missing pair_id/a_id/b_id")
            continue
        exp = _pair_id(str(a_id), str(b_id))
        if pid != exp:
            problems.append(f"pair[{i}] pair_id mismatch {pid} != {exp}")
        if a_id == b_id:
            problems.append(f"pair[{i}] self-map (a_id == b_id)")
        if verdict not in _VALID_VERDICTS:
            problems.append(f"pair[{i}] invalid verdict {verdict!r}")
        if pid in seen:
            problems.append(f"pair[{i}] duplicate pair_id {pid}")
        seen.add(pid)
    return problems


def gate_ready(ledger: dict[str, Any], threshold: float) -> tuple[bool, list[dict]]:
    """(ready, pending_high_sim) — ready is True only if no high-sim pair is PENDING."""
    pending = [
        p for p in ledger.get("pairs", [])
        if p.get("verdict") == "PENDING" and float(p.get("max_similarity", 0.0)) >= threshold
    ]
    return (len(pending) == 0, pending)


def _selftest() -> int:
    fails: list[str] = []

    # Control 1: a sound ledger (all PENDING is fine) -> no structural problems.
    good = {
        "pairs": [
            {"pair_id": _pair_id("a", "b"), "a_id": "a", "b_id": "b",
             "verdict": "PENDING", "max_similarity": 0.9},
            {"pair_id": _pair_id("c", "d"), "a_id": "c", "b_id": "d",
             "verdict": "PENDING", "max_similarity": 0.6},
        ]
    }
    if validate_ledger(good):
        fails.append("sound ledger flagged")

    # Control 2: self-map -> detected.
    bad_self = {"pairs": [{"pair_id": _pair_id("a", "a"), "a_id": "a", "b_id": "a",
                           "verdict": "PENDING", "max_similarity": 1.0}]}
    if not validate_ledger(bad_self):
        fails.append("self-map not detected")

    # Control 3: invalid verdict -> detected.
    bad_v = {"pairs": [{"pair_id": _pair_id("a", "b"), "a_id": "a", "b_id": "b",
                        "verdict": "MERGEE", "max_similarity": 0.9}]}
    if not validate_ledger(bad_v):
        fails.append("invalid verdict not detected")

    # Control 4: gate REFUSES when a high-sim pair is still PENDING.
    ready, pending = gate_ready(good, 0.5)
    if ready or len(pending) != 2:
        fails.append("gate did not refuse on pending high-sim pairs")

    # Control 5: gate PASSES once every pair is owner-adjudicated.
    adjudicated = {
        "pairs": [
            {"pair_id": _pair_id("a", "b"), "a_id": "a", "b_id": "b",
             "verdict": "MERGE", "max_similarity": 0.9},
            {"pair_id": _pair_id("c", "d"), "a_id": "c", "b_id": "d",
             "verdict": "KEEP_SEPARATE", "max_similarity": 0.6},
        ]
    }
    ready, pending = gate_ready(adjudicated, 0.5)
    if not ready or pending:
        fails.append("gate did not pass on fully adjudicated ledger")

    if fails:
        print("FAIL verify_duplicate_gate selftest: " + " | ".join(fails))
        return 2
    print("ok verify_duplicate_gate selftest: 5/5 (sound, self-map, bad verdict, gate refuse, gate pass)")
    return 0


def _run(gate: bool) -> int:
    cfg = _load_config()
    ledger_path = _PROJECT_ROOT / cfg["ledger_file"]
    if not ledger_path.exists():
        print(f"verify_duplicate_gate: ledger not found {ledger_path}", file=sys.stderr)
        return 1
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"verify_duplicate_gate: ledger JSON error: {e}", file=sys.stderr)
        return 1

    problems = validate_ledger(ledger)
    pairs = ledger.get("pairs", [])
    if problems:
        print("FAIL verify_duplicate_gate: " + " | ".join(problems[:20]))
        return 1

    if gate:
        ready, pending = gate_ready(ledger, float(cfg["apply_threshold"]))
        if not ready:
            print(
                f"FAIL verify_duplicate_gate --gate: {len(pending)} pair(s) at/above "
                f"threshold {cfg['apply_threshold']} still PENDING (owner must adjudicate)"
            )
            return 2
        print(f"ok verify_duplicate_gate --gate: {len(pairs)} pairs all adjudicated, apply allowed")
        return 0

    n_merge = sum(1 for p in pairs if p["verdict"] == "MERGE")
    n_keep = sum(1 for p in pairs if p["verdict"] == "KEEP_SEPARATE")
    n_pending = sum(1 for p in pairs if p["verdict"] == "PENDING")
    print(
        f"ok verify_duplicate_gate: {len(pairs)} pairs, MERGE={n_merge}, "
        f"KEEP_SEPARATE={n_keep}, PENDING={n_pending} (structure clean)"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    return _run(gate="--gate" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
