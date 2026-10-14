#!/usr/bin/env python3
"""T-132 - THE AGENT CONTEXT PROBE (READ-ONLY).

WHY THIS EXISTS. A local agent session runs on a chain of four numbers that nobody declares together:
what the MODEL SERVER can attend to, what the HARNESS is TOLD it can attend to, WHEN the harness
decides to compact, and what the harness's own LEDGER says its prompt cache actually reused. Every
link is silent when it is wrong: the server truncates without saying so, a declared window smaller
than the served one throws usable context away, and a compaction trigger derived from a cloud price
tier fires on hardware we own.

MEASURED 2026-10-14, and the reason this rail exists rather than a note: the harness's compaction
trigger for the local models resolves to ~80% of their small served window, so an agent session on them
compacts long before the window is full and pays a full COLD re-prefill of the rewritten
history on the next turn. The rule, the thresholds and the measured baseline live in
`config/agent_context.yaml` (ONE home, C12): this file names no path, no host and no baseline number of
its own, and two of its known-answer controls prove exactly that by reading its own bytes.

READ-ONLY: this rail measures, it never writes a setting. Fixing a fault it reports is a config act.

Usage:  python3 scripts/agent_context_probe.py [--json] [--selftest]
Exit:   rc 0 = every layer coherent | rc 2 = a declared fault | rc 1 = the probe itself failed
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

CONFIG_REL = "config/agent_context.yaml"   # the ONE home; every other value is read from it (C12)


class ProbeError(SystemExit):
    """Fail-closed: an unreadable declaration is a fault, never a silent pass (C16)."""


def repo_root() -> Path:
    """The repository root, derived from this file's own location (never an absolute literal)."""
    return Path(__file__).resolve().parents[1]


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load the context contract. Refuses a missing or non-mapping declaration."""
    import yaml

    p = Path(path) if path else repo_root() / CONFIG_REL
    if not p.is_file():
        raise ProbeError(f"FAIL-CLOSED (agent-context): no declaration at {p} - the rule has ONE home (C12)")
    cfg = yaml.safe_load(p.read_text())
    if not isinstance(cfg, dict):
        raise ProbeError(f"FAIL-CLOSED (agent-context): {p} does not parse to a mapping")
    return cfg


def home_path(cfg: dict[str, Any], key: str) -> Path:
    """Resolve a declared home to a path. The '#<field>' hint is stripped; '~' is expanded."""
    raw = str(cfg.get("homes", {}).get(key, "")).strip()
    if not raw:
        raise ProbeError(f"FAIL-CLOSED (agent-context): the declaration names no home for {key!r} (C12)")
    return Path(os.path.expanduser(raw.split("#", 1)[0]))


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, refusing anything that is not an object."""
    if not path.is_file():
        raise ProbeError(f"FAIL-CLOSED (agent-context): declared declaration unreadable: {path}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ProbeError(f"FAIL-CLOSED (agent-context): {path} is not a JSON object")
    return data


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML mapping, returning {} when the file is absent (the harness may have no config yet)."""
    import yaml

    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def declared_windows(provider: dict[str, Any]) -> dict[str, int | None]:
    """Layer 2: what the harness is TOLD each model can attend to."""
    out: dict[str, int | None] = {}
    for model in provider.get("models") or []:
        if isinstance(model, dict) and model.get("name"):
            limit = model.get("context_limit")
            out[str(model["name"])] = int(limit) if isinstance(limit, (int, float)) else None
    return out


def provider_auth(provider: dict[str, Any]) -> tuple[str, str | None]:
    """The base URL and the Authorization header, read from the harness's own declaration."""
    base = str(provider.get("base_url") or "").strip()
    auth = None
    headers = provider.get("headers") or {}
    if isinstance(headers, dict):
        for name, value in headers.items():
            if str(name).lower() == "authorization":
                auth = str(value)
    return base, auth


def served_windows(cfg: dict[str, Any], base_url: str, auth: str | None, timeout: int = 10) -> dict[str, Any]:
    """Layer 1: what the SERVER says it can attend to. Returns {'windows': {...}, 'error': str|None}."""
    template = str(cfg.get("homes", {}).get("served_window_endpoint", "")).strip()
    if not template or not base_url:
        return {"windows": {}, "error": "no served-window endpoint is declared (C12)"}
    url = template.split("#", 1)[0].format(base_url=base_url.rstrip("/"))
    request = urllib.request.Request(url, headers={"Authorization": auth} if auth else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - declared local home
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"windows": {}, "error": f"{type(exc).__name__}: {exc}"}
    field = template.split("#", 1)[1] if "#" in template else "max_model_len"
    windows: dict[str, int] = {}
    for entry in payload.get("data") or []:
        if isinstance(entry, dict) and entry.get("id") is not None and isinstance(entry.get(field), (int, float)):
            windows[str(entry["id"])] = int(entry[field])
    return {"windows": windows, "error": None}


def parity(served: dict[str, int], declared: dict[str, int | None], cfg: dict[str, Any]) -> dict[str, str]:
    """Layer 1 vs Layer 2. The verdict per model; the vocabulary comes from the declaration."""
    rule = cfg.get("parity_rule") or {}
    below, above = rule.get("on_served_below_declared"), rule.get("on_declared_below_served")
    missing = rule.get("on_missing_either_side")
    verdicts: dict[str, str] = {}
    for model in sorted(set(served) | set(declared)):
        s, d = served.get(model), declared.get(model)
        if s is None or d is None:
            verdicts[model] = str(missing)
        elif s == d:
            verdicts[model] = "ok"
        elif s < d:
            verdicts[model] = str(below)
        else:
            verdicts[model] = str(above)
    return verdicts


def effective_trigger(window: int, threshold: float, cap: int) -> int:
    """Layer 3: the trigger is the EARLIER of the percentage and the cap (goose's own semantics)."""
    return int(min(threshold * window, cap))


def resolve_trigger_inputs(cfg: dict[str, Any], harness: dict[str, Any]) -> dict[str, Any]:
    """Read the trigger's inputs from the process env, then the harness's own config, then the default."""
    trigger = cfg.get("trigger") or {}
    out: dict[str, Any] = {}
    for label, env_key, default_key in (
        ("threshold", "threshold_env", "threshold_default"),
        ("cap", "cap_env", "cap_default"),
    ):
        env_name = str(trigger.get(env_key, ""))
        raw = os.environ.get(env_name) if env_name else None
        source = "process env" if raw is not None else "default"
        if raw is None:
            raw = harness.get(env_name)
            source = "harness config" if raw is not None else "default"
        if raw is None:
            raw = trigger.get(default_key)
        out[label] = {"value": raw, "source": source, "env": env_name}
    out["threshold"]["value"] = float(out["threshold"]["value"])
    out["cap"]["value"] = int(out["cap"]["value"])
    return out


def window_class(window: int, classes: dict[str, Any]) -> str | None:
    """The MOST capable class the window satisfies; first-declared wins a tie (the rule is declared)."""
    best: tuple[int, str] | None = None
    for name, spec in classes.items():
        minimum = spec.get("min_window") if isinstance(spec, dict) else None
        if not isinstance(minimum, (int, float)) or window < minimum:
            continue
        if best is None or int(minimum) > best[0]:
            best = (int(minimum), str(name))
    return best[1] if best else None


def ledger_summary(db: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Layer 4: the measured cache evidence, with ABSENT != ZERO (D-2957) held as a rule, not a habit."""
    accounting = cfg.get("cache_accounting") or {}
    ledger = cfg.get("homes", {}).get("cache_ledger", "")
    table = str(ledger).split("#", 1)[1] if "#" in str(ledger) else ""
    if not db.is_file() or not table:
        return {"available": False, "reason": f"declared ledger unreadable or unnamed: {db}", "per_model": []}
    field, input_field = str(accounting.get("field", "")), str(accounting.get("input_field", ""))
    min_calls = int(accounting.get("min_calls_for_a_ratio", 0))
    query = (
        f'SELECT model, COUNT(*), SUM("{input_field}"), SUM("{field}"), COUNT("{field}") '  # noqa: S608 - names declared
        f'FROM "{table}" GROUP BY model ORDER BY 3 DESC'
    )
    try:
        connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = connection.execute(query).fetchall()
        connection.close()
    except sqlite3.Error as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}", "per_model": []}
    out_rows = []
    for model, calls, tokens_in, cache_sum, cache_present in rows:
        carried = int(cache_present or 0)
        ratio = (float(cache_sum) / float(tokens_in)) if cache_sum is not None and tokens_in else None
        if carried < min_calls or ratio is None:
            verdict = "unknown_not_zero" if carried == 0 else "inconclusive"
        else:
            verdict = "measured"
        out_rows.append({
            "model": model, "calls": int(calls), "input_tokens": int(tokens_in or 0),
            "cache_read_tokens": None if cache_sum is None else int(cache_sum),
            "rows_carrying_the_field": carried, "cache_read_ratio": ratio, "verdict": verdict,
        })
    return {"available": True, "reason": None, "per_model": out_rows, "min_calls_for_a_ratio": min_calls}


def prefix_hazards(cfg: dict[str, Any], harness: dict[str, Any]) -> list[dict[str, str]]:
    """The prefix-stability hazards this machine can settle from its own live declaration."""
    stability = cfg.get("prefix_stability") or {}
    injections = [str(name) for name in (stability.get("injection_envs") or [])]
    if not injections:
        raise ProbeError("FAIL-CLOSED (agent-context): prefix_stability names no injection_envs - the "
                         "probe cannot report an injection hazard it has not been told how to look for (C12)")
    found: list[dict[str, str]] = []
    live = sorted(name for name in injections if os.environ.get(name) or harness.get(name))
    found.append({
        "hazard": "per_turn_injection_at_the_head",
        "state": "PRESENT" if live else "ABSENT (measured)",
        "detail": f"per-turn injection variables set: {live}" if live else "no per-turn injection is configured",
    })
    return found


def build_report(cfg: dict[str, Any]) -> dict[str, Any]:
    """Measure all four layers and assemble the report. Nothing here writes anything."""
    provider = read_json(home_path(cfg, "declaration"))
    harness = read_yaml_mapping(home_path(cfg, "harness_config"))
    base_url, auth = provider_auth(provider)
    served = served_windows(cfg, base_url, auth)
    declared = declared_windows(provider)
    verdicts = parity(served["windows"], declared, cfg)
    inputs = resolve_trigger_inputs(cfg, harness)
    classes = cfg.get("classes") or {}
    routes = {}
    for model, window in sorted(served["windows"].items()):
        routes[model] = {
            "window": window,
            "class": window_class(window, classes),
            "trigger": effective_trigger(window, inputs["threshold"]["value"], inputs["cap"]["value"]),
        }
    ledger = ledger_summary(home_path(cfg, "cache_ledger"), cfg)
    return {
        "served": served["windows"],
        "served_error": served["error"],
        "declared": declared,
        "parity": verdicts,
        "trigger_inputs": inputs,
        "routes": routes,
        "ledger": ledger,
        "prefix_hazards": prefix_hazards(cfg, harness),
    }


def render(report: dict[str, Any], cfg: dict[str, Any]) -> int:
    """Print the report and return the exit code the declaration names."""
    faults: list[str] = []
    print("== LAYER 1/2 - served window vs declaration ==")
    for model, verdict in sorted(report["parity"].items()):
        window = report["served"].get(model)
        print(f"   {verdict:16} {model:44} served={window if window is not None else 'UNREADABLE'}")
    if report["served_error"]:
        faults.append(f"the served window is unreadable ({report['served_error']}) - every parity verdict is UNVERIFIABLE")
    for model, verdict in report["parity"].items():
        if verdict != "ok":
            faults.append(f"{model}: {verdict}")
    print("== LAYER 3 - the derived compaction trigger ==")
    for label, spec in report["trigger_inputs"].items():
        print(f"   {label:10} {spec['value']!r:>10}  from {spec['source']} ({spec['env']})")
    for model, spec in sorted(report["routes"].items()):
        print(f"   trigger {spec['trigger']:>8} for a {spec['window']:>7} window  class={spec['class']}  {model}")
    print("== LAYER 4 - the measured cache evidence ==")
    if not report["ledger"]["available"]:
        print(f"   UNKNOWN (not zero): {report['ledger']['reason']}")
    for row in report["ledger"]["per_model"]:
        ratio = "n/a" if row["cache_read_ratio"] is None else f"{row['cache_read_ratio']:.1%}"
        print(f"   {row['verdict']:16} calls={row['calls']:>6} input={row['input_tokens']:>12} "
              f"carrying={row['rows_carrying_the_field']:>5} ratio={ratio:>7}  {row['model']}")
    for hazard in report["prefix_hazards"]:
        print(f"== PREFIX - {hazard['hazard']}: {hazard['state']} - {hazard['detail']}")
    if faults:
        print(f"\nFAIL agent-context: {len(faults)} declared fault(s)")
        for fault in faults:
            print(f"   - {fault}")
        return int(cfg.get("exit_codes", {}).get("fault", 2))
    print("\nok agent-context: the four layers agree, and nothing measured was written")
    return int(cfg.get("exit_codes", {}).get("ok", 0))


#: ── END OF THE REPORT PATH ──────────────────────────────────────────────────────────────────────
#: Everything ABOVE this line can reach a reader as a printed path, host or number, so it may name
#: none of them (C12). Everything BELOW is control data: a KNOWN ANSWER is allowed to name the baseline
#: the declaration owns - that is what makes it known - and the control proves the split holds.
REPORT_PATH_MARKER = "#: ── END OF THE REPORT PATH"

FORBIDDEN_EVERYWHERE = ("/Users/", "sessions.db", "model_settings.json", "custom_providers", "localhost", "11435")
BASELINE_NUMBERS = ("225000", "32768", "262144", "26214", "131072")
CONTROL_LABELS = (
    "the_trigger_is_the_earlier_of_the_percentage_and_the_cap",
    "a_cap_below_the_percentage_binds",
    "a_served_window_below_the_declaration_is_a_truncation_risk",
    "a_declaration_below_the_served_window_is_a_wasted_window",
    "parity_is_ok_only_when_the_two_are_equal",
    "a_model_with_no_served_window_is_unverifiable_never_routed",
    "the_route_is_the_most_capable_class_the_window_satisfies",
    "a_window_below_every_class_satisfies_none",
    "a_zero_cache_read_with_no_ratio_is_unknown_never_zero",
    "the_probe_names_no_path_or_host_of_its_own",
    "the_report_path_names_no_baseline_number_the_declaration_owns",
    "an_undeclared_injection_env_list_is_refused",
)


def report_path_source() -> str:
    """This file UP TO the controls: the part that can emit a number, path or host to a reader."""
    return Path(__file__).read_text().split(REPORT_PATH_MARKER, 1)[0]


def selftest(cfg: dict[str, Any]) -> int:
    """Known-answer controls. Every control calls the SAME helper the report calls (D-2679)."""
    passed = 0
    total = 0
    classes = {"agent_loop": {"min_window": 131072}, "agent_probe": {"min_window": 32768},
               "pipeline_batch": {"min_window": 32768}}

    def control(label: str, ok: bool) -> None:
        nonlocal passed, total
        total += 1
        if ok:
            passed += 1
        print(f"   {'ok  ' if ok else 'FAIL'} {label}")

    control(CONTROL_LABELS[0], effective_trigger(32768, 0.8, 225000) == 26214)
    control(CONTROL_LABELS[1], effective_trigger(262144, 0.8, 200000) == 200000)
    rule = {"on_served_below_declared": "truncation_risk", "on_declared_below_served": "wasted_window",
            "on_missing_either_side": "unverifiable"}
    control(CONTROL_LABELS[2], parity({"m": 16384}, {"m": 32768}, {"parity_rule": rule}) == {"m": "truncation_risk"})
    control(CONTROL_LABELS[3], parity({"m": 65536}, {"m": 32768}, {"parity_rule": rule}) == {"m": "wasted_window"})
    control(CONTROL_LABELS[4], parity({"a": 32768, "b": 1}, {"a": 32768, "b": 2}, {"parity_rule": rule})["a"] == "ok")
    control(CONTROL_LABELS[5], parity({"a": 1}, {"a": 2, "b": 2}, {"parity_rule": rule})["b"] == "unverifiable")
    control(CONTROL_LABELS[6], window_class(262144, classes) == "agent_loop"
            and window_class(131072, classes) == "agent_loop"
            and window_class(32768, classes) == "agent_probe")
    control(CONTROL_LABELS[7], window_class(4096, classes) is None)
    # the ABSENT != ZERO rule, exercised on a real query against an in-memory ledger (D-2957)
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE "usage_ledger" (model TEXT, input_tokens INT, cache_read_tokens INT)')
    connection.executemany('INSERT INTO "usage_ledger" VALUES (?,?,?)',
                           [("local", 1000, None), ("local", 1000, None)])
    connection.commit()
    probe = {"homes": {"cache_ledger": "x#usage_ledger"},
             "cache_accounting": {"field": "cache_read_tokens", "input_field": "input_tokens",
                                  "min_calls_for_a_ratio": 1}}
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "agent_context_probe_selftest.db"
    try:
        target = sqlite3.connect(str(tmp))          # the FILE-backed copy exercises the real code path
        connection.backup(target)
        target.close()
        rows = ledger_summary(tmp, probe)["per_model"]
        control(CONTROL_LABELS[8], len(rows) == 1 and rows[0]["verdict"] == "unknown_not_zero"
                and rows[0]["cache_read_ratio"] is None and rows[0]["rows_carrying_the_field"] == 0)
    finally:
        connection.close()
        tmp.unlink(missing_ok=True)
    report_path = report_path_source()
    control(CONTROL_LABELS[9], not [lit for lit in FORBIDDEN_EVERYWHERE if lit in report_path])
    control(CONTROL_LABELS[10], not [num for num in BASELINE_NUMBERS if num in report_path_source()])
    refused = False
    try:
        prefix_hazards({"prefix_stability": {}}, {})
    except ProbeError:
        refused = True
    control(CONTROL_LABELS[11], refused)

    held = passed == total
    print(f"{'ok ' if held else 'FAIL'} agent-context-probe --selftest: {passed}/{total} known-answer control(s) green")
    codes = cfg.get("exit_codes", {})
    return int(codes.get("ok", 0)) if held else int(codes.get("error", 1))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: report the four layers, or prove the controls."""
    parser = argparse.ArgumentParser(description="Read-only probe of the agent harness's context contract (T-132)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls")
    parser.add_argument("--config", default=None, help="override the declaration path (testing only)")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.selftest:
        return selftest(cfg)
    try:
        report = build_report(cfg)
    except ProbeError as exc:
        print(f"FAIL agent-context: {exc}", file=sys.stderr)
        return int(cfg.get("exit_codes", {}).get("fault", 2))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return int(cfg.get("exit_codes", {}).get("ok", 0))
    return render(report, cfg)


if __name__ == "__main__":
    sys.exit(main())
