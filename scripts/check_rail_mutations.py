#!/usr/bin/env python3
"""check_rail_mutations.py - THE MUTATION GATE (D-2676): the STANDING RULE's teeth (iv).

WHY THIS EXISTS
    The standing rule (adopted 2026-09-27, D-2676): no rule lands without (i) ONE HOME for the rule, (ii) a
    BOUNDARY CONTROL that has been SEEN, (iii) a NAMED oracle, (iv) a MUTATION that REDs that oracle. (i)-(iii)
    each have a rail; (iv) had none, so a rule could pass every check in this repository without anyone ever
    showing the rule CAN FAIL. MEASURED: every instance of the class behind BUG-527/566/568/569/574 was a rule
    whose DECLARATION was read while its SUBJECT was never mutated.

WHAT IT DECIDES (0 clean | 1 FATAL fail-closed C16 | 2 owner-owed: a runner over the declared time ceiling)
    1 FATAL a declared mutation DOES NOT RED its declared control (the rule is declared, not read), reds WITHOUT
            the declared marker (a crash is not a control, BUG-492), or reds in the BASELINE (no differential).
    1 FATAL a mutation whose find-text no longer matches the bytes, is byte-identical to its subject, or whose
            declared subject/runner is absent - a declaration that DRIFTED FROM REALITY (D-405).
    1 FATAL the NEGATIVE CONTROL reds: a no-op mutation changed a verdict, so the runner's input is uncontrolled.
    1 FATAL COVERAGE: fewer mutations than the declared FLOOR, or a declared subject with no mutation entry.
    1 FATAL COVERAGE JOIN (D-2679): a rail at the COMMIT BOUNDARY that the declared coverage does not name, or a
            join whose declared registry/key/line cannot be read at all (a join that cannot be evaluated is a
            VERDICT, never a traceback: the BUG-579 rule, one level up).
    2 OWED  a runner slower than the declared ceiling (class iii of D-2665) - loud, never fatal (BUG-457).

EVERY fact is DECLARED in config/rail_mutations.yaml (C12): no path, count, marker or verdict is written here.

THE COVERAGE JOIN (D-2679). The rails the standing rule covers are a SUPERSET of the rails at the COMMIT BOUNDARY,
and the boundary set is READ from its ONE home (config/rail_registry.yaml#commit_boundary, declared in
config/rail_mutations.yaml#coverage.boundary_join) and JOINED here - never restated. MEASURED before the join:
RAIL 3 (verify_recalibration_pins.py) and RAIL 5 (check_declaration_consumers.py) gated EVERY commit while this
gate reported coverage of the list it happened to hold, so two boundaries were covered on PAPER only - the
D-2676 class turned on the standing rule's own coverage. The registry the join reads is verified against the bytes
of the path GIT resolves for the commit boundary (git-path:hooks/pre-commit) by scripts/check_rail_registry.py, so the derivation rests on a checked declaration. The
SUPERSET direction is declared, not assumed: a rail whose own rule gates the boundary (the rehearsal, D-2675) is
covered BEYOND the boundary, which is not a fault.
The fixture is a REAL repository (git init + commit) built from DECLARED paths in the SYSTEM temp dir, so it is
never inside the tree it audits (BUG-537) and the rails read a real ambient git subject (BUG-527). --selftest
proves every decision above on synthetic observations, including the joins that read the DECLARATION itself.

A DECLARED FIXTURE INPUT MUST EXIST (BUG-589). MEASURED 2026-09-27: the first subject whose runner reads a
path the fixture never carried (governance/bug_status.json, read by recompute_decision_summary.py --selftest)
made that runner's BASELINE red, and this gate blamed the MUTATION - a MISDIAGNOSIS of which of the two facts
was wrong (D-405: a declaration whose subject is absent is an assertion). The declaration is now read BEFORE
the fixture is built and the verdict names the missing input.
"""
from __future__ import annotations

import argparse
import copy
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib import fixture  # noqa: E402 - BUG-577: the fixture rules have ONE home, never a copy

CFG = REPO / "config" / "rail_mutations.yaml"
EXIT_CLEAN, EXIT_FATAL, EXIT_OWED = 0, 1, 2
REQUIRED_KEYS = ("id", "subject", "op", "runner", "runner_args", "expect", "mutated_rc", "marker", "why")


@dataclass(frozen=True)
class Obs:
    """One measured fact: an exit code, the text that accompanied it, and how long it took."""

    rc: int
    text: str = ""
    secs: float = 0.0


def cfg() -> dict[str, Any]:
    """Read the ONE home of every declared mutation; a missing or under-declared entry is a defect, not a pass."""
    if not CFG.exists():
        raise SystemExit("FAIL-CLOSED (C16): config/rail_mutations.yaml is missing - without it the standing rule "
                         "is prose again, which is the state this gate exists to end (BUG-462 class)")
    doc: Any = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not doc.get("mutations") or not doc.get("coverage") or not doc.get("fixture"):
        raise SystemExit("FAIL-CLOSED (C16): config/rail_mutations.yaml declares no fixture/coverage/mutations")
    for m in doc["mutations"]:
        for k in REQUIRED_KEYS:
            if k not in m:
                raise SystemExit("FAIL-CLOSED (C16): mutation " + repr(m.get("id")) + " declares no " + repr(k)
                                 + " - an undeclared fact is an assertion (C12)")
        if str(m["op"]) not in ("replace", "append"):
            raise SystemExit("FAIL-CLOSED (C16): mutation " + repr(m["id"]) + " declares op " + repr(m["op"]))
        if str(m["op"]) == "replace" and ("find" not in m or "replace" not in m):
            raise SystemExit("FAIL-CLOSED (C16): mutation " + repr(m["id"]) + " replaces without find/replace")
        if str(m["op"]) == "append" and not m.get("append"):
            raise SystemExit("FAIL-CLOSED (C16): mutation " + repr(m["id"]) + " appends without text")
        if str(m["expect"]) not in ("red", "green"):
            raise SystemExit("FAIL-CLOSED (C16): mutation " + repr(m["id"]) + " declares expect " + repr(m["expect"]))
    if (not doc["coverage"].get("required_subjects") or not doc["coverage"].get("boundary_join")
            or not doc.get("budget")):
        raise SystemExit("FAIL-CLOSED (C16): coverage declares no required_subjects / boundary_join, or budget "
                         "declares no ceiling - the coverage join's ONE home is a declaration (D-2679)")
    return doc


def fixture_declaration_problems(f: dict[str, Any], repo: Path) -> list[str]:
    """Every DECLARED fixture input must EXIST; a missing one is a fault about the FIXTURE, never about a mutation.

    WHY THIS EXISTS (BUG-589). A runner reads the fixture, so an input the fixture never carried reds that
    runner's BASELINE - and this gate's verdict then says "the oracle's BASELINE is not green ... so its red
    after one proves nothing" and "the runner DID go red, but not through the declared control". MEASURED
    2026-09-27: both sentences were TRUE and both named the wrong object. scripts/recompute_decision_summary.py
    --selftest reads governance/bug_status.json (its bug citations are checked against the register), the
    fixture declared only justfile, and the FIRST subject whose runner needed an undeclared input was reported
    as a bad MUTATION. A declaration that cannot be evaluated against reality is how a gate misdiagnoses its own
    subject (D-405: a declaration whose subject is absent is an assertion).
    """
    problems: list[str] = []
    for bucket, kind in (("include_dirs", "dir"), ("include_files", "file")):
        for x in f.get(bucket) or []:
            here = repo / str(x)
            exists = here.is_dir() if kind == "dir" else here.is_file()
            if not exists:
                problems.append("fixture." + bucket + " names " + repr(x) + ", which does not EXIST: a declared "
                                "input the fixture never carries is an assertion (D-405), and a runner that reads "
                                "it reds in its BASELINE (BUG-589)")
    for g in f.get("include_globs") or []:
        if not [p for p in sorted(repo.glob(str(g)))]:
            problems.append("fixture.include_globs names " + repr(g) + ", which matches NOTHING: a glob that "
                            "silently carries no input is an assertion (D-405)")
    return problems


def build(doc: dict[str, Any]) -> Path:
    """Materialize a REAL repository of the DECLARED paths in the system temp dir; fail closed at every step."""
    f = doc["fixture"]
    absent = fixture_declaration_problems(f, REPO)
    if absent:
        raise SystemExit("FAIL-CLOSED (C16): the fixture does not carry the inputs its runners read, so a "
                         "BASELINE would red for a reason that is not the mutation's and this gate would "
                         "blame the MUTATION (BUG-589): " + "; ".join(absent))
    root = Path(tempfile.mkdtemp(prefix=str(f["prefix"]))).resolve()
    fixture.outside_tree(root, where="the mutation fixture")
    for d in f["include_dirs"]:
        shutil.copytree(REPO / str(d), root / str(d), symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for x in f["include_files"]:
        here = root / str(x)
        here.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / str(x), here)
    for g in f["include_globs"]:
        for p in sorted(REPO.glob(str(g))):
            here = root / p.relative_to(REPO).parent
            here.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, here / p.name)
    steps = {"init": ["git", "init", "-q", "."], "add": ["git", "add", "-A"],
             "commit": ["git", "-c", "user.email=" + str(f["commit_identity"]["email"]),
                        "-c", "user.name=" + str(f["commit_identity"]["name"]),
                        "commit", "-qm", str(f["commit_message"])]}
    for step in f["git"]:
        p = subprocess.run(steps[str(step)], cwd=root, capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit("FAIL-CLOSED (C16): the fixture could not be a REAL repository (git " + str(step)
                             + " rc=" + str(p.returncode) + ": " + (p.stdout + p.stderr).strip()[:200]
                             + ") - a rail would then red for a reason that is not the mutation's (BUG-527)")
    return root


def run(root: Path, rel: str, args: list[str], timeout: int, seconds: float | None = None) -> Obs:
    """Run one runner in the fixture; a timeout is an OBSERVATION (124), never an exception."""
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, rel, *args], cwd=root, capture_output=True, text=True, timeout=timeout)
        rc, out = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rc, out = 124, "TIMEOUT after " + str(timeout) + "s"
    return Obs(rc, out, seconds if seconds is not None else time.time() - t0)


def measure(doc: dict[str, Any]) -> tuple[dict[str, Obs], Path]:
    """Baseline then mutated, per entry; the FIXTURE copy is restored in a finally - the live tree is never written."""
    root = build(doc)
    obs: dict[str, Obs] = {}
    for m in doc["mutations"]:
        mid = str(m["id"])
        subj = REPO / str(m["subject"])
        if not subj.is_file():
            obs[mid + ".declared"] = Obs(1, "the declared subject does not exist on disk: " + str(m["subject"]))
            continue
        tmo = int(m.get("timeout_seconds") or doc["fixture"]["timeout_seconds"])
        args = [str(a) for a in m["runner_args"]]
        obs[mid + ".base"] = run(root, str(m["runner"]), args, tmo)
        original = subj.read_text(encoding="utf-8")
        if str(m["op"]) == "replace":
            n = original.count(str(m["find"]))
            if n != 1:
                obs[mid + ".declared"] = Obs(1, "the mutation's find-text matches " + str(n) + " time(s) in "
                                             + str(m["subject"]) + " (exactly 1 required) - the declaration has "
                                             "DRIFTED from the bytes it claims to mutate, so it proves nothing")
                continue
            mutated = original.replace(str(m["find"]), str(m["replace"]))
        else:
            mutated = original + str(m["append"])
        if mutated == original:
            obs[mid + ".declared"] = Obs(1, "the mutation is byte-identical to its subject: it mutates nothing, so "
                                           "it can prove nothing")
            continue
        target = root / str(m["subject"])
        try:
            target.write_text(mutated, encoding="utf-8")
            obs[mid + ".mut"] = run(root, str(m["runner"]), args, tmo)
        finally:
            target.write_text(original, encoding="utf-8")
    return obs, root


def boundary_rails(doc: dict[str, Any]) -> tuple[list[str], list[str]]:
    """The rails at the COMMIT BOUNDARY, READ from the ONE home of that fact (D-2679) - never restated here.

    Returns (rails, faults): a fault is a FATAL string, never an exception, so a join that cannot be evaluated
    produces a VERDICT instead of a traceback (the BUG-579 rule, one level up: a crash is not a control). The
    registry read here is itself verified against the bytes of gitdir:hooks/pre-commit by
    scripts/check_rail_registry.py, and config/declaration_consumers.yaml declares THIS gate as a consumer of it.
    """
    join = (doc.get("coverage") or {}).get("boundary_join") or {}
    reg = REPO / str(join.get("registry") or "")
    if not str(join.get("registry") or "") or not reg.is_file():
        return [], ["the coverage join names " + repr(join.get("registry")) + ", which does not EXIST: a join to "
                    "nothing is an assertion (D-405), and the standing rule's coverage would fall back to being "
                    "restated here instead of derived (D-2679)"]
    node: Any = yaml.safe_load(reg.read_text(encoding="utf-8"))
    for part in [x for x in str(join.get("key") or "").split(".") if x]:
        if not isinstance(node, dict) or part not in node:
            return [], ["the coverage join reads " + str(join.get("registry")) + "#" + str(join.get("key"))
                        + ", a key that is ABSENT: the standing rule's coverage cannot be derived from it (D-2679)"]
        node = node[part]
    lines = [str(x) for x in (node if isinstance(node, list) else [])]
    if not lines:
        return [], ["the coverage join reads " + str(join.get("registry")) + "#" + str(join.get("key")) + " and "
                    "finds no line at all: a commit boundary nothing declares is a boundary nothing gates (D-405)"]
    prefix, suffix = str(join.get("script_prefix") or ""), str(join.get("script_suffix") or "")
    rails: list[str] = []
    for line in lines:
        here = [t for t in line.split() if t.startswith(prefix) and t.endswith(suffix)]
        if not here:
            return [], ["a commit-boundary line names no " + prefix + "*" + suffix + " script (" + line + "): a "
                        "boundary rule that cannot be joined to a rail is a rule nothing can test (C16)"]
        rails.extend(here)
    return sorted(set(rails)), []


def classify(obs: dict[str, Obs], doc: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    """Every declared claim is either MEASURED or FATAL; a missing observation is never a pass (C16)."""
    fatal: list[str] = []
    owed: list[str] = []
    ceiling = float(doc["budget"]["max_seconds_per_runner"])
    red = [m for m in doc["mutations"] if str(m["expect"]) == "red"]
    for m in doc["mutations"]:
        mid = str(m["id"])
        drift = obs.get(mid + ".declared")
        if drift is not None:
            fatal.append("mutation " + mid + " can prove nothing: " + drift.text)
            continue
        base, mut = obs.get(mid + ".base"), obs.get(mid + ".mut")
        if base is None or mut is None:
            fatal.append("mutation " + mid + " produced no observation (a missing observation is never a pass)")
            continue
        marker = str(m["marker"])
        if base.rc != 0:
            fatal.append("mutation " + mid + ": the oracle's BASELINE is not green (rc=" + str(base.rc) + "): the "
                         "runner is already red before any mutation, so its red after one proves nothing")
        if str(m["expect"]) == "red":
            if marker in base.text and bool(m.get("marker_absent_in_baseline", True)):
                fatal.append("mutation " + mid + ": " + repr(marker) + " is ALREADY in the baseline - there is no "
                             "differential, so this entry measures nothing")
            if mut.rc != int(m["mutated_rc"]):
                fatal.append("mutation " + mid + " DID NOT RED the oracle: rc=" + str(mut.rc) + ", declared "
                             + str(m["mutated_rc"]) + " - " + str(m["runner"]) + " keeps its verdict while "
                             + str(m["subject"]) + " is mutated: the rule is DECLARED but not READ")
            elif marker not in mut.text:
                fatal.append("mutation " + mid + ": the runner DID go red, but not through the declared control "
                             + repr(marker) + " - a RED for an undeclared reason is a crash, not a control")
        else:
            if mut.rc != int(m["mutated_rc"]) or marker not in mut.text:
                fatal.append("mutation " + mid + " (NEGATIVE CONTROL) changed the verdict: rc=" + str(mut.rc)
                             + ", marker " + repr(marker) + (" present" if marker in mut.text else " ABSENT")
                             + " - a no-op mutation that reds means the runner's input is uncontrolled (class iii)")
        for ob, lbl in ((base, "baseline"), (mut, "mutated")):
            if ob.secs > ceiling:
                owed.append("mutation " + mid + ": the " + lbl + " run took " + ("%.1f" % ob.secs) + "s, over the "
                            "declared ceiling of " + str(ceiling) + "s - a runner that slow has an uncontrolled "
                            "input (class iii of D-2665); owner-owed, never fatal (BUG-457)")
    for p in sorted({str(m[k]) for m in doc["mutations"] for k in ("subject", "runner")}):
        if not (REPO / p).is_file():
            fatal.append("a declared path does not exist: " + p + " - a declaration whose subject is absent is an "
                         "assertion (D-405), and it can silently outlive a rename")
    if len(doc["mutations"]) < int(doc["coverage"]["min_mutations"]):
        fatal.append("the gate tests " + str(len(doc["mutations"])) + " mutation(s), below the declared floor of "
                     + str(doc["coverage"]["min_mutations"]) + " - the floor is the shrink guard: lower it in a "
                     "DIFF A HUMAN READS, never by quietly deleting an entry")
    covered = {str(m["subject"]) for m in red}
    declared = {str(s) for s in doc["coverage"]["required_subjects"]}
    for s in sorted(declared):
        if s not in covered:
            fatal.append("declared subject " + s + " has no mutation entry: the standing rule covers it on "
                         "PAPER only (D-2676: a rule that cannot be made to fail is not a rule)")
    # D-2679: the coverage set is JOINED to the ONE home of the commit boundary in the direction that matters - a
    # rail that gates EVERY commit must be covered. The reverse is deliberately NOT a fault, and the reason is
    # declared rather than assumed: a rail whose own rule gates the boundary (the rehearsal, D-2675) is covered
    # BEYOND the boundary, so the coverage set is a declared SUPERSET, not a copy.
    rails, join_faults = boundary_rails(doc)
    fatal.extend(join_faults)
    for r in rails:
        if r not in declared:
            fatal.append("D-2679: the commit boundary names " + r + " but the standing rule's coverage does not - "
                         "a rail that gates EVERY commit must be the subject of a mutation (D-2676), and the "
                         "coverage list must never be a SECOND HOME of 'this rail gates a commit': two lists of one "
                         "fact drift, and only one of them can be right")
    return (EXIT_FATAL if fatal else (EXIT_OWED if owed else EXIT_CLEAN)), fatal, owed


def clean_obs(doc: dict[str, Any]) -> dict[str, Obs]:
    """The GREEN observation set: baseline clean, every red entry red through its own declared marker."""
    obs: dict[str, Obs] = {}
    for m in doc["mutations"]:
        mid = str(m["id"])
        obs[mid + ".base"] = Obs(0, "clean baseline: every control fires")
        if str(m["expect"]) == "red":
            obs[mid + ".mut"] = Obs(int(m["mutated_rc"]), "  FAIL selftest/declared-control: rc="
                                   + str(m["mutated_rc"]) + " :: " + str(m["marker"]) + "\n")
        else:
            obs[mid + ".mut"] = Obs(int(m["mutated_rc"]), str(m["marker"]) + " (synthetic observation: only the marker matters)\n")
    return obs


def selftest() -> int:
    """Known-answer controls: every decision must be SEEN to fire, including the joins that read the DECLARATION."""
    doc = cfg()
    base = clean_obs(doc)
    red0 = next(m for m in doc["mutations"] if str(m["expect"]) == "red")
    grn0 = next(m for m in doc["mutations"] if str(m["expect"]) == "green")
    rid, gid = str(red0["id"]), str(grn0["id"])
    ceiling = float(doc["budget"]["max_seconds_per_runner"])
    cases: list[tuple[str, dict[str, Obs], int]] = [("clean_gate", dict(base), EXIT_CLEAN)]
    m = dict(base)
    m[rid + ".declared"] = Obs(1, "the mutation's find-text matches 0 time(s) - the declaration has DRIFTED")
    cases.append(("stale_mutation_text_is_fatal", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".declared"] = Obs(1, "the declared subject does not exist on disk: scripts/gone.py")
    cases.append(("declared_subject_absent_is_fatal", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".mut"] = Obs(0, "all controls ok")
    cases.append(("mutation_did_not_red (the rule is not read)", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".mut"] = Obs(1, "Traceback (most recent call last): TypeError: unsupported operand")
    cases.append(("red_for_an_undeclared_reason (a crash is not a control)", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".base"] = Obs(0, str(red0["marker"]) + " already present before any mutation")
    cases.append(("marker_already_in_baseline (no differential)", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".base"] = Obs(1, "FAIL some-other-control: the runner is already red")
    cases.append(("baseline_not_green (a red proves nothing)", m, EXIT_FATAL))
    m = dict(base)
    m[gid + ".mut"] = Obs(1, "FAIL selftest/anything: a no-op mutation changed a verdict")
    cases.append(("no_op_mutation_red (input uncontrolled)", m, EXIT_FATAL))
    m = dict(base)
    del m[rid + ".mut"]
    cases.append(("observation_missing (never a silent pass)", m, EXIT_FATAL))
    m = dict(base)
    m[rid + ".base"] = Obs(0, "clean baseline", ceiling + 1.0)
    cases.append(("slow_runner_is_owner_owed", m, EXIT_OWED))
    floor = copy.deepcopy(doc)
    floor["coverage"]["min_mutations"] = len(doc["mutations"]) + 1
    cases.append(("coverage_floor_is_read", dict(base), EXIT_FATAL))
    blind = copy.deepcopy(doc)
    blind["coverage"]["required_subjects"] = ["scripts/no_such_declared_rail.py"]
    cases.append(("required_subject_declaration_is_read", dict(base), EXIT_FATAL))
    # D-2679: the coverage list may not go STALE when the COMMIT BOUNDARY grows, and a join that cannot be
    # evaluated must be a VERDICT rather than a traceback (the BUG-579 rule, applied to this gate's own join).
    boundary = copy.deepcopy(doc)
    uncovered = boundary_rails(doc)[0][0]
    boundary["coverage"]["required_subjects"] = [s for s in doc["coverage"]["required_subjects"] if s != uncovered]
    cases.append(("boundary_rail_missing_from_coverage", dict(base), EXIT_FATAL))
    no_join = copy.deepcopy(doc)
    no_join["coverage"]["boundary_join"]["registry"] = "config/no_such_registry.yaml"
    cases.append(("coverage_join_to_nothing", dict(base), EXIT_FATAL))
    docs = {"coverage_floor_is_read": floor, "required_subject_declaration_is_read": blind,
            "boundary_rail_missing_from_coverage": boundary, "coverage_join_to_nothing": no_join}
    bad = 0
    for name, obs, expect in cases:
        rc, fatal, owed = classify(obs, docs.get(name, doc))
        good = rc == expect
        bad += 0 if good else 1
        print("  " + ("ok  " if good else "FAIL") + " selftest/" + name + ": rc=" + str(rc) + " expected="
              + str(expect) + ("" if good else " :: " + "; ".join((fatal + owed)[:1])))
    joins = [("every declared mutation names a subject and a runner that EXIST (D-405, both directions)",
              all((REPO / str(m[k])).is_file() for m in doc["mutations"] for k in ("subject", "runner"))),
             ("the fixture is built from DECLARED paths under the SYSTEM temp dir, never inside the tree (BUG-537)",
              bool(doc["fixture"]["include_dirs"]) and str(doc["fixture"]["under"]) == "system_temp"),
             ("a declared fixture input that does not EXIST is a fault, so an under-declared fixture is caught "
              "before it is blamed on a mutation (BUG-589)",
              not fixture_declaration_problems(doc["fixture"], REPO)
              and bool(fixture_declaration_problems({"include_files": ["governance/no_such_input.json"]}, REPO))
              and bool(fixture_declaration_problems({"include_globs": ["governance/no_such_glob_*.yaml"]}, REPO))),
             ("the gate has a NEGATIVE control: >=1 mutation that must NOT red (BUG-492, inverted)",
              any(str(m["expect"]) == "green" for m in doc["mutations"])),
             ("the COMMIT BOUNDARY is READ from its ONE home and every rail there is inside the declared coverage "
              "(D-2679: coverage cannot silently go stale when the boundary grows)",
              not boundary_rails(doc)[1]
              and all(r in {str(s) for s in doc["coverage"]["required_subjects"]} for r in boundary_rails(doc)[0]))]
    for why, good in joins:
        bad += 0 if good else 1
        print("  " + ("ok  " if good else "FAIL") + " selftest/" + why)
    print("rail-mutation controls: " + str(len(cases) + len(joins) - bad) + "/" + str(len(cases) + len(joins))
          + " known-answer control(s) fire")
    return EXIT_CLEAN if not bad else EXIT_FATAL


def main() -> int:
    """CLI: --check (default) | --selftest | --keep (keep the fixture for inspection)."""
    ap = argparse.ArgumentParser(description="the standing rule's teeth: a mutation that must RED its control")
    ap.add_argument("--selftest", action="store_true", help="the gate's own known-answer controls")
    ap.add_argument("--keep", action="store_true", help="keep the fixture and print its path")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    doc = cfg()
    obs, root = measure(doc)
    rc, fatal, owed = classify(obs, doc)
    red = [m for m in doc["mutations"] if str(m["expect"]) == "red"]
    try:
        if rc == EXIT_CLEAN:
            print("ok rail mutations: " + str(len(red)) + " declared rule(s) SEEN to red through their own control ("
                  + ", ".join(str(m["id"]) for m in red) + "), " + str(len(doc["mutations"]) - len(red))
                  + " negative control(s) stayed green, " + str(len({str(m["subject"]) for m in red})) + "/"
                  + str(len(doc["coverage"]["required_subjects"])) + " declared subject(s) covered ("
                  + str(len(boundary_rails(doc)[0])) + " derived from the commit boundary, D-2679), fixture "
                  + str(root))
        else:
            print(("FAIL rail mutations" if rc == EXIT_FATAL else "OWED rail mutations")
                  + ": the standing rule's teeth are not what the declarations say they are:")
            for x in fatal:
                print("  - " + x)
            for x in owed:
                print("  ! " + x)
    finally:
        if a.keep:
            print("fixture kept: " + str(root))
        else:
            shutil.rmtree(root, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
