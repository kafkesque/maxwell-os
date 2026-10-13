#!/usr/bin/env python3
"""specs/retrieval_goldens.spec.md — the paired contract for the golden re-anchor gate.

Every test names the INV it pins (D-2978). The pure tests drive `judge_review` directly; the two subprocess tests
drive the CLI modes. Both must stay **store-free**: a control that needs the FAISS index never runs on a laptop
(BUG-492 — a control nothing runs is a comment).
"""

from __future__ import annotations

import ast
import csv
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.reanchor_retrieval_goldens import (  # noqa: E402
    ANCHOR_MODE,
    ANCHOR_MODES,
    DECISIONS,
    GOLDEN_PATH,
    _sheet,
    controls,
    judge_review,
)

SCRIPT = PROJECT_ROOT / "scripts" / "reanchor_retrieval_goldens.py"
SRC = SCRIPT.read_text(encoding="utf-8")
REANCHOR = yaml.safe_load((PROJECT_ROOT / "config" / "pipeline_config.yaml").read_text())[
    "retrieval_benchmark"
]["reanchor"]
REVIEWED = PROJECT_ROOT / "governance" / "golden_reanchor_candidates_20261011.reviewed.csv"
DRAFT = PROJECT_ROOT / "governance" / "golden_reanchor_proposed_20261011.yaml"

# the query retired ON PURPOSE by the 20261011T221956Z apply: anchoring it would ADD it back (reported, INV-7)
RETIRED_QUERY = "can a large language model be compressed into a smaller one"


def _fns() -> dict[str, str]:
    """{function name: unparsed source} for every top-level def in the applier - the source-level joins."""
    tree = ast.parse(SRC)
    return {n.name: ast.unparse(n) for n in tree.body if isinstance(n, ast.FunctionDef)}


# ── INV-1 · the vocabulary has ONE home; an unknown token is named and NEVER normalised ────────────────
def test_inv1_the_vocabulary_has_one_home_in_config() -> None:
    assert DECISIONS == tuple(str(x) for x in REANCHOR["decisions"])
    assert len(DECISIONS) >= 2


def test_inv1_an_offending_token_is_refused_and_suggested_but_not_applied() -> None:
    rep = judge_review(_sheet(["anchor", "ambigouos"]), ["q1"], mode="set")
    assert any("ambigouos" in f for f in rep["faults"])
    assert rep["near_miss"]["ambigouos"] == "ambiguous"
    # the sheet itself is UNCHANGED: the applier suggests, it does not decide (the writer must fix the cell)
    assert not any(r["decision"] == "ambiguous" for r in _sheet(["anchor", "ambigouos"]))


# ── INV-2 · the anchor is the NAME; the resolver is imported, never restated ───────────────────────────
def test_inv2_the_resolver_is_imported_not_restated() -> None:
    assert "def resolve_name" not in SRC


# ── INV-3 · one owner-signed anchor per query, OR a DECLARED set ───────────────────────────────────────
def test_inv3_single_mode_refuses_more_than_one_anchor() -> None:
    rep = judge_review(_sheet(["anchor", "anchor"]), ["q1"], mode="single")
    assert any("requires exactly ONE" in f for f in rep["faults"])


def test_inv3_set_mode_builds_the_expected_set_in_rank_order() -> None:
    rep = judge_review(_sheet(["", "anchor", "anchor"], names=["a", "b", "c"]), ["q1"], mode="set")
    assert rep["faults"] == []
    assert rep["plans"][0]["verdict"] == "anchor-set"
    assert rep["plans"][0]["names"] == ["b", "c"]


def test_inv3_an_unreadable_rank_sorts_last_and_never_first() -> None:
    rows = [
        {
            "query": "q1",
            "rank": "x",
            "cand_name": "a",
            "decision": "anchor",
            "owner_signature": "B.",
        },
        {
            "query": "q1",
            "rank": "2",
            "cand_name": "b",
            "decision": "anchor",
            "owner_signature": "B.",
        },
    ]
    assert judge_review(rows, ["q1"], mode="set")["plans"][0]["names"] == ["b", "a"]


def test_inv3_the_mode_is_declared_in_config_and_known() -> None:
    assert ANCHOR_MODE in ANCHOR_MODES
    assert str(REANCHOR.get("anchor_mode")) == ANCHOR_MODE


# ── INV-4 · the SET is what recall is measured over (the only reason a set is allowed) ─────────────────
def test_inv4_recall_is_micro_over_the_expected_set() -> None:
    bench = ast.parse(
        (PROJECT_ROOT / "pipeline" / "retrieval_benchmark.py").read_text(encoding="utf-8")
    )
    fn = next(n for n in bench.body if isinstance(n, ast.FunctionDef) and n.name == "_recall_at_k")
    assert "return hits / len(expected)" in ast.unparse(fn)


def test_inv4_every_expected_name_is_resolved() -> None:
    g = ast.parse((PROJECT_ROOT / "pipeline" / "golden.py").read_text(encoding="utf-8"))
    fn = next(
        n for n in g.body if isinstance(n, ast.FunctionDef) and n.name == "resolve_golden_anchors"
    )
    assert "for nm in names" in ast.unparse(fn)


# ── INV-5 · an abstention is excluded and counted; an unjudged query refuses ───────────────────────────
def test_inv5_an_abstention_is_excluded_from_the_set_and_counted() -> None:
    rep = judge_review(_sheet(["anchor", "ambiguous", "anchor"]), ["q1"], mode="set")
    assert rep["plans"][0]["names"] == ["name1", "name3"]
    assert rep["abstentions"] == 1


def test_inv5_a_query_with_no_verdict_refuses_the_write() -> None:
    rep = judge_review(_sheet(["", "", ""]), ["q1"], mode="single")
    assert rep["unreviewed"] == ["q1"]
    assert rep["faults"]


def test_inv5_a_query_marked_only_ambiguous_parks() -> None:
    rep = judge_review(_sheet(["ambiguous", "ambiguous"]), ["q1"], mode="set")
    assert rep["unreviewed"] == ["q1"] and rep["faults"]


def test_inv5_an_anchor_with_no_owner_signature_is_refused() -> None:
    rep = judge_review(_sheet(["anchor"], sig=""), ["q1"], mode="single", signature_required=True)
    assert any("owner_signature" in f for f in rep["faults"])


# ── INV-6 · ONE judgment, two callers ──────────────────────────────────────────────────────────────────
def test_inv6_check_and_apply_call_the_one_judgment() -> None:
    fns = _fns()
    assert "judge_review(" in fns["_check_reviewed"]
    assert "judge_review(" in fns["_apply_reviewed"]
    # and the verdict rule is not restated inside either caller (the D-2642 class, in a control)
    assert "rows marked 'anchor'" not in fns["_check_reviewed"]
    assert "rows marked 'anchor'" not in fns["_apply_reviewed"]


def test_inv6_the_store_imports_are_lazy_so_selftest_is_hermetic() -> None:
    tree = ast.parse(SRC)
    top_level = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    mods = {getattr(n, "module", None) for n in top_level}
    assert "pipeline.retrieve" not in mods
    assert "pipeline.golden" not in mods


# ── INV-7 · dropped on purpose; ADDED is declared ─────────────────────────────────────────────────────
def test_inv7_a_rewrite_query_row_drops_the_query_and_an_add_is_declared() -> None:
    rep = judge_review(_sheet(["rewrite-query"]), ["q1"], mode="single")
    assert rep["dropped"] == ["q1"] and not rep["faults"]
    rep2 = judge_review(_sheet(["anchor"]), ["q1"], mode="single", live=["some other query"])
    assert rep2["added"] == ["q1"]


def test_inv7_a_draft_query_with_no_csv_rows_is_a_fault() -> None:
    rep = judge_review(_sheet(["anchor"]), ["q1", "q2"], mode="single")
    assert any("carries no row for it" in f for f in rep["faults"])


# ── INV-8 · nothing is written without a C13 backup ───────────────────────────────────────────────────
def test_inv8_the_apply_backs_up_before_writing() -> None:
    fn = _fns()["_apply_reviewed"]
    assert "copy2" in fn and "bak_" in fn
    assert fn.index("copy2") < fn.index("write_text")


# ── INV-9 · the pre-flight writes NOTHING and returns 1 on a fault ────────────────────────────────────
def test_inv9_the_pre_flight_writes_nothing_and_blocks(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.csv"
    draft = tmp_path / "draft.yaml"
    sheet.write_text("query,rank,cand_name,decision,owner_signature\nq1,1,n1,,\n", encoding="utf-8")
    draft.write_text(
        yaml.safe_dump({"queries": [{"query": "q1", "query_type": "synonym"}]}), encoding="utf-8"
    )
    before = sorted(p.name for p in tmp_path.iterdir())
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--csv", str(sheet), "--yaml-out", str(draft), "--check"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert "no row marked 'anchor'" in res.stdout or "fault(s)" in res.stdout
    assert sorted(p.name for p in tmp_path.iterdir()) == before


# ── INV-10 · the judgment is proven by known-answer controls, run by the ladder ───────────────────────
def test_inv10_every_control_fires_and_the_cli_selftest_is_green() -> None:
    assert all(ok for _label, ok in controls())
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--selftest"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "known-answer control(s) fire" in res.stdout


# ── THE OWNER'S SHEET — the measurement of record (the reason the mode exists) ─────────────────────────
@pytest.mark.skipif(
    not REVIEWED.exists() or not DRAFT.exists(), reason="the reviewed sheet is not present"
)
def test_the_owners_reviewed_sheet_applies_under_a_declared_set() -> None:
    rows = list(csv.DictReader(REVIEWED.open(newline="", encoding="utf-8")))
    queries = [
        str(q.get("query", ""))
        for q in yaml.safe_load(DRAFT.read_text(encoding="utf-8"))["queries"]
    ]
    live = {
        str(q.get("query", ""))
        for q in yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))["queries"]
    }
    rep = judge_review(rows, queries, mode="set", live=sorted(live))
    assert rep["faults"] == []
    sets = [p for p in rep["plans"] if p["verdict"] == "anchor-set"]
    assert len(sets) == 29
    assert sum(len(p["names"]) for p in sets) == 120
    assert rep["dropped"] == [RETIRED_QUERY]
    assert rep["added"] == []
    assert rep["abstentions"] == 19
