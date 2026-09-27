#!/usr/bin/env python3
"""git_subject.py - the git SUBJECT of a rail's audit: DISCOVERED from this repo and PINNED, never inherited.

THE DEFECT THIS CLOSES (BUG-527, MEASURED 2026-09-26)
    A rail that shells `git diff --cached` / `git show` audits whichever index the ENVIRONMENT names.
    GIT_INDEX_FILE / GIT_DIR / GIT_WORK_TREE are inherited by every child process, so the subject of the audit
    was nobody's declared home: a value in the ambient environment decided WHAT was read while the rail
    reported on it as if it were the commit. The rail did not misreport - it faithfully audited the index it
    was TOLD to audit. MEASURED in this repo: `GIT_INDEX_FILE=/tmp/abidx scripts/check_session_plan.py
    --staged` returned rc=0 ("all declared") while the real staged set was never audited; the same day an
    unflagged `git add` moved the commit set 42 -> 43 and NOBODY observed it, because the index has no
    declared writer either. The repo already solved this shape for the git DIR
    (config/repo_integrity.yaml#git.resolve_from) - the lesson was never carried to the INDEX.

WHY 'REFUSE WHEN THE VARIABLE IS SET' WOULD HAVE BEEN A NEW BUG (measured, not argued)
    Probe, 2026-09-26: `git init --separate-git-dir` (this repo's layout) + a probe pre-commit hook. Git HANDS
    the hook GIT_DIR=<abs git dir> and GIT_INDEX_FILE=<abs git dir>/index - the REAL repository. A
    presence-detecting rail would therefore refuse EVERY commit. A bypass is closed by a rule that cannot fire
    on the legitimate case, so the rule is PIN + COMPARE: an ambient value that resolves to the SAME subject is
    tolerated (this is the production hook case), one that resolves to a DIFFERENT subject is REFUSED.

THE RULE (both sets DECLARED in config/repo_integrity.yaml#git_subject - never restated here, D-2646)
    subject_env - variables that can name WHICH repository / worktree / index / object store a read hits.
        DISCOVER each value from THIS FILE's location with every guard variable REMOVED from the child
        (discovery, not inheritance), then COMPARE. Divergence is a refusal (exit 1, C16: fail closed);
        an unreadable or unresolvable value is also a refusal - nothing is guessed.
    clear_env   - repository-local variables that name no comparable path, or that can REDIRECT an object read
        without naming one we could compare (GIT_ALTERNATE_OBJECT_DIRECTORIES, the GIT_CONFIG family,
        replace/graft/shallow overrides). They are REMOVED from every child git environment: where there is
        nothing to compare against, CLEARING is strictly stronger than refusing and cannot misfire.
    UNION CONTROL - `git rev-parse --local-env-vars` is git's OWN authority on which variables are
        repository-local. The control asserts that list is covered by subject_env + clear_env, so a variable a
        future git adds cannot silently escape the pin.

ADOPTION (BUG-566/BUG-567, D-2673): ADOPT git's OWN index, NEVER merely tolerate it
    MEASURED 2026-09-26 (git 2.39.5, this --separate-git-dir layout, probe re-run 2026-09-27): `git commit --
    <path>` (a PARTIAL commit) makes git hand the pre-commit hook GIT_INDEX_FILE=<gitdir>/next-index-<pid>.lock,
    the file EXISTS at hook time, git removes it on exit, and that index IS exactly the commit set. TWO RAILS,
    ONE FACT: rail 5 printed it as "accepted and NAMED" (while having DELETED it from its own child environment,
    so it actually audited <gitdir>/index and its note was false in BOTH directions), and rail 4's pin REFUSED
    it - so NO partial commit could pass, and a rule that cannot fire on the legitimate case is the shape this
    module's own doc forbids. Mere tolerance would be WORSE than the refusal: a rail would then NAME an index it
    did not read. So an ambient minted index is ADOPTED and BECOMES the subject (index_subject). It is adopted
    only when ALL THREE declared conditions hold (adopt_index): the realpath is a file DIRECTLY inside the PINNED
    git dir, its basename matches a declared owner_name_globs entry, and it EXISTS - a missing index reads as
    EMPTY, which would return "all declared" over no bytes at all (the silent wrong-subject audit of BUG-527).
    The globs have ONE home (config) and minted_index_name() MEASURES the name git actually mints, so a future
    git renaming it cannot leave the adoption rule silently dead (D-405: join to reality, not to memory).

ONE HOME (D-2646): this module is the only implementation of the rule; every child `git` call in a rail that
imports it goes through run_git()/run_git_raw()/run_git_paths(), so there is one call site to audit, not three.
Consumers (a CLAIM, D-405/D-2674): scripts/verify_recalibration_pins.py (RAIL 3), scripts/check_session_plan.py
(RAIL 4) and scripts/check_declaration_consumers.py (RAIL 5). DELIBERATELY EXEMPT: scripts/check_repo_integrity.py
(RAIL 0) does NOT import this module and must not - it is the rail that reports BROKEN git metadata, so pinning it
would make the recovery rail fail closed on the condition it exists to name; its own subject is still ambient,
which is FILED as BUG-568 rather than papered over by this list. Controls: --selftest (wired into `just health`).

Usage: python3 scripts/lib/git_subject.py --selftest | --discover-git-dir | --print-git-dir | --minted-index-name
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "repo_integrity.yaml"


class SubjectRefused(SystemExit):
    """The environment names a subject this rail did not audit: refuse rather than report (C16, fail closed)."""


@dataclass(frozen=True)
class Subject:
    """The pinned subject of an audit: WHICH repository, worktree and index every read in this rail hits."""

    git_dir: str
    work_tree: str
    index_file: str

    def pinned(self) -> dict[str, str]:
        """Every ambient guard variable this subject can compare itself against, with its pinned value."""
        return {
            "GIT_DIR": self.git_dir,
            "GIT_WORK_TREE": self.work_tree,
            "GIT_INDEX_FILE": self.index_file,
            "GIT_COMMON_DIR": self.git_dir,
            "GIT_OBJECT_DIRECTORY": os.path.join(self.git_dir, "objects"),
        }

    def env(self, environ: Mapping[str, str], guard: Sequence[str]) -> dict[str, str]:
        """A child environment that CANNOT name a different subject: guards removed, pins written last."""
        env = {k: v for k, v in environ.items() if k not in guard}
        env.update(self.pinned())
        return env


def config() -> dict[str, Any]:
    """Read the declared home of the guard sets and the resolve probe; a missing declaration is a refusal."""
    if not CONFIG.exists():
        raise SubjectRefused("FAIL-CLOSED (BUG-527): " + str(CONFIG) + " is absent - the git-subject rule would "
                             "be prose again (BUG-462 class)")
    doc: Any = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    block = doc.get("git_subject") or {}
    if not block.get("subject_env") or not block.get("clear_env") or "git" not in doc:
        raise SubjectRefused("FAIL-CLOSED (BUG-527): config/repo_integrity.yaml declares no "
                             "git_subject.subject_env/clear_env - the guard set has no home, so nothing may be "
                             "audited through it")
    return doc


def guard_vars(doc: dict[str, Any]) -> list[str]:
    """Every variable the pin OWNS: compared (subject_env) or cleared (clear_env)."""
    block = doc["git_subject"]
    return [str(v) for v in list(block["subject_env"]) + list(block["clear_env"])]


def discover(doc: dict[str, Any], index_file: str | None = None) -> Subject:
    """Resolve this repo's subject with every guard variable REMOVED from the child: discovery, not inheritance."""
    clean = {k: v for k, v in os.environ.items() if k not in guard_vars(doc)}
    probe = str(doc["git"].get("resolve_from") or "").split() or ["rev-parse", "--absolute-git-dir"]
    got: dict[str, str] = {}
    for key, argv in (("GIT_DIR", probe), ("GIT_WORK_TREE", ["rev-parse", "--show-toplevel"])):
        p = subprocess.run(["git", "-C", str(REPO), *argv], capture_output=True, text=True, env=clean)
        val = p.stdout.strip().splitlines()[-1].strip() if p.returncode == 0 and p.stdout.strip() else ""
        if not val:
            raise SubjectRefused("FAIL-CLOSED (BUG-527): `git " + " ".join(argv) + "` does not resolve from "
                                 + str(REPO) + " with the git environment cleared (rc=" + str(p.returncode)
                                 + ") - there is no subject to audit")
        got[key] = os.path.realpath(val)
    idx = os.path.realpath(index_file) if index_file else os.path.join(got["GIT_DIR"], "index")
    return Subject(git_dir=got["GIT_DIR"], work_tree=got["GIT_WORK_TREE"], index_file=idx)


def _names_same_subject(raw: str, want: str) -> bool:
    """True when the ambient value resolves to the pinned path (relative values resolved as git would read them)."""
    candidates = [raw] if os.path.isabs(raw) else [str(Path(os.getcwd()) / raw), str(REPO / raw)]
    return any(os.path.realpath(c) == os.path.realpath(want) for c in candidates)


def index_tolerance(doc: dict[str, Any]) -> list[str]:
    """The DECLARED names git mints for a partial commit's temporary index (ONE home, D-2646)."""
    block = doc.get("git_subject") or {}
    tol = block.get("index_tolerance") or {}
    globs = [str(g) for g in (tol.get("owner_name_globs") or []) if str(g).strip()]
    if not globs:
        raise SubjectRefused("FAIL-CLOSED (BUG-566): config/repo_integrity.yaml declares no "
                             "git_subject.index_tolerance.owner_name_globs - an adoption rule with no declared "
                             "home would be prose again (BUG-462 class)")
    return globs


def adopt_index(doc: dict[str, Any], subj: Subject, raw: str) -> tuple[str, str]:
    """(adopted realpath, note) for git's OWN temporary index, or ("", refusal) - ADOPT, never merely tolerate.

    Three conditions, ALL required, because a rail that NAMES an index it did not read is worse than one that
    refuses: (1) the realpath is a file DIRECTLY inside the PINNED git dir (so a `../` escape or a sibling
    repository's temp index is refused), (2) its basename matches a declared owner_name_globs entry (so a
    foreign index parked in the git dir is refused), (3) it EXISTS - git reads a missing index as EMPTY, which
    would report "all declared" over no bytes at all (the silent wrong-subject audit BUG-527 closed).
    """
    if not raw:
        return "", ""
    cand = os.path.realpath(raw)
    if os.path.dirname(cand) != os.path.realpath(subj.git_dir):
        return "", ("GIT_INDEX_FILE=" + raw + " is not a file inside the pinned git dir " + subj.git_dir
                    + " (resolved: " + cand + ") - another repository's index is not this one's subject")
    globs = index_tolerance(doc)
    if not any(fnmatch.fnmatch(os.path.basename(cand), g) for g in globs):
        return "", ("GIT_INDEX_FILE=" + raw + " matches none of the declared "
                    "git_subject.index_tolerance.owner_name_globs (" + ", ".join(globs) + ") - only an index git "
                    "ITSELF mints in the pinned git dir is adopted")
    if not os.path.isfile(cand):
        return "", ("GIT_INDEX_FILE=" + raw + " does not exist - git reads a missing index as EMPTY, so the audit "
                    "would report over no bytes at all (the silent audit of BUG-527)")
    return cand, ("ADOPTED git's OWN temporary index for this commit (" + cand + ": basename matches the declared "
                  "index_tolerance.owner_name_globs and it is inside the pinned git dir) - at the WRITE moment "
                  "that IS the commit set, so it is READ as the subject, not merely accepted (BUG-566/D-2673)")


def index_subject(index_file: str | None = None,
                  environ: Mapping[str, str] | None = None) -> tuple[Subject, str]:
    """THE entry point for the index as well as the repository: the pinned subject AND the index's provenance.

    An explicit index_file (a rail's own --index-file flag) is a DECLARED home and always wins. Without it, an
    ambient GIT_INDEX_FILE that is git's own minted temp index for the pinned git dir is ADOPTED and BECOMES the
    subject, so the rail reads the COMMIT SET instead of the index it happens to find (BUG-566); anything else
    ambient is REFUSED here rather than silently audited (C16, fail closed, nothing guessed).
    """
    doc = config()
    env = os.environ if environ is None else environ
    note, chosen = "", index_file
    if not chosen:
        raw = str(env.get("GIT_INDEX_FILE") or "")
        if raw:
            adopt, note = adopt_index(doc, discover(doc), raw)
            if not adopt:
                raise SubjectRefused("REFUSED git-index (BUG-566, fail closed, C16):\n  " + note
                                     + "\n  Pass the explicit --index-file flag this rail documents for a "
                                       "diagnostic read, or unset GIT_INDEX_FILE: there is no silent override.")
            chosen = adopt
    subj = discover(doc, chosen)
    bad = faults(doc, subj, chosen, env)
    if bad:
        raise SubjectRefused("REFUSED git-subject (BUG-527, fail closed, C16):\n  " + "\n  ".join(bad))
    return subj, note


def faults(doc: dict[str, Any], subj: Subject, index_file: str | None = None,
           environ: Mapping[str, str] | None = None) -> list[str]:
    """Every ambient guard value naming a DIFFERENT subject ([] = the legitimate case, e.g. the live hook)."""
    env = os.environ if environ is None else environ
    pinned = subj.pinned()
    if index_file:
        pinned["GIT_INDEX_FILE"] = os.path.realpath(index_file)
    out: list[str] = []
    for var, want in pinned.items():
        raw = env.get(var)
        if raw is None or raw == "" or _names_same_subject(str(raw), want):
            continue
        out.append(var + "=" + str(raw) + " names a DIFFERENT subject than the one audited (" + var + "=" + want
                   + ") - the environment would decide what this rail reads, and a rail that reports on a "
                     "subject nobody declared is not a rail (BUG-527). Unset it, or pass the explicit flag the "
                     "rail documents: there is no silent override.")
    return out


def subject(index_file: str | None = None, environ: Mapping[str, str] | None = None) -> Subject:
    """THE pinned subject, or a refusal that prints both paths. Never a guess (C16)."""
    return index_subject(index_file, environ)[0]


def minted_index_name() -> str:
    """MEASURE the basename git mints for a PARTIAL commit's temp index (D-405: join the globs to REALITY).

    A probe repository in THIS layout (--separate-git-dir) with a pre-commit hook that records $GIT_INDEX_FILE:
    one normal commit, then one partial commit. The control asserts the measured name matches a declared glob,
    so a future git renaming it cannot leave the adoption rule silently dead (BUG-492: a rule never SEEN to fire
    is not a rule). The hook receives LOG and the log path is baked in - the parent environment is not mutated.
    """
    doc = config()
    with tempfile.TemporaryDirectory(prefix="mint_probe_") as td:
        work, gdir, log = os.path.join(td, "w"), os.path.join(td, "g.git"), os.path.join(td, "env.log")
        os.makedirs(work)

        def g(*argv: str) -> subprocess.CompletedProcess:
            clean = {k: v for k, v in os.environ.items() if k not in guard_vars(doc)}
            return subprocess.run(["git", *argv], cwd=work, capture_output=True, text=True, env=clean)

        g("init", "-q", "--separate-git-dir", gdir)
        hook = os.path.join(gdir, "hooks", "pre-commit")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\necho "$GIT_INDEX_FILE" >> "' + log + '"\n')
        os.chmod(hook, 0o755)
        with open(os.path.join(work, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("a\n")
        g("add", "a.txt")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "one")
        with open(os.path.join(work, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("b\n")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "two", "--", "a.txt")
        with open(log, encoding="utf-8") as fh:
            seen = [os.path.basename(ln.strip()) for ln in fh.read().splitlines() if ln.strip()]
        return next((m for m in reversed(seen) if m != "index"), "")


def run_git(subj: Subject, argv: Sequence[str], doc: dict[str, Any] | None = None) -> tuple[int, str]:
    """The ONLY child-git call site of a pinned rail: the pinned subject decides what is read (D-2646)."""
    env = subj.env(os.environ, guard_vars(doc or config()))
    p = subprocess.run(["git", *argv], cwd=REPO, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def pinned_env(index_file: str | None = None, doc: dict[str, Any] | None = None) -> dict[str, str]:
    """The child environment a rail hands git: guards removed, pins written last (ONE call site per rail)."""
    d = doc or config()
    return discover(d, index_file).env(os.environ, guard_vars(d))


def run_git_raw(argv: Sequence[str], index_file: str | None = None) -> tuple[int, bytes]:
    """Bytes-returning sibling of run_git, for reads where a text decode would corrupt the subject."""
    p = subprocess.run(["git", *argv], cwd=REPO, capture_output=True, env=pinned_env(index_file))
    return p.returncode, p.stdout


def run_git_paths(subj: Subject, argv: Sequence[str],
                  doc: dict[str, Any] | None = None) -> tuple[int, list[str]]:
    """A git NAME-LIST read (BUG-565): the `-z` flag and the NUL parse live HERE, so no caller splits on blanks.

    MEASURED 2026-09-26 (found because this defect REFUSED the owner's own PROMOTE): the staged set was read as
    TEXT and split on WHITESPACE. ELEVEN tracked paths in this repo contain a space - including the write-locked
    owner instrument `governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` - so rail 4 audited it as THREE
    phantom paths (`governance/Copy`, `of`, `ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`). Both directions went
    blind at once: the owner's one-off crossing permit could never GRANT the path it names, and the BUG-528
    family check could never FORBID it. The rule is a fact about the NAME LIST, so it has ONE home: a caller
    cannot forget the flag because it is not the caller's to pass.
    """
    env = subj.env(os.environ, guard_vars(doc or config()))
    p = subprocess.run(["git", *argv, "-z"], cwd=REPO, capture_output=True, env=env)
    return p.returncode, [b.decode("utf-8", "surrogateescape") for b in p.stdout.split(b"\0") if b]


def selftest() -> int:
    """Known-answer controls (BUG-492): each can FAIL, and one only certifies that the pin changed nothing."""
    doc = config()
    subj = discover(doc)
    union_ok = True
    rc, out = run_git(subj, ["rev-parse", "--local-env-vars"], doc)
    if rc != 0:
        union_ok = False
        missing = ["<git rev-parse --local-env-vars did not resolve>"]
    else:
        missing = sorted(set(out.split()) - set(guard_vars(doc)))
        union_ok = not missing
    decoy_env = dict(os.environ, GIT_DIR="/tmp/git_subject_decoy")
    p = subprocess.run([sys.executable, str(Path(__file__)), "--discover-git-dir"], capture_output=True, text=True,
                       env=decoy_env, cwd=str(REPO))
    inherited_free = p.stdout.strip() == subj.git_dir
    try:
        subject(environ=decoy_env)
        refused_decoy = False
    except SubjectRefused:
        refused_decoy = True
    live_hook = faults(doc, subj, None, dict(os.environ, GIT_DIR=subj.git_dir,
                                             GIT_INDEX_FILE=subj.index_file, GIT_WORK_TREE=subj.work_tree)) == []
    rc_a, ambient = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=REPO, capture_output=True,
                                   text=True).returncode, ""
    ambient = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=REPO, capture_output=True,
                             text=True).stdout.split()
    rc_b, pinned = run_git(subj, ["diff", "--cached", "--name-only"], doc)
    same_read = rc_a == 0 and rc_b == 0 and sorted(ambient) == sorted(pinned.split())
    # BUG-566/D-2673 controls: the adoption rule, BOTH directions, plus the D-405 join to what git MEASURES.
    minted = minted_index_name()
    globs = index_tolerance(doc)
    minted_declared = bool(minted) and any(fnmatch.fnmatch(minted, g) for g in globs)
    own_not_minted = not any(fnmatch.fnmatch("index", g) for g in globs)
    with tempfile.TemporaryDirectory(prefix="adopt_probe_") as td:
        gdir, other = os.path.join(td, "g.git"), os.path.join(td, "other")
        os.makedirs(gdir)
        os.makedirs(other)
        fake = Subject(git_dir=gdir, work_tree=td, index_file=os.path.join(gdir, "index"))
        name = minted or "next-index-0.lock"
        own = os.path.join(gdir, "index")
        minted_in_gitdir = os.path.join(gdir, name)
        foreign = os.path.join(other, name)
        escape = os.path.join(gdir, "..", name)
        for f in (own, minted_in_gitdir, foreign, escape):
            open(f, "w", encoding="utf-8").close()
        adopted, adopt_note = adopt_index(doc, fake, minted_in_gitdir)
        controls = [
            ("git's OWN local-env list is covered by the declared guard set (no variable escapes the pin)", union_ok),
            ("discovery IGNORES an inherited GIT_DIR (a decoy ambient repo does not become the subject)", inherited_free),
            ("an ambient GIT_DIR naming a DECOY repository is REFUSED (the executed bypass, BUG-527)", refused_decoy),
            ("a synthetic GIT_INDEX_FILE is REFUSED (the A/B bypass that returned rc=0 before the fix)",
             faults(doc, subj, None, dict(os.environ, GIT_INDEX_FILE="/tmp/not_the_index")) != []),
            ("a relative index value that names no path is REFUSED (fail closed, nothing guessed)",
             faults(doc, subj, None, dict(os.environ, GIT_INDEX_FILE=".git/index")) != []),
            ("OVERREACH control: the LIVE hook's own GIT_DIR/GIT_INDEX_FILE (same subject) is TOLERATED",
             live_hook),
            ("DIFFERENTIAL control: the pinned read equals the unpinned read in this environment (the fix changes "
             "no legitimate result)", same_read),
            ("D-405 JOIN TO REALITY: the declared owner_name_globs MATCH the index name git ACTUALLY mints for a "
             "partial commit in this layout [measured: " + (minted or "<nothing recorded>") + "]",
             minted_declared),
            ("OVERREACH control: the repo's OWN index name is NOT adopted as a minted temp index (adoption cannot "
             "swallow the real index)", own_not_minted),
            ("BUG-566: git's OWN minted temp index inside the PINNED git dir is ADOPTED, READ and NAMED (the "
             "legitimate partial commit must not be refused)",
             adopted == os.path.realpath(minted_in_gitdir) and "ADOPTED" in adopt_note),
            ("BUG-566: a minted NAME inside a FOREIGN git dir is REFUSED (a name is not a subject)",
             adopt_index(doc, fake, foreign)[0] == ""),
            ("BUG-566: a `..` escape out of the pinned git dir is REFUSED",
             adopt_index(doc, fake, escape)[0] == ""),
            ("BUG-566: a minted name in the pinned git dir that DOES NOT EXIST is REFUSED (a missing index reads "
             "as EMPTY - the silent wrong-subject audit of BUG-527)",
             adopt_index(doc, fake, os.path.join(gdir, "next-index-99999.lock"))[0] == ""),
        ]
    bad = 0
    for name_, ok in controls:
        print(("  ok   " if ok else "  FAIL ") + name_)
        bad += 1 - int(ok)
    if missing:
        print("        uncovered variable(s): " + ", ".join(missing))
    print("git-subject controls: " + str(len(controls) - bad) + "/" + str(len(controls))
          + " known-answer control(s) fire | subject " + subj.git_dir)
    return 1 if bad else 0


def main(argv: Sequence[str] | None = None) -> int:
    """--selftest runs the controls; the discovery modes exist so the controls can prove non-inheritance."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return selftest()
    if "--discover-git-dir" in args:
        print(discover(config()).git_dir)
        return 0
    if "--print-git-dir" in args:
        print(subject().git_dir)
        return 0
    if "--minted-index-name" in args:
        print(minted_index_name())
        return 0
    print(__doc__.splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
