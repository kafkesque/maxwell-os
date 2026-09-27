#!/usr/bin/env python3
"""check_boundary_rehearsal.py - the BOUNDARY REHEARSAL (D-2675): the write boundary at a REAL commit.

WHY THIS EXISTS (the CLASS, not the instance)
    BUG-527, BUG-566, BUG-568, BUG-569 and BUG-574 are ONE defect class: a rail's rule about the AMBIENT git
    environment git hands its own pre-commit hook (GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE) was tested ONLY
    against SYNTHETIC fixtures - every control built its OWN `git init` - so the value git ACTUALLY hands the
    hook was in NO test. MEASURED 2026-09-27: 13/13 git-subject controls GREEN while 100 percent of commits in
    this repository were REFUSED (BUG-574: the adoption rule refused the repository's OWN index). A control
    never seen to FAIL is not a control; a boundary never seen to ACCEPT a legitimate commit is not a boundary.
    This rail builds a REAL repository in the SYSTEM temp dir, installs the hooks with the repository's OWN
    installer, performs a REAL normal commit and a REAL partial commit THROUGH the hook, PLANTS real violations
    and asserts they are REFUSED, and runs every write-boundary rail's own --selftest.

WHAT IT DECIDES (0 clean | 1 FATAL fail-closed C16 | 2 owner-owed: a declared DEBT is PAID)
    1 FATAL a declared fact about the boundary is not what the boundary DOES: a legitimate commit REFUSED, a
            planted violation ACCEPTED (a boundary with no teeth), a note whose PROVENANCE is not the declared
            one (or is absent), a rail --selftest that fails, or an observation MISSING (never a silent pass).
    1 FATAL the fresh-repository first commit refused for a reason the declaration does NOT name - a NEW
            instance of the class must not hide behind the declared one.
    2 OWED  the fresh-repository first commit now PASSES: the declared debt (BUG-576) is PAID and the
            declaration must be WITHDRAWN by a decision (a declaration that outlives its subject is BUG-542).
EVERY fact is DECLARED in config/boundary_rehearsal.yaml (C12: no path, count or verdict is written here) and
the note PROVENANCE is read from its ONE home (scripts/lib/git_subject.py#note_kind), never restated. The
fixture holds TRACKED HEAD bytes only (`git archive HEAD`) in the system temp dir, so it carries no dirt of the
live tree and this rail can never write inside the tree it audits (BUG-537). --selftest proves every decision.
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib import git_subject  # noqa: E402

CFG = REPO / "config" / "boundary_rehearsal.yaml"
NOTE_LINE = re.compile(r"^note [^\n]*$", re.MULTILINE)
EXIT_CLEAN, EXIT_FATAL, EXIT_OWED = 0, 1, 2
_ENV: dict[str, str] | None = None


@dataclass(frozen=True)
class Obs:
    """One measured fact: an exit code plus the text that accompanied it."""

    rc: int
    text: str = ""

    def tail(self, n: int = 2) -> str:
        """The first n non-empty lines, so a reason prints something a human can act on."""
        return " / ".join([ln.strip() for ln in self.text.splitlines() if ln.strip()][:n])[:300]


def env() -> dict[str, str]:
    """The environment every fixture command runs in: every git guard variable REMOVED (BUG-527)."""
    global _ENV
    if _ENV is None:
        guard = set(git_subject.guard_vars(git_subject.config()))
        _ENV = {k: v for k, v in os.environ.items() if k not in guard}
    return _ENV


def cfg() -> dict[str, Any]:
    """The declared rehearsal; an absent or incomplete declaration FAILS CLOSED (C16)."""
    if not CFG.is_file():
        raise SystemExit("FAIL-CLOSED (C16): " + str(CFG) + " is absent - a rehearsal with no declarations "
                         "rehearses nothing, and an undeclared expectation is an assertion")
    doc = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    missing = [k for k in ("authority", "temp", "rails", "module", "scenarios", "declared_debt") if k not in doc]
    if missing:
        raise SystemExit("FAIL-CLOSED (C16): " + str(CFG) + " declares no " + ", ".join(missing) + " - the "
                         "boundary would then be rehearsed against a default, which has no home (C12)")
    for rail in doc["rails"]:
        for k in ("role", "invocation", "staged_rc", "ambient_note", "partial_note", "selftest"):
            if k not in rail:
                raise SystemExit("FAIL-CLOSED (C16): rail " + repr(rail.get("role")) + " declares no " + repr(k)
                                 + " - a provenance that is not declared is an assertion with no home (C12)")
    for key in ("normal_commit", "partial_commit"):
        if "note_field" not in (doc["scenarios"].get(key) or {}):
            raise SystemExit("FAIL-CLOSED (C16): scenario " + repr(key) + " declares no note_field - the "
                             "provenance count would then be a constant in code (C12)")
    return doc


def sh(argv: list[str], cwd: Path, timeout: int, stdin: bytes | None = None,
       extra: dict[str, str] | None = None) -> Obs:
    """One command in the fixture: CLEANED environment, HARD timeout (a rail that hangs lies by omission)."""
    e = dict(env())
    e.update(extra or {})
    try:
        p = subprocess.run(argv, cwd=str(cwd), capture_output=True, env=e, timeout=timeout,
                           input=stdin if stdin is not None else b"")
    except subprocess.TimeoutExpired:
        return Obs(124, "TIMEOUT after " + str(timeout) + "s: " + " ".join(argv))
    except OSError as exc:
        return Obs(127, str(exc))
    return Obs(p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace"))


def rail_cmd(text: str) -> list[str]:
    """A declared invocation as argv, run with THIS interpreter (a rail is a python script)."""
    return [sys.executable, *text.split()]


def note_kinds(text: str) -> list[str]:
    """The PROVENANCE of every note line printed, decided by the ONE home (D-2646)."""
    return [git_subject.note_kind(ln) for ln in NOTE_LINE.findall(text)]


def rail_by_role(doc: dict[str, Any], role: str) -> dict[str, Any]:
    """The rail a scenario names by ROLE: a planted violation must be refused by the DECLARED rail, never by
    whichever rule happened to fire first."""
    for rail in doc["rails"]:
        if str(rail["role"]) == role:
            return rail
    raise SystemExit("FAIL-CLOSED (C16): config/boundary_rehearsal.yaml names rail role " + repr(role)
                     + " which it does not declare")


def mutate(path: Path, op: str, text: str) -> None:
    """The declared fixture mutation: append, or create. Never a rewrite - the fixture is a REPLICA of HEAD."""
    if op == "append":
        with path.open("a", encoding="utf-8") as fh:
            fh.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def outside_tree(root: Path) -> None:
    """The fixture must not live inside the tree it audits (BUG-537): `git clean -qfdx` and rmtree run
    here, so a mis-derived temp root would DELETE the live tree. Derived from REPO, never declared, so it
    cannot be re-pointed by a config edit (C12)."""
    if root == REPO or REPO in root.parents:
        raise SystemExit("FAIL-CLOSED (C16): the rehearsal fixture resolved INSIDE the tree it audits ("
                         + str(root) + "): refusing to clean, commit or delete there")


def build(doc: dict[str, Any], obs: dict[str, Obs], t: int) -> tuple[Path, Path, Path]:
    """A REAL repository in the system temp dir, in the LIVE layout, holding TRACKED HEAD bytes only."""
    tp = doc["temp"]
    root = Path(tempfile.mkdtemp(prefix=str(tp["prefix"]))).resolve()
    outside_tree(root)   # FAIL CLOSED before anything here is deleted, cleaned or committed
    work, gitdir = root / str(tp["work_name"]), root / str(tp["git_dir_name"])
    work.mkdir(parents=True)
    gitdir.mkdir(parents=True)
    obs["setup.init"] = sh(["git", "init", "-q", "--separate-git-dir", str(gitdir)], work, t)
    sh(["git", "config", "user.name", str(tp["identity"]["name"])], work, t)
    sh(["git", "config", "user.email", str(tp["identity"]["email"])], work, t)
    src = subprocess.run(["git", "-C", str(REPO), *[str(x) for x in tp["materialize"]]], capture_output=True,
                         env=env())
    if src.returncode != 0:
        obs["setup.materialize"] = Obs(src.returncode, src.stderr.decode("utf-8", "replace"))
    else:
        obs["setup.materialize"] = sh(["tar", "-x", "-C", str(work)], work, t, stdin=src.stdout)
    sh(["bash", "scripts/install_git_hooks.sh"], work, t)   # rc NOT asserted: it ends with its own self-check
    obs["setup.hooks_rederive"] = sh(["bash", "scripts/install_git_hooks.sh", "--check"], work, t)
    return root, work, gitdir


def clean_reset(work: Path, t: int) -> None:
    """Every scenario starts from the SAME state: HEAD, no staged path, no untracked residue."""
    sh(["git", "reset", "-q", "--hard", "HEAD"], work, t)
    sh(["git", "clean", "-qfdx"], work, t)


def rehearse(doc: dict[str, Any]) -> tuple[Path, dict[str, Obs]]:
    """Every declared fact, MEASURED at the boundary. A boundary fault is RECORDED, never raised."""
    t, obs = int(doc["temp"]["timeout_seconds"]), {}
    root, work, gitdir = build(doc, obs, t)
    if any(obs[k].rc != 0 for k in ("setup.init", "setup.materialize", "setup.hooks_rederive")):
        return root, obs      # a fixture that did not build cannot rehearse: reported, never papered over
    sc = doc["scenarios"]
    # (1) THE FRESH REPOSITORY: its FIRST commit goes through the hook - the declared debt (BUG-576), and the
    #     reason the bootstrap below exists at all.
    sh(["git", "add", "-A"], work, t)
    obs["fresh.first_commit"] = sh(["git", "commit", "-qm", str(doc["temp"]["bootstrap"]["message"])], work, t)
    obs["bootstrap.commit"] = sh(["git", "commit", "-qm", str(doc["temp"]["bootstrap"]["message"]),
                                  *[str(x) for x in doc["temp"]["bootstrap"]["flags"]]], work, t)
    # (2) A LEGITIMATE COMMIT: the case BUG-574 refused 100 percent of - a real staged change, full index.
    legit = str(sc["partial_commit"]["path"])
    txt = str(sc["mutation"]["text"])
    mutate(work / legit, str(sc["mutation"]["op"]), txt)
    sh(["git", "add", "-f", "--", legit], work, t)
    obs["commit.normal"] = sh(["git", "commit", "-qm", "rehearsal normal"], work, t)
    # (3) A REAL PARTIAL commit: git mints its OWN temp index (next-index-<pid>.lock) and hands it to the hook.
    mutate(work / legit, str(sc["mutation"]["op"]), txt)
    sh(["git", "add", "-f", "--", legit], work, t)
    obs["commit.partial"] = sh(["git", "commit", "-qm", "rehearsal partial", "--", legit], work, t)
    # (4) EACH RAIL, ALONE: its verdict and the PROVENANCE of its note for the ambient value the hook receives.
    for rail in doc["rails"]:
        role = str(rail["role"])
        obs["rail." + role + ".staged"] = sh(rail_cmd(str(rail["invocation"])), work, t)
        obs["rail." + role + ".ambient"] = sh(rail_cmd(str(rail["invocation"])), work, t,
                                              extra={"GIT_INDEX_FILE": str(gitdir / "index")})
        obs["rail." + role + ".selftest"] = sh(rail_cmd(str(rail["selftest"])), work, t)
    # (5) PLANTED VIOLATIONS: a boundary that accepts these has no teeth.
    for planted in sc["planted"]:
        name, path = str(planted["name"]), str(planted["path"])
        clean_reset(work, t)
        mutate(work / path, str(planted["op"]), txt)
        sh(["git", "add", "-f", "--", path], work, t)
        obs["neg." + name + ".rail"] = sh(rail_cmd(str(rail_by_role(doc, str(planted["rail"]))["invocation"])),
                                          work, t)
        obs["neg." + name + ".commit"] = sh(["git", "commit", "-qm", "rehearsal " + name], work, t)
    clean_reset(work, t)
    obs["module.selftest"] = sh(rail_cmd(str(doc["module"]["selftest"])), work, t)
    return root, obs


def classify(obs: dict[str, Obs], doc: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    """Every declared fact against what the boundary DID. PURE - the selftest drives it with synthetic facts."""
    fatal: list[str] = []
    owed: list[str] = []
    sc = doc["scenarios"]

    def need(name: str, want_rc: int, why: str) -> Obs | None:
        """One declared fact. An UNOBSERVED fact is a fault, never a pass (C16)."""
        got = obs.get(name)
        if got is None:
            fatal.append(name + ": NOT OBSERVED - " + why + " (an unobserved fact is never a pass, C16)")
            return None
        if got.rc != want_rc:
            fatal.append(name + ": rc=" + str(got.rc) + ", declared " + str(want_rc) + " - " + why
                         + ("\n      " + got.tail() if got.text.strip() else ""))
            return None
        return got

    for name, why in (("setup.init", "the fixture repository must exist before the boundary is rehearsed"),
                      ("setup.materialize", "the fixture must hold the TRACKED HEAD bytes"),
                      ("setup.hooks_rederive", "the installed hook must EQUAL its own re-derivation (BUG-526)"),
                      ("bootstrap.commit", "the fixture must have a HEAD before a legitimate commit is rehearsed")):
        need(name, 0, why)
    # A LEGITIMATE COMMIT MUST PASS. This is the BUG-574 control: every synthetic control was green while every
    # commit in the repository was refused, because the value git HANDS the hook was in no test.
    for name, key, what in (("commit.normal", "normal_commit", "a real NORMAL commit through the hook"),
                            ("commit.partial", "partial_commit", "a real PARTIAL commit (git OWN temp index)")):
        got = need(name, int(sc[key]["expect_rc"]), what + " must be ACCEPTED - a rule that cannot fire on the "
                                                          "legitimate case is the BUG-574 class")
        if got is None:
            continue
        kind, field = str(sc[key]["note_kind"]), str(sc[key]["note_field"])
        want_n = sum(1 for r in doc["rails"] if str(r[field]) == kind)
        got_n = sum(1 for k in note_kinds(got.text) if k == kind)
        if got_n != want_n:
            fatal.append(name + ": " + str(got_n) + " note(s) of provenance " + repr(kind) + ", declared "
                         + str(want_n) + " by " + repr(field) + " - at the write moment each pinned rail must NAME the subject it READ; a "
                         "note that is absent, or of another provenance, is a claim with no evidence (BUG-567)")
    # EACH RAIL ALONE: its verdict, and the provenance of the note it prints for the ambient hook environment.
    for rail in doc["rails"]:
        role = str(rail["role"])
        need("rail." + role + ".staged", int(rail["staged_rc"]), role + " must be CLEAN at an inert staged set: "
             + str(rail["why"]))
        got = need("rail." + role + ".ambient", 0, role + " must TOLERATE the ambient value git hands the hook")
        if got is not None:
            want = str(rail["ambient_note"])
            kinds = note_kinds(got.text)
            if (want == "none" and kinds) or (want != "none" and kinds.count(want) != 1):
                fatal.append("rail." + role + ".ambient: note provenance " + repr(kinds or ["none"])
                             + ", declared " + repr(want) + " - " + str(rail["ambient_note_why"]))
        need("rail." + role + ".selftest", 0, role + " own known-answer controls must fire (BUG-492)")
    need("module.selftest", 0, "the git-subject rule own controls must fire (ONE home, D-2646)")
    # PLANTED VIOLATIONS: the boundary must have TEETH, and the DECLARED rail must be the one that refuses.
    for planted in sc["planted"]:
        name, role, path = str(planted["name"]), str(planted["rail"]), str(planted["path"])
        got = need("neg." + name + ".rail", int(planted["expect_rail_rc"]),
                   "the planted violation (" + str(planted["why"]) + ") must be refused by " + role)
        if got is not None and path not in got.text:
            fatal.append("neg." + name + ".rail: " + role + " refused but never NAMES the planted path "
                         + repr(path) + " - a refusal that does not name its subject cannot be told from an "
                         "unrelated fault")
        blocked = obs.get("neg." + name + ".commit")
        if blocked is None:
            fatal.append("neg." + name + ".commit: NOT OBSERVED - the planted violation was never handed to the "
                         "hook, so nothing shows the boundary REFUSES a commit")
        elif blocked.rc == 0:
            fatal.append("neg." + name + ".commit: the commit LANDED (rc=0) over " + str(planted["why"])
                         + " - the write boundary has no teeth at a real commit")
    # DECLARED DEBT (BUG-576): a refusal the declaration NAMES is tolerated and re-measured; one it does NOT
    # name is a NEW instance of the class and must not hide behind the declared one; and a PAID debt must be
    # withdrawn by a decision, never silently kept.
    for debt in doc["declared_debt"]:
        name = str(debt["observation"])
        got = obs.get(name)
        if got is None:
            fatal.append(name + ": NOT OBSERVED - " + str(debt["id"]) + " is re-measured here")
        elif got.rc == 0:
            owed.append(str(debt["id"]) + " (" + str(debt["title"]) + "): the declared refusal NO LONGER HAPPENS "
                        "- the debt is PAID, so the declaration must be WITHDRAWN by a decision")
        elif str(debt["marker"]) not in got.text:
            fatal.append(name + ": refused (rc=" + str(got.rc) + ") for a reason the declaration does NOT name "
                         "(" + str(debt["id"]) + " declares " + repr(str(debt["marker"])) + " from "
                         + str(debt["rail"]) + "): a NEW instance of the class, not the declared debt - a "
                         "declared debt must never become a blanket excuse")
    return (EXIT_FATAL if fatal else (EXIT_OWED if owed else EXIT_CLEAN)), fatal, owed


# ------------------------------------------------------------------------------------------------ controls
def note_block(kind: str, n: int = 1) -> str:
    """A synthetic note block of the DECLARED provenance, built from the marker's ONE home (D-2646)."""
    marker = git_subject.NOTE_MARKERS[kind]
    return "".join("note rail " + str(i) + ": GIT_INDEX_FILE=/g/index " + marker + " (/g/index)" + chr(10)
                   for i in range(n))


def clean_obs(doc: dict[str, Any]) -> dict[str, Obs]:
    """A synthetic rehearsal in which EVERY declared fact holds - the classifier's own positive control."""
    obs: dict[str, Obs] = {}
    sc = doc["scenarios"]
    for k in ("setup.init", "setup.materialize", "setup.hooks_rederive", "bootstrap.commit", "module.selftest"):
        obs[k] = Obs(0, "")
    for key, name in (("normal_commit", "commit.normal"), ("partial_commit", "commit.partial")):
        kind, field = str(sc[key]["note_kind"]), str(sc[key]["note_field"])
        n = sum(1 for r in doc["rails"] if str(r[field]) == kind)
        obs[name] = Obs(0, note_block(kind, n))
    for rail in doc["rails"]:
        role, kind = str(rail["role"]), str(rail["ambient_note"])
        obs["rail." + role + ".staged"] = Obs(int(rail["staged_rc"]), "")
        obs["rail." + role + ".ambient"] = Obs(0, "" if kind == "none" else note_block(kind))
        obs["rail." + role + ".selftest"] = Obs(0, "")
    for planted in sc["planted"]:
        n = str(planted["name"])
        obs["neg." + n + ".rail"] = Obs(int(planted["expect_rail_rc"]), str(planted["path"]) + " refused")
        obs["neg." + n + ".commit"] = Obs(1, str(planted["path"]) + " refused")
    for debt in doc["declared_debt"]:
        obs[str(debt["observation"])] = Obs(1, str(debt["marker"]) + ": " + str(debt["title"]))
    return obs


def selftest() -> int:
    """Known-answer controls: every decision above must be SEEN to fire, and the provenance join must be REAL."""
    doc = cfg()
    subj = git_subject.discover(git_subject.config())
    own = git_subject.adopt_index(git_subject.config(), subj, subj.index_file)[1]
    cases: list[tuple[str, dict[str, Obs], int]] = []
    base = clean_obs(doc)
    cases.append(("clean_rehearsal", dict(base), EXIT_CLEAN))
    m = dict(base)
    m["commit.normal"] = Obs(1, "REFUSED git-subject (BUG-574): the ambient value IS the pinned subject")
    cases.append(("legit_commit_refused (BUG-574 shape)", m, EXIT_FATAL))
    m = dict(base)
    m["commit.normal"] = Obs(0, "")
    cases.append(("note_never_printed", m, EXIT_FATAL))
    m = dict(base)
    m["commit.partial"] = Obs(0, note_block("own_index", len(doc["rails"])))
    cases.append(("wrong_note_provenance (BUG-567 shape)", m, EXIT_FATAL))
    first = str(doc["scenarios"]["planted"][0]["name"])
    m = dict(base)
    m["neg." + first + ".commit"] = Obs(0, "")
    cases.append(("planted_violation_LANDED (no teeth)", m, EXIT_FATAL))
    m = dict(base)
    del m["rail.RAIL 0.selftest"]
    cases.append(("observation_missing", m, EXIT_FATAL))
    m = dict(base)
    m["setup.hooks_rederive"] = Obs(1, "hook DIFFERS from its re-derivation")
    cases.append(("hook_not_the_declared_one", m, EXIT_FATAL))
    for debt in doc["declared_debt"]:
        obs_name = str(debt["observation"])
        m = dict(base)
        m[obs_name] = Obs(0, "")
        cases.append(("debt_" + str(debt["id"]) + "_paid (stale declaration)", m, EXIT_OWED))
        m = dict(base)
        m[obs_name] = Obs(1, "FAIL something-else: refused for an undeclared reason")
        cases.append(("undeclared_refusal_at_" + obs_name, m, EXIT_FATAL))
    # A control for the DECLARED FIELD ITSELF (the defect this fix closes): if `partial_note` were IGNORED, the
    # wrong-provenance partial commit would pass. Mutating every rail's declaration to `none` must turn it RED.
    blind = copy.deepcopy(doc)
    for rail in blind["rails"]:
        rail["partial_note"] = "none"
    cases.append(("partial_note_declaration_is_read", dict(base), EXIT_FATAL))
    docs = {"partial_note_declaration_is_read": blind}   # the ONE case classified against a MUTATED doc
    bad = 0
    for name, obs, expect in cases:
        rc, fatal, owed = classify(obs, docs.get(name, doc))
        good = rc == expect
        bad += 0 if good else 1
        print("  " + ("ok  " if good else "FAIL") + " selftest/" + name + ": rc=" + str(rc) + " expected="
              + str(expect) + ("" if good else " :: " + "; ".join((fatal + owed)[:1])))
    joins = [("the note the RULE actually builds for the repo OWN index is read as provenance own_index",
              git_subject.note_kind(own) == "own_index"),
             ("a REFUSAL is never read as a note (provenance none)",
              git_subject.note_kind("REFUSED git-index (BUG-566, fail closed, C16): ...") == "none"),
             ("the config declares the debt it re-measures and a bootstrap that exists only for it",
              bool(doc["declared_debt"]) and "--no-verify" in [str(x) for x in doc["temp"]["bootstrap"]["flags"]])]
    for why, good in joins:
        bad += 0 if good else 1
        print("  " + ("ok  " if good else "FAIL") + " selftest/" + why)
    print("boundary-rehearsal controls: " + str(len(cases) + len(joins) - bad) + "/" + str(len(cases) + len(joins))
          + " known-answer control(s) fire")
    return EXIT_CLEAN if not bad else EXIT_FATAL


def main() -> int:
    """CLI: --check (default) | --selftest | --keep (keep the fixture for inspection)."""
    ap = argparse.ArgumentParser(description="the write boundary at a REAL commit (D-2675)")
    ap.add_argument("--selftest", action="store_true", help="the rail's own known-answer controls")
    ap.add_argument("--keep", action="store_true", help="keep the fixture and print its path")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    doc = cfg()
    root, obs = rehearse(doc)
    rc, fatal, owed = classify(obs, doc)
    try:
        if rc == EXIT_CLEAN:
            print("ok boundary rehearsal: a real NORMAL commit and a real PARTIAL commit both PASSED through the "
                  "hook (" + str(len(note_kinds(obs["commit.normal"].text))) + " pinned note(s), "
                  + str(len(note_kinds(obs["commit.partial"].text))) + " at the partial commit), "
                  + str(len(doc["scenarios"]["planted"])) + " planted violation(s) REFUSED by their declared rail, "
                  + str(len(doc["rails"]) + 1) + " rail selftest(s) fire, "
                  + str(len(doc["declared_debt"])) + " declared debt re-measured ("
                  + ", ".join(str(d["id"]) for d in doc["declared_debt"]) + ")")
        else:
            print(("FAIL boundary rehearsal" if rc == EXIT_FATAL else "OWED boundary rehearsal")
                  + ": the write boundary is not what the declarations say it is:")
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
