#!/usr/bin/env python3
"""readmit_disposed.py — re-convert the S0 artefacts D-3086 disposed (verdict `quarantine_and_reconvert`).

Single source of truth = the disposition receipts declared at `disposition_receipt_prefix` in
config/ingest_identity_gate.yaml (BUG-935/D-3099). A receipt line whose `verdict` is
`quarantine_and_reconvert`, whose `applied` is true, and whose `artefact` is NOT on disk (the pen
was purged) names a work whose source `container` is still present and whose checkpoint row dispose
dropped (D-3086). Re-converting runs the FIXED stage0 engine (placeholder image mode,
stage0.artifact.image_export_mode) over exactly those containers, so the shape gate admits what the
old engine wrote wrong.

WHY A DRIVER AND NOT A BARE `stage0_convert.py` RUN. A bare run scans every source file not in the
checkpoint (measured 2026-10-18: 448 of 1,770 files under books/) and would convert the whole
backlog, not the disposed set. This driver scopes the scan to the receipted containers so the blast
radius is the disposed set and nothing else (the cascade rule).

--dry-run prints the exact containers + their missing artefacts and converts nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

import pipeline.stage0_convert as s0  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402

_CFG = Path(__file__).resolve().parent.parent / "config" / "ingest_identity_gate.yaml"


def _decl(key: str) -> str:
    """Read one declared string from ingest_identity_gate.yaml, fail-closed (C16)."""
    value = _find_key(yaml.safe_load(_CFG.read_text(encoding="utf-8")), key)
    if not value:
        raise SystemExit(f"FATAL: no {key!r} declared in ingest_identity_gate.yaml (C16)")
    return value


def _find_key(doc: Any, key: str) -> str | None:
    """Return the first string value of `key` anywhere in the document (the declared single home)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k == key and isinstance(v, str):
                return v
            found = _find_key(v, key)
            if found:
                return found
    elif isinstance(doc, list):
        for item in doc:
            found = _find_key(item, key)
            if found:
                return found
    return None


def _receipt_base() -> tuple[Path, str]:
    """The (folder, stem) the disposition receipts live under, read from the declared prefix (C12)."""
    prefix = _decl("disposition_receipt_prefix")
    base = Path(__file__).resolve().parent.parent / prefix
    return base.parent, base.name


def terminal_containers() -> set[str]:
    """Resolved container paths already recorded terminal (`skipped_image_heavy` — a policy skip, never re-attempted)."""
    folder, stem = _receipt_base()
    verdict = _decl("disposition_terminal_verdict")
    out: set[str] = set()
    for receipt in sorted(folder.glob(f"{stem}*.applied.jsonl")):
        for line in receipt.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("applied") and rec.get("verdict") == verdict:
                container = Path(str(rec.get("container") or ""))
                if container.name:
                    out.add(str(container.resolve()))
    return out


def disposed_containers() -> list[Path]:
    """The source container of every DISPOSED artefact whose .md is still missing on disk — MINUS the terminal set.

    A container the fixed engine already SKIPPED (no text layer, scan_policy=skip) is recorded terminal so this
    function does not hand it back to be re-converted forever (BUG-923 / D-3086 readmit closure).
    """
    folder, stem = _receipt_base()
    terminal = terminal_containers()
    containers: list[Path] = []
    for receipt in sorted(folder.glob(f"{stem}*.applied.jsonl")):
        for line in receipt.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if not (rec.get("applied") and rec.get("verdict") == "quarantine_and_reconvert"):
                continue
            container = Path(str(rec.get("container") or ""))
            artefact = Path(str(rec.get("artefact") or ""))
            if str(container.resolve()) in terminal:
                continue
            if container.exists() and not artefact.exists():
                containers.append(container)
    seen: set[str] = set()
    unique: list[Path] = []
    for c in containers:
        key = str(c.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def record_terminal(containers: list[Path]) -> Path:
    """Write ONE disposition receipt that closes `containers` as `skipped_image_heavy` (terminal, applied).

    The disposition vocabulary already names `skipped_image_heavy` as the terminal verdict (config, C12); this
    receipt is the D-3036 act — the trace that turns "missing, keep re-attempting" into "named, policy-skipped".
    """
    folder, stem = _receipt_base()
    verdict = _decl("disposition_terminal_verdict")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rows: list[dict[str, Any]] = []
    for c in containers:
        artefact = c.with_suffix(".md")
        rows.append({
            "schema_version": "1.0",
            "gen_model": "none (deterministic)",
            "pipeline_commit": "readmit_disposed",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "books_dir": str(s0.BOOKS_DIR),
            "applied": True,
            "verdict": verdict,
            "container": str(c),
            "artefact": str(artefact),
            "reason": "no extractable text layer (scan_policy=skip): a policy outcome, never a fault (BUG-923)",
        })
    receipt = folder / f"{stem}{stamp}_TERMINAL.applied.jsonl"
    safe_write(receipt, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-convert the D-3086-disposed S0 artefacts via the fixed engine")
    parser.add_argument("--dry-run", action="store_true", help="print the exact set and convert nothing")
    parser.add_argument("--record-terminal", action="store_true",
                        help="record every still-missing container as terminal (skipped_image_heavy) and convert nothing")
    args = parser.parse_args()

    containers = disposed_containers()
    print(f"disposed containers whose artefact is still missing: {len(containers)}")
    for c in containers:
        label = str(c.relative_to(s0.BOOKS_DIR)) if c.is_relative_to(s0.BOOKS_DIR) else str(c)
        print(f"  {label}")
    if args.record_terminal:
        if not containers:
            print("nothing to record: the disposed set is already terminal")
            return 0
        receipt = record_terminal(containers)
        print(f"recorded {len(containers)} containers as terminal -> {receipt}")
        return 0
    if args.dry_run or not containers:
        return 0

    #: Scope the scan to exactly these containers. run_stage0's corpus-wide scan is the whole backlog;
    #: this driver exists to keep the blast radius at the disposed set (the cascade rule). The override is
    #: process-local and documented here — the receipts are the single source of truth (D-3034).
    s0.find_books = lambda books_dir, subdir=None: [c for c in containers if c.is_relative_to(books_dir)]  # type: ignore[assignment]
    result = s0.run_stage0(books_dir=s0.BOOKS_DIR)
    if result is None:
        return 0
    failed_count, converted_count = result
    print(f"re-converted: {converted_count} | failed: {failed_count}")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
