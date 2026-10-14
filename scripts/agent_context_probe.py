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

Usage:  python3 scripts/agent_context_probe.py [--json] [--selftest] [--prefix-audit] [--prefill-ab]
Exit:   rc 0 = every layer coherent | rc 2 = a declared fault | rc 1 = the probe itself failed

READ-ONLY, with ONE declared exception: `--prefill-ab` SENDS three prompts (the two-call A/B that
certifies prefix reuse, plus its control). It is opt-in and OFF the ladder, because a rail that needs
the network must never be the thing that decides whether a build is green. Every other mode only reads.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
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


def measured_prompt_tokens(record: dict[str, Any]) -> int:
    """A prompt size is MEASURED or it is REFUSED. BUG-794: an estimate published a claim that was false."""
    if record.get("estimated"):
        raise ProbeError("FAIL-CLOSED (agent-context): a prompt size derived from a chars-per-token rule is "
                         "not a measurement - read the server's own counter instead (BUG-794)")
    value = record.get("prompt_tokens")
    if not isinstance(value, (int, float)) or value <= 0:
        raise ProbeError("FAIL-CLOSED (agent-context): a reading with no measured prompt size is refused")
    return int(value)


def prefill_seconds(prompt_tokens: int, tps: float | None) -> float | None:
    """Layer 5: the seconds a turn spends BEFORE its first decoded token (None when throughput is unmeasured)."""
    if not isinstance(tps, (int, float)) or tps <= 0:
        return None
    return round(float(prompt_tokens) / float(tps), 1)


def measured_prefill(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Layer 5's measured rows: one per model, each proved by the token count the SERVER echoed."""
    rows: dict[str, dict[str, Any]] = {}
    for model, row in ((cfg.get("measured_20261014") or {}).get("prefill") or {}).items():
        if not isinstance(row, dict):
            continue                     # an explicitly unmeasured model is a HOLE, not an error
        rows[str(model)] = {"prompt_tokens": measured_prompt_tokens(row),
                            "prefill_tps": row.get("prefill_tps"), "decode_tps": row.get("decode_tps")}
    return rows


def prefill_bill(window: int, tps: float | None, classes: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Layer 5, the TWO-SIDED predicate: a class is satisfied by the WINDOW and by the PREFILL BILL.

    The window is the FLOOR a class declares; the bill is what a turn actually costs. A model with a
    large window and a small throughput satisfies the floor and fails the bill - and the class's
    WORKING SET is what gets divided, never the window: a window is not a budget.
    """
    policy = str((cfg.get("prefill_budget") or {}).get("unknown_tps", "refuse_route"))
    evaluated: list[dict[str, Any]] = []
    for name, spec in classes.items():
        if not isinstance(spec, dict):
            continue
        floor, working, allowed = spec.get("min_window"), spec.get("working_set"), spec.get("prefill_budget_s")
        if not isinstance(floor, (int, float)) or window < floor:
            continue
        seconds = prefill_seconds(int(working), tps) if isinstance(working, (int, float)) else None
        if seconds is None:
            verdict = policy
        elif isinstance(allowed, (int, float)) and seconds <= float(allowed):
            verdict = "routable"
        else:
            verdict = "prefill_bill"
        evaluated.append({"class": str(name), "min_window": floor, "working_set": working,
                          "seconds": seconds, "budget_s": allowed, "verdict": verdict})
    routable = [row for row in evaluated if row["verdict"] == "routable"]
    best = max(routable, key=lambda row: row["min_window"], default=None)
    return {"window": window, "prefill_tps": tps, "unknown_tps_policy": policy, "evaluated": evaluated,
            "routable": [row["class"] for row in routable], "best": best["class"] if best else None}


def cache_verdict(proof: dict[str, Any]) -> str:
    """The proof's NUMBERS decide the verdict; the prose in `status` is a label, never the evidence.

    A measured speedup below the declared bar is DISPROVEN - never "unknown", because the run HAPPENED.
    An unrun proof is `not_yet_run`, and a declaration that carries neither is a fault, not a pass.
    """
    measured = proof.get("measured_20261014") or {}
    speedup, bar = measured.get("speedup_measured"), proof.get("min_speedup")
    if isinstance(speedup, (int, float)) and isinstance(bar, (int, float)):
        return "proven" if float(speedup) >= float(bar) else "disproven"
    if str(proof.get("status", "")).strip().lower().startswith("not_yet_run"):
        return "not_yet_run"
    return "undeclared"


def prefix_rows_from_source(source: str, label: str, floor: int) -> dict[str, list[dict[str, Any]]]:
    """Classify every module-level *SYSTEM* constant in ONE file's source (pure: source in, rows out).

    Four things a grep cannot tell apart: a byte-stable PROMPT, a prompt BUILT per call (an f-string or
    a concatenation - unique every call, amortisable by nothing), a name that merely mentions a system
    (a role string, a token budget), and a constant too short to be a prompt at all.
    """
    import ast

    out: dict[str, list[dict[str, Any]]] = {"stable": [], "volatile": [], "ignored": []}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name) and "SYSTEM" in t.id]
        if not names:
            continue
        name = names[0]
        literal = isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        row: dict[str, Any] = {"file": label, "name": name,
                               "chars": len(node.value.value) if literal else None}
        if not literal:
            row["state"] = ("built_per_call" if isinstance(node.value, (ast.JoinedStr, ast.BinOp, ast.Call))
                            else "not_a_prompt")
            out["volatile" if row["state"] == "built_per_call" else "ignored"].append(row)
        elif len(node.value.value) < floor:
            row["state"] = "below_the_declared_prompt_floor"
            out["ignored"].append(row)
        else:
            row["state"] = "byte_stable"
            out["stable"].append(row)
    return out


def prefix_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    """The pipeline's amortisation PRECONDITION, over the pipeline's own source.

    A prefix that interpolates a date, a run id or a path is unique per call, so NO amount of batching
    can amortise it. And a prefix is only worth amortising if it is LONG: the classified rows are the
    precondition, so a label counted as a prefix would overstate what packing can buy.
    """
    stages = cfg.get("pipeline_stages") or {}
    declared = int(stages.get("system_prefixes_verified_byte_stable", 0))
    floor = int(stages.get("min_prompt_chars", 1))
    totals: dict[str, list[dict[str, Any]]] = {"stable": [], "volatile": [], "ignored": []}
    for path in sorted((repo_root() / "pipeline").glob("*.py")):
        rows = prefix_rows_from_source(path.read_text(), path.name, floor)
        for key, items in rows.items():
            totals[key].extend(items)
    return {"declared_stable": declared, "stable": len(totals["stable"]), "rows": totals["stable"],
            "volatile": totals["volatile"], "ignored": totals["ignored"],
            "prompt_floor_chars": floor, "ok": len(totals["stable"]) >= declared}


def ab_probe(cfg: dict[str, Any], model: str, prompt_tokens: int, timeout: int = 900) -> dict[str, Any]:
    """The ONLY certification of prefix REUSE: one identical prefix, two calls, the server's own count.

    Sends, so it is opt-in and declared OFF the ladder. The third call is the CONTROL: the same prefix
    on a DIFFERENT model must NOT be reused, which is what makes the first two a measurement of a cache
    rather than of a page of memory that happened to be warm.
    """
    ab = (cfg.get("prefill_budget") or {}).get("ab_probe") or {}
    filler, per_unit = str(ab.get("filler", "")), float(ab.get("chars_per_token_measured", 0) or 0)
    if not filler or per_unit <= 0:
        raise ProbeError("FAIL-CLOSED (agent-context): the A/B names no declared filler or its measured "
                         "chars-per-token rate - a probe may not invent either (C12)")
    prefix = (filler * (int(prompt_tokens * per_unit) // len(filler) + 1))[: int(prompt_tokens * per_unit)]
    provider = read_json(home_path(cfg, "declaration"))
    base_url, auth = provider_auth(provider)
    template = str(cfg.get("homes", {}).get("chat_endpoint", "")).split("#", 1)[0]
    if not template or not base_url:
        raise ProbeError("FAIL-CLOSED (agent-context): the declaration names no chat endpoint (C12)")
    url = template.format(base_url=base_url.rstrip("/"))

    def once(target: str, tail: str) -> dict[str, Any]:
        payload = {"model": target, "max_tokens": 1, "temperature": 0.0, "stream": False,
                   "messages": [{"role": "system", "content": "You are a terse assistant."},
                                {"role": "user", "content": prefix + "\n" + tail}]}
        started = time.time()
        body = _post_json(url, payload, auth, timeout)
        usage = body.get("usage") or {}
        return {"model": target, "seconds": round(time.time() - started, 1),
                "prompt_tokens": usage.get("prompt_tokens"),
                "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                "prefill_tps": usage.get("prompt_tokens_per_second")}

    first, second = once(model, "Reply OK (a)"), once(model, "Reply OK (b)")
    control = once(str(ab.get("control_model", "")), "Reply OK (c)")
    speedup = None
    if first.get("seconds") and second.get("seconds"):
        speedup = round(float(first["seconds"]) / float(second["seconds"]), 2)
    proof = (cfg.get("cache_accounting") or {}).get("proof") or {}
    bar = proof.get("min_speedup")
    sent = {"chars": len(prefix), "tokens_estimated_from_the_declared_rate": prompt_tokens}
    return {"model": model, "sent": sent, "call1": first, "call2": second, "control_call": control,
            "control_model": ab.get("control_model"), "speedup": speedup, "bar": bar,
            "verdict": ("proven" if isinstance(speedup, float) and isinstance(bar, (int, float))
                        and speedup >= float(bar) else "disproven")}


def _post_json(url: str, payload: dict[str, Any], auth: str | None, timeout: int) -> dict[str, Any]:
    """The one POST this probe ever makes; reached only by the declared, off-ladder A/B mode."""
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - declared local home
        return json.loads(response.read().decode())


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
    prefill_rows = measured_prefill(cfg)
    routes = {}
    for model, window in sorted(served["windows"].items()):
        tps = (prefill_rows.get(model) or {}).get("prefill_tps")
        bill = prefill_bill(window, tps, classes, cfg)
        routes[model] = {
            "window": window,
            "class": window_class(window, classes),
            "trigger": effective_trigger(window, inputs["threshold"]["value"], inputs["cap"]["value"]),
            "prefill_tps": tps,
            "evaluated": bill["evaluated"],
            "routable_classes": bill["routable"],
            "best_class": bill["best"],
        }
    ledger = ledger_summary(home_path(cfg, "cache_ledger"), cfg)
    proof = (cfg.get("cache_accounting") or {}).get("proof") or {}
    return {
        "served": served["windows"],
        "served_error": served["error"],
        "declared": declared,
        "parity": verdicts,
        "trigger_inputs": inputs,
        "routes": routes,
        "ledger": ledger,
        "cache_verdict": cache_verdict(proof),
        "cache_proof_bar": proof.get("min_speedup"),
        "cache_proof_status": proof.get("status"),
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
    if report["cache_verdict"] == "undeclared":
        faults.append("the cache proof carries NO measured verdict and no not-yet-run status: a rail that "
                      "cannot say whether reuse was measured cannot say whether the local loop is affordable")
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
    print(f"== LAYER 4b - the cache proof reads: {report['cache_verdict']} "
          f"(declared bar {report['cache_proof_bar']}x, declared status {report['cache_proof_status']!r}) ==")
    print("== LAYER 5 - the prefill bill (a window is not a budget) ==")
    for model, spec in sorted(report["routes"].items()):
        if spec["prefill_tps"] is None:
            print(f"   UNMEASURED throughput -> NO route, fail-closed: {model}")
            continue
        print(f"   {float(spec['prefill_tps']):>7.1f} tok/s  best={str(spec['best_class']):13} "
              f"routable={spec['routable_classes']}  {model}")
        for row in spec["evaluated"]:
            print(f"        {row['class']:16} working_set={row['working_set']:>7} seconds={row['seconds']} "
                  f"budget_s={row['budget_s']} -> {row['verdict']}")
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

#: The prefix auditor's own fixture: one module with all FOUR shapes the classifier must separate, so
#: the control cannot pass by classifying everything the same way.
PREFIX_FIXTURE_SOURCE = (
    'SYSTEM_PROMPT = "{pad}"\n'
    'SYSTEM = "system"\n'
    'SYSTEM_LIVE = f"built per call {pad}"\n'
    'MAX_SYSTEM_CHARS = 400\n'
)
#: The forbidden set and the baseline numbers are DECLARED (config/agent_context.yaml#self_scan, C12):
#: a fixture nobody declares is a magic value with a good excuse, and this self-scan is the rail that
#: proves the report path names neither a path, a host nor a number the declaration owns.
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
    "a_model_that_cannot_pay_the_prefill_bill_is_not_routable_to_the_class",
    "the_working_set_is_divided_not_the_window",
    "a_measured_cache_failure_is_disproven_and_never_unknown",
    "an_estimated_prompt_size_is_refused_as_a_measurement",
    "the_prompt_floor_separates_a_prefix_from_a_label",
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
    scan = cfg.get("self_scan") or {}
    forbidden = tuple(str(lit) for lit in (scan.get("forbidden_everywhere") or []))
    baselines = tuple(str(num) for num in (scan.get("baseline_numbers") or []))
    if not forbidden or not baselines:
        raise ProbeError("FAIL-CLOSED (agent-context): self_scan declares no fixtures - a self-scan with no "
                         "declared forbidden set proves nothing (C12)")
    control(CONTROL_LABELS[9], not [lit for lit in forbidden if lit in report_path])
    control(CONTROL_LABELS[10], not [num for num in baselines if num in report_path_source()]
            and REPORT_PATH_MARKER == str(scan.get("marker", "")))
    refused = False
    try:
        prefix_hazards({"prefix_stability": {}}, {})
    except ProbeError:
        refused = True
    control(CONTROL_LABELS[11], refused)

    # ── LAYER 5: the prefill bill, asserted against the DECLARATION's own measured throughputs ──
    live_classes = cfg.get("classes") or {}
    throughputs = [float(row["prefill_tps"]) for row in measured_prefill(cfg).values()
                   if isinstance(row.get("prefill_tps"), (int, float))]
    if not throughputs:
        raise ProbeError("FAIL-CLOSED (agent-context): no measured throughput is declared - the prefill "
                         "bill cannot be controlled, and a control that cannot run is not a control")
    floor = int((live_classes.get("agent_loop") or {}).get("min_window", 0))
    fast = prefill_bill(floor, max(throughputs), live_classes, cfg)
    slow = prefill_bill(floor, min(throughputs), live_classes, cfg)
    control(CONTROL_LABELS[12], "agent_loop" in fast["routable"] and "agent_loop" not in slow["routable"])
    # the bill divides the WORKING SET: with the window divided instead, this model is refused
    toy = {"c": {"min_window": 1, "working_set": 10, "prefill_budget_s": 100}}
    toy_bill = prefill_bill(1000000, 1.0, toy, cfg)
    control(CONTROL_LABELS[13], toy_bill["routable"] == ["c"]
            and toy_bill["evaluated"][0]["working_set"] == 10)
    # the verdict comes from the NUMBERS: a status string alone may not manufacture one
    control(CONTROL_LABELS[14],
            cache_verdict({"min_speedup": 5, "measured_20261014": {"speedup_measured": 1.01}}) == "disproven"
            and cache_verdict({"min_speedup": 5, "measured_20261014": {"speedup_measured": 44}}) == "proven"
            and cache_verdict({"status": "not_yet_run_on_this_machine"}) == "not_yet_run")
    estimated_refused = False
    try:
        measured_prompt_tokens({"prompt_tokens": 50000, "estimated": True})
    except ProbeError:
        estimated_refused = True
    control(CONTROL_LABELS[15], estimated_refused
            and measured_prompt_tokens({"prompt_tokens": 50000}) == 50000)
    audit = prefix_audit(cfg)
    fixture_rows = prefix_rows_from_source(PREFIX_FIXTURE_SOURCE.replace("{pad}", "x" * 300), "fixture.py", 200)
    control(CONTROL_LABELS[16],
            all(row["chars"] >= audit["prompt_floor_chars"] for row in audit["rows"])
            and [row["name"] for row in fixture_rows["stable"]] == ["SYSTEM_PROMPT"]
            and [row["name"] for row in fixture_rows["volatile"]] == ["SYSTEM_LIVE"]
            and sorted(row["name"] for row in fixture_rows["ignored"]) == ["MAX_SYSTEM_CHARS", "SYSTEM"])

    held = passed == total
    print(f"{'ok ' if held else 'FAIL'} agent-context-probe --selftest: {passed}/{total} known-answer control(s) green")
    codes = cfg.get("exit_codes", {})
    return int(codes.get("ok", 0)) if held else int(codes.get("error", 1))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: report the layers, audit the pipeline's prefixes, run the A/B, or prove the controls."""
    parser = argparse.ArgumentParser(description="Read-only probe of the agent harness's context contract (T-132)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls")
    parser.add_argument("--prefix-audit", action="store_true", help="audit the pipeline's system prefixes (offline)")
    parser.add_argument("--prefill-ab", action="store_true", help="SEND the two-call prefix-reuse A/B (off the ladder)")
    parser.add_argument("--model", default="", help="the model the A/B runs on (default: the declared loop slot)")
    parser.add_argument("--tokens", type=int, default=0, help="A/B prefix size (default: the declared working set)")
    parser.add_argument("--config", default=None, help="override the declaration path (testing only)")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    codes = cfg.get("exit_codes", {})
    if args.selftest:
        return selftest(cfg)
    if args.prefix_audit:
        audit = prefix_audit(cfg)
        for row in audit["rows"]:
            print(f"   stable  {row['chars']:>6} chars  {row['file']}:{row['name']}")
        for row in audit["volatile"]:
            print(f"   VOLATILE (built per call, not amortisable)  {row['file']}:{row['name']}")
        for row in audit["ignored"]:
            print(f"   not a prompt ({row['state']})  {row['file']}:{row['name']}")
        print(f"{'ok ' if audit['ok'] else 'FAIL'} prefix-audit: {audit['stable']} byte-stable system "
              f"prefix(es), {len(audit['volatile'])} built per call (declared minimum {audit['declared_stable']})")
        return int(codes.get("ok", 0) if audit["ok"] else codes.get("fault", 2))
    if args.prefill_ab:
        classes = cfg.get("classes") or {}
        slots = ((cfg.get("routing") or {}).get("measured_routable_20261014") or {}).get("agent_loop") or [""]
        model = args.model or str(slots[0])
        tokens = args.tokens or int((classes.get("agent_loop") or {}).get("working_set", 0))
        if not model or not tokens:
            raise ProbeError("FAIL-CLOSED (agent-context): the A/B needs a model and a prefix size, and "
                             "neither is invented here (C12)")
        result = ab_probe(cfg, model, tokens)
        print(json.dumps(result, indent=2, sort_keys=True))
        proven = result["verdict"] == "proven"
        print(f"{'ok ' if proven else 'FAIL'} prefill-ab: {result['speedup']}x against a declared bar of "
              f"{result['bar']}x -> {result['verdict']}")
        return int(codes.get("ok", 0) if proven else codes.get("fault", 2))
    try:
        report = build_report(cfg)
    except ProbeError as exc:
        print(f"FAIL agent-context: {exc}", file=sys.stderr)
        return int(codes.get("fault", 2))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return int(codes.get("ok", 0))
    return render(report, cfg)


if __name__ == "__main__":
    sys.exit(main())
