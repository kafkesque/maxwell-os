"""Resolve Dropbox conflicted copies so every artifact has ONE live source of truth.

MEASURED 2026-09-26: Dropbox created 36 conflicted-copy siblings in this tree and reverted the
live file to an older blob. 26 copies held NEWER work than the live file - one of them the whole
D-2645/D-2646 rail work, one the wired justfile. A live artifact that reverts under a rail is
indistinguishable from silent drift, so every rail that read one of those files read a stale tree
and still printed ok.

Resolution order is MEASURED, never guessed:
  1. identical to the INDEX  -> the index holds it; git checkout -- <path> is lossless
  2. identical to HEAD       -> the copy is the committed mark; the live file is the work
  3. otherwise               -> git merge-file, a real 3-way merge with base = the HEAD blob
Anything that still carries conflict markers is NOT written; it is recorded for the owner.

DRY RUN by default: --apply is required to move a byte (C6). --check is read-only (it writes no register) and
is what `just health` runs, so a reverted live file can never again pass silently.

TRI-STATE (BUG-457/BUG-492): 0 no sibling (one live artifact per path) | 1 a sibling the MEASURED rule proves
resolvable is still unapplied | 2 owner-owed only (a sibling only the owner can settle). A resolver that always
exits 0 is a register that can never fire.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

NL = chr(10)
ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "config" / "conflict_policy.yaml"


def sha16(data: bytes) -> str:
    """Short content hash used to compare two artifacts by what they ARE."""
    return hashlib.sha256(data).hexdigest()[:16]


def git_blob(ref: str, rel: str) -> bytes | None:
    """The blob at ref:rel, or None when git does not carry that path."""
    spec = (ref + ":" if ref else ":") + rel
    r = subprocess.run(["git", "show", spec], capture_output=True, cwd=str(ROOT))
    return r.stdout if r.returncode == 0 else None


def live_of(copy: Path, marker: str) -> Path:
    """The live path a conflicted copy shadows. Name surgery, no regex."""
    n = copy.name
    i = n.find(marker)
    if i < 0:
        return copy
    j = n.find(")", i)
    return copy.with_name(n[:i] + n[j + 1:])


def merge_file(ours: bytes, base: bytes, theirs: bytes) -> tuple[int, bytes]:
    """3-way merge with the same engine git and Dropbox use. rc>0 counts conflicting hunks."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "ours").write_bytes(ours)
        (p / "base").write_bytes(base)
        (p / "theirs").write_bytes(theirs)
        r = subprocess.run(["git", "merge-file", "-p", "ours", "base", "theirs"],
                           capture_output=True, cwd=td)
        return r.returncode, r.stdout


def atomic_write(path: Path, data: bytes) -> None:
    """tempfile -> fsync -> os.replace (C6): a merge that dies may not leave half a file."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def archive_copy(copy: Path, archive: Path) -> None:
    """Move the resolved sibling out of the tree. Never deleted, always recoverable."""
    archive.mkdir(parents=True, exist_ok=True)
    dest = archive / copy.name
    if dest.exists():
        dest = archive / (copy.name + "." + sha16(copy.read_bytes()))
    shutil.move(str(copy), str(dest))


def resolve(policy: dict, apply: bool) -> list[tuple[str, str, str, str]]:
    """Classify every sibling and, when apply, resolve the provable ones."""
    marker = policy["name_marker"]
    archive = ROOT / policy["archive_dir"]
    never = tuple(policy["never_touch"])
    rows: list[tuple[str, str, str, str]] = []
    # MEASURED 2026-09-26: an ARCHIVED sibling is a fixed point - it is a record of a resolution that already
    # happened, so re-reporting it as NO-LIVE/'held' drowned the register in rows that no longer describe a live
    # divergence and made the run non-idempotent (36 rows of which 22 were the archive talking to itself).
    arch_rel = str(policy["archive_dir"]).rstrip("/") + "/"
    copies = sorted(p for p in ROOT.rglob("*conflicted copy*")
                    if "/.git/" not in str(p)
                    and not p.relative_to(ROOT).as_posix().startswith(arch_rel))
    for copy in copies:
        rel = copy.relative_to(ROOT).as_posix()
        live = live_of(copy, marker)
        lrel = live.relative_to(ROOT).as_posix()
        if any(rel.startswith(n) or lrel.startswith(n) for n in never):
            rows.append((lrel, "OWNER:pipeline-state", "never text-merged", "held"))
            continue
        if not live.exists():
            rows.append((lrel, "NO-LIVE", "the copy is the only artifact", "held"))
            continue
        cb, lb = copy.read_bytes(), live.read_bytes()
        if copy.suffix == ".pyc":
            rows.append((lrel, "BUILD-ARTIFACT", "no compiled file belongs in the repo (C19)",
                         "archived" if apply else "would-archive"))
            if apply:
                archive_copy(copy, archive)
            continue
        if sha16(cb) == sha16(lb):
            rows.append((lrel, "IDENTICAL", "same bytes: the sibling is pure duplication",
                         "archived" if apply else "would-archive"))
            if apply:
                archive_copy(copy, archive)
            continue
        idx = git_blob("", lrel)
        head = git_blob("HEAD", lrel)
        if idx is not None and sha16(cb) == sha16(idx):
            rows.append((lrel, "RESTORE-FROM-INDEX", "conflicted == index: recovery is lossless",
                         "restored" if apply else "would-restore"))
            if apply:
                subprocess.run(["git", "checkout", "--", lrel], cwd=str(ROOT))
                archive_copy(copy, archive)
            continue
        if head is not None and sha16(cb) == sha16(head):
            rows.append((lrel, "COPY-IS-HEAD", "the sibling is the committed mark: live wins",
                         "archived" if apply else "would-archive"))
            if apply:
                archive_copy(copy, archive)
            continue
        base = head if head is not None else idx
        if base is None:
            rows.append((lrel, "UNTRACKED-DIVERGED", "no git base: owner judgement", "held"))
            continue
        rc, merged = merge_file(lb, base, cb)
        if rc == 0:
            rows.append((lrel, "3-WAY-CLEAN", "merged " + str(len(merged)) + " bytes",
                         "merged" if apply else "would-merge"))
            if apply:
                atomic_write(live, merged)
                archive_copy(copy, archive)
        else:
            lset = set(lb.decode("utf-8", "replace").splitlines())
            cset = set(cb.decode("utf-8", "replace").splitlines())
            if not (lset - cset) or not (cset - lset):
                # MEASURED fallback (git found overlapping hunks, but the artifacts disagree about
                # nothing): every line of one side survives in the other, so no side lost work. An
                # append-only artifact is SUPERSEDED, never merged - adopt the side carrying the
                # other's lines and hold only a genuine two-sided divergence.
                winner, wname = (cb, "COPY-SUPERSET") if not (lset - cset) else (lb, "LIVE-SUPERSET")
                rows.append((lrel, wname, "one side is a line-superset: no work is lost",
                             "merged" if apply else "would-merge"))
                if apply:
                    atomic_write(live, winner)
                    archive_copy(copy, archive)
            else:
                rows.append((lrel, "CONFLICT:" + str(rc), "hunks need a human - NOT written", "held"))
    return rows


def write_register(rows: list[tuple[str, str, str, str]], apply: bool, register: Path) -> None:
    """The owner-visible record: what was resolved, how, and what is still held."""
    head = "# Dropbox conflict register" + NL + NL
    head += ("Mode: " + ("APPLY" if apply else "DRY RUN") + " | decided D-2647 | "
             "one live artifact, one source of truth. The resolution rule is measured, never "
             "guessed: index > head > 3-way merge (git merge-file)." + NL + NL)
    head += "| live path | verdict | why | action |" + NL + "|---|---|---|---|" + NL
    body = "".join("| " + r[0] + " | " + r[1] + " | " + r[2] + " | " + r[3] + " |" + NL for r in rows)
    atomic_write(register, (head + body).encode())


EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
RESOLVABLE: tuple[str, ...] = ("would-archive", "would-restore", "would-merge")


def verdict_code(rows: list[tuple[str, str, str, str]], apply: bool) -> int:
    """Encode the tree's state in the exit code (BUG-457): the one thing that makes health able to refuse.

    MEASURED 2026-09-26: the first version returned 0 in every mode, so wiring it into a rail would have added
    a line that can never fail - a register that cries nothing (BUG-492). DRIFT outranks OWNER-OWED, because a
    resolvable sibling is a defect a machine already decided how to fix.
    """
    if not rows:
        return EXIT_CLEAN
    if not apply and any(r[3] in RESOLVABLE for r in rows):
        return EXIT_DRIFT
    if any(r[3] == "held" for r in rows):
        return EXIT_OWED
    return EXIT_CLEAN


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the tri-state rule (BUG-492: a detector never seen failing is not one)."""
    def row(action: str) -> tuple[str, str, str, str]:
        return ("live.md", action, "why", action)

    return [
        ("no sibling is CLEAN: one live artifact per path",
         verdict_code([], False) == EXIT_CLEAN),
        ("a resolvable sibling that is still unapplied is DRIFT (a reverted live file cannot pass)",
         verdict_code([row("would-merge")], False) == EXIT_DRIFT),
        ("DRIFT outranks OWNER-OWED when both are present",
         verdict_code([row("would-merge"), row("held")], False) == EXIT_DRIFT),
        ("siblings only the owner can settle are OWNER-OWED, never DRIFT",
         verdict_code([row("held")], False) == EXIT_OWED),
        ("after --apply a held sibling still reports OWNER-OWED",
         verdict_code([row("merged"), row("held")], True) == EXIT_OWED),
        ("after --apply with nothing held the tree is CLEAN",
         verdict_code([row("merged")], True) == EXIT_CLEAN),
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Resolve Dropbox conflicted copies (dry run by default)")
    ap.add_argument("--apply", action="store_true", help="resolve the provable ones (C6)")
    ap.add_argument("--check", action="store_true",
                    help="read-only: report the state, write nothing, exit tri-state (BUG-457)")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls (BUG-492)")
    a = ap.parse_args(argv)
    if a.selftest:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [name for name, ok in rows if not ok]
        if failed:
            print("FAIL dropbox-conflicts: " + str(len(failed)) + " of " + str(len(rows))
                  + " known-answer control(s) did not fire")
            return EXIT_DRIFT
        print("ok dropbox-conflicts: " + str(len(rows)) + "/" + str(len(rows))
              + " known-answer control(s) fire")
        return EXIT_CLEAN
    if a.apply and a.check:
        raise SystemExit("FAIL-CLOSED (dropbox-conflicts): --apply and --check contradict (one moves bytes, one "
                         "must not) - refusing rather than picking one")
    policy = yaml.safe_load(POLICY.read_text())
    rows = resolve(policy, a.apply)
    if not a.check:
        write_register(rows, a.apply, ROOT / policy["register"])
    w = max(len(r[0]) for r in rows) if rows else 10
    print(("APPLY" if a.apply else "CHECK" if a.check else "DRY RUN") + ": " + str(len(rows)) + " sibling(s)")
    for r in sorted(rows, key=lambda x: x[1]):
        print("  " + r[0].ljust(w) + " | " + r[1].ljust(20) + " | " + r[3])
    if not rows:
        print("ok dropbox-conflicts: 0 conflicted-copy sibling(s) - one live artifact per path")
    return verdict_code(rows, a.apply)


if __name__ == "__main__":
    raise SystemExit(main())
