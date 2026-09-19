#!/usr/bin/env python3
"""Drift monitor (mechanism M3-enforcement).

WHY: criteria written in prose drift, and a claim of "done" that is not re-derivable is how a
stalled run got reported as a result. This script evaluates every check in
governance/p0_p1_criteria.yaml against the FILESYSTEM and prints OK / DRIFT / WARN.

If this prints DRIFT for a criterion, any claim that the corresponding task is complete is void,
regardless of how the work reads in a summary.

    python3 scripts/drift_monitor.py            # full
    python3 scripts/drift_monitor.py --quiet     # only DRIFT/WARN lines
Exit: 0 = no DRIFT (warnings allowed), 1 = >=1 DRIFT, 2 = criteria/monitor unusable.
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parents[1]
CRITERIA: Path = REPO / "governance" / "p0_p1_criteria.yaml"
for _p in (str(REPO), str(REPO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OK: str = "OK"
DRIFT: str = "DRIFT"
WARN: str = "WARN"


def _read(path: Path) -> str:
    """Read a text file, returning '' when unreadable (a missing file is DRIFT, not a crash)."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _dotted(cfg: Any, dotted: str) -> Any:
    """Walk a dotted path through nested dicts."""
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _newest(pattern: str) -> Path | None:
    """Newest file matching a repo-relative glob, or None."""
    hits = sorted(globmod.glob(str(REPO / pattern)))
    hits = [h for h in hits if not h.endswith(".tmp")]
    return Path(hits[-1]) if hits else None


# ── check implementations ────────────────────────────────────────────────
def check_source_contains(a: dict[str, Any]) -> tuple[str, str]:
    """A file must contain a needle."""
    text = _read(REPO / a["file"])
    if not text:
        return DRIFT, "file missing/unreadable: " + a["file"]
    return (OK, "present") if a["needle"] in text else (DRIFT, "needle absent: " + a["needle"])


def check_source_not_contains(a: dict[str, Any]) -> tuple[str, str]:
    """A file must NOT contain a needle (guards against the defect coming back)."""
    text = _read(REPO / a["file"])
    if not text:
        return DRIFT, "file missing/unreadable: " + a["file"]
    return (DRIFT, "forbidden needle present: " + a["needle"]) if a["needle"] in text else (OK, "absent")


def check_config_gte(a: dict[str, Any]) -> tuple[str, str]:
    """A YAML config value must be >= min."""
    import yaml

    try:
        cfg = yaml.safe_load(_read(REPO / a["file"]))
    except Exception as exc:
        return DRIFT, "config unparseable: " + type(exc).__name__
    val = _dotted(cfg, a["dotted"])
    if val is None:
        return DRIFT, a["dotted"] + " absent"
    try:
        return (OK, str(val)) if float(val) >= float(a["min"]) else (DRIFT, str(val) + " < " + str(a["min"]))
    except (TypeError, ValueError):
        return DRIFT, "not numeric: " + repr(val)


def check_artifact_glob(a: dict[str, Any]) -> tuple[str, str]:
    """At least one file must match a glob."""
    hits = [h for h in globmod.glob(str(REPO / a["glob"])) if not h.endswith(".tmp")]
    return (OK, str(len(hits)) + " file(s)") if hits else (DRIFT, "no match: " + a["glob"])


def check_jsonl_rows_gte(a: dict[str, Any]) -> tuple[str, str]:
    """A JSONL file must hold >= min rows matching an optional field filter."""
    path = REPO / a["file"]
    if not path.exists():
        return DRIFT, "missing: " + a["file"]
    want = a.get("where") or {}
    n = 0
    for line in _read(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if all(str(row.get(k)) == str(v) for k, v in want.items()):
            n += 1
    return (OK, str(n) + " rows") if n >= int(a["min"]) else (DRIFT, str(n) + " rows < " + str(a["min"]))


def _newest_json(pattern: str) -> tuple[dict[str, Any] | None, str]:
    """Load the newest JSON artifact matching a glob."""
    path = _newest(pattern)
    if path is None:
        return None, "no match: " + pattern
    try:
        return json.loads(_read(path)), str(path.relative_to(REPO))
    except Exception as exc:
        return None, "unparseable " + str(path.name) + ": " + type(exc).__name__


def _num(a: dict[str, Any], key: str) -> float | None:
    """Resolve a numeric field, allowing 'other' to name a sibling key."""
    val = a.get(key)
    if isinstance(val, str) and "other" in a:
        obj, _ = _newest_json(a["glob"])
        val = (obj or {}).get(a["other"])
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def check_newest_json_gte(a: dict[str, Any]) -> tuple[str, str]:
    """A field in the newest JSON artifact must be >= min."""
    obj, where = _newest_json(a["glob"])
    if obj is None:
        return DRIFT, where
    val = obj.get(a["path"])
    if val is None:
        return DRIFT, a["path"] + " absent in " + where
    return (OK, str(val) + " in " + Path(where).name) if float(val) >= float(a["min"]) else (DRIFT, str(val) + " < " + str(a["min"]))


def check_newest_json_lt(a: dict[str, Any]) -> tuple[str, str]:
    """A field in the newest JSON artifact must be < another field (all-failed detection)."""
    obj, where = _newest_json(a["glob"])
    if obj is None:
        return DRIFT, where
    left, right = obj.get(a["path"]), obj.get(a["other"])
    if left is None or right is None:
        return DRIFT, a["path"] + "/" + a["other"] + " absent"
    if float(right) == 0:
        return DRIFT, a["other"] + "=0 -> the judge layer never ran"
    return (OK, str(left) + " < " + str(right)) if float(left) < float(right) else (DRIFT, str(left) + " >= " + str(right) + " -> every call failed")


def check_preflight_fingerprint_match(a: dict[str, Any]) -> tuple[str, str]:
    """The newest preflight artifact must carry the CURRENT harness fingerprint.

    A result scored under a stale gate is not comparable (M1/M3 invariant #5).
    """
    obj, where = _newest_json("governance/bench_preflight_latest.json")
    if obj is None:
        return DRIFT, where
    if obj.get("static_only"):
        return WARN, "newest gate artifact is --static (no live cells probed)"
    try:
        import bench_preflight as bp

        cfg = bp.load_config()
        models = obj.get("models") or []
        suites = obj.get("suites") or []
        fp = bp.fingerprint(cfg, models, suites, {k: int(v) for k, v in (obj.get("budgets") or {}).items()})
    except Exception as exc:
        return DRIFT, "cannot recompute fingerprint: " + type(exc).__name__
    if fp != obj.get("fingerprint"):
        return DRIFT, "stale gate: artifact " + str(obj.get("fingerprint")) + " vs current " + fp
    bad = [c for c in (obj.get("cells") or []) if c.get("status") != "VALID"]
    if bad:
        # A non-VALID cell is the DESIGNED outcome of the gate: the cell becomes NA and is
        # excluded from accuracy (never scored 0). Counting it as DRIFT pressures the
        # operator to weaken the gate to get a green board — the exact inversion of the
        # M1/M3 invariant "NA is never 0". Only a stale fingerprint is drift; a designed
        # NA is a loud WARN that names the cell.
        names = ", ".join(sorted(
            str(c.get("model")) + "/" + str(c.get("suite")) + "=" + str(c.get("status"))
            for c in bad
        ))
        return WARN, str(len(bad)) + " cell(s) NA by design (excluded, never scored 0): " + names
    return OK, "fingerprint " + fp + " matches"


def check_command_exit_zero(a: dict[str, Any]) -> tuple[str, str]:
    """A command must exit 0."""
    try:
        proc = subprocess.run(a["cmd"], shell=True, cwd=str(REPO), capture_output=True, text=True, timeout=180)
    except Exception as exc:
        return DRIFT, "command failed to run: " + type(exc).__name__
    if proc.returncode == 0:
        return OK, "exit 0"
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return DRIFT, "exit " + str(proc.returncode) + (" | " + tail[-1][:110] if tail else "")


CHECKS: dict[str, Any] = {
    "source_contains": check_source_contains,
    "source_not_contains": check_source_not_contains,
    "config_gte": check_config_gte,
    "artifact_glob": check_artifact_glob,
    "jsonl_rows_gte": check_jsonl_rows_gte,
    "newest_json_gte": check_newest_json_gte,
    "newest_json_lt": check_newest_json_lt,
    "preflight_fingerprint_match": check_preflight_fingerprint_match,
    "command_exit_zero": check_command_exit_zero,
}


def main() -> int:
    """Evaluate every criterion and report drift. Returns the exit code."""
    ap = argparse.ArgumentParser(description="Re-derive governance/p0_p1_criteria.yaml from the filesystem")
    ap.add_argument("--quiet", action="store_true", help="print only DRIFT/WARN rows")
    ap.add_argument("--criteria", default=str(CRITERIA))
    args = ap.parse_args()

    import yaml

    path = Path(args.criteria)
    if not path.exists():
        print("criteria file missing: " + str(path))
        return 2
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows: list[dict[str, Any]] = []
    print("=" * 96)
    print("DRIFT MONITOR   criteria=" + path.name + "   " + time.strftime("%Y-%m-%dT%H:%M:%S"))
    print("=" * 96)
    for crit in spec.get("checks", []):
        fn = CHECKS.get(str(crit.get("check")))
        if fn is None:
            status, detail = DRIFT, "unknown check type: " + str(crit.get("check"))
        else:
            try:
                status, detail = fn(crit.get("args") or {})
            except Exception as exc:
                status, detail = DRIFT, "check raised " + type(exc).__name__ + ": " + str(exc)[:80]
        sev = str(crit.get("severity", "fail"))
        if status == DRIFT and sev == "warn":
            status = WARN
        rows.append({"id": crit.get("id"), "severity": sev, "status": status, "detail": detail,
                     "desc": crit.get("desc")})
        if args.quiet and status == OK:
            continue
        mark = {OK: "  [OK]   ", DRIFT: "  [DRIFT]", WARN: "  [WARN] "}[status]
        print(mark + " " + str(crit.get("id", "?")).ljust(34) + str(detail)[:110])
    n_drift = sum(1 for r in rows if r["status"] == DRIFT)
    n_warn = sum(1 for r in rows if r["status"] == WARN)
    print("-" * 96)
    print("  " + str(len(rows)) + " criteria | OK " + str(len(rows) - n_drift - n_warn)
          + " | DRIFT " + str(n_drift) + " | WARN " + str(n_warn))
    out = REPO / "governance" / ("drift_report_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "criteria": str(path),
                               "n_drift": n_drift, "n_warn": n_warn, "rows": rows}, indent=2), encoding="utf-8")
    os.replace(tmp, out)
    print("  artifact: " + str(out.relative_to(REPO)))
    return 1 if n_drift else 0


if __name__ == "__main__":
    sys.exit(main())
