"""tests/test_handoff_obligation.py - D-2972: the receipt obligation is REFUSED, ATTRIBUTED and FOUND.

WHY THIS FILE EXISTS
--------------------
D-2971 repaired BUG-376 with an act (`scripts/lib/handoff.py --rebaseline`) and left one item OWED, naming it
loudly: the declared in-place routes in `scripts/recompute_decision_summary.py` discharged their receipt
obligation in PROSE ("NEXT (same sitting): re-baseline the receipt"), and a rule that lives in a `print` is a
favour (C12/D-2655) - which is why the rail stayed RED for five days while the obligation sat in a stdout line.
MEASURED at the time: one of those routes recommended `scripts/lib/handoff.py --backfill`, a remedy D-2971 had
explicitly REJECTED (it re-cuts EVERY declared path, moving baselines nobody measured as broken, and remembers
nothing about the rewrite). Two ratified positions about one act, disagreeing on disk.

These controls pin the closure, and each one can fail:

  * the ROUTES refuse to move a receipted region without an owner - the licence is read BEFORE the no-op
    branches, so "there is nothing to do" can never be the door a licence is walked past;
  * the RAIL'S FINDING names the act and NEVER the rejected route, and the finding TEXT has one home, so a
    remedy cannot drift out of the rail while a test still believes it (BUG-746);
  * the ATTRIBUTION is joined BY CONTENT against governance/MUTATION_JOURNAL.jsonl: a governed write whose
    post-image IS the current bytes is named, and a path no governed write records is declared UNATTRIBUTED
    rather than blamed on whichever record happens to be newest (D-403/BUG-488).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib import handoff  # noqa: E402

ROUTES = ROOT / "scripts" / "recompute_decision_summary.py"
RAIL = ROOT / "scripts" / "verify_handoffs.py"
REGISTRY = "config/decisions.yaml"


def _routes_module():
    """Import the in-place routes' module (its CLI is what the licence gate lives in)."""
    import recompute_decision_summary as routes

    return routes


def test_the_in_place_routes_refuse_to_move_a_receipted_region_without_an_owner() -> None:
    """D-2972: an in-place edit of an append_only artifact needs a NAMED decision, or it does not happen."""
    routes = _routes_module()
    prog = "recompute_decision_summary.py"  # argv[0]: the helper reads the TOKENS after it, as main() does
    for flag in (routes.CANONICALISE_FLAG, routes.STRIP_FLAG):
        with pytest.raises(SystemExit) as excinfo:
            routes.in_place_licence([prog, flag, routes.APPLY_FLAG], flag)
        assert routes.LICENCE_FLAG in str(excinfo.value), "the refusal must name the flag the caller owes"
        with pytest.raises(SystemExit) as bogus:
            routes.in_place_licence([prog, flag, routes.LICENCE_FLAG, "D-0000"], flag)
        assert "names no record" in str(bogus.value), (
            "a licence that names a decision which does not exist must be refused: the edit would be "
            "attributable to nothing"
        )
        with pytest.raises(SystemExit):
            routes.in_place_licence([prog, flag, routes.LICENCE_FLAG], flag)
        with pytest.raises(SystemExit):
            routes.in_place_licence([prog, flag, "--teleport"], flag)
        assert routes.in_place_licence([prog, flag, routes.LICENCE_FLAG, "D-2655"], flag) == ("D-2655", False)
        assert routes.in_place_licence([prog, flag, routes.APPLY_FLAG, routes.LICENCE_FLAG, "D-2655"], flag) == (
            "D-2655", True)


def test_the_licence_is_read_before_the_no_op_branch_it_could_hide_behind() -> None:
    """The refusal must not be reachable ONLY when there is work to do: both routes are INERT right now.

    MEASURED today: `--canonicalise-states` refuses as ALREADY CANONICALISED (its pin is empty) and
    `--strip-derived-head` refuses as ALREADY STRIPPED, so a licence checked after those branches would never
    run in this repo - a gate whose only live path is unreachable is a comment (BUG-492).
    """
    routes = _routes_module()
    prog = "recompute_decision_summary.py"
    with pytest.raises(SystemExit):
        routes.strip_main([prog, routes.STRIP_FLAG, "--apply"])
    with pytest.raises(SystemExit):
        routes.canonicalise_main([prog, routes.CANONICALISE_FLAG])
    # ... and with a live licence each route reaches its own no-op verdict, so the refusal above was the
    # LICENCE and not an accident of the route's state: the licence is read first, and preview writes nothing.
    assert routes.strip_main([prog, routes.STRIP_FLAG, routes.LICENCE_FLAG, "D-2655"]) == 0
    assert routes.canonicalise_main([prog, routes.CANONICALISE_FLAG, routes.LICENCE_FLAG, "D-2655"]) == 0


def test_the_remedy_the_rail_prints_never_names_the_route_D_2971_rejected() -> None:
    """The rail's finding is the ONE place a reader learns the act: it must not recommend a rejected one."""
    text = handoff.unrepaired_region_finding("decisions_registry", REGISTRY, "rewritten", "a byte moved")
    assert "--rebaseline decisions_registry --because <D-id>" in text, text
    assert "--backfill" not in text, "D-2971 rejected --backfill as a remedy; the finding must not name it"
    assert "COMMIT" in text, "the ordering is structural: the edit is committed FIRST (BUG-559)"
    assert "UNATTRIBUTED" in text or "post-image of a GOVERNED write" in text, (
        "the finding must say WHO moved the region, or say that nothing recorded it"
    )
    source = ROUTES.read_text(encoding="utf-8")
    assert "--backfill" not in source, (
        "an in-place route still names --backfill, the remedy D-2971 rejected: two ratified positions about "
        "one act disagreeing on disk is exactly the drift this repo fails closed on"
    )


def test_the_obligation_and_its_remedy_have_ONE_home() -> None:
    """D-274a: two implementations of one rule drift, so the text lives where the rule lives (D-2972)."""
    for name in ("unrepaired_region_finding", "rebaseline_next_steps", "attribution_line", "artifact_of"):
        assert callable(getattr(handoff, name, None)), name + " belongs to the receipt module's one home"
    rail = RAIL.read_text(encoding="utf-8")
    assert "handoff.unrepaired_region_finding(" in rail, "the rail must print the rule's own sentence"
    assert "not a prefix of the current bytes" not in rail, (
        "the rail grew a SECOND copy of the finding text - the controls then assert on a sentence nobody prints"
    )
    routes = ROUTES.read_text(encoding="utf-8")
    assert "handoff.rebaseline_next_steps(" in routes, "a route must state the obligation in the act's own words"
    assert "re-baseline the receipt, then --check" not in routes, "the prose obligation is what D-2972 closed"


def test_the_attribution_is_joined_by_CONTENT_and_never_by_recency() -> None:
    """A journal record is a claim about BYTES and `writer` is only a name (D-403)."""
    live = handoff.sha256_file(ROOT / REGISTRY)[:16]
    assert handoff.governed_subject() == REGISTRY, "the positive subject is derived, not restated (C12)"
    rec = handoff.last_governed_write(REGISTRY)
    assert rec is not None, "the registry's current bytes ARE a governed write's post-image (measured)"
    assert str(rec.get("post_sha16")) == live, "the join must be the POST-IMAGE, not the newest record"
    assert str(rec.get("writer") or ""), "an attribution that cannot name the writer is not an attribution"
    assert handoff.attribution_line(REGISTRY).startswith("the bytes now on disk ARE the post-image")

    unrecorded = handoff.unrecorded_subject()
    assert handoff.last_governed_write(unrecorded) is None, (
        unrecorded + " is written by APPEND (never through write_guard), so no governed write owns its bytes"
    )
    line = handoff.attribution_line(unrecorded)
    assert line.startswith("NO governed write is recorded"), line
    assert "writer=" not in line, "the probe must not name a writer it cannot back (D-403/BUG-488)"
    assert handoff.last_governed_write(handoff.ATTRIBUTION_ABSENT_SUBJECT) is None


def test_the_obligation_names_the_artifact_from_its_declaration() -> None:
    """The act re-cuts a DECLARED receipt: the route may not type an artifact id, and an undeclared path refuses."""
    assert handoff.artifact_of(REGISTRY) == "decisions_registry"
    with pytest.raises(SystemExit):
        handoff.artifact_of("config/no-such-declared-artifact.yaml")
    steps = handoff.rebaseline_next_steps(handoff.artifact_of(REGISTRY), "D-2655")
    for token in ("--rebaseline decisions_registry", "--because D-2655", "COMMIT", "UNREVISIONED"):
        assert token in steps, token
