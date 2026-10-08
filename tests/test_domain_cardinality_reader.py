"""test_domain_cardinality_reader.py — control tests for the BUG-631 READER-limb (D-2843).

Proves the reader counts only the canonical ``domains`` array, reports over-cap FBs, names parse-defects
instead of silently counting them as zero, and exits fail-closed via ``main()``. R5: generator != verifier.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import scripts.check_domain_cardinality as reader


def _make_store(tmp_path: Path, rows: list[tuple[str, str | None, str]]) -> Path:
    """Create a synthetic ``fbs`` store and return its path."""
    db = tmp_path / "synthetic.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE fbs (fb_id TEXT, domains TEXT, classification_status TEXT)")
    conn.executemany(
        "INSERT INTO fbs (fb_id, domains, classification_status) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db


def test_count_domains_well_formed():
    assert reader.count_domains('["a", "b", "c"]') == (3, None)


def test_count_domains_null_and_empty_are_zero():
    assert reader.count_domains(None) == (0, None)
    assert reader.count_domains("") == (0, None)
    assert reader.count_domains("   ") == (0, None)


def test_count_domains_names_defect_not_zero():
    # parse-defect must be NAMED (a reason string), never a silent (0, None).
    count, reason = reader.count_domains("not json")
    assert count == 0 and reason is not None
    assert reader.count_domains('{"a": 1}')[1] is not None  # not a list
    assert reader.count_domains("[1, 2]")[1] is not None  # list of non-strings


def test_measure_store_counts_only_canonical_domains(tmp_path):
    db = _make_store(
        tmp_path,
        [
            ("ok1", json.dumps(["a", "b", "c", "d", "e", "f", "g"]), "CLEAN"),  # == cap (7)
            ("over", json.dumps(["a", "b", "c", "d", "e", "f", "g", "h"]), "CLEAN"),  # 8 > 7
            ("ok2", json.dumps(["a"]), "CLEAN"),
        ],
    )
    result = reader.measure_store(db, reader.MAX_DOMAINS_PER_FB)
    assert result["total_fbs"] == 3
    assert [fb["fb_id"] for fb in result["over_cap"]] == ["over"]
    assert result["over_cap"][0]["domain_count"] == 8
    assert result["parse_defects"] == []


def test_measure_store_reports_parse_defect(tmp_path):
    db = _make_store(
        tmp_path,
        [
            ("bad", "not-json", "CLEAN"),
            ("fine", json.dumps(["a", "b"]), "CLEAN"),
        ],
    )
    result = reader.measure_store(db, reader.MAX_DOMAINS_PER_FB)
    assert [d["fb_id"] for d in result["parse_defects"]] == ["bad"]
    assert result["over_cap"] == []


def test_receipt_stamps_all_fields():
    receipt = reader.build_receipt(
        {
            "total_fbs": 3,
            "over_cap": [{"fb_id": "x", "domain_count": 6, "classification_status": "CLEAN"}],
            "parse_defects": [],
        },
        Path("knowledge pipeline/maxwell.db"),
        reader.MAX_DOMAINS_PER_FB,
    )
    assert receipt["schema_version"] == "1.0"
    assert receipt["max_domains_per_fb"] == 7
    assert receipt["over_cap_count"] == 1
    assert receipt["total_fbs"] == 3


def test_main_exit_drift_when_over_cap(tmp_path, monkeypatch):
    db = _make_store(tmp_path, [("over", json.dumps(["a", "b", "c", "d", "e", "f", "g", "h"]), "CLEAN")])
    monkeypatch.setattr(reader, "DB_PATH", db)
    assert reader.main([]) == reader.EXIT_DRIFT


def test_main_exit_clean_when_no_over_cap(tmp_path, monkeypatch):
    db = _make_store(tmp_path, [("ok", json.dumps(["a", "b"]), "CLEAN")])
    monkeypatch.setattr(reader, "DB_PATH", db)
    assert reader.main([]) == reader.EXIT_CLEAN


def test_main_exit_owed_on_parse_defect(tmp_path, monkeypatch):
    db = _make_store(tmp_path, [("bad", "nope", "CLEAN")])
    monkeypatch.setattr(reader, "DB_PATH", db)
    assert reader.main([]) == reader.EXIT_OWED
