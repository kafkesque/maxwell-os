"""D2590 / D-2942 / D-2943 — the non-principle (procedural + episodic) commit tier.

These tests pin the FOUR properties the build rests on, each with a control that FAILS if the
property is lost:

  1. the `type_body` field list comes from the ontology (`content_types.yaml::s2_body_fields` minus
     `core_body`) and never from a literal in code (C12);
  2. a role that carries no factual claim derives `(QUARANTINE, s5_not_applicable)` — NOT
     undecidable, and NEVER PASS (D-2942 / R5 / D2298);
  3. that disposition is SCOPED: a `principle` with no verification record is still refused, so the
     change cannot become a general "commit unverified rows" switch;
  4. the ingest set is selected by the ROW's own content_type, and every exclusion is declared
     (a silent drop is the defect this build repairs).
"""

from __future__ import annotations

import json

import pytest

from pipeline.content_types import CORE_BODY, type_body_fields
from pipeline.serving_gate import (
    content_types_without_factual_claim,
    derive_status,
    pre_write_verdict,
)

#: The roles the non-principle tier commits (config-driven, never a literal list in the test).
COMMIT_ROLES = sorted(content_types_without_factual_claim())


def _fb_row(**overrides) -> dict:
    """A minimal row that satisfies the NOT NULL columns, with the D-2942 disposition applied."""
    row = {
        "fb_id": "fb_test_1",
        "name": "A procedure",
        "definition": "A definition.",
        "content_type": "process_template",
        "type_body": json.dumps({"steps": ["one", "two"]}),
    }
    row.update(overrides)
    return row


# ── 1. the ontology contract ─────────────────────────────────────────────────────────────────────


def test_type_body_fields_match_the_declared_ontology():
    """The field lists are READ from config/content_types.yaml — measured, not asserted by prose."""
    assert type_body_fields("process_template") == ("trigger", "prerequisite", "steps", "done_condition")
    assert type_body_fields("process_instance") == (
        "instance_text", "actors", "outcome_metric", "outcome_qualitative", "domain_context",
    )
    assert type_body_fields("tool_instruction") == (
        "tool_name", "platform", "description", "syntax", "parameters", "output", "example", "caveats",
    )
    assert type_body_fields("growth_edge") == ("body", "category", "actionable", "status", "priority")


def test_type_body_excludes_core_body_fields():
    """A field with a first-class column is NOT copied into type_body (one value, one home)."""
    assert "failure_mode" in CORE_BODY  # declared core → column exists
    assert "failure_mode" not in type_body_fields("process_template")
    assert type_body_fields("principle") == ()  # the principle body IS the core body
    assert type_body_fields(None) == ()


def test_build_type_body_keeps_only_present_fields():
    """An absent key must not become a fabricated "" — that is how slop enters a store."""
    from pipeline.stage6_commit import build_type_body

    body = json.loads(build_type_body({
        "content_type": "process_template", "trigger": "when X", "steps": ["a"], "prerequisite": "",
        "done_condition": "Y done",
    }))
    assert body == {"trigger": "when X", "steps": ["a"], "done_condition": "Y done"}


def test_build_type_body_fails_loud_for_an_undeclared_role():
    """A role with no declared body contract is a config regression, never an empty body (C16)."""
    from pipeline.stage6_commit import build_type_body

    with pytest.raises(RuntimeError, match="no s2_body_fields"):
        build_type_body({"content_type": "principle", "application": "x"})


# ── 2. the disposition, and its scope ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("role", COMMIT_ROLES)
def test_disposition_is_not_applicable_for_a_role_with_no_factual_claim(role):
    """Absent record + a role with no NLI claim → NOT-APPLICABLE (decidable), never PASS."""
    status, reason = derive_status(None, content_type=role)
    assert status == "QUARANTINE"
    assert reason == "s5_not_applicable"


def test_absent_record_on_a_principle_is_still_unknown_not_not_applicable():
    """The scoping control: the disposition must NOT leak to roles that DO carry factual claims."""
    status, reason = derive_status(None, content_type="principle")
    assert (status, reason) == ("QUARANTINE", "unknown")
    status2, reason2 = derive_status(None)
    assert (status2, reason2) == ("QUARANTINE", "unknown")


def test_a_present_record_is_evaluated_on_its_own_terms_whatever_the_role():
    """Rule order (D-2942): a present record wins over the role rule — a claim is a claim."""
    record = json.dumps([{"check_name": "factual", "passed": True, "detail": "ENTAIL 3/3"}])
    status, reason = derive_status(record, content_type="process_template")
    assert (status, reason) == ("PASS", "entail")


def test_pre_write_gate_refuses_a_principle_with_no_record():
    """The gate stays a gate: a principle with no verification record is still UNDECIDABLE."""
    ok, complaint = pre_write_verdict({"fb_id": "p1", "content_type": "principle",
                                       "status": "QUARANTINE", "s5_reason": "s5_not_applicable"})
    assert not ok
    assert "UNDECIDABLE" in complaint


def test_pre_write_gate_refuses_a_non_fb_row_stored_as_pass():
    """An unverified procedural row can never be stored as PASS (no manufactured trust)."""
    ok, complaint = pre_write_verdict({"fb_id": "p2", "content_type": "tool_instruction",
                                       "status": "PASS", "s5_reason": "entail"})
    assert not ok
    assert "STATUS_MISMATCH" in complaint


def test_pre_write_gate_accepts_the_not_applicable_pair():
    ok, complaint = pre_write_verdict({"fb_id": "p3", "content_type": "growth_edge",
                                       "status": "QUARANTINE", "s5_reason": "s5_not_applicable"})
    assert ok, complaint


def test_content_types_without_factual_claim_is_declared_and_non_empty():
    """An empty/missing list would silently disable the disposition — it must fail loud (C16)."""
    assert COMMIT_ROLES == ["growth_edge", "process_instance", "process_template", "tool_instruction"]


def test_the_disposition_is_exhaustively_scoped_to_the_declared_roles():
    """Exhaustive both-ways proof over EVERY declared content_type and every malformed input.

    Forward: a declared role never derives PASS and never derives the generic 'unknown'.
    Backward: NO other role can ever derive the not-applicable disposition, and its rule output is
    still refused by the pre-write gate (so the disposition cannot become a general bypass).
    """
    from pipeline.content_types import CONTENT_TYPES_ALL

    for role in sorted(CONTENT_TYPES_ALL) + ["", "bogus_role", "PRINCIPLE", None]:
        for record in (None, [], "not-json", json.dumps([])):
            status, reason = derive_status(record, content_type=role)
            assert status == "QUARANTINE", f"{role!r} must never derive {status}"
            ok, complaint = pre_write_verdict(
                {"fb_id": "x", "content_type": role, "status": status, "s5_reason": reason}
            )
            if role in COMMIT_ROLES:
                assert reason == "s5_not_applicable"
                assert ok, f"{role!r}: the rule's own output must be storable, got {complaint}"
            else:
                assert reason != "s5_not_applicable", f"{role!r} must never be not-applicable"
                assert reason == "unknown"
                assert not ok, f"{role!r} with no verification record must stay refused"


def test_derive_status_never_raises_on_malformed_input():
    """The rule must answer every input with a declared (status, reason) — never raise, never guess."""
    for record in (None, [], "not-json", json.dumps([]), json.dumps([{"check_name": "factual"}]), b"xxx"):
        status, reason = derive_status(record, content_type="process_template")
        assert status in ("PASS", "QUARANTINE")
        assert isinstance(reason, str) and reason


# ── 3. the write path, end to end (tmp DB only) ──────────────────────────────────────────────────


@pytest.fixture()
def conn(tmp_path):
    """A migrated store in a TMP DIR (tests may not write outside tmp — tests/conftest.py)."""
    from pipeline.stage6_commit import init_db

    try:
        c = init_db(tmp_path / "t.db")
    except RuntimeError as exc:  # sqlite-vec unavailable in this interpreter
        pytest.skip(f"sqlite-vec unavailable: {exc}")
    yield c
    c.close()


def test_insert_fb_commits_a_non_fb_row_as_quarantine_with_its_body(conn):
    from pipeline.stage6_commit import insert_fb, stamp_non_fb_disposition

    row = _fb_row()
    stamp_non_fb_disposition(row)
    assert insert_fb(conn, row) is True
    stored = conn.execute(
        "SELECT content_type, status, s5_reason, type_body FROM fbs WHERE fb_id = ?", (row["fb_id"],)
    ).fetchone()
    assert stored[0] == "process_template"
    assert stored[1] == "QUARANTINE"          # never PASS
    assert stored[2] == "s5_not_applicable"   # the rule's own output
    assert json.loads(stored[3]) == {"steps": ["one", "two"]}


def test_growth_edge_epistemic_status_stays_namespaced(conn):
    """The GE `status` (open|speculative|…) must NOT reach the governed `status` column."""
    from pipeline.stage6_commit import insert_fb, stamp_non_fb_disposition

    row = _fb_row(fb_id="ge1", content_type="growth_edge",
                  type_body=json.dumps({"body": "b", "category": "open_tension",
                                        "actionable": True, "status": "open", "priority": "high"}))
    row["status"] = "open"  # as it arrives from the sidecar
    stamp_non_fb_disposition(row)
    assert insert_fb(conn, row) is True
    status, body = conn.execute(
        "SELECT status, type_body FROM fbs WHERE fb_id = 'ge1'"
    ).fetchone()
    assert status == "QUARANTINE"
    assert json.loads(body)["status"] == "open"  # preserved, namespaced


def test_a_verified_principle_still_commits_as_pass(conn):
    """Regression control: the new tier must not disturb the existing S5-verified path."""
    from pipeline.stage6_commit import insert_fb

    print_row = {
        "fb_id": "p_ok", "name": "A principle", "definition": "D", "content_type": "principle",
        "status": "PASS", "s5_reason": "entail",
        "verification_results": json.dumps(
            [{"check_name": "factual", "passed": True, "detail": "ENTAIL 3/3"}]
        ),
    }
    assert insert_fb(conn, print_row) is True
    assert conn.execute("SELECT status FROM fbs WHERE fb_id = 'p_ok'").fetchone()[0] == "PASS"


# ── 4. the ingest set and its receipt ────────────────────────────────────────────────────────────


def test_loader_selects_by_the_rows_own_content_type_and_declares_every_exclusion():
    """Integration (read-only): the tier's invariants hold against the run on disk."""
    from pipeline.pipeline_paths import DB_PATH
    from pipeline.stage6_commit import _run_id_for_commit, _stored_fb_ids, load_non_fb_sidecars

    rows, already_stored, receipt = load_non_fb_sidecars(_run_id_for_commit(), _stored_fb_ids(DB_PATH))

    assert rows, "the canonical run must yield a non-principle tier (D2590)"
    assert {r["content_type"] for r in rows} <= set(COMMIT_ROLES)
    assert len({r["fb_id"] for r in rows}) == len(rows), "no duplicate fb_id may be committed"
    # RULE 4: the tier describes the RUN, so the same rows come back whether or not the store has them.
    assert receipt["tier_rows"] == len(rows)
    assert receipt["already_stored_in_tier"] == len(already_stored)
    assert receipt["new_rows"] == len(rows) - len(already_stored)
    assert all(r.get("pipeline_run_id") == receipt["run_id"] for r in rows)
    assert all(r.get("type_body") for r in rows), "every committed row carries its declared body"
    assert all(json.loads(r["type_body"]) for r in rows)
    assert all(r["s5_reason"] == receipt["disposition_reason"] for r in rows)
    # S5-owned columns must be STRIPPED from the input and re-stamped by the gate alone.
    for column in ("epistemic_status", "isor", "practicality", "needs_human_review", "verifier_model",
                   "verification_method", "committed_at"):
        assert all(column not in r for r in rows), f"{column} leaked from a sidecar into the commit set"
    # Every exclusion is declared, never silent.
    assert receipt["excluded"]["not_a_commit_role"] > 0  # 196 principle-typed rows sit in the sidecars
    assert receipt["quarantine_shelf_records"] > 0       # the D2616 hold shelf
    assert receipt["taxonomy_unlabelled"] <= receipt["tier_rows"]
