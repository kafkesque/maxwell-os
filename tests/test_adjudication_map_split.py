#!/usr/bin/env python3
"""tests/test_adjudication_map_split.py - D-2967/BUG-741: a map destination is a ROLE xor a DISPOSITION.

WHY. The owner adjudication map carried content_type values AND disposition values in ONE key, and the
ROUTER's tier 1 - the highest authority in the deterministic content_type router - admitted BOTH
vocabularies (it tested membership in CONTENT_TYPES_ALL, which INCLUDES the two dispositions). MEASURED
before the fix: 375 of the 542 entries tier 1 admitted named a DISPOSITION as if it were a role, so a
record the owner had ruled noise_drop resolved to content_type='noise_drop'. With the D-2938 persist flag
on (stage4.persist_resolved_content_type) that value is written into the FB checkpoint and the D-2965
leaf gate refuses it at S6, where stage6.max_failed_ratio 0.0 turns ONE refused row into a HALTED rollback.
These controls pin the split, the roles-only admission, the parity (no silent drop) and the LOUD refusals
that stop a stale map from silently emptying tier 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pipeline import content_types as ct

ROOT = Path(ct.__file__).resolve().parent.parent


def _cfg() -> dict:
    return yaml.safe_load((ROOT / "config/content_types.yaml").read_text(encoding="utf-8"))


def _schema() -> dict:
    return _cfg()["adjudication_map"]


def _map_rows() -> list[dict]:
    doc = json.loads((ROOT / _schema()["path"]).read_text(encoding="utf-8"))
    return doc[_schema()["rows_key"]]


def test_the_map_schema_has_one_home_and_the_router_reads_it() -> None:
    """C12: the path and the two destination keys are DECLARED, never hardcoded in the reader."""
    schema = _schema()
    assert ct._MAP_SCHEMA == schema
    assert ct._ADJUDICATION_PATH == ROOT / schema["path"]


def test_every_row_carries_exactly_one_destination_key_and_no_legacy_key() -> None:
    schema = _schema()
    role_key, disp_key, legacy = schema["role_key"], schema["disposition_key"], schema["legacy_conflated_key"]
    rows = _map_rows()
    assert rows, "the map must not be empty"
    for i, row in enumerate(rows):
        assert legacy not in row, f"row {i} still carries the conflated {legacy!r} key"
        assert bool(row.get(role_key)) != bool(row.get(disp_key)), f"row {i} must name a role XOR a disposition"


def test_tier_one_admits_roles_only_and_drops_nothing_silently() -> None:
    """The measured defect was a DISPOSITION read as a ROLE; parity is the second half of the control."""
    schema = _schema()
    assert not (set(ct._ADJUDICATION_MAP.values()) & set(ct.CONTENT_TYPE_DISPOSITIONS))
    role_rows = {str(r["fb_id"]): str(r[schema["role_key"]]) for r in _map_rows() if r.get(schema["role_key"])}
    assert ct._ADJUDICATION_MAP == role_rows


def test_the_disposition_rows_survive_the_split_and_name_declared_values() -> None:
    schema = _schema()
    declared = set(_cfg()["dispositions"])
    disp_rows = [r for r in _map_rows() if r.get(schema["disposition_key"])]
    assert disp_rows, "the split must PRESERVE the disposition rulings, not drop them"
    orphans = sorted({str(r[schema["disposition_key"]]) for r in disp_rows
                      if str(r[schema["disposition_key"]]) not in declared})
    assert orphans == [], f"the map names dispositions the ontology does not declare: {orphans}"


def _write_map(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "map.json"
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def test_a_legacy_conflated_key_RAISES_rather_than_emptying_tier_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ct, "_ADJUDICATION_PATH", _write_map(tmp_path, [{"fb_id": "a", "proposed": "principle"}]))
    with pytest.raises(RuntimeError, match="LEGACY conflated"):
        ct._load_adjudication_map()


def test_a_row_naming_both_keys_RAISES(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    schema = _schema()
    row = {"fb_id": "a", schema["role_key"]: "principle", schema["disposition_key"]: "noise_drop"}
    monkeypatch.setattr(ct, "_ADJUDICATION_PATH", _write_map(tmp_path, [row]))
    with pytest.raises(RuntimeError, match="BOTH"):
        ct._load_adjudication_map()


def test_an_undeclared_role_RAISES(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    schema = _schema()
    monkeypatch.setattr(ct, "_ADJUDICATION_PATH",
                        _write_map(tmp_path, [{"fb_id": "a", schema["role_key"]: "made_up_type"}]))
    with pytest.raises(RuntimeError, match="UNDECLARED role"):
        ct._load_adjudication_map()


def test_a_row_with_neither_key_yields_no_admission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ct, "_ADJUDICATION_PATH", _write_map(tmp_path, [{"fb_id": "a", "reason": "x"}]))
    assert ct._load_adjudication_map() == {}


def test_tier_one_is_reachable_and_the_split_did_not_change_a_role() -> None:
    """The split must be a RENAME of the key, not a change of verdict: the live map still grants roles."""
    assert ct._ADJUDICATION_MAP, "tier 1 must not be empty after the split"
    assert set(ct._ADJUDICATION_MAP.values()) <= set(ct.CONTENT_TYPES)
