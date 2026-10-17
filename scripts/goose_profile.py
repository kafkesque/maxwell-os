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

THREE FACTS DECIDE THE VERDICT, never a count:
  * POLICY vs STATE. config/extension_profiles.yaml classifies every extension `always` / `on_demand` / `never`;
    the harness config declares `enabled`. Agreement is rc 0. A disagreement is OWNER-OWED (rc 2), because flipping
    the owner's config is their act - and it is reported as a LIST, with the measured token cost of each, not as a
    number.
  * TOTALITY (C16). An extension the policy does not classify is not "fine" - it is an unowned decision, which is a
    FAULT (rc 1), not a warning.
  * RESOLUTION (D-3034). A name in the policy that the harness config does not declare is a FAULT. So is a profile
    that adds a name it may not add (an unknown name, or one classified `never`).

Usage:
  python3 scripts/goose_profile.py --list
  python3 scripts/goose_profile.py --render workshop
  python3 scripts/goose_profile.py --check          # tri-state: 0 agree | 1 FAULT | 2 owner-owed drift
  python3 scripts/goose_profile.py --selftest
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
POLICY = REPO / "config" / "extension_profiles.yaml"
FLIP_WRITER = REPO / "agent" / "adapters" / "goose" / "apply_provider_flip.py"

ALWAYS, ON_DEMAND, NEVER, UNCLASSIFIED = "always", "on_demand", "never", "UNCLASSIFIED"


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
    """Turn the three policy lists into one name -> class map, and report any name in two classes.

    Args:
        policy: the parsed config/extension_profiles.yaml.

    Returns:
        (classes, faults) where faults names every ambiguity. A name declared twice is a FAULT, not a last-wins
        (C12: one home means one answer).
    """
    classes: dict[str, str] = {}
    faults: list[str] = []
    for cls, key in ((ALWAYS, "always"), (ON_DEMAND, "on_demand"), (NEVER, "never")):
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
    members = [n for n, c in classes.items() if c == ALWAYS]
    return members + [n for n in adds if n not in members]


def check(policy: dict[str, Any], config: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    """Compare the POLICY against the harness STATE, in the three states the rail registry can report.

    Args:
        policy: the parsed policy.
        config: the parsed harness config.

    Returns:
        (rc, faults, drift): rc 0 agree / 1 fault / 2 owner-owed; faults are structural; drift is policy-vs-state.
    """
    classes, faults = classify(policy)
    extensions = config.get("extensions") or {}
    if not isinstance(extensions, dict) or not extensions:
        return 1, ["the harness config declares no extensions - the comparison has no subject"], []

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

    drift: list[str] = []
    for name, cfg in sorted(extensions.items()):
        if name not in classes:
            continue
        enabled = bool(isinstance(cfg, dict) and cfg.get("enabled"))
        if classes[name] == ALWAYS and not enabled:
            drift.append(f"{name}: policy says ALWAYS but the harness has it DISABLED")
        elif classes[name] == NEVER and enabled:
            drift.append(f"{name}: policy says NEVER but the harness has it ENABLED")
        elif classes[name] == ON_DEMAND and enabled:
            drift.append(f"{name}: policy says ON_DEMAND but the harness has it ENABLED as default")

    if faults:
        return 1, faults, drift
    return (2 if drift else 0), faults, drift


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
        text = " ".join(parts).strip()
        if not text:
            unverified.append(f"{name}: declares no cmd (D-3034)")
            continue
        if any(" " in p for p in parts):
            unverified.append(f"{name}: an argument contains whitespace - the single-string form is UNVERIFIED for it")
        cmd += f" --with-extension '{text}'"
    lines.append("      " + cmd)
    for note in unverified:
        lines.append(f"      UNVERIFIED {note}")
    measured = [costs[n] for n in members if n in costs and costs[n].get("tokens_est")]
    if measured:
        total = sum(int(r["tokens_est"]) for r in measured)
        lines.append(f"      measured schema cost of the MEASURED members: ≈{total} tokens per request")
    lines.append("      (platform/builtin schema bytes are NOT measured - absent, not zero, D-2957)")
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
    text = render(policy, config, classes, "work")
    controls.append(("the render marks a whitespace-bearing stdio arg UNVERIFIED", "UNVERIFIED" in text))
    controls.append(("the render never silently enables a NEVER extension", "tom" not in text.split("(b)")[1]))

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
    parser.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()

    policy = _yaml(POLICY)
    classes, faults = classify(policy)
    config = _yaml(declared_home())

    if args.list:
        costs = _costs(policy)
        for cls in (ALWAYS, ON_DEMAND, NEVER):
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

    rc, faults, drift = check(policy, config)
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
    return rc


if __name__ == "__main__":
    sys.exit(main())
