#!/usr/bin/env python3
"""RAIL 4 (BUG-430): work may only touch what the session's plan declared (anti-drift lock).

The failure this blocks: a session asked for A wanders into B, rewrites an artifact nobody asked about, and
the owner discovers it later. Rail: the plan file lists the paths the session may touch; the commit is
refused if it touched anything else. To widen scope you must FIRST commit the plan change - so scope creep
becomes a visible, reviewable act instead of a side effect.
Usage: python3 scripts/check_session_plan.py [--commit HEAD] [--staged] [--plan ...]
Post-hoc checking catches violations AFTER they are in history (BUG-445): install the hook instead -
bash scripts/install_git_hooks.sh - so rail 4 refuses the commit rather than reporting it.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def _paths(a: argparse.Namespace) -> list[str]:
    """File list to audit: the staged set (--staged, pre-commit) or a finished commit's paths."""
    cmd = ["git", "diff", "--cached", "--name-only"] if a.staged else ["git", "show", "--name-only", "--format=", a.commit]
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).stdout.split()


def main() -> int:
    """Compare a commit's file list against the plan's allow-list."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--plan", default="governance/session_plan_20260924.yaml")
    ap.add_argument("--staged", action="store_true",
                    help="audit the STAGED set (for the pre-commit hook) instead of a finished commit")
    a = ap.parse_args()
    plan_path = REPO / a.plan
    if not plan_path.exists():
        print(f"FAIL session plan: {a.plan} does not exist - a session with no plan file may not commit")
        return 1
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    allow = plan.get("may_touch") or []
    forbid = plan.get("will_not_touch") or []
    out = _paths(a)
    # will_not_touch OUTRANKS may_touch: widening the allow-list must never launder a forbidden
    # path into compliance (BUG-445). A forbidden path is a distinct, louder verdict.
    forbidden = [f for f in out if any(fnmatch.fnmatch(f, pat) for pat in forbid)]
    if forbidden:
        print(f"FORBIDDEN session plan: {len(forbidden)} path(s) are declared will_not_touch -> widening")
        print("           'may_touch' is NOT a remedy; the owner gate or a revert is:")
        for f in forbidden:
            print("  ", f)
        print("   -> git checkout HEAD -- <path>   OR get the owner gate, then declare a NEW plan revision")
        return 2
    offenders = [f for f in out if not any(fnmatch.fnmatch(f, pat) for pat in allow) and f != a.plan]
    if offenders:
        print(f"FAIL session plan: commit {a.commit} touched {len(offenders)} path(s) outside the plan:")
        for o in offenders:
            print("  ", o)
        print("   -> widen 'may_touch' in", a.plan, "and commit the plan FIRST, or revert the file")
        return 1
    scope = "staged set" if a.staged else f"commit {a.commit}"
    print(f"ok session plan: {scope} touched {len(out)} path(s), all declared in {a.plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
