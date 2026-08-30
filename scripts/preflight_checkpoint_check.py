#!/usr/bin/env python3
"""
preflight_checkpoint_check.py — Checkpoint boundary + SHA-256 manifest gate.

Authority: BUG-188 hardening (D2487). Run BEFORE S5 consumes S4 output.

Detects the BUG-188 failure class — a JSONL checkpoint silently truncated at a
byte or record boundary that a naive reader accepts:

  1. BOUNDARY — every non-empty line must be standalone JSON (catches a partial
     tail record cut mid-object), and the file must end on a newline-terminated
     complete record.
  2. RECORD COUNT — on-disk count vs. manifest record_count (catches a clean cut
     at a trailing `\n` that drops WHOLE records — invisible to a line reader).
  3. SHA-256 — full-file digest vs. manifest (catches any byte corruption).

Usage:
    python3 scripts/preflight_checkpoint_check.py --check <checkpoint.jsonl>
    python3 scripts/preflight_checkpoint_check.py --write-manifest <checkpoint.jsonl>
    python3 scripts/preflight_checkpoint_check.py --check <checkpoint.jsonl> --expect-count N

Exit 0 = clean; non-zero = fail-loud (do NOT consume the checkpoint).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.io_guard import safe_write  # noqa: E402

MANIFEST_SUFFIX = ".manifest.json"


def _sha256(path: Path) -> str:
    """Stream the file in 1 MiB chunks so multi-GB checkpoints don't blow RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def boundary_check(path: Path) -> tuple[int, list[str]]:
    """Return (record_count, problems). A problem means a partial/corrupt record."""
    problems: list[str] = []
    count = 0
    last_had_newline = True
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            last_had_newline = line.endswith("\n")
            if not line.strip():
                continue
            try:
                json.loads(line)
                count += 1
            except json.JSONDecodeError as e:
                problems.append(f"line {lineno}: unparseable/partial JSON — {e}")
    if not last_had_newline:
        problems.append("file does not end with a newline (possible tail truncation)")
    return count, problems


def write_manifest(path: Path) -> int:
    """Boundary-check, then persist sha256 + record_count as a sidecar manifest."""
    count, problems = boundary_check(path)
    if problems:
        print(f"❌ Refusing to write manifest — checkpoint failed boundary check: {path}")
        for p in problems:
            print(f"   {p}")
        return 1
    manifest = {
        "checkpoint": str(path.resolve()),
        "checkpoint_sha256": _sha256(path),
        "record_count": count,
        "boundary_ok": True,
        "timestamp": time.time(),
        "writer": "preflight_checkpoint_check.py",
    }
    mpath = Path(str(path) + MANIFEST_SUFFIX)
    safe_write(mpath, json.dumps(manifest, indent=2, ensure_ascii=False), force_shrink=True)
    print(f"✅ Manifest written: {mpath.name}")
    print(f"   record_count={count}  sha256={manifest['checkpoint_sha256'][:16]}…")
    return 0


def check(path: Path, expect_count: int | None) -> int:
    """Verify boundary, then sha256 + record count against manifest / --expect-count."""
    if not path.exists():
        print(f"❌ Checkpoint not found: {path}")
        return 1
    count, problems = boundary_check(path)
    if problems:
        print(f"❌ BOUNDARY FAIL: {path}")
        for p in problems:
            print(f"   {p}")
        return 1
    print(f"✅ Boundary OK: {count} records, every line standalone JSON, newline-terminated")

    mpath = Path(str(path) + MANIFEST_SUFFIX)
    if mpath.exists():
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — fail-loud, not silent
            print(f"❌ Manifest unreadable: {mpath} ({e})")
            return 1
        digest = _sha256(path)
        if manifest.get("checkpoint_sha256") and digest != manifest["checkpoint_sha256"]:
            print(f"❌ SHA-256 MISMATCH: on-disk {digest[:16]}… vs manifest {str(manifest['checkpoint_sha256'])[:16]}…")
            return 1
        print(f"✅ SHA-256 matches manifest: {digest[:16]}…")
        if manifest.get("record_count") is not None and manifest["record_count"] != count:
            print(f"❌ RECORD COUNT MISMATCH: on-disk {count} vs manifest {manifest['record_count']}")
            return 1
        print(f"✅ Record count matches manifest: {count}")
    elif expect_count is not None:
        if expect_count != count:
            print(f"❌ RECORD COUNT MISMATCH: on-disk {count} vs --expect-count {expect_count}")
            return 1
        print(f"✅ Record count matches --expect-count: {count}")
    else:
        print("⚠️  No manifest and no --expect-count — boundary verified but integrity not pinned.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Checkpoint boundary + sha256 manifest gate (D2487)")
    parser.add_argument("path", help="Checkpoint JSONL path")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Verify boundary + manifest/sha256/count")
    group.add_argument("--write-manifest", action="store_true", help="Write manifest after a successful run")
    parser.add_argument("--expect-count", type=int, default=None, help="Expected record count (no manifest fallback)")
    args = parser.parse_args()

    path = Path(args.path)
    if args.write_manifest:
        return write_manifest(path)
    return check(path, args.expect_count)


if __name__ == "__main__":
    sys.exit(main())
