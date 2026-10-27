#!/usr/bin/env python3
"""Pre-flight gate for the benchmark suites (mechanism M1).

WHY THIS EXISTS
---------------
tools/model_eval_suite.py sends real requests and grades the RESPONSE. It has no way to
tell "the model is bad" from "the harness asked a question the model could not answer".
Every historical incident has that exact shape, and in every one the harness defaulted to
"the model is bad":

  BUG-257  niah ctx 32000    -> HTTP 400 scored as a model failure (it is a chat-template ceiling)
  BUG-258  transport errors  -> scored as model failures (REAP toolcalling 0.50 -> 1.00 after fix)
  BUG-259  pruned models     -> still quoted as candidates in the decision table
  BUG-260  raw label vs canonical gold -> implausible 0.20 headlines
  BUG-262  missing reasoning-off prefix -> gpt-oss 0.00 on toolcalling = format artifact
  BUG-263  judge max_tokens=64 vs a Harmony reasoning model -> relabel silently labelled NOTHING
  OptiQ    max_tokens=512 vs a reasoning-first model -> 31% "no json", accuracy 0.445 vs 0.727

This module is the missing gate. It runs the REAL harness call() with the REAL per-item
max_tokens for each (model, suite) cell BEFORE any scoring and classifies the cell:

    VALID        -> the suite may score this cell
    NO_CONTENT   -> empty answer (reasoning-only / budget too small)  => NA, never 0
    NO_JSON      -> answer is not parseable JSON at this budget          => NA, never 0
    CTX_CEILING  -> HTTP 400 at this ctx_tokens (chat-template limit)    => NA, never 0
    HTTP_ERROR   -> other transport failure                              => NA, never 0
    TIMEOUT      -> exceeded omlx.timeout_s                              => NA, never 0

USAGE
-----
    python3 tools/bench_preflight.py --static            # env only; safe while a run is live
    python3 tools/bench_preflight.py                     # full gate (must be the only oMLX client)
    python3 tools/bench_preflight.py --models A,B --suites planning,toolcalling

EXIT CODES (see config/bench_preflight.yaml)
    0 all probed cells VALID   1 >=1 cell not VALID   2 environment unsafe
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

REPO: Path = Path(__file__).resolve().parents[1]
TOOLS: Path = REPO / "tools"
for _p in (str(REPO), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CONFIG_PATH: Path = REPO / "config" / "bench_preflight.yaml"
VALID: str = "VALID"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the preflight policy. Raises if absent: a missing gate must never pass silently (C16)."""
    import yaml  # local import keeps --help usable without PyYAML

    if not path.exists():
        raise FileNotFoundError("preflight config missing: " + str(path))
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _http_get(cfg: dict[str, Any], path: str) -> dict[str, Any] | None:
    """GET an oMLX endpoint, returning parsed JSON or None on any failure."""
    url = cfg["omlx"]["base_url"].rstrip("/") + path
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + cfg["omlx"]["api_key"]})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def list_models(cfg: dict[str, Any]) -> list[str]:
    """Return the models the running oMLX server currently exposes."""
    payload = _http_get(cfg, cfg["omlx"]["models_path"]) or {}
    return sorted(str(m.get("id", "")) for m in payload.get("data", []))


def _process_table() -> list[tuple[int, str, int]]:
    """Portable process listing (no pgrep) -> [(pid, ppid, command)]."""
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,ppid=,command="], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return []
    rows: list[tuple[int, str, int]] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            rows.append((int(parts[0]), parts[2].strip(), int(parts[1])))
        except ValueError:
            continue
    return rows


def _ancestor_pids() -> set[int]:
    """Return our own pid plus every ancestor pid.

    WHY: a benchmark launched as 'bash -c cd ... && python3 tools/model_eval_suite.py' makes the
    WRAPPER shell match the pattern too, so the gate flagged its own launcher as a concurrent run
    and refused to start. Excluding the ancestor chain fixes that without loosening the guard.
    """
    table = {pid: ppid for pid, _cmd, ppid in _process_table()}
    seen: set[int] = set()
    cur = os.getpid()
    while cur and cur not in seen:
        seen.add(cur)
        cur = table.get(cur, 0)
    return seen


def concurrent_benchmarks(cfg: dict[str, Any]) -> list[str]:
    """Return commands of other benchmark processes. Probing during a run evicts the resident model (BUG-255)."""
    mine = _ancestor_pids()
    hits: list[str] = []
    for pid, cmd, _ppid in _process_table():
        if pid in mine or "bench_preflight" in cmd:
            continue
        for pat in cfg["environment"]["block_if_running"]:
            if pat in cmd:
                hits.append(str(pid) + " " + cmd[:120])
                break
    return hits


def disk_free_gb(path: Path) -> float:
    """Free GiB on the volume holding path (BUG-261: a reclaim filled the disk to 1.7 GiB)."""
    import shutil

    return round(shutil.disk_usage(str(path)).free / (1024 ** 3), 1)


def _sha(path: Path) -> str:
    """SHA-256 of a file, or 'missing'."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else "missing"


def fingerprint(cfg: dict[str, Any], models: list[str], suites: list[str], budgets: dict[str, int]) -> str:
    """Stable hash of (harness code, policy, models, suites, per-suite budgets).

    A result is only comparable to a preflight with the SAME fingerprint; the audit script
    uses this to refuse stale gates.
    """
    blob = json.dumps(
        {
            "harness": _sha(TOOLS / "model_eval_suite.py"),
            "config": _sha(CONFIG_PATH),
            "models": sorted(models),
            "suites": sorted(suites),
            "budgets": {k: budgets[k] for k in sorted(budgets)},
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _phantom_check() -> dict[str, Any]:
    """BUG-1037: every registered model id's bytes must resolve on disk (D-3034).

    The portfolio check above compares NAMES against the live list; it never asks whether an
    id's bytes exist, so subset mode passed while phantom ids stayed registered. This is the
    instrument that would have caught BUG-410's 6 phantoms. The resolution rule is reused from
    scripts/list_model_phantoms.py (single source, no duplicate implementation - C21).
    """
    scripts = str(REPO / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        from list_model_phantoms import list_phantoms, _engine_paths  # noqa: PLC0415

        model_dir, settings = _engine_paths()
        hub = Path.home() / ".cache" / "huggingface" / "hub"
        phantoms = list_phantoms(model_dir, settings, hub)
    except Exception as exc:  # C16: a missing/unreadable registry must not pass silently
        return {"check": "phantom_models", "ok": False,
                "detail": "registry unusable: " + type(exc).__name__ + " " + str(exc)[:120]}
    return {"check": "phantom_models", "ok": not phantoms,
            "detail": "0 phantoms" if not phantoms else "UNRESOLVED: " + ", ".join(sorted(phantoms))}


def check_environment(cfg: dict[str, Any], models: list[str], full: bool) -> tuple[list[dict[str, Any]], bool]:
    """Run every non-model environment check. Returns (findings, unsafe)."""
    findings: list[dict[str, Any]] = []
    unsafe = False

    health = _http_get(cfg, cfg["omlx"]["health_path"])
    findings.append({"check": "omlx_reachable", "ok": health is not None,
                     "detail": (health or {}).get("status", "UNREACHABLE")})
    unsafe = unsafe or health is None

    live = list_models(cfg)
    expected = list(cfg["environment"]["expected_models"])
    mode = cfg["environment"].get("expected_models_mode", "exact")
    if mode == "exact":
        ok = live == sorted(expected)
        detail = "match" if ok else "registry=" + str(live) + " expected=" + str(sorted(expected))
    else:
        missing = [m for m in expected if m not in live]
        ok = not missing
        detail = "all present" if ok else "missing=" + str(missing)
    findings.append({"check": "portfolio_" + mode, "ok": ok, "detail": detail})
    unsafe = unsafe or not ok

    phantom = _phantom_check()
    findings.append(phantom)
    unsafe = unsafe or not phantom["ok"]

    want = {m for m in models}
    unseen = [m for m in want if m not in live]
    findings.append({"check": "requested_models_served", "ok": not unseen,
                     "detail": "all served" if not unseen else "not in registry: " + str(unseen)})
    unsafe = unsafe or bool(unseen)

    free = disk_free_gb(REPO)
    floor = float(cfg["environment"]["min_free_gb"])
    findings.append({"check": "disk_free_gb", "ok": free >= floor, "detail": str(free) + " GiB (floor " + str(floor) + ")"})
    unsafe = unsafe or free < floor

    busy = concurrent_benchmarks(cfg)
    findings.append({"check": "no_concurrent_benchmark", "ok": not busy,
                     "detail": "idle" if not busy else "LIVE: " + "; ".join(busy)})
    if full:
        unsafe = unsafe or bool(busy)
    return findings, unsafe


def load_harness() -> tuple[dict[str, Callable[[], list[dict[str, Any]]]], Callable[..., str]]:
    """Import the real harness so the gate probes the exact production call path (not a copy)."""
    import model_eval_suite as harness  # tools/ is on sys.path

    return harness.SUITES, harness.call


def first_item(suite: str, suites: dict[str, Callable[[], list[dict[str, Any]]]], cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Build a suite and return its first item, or None if the suite cannot be built."""
    try:
        items = suites[suite]()
    except Exception:
        return None
    if not items:
        return None
    item = dict(items[0])
    item.setdefault("max_tokens", int(cfg["probe"]["default_max_tokens"]))
    return item


def _classify_error(rec: dict[str, Any], cfg: dict[str, Any], text: str) -> str:
    """Map a call exception onto a cell status."""
    markers = [str(m) for m in cfg["probe"]["http_error_markers"]]
    if str(cfg["probe"]["ceiling_marker"]) in text and rec["ctx_tokens"]:
        return "CTX_CEILING"
    if "timeout" in text.lower():
        return "TIMEOUT"
    if any(m in text for m in markers):
        return "HTTP_ERROR"
    return "NO_CONTENT"


def _gradable(item: dict[str, Any], content: str) -> tuple[bool, str]:
    """Ask the suite's OWN grader whether this response can be scored at all.

    This replaces an earlier "is it JSON?" rule that was simply WRONG for most suites. Replaying
    the stored checkpoint showed planning graded-ok rows are 0% JSON, niah 0%, ifeval 0%,
    humaneval 1.3% - their graders read prose or numbers. Demanding JSON marked real measurements
    NA, which is the same class of error as scoring a harness failure as a model failure, inverted.

    Args:
        item: a built suite item (must carry its "grader" callable).
        content: the raw model response.

    Returns:
        (gradable, detail) - False when the grader cannot render a verdict.
    """
    grader = item.get("grader")
    if not callable(grader):
        return False, "suite item carries no grader"
    try:
        verdict = grader(content)
    except Exception as exc:
        return False, "grader raised " + type(exc).__name__ + ": " + str(exc)[:90]
    if not (isinstance(verdict, tuple) and len(verdict) == 2):
        return False, "grader returned " + type(verdict).__name__ + ", expected (ok, detail)"
    return True, str(verdict[1])[:80]


def probe_cell(cfg: dict[str, Any], model: str, suite: str, item: dict[str, Any],
               call: Callable[..., str]) -> dict[str, Any]:
    """Probe one (model, suite) cell and decide whether the harness can GRADE it. Never raises.

    A cell is VALID when the real call returns content and the suite's real grader can render a
    verdict on it. Correctness is NOT required: the question is "can this cell be measured?",
    never "is the model right?".
    """
    rec: dict[str, Any] = {
        "model": model, "suite": suite, "item_id": item.get("id", "?"),
        "max_tokens": item.get("max_tokens"), "ctx_tokens": item.get("ctx_tokens"),
        "latency_s": None, "content_chars": 0, "status": None, "detail": "",
    }
    attempts = int(cfg["probe"].get("warmup_retries", 1)) + 1
    min_chars = int(cfg["probe"]["min_content_chars"])
    content = ""
    status: str | None = None
    detail = ""
    for attempt in range(attempts):
        t0 = time.time()
        try:
            content = call(model, item["system"], item["user"], int(item.get("max_tokens", 512))) or ""
        except Exception as exc:
            detail = type(exc).__name__ + ": " + str(exc)[:180]
            rec["latency_s"] = round(time.time() - t0, 2)
            status = _classify_error(rec, cfg, detail)
            if status in ("CTX_CEILING", "TIMEOUT", "HTTP_ERROR"):
                break  # a transport or context-ceiling failure will not fix itself on retry
            continue
        rec["latency_s"] = round(time.time() - t0, 2)
        rec["content_chars"] = len(content)
        if len(content) >= min_chars:
            if attempt > 0:
                rec["warmup_retry"] = True
            status = None
            break
        status = "NO_CONTENT"
        detail = "empty content (cold reload, or a reasoning model with too small a budget?)"

    if status is not None:
        rec["status"] = status
        rec["detail"] = detail
        return rec

    gradable, gdetail = _gradable(item, content)
    if not gradable:
        rec["status"] = "GRADER_ERROR"
        rec["detail"] = gdetail
        return rec
    if suite in set(cfg["probe"]["json_suites"]):
        try:
            json.loads(content[content.find("{"): content.rfind("}") + 1])
        except Exception:
            rec["status"] = "NO_JSON"
            rec["detail"] = "unparseable JSON at max_tokens=" + str(rec["max_tokens"]) + " (suite requires JSON)"
            return rec
    rec["status"] = VALID
    rec["detail"] = "gradable: " + gdetail
    return rec


def write_artifact(cfg: dict[str, Any], payload: dict[str, Any]) -> Path:
    """Persist the gate artifact (atomic-ish) plus a stable 'latest' pointer for the audit."""
    outdir = REPO / cfg["artifacts"]["dir"]
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = outdir / ("bench_preflight_" + stamp + ".json")
    text = json.dumps(payload, indent=2, sort_keys=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    latest = outdir / cfg["artifacts"]["latest_name"]
    latest.write_text(text, encoding="utf-8")
    return path


def _is_json(text: Any) -> bool:
    """True when the brace-delimited part of text parses as JSON."""
    body = str(text or "").strip()
    head, tail = body.find("{"), body.rfind("}")
    if head < 0 or tail <= head:
        return False
    try:
        json.loads(body[head:tail + 1])
        return True
    except Exception:
        return False


def selftest(cfg: dict[str, Any]) -> int:
    """Stress-test the gate's OWN assumptions against the stored checkpoint.

    This is the step whose absence caused circular debugging: the gate was validated against an
    assumption ("suites return JSON") instead of against the artifacts. For every suite where
    the gate enforces JSON, the share of historically GRADED-OK rows that ARE valid JSON must
    clear probe.selftest_min_json_agreement. If it does not, the GATE is wrong, not the models.

    Returns:
        0 when every enforced suite agrees with history, 1 when a rule contradicts it.
    """
    ckpt = REPO / str((cfg.get("stale_row_guards") or {}).get("checkpoint", "governance/model_eval_checkpoint.jsonl"))
    if not ckpt.exists():
        print("selftest: checkpoint missing: " + str(ckpt))
        return 2
    per_suite: dict[str, list[int]] = {}
    for line in ckpt.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("err") or row.get("na") or not row.get("ok"):
            continue
        slot = per_suite.setdefault(str(row.get("suite")), [0, 0])
        slot[0] += 1
        if _is_json(row.get("pred")):
            slot[1] += 1
    enforced = set(cfg["probe"]["json_suites"])
    floor = float(cfg["probe"]["selftest_min_json_agreement"])
    print("=" * 88)
    print("GATE SELFTEST — does the JSON rule agree with the artifacts?")
    print("=" * 88)
    bad: list[str] = []
    for suite, (n, j) in sorted(per_suite.items(), key=lambda kv: -kv[1][0]):
        rate = j / n if n else 0.0
        tag = "ENFORCED" if suite in enforced else "-"
        flag = ""
        if suite in enforced and rate < floor:
            flag = "   <-- CONTRADICTS HISTORY: the gate is wrong, not the model"
            bad.append(suite)
        pct = str(round(rate * 100, 1)).rjust(6) + chr(37)
        print("  " + suite.ljust(16) + str(n).rjust(5) + " graded-ok  json=" + pct + "  " + tag + flag)
    print("-" * 88)
    if bad:
        print("  FAIL: JSON enforced on " + ", ".join(bad) + " but history disagrees")
        return 1
    print("  PASS: every JSON-enforced suite agrees with history at >=" + str(floor))
    return 0


def main() -> int:
    """Run the gate. Returns the configured exit code."""
    ap = argparse.ArgumentParser(description="Pre-flight gate for benchmark suites")
    ap.add_argument("--models", nargs="*", default=[], help="comma or space separated")
    ap.add_argument("--suites", nargs="*", default=[], help="comma or space separated")
    ap.add_argument("--static", action="store_true", help="environment checks only (safe while a run is live)")
    ap.add_argument("--selftest", action="store_true",
                    help="stress-test the gate's own rules against the stored checkpoint (no model calls)")
    args = ap.parse_args()

    cfg = load_config()
    codes = cfg["exit_codes"]
    if getattr(args, "selftest", False):
        return selftest(cfg)
    suites_map, call = load_harness()

    # accept both "--suites a,b" and "--suites a b" (a usage error must not masquerade as a gate run)
    models = [m.strip() for chunk in args.models for m in chunk.split(",") if m.strip()] or list(cfg["environment"]["expected_models"])
    suites = [s.strip() for chunk in args.suites for s in chunk.split(",") if s.strip()] or sorted(suites_map)

    items = {s: first_item(s, suites_map, cfg) for s in suites}
    budgets = {s: int((items[s] or {}).get("max_tokens", cfg["probe"]["default_max_tokens"])) for s in suites}
    fp = fingerprint(cfg, models, suites, budgets)

    print("=" * 78)
    print("BENCH PREFLIGHT   fingerprint=" + fp + "   " + datetime.now().isoformat(timespec="seconds"))
    print("  models: " + str(len(models)) + "   suites: " + ", ".join(suites))
    print("=" * 78)

    findings, unsafe = check_environment(cfg, models, full=not args.static)
    for f in findings:
        print(("  [OK]   " if f["ok"] else "  [FAIL] ") + f["check"].ljust(24) + str(f["detail"]))

    cells: list[dict[str, Any]] = []
    if args.static:
        print("\n  --static: LIVE MODEL PROBES SKIPPED (reason: " +
              ("a benchmark is running" if concurrent_benchmarks(cfg) else "requested") + ")")
    elif unsafe:
        print("\n  ENVIRONMENT UNSAFE -> refusing to spend model time. Fix the FAIL rows above.")
    else:
        print("\n  probing " + str(len(models) * len(suites)) + " cells (real call path, real budgets)...")
        for model in models:
            for suite in suites:
                item = items[suite]
                if item is None:
                    cells.append({"model": model, "suite": suite, "status": "SUITE_BUILD_FAILED",
                                  "detail": "suite builder raised", "max_tokens": budgets[suite]})
                    print("  " + model[:34].ljust(34) + suite.ljust(14) + "SUITE_BUILD_FAILED")
                    continue
                rec = probe_cell(cfg, model, suite, item, call)
                cells.append(rec)
                mark = "OK " if rec["status"] == VALID else "NA "
                print("  " + mark + model[:32].ljust(32) + suite.ljust(14) +
                      "mt=" + str(rec["max_tokens"]).ljust(5) +
                      "t=" + str(rec["latency_s"]).ljust(7) +
                      "chars=" + str(rec["content_chars"]).ljust(6) + rec["status"] +
                      ("  " + rec["detail"][:70] if rec["status"] != VALID else ""))

    invalid = [c for c in cells if c.get("status") != VALID]
    payload: dict[str, Any] = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "fingerprint": fp, "models": models, "suites": suites, "budgets": budgets,
        "static_only": bool(args.static), "environment": findings, "env_unsafe": unsafe,
        "cells": cells, "n_cells": len(cells), "n_invalid": len(invalid),
        "invalid_cells": [[c["model"], c["suite"], c["status"]] for c in invalid],
    }
    path = write_artifact(cfg, payload)
    print("\n  artifact: " + str(path.relative_to(REPO)))
    if invalid:
        print("  " + str(len(invalid)) + " cell(s) NOT VALID -> those cells are NA in scoring, never 0.")
    if args.static:
        return codes["ok"]
    if unsafe:
        return codes["env_unsafe"]
    if invalid:
        return codes["cell_invalid"]
    print("  ALL CELLS VALID -> clear to run.")
    return codes["ok"]


if __name__ == "__main__":
    sys.exit(main())
