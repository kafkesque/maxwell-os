#!/usr/bin/env python3
"""scripts/check_revoked_references.py - the anti-resurrection rail (D-2645, completes D-2643/BUG-503).

WHY. D-2643 made the abandoned D2205 migration UNREACHABLE to EXECUTE: the three justfile recipes are gone and
pipeline/migrate_D2205_epistemic.py refuses with exit 2 unless the owner passes the explicit opt-in flag. That is
a TOMBSTONE, and a tombstone does not stop RE-PROPOSAL: a future agent can read the archaeology (kept on purpose),
find the eight column names, and write a NEW migration with the same defect - a fourth epistemic column colliding
in name with the live epistemic_status, DEFAULT corroborated.

ONE HOME (D-2642). WHAT is revoked is declared on the decision record (config/decisions.yaml, the prefixed
revocation_* keys). The RULES - which states require the declaration, which carry pinned legacy debt, what
counts as LIVE code - are declared in config/decisions_policy.yaml. This script declares no token itself, and
its known-answer controls use a RESERVED fixture token so the rail never names its own live subject (F1).

WHAT COUNTS AS A REFERENCE. A docstring is archaeology and is NOT a reference. A comment is invisible to the AST
and is NOT a reference. An inline string, an identifier, an attribute or a keyword name IS a reference; in
YAML/TOML/justfile a VALUE is a reference and a comment is not. The selftest holds a known-answer control for
every one of those cases, because a guardrail never seen failing is not a guardrail (BUG-492).

EXIT: 0 clean | 1 a live file names a revoked token (fail closed) | 2 the subject cannot be resolved (owner-owed:
a rail that cannot see its own subject must never report clean - BUG-457).

Usage: python3 scripts/check_revoked_references.py [--selftest] [--list]
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "config" / "decisions_policy.yaml"
DECISIONS = ROOT / "config" / "decisions.yaml"
PREFIX = "check-revoked-references"
EXIT_CLEAN = 0
EXIT_REFERENCE = 1
EXIT_UNRESOLVABLE = 2
#: A RESERVED fixture namespace for the known-answer controls. It is NOT a revoked token and may not become
#: one: the controls must be able to name something WITHOUT the detector naming the live subject. MEASURED
#: 2026-09-25 (audit F1): the first version of these controls used the live token, and because scripts/** is
#: inside this rail own scan set, declaring that token made the rail FIRE ON ITSELF.
FIXTURE_TOKEN = "fixture_revoked_token_zz"
FIXTURE_IDS = ("D-9199", "D-9198")   # BUG-523: inside reserved_fixture_ids, never live-space


def load_yaml(path: Path) -> Any:
    """Load a YAML document or FAIL CLOSED (C16): a rail may not read its own subject leniently."""
    if not path.exists():
        raise SystemExit(f"FAIL {PREFIX}: {path.relative_to(ROOT)} does not exist")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL {PREFIX}: {path.relative_to(ROOT)} is unreadable: {exc}")


def declared(doc: dict, key: str, where: str) -> Any:
    """Read a declared key or FAIL CLOSED: an absent declaration is the error, never a default (D-2644)."""
    if key not in doc or doc[key] is None:
        raise SystemExit(f"FAIL {PREFIX}: {where} declares no '{key}' - a default here would be undeclared")
    return doc[key]


def build_patterns(tokens: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Return (token, pattern) pairs; a decision id also matches its dashed spelling (one token, one id)."""
    pats: list[tuple[str, re.Pattern[str]]] = []
    for token in tokens:
        if re.fullmatch("[Dd]-?[0-9]+", token):
            core = "[Dd]-?" + re.sub("^[Dd]-?", "", token)
        else:
            core = re.escape(token)
        pats.append((token, re.compile("(?<![A-Za-z0-9_-])" + core + "(?![A-Za-z0-9_])", re.IGNORECASE)))
    return pats


def hits_in(text: str, pats: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    """Return every revoked token the given text names."""
    return [token for token, pat in pats if pat.search(text)]


def strip_comment(line: str) -> str:
    """Drop a trailing comment from a non-Python line (a value is a dependency, a comment is archaeology)."""
    for i, ch in enumerate(line):
        if ch != "#" or i == 0 or not line[i - 1].isspace():
            continue
        head = line[:i]
        if head.count('"') % 2 or head.count("'") % 2:
            continue
        return head
    return line


def python_refs(path: Path, pats: list[tuple[str, re.Pattern[str]]]) -> list[tuple[int, str]]:
    """Return (lineno, token) for CODE references; docstrings are excluded and comments are invisible."""
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [(-1, "UNPARSABLE:" + str(exc))]
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    skip.add(id(body[0].value))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        texts: list[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            texts.append(node.value)
        elif isinstance(node, ast.Attribute):
            texts.append(node.attr)
        elif isinstance(node, ast.Name):
            texts.append(node.id)
        elif isinstance(node, ast.keyword) and node.arg:
            texts.append(node.arg)
        elif isinstance(node, ast.arg):
            texts.append(node.arg)
        for text in texts:
            for token in hits_in(text, pats):
                found.append((getattr(node, "lineno", -1), token))
    return found


def text_refs(path: Path, pats: list[tuple[str, re.Pattern[str]]]) -> list[tuple[int, str]]:
    """Return (lineno, token) for a non-Python file: values are scanned, comments are not."""
    found: list[tuple[int, str]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        for token in hits_in(strip_comment(line), pats):
            found.append((n, token))
    return found


def literal_var(path: Path, name: str) -> Any:
    """Return a module-level literal by name; fail closed if the declared evidence is absent."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        # MEASURED 2026-09-25: the first version assumed every module-level node is an assignment, so a bare
        # ast.Expr (a docstring, a bare expression statement) raised AttributeError before the reader ever
        # reached EPISTEMIC_COLUMNS. A literal reader must NAME the node kinds it can read and SKIP every other
        # kind: an unhandled node is not a near miss, it is a crash (C16).
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):   # EPISTEMIC_COLUMNS is an ANNOTATED assignment
            targets = [node.target]
        else:
            continue
        if any(getattr(t, "id", None) == name for t in targets):
            if isinstance(node.value, (ast.Dict, ast.List, ast.Tuple, ast.Constant)):
                return ast.literal_eval(node.value)
    raise SystemExit(f"FAIL {PREFIX}: {path.name} declares no literal {name}")


def revoked_subject(policy: dict) -> tuple[list[str], dict[str, str]]:
    """Return (tokens, provenance) from the records; fail closed on a broken or stale declaration.

    The revocation is declared with PREFIXED SCALAR KEYS (audit F2, MEASURED 2026-09-25): none of the 780
    records carries a mapping-shaped value, so a prefixed key adds no new shape to a governed registry and
    remains greppable without parsing YAML.
    """
    data = load_yaml(DECISIONS)
    rules = declared(policy, "revocation", "config/decisions_policy.yaml")
    prefix = str(declared(rules, "field_prefix", "revocation"))
    whole_states = {str(s).upper() for s in declared(rules, "whole_record_states", "revocation")}
    legacy_states = {str(s).upper() for s in declared(rules, "legacy_debt_states", "revocation")}
    legacy_ids = {str(i) for i in (rules.get("legacy_debt_ids") or [])}
    required = declared(rules, "required_fields", "revocation")
    tokens: list[str] = []
    provenance: dict[str, str] = {}
    seen_legacy: set[str] = set()
    for record in declared(data, "decisions", "config/decisions.yaml") or []:
        rid = str(record.get("id") or "").strip()
        state = str(record.get("state") or "").strip().upper()
        fields = {str(f): record.get(prefix + str(f)) for f in required}
        present = {f for f, v in fields.items() if v not in (None, "", [], {})}
        home = record.get(prefix + "tokens_home")
        if present or home:
            missing = sorted(set(fields) - present)
            if missing:
                raise SystemExit(
                    f"FAIL {PREFIX}: {rid} declares a partial {prefix} revocation, missing {missing} - a "
                    "revocation without scope, reason, evidence, date and tokens is a rumour (D-2645)"
                )
            if home:
                path_txt, _, var = str(home).partition("::")
                actual = list(literal_var(ROOT / path_txt, var))
                if list(fields["tokens"]) != actual:
                    raise SystemExit(
                        f"FAIL {PREFIX}: {rid} declares tokens but {home} holds {actual} - the declaration "
                        "and its evidence disagree (D-2642)"
                    )
            for raw in fields["tokens"]:
                token = str(raw)
                if provenance.get(token, rid) != rid:
                    raise SystemExit(
                        f"FAIL {PREFIX}: revoked token {token!r} is declared by BOTH {provenance[token]} "
                        f"and {rid} - one token, one subject (D-2645)"
                    )
                provenance[token] = rid
                tokens.append(token)
        elif state in whole_states:
            if rid not in legacy_ids:
                raise SystemExit(
                    f"FAIL {PREFIX}: {rid} is {state} with no {prefix} declaration - a whole-record "
                    "withdrawal must carry its scope, reason, evidence, date and tokens (D-2645)"
                )
            tokens.append(rid)
            provenance[rid] = rid
        elif state in legacy_states:
            if rid in legacy_ids:
                seen_legacy.add(rid)
            else:
                raise SystemExit(
                    f"FAIL {PREFIX}: {rid} is {state} and is NOT in legacy_debt_ids - new debt may not "
                    "be declared by silence (D-2645)"
                )
    stale = sorted(legacy_ids - seen_legacy)
    if stale:
        raise SystemExit(
            f"FAIL {PREFIX}: legacy_debt_ids lists {stale}, which is no longer a blockless "
            "SUPERSEDED/ARCHIVED record - the list may only shrink (D-2645)"
        )
    return tokens, provenance


def scan_files(policy: dict) -> tuple[list[Path], int]:
    """Return (live files, declared file count); fail closed on any declared path that is ABSENT.

    A declared scan root that silently does not exist NARROWS the scan, and a narrowed scan still prints ok -
    that is the silent error this rail exists to prevent (C16, audit F3). An exemption for an absent file is
    worse: it is a PERMISSION pre-registered for a file a future author has not written yet (audit F4).
    """
    rail = declared(policy, "reference_rail", "config/decisions_policy.yaml")
    reasons = rail.get("exempt_reasons") or {}
    exempt: set[str] = set()
    for rel in declared(rail, "exempt_paths", "reference_rail"):
        target = ROOT / str(rel)
        if not target.exists():
            raise SystemExit(
                f"FAIL {PREFIX}: exempt_paths names {rel}, which does not exist - a stale exemption is a "
                "permission nobody can be held to (D-2645)"
            )
        if not str(reasons.get(str(rel)) or "").strip():
            raise SystemExit(
                f"FAIL {PREFIX}: exempt_paths names {rel} with no exempt_reasons entry - an undocumented "
                "exemption is an over-permission, not a declaration (D-2642)"
            )
        exempt.add(str(target))
    paths: list[Path] = []
    for root in declared(rail, "scan_roots", "reference_rail"):
        base = ROOT / str(root)
        if not base.is_dir():
            raise SystemExit(
                f"FAIL {PREFIX}: scan_roots names {root}, which is not a directory - a scan root that "
                "silently does not exist narrows the scan (C16)"
            )
        paths.extend(sorted(base.rglob("*.py")))
    for name in declared(rail, "scan_files", "reference_rail"):
        candidate = ROOT / str(name)
        if not candidate.is_file():
            raise SystemExit(f"FAIL {PREFIX}: scan_files names {name}, which is not a file (C16)")
        paths.append(candidate)
    for pattern in declared(rail, "scan_globs", "reference_rail"):
        matched = sorted(ROOT.glob(pattern))
        if not matched:
            raise SystemExit(
                f"FAIL {PREFIX}: scan_globs {pattern!r} matches no file - a glob that matches nothing "
                "makes the scan look complete while reading nothing (C16)"
            )
        paths.extend(matched)
    return [p for p in paths if str(p) not in exempt], len({str(p) for p in paths})


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls: the rail must be seen firing AND silent on the archaeology (BUG-492).

    THE FIXTURE NAMESPACE (audit F1, MEASURED 2026-09-25). The controls originally used the LIVE revoked token
    as their fixture. Because scripts/** is inside this rail own scan set, declaring that token made the rail
    FIRE ON ITSELF - the first cascade the rail would have caused. The fixture now uses a RESERVED name that is
    not, and may not become, a revoked token: a detector that must exempt itself to pass is weaker than one that
    needs no exemption at all. A fixture colliding with production is a defect; a fixture namespace is the fix.
    """
    pats = build_patterns([FIXTURE_TOKEN, FIXTURE_IDS[0]])
    tmp = Path(tempfile.mkdtemp(prefix="revoked-refs-"))
    code = tmp / "code.py"
    code.write_text('x = row["' + FIXTURE_TOKEN + '"]  # D-9199' + chr(10) + "y = D9199" + chr(10), encoding="utf-8")
    doc = tmp / "doc.py"
    doc.write_text('"""' + FIXTURE_TOKEN + ' is abandoned (D-9199)."""' + chr(10) + "x = 1" + chr(10), encoding="utf-8")
    comment = tmp / "comment.py"
    comment.write_text("# " + FIXTURE_TOKEN + " D-9199" + chr(10) + "x = 1" + chr(10), encoding="utf-8")
    value = tmp / "value.yaml"
    value.write_text("col: " + FIXTURE_TOKEN + chr(10) + "ref: D-9199" + chr(10), encoding="utf-8")
    ycomment = tmp / "comment.yaml"
    ycomment.write_text("# " + FIXTURE_TOKEN + " D-9199" + chr(10) + "col: other" + chr(10), encoding="utf-8")
    other = tmp / "other.py"
    other.write_text('x = d["D-9198"]' + chr(10), encoding="utf-8")
    suffix = tmp / "suffix.py"
    suffix.write_text('x = row["' + FIXTURE_TOKEN + '_suffix"]' + chr(10), encoding="utf-8")
    return [
        ("a code string names the token", bool(python_refs(code, pats))),
        ("the dashed id is one token", any(t == FIXTURE_IDS[0] for _, t in python_refs(code, pats))),
        ("every fixture id is RESERVED and no reserved id is LIVE", fixtures_are_reserved()),
        ("a docstring is archaeology, not a reference", not python_refs(doc, pats)),
        ("a comment is not a reference", not python_refs(comment, pats)),
        ("a yaml VALUE is a reference", len(text_refs(value, pats)) == 2),
        ("a yaml comment is not a reference", not text_refs(ycomment, pats)),
        ("a different id is not a reference", not python_refs(other, pats)),
        # MEASURED 2026-09-26: this control's NAME named the LIVE subject ('epistemic_state'), so the rail found
        # one live reference to a revoked scope - its own known-answer fixture. A fixture names the RESERVED
        # token, never the revoked subject: the description is derived from FIXTURE_TOKEN like every other
        # fixture in this file, so the detector cannot trip on its own control.
        ("a PREFIX is not a reference (" + FIXTURE_TOKEN + " vs " + FIXTURE_TOKEN + "_suffix)",
         not python_refs(suffix, pats)),
    ]


def main(argv: list[str]) -> int:
    """Run the known-answer controls, or scan the live tree for references to a revoked scope."""
    ap = argparse.ArgumentParser(description="D-2645 anti-resurrection rail.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true", help="print the resolved revoked token set")
    args = ap.parse_args(argv)

    if args.selftest:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [n for n, ok in rows if not ok]
        if failed:
            print(f"FAIL {PREFIX} --selftest: {len(failed)} of {len(rows)} known-answer control(s) did not fire")
            return EXIT_REFERENCE
        print(f"ok {PREFIX} --selftest: {len(rows)}/{len(rows)} known-answer control(s) fire")
        return EXIT_CLEAN

    policy = load_yaml(POLICY)
    tokens, provenance = revoked_subject(policy)
    if args.list:
        for token in tokens:
            print(f"  revoked token {token!r} (declared by {provenance[token]})")
    if not tokens:
        print(f"owner-owed (loud, NOT fatal - BUG-457): no decision declares a revoked scope, so {PREFIX} has no subject")
        return EXIT_UNRESOLVABLE

    pats = build_patterns(tokens)
    owned, declared_total = scan_files(policy)
    findings: list[str] = []
    for path in owned:
        rel = path.relative_to(ROOT).as_posix()
        rows = python_refs(path, pats) if path.suffix == ".py" else text_refs(path, pats)
        for lineno, token in rows:
            findings.append(f"{rel}:{lineno} names revoked token {token!r} (declared by {provenance[token]})")
    if findings:
        print(f"FAIL {PREFIX}: {len(findings)} LIVE reference(s) to a revoked scope:")
        for line in findings[:40]:
            print("  !! " + line)
        print("  a tombstone stops execution; this rail stops re-proposal (D-2643/D-2645).")
        return EXIT_REFERENCE
    print(f"ok {PREFIX}: {len(tokens)} revoked token(s) named by no live file "
          f"({len(owned)} of {declared_total} declared file(s) scanned)")
    return EXIT_CLEAN


def fixtures_are_reserved() -> bool:
    """BUG-523: a fixture id must lie in the DECLARED reserved range, and the range must be empty in the registry.

    Found by a human asking what had to be ratified (2026-09-26): both fixture ids were drawn from the live decision
    space. The range is read from config (C12) - a hardcoded bound here would be a second home for the reservation.
    """
    root = Path(__file__).resolve().parent.parent
    policy = (root / "config" / "decisions_policy.yaml").read_text(encoding="utf-8")
    m = re.search(r"reserved_fixture_ids:\s*\n\s*range:\s*\[\s*D-(\d+)\s*,\s*D-(\d+)\s*\]", policy)
    if not m:
        print("  FAIL reference-rail: config/decisions_policy.yaml declares no reserved_fixture_ids.range")
        return False
    lo, hi = int(m.group(1)), int(m.group(2))
    for fid in FIXTURE_IDS:
        n = int(fid.split("-")[1])
        if not (lo <= n <= hi):
            print("  FAIL reference-rail: fixture id " + fid + " is OUTSIDE the reserved range D-" + str(lo) + "..D-" + str(hi))
            return False
    live = (root / "config" / "decisions.yaml").read_text(encoding="utf-8")
    for fid in FIXTURE_IDS:
        if re.search(r"\b" + fid + r"\b", live):
            print("  FAIL reference-rail: reserved fixture id " + fid + " EXISTS in config/decisions.yaml - the")
            print("       reservation is collided: rename the fixture, never the record (BUG-523)")
            return False
    return True


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
