#!/usr/bin/env python3
"""check_commit_scope_guard.py - THE RED LOOP BUG-773 OWED (D-2933 rule V).

THE CONTRADICTION THIS WATCHES. config/dedup_identity.yaml declares
`edition_supersession.execution.never_at_commit: true` - "a commit may never rewrite an existing row's body". The
commit stage holds an escape route that does exactly that (`INSERT OR REPLACE INTO fbs`), so the rule is true only
while the LIVE scope keeps existing rows off that route.

MEASURED 2026-10-17, two-sided, on a temp database built from the live `fbs` DDL (78 columns):
  ROUTE 1  INSERT OR REPLACE for an fb_id the store already holds  -> body became MOVED-BODY  (DESTROYED)
  ROUTE 2  the S5-scoped UPDATE (verification_scoped)              -> body stayed ORIGINAL-BODY (SURVIVES)
The live `stage6.commit_scope` is `verification_scoped`, so the contradiction is NOT LIVE - and `full_upsert` remains
an unguarded escape route one config edit away. That edit is the whole risk: the knob and the rule are two files, and
NOTHING compared them. A rule in one file and a switch in another is a promise with no reader.

WHAT THIS RAIL ADDS BEYOND THE KNOB. A faithful knob says nothing about the ROUTE. Measured the same day, the
protection is a dispatch line inside stage6_commit.py; a future edit could leave the config perfect and delete the
branch, which is class (i) of the rail registry - a control nothing runs (BUG-492). So the rail reads the SOURCE
TOO, and both halves must agree before it says ok:
  1. THE KNOB: never_at_commit (the rule) vs stage6.commit_scope (the switch).
  2. THE ROUTE: the dispatch that sends an already-present fb_id to the S5-owned UPDATE, and the UPDATE itself.
  3. THE ESCAPE: `INSERT OR REPLACE INTO fbs` present AND the scope off the guarded path = the destroying combination.

TRI-STATE. 0 the declared rule holds on the route that will run | 1 FATAL (the live configuration destroys a body the
rule protects, or a half of the route is missing). There is no owner-owed state here: this is not a matter of taste.

Usage:
  python3 scripts/check_commit_scope_guard.py
  python3 scripts/check_commit_scope_guard.py --selftest
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
PIPELINE_CONFIG = REPO / "config" / "pipeline_config.yaml"
DEDUP_IDENTITY = REPO / "config" / "dedup_identity.yaml"
STAGE6 = REPO / "pipeline" / "stage6_commit.py"

GUARDED_SCOPE = "verification_scoped"
KNOWN_SCOPES = (GUARDED_SCOPE, "full_upsert")
#: The two source facts that make the guarded scope real. A path shape is not proof; a branch that calls the
#: S5-scoped writer, and a writer whose statement is an UPDATE, are.
DISPATCH_MARK = 'if S6_COMMIT_SCOPE == "verification_scoped" and fbs_rowid('
WRITER_DEF = "def update_s5_provenance("
WRITER_SQL = "UPDATE fbs SET"
DESTROYER_MARK = "INSERT OR REPLACE INTO fbs"


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Parse a YAML mapping, fail closed.

    Args:
        path: the file to parse.

    Returns:
        The mapping.

    Raises:
        SystemExit: when the file is absent, unreadable or not a mapping (C16: absent is FATAL, not empty).
    """
    import yaml

    if not path.exists():
        raise SystemExit(f"FATAL: {path} does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FATAL: {path} is not a mapping")
    return data


def verdict(rule: Any, scope: Any, owned_columns: Any, source: str) -> tuple[int, list[str]]:
    """Decide the rail's state from four readings, so the decision is testable without the repository.

    Args:
        rule: `never_at_commit` as declared.
        scope: `stage6.commit_scope` as configured.
        owned_columns: `stage6.s5_owned_columns` as configured.
        source: the text of pipeline/stage6_commit.py.

    Returns:
        (rc, lines): 0 when the declared rule holds on the route that will run, 1 otherwise.
    """
    lines: list[str] = []
    if rule is None:
        return 1, ["never_at_commit is ABSENT from config/dedup_identity.yaml - an absent rule is not a false rule (C16)"]
    if scope is None:
        return 1, ["stage6.commit_scope is ABSENT - the commit route is undeclared"]
    if scope not in KNOWN_SCOPES:
        return 1, [f"stage6.commit_scope {scope!r} is not one of {KNOWN_SCOPES} - stage6 would refuse to commit at all"]

    destroying_route = DESTROYER_MARK in source
    dispatch = DISPATCH_MARK in source
    writer = WRITER_DEF in source and WRITER_SQL in source

    if scope == GUARDED_SCOPE:
        if not owned_columns:
            lines.append("commit_scope is verification_scoped but stage6.s5_owned_columns is empty - "
                         "stage6 refuses that pairing, so the run would stop rather than overwrite")
            return 1, lines
        if not dispatch:
            lines.append("THE CONFIG IS RIGHT AND THE ROUTE IS GONE: no dispatch sends an already-present fb_id to "
                         "update_s5_provenance, so verification_scoped protects nothing (BUG-492)")
            return 1, lines
        if not writer:
            lines.append("update_s5_provenance is missing, or its statement is not an UPDATE fbs - the guarded scope "
                         "has no writer to reach")
            return 1, lines
        tail = (" (the destroying INSERT OR REPLACE is still present in insert_fb, reachable only by explicit "
                "full_upsert)") if destroying_route else " (insert_fb no longer rewrites a body at all)"
        lines.append(f"the declared rule holds: never_at_commit={rule}, scope={scope}, dispatch present, writer scoped"
                     + tail)
        return 0, lines

    # scope == full_upsert from here: the guarded branch will not be taken for an existing row.
    if rule is True and destroying_route:
        lines.append("THE DECLARED RULE IS CONTRADICTED BY THE LIVE SCOPE: never_at_commit=true while the route that "
                     "will run rewrites an existing row's body (INSERT OR REPLACE). Measured two-sided 2026-10-17: "
                     "route 1 destroyed the body, route 2 preserved it. Refusing.")
        return 1, lines
    if destroying_route:
        lines.append("scope=full_upsert with never_at_commit not declared true - the rewrite is permitted by this "
                     "configuration but not by the rule; nothing to refuse")
        return 0, lines
    lines.append("scope=full_upsert but insert_fb no longer contains INSERT OR REPLACE INTO fbs - the escape route "
                 "itself was repaired, so the knob no longer decides whether a body survives")
    return 0, lines


def read_state() -> tuple[int, list[str]]:
    """Read the four live readings and hand them to `verdict`.

    Returns:
        (rc, lines) as `verdict` returns them.
    """
    pipeline = _yaml(PIPELINE_CONFIG)
    dedup = _yaml(DEDUP_IDENTITY)
    stage6 = (pipeline.get("stage6") or {}) if isinstance(pipeline.get("stage6"), dict) else {}
    execution = ((dedup.get("edition_supersession") or {}).get("execution") or {})
    if not isinstance(execution, dict):
        execution = {}
    source = STAGE6.read_text(encoding="utf-8") if STAGE6.exists() else ""
    if not source:
        return 1, [f"FATAL: {STAGE6} is missing or empty - the route cannot be read"]
    return verdict(execution.get("never_at_commit"), stage6.get("commit_scope"),
                   stage6.get("s5_owned_columns"), source)


def _selftest() -> int:
    """Known-answer controls, each one a state this repository could actually reach.

    Returns:
        0 when every control holds, 1 otherwise.
    """
    guarded_source = f"{DISPATCH_MARK}...\n{WRITER_DEF}\n...\n{WRITER_SQL}\n...\n{DESTROYER_MARK}"
    repaired_source = f"{DISPATCH_MARK}...\n{WRITER_DEF}\n...\n{WRITER_SQL}"
    controls: list[tuple[str, bool]] = [
        ("rule true + verification_scoped + a live dispatch is ok",
         verdict(True, GUARDED_SCOPE, ["status"], guarded_source)[0] == 0),
        ("rule true + full_upsert + the destroying route is RED (the measured ROUTE 1)",
         verdict(True, "full_upsert", ["status"], guarded_source)[0] == 1),
        ("the config is right but the dispatch was deleted -> RED (BUG-492)",
         verdict(True, GUARDED_SCOPE, ["status"], f"{WRITER_DEF}\n{WRITER_SQL}\n{DESTROYER_MARK}")[0] == 1),
        ("the writer is missing -> RED", verdict(True, GUARDED_SCOPE, ["status"], DESTROYER_MARK)[0] == 1),
        ("verification_scoped with no S5-owned columns -> RED",
         verdict(True, GUARDED_SCOPE, [], guarded_source)[0] == 1),
        ("an unknown scope -> RED", verdict(True, "upsert_everything", ["status"], guarded_source)[0] == 1),
        ("an ABSENT rule is FATAL, never read as false", verdict(None, GUARDED_SCOPE, ["s"], guarded_source)[0] == 1),
        ("rule not declared: the same rewrite is permitted, not refused",
         verdict(False, "full_upsert", ["status"], guarded_source)[0] == 0),
        ("the escape route repaired -> ok even at full_upsert (the knob stops mattering)",
         verdict(True, "full_upsert", ["status"], repaired_source)[0] == 0),
    ]
    for label, ok in controls:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    passed = sum(1 for _, ok in controls if ok)
    print(f"selftest: {passed}/{len(controls)}")
    return 0 if passed == len(controls) else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: CLI arguments (default: sys.argv[1:]).

    Returns:
        0 when the declared rule holds on the live route, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description="the BUG-773 red loop: D-2933 rule V vs the live commit route")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    rc, lines = read_state()
    for line in lines:
        print(f"{'ok  ' if rc == 0 else 'FAIL'} commit-scope: {line}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
