#!/usr/bin/env python3
"""Restore truncated FB names in S4/S5 checkpoints from the intact S2 checkpoint (P1-1 / BUG-149).

BUG-149: ``normalize_fb_name(max_words=5)`` was hardcoded in S4, truncating ~176/2830
FB names mid-thought (e.g. "Perceived Complexity and Deviation in Metaphor" ->
"Perceived Complexity and Deviation in"). The full names are intact in the S2
checkpoint; this script re-normalizes them with the now-config-driven
``FB_NAME_MAX_WORDS`` (8) and patches S4 + S5 in place — no re-run of S4/S5 required.

Matching is via ``source_clusters[0]`` (S4/S5) == ``source_cluster`` (S2), which D2350
guarantees preserves the real cluster id (fb_id drifts between S2->S4, so it is NOT a
reliable join key).

Only PURE truncations are patched: a name is rewritten iff its (suffix-stripped) current
form equals ``normalize_fb_name(raw, 5)`` — the exact output of the old hardcoded cap.
Names that S4 auto-disambiguated ("... (2)") are preserved with their suffix re-applied
to the restored base, so collisions are NOT re-introduced (D2069).

Writes are crash-safe (C6): tempfile -> flush -> fsync -> os.replace. Deterministic and
re-runnable; S2 remains the authoritative source for re-derivation.

Exit codes: 0 = patched (or nothing to do), 1 = S2/S4 missing.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_SUFFIX_RE = re.compile(r" \(\d+\)$")


def _quiet_normalize(raw: str, max_words: int, normalize) -> str:
    """Call normalize_fb_name without its truncation-warning side effect."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        return normalize(raw, max_words=max_words)


def build_name_map(s2_path: Path, normalize, max_words: int) -> dict[str, tuple[str, str]]:
    """Build {source_cluster: (old_n5, new_n8)} from the S2 checkpoint."""
    name_map: dict[str, tuple[str, str]] = {}
    with open(s2_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            sc = rec.get("source_cluster")
            raw = rec.get("name") or ""
            if sc:
                n5 = _quiet_normalize(raw, 5, normalize)
                n8 = _quiet_normalize(raw, max_words, normalize)
                name_map[str(sc)] = (n5, n8)
    return name_map


def _patch_name(current: str | None, entry: tuple[str, str]) -> str | None:
    """Return the corrected name, or None if no change is warranted.

    Only rewrites when the suffix-stripped current name equals the old-cap output (n5)
    AND the new cap actually changes it (n8 != n5) — i.e. a genuine truncation. Any
    "(N)" disambiguation suffix is preserved and re-applied to the restored base.
    """
    n5, n8 = entry
    if not current or n8 == n5:
        return None
    m = _SUFFIX_RE.search(current)
    suffix = m.group(0) if m else ""
    base = _SUFFIX_RE.sub("", current) if suffix else current
    if base == n5:
        return n8 + suffix
    return None


def _atomic_patch(path: Path, name_map: dict[str, tuple[str, str]]) -> tuple[int, int]:
    """Stream-patch `path` via source_clusters[0] -> corrected name. Crash-safe."""
    changed = 0
    total = 0
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".restore.tmp")
    try:
        with os.fdopen(fd, "w") as out:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    total += 1
                    keys = rec.get("source_clusters") or []
                    if keys:
                        entry = name_map.get(str(keys[0]))
                        if entry:
                            new_name = _patch_name(rec.get("name"), entry)
                            if new_name is not None and new_name != rec.get("name"):
                                rec["name"] = new_name
                                changed += 1
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return changed, total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore truncated FB names in S4/S5 from the intact S2 checkpoint (P1-1/BUG-149)."
    )
    parser.add_argument("--run-id", default=None, help="run_id to patch (e.g. t11); overrides MAXWELL_RUN_ID")
    parser.add_argument("--s2", default=None, help="S2 checkpoint path (overrides --run-id derivation)")
    parser.add_argument("--s4", default=None, help="S4 checkpoint path (overrides --run-id derivation)")
    parser.add_argument("--s5", default=None, help="S5 checkpoint path (overrides --run-id derivation)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    if args.run_id:
        os.environ["MAXWELL_RUN_ID"] = args.run_id

    from pipeline.pipeline_paths import FB_NAME_MAX_WORDS, STAGE2_CHECKPOINT, STAGE4_CHECKPOINT, STAGE5_CHECKPOINT
    from pipeline.stage4_merge import normalize_fb_name

    s2_path = Path(args.s2) if args.s2 else Path(STAGE2_CHECKPOINT)
    s4_path = Path(args.s4) if args.s4 else Path(STAGE4_CHECKPOINT)
    s5_path = Path(args.s5) if args.s5 else Path(STAGE5_CHECKPOINT)

    if not s2_path.exists():
        print(f"❌ S2 checkpoint not found: {s2_path}")
        return 1
    if not s4_path.exists():
        print(f"❌ S4 checkpoint not found: {s4_path}")
        return 1

    name_map = build_name_map(s2_path, normalize_fb_name, FB_NAME_MAX_WORDS)
    print(f"📄 S2 name map: {len(name_map)} clusters")
    print(f"   FB_NAME_MAX_WORDS: {FB_NAME_MAX_WORDS}")

    for label, path in (("S4", s4_path), ("S5", s5_path)):
        if not path.exists():
            print(f"   ⚠️  {label} checkpoint not found — skipping ({path})")
            continue
        if args.dry_run:
            changed = total = 0
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    total += 1
                    keys = rec.get("source_clusters") or []
                    if keys:
                        entry = name_map.get(str(keys[0]))
                        if entry:
                            new_name = _patch_name(rec.get("name"), entry)
                            if new_name is not None and new_name != rec.get("name"):
                                changed += 1
            print(f"   🔍 {label}: would change {changed}/{total} names (dry-run)")
            continue
        changed, total = _atomic_patch(path, name_map)
        print(f"   ✅ {label}: patched {changed}/{total} names")

    return 0


if __name__ == "__main__":
    sys.exit(main())
