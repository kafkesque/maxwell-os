"""BUG-614 (D-2801/D-2805/D-2806): pin stamp.stage_code_fingerprint contract.

The helper content-hashes a stage's producing code from a config-owned
``{stage}.fingerprint_files`` list (C12) so an uncommitted edit invalidates a
stale checkpoint fail-closed. It was the highest-risk untested code in the tree —
wired into stage0/0_5/1/1_3/1_5/2/4/5/6 with zero tests. These tests pin:

  1. determinism + 16-hex shape (SHA-256 prefix),
  2. C16 fail-closed on an empty/missing file list,
  3. C16 fail-closed on a missing declared file,
  4. byte-content sensitivity (an edit MUST move the fingerprint),
  5. crash-safe write/read round-trip (C6),
  6. legacy no-sidecar checkpoint is allowed to resume (incremental adoption),
  7. a stored-vs-current mismatch is refused fail-closed.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import stamp  # noqa: E402


def test_fingerprint_is_deterministic_and_16hex():
    fp1 = stamp.stage_code_fingerprint("stage0")
    fp2 = stamp.stage_code_fingerprint("stage0")
    assert fp1 == fp2
    assert len(fp1) == 16
    assert all(c in "0123456789abcdef" for c in fp1)


def test_refuses_empty_file_list(monkeypatch):
    monkeypatch.setattr(stamp, "_STAGE_CFG", {})
    with pytest.raises(RuntimeError, match="refusing to fingerprint nothing"):
        stamp.stage_code_fingerprint("stage_nonexistent")


def test_refuses_missing_declared_file(monkeypatch):
    monkeypatch.setattr(
        stamp, "_STAGE_CFG",
        {"stage_x": {"fingerprint_files": ["pipeline/this_module_does_not_exist.py"]}},
    )
    with pytest.raises(RuntimeError, match="fingerprint_files entry missing"):
        stamp.stage_code_fingerprint("stage_x")


def test_fingerprint_changes_with_byte_content(tmp_path, monkeypatch):
    mod = tmp_path / "mod.py"
    mod.write_text("A", encoding="utf-8")
    monkeypatch.setattr(stamp, "_STAGE_CFG", {"stage_y": {"fingerprint_files": [str(mod)]}})
    fp_a = stamp.stage_code_fingerprint("stage_y")
    mod.write_text("B", encoding="utf-8")
    fp_b = stamp.stage_code_fingerprint("stage_y")
    assert fp_a != fp_b


def test_write_read_roundtrip(tmp_path):
    ckpt = tmp_path / "checkpoint.jsonl"
    fp = stamp.write_stage_code_fingerprint(ckpt, "stage0")
    assert fp == stamp.stage_code_fingerprint("stage0")
    assert stamp.read_stage_code_fingerprint(ckpt) == fp
    sidecar = stamp.stage_code_fingerprint_path(ckpt)
    assert sidecar.exists()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["stage_key"] == "stage0"


def test_check_allows_legacy_no_sidecar(tmp_path):
    # A pre-BUG-614 checkpoint has no sidecar; resume is allowed unchanged (incremental).
    ckpt = tmp_path / "no_sidecar.jsonl"
    stamp.check_stage_code_fingerprint(ckpt, "stage0")  # must not raise


def test_check_raises_on_mismatch(tmp_path):
    ckpt = tmp_path / "ckpt.jsonl"
    stamp.write_stage_code_fingerprint(ckpt, "stage0")
    sidecar = stamp.stage_code_fingerprint_path(ckpt)
    sidecar.write_text(
        json.dumps({"fingerprint_id": "deadbeefdeadbeef", "stage_key": "stage0"}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="code fingerprint mismatch"):
        stamp.check_stage_code_fingerprint(ckpt, "stage0")
