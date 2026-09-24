#!/usr/bin/env python3
"""RAIL 4 (BUG-430): work may only touch what the session's plan declared (anti-drift lock).

The failure this blocks: a session asked for A wanders into B, rewrites an artifact nobody asked about, and
the owner discovers it later. Rail: the plan file lists the paths the session may touch; the commit is
refused if it touched anything else. To widen scope you must FIRST commit the plan change - so scope creep
becomes a visible, reviewable act instead of a side effect.
Usage: python3 scripts/check_session_plan.py [--commit HEAD] [--plan governance/session_plan_20260924.yaml]
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    """Compare a commit's file list against the plan's allow-list."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--plan", default="governance/session_plan_20260924.yaml")
    a = ap.parse_args()
    plan_path = REPO / a.plan
    if not plan_path.exists():
        print(f"FAIL session plan: {a.plan} does not exist - a session with no plan file may not commit")
        return 1
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    allow = plan.get("may_touch") or []
    out = subprocess.run(["git", "show", "--name-only", "--format=", a.commit],
                         cwd=REPO, capture_output=True, text=True).stdout.split()
    offenders = [f for f in out if not any(fnmatch.fnmatch(f, pat) for pat in allow) and f != a.plan]
    if offenders:
        print(f"FAIL session plan: commit {a.commit} touched {len(offenders)} path(s) outside the plan:")
        for o in offenders:
            print("  ", o)
        print("   -> widen 'may_touch' in", a.plan, "and commit the plan FIRST, or revert the file")
        return 1
    print(f"ok session plan: commit {a.commit} touched {len(out)} path(s), all declared in {a.plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
