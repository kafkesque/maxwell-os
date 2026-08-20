#!/usr/bin/env python3
r"""Seed the S2 ``.gated_ids`` sidecar from a historical runner log (D2421).

The ``--reprocess-gated`` resume path in ``stage2_extract.py`` requires a prior
run's ``<checkpoint>.gated_ids`` sidecar to know which clusters were summary-gated
(``is_summary=true``) and should re-enter extraction. The T1.1 S2 checkpoint
(Aug 19) predates the D2421 code change, so no sidecar exists on disk — it must be
derived once from ``runner_t11_v3.log``.

This is a one-time deterministic bridge:

    runner_t11_v3.log
        └─ lines matching ``summary gated``
            └─ cluster IDs (``cluster_\d+(_s\d+)?(_sub\d+)?``)
                └─ dedup → validate vs. existing .segids → write .gated_ids

The marker and ID pattern are config-driven (``stage2.gated_seed_marker`` /
``stage2.gated_seed_id_regex``) per C12. Run-specific paths are CLI args (they vary
per run and are not stable config).

Exit codes: 0 = seeded, 1 = no gated IDs found, 2 = write failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_cfg() -> dict:
    """Load pipeline config (C12: marker + regex are data, not code)."""
    import yaml

    cfg_path = PROJECT_ROOT / "config" / "pipeline_config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("stage2", {})


def _atomic_write(path: Path, data: list[str]) -> str:
    """Crash-safe write (C6): tempfile → fsync → os.replace. Returns SHA-256."""
    payload = json.dumps(sorted(data))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".gated_ids.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return digest


def seed_gated_ids(log_path: Path, out_path: Path, segids_path: Path | None) -> int:
    """Extract unique gated cluster IDs from the log and write the sidecar."""
    cfg = _load_cfg()
    marker: str = cfg.get("gated_seed_marker", "summary gated")
    id_regex: str = cfg.get("gated_seed_id_regex", r"cluster_\d+(_s\d+)?(_sub\d+)?")
    id_pat = re.compile(id_regex)

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in log_text.splitlines() if marker in ln]

    seen: set[str] = set()
    ordered: list[str] = []
    duplicates = 0
    for ln in lines:
        m = id_pat.search(ln)
        if not m:
            continue
        cid = m.group(0)
        if cid in seen:
            duplicates += 1
        else:
            seen.add(cid)
            ordered.append(cid)

    if not ordered:
        print(f"❌ No gated cluster IDs found matching marker '{marker}' in {log_path}")
        return 1

    # Optional validation: gated IDs should be a subset of the processed .segids
    # (a gated cluster is still marked processed on its first pass). Report anomalies.
    not_in_segids: list[str] = []
    segids_total = 0
    if segids_path and segids_path.exists():
        segids = set(json.loads(segids_path.read_text(encoding="utf-8")))
        segids_total = len(segids)
        not_in_segids = [c for c in ordered if c not in segids]

    digest = _atomic_write(out_path, ordered)

    print(f"📄 Log:            {log_path}")
    print(f"   Marker lines:   {len(lines)}")
    print(f"   Unique IDs:     {len(ordered)}")
    print(f"   Duplicate hits: {duplicates}")
    if segids_path:
        print(f"   In .segids:     {len(ordered) - len(not_in_segids)} / {segids_total}")
        if not_in_segids:
            print(f"   ⚠️  NOT in .segids ({len(not_in_segids)}): {not_in_segids[:10]}{' …' if len(not_in_segids) > 10 else ''}")
    print(f"💾 Sidecar:        {out_path}")
    print(f"🔑 SHA-256:        {digest}")
    return 0


def main() -> int:
    from pipeline.pipeline_paths import STAGE2_CHECKPOINT

    parser = argparse.ArgumentParser(
        description="Seed the S2 .gated_ids sidecar from a historical runner log (D2421)."
    )
    parser.add_argument("--log", required=True, help="Path to the runner log (e.g. runner_t11_v3.log)")
    parser.add_argument(
        "--out",
        default=str(STAGE2_CHECKPOINT) + ".gated_ids",
        help="Output .gated_ids sidecar path (default: <S2 checkpoint>.gated_ids)",
    )
    parser.add_argument(
        "--validate-segids",
        default=None,
        help="Optional .segids path to cross-check gated IDs against processed clusters",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"❌ Log not found: {log_path}")
        return 1
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    segids_path = Path(args.validate_segids) if args.validate_segids else None

    return seed_gated_ids(log_path, out_path, segids_path)


if __name__ == "__main__":
    sys.exit(main())
