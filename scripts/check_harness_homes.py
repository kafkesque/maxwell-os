#!/usr/bin/env python3
"""check_harness_homes.py — T-157: the harness homes a DECISION names, READ BACK as a rail.

WHY THIS EXISTS (measured, not asserted). MEASURED 2026-10-15: the client home declared at
`config/agent_context.yaml#homes.harness_config` read the ESCALATION provider while BUG-243 (CLOSED) rested on the
rationale that the engine provider was active and D-295 recorded the same remedy. That reversal was invisible for
months for one reason: this repository measures `config/*.yaml` to the KEY and never read the harness homes that
`homes` itself declares. A declaration nothing compares is a claim, not a bound fact (D-3034). T-174 then measured
the consequence from the other side: a headless run answered while the engine's OWN request counter did not move —
the session had left the machine while every declaration in the repository looked right.

WHAT IT READS. Every entry of `config/agent_context.yaml#home_facts` names a home (by pointer into `homes`), the
KEY to read inside it, and what the declaration says it must hold. Each is classified:

  BOUND                    the home says what the declaration says.
  CONFLICT                 it does not — a reversal, printed WITH the decision and the row that own it.
  WAITING-ON-A-HUMAN-WORD  no expectation is declared yet (`must_equal: null`): owner-owed, loud.
  UNREADABLE / ABSENT      the home, the key or a pointer cannot be read: FATAL, never BOUND (D-795 — an absent
                           surface is never reported as clean, and a fact nobody can read is not a fact).

It also prints the ENGINE'S OWN counter witness (`homes.engine_stats`) — the reading T-174 used by hand: a run
that answers while that number stands still is a run that left the machine.

READ-ONLY: it measures; it never writes a home. Fixing what it reports is an ACT
(`python3 pipeline/apply_provider_flip.py`, whose plan is dry-run by default).

Exit: 0 every fact BOUND | 1 FATAL (an unreadable home, key or pointer) | 2 CONFLICT or WAITING-ON-A-HUMAN-WORD,
loud and NOT fatal (BUG-457) | --selftest 0/1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

CONFIG = Path("config/agent_context.yaml")

BOUND, CONFLICT, WAITING, FATAL_STATE, WITNESS_ABSENT = "BOUND", "CONFLICT", "WAITING-ON-A-HUMAN-WORD", "FATAL", \
    "WITNESS-ABSENT"
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2

CONTROL_LABELS = (
    "a_home_that_says_what_the_declaration_says_reads_BOUND",
    "a_home_that_says_something_else_reads_CONFLICT_and_names_its_decision",
    "a_fact_with_no_declared_expectation_is_WAITING_ON_A_HUMAN_WORD",
    "an_absent_home_is_FATAL_and_never_BOUND",
    "a_declared_key_missing_from_the_home_is_FATAL",
    "an_unresolvable_pointer_is_FATAL_and_never_a_literal",
    "the_rail_names_no_home_path_key_or_provider_of_its_own",
)


class HomeError(SystemExit):
    """Fail-closed: an unreadable declaration is a fault, never a silent pass (C16)."""


def declared(doc: dict[str, Any], *path: str) -> Any:
    """Fail-closed navigation of a key the DECLARATION owns: absent is a fault, never a code default (C12)."""
    node: Any = doc
    for part in path:
        if not isinstance(node, dict) or part not in node:
            raise HomeError(f"FATAL: {CONFIG}#{'.'.join(path)} is not declared — this rail reads a declaration "
                            f"and restates none of it, so an absent key is a fault (C12/C16)")
        node = node[part]
    return node


def load(config: Path = CONFIG) -> dict[str, Any]:
    """Read the one home. Unreadable/unparseable is FATAL (C16); nothing here is defaulted."""
    import yaml

    try:
        doc = yaml.safe_load(config.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — any failure means this rail cannot know anything
        raise HomeError(f"FATAL: {config} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(doc, dict):
        raise HomeError(f"FATAL: {config} is not a mapping — there is no declaration to read")
    return doc


def home_path(homes: dict[str, Any], name: str) -> Path:
    """The declared home as a Path. A '~' path is the OWNER's home, written here and never mirrored (D-2646)."""
    if name not in homes:
        raise HomeError(f"FATAL: home_facts names the home {name!r}, which `homes` does not declare")
    return Path(str(homes[name])).expanduser()


def resolve_pointer(ref: str) -> str:
    """'@config/x.yaml#a.b' -> the value in its one home, through the repo's ONE pointer resolver (D-2646)."""
    from pipeline.harness_env import (
        resolve,  # never re-implemented, and it raises on a broken pointer
    )

    return resolve(ref)


def key_path(template: str, doc: dict[str, Any]) -> str:
    """Resolve the `<provider>` / `<escalation_provider>` tokens in a declared key path from engine.yaml.

    The tokens exist so this config never has to restate a provider name to point at a provider's block: the
    provider ids live in config/engine.yaml#harnesses, which is the home that owns them (C12).
    """
    tokens = {
        "provider": str(declared(doc, "harnesses", "goose_provider_id")),
        "escalation_provider": str(declared(doc, "harnesses", "escalation_provider_id")),
    }
    resolved = template
    for token, value in tokens.items():
        resolved = resolved.replace(f"<{token}>", value)
    if "<" in resolved:
        raise HomeError(f"FATAL: the declared key path {template!r} uses a token this rail does not declare "
                        f"(declared tokens: {sorted(tokens)})")
    return resolved


def dig(node: Any, dotted: str) -> tuple[Any, bool]:
    """Navigate a dotted key path inside a home. Returns (value, found) — never a silent None (D-795)."""
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def normalise(value: Any) -> str:
    """Compare facts as text: YAML booleans and numbers must not read as a mismatch against a declared string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def witness(homes: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    """The engine's own request counter, declared as homes.engine_stats = 'path#dotted.key'.

    A reading, not a gate: the counter is the one witness that says whether a session was served BY THIS MACHINE
    (T-174/BUG-849 used it by hand). An absent witness is printed and is NOT fatal — the engine may simply not
    have served anything yet — but it is never silently zero (D-2957).
    """
    if "engine_stats" not in homes:
        return {"state": WITNESS_ABSENT, "detail": "homes.engine_stats is not declared", "value": None}
    ref = str(homes["engine_stats"])
    path_text, _, dotted = ref.partition("#")
    path = Path(path_text).expanduser()
    if not path.exists():
        return {"state": WITNESS_ABSENT, "detail": f"{path} does not exist yet", "value": None}
    try:
        node: Any = json.loads(path.read_text(encoding="utf-8")) if not dotted else None
        if dotted:
            node = json.loads(path.read_text(encoding="utf-8"))
            node, found = dig(node, dotted)
            if not found:
                return {"state": WITNESS_ABSENT, "detail": f"{ref} carries no such key", "value": None}
    except Exception as exc:  # noqa: BLE001 — an unreadable witness is reported, never guessed
        return {"state": WITNESS_ABSENT, "detail": f"unreadable ({type(exc).__name__}: {exc})", "value": None}
    import time

    age = time.time() - path.stat().st_mtime
    return {"state": "READ", "detail": f"declared at {ref}, last written {age / 60:.1f} min ago",
            "value": normalise(node), "path": str(path)}


def census(config: Path = CONFIG) -> dict[str, Any]:
    """Read every declared fact back from the home that owns it. Never writes, never defaults."""
    doc = load(config)
    homes = declared(doc, "homes")
    facts = declared(doc, "home_facts")
    if not isinstance(facts, list) or not facts:
        raise HomeError(f"FATAL: {config}#home_facts must be a non-empty list of declared facts (C12/C16)")
    engine = load(_PROJECT_ROOT / "config/engine.yaml")
    rows: list[dict[str, Any]] = []
    for fact in facts:
        for key in ("id", "home", "key", "must_equal", "decided_by"):
            if key not in fact:
                raise HomeError(f"FATAL: the fact {fact.get('id')!r} does not declare {key!r} — a fact without an "
                                f"owner or an expectation is a claim nobody can read (D-3034)")
        path = home_path(homes, str(fact["home"]))
        row: dict[str, Any] = {"id": str(fact["id"]), "home": str(fact["home"]), "path": str(path),
                               "decided_by": [str(d) for d in fact["decided_by"]],
                               "row": str(fact.get("row") or ""), "key": "", "want": "", "have": ""}
        if not path.exists():
            row.update(state=FATAL_STATE, detail=f"the declared home does not exist: {path}")
            rows.append(row)
            continue
        try:
            want_raw = fact["must_equal"]
            if want_raw is None:
                row.update(state=WAITING, detail="no expectation declared yet — the owner's word decides it")
            else:
                want = resolve_pointer(str(want_raw)) if str(want_raw).startswith("@") else normalise(want_raw)
                keyed = key_path(str(fact["key"]), engine)
                row["key"] = keyed
                row["want"] = want
                home_doc = load(path)
                have_raw, found = dig(home_doc, keyed)
                if not found:
                    row.update(state=FATAL_STATE,
                               detail=f"the home does not carry the declared key {keyed!r} — a fact nobody can "
                                      f"read is not a fact (D-795)")
                elif normalise(have_raw) != want:
                    row.update(state=CONFLICT, have=normalise(have_raw),
                               detail=f"the home says {normalise(have_raw)!r}, the declaration says {want!r}")
                else:
                    row.update(state=BOUND, have=normalise(have_raw))
        except HomeError as exc:
            row.update(state=FATAL_STATE, detail=str(exc))
        except SystemExit as exc:  # an unresolvable '@' pointer raises SystemExit inside the resolver
            row.update(state=FATAL_STATE, detail=f"the declared pointer does not resolve: {exc}")
        rows.append(row)
    states = {row["state"] for row in rows}
    rc = RC_FATAL if FATAL_STATE in states else (RC_OWNER_OWED if states & {CONFLICT, WAITING} else RC_OK)
    return {"rc": rc, "config": str(config), "rows": rows, "witness": witness(homes, doc),
            "facts": len(rows),
            "bound": sum(1 for row in rows if row["state"] == BOUND),
            "conflict": sum(1 for row in rows if row["state"] == CONFLICT),
            "waiting": sum(1 for row in rows if row["state"] == WAITING),
            "fatal": sum(1 for row in rows if row["state"] == FATAL_STATE)}


def report(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the census in the units the owner acts on: one line per fact, with its owner and its row."""
    print(f"harness homes: {rep['facts']} declared fact(s) | bound {rep['bound']} | conflicting "
          f"{rep['conflict']} | waiting {rep['waiting']} | unreadable {rep['fatal']}", file=stream)
    for row in rep["rows"]:
        owner = ",".join(row["decided_by"]) or "no decision"
        where = f"{row['home']}#{row['key']}" if row["key"] else row["home"]
        line = f"  {row['state']:<24} {row['id']} ({where}) — {owner}"
        if row.get("row"):
            line += f", {row['row']}"
        if row["state"] in (CONFLICT, FATAL_STATE):
            line += f": {row.get('detail', '')}"
        print(line, file=stream)
    wit = rep["witness"]
    print(f"  engine counter witness: {wit.get('value') or wit['state']} ({wit['detail']})", file=stream)


def selftest() -> int:
    """Known-answer controls, each over a synthetic home in a temp dir (no repo fixture, BUG-577)."""
    import tempfile

    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    def fixture(root: Path, home_text: str, *, must_equal: Any = "vendor_b", key: str = "active_provider",
                home_name: str = "harness_config", write_home: bool = True) -> Path:
        if write_home:
            (root / "client.yaml").write_text(home_text, encoding="utf-8")
        cfg = root / "agent_context.yaml"
        cfg.write_text(
            "homes:\n"
            f"  {home_name}: '{root / 'client.yaml'}'\n"
            "  engine_stats: '/nonexistent/engine_stats.json#total_requests'\n"
            "home_facts:\n"
            "  - id: the_fact\n"
            f"    home: {home_name}\n"
            f"    key: '{key}'\n"
            f"    must_equal: {json.dumps(must_equal)}\n"
            "    decided_by: [D-295]\n"
            "    row: T-157\n", encoding="utf-8")
        return cfg

    with tempfile.TemporaryDirectory(prefix="harness_homes_") as tmp:
        root = Path(tmp)
        cfg = fixture(root, "active_provider: vendor_b\n")
        rep = census(cfg)
        if rep["rows"][0]["state"] != BOUND or rep["rc"] != RC_OK:
            mark(CONTROL_LABELS[0], f"a matching home read {rep['rows'][0]['state']} rc {rep['rc']}")

        (root / "client.yaml").write_text("active_provider: someone_else\n", encoding="utf-8")
        rep = census(cfg)
        if rep["rows"][0]["state"] != CONFLICT or rep["rc"] != RC_OWNER_OWED:
            mark(CONTROL_LABELS[1], f"a reversed home read {rep['rows'][0]['state']} rc {rep['rc']}")
        if "D-295" not in rep["rows"][0]["decided_by"] or rep["rows"][0]["row"] != "T-157":
            mark(CONTROL_LABELS[1], "the conflict does not name the decision and the row that own it")
        if "someone_else" not in rep["rows"][0]["detail"]:
            mark(CONTROL_LABELS[1], "the conflict does not print what the home actually says")

        (root / "client.yaml").write_text("active_provider: vendor_b\n", encoding="utf-8")
        waiting_cfg = fixture(root, "", must_equal=None)
        rep = census(waiting_cfg)
        if rep["rows"][0]["state"] != WAITING or rep["rc"] != RC_OWNER_OWED:
            mark(CONTROL_LABELS[2], f"a fact with no expectation read {rep['rows'][0]['state']} rc {rep['rc']}")

        absent = fixture(root, "", write_home=False)
        rep = census(absent)
        if rep["rows"][0]["state"] != FATAL_STATE or rep["rc"] != RC_FATAL:
            mark(CONTROL_LABELS[3], f"an ABSENT home read {rep['rows'][0]['state']} rc {rep['rc']}")

        cfg_key = fixture(root, "providers:\n  vendor_b:\n    enabled: true\n", key="providers.vendor_b.model")
        rep = census(cfg_key)
        if rep["rows"][0]["state"] != FATAL_STATE:
            mark(CONTROL_LABELS[4], f"a key the home does not carry read {rep['rows'][0]['state']}")

        cfg_ptr = fixture(root, "active_provider: vendor_b\n", must_equal="@config/does_not_exist.yaml#a.b")
        rep = census(cfg_ptr)
        if rep["rows"][0]["state"] != FATAL_STATE:
            mark(CONTROL_LABELS[5], f"an unresolvable pointer read {rep['rows'][0]['state']}")

        own = Path(__file__).resolve().read_text(encoding="utf-8")
        # The measured reversal QUOTED in the module docstring is EVIDENCE (D-3038), not a restatement this rail
        # runs on, so the leak check reads the CODE: comments and the module docstring are stripped first. What it
        # forbids is the rail OWNING a home path, a key or a provider name of its own.
        code = re.sub(r"(?m)#.*$", "", re.sub(r'""".*?"""', "", own, count=1, flags=re.S))
        if re.search(r"['\"]~/", code):
            mark(CONTROL_LABELS[6], "the rail restates a home path of its own in code")
        # The names to look for are READ FROM THEIR DECLARATION, never written into this control: a literal list
        # here would match itself and the control could never pass (the same self-reference the surface rail
        # caught). A declared provider name QUOTED in this rail's code would be a second home for it (C12).
        engine = load(_PROJECT_ROOT / "config/engine.yaml")
        for literal in (str(engine["harnesses"]["goose_provider_id"]),
                        str(engine["harnesses"]["escalation_provider_id"])):
            if re.search(rf"['\"]{re.escape(literal)}", code):
                mark(CONTROL_LABELS[6], f"the rail quotes the declared provider {literal!r} in code")

    failed = {label for label, _ in failures}
    for label in CONTROL_LABELS:
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    for label, detail in failures:
        print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
    if failures:
        return RC_FATAL
    print(f"selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} controls green")
    return RC_OK


def main(argv: list[str] | None = None) -> int:
    """CLI: (default) the census | --json | --selftest."""
    parser = argparse.ArgumentParser(description="The harness homes a decision names, read back (T-157).")
    parser.add_argument("--json", action="store_true", help="emit the census as JSON")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls (no live home, no writes)")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    try:
        rep = census()
    except HomeError as exc:
        print(str(exc), file=sys.stderr)
        return RC_FATAL
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        report(rep)
    return int(rep["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
