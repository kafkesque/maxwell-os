#!/usr/bin/env python3
"""check_declaration_consumers.py - the CONSUMER JOIN: a declaration and the code that reads it are ONE object (D-2669).

WHY (the class, not the instance). BUG-562: config/serving_gate.yaml (a GRANTED artifact) landed while
pipeline/serving_gate.py - the ONLY code that reads it - was withheld as will_not_touch. Nothing REFUSED that commit
set; the property held only because a session looked. D-405 joins a claim to the bytes it describes; this rail joins
a declaration to the CODE that consumes it, at the moment a commit would split them.

TWO MOMENTS, ONE HOME (the RAIL 3 precedent, config/recalibration_pins.yaml + config/declaration_consumers.yaml):
  * --staged - the WRITE moment (gitdir:hooks/pre-commit): a STAGED declaration whose declared consumer is in NEITHER
    HEAD NOR the index has a WITHDRAWN CONSUMER -> rc=1 and the commit is refused. Worktree existence is deliberately
    NOT enough: the BUG-562 state was a consumer that EXISTED and was untracked.
  * default  - the STATE moment (the ladder): every declaration and every consumer must EXIST on disk, and a
    declaration that genuinely has no consumer must say so with exempt_reason.
NOT overreaching: a staged path the registry does not name is tolerated, and a consumer already in HEAD is not
withheld. There is NO "the consumer lands later" escape - the escape is: do not stage the declaration.

Exit: 0 ok | 1 fault(s) | 2 the registry is unreadable/incomplete, or the audited subject was INHERITED (C16/BUG-527).
Usage: python3 scripts/check_declaration_consumers.py [--staged] [--index-file P] [--registry P] [--selftest]
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/declaration_consumers.yaml"


def _git(root: pathlib.Path, args: list[str], index_file: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    """Run git against root. GIT_INDEX_FILE is NEVER inherited: the audited subject is not inherited (BUG-527)."""
    env = {k: v for k, v in os.environ.items() if k != "GIT_INDEX_FILE"}
    if index_file is not None:
        env["GIT_INDEX_FILE"] = str(index_file)
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env=env)


def staged_set(root: pathlib.Path, index_file: pathlib.Path | None = None) -> set[str]:
    """The staged paths (the commit set) from the index the CALLER names - never from the environment."""
    r = _git(root, ["diff", "--cached", "--name-only"], index_file)
    return {ln for ln in r.stdout.splitlines() if ln.strip()} if r.returncode == 0 else set()


def in_head(root: pathlib.Path, path: str, index_file: pathlib.Path | None = None) -> bool:
    """True iff the path has bytes in HEAD: a claim over HEAD bytes survives a checkout, one over untracked does not."""
    return _git(root, ["cat-file", "-e", "HEAD:" + path], index_file).returncode == 0


def in_index(root: pathlib.Path, path: str, index_file: pathlib.Path | None = None) -> bool:
    """True iff the path is in the (possibly named) index: staged means it lands in THIS commit."""
    return _git(root, ["ls-files", "--error-unmatch", "--", path], index_file).returncode == 0


def load(path: pathlib.Path) -> list[dict]:
    """Fail closed (C16): a registry that is not a mapping of edges is never a silent empty set."""
    if not path.is_file():
        raise SystemExit("FAIL-CLOSED: " + str(path) + " is absent - a consumer join with no registry decides nothing")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("declarations"), list):
        raise SystemExit("FAIL-CLOSED: " + str(path) + " has no declarations list - fail closed, never green")
    edges: list[dict] = []
    for i, e in enumerate(doc["declarations"], start=1):
        if not isinstance(e, dict) or not str(e.get("declaration") or "").strip():
            raise SystemExit("FAIL-CLOSED: declarations entry #" + str(i) + " names no declaration")
        if not isinstance(e.get("consumers"), list):
            raise SystemExit("FAIL-CLOSED: declarations entry #" + str(i) + " has no consumer list (use [] plus exempt_reason)")
        edges.append({"declaration": str(e["declaration"]), "consumers": [str(c) for c in e["consumers"]],
                      "why": str(e.get("why") or ""), "exempt_reason": str(e.get("exempt_reason") or "")})
    if not edges:
        raise SystemExit("FAIL-CLOSED: the registry declares ZERO edges - a control that cannot fire (BUG-492)")
    return edges


def verdicts(root: pathlib.Path, edges: list[dict], staged: set[str] | None = None,
             index_file: pathlib.Path | None = None) -> tuple[list[str], list[str]]:
    """Join each declaration to its consumers, and - in staged mode - to the COMMIT SET that would carry it."""
    faults: list[str] = []
    notes: list[str] = []
    n_consumers = 0
    for e in edges:
        decl, cons = e["declaration"], e["consumers"]
        if not (root / decl).is_file():
            faults.append("declared home " + decl + " DOES NOT EXIST - a declaration whose subject is absent is an "
                          "assertion, not a declaration (D-405/BUG-488)")
        if not cons:
            if not e["exempt_reason"].strip():
                faults.append("declared home " + decl + " names NO consumer and no exempt_reason - consumers: [] must be "
                              "EXPLICIT (config/flag_consumer_registry.yaml vocabulary)")
            else:
                notes.append("declared home " + decl + " has no consumer, declared: " + e["exempt_reason"][:70])
            continue
        n_consumers += len(cons)
        for c in cons:
            if not (root / c).is_file():
                faults.append("declared home " + decl + " names consumer " + c + ", which DOES NOT EXIST on disk - a "
                              "declaration joined to nothing (D-405)")
        if staged is None or decl not in staged:
            continue
        withheld = [c for c in cons if not (in_head(root, c, index_file) or in_index(root, c, index_file))]
        if withheld:
            faults.append("WITHDRAWN CONSUMER (BUG-562): " + decl + " is STAGED but " + ", ".join(withheld) + " is in "
                          "NEITHER HEAD NOR the index - this commit would split the declaration from the only code that "
                          "reads it. Stage it in the SAME commit, or do not stage the declaration")
    if not faults:
        mode = "the commit set" if staged is not None else "the tree"
        notes.append("ok declaration consumers: " + str(len(edges)) + " declared home(s), " + str(n_consumers) +
                     " consumer edge(s) all resolve for " + mode)
    return faults, notes


def selftest() -> int:
    """Known-answer controls over a SYNTHETIC repo (no live-tree write, no inherited index - BUG-492/BUG-527)."""
    import tempfile

    ok = fail = 0

    def check(name: str, got: int, want: int, why: str) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
            print("  ok   " + name + " - " + why)
        else:
            fail += 1
            print("  FAIL " + name + ": got " + str(got) + ", want " + str(want) + " - " + why)

    def edge(**kw) -> list[dict]:
        e = {"declaration": "config/a.yaml", "consumers": ["pipeline/a.py"], "why": "fixture", "exempt_reason": ""}
        e.update(kw)
        return [e]

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "config").mkdir()
        (root / "pipeline").mkdir()
        (root / "config/a.yaml").write_text("a: 1\n", encoding="utf-8")
        (root / "pipeline/a.py").write_text("x = 1\n", encoding="utf-8")
        _git(root, ["init", "-q"])
        _git(root, ["add", "-A"])
        _git(root, ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"])
        check("clean_state", len(verdicts(root, edge())[0]), 0, "a declared home whose consumer exists is silent")
        check("consumer_absent", len(verdicts(root, edge(consumers=["pipeline/missing.py"]))[0]), 1,
              "a declaration naming a consumer that exists nowhere is a D-405 fault")
        check("declaration_absent", len(verdicts(root, edge(declaration="config/gone.yaml"))[0]), 1,
              "a declaration whose subject is absent (BUG-488)")
        check("empty_no_reason", len(verdicts(root, edge(consumers=[]))[0]), 1,
              "consumers: [] without exempt_reason is implied emptiness, not declared")
        check("empty_with_reason", len(verdicts(root, edge(consumers=[], exempt_reason="nothing reads it yet"))[0]), 0,
              "an explicit exempt_reason makes the emptiness a declaration")
        (root / "config/a.yaml").write_text("a: 2\n", encoding="utf-8")
        _git(root, ["add", "config/a.yaml"])
        st = staged_set(root)
        (root / "pipeline/c.py").write_text("z = 1\n", encoding="utf-8")   # exists on disk, UNTRACKED - the BUG-562 shape
        got = [x for x in verdicts(root, edge(consumers=["pipeline/c.py"]), staged=st)[0] if "WITHDRAWN" in x]
        check("staged_withheld_consumer", len(got), 1,
              "THE BUG-562 COMMIT SET: the declaration is staged and its consumer is in neither HEAD nor the index")
        (root / "pipeline/b.py").write_text("y = 1\n", encoding="utf-8")
        _git(root, ["add", "pipeline/b.py"])
        check("staged_paired", len(verdicts(root, edge(consumers=["pipeline/b.py"]), staged=staged_set(root))[0]), 0,
              "a consumer staged in the SAME commit is not withheld")
        check("head_covers", len(verdicts(root, edge(), staged=staged_set(root))[0]), 0,
              "a consumer already in HEAD is not withheld - the rail does not overreach")
        (root / "config/z.yaml").write_text("z: 1\n", encoding="utf-8")
        _git(root, ["add", "config/z.yaml"])
        check("no_overreach", len(verdicts(root, edge(), staged=staged_set(root))[0]), 0,
              "a staged artifact the registry does not name is tolerated (this is NOT a config census)")
        rc = 0
        try:
            load(root / "bad.yaml")
        except SystemExit:
            rc = 2
        check("fail_closed", rc, 2, "a registry that is not a mapping of edges is never a silent empty set (C16)")
        rc = 0
        try:
            load(root / "absent.yaml")
        except SystemExit:
            rc = 2
        check("fail_closed_absent", rc, 2, "an absent registry is a control that cannot fire (C16)")
    print("declaration-consumer controls: " + str(ok) + "/" + str(ok + fail) + " known-answer control(s) fire")
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the CONSUMER JOIN: no declaration without its reader (D-2669)")
    ap.add_argument("--staged", action="store_true", help="the WRITE moment: refuse a staged declaration whose consumer is withheld")
    ap.add_argument("--index-file", default=None, help="the DECLARED diagnostic index (BUG-527); never inherited")
    ap.add_argument("--registry", default=str(REGISTRY), help="the declared home of the edges")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over a synthetic repo (BUG-492)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if os.environ.get("GIT_INDEX_FILE") and not a.index_file:
        print("note declaration consumers: the index is the one git PASSED to this run ("
              + str(os.environ["GIT_INDEX_FILE"]) + ") - at the WRITE moment that IS the commit's subject, so it is "
              "accepted and NAMED; a DIAGNOSTIC run that inherits an index silently would be a different subject "
              "(BUG-527), so pass --index-file explicitly there")
    idx = pathlib.Path(a.index_file) if a.index_file else None
    try:
        edges = load(pathlib.Path(a.registry))
    except SystemExit as e:
        print(str(e))
        return 2
    staged = staged_set(ROOT, idx) if a.staged else None
    faults, notes = verdicts(ROOT, edges, staged, idx)
    for n in notes:
        print(n)
    if faults:
        print("FAIL declaration consumers: " + str(len(faults)) + " fault(s) - a declaration and its reader are ONE object (D-405):")
        for f in faults:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
