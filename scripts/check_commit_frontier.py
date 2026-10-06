#!/usr/bin/env python3
"""check_commit_frontier.py — the ANTI-CIRCLE rail (D-2860).

WHY. The "2 weeks of circles" (2026-09-23 -> 2026-10-07) had ONE root cause: 34 decisions
D-2826..D-2859 were RATIFIED in the WORKTREE but never COMMITTED (HEAD held 955 decisions while the
worktree held 989). Every session re-derived referee variants, re-ran the A/B, wrote more audits — and
never committed, because NOTHING compared "what the worktree has ACCEPTED" against "what HEAD holds
DURABLY." A rail nothing runs is a comment (BUG-492); the missing rail here cost two weeks.

CHECKS (config = config/commit_frontier.yaml, the ONE home — C12/C20):
  1. FRONTIER-DIRTY — any critical_files entry with uncommitted changes -> FATAL. Uncommitted governance
     state is the exact precondition for the circle; the fix is `git commit`, and this rail says so at
     boot (`just health`) instead of letting it ride for weeks.
  2. ACCEPTED-NOT-COMMITTED — a decision whose state ∈ accepted_states (RATIFIED/ACTIVE/RESOLVED) exists
     in the worktree but NOT in HEAD (absent, or present with a non-accepted state) -> FATAL. This is the
     precise "ratified but uncommitted" condition the circle was made of.

It is a BOOT + health gate, NOT a commit hook: at the commit moment a staged file is by definition
uncommitted, so a hook would always refuse the very act that clears the frontier.

Exit: 0 clean | 1 frontier violation (commit first) | 2 config defect (fail-closed, C16).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "commit_frontier.yaml"
DECISIONS = REPO / "config" / "decisions.yaml"


def _git(*args: str) -> str:
    """Run a git porcelain command from the repo root; fail closed (C16) on a git error."""
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"FAIL-CLOSED: git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _load_config() -> dict:
    """Load the frontier declaration; a missing file is a defect, not an empty config (fail closed)."""
    if not CONFIG.exists():
        raise SystemExit("FAIL-CLOSED: config/commit_frontier.yaml does not exist")
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def _dirty_files() -> set[str]:
    """Return the set of repo-relative paths with uncommitted changes, from git itself."""
    dirty: set[str] = set()
    for line in _git("status", "--porcelain").splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]  # rename/copy target is the live path
        if path:
            dirty.add(path)
    return dirty


def _decision_states(worktree: bool) -> dict[str, str]:
    """Map decision id -> state from the worktree file, or from HEAD (empty if absent from HEAD)."""
    if worktree:
        if not DECISIONS.exists():
            raise SystemExit("FAIL-CLOSED: config/decisions.yaml does not exist")
        text = DECISIONS.read_text(encoding="utf-8")
    else:
        proc = subprocess.run(
            ["git", "show", "HEAD:config/decisions.yaml"], cwd=REPO,
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return {}  # file not yet in HEAD: every worktree record is uncommitted
        text = proc.stdout
    data = yaml.safe_load(text) or {}
    return {str(r["id"]): str(r.get("state", "")) for r in data.get("decisions", []) if "id" in r}


def _validate(cfg: dict) -> str | None:
    """Return an error string if the config is malformed, else None."""
    critical = cfg.get("critical_files")
    accepted = cfg.get("accepted_states")
    if not isinstance(critical, list) or not critical:
        return "config/commit_frontier.yaml#critical_files is empty/missing"
    if not isinstance(accepted, list) or not accepted:
        return "config/commit_frontier.yaml#accepted_states is empty/missing"
    for rel in critical:
        if not (REPO / rel).exists():
            return f"critical_files entry does not exist: {rel}"
    return None


def check(cfg: dict) -> int:
    """Evaluate the frontier; return the worst exit code (0 clean, 1 violation, 2 defect)."""
    err = _validate(cfg)
    if err:
        print(f"FAIL-CLOSED: {err}")
        return 2

    violations: list[str] = []
    dirty = _dirty_files()
    for rel in cfg["critical_files"]:
        if rel in dirty:
            violations.append(f"UNCOMMITTED governance file: {rel}")

    wd = _decision_states(worktree=True)
    head = _decision_states(worktree=False)
    for did, state in wd.items():
        if state in cfg["accepted_states"] and head.get(did) not in cfg["accepted_states"]:
            violations.append(f"ACCEPTED decision {did} ({state}) is in the worktree but NOT committed to HEAD")

    if violations:
        print("COMMIT-FIRST (anti-circle, D-2860): the worktree holds uncommitted governance state:")
        for v in violations:
            print(f"  - {v}")
        print("  -> commit the ratified/governance backlog BEFORE minting new decisions (the 2-week-circle root cause).")
        return 1
    print("ok commit-frontier: governance state is committed (no ratified-but-uncommitted work)")
    return 0


def selftest() -> int:
    """Controls for this rail (BUG-492): config loads, critical files exist, and the two data sources
    (worktree + HEAD) are both readable. Deliberately does NOT assert check() == 0: that depends on the
    live tree state, which is the rail's subject, not its control."""
    cfg = _load_config()
    err = _validate(cfg)
    assert err is None, err
    known = set(_decision_states(worktree=True).values())
    unknown = set(cfg["accepted_states"]) - known
    assert not unknown, f"accepted_states has unknown states: {sorted(unknown)}"
    assert isinstance(_decision_states(worktree=False), dict), "HEAD decisions unreadable"
    print("ok commit_frontier --selftest: controls load; critical files present; accepted_states valid")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Anti-circle commit-frontier rail (D-2860)")
    ap.add_argument("--selftest", action="store_true", help="verify the rail's own controls (BUG-492)")
    args = ap.parse_args()
    cfg = _load_config()
    if args.selftest:
        return selftest()
    return check(cfg)


if __name__ == "__main__":
    sys.exit(main())
