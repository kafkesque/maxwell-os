"""D-2983 contract for the LADDER RECEIPT — the whole-set verdict as a measurement (BUG-759).

Paired 1:1 with specs/ladder_receipt.spec.md (D-2978: one governed surface, one spec, one contract).
The machine runner is the grader; the spec is the definition, not a report. Every INV in the spec names the
test that decides it, and test_the_spec_is_paired_1to1_with_its_contract enforces that pairing.

No test here runs a full ladder (12 minutes) and no test writes to the declared record: the rule is driven
through its pure functions, and the crash-safe write is driven against a temp path.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAIL = PROJECT_ROOT / "scripts" / "run_ladder.py"
REGISTRY = PROJECT_ROOT / "config" / "rail_registry.yaml"
MUTATIONS = PROJECT_ROOT / "config" / "rail_mutations.yaml"
JUSTFILE = PROJECT_ROOT / "justfile"
SPEC = PROJECT_ROOT / "specs" / "ladder_receipt.spec.md"
MOMENT = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def _rail():
    """The rail under test, loaded from its path (it is a script, not an installed module)."""
    spec = importlib.util.spec_from_file_location("ladder_under_test", RAIL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recipe_body(rail, name: str) -> list[str]:
    """A recipe's declaring lines, read through the RAIL's own rule (never a second parser in this file)."""
    return dict(rail.recipes_of(JUSTFILE.read_text(encoding="utf-8")))[name]


def _record(rail, lines: list[str], *, recipe: str = "health", faults: list | None = None, age_hours: float = 2.0,
            head_at_start: str = "abc1234", head_at_end: str = "abc1234", state: str = "finished",
            worktree: dict | None = None):
    """A synthetic record measured over exactly `lines` - the shape the collector writes, built by hand.

    BUG-1010: the shape now carries WHICH BYTES it is about (`state`, both ends' HEAD, the worktree readings), so a
    control that leaves them out would be driving a record the collector can no longer produce.
    """
    return {
        "schema_version": rail.RECEIPT_SCHEMA,
        "state": state,
        "line_count": len(lines),
        "line_set_fingerprint": rail.line_set_fingerprint(recipe, lines),
        "worst_rc": rail.EXIT_FATAL if faults else rail.EXIT_CLEAN,
        "faults": faults or [],
        "started_at": (MOMENT - timedelta(hours=age_hours, minutes=9)).isoformat(timespec="seconds"),
        "measured_at": (MOMENT - timedelta(hours=age_hours)).isoformat(timespec="seconds"),
        "head_at_start": head_at_start,
        "head_at_end": head_at_end,
        "worktree": worktree if worktree is not None else {
            "modified_at_start": [], "modified_at_end": [], "untracked_at_start": [], "minted_during_scan": []},
    }


def _opening(head: str = "abc1234", modified: list | None = None, untracked: list | None = None) -> dict:
    """The state a scan is a measurement OF, as `snapshot()` reads it at the opening."""
    return {"started_at": (MOMENT - timedelta(minutes=9)).isoformat(timespec="seconds"), "head": head,
            "worktree": {"modified": modified or [], "untracked": untracked or []}}


def test_the_spec_is_paired_1to1_with_its_contract():
    """D-2978: every invariant in the spec names the test that decides it, and every named test exists."""
    spec_text = SPEC.read_text(encoding="utf-8")
    named = re.findall(r"\*\*Test:\*\*\s*`([a-z0-9_]+)`", spec_text)
    invariants = re.findall(r"(?m)^### (INV-\d+)", spec_text)
    assert invariants, "the spec declares no invariants"
    assert len(named) == len(invariants), (
        f"{len(invariants)} invariant(s) but {len(named)} named test(s): an invariant without a test is a claim.")
    defined = set(re.findall(r"(?m)^def (test_[a-z0-9_]+)\(", Path(__file__).read_text(encoding="utf-8")))
    missing = [name for name in named if name not in defined]
    assert not missing, f"the spec names test(s) that do not exist here: {missing}"


def test_the_record_carries_its_coverage_and_age():
    """INV-1: the coverage is the recipe plus its ORDERED lines, and the moment is what makes it ageable."""
    rail = _rail()
    lines = ["echo A", "sh -c 'exit 1'"]
    coverage = rail.line_set_fingerprint("health", lines)
    record = _record(rail, lines)
    assert rail.receipt_verdict(record, coverage, len(lines), recipe="health", now=MOMENT,
                                max_age_hours=72)[0] == rail.EXIT_CLEAN
    assert rail.line_set_fingerprint("health", lines + ["echo B"]) != coverage, "an added line is a new coverage"
    assert rail.line_set_fingerprint("health", list(reversed(lines))) != coverage, "order is part of the coverage"
    assert rail.line_set_fingerprint("health-deep", lines) != coverage, "another recipe is a new coverage"
    assert rail.age_hours(record["measured_at"], MOMENT) == 2.0
    assert rail.age_hours("not a timestamp", MOMENT) is None, "an unreadable moment must not read as 'now'"


def test_a_recorded_red_cannot_go_quiet():
    """INV-2: a measured fault under exactly the coverage in force is FATAL and it NAMES the faults (C16)."""
    rail = _rail()
    lines = ["echo A", "python3 scripts/check_something.py || exit 1"]
    coverage = rail.line_set_fingerprint("health", lines)
    record = _record(rail, lines, faults=[{"line": lines[1], "rc": 1, "seconds": 3.0}])
    rc, message = rail.receipt_verdict(record, coverage, len(lines), recipe="health", now=MOMENT, max_age_hours=72)
    assert rc == rail.EXIT_FATAL, "a recorded red read as green is the blindness BUG-759 filed"
    assert "1 fault" in message and lines[1] in message, "the fault must be NAMED, not merely counted"


def test_unknown_is_owner_owed_and_names_the_remedy():
    """INV-3: never measured here is rc=2 (loud, not fatal), and the remedy is the DERIVED entry point."""
    rail = _rail()
    lines = ["echo A"]
    coverage = rail.line_set_fingerprint("health", lines)
    remedy = rail.remedy_for("health", JUSTFILE.read_text(encoding="utf-8"))
    assert "health-full" in remedy, "the remedy must name the ladder's own whole-set entry point (D-405)"
    rc, message = rail.receipt_verdict(None, coverage, len(lines), recipe="health", now=MOMENT,
                                       max_age_hours=72, absent="no full scan is recorded at temp/x.json",
                                       remedy=remedy)
    assert rc == rail.EXIT_OWED and rc != rail.EXIT_FATAL
    assert "UNKNOWN" in message and "no full scan" in message and "health-full" in message
    stale = _record(rail, lines, age_hours=80.0)
    rc, message = rail.receipt_verdict(stale, coverage, len(lines), recipe="health", now=MOMENT, max_age_hours=72)
    assert rc == rail.EXIT_OWED and "80.0h" in message, "the declared budget is what ages a record out"


def test_a_changed_ladder_invalidates_its_record():
    """INV-4: a record measured over a different line set is evidence for a ladder that no longer exists."""
    rail = _rail()
    recorded_lines = ["echo A"]
    current_lines = ["echo A", "echo B"]
    record = _record(rail, recorded_lines)
    rc, message = rail.receipt_verdict(record, rail.line_set_fingerprint("health", current_lines),
                                       len(current_lines), recipe="health", now=MOMENT, max_age_hours=72)
    assert rc == rail.EXIT_OWED and "UNKNOWN" in message and "CHANGED" in message
    assert record["line_set_fingerprint"] in message and rail.line_set_fingerprint("health", current_lines) in message, (
        "both coverages must appear: the reader has to see WHICH ladder the record speaks for (D-2660)")


def test_the_whole_set_entry_point_is_derived():
    """INV-5: the entry point is READ from the ladder's bytes; a ladder that declares none is reported."""
    rail = _rail()
    assert rail.whole_set_entry("health", JUSTFILE.read_text(encoding="utf-8")) == "health-full", (
        "the entry point must be derived from the ladder, never restated in code or in a message")
    synthetic = ("probe:\n    echo A\n"
                 "fuller:\n    python3 scripts/run_ladder.py --collect probe\n")
    assert rail.whole_set_entry("probe", synthetic) == "fuller"
    near = ("probe:\n    echo A\n"
            "deeper:\n    python3 scripts/run_ladder.py --collect probe-deep\n")
    assert rail.whole_set_entry("probe", near) == "", (
        "'--collect probe-deep' is NOT an entry point for 'probe': a prefix match invents a remedy")
    assert "NO entry point" in rail.remedy_for("probe", near), (
        "a ladder with no whole-set entry point owes a fault, not an invented recipe name (BUG-492)")
    assert rail.whole_set_entry("__absent__", JUSTFILE.read_text(encoding="utf-8")) == ""


def test_the_record_home_is_declared_and_never_committed():
    """INV-6: path/recipe/budget are DECLARED (no code default), and the record stays out of version control."""
    rail = _rail()
    block = rail.receipt_declaration()
    assert {"path", "recipe", "max_age_hours"} <= set(block)
    assert block["recipe"] in dict(rail.recipes_of(JUSTFILE.read_text(encoding="utf-8"))), (
        "the declared recipe must be one the ladder actually declares (D-405)")
    rel = str(block["path"])
    ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index", rel], cwd=PROJECT_ROOT)
    assert ignored.returncode == 0, f"the declared record path {rel} is not ignored by git: it would dirty the tree"
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=PROJECT_ROOT,
                             capture_output=True, text=True)
    assert tracked.returncode != 0, "the record must never be tracked: it is THIS clone's local observation"
    reader = RAIL.read_text(encoding="utf-8").split("def receipt_declaration", 1)[1].split("\ndef ", 1)[0]
    for key in ("path", "recipe", "max_age_hours"):
        assert f'get("{key}", ' not in reader, f"receipt_declaration must not default {key} in code (D-2644/C12)"


def test_the_record_equals_the_measurement(tmp_path, monkeypatch):
    """INV-7: the record IS the measurement, it round-trips, and the write is crash-safe (C6)."""
    rail = _rail()
    lines = ["echo A", "echo B"]
    payload = rail.scan_payload("health", lines, rail.EXIT_FATAL, [(lines[1], 1, 0.44)], 2.26, ladder="justfile",
                               opening=_opening(), head_at_end="deadbee",
                               worktree={"modified": [], "untracked": []}, now=MOMENT, state="finished")
    assert payload["line_count"] == len(lines)
    assert payload["line_set_fingerprint"] == rail.line_set_fingerprint("health", lines)
    assert payload["worst_rc"] == rail.EXIT_FATAL and payload["elapsed_seconds"] == 2.3
    assert payload["faults"] == [{"line": lines[1], "rc": 1, "seconds": 0.4}]
    assert payload["measured_at"] == MOMENT.isoformat(timespec="seconds")
    assert payload["started_at"] == _opening()["started_at"], "the opening is its OWN field, not the write time"
    assert payload["schema_version"] == rail.RECEIPT_SCHEMA and payload["rail"] == "run_ladder.py"
    target = tmp_path / "receipt.json"
    monkeypatch.setattr(rail, "receipt_path", lambda: target)
    written = rail.record_scan("health", lines, rail.EXIT_CLEAN, [], 0.5, opening=_opening(), environ={})
    assert written == target and target.is_file(), "a green scan is recorded too: the record is not a failure log"
    back, absent = rail.recorded_scan()
    assert absent == "" and back["line_set_fingerprint"] == rail.line_set_fingerprint("health", lines)
    assert back["state"] == "finished", "a record that cannot say it FINISHED is not a verdict (BUG-1010)"
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".")] == [], (
        "the crash-safe write must leave no temp file behind (C6)")


def test_the_record_is_a_verdict_about_the_bytes_it_ran():
    """INV-10: a commit NAMES the bytes only while the worktree equals it; every other shape is OWNER-OWED."""
    rail = _rail()
    lines = ["echo A", "echo B"]
    coverage = rail.line_set_fingerprint("health", lines)
    clean = {"modified_at_start": [], "modified_at_end": [], "untracked_at_start": [], "minted_during_scan": []}
    rc, message = rail.receipt_verdict(_record(rail, lines), coverage, len(lines), recipe="health", now=MOMENT,
                                       max_age_hours=72)
    assert rc == rail.EXIT_CLEAN and "abc1234" in message, "a clean scan at an unmoved HEAD is the one green state"
    cases = {
        "a commit landed MID-SCAN": _record(rail, lines, head_at_end="def5678"),
        "the scan BEGAN on a modified tracked file": _record(rail, lines, worktree=dict(
            clean, modified_at_start=["scripts/run_ladder.py"])),
        "the scan ENDED on a modified tracked file": _record(rail, lines, worktree=dict(
            clean, modified_at_end=["config/x.yaml"])),
        "the record names NO commit": _record(rail, lines, head_at_start="", head_at_end=""),
        "the scan never FINISHED": _record(rail, lines, state="running"),
    }
    for why, record in cases.items():
        rc, message = rail.receipt_verdict(record, coverage, len(lines), recipe="health", now=MOMENT,
                                          max_age_hours=72)
        assert rc == rail.EXIT_OWED, f"{why}: must be OWNER-OWED, not green and not fatal (got rc={rc})"
        assert "UNKNOWN" in message or "no fault" in message, f"{why}: the message must say the record is unusable"
    # a recorded RED outranks unattributability: a fault that WAS measured may not be softened into "unknown"
    red = _record(rail, lines, faults=[{"line": lines[1], "rc": 1, "seconds": 0.2}], head_at_end="def5678")
    rc, message = rail.receipt_verdict(red, coverage, len(lines), recipe="health", now=MOMENT, max_age_hours=72)
    assert rc == rail.EXIT_FATAL and "1 fault" in message, "C16: a measured red may not be quieted by a provenance defect"
    # the shape it deliberately does NOT gate: the scan's own OUTPUTS
    minted = _record(rail, lines, worktree=dict(clean, minted_during_scan=["governance/evidence/NEW.json"]))
    rc, message = rail.receipt_verdict(minted, coverage, len(lines), recipe="health", now=MOMENT, max_age_hours=72)
    assert rc == rail.EXIT_CLEAN and "minted during the scan" in message, (
        "D-3151: a rule that reds a scan for leaving an artefact is a rule that gets bypassed - so it is REPORTED")


def test_git_overrides_are_cleared_before_the_worktree_is_read():
    """INV-10: an inherited GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE is never obeyed (BUG-527's class, one level up)."""
    rail = _rail()
    armed = {"GIT_DIR": "/decoy/.git", "GIT_WORK_TREE": "/decoy", "GIT_INDEX_FILE": "/decoy/index", "PATH": "/bin"}
    scrubbed = rail.cleared(armed)
    assert scrubbed == {"PATH": "/bin"}, "git's own overrides must be dropped and everything else KEPT"
    live = rail.worktree_state()
    # the ARMED reading is this process's real environment with the three overrides added, so the only variable
    # between the two readings is the thing under test
    armed_live = dict(os.environ, GIT_DIR="/decoy/.git", GIT_WORK_TREE="/decoy",
                      GIT_INDEX_FILE=str(Path(tempfile.gettempdir()) / ".no_such_index_for_a_control"))
    assert rail.worktree_state(armed_live) == live, (
        "MEASURED on this clone: an inherited empty GIT_INDEX_FILE made `git status --porcelain -uall` answer 3973 "
        "lines against 0 - an unscrubbed reading would mark every scan un-attributable")


def test_the_order_is_load_bearing():
    """INV-8: the record is read FIRST and enforced LAST, and the guard class is pinned (class (ii))."""
    rail = _rail()
    text = JUSTFILE.read_text(encoding="utf-8")
    body = _recipe_body(rail, "health")
    reading = [line for line in body if "run_ladder.py" in line]
    assert "--banner" in reading[0] and "--full" in reading[0], "the banner must stand first, before any rail"
    assert "exit 1" not in reading[0], "a banner that can abort would hide the ladder it exists to declare"
    assert "--receipt-check" in body[-1], "the enforced whole-set check must stand LAST in the recipe"
    assert "[ $? -eq 2 ]" in body[-1], "UNKNOWN is owner-owed: rc=2 must stay loud and not fatal (BUG-457)"
    assert "--receipt-check" not in rail.parse(text, "health"), (
        "the reader drops self-invocations, so the whole-set scan can never be blocked by its own record")
    guards = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["guards"]
    assert guards["scripts/run_ladder.py --receipt-check"] == "tri_state", (
        "the guard class is PINNED: dropping it to fatal, or to nothing, is class (ii) of D-2665")


def test_the_rule_is_mutation_locked_and_its_controls_run():
    """INV-9: the rule has a declared mutation that reds its own named control, and the ladder runs the controls."""
    rail = _rail()
    rules = yaml.safe_load(MUTATIONS.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in rules["mutations"]}
    entry = entries["a_recorded_ladder_red_is_load_bearing"]
    assert entry["subject"] == "scripts/run_ladder.py" and entry["runner_args"] == ["--selftest"]
    assert entry["expect"] == "red" and entry["mutated_rc"] == rail.EXIT_FATAL
    assert entry["marker"] == "  FAIL selftest/a_recorded_ladder_red_is_not_silently_green"
    assert RAIL.read_text(encoding="utf-8").count(entry["find"]) == 1, (
        f"the declared find-text must match exactly one line: {entry['find']!r}")
    assert rules["coverage"]["min_mutations"] <= len(rules["mutations"]), "the mutation floor is a shrink guard"
    body = _recipe_body(rail, "health")
    assert any("run_ladder.py --selftest" in line for line in body), (
        "a control nothing runs is a comment (BUG-492)")
