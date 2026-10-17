#!/usr/bin/env python3
"""goose_profile.py - COMPOSE A SESSION'S EXTENSION SET FROM A DECLARED POLICY (T-186/D-3056).

WHY THIS EXISTS. goose already can start a session with no default extensions at all
(`--no-profile`) and add exactly the ones named on the command line (`--with-builtin`,
`--with-extension`). MEASURED 2026-10-17, two-sided: `--no-profile --with-builtin developer`
started with ZERO warnings and answered, while `--no-profile --with-builtin developer,not_a_real_extension`
printed `Warning: Failed to start extension 'not_a_real_extension' ... continuing without it`. So the RELAXATION is
real and it is the harness's, not ours. What was missing is the POLICY: which extensions may be resident at all, and
which of them a given session needs. That policy lives in config/extension_profiles.yaml.

THE TWO REALISATIONS, each printed only in the form it was MEASURED in:
  (a) THE PERSISTENT ONE - flip `enabled:` in the harness config. This is how goose actually persists an extension,
      it is the form every live extension is already in, and it takes effect at the NEXT session's birth (a running
      session keeps the surface it was born with - AGENTS.md harness fact). This script NEVER writes that file: it
      PRINTS the exact flips, because editing the owner's home is an owner act.
  (b) THE PER-SESSION ONE - `goose run --no-profile --with-builtin A,B --with-extension '<cmd> <args>'`. Measured for
      platform/builtin names. A stdio command whose arguments contain WHITESPACE cannot be passed through the
      documented single-string form without a quoting assumption, so those are marked UNVERIFIED rather than
      silently emitted as if they worked (C16: a claim that has not been measured is not a claim).

ADOPTION ON ARRIVAL (D-3060). An extension that arrives from the internet, or from a harness upgrade, has no
classification - and the rail already refuses to call that clean. `--adopt` makes the REGISTRATION automatic
(new names land in `quarantine`, refused by every profile) while leaving the DECISION to a human, because the only
thing an arrival proves is that bytes exist. Quarantine is reported OWNER-OWED (rc 2), so it is loud on every run
and fatal to nothing.

THE SUBAGENT SURFACE. A delegate is its own session and pays its own schema tax, so `--delegate NAME` renders the
exact `extensions:` list a delegate should be born with, checked against the harness declaration first (a name the
harness does not declare is refused, D-3034).

THREE FACTS DECIDE THE VERDICT, never a count:
  * POLICY vs STATE. config/extension_profiles.yaml classifies every extension `always` / `on_demand` / `never`;
    the harness config declares `enabled`. Agreement is rc 0. A disagreement is OWNER-OWED (rc 2), because flipping
    the owner's config is their act - and it is reported as a LIST, with the measured token cost of each, not as a
    number.
  * TOTALITY (C16). An extension the policy does not classify is not "fine" - it is an unowned decision, which is a
    FAULT (rc 1), not a warning.
  * RESOLUTION (D-3034). A name in the policy that the harness config does not declare is a FAULT. So is a profile
    that adds a name it may not add (an unknown name, or one classified `never`).

THE BIRTH, AND WHY IT IS A COMMAND (D-3064). A profile that is only RENDERED is a policy nobody performs. `--launch`
executes the per-session form - so a task-labelled session is one word (`just session workshop`), the surface is
EXPLICIT rather than inherited, and the OS can say afterwards what the session was GIVEN. Two refusals make it a
control instead of a convenience: a profile the policy does not declare cannot be born, and a profile whose stdio
member would start DEAD cannot be born either (a dead extension prints its failure to the TERMINAL, the session
continues without it, and from the inside the two are indistinguishable - MEASURED 2026-10-17).

`--born` answers the question no transcript can: WHAT SURFACE WAS THIS SESSION GIVEN? It reads the harness's own
record (`enabled_extensions.v0` in the session store, resolved through config/agent_context.yaml), maps the display
names the record carries back to the policy's keys, and reports the profile the surface EQUALS - or that it equals
none. A session born before the harness recorded a surface reads NOT RECORDED, never "empty" (C16).

Usage:
  python3 scripts/goose_profile.py --list
  python3 scripts/goose_profile.py --render workshop
  python3 scripts/goose_profile.py --launch workshop   # BIRTH; refuses a dead member; replaces this process
  python3 scripts/goose_profile.py --born 5            # what the last 5 sessions were GIVEN at birth
  python3 scripts/goose_profile.py --check          # tri-state: 0 agree | 1 FAULT | 2 owner-owed drift
  python3 scripts/goose_profile.py --selftest
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
POLICY = REPO / "config" / "extension_profiles.yaml"
FLIP_WRITER = REPO / "agent" / "adapters" / "goose" / "apply_provider_flip.py"

ALWAYS, ON_DEMAND, NEVER, UNCLASSIFIED = "always", "on_demand", "never", "UNCLASSIFIED"
#: Quarantine is NOT a fourth class of residency - it is the ABSENCE of a decision, and it grants none.
QUARANTINE = "quarantine"
CLASSES = ((ALWAYS, "always"), (ON_DEMAND, "on_demand"), (NEVER, "never"), (QUARANTINE, "quarantine"))


def declared_home() -> pathlib.Path:
    """The harness config path, RESOLVED from its one declared home (C21: one resolver).

    Returns:
        The path the harness itself reads its extension declarations from.

    Raises:
        SystemExit: when the declaration cannot be loaded - FATAL, never a default (C16).
    """
    spec = importlib.util.spec_from_file_location("_provider_flip", FLIP_WRITER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FATAL: cannot load the declared resolver from {FLIP_WRITER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.declared_home()


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Parse a YAML mapping, fail closed.

    Args:
        path: the file to parse.

    Returns:
        The mapping (empty when the file is empty).

    Raises:
        SystemExit: when the file is absent, unreadable or not a mapping.
    """
    import yaml

    if not path.exists():
        raise SystemExit(f"FATAL: {path} does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"FATAL: {path} is not a mapping")
    return data


def classify(policy: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Turn the policy's class lists into one name -> class map, and report any name in two classes.

    Args:
        policy: the parsed config/extension_profiles.yaml.

    Returns:
        (classes, faults) where faults names every ambiguity. A name declared twice is a FAULT, not a last-wins
        (C12: one home means one answer). QUARANTINE is carried in the same map so a quarantined name RESOLVES
        (D-3034) while granting nothing.
    """
    classes: dict[str, str] = {}
    faults: list[str] = []
    for cls, key in CLASSES:
        declared = policy.get(key) or []
        names = declared if isinstance(declared, list) else list(declared)
        for raw in names:
            name = str(raw).strip()
            if name in classes:
                faults.append(f"{name} is classified TWICE ({classes[name]} and {cls}) - one extension, one class")
                continue
            classes[name] = cls
    return classes, faults


def profile_members(policy: dict[str, Any], classes: dict[str, str], profile: str) -> list[str]:
    """Resolve a profile name to the extensions a session would be born with.

    Args:
        policy: the parsed policy.
        classes: the name -> class map.
        profile: the profile to resolve.

    Returns:
        Always-class extensions plus the profile's additions, order-stable and de-duplicated.

    Raises:
        SystemExit: when the profile is not declared, or adds a name it may not add (fail closed, D-3034).
    """
    profiles = policy.get("profiles") or {}
    if profile not in profiles:
        raise SystemExit(
            f"REFUSED: profile {profile!r} is not declared. Declared: {', '.join(sorted(profiles)) or '(none)'}"
        )
    adds = [str(x) for x in ((profiles[profile] or {}).get("adds") or [])]
    for name in adds:
        if name not in classes:
            raise SystemExit(f"REFUSED: profile {profile!r} adds {name!r}, which the policy does not classify")
        if classes[name] == NEVER:
            raise SystemExit(f"REFUSED: profile {profile!r} adds {name!r}, which the policy classifies NEVER")
        if classes[name] == QUARANTINE:
            raise SystemExit(
                f"REFUSED: profile {profile!r} adds {name!r}, which is QUARANTINED - an arrival is not a decision"
                f" (D-3060); classify it in always / on_demand / never first"
            )
    members = [n for n, c in classes.items() if c == ALWAYS]
    return members + [n for n in adds if n not in members]


def check(policy: dict[str, Any], config: dict[str, Any]) -> tuple[int, list[str], list[str], list[str]]:
    """Compare the POLICY against the harness STATE, in the three states the rail registry can report.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.

    Returns:
        (rc, faults, drift, pending): rc 0 agree / 1 fault / 2 owner-owed; faults are structural; drift is
        policy-vs-state; pending is every QUARANTINED extension (registered on arrival, no decision yet).
    """
    classes, faults = classify(policy)
    extensions = config.get("extensions") or {}
    if not isinstance(extensions, dict) or not extensions:
        return 1, ["the harness config declares no extensions - the comparison has no subject"], [], []

    for name in sorted(classes):
        if name not in extensions:
            faults.append(f"{name} is classified {classes[name]} but the harness config does not declare it (D-3034)")

    for name in sorted(extensions):
        if name not in classes:
            faults.append(f"{name} is declared by the harness and NOT classified by the policy - an unowned decision (C16)")

    for profile in sorted(policy.get("profiles") or {}):
        try:
            profile_members(policy, classes, profile)
        except SystemExit as exc:
            faults.append(str(exc))

    # THE SUBJECT IS THE DECLARED DEFAULT, not the always minimum: a session default is a decision, and
    # comparing against a minimum would report a deliberate choice as drift for ever (a rail that cries wolf).
    default = str(policy.get("default_profile") or "")
    try:
        expected = set(profile_members(policy, classes, default)) if default else {n for n, c in classes.items() if c == ALWAYS}
    except SystemExit as exc:
        faults.append(str(exc))
        expected = {n for n, c in classes.items() if c == ALWAYS}

    drift: list[str] = []
    pending: list[str] = []
    quarantine = policy.get("quarantine") or {}
    for name in sorted(quarantine if isinstance(quarantine, dict) else {n: {} for n in quarantine}):
        entry = quarantine.get(name) if isinstance(quarantine, dict) else {}
        stamp = (entry or {}).get("adopted") if isinstance(entry, dict) else None
        pending.append(
            f"{name}: QUARANTINED {stamp or '(undated)'} - registered on arrival, granted NOTHING, refused by every"
            f" profile; classify it (always / on_demand / never) with a `why`"
        )
    for name, cfg in sorted(extensions.items()):
        if name not in classes or classes[name] == QUARANTINE:
            continue
        enabled = bool(isinstance(cfg, dict) and cfg.get("enabled"))
        if name in expected and not enabled:
            drift.append(f"{name}: the declared default ENABLES it but the harness has it DISABLED")
        elif name not in expected and enabled:
            drift.append(f"{name}: classified {classes[name]}, not part of the declared default, but ENABLED")

    # A DELEGATE PROFILE NAMES WHAT A CHILD IS BORN WITH - AND A CHILD CAN ONLY BE GIVEN WHAT THE CONFIG ENABLES.
    # MEASURED 2026-10-17 two-sided (D-3067): a subagent asked for ["developer","filesystem"] while `filesystem` was
    # DISABLED was born with `developer` ALONE (session 20261017_15), and the same mechanism provisioned
    # ["analyze","memory"] exactly when both were ENABLED (session 20261017_16). So `enabled:` is not merely the
    # session default - it is a GATE on named provisioning, and a delegate profile naming a disabled extension is a
    # declaration that resolves to nothing. Reported here so it is a reading, never a worker's silent missing tool.
    for delegate, spec in sorted((policy.get("delegate_profiles") or {}).items()):
        if not isinstance(spec, dict):
            continue
        for name in [str(x) for x in (spec.get("extensions") or [])]:
            if name not in extensions:
                faults.append(
                    f"delegate profile {delegate!r} names {name!r}, which the harness does not declare (D-3034)")
            elif not bool((extensions.get(name) or {}).get("enabled")):
                drift.append(
                    f"delegate profile {delegate!r} names {name!r}, but the harness has it DISABLED - a child born"
                    f" with that list is provisioned WITHOUT it (D-3067)")

    if faults:
        return 1, faults, drift, pending
    return (2 if drift or pending else 0), faults, drift, pending


def _costs(policy: dict[str, Any]) -> dict[str, Any]:
    """Per-extension measured cost, read from the receipt the policy points at.

    Args:
        policy: the parsed policy (its measured_by pointer names the receipt).

    Returns:
        name -> receipt row. Empty when the receipt is absent - an absent reading is ABSENT, never zero (D-2957).
    """
    pointer = str((policy.get("measured_by") or {}).get("receipt") or "")
    path = REPO / pointer if pointer else None
    if not path or not path.exists():
        return {}
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(r.get("name")): r for r in receipt.get("rows") or [] if isinstance(r, dict)}


def render(policy: dict[str, Any], config: dict[str, Any], classes: dict[str, str], profile: str) -> str:
    """Print the two realisations of one profile, each in the form it has been measured in.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.
        classes: the name -> class map.
        profile: the profile to render.

    Returns:
        A human-readable plan. Writes nothing.
    """
    members = profile_members(policy, classes, profile)
    extensions = config.get("extensions") or {}
    costs = _costs(policy)

    lines = [f"PROFILE {profile} - {len(members)} extension(s)", ""]
    flips_on = [n for n in members if n in extensions and not (extensions[n] or {}).get("enabled")]
    flips_off = [n for n in extensions if n not in members and (extensions[n] or {}).get("enabled")]
    lines.append("(a) PERSISTENT realisation - set `enabled:` in " + str(declared_home()))
    for name in flips_on:
        lines.append(f"      enable  {name}")
    for name in flips_off:
        row = costs.get(name) or {}
        cost = f"  (frees ≈{row['tokens_est']} tok/request)" if row.get("tokens_est") else ""
        lines.append(f"      disable {name}{cost}")
    if not flips_on and not flips_off:
        lines.append("      already in this state")

    builtin = [n for n in members if (extensions.get(n) or {}).get("type") in ("platform", "builtin")]
    stdio = [n for n in members if (extensions.get(n) or {}).get("type") == "stdio"]
    lines += ["", "(b) PER-SESSION realisation - born this way, leaves no trace in the config"]
    cmd = "goose run --no-profile"
    if builtin:
        cmd += f" --with-builtin {','.join(builtin)}"
    unverified: list[str] = []
    for name in stdio:
        cfg = extensions.get(name) or {}
        parts = [str(cfg.get("cmd") or "")] + [str(a) for a in (cfg.get("args") or [])]
        if not "".join(parts).strip():
            unverified.append(f"{name}: declares no cmd (D-3034)")
            continue
        resolved = [str(_abs_script(p, cfg, pathlib.Path.cwd()))
                    if p and not p.startswith("-") and SCRIPTISH.search(p) else p for p in parts]
        for p in resolved:
            if SCRIPTISH.search(p) and not pathlib.Path(p).exists():
                unverified.append(f"{name}: {p} does not exist - the extension would be born DEAD")
        cmd += " --with-extension '" + " ".join(_quoted(p) for p in resolved) + "'"
    lines.append("      " + cmd)
    for note in unverified:
        lines.append(f"      UNVERIFIED {note}")
    measured = [costs[n] for n in members if n in costs and costs[n].get("tokens_est")]
    if measured:
        total = sum(int(r["tokens_est"]) for r in measured)
        lines.append(f"      measured schema cost of the MEASURED members: ≈{total} tokens per request")
    lines.append("      (platform/builtin schema bytes are NOT measured - absent, not zero, D-2957)")
    return "\n".join(lines)


#: The harness's OWN record of the surface a session was GIVEN at birth. READ, never restated (C12): the path and
#: the key live in one declared place, and this file names neither of its own.
AGENT_CONTEXT = REPO / "config" / "agent_context.yaml"
#: The key the harness stores that surface under (MEASURED 2026-10-17, BUG-873 limb b). A session born before
#: 2026-10-13 carries NO such key: it must read NOT RECORDED, never "empty" - an absence is not a zero (C16).
SURFACE_KEY = "enabled_extensions.v0"
NOT_RECORDED = "NOT RECORDED"
BORN_DEFAULT = 5
#: An argument with this shape is a SCRIPT PATH, resolved against the cwd at birth. A RELATIVE one is a death
#: sentence for any session not launched from the same directory - MEASURED two-sided 2026-10-17: the declared
#: `docguard` command (`python3 mcp_doc_guard.py`) starts from the repo root and fails from /tmp, and the harness
#: prints that failure to the TERMINAL and lets the session continue WITHOUT the write gate.
SCRIPTISH = re.compile(r"\.(?:py|js|mjs|cjs|sh|rb)$")


def sessions_db() -> pathlib.Path:
    """The harness session store, resolved from its ONE declared pointer (C12: no second home for a path).

    Returns:
        The sqlite path. The pointer is '<path>#<table>'; only the path is used here.

    Raises:
        SystemExit: when the pointer is absent - a reader with a hardcoded home would be the defect this avoids.
    """
    doc = _yaml(AGENT_CONTEXT)
    pointer = str((doc.get("homes") or {}).get("cache_ledger") or "").strip()
    if not pointer:
        raise SystemExit(
            f"FATAL: {AGENT_CONTEXT.name}#homes.cache_ledger is not declared, so the session store has no home"
        )
    return pathlib.Path(os.path.expanduser(pointer.split("#", 1)[0]))


def display_names(config: dict[str, Any]) -> dict[str, str]:
    """Map the DISPLAY name each session record carries back to the KEY the policy classifies.

    Args:
        config: the parsed harness config.

    Returns:
        display name -> key, and key -> key (so a record that already holds a key resolves too). The harness
        records 'Extension Manager' where the policy says 'extensionmanager'; without this map the comparison
        would read a matching surface as a stranger.
    """
    out: dict[str, str] = {}
    for key, cfg in (config.get("extensions") or {}).items():
        out[str(key)] = str(key)
        out[str((cfg or {}).get("name") or key)] = str(key)
    return out


def born_sessions(db: pathlib.Path, limit: int) -> list[dict[str, Any]]:
    """Read the last `limit` sessions and the surface each was GIVEN at birth - from the harness's own store.

    Args:
        db: the session store (see sessions_db).
        limit: how many of the newest sessions to read.

    Returns:
        One row per session: id, created, name, type, surface (None = NOT RECORDED), extensions (raw count).

    Raises:
        SystemExit: when the store is absent - a reading of nothing is not a reading.
    """
    import sqlite3

    if not db.exists():
        raise SystemExit(f"FATAL: the harness session store {db} does not exist - nothing to read")
    rows: list[dict[str, Any]] = []
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "select id, created_at, name, session_type, extension_data from sessions "
            "order by created_at desc, id desc limit ?",
            (int(limit),),
        )
        for sid, created, name, stype, blob in cur.fetchall():
            surface: list[str] | None = None
            try:
                data = json.loads(blob or "{}")
            except (json.JSONDecodeError, TypeError):
                data = {}
            entry = data.get(SURFACE_KEY) if isinstance(data, dict) else None
            if isinstance(entry, dict) and isinstance(entry.get("extensions"), list):
                surface = [
                    str(e.get("name") if isinstance(e, dict) else e) for e in entry["extensions"]
                ]
            rows.append(
                {
                    "id": str(sid),
                    "created": str(created or ""),
                    "name": str(name or ""),
                    "type": str(stype or ""),
                    "surface": surface,
                }
            )
    finally:
        conn.close()
    return rows


def profile_of(surface_keys: set[str], policy: dict[str, Any], classes: dict[str, str]) -> list[str]:
    """Every declared profile whose member set EQUALS this surface - a match, never a guess.

    Args:
        surface_keys: the born surface, mapped to policy keys.
        policy: the parsed policy.
        classes: the name -> class map.

    Returns:
        The profiles the surface IS. Empty when it equals no declared profile - which is a reading, not a fault:
        a session may legitimately be born with a set no profile names.
    """
    out: list[str] = []
    for name in (policy.get("profiles") or {}):
        try:
            members = set(profile_members(policy, classes, str(name)))
        except SystemExit:
            continue
        if members == surface_keys:
            out.append(str(name))
    return out


def render_born(rows: list[dict[str, Any]], policy: dict[str, Any], classes: dict[str, str],
                config: dict[str, Any]) -> str:
    """Print the surface each session was born with, and which declared profile - if any - it equals.

    Args:
        rows: the output of born_sessions.
        policy: the parsed policy.
        classes: the name -> class map.
        config: the parsed harness config.

    Returns:
        The reading, one block per session.
    """
    names = display_names(config)
    lines: list[str] = []
    for row in rows:
        lines.append(f"{row['id']}  {row['created']}  [{row['type']}] {row['name'][:46]!r}")
        surface = row["surface"]
        if surface is None:
            lines.append(f"   surface: {NOT_RECORDED} (born before the harness recorded one, or by a build that does not)")
            lines.append("")
            continue
        keys = {names.get(str(n), str(n)) for n in surface}
        unknown = sorted(k for k in keys if k not in classes)
        matched = profile_of(keys, policy, classes)
        lines.append(f"   surface: {len(surface)} extension(s) -> " +
                     (", ".join(matched) if matched else "NO DECLARED PROFILE"))
        if unknown:
            lines.append(f"   !! {len(unknown)} name(s) the policy does not classify: {', '.join(unknown)}")
        lines.append("")
    return "\n".join(lines).rstrip()


#: The ONE override a human may set without naming a profile on the command line (D-3065). A profile is RESOLVED,
#: never remembered: the resolver is deterministic, so no model and no memory decides a session's surface.
PROFILE_ENV = "MAXWELL_PROFILE"


def _abs_script(part: str, cfg: dict[str, Any], birth_cwd: pathlib.Path) -> pathlib.Path:
    """Resolve a declared SCRIPT argument IN THE DECLARATION'S OWN CONTEXT, then the birth directory.

    WHY THIS ORDER (MEASURED 2026-10-17, BUG-878 RE-SCOPED). The harness starts a CONFIG-declared stdio extension in
    the `cwd` that declaration carries, so `args: [mcp_doc_guard.py]` beside `cwd: <repo>` starts from `<repo>` even
    when the session was born in /tmp - MEASURED: session 20261017_10, born in /private/tmp, 12 extensions, ZERO
    start warnings. A `--with-extension` string carries NO cwd, so the SAME declaration resolves against the
    caller's directory and dies there - MEASURED: the failing invocation, whose surface records a member named
    `python3` and no cwd. The declaration's context is therefore FIRST; the caller's directory is only a fallback.
    Resolving in the caller's context is the defect, whichever route is used.

    Args:
        part: one declared command part.
        cfg: that extension's declaration (its `cwd` is the context it will be started in).
        birth_cwd: the directory the session is being born in.

    Returns:
        An ABSOLUTE path. It may not exist: the caller checks, because a refusal must name what it looked for.
    """
    raw = pathlib.Path(os.path.expanduser(part))
    if raw.is_absolute():
        return raw
    declared = str(cfg.get("cwd") or "").strip()
    if declared:
        candidate = pathlib.Path(os.path.expanduser(declared)) / raw
        if candidate.exists():
            return candidate
    return birth_cwd / raw


def _quoted(part: str) -> str:
    """Quote a part for the harness's single-string extension form when it contains whitespace.

    MEASURED 2026-10-17: `--with-extension 'python3 "<path with a space>/mcp_doc_guard.py"'` starts with ZERO
    warnings from /tmp (session 20261017_11), so the quoted form IS verified for a PATH argument. The unquoted form
    of the same path is not verified - and it is what made a sound declaration look directory-dependent.

    Args:
        part: one resolved command part.

    Returns:
        The part, quoted only when quoting is needed.
    """
    return f'"{part}"' if any(c.isspace() for c in part) else part


def resolve_profile(policy: dict[str, Any], environ: dict[str, str] | None = None) -> tuple[str, str]:
    """The profile a birth uses when none is NAMED, and the reason - deterministic, auditable, model-free.

    WHY RESOLVED AND NOT CHOSEN (D-3065). Requiring a human to remember which of eight profiles to name is a
    cognitive tax on the one act that must never be got wrong, and an LLM router would add a failure mode, a
    latency and its own token cost to the BIRTH - where nothing is measured yet. Precedence is therefore a two-line
    rule an operator can hold in their head: an explicit `MAXWELL_PROFILE` wins, otherwise the DECLARED default.
    `default_profile` is itself a decision with a reason in the policy file, so "which profile?" is answered once,
    in writing, instead of once per session by a human under time pressure.

    Args:
        policy: the parsed policy (its `profiles` and `default_profile`).
        environ: the environment to read (default: os.environ).

    Returns:
        (profile, reason) - the profile is always one the policy declares.

    Raises:
        SystemExit: when the policy declares no usable default, or the override names no declared profile.
    """
    environ = os.environ if environ is None else environ
    declared = policy.get("profiles") or {}
    asked = str(environ.get(PROFILE_ENV) or "").strip()
    if asked:
        if asked not in declared:
            raise SystemExit(
                f"FATAL: {PROFILE_ENV}={asked} names no profile this policy declares "
                f"({', '.join(sorted(declared))}) - refusing the birth"
            )
        return asked, f"{PROFILE_ENV}={asked}"
    default = str(policy.get("default_profile") or "").strip()
    if default not in declared:
        raise SystemExit(
            f"FATAL: default_profile={default or '(absent)'} is not a declared profile - the birth has no surface "
            f"to resolve to (C16: an absent default is fatal, never a guess)"
        )
    return default, f"default_profile={default}"


def unresolvable(policy: dict[str, Any], config: dict[str, Any], classes: dict[str, str],
                 profile: str, cwd: pathlib.Path) -> list[str]:
    """Every stdio member of `profile` whose declared command would NOT start from `cwd`.

    WHY A CHECK AND NOT A COMMENT. A stdio extension that fails to start prints its failure to the TERMINAL and the
    session continues without it (measured harness fact). From INSIDE, a session born without its write gate is
    indistinguishable from one that has it - so the birth must be REFUSED, not annotated.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.
        classes: the name -> class map.
        profile: the profile about to be born.
        cwd: the directory the session would start in.

    Returns:
        One line per member that cannot start, naming the path that does not resolve. Empty when all resolve.
    """
    extensions = config.get("extensions") or {}
    out: list[str] = []
    for name in profile_members(policy, classes, profile):
        cfg = extensions.get(name) or {}
        if str(cfg.get("type") or "") != "stdio":
            continue
        parts = [str(cfg.get("cmd") or "")] + [str(a) for a in (cfg.get("args") or [])]
        declared = str(cfg.get("cwd") or "").strip()
        for part in parts:
            if not part or part.startswith("-") or not SCRIPTISH.search(part):
                continue
            path = _abs_script(part, cfg, cwd)
            if path.exists():
                continue
            out.append(
                f"{name}: {part} resolves to {path}, which does not exist - the extension would be born DEAD, and "
                f"the session would not be told (looked in the declaration's cwd "
                f"{declared or '(none declared)'}, then in {cwd})"
            )
    return out


def birth_argv(policy: dict[str, Any], config: dict[str, Any], classes: dict[str, str],
               profile: str, cwd: pathlib.Path | None = None) -> list[str]:
    """The exact argv that BIRTHS an interactive session with one profile (the per-session realisation).

    Every SCRIPT argument is inlined as an ABSOLUTE, quoted-when-needed path resolved in the DECLARATION's context
    (see `_abs_script`), so the command does not depend on the directory it is run from - which is the whole
    difference between a declaration and a convention.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.
        classes: the name -> class map.
        profile: the profile to be born with (refused when the policy does not declare it).
        cwd: the birth directory (default: the current one).

    Returns:
        The command, in the form MEASURED for platform/builtin names.

    Raises:
        SystemExit: on an undeclared profile, a stdio member with no declared command (D-3034), a script argument
        that resolves nowhere, or a `cmd` itself containing whitespace (that form is UNVERIFIED - only a PATH
        argument was measured).
    """
    cwd = pathlib.Path.cwd() if cwd is None else cwd
    members = profile_members(policy, classes, profile)
    extensions = config.get("extensions") or {}
    builtin = [n for n in members if (extensions.get(n) or {}).get("type") in ("platform", "builtin")]
    stdio = [n for n in members if (extensions.get(n) or {}).get("type") == "stdio"]
    argv = ["goose", "session", "--no-profile"]
    if builtin:
        argv += ["--with-builtin", ",".join(builtin)]
    for name in stdio:
        cfg = extensions.get(name) or {}
        cmd = str(cfg.get("cmd") or "").strip()
        if not cmd:
            raise SystemExit(f"FATAL: {name} declares no cmd - it cannot be born (D-3034)")
        if any(c.isspace() for c in cmd):
            raise SystemExit(
                f"FATAL: {name} declares a cmd containing whitespace; the single-string form is UNVERIFIED for a "
                f"COMMAND (only a path argument is measured), so {profile} may be RENDERED but not LAUNCHED"
            )
        parts = [cmd]
        for arg in (cfg.get("args") or []):
            text = str(arg)
            if text and not text.startswith("-") and SCRIPTISH.search(text):
                path = _abs_script(text, cfg, cwd)
                if not path.exists():
                    raise SystemExit(
                        f"FATAL: {name}: {text} resolves to {path} in the declaration's context AND nowhere "
                        f"else - the extension would be born DEAD, and the session would not be told"
                    )
                text = str(path)
            parts.append(text)
        argv += ["--with-extension", " ".join(_quoted(p) for p in parts)]
    return argv


def launch(policy: dict[str, Any], config: dict[str, Any], classes: dict[str, str],
           profile: str | None = None) -> None:
    """Birth an interactive session, RESOLVING the profile when none is named, and refusing a dead member first.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.
        classes: the name -> class map.
        profile: an explicit profile, or None to resolve one from the policy (D-3065).

    Returns:
        Never - the process is REPLACED by the harness (so the exit code is the session's own).

    Raises:
        SystemExit: when a member cannot start from this directory - the birth is refused BEFORE anything runs.
    """
    cwd = pathlib.Path.cwd()
    reason = "named on the command line"
    if profile is None:
        profile, reason = resolve_profile(policy)
    argv = birth_argv(policy, config, classes, profile, cwd)
    dead = unresolvable(policy, config, classes, profile, cwd)
    if dead:
        print(f"FATAL: {profile} would be born with a DEAD extension - refusing the birth")
        for line in dead:
            print("   " + line)
        raise SystemExit(1)
    print(f"BIRTH profile={profile} ({reason}) cwd={cwd}", file=sys.stderr)
    print("   " + " ".join(argv), file=sys.stderr)
    print("   (this session inherits NOTHING from the harness config: the command above IS its surface)",
          file=sys.stderr)
    sys.stderr.flush()
    sys.stdout.flush()
    os.execvp(argv[0], argv)


def undiscovered(policy: dict[str, Any], config: dict[str, Any]) -> list[str]:
    """Every extension the harness declares that no class carries yet - what an arrival leaves behind.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.

    Returns:
        Sorted names awaiting a decision. Empty when the classification is TOTAL (C16).
    """
    classes, _faults = classify(policy)
    return [name for name in sorted(config.get("extensions") or {}) if name not in classes]


def adopt_text(text: str, names: list[str], config: dict[str, Any], today: str) -> str:
    """Append `names` to the quarantine block WITHOUT re-serialising the file.

    Args:
        text: the policy file's current bytes.
        names: the extensions to register.
        config: the parsed harness config (for the `seen:` stamp - what it was on the day it arrived).
        today: the adoption date, ISO.

    Returns:
        The new file text. Every comment and every ordering above the block survives: a re-dump would destroy the
        `why:` prose that IS the policy, so the splicing is line-level on purpose.
    """
    if not names:
        return text
    lines = text.splitlines()
    if not any(re.match(r"^quarantine:\s*$", line) for line in lines):
        lines += ["quarantine:"]
    for name in names:
        cfg = (config.get("extensions") or {}).get(name) or {}
        seen = f"enabled={'true' if cfg.get('enabled') else 'false'}, type={cfg.get('type') or 'unknown'}"
        lines += [f"  {name}:", f"    adopted: '{today}'", f"    seen: {seen}"]
    return "\n".join(lines) + "\n"


def write_policy(text: str) -> None:
    """Replace the policy file crash-safely (C6: tempfile -> fsync -> os.replace).

    Args:
        text: the bytes to write.

    Raises:
        SystemExit: when the written file does not parse, or an adopted name does not resolve to QUARANTINE.
    """
    fd, tmp = tempfile.mkstemp(dir=str(POLICY.parent), prefix=".extension_profiles.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, POLICY)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    classes, faults = classify(_yaml(POLICY))
    if faults:
        raise SystemExit(f"FATAL: the adopted file reports {len(faults)} fault(s): {faults} - the write is REFUSED")


def render_delegate(policy: dict[str, Any], classes: dict[str, str], config: dict[str, Any], name: str) -> str:
    """Print the `extensions:` list a delegate of this class should be born with.

    Args:
        policy: the parsed policy.
        classes: the name -> class map.
        config: the parsed harness config.
        name: the delegate profile.

    Returns:
        The delegate call's argument list plus what it resolved to.

    Raises:
        SystemExit: when the profile is undeclared, or names an extension the harness does not declare (D-3034).
    """
    profiles = policy.get("delegate_profiles") or {}
    refused_classes = profiles.get("refused") or {}
    if name in refused_classes:
        raise SystemExit(f"REFUSED: delegate class {name!r} is refused by decision: {refused_classes[name]}")
    spec = profiles.get(name)
    if not isinstance(spec, dict):
        raise SystemExit(
            f"REFUSED: delegate profile {name!r} is not declared."
            f" Declared: {', '.join(n for n, s in profiles.items() if isinstance(s, dict)) or '(none)'}"
        )
    declared = config.get("extensions") or {}
    wanted = [str(x) for x in (spec.get("extensions") or [])]
    missing = [n for n in wanted if n not in declared]
    if missing:
        raise SystemExit(f"REFUSED: delegate profile {name!r} names {missing}, which the harness does not declare")
    refused = [n for n in wanted if classes.get(n) in (NEVER, QUARANTINE)]
    if refused:
        raise SystemExit(f"REFUSED: delegate profile {name!r} names {refused}, which is never/quarantined")
    lines = [f"DELEGATE PROFILE {name} - {len(wanted)} extension(s)", "",
             "      extensions=" + json.dumps(wanted) + ",",
             f"      # {spec.get('why') or ''}"]
    for n in wanted:
        cfg = declared.get(n) or {}
        lines.append(f"      # resolved: {n:16} type={cfg.get('type') or '?':9} enabled={bool(cfg.get('enabled'))}")
    lines.append(f"      # the parent carries {len(declared)} declared extension(s); this child is born with {len(wanted)}")
    return "\n".join(lines)


def _selftest() -> int:
    """Known-answer controls over pure functions - no filesystem fixture, no live harness.

    Returns:
        0 when every control holds, 1 otherwise.
    """
    policy = {
        "always": ["developer", "docguard"],
        "on_demand": {"filesystem": {"why": "x", "profiles": ["work"]}},
        "never": {"tom": {"why": "0 tools"}},
        "profiles": {"work": {"adds": ["filesystem"]}, "bad": {"adds": ["tom"]}, "ghost": {"adds": ["nope"]}},
    }
    config = {
        "extensions": {
            "developer": {"type": "platform", "enabled": True},
            "docguard": {"type": "stdio", "enabled": True, "cmd": "uvx", "args": ["docguard"]},
            "filesystem": {"type": "stdio", "enabled": True, "cmd": "npx", "args": ["fs", "/a b/c"]},
            "tom": {"type": "platform", "enabled": False},
        }
    }
    classes, faults = classify(policy)
    # The two rc controls below must be judged on a policy whose PROFILES all resolve: a deliberate
    # refusal in the bad/ghost fixture would mask the drift they exist to isolate.
    clean = dict(policy, profiles={"work": {"adds": ["filesystem"]}})
    controls: list[tuple[str, bool]] = [
        ("three lists become one name -> class map", classes == {
            "developer": ALWAYS, "docguard": ALWAYS, "filesystem": ON_DEMAND, "tom": NEVER}),
        ("a well-formed policy yields no ambiguity fault", faults == []),
        ("a profile resolves to ALWAYS + its own additions",
         profile_members(policy, classes, "work") == ["developer", "docguard", "filesystem"]),
        ("a profile that adds a NEVER extension is REFUSED", _refuses(lambda: profile_members(policy, classes, "bad"))),
        ("a profile that adds an unclassified name is REFUSED", _refuses(lambda: profile_members(policy, classes, "ghost"))),
        ("an undeclared profile is REFUSED", _refuses(lambda: profile_members(policy, classes, "nope"))),
        ("an ENABLED on_demand extension is OWNER-OWED drift, not a fault", check(clean, config)[0] == 2),
    ]
    doubled = dict(policy, **{"never": {"tom": {"why": "0"}, "docguard": {"why": "second answer"}}})
    controls.append(("a name in two classes is a FAULT", check(doubled, config)[0] == 1))
    unclassified = {"extensions": dict(config["extensions"], stranger={"type": "stdio", "enabled": False})}
    controls.append(("an extension nobody classified is a FAULT, never silence", check(policy, unclassified)[0] == 1))
    unresolved = {"extensions": {"developer": {"type": "platform", "enabled": True}}}
    controls.append(("a policy name the harness does not declare is a FAULT",
                     any("does not declare" in f for f in check(policy, unresolved)[1])))
    agreeing = {"extensions": {"developer": {"type": "platform", "enabled": True},
                               "docguard": {"type": "stdio", "enabled": True, "cmd": "uvx", "args": ["d"]},
                               "filesystem": {"type": "stdio", "enabled": False, "cmd": "npx", "args": ["fs"]},
                               "tom": {"type": "platform", "enabled": False}}}
    controls.append(("policy and state agreeing is rc 0", check(clean, agreeing)[0] == 0))
    # THE SUBJECT IS THE DECLARED DEFAULT: the same state is drift against the always minimum and clean once
    # the default names a profile that includes it - a deliberate choice is not rot.
    work_state = {"extensions": {
        "developer": {"type": "platform", "enabled": True},
        "docguard": {"type": "stdio", "enabled": True, "cmd": "uvx", "args": ["d"]},
        "filesystem": {"type": "stdio", "enabled": True, "cmd": "npx", "args": ["fs"]},
        "tom": {"type": "platform", "enabled": False},
    }}
    controls.append(("the check measures the DECLARED DEFAULT, not the always minimum",
                     check(clean, config)[0] == 2
                     and check(dict(clean, default_profile="work"), work_state)[0] == 0))
    text = render(policy, config, classes, "work")
    controls.append(("the render QUOTES a whitespace-bearing path arg (measured form) and marks nothing UNVERIFIED",
                     '"/a b/c"' in text and "UNVERIFIED" not in text))
    controls.append(("the render never silently enables a NEVER extension", "tom" not in text.split("(b)")[1]))

    # ADOPTION ON ARRIVAL (D-3060): a new name must REGISTER itself and grant NOTHING.
    arrived = {"extensions": dict(config["extensions"], stranger={"type": "stdio", "enabled": True})}
    controls.append(("an arriving extension is discovered as undecided",
                     undiscovered(policy, arrived) == ["stranger"]))
    import yaml as _yamlmod

    adopted = _yamlmod.safe_load(adopt_text("quarantine:\n  # (empty)\n", ["stranger"], arrived, "2026-10-17"))
    controls.append(("the adoption writes a dated quarantine row and touches no class list",
                     list(adopted.get("quarantine") or {}) == ["stranger"]
                     and adopted["quarantine"]["stranger"]["adopted"] == "2026-10-17"
                     and not any(k in adopted for k in ("always", "on_demand", "never"))))
    qpolicy = dict(policy, quarantine={"stranger": {"adopted": "2026-10-17"}},
                   profiles={"work": {"adds": ["filesystem"]}, "q": {"adds": ["stranger"]}})
    qclasses, qfaults = classify(qpolicy)
    controls.append(("a quarantined name RESOLVES as a class", qfaults == [] and qclasses.get("stranger") == QUARANTINE))
    controls.append(("a profile may not add a QUARANTINED extension",
                     _refuses(lambda: profile_members(qpolicy, qclasses, "q"))))
    qrc, qfa, qdr, qpend = check(dict(qpolicy, profiles={"work": {"adds": ["filesystem"]}}), arrived)
    controls.append(("quarantine is OWNER-OWED (rc 2) and never a structural fault",
                     qrc == 2 and qfa == [] and len(qpend) == 1))

    # THE SUBAGENT SURFACE: a delegate is a session, born with the smallest set that closes its task.
    dpolicy = dict(policy, delegate_profiles={
        "review": {"extensions": ["developer", "docguard"], "why": "x"},
        "ghost": {"extensions": ["nope"], "why": "x"},
        "refused": {"research": "no local model is measured on open-web synthesis"},
    })
    dclasses, _dfaults = classify(dpolicy)
    controls.append(("a delegate profile resolves to its declared set",
                     "docguard" in render_delegate(dpolicy, dclasses, config, "review")))
    controls.append(("a delegate profile naming an undeclared extension is REFUSED",
                     _refuses(lambda: render_delegate(dpolicy, dclasses, config, "ghost"))))
    controls.append(("a delegate class refused by decision is REFUSED",
                     _refuses(lambda: render_delegate(dpolicy, dclasses, config, "research"))))
    # A CHILD CANNOT BE GIVEN WHAT THE CONFIG DISABLES (measured 2026-10-17, D-3067): the same policy naming an
    # extension the harness has switched OFF must be OWNER-OWED, never silently resolved.
    disabled = {"extensions": dict(config["extensions"], filesystem={"type": "stdio", "enabled": False,
                                                                    "cmd": "npx", "args": ["fs", "/a b/c"]})}
    dpol = dict(policy, profiles={"work": {"adds": []}}, default_profile="work",
                delegate_profiles={"sweeper": {"extensions": ["developer", "filesystem"], "why": "x"}})
    drows, _dfa, ddrift, _dp = check(dpol, disabled)
    controls.append(("a delegate profile naming a DISABLED extension is OWNER-OWED, not a silent drop",
                     drows == 2 and any("sweeper" in d and "DISABLED" in d for d in ddrift)))

    # THE BIRTH: a session is born with an EXPLICIT surface, and a surface that would be born DEAD is refused.
    bpolicy = dict(policy, profiles={"work": {"adds": ["filesystem"]}, "plain": {"adds": []}})
    argv = birth_argv(bpolicy, config, classes, "plain", REPO)
    controls.append(("the birth argv is the per-session form, not a config edit",
                     argv[:3] == ["goose", "session", "--no-profile"] and "developer" in argv[4]))
    controls.append(("the birth argv never names a NEVER extension", "tom" not in " ".join(argv)))
    controls.append(("an undeclared profile cannot be born",
                     _refuses(lambda: birth_argv(bpolicy, config, classes, "nope"))))
    controls.append(("a whitespace-bearing PATH argument is QUOTED, not refused (that form is MEASURED)",
                     '"' in birth_argv(bpolicy, config, classes, "work", REPO)[-1]))
    # MEASURED TWO-SIDED 2026-10-17: `python3 mcp_doc_guard.py` starts from the repo root and fails from anywhere
    # else, and the harness tells the TERMINAL only. So the check must catch it - and must NOT cry wolf at home.
    localcfg = {"extensions": dict(config["extensions"], local={
        "type": "stdio", "enabled": True, "cmd": "python3", "args": ["mcp_doc_guard.py"]})}
    lclasses = dict(classes, local=ALWAYS)
    controls.append(("a RELATIVE script member is caught away from the repo root",
                     bool(unresolvable(bpolicy, localcfg, lclasses, "plain", pathlib.Path(tempfile.gettempdir())))))
    controls.append(("the same member resolves AT the repo root",
                     unresolvable(bpolicy, localcfg, lclasses, "plain", REPO) == []))
    # THE CONTEXT BELONGS TO THE DECLARATION (BUG-878 re-scoped, D-3065). The harness starts a config-declared
    # extension in ITS OWN cwd - measured from /tmp with zero warnings - so a relative arg beside a declared cwd is
    # SOUND from any birth directory, and the launcher must resolve it there rather than accusing the declaration.
    declared_ctx = {"extensions": dict(config["extensions"], local={
        "type": "stdio", "enabled": True, "cmd": "python3", "args": ["mcp_doc_guard.py"], "cwd": str(REPO)})}
    elsewhere = pathlib.Path(tempfile.gettempdir())
    controls.append(("a RELATIVE script arg is resolved in the DECLARATION's cwd, not the birth cwd",
                     str(REPO / "mcp_doc_guard.py") in " ".join(
                         birth_argv(bpolicy, declared_ctx, lclasses, "plain", elsewhere))))
    controls.append(("such a member is NOT 'unresolvable' from an unrelated directory",
                     unresolvable(bpolicy, declared_ctx, lclasses, "plain", elsewhere) == []))
    # THE PROFILE IS RESOLVED, NOT REMEMBERED (D-3065): deterministic, so it can be stated and audited.
    controls.append(("no name given -> the declared default, with its reason",
                     resolve_profile({"profiles": {"work": {}}, "default_profile": "work"}, {})
                     == ("work", "default_profile=work")))
    controls.append(("MAXWELL_PROFILE wins over the default",
                     resolve_profile({"profiles": {"work": {}, "plain": {}}, "default_profile": "work"},
                                     {PROFILE_ENV: "plain"})[0] == "plain"))
    controls.append(("an override naming no declared profile is REFUSED",
                     _refuses(lambda: resolve_profile({"profiles": {"work": {}}, "default_profile": "work"},
                                                     {PROFILE_ENV: "ghost"}))))
    controls.append(("an absent default is FATAL, never a guess",
                     _refuses(lambda: resolve_profile({"profiles": {"work": {}}}, {}))))
    controls.append(("a born surface EQUAL to a profile is that profile",
                     profile_of({"developer", "docguard", "filesystem"}, bpolicy, classes) == ["work"]))
    controls.append(("a born surface no profile names matches NONE (a reading, not a guess)",
                     profile_of({"filesystem"}, bpolicy, classes) == []))
    controls.append(("the harness's display name maps back to the policy key",
                     display_names({"extensions": {"extensionmanager": {
                         "type": "platform", "name": "Extension Manager"}}})["Extension Manager"] == "extensionmanager"))

    for label, ok in controls:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    passed = sum(1 for _, ok in controls if ok)
    print(f"selftest: {passed}/{len(controls)}")
    return 0 if passed == len(controls) else 1


def _refuses(fn: Any) -> bool:
    """True when calling fn raises SystemExit - the only acceptable answer to an unresolvable declaration.

    Args:
        fn: a zero-argument callable expected to refuse.

    Returns:
        Whether it refused.
    """
    try:
        fn()
    except SystemExit:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: CLI arguments (default: sys.argv[1:]).

    Returns:
        Tri-state: 0 agree / 1 FAULT / 2 owner-owed drift (or the selftest verdict).
    """
    parser = argparse.ArgumentParser(description="compose a goose session's extension set from a declared policy")
    parser.add_argument("--list", action="store_true", help="print the policy and the profiles")
    parser.add_argument("--render", metavar="PROFILE", help="print the two realisations of one profile")
    parser.add_argument("--check", action="store_true", help="compare the policy against the harness state")
    parser.add_argument("--adopt", action="store_true", help="register newly arrived extensions into quarantine")
    parser.add_argument("--delegate", metavar="PROFILE", help="print the extensions list a delegate is born with")
    parser.add_argument("--launch", nargs="?", const="", metavar="PROFILE",
                        help="BIRTH an interactive session; with no PROFILE the policy RESOLVES one (D-3065)")
    parser.add_argument("--born", nargs="?", const=BORN_DEFAULT, type=int, metavar="N",
                        help="read the last N sessions' BIRTH SURFACES from the harness's own record")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()

    policy = _yaml(POLICY)
    classes, faults = classify(policy)
    config = _yaml(declared_home())

    if args.adopt:
        arrived = undiscovered(policy, config)
        if not arrived:
            print(f"ok extension-adoption: every declared extension already carries a decision ({len(classes)})")
            return 0
        text = adopt_text(POLICY.read_text(encoding="utf-8"), arrived, config, datetime.date.today().isoformat())
        write_policy(text)
        print(f"adopted {len(arrived)} extension(s) into QUARANTINE (registered, granted NOTHING): {', '.join(arrived)}")
        print(f"   next: move each to always / on_demand / never with a `why` in {POLICY.name}, then re-run --check")
        return 0 if not faults else 1

    if args.delegate:
        print(render_delegate(policy, classes, config, args.delegate))
        return 0

    if args.list:
        costs = _costs(policy)
        for cls, _key in CLASSES:
            names = [n for n, c in classes.items() if c == cls]
            print(f"{cls.upper()} ({len(names)})")
            for name in names:
                row = costs.get(name) or {}
                measured = row.get("verdict", "unmeasured")
                toks = row.get("tokens_est")
                print(f"   {name:20} {measured:16} {'≈' + str(toks) + ' tok/req' if toks else ''}")
        print("\nPROFILES")
        for name, spec in (policy.get("profiles") or {}).items():
            print(f"   {name:12} + {', '.join(spec.get('adds') or [])}")
        if faults:
            print("\nFAULTS")
            for f in faults:
                print("   " + f)
        return 0

    if args.render:
        print(render(policy, config, classes, args.render))
        return 0

    if args.born is not None:
        rows = born_sessions(sessions_db(), args.born)
        print(f"BIRTH SURFACES - the last {len(rows)} session(s), read from the harness's own store")
        print("(the surface a session was GIVEN at birth; a config edit is NOT live inside it, BUG-873)")
        print("(a member that FAILED to start still appears here: the record says what was GIVEN, never what started)")
        print("")
        print(render_born(rows, policy, classes, config))
        return 0

    if args.launch is not None:
        launch(policy, config, classes, args.launch or None)
        return 0

    rc, faults, drift, pending = check(policy, config)
    if faults:
        print(f"FAIL extension-profiles: {len(faults)} structural fault(s)")
        for f in faults:
            print("   " + f)
    else:
        print(f"ok extension-profiles: every declared extension is classified, every profile resolves "
              f"({len(classes)} extension(s), {len(policy.get('profiles') or {})} profile(s))")
    if drift:
        verdict = "FAIL" if faults else "OWNER-OWED"
        print(f"{verdict} policy vs live state: {len(drift)} extension(s) resident against the policy")
        for d in drift:
            print("   " + d)
    if pending:
        print(f"OWNER-OWED quarantine: {len(pending)} extension(s) arrived and carry no decision (D-3060)")
        for p in pending:
            print("   " + p)
    return rc


if __name__ == "__main__":
    sys.exit(main())
