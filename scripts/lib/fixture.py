#!/usr/bin/env python3
"""fixture.py - THE ONE HOME of the FIXTURE RULES (BUG-577, D-2676(i)).

WHY THIS EXISTS
    scripts/check_boundary_rehearsal.py and scripts/check_rail_mutations.py restated the BUG-537 rule "a fixture
    must resolve OUTSIDE the tree it audits" VERBATIM, and scripts/check_repo_integrity.py built the same kind of
    throwaway repository inline. ONE rule in THREE files is a rule that can be repaired in one and left silently
    stale in the others - the fork D-2646 forbids - and it was MEASURED in the same change-set that adopted the
    standing rule. This module is the single home for both fixture rules; the three callers IMPORT it.

WHAT IT DECIDES
    outside_tree(root, where=...) REFUSES (fail-closed, C16) a fixture root that IS the audited tree or lies INSIDE
    it. Copies, git metadata, 'git clean -qfdx' and rmtree all run at that root, so a mis-derived temp root would
    DELETE the live tree (BUG-537).
    real_repo(parent, name, commit=..., identity=..., message=...) builds a REAL repository with git, because a rail
    reads an ambient git subject derived from where it lives: a fixture that is not a repository would red for a
    reason that is not the mutation's (BUG-527). It returns None when git refuses - a control that cannot run is
    never a pass (BUG-492).

WHAT IT DOES NOT DECLARE (C12/C12d)
    Nothing. The audited tree is DERIVED from this file's own location, never read from config, so no config edit
    can re-point the rule (C12). The builder supplies no identity and no commit message of its own: the CALLER
    passes them, so no fact that belongs to a caller becomes a second home here, and this module names no rail.

    THE CHILD ENVIRONMENT IS THIS MODULE OWN DECISION (BUG-591, D-2697). git() runs with every guard
    variable CLEARED, derived from the pin ONE home (scripts/lib/git_subject.py#cleared_env, D-2646): a
    builder that INHERITS the ambient subject builds into whichever repository the environment names.
    MEASURED 2026-09-27 while instrumenting BUG-568: with GIT_DIR=<decoy>/.git ambient this builder returned
    None for a fixture it had not created, and a caller selftest then read a <fixture>/.git/HEAD git had
    never written.

ORACLE (D-2676 iii): 'python3 scripts/lib/fixture.py --selftest', run by the ladder as its OWN declaring line, so
    the boundary control is SEEN in every health run (D-2676 ii).
TEETH (D-2676 iv): config/rail_mutations.yaml#fixture_outside_tree_rule_is_load_bearing reduces the refusal to a
    no-op and requires the control below to go RED through its own named marker; #the_fixture_builder_does_not_
    inherit_the_ambient_subject hands the child the AMBIENT environment again and requires the DECOY control to
    go RED through its own marker (BUG-591).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import git_subject  # noqa: E402 - the git-subject pin has ONE home (D-2646): the child environment is DERIVED from it, never restated

AUDITED = Path(__file__).resolve().parents[2]
EXIT_CLEAN, EXIT_FATAL, EXIT_CANNOT_RUN = 0, 1, 125   # 125: the command could not be LAUNCHED at all


def outside_tree(root: Path, *, where: str) -> None:
    """FAIL CLOSED (C16) when a fixture root IS the audited tree or lies INSIDE it (BUG-537, ONE home: BUG-577).

    'where' is the CALLER's own name for its fixture, so the refusal reads as that caller's verdict and this
    module restates no rail's vocabulary. Containment, not equality: a root one level below the audited tree is
    just as destructive, because rmtree and 'git clean -qfdx' run at whatever root the caller derived.
    """
    if root == AUDITED or AUDITED in root.parents:
        raise SystemExit("FAIL-CLOSED (C16): " + where + " resolved INSIDE the tree it audits (" + str(root)
                         + "): refusing to copy into, clean, commit in, or delete there")


def git(cwd: Path, *argv: str) -> int:
    """Run git in 'cwd' and return its exit code: a refused command is an OBSERVATION for the caller, never a crash.

    A 'cwd' that is not a directory cannot even be LAUNCHED, and a launch failure is a refusal too (EXIT_CANNOT_RUN,
    never a traceback): the BUG-579 rule - a crash is a verdict - applies to this builder's own helper as much as to
    a rail. FOUND BY the selftest below: its first version died with NotADirectoryError where it should have read a
    refusal, which is why the control exists at all.
    """
    try:
        return subprocess.run(["git", *argv], cwd=str(cwd), capture_output=True, text=True,
                              env=git_subject.cleared_env(git_subject.config())).returncode
    except OSError:
        return EXIT_CANNOT_RUN


def real_repo(parent: Path, name: str, *, commit: bool, identity: tuple[str, str], message: str) -> Path | None:
    """A REAL repository built by git itself under 'parent'; None when git refused (never a pass, BUG-492).

    BORN vs UNBORN is the caller's choice (BUG-576): commit=False leaves HEAD naming a branch with no commit yet,
    which is the state the BUG-400/BUG-564 RECOVERY route produces. The caller supplies 'identity' and 'message',
    so no test's own vocabulary is declared here. The caller ALSO owns the outside_tree() refusal for its parent:
    a builder cannot prove where its caller put it (BUG-537).
    """
    root = parent / name
    if git(parent, "init", "-q", str(root)) != 0:
        return None
    if commit and git(root, "-c", "user.email=" + identity[0], "-c", "user.name=" + identity[1],
                      "commit", "-q", "--allow-empty", "-m", message) != 0:
        return None
    return root


def selftest() -> int:
    """Known-answer controls (D-2676 ii/iii): the refusal FIRES on the audited tree and its descendants, does NOT
    fire on a root that is genuinely outside, and the builder produces a real repository in BOTH HEAD states."""
    ok = fail = 0

    def check(name: str, got: bool, why: str) -> None:
        nonlocal ok, fail
        if got:
            ok += 1
            print("  ok   selftest/" + name + ": " + why)
        else:
            fail += 1
            print("FAIL selftest/" + name + ": " + why)

    def refuses(candidate: Path) -> bool:
        """True when the shared rule REFUSES this root (the refusal is the rule's whole verdict)."""
        try:
            outside_tree(candidate, where="selftest fixture")
        except SystemExit:
            return True
        return False

    check("outside_tree_refuses_the_audited_tree", refuses(AUDITED),
          "the audited tree ITSELF is refused: a fixture root equal to it would clean, commit in and rmtree the "
          "live tree (BUG-537)")
    check("outside_tree_refuses_a_descendant", refuses(AUDITED / "scripts"),
          "... and so is every root INSIDE it - containment, not equality, is the rule (BUG-537)")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        check("outside_tree_accepts_a_root_outside_the_tree", not refuses(root),
              "a root in the system temp dir is ACCEPTED: a rule that refuses everything is not a rule (BUG-492)")
        identity, message = ("fixture-selftest@localhost", "fixture-selftest"), "fixture selftest base"
        unborn = real_repo(root, "unborn_fixture", commit=False, identity=identity, message=message)
        born = real_repo(root, "born_fixture", commit=True, identity=identity, message=message)
        check("real_repo_builds_a_real_repository",
              bool(unborn and born and (unborn / ".git").is_dir() and (born / ".git").is_dir()),
              "git really built the fixtures: a rule about a repository can only be tested by RUNNING it in one "
              "(BUG-574)")
        check("real_repo_commit_flag_decides_HEAD",
              bool(unborn and born and git(unborn, "rev-parse", "HEAD") != 0
                   and git(born, "rev-parse", "HEAD") == 0),
              "commit=False leaves HEAD UNBORN and commit=True makes it resolve, so a caller can drive BOTH states "
              "(BUG-576)")
        # BUG-591: the builder must NOT inherit the ambient subject. The DECOY is a REAL repository, so the
        # only thing that decides where a fixture lands is the environment this builder hands its child git.
        prior_dir = os.environ.get("GIT_DIR")
        prior_tree = os.environ.get("GIT_WORK_TREE")
        decoy = real_repo(root, "decoy_subject", commit=True, identity=identity, message=message)
        try:
            os.environ["GIT_DIR"] = str((decoy if decoy is not None else root / "decoy_subject") / ".git")
            os.environ["GIT_WORK_TREE"] = str(decoy if decoy is not None else root / "decoy_subject")
            armed = os.environ["GIT_DIR"] == str((decoy if decoy is not None else root / "decoy_subject") / ".git")   # anti-vacuity: the value IS in the environment
            decoy_readable = bool(decoy is not None and git(decoy, "rev-parse", "HEAD") == 0)
            hot = real_repo(root, "under_a_decoy_ambient_subject", commit=True, identity=identity, message=message)
            own = bool(hot is not None and (hot / ".git").is_dir())
        finally:
            for key, prior in (("GIT_DIR", prior_dir), ("GIT_WORK_TREE", prior_tree)):
                if prior is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prior
        check("a_fixture_is_built_in_its_own_worktree_under_a_decoy_git_dir",
              bool(armed and decoy_readable and hot is not None and own),
              "with GIT_DIR naming ANOTHER repository the builder must still build and read ITS OWN fixture: an "
              "inherited subject builds into the decoy - the BUG-527 class one module over (BUG-591)")
        afile = root / "not_a_directory"
        afile.write_text("x" + chr(10), encoding="utf-8")
        check("real_repo_reports_a_refused_git_as_None",
              real_repo(afile, "nested", commit=False, identity=identity, message=message) is None,
              "git cannot init under a FILE: the builder returns None, never a traceback and never a pass")
    print(("ok" if not fail else "FAIL") + " fixture: " + str(ok) + "/" + str(ok + fail)
          + " known-answer control(s) fire")
    return EXIT_CLEAN if not fail else EXIT_FATAL


def main(argv: list[str] | None = None) -> int:
    """CLI: --selftest, the NAMED oracle of the fixture rules (D-2676 iii)."""
    ap = argparse.ArgumentParser(description="the ONE home of the fixture rules (BUG-537 / BUG-577)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over the shared fixture rules")
    a = ap.parse_args(argv)
    if not a.selftest:
        ap.print_help()
        return EXIT_CLEAN
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
