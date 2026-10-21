#!/usr/bin/env python3
"""W3 - WHICH HARNESS CAN BE WIRED TO THE ENGINE, AND WHICH CAN WORK UNATTENDED?

The engine ships its own wiring for nine clients, so the authoritative answer is LOCAL, not a
web search: Resources/omlx/integrations/<tool>.py is the exact code that configures each
harness, and "omlx launch <tool>" is the exact command that runs it. This workstream reads
BOTH, plus each installed CLI's own --help, and asks one question of each: can it be driven
WITHOUT a human at the keyboard (a print/exec/headless mode), or is it an interactive shell?
Maxwell OS automation depends on the first kind; the second kind is human-driven exploration.

Usage: python3 pipeline/research/ws_harness_survey.py --report <10_report.md> [--json-out f]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_HINT = re.compile(r"(ANTHROPIC_[A-Z_]+|OPENAI_[A-Z_]+|[A-Z_]*BASE_URL|[A-Z_]*API_KEY|[A-Z_]*MODEL[A-Z_]*)")
HEADLESS_HINT = re.compile(r"(--print|--exec|--non-interactive|exec|headless|--prompt|--message|--text)", re.I)
TOOL_BIN = {"claude": "claude", "codex": "codex", "opencode": "opencode", "openclaw": "openclaw",
            "hermes": "hermes", "pi": "pi", "copilot": "copilot", "dsh": "deepseek"}
LIST_RE = re.compile(r"^\s*([a-z_]+)\s+(.*?)\s*\((installed|not installed)\)\s*$")


def engine_conf() -> dict:
    """Read the engine's declared facts from its one home (C12)."""
    import yaml
    return yaml.safe_load((ROOT / "config" / "engine.yaml").read_text(encoding='utf-8'))["engine"]


def launch_list(cli: pathlib.Path) -> str:
    """Ask the engine which integrations it can launch (the authoritative list)."""
    try:
        proc = subprocess.run([str(cli), "launch", "list"], capture_output=True, text=True, timeout=60)
        return (proc.stdout + proc.stderr).strip()
    except Exception as exc:
        return "ERROR " + type(exc).__name__ + ": " + str(exc)


def integration_source(bundle: str, tool: str) -> tuple[str, str]:
    """Return the env names the engine sets for a tool, and any headless evidence in its code."""
    d = pathlib.Path(bundle) / "Resources" / "omlx" / "integrations"
    cand = [p for p in ([d / (tool + ".py")] + list(d.glob(tool + "*.py"))) if p.exists()]
    if not cand:
        return "", ""
    text = cand[0].read_text(errors="replace", encoding='utf-8')
    envs = sorted(set(ENV_HINT.findall(text)))
    head = "evidence" if HEADLESS_HINT.search(text) else "none"
    return cand[0].name + ": " + ", ".join(envs[:6]), head


def cli_probe(binary: str) -> str:
    """Look for a headless flag in the installed CLI's own help text."""
    try:
        proc = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return "not installed"
    except Exception as exc:
        return "probe error " + type(exc).__name__
    text = proc.stdout + proc.stderr
    hits = sorted(set(re.findall(r"(--print|--exec|--non-interactive|--headless|--prompt)", text)))
    return ("headless flags: " + ", ".join(hits)) if hits else "no headless flag in --help"


def main(argv: list[str]) -> int:
    """Survey every integration and append the verdict to the run's report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    report = pathlib.Path(args.report)
    conf = engine_conf()
    cli = pathlib.Path(conf["launch_cli"])

    def emit(line: str) -> None:
        with open(report, "a", encoding='utf-8') as fh:
            fh.write(line.rstrip() + chr(10))
            fh.flush()

    emit("")
    emit("## W3 harness survey - what the engine can wire, and what can run unattended")
    emit("STEP 1: asking the engine itself (omlx launch list)")
    listing = launch_list(cli)
    for l in listing.splitlines():
        emit("  " + l)
    rows = {}
    emit("| tool | installed | engine wiring (env it sets) | headless in engine code | CLI probe |")
    emit("|---|---|---|---|---|")
    for line in listing.splitlines():
        m = LIST_RE.match(line)
        if not m:
            continue
        tool, display, state = m.group(1), m.group(2).strip(), m.group(3) == "installed"
        wiring, head = integration_source(conf["bundle"], tool)
        probe = cli_probe(TOOL_BIN.get(tool, tool)) if state else "not installed"
        rows[tool] = {"display": display, "installed": state, "wiring": wiring,
                      "headless_in_engine_code": head, "cli_probe": probe}
        emit("| " + tool + " | " + str(state) + " | " + (wiring or "-") + " | " + head + " | " + probe + " |")
        emit("STEP: " + tool + " surveyed (installed=" + str(state) + ")")
    emit("")
    emit("READING: a tool with a headless mode AND engine wiring can be driven by a script. A tool with neither is")
    emit("an interactive shell: its value is human-driven exploration, not unattended pipeline work.")
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(rows, indent=1), encoding='utf-8')
    emit("STEP final: survey complete")
    emit("TERMINAL: DONE - every integration classified for unattended use")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
