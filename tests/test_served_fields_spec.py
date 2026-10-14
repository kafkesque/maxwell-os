#!/usr/bin/env python3
"""tests/test_served_fields_spec.py — the paired contract for specs/served_fields.spec.md (D-2978).

One test per invariant, named in the spec. The tests drive the rail's PURE classifier (`verdict_for`) as known
answers, the rail's own AST scan, the declaration that is the ONE home, the LIVE verdict, and the ledger↔cache arm
(the formula imported, never restated).
"""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = PROJECT_ROOT / "specs" / "served_fields.spec.md"
SRC = PROJECT_ROOT / "scripts" / "check_served_fields.py"
PARITY = PROJECT_ROOT / "scripts" / "check_feedback_parity.py"
DECLARATION = PROJECT_ROOT / "config" / "served_fields.yaml"
FEEDBACK_POLICY = PROJECT_ROOT / "config" / "feedback.yaml"
FEEDBACK_SRC = PROJECT_ROOT / "pipeline" / "feedback.py"

_spec = importlib.util.spec_from_file_location("check_served_fields", SRC)
sf = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(sf)

DECL = yaml.safe_load(DECLARATION.read_text())
VOCAB = set(DECL["owner_word"]["vocabulary"])
FLAGGED_DERIVED = {"derivations:dead_but_read", "derivations:declared_but_empty", "derivations:orphan_magic_threshold"}


def _state(**kw) -> dict:
    base: dict = {"field": "f", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"]}
    base.update(kw)
    return base


def _live() -> tuple[int, str]:
    """Run the LIVE rail - the claim is the exit code and the text, not an abstraction."""
    proc = subprocess.run(
        [sys.executable, str(SRC)], capture_output=True, text=True, cwd=str(PROJECT_ROOT), check=False
    )
    return proc.returncode, proc.stdout + proc.stderr


# ── INV-1 — an advertised field is a CLAIM, read from the AST ────────────────────────────────────────────────────

def test_the_scan_reads_the_ast_and_joins_the_store() -> None:
    """INV-1: the payload's own keys are found, and only the ones that name a store column count."""
    columns = sf.columns_of_store()
    found = sf.advertised_fields("maxwell_mcp_server.py", "dict_keys", columns)
    assert {"borp_score", "feedback_score", "confidence_score"} <= found, sorted(found)
    assert "rank" not in found, "a payload key that names no store column is STRUCTURE, not a claim"


def test_a_comment_cannot_advertise_a_field(tmp_path: Path) -> None:
    """INV-1: a mention in a comment or a docstring is not an advertisement (the AST, not the text)."""
    rel = "temp_advert_probe.py"
    probe = PROJECT_ROOT / rel
    probe.write_text('"""borp_score lives here"""\n# borp_score in a comment\nX = {"other": 1}\n')
    try:
        found = sf.advertised_fields(rel, "dict_keys", sf.columns_of_store())
        assert "borp_score" not in found, found
    finally:
        probe.unlink()


# ── INV-2 — a flagged advertised field must carry a declaration ──────────────────────────────────────────────────

def test_an_undeclared_advert_is_refused() -> None:
    """INV-2: an advertised field a register flags, with no disposition, is a DEFECT (the BUG-511 family)."""
    verdict, detail = sf.verdict_for(_state(), VOCAB)
    assert verdict == sf.DEFECT_UNDECLARED, detail
    assert "BUG-511" in detail


# ── INV-3 — the owner word is vocabulary-checked and SIGNED ──────────────────────────────────────────────────────

def test_a_word_outside_the_vocabulary_is_refused() -> None:
    """INV-3: a token no reader implements is refused BY NAME (the T-101 lesson)."""
    verdict, detail = sf.verdict_for(_state(declared={"word": "drop", "anchor": "x"}), VOCAB)
    assert verdict == sf.DEFECT_WORD, detail


def test_an_unsigned_word_is_refused() -> None:
    """INV-3: a word with no anchor is not a rule."""
    verdict, detail = sf.verdict_for(_state(declared={"word": "retire", "anchor": ""}), VOCAB)
    assert verdict == sf.DEFECT_ANCHOR, detail


def test_a_pending_word_is_owner_owed_and_a_written_word_is_owed_until_it_lands() -> None:
    """INV-3/INV-6: pending and written-but-not-landed are BOTH owner-owed (loud), never silently OK."""
    pending, _ = sf.verdict_for(_state(declared={"word": "pending", "anchor": "", "owed": "T-107"}), VOCAB)
    written, _ = sf.verdict_for(_state(declared={"word": "retire", "anchor": "owner 2026-10-13"}), VOCAB)
    assert (pending, written) == (sf.OWNER_OWED, sf.OWNER_OWED)


# ── INV-4 — a declaration tracks its subject in BOTH directions ──────────────────────────────────────────────────

def test_a_stale_declaration_is_refused() -> None:
    """INV-4: a declaration whose subject no surface advertises is an assertion (BUG-488/D-405)."""
    verdict, detail = sf.verdict_for(
        {"field": "ghost", "surfaces": [], "flags": [], "declared": {"word": "retire", "anchor": "x"}}, VOCAB
    )
    assert verdict == sf.DEFECT_STALE, detail


def test_an_acknowledgement_must_still_be_advertised() -> None:
    """INV-4: the same rule for a SOURCE-owned row, in the other direction."""
    live, _ = sf.verdict_for(
        _state(field="jargon", flags=["store_columns:status=debt"], acknowledged={"owned_by": "x"}), VOCAB
    )
    stale, _ = sf.verdict_for(
        {"field": "jargon", "surfaces": [], "flags": [], "acknowledged": {"owned_by": "x"}}, VOCAB
    )
    assert (live, stale) == (sf.ACKNOWLEDGED, sf.DEFECT_STALE)


# ── INV-5 — a promotion names a home that RESOLVES ───────────────────────────────────────────────────────────────

def test_a_promotion_must_name_a_resolving_home() -> None:
    """INV-5: a missing home is a DEFECT; the declared promotion's home resolves in the tree."""
    verdict, detail = sf.verdict_for(
        _state(home_ok=False, declared={"word": "promote corroboration", "anchor": "x"}), VOCAB
    )
    assert verdict == sf.DEFECT_HOME, detail
    home = DECL["promotions"]["corroboration"]["home"]
    assert sf.home_exists(home), f"{home} does not resolve"


# ── INV-6 — the debt is loud, not fatal, and shrink-only ─────────────────────────────────────────────────────────

def test_the_debt_is_loud_not_fatal_and_shrink_only() -> None:
    """INV-6: rc 2 with debt == ceiling; the ceiling may never be raised by an edit, and the floor is 0."""
    rc, out = _live()
    declared_fields = {str(row["field"]) for row in DECL["declared"]}
    assert DECL["coverage"]["min_declared_debt"] == 0
    assert DECL["coverage"]["max_declared_debt"] == len(declared_fields), (
        "the ceiling is born at the MEASURED debt; raising it later is a DECISION (C12/D-2644)"
    )
    assert rc == 2, out
    assert f"{len(declared_fields)} declared-absent advertised" in out, out
    assert "0 undeclared, 0 stale" in out, out
    for field in declared_fields:
        assert f"owed: {field}:" in out, f"{field} is declared but the rail does not report it as owed"


def test_every_declared_row_names_a_flag_a_register_actually_raises() -> None:
    """INV-6/INV-2: a declaration must cite the register reason it answers (no invented defects)."""
    flags = sf.register_flags(DECL)
    for row in DECL["declared"]:
        assert flags.get(str(row["field"])), f"{row['field']} is declared but no register flags it"
        assert any(f in FLAGGED_DERIVED or f.startswith("store_columns:") for f in flags[str(row["field"])])


# ── INV-7 — the cache is reproducible from its ledger through ONE formula ─────────────────────────────────────────

def test_the_parity_rail_drives_the_writer_formula() -> None:
    """INV-7: the parity rail's known answers fire (empty failures) and the writer lands the declared value."""
    spec = importlib.util.spec_from_file_location("check_feedback_parity", PARITY)
    cp = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(cp)
    assert cp.controls() == [], cp.controls()
    assert cp.declared_aggregate([0.6, 0.9, 0.9]) == 0.8
    assert cp.declared_aggregate([]) is None


def test_the_formula_is_not_restated_in_the_rail() -> None:
    """INV-7: the formula has ONE home - the LIVE path may not compute an aggregate of its own (BUG-502 class)."""
    src = PARITY.read_text()
    assert "from pipeline.feedback import" in src and "declared_aggregate" in src
    tree = ast.parse(src)
    assert not any(
        isinstance(node, ast.FunctionDef) and node.name == "declared_aggregate" for node in ast.walk(tree)
    ), "the rail imports the formula; it may not own a copy"
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    live_path = ast.unparse(main)
    assert "sum(" not in live_path, "the LIVE path must call declared_aggregate, not sum ratings itself (D-2642)"
    # the CONTROL is allowed to compute the expected value independently - a circular oracle proves nothing
    assert "round(sum(FIXTURE_RATINGS)" in src, "the control must keep an INDEPENDENT expectation"


# ── INV-8 — absence is NULL, never hollow, and DECLARED ─────────────────────────────────────────────────────────

def test_an_empty_ledger_leaves_the_absence_absent() -> None:
    """INV-8: `declared_aggregate([])` is None and the declared absence shape is NULL + count 0 (D-2957)."""
    from pipeline.feedback import declared_aggregate

    assert declared_aggregate([]) is None
    policy = yaml.safe_load(FEEDBACK_POLICY.read_text())
    assert policy["absence"]["shape"] == "feedback_score IS NULL AND feedback_count = 0"
    assert policy["aggregate"]["home"] == "pipeline/feedback.py::declared_aggregate"
    assert "prior_weight" in policy["aggregate"] and "prior" in policy["aggregate"]


# ── INV-9 — a failed read is never a healthy verdict ────────────────────────────────────────────────────────────

def test_a_failed_read_reports_unmeasured(tmp_path: Path) -> None:
    """INV-9: the tri-state - an error can never be read as 'this FB is fine' (C16)."""
    from pipeline.feedback import get_fb_feedback_stats

    stats = get_fb_feedback_stats("fb-does-not-exist", tmp_path / "empty.db")
    assert stats["state"] == "unmeasured", stats
    assert stats["needs_retirement"] is None and stats["needs_boost"] is None, stats
    assert stats.get("error")


def test_the_thresholds_have_one_home_and_no_code_default() -> None:
    """INV-8/INV-9: the thresholds are declared, and the module holds no literal fallback (C12/D-2644)."""
    src = FEEDBACK_SRC.read_text()
    policy = yaml.safe_load(FEEDBACK_POLICY.read_text())
    for literal in ("RETIREMENT_THRESHOLD", "RETIREMENT_MIN_FEEDBACKS", "BOOST_THRESHOLD"):
        assert literal not in src, f"{literal} is a policy value with no home (C12)"
    assert "no default" in src.lower() or "fail-closed" in src
    assert policy["thresholds"]["retirement"]["min_feedback"] == 5
    with pytest.raises(KeyError):
        from pipeline import feedback as fb

        fb.declared("thresholds.retirement.not_a_key")

# ── INV-10 — a granted owner word is JOINED to the thing it names, never restated ─────────────────────────────────

def test_the_tier_word_is_joined_to_the_measure_it_names() -> None:
    """INV-10 (T-118): the tier vocabulary must be the MEASURE's own, and the word must be SIGNED."""
    policy = DECL.get("tier_policy")
    assert isinstance(policy, dict), "T-118 is granted: the declaration must carry the tier policy"
    assert policy["word"] == "tier" and policy["word"] in sf.TIER_WORDS
    assert str(policy.get("granted") or "").strip(), "an unsigned word is not a rule (T-101)"
    assert str(policy.get("granted_by") or "").strip()
    rel, _, symbol = str(policy["vocabulary_home"]).partition("::")
    tokens = sf.symbol_literals(rel, symbol)
    assert set(policy["vocabulary"]) <= tokens, "a tier token living only in config is a RIVAL definition (C12)"
    joined = sf.tier_faults(policy, tokens, sf.home_exists(policy["vocabulary_home"]), sf.home_exists(policy["accessor"]))
    assert joined == [], joined
    rival = {**policy, "vocabulary": [*policy["vocabulary"], "gold"]}
    assert sf.tier_faults(rival, tokens, True, True), "a tier defined in config must be REFUSED, not tolerated"
    rc, out = _live()
    assert sf.DEFECT_TIER not in out, out
    assert rc != 1, out
