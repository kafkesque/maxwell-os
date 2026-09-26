#!/usr/bin/env python3
"""RAIL 4 (BUG-430): work may only touch what the session's plan declared (anti-drift lock).

The failure this blocks: a session asked for A wanders into B, rewrites an artifact nobody asked about, and
the owner discovers it later. Rail: the plan file lists the paths the session may touch; the commit is
refused if it touched anything else. To widen scope you must FIRST commit the plan change - so scope creep
becomes a visible, reviewable act instead of a side effect.

TWO HARDENINGS, both MEASURED 2026-09-26 (each closes an executed bypass, each with a control that fails on
the pre-fix code):
  * BUG-527 - the AUDITED SUBJECT is no longer inherited. This rail shells git, and `GIT_INDEX_FILE=/tmp/abidx
    ... --staged` returned rc=0 ("all declared") while the real staged set was never read: the rail faithfully
    audited the index it was TOLD to audit, and the environment was nobody's declared home. The subject is now
    DISCOVERED from this file's location and PINNED (scripts/lib/git_subject.py, one home, D-2646). The
    explicit `--index-file` flag replaces the inherited variable for controls and diagnostics: a visible
    argument is a declared home, an inherited variable is not.
  * BUG-528 - PROTECTION IS BY FAMILY, not by name. will_not_touch matched NAMES, so a sync client's rename of
    a protected artifact (`Copy of X.csv`, `X.csv (machine's conflicted copy DATE)`) was out of scope, and one
    such sibling was ITSELF listed in may_touch: the owner instrument was editable through its copy while
    forbidden through its name. The renaming VOCABULARY is consumed from its one home
    (config/repo_integrity.yaml#conflict_marker) instead of being restated here.

THIRD HARDENING, MEASURED 2026-09-26 (D-2668): `crossing: true` was a RECORD no rail consumed, so the
pipeline/** boundary stayed closed while the plan read as if the owner had acked it. A crossing is now a PERMIT
only for the paths it NAMES (`crossed:`), only with a NAMED ACK (`acked_by` + `acked_on`), and only until it is
SPENT (`spent_by`, the commit that used it) - an ack may not outlive the commit it was given for. A `crossed:`
path outside every will_not_touch family is refused, or `crossed:` would be a second, unaudited may_touch.

Usage: python3 scripts/check_session_plan.py [--commit HEAD] [--staged] [--plan ...] [--index-file P] [--selftest]
Post-hoc checking catches violations AFTER they are in history (BUG-445): install the hook instead -
bash scripts/install_git_hooks.sh - so rail 4 refuses the commit rather than reporting it.
Exit: 0 ok | 1 defect (including a self-contradicting plan) | 2 owner-owed (a will_not_touch path)
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib import git_subject  # noqa: E402

DEFAULT_PLAN = "governance/session_plan_20260924.yaml"


def families(doc: dict | None) -> list[re.Pattern[str]]:
    """The sync client's renaming vocabulary, consumed from its ONE home - never restated here (D-2646)."""
    cm = (doc or {}).get("conflict_marker") or {}
    return [re.compile(str(p)) for p in list(cm.get("patterns") or []) + list(cm.get("prefix_patterns") or [])]


def canonical_names(path: str, pats: list[re.Pattern[str]]) -> list[str]:
    """Every path this one could be a sync-client RENAME of: itself plus its canonical form(s).

    BUG-531 (MEASURED 2026-09-26, found by the failing control, not by production): the vocabulary was
    applied to the WHOLE PATH, so `^Copy of ` could never match - `governance/Copy of X.csv` does not
    START with `Copy of `. The suffix form passed only because it was unanchored, which is exactly what
    made the defect silent: one control fired, so the family logic looked proven. A rename is a fact
    about the NAME, so each pattern is applied to the BASENAME and the surviving directory is rejoined.
    The VOCABULARY is not touched: it still lives once in config/repo_integrity.yaml#conflict_marker.
    """
    base = os.path.basename(path)
    parent = path[: len(path) - len(base)]
    out = [path]
    for p in pats:
        try:
            n = p.sub("", base)
        except re.error:
            continue
        cand = parent + n
        if n and n != base and cand not in out:
            out.append(cand)
    return out


def widening_faults(plan: dict, plan_rel: str) -> list[str]:
    """BUG-548: an entry that RECORDS a permission the contract does not GRANT (the D-2649 shape).

    MEASURED 2026-09-26: four of fifteen recorded widenings were never in `may_touch`. Rail 4 reads `may_touch`
    ONLY and NOTHING read `widening_log`, so the plan documented permissions it did not give and the artifacts
    sat uncommittable while the plan read as if they were permitted. A RECORD WITH NO CONSUMER IS NOT A RULE.

    The rule: every path an entry claims as a WIDENING (`widened:`, `additions[*].pattern`) must be MATCHED by
    may_touch, unless the entry explains itself as one of the two declared exceptions -
      * `crossing: true` - an owner-acked ONE-OFF crossing of will_not_touch (the pipeline/** convention: the
        SUBJECT of an ack, never standing permission);
      * `withdrawn:` - the path was recorded and then withheld, listed as {'pattern': ..., 'why': ...}.
    """
    allow = [str(x) for x in (plan.get("may_touch") or [])]
    faults: list[str] = []
    for i, entry in enumerate(plan.get("widening_log") or [], start=1):
        if not isinstance(entry, dict) or entry.get("crossing") is True:
            continue
        gone = {str(w.get("pattern")) for w in (entry.get("withdrawn") or []) if isinstance(w, dict)}
        claims = [str(p) for p in (entry.get("widened") or [])]
        claims += [str(a.get("pattern")) for a in (entry.get("additions") or []) if isinstance(a, dict)]
        for pat in claims:
            if pat in gone or any(fnmatch.fnmatch(pat, a) for a in allow):
                continue
            faults.append("widening_log entry #" + str(i) + " RECORDS '" + pat + "' but may_touch does not GRANT "
                          "it (BUG-548: the record is not the rule) -> add it to may_touch as a NAMED path, list "
                          "it under `withdrawn:`, or mark the entry `crossing: true`")
    return faults


def crossing_permits(plan: dict, forbid: list[str], pats: list[re.Pattern[str]]) -> tuple[list[str], list[str], list[str]]:
    """D-2668: an owner-acked `crossing: true` entry is a PERMIT only for the paths it NAMES.

    MEASURED 2026-09-26 (BUG-562): `crossing: true` was a RECORD that NOTHING consumed - `widening_faults`
    tolerated it and `verdicts` ignored it - so the plan read as if the owner had acked the pipeline/**
    boundary while every path under it still returned rc=2. A record with no consumer is not a rule; its
    inverse is worse: a permit with no SUBJECT and no ACK is standing permission nobody granted.

    Three conditions, each with a control that can fail (BUG-492), all three required:
      * SUBJECT - `crossed:` names the paths. A `crossed:` path that is NOT in a will_not_touch family is
        refused, or `crossed:` would become a second, unaudited may_touch (the granting-direction bypass).
      * ACK - `acked_by` + `acked_on` name who acked and when. Named subjects with no ack is a FAIL, not a
        pass, because the entry then LOOKS like a permit while granting nothing (the BUG-548 shape).
      * SPENT - `spent_by` is the commit that used it. Once set the entry yields NOTHING, so an ack cannot
        outlive the commit it was given for and decay into standing permission over production files.
    """
    permits: list[str] = []
    faults: list[str] = []
    notes: list[str] = []
    for i, entry in enumerate(plan.get("widening_log") or [], start=1):
        if not isinstance(entry, dict) or entry.get("crossing") is not True:
            continue
        crossed = [str(p) for p in (entry.get("crossed") or [])]
        if not crossed:
            continue  # a RECORD, not a permit (BUG-548: tolerated, grants nothing)
        owner = str(entry.get("acked_by") or "").strip()
        when = str(entry.get("acked_on") or "").strip()
        if not (owner and when):
            faults.append("widening_log entry #" + str(i) + " NAMES " + str(len(crossed)) + " crossing subject(s) "
                          "but no ACK: a permit without its ack is the BUG-548 shape in the GRANTING direction "
                          "-> add `acked_by` + `acked_on`, or drop `crossed:` and let it stay a RECORD")
            continue
        for pat in crossed:
            if any(fnmatch.fnmatch(n, f) for n in canonical_names(pat, pats) for f in forbid):
                continue
            faults.append("widening_log entry #" + str(i) + " crosses '" + pat + "' which is NOT in any "
                          "will_not_touch family - `crossed:` is not a second may_touch: grant a path there, or "
                          "record it as a `widened:` widening instead")
        if entry.get("spent_by"):
            continue  # SPENT: the ack was used by that commit and yields no further permit
        permits += crossed
        notes.append("PERMIT session plan: widening_log entry #" + str(i) + " crosses " + str(len(crossed))
                     + " will_not_touch path(s) under an owner ack (" + owner + ", " + when + ") -> mark it "
                     "`spent_by: <commit>` when it lands, or an acked permit decays into standing permission "
                     "(D-2668)")
    return permits, faults, notes

def verdicts(plan: dict, out: list[str], pats: list[re.Pattern[str]], plan_rel: str) -> tuple[int, list[str]]:
    """The whole rule as a pure function, so the controls can hand it a synthetic plan as easily as the live one."""
    allow = [str(x) for x in (plan.get("may_touch") or [])]
    forbid = [str(x) for x in (plan.get("will_not_touch") or [])]
    lines: list[str] = []
    # THE PLAN'S OWN HONESTY, checked on EVERY invocation - a plan that records a permission it does not grant
    # is refused even when the staged set is clean (BUG-548).
    lie = widening_faults(plan, plan_rel)
    if lie:
        lines.append("FAIL session plan: the plan RECORDS permissions it does not GRANT (BUG-548):")
        lines += ["  " + x for x in lie]
        return 1, lines
    permits, permit_faults, permit_notes = crossing_permits(plan, forbid, pats)
    if permit_faults:
        lines.append("FAIL session plan: a `crossing` entry claims a permit it may not use (D-2668):")
        lines += ["  " + x for x in permit_faults]
        return 1, lines
    lines += permit_notes
    defect = [str(x) for x in (plan.get("may_touch") or [])
              if any(fnmatch.fnmatch(n, f) for n in canonical_names(str(x), pats) for f in forbid)]
    if defect:
        lines.append("FAIL session plan: the plan CONTRADICTS itself - " + str(len(defect))
                     + " may_touch entry(ies) resolve into a will_not_touch family (BUG-528):")
        lines += ["   " + x for x in defect]
        lines.append("   -> remove the entry (a copy of a protected artifact is not a permit to edit it)")
        return 1, lines
    forbidden = [f for f in out
                 if any(fnmatch.fnmatch(n, pat) for n in canonical_names(f, pats) for pat in forbid)
                 and not any(fnmatch.fnmatch(f, c) for c in permits)]
    if forbidden:
        lines.append("FORBIDDEN session plan: " + str(len(forbidden)) + " path(s) are declared will_not_touch, "
                     "by name or as a sync-client RENAME of one (BUG-528) -> widening")
        lines.append("           'may_touch' is NOT a remedy; the owner gate or a revert is:")
        lines += ["  " + f for f in forbidden]
        lines.append("   -> git checkout HEAD -- <path>   OR get the owner gate, then declare a NEW plan revision")
        return 2, lines
    offenders = [f for f in out
                 if not any(fnmatch.fnmatch(f, pat) for pat in allow) and f != plan_rel
                 and not any(fnmatch.fnmatch(f, c) for c in permits)]
    if offenders:
        lines.append("FAIL session plan: touched " + str(len(offenders)) + " path(s) outside the plan:")
        lines += ["  " + o for o in offenders]
        lines.append("   -> widen 'may_touch' in " + plan_rel + " and commit the plan FIRST, or revert the file")
        return 1, lines
    return 0, lines


def _paths(a: argparse.Namespace) -> list[str]:
    """The file list to audit: the PINNED staged set (--staged) or a finished commit's paths (BUG-527)."""
    subj = git_subject.subject(a.index_file)
    if a.staged:
        rc, out = git_subject.run_git(subj, ["diff", "--cached", "--name-only"])
        if rc != 0:
            raise git_subject.SubjectRefused("REFUSED (C16): `git diff --cached` did not resolve against the "
                                             "pinned index " + subj.index_file)
        return out.split()
    rc, out = git_subject.run_git(subj, ["show", "--name-only", "--format=", a.commit])
    if rc != 0:
        raise git_subject.SubjectRefused("REFUSED (C16): commit " + a.commit + " does not resolve")
    return out.split()


def main(argv: list[str] | None = None) -> int:
    """Compare a commit's (or the pinned staged set's) file list against the plan's allow-list."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--plan", default=DEFAULT_PLAN)
    ap.add_argument("--staged", action="store_true",
                    help="audit the STAGED set (for the pre-commit hook) instead of a finished commit")
    ap.add_argument("--index-file", default=None,
                    help="audit an EXPLICIT index instead of this repo's (controls/diagnostics; an inherited "
                         "GIT_INDEX_FILE is refused, not obeyed - BUG-527)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls, incl. the index control")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    plan_path = REPO / a.plan
    if not plan_path.exists():
        print("FAIL session plan: " + a.plan + " does not exist - a session with no plan file may not commit")
        return 1
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    pats = families(yaml.safe_load((REPO / "config" / "repo_integrity.yaml").read_text(encoding="utf-8")))
    rc, lines = verdicts(plan, _paths(a), pats, a.plan)
    for line in lines:
        print(line)
    scope = "staged set" if a.staged else "commit " + a.commit
    if rc == 0:
        print("ok session plan: " + scope + " touched " + str(len(_paths(a))) + " path(s), all declared in " + a.plan)
    return rc


def _staged_count_raw() -> int:
    """The REAL index's staged count, read with no pin - the control's own control (BUG-492: the incident)."""
    out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=REPO, capture_output=True, text=True)
    return len(out.stdout.split())


def selftest() -> int:
    """Controls that can FAIL (BUG-492), including the anti-overreach one and the one that fires on the bypass."""
    pats = families(yaml.safe_load((REPO / "config" / "repo_integrity.yaml").read_text(encoding="utf-8")))
    live = yaml.safe_load((REPO / DEFAULT_PLAN).read_text(encoding="utf-8"))
    protect = "governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv"
    renamed = "governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv"
    conflicted = protect + " (Dropbox's conflicted copy 2026-09-26)"
    # A control's baseline is SYNTHETIC (BUG-492): a control that can only PASS while the live plan happens to be
    # clean is not a control. The live plan's own contradictions are reported by their own control below.
    clean = {"may_touch": ["scripts/*.py", "governance/buglog.md"], "will_not_touch": list(live["will_not_touch"])}
    stale = {"may_touch": list(clean["may_touch"]) + [renamed], "will_not_touch": list(clean["will_not_touch"])}
    live_faults = verdicts(live, [], pats, DEFAULT_PLAN)[0]
    controls = [
        ("a will_not_touch path is FORBIDDEN (rc=2, the owner gate)",
         verdicts(clean, [protect], pats, DEFAULT_PLAN)[0] == 2),
        ("a 'Copy of <will_not_touch>' SIBLING is FORBIDDEN (BUG-528: the rename bypass)",
         verdicts(clean, [renamed], pats, DEFAULT_PLAN)[0] == 2),
        ("a '<will_not_touch> (conflicted copy DATE)' sibling is FORBIDDEN",
         verdicts(clean, [conflicted], pats, DEFAULT_PLAN)[0] == 2),
        ("ANTI-OVERREACH: a genuinely unrelated path is TOLERATED (an in-plan path, rc=0)",
         verdicts(clean, ["scripts/check_session_plan.py"], pats, DEFAULT_PLAN)[0] == 0),
        ("ANTI-OVERREACH: an unrelated path is still only rc=1 (outside the plan, not forbidden)",
         verdicts(clean, ["docs/not_in_the_plan.md"], pats, DEFAULT_PLAN)[0] == 1),
        ("a plan whose may_touch lists a protected artifact's COPY is a defect (the live stale entry, rc=1)",
         verdicts(stale, ["scripts/check_session_plan.py"], pats, DEFAULT_PLAN)[0] == 1),
        ("the LIVE plan is self-consistent: no may_touch entry resolves into a will_not_touch family "
         "(a FAIL here is a plan defect, not a control defect)", live_faults == 0),
    ]
    real_before = _staged_count_raw()
    fd, synth = tempfile.mkstemp(prefix="rail4_synth_")
    os.close(fd)
    os.unlink(synth)
    env = dict(os.environ, GIT_INDEX_FILE=synth)
    try:
        subprocess.run(["git", "read-tree", "HEAD"], cwd=REPO, env=env, capture_output=True)
        subprocess.run(["git", "update-index", "--force-remove", "agent/session_seed.yaml"],
                       cwd=REPO, env=env, capture_output=True)
        p = subprocess.run([sys.executable, str(Path(__file__)), "--staged"], cwd=REPO, env=env,
                           capture_output=True, text=True)
        env_refused = p.returncode != 0
    finally:
        if os.path.exists(synth):
            os.unlink(synth)
    real_after = _staged_count_raw()
    controls.append(("INDEX control: an inherited/synthetic GIT_INDEX_FILE is REFUSED, not obeyed (BUG-527)",
                     env_refused))
    controls.append(("CONTROL ON THE CONTROL: the real index is untouched by that probe (it was not, on "
                     "2026-09-26: 42 -> 43, observed by hand only)", real_before == real_after))
    granted = {"widening_log": [{"widened": ["scripts/*.py"]}], "may_touch": list(live["may_touch"])}
    ungranted = {"widening_log": [{"widened": ["governance/nowhere_at_all.md"]}], "may_touch": list(live["may_touch"])}
    withheld = {"widening_log": [{"widened": ["governance/nowhere_at_all.md"],
                                  "withdrawn": [{"pattern": "governance/nowhere_at_all.md", "why": "recorded then refused"}]}],
                "may_touch": list(live["may_touch"])}
    crossed = {"widening_log": [{"additions": [{"pattern": "pipeline/stage5_verify.py"}], "crossing": True}],
               "may_touch": list(live["may_touch"])}
    controls += [
        ("BUG-548: an entry that RECORDS a widening may_touch does not GRANT is a FAIL (the record is not the rule)",
         widening_faults(ungranted, DEFAULT_PLAN) != []),
        ("BUG-548 ANTI-OVERREACH: an entry whose recorded path IS granted is TOLERATED",
         widening_faults(granted, DEFAULT_PLAN) == []),
        ("BUG-548: a WITHDRAWN claim is TOLERATED (a withheld request is not a lie)",
         widening_faults(withheld, DEFAULT_PLAN) == []),
        ("BUG-548: an owner-acked `crossing: true` is TOLERATED (it never claimed to be a permit)",
         widening_faults(crossed, DEFAULT_PLAN) == []),
        ("BUG-548: the LIVE plan records no permission it does not grant (a FAIL here is a plan defect)",
         widening_faults(live, DEFAULT_PLAN) == []),
    ]
    def _cross(**over) -> dict:
        """A SYNTHETIC baseline (BUG-492): the permit controls must not depend on the live plan's state."""
        entry = {"crossing": True, "crossed": ["pipeline/stage5_verify.py"], "acked_by": "owner",
                 "acked_on": "2026-09-26"}
        entry.update(over)
        return {"widening_log": [entry], "may_touch": list(clean["may_touch"]),
                "will_not_touch": list(clean["will_not_touch"])}
    sib = "pipeline/stage6_commit.py"
    controls += [
        ("D-2668: a NAMED, ACKED crossing subject is PERMITTED (the owner's one-off CROSS, rc=0)",
         verdicts(_cross(), ["pipeline/stage5_verify.py"], pats, DEFAULT_PLAN)[0] == 0),
        ("D-2668 ANTI-OVERREACH: an UNNAMED SIBLING of the crossing subject stays FORBIDDEN (rc=2) - the permit "
         "names its subject or it is not a permit",
         verdicts(_cross(), [sib], pats, DEFAULT_PLAN)[0] == 2),
        ("D-2668: `crossed:` with NO ack is a FAIL (rc=1) - a permit without its ack only LOOKS like permission",
         verdicts(_cross(acked_by="", acked_on=""), ["pipeline/stage5_verify.py"], pats, DEFAULT_PLAN)[0] == 1),
        ("D-2668: a SPENT crossing permits NOTHING (rc=2) - an ack may not outlive the commit it was given for",
         verdicts(_cross(spent_by="deadbeef"), ["pipeline/stage5_verify.py"], pats, DEFAULT_PLAN)[0] == 2),
        ("D-2668: a `crossed:` path OUTSIDE every will_not_touch family is a FAIL (crossed is not a 2nd may_touch)",
         verdicts(_cross(crossed=["docs/not_protected.md"]), ["docs/not_protected.md"], pats, DEFAULT_PLAN)[0] == 1),
        ("D-2668: the LIVE plan's crossing entries are well-formed (a FAIL here is a plan defect)",
         crossing_permits(live, list(live.get("will_not_touch") or []), pats)[1] == []),
    ]

    bad = 0
    for name, ok in controls:
        print(("  ok   " if ok else "  FAIL ") + name)
        bad += 1 - int(ok)
    print("session-plan controls: " + str(len(controls) - bad) + "/" + str(len(controls))
          + " known-answer control(s) fire")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
