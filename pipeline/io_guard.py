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


def load_jsonl(path, *, context: str = "", fail_closed: bool = True) -> list[dict]:
    """Load a JSONL file, one JSON object per line — fail-closed (D2332).

    Guards against pretty-printed JSON (multi-line records) being misread as
    JSONL. A pretty-printed S2 checkpoint parses as only a *subset* of lines,
    silently corrupting the downstream merge/verify. This loader raises on any
    non-empty line that is not standalone JSON so corruption is loud, not silent.

    Args:
        path: Path to the JSONL file.
        context: Human-readable stage name for error messages (e.g. "S2 checkpoint").
        fail_closed: If True (default), raise on any unparseable non-empty line.

    Returns:
        List of parsed dict records, in file order.
    """
    path = Path(path)
    records: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as e:
                if not fail_closed:
                    continue
                label = f"{context} " if context else ""
                raise ValueError(
                    f"FATAL: {label}JSONL parse failure in {path} line {lineno}: {e}. "
                    f"File appears pretty-printed/multi-line, not one-JSON-object-per-line. "
                    f"Regenerate the checkpoint (re-run the upstream stage) — do not hand-edit."
                ) from e
    return records


def _write_all_bytes(fd: int, data: bytes) -> None:
    """Write all bytes to fd, looping to handle partial writes (C16 fail-loud).

    os.write() is NOT guaranteed to write the entire buffer in one call — on
    macOS write(2) caps a single call at 2**31-1 bytes, and the previous code
    ignored the return value, silently truncating large files (BUG-188). Loop
    until every byte is written; raise if a write makes no progress.
    """
    view = memoryview(data)
    written_total = 0
    while written_total < len(data):
        n = os.write(fd, view[written_total:])
        if n <= 0:
            raise OSError(
                f"os.write returned {n} after {written_total}/{len(data)} bytes — "
                f"write stalled; refusing to leave a truncated file"
            )
        written_total += n


def safe_write(path, content, shrink_guard=True, force_shrink=False):
    """Atomic file write with shrink guard + truncation detection (BUG-188).

    Args:
        path: Target file path (string or Path).
        content: String or bytes content to write.
        shrink_guard: If True, refuse to replace existing file with
                      content >10% smaller (partial-state guard).
        force_shrink: Bypass shrink guard (use explicitly).

    Raises:
        ValueError: If shrink guard triggers and not force_shrink.
        IOError: If the written byte count does not match the intended content
                 (C16 fail-loud — a partial write is never silently accepted).
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
        _write_all_bytes(fd, content_bytes)
        os.fsync(fd)  # D2177: flush to physical media before close
        # BUG-188: verify the FULL byte count landed on disk BEFORE replace.
        st = os.fstat(fd)
        if st.st_size != content_size:
            raise IOError(
                f"TRUNCATION: {path.name} wrote {st.st_size} bytes but expected "
                f"{content_size} bytes (missing {content_size - st.st_size}). "
                f"Refusing to replace with a partial file."
            )
        os.close(fd)
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure (fd may already be closed)
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def safe_write_jsonl(path, records, shrink_guard=True, force_shrink=False):
    """Stream records to a JSONL file atomically (BUG-188: no multi-GB join).

    Unlike safe_write — which requires the caller to build one giant in-memory
    string — this writes one JSON object per line incrementally to a temp file,
    fsyncs, verifies both byte count AND record count on disk, then atomically
    replaces the target. This is the crash-safe + fail-loud writer for large
    JSONL checkpoints (the S4 checkpoint exceeded 2GB when built as a single
    join string and was silently truncated).

    Args:
        path: Target JSONL path.
        records: Iterable of dict records.
        shrink_guard: If True, refuse to replace an existing larger file with
                      >10% smaller content (partial-state guard).
        force_shrink: Bypass shrink guard.

    Raises:
        ValueError: If shrink guard triggers and not force_shrink.
        IOError: If the on-disk byte/record count does not match the records.

    Returns:
        Number of records written.
    """
    path = Path(path)
    records = list(records)  # materialize for count verification (cheap: refs)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        expected_bytes = 0
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records:
                line = json.dumps(rec, ensure_ascii=False) + "\n"
                f.write(line)
                expected_bytes += len(line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())  # D2177: flush before close
        # fd is now closed by the fdopen context; verify bytes landed on disk
        actual_bytes = os.stat(tmp_path).st_size
        if actual_bytes != expected_bytes:
            raise IOError(
                f"TRUNCATION: {path.name} wrote {actual_bytes} bytes but expected "
                f"{expected_bytes} bytes (missing {expected_bytes - actual_bytes})."
            )
        # Shrink guard (mirror safe_write)
        if shrink_guard and not force_shrink and path.exists():
            existing_size = path.stat().st_size
            if existing_size > 0 and actual_bytes < existing_size * 0.9:
                raise ValueError(
                    f"SHRINK GUARD: {path.name} would shrink "
                    f"{existing_size} bytes → {actual_bytes} bytes "
                    f"({(1 - actual_bytes / existing_size) * 100:.1f}% reduction). "
                    f"Use force_shrink=True to override."
                )
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return len(records)


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
        """Append one JSONL line. Thread-safe via O_APPEND (fail-loud write).

        A short/partial append is never silently accepted (BUG-188 class) —
        _write_all_bytes loops the os.write and raises if it stalls.
        """
        line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(self.path, os.O_APPEND | os.O_WRONLY)
        try:
            _write_all_bytes(fd, line)
            os.fsync(fd)  # D2177: durable before returning
        finally:
            os.close(fd)

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
