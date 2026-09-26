#!/usr/bin/env python3
"""check_silent_repair.py - the rail that DETECTS a reader which repairs undecodable bytes instead of failing.

MEASURED 2026-09-26 (BUG-518/BUG-519 class): 28 `errors="replace"` / `errors="ignore"` read sites across scripts/,
pipeline/ and tools/. Neither mode CRASHES - `replace` turns a bad byte into U+FFFD and `ignore` DROPS it - so both
CHANGE THE TEXT SILENTLY (BUG-511: 0xD1 is an em dash in Mac Roman and an N-tilde in cp1252, and neither raises).
A silent repair is an error leak (C16): the reader that guesses is not protected from a crash, it is protected from
NOTICING. The fix is never a better default: it is the declared-encoding home (scripts/lib/artifact_encoding.py),
which opens an artifact in the encoding it DECLARES and fails CLOSED when it cannot.

WHY A RAIL AND NOT A REVIEW. An invariant no machine enforces is a comment (BUG-492). This rail classifies every
`errors=` site in the declared scan roots:
  * an entry in `allowed` - repair is CORRECT: the bytes are a RUNTIME LOG or a FOREIGN stream (git output, a socket
    reply), not an artifact whose encoding is a declared fact. Each entry carries its reason.
  * an entry in `debt`   - an artifact/source read that still repairs silently. Counted against a SHRINK-ONLY
    ceiling (D-2642): the number is a measurement, so it may only be LOWERED (the fix is delegation, D-2646).
  * no entry             - DRIFT. A new silent repair is a defect, not a style choice.
It is an AST scan, not a grep: a COMMENT that mentions errors="replace" decides nothing and is invisible here.
An `errors=` argument that is NOT a literal is reported as `unresolvable` and must be declared too - a detector
never passes what it cannot read.

IT KEYS A SITE BY CONTENT, NOT BY LINE NUMBER (BUG-542, MEASURED 2026-09-26S). An entry keys its site with
either `lines:` (legacy, a coordinate) or `match:` (the substring the repairing LINE carries). A line number is not
a fact about the code: rail 0 was edited for BUG-547, its repair site moved 280 -> 306, and this register reported
the SAME site twice - STALE at 280 and DRIFT at 306 - while the DRIFT is FATAL, so `just health` aborted and HID
every rail below it (BUG-457: an abort is an amnesia generator). The previous remedy for this bug re-pointed the
LINE NUMBER, which is why the class came back the same day. A `match:` that resolves to no measured site is
REPORTED, never dropped: a key that can match nothing is a comment (BUG-492).

TRI-STATE (BUG-457): 0 clean | 1 a NEW/undeclared site, or the ceiling widened | 2 declared debt only (loud, NOT
fatal). CLI: --selftest | --check | --list.

FAIL CLOSED ON ITS OWN POLICY (BUG-544, MEASURED 2026-09-26): an ABSENT, EMPTY or unparseable declaration, one that
is not a mapping, one missing `scan_roots`/`ceiling`, or a declared scan root that is not on disk is a NAMED failure
(exit 1) - never a traceback, and never a silent narrowing of the census. `--selftest` carries one known-answer
control per case, because a control that was never SEEN to fire is a comment (BUG-492).
"""
from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import yaml

REPO = Path(__file__).resolve().parents[1]
DECLARATION_REL = "config/silent_repair.yaml"
REQUIRED_DECLARATION_KEYS = ("scan_roots", "ceiling")
REPAIR_MODES = ("replace", "ignore")
UNRESOLVABLE = "unresolvable"
PREFIX = "silent-repair"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2


def findings_in(source: str) -> list[tuple[int, str]]:
    """Every `errors=` argument that repairs silently (or cannot be read) in one module, as (line, mode)."""
    out = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "errors":
                continue
            line = int(getattr(kw, "lineno", node.lineno))
            if isinstance(kw.value, ast.Constant) and kw.value.value in REPAIR_MODES:
                out.add((line, str(kw.value.value)))
            elif not isinstance(kw.value, ast.Constant):
                out.add((line, UNRESOLVABLE))     # fail closed: not "probably fine", but UNREAD by this rail
    return sorted(out)


def scan(cfg: dict, repo: Path = REPO) -> tuple[dict[str, list[tuple[int, str]]], dict[str, dict[int, str]], list[str]]:
    """{relative path: findings} for every module under the declared scan roots.

    Also returns, per file, the SOURCE TEXT of every flagged line, because a declared entry may be keyed by CONTENT
    (`match:`) rather than by a line number (BUG-542).

    FAILS CLOSED (C16, BUG-544): an EMPTY scan_roots - or a declared root that is not on disk - would narrow the
    census to nothing and still print ok. A rail that can never say FAIL is a comment (BUG-492); the sibling rail
    scripts/check_config_defaults.py carries the same guard for the same reason.
    """
    found: dict[str, list[tuple[int, str]]] = {}
    texts: dict[str, dict[int, str]] = {}
    broken: list[str] = []
    roots = cfg.get("scan_roots") or []
    if not roots:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): scan_roots is EMPTY - a census over no root is not a "
                         "measurement (C16)")
    for root in roots:
        base = repo / str(root)
        if not base.exists():
            raise SystemExit("FAIL-CLOSED (" + PREFIX + "): scan root " + repr(str(root)) + " does not exist under "
                             + str(repo) + " - a scan root that silently does not exist narrows the census and still "
                             "prints ok (C16)")
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(repo).as_posix()
            try:
                source = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                broken.append(rel + ": " + type(exc).__name__); continue
            try:
                hits = findings_in(source)
            except SyntaxError as exc:
                broken.append(rel + ": " + type(exc).__name__); continue
            if hits:
                listing = source.splitlines()
                found[rel] = hits
                texts[rel] = {ln: (listing[ln - 1].strip() if 0 < ln <= len(listing) else "") for ln, _ in hits}
    return found, texts, broken


def _claim(out: dict, faults: list[str], pair: tuple[str, int], kind: str, modes: set[str]) -> None:
    """Record one declared site, refusing a SECOND entry for the same site (one site, one declaration, D-2646)."""
    if pair in out:
        faults.append("two entries declare the same SITE " + pair[0] + ":" + str(pair[1]) + " - one site, one "
                      "declaration (D-2646); the later entry would be dropped in silence (C16)")
    out[pair] = (kind, modes)


def declared_sites(cfg: dict, found: dict[str, list[tuple[int, str]]],
                   texts: dict[str, dict[int, str]]) -> tuple[dict[tuple[str, int], tuple[str, set[str]]], list[str], list[str]]:
    """{(path, line): (kind, {modes})} for every allowed/debt entry, RESOLVED against the measurement (BUG-542).

    An entry keys its site by EXACTLY ONE of `lines:` (legacy coordinate) or `match:` (the content of the repairing
    line). A `match` is resolved against the MEASURED line text, so the declaration survives the site MOVING - the
    defect this fixes, where the coordinate stayed and the site did not. Returns (sites, stale_keys, bad_keys): a
    `match` that resolves to nothing is a STALE key (reported, never dropped - BUG-492), and an ambiguous
    declaration (both keys, neither key, two entries on one site) is a BROKEN key (fail closed, C16).
    """
    out: dict[tuple[str, int], tuple[str, set[str]]] = {}
    stale: list[str] = []
    bad: list[str] = []
    for kind in ("allowed", "debt"):
        for entry in cfg.get(kind) or []:
            path = str(entry["path"])
            modes = {str(entry.get("mode") or REPAIR_MODES[0])}
            lines = [int(x) for x in entry.get("lines") or []]
            match = entry.get("match")
            if bool(lines) == bool(match):
                bad.append(kind + " entry for " + path + " must key its site by EXACTLY ONE of `lines:` (legacy "
                           "coordinate) or `match:` (content) - both or neither cannot be resolved (C16)")
                continue
            if match:
                pattern = str(match)
                pairs = [(path, ln) for rel, hits in found.items() if rel == path for ln, _ in hits
                         if pattern in (texts.get(rel) or {}).get(ln, "")]
                if not pairs:
                    stale.append(path + " `match: " + pattern + "`")
                for pair in pairs:
                    _claim(out, bad, pair, kind, modes)
                continue
            for line in lines:
                _claim(out, bad, (path, line), kind, modes)
    return out, stale, bad


def verdict(found: dict, sites: dict, ceiling: int) -> tuple[int, int, list[str], list[str]]:
    """An undeclared site is a DEFECT; declared debt above the ceiling is DRIFT; a vanished entry is STALE."""
    unknown: list[str] = []
    debt = 0
    for rel, hits in sorted(found.items()):
        for line, mode in hits:
            entry = sites.get((rel, line))
            if entry is None:
                unknown.append(rel + ":" + str(line) + " repairs silently (" + mode + ") with no entry")
                continue
            kind, modes = entry
            if mode not in modes:
                unknown.append(rel + ":" + str(line) + " mode " + mode + " is beyond its " + kind + " entry")
            elif kind == "debt":
                debt += 1
    seen = {(rel, line) for rel, hits in found.items() for line, _ in hits}
    stale = [p + ":" + str(l) for (p, l) in sorted(sites) if (p, l) not in seen]
    if unknown:
        return EXIT_DRIFT, debt, unknown, stale
    if debt > ceiling:
        return EXIT_DRIFT, debt, ["the declared ceiling is " + str(ceiling) + " but " + str(debt) + " site(s) still "
                                 "repair silently - a ceiling is SHRINK-ONLY (D-2642); raise it by DECISION only"], stale
    return (EXIT_OWED if (debt or stale) else EXIT_CLEAN), debt, [], stale


def config_path(repo: Path = REPO) -> Path:
    """The declaration this rail obeys, resolved under the repo it was ASKED about (BUG-544: `repo` was ignored)."""
    return repo / DECLARATION_REL


def declaration_text(path: Path) -> str:
    """The declaration's bytes, or a NAMED failure (BUG-544: a rail DECIDES, it does not raise a traceback)."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is ABSENT: " + str(path)
                         + " - this rail measures nothing without it, and 'nothing found' is not 'clean'")
    except IsADirectoryError:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is a DIRECTORY, not a document: " + str(path))
    except UnicodeDecodeError as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is not UTF-8 (" + type(exc).__name__
                         + "): " + str(path))
    except OSError as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is UNREADABLE (" + type(exc).__name__
                         + "): " + str(path))


def parse_declaration(text: str, path: Path) -> dict:
    """The declaration as a mapping, or a NAMED failure. Pure, so a known-answer control can fire it (BUG-492)."""
    if not text.strip():
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is EMPTY: " + str(path)
                         + " - an empty policy declares 0 sites and would read as clean")
    try:
        cfg = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration does not parse as YAML ("
                         + type(exc).__name__ + "): " + str(path))
    if not isinstance(cfg, dict):
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration is not a MAPPING but " + type(cfg).__name__
                         + ": " + str(path))
    missing = [key for key in REQUIRED_DECLARATION_KEYS if key not in cfg]
    if missing:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declaration declares no " + ", ".join(missing)
                         + " - a rail that cannot see its own policy is the defect it measures (D-2644): " + str(path))
    return cfg


def load(repo: Path = REPO) -> dict:
    """The policy: which sites may repair silently, which still owe a repoint, and how much debt is declared."""
    path = config_path(repo)
    return parse_declaration(declaration_text(path), path)


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492): the detector must be SEEN to fire, and SEEN to stay quiet, on known cases."""
    allowed = {("scripts/log_reader.py", 10): ("allowed", {"replace"})}
    debt = {("scripts/artifact_reader.py", 12): ("debt", {"ignore"})}
    # BUG-544 fixtures: a name under the temp dir that cannot exist (uuid4), so "ABSENT" is PROVEN absent.
    absent = Path(tempfile.gettempdir()) / ("silent_repair_absent_" + uuid4().hex + ".yaml")
    # BUG-542 fixtures: ONE site at line 306, and registers that key it by content, by a STALE coordinate, by a key
    # that matches nothing, by both keys, by neither, and by two entries at once.
    moved_found = {"scripts/rail.py": [(306, "replace")]}
    moved_texts = {"scripts/rail.py": {306: 'last = reflog.read_text(errors="replace").splitlines()'}}
    moved_content = {"allowed": [{"path": "scripts/rail.py", "match": "reflog.read_text", "mode": "replace"}]}
    moved_lines = {"allowed": [{"path": "scripts/rail.py", "lines": [280], "mode": "replace"}]}
    dead_key = {"allowed": [{"path": "scripts/rail.py", "match": "no such text", "mode": "replace"}]}
    both_keys = {"allowed": [{"path": "scripts/rail.py", "match": "reflog", "lines": [306], "mode": "replace"}]}
    no_keys = {"allowed": [{"path": "scripts/rail.py", "mode": "replace"}]}
    double_claim = {"allowed": [{"path": "scripts/rail.py", "lines": [306], "mode": "replace"},
                                {"path": "scripts/rail.py", "match": "reflog.read_text", "mode": "replace"}]}

    def named(fn, *args) -> str:
        """The NAMED message of the SystemExit `fn(*args)` raises, or '' when it does NOT fail closed (BUG-544)."""
        try:
            fn(*args)
        except SystemExit as exc:
            return str(exc)
        return ""

    t_absent = named(declaration_text, absent)
    t_empty = named(parse_declaration, "   " + chr(10), absent)
    t_unparsed = named(parse_declaration, "allowed: [" + chr(10), absent)
    t_unmapped = named(parse_declaration, "- 1" + chr(10) + "- 2" + chr(10), absent)
    t_missing = named(parse_declaration, "schema_version: '1.0'" + chr(10), absent)
    t_narrow = named(scan, {"scan_roots": ["no_such_root_zz"]}, REPO)
    return [
        ("read_text(errors=\"replace\") IS flagged",
         findings_in('t = p.read_text(encoding="utf-8", errors="replace")\n') == [(1, "replace")]),
        ("errors=\"ignore\" IS flagged",
         findings_in('t = p.read_text(errors="ignore")\n') == [(1, "ignore")]),
        ("open(p, errors=\"replace\") IS flagged",
         findings_in('with open(p, errors="replace") as fh:\n    pass\n') == [(1, "replace")]),
        ("a DYNAMIC errors= is flagged as unresolvable (a detector never passes what it cannot read)",
         findings_in("t = p.read_text(errors=REPAIR)\n") == [(1, UNRESOLVABLE)]),
        ("encoding=\"utf-8\" alone is NOT flagged",
         findings_in('t = p.read_text(encoding="utf-8")\n') == []),
        ("errors=None (the Python default, strict) is NOT flagged",
         findings_in("t = p.read_text(errors=None)\n") == []),
        ("a COMMENT naming errors=\"replace\" decides nothing (AST, not grep)",
         findings_in('# we used errors="replace" once\nX = 1\n') == []),
        ("a declared ALLOWED site is tolerated", verdict({"scripts/log_reader.py": [(10, "replace")]}, allowed, 0)[0] == EXIT_CLEAN),
        ("a declared DEBT site is OWED at the ceiling and DRIFT above it",
         verdict({"scripts/artifact_reader.py": [(12, "ignore")]}, debt, 1)[0] == EXIT_OWED
         and verdict({"scripts/artifact_reader.py": [(12, "ignore")]}, debt, 0)[0] == EXIT_DRIFT),
        ("an undeclared site is DRIFT", verdict({"scripts/new_reader.py": [(3, "replace")]}, allowed, 9)[0] == EXIT_DRIFT),
        ("a NEW mode on a declared site is DRIFT (the entry declares the mode, not just the line)",
         verdict({"scripts/log_reader.py": [(10, "ignore")]}, allowed, 9)[0] == EXIT_DRIFT),
        ("an entry with no measured site is STALE and reported",
         verdict({}, allowed, 0) == (EXIT_OWED, 0, [], ["scripts/log_reader.py:10"])),
        # BUG-544: the rail must DECIDE on a broken declaration of its own policy, never surface a traceback at a
        # caller. Each control asserts the NAMED sentence, because "exit != 0" alone cannot tell the two apart.
        ("an ABSENT declaration is a NAMED failure, not a traceback (BUG-544)", "ABSENT" in t_absent),
        ("an EMPTY declaration is a NAMED failure (BUG-544)", "EMPTY" in t_empty),
        ("an unparseable declaration is a NAMED failure (BUG-544)", "does not parse" in t_unparsed),
        ("a declaration that is not a mapping is a NAMED failure (BUG-544)", "not a MAPPING" in t_unmapped),
        ("a declaration missing a REQUIRED key is a NAMED failure (BUG-544)", "declares no" in t_missing),
        ("a declared scan root that does not exist is a NAMED failure, not a silent narrowing (C16)",
         "does not exist" in t_narrow),
        # BUG-542: the register must survive its site MOVING. Line-keyed = the defect; content-keyed = the fix.
        ("a CONTENT-keyed entry tolerates its site after it MOVED (BUG-542)",
         declared_sites(moved_content, moved_found, moved_texts)[0].get(("scripts/rail.py", 306)) == ("allowed", {"replace"})
         and not declared_sites(moved_content, moved_found, moved_texts)[1]
         and not declared_sites(moved_content, moved_found, moved_texts)[2]),
        ("a LINE-keyed entry for that SAME moved site is STALE - the defect the content key fixes (BUG-542)",
         declared_sites(moved_lines, moved_found, moved_texts)[0].get(("scripts/rail.py", 280)) == ("allowed", {"replace"})
         and declared_sites(moved_lines, moved_found, moved_texts)[1] == []),
        # anti-overreach (BUG-492): the fix must not buy silence - a key that matches NOTHING is reported, and an
        # ambiguous declaration fails closed rather than dropping a site.
        ("a `match:` that resolves to NO measured site is REPORTED, never silently dropped (BUG-492)",
         declared_sites(dead_key, moved_found, moved_texts)[1] == ["scripts/rail.py `match: no such text`"]),
        ("an entry keying BOTH `lines:` and `match:` is a BROKEN declaration (fail closed, C16)",
         len(declared_sites(both_keys, moved_found, moved_texts)[2]) == 1),
        ("an entry keying NEITHER is a BROKEN declaration (fail closed, C16)",
         len(declared_sites(no_keys, moved_found, moved_texts)[2]) == 1),
        ("two entries claiming ONE site is a BROKEN declaration (one site, one declaration, D-2646)",
         len(declared_sites(double_claim, moved_found, moved_texts)[2]) == 1),
    ]


def main(argv: list[str]) -> int:
    """--selftest | --check | --list. Any other argument is refused (C16: an ignored argument is a silent error)."""
    ap = argparse.ArgumentParser(add_help=False)
    for flag in ("--selftest", "--check", "--list"):
        ap.add_argument(flag, action="store_true")
    args, unknown = ap.parse_known_args(argv)
    if unknown or sum([args.selftest, args.check, args.list]) != 1:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): pass exactly ONE of --selftest | --check | --list (unknown: "
                         + str(unknown) + ")")
    if args.selftest:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [n for n, ok in rows if not ok]
        if failed:
            print("FAIL " + PREFIX + ": " + str(len(failed)) + " of " + str(len(rows)) + " control(s) did not fire")
            return EXIT_DRIFT
        print("ok " + PREFIX + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
        return EXIT_CLEAN
    cfg = load()
    found, texts, broken = scan(cfg)
    sites, stale_keys, bad_keys = declared_sites(cfg, found, texts)
    if args.list:
        for rel, hits in sorted(found.items()):
            print("   " + rel + " : " + ", ".join(str(line) + "/" + mode for line, mode in hits))
        print("LIST: " + str(sum(len(h) for h in found.values())) + " silent-repair site(s) in "
              + ", ".join(str(r) for r in cfg.get("scan_roots") or []))
        return EXIT_CLEAN
    code, debt, unknown, stale = verdict(found, sites, int((cfg.get("ceiling") or {}).get("debt", 0)))
    stale = stale + stale_keys
    for line in unknown:
        print("  DRIFT " + line)
    for line in stale:
        print("  STALE " + line + " - declared but NOT measured; correct the entry or LOWER the ceiling")
    for line in bad_keys:
        print("  BROKEN " + line)
    for rel in broken:
        print("  BAD   " + rel + " does not parse (a rail cannot certify what it cannot read)")
    mark = "ok " if code == EXIT_CLEAN else ("OWED " if code == EXIT_OWED else "FAIL ")
    print(mark + PREFIX + ": debt " + str(debt) + " of ceiling " + str((cfg.get("ceiling") or {}).get("debt"))
          + " | unknown " + str(len(unknown)) + " | allowed " + str(sum(1 for e in cfg.get("allowed") or []))
          + " entry(ies) | home " + str(cfg.get("home")))
    return EXIT_DRIFT if (broken or bad_keys) else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
