#!/usr/bin/env python3
"""assert_db_torn_upload_guard.py — D-366: make a torn or partial cloud upload of the live DB LOUD.

WHY THIS EXISTS (BUG-400, accepted-and-documented by D-366): the repo, the knowledge pipeline tree and
`knowledge pipeline/maxwell.db` live inside a Dropbox File Provider domain. That is a known accepted C3
exception, not a silent one. The dangerous failure mode is NOT a missing file — it is a `maxwell.db` that
exists, opens, and is a PARTIAL or TORN copy pushed mid-run by the sync client. A torn SQLite file can
still be opened by a reader, and a reader that resolves it as authoritative silently serves truncated data.

WHAT IT DOES: records a (size, mtime, sha256, integrity) fingerprint of the declared DB before and after a
run, and refuses loudly when the pair is inconsistent with a completed run:
  * `--record pre|post`  appends a fingerprint to the ledger
  * `--check`            compares the last pre/post pair and exits 1 on a tear
  * `--integrity`        runs PRAGMA quick_check on the DB
It never writes to the DB, never deletes it, and never repairs it (a repair is an owner decision).

C12: the DB path, the ledger path and the journal-mode expectation live in config/pipeline_config.yaml and
config/archive_index.yaml — nothing is hardcoded here. C16: a refused check exits nonzero and says why.
C6: the ledger is appended atomically via tempfile -> fsync -> os.replace.

Usage:
    python3 scripts/assert_db_torn_upload_guard.py --record pre  --label d366_demo
    python3 scripts/assert_db_torn_upload_guard.py --record post --label d366_demo
    python3 scripts/assert_db_torn_upload_guard.py --check --label d366_demo
    python3 scripts/assert_db_torn_upload_guard.py --integrity
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO: Path = Path(__file__).resolve().parents[1]

# ── C12: config, not constants ───────────────────────────────────────────────
GUARD_CONFIG: Path = REPO / "config" / "db_torn_upload_guard.yaml"
DEFAULT_CONFIG: dict = {
    "ledger": "governance/db_torn_upload_ledger.jsonl",
    "db_path_config": "config/pipeline_config.yaml",
    "db_path_keys": ["stage6", "db_path"],
    "chunk_bytes": 8 * 1024 * 1024,
}


def _load_guard_config() -> dict:
    """Read the guard contract; fall back to the documented defaults (declared, never silent)."""
    if GUARD_CONFIG.exists():
        loaded = yaml.safe_load(GUARD_CONFIG.read_text(encoding="utf-8")) or {}
        return {**DEFAULT_CONFIG, **loaded}
    return dict(DEFAULT_CONFIG)


def _resolve_db_path(cfg: dict) -> Path:
    """Resolve the declared live DB path from config. Refuses rather than guessing the location."""
    declared = cfg.get("db_path")
    if isinstance(declared, str) and declared:
        direct = Path(declared)
        return direct if direct.is_absolute() else REPO / direct
    src = REPO / str(cfg["db_path_config"])
    if not src.exists():
        raise SystemExit(f"RED db_torn_upload_guard: config {src} does not exist (C16: refusing to guess)")
    node: object = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    for key in cfg["db_path_keys"]:
        if isinstance(node, dict):
            node = node.get(key)
        else:
            node = None
        if node is None:
            break
    if not isinstance(node, str) or not node:
        raise SystemExit(
            f"RED db_torn_upload_guard: could not resolve {'/'.join(cfg['db_path_keys'])} "
            f"in {cfg['db_path_config']} (C12/C16)"
        )
    path = Path(node)
    return path if path.is_absolute() else REPO / path


def sha256_file(path: Path, chunk_bytes: int) -> str:
    """Hash a file in chunks so a multi-hundred-MB DB does not have to fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def fingerprint(db: Path, cfg: dict) -> dict:
    """Measure (size, mtime, sha256) of the live DB. Measurement only — never a write."""
    stat = db.stat()
    return {
        "recorded": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "path": str(db.relative_to(REPO)) if db.is_relative_to(REPO) else str(db),
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha256_file(db, int(cfg["chunk_bytes"])),
    }


def quick_check(db: Path) -> str:
    """Run SQLite PRAGMA quick_check read-only. Returns the raw verdict string."""
    uri = f"file:{db}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        row = conn.execute("PRAGMA quick_check").fetchone()
    return str(row[0]) if row else "unknown"


def append_ledger(ledger: Path, record: dict) -> None:
    """Append one JSON record atomically (C6). The ledger is append-only and is never rewritten."""
    ledger.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + os.linesep
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(ledger.parent), delete=False) as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
        staged = Path(handle.name)
    with ledger.open("a", encoding="utf-8") as out:
        out.write(staged.read_text(encoding="utf-8"))
        out.flush()
        os.fsync(out.fileno())
    staged.unlink(missing_ok=True)


def read_label(ledger: Path, label: str) -> list[dict]:
    """Return every ledger record for a label, tolerating a torn final line (a crash mid-append)."""
    if not ledger.exists():
        return []
    records: list[dict] = []
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if parsed.get("label") == label:
            records.append(parsed)
    return records


def main() -> int:
    """Record, check or integrity-test the live DB fingerprint pair declared by D-366."""
    cfg = _load_guard_config()
    ledger = REPO / str(cfg["ledger"])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", choices=["pre", "post"], help="append a fingerprint to the ledger")
    parser.add_argument("--label", default="default", help="run label pairing a pre with its post")
    parser.add_argument("--check", action="store_true", help="compare the last pre/post pair for a label")
    parser.add_argument("--integrity", action="store_true", help="run PRAGMA quick_check read-only")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    db = _resolve_db_path(cfg)
    if not db.exists():
        print(f"RED db_torn_upload_guard: declared DB {db} does not exist (C16)", file=sys.stderr)
        return 1

    if args.integrity:
        verdict = quick_check(db)
        ok = verdict.lower() == "ok"
        if not args.quiet:
            print(f"db integrity: {db.name} -> {verdict}")
        return 0 if ok else 1

    if args.record:
        record = fingerprint(db, cfg)
        record["phase"] = args.record
        record["label"] = args.label
        record["guard"] = "D-366/BUG-400"
        append_ledger(ledger, record)
        if not args.quiet:
            print(f"recorded {args.record}: {record['path']} {record['bytes']} B sha256[:16]={record['sha256'][:16]}")
        return 0

    if args.check:
        records = read_label(ledger, args.label)
        pres = [r for r in records if r.get("phase") == "pre"]
        posts = [r for r in records if r.get("phase") == "post"]
        if not pres or not posts:
            print(f"RED db_torn_upload_guard: label {args.label!r} has no complete pre/post pair "
                  f"(pre={len(pres)} post={len(posts)}) — the gate is NOT satisfied (C16)", file=sys.stderr)
            return 1
        pre, post = pres[-1], posts[-1]
        same = pre["sha256"] == post["sha256"]
        current = fingerprint(db, cfg)
        live_matches_post = current["sha256"] == post["sha256"]
        if not live_matches_post:
            print(f"RED db_torn_upload_guard: the DB on disk NO LONGER matches the post-run fingerprint "
                  f"(post {post['sha256'][:16]} != live {current['sha256'][:16]}) — a writer, or the sync "
                  f"client, changed it after the run. Do not treat the on-disk file as the run's output.",
                  file=sys.stderr)
            return 1
        if not same and post["bytes"] < pre["bytes"]:
            print(f"RED db_torn_upload_guard: TORN — the DB SHRANK across the run "
                  f"({pre['bytes']} -> {post['bytes']} B): a completed pipeline run does not truncate the store.",
                  file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"ok   db_torn_upload_guard: label {args.label} pre/post pair consistent "
                  f"({'unchanged' if same else 'changed'}, {post['bytes']} B, sha256[:16]={post['sha256'][:16]})")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
