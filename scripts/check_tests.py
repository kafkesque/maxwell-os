#!/usr/bin/env python3
"""scripts/check_tests.py - the SUITE RAIL (D-2656).

WHY THIS EXISTS
---------------
`just health` runs RAILS, not the SUITE (D-390). A failing or stale assertion in
tests/ was therefore INVISIBLE to every rail: BUG-470 sat at HEAD for that reason, and on
2026-09-26 the suite was MEASURED red (3 failed) while `just health` was green - a control
that never fires. This script makes the suite a RAIL: measured, gated, reported.

WHAT IT DECIDES (0 clean | 1 FATAL fail-closed C16 | 2 owner-owed, loud NOT fatal)
---------------------------------------------------------------------------------
  1 FATAL  the pytest summary is UNREADABLE, or fewer tests were collected than the
           declared floor - a collection ERROR must never read as "no tests, pass".
  1 FATAL  a failure NOT in the declared red set (a REGRESSION).
  2 OWED   a declared red test now PASSES - the ceiling is stale and must be shrunk by a
           decision; a paid debt must not stay declared (a declaration that outlives its
           subject is the BUG-542 class).
  0 clean  the failure set equals the declared set exactly.
The declared red set is a CEILING, SHRINK-ONLY (config/test_isolation.yaml). It is NOT a
re-baseline: a NEW failure can never be absorbed by editing that ceiling.

ISOLATION (BUG-546 / BUG-473)
-----------------------------
A suite run is not read-only by nature: on 2026-09-25 it RENAMED a live 1.03 GB S5
checkpoint (BUG-473), and tests/test_stage4_preflight_smoke_stress.py resolved the
PRODUCTION stage root BY HAND and `shutil.rmtree`'d a run dir inside the live tree
(BUG-546, measured 2026-09-26). The destructive path is FIXED, and conftest.py fails the
session (exitstatus 1) on any undeclared move of a production artifact - this rail reads
that as a breach. NOTE: MAXWELL_PIPELINE_ROOT is NOT a sandbox for the suite (config/ and
the books/DB paths also resolve under PROJECT_ROOT) - see config/test_isolation.yaml.

`--selftest` proves every decision above with real fixture suites (BUG-492).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CFG_PATH = REPO / "config" / "test_isolation.yaml"
SECTION = "suite_rail"

SUMMARY_RE = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected)")
NODE_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.MULTILINE)
COUNTS = ("passed", "failed", "skipped", "error", "xfailed", "xpassed", "deselected")
EXIT_CLEAN, EXIT_FATAL, EXIT_OWED = 0, 1, 2


def _cfg() -> dict:
    """The declared rail config. An absent or malformed section FAILS CLOSED (C16).

    The interpreter refusal is the BUG-1094 half of the BUG-1000 class: this rail reads a YAML config and
    RUNS the suite, so a bare `python3 scripts/check_tests.py` from a shell whose `python3` has neither PyYAML
    nor pytest must say so BY ABSOLUTE PATH and name the command that works (D-3100), never raise a bare
    ModuleNotFoundError from inside a loader - the operator learns nothing about which interpreter to use.
    """
    try:
        import yaml
    except ModuleNotFoundError:  # C16: not silent, and not an unattributable traceback either (D-3100)
        raise SystemExit(
            "FAIL-CLOSED (C16): the interpreter running this rail cannot import PyYAML, so it cannot read its "
            "own declaration.\n"
            f"  running as : {sys.executable}\n"
            f"  needs      : {CFG_PATH.relative_to(REPO)}\n"
            "  run it as  : just health   (the justfile prepends the repo pin, scripts/resolve_python.sh,\n"
            "               which PROVES the pin can import what the rails need - BUG-1000/BUG-1094)")

    data = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or SECTION not in data:
        raise SystemExit(f"FAIL-CLOSED (C16): {CFG_PATH} declares no '{SECTION}:' section - "
                         "the rail would be reading a default, which is a declaration with no home (C12)")
    sec = data[SECTION]
    if not isinstance(sec, dict):
        raise SystemExit(f"FAIL-CLOSED (C16): '{SECTION}:' is not a mapping")
    return sec


def parse_counts(text: str) -> dict | None:
    """Every 'N <outcome>' pair on the pytest summary line, or None when unreadable."""
    out: dict = {}
    for m in SUMMARY_RE.finditer(text):
        key = m.group(2)
        if key == "errors":
            key = "error"
        out[key] = int(m.group(1))
    if "passed" not in out and "failed" not in out and "error" not in out:
        return None
    return out


def collected_of(counts: dict) -> int:
    """Total collected tests, derived from the summary only (no second source)."""
    return sum(counts[k] for k in COUNTS if k in counts)


def failed_ids(text: str) -> list[str]:
    """The node ids pytest reported as FAILED/ERROR, sorted, de-duplicated."""
    return sorted({m.group(2) for m in NODE_RE.finditer(text)})


def classify(text: str, red: list[str], floor: int, strict: bool) -> tuple[int, list[str], dict]:
    """Decide the rail's verdict from the raw pytest output. Pure - the selftest drives it."""
    counts = parse_counts(text)
    if counts is None:
        return EXIT_FATAL, ["pytest printed no readable summary line - the rail cannot read its "
                            "subject, so it must not pass (C16)"], {}
    got = collected_of(counts)
    fails = failed_ids(text)
    red_set = set(red)
    new = sorted(set(fails) - red_set)
    paid = sorted(x for x in red_set if x not in set(fails))
    detail = {"collected": got, "passed": counts.get("passed", 0), "failed": counts.get("failed", 0),
              "skipped": counts.get("skipped", 0), "error": counts.get("error", 0),
              "failed_ids": fails, "new_failures": new, "paid_red": paid}
    fatal: list[str] = []
    if got < floor:
        fatal.append(f"collected {got} test(s) < declared floor {floor} - a collection ERROR must "
                     "not read as 'no tests, pass' (BUG-492 false-witness)")
    if new:
        fatal.append(f"{len(new)} NEW failure(s) outside the declared red set (a REGESSION, never "
                     "absorbed by editing the ceiling): " + ", ".join(new))
    if counts.get("error", 0):
        fatal.append(f"{counts['error']} ERROR(s) - a test that cannot run is not a test that passed")
    if strict and red_set & set(fails):
        fatal.append(f"--strict: {len(red_set & set(fails))} declared red test(s) still fail - the deep "
                     "rail demands the suite green")
    if fatal:
        return EXIT_FATAL, fatal, detail
    if paid:
        return EXIT_OWED, [f"{len(paid)} declared red test(s) now PASS - the ceiling is STALE and must "
                           "be shrunk by a decision; a paid debt must not stay declared: " + ", ".join(paid)], detail
    return EXIT_CLEAN, [], detail


def run_suite(sec: dict) -> str:
    """Run the declared invocation at the repo root and return its combined output.

    THE SUBJECT IS NOT INHERITED FROM THE SHELL (BUG-1094: the BUG-1000 shape INSIDE a rail). MEASURED
    2026-10-27: `suite_rail.invocation` names a bare `python3`, which is resolved by PATH ORDER - so under
    `just` (which prepends the repo pin, scripts/resolve_python.sh) this rail read 580 tests and 1 real
    failure, while from a shell whose `python3` is /usr/bin/python3 (3.9.6, no PyYAML, no pytest) the VERY
    SAME rail read NOTHING and reported 'no readable summary' - a FATAL about the SHELL, dressed as a verdict
    on tests/. A rail that cannot name its own interpreter reports whichever subject PATH hands it.

    TWO ACTS, BOTH HERE. (1) A bare `python3`/`python` in the DECLARED invocation is substituted with the
    interpreter RUNNING this rail - the same rule scripts/r5_review_gate.py:137 and run_ladder.run_layer()
    already apply, so there is no second home for it. (2) An interpreter with no pytest is REFUSED loudly
    and by absolute path, because 'unreadable summary' is not a symptom the operator can act on (D-3100:
    a handover names the command that works).
    """
    inv = sec["invocation"]
    if not isinstance(inv, list) or not inv:
        raise SystemExit("FAIL-CLOSED (C16): suite_rail.invocation must be a non-empty list")
    if importlib.util.find_spec("pytest") is None:
        raise SystemExit(
            "FAIL-CLOSED (C16): the interpreter running this rail cannot import pytest, so the suite cannot be "
            f"read AT ALL - a fact about the INTERPRETER, never a verdict on tests/.\n"
            f"  running as : {sys.executable}\n"
            f"  declared   : {inv}\n"
            "  run it as  : just health   (the justfile prepends the repo pin, scripts/resolve_python.sh,\n"
            "               which PROVES the pin can import what the rails need - BUG-1000)\n"
            "  why        : the declared invocation names a bare python3, resolved by PATH ORDER (BUG-1094); "
            "this rail substitutes sys.executable for it, so the interpreter you launch with is the one that "
            "must have the dependencies.")
    argv = [sys.executable if str(part) in ("python3", "python") else str(part) for part in inv]
    try:
        r = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                           timeout=int(sec["timeout_seconds"]))
    except subprocess.TimeoutExpired:
        raise SystemExit(f"FAIL-CLOSED (C16): the suite exceeded suite_rail.timeout_seconds="
                         f"{sec['timeout_seconds']} - a rail that hangs is a rail that lies by omission")
    return (r.stdout or "") + (r.stderr or "")


def check(strict: bool, as_json: bool) -> int:
    """Run the rail. Prints ONE line when clean; names every reason when it is not."""
    sec = _cfg()
    red = list(sec["known_red"])
    floor = int(sec["min_collected"])
    text = run_suite(sec)
    rc, reasons, detail = classify(text, red, floor, strict)
    if as_json:
        print(json.dumps({"rc": rc, "reasons": reasons, **detail}, indent=2, sort_keys=True))
        return rc
    if rc == EXIT_CLEAN:
        print(f"ok tests: {detail['collected']} collected (floor {floor}), {detail['passed']} passed, "
              f"{len(red)} declared red (shrink-only: {sec['known_red_reason'].split(' - ')[0]}), "
              f"0 new, {detail['skipped']} skipped")
        return rc
    tag = "FAIL tests" if rc == EXIT_FATAL else "OWED tests"
    print(f"{tag}: the suite is not in its declared shape:")
    for reason in reasons:
        print(f"  - {reason}")
    if detail:
        print(f"  measured: {detail['collected']} collected, {detail['passed']} passed, "
              f"{detail['failed']} failed, {detail['error']} error; declared red = {len(red)}")
    return rc


def selftest() -> int:
    """Known-answer controls: every decision this rail makes must be SEEN to fire (BUG-492)."""
    red = ["tests/test_x.py::test_declared"]
    cases: list[tuple[str, str, list[str], int, bool]] = [
        ("all green, nothing declared", "2 passed in 0.01s", [], 1, False),
        ("exactly the declared red", "1 failed, 1 passed in 0.01s\nFAILED tests/test_x.py::test_declared", red, 1, False),
        ("a NEW failure", "2 failed in 0.01s\nFAILED tests/test_x.py::test_declared\nFAILED tests/test_y.py::test_other",
         red, 1, False),
        ("a collection FLOOR breach", "1 passed in 0.01s", red, 9, False),
        ("a collection ERROR", "1 error in 0.01s\nERROR tests/test_z.py::test_broken", red, 1, False),
        ("unreadable summary", "Internal error: crashed before collection", red, 1, False),
        ("a PAID declared red", "2 passed in 0.01s", red, 1, False),
        ("strict with a declared red still failing", "1 failed in 0.01s\nFAILED tests/test_x.py::test_declared", red, 1, True),
    ]
    want = [EXIT_CLEAN, EXIT_CLEAN, EXIT_FATAL, EXIT_FATAL, EXIT_FATAL, EXIT_FATAL, EXIT_OWED, EXIT_FATAL]
    bad = 0
    for (name, text, r, floor, strict), expect in zip(cases, want):
        rc, reasons, _ = classify(text, r, floor, strict)
        ok = rc == expect
        bad += 0 if ok else 1
        print(f"  {'ok ' if ok else 'FAIL'} selftest/{name}: rc={rc} expected={expect}"
              f"{'' if ok else ' :: ' + '; '.join(reasons)}")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "tests").mkdir()
        (root / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (root / "tests" / "test_bad.py").write_text("def test_bad():\n    assert False\n", encoding="utf-8")
        for label, target, floor, expect in (("real green run", "tests/test_ok.py", 1, EXIT_CLEAN),
                                             ("real red run", "tests/test_bad.py", 1, EXIT_FATAL),
                                             ("real empty run", "tests/test_ok.py", 9, EXIT_FATAL)):
            r = subprocess.run([sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider"],
                               cwd=str(root), capture_output=True, text=True)
            rc, reasons, detail = classify((r.stdout or "") + (r.stderr or ""), [], floor, False)
            ok = rc == expect
            bad += 0 if ok else 1
            print(f"  {'ok ' if ok else 'FAIL'} selftest/{label}: rc={rc} expected={expect} "
                  f"(collected {detail.get('collected')}){'' if ok else ' :: ' + '; '.join(reasons)}")
    print(f"selftest: {'ok - every decision fired' if not bad else f'FAIL - {bad} control(s) did not fire'} "
          f"({len(cases) + 3} controls)")
    return EXIT_CLEAN if not bad else EXIT_FATAL


def main() -> int:
    """CLI: --check (default) | --selftest | --strict | --json."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="run the rail (default)")
    ap.add_argument("--selftest", action="store_true", help="the rail's own known-answer controls")
    ap.add_argument("--strict", action="store_true", help="fail when any declared red test still fails")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return check(a.strict, a.json)


if __name__ == "__main__":
    sys.exit(main())
