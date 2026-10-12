#!/usr/bin/env python3
"""scripts/simulate_commit_dedup_gate.py — READ-ONLY evidence run for the D-2951 dedup gate.

WHY THIS EXISTS: `stage6.dedup_gate.mode: enforce` changes what Stage 6 WRITES. A gate is only
worth enforcing once it has been shown, on the REAL artifact, to decide what its author believes
— so this script runs the SAME `CommitDedupGate` the commit path runs (no second copy of the
decisions, no LLM anywhere, D-343) and writes NOTHING to the store or the checkpoints. It is the
measured flip criterion for report -> enforce.

THREE SCOPES (they answer different questions):

  --scope batch   Candidates = the S5 checkpoint ALONE, index EMPTY. The raw artifact: what the
                  S5-principle path produced on its own.

  --scope run     Candidates = the FAITHFUL S6 input (S5 checkpoint + the D-2590 non-principle
                  tier from the S4 sidecars), index EMPTY. This is the D-2949 #4 defect
                  measured directly: two extractions of ONE concept inside ONE run.
                  MEASURED 2026-10-12 — the distinction is decisive: the S5 checkpoint alone
                  holds ZERO duplicate-name groups, while every duplicate the D-2949 audit found
                  in the store lives in the sidecar tier (process_template / tool_instruction).
                  A simulation over the checkpoint alone would certify a gate it never exercised.

  --scope store   The honest S6 path: index = the live store, candidates = the faithful input
                  minus the fb_ids the store already holds (an existing fb_id is taken by the
                  verification_scoped provenance path — D-2933 rule V — and never reaches the
                  gate).

Read-only guarantee: the store is opened `mode=ro`; nothing is written unless --out is given,
and --out writes only the receipt JSON you name.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.dedup_gate import CommitDedupGate, load_committed_index  # noqa: E402
from pipeline.pipeline_paths import DB_PATH, S6_COMMIT_NON_FB, STAGE5_CHECKPOINT  # noqa: E402
from pipeline.schema_accessor import fb_id  # noqa: E402
# The D-2590 non-principle tier is part of S6's input, so the simulation reads it through the
# SAME loader S6 uses rather than re-deriving it (no second copy of the rule).
from pipeline.stage6_commit import (  # noqa: E402
    _run_id_for_commit,
    _stored_fb_ids,
    load_non_fb_sidecars,
)

SHOW_MAX = 20


def load_checkpoint(path: Path) -> list[dict]:
    """Read the S5 checkpoint (JSONL) into memory — the artifact S6 would commit."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_run_input(checkpoint_path: Path, include_sidecars: bool) -> tuple[list[dict], dict, set[str]]:
    """The rows Stage 6 would actually commit, in the order it commits them (see module docstring)."""
    rows = load_checkpoint(checkpoint_path)
    info: dict = {"checkpoint_rows": len(rows), "sidecar_rows": 0}
    stored: set[str] = set()
    if include_sidecars and S6_COMMIT_NON_FB:
        stored = _stored_fb_ids(DB_PATH)
        non_fb, _already, receipt = load_non_fb_sidecars(_run_id_for_commit(), stored)
        rows.extend(non_fb)
        info["sidecar_rows"] = len(non_fb)
        info["sidecar_by_role"] = receipt.get("by_role")
        info["sidecar_new_rows"] = receipt.get("new_rows")
    elif include_sidecars:
        info["sidecar_note"] = "stage6.commit_non_fb_types=false — the tier is not ingested today"
    info["total_rows"] = len(rows)
    return rows, info, stored


def run(scope: str, conn: sqlite3.Connection, checkpoint_path: Path) -> dict:
    """Feed the S6 input through the gate under `scope`; return the gate's receipt."""
    if scope == "store":
        rows, info, stored = load_run_input(checkpoint_path, include_sidecars=True)
        gate = CommitDedupGate(load_committed_index(conn), mode="report")
    elif scope == "run":
        rows, info, _stored = load_run_input(checkpoint_path, include_sidecars=True)
        gate = CommitDedupGate({}, mode="report")
        stored = set()  # a fresh store: nothing is ALREADY_STORED for this question
    else:  # batch: the raw S5 artifact on its own
        rows, info, stored = load_run_input(checkpoint_path, include_sidecars=False)
        gate = CommitDedupGate({}, mode="report")

    skipped = 0
    for fb in rows:
        if fb_id(fb) in stored:  # D-2933: an existing fb_id never reaches the gate
            skipped += 1
            continue
        gate.decide(fb)
        gate.observe(fb)
    receipt = gate.receipt()
    receipt["scope"] = scope
    receipt["input"] = info
    receipt["skipped_already_stored"] = skipped
    return receipt


def report(receipt: dict) -> None:
    """Print the evidence a human needs to make the report -> enforce call."""
    print(f"{'=' * 78}")
    print(f"scope={receipt['scope']}  mode={receipt['mode']} (report: nothing is written)")
    print(f"input           : {receipt['input']}")
    print(f"candidates      : {receipt['candidates']}  "
          f"(skipped, already in store: {receipt['skipped_already_stored']})")
    print(f"store indexed   : {receipt['store_rows_indexed']} row(s) / "
          f"{receipt['store_names_indexed']} normalized name(s)")
    print(f"kinds           : {receipt['kinds']}")
    print(f"actions         : {receipt['actions']}")
    linked = receipt["linked_duplicates"]
    print(f"\nWOULD LINK as duplicate (duplicate_of + QUARANTINE, never deleted): {len(linked)}")
    for d in linked[:SHOW_MAX]:
        ev = d.get("evidence", {})
        print(f"  {str(d['name'])[:44]:46} jaccard={ev.get('jaccard')} seq={ev.get('seq_ratio')} "
              f"richness {ev.get('richness_candidate')}->{ev.get('richness_canonical')} "
              f"canonical={str(d.get('canonical_fb_id'))[:12]}")
    if len(linked) > SHOW_MAX:
        print(f"  ... and {len(linked) - SHOW_MAX} more (see --out)")
    for key, rows in receipt["advisories"].items():
        print(f"\nADVISORY {key}: {len(rows)} (owner call, nothing linked)")
        for d in rows[:5]:
            print(f"  {str(d['name'])[:44]:46} kind={d['kind']} would={d['would']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only simulation of the D-2951 commit dedup gate.")
    ap.add_argument("--scope", choices=("batch", "run", "store"), default="run",
                    help="batch = S5 checkpoint alone; run = faithful S6 input (default); "
                         "store = faithful input against the live store")
    ap.add_argument("--checkpoint", default=str(STAGE5_CHECKPOINT), help="S5 checkpoint JSONL")
    ap.add_argument("--out", default=None, help="optional path to write the full receipt JSON")
    args = ap.parse_args()

    ckpt = Path(args.checkpoint)
    if not ckpt.exists():
        print(f"ERROR: checkpoint not found: {ckpt} (C16 fail-closed)")
        return 2

    conn = sqlite3.connect(f"file:{quote(str(DB_PATH))}?mode=ro", uri=True)
    receipt = run(args.scope, conn, ckpt)
    conn.close()
    report(receipt)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"\nfull receipt: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
