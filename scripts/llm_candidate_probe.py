#!/usr/bin/env python3
"""llm_candidate_probe.py - ONE RECEIPT PER CANDIDATE MODEL, IN THE ORDER THE EVIDENCE HAS TO COME (D-3061).

WHY THIS EXISTS. Model research had no shape: a candidate was argued about in prose, `llmfit` was sometimes
consulted and sometimes not, and a benchmark number quoted from a card sat next to a local measurement as if the two
were the same kind of claim. This script makes the ORDER mechanical, because the order is the argument:

  1. IS IT HERE AT ALL (D-3034/D-2957). llmfit's catalogue is queried by exact id. Not found is reported as
     NOT-IN-CATALOG - an ABSENT reading, never a zero and never a guess.
  2. DOES IT FIT THIS MACHINE. fit_level / memory_required_gb / disk_size_gb / best_quant, read from llmfit.
  3. WHAT WOULD IT COST PER TOKEN. estimated_tps, WITH the context cap llmfit computed it at (8192 by default) named
     beside it - a speed estimate at a context this OS never runs in is a ceiling, never a loop time.
  4. WHAT MAY NOT BE USED AS EVIDENCE. The refused classes come from config/model_oracles.yaml, so the refusals are
     declared once (C12) and printed every time instead of being remembered.
  5. WHAT STILL HAS TO HAPPEN. A promotion is gated on the machine-truthful oracle, which is a MEASURED LOOP -
     `python3 scripts/measure_subagent_loop.py` - never on this receipt.

WHAT THIS SCRIPT DOES NOT DO. It does not download, serve, benchmark or promote anything: llmfit is read-only, and a
probe that could install a model would be an unwatched mover (D-3049) wearing a research label.

Usage:
  python3 scripts/llm_candidate_probe.py --model Qwen/Qwen3-30B-A3B-Instruct-2507
  python3 scripts/llm_candidate_probe.py --model ... --write     # receipt -> governance/evidence/
  python3 scripts/llm_candidate_probe.py --oracles               # the declared oracle vocabulary
  python3 scripts/llm_candidate_probe.py --selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
ORACLES = REPO / "config" / "model_oracles.yaml"
EVIDENCE = REPO / "governance" / "evidence"
LLMFIT_TIMEOUT_S = 120.0
SCHEMA_VERSION = "1.0"


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Parse a YAML mapping, fail closed (C16: a missing declaration is FATAL, never a default).

    Args:
        path: the file to parse.

    Returns:
        The mapping.

    Raises:
        SystemExit: when the file is absent, unreadable, or not a mapping.
    """
    import yaml

    if not path.exists():
        raise SystemExit(f"FATAL: {path} does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FATAL: {path} is not a mapping")
    return data


def llmfit() -> tuple[str, str]:
    """Resolve the llmfit binary from PATH - never a hardcoded home (C12).

    Returns:
        (binary, version).

    Raises:
        SystemExit: when llmfit is not on PATH, or does not answer --version.
    """
    binary = shutil.which("llmfit")
    if not binary:
        raise SystemExit("FATAL: llmfit is not on PATH - the fit oracle is ABSENT, not empty (D-2957)")
    proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
    return binary, (proc.stdout or proc.stderr).strip().splitlines()[0] if proc.stdout or proc.stderr else "unknown"


def probe(binary: str, model: str) -> dict[str, Any] | None:
    """Read one model's fit record from llmfit.

    Args:
        binary: the resolved llmfit path.
        model: the exact HuggingFace id.

    Returns:
        The model record, or None when llmfit does not carry it (NOT-IN-CATALOG - absent, not zero).

    Raises:
        SystemExit: when llmfit answers something that is not JSON, or answers nothing at all.
    """
    proc = subprocess.run([binary, "info", model, "--json"], capture_output=True, text=True, timeout=LLMFIT_TIMEOUT_S)
    if proc.returncode == 2:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        first = (proc.stdout or proc.stderr).strip().splitlines()
        raise SystemExit(f"FATAL: llmfit did not answer JSON for {model}: {first[:1]}") from exc
    models = payload.get("models") if isinstance(payload, dict) else None
    if not models:
        return None
    return models[0]


def verdict(row: dict[str, Any] | None) -> list[str]:
    """Render the fit reading, naming the context its speed was estimated at.

    Args:
        row: a llmfit model record, or None.

    Returns:
        Human-readable lines. A None row yields exactly one: NOT-IN-CATALOG.
    """
    if row is None:
        return ["  NOT-IN-CATALOG: llmfit does not carry this id - the fit reading is ABSENT, not zero (D-2957)"]
    effective = row.get("effective_context_length")
    declared = row.get("context_length")
    return [
        f"  name           {row.get('name')}",
        f"  params         {row.get('parameter_count')}  moe={row.get('is_moe')}  license={row.get('license')}",
        f"  context        declared={declared}  estimated_at={effective}"
        + ("   <-- the speed below is computed at THIS cap, never at the declared one" if effective and declared
           and int(effective) < int(declared) else ""),
        f"  fit            fit_level={row.get('fit_level')}  memory_required_gb={row.get('memory_required_gb')}"
        f"  disk_size_gb={row.get('disk_size_gb')}  best_quant={row.get('best_quant')}",
        f"  speed          estimated_tps={row.get('estimated_tps')} (a CEILING: prefill + growing-context decode"
        f" are what a loop costs, DELEGATE-002)",
        f"  tags           {row.get('capabilities')}   <-- catalogue tags: measured INVERTED on this roster,"
        f" never capability evidence",
    ]


def render(model: str, version: str, row: dict[str, Any] | None, oracles: dict[str, Any]) -> str:
    """Compose the whole probe, in the order the evidence has to come.

    Args:
        model: the candidate id.
        version: the llmfit version string.
        row: the fit record, or None.
        oracles: the parsed config/model_oracles.yaml.

    Returns:
        A printable receipt body.
    """
    lines = [f"CANDIDATE {model}", f"  fit oracle     {version}", "", "1. IS IT IN THE CATALOGUE"] + verdict(row)
    lines += ["", "2. WHAT MAY NOT BE USED AS EVIDENCE (declared once, in config/model_oracles.yaml)"]
    for name, why in (oracles.get("refused_as_evidence") or {}).items():
        lines.append(f"  REFUSED  {name:28} {why}")
    lines += ["", "3. WHAT STILL HAS TO HAPPEN BEFORE A PROMOTION"]
    gate = [n for n, spec in (oracles.get("oracles") or {}).items()
            if isinstance(spec, dict) and spec.get("gates_promotion")]
    for name in gate or ["(NONE DECLARED - no oracle may gate a promotion: a FAULT)"]:
        spec = (oracles.get("oracles") or {}).get(name) or {}
        lines.append(f"  GATE     {name}  {spec.get('rail') or spec.get('measures') or ''}")
    lines.append("  A download is justified only by a ROLE THAT IS EMPTY, never by a model that is merely newer.")
    return "\n".join(lines)


def write_receipt(body: dict[str, Any], model: str) -> pathlib.Path:
    """Write the receipt crash-safely and immutably named by date + model (C6/R14).

    Args:
        body: the receipt payload.
        model: the candidate id (used in the filename).

    Returns:
        The receipt path.
    """
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    slug = model.replace("/", "__")
    path = EVIDENCE / f"LLM_CANDIDATE_{datetime.date.today():%Y%m%d}_{slug}.json"
    fd, tmp = tempfile.mkstemp(dir=str(EVIDENCE), prefix=".llm_probe.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(body, handle, indent=1, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def _selftest() -> int:
    """Known-answer controls over the pure rendering - no llmfit call, no filesystem write.

    Returns:
        0 when every control holds, 1 otherwise.
    """
    good = {
        "name": "Qwen/Qwen3-30B-A3B-Instruct-2507", "parameter_count": "30.5B", "is_moe": True,
        "license": "apache-2.0", "context_length": 262144, "effective_context_length": 8192,
        "fit_level": "Perfect", "memory_required_gb": 15.6, "disk_size_gb": 30.53, "best_quant": "mlx-8bit",
        "estimated_tps": 59.3, "capabilities": ["Tool Use"],
    }
    oracles = {"refused_as_evidence": {"parameter_count": "x"}, "oracles": {
        "measure_subagent_loop": {"gates_promotion": True, "rail": "measure_subagent_loop.py"},
        "llmfit": {"gates_promotion": False}}}
    text = render("m", "llmfit 0.9.38", good, oracles)
    controls = [
        ("an absent catalogue row is NOT-IN-CATALOG, never a zero", "NOT-IN-CATALOG" in " ".join(verdict(None))),
        ("the speed estimate names the context it was computed at", "estimated_at=8192" in text),
        ("a capped estimate is marked as a cap", "computed at THIS cap" in text),
        ("catalogue tags are printed as refused evidence", "measured INVERTED" in text),
        ("only the machine-truthful oracle is printed as a gate",
         "GATE     measure_subagent_loop" in text and "GATE     llmfit" not in text),
        ("refused classes are printed, not remembered", "REFUSED  parameter_count" in text),
    ]
    for label, ok in controls:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    passed = sum(1 for _, ok in controls if ok)
    print(f"selftest: {passed}/{len(controls)}")
    return 0 if passed == len(controls) else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: CLI arguments (default: sys.argv[1:]).

    Returns:
        0 on success / 1 when a declaration is broken.
    """
    parser = argparse.ArgumentParser(description="one receipt per candidate model, fit-first (D-3061)")
    parser.add_argument("--model", help="exact HuggingFace id to probe")
    parser.add_argument("--write", action="store_true", help="write the receipt to governance/evidence/")
    parser.add_argument("--oracles", action="store_true", help="print the declared oracle vocabulary")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    oracles = _yaml(ORACLES)
    if args.oracles:
        for name, spec in (oracles.get("oracles") or {}).items():
            kind = (spec or {}).get("kind")
            gate = "GATE" if (spec or {}).get("gates_promotion") else "prior"
            print(f"  {name:24} {kind:9} {gate:6} {(spec or {}).get('measures', '')[:90]}")
        for name, why in (oracles.get("refused_as_evidence") or {}).items():
            print(f"  REFUSED {name:24} {why}")
        return 0
    if not args.model:
        parser.error("--model is required (or --oracles / --selftest)")
    binary, version = llmfit()
    row = probe(binary, args.model)
    print(render(args.model, version, row, oracles))
    if args.write:
        body = {
            "schema_version": SCHEMA_VERSION,
            "gen_model": f"deterministic: llmfit {version}",
            "pipeline_commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                              capture_output=True, text=True).stdout.strip(),
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "candidate": args.model,
            "fit": row,
            "absent": row is None,
            "gates_promotion": [n for n, s in (oracles.get("oracles") or {}).items()
                                if isinstance(s, dict) and s.get("gates_promotion")],
        }
        print(f"\nreceipt -> {write_receipt(body, args.model)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
