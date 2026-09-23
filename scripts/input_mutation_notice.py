#!/usr/bin/env python3
"""scripts/input_mutation_notice.py - a repair script that rewrites a DECLARED stage input must say so.

Root cause of C-3/BUG-376: `reclassify_merged_axis.py`, `sync_checkpoint_from_db.py`, `apply_bug150_*` and
friends rewrite `knowledge pipeline/stage4_merge/t11/checkpoint_enriched.jsonl` IN PLACE. Downstream, the S5
fingerprint still declares the old bytes, so a completed 7995-row run silently became uncitable and the next
run discards it (~1.3 h). The config-side acknowledgement list cannot scale to that.

Standing rule (D-340): a DECLARED stage input is immutable; a writer either writes a NEW artifact, or it
publishes a MUTATION NOTICE next to the artifact. `scripts/verify_declared_inputs.py` accepts a mismatch when a
notice covers it - so the exception is authored by the writer AT THE MOMENT of the change, never hand-edited
into config afterwards.

Usage (from inside a repair script, before it rewrites):
  python3 scripts/input_mutation_notice.py --artifact <path> --issue BUG-376 --before <sha256_before> \
      --reason "kind-swap repair (T-311)"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTICE_SUFFIX = ".mutation_notice.json"


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file, streamed."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_notice(artifact: Path, before: str, reason: str, issue: str) -> Path:
    """Atomically write the mutation notice for ``artifact`` (C6) and return its path."""
    if not artifact.exists():
        raise FileNotFoundError(f"{artifact} does not exist - cannot declare a mutation of nothing")
    doc = {
        "schema_version": "1.0",
        "artifact": str(artifact.relative_to(PROJECT_ROOT)) if artifact.is_absolute() else str(artifact),
        "sha256_before": before,
        "sha256_after": sha256_file(artifact),
        "bytes_after": artifact.stat().st_size,
        "reason": reason,
        "issue": issue,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "written_by": os.path.basename(sys.argv[0]),
        "rule": "D-340: a declared stage input is immutable; an in-place writer must publish this notice",
    }
    out = artifact.with_name(artifact.name + NOTICE_SUFFIX)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=2) + "\n"); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, out)
    return out


def main() -> int:
    """CLI: declare an in-place mutation of a declared stage input."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--before", required=True, help="sha256 of the artifact BEFORE the mutation")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--issue", default="D-340")
    a = ap.parse_args()
    art = Path(a.artifact)
    out = write_notice(art if art.is_absolute() else PROJECT_ROOT / art, a.before, a.reason, a.issue)
    print(f"mutation notice written: {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
