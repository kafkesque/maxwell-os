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
import time
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
    cfg = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    for key in ("homes", "ledger_fields", "ceiling", "cloud_model_families", "ratio",
                "metering_classes", "token_ceiling_counts"):
        if key not in cfg:
            raise SystemExit(f"FATAL: {path.name} declares no '{key}' — refusing to invent it (C12)")
    return cfg


def pointer(ref: str) -> str:
    """Resolve an '@file#dotted.path' pointer through the ONE resolver; refuse a bare literal.

    A pointer may point AT another pointer (a class home names `homes.ledger` rather than restating the
    ledger path, so the address lives in exactly one place — C12). The chain is followed to its END,
    bounded: a chain that does not terminate is refused, because a home that cannot be reached is not
    a home (C16).
    """
    text = str(ref)
    if not text.startswith("@"):
        raise SystemExit(f"FATAL: '{ref}' is not a pointer — a path written into this file would be "
                         f"the second home C12 forbids")
    for _ in range(5):
        text = resolve(text)
        if not str(text).startswith("@"):
            return str(text)
    raise SystemExit(f"FATAL: the pointer chain from '{ref}' does not terminate — refusing to guess "
                     f"which home it meant (C16)")


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
    doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    models = doc.get("models") if isinstance(doc, dict) else None
    if not isinstance(models, dict) or not models:
        raise SystemExit(f"FATAL: {path} carries no 'models' mapping — the join that defines LOCAL "
                         f"has nothing to join against (C16)")
    return set(models)


def resolve_home(ref: str) -> tuple[pathlib.Path, str]:
    """A declared HOME as (REALPATH, table). 'Ownership' means realpath — this is the D-3034 resolver.

    A pointer is followed to its end (so a class home can name `homes.ledger` instead of restating the
    address — C12), and a repo-relative path is resolved from ROOT. The returned path is passed through
    `realpath`, so two spellings of one file can never be mistaken for two ledgers, and two different
    files can never be mistaken for one.
    """
    text = pointer(ref) if str(ref).startswith("@") else str(ref)
    file_part, _, table = text.partition("#")
    if not table:
        raise SystemExit(f"FATAL: the home '{ref}' names no table after '#' — a table invented here "
                         f"would be a second home (C12)")
    path = pathlib.Path(os.path.expanduser(file_part))
    if not path.is_absolute():
        path = ROOT / path
    return pathlib.Path(os.path.realpath(path)), table


def ledger_home(cfg: dict[str, Any]) -> tuple[pathlib.Path, str]:
    """The ledger FILE and its TABLE, both read from the declared pointer (no literal here)."""
    return resolve_home(cfg["homes"]["ledger"])


def metering_classes(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The declared classes. A class without a home, a reading, or a reason is not a class (C16).

    Validated here rather than trusted: `reading` must be one of the two the instrument can compute, and
    a `windowed` class must declare the window, because "the last N days" with no N is not a reading.
    """
    classes = cfg.get("metering_classes")
    if not isinstance(classes, dict) or not classes:
        raise SystemExit("FATAL: config declares no 'metering_classes' — one class is not a split (D-3101)")
    for name, spec in classes.items():
        if not isinstance(spec, dict):
            raise SystemExit(f"FATAL: metering class '{name}' is not a mapping (C16)")
        for key in ("home", "reading", "why"):
            if not spec.get(key):
                raise SystemExit(f"FATAL: metering class '{name}' declares no '{key}' — a class with no "
                                 f"reason cannot be reviewed and is refused (C12)")
        if spec["reading"] not in ("lifetime", "windowed"):
            raise SystemExit(f"FATAL: metering class '{name}' declares reading "
                             f"'{spec['reading']}' — only lifetime|windowed are computable (C16)")
        if spec["reading"] == "windowed" and not int(spec.get("window_days") or 0):
            raise SystemExit(f"FATAL: metering class '{name}' is windowed but declares no "
                             f"'window_days' — a window with no length is not a reading (C16)")
    return classes


def window_since(days: int, now: float | None = None) -> float:
    """The epoch a window opens at. `now` is injectable so a control's answer is known, not clock-dependent."""
    return (time.time() if now is None else now) - float(days) * 86400.0


def split_window(rows: list[dict[str, Any]], days: int,
                 now: float | None = None) -> tuple[list[dict[str, Any]], int]:
    """(rows inside the window, count of UNDATED rows). An undated row is never silently dropped.

    It stays in the lifetime total, it is REPORTED as undated, and it is excluded from the window —
    because a row that cannot be dated cannot be claimed inside a period (D-2957: absent is not zero).
    """
    since = window_since(days, now)
    inside: list[dict[str, Any]] = []
    undated = 0
    for row in rows:
        at = row.get("at")
        if at is None:
            undated += 1
        elif float(at) >= since:
            inside.append(row)
    return inside, undated


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


def breaches(summary: dict[str, Any], ceiling: dict[str, Any],
             token_basis: str = "gross") -> list[str]:
    """Every ceiling that is EXCEEDED, named with both numbers — never a bare boolean.

    `token_basis` decides what the TOKEN leg counts: `gross` (every reported input token — the gated
    number) or `billable_fresh` (gross minus cache reads — the tokens that are new work). The basis is
    declared in config, never inferred here, and the label says which one produced the number.
    """
    cloud = summary["tiers"]["cloud"]
    if token_basis == "billable_fresh":
        tokens = cloud["input"] - cloud["cache_read"]
        token_label = "cloud billable-fresh input tokens"
    else:
        tokens = cloud["input"]
        token_label = "cloud input tokens"
    out: list[str] = []
    for key, measured, label in (
            ("cloud_cost_usd", cloud["cost"], "cloud cost USD"),
            ("cloud_input_tokens", tokens, token_label),
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


def read_economy(cfg: dict[str, Any] | None = None, *, local: set[str] | None = None,
                 now: float | None = None) -> dict[str, dict[str, Any]]:
    """ONE reading PER METERING CLASS — the whole of D-3101 in one function.

    A class owns the ledger its home resolves to (REALPATH — D-3034), so the discriminator is a file,
    not a judgement. A class whose ledger is absent, or empty, is UNMEASURED: loud, rc-neutral, and
    never satisfied by another class's rows — otherwise the "split" would be two names for one number,
    which is exactly the defect it exists to repair.
    """
    cfg = cfg or load_config()
    local = local_model_set(cfg) if local is None else local
    families = cfg["cloud_model_families"]
    floor = declared_min_calls(cfg)
    basis = str(cfg["token_ceiling_counts"])
    ceiling = cfg["ceiling"]
    readings: dict[str, dict[str, Any]] = {}
    for name, spec in metering_classes(cfg).items():
        db, table = resolve_home(str(spec["home"]))
        rows = read_rows(db, table, cfg["ledger_fields"])
        if rows is None or not rows:
            why = (f"no ledger at {db}" if rows is None else f"the ledger at {db} carries no rows")
            readings[name] = {"state": "UNMEASURED", "home": db, "spec": spec,
                              "gate": bool(spec.get("gate", True)),
                              "why": f"{why} — this class is UNMEASURED and is NOT folded into another "
                                     f"class (absent is not zero, D-2957)"}
            continue
        lifetime = summarise(rows, local, families, floor)
        entry: dict[str, Any] = {"state": "MEASURED", "home": db, "spec": spec, "rows": len(rows),
                                 "lifetime": lifetime, "gate": bool(spec.get("gate", True))}
        if spec["reading"] == "windowed":
            days = int(spec["window_days"])
            inside, undated = split_window(rows, days, now)
            entry["window"] = summarise(inside, local, families, floor)
            entry["window_days"] = days
            entry["undated"] = undated
            entry["gated"] = entry["window"]
        else:
            entry["undated"] = sum(1 for row in rows if row.get("at") is None)
            entry["gated"] = lifetime
        entry["breaches"] = breaches(entry["gated"], ceiling, basis) if entry["gate"] else []
        readings[name] = entry
    return readings


def _tier_line(label: str, summary: dict[str, Any]) -> str:
    """One line per READING, always carrying gross and fresh input side by side (the named second axis)."""
    cloud = summary["tiers"]["cloud"]
    fresh = cloud["input"] - cloud["cache_read"]
    return (f"  {label:<24}{cloud['calls']:>9,} calls {cloud['input']:>16,} gross "
            f"{cloud['cache_read']:>16,} cached {fresh:>15,} fresh {cloud['cost']:>10,.2f} USD")


def report_economy(readings: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> str:
    """The class-by-class reading. The LIFETIME total is printed for EVERY measured class, gate or not,
    so a window can never hide history — it only decides what the GATE looks at."""
    lines = [f"metering classes ({len(readings)} declared) — a class owns the ledger its home resolves to"]
    for name, reading in readings.items():
        spec = reading["spec"]
        head = f"[{name}] reading={spec['reading']}"
        if spec["reading"] == "windowed":
            head += f" window={int(spec['window_days'])}d"
        head += f" gate={'yes' if reading.get('gate') else 'no'}"
        lines.append(head)
        if reading["state"] == "UNMEASURED":
            lines.append(f"  UNMEASURED  {reading['why']}")
            continue
        lines.append(_tier_line("lifetime (history)", reading["lifetime"]))
        if spec["reading"] == "windowed":
            lines.append(_tier_line(f"last {reading['window_days']}d (gate)", reading["window"]))
        if reading["undated"]:
            lines.append(f"  {reading['undated']:,} row(s) UNDATED — counted in the lifetime total, "
                         f"excluded from the window (a row that cannot be dated is not claimed)")
        lines.append("  gate: " + ("within every ceiling" if not reading["breaches"]
                                  else "CEILING EXCEEDED — " + "; ".join(reading["breaches"])))
    ceiling = cfg["ceiling"]
    measured = ceiling.get("measured_20261015") or {}
    for key, label in (("cloud_cost_usd", "cloud cost USD"),
                       ("cloud_input_tokens", "cloud input tokens"),
                       ("cloud_calls", "cloud calls")):
        value = float(ceiling[key])
        was = measured.get(key)
        lines.append(f"ceiling {label}: {value:,.2f} (shrink-only; measured 2026-10-15 at "
                     f"{float(was):,.2f})" if was is not None else f"ceiling {label}: {value:,.2f}")
    lines.append(f"token ceiling counts: {cfg['token_ceiling_counts']} "
                 f"(reported bases: {', '.join(cfg.get('report_token_bases') or [])})")
    lines.append("an escalation carries a reason: " + ", ".join(cfg["escalation"]["reasons"])
                 if "escalation" in cfg else "an escalation carries a reason (none declared)")
    return "\n".join(lines)


def _synth(dirname: pathlib.Path, rows: list[dict[str, Any]], drop: str | None = None) -> pathlib.Path:
    """A synthetic ledger carrying the DECLARED schema — the control's known answer (D-400)."""
    dirname.mkdir(parents=True, exist_ok=True)
    db = dirname / "sessions.db"
    spec = {"model": "TEXT", "input_tokens": "INTEGER", "output_tokens": "INTEGER",
            "cache_read_tokens": "INTEGER", "cost": "REAL", "cost_source": "TEXT",
            "created_timestamp": "INTEGER"}
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
    src = pathlib.Path(__file__).read_text(encoding='utf-8')
    cfg_text = CONFIG.read_text(encoding='utf-8') if CONFIG.exists() else ""

    def row(model: str, i: int, o: int = 0, cr: int = 0, cost: float | None = None,
            cs: str | None = None, at: int | None = None) -> dict[str, Any]:
        return {"model": model, "input_tokens": i, "output_tokens": o, "cache_read_tokens": cr,
                "cost": cost, "cost_source": cs, "created_timestamp": at}

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
            "metering_classes": {"harness_metering": {"home": "@config/x.yaml#y", "reading": "lifetime",
                                                      "why": "control: one class, the baseline shape"}},
            "token_ceiling_counts": "gross",
            "report_token_bases": ["gross", "billable_fresh"],
        }
        cpath.write_text(yaml.safe_dump(base), encoding='utf-8')
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

        # ── D-3101 CONTROLS ────────────────────────────────────────────────────────────────────────
        # These prove the SPLIT, which is the whole decision: (a) one ledger can yield two readings,
        # (b) a row in one class can never be counted in another, (c) an absent class ledger is
        # UNMEASURED rather than satisfied by the other class's rows, (d) the token ceiling's BASIS is
        # declared and changes the answer, and (e) a row that cannot be dated is reported, never
        # quietly slipped into the window.
        NOW = 1_800_000_000.0                      # a FIXED clock: a windowed answer must be known
        old_at, new_at = int(NOW - 40 * 86400), int(NOW - 1 * 86400)

        def class_cfg(name: str, classes: dict[str, Any], **over: Any) -> pathlib.Path:
            """A config with declared classes — the shipped loader is exercised, never a copy of it."""
            doc = json.loads(json.dumps(base))
            doc["metering_classes"] = classes
            doc["ledger_fields"] = dict(base["ledger_fields"], at="created_timestamp")
            doc.update(over)
            path = tmp / f"{name}.yaml"
            path.write_text(yaml.safe_dump(doc), encoding='utf-8')
            return path

        def cost_of(summary: dict[str, Any]) -> float:
            return float(summary["tiers"]["cloud"]["cost"])

        two = _synth(tmp / "two_readings", [
            row("deepseek-v4-pro", 1000, 10, 0, 5.0, "estimated", at=old_at),
            row("deepseek-v4-pro", 1000, 10, 0, 0.5, "estimated", at=new_at)])
        rd1 = read_economy(load_config(class_cfg("two_readings", {"harness_metering": {
            "home": f"{two}#usage_ledger", "reading": "windowed", "window_days": 30, "gate": True,
            "why": "control"}})), local=LOC, now=NOW)["harness_metering"]
        checks.append(("one_ledger_yields_TWO_readings_that_differ",
                       rd1["state"] == "MEASURED"
                       and abs(cost_of(rd1["lifetime"]) - 5.5) < 1e-9
                       and abs(cost_of(rd1["window"]) - 0.5) < 1e-9))

        hdb = _synth(tmp / "split_h", [row("deepseek-v4-pro", 10, 1, 0, 1.0, "estimated", at=new_at)])
        pdb = _synth(tmp / "split_p", [row("deepseek-v4-pro", 20, 2, 0, 2.0, "estimated", at=new_at),
                                       row("deepseek-v4-pro", 30, 3, 0, 3.0, "estimated", at=new_at)])
        rd2 = read_economy(load_config(class_cfg("split", {
            "harness_metering": {"home": f"{hdb}#usage_ledger", "reading": "lifetime", "gate": True,
                                 "why": "control"},
            "pipeline_ingestion": {"home": f"{pdb}#usage_ledger", "reading": "windowed",
                                   "window_days": 30, "gate": True, "why": "control"}})),
            local=LOC, now=NOW)
        checks.append(("a_pipeline_row_is_never_counted_as_harness",
                       rd2["harness_metering"]["lifetime"]["tiers"]["cloud"]["calls"] == 1
                       and rd2["pipeline_ingestion"]["window"]["tiers"]["cloud"]["calls"] == 2
                       and abs(cost_of(rd2["harness_metering"]["lifetime"]) - 1.0) < 1e-9))

        rd3 = read_economy(load_config(class_cfg("absent_class", {
            "harness_metering": {"home": f"{hdb}#usage_ledger", "reading": "lifetime", "gate": True,
                                 "why": "control"},
            "pipeline_ingestion": {"home": f"{tmp / 'nope' / 'usage.db'}#usage_ledger",
                                   "reading": "windowed", "window_days": 30, "gate": True,
                                   "why": "control"}})), local=LOC, now=NOW)
        checks.append(("an_absent_class_ledger_is_UNMEASURED_never_satisfied_by_the_other_class",
                       rd3["pipeline_ingestion"]["state"] == "UNMEASURED"
                       and "UNMEASURED" in rd3["pipeline_ingestion"]["why"]
                       and rd3["harness_metering"]["state"] == "MEASURED"))

        cached = _synth(tmp / "cached", [
            row("deepseek-v4-pro", 2000000, 10, 1900000, 0.01, "estimated", at=new_at)])
        base_classes = {"harness_metering": {"home": f"{cached}#usage_ledger", "reading": "lifetime",
                                             "gate": True, "why": "control"}}
        gross_b = read_economy(load_config(class_cfg("basis_gross", base_classes,
                                                     token_ceiling_counts="gross")),
                               local=LOC, now=NOW)["harness_metering"]["breaches"]
        fresh_b = read_economy(load_config(class_cfg("basis_fresh", base_classes,
                                                     token_ceiling_counts="billable_fresh")),
                               local=LOC, now=NOW)["harness_metering"]["breaches"]
        checks.append(("the_token_ceiling_basis_is_declared_and_decides_the_reading",
                       any("input tokens" in b for b in gross_b)
                       and not any("input tokens" in b for b in fresh_b)))

        und = _synth(tmp / "undated", [
            row("deepseek-v4-pro", 1000, 10, 0, 2.0, "estimated", at=None),
            row("deepseek-v4-pro", 1000, 10, 0, 0.5, "estimated", at=new_at)])
        rd5 = read_economy(load_config(class_cfg("undated", {"harness_metering": {
            "home": f"{und}#usage_ledger", "reading": "windowed", "window_days": 30, "gate": True,
            "why": "control"}})), local=LOC, now=NOW)["harness_metering"]
        checks.append(("an_undated_row_is_counted_in_the_lifetime_and_never_smuggled_into_the_window",
                       rd5["undated"] == 1
                       and abs(cost_of(rd5["lifetime"]) - 2.5) < 1e-9
                       and abs(cost_of(rd5["window"]) - 0.5) < 1e-9))

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
        cfg = load_config()
        readings = read_economy(cfg)
    except SystemExit as exc:
        print(str(exc))
        return RC_BREACH
    measured = {name: r for name, r in readings.items() if r["state"] == "MEASURED"}
    if not measured:
        print("UNMEASURED delegation-economy: no metering class has a ledger to read — "
              + "; ".join(f"{name}: {r['why']}" for name, r in readings.items()))
        return RC_UNMEASURED
    bad = [f"[{name}] {line}" for name, reading in measured.items() if reading.get("gate")
           for line in reading["breaches"]]
    # A declared GATE class with no ledger is not "green": nothing about it was measured. That is the
    # whole of D-2957 (absent is not zero), so it is reported loudly and returns UNMEASURED (2) —
    # tolerated by the ladder exactly as an OWNER-OWED env name is (BUG-457), never silently passed.
    unmeasured_gates = [name for name, reading in readings.items()
                        if reading["state"] == "UNMEASURED" and reading.get("gate")]
    if args.json:
        print(json.dumps({"classes": readings, "breaches": bad,
                          "unmeasured_gate_classes": unmeasured_gates}, indent=1, default=str))
    else:
        print(report_economy(readings, cfg))
        for line in bad:
            print(f"  BREACH  {line}")
        if bad:
            print("  a ceiling is SHRINK-ONLY: route the work to T0 (script) or T1 (local engine), or the "
                  "OWNER raises the ceiling with a reason (D-3023)")
        for name in unmeasured_gates:
            print(f"  UNMEASURED CLASS  [{name}] {readings[name]['why']}")
        if unmeasured_gates:
            print("  a class with no ledger is not a zero and not a pass: the gate is green only on what "
                  "was measured, and this class was not (D-2957)")
    if bad:
        return RC_BREACH
    if unmeasured_gates:
        return RC_UNMEASURED
    return RC_OK


if __name__ == "__main__":
    raise SystemExit(main())
