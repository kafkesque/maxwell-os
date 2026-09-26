#!/usr/bin/env python3
"""scripts/verify_recalibration_pins.py - the recalibration trigger (D-353).

Every artifact the abstention / classification measurement depends on is digest-pinned. If one changes
without a new decision id in config/decisions.yaml, the measurement on disk is stale and this goes RED.
This is the trigger whose absence caused BUG-391 (a ratified point measured on a reference that then
moved). Read-only, deterministic, no LLM.

A MOVED PIN IS OWNER-OWED, NOT FATAL (BUG-536; the BUG-457 tri-state). MEASURED 2026-09-26: this rail's
only exit was 1 and `just health` ran it with `|| exit 1`, so a moved pin ABORTED the ladder and hid eleven
rails (72-82) for a whole pass - the third instance of the same class (BUG-467, then D-382's own rationale,
which recorded "just health was RED for a whole pass while every individual rail was green"). An abort is an
amnesia generator: it hides its own successors, so the eleven rails that could have gone GREEN were never
run at all. The two cases are separated by the KIND of fact and the producer decides which it is:
  * FATAL (1) - the DECLARATION is broken: a pinned path that does not exist, or a decision id the registry
    does not carry. Nothing can be concluded about a measurement whose reference is missing (C16: fail closed).
  * OWED  (2) - the pin has fallen BEHIND the work. Only the owner can close it (re-measure, mint, re-pin),
    so it is DEBT, loud, and not fatal (BUG-457).
Nothing is loosened: the pre-commit hook still runs `--staged || exit 1`, so ANY non-zero - 1 or 2 - still
REFUSES the commit that would make a measurement unreproducible.

TWO MOMENTS, ONE HOME (BUG-526; the D-2649 pattern - a rule enforced at one moment only is half a rule):
  * SCAN  (no args)   - every pin vs disk vs registry. `just health` runs this.
  * WRITE (--staged)  - the STAGED set, i.e. the bytes that would BECOME PERMANENT. The pre-commit hook
    runs this through scripts/install_git_hooks.sh. MEASURED 2026-09-26: this invariant lived only at scan
    time, so a pinned artifact could be *edited* and the edit made permanent by a commit that never
    consulted the pin - the first moment anyone learned was the next `just health`, after the ratified
    measurement had already been invalidated in the tree. A rail that runs only when someone remembers to
    run it is not a rail during the interval in which the work happens.

The staged rule does NOT overreach: a commit that names no pinned artifact is TOLERATED even while the
tree is RED (the OVERREACH control, BUG-492). Only the commit that would make a pinned measurement
unreproducible is refused.

The pin declarations and their digests have exactly ONE home: config/recalibration_pins.yaml. This module
CONSUMES that home at both moments; it never restates it (D-2646).

Usage:  python3 scripts/verify_recalibration_pins.py [--staged] [--selftest]
Exit (tri-state, BUG-457/BUG-536): 0 = clean | 1 = a BROKEN pin declaration (a missing pinned path, or a
decision the registry does not carry): fail closed | 2 = a pinned artifact MOVED, so the OWNER owes the
re-measure and the re-mint. The WRITE gate (--staged) is a REFUSAL and returns 1 for either kind.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PINS = _ROOT / "config" / "recalibration_pins.yaml"
_PINS_REL = "config/recalibration_pins.yaml"
_RED = "RED  "
_OWED = "OWED "
# BUG-457/BUG-536 tri-state: 0 clean | 1 a BROKEN declaration (fail closed) | 2 the OWNER owes a re-mint.
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
_DECISION_FILES = ("config/decisions.yaml", "DECISION-LOG.md", "MASTER-TASK-REGISTER.md")
# D-2644/BUG-521: the encoding of every artifact this rail reads is DECLARED, never left to the platform.
_ENCODING = "utf-8"
# A sentinel that separates "the caller handed us no predecessor" from "there is no predecessor in HEAD": the
# first is an UNKNOWN (fail closed), the second is a first commit. It MUST sit above every signature that uses it
# as a default - a default is evaluated at def time, and this file's own rail caught that mistake (BUG-535).
_UNSET = object()


def digest(root: pathlib.Path, rel: str) -> str:
    """sha256 of a repo-relative file."""
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def decision_ids(root: pathlib.Path) -> set[str]:
    """Every decision id named by the registry, the log or the task register."""
    ids: set[str] = set()
    for rel in _DECISION_FILES:
        f = root / rel
        if f.exists():
            ids |= set(re.findall(r"(D-[0-9]+)", f.read_text(encoding=_ENCODING)))
    return ids


def scan_split(root: pathlib.Path, cfg: dict) -> tuple[list[str], list[str]]:
    """Every pin vs disk vs registry - the SCAN rule, SPLIT BY THE KIND OF FACT (BUG-536).

    Returns (fatal, owed). The PRODUCER decides the severity where the fault is created; there is no
    classifier downstream, so a fault cannot be re-graded by its wording (the BUG-526/528/531 family:
    enforcement by NAME instead of by IDENTITY).
      * fatal - the declaration itself is broken, so nothing can be concluded about the measurement it
        certifies (C16: fail closed).
      * owed  - the pin has fallen behind the work; only the owner can close it (re-measure, mint, re-pin).
    """
    ids = decision_ids(root)
    fatal: list[str] = []
    owed: list[str] = []
    for name, pin in cfg["pins"].items():
        p = root / pin["path"]
        if not p.exists():
            fatal.append(name + ": pinned path is missing: " + pin["path"])
            continue
        if digest(root, pin["path"]) != pin["sha256"]:
            owed.append(name + ": " + pin["path"] + " CHANGED since it was pinned - re-run the measurement and mint a new decision (this is the BUG-391 class)")
        if pin["decision"] not in ids:
            fatal.append(name + ": pinned to decision " + pin["decision"] + " which is not in config/decisions.yaml")
    return fatal, owed


def all_faults(root: pathlib.Path, cfg: dict) -> list[str]:
    """BOTH kinds, for the WRITE gate: a commit is refused by either (one producer, no restated wording)."""
    fatal, owed = scan_split(root, cfg)
    return fatal + owed


def staged_faults(cfg: dict, staged: list[str], blob, scan, head=_UNSET, tree_blob=None) -> list[str]:
    """
    The WRITE-time rule: refuse the commit that would make a pinned measurement unreproducible.

    `blob(rel)` returns the STAGED bytes (the bytes that would become permanent) or None when they cannot
    be read; `scan()` returns the SCAN rule's faults, needed because committing the pins file itself is a
    change to the declaration and must satisfy the whole invariant. Both are injected so the controls can
    hand this function a broken rule as easily as a legal document (BUG-492).
    """
    pinned = {pin["path"]: (name, pin) for name, pin in cfg["pins"].items()}
    faults: list[str] = []
    for rel in staged:
        if rel == _PINS_REL:
            faults += ["staged " + rel + " declares the pins themselves - every pin must hold for the commit to be legal: " + x for x in scan()]
            faults += _repin_faults(cfg, blob, head, tree_blob)
            continue
        if rel in pinned:
            name, pin = pinned[rel]
            raw = blob(rel)
            got = hashlib.sha256(raw).hexdigest() if raw is not None else None
            if got is None:
                faults.append("staged " + rel + " is pinned as '" + name + "' but its staged bytes could not be READ - an unknown is not a clean (fail closed)")
                continue
            if got != pin["sha256"]:
                faults.append(
                    "staged " + rel + " is pinned as '" + name + "' (decision " + pin["decision"] + ") and its staged bytes have MOVED: "
                    "the measurement that pin certifies is no longer reproducible from this commit. Re-run the measurement, mint a NEW "
                    "decision id, then record the new sha256 AND the new decision in " + _PINS_REL + " (the pin is the declaration home).")
    return faults


def _repin_faults(cfg: dict, blob, head, tree_blob) -> list[str]:
    """
    A re-pin is a RE-MINT (BUG-535).

    The hole this closes: `staged_faults` refused a moved pinned artifact, and refused staging the pins file
    while the SCAN was red - so the one legal-looking way to clear a CHANGED pinned artifact was to overwrite
    its sha256 under the OLD decision id. That turns the scan GREEN and the commit was TOLERATED, while the old
    decision kept certifying a measurement nobody re-ran (BUG-391/BUG-526 class: the rule lived in a message,
    not in a check). So: a sha256 may only move in the same commit that changes its `decision:` to a decision
    minted for the new measurement, and a pin may only disappear with a `retired:` marker. An unreadable
    predecessor, or a declaration staged apart from the bytes on disk, is an UNKNOWN - and an unknown is not a
    clean (C16/BUG-457).
    """
    raw = blob(_PINS_REL)
    if raw is None:
        return ["staged " + _PINS_REL + " cannot be READ - an unknown is not a clean (fail closed)"]
    faults: list[str] = []
    if tree_blob is not None and tree_blob(_PINS_REL) != raw:
        faults.append("staged " + _PINS_REL + " differs from the declaration ON DISK: a partially staged pins file "
                      "would commit lines nobody can see in the working tree. Commit the whole declaration (fail closed).")
    if head is _UNSET:
        return faults + ["staged " + _PINS_REL + " but its committed predecessor could not be read, so the re-pin "
                         "rule cannot be evaluated (fail closed, BUG-535)."]
    if head is None:
        return faults   # no predecessor: a first-ever pins file is not a re-pin (no overreach, BUG-492)
    try:
        prev = (yaml.safe_load(head.decode(_ENCODING)) or {}).get("pins") or {}
    except Exception as exc:  # noqa: BLE001 - a predecessor we cannot parse is an unknown, never a clean
        return faults + ["the committed predecessor of " + _PINS_REL + " does not parse (" + type(exc).__name__
                         + ") - the re-pin rule cannot be evaluated (fail closed)."]
    cur = cfg.get("pins") or {}
    retired = {str(x) for x in (cfg.get("retired") or [])}
    for name, pin in sorted(cur.items()):
        old = prev.get(name)
        if not old:
            continue
        if pin.get("sha256") != old.get("sha256") and pin.get("decision") == old.get("decision"):
            faults.append("re-pin WITHOUT a re-mint (BUG-535): pin '" + name + "' moved its sha256 while its decision "
                          "stayed " + str(pin.get("decision")) + ". A sha256 is the digest of one measurement; if it "
                          "moved, that measurement was re-run and must be certified by a NEW decision id. Mint the "
                          "decision, then record the new sha256 AND the new id here (the pin is the declaration home).")
    for name in sorted(set(prev) - set(cur)):
        if name not in retired:
            faults.append("pin '" + name + "' was REMOVED without a `retired:` marker (BUG-535): a withdrawn meter must "
                          "say so in this same home, or the next reader cannot tell a retired meter from a forgotten one.")
    return faults


def _head_pins() -> bytes | None:
    """The committed predecessor of the pins file, or None when it has no predecessor (a first commit)."""
    out = subprocess.run(["git", "show", "HEAD:" + _PINS_REL], cwd=_ROOT, capture_output=True)
    return out.stdout if out.returncode == 0 else None


def _tree_blob(rel: str) -> bytes:
    """The bytes of a file in the WORKING TREE (used to refuse a partially staged declaration)."""
    return (_ROOT / rel).read_bytes()


def _staged_paths() -> list[str]:
    """The staged set, read from git - never assumed."""
    out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=_ROOT, capture_output=True, text=True)
    return out.stdout.split()


def _staged_blob(rel: str):
    """The bytes that would become permanent, or None (deleted / unreadable)."""
    out = subprocess.run(["git", "show", ":" + rel], cwd=_ROOT, capture_output=True)
    return out.stdout if out.returncode == 0 else None


def selftest() -> int:
    """Known-answer controls (BUG-492): every one must be able to FAIL before it can certify anything."""
    cfg = {"pins": {"meter": {"path": "meter.py", "sha256": hashlib.sha256(b"PINNED").hexdigest(), "decision": "D-382"}}}
    good, moved = b"PINNED", b"MOVED"

    def _pins_doc(sha: str, decision: str, keep: bool = True) -> bytes:
        """A synthetic pins document (the declaration home) with ONE pin, as bytes."""
        pins = {"meter": {"path": "meter.py", "sha256": sha, "decision": decision}} if keep else {}
        return yaml.safe_dump({"pins": pins}).encode()

    pinned_sha, repinned_sha = hashlib.sha256(b"PINNED").hexdigest(), hashlib.sha256(b"MOVED").hexdigest()
    before = _pins_doc(pinned_sha, "D-382")                 # the committed predecessor
    legal = _pins_doc(pinned_sha, "D-382")                  # unchanged declaration
    laundering = _pins_doc(repinned_sha, "D-382")           # sha moved, decision NOT re-minted
    reminted = _pins_doc(repinned_sha, "D-383")             # sha moved WITH a minted decision
    dropped = _pins_doc(pinned_sha, "D-382", keep=False)    # the pin was REMOVED
    controls = [
        ("a staged pinned artifact whose bytes MOVED is REFUSED",
         staged_faults(cfg, ["meter.py"], lambda rel: moved, lambda: []) != []),
        ("a staged pinned artifact whose bytes STILL MATCH its pin is TOLERATED (the legal commit)",
         staged_faults(cfg, ["meter.py"], lambda rel: good, lambda: []) == []),
        ("OVERREACH control: a staged set naming NO pinned artifact is TOLERATED",
         staged_faults(cfg, ["scripts/other.py", "config/other.yaml"], lambda rel: moved, lambda: []) == []),
        ("a staged pinned artifact whose staged bytes cannot be READ is REFUSED (fail closed)",
         staged_faults(cfg, ["meter.py"], lambda rel: None, lambda: []) != []),
        ("staging the PINS FILE while a pin is RED is REFUSED",
         staged_faults(cfg, [_PINS_REL], lambda rel: good, lambda: ["meter: moved"], head=None) != []),
        ("staging the PINS FILE while every pin holds is TOLERATED",
         staged_faults(cfg, [_PINS_REL], lambda rel: legal, lambda: [], head=before,
                       tree_blob=lambda rel: legal) == []),
        ("BUG-535: a sha256 moved under the SAME decision (the laundering move) is REFUSED",
         staged_faults(yaml.safe_load(laundering), [_PINS_REL], lambda rel: laundering, lambda: [],
                       head=before, tree_blob=lambda rel: laundering) != []),
        ("BUG-535: a sha256 moved WITH a newly minted decision is TOLERATED (the legal re-pin)",
         staged_faults(yaml.safe_load(reminted), [_PINS_REL], lambda rel: reminted, lambda: [],
                       head=before, tree_blob=lambda rel: reminted) == []),
        ("BUG-535: a partially staged pins file (staged bytes != on-disk bytes) is REFUSED",
         staged_faults(cfg, [_PINS_REL], lambda rel: legal, lambda: [], head=before,
                       tree_blob=lambda rel: laundering) != []),
        ("BUG-535: a REMOVED pin without a `retired:` marker is REFUSED",
         staged_faults(yaml.safe_load(dropped), [_PINS_REL], lambda rel: dropped, lambda: [],
                       head=before, tree_blob=lambda rel: dropped) != []),
        ("BUG-535: a REMOVED pin carrying a `retired:` marker is TOLERATED",
         staged_faults({**(yaml.safe_load(dropped)), "retired": ["meter"]}, [_PINS_REL],
                       lambda rel: dropped, lambda: [], head=before, tree_blob=lambda rel: dropped) == []),
        ("BUG-535: an unreadable predecessor fails CLOSED, and a first-ever pins file is TOLERATED (no overreach)",
         staged_faults(cfg, [_PINS_REL], lambda rel: legal, lambda: [], head=_UNSET,
                       tree_blob=lambda rel: legal) != []
         and staged_faults(cfg, [_PINS_REL], lambda rel: legal, lambda: [], head=None,
                           tree_blob=lambda rel: legal) == []),
        # BUG-536: the SCAN's severity split. A control that cannot be handed a BROKEN declaration is a
        # comment, so _split_probe BUILDS the broken one in a temp root instead of hoping the live tree
        # happens to be broken in the right way (BUG-492).
        ("BUG-536: a MOVED pin is OWNER-OWED (the owner owes the re-mint) and is NOT a fatal drift",
         _split_probe(moved=True) == (0, 1, 1)),
        ("BUG-536: a pin whose PATH is MISSING is FATAL - a broken declaration fails CLOSED (C16)",
         _split_probe(path_missing=True) == (1, 0, 1)),
        ("BUG-536: a pin naming a DECISION the registry does not carry is FATAL",
         _split_probe(carried=False) == (1, 0, 1)),
        ("BUG-536: the split is TOTAL and DISJOINT - no fault is lost or counted twice (BUG-492)",
         _split_probe(moved=True, path_missing=True, carried=False) == (2, 1, 3)),
    ]
    bad = 0
    for name, ok in controls:
        print(("  ok   " if ok else "  FAIL ") + name)
        bad += 1 - int(ok)
    print("recalibration-pins controls: " + str(len(controls) - bad) + "/" + str(len(controls)) + " known-answer control(s) fire")
    return 1 if bad else 0


def _split_probe(moved: bool = False, path_missing: bool = False, carried: bool = True) -> tuple[int, int, int]:
    """Run the SCAN rule over a TEMP root holding exactly the fault kinds asked for (BUG-536/BUG-492).

    Returns (fatal, owed, total). `total` is what the WRITE gate sees, so a control that made the split
    LOSSY - a fault dropped from both lists - fails here rather than in production.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "config").mkdir()
        (root / "config" / "decisions.yaml").write_text("D-1\n", encoding=_ENCODING)
        (root / "meter.py").write_bytes(b"x = 1\n")
        real = hashlib.sha256((root / "meter.py").read_bytes()).hexdigest()
        pins: dict[str, dict] = {}
        if path_missing:
            pins["missing"] = {"path": "nope.py", "sha256": real, "decision": "D-1"}
        if moved:
            pins["moved_pin"] = {"path": "meter.py", "sha256": "0" * 64, "decision": "D-1"}
        if not carried:
            pins["ghost"] = {"path": "meter.py", "sha256": real, "decision": "D-404"}
        cfg = {"pins": pins}
        fatal, owed = scan_split(root, cfg)
        return (len(fatal), len(owed), len(all_faults(root, cfg)))


def main(argv: list[str] | None = None) -> int:
    """Compare every pin to disk and to the registry, or the staged set to the pins.

    The SCAN is tri-state (BUG-536): 1 only for a BROKEN declaration, 2 for a pin the owner owes a re-mint
    on. The WRITE gate refuses either kind with 1 - a commit is not a place for debt.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true", help="audit the STAGED set (pre-commit hook) instead of the tree")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls (BUG-492)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = yaml.safe_load(_PINS.read_text(encoding=_ENCODING))
    if a.staged:
        staged = _staged_paths()
        faults = staged_faults(cfg, staged, _staged_blob, lambda: all_faults(_ROOT, cfg),
                               head=_head_pins(), tree_blob=_tree_blob)
    else:
        faults = all_faults(_ROOT, cfg)
    if a.staged:
        for line in faults:
            print(_RED + line)
        print("recalibration pins (write gate): " + str(len(staged)) + " staged path(s), " + str(len(faults)) + " RED")
        return EXIT_DRIFT if faults else EXIT_CLEAN   # a REFUSAL: either kind blocks the commit
    fatal, owed = scan_split(_ROOT, cfg)
    for line in owed:
        print(_OWED + line)
    for line in fatal:
        print(_RED + line)
    print(("FAIL " if fatal else ("OWED " if owed else "ok ")) + "recalibration pins: "
          + str(len(cfg["pins"])) + " pinned, " + str(len(fatal)) + " DRIFT, " + str(len(owed)) + " OWNER-OWED")
    return EXIT_DRIFT if fatal else (EXIT_OWED if owed else EXIT_CLEAN)


if __name__ == "__main__":
    raise SystemExit(main())
