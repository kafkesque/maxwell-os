#!/usr/bin/env python3
"""Make 'the repository itself is intact' a rail instead of an assumption (BUG-400 P0-A/P0-B; BUG-500).

WHY
    Every other rail in this repo reads a file and trusts that the read is the file the author wrote. Inside a
    Dropbox File Provider domain that trust is unfounded: on 2026-09-25 the provider renamed .git/refs/heads/
    main (so HEAD stopped resolving and 'git status' offered a 1,220-file first commit), renamed .git/logs/HEAD
    (so 'git reflog' served a stale branch reflog that disagreed with HEAD), and renamed 43 worktree files -
    38 of them leaving the canonical path EMPTY, including the justfile, config/decisions.yaml, DECISION-LOG.md
    and governance/buglog.md. No rail noticed, because no rail looked at the repository as an object.

TWO LAYERS (BUG-500)
    Layer 1 DETECTS a rename inside git metadata, and the pre-commit hook refuses to commit through it.
    Layer 2 PREVENTS it: the git dir must live OUTSIDE every declared sync root, because a rail cannot stop a
    sync client - it can only make the condition loud. This rail asserts BOTH, so the fix is enforced and not
    merely remembered. Measured scope of the fix: a SEPARATE git dir changes no absolute path baked into any
    artifact (the worktree path is untouched), which is why it is the low-risk half of the D-366 relocation.

WHAT IT CHECKS (all probes READ FROM config/repo_integrity.yaml - never invented here; C12)
    1. The git dir resolves as GIT resolves it ('git rev-parse --absolute-git-dir') and lies OUTSIDE every
       declared sync root. A '.git' that is a DIRECTORY inside a synced worktree is the pre-fix layout: it is
       reported as the defect it is (BUG-500), never silently accepted.
    2. HEAD is BORN, UNBORN or BROKEN - three DECLARED states, never a guess (BUG-576). BORN: the born probe
       resolves. UNBORN: HEAD names a ref that does not exist YET - a FRESH repository, and the state the
       BUG-400/BUG-564 RECOVERY route produces. An unborn HEAD is INTACT: 'logs/HEAD' does not exist because git
       creates it AT the first commit, so the reflog probe below is vacuous there and the born probe is the ONLY
       must_resolve entry skipped. BROKEN: neither - the P0-A defect, which the unborn rule must never hide.
       MEASURED 2026-09-27 (boundary rehearsal, real fresh repository): before this fix the rail called an
       unborn HEAD broken metadata and so REFUSED the first commit of a recovered repository - the BUG-574 class
       (a rule that cannot fire on the legitimate case, and a control that only ever asserted refusals).
    3. No conflict-marked name exists INSIDE the git dir (git metadata may not be renamed; P0-A).
    4. The git dir's 'logs/HEAD' exists and its last recorded commit equals HEAD (two records, one fact; P0-A).
    5. No conflict-marked name exists in the worktree; and no TRACKED path is missing from the worktree while
       a conflict copy for it exists (the copy took the canonical name's place; P0-B).

    The git dir is walked as its OWN root wherever it lives - inside the worktree, or outside it after the
    BUG-500 fix - so the probes are identical before and after the fix. A layout migration must not be able to
    blind the rail that exists to police it.

    A conflict copy under a 'report_only_globs' path is owner-owed (exit 2), not fatal: it is real, but it is
    not repository corruption.

Exit: 0 intact | 1 repository integrity defect (P0-A/P0-B/BUG-500) | 2 owner-owed conflict copies only

BUG-541 (MEASURED 2026-09-26). verdict() and the report path are TOTAL: when the canonical name of a
    conflict copy is a DIRECTORY (the measured case is the pre-fix '.git' directory against the 58-byte
    'gitdir:' pointer that replaced it) there are no bytes to compare, so the verdict is OWNER_OWED and the
    plan KEEPS RUNNING. Before this fix '--plan' died with IsADirectoryError - the recovery path crashed
    during exactly the incident it exists for.

--plan prints the deterministic repair (RESTORE_ONLY_COPY / RESTORE_SUPERSET / VAULT) as explicit 'mv'
    commands. It is the SINGLE definition of the conflict-copy -> canonical mapping, so a recovery is a
    reviewed plan rather than an improvised mv, and re-running it is a no-op (idempotent by construction).
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
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib import fixture, git_subject  # noqa: E402 - BUG-577/BUG-568: the fixture rules and the git-subject pin have ONE home each, never a copy

CONFIG = REPO / "config" / "repo_integrity.yaml"
# The DECLARED probes that decide whether HEAD is born, unborn or broken (BUG-576); validated in load_config.
UNBORN_KEYS = ("head_born_probe", "head_unborn_probe", "head_unborn_ref_probe")


def load_config() -> dict[str, Any]:
    """Read the rail's single source of truth; a missing or malformed config is a defect, not a pass."""
    if not CONFIG.exists():
        raise SystemExit(f"FAIL repo-integrity: {CONFIG.relative_to(REPO)} is missing - the probes are prose "
                         "again (BUG-462 class)")
    cfg: Any = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or "conflict_marker" not in cfg or "git" not in cfg:
        raise SystemExit("FAIL repo-integrity: config declares no conflict_marker/git block")
    for key in UNBORN_KEYS:
        if not str(cfg["git"].get(key) or "").strip():
            raise SystemExit(f"FAIL repo-integrity: config declares no git.{key} - the rail cannot tell an "
                             f"UNBORN HEAD from broken metadata without inventing the probe here (C12, BUG-576)")
    if str(cfg["git"]["head_born_probe"]).strip() not in [str(a).strip() for a in cfg["git"].get("must_resolve") or []]:
        raise SystemExit("FAIL repo-integrity: git.head_born_probe is not one of git.must_resolve - the UNBORN "
                         "rule would skip a probe that nothing requires, so the declaration would be inert and "
                         "an unborn repository would be reported by no probe at all (BUG-576)")
    return cfg


_PIN: tuple[dict[str, str], str] | None = None


def subject_bits() -> tuple[dict[str, str], str]:
    """(the environment EVERY child git read in this rail runs with, the note naming the subject audited).

    BUG-568, MEASURED 2026-09-27 before this fix: with `GIT_DIR=<decoy>/.git` ambient this rail printed
    `ok repo-integrity: git dir <decoy>/.git ...` rc=0 - it CERTIFIED A FOREIGN REPOSITORY - and `--worktree`
    reported 723 phantom dirty paths read through the decoy's index, while `--selftest` crashed with a
    FileNotFoundError instead of reporting. The rule has ONE home (D-2646, config/repo_integrity.yaml#git_subject
    via scripts/lib/git_subject.py): the subject is DERIVED from the WORKTREE with every guard variable removed,
    an ambient value naming a DIFFERENT subject is REFUSED, and every child run here writes that pinned subject.
    A repository whose metadata is BROKEN pins nothing and is REPORTED, never refused - which is why THIS rail may
    pin at all, and why it pins through recovery_subject() rather than discover().
    """
    global _PIN
    if _PIN is None:
        doc = git_subject.config()
        subj, note = git_subject.recovery_subject()
        _PIN = ((subj.env(os.environ, git_subject.guard_vars(doc)) if subj
                 else git_subject.cleared_env(doc)), note)
    return _PIN


def env_for(root: Path) -> dict[str, str]:
    """The child environment for a read at 'root': the PINNED subject for THIS repository, guards CLEARED for any
    other root - a fixture MUST resolve from its own worktree, or the known-answer controls below would read the
    live repository (the other half of the same rule, BUG-568)."""
    if os.path.realpath(str(root)) == os.path.realpath(str(REPO)):
        return subject_bits()[0]
    return git_subject.cleared_env(git_subject.config())


def git_at(root: Path, *argv: str) -> tuple[int, str]:
    """Run git with an EXPLICIT root; returns (returncode, stdout+stderr stripped). Never raises on a failure.

    Every probe takes its repository as an ARGUMENT instead of a constant, because a rule about a repository can
    only be tested by RUNNING it in one: the known-answer controls below build REAL repositories in the system
    temp dir and drive THIS function, never a lookalike.
    """
    p = subprocess.run(["git", *argv], cwd=str(root), capture_output=True, text=True, env=env_for(root))
    return p.returncode, (p.stdout + p.stderr).strip()


def git(*argv: str) -> tuple[int, str]:
    """Run git in THIS repository (the default root of every probe)."""
    return git_at(REPO, *argv)


def head_state(cfg: dict[str, Any], root: Path = REPO) -> tuple[str, str]:
    """'born' | 'unborn' | 'broken', plus the ref HEAD names (or why it names none).

    BUG-576. An UNBORN HEAD (HEAD names a branch with no commit yet; git creates logs/HEAD AT the first commit)
    is LEGITIMATE and is the state the BUG-400/BUG-564 RECOVERY route produces - before this fix the rail
    reported it as broken metadata and so refused the one commit that repairs the repository. The probes are
    DECLARED (C12, validated in load_config). Unborn is NOT a blanket excuse: the ref HEAD names must still NOT
    resolve as an object (C16), and a ref that DOES resolve while the born probe does not is 'broken'.
    """
    gcfg = cfg["git"]
    born, unborn, ref_probe = (str(gcfg[k]).strip() for k in UNBORN_KEYS)
    if git_at(root, *born.split())[0] == 0:
        return "born", ""
    rc, out = git_at(root, *unborn.split())
    ref = out.splitlines()[-1].strip() if out else ""
    if rc == 0 and ref:
        if git_at(root, *ref_probe.split(), ref)[0] != 0:
            return "unborn", ref
        return "broken", ref + " resolves as an object while '" + born + "' does not"
    return "broken", "'" + unborn + "' named no ref" + ((": " + ref) if ref else "")


def resolve_git_dir(cfg: dict[str, Any], root: Path = REPO) -> Path | None:
    """The git dir AS GIT RESOLVES IT - never as this file guesses it ('.git' may be a pointer FILE; BUG-500).

    'root' is a parameter for the same reason every probe takes one: a known-answer control resolves the git dir
    of a real fixture repository with THIS function, so the rule under test is the rule that ships.
    """
    probe = str(cfg["git"].get("resolve_from") or "rev-parse --absolute-git-dir")
    rc, out = git_at(root, *probe.split())
    if rc != 0 or not out:
        return None
    return Path(out.splitlines()[-1].strip())


def sync_root_hit(cfg: dict[str, Any], path: Path) -> str:
    """The declared sync-domain marker that contains 'path', or '' - never a client name hardcoded here (C12)."""
    s = path.as_posix()
    for marker in cfg["git"].get("sync_root_markers") or []:
        if marker and str(marker) in s:
            return str(marker)
    return ""


def tracked_paths() -> set[str]:
    """The index's path list (what git believes it owns), as repo-relative POSIX strings."""
    rc, out = git("ls-files", "-z")
    if rc != 0:
        return set()
    return {p for p in out.split("\0") if p}


def _rel(p: Path) -> str:
    """Repo-relative POSIX path when it is inside the worktree; the absolute path when it is not."""
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return str(p)


def _is_git_dir(path: Path, git_dir: Path | None) -> bool:
    """True when 'path' is the git dir (compared resolved, so a symlinked tmp path still matches)."""
    if git_dir is None:
        return False
    try:
        return path.resolve() == git_dir.resolve()
    except OSError:
        return False


def _same_bytes(a: Path, b: Path) -> bool | None:
    """True/False when BOTH sides are regular files; None when one side has no bytes to compare (BUG-541).

    A conflict copy can have a DIRECTORY as its canonical name - the measured case is the pre-fix '.git'
    directory (resurrected by the sync client) against the 58-byte 'gitdir:' POINTER FILE that replaced it.
    read_bytes() on that directory raised IsADirectoryError, so the ONE documented recovery path ('--plan')
    crashed with a traceback exactly during the incident it exists for, and 'just health' RAIL 0 would have
    crashed the same way the moment the git dir resolved again. A rail must DECIDE, never raise (C16).
    """
    if not (a.is_file() and b.is_file()):
        return None
    return a.read_bytes() == b.read_bytes()


def _content_word(row: dict[str, Any]) -> str:
    """identical | DIVERGES | UNCOMPARABLE - a three-way word, because 'one side is a directory' is neither."""
    same = _same_bytes(row["cc_abs"], row["canonical_abs"])
    if same is None:
        return "UNCOMPARABLE (one side is a DIRECTORY)"
    return "identical" if same else "DIVERGES"


def _scan_root(root: Path, tracked: set[str], pattern: re.Pattern[str], git_dir: Path | None,
               in_git: bool) -> list[dict[str, Any]]:
    """Walk ONE root (the worktree, or the git dir) and return its conflict-marked paths.

    Only directory-entry names are read (no file contents), so the cost is a directory walk, not I/O on the
    43 copies; the hash of a copy is not needed to DECIDE (the verdicts are name-based by construction).
    """
    rows: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if not in_git and _is_git_dir(Path(dirpath), git_dir):
            dirnames[:] = []          # the git dir is scanned once, as its own root, wherever it lives
            continue
        for name in list(dirnames) + list(filenames):
            m = pattern.search(name)
            if not m:
                continue
            p = Path(dirpath) / name
            canonical = p.with_name(pattern.sub("", name))
            rel_canon = "" if in_git else _rel(canonical)
            rows.append({
                "cc": _rel(p),
                "canonical": str(canonical) if in_git else rel_canon,
                "marker": m.group(1).strip(),
                "canonical_exists": canonical.exists(),
                "canonical_tracked": (not in_git) and (rel_canon in tracked),
                "in_git": in_git,
                "git_rel": _rel(canonical) and None if not in_git else _git_rel(canonical, root),
                "cc_abs": p,
                "canonical_abs": canonical,
            })
    return rows


def _git_rel(canonical: Path, git_dir: Path) -> str | None:
    """Path of a canonical git-metadata file RELATIVE TO THE GIT DIR (what prefer_superset_prefixes names)."""
    try:
        return canonical.relative_to(git_dir).as_posix()
    except ValueError:
        return None


def _declared_archive() -> str:
    """The sibling archive dir, read from its ONE home (C12): config/conflict_policy.yaml."""
    try:
        pol = (yaml.safe_load((REPO / "config" / "conflict_policy.yaml").read_text(encoding="utf-8")) or {})
    except OSError:
        return ""
    return str(pol.get("archive_dir") or "")


def archived_under(archive: str, rel: str) -> bool:
    """True when a conflict copy is a FIXED POINT: a sibling already resolved INTO the declared archive.

    D-2647 already taught the RESOLVER this rule - an archived sibling is a record of a resolution that
    happened, and re-reporting it made the resolver non-idempotent. Rail 0 kept re-deriving its own history:
    MEASURED 2026-09-26, 30 of its 36 owner-owed rows were the archive talking to itself, which SATURATED the
    exit-2 commit gate so the gate could no longer distinguish its own history from a live divergence
    (BUG-547). The archive dir has ONE home; this consumes it rather than restating a path (C12, D-2646).
    """
    if not archive:
        return False
    a = archive.rstrip("/") + "/"
    return rel == archive.rstrip("/") or rel.startswith(a)


def scan(cfg: dict[str, Any], git_dir: Path | None = None) -> list[dict[str, Any]]:
    """Every conflict-marked path in BOTH roots: the git dir (wherever it is) and the worktree.

    PUBLIC API: the 2026-09-25 repair executor imports this, verdict() and superset_holds(), so the shape of a
    row is a contract, not an implementation detail (C21).
    """
    resolved = resolve_git_dir(cfg)
    if git_dir is None or not Path(git_dir).is_dir():
        git_dir = resolved
    pattern = re.compile(cfg["conflict_marker"]["patterns"][0])
    tracked = tracked_paths()
    rows: list[dict[str, Any]] = []
    if git_dir is not None:
        rows += _scan_root(Path(git_dir), tracked, pattern, git_dir, True)
    rows += _scan_root(REPO, tracked, pattern, git_dir, False)
    archive = _declared_archive()
    rows = [r for r in rows if not archived_under(archive, r["cc"])]
    return sorted(rows, key=lambda r: r["cc"])


def superset_holds(cfg: dict[str, Any], row: dict[str, Any]) -> bool:
    """True when canonical is a byte-prefix of the conflict copy: the copy is strictly newer, same history."""
    allowed = cfg["repair"].get("prefer_superset_prefixes") or []
    if row.get("git_rel") not in allowed or not row["canonical_exists"]:
        return False
    if not (row["cc_abs"].is_file() and row["canonical_abs"].is_file()):
        return False          # a DIRECTORY has no bytes: never claim a superset over one (BUG-541)
    canon = row["canonical_abs"].read_bytes()
    cc = row["cc_abs"].read_bytes()
    return cc.startswith(canon) and len(cc) > len(canon)


def verdict(cfg: dict[str, Any], row: dict[str, Any]) -> str:
    """One of RESTORE_ONLY_COPY | RESTORE_SUPERSET | VAULT | OWNER_OWED - the repair vocabulary."""
    if not row["canonical_exists"]:
        transient = cfg["repair"].get("transient_git_paths") or []
        name = row["canonical"].split("/")[-1]
        return "VAULT" if row["in_git"] and name in transient else "RESTORE_ONLY_COPY"
    if superset_holds(cfg, row):
        return "RESTORE_SUPERSET"
    same = _same_bytes(row["cc_abs"], row["canonical_abs"])
    if same is None:
        # BUG-541. No bytes to compare and NEITHER side may be moved by a rail: promoting the file would
        # destroy a directory, promoting the directory would re-break git. Fail closed to a human verdict
        # (the plan prints it and keeps running) instead of raising.
        return "OWNER_OWED"
    if same:
        return "VAULT"
    return "OWNER_OWED"


def report_only(cfg: dict[str, Any], rel: str) -> bool:
    """True when a conflict copy here is owner-owed rather than repository corruption."""
    return any(fnmatch.fnmatch(rel, g) for g in cfg["severity"].get("report_only_globs") or [])


def checks(cfg: dict[str, Any], git_dir: Path | None, rows: list[dict[str, Any]],
           root: Path = REPO) -> tuple[list[str], list[str], list[str]]:
    """Return (fails, owner_owed, notes) by evaluating every probe in the config against 'root'.

    'root' defaults to this repository and is a parameter so a known-answer control can run EVERY probe (not a
    lookalike) inside a real repository in the system temp dir.
    """
    fails: list[str] = []
    owed: list[str] = []
    notes: list[str] = []
    gcfg = cfg["git"]
    if git_dir is None:
        fails.append(f"the git dir does not resolve ('{gcfg.get('resolve_from')}') - this is not a readable "
                     "git worktree (P0-A)")
        return fails, owed, notes
    state, ref = head_state(cfg, root)
    if state == "broken":
        fails.append(f"HEAD is NEITHER born nor UNBORN: '{gcfg['head_born_probe']}' does not resolve and "
                     f"'{gcfg['head_unborn_probe']}' named no ref ({ref}) - a HEAD that resolves to nothing is "
                     f"the P0-A defect, and the UNBORN rule (BUG-576) must not hide it")
    hit = sync_root_hit(cfg, git_dir)
    if hit and gcfg.get("require_git_dir_outside_sync_root"):
        fails.append(f"the git dir {git_dir} is INSIDE a sync domain (matched '{hit}') - a sync client RENAMES "
                     "what it syncs, so git metadata here can be renamed at any moment and every commit through "
                     "it is a gamble (BUG-500). Fix: relocate the git dir out of the synced tree and leave a "
                     "one-line 'gitdir:' pointer at .git")
    elif hit:
        owed.append(f"the git dir {git_dir} is inside sync domain '{hit}'; config tolerates this today, but "
                    "the corruption vector is live (BUG-500)")
    else:
        notes.append(f"git dir {git_dir} is outside every declared sync root")
    for argv in gcfg.get("must_resolve") or []:
        if state == "unborn" and str(argv).strip() == str(gcfg["head_born_probe"]).strip():
            notes.append(f"'{argv}' does not resolve YET: the repository is UNBORN - HEAD names {ref} with no "
                         f"commit yet, which is the state a FRESH or freshly RECOVERED repository is in "
                         f"(BUG-576). Every other probe below is still required")
            continue
        rc, out = git_at(root, *argv.split())
        if rc != 0:
            fails.append(f"'git {argv}' does not resolve (rc={rc}: {out.splitlines()[-1] if out else ''}) - "
                         "every rail below is reading a repository that is not there (P0-A)")
    rc, head = git_at(root, "rev-parse", "HEAD")
    head = head if rc == 0 else ""
    reflog_rel = gcfg.get("head_reflog_relpath")
    reflog = git_dir / str(reflog_rel)
    if reflog_rel and state == "unborn":
        notes.append(f"{git_dir}/{reflog_rel} does not exist YET: git creates it AT the first commit, and HEAD "
                     f"names {ref} with no commit yet - an UNBORN repository, not renamed metadata (BUG-576)")
    elif reflog_rel and not reflog.exists():
        fails.append(f"{git_dir}/{reflog_rel} is MISSING - git's reflog for HEAD has been renamed away, and "
                     "'git reflog' will silently serve a stale branch reflog (P0-A, measured 2026-09-25: "
                     "reflog said HEAD@{0}=a1061cd while HEAD was 96b1e9c)")
    elif reflog_rel and gcfg.get("reflog_must_agree_with_head"):
        last = [ln for ln in reflog.read_text(errors="replace").splitlines() if ln.strip()]
        last_sha = last[-1].split()[1] if last and len(last[-1].split()) > 1 else ""
        if head and last_sha and last_sha != head:
            fails.append(f"{git_dir}/{reflog_rel} records HEAD as {last_sha[:7]} while HEAD is {head[:7]} - "
                         "two records of one fact disagree (P0-A)")
    for row in rows:
        if row["in_git"]:
            fails.append(f"{row['cc']} - git metadata was RENAMED by a sync client (P0-A)")
        elif report_only(cfg, row["cc"]):
            owed.append(f"{row['cc']} (conflict copy under a report-only path; canonical "
                        f"{'present' if row['canonical_exists'] else 'MISSING'})")
        elif not row["canonical_exists"] and row["canonical_tracked"]:
            fails.append(f"{row['cc']} - TRACKED path {row['canonical']} is MISSING and this copy is the "
                         "ONLY surviving copy (P0-B)")
        elif not row["canonical_exists"]:
            owed.append(f"{row['cc']} - canonical {row['canonical']} is MISSING and untracked (P0-B)")
        else:
            owed.append(f"{row['cc']} - duplicate of {row['canonical']}; content {_content_word(row)}")
    return fails, owed, notes


def print_plan(cfg: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """Print the deterministic repair as explicit mv commands (the SINGLE mapping; see the module docstring)."""
    vault = Path(os.path.expanduser(cfg["repair"]["vault_dir"])) / cfg["repair"]["vault_subdir"]
    print(f"# repair plan - conflict copies: {len(rows)}; vault: {vault}")
    for row in rows:
        v = verdict(cfg, row)
        if v in ("RESTORE_ONLY_COPY", "RESTORE_SUPERSET"):
            note = "canonical path emptied by the sync client" if v == "RESTORE_ONLY_COPY" else \
                   "canonical is a byte-prefix of this copy: the copy is strictly newer"
            print(f"# {v}: {note}")
            print(f"mv -- {shq(str(row['cc_abs']))} {shq(str(row['canonical_abs']))}")
        else:
            print(f"# {v}: bytes preserved, canonical left untouched (owner ruling owed)")
            dest = vault / row["cc"]
            print(f"mkdir -pv {shq(str(dest.parent))}")
            print(f"mv -- {shq(str(row['cc_abs']))} {shq(str(dest))}")


def shq(s: str) -> str:
    """POSIX single-quote a path for a printed command (a printed plan must be copy-pasteable)."""
    return "'" + s.replace("'", "'\\''") + "'"


def _row(cc: Path, canonical: Path, *, in_git: bool = False, git_rel: str | None = None) -> dict[str, Any]:
    """A row shaped EXACTLY as scan() builds one - a control must exercise the contract, not a lookalike."""
    return {"cc": str(cc), "canonical": str(canonical), "canonical_abs": canonical, "cc_abs": cc,
            "canonical_exists": canonical.exists(), "in_git": in_git, "git_rel": git_rel}




def ignore_probe_path(pattern: str) -> str:
    """The path git is ASKED about, DERIVED from the declared pattern - never typed twice.

    BUG-563: a declaration that claims an exclusion must be joined to the verdict GIT ITSELF gives, or it is a
    claim about a repository nobody asked. Each run of '*' becomes a literal 'x', so 'backups/**' probes
    'backups/x' and the answer comes from .gitignore's bytes rather than from this file's belief (D-405).
    """
    return re.sub(r"\*+", "x", str(pattern))


def dirty_msg(st: str, path: str) -> str:
    """The ONE wording for 'dirty and in neither declared home' (a fault text is a fact, not a flourish)."""
    return (st.strip() + " " + path + " is dirty and is NEITHER GRANTED by the plan's may_touch NOR "
            "declared-excluded in config/repo_integrity.yaml#worktree.excluded (BUG-563): no plan may commit it "
            "and git does not ignore it, so the tree can never be clean and its content is unversioned BY "
            "ACCIDENT - grant it (named, in the plan) or declare the exclusion (with a why)")


def dirty_entries() -> list[tuple[str, str]]:
    """(status, path) for every dirty path in the worktree, from a NUL-separated read.

    BUG-565: a NAME LIST, never a whitespace split - ELEVEN tracked paths here contain a space. `-z` with
    --untracked-files=all lists an untracked directory's FILES individually, which is the granularity a
    per-path disposition needs; a rename record carries TWO paths, so its origin is consumed with its status.
    """
    # MEASURED 2026-09-27: the shared git() helper STRIPS its output, which ate the leading space of the
    # two-character status field (" M .gitignore" -> "M .gitignore") and turned the path into "gitignore". A
    # parser may not depend on a whitespace convention it does not own (C16), so the records are read RAW.
    r = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=REPO,
                       capture_output=True, env=env_for(REPO))
    if r.returncode != 0:
        raise SystemExit("REFUSED (C16): `git status` did not resolve - the worktree subject is unavailable "
                         "(rail 0's own subject, BUG-568: it is deliberately NOT pinned to an ambient index)")
    rows = [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]
    dirty: list[tuple[str, str]] = []
    i = 0
    while i < len(rows):
        rec = rows[i]
        st, path = rec[:2], rec[3:]
        dirty.append((st, path))
        i += 2 if ("R" in st or "C" in st) else 1
    return dirty


def worktree_faults(dirty: list[tuple[str, str]], grants: list[str], excluded: list[dict[str, Any]],
                    is_ignored: Any) -> tuple[list[str], int, int]:
    """PURE (BUG-492): every input is a PARAMETER, including git's own ignore verdict (is_ignored).

    THE RULE (BUG-563). A dirty path must sit in ONE of TWO declared homes - GRANTED by the plan's may_touch (it
    can be committed) or DECLARED-EXCLUDED here AND actually ignored by git. MEASURED before the fix: 123 of
    124 dirty paths sat in NEITHER, so a session was obliged to create paths (C13 evidence) that no plan could
    commit and git would never ignore - the tree could not be clean, and the evidence trail was unversioned by
    accident. Control (i) of D-2676: this returns the faults, so a control can be SEEN to fire on a synthetic
    tree without touching this repository's dirt.
    """
    faults: list[str] = []
    allow = [str(g) for g in grants]
    n_granted = n_excluded = 0
    for st, path in dirty:
        if any(fnmatch.fnmatch(path, g) for g in allow):
            n_granted += 1
            continue
        hit = [e for e in excluded
               if isinstance(e, dict) and fnmatch.fnmatch(path, str(e.get("pattern")))]
        if hit and is_ignored(path):
            n_excluded += 1
            continue
        faults.append(dirty_msg(st, path))
    for e in excluded:
        if not isinstance(e, dict):
            continue
        pat = str(e.get("pattern"))
        if not is_ignored(ignore_probe_path(pat)):
            faults.append("declared-excluded '" + pat + "' is NOT ignored by git (probe '"
                          + ignore_probe_path(pat) + "'): the declaration claims an exclusion this repository "
                          "does not make - fix the declaration or the .gitignore bytes (D-405/BUG-563)")
    return faults, n_granted, n_excluded


def worktree_main(cfg: dict[str, Any]) -> int:
    """The LIVE run: join BOTH declared homes to git's own verdicts over the real dirty set (BUG-563)."""
    w = cfg.get("worktree") or {}
    plan_rel = str(w.get("plan") or "")
    if not plan_rel:
        print("FAIL repo-integrity worktree: config/repo_integrity.yaml#worktree.plan is not declared - the "
              "GRANTING home is unknown, so nothing can be classified (C16, fail closed)")
        return int((cfg.get("exit_codes") or {}).get("fail", 1))
    plan = yaml.safe_load((REPO / plan_rel).read_text(encoding="utf-8")) or {}
    grants = [str(x) for x in (plan.get("may_touch") or [])]
    excluded = list(w.get("excluded") or [])

    def is_ignored(p: str) -> bool:
        """git's OWN answer about one path - the only authority on what this repository ignores."""
        return git("check-ignore", "-q", "--no-index", p)[0] == 0

    dirty = dirty_entries()
    faults, n_granted, n_excluded = worktree_faults(dirty, grants, excluded, is_ignored)
    codes = cfg.get("exit_codes") or {"ok": 0, "fail": 1}
    if faults:
        print("FAIL repo-integrity worktree: " + str(len(faults)) + " path(s)/declaration(s) have NO declared "
              "home (BUG-563) - a dirty path must be GRANTED by " + plan_rel + " or declared-excluded:")
        for f in faults:
            print("   ", f)
        return int(codes["fail"])
    print("ok repo-integrity worktree: " + str(len(dirty)) + " dirty path(s) - " + str(n_granted)
          + " granted by " + plan_rel + ", " + str(n_excluded) + " declared-excluded (each joined to git's own "
          "ignore verdict), 0 in neither home")
    return int(codes["ok"])


def worktree_selftest() -> int:
    """Known-answer controls for the BUG-563 rule (BUG-492: a control that cannot fire is a comment).

    The ignore verdict is an INPUT, so every control is SYNTHETIC and none depends on this repository's current
    dirt: a control that can only pass while the live tree happens to be clean is not a control. The LIVE join to
    git's own verdicts is performed by --worktree, which the ladder runs. The exclusion FIXTURE is the live
    declaration's own first pattern, so this control and the declaration cannot drift apart (C12d).
    """
    cfg = load_config()
    excluded = [e for e in ((cfg.get("worktree") or {}).get("excluded") or []) if isinstance(e, dict)]
    if not excluded:
        print("FAIL repo-integrity selftest: config/repo_integrity.yaml#worktree.excluded is empty - the rule has "
              "no declared exclusion to be tested against (BUG-563)")
        return 1
    fixture = [dict(excluded[0])]
    pat = str(fixture[0].get("pattern"))
    sample = pat.replace("**", "one") if "**" not in pat else pat.replace("**", "one")
    probe = ignore_probe_path(pat)
    clean_exc = [{"pattern": "nothing/declared/*", "why": "selftest: a pattern that matches no case here"}]
    cases: list[tuple[str, list[tuple[str, str]], list[str], list[dict[str, Any]], set[str], bool]] = [
        ("an undeclared dirty path is a FAULT",
         [("??", "governance/UNKNOWN.json")], [], [], set(), True),
        ("a dirty path GRANTED by may_touch is NOT a fault",
         [("??", "governance/UNKNOWN.json")], ["governance/*.json"], [], set(), False),
        ("a dirty path DECLARED EXCLUDED and ignored by git is NOT a fault",
         [("??", sample)], [], fixture, {sample, probe}, False),
        ("a declaration git does NOT honour is a FAULT (the D-405 join)",
         [("??", sample)], [], fixture, {sample, sample}, True),
        ("a MIXED tree counts BOTH homes and faults neither",
         [(" M", "governance/UNKNOWN.json"), ("??", sample)], ["governance/UNKNOWN.json"], fixture,
         {sample, probe}, False),
    ]
    ok, n = True, 0
    for label, dirty, grants, exc, ignored, want in cases:
        n += 1
        faults, _g, _e = worktree_faults(dirty, grants, exc, lambda p, s=ignored: p in s)
        if bool(faults) != want:
            print("FAIL repo-integrity selftest: " + label + " - the rule said " + repr(bool(faults))
                  + " for " + repr(dirty) + " (faults: " + "; ".join(faults) + ")")
            ok = False
    n += 1
    faults, ng, ne = worktree_faults([(" M", "governance/UNKNOWN.json"), ("??", sample)],
                                     ["governance/UNKNOWN.json"], fixture, lambda p: p in {sample, probe})
    if (ng, ne) != (1, 1):
        print("FAIL repo-integrity selftest: the two homes are not COUNTED separately - granted=" + str(ng)
              + " excluded=" + str(ne) + " (a count that cannot be wrong is not a measurement)")
        ok = False
    if ok:
        print("ok repo-integrity worktree selftest: " + str(n) + " known-answer control(s) fire on BOTH homes "
              "and on the git join")
        return 0
    return 1


def selftest() -> int:
    """Known-answer controls for the repair vocabulary (BUG-492: a control must be SEEN to fire).

    Control 1 IS the measured BUG-541 regression: before the fix it raised IsADirectoryError.
    """
    cfg = load_config()
    pattern = re.compile(cfg["conflict_marker"]["patterns"][0])
    name = "probe (fixture conflicted copy selftest)"
    ok = True
    n = 0
    if not pattern.search(name):
        print("FAIL repo-integrity selftest: the config conflict_marker pattern does not match the fixture "
              "name - the control's vocabulary drifted from the config (BUG-492)")
        ok = False
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        cc = t / name
        cc.write_bytes(b"gitdir: /somewhere/outside\n")
        cases: list[tuple[str, dict[str, Any], str]] = []
        d = t / "pre_fix_layout"
        d.mkdir()
        cases.append(("a canonical name that is a DIRECTORY is OWNER_OWED, not a traceback", _row(cc, d),
                      "OWNER_OWED"))
        dsub = t / "superset_eligible"
        dsub.mkdir()
        cases.append(("a DIRECTORY never wins a superset claim", _row(cc, dsub, in_git=True,
                      git_rel=(cfg["repair"].get("prefer_superset_prefixes") or [""])[0]), "OWNER_OWED"))
        ident = t / "identical_other"
        ident.write_bytes(cc.read_bytes())
        cases.append(("byte-identical copy is VAULT", _row(cc, ident), "VAULT"))
        diff = t / "diverging_other"
        diff.write_bytes(b"something else\n")
        cases.append(("a diverging copy is OWNER_OWED", _row(cc, diff), "OWNER_OWED"))
        cases.append(("a missing canonical is RESTORE_ONLY_COPY", _row(cc, t / "not_there"),
                      "RESTORE_ONLY_COPY"))
        transient = (cfg["repair"].get("transient_git_paths") or ["COMMIT_EDITMSG"])[0]
        cases.append(("a missing transient git file is VAULT", _row(cc, t / transient, in_git=True), "VAULT"))
        sup_canon = t / "superset_canon"
        sup_canon.write_bytes(b"line1\n")
        sup_cc = t / ("superset " + name)
        sup_cc.write_bytes(b"line1\nline2\n")
        cases.append(("a canonical that is a byte-prefix is RESTORE_SUPERSET",
                      _row(sup_cc, sup_canon, in_git=True,
                           git_rel=(cfg["repair"].get("prefer_superset_prefixes") or [""])[0]),
                      "RESTORE_SUPERSET"))
        for label, row, want in cases:
            n += 1
            got = verdict(cfg, row)
            if got != want:
                print("FAIL repo-integrity selftest: " + label + " - the meter said " + repr(got)
                      + " instead of " + repr(want))
                ok = False
        # the report path must be total too (it read bytes inline before the fix)
        word = _content_word(_row(cc, d))
        n += 1
        if "UNCOMPARABLE" not in word:
            print("FAIL repo-integrity selftest: the report path said " + repr(word)
                  + " for a directory canonical instead of UNCOMPARABLE")
            ok = False
        # BUG-576, FOUR controls. A rule about a repository can only be tested by RUNNING it in one (BUG-574),
        # so each control builds a REAL repository with git and drives the SHIPPING functions - head_state(),
        # resolve_git_dir() and checks() - never a lookalike. BUG-577: the builder now has ONE home
        # (scripts/lib/fixture.py#real_repo) and the inline copy that used to live here is DELETED; the identity
        # and the message are THIS control's own facts and are passed IN, so the shared builder declares no
        # caller's vocabulary (C12d).
        _ident, _msg = ("repo-integrity-selftest@localhost", "repo-integrity-selftest"), "repo-integrity selftest"

        def _fixture(name: str, *, commit: bool) -> Path | None:
            """A real repository built by the ONE home (BUG-577); None when git refused (never a pass, BUG-492)."""
            return fixture.real_repo(t, name, commit=commit, identity=_ident, message=_msg)

        fresh = _fixture("unborn", commit=False)
        born = _fixture("born", commit=True)
        neither = _fixture("neither", commit=False)
        if fresh is None or born is None or neither is None:
            print("FAIL repo-integrity selftest: git refused to build a fixture repository - the BUG-576 "
                  "controls could not run (a control that cannot run is never a pass)")
            ok = False
        else:
            (neither / ".git" / "HEAD").write_text("0" * 40 + chr(10), encoding="utf-8")
            for label, root, want_state, why in [
                    ("unborn_head_is_accepted", fresh, "unborn",
                     "a FRESH repository - HEAD names a branch with no commit yet, the state the BUG-400/BUG-564 "
                     "RECOVERY route produces - must be ACCEPTED by every probe, not called broken metadata"),
                    ("unborn_branch_does_not_swallow_born", born, "born",
                     "a repository WITH a commit must read BORN: the UNBORN rule must not excuse a probe in it"),
                    ("head_that_is_neither_is_broken", neither, "broken",
                     "a HEAD that resolves to nothing is the P0-A defect, and the UNBORN rule must not hide it")]:
                n += 1
                gdir = resolve_git_dir(cfg, root)
                st = head_state(cfg, root)[0] if gdir else "no git dir"
                fails = checks(cfg, gdir, [], root=root)[0] if gdir else []
                if gdir is None or st != want_state:
                    print("FAIL repo-integrity selftest/" + label + ": the rail read HEAD as " + repr(st)
                          + " instead of " + repr(want_state) + " - " + why)
                    ok = False
                elif want_state == "broken" and not [f for f in fails if "NEITHER born nor UNBORN" in f]:
                    print("FAIL repo-integrity selftest/" + label + ": a broken HEAD reported no NEITHER born "
                          "nor UNBORN defect - the state is detected but nothing is SAID: " + why)
                    ok = False
                elif want_state != "broken" and fails:
                    print("FAIL repo-integrity selftest/" + label + ": " + repr(want_state) + " is INTACT but "
                          "the rail reports " + str(len(fails)) + " defect(s), first: " + fails[0][:140])
                    ok = False
            # TWO-SIDED: the UNBORN state must be SAID where it holds and NEVER where it does not - a skip the
            # report does not name is indistinguishable from a probe that passed.
            n += 1
            said_unborn = any("UNBORN" in x for x in checks(cfg, resolve_git_dir(cfg, fresh), [], root=fresh)[2])
            said_born = any("UNBORN" in x for x in checks(cfg, resolve_git_dir(cfg, born), [], root=born)[2])
            if not said_unborn or said_born:
                print("FAIL repo-integrity selftest/unborn_state_is_named: an unborn repository must SAY so "
                      "(said=" + str(said_unborn) + ") and a born one must never (said=" + str(said_born) + ") - "
                      "the UNBORN rule must not become a blanket excuse")
                ok = False
            # THE DIFFERENTIAL (the counterweight): in a BORN repository whose reflog was renamed away - the
            # 2026-09-25 accident this rail exists for - the reflog probe must STILL fail.
            n += 1
            (resolve_git_dir(cfg, born) / str(cfg["git"]["head_reflog_relpath"])).unlink()
            renamed = checks(cfg, resolve_git_dir(cfg, born), [], root=born)[0]
            if not [f for f in renamed if "is MISSING" in f]:
                print("FAIL repo-integrity selftest/renamed_reflog_in_a_born_repo_still_fails: the reflog of a "
                      "BORN repository was renamed away and the rail reported " + repr(renamed[:1]) + " - the "
                      "UNBORN rule (BUG-576) must not weaken the 2026-09-25 detection (C16)")
                ok = False
    # BUG-568, the PIN - measured before it: a decoy ambient subject CERTIFIED, and --selftest CRASHED.
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        _ident, _msg = ("repo-integrity-pin@localhost", "repo-integrity-pin"), "repo-integrity pin selftest"
        decoy = fixture.real_repo(t, "decoy_subject", commit=True, identity=_ident, message=_msg)
        broken = fixture.real_repo(t, "pin_broken", commit=False, identity=_ident, message=_msg)
        if decoy is None or broken is None:
            print("FAIL repo-integrity selftest/rail0_pins_its_own_subject: git refused to build the DECOY or "
                  "BROKEN fixture - a control that cannot run is never a pass (BUG-492)")
            ok = False
        else:
            n += 1
            me = [sys.executable, str(Path(__file__).resolve())]
            clean = {k: v for k, v in os.environ.items()
                     if k not in git_subject.guard_vars(git_subject.config())}
            decoy_env = dict(clean, GIT_DIR=str(decoy / ".git"), GIT_WORK_TREE=str(decoy))
            own = git_subject.discover(git_subject.config()).git_dir
            hook_env = dict(clean, GIT_DIR=own, GIT_INDEX_FILE=os.path.join(own, "index"))

            def _rail(argv: list[str], env: dict[str, str]) -> tuple[int, str]:
                r = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, env=env)
                return r.returncode, r.stdout + r.stderr

            rc_clean, out_clean = _rail(me, clean)
            rc_decoy, out_decoy = _rail(me, decoy_env)
            rc_doc, out_doc = _rail(me + ["--selftest"], decoy_env)
            rc_hook, out_hook = _rail(me, hook_env)
            bad: list[str] = []
            if rc_clean != 0:
                bad.append("anti-vacuity: the SAME command with NO ambient guard values is rc " + str(rc_clean)
                           + ", so a red here would prove nothing about the decoy")
            if not (rc_decoy == 1 and "REFUSED git-subject" in out_decoy and "ok repo-integrity" not in out_decoy):
                bad.append("a DECOY GIT_DIR was NOT refused: rc=" + str(rc_decoy) + " out="
                           + out_decoy.strip()[:140])
            if not (rc_hook == 0 and "note repo-integrity: " in out_hook and own in out_hook):
                bad.append("the HOOK'S OWN ambient values (GIT_DIR=" + own + " + its index) were not TOLERATED and "
                           "NAMED: rc=" + str(rc_hook) + " - a rule that refuses every commit is not a rule "
                           "(BUG-574), and a note that names no subject is the lie BUG-567 closed")
            if not (rc_doc == 1 and "REFUSED" in out_doc and "Traceback" not in out_doc):
                bad.append("the decoy CRASHED --selftest instead of being refused: rc=" + str(rc_doc) + " tail="
                           + out_doc.strip()[-200:])
            if bad:
                print("FAIL repo-integrity selftest/rail0_pins_its_own_subject: " + " | ".join(bad))
                ok = False
            # TOLERANCE, two-sided: a BROKEN repository is REPORTED (never refused) while an INTACT one still pins.
            n += 1
            os.rename(str(broken / ".git"), str(broken / "gitdir_renamed_away"))
            subj_here, _n1 = git_subject.recovery_subject(environ={})
            subj_broken, note_broken = git_subject.recovery_subject(environ={}, root=broken)
            if not (subj_here is not None and subj_here.git_dir == os.path.realpath(own)
                    and subj_broken is None and "NO SUBJECT PINNED" in note_broken
                    and resolve_git_dir(cfg, broken) is None):
                print("FAIL repo-integrity selftest/a_broken_repository_is_reported_not_refused: the tolerant pin "
                      "must (a) PIN an intact repository (got " + repr(bool(subj_here)) + "), (b) return NO subject "
                      "for one whose git metadata was renamed away (got " + repr(subj_broken) + ", note="
                      + note_broken[:80] + "), and (c) let the rail's own probe REPORT it (resolve_git_dir=None) "
                      "- the recovery rail cannot fail closed on the condition it exists to name")
                ok = False
    # BUG-547, two-sided control: the archive rule must excuse its OWN history and nothing else.
    n += 1
    if not archived_under("archive/conflicted_20260926/",
                          "archive/conflicted_20260926/buglog (M1 max's conflicted copy 2026-09-26).md"):
        print("FAIL repo-integrity selftest: an ARCHIVED sibling was reported as a live finding (BUG-547)")
        ok = False
    n += 1
    if archived_under("archive/conflicted_20260926/",
                      "governance/buglog (M1 max's conflicted copy 2026-09-26).md"):
        print("FAIL repo-integrity selftest: a LIVE sibling was excused as archived (the archive rule overreaches)")
        ok = False
    if ok:
        print(f"ok repo-integrity selftest: {n} known-answer control(s)")
        return 0
    return 1


def main() -> int:
    """Evaluate every probe and report; exit per config.repo_integrity.exit_codes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print the deterministic repair as mv commands")
    ap.add_argument("--quiet", action="store_true", help="print one summary line only (for rails)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls; no repo access")
    ap.add_argument("--worktree", action="store_true",
                    help="audit the DIRTY WORKTREE against its two declared homes (BUG-563; never the "
                         "staged set, which is rail 4's subject)")
    a = ap.parse_args()
    # BUG-568: the subject is derived BEFORE any mode reads a repository, so no mode of this rail can run under a
    # subject nobody declared (a decoy is refused in EVERY mode, --selftest included: MEASURED before this fix,
    # that mode crashed with a traceback while the decoy's git dir was being used to build its own fixtures).
    print("note repo-integrity: " + subject_bits()[1])
    if a.selftest:
        rc = worktree_selftest()
        return selftest() or rc
    cfg = load_config()
    if a.worktree:
        return worktree_main(cfg)
    git_dir = resolve_git_dir(cfg)
    rows = scan(cfg, git_dir)
    if a.plan:
        print_plan(cfg, rows)
        return 0
    state, ref = head_state(cfg)
    fails, owed, notes = checks(cfg, git_dir, rows)
    codes = cfg.get("exit_codes") or {"ok": 0, "fail": 1, "owner_owed": 2}
    if fails:
        print(f"FAIL repo-integrity: {len(fails)} repository integrity defect(s):")
        for f in fails:
            print("   ", f)
    if owed:
        print(f"owner_owed repo-integrity: {len(owed)} conflict copy/copies (bytes intact, disposition owed):")
        for o in owed:
            print("   ", o)
    if not fails and not owed:
        subject = (f"UNBORN: HEAD names {ref} with no commit yet - a fresh or freshly RECOVERED repository, "
                   f"INTACT (BUG-576)" if state == "unborn"
                   else f"HEAD resolves and {cfg['git']['head_reflog_relpath']} agrees")
        print(f"ok repo-integrity: git dir {git_dir}, {subject}, 0 conflict-marked names in 2 sweeps")
        return int(codes["ok"])
    if fails:
        return int(codes["fail"])
    return int(codes["owner_owed"])


if __name__ == "__main__":
    sys.exit(main())
