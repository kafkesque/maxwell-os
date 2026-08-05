#!/usr/bin/env python3
"""
io_guard.py — Safe I/O operations for pipeline output protection.

§F of FABLE-SOLUTIONS-2026-06-11. Three mechanisms:

1. safe_write(path, content, shrink_guard=True):
   Atomic write via temp file + os.replace(). Shrink guard refuses to
   replace an existing file with content >10% smaller unless --force-shrink.
   Prevents the exact bug that destroyed 525 D5 principles (partial-state
   checkpoint overwrite).

2. supersede_dir(path):
   Batch re-runs never delete prior output. Call supersede_dir, which
   MOVES existing batch dir to backup/superseded/{name}-{timestamp}/
   and returns a fresh empty path. Deletion-by-overwrite on re-runs is
   mechanically impossible.

3. PrincipleJournal(path):
   Append-only journal. Every accepted principle appends one JSONL line.
   Append-only files cannot be destroyed by overwrite bugs.

Usage:
    from tools.io_guard import safe_write, supersede_dir, PrincipleJournal

    # Atomic write with shrink protection
    safe_write("/path/to/output.json", json.dumps(data))

    # Safe re-run (moves old data, returns fresh path)
    fresh = supersede_dir("/path/to/5.generated/batch_001")

    # Append-only journal
    journal = PrincipleJournal("principles.append.jsonl")
    journal.append(principle_data)
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def safe_write(path, content, shrink_guard=True, force_shrink=False):
    """Atomic file write with shrink guard.

    Args:
        path: Target file path (string or Path).
        content: String content to write.
        shrink_guard: If True, refuse to replace existing file with
                      content >10% smaller (partial-state guard).
        force_shrink: Bypass shrink guard (use explicitly).

    Raises:
        ValueError: If shrink guard triggers and not force_shrink.
    """
    path = Path(path)
    content_bytes = content.encode("utf-8") if isinstance(content, str) else content
    content_size = len(content_bytes)

    # Shrink guard: existing file replaced by much smaller content
    if shrink_guard and not force_shrink and path.exists():
        existing_size = path.stat().st_size
        if existing_size > 0 and content_size < existing_size * 0.9:
            raise ValueError(
                f"SHRINK GUARD: {path.name} would shrink "
                f"{existing_size} bytes → {content_size} bytes "
                f"({(1 - content_size / existing_size) * 100:.1f}% reduction). "
                f"This is a partial-state overwrite (the exact bug that "
                f"destroyed 525 D5 principles). "
                f"Use force_shrink=True to override."
            )

    # Atomic write: tempfile → fsync → os.replace (C6)
    # D2177: os.fsync(fd) is MANDATORY before os.close(). Without it,
    # data sits in the OS buffer — a kernel panic or power loss between
    # os.write() and the OS flush cycle corrupts the checkpoint.
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content_bytes)
        os.fsync(fd)  # D2177: flush to physical media before close
        os.close(fd)
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def supersede_dir(path):
    """Move existing directory to backup/superseded/ and return fresh path.

    Batch re-runs call this instead of rm -rf. The old data is preserved
    in backup/superseded/ until the superseding batch passes S7.

    Args:
        path: Directory path to supersede (string or Path).

    Returns:
        Path to the fresh (now-empty) directory.
    """
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Destination: backup/superseded/{dir_name}-{timestamp}/
    backup_root = path.parent.parent / "backup" / "superseded"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_root / f"{path.name}-{timestamp}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))

    # Create fresh empty directory
    path.mkdir(parents=True, exist_ok=True)

    print(f"  🔄 Superseded: {path.name} → {dest.relative_to(path.parent.parent)}")
    return path


class PrincipleJournal:
    """Append-only journal for accepted principles.

    Append-only files cannot be destroyed by overwrite bugs.
    If every checkpoint dies, the journal replays.

    Usage:
        journal = PrincipleJournal("principles.append.jsonl")
        journal.append({"principle": "...", "cluster_id": 42})
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Touch file if not exists
        if not self.path.exists():
            self.path.write_text("")

    def append(self, record):
        """Append one JSONL line. Thread-safe via append-mode open."""
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(self.path, "a") as f:
            f.write(line)

    def replay(self):
        """Yield all records in order."""
        if not self.path.exists():
            return
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    @property
    def count(self):
        """Number of records in the journal."""
        count = 0
        for _ in self.replay():
            count += 1
        return count
