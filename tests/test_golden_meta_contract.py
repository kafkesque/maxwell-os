"""D2504 — `.golden_meta.json` ⇄ live golden file contract guard.

The golden few-shot provenance sidecar (`config/golden/.golden_meta.json`)
must never drift from the actual golden file it stamps. A silently-edited
golden set that ships with a stale hash/count is exactly the BUG-201 class
(silent truncation) the roundtable flagged. This CI guard fails closed on:

  - hash drift    — golden bytes changed without re-stamping `golden_sha256`
  - count drift   — `total_examples` no longer equals the real example count
  - header drift  — YAML `meta.total_examples` no longer equals the example list
  - commit drift  — `pipeline_commit` is not a valid commit reachable in this repo

The expected values live in the JSON (data, not code — C12); the golden path
comes from `stage2.golden_path` (config, not hardcoded).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from pipeline.pipeline_paths import S2_GOLDEN_PATH

ROOT = Path(__file__).resolve().parent.parent
META_PATH = ROOT / "config" / "golden" / ".golden_meta.json"


def _load_meta() -> dict:
    return json.loads(META_PATH.read_text())


def _load_golden() -> dict:
    return yaml.safe_load((ROOT / S2_GOLDEN_PATH).read_text())


def test_golden_meta_hash_matches_actual() -> None:
    """`golden_sha256` must be the live SHA-256 of the golden file bytes."""
    meta = _load_meta()
    actual = hashlib.sha256((ROOT / S2_GOLDEN_PATH).read_bytes()).hexdigest()
    assert meta.get("golden_sha256") == actual, (
        "golden file changed without re-stamping .golden_meta.json — "
        "run the re-stamp (author_golden.py step 5) or revert the edit"
    )


def test_golden_meta_count_matches_actual() -> None:
    """`total_examples` must equal the real example count AND the YAML header."""
    meta = _load_meta()
    data = _load_golden()
    actual = len(data.get("examples", []))
    declared = data.get("meta", {}).get("total_examples")
    assert meta.get("total_examples") == actual, (
        f".golden_meta.json total_examples={meta.get('total_examples')} != "
        f"actual {actual}"
    )
    assert declared == actual, (
        f"golden YAML meta.total_examples={declared} != actual {actual}"
    )


def test_golden_meta_count_arithmetic() -> None:
    """convergent_positives + hard_negatives must equal total_examples."""
    meta = _load_meta()
    total = meta.get("total_examples")
    conv = meta.get("convergent_positives")
    neg = meta.get("hard_negatives")
    if total is not None and conv is not None and neg is not None:
        assert conv + neg == total, (
            f"convergent_positives({conv}) + hard_negatives({neg}) "
            f"!= total_examples({total})"
        )


def test_golden_meta_pipeline_commit_is_valid() -> None:
    """`pipeline_commit` must be a commit reachable in this repo (no stale garbage)."""
    meta = _load_meta()
    commit = meta.get("pipeline_commit")
    assert commit and len(commit) >= 7, f"pipeline_commit missing/short: {commit!r}"
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        f"pipeline_commit={commit!r} is not a valid commit in this repo — "
        "re-stamp .golden_meta.json to HEAD"
    )


if __name__ == "__main__":
    test_golden_meta_hash_matches_actual()
    test_golden_meta_count_matches_actual()
    test_golden_meta_count_arithmetic()
    test_golden_meta_pipeline_commit_is_valid()
    print("golden meta contract tests OK")
