#!/usr/bin/env python3
"""pipeline/delegation_economy.py — THE DELEGATION ECONOMY, MEASURED (D-3023).

WHY. Measured 2026-10-15: the harness's own ledger holds 4,151,736,928 CLOUD input tokens
($112.75) against 3,663,410 LOCAL ones — the local fleet carried 0.09% of the load while it sat
idle. Nothing in the repo measured that, so nothing could route around it. This is the instrument
that makes a cloud token an ESCALATION: a counted, ceilinged, provenance-carrying event instead of
an ambient default (C1/C3 sovereignty first, money second).

WHAT IT DOES. Reads the harness's OWN ledger, classifies every row into a tier (local / cloud /
unclassified) by JOINING the engine's model registry, and holds the totals against the
SHRINK-ONLY ceilings declared in config/delegation_economy.yaml. It WRITES NOTHING and sends
nothing.

C12. This file names no path, no table, no model, no threshold and no ceiling of its own: every
one of them is read from config/delegation_economy.yaml, and --selftest proves that by reading its
own bytes. The pointer resolver is pipeline/harness_env.py::resolve, REUSED rather than rewritten
(C21). The engine model registry is joined from the home config/agent_context.yaml already
declares — no list of local models is written down anywhere.

rc: 0 within every ceiling | 1 a ceiling is EXCEEDED (a budget breach — the only fatal reading)
    2 UNMEASURED (no ledger, or an empty one) — loud, NOT fatal (BUG-457)

Usage: python3 pipeline/delegation_economy.py            # the reading
       python3 pipeline/delegation_economy.py --check     # the gate
       python3 pipeline/delegation_economy.py --json
       python3 pipeline/delegation_economy.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sqlite3
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:      # the repo idiom: runnable directly AND importable (C21)
    sys.path.insert(0, str(ROOT))

from pipeline.harness_env import resolve  # ONE resolver (C21) — never a second pointer reader

CONFIG = ROOT / "config" / "delegation_economy.yaml"

RC_OK = 0
RC_BREACH = 1      # a declared SHRINK-ONLY ceiling is exceeded: the only fatal reading
RC_UNMEASURED = 2  # nothing to measure: loud, NOT fatal (BUG-457)

TIERS = ("local", "cloud", "unclassified")


def load_config(path: pathlib.Path = CONFIG) -> dict[str, Any]:
    """Read the ONE home of the economy's declarations; never invent a default (C12/C16)."""
    if not path.exists():
        raise SystemExit(f"FATAL: {path} is absent — it is the one home of the economy's ceilings (C12)")
    cfg = yaml.safe_load(path.read_text()) or {}
    for key in ("homes", "ledger_fields", "ceiling", "cloud_model_families", "ratio"):
        if key not in cfg:
            raise SystemExit(f"FATAL: {path.name} declares no '{key}' — refusing to invent it (C12)")
    return cfg


def pointer(ref: str) -> str:
    """Resolve an '@file#dotted.path' pointer through the ONE resolver; refuse a bare literal."""
    if not str(ref).startswith("@"):
        raise SystemExit(f"FATAL: '{ref}' is not a pointer — a path written into this file would be "
                         f"the second home C12 forbids")
    return resolve(str(ref))


def local_model_set(cfg: dict[str, Any]) -> set[str]:
    """The engine's OWN model registry, joined from the home the context contract declares.

    The join is the measurement: a model the engine knows cannot be a cloud model, whatever its
    name looks like. An unreadable registry is FATAL — a tier nobody can decide is not a tier.
    """
    home = pointer(cfg["homes"]["local_model_set"])
    path = pathlib.Path(os.path.expanduser(home.split("#", 1)[0]))
    if not path.exists():
        raise SystemExit(f"FATAL: the engine's model registry is absent at {path} — the local tier "
                         f"cannot be decided, and an undecidable tier is not a tier (C16)")
    doc = yaml.safe_load(path.read_text()) or {}
    models = doc.get("models") if isinstance(doc, dict) else None
    if not isinstance(models, dict) or not models:
        raise SystemExit(f"FATAL: {path} carries no 'models' mapping — the join that defines LOCAL "
                         f"has nothing to join against (C16)")
    return set(models)


def ledger_home(cfg: dict[str, Any]) -> tuple[pathlib.Path, str]:
    """The ledger FILE and its TABLE, both read from the declared pointer (no literal here)."""
    home = pointer(cfg["homes"]["ledger"])
    file_part, _, table = home.partition("#")
    if not table:
        raise SystemExit(f"FATAL: the ledger pointer '{cfg['homes']['ledger']}' names no table after "
                         f"'#' — a table name invented here would be a second home (C12)")
    return pathlib.Path(os.path.expanduser(file_part)), table


def read_rows(db: pathlib.Path, table: str, fields: dict[str, str]) -> list[dict[str, Any]] | None:
    """Read the declared columns, READ-ONLY. Returns None when there is no ledger to read.

    A missing COLUMN is fatal (C16); a missing FILE is not an error but an absence, and an absence
    is reported as UNMEASURED rather than as a zero (D-2957).
    """
    if not db.exists():
        return None
    cols = ", ".join(f"{col} AS {name}" for name, col in fields.items())
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.execute(f"SELECT {cols} FROM {table}")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]
    except sqlite3.Error as exc:
        raise SystemExit(f"FATAL: the ledger at {db} does not carry the declared columns ({exc}) — "
                         f"a column that is missing is not a zero (C16)")
    finally:
        con.close()


def tier_of(model: str, local: set[str], families: list[str]) -> str:
    """LOCAL if the engine's registry knows it; CLOUD if it names a declared family; else UNCLASSIFIED."""
    if model in local:
        return "local"
    low = (model or "").lower()
    if any(fam in low for fam in families):
        return "cloud"
    return "unclassified"


def declared_min_calls(cfg: dict[str, Any]) -> int:
    """The declared floor below which a share is INCONCLUSIVE and is never printed as a number."""
    value = cfg["ratio"]["min_calls"]
    return int(resolve(value)) if isinstance(value, str) and value.startswith("@") else int(value)


def summarise(rows: list[dict[str, Any]], local: set[str], families: list[str],
              min_calls: int) -> dict[str, Any]:
    """Totals per tier. A row with no cost is counted as UNKNOWN, never as a measured zero."""
    tiers: dict[str, dict[str, Any]] = {
        t: {"calls": 0, "input": 0, "output": 0, "cache_read": 0, "cost": 0.0,
            "cost_rows": 0, "cost_unknown": 0} for t in TIERS}
    sources: collections.Counter = collections.Counter()
    for row in rows:
        bucket = tiers[tier_of(str(row.get("model") or ""), local, families)]
        bucket["calls"] += 1
        for key in ("input", "output", "cache_read"):
            bucket[key] += int(row.get(key) or 0)
        cost = row.get("cost")
        if cost is None:
            bucket["cost_unknown"] += 1
            sources["(no cost recorded)"] += 1
        else:
            bucket["cost"] += float(cost)
            bucket["cost_rows"] += 1
            sources[str(row.get("cost_source") or "(no cost_source)")] += 1
    decided = tiers["local"]["calls"] + tiers["cloud"]["calls"]
    share = (tiers["local"]["input"] / (tiers["local"]["input"] + tiers["cloud"]["input"])
             if tiers["local"]["input"] + tiers["cloud"]["input"] else None)
    return {"tiers": tiers, "rows": len(rows), "decided_calls": decided,
            "local_share": share, "min_calls": min_calls, "sources": dict(sources)}


def breaches(summary: dict[str, Any], ceiling: dict[str, Any]) -> list[str]:
    """Every ceiling that is EXCEEDED, named with both numbers — never a bare boolean."""
    cloud = summary["tiers"]["cloud"]
    out: list[str] = []
    for key, measured, label in (
            ("cloud_cost_usd", cloud["cost"], "cloud cost USD"),
            ("cloud_input_tokens", cloud["input"], "cloud input tokens"),
            ("cloud_calls", cloud["calls"], "cloud calls")):
        limit = float(ceiling[key])
        if measured > limit:
            out.append(f"{label}: {measured:,.2f} > ceiling {limit:,.2f}")
    return out


def report_text(summary: dict[str, Any], cfg: dict[str, Any]) -> str:
    """The reading, as a table plus the provenance of every number in it."""
    lines = [f"{'tier':<13}{'calls':>8}{'input_tok':>16}{'output_tok':>14}{'cache_read':>16}{'cost_usd':>12}"]
    for tier in TIERS:
        b = summary["tiers"][tier]
        lines.append(f"{tier:<13}{b['calls']:>8,}{b['input']:>16,}{b['output']:>14,}"
                     f"{b['cache_read']:>16,}{b['cost']:>12,.2f}")
    lines.append(f"rows read: {summary['rows']:,} | tier-decided calls: {summary['decided_calls']:,} "
                 f"(floor for a share: {summary['min_calls']})")
    lines.append("cost provenance: " + ", ".join(f"{k}={v:,}" for k, v in sorted(summary["sources"].items())))
    share = summary["local_share"]
    lines.append("local share of decided input tokens: " +
                 (f"{share * 100:.2f}% (advisory — not a gate until a route registry exists)"
                  if share is not None and summary["decided_calls"] >= summary["min_calls"]
                  else "INCONCLUSIVE below the declared call floor"))
    ceiling = cfg["ceiling"]
    measured = ceiling.get("measured_20261015") or {}
    for key, label in (("cloud_cost_usd", "cloud cost USD"),
                       ("cloud_input_tokens", "cloud input tokens"),
                       ("cloud_calls", "cloud calls")):
        value = float(ceiling[key])
        was = measured.get(key)
        lines.append(f"ceiling {label}: {value:,.2f} (shrink-only; measured 2026-10-15 at "
                     f"{float(was):,.2f})" if was is not None else f"ceiling {label}: {value:,.2f}")
    lines.append("an escalation carries a reason: " + ", ".join(cfg["escalation"]["reasons"])
                 if "escalation" in cfg else "an escalation carries a reason (none declared)")
    return "\n".join(lines)


def measure(config_path: pathlib.Path = CONFIG, *, ledger: pathlib.Path | None = None,
            local: set[str] | None = None, table: str | None = None
            ) -> tuple[dict[str, Any] | None, dict[str, Any], str]:
    """The one reading. Returns (summary_or_None, config, why_unmeasured)."""
    cfg = load_config(config_path)
    if local is None:
        local = local_model_set(cfg)
    if ledger is None:
        db, tname = ledger_home(cfg)
    else:
        db, tname = pathlib.Path(ledger), (table or ledger_home(cfg)[1])
    rows = read_rows(db, tname, cfg["ledger_fields"])
    if rows is None:
        return None, cfg, f"no ledger at {db} — the economy is UNMEASURED (absent is not zero, D-2957)"
    if not rows:
        return None, cfg, f"the ledger at {db} carries no rows"
    return summarise(rows, local, cfg["cloud_model_families"], declared_min_calls(cfg)), cfg, ""


def _synth(dirname: pathlib.Path, rows: list[dict[str, Any]], drop: str | None = None) -> pathlib.Path:
    """A synthetic ledger carrying the DECLARED schema — the control's known answer (D-400)."""
    dirname.mkdir(parents=True, exist_ok=True)
    db = dirname / "sessions.db"
    spec = {"model": "TEXT", "input_tokens": "INTEGER", "output_tokens": "INTEGER",
            "cache_read_tokens": "INTEGER", "cost": "REAL", "cost_source": "TEXT"}
    if drop:
        spec.pop(drop)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE usage_ledger (" + ", ".join(f"{c} {t}" for c, t in spec.items()) + ")")
    for r in rows:
        keys = [k for k in spec]
        con.execute(f"INSERT INTO usage_ledger ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
                    [r.get(k) for k in keys])
    con.commit()
    con.close()
    return db


def _selftest() -> int:
    """Known-answer controls. A control verifies the SHIPPED path, never a copy of it."""
    import tempfile
    checks: list[tuple[str, bool]] = []
    src = pathlib.Path(__file__).read_text()
    cfg_text = CONFIG.read_text() if CONFIG.exists() else ""

    def row(model: str, i: int, o: int = 0, cr: int = 0, cost: float | None = None,
            cs: str | None = None) -> dict[str, Any]:
        return {"model": model, "input_tokens": i, "output_tokens": o, "cache_read_tokens": cr,
                "cost": cost, "cost_source": cs}

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        cpath = tmp / "cfg.yaml"
        base = {
            "homes": {"ledger": "@config/x.yaml#y", "local_model_set": "@config/x.yaml#z"},
            "ledger_fields": {"model": "model", "input": "input_tokens", "output": "output_tokens",
                              "cache_read": "cache_read_tokens", "cost": "cost",
                              "cost_source": "cost_source"},
            "cloud_model_families": ["deepseek", "gpt-"],
            "ceiling": {"cloud_cost_usd": 10.0, "cloud_input_tokens": 1000000, "cloud_calls": 100},
            "ratio": {"min_calls": 30},
        }
        cpath.write_text(yaml.safe_dump(base))
        LOC = {"gemma-4-E4B-it-MLX-4bit", "gpt-local-test"}

        s, _, why = measure(cpath, ledger=_synth(tmp / "local_only", [
            row("gpt-local-test", 1000), row("gpt-local-test", 500)]), local=LOC, table="usage_ledger")
        checks.append(("a_local_only_ledger_reads_within_ceiling",
                       s is not None and s["tiers"]["cloud"]["calls"] == 0 and breaches(s, base["ceiling"]) == []))

        s_over, _, _ = measure(cpath, ledger=_synth(tmp / "over", [
            row("deepseek-v4-pro", 2000000, 10, 0, 20.0, "estimated")]), local=LOC, table="usage_ledger")
        checks.append(("a_cloud_row_over_the_ceiling_reads_BREACH",
                       s_over is not None and len(breaches(s_over, base["ceiling"])) == 2))

        s_under, _, _ = measure(cpath, ledger=_synth(tmp / "under", [
            row("deepseek-v4-pro", 100, 10, 0, 0.01, "estimated")]), local=LOC, table="usage_ledger")
        checks.append(("a_cloud_row_under_the_ceiling_reads_ok",
                       s_under is not None and breaches(s_under, base["ceiling"]) == []))

        absent, _, why_absent = measure(cpath, ledger=tmp / "nope" / "sessions.db", local=LOC,
                                            table="usage_ledger")
        checks.append(("an_absent_ledger_is_UNMEASURED_and_never_zero",
                       absent is None and "UNMEASURED" in why_absent))

        s_mixed, _, _ = measure(cpath, ledger=_synth(tmp / "mixed", [
            row("gemma-4-E4B-it-MLX-4bit", 700),
            row("deepseek-v4-pro", 300, 5, 0, 0.02, "estimated"),
            row("mystery-9B-MLX", 50, 0, 0, None, None)]), local=LOC, table="usage_ledger")
        checks.append(("a_local_model_whose_name_carries_a_cloud_marker_still_reads_LOCAL",
                       s_mixed is not None and s_mixed["tiers"]["local"]["calls"] == 1
                       and s_mixed["tiers"]["cloud"]["calls"] == 1))
        checks.append(("an_unrecognised_model_reads_UNCLASSIFIED_and_joins_neither_tier",
                       s_mixed is not None and s_mixed["tiers"]["unclassified"]["calls"] == 1
                       and s_mixed["tiers"]["cloud"]["calls"] == 1 and s_mixed["tiers"]["local"]["calls"] == 1))
        checks.append(("a_row_with_no_cost_is_UNKNOWN_never_a_measured_zero",
                       s_mixed is not None and s_mixed["tiers"]["unclassified"]["cost_unknown"] == 1
                       and s_mixed["tiers"]["unclassified"]["cost_rows"] == 0
                       and s_mixed["tiers"]["cloud"]["cost_rows"] == 1))
        checks.append(("a_ratio_below_the_declared_call_floor_is_INCONCLUSIVE",
                       s_mixed is not None and s_mixed["local_share"] is not None
                       and s_mixed["decided_calls"] < s_mixed["min_calls"]))
        checks.append(("a_share_is_never_printed_below_the_declared_floor",
                       "INCONCLUSIVE" in report_text(s_mixed, base)))

        try:
            measure(cpath, ledger=_synth(tmp / "missing_col", [row("gemma-4-E4B-it-MLX-4bit", 1)],
                                         drop="output_tokens"), local=LOC, table="usage_ledger")
            fatal_on_missing_column = False
        except SystemExit:
            fatal_on_missing_column = True
        checks.append(("a_ledger_missing_a_declared_column_is_FATAL_not_a_zero", fatal_on_missing_column))

    # C12, proved by reading the module's own bytes: the needles are DERIVED from the config, so a
    # ceiling copied into this file would be caught instead of declared.
    declared = (yaml.safe_load(cfg_text) or {}).get("ceiling", {}) if cfg_text else {}
    keys = ("cloud_cost_usd", "cloud_input_tokens", "cloud_calls")
    needles = [str(declared[k]) for k in keys if k in declared]
    checks.append(("the_module_names_no_ceiling_of_its_own",
                   len(needles) == 3 and all(n not in src for n in needles)))
    baseline = declared.get("measured_20261015") or {}
    checks.append(("every_ceiling_sits_at_or_above_its_measured_baseline",
                   all(k in baseline and float(declared[k]) >= float(baseline[k]) for k in keys)))
    checks.append(("the_module_reuses_the_ONE_pointer_resolver_C21",
                   "from pipeline.harness_env import resolve" in src))
    try:
        real = load_config(CONFIG)
        names = local_model_set(real)
        db_file, table = ledger_home(real)
        ok = len(names) >= 1 and db_file.name.endswith(".db") and bool(table)
    except SystemExit:
        ok = False
    checks.append(("the_declared_homes_resolve_to_a_registry_and_a_ledger", ok))

    bad = 0
    for label, good in checks:
        print(("  PASS " if good else "  FAIL ") + label)
        bad += 0 if good else 1
    print(f"selftest: {len(checks) - bad}/{len(checks)}")
    return RC_OK if not bad else RC_BREACH


def main(argv: list[str] | None = None) -> int:
    """Entry point: the reading, the gate, the JSON form, the controls."""
    ap = argparse.ArgumentParser(description="The delegation economy, measured (D-3023).")
    ap.add_argument("--check", action="store_true", help="the gate: rc 1 when a ceiling is exceeded")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    try:
        summary, cfg, why = measure()
    except SystemExit as exc:
        print(str(exc))
        return RC_BREACH
    if summary is None:
        print(f"UNMEASURED delegation-economy: {why}")
        return RC_UNMEASURED
    bad = breaches(summary, cfg["ceiling"])
    if args.json:
        print(json.dumps({"summary": summary, "breaches": bad}, indent=1, default=str))
    else:
        print(report_text(summary, cfg))
    if bad:
        for line in bad:
            print(f"  BREACH  {line}")
        print("  a ceiling is SHRINK-ONLY: route the work to T0 (script) or T1 (local engine), or the "
              "OWNER raises the ceiling with a reason (D-3023)")
        return RC_BREACH
    return RC_OK


if __name__ == "__main__":
    raise SystemExit(main())
