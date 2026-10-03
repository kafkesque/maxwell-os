#!/usr/bin/env python3
"""Enforce the S4 golden/eval split-manifest leakage guard (D-2733, owner gate OG-1 = OPTION A).

WHY (D-2729/D-2731): the 208 anchors are split into a 46-id golden pool (S4 few-shot exemplars)
and a 162-id eval set. If any golden id re-enters eval, S4 is evaluated on data it was few-shot on,
so every downstream number (S4, Ragas, retrieval) becomes circular and uninterpretable. This rail
makes that overlap mechanically impossible by failing closed on any intersection.

Enforced invariants (all reproducible from the manifest alone):
  1. disjointness: golden_pool_ids ∩ eval_ids = ∅  (THE leakage guard)
  2. cardinality:  golden_pool_count + eval_count == total_anchors, each list matches its declared
                   count, and neither list carries a duplicate id
  3. option == "A"  (Option B superseded, Option C rejected — D-2729)
  4. ids_sha256 pin: recomputed over the sorted golden_pool_ids and compared to the manifest's pin
     (canonical form documented under BUG-603, CLOSED by D-2813)

The manifest's `ids_sha256` pin IS enforced here (BUG-603 CLOSED by D-2813): build_split_manifest.py
now emits the pin with a documented canonical form — the sha256 of the newline-joined, sorted
golden_pool_ids — and this rail recomputes it, failing closed on any golden-pool drift or tamper.

Usage:  python3 scripts/verify_split_manifest.py            (enforce, exit 0 pass / 1 fail)
        python3 scripts/verify_split_manifest.py --selftest (known-answer controls, BUG-492)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "eval_integrity.yaml"


def _manifest_path() -> Path:
    """Return the split-manifest path declared in config/eval_integrity.yaml (C12: no hardcoded path)."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    block = cfg.get("split_manifest") or {}
    raw = block.get("file")
    if not raw:
        raise SystemExit(f"FAIL-CLOSED: {CONFIG} declares no split_manifest.file (C12)")
    return REPO / raw


def _ids_sha256(ids: list[str]) -> str:
    """Return the documented canonical sha256 pin over the sorted golden id list (BUG-603/D-2813).

    Canonical form: sha256 of the newline-joined, sorted golden_pool_ids — identical to the emitter in
    scripts/build_split_manifest.py, so the pin is reproducible and this rail can enforce it fail-closed.
    """
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def _problems(manifest: dict) -> list[str]:
    """Return every way the manifest violates the leakage guard; empty list means PASS."""
    problems: list[str] = []
    golden = manifest.get("golden_pool_ids") or []
    evals = manifest.get("eval_ids") or []
    gs, es = set(golden), set(evals)
    overlap = sorted(gs & es)
    if overlap:
        problems.append(f"LEAKAGE: {len(overlap)} golden id(s) re-enter eval: {overlap}")
    if manifest.get("option") != "A":
        problems.append(f"option is {manifest.get('option')!r}, expected 'A' (OG-1)")
    if len(golden) != len(gs) or len(evals) != len(es):
        problems.append("duplicate ids within golden_pool_ids or eval_ids")
    declared_g = manifest.get("golden_pool_count")
    declared_e = manifest.get("eval_count")
    total = manifest.get("total_anchors")
    if declared_g != len(golden) or declared_e != len(evals):
        problems.append(f"declared counts {declared_g}/{declared_e} != list lengths {len(golden)}/{len(evals)}")
    if total != len(golden) + len(evals):
        problems.append(f"total_anchors {total} != golden+eval {len(golden) + len(evals)}")
    pin = manifest.get("ids_sha256")
    if pin is None:
        problems.append("ids_sha256 pin missing (BUG-603/D-2813: canonical form is now required)")
    elif pin != _ids_sha256(golden):
        problems.append("ids_sha256 pin MISMATCH: golden_pool_ids drifted or tampered (BUG-603/D-2813)")
    return problems


def _verify(path: Path) -> int:
    """Enforce the guard against the manifest at `path`; fail-closed (exit 1) on any violation."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = _problems(manifest)
    if problems:
        print("FAIL split_manifest rail (D-2733):")
        for p in problems:
            print("  -", p)
        return 1
    print("ok split_manifest rail (D-2733): disjoint golden "
          f"{len(manifest['golden_pool_ids'])} / eval {len(manifest['eval_ids'])} / total {manifest['total_anchors']}"
          f" | option {manifest.get('option')} | ids_sha256 verified (BUG-603 CLOSED)")
    return 0


def _selftest() -> int:
    """Known-answer controls (BUG-492): clean PASS, leak FAIL, option-C FAIL, tampered-pin FAIL must all fire."""
    base = {
        "option": "A",
        "golden_pool_count": 1,
        "eval_count": 2,
        "total_anchors": 3,
        "golden_pool_ids": ["R001"],
        "eval_ids": ["R002", "R003"],
    }
    base["ids_sha256"] = _ids_sha256(base["golden_pool_ids"])
    failures: list[str] = []
    if _problems(base):
        failures.append("clean manifest must PASS but failed")
    leaky = dict(base)
    leaky["eval_ids"] = ["R001", "R002"]  # golden id re-enters eval
    if not any("LEAKAGE" in p for p in _problems(leaky)):
        failures.append("leaky manifest must FAIL but passed")
    wrong = dict(base)
    wrong["option"] = "C"  # D-2729: Option C (leak) is REJECTED
    if not any("option" in p for p in _problems(wrong)):
        failures.append("option-C manifest must FAIL but passed")
    tampered = dict(base)
    tampered["ids_sha256"] = "0" * 64  # drift/tamper seal broken
    if not any("ids_sha256" in p for p in _problems(tampered)):
        failures.append("tampered ids_sha256 pin must FAIL but passed")
    if failures:
        for f in failures:
            print("FAIL", f)
        return 1
    print("ok verify_split_manifest --selftest: clean PASS, leak FAIL, option-C FAIL, tampered-pin FAIL (all controls fire)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(_selftest())
    raise SystemExit(_verify(_manifest_path()))
