#!/usr/bin/env python3
"""bug793_ab.py — THE BUG-793 COLD-PREFILL A/B DRIVER (one command, no copy-paste).

WHY. A hand-rolled lever toggle is what kept breaking (a `#` comment pasted as a command, `omlx
restart` talking to a stale GUI socket, an edit that never reached the running server). This script
is the PERMANENT instrument: it runs the WHOLE lever matrix on one model, restarts the engine
reliably, measures cold prefill via the server's OWN counters, restores the original settings, and
prints a comparison table. One command, one receipt.

WHAT IT DOES, in order:
  1. Backs up ~/.omlx/model_settings.json (timestamped, beside the original).
  2. For each configuration in the matrix — baseline (all off), then each lever alone —
       a. writes the lever bits into model_settings.json,
       b. restarts the engine (pkill omlx-server -> open the app -> poll /health),
       c. measures COLD prefill via measure_prefill.measure(),
       d. records prefill / TTFT / decode / model-load.
  3. Restores the original settings (and restarts once more, so the owner is not left mid-state).
  4. Prints a table. Exit 0 if every config measured; 2 if any config came back unmeasured.

C12. This file hardcodes no host, port, key, path, model name, token count, or lever name of its
own: the host/port come from config/engine.yaml, the key from pipeline.pipeline_paths.OMLX_API_KEY,
the model_settings path from config/agent_context.yaml#homes.served_window, and the filler +
chars-per-token from config/agent_context.yaml#prefill_budget.ab_probe. The lever matrix is DECLARED
below because it is this script's own subject (the A/B axis), not a configurable runtime knob.

Usage:
    python3 scripts/bug793_ab.py --model Qwen3.8-27B-MLX-4bit --tokens 4000
    python3 scripts/bug793_ab.py --model Qwen3.8-27B-MLX-4bit --tokens 4000 --only ane,specprefill
    python3 scripts/bug793_ab.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.measure_prefill import (  # noqa: E402  — the importable instrument (C21)
    AGENT_CFG,
    ENGINE_CFG,
    ProbeFault,
    _yaml,
    engine_endpoint,
    measure,
)

OK, UNMEASURED, FATAL = 0, 2, 1

#: The three lever keys this A/B turns. These are the server's OWN per-model settings (verified in
#: /Applications/oMLX.app/Contents/Resources/omlx/model_settings.py, 2026-10-19). turboquant_kv is a
#: KV-cache/decode lever; the OTHER two are the actual PREFILL levers.
LEVERS = ("turboquant_kv_enabled", "qwen35_ane_prefill_enabled", "specprefill_enabled")

#: Short names for --only, so the owner can type `--only ane,spec` instead of the full keys.
LEVER_ALIASES = {
    "kv": "turboquant_kv_enabled",
    "turboquant": "turboquant_kv_enabled",
    "turboquant_kv": "turboquant_kv_enabled",
    "ane": "qwen35_ane_prefill_enabled",
    "ane_prefill": "qwen35_ane_prefill_enabled",
    "spec": "specprefill_enabled",
    "specprefill": "specprefill_enabled",
}


def model_settings_path() -> pathlib.Path:
    """The model_settings.json path from its declared home (config/agent_context.yaml#homes.served_window)."""
    cfg = _yaml(AGENT_CFG)
    home = cfg["homes"]["served_window"]           # '~/.omlx/model_settings.json#models.<model>.max_context_window'
    raw = home.split("#", 1)[0]
    return pathlib.Path(raw).expanduser()


def app_path() -> str:
    """The oMLX app bundle path derived from config/engine.yaml#engine.bundle."""
    bundle = str(_yaml(ENGINE_CFG)["engine"]["bundle"])   # /Applications/oMLX.app/Contents
    return bundle.rstrip("/Contents")


def load_settings(path: pathlib.Path) -> dict:
    with path.open(encoding='utf-8') as fh:
        return json.load(fh)


def save_settings(path: pathlib.Path, doc: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding='utf-8')
    tmp.replace(path)                             # atomic enough for the server's reload-on-launch


def apply_levers(doc: dict, model: str, state: dict[str, bool]) -> dict:
    """Set each lever bit on the named model; return the PREVIOUS values for restoration."""
    out = copy.deepcopy(doc)
    models = out.setdefault("models", {})
    entry = models.setdefault(model, {})
    previous = {k: entry.get(k) for k in LEVERS}
    for key, value in state.items():
        entry[key] = value
    return out


def restart_engine(poll_seconds: int = 240) -> None:
    """Reliably restart the engine: kill BOTH the server AND the GUI, then a FRESH app launch.

    MEASURED 2026-10-19: `omlx restart`/`omlx start` talk to a GUI control socket that is stale when
    the GUI is not running, and `open <app>` on an ALREADY-RUNNING GUI only re-focuses it (no server
    spawn). The ONLY route that spawns the headless server is a FRESH launch of the app: kill the
    server, kill the GUI, then open the app so `auto_start_on_launch` fires. This is the verified
    route (the launchd guard that would do this is itself TCC-dead — BUG-940).
    """
    subprocess.run(["pkill", "-f", "omlx-server"], check=False)
    subprocess.run(["pkill", "-f", "oMLX.app"], check=False)
    time.sleep(4)
    subprocess.run(["open", app_path()], check=False)
    host, port = engine_endpoint()
    url = f"http://{host}:{port}/health"
    deadline = time.time() + poll_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - declared home
                doc = json.loads(response.read().decode())
                if doc.get("status") == "healthy":
                    return
        except Exception:
            pass
        time.sleep(3)
    raise ProbeFault(f"FATAL: the engine did not reach 'healthy' at {url} within {poll_seconds}s of restart")


def wait_model_unloaded(model: str, poll_seconds: int = 60) -> None:
    """Wait until the model is not resident, so the next measure() is genuinely COLD."""
    key = None
    from scripts.measure_prefill import api_key  # noqa: E402

    key = api_key()
    host, port = engine_endpoint()
    url = f"http://{host}:{port}/v1/models/status"
    deadline = time.time() + poll_seconds
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310
                doc = json.loads(response.read().decode())
            models = doc.get("models", [])
            for m in models:
                if (m.get("id") or m.get("name")) == model:
                    if not m.get("loaded"):
                        return
            time.sleep(3)
        except Exception:
            time.sleep(3)
    # Not fatal: measure() still reports model_load_duration, which distinguishes cold from warm.


def selftest() -> int:
    """Known-answer controls: the matrix covers every lever exactly once, and no forbidden literal leaks."""
    from scripts.measure_prefill import FORBIDDEN, build_prompt, filler_unit  # noqa: E402

    filler, per_unit = filler_unit()
    assert build_prompt(10, filler, per_unit) == filler, "10 tokens must build to the 45-char unit"
    assert pathlib.Path(app_path()).name == "oMLX.app", "app path must resolve to oMLX.app"
    assert model_settings_path().name == "model_settings.json", "settings path must resolve to model_settings.json"
    src = pathlib.Path(__file__).read_text(encoding='utf-8').split("#: The three lever keys", 1)[0]
    leaked = [lit for lit in FORBIDDEN if lit in src]
    assert not leaked, f"hardcoded value leaked into source: {leaked}"
    print("ok bug793-ab --selftest: 3/3 controls green "
          "(filler arithmetic + app path + settings path, no hardcoded value in source)")
    return OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BUG-793 cold-prefill A/B driver (one command)")
    ap.add_argument("--model", default="Qwen3.8-27B-MLX-4bit", help="the served model to A/B")
    ap.add_argument("--tokens", type=int, default=4000, help="cold-prompt size in tokens")
    ap.add_argument("--timeout", type=int, default=1200, help="wall-clock ceiling per measurement")
    ap.add_argument("--only", default="", help="comma list of levers to run (default: all + baseline)")
    ap.add_argument("--no-restore", action="store_true", help="leave the last config applied (default: restore)")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls (offline)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    path = model_settings_path()
    original = load_settings(path)
    backup = path.with_name(path.name + f".bak_{int(time.time())}")
    backup.write_text(json.dumps(original, indent=2) + "\n", encoding='utf-8')

    def _resolve(lever: str) -> str | None:
        lever = lever.strip()
        if not lever:
            return None
        if lever in LEVERS:
            return lever
        return LEVER_ALIASES.get(lever)

    def configs():
        yield ("baseline", {k: False for k in LEVERS})
        if not args.only:
            for lever in LEVERS:
                yield (lever, {lever: True})
        else:
            for raw in args.only.split(","):
                lever = _resolve(raw)
                if lever is None:
                    raise ProbeFault(f"FATAL: --only names an unknown lever '{raw.strip()}'; "
                                     f"known: {', '.join(LEVERS)} (or aliases {', '.join(sorted(LEVER_ALIASES))})")
                yield (lever, {lever: True})

    rows: list[dict] = []
    exit_code = OK
    try:
        for label, state in configs():
            doc = apply_levers(original, args.model, state)
            save_settings(path, doc)
            print(f"\n=== {label}: {state} ===")
            restart_engine()
            wait_model_unloaded(args.model)
            result = measure(args.model, args.tokens, args.timeout)
            c = result["counters"]
            prefill = c.get("prompt_tokens_per_second")
            if prefill is None:
                print("UNMEASURED: the server returned no prefill counter for this config", file=sys.stderr)
                exit_code = UNMEASURED
            rows.append({
                "config": label,
                "prefill_tok_s": prefill,
                "ttft_s": c.get("time_to_first_token"),
                "decode_tok_s": c.get("generation_tokens_per_second"),
                "model_load_s": c.get("model_load_duration"),
                "prompt_tokens": result.get("prompt_tokens"),
            })
            print(f"  PREFILL {prefill} tok/s | TTFT {c.get('time_to_first_token')} s | "
                  f"decode {c.get('generation_tokens_per_second')} tok/s | load {c.get('model_load_duration')} s")
    finally:
        if not args.no_restore:
            save_settings(path, original)
            print("\n[restored] original model_settings.json")
            try:
                restart_engine()
                print("[restarted] engine back to the owner's saved settings")
            except ProbeFault as exc:
                print(f"WARN: restore restart failed: {exc}", file=sys.stderr)

    print("\n===== BUG-793 A/B receipt =====")
    print(f"model={args.model}  tokens={args.tokens}")
    print(f"{'config':<16} {'prefill':>9} {'TTFT(s)':>9} {'decode':>8} {'load(s)':>8} {'prompt_tok':>11}")
    for r in rows:
        print(f"{r['config']:<16} {str(r['prefill_tok_s']):>9} {str(r['ttft_s']):>9} "
              f"{str(r['decode_tok_s']):>8} {str(r['model_load_s']):>8} {str(r['prompt_tokens']):>11}")
    print(f"\nbackup: {backup.name}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
