#!/usr/bin/env python3
"""check_undeclared_encoding.py - D-2644 in CODE: an encoding the ENVIRONMENT decides is UNDECLARED.

WHY (BUG-521, MEASURED 2026-09-26): text reads/writes across this repo never name a codec, so the codec is
locale.getpreferredencoding(False) - the environment decides, not the artifact. On this machine that is UTF-8 and
therefore INERT, which is exactly why 166 modules carried it unseen. It is not inert elsewhere: under LC_ALL=C a
non-ASCII byte raises a UnicodeDecodeError that names no artifact (C16 error leak), and on Windows the default is
cp1252, so 0xD1 decodes to 'N-tilde' instead of an em dash in every reader AND every writer (BUG-511). A written
artifact's bytes then differ per machine, so a sha256 pin does not pin the same bytes (C3 / C26 / R14).

A SITE is a Call that reads or writes TEXT without naming an encoding: read_text/write_text (no `encoding`, or
`encoding=None` - an explicit None IS the default), or open/Path.open in a text mode ('b' modes excluded). A mode
that is not a literal is UNRESOLVABLE: it is not proof of text, so the rail will not judge it - it is counted
separately and repaired by making the mode literal.

RULER (D-2642). config/undeclared_encoding.yaml#ceiling IS the number and THIS RAIL writes it (--record), never a
human transcribing a probe. A raise is REFUSED once measured_by is this rail. `files` is the unit of repair.

TRI-STATE (BUG-457): 0 clean | 1 DRIFT | 2 owner-owed.
CLI: --selftest | --check | --list | --record. Exactly ONE is required (C16).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "undeclared-encoding"
REGISTER = ROOT / "config" / "undeclared_encoding.yaml"
RAIL_REL = "scripts/check_undeclared_encoding.py"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
TEXT_CALLS = ("read_text", "write_text")
WRITE_MODES = ("w", "a", "x", "+")
KEYS = ("files", "sites", "writes", "unresolvable")

sys.path.insert(0, str(ROOT / "scripts"))
from lib import yaml_guard  # noqa: E402 - D-2648: the bytes must PARSE before they are written
from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 - D-401/I1 (C6)


def declared(reg: dict, key: str) -> Any:
    """Read a required key from the register; a code default here would BE the defect this rail measures."""
    if key not in reg:
        raise SystemExit("FAIL " + PREFIX + ": " + REGISTER.name + " declares no " + repr(key)
                         + " - a rule read with a code default is the defect this rail measures")
    return reg[key]


def _indices(call: ast.Call, name: str) -> tuple[int, int]:
    """(mode index, encoding index) for this call form.

    MEASURED during the audit of this rail's own first draft: Path.open's FIRST positional is the mode, while the
    builtin open's first positional is the file. Using one index for both classified `p.open('a')` as a READ.
    """
    if name == "read_text":
        return -1, 0                      # read_text(encoding, errors, ...)
    if name == "write_text":
        return -1, 1                      # write_text(data, encoding, errors, ...) - DATA is first
    if isinstance(call.func, ast.Name):
        return 1, 3                       # builtin open(file, mode, buffering, encoding, ...)
    return 0, 2                           # path.open(mode, buffering, encoding, ...)


def _names_encoding(call: ast.Call, name: str) -> bool:
    """True only when an encoding is named and it is not None: `encoding=None` IS the platform default."""
    for kw in call.keywords:
        if kw.arg == "encoding":
            if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                return False
            return True
    _, enc = _indices(call, name)
    if enc < 0 or len(call.args) <= enc:
        return False
    arg = call.args[enc]
    return not (isinstance(arg, ast.Constant) and arg.value is None)


def _literal_mode(call: ast.Call, name: str) -> tuple[bool, str]:
    """(is_literal, mode). A non-literal mode is UNRESOLVABLE, never assumed to be text."""
    midx, _ = _indices(call, name)
    if midx < 0:
        return True, "r"
    for kw in call.keywords:
        if kw.arg == "mode":
            return (True, str(kw.value.value)) if isinstance(kw.value, ast.Constant) else (False, "")
    if len(call.args) > midx:
        arg = call.args[midx]
        return (True, str(arg.value)) if isinstance(arg, ast.Constant) else (False, "")
    return True, "r"


def findings_in(source: str, non_text_open: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    """Every undeclared-encoding site in one module, as (line, kind): read | write | unresolvable.

    `non_text_open` is the declared set of `.open()` receivers that are NOT text file opens (os.open ->
    a raw fd with flags, fitz.open -> a PDF document). They are never text and never UNRESOLVABLE, so
    the rail skips them rather than demanding a literal 'mode' they do not have.
    """
    out: set[tuple[int, str]] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
        if name not in ("open",) + TEXT_CALLS:
            continue
        if (name == "open" and isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name) and func.value.id in non_text_open):
            continue
        line = int(getattr(node, "lineno", 0))
        if _names_encoding(node, name):
            continue
        if name in TEXT_CALLS:
            out.add((line, "write" if name == "write_text" else "read"))
            continue
        literal, mode = _literal_mode(node, name)
        if not literal:
            out.add((line, "unresolvable"))
        elif "b" in mode:
            continue
        else:
            out.add((line, "write" if any(c in mode for c in WRITE_MODES) else "read"))
    return sorted(out)


def scan(reg: dict, repo: Path = ROOT) -> tuple[dict[str, list[tuple[int, str]]], list[str]]:
    """{rel path: sites} for every module under scan_roots, plus the modules a census could not read."""
    exempt = [str(x) for x in declared(reg, "exempt")]
    non_text_open = tuple(str(x) for x in declared(reg, "non_text_open"))
    found: dict[str, list[tuple[int, str]]] = {}
    unreadable: list[str] = []
    for root in declared(reg, "scan_roots"):
        base = repo / str(root)
        if not base.is_dir():
            raise SystemExit("FAIL " + PREFIX + ": scan_roots names " + str(root) + ", which is not a directory")
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(repo).as_posix()
            if rel in exempt:
                continue
            try:
                sites = findings_in(path.read_text(encoding="utf-8"), non_text_open)
            except (SyntaxError, UnicodeDecodeError, OSError):
                unreadable.append(rel)
                continue
            if sites:
                found[rel] = sites
    return found, unreadable


def classify(found: dict, allowed: list) -> tuple[dict[str, int], list, list, dict]:
    """Split measured sites into tolerated and debt; report tolerances that disagree or vanished."""
    tol: dict[tuple[str, int], str] = {}
    for entry in allowed:
        for line in declared(entry, "lines"):
            tol[(str(entry["path"]), int(line))] = str(entry["kind"])
    debt = {k: 0 for k in KEYS}
    seen: set[tuple[str, int]] = set()
    mismatched: list[str] = []
    for rel, sites in found.items():
        rest = []
        for line, kind in sites:
            key = (rel, line)
            if key in tol:
                seen.add(key)
                if tol[key] != kind:
                    mismatched.append(rel + ":" + str(line) + " measured " + kind + ", declared " + tol[key])
                continue
            rest.append((line, kind))
        if rest:
            debt["files"] += 1
            debt["sites"] += len(rest)
            debt["writes"] += sum(1 for _, k in rest if k == "write")
            debt["unresolvable"] += sum(1 for _, k in rest if k == "unresolvable")
    stale = [k for k in tol if k not in seen]
    return debt, stale, mismatched, tol


def record(debt: dict, ceiling: dict, reg: dict) -> int:
    """Write the measured number (D-2642): either direction on first record, DOWNWARD only afterwards."""
    handover = str(reg.get("measured_by")) != RAIL_REL
    for key in KEYS:
        if not handover and debt[key] > int(ceiling[key]):
            raise SystemExit("FAIL " + PREFIX + ": measured " + key + "=" + str(debt[key]) + " is ABOVE the "
                             "declared ceiling " + str(ceiling[key]) + " and this rail may only LOWER it - a "
                             "measurement above the declaration is DRIFT, never a new declaration (D-2642)")
    text = REGISTER.read_text(encoding="utf-8")
    block = "ceiling:\n" + "".join("  " + k + ": " + str(debt[k]) + "\n" for k in KEYS) + "  direction: shrink_only\n"
    text, n = re.subn(r"(?ms)^ceiling:\n(?:[ \t]+.*\n)+", block, text, count=1)
    text, n2 = re.subn(r"(?m)^measured_by: .*$", "measured_by: " + RAIL_REL, text, count=1)
    if (n, n2) != (1, 1):
        raise SystemExit("FAIL " + PREFIX + ": could not locate the ceiling/measured_by block in "
                         + REGISTER.name + " - refusing to write a number I cannot place (C16)")
    yaml_guard.assert_yaml(text, REGISTER, RAIL_REL)
    write_document(REGISTER, text, writer=RAIL_REL, owned_keys={OWNED_ANY}, backup=True)
    print(PREFIX + ": recorded " + " ".join(k + "=" + str(debt[k]) for k in KEYS)
          + " | measured_by " + ("probe -> rail" if handover else "rail (lowered)"))
    return EXIT_OWED


def controls() -> list:
    """Known-answer controls (BUG-492): the rail must be SEEN to fire and SEEN to stay quiet."""
    def site(src: str, line: int, kind: str) -> bool:
        return (line, kind) in findings_in(src)
    return [
        ("read_text() with no encoding is a read site", site("p.read_text()\n", 1, "read")),
        ("read_text(encoding=...) is clean", findings_in('p.read_text(encoding="utf-8")\n') == []),
        ("read_text positional encoding is clean", findings_in('p.read_text("utf-8")\n') == []),
        ("encoding=None is STILL the platform default", site("p.read_text(encoding=None)\n", 1, "read")),
        ("bare open() is a read site", site("open(p)\n", 1, "read")),
        ("open(p, 'rb') needs no codec", findings_in("open(p, 'rb')\n") == []),
        ("open(p, mode='w') is a write site", site("open(p, mode='w')\n", 1, "write")),
        ("Path.open('a') is a write site", site("p.open('a')\n", 1, "write")),
        ("open(p, 'r+') is a write site (an update mode writes)", site("open(p, 'r+')\n", 1, "write")),
        ("write_text() is a write site", site('p.write_text("x")\n', 1, "write")),
        ("open(p, 'r', 1, 'utf-8') is clean", findings_in("open(p, 'r', 1, 'utf-8')\n") == []),
        ("p.open('r', -1, 'utf-8') is clean (attribute arg positions)", findings_in("p.open('r', -1, 'utf-8')\n") == []),
        ("a non-literal mode is UNRESOLVABLE, never assumed text", site("open(p, m)\n", 1, "unresolvable")),
        ("a comment naming open() is invisible (AST)", findings_in("# open(p)\n") == []),
        ("errors= without an encoding is STILL undeclared", site('p.read_text(errors="replace")\n', 1, "read")),
        ("os.open(...) is NOT a text open and is never unresolvable",
         findings_in("os.open(p, os.O_RDONLY)\n", ("os",)) == []),
        ("fitz.open(...) is NOT a text open and is never unresolvable",
         findings_in("fitz.open(p)\n", ("fitz",)) == []),
    ]


def run_controls() -> int:
    """Run the known-answer controls AND assert the negative controls are not vacuous."""
    results = controls()
    for name, ok in results:
        print(("  ok   " if ok else "  FAIL ") + name)
    if all(ok for _, ok in results):
        # a control set that passes on a BROKEN rule would be worse than none: prove the detector can fire
        broken = findings_in("p.read_text()\n")
        if broken != [(1, "read")]:
            print("  FAIL control set is vacuous: the detector cannot be seen firing at all")
            results.append(("non-vacuity", False))
    passed = sum(1 for _, ok in results if ok)
    print(PREFIX + ": " + str(passed) + "/" + str(len(results)) + " known-answer controls ok")
    return EXIT_CLEAN if passed == len(results) else EXIT_DRIFT


def main(argv: list) -> int:
    """Entry point: exactly ONE mode is required (C16 - an ambiguous invocation must not silently scan)."""
    modes = [a for a in argv if a in ("--selftest", "--check", "--list", "--record")]
    if len(argv) != 1 or len(modes) != 1:
        raise SystemExit("FAIL " + PREFIX + ": exactly ONE of --selftest | --check | --list | --record is "
                         "required (C16); got " + repr(argv))
    if modes[0] == "--selftest":
        return run_controls()
    reg = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    found, unreadable = scan(reg)
    debt, stale, mismatched, _ = classify(found, declared(reg, "allowed"))
    ceiling = declared(reg, "ceiling")
    if modes[0] == "--list":
        for rel in sorted(found):
            for line, kind in found[rel]:
                print("  " + rel + ":" + str(line) + " " + kind)
        print(PREFIX + ": " + str(len(found)) + " file(s), " + str(sum(len(v) for v in found.values())) + " site(s)")
        return EXIT_CLEAN
    if modes[0] == "--record":
        return record(debt, ceiling, reg)
    over = any(debt[k] > int(ceiling[k]) for k in KEYS)
    bad = bool(over or stale or mismatched or unreadable)
    mark = "FAIL " if bad else ("OWED " if debt["sites"] else "ok ")
    print(mark + PREFIX + ": files " + str(debt["files"]) + " of ceiling " + str(ceiling["files"])
          + " | sites " + str(debt["sites"]) + " of ceiling " + str(ceiling["sites"])
          + " | writes " + str(debt["writes"]) + " of ceiling " + str(ceiling["writes"])
          + " | unresolvable " + str(debt["unresolvable"]) + " of ceiling " + str(ceiling["unresolvable"])
          + " | allowed " + str(len(declared(reg, "allowed"))) + " entry(ies) | home " + str(declared(reg, "home")))
    for note in mismatched:
        print("  DRIFT a tolerance disagrees with the measurement: " + note)
    for key in stale:
        print("  DRIFT STALE tolerance (declared, no measured site): " + key[0] + ":" + str(key[1]))
    for rel in unreadable:
        print("  DRIFT could not parse/read: " + rel)
    if bad:
        return EXIT_DRIFT
    return EXIT_OWED if debt["sites"] else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
