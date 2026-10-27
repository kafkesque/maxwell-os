#!/usr/bin/env python3
"""hardware_calibrate.py — the personal-calibration resolver (D-3178).

THE PROBLEM IT SOLVES. Finding the right model for each job on a given machine took this owner a day of
measurements and several wrong turns (governance/SPECULATIVE_DECODING_M1_20261027.md). None of that search was
machine-specific knowledge an installer could not carry. This script is the thing that carries it: on any host it
detects what is actually there, predicts what can run from a MEASURED bandwidth, and assigns roles from
RECEIPTS — never from model cards, download counts or a vendor claim.

THE THREE LAYERS, AND WHY EACH IS REPORTED DIFFERENTLY (D-3036)
    1. DETECT  — deterministic facts. If a fact cannot be read it is reported NOT RECORDED, never guessed.
    2. PREDICT — roofline from a measured streaming-copy bandwidth. Labelled PREDICTED. It may PRUNE a
                 candidate (do not download 15 GB for 2 t/s) but may never assign a role.
    3. VERIFY  — a MEASURED receipt (cold prefill with cached_tokens=0, decode at >= min_decode_tokens tokens)
                 plus, where the role demands it, a PASSING accuracy gate. Receipts are keyed to the hardware
                 fingerprint AND the engine version: a reading from 0.7.3.dev2 is not a reading of 0.7.3rc1.

FAIL-CLOSED. A role with no measured candidate is reported UNCALIBRATED. It is never filled with a prediction, a
bigger-looking model, or the incumbent "because it was there before" — that is how an assignment becomes folklore.

C12: every value (paths, thresholds, objectives, probe sizes) comes from config/hardware_profile.yaml. This file
names no host, port, threshold, role or model.

Usage:
    python3 scripts/hardware_calibrate.py                     # detect + predict + assign (read only)
    python3 scripts/hardware_calibrate.py --json              # machine-readable
    python3 scripts/hardware_calibrate.py --write             # emit config/model_roles.yaml
    python3 scripts/hardware_calibrate.py --bandwidth         # re-measure streaming bandwidth
    python3 scripts/hardware_calibrate.py --selftest          # offline known-answer controls

Exit: 0 all roles resolved | 2 at least one role UNCALIBRATED (unmeasured, by design) | 1 the probe itself failed
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # the repo idiom: runnable AND importable (C21)
    sys.path.insert(0, str(ROOT))

CFG_PATH = ROOT / "config" / "hardware_profile.yaml"
OK, UNCALIBRATED, FATAL = 0, 2, 1


def _cfg() -> dict[str, Any]:
    """Load the calibration declaration (C12: this file holds no value of its own)."""
    import yaml  # noqa: PLC0415

    if not CFG_PATH.is_file():
        raise SystemExit("hardware_calibrate: missing " + str(CFG_PATH))
    doc = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit("hardware_calibrate: config does not parse to a mapping")
    return doc


def _sysctl(key: str) -> str | None:
    """Read one sysctl key, or None when the platform does not have it (never a guess)."""
    try:
        out = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=10, check=False)
        value = out.stdout.strip()
        return value or None
    except (OSError, subprocess.SubprocessError):
        return None


def detect(cfg: dict[str, Any]) -> dict[str, Any]:
    """Layer 1: deterministic hardware and engine facts (D-3034: every value resolves or is NOT RECORDED)."""
    keys = cfg["detect"]["sysctl_keys"]
    paths = cfg["detect"]["paths"]
    ram_bytes = _sysctl(keys["ram_bytes"])
    wired = _sysctl(keys["wired_limit_mb"])
    bf16 = _sysctl(keys["bf16_native"])
    plist = Path(str(paths["app_plist"]))
    version = None
    if plist.is_file():
        try:
            out = subprocess.run(
                ["/usr/libexec/PlistBuddy", "-c", "Print :" + str(paths["app_version_key"]), str(plist)],
                capture_output=True, text=True, timeout=10, check=False)
            version = out.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            version = None
    return {
        "chip": _sysctl(keys["chip"]) or "NOT RECORDED",
        "ram_gb": round(int(ram_bytes) / 2**30, 1) if ram_bytes else None,
        "perf_cores": _sysctl(keys["perf_cores"]) or "NOT RECORDED",
        "wired_limit_gb": round(int(wired) / 1024, 1) if wired else None,
        # MEASURED capability, not a spec-sheet claim: this is WHY the MTP head's bf16 scales cost this chip
        # (PR 990's own warning) and why oMLX 0.7.3rc1 ships float16 activations for M1/M2.
        "bf16_native": (bf16 == "1") if bf16 is not None else "NOT RECORDED",
        "os": platform.platform(),
        "engine_version": version or "NOT RECORDED",
        "disk_free_gb": round(_disk_free_gb(ROOT), 1),
    }


def _disk_free_gb(path: Path) -> float:
    """Free bytes on the volume holding `path`, in GiB."""
    stat = os.statvfs(str(path))
    return (stat.f_bavail * stat.f_frsize) / 2**30


def _now() -> str:
    """The clock every dynamic figure is stamped with (BUG-1060: a reading without a time is a claim)."""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _pool(cfg: dict[str, Any]) -> dict[str, Any]:
    """ONE read of the engine's pool document: ceiling, resident and the loaded set come from the SAME instant.

    The endpoint is `config/engine.yaml#engine.status_endpoint`, not a literal, and the key is the declared
    pointer. Reading the ceiling from /health and the residency from /v1/models/status would be two instants
    presented as one — the exact defect this function exists to remove.
    """
    import yaml  # noqa: PLC0415

    engine = yaml.safe_load((ROOT / str(cfg["detect"]["engine"])).read_text(encoding="utf-8"))["engine"]
    url = f"http://{engine['host']}:{engine['port']}{engine['status_endpoint']}"
    from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: PLC0415

    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + str(OMLX_API_KEY)})
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - the declared home
        return json.loads(response.read().decode())


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append + fsync (C6). A receipt a crash can truncate is not a receipt (D-3036)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def ceiling_reading(cfg: dict[str, Any], hardware: dict[str, Any]) -> dict[str, Any]:
    """The memory budget as a READING: clock, a second sample, the observed range, and the resident figure.

    BUG-1060: `final_ceiling` is computed against AVAILABLE memory, so it MOVED between 49.2 and 61.3 GiB within
    one hour on this host. A single sample printed as a property turned "43.7 GiB into 40.4 usable" into a
    standing fact when neither number was stable. Two samples per call make a moving figure VISIBLE in the run
    that reads it; the receipt keeps every reading so the quoted range is a set of measurements, not a memory.
    """
    spec = cfg["memory"].get("ceiling_readings") or {}
    fallback = round(float(hardware["ram_gb"]) - float(cfg["memory"]["fallback_reserve_gb"]), 1)
    try:
        first = _pool(cfg)
    except Exception as exc:  # noqa: BLE001 - the fallback is declared, and its reason is reported
        return {"gb": fallback, "source": f"RAM minus reserve (engine unreachable: {type(exc).__name__})",
                "at": _now(), "planning_gb": fallback, "gb_second": None, "range_gb": None, "n_readings": 0,
                "receipt": None, "resident_gb": None, "loaded": None}
    at = _now()
    ceiling_gb = round(float(first["final_ceiling"]) / 2**30, 1)
    resident_gb = round(float(first["current_model_memory"]) / 2**30, 1)
    loaded = sorted(m.get("id") for m in first.get("models") or [] if m.get("loaded"))
    second_gb: float | None = None
    if spec.get("receipt"):
        time.sleep(float(spec.get("second_sample_gap_s") or 0))
        try:
            second = _pool(cfg)
            second_gb = round(float(second["final_ceiling"]) / 2**30, 1)
        except Exception:  # noqa: BLE001 - a second sample is evidence, and its absence is reported not faked
            second_gb = None
        receipt = ROOT / str(spec["receipt"])
        _append_jsonl(receipt, [{"at": at, "final_ceiling_gb": ceiling_gb, "resident_gb": resident_gb,
                                 "loaded_count": len(loaded)}])
        lo, hi, n = _observed_range(receipt, int(spec.get("report_window_n") or 0))
    else:
        lo, hi, n = (None, None, 0)
    return {"gb": ceiling_gb, "source": "engine final_ceiling (a DYNAMIC reading, BUG-1060)", "at": at,
            "planning_gb": min(lo, ceiling_gb) if lo is not None else ceiling_gb,
            "gb_second": second_gb, "range_gb": (lo, hi) if lo is not None else None, "n_readings": n,
            "receipt": str(spec.get("receipt")) if spec.get("receipt") else None,
            "resident_gb": resident_gb, "loaded": loaded}


def _observed_range(receipt: Path, window: int) -> tuple[float | None, float | None, int]:
    """Min/max of the last `window` readings in the ceiling receipt: a range must be MEASURED, never remembered."""
    if not receipt.is_file():
        return (None, None, 0)
    rows = [json.loads(line) for line in receipt.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if isinstance(r.get("final_ceiling_gb"), (int, float))]
    if window:
        rows = rows[-window:]
    if not rows:
        return (None, None, 0)
    values = [float(r["final_ceiling_gb"]) for r in rows]
    return (min(values), max(values), len(values))


def ceiling_text(reading: dict[str, Any]) -> str:
    """The face of a dynamic figure: value, clock, second sample, and the range it was drawn from (BUG-1060)."""
    if not reading:
        return "NOT READ"
    text = f"{reading['gb']} GiB read at {reading.get('at') or 'NOT STAMPED'}"
    second = reading.get("gb_second")
    if second is not None and abs(float(second) - float(reading["gb"])) >= 0.05:
        text += f", {second} GiB two seconds later (the ceiling MOVES)"
    rng = reading.get("range_gb")
    if rng:
        text += (f"; observed range {rng[0]}-{rng[1]} GiB over the last {reading.get('n_readings')} reading(s)"
                 f" in {reading.get('receipt')}")
    return text


def measured_text(reading: dict[str, Any], weights_gb: float, portfolio_n: int = 0) -> str:
    """MEASURED resident beside the WEIGHTS-ONLY sum: two different quantities, printed as two (D-3109).

    They are also quantities over different OBJECTS unless the whole portfolio happens to be resident, so the
    loaded count is printed against the portfolio size: MEASURED 2026-10-27 the engine held 19.9 GiB with 2 of
    the portfolio's 6 models loaded while the sum read 43.7 GiB, and a bare difference of "23.8 GiB below"
    would have described a subset as if it were the set."""
    resident = reading.get("resident_gb")
    if resident is None:
        return "NOT READ (engine unreachable: the weights-only sum below is unverified against real residency)"
    loaded = reading.get("loaded") or []
    size = f"{len(loaded)}/{portfolio_n} of the assigned portfolio's model(s) are loaded" if portfolio_n else \
        f"{len(loaded)} model(s) are loaded"
    return (f"{resident} GiB resident at {reading.get('at')} — {size}; the engine figure includes KV, "
            f"activations and any unassigned resident, while the {weights_gb} GiB sum counts WEIGHTS only")


def measure_bandwidth(cfg: dict[str, Any]) -> float | None:
    """Layer 2 input: streaming-copy bandwidth in GB/s, measured with MLX on this device.

    Decode on this class of hardware is WEIGHT-READ bound (MEASURED: decode is flat from 157 to 1850 tokens of
    context), so the traffic a copy pays is the traffic a decode step pays. Returns None when MLX is absent —
    the caller then reports PREDICTED values as unavailable rather than inventing a number."""
    probe = cfg["predict"]["bandwidth_probe"]
    try:
        import mlx.core as mx  # noqa: PLC0415
    except ImportError:
        return None
    n = int(float(probe["buffer_gb"]) * 2**30 / 4)  # float32 elements
    src = mx.ones((n,), dtype=mx.float32)
    mx.eval(src)
    samples: list[float] = []
    for _ in range(int(probe["repeats"])):
        started = time.perf_counter()
        # MEASURED TRAP (2026-10-27): `mx.array(src)` does NOT materialise a copy, so the first version of this
        # probe reported 5,149,844 GB/s — an impossible number that would have predicted 4,167,923 t/s. An
        # elementwise op over the whole buffer is real traffic and is forced to complete by mx.eval.
        dst = src + 1.0
        mx.eval(dst)
        elapsed = time.perf_counter() - started
        if elapsed > 0:
            samples.append((2 * n * 4) / elapsed / 1e9)  # GB moved (read+write) per second
    if not samples:
        return None
    value = round(statistics.median(samples), 1)
    if value > float(probe["max_plausible_gbs"]):
        print(f"  bandwidth probe REFUSED: {value} GB/s exceeds the declared plausible ceiling "
              f"({probe['max_plausible_gbs']}) — a broken probe, not a fast machine", file=sys.stderr)
        return None
    return value


def model_bytes(models_root: Path, name: str) -> int | None:
    """Real on-disk weight bytes for a served model, following symlinks (D-3034)."""
    path = models_root / name
    if not path.exists():
        return None
    return weight_bytes(path)


def weight_bytes(path: Path) -> int | None:
    """The weight files in ONE directory, symlinks followed. Absent or empty is None, never 0."""
    if not path.exists():
        return None
    total = 0
    for item in sorted(path.glob("*.safetensors")):
        try:
            total += item.stat().st_size  # stat() follows the symlink
        except OSError:
            return None
    return total or None


def engine_model_paths(cfg: dict[str, Any]) -> dict[str, str]:
    """id -> the directory THE ENGINE says that id's bytes live in.

    MEASURED 2026-10-27: a model the engine discovered from the hub cache (`lmstudio-community--<name>`) has NO
    entry under `detect.paths.models_root`, so `model_bytes` returned None and a declared candidate would have
    been ranked with an unknown footprint. The serving directory is not the only witness of where bytes are —
    the engine's own `model_path` is — and a register that cannot size a candidate it declares has a blind spot
    exactly where a new candidate enters. Only consulted when a candidate's farm entry is absent (so the common
    path never pays a request), and an unreachable engine returns {} rather than inventing a path.
    """
    try:
        return {str(m.get("id")): str(m.get("model_path") or "") for m in (_pool(cfg).get("models") or [])}
    except Exception:  # noqa: BLE001 - the caller reports 'size unknown' rather than guessing
        return {}


def receipts(cfg: dict[str, Any], hardware: dict[str, Any]) -> list[dict[str, Any]]:
    """Measured receipts that belong to THIS hardware and THIS engine version (never pooled across them)."""
    path = ROOT / str(cfg["receipts"])
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        same_chip = (row.get("hardware") or {}).get("chip") == hardware["chip"]
        same_engine = (row.get("engine") or {}).get("version") == hardware["engine_version"]
        if same_chip and same_engine:
            rows.append(row)
    return rows


def gates(cfg: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """Latest verdict per (GATE, model) - the gate's own artifact, never a re-derivation.

    BUG-1063 limb 1: this used to key on MODEL alone, so with two gates in one artifact a `plan_quality`
    PASS could satisfy the `review` role's `r5_review` gate. A row's gate identity is now its own
    `gate:` field, or - for rows written before that field existed - the receipt's DECLARED
    `row_gate_default` (a declaration, never an inference from a filename).
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for gate_id, spec in (cfg.get("gates") or {}).items():
        path = ROOT / str(spec.get("receipt") or "")
        default = str(spec.get("row_gate_default") or gate_id)
        if not path.is_file():
            out.setdefault(str(gate_id), {})
            continue
        latest = out.setdefault(str(gate_id), {})
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("gate") or default) != str(gate_id):
                continue  # a row that RESOLVES to another gate cannot resolve this one
            model = str(row.get("model") or "")
            if model and (model not in latest or str(row.get("ts", "")) >= str(latest[model].get("ts", ""))):
                latest[model] = row
    return out


def predict_decode(hardware: dict[str, Any], cfg: dict[str, Any], nbytes: int,
                   fraction: float, bandwidth: float | None) -> dict[str, float] | None:
    """Roofline: bandwidth / bytes-read-per-token, times the efficiency this device actually reaches."""
    if not bandwidth:
        return None
    traffic = nbytes * fraction
    ceiling = bandwidth * 1e9 / traffic if traffic else 0.0
    return {"roofline_tps": round(ceiling, 1),
            "predicted_tps": round(ceiling * float(cfg["predict"]["decode_efficiency"]), 2),
            "bandwidth_gbs": bandwidth}


def resolve(cfg: dict[str, Any], hardware: dict[str, Any], budget_gb: float, bandwidth: float | None,
            rows: list[dict[str, Any]], gate_rows: dict[str, dict[str, dict[str, Any]]],
            allow_predicted: bool) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Assign each role from MEASURED receipts; report UNCALIBRATED where nothing measured qualifies."""
    models_root = Path(os.path.expanduser(str(cfg["detect"]["paths"]["models_root"])))
    usable_gb = usable_gb_for(cfg, budget_gb)
    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(str(row.get("model")), []).append(row)

    table: list[dict[str, Any]] = []
    # A candidate the engine discovered from the hub cache has no farm entry; ask the engine for its real path
    # only when that is the case, so the common path stays request-free (engine_model_paths).
    missing = [str(c["model"]) for c in cfg["candidates"] if not (models_root / str(c["model"])).exists()]
    served_paths = engine_model_paths(cfg) if missing else {}
    for cand in cfg["candidates"]:
        name = str(cand["model"])
        nbytes = model_bytes(models_root, name)
        bytes_src = "serving dir"
        if nbytes is None and served_paths.get(name):
            nbytes = weight_bytes(Path(served_paths[name]))
            bytes_src = "engine model_path"
        measured = by_model.get(name, [])
        usable = [r for r in measured if int(r.get("generation_tokens") or 0) >= int(cfg["receipts_min_decode_tokens"])]
        # the MEDIAN across readings, with n reported: an MTP model's rate is CONTENT-dependent (acceptance
        # varies with the text), so a single receipt is not a stable claim and max() would flatter it.
        best_decode = round(statistics.median([float(r["decode_tps"]) for r in usable]), 2) if usable else None
        best_prefill = round(statistics.median([float(r["prefill_tps"]) for r in usable]), 2) if usable else None
        n_readings = len(usable)
        row: dict[str, Any] = {
            "model": name,
            "gb": round(nbytes / 2**30, 1) if nbytes else None,
            "fits": bool(nbytes and nbytes / 2**30 <= usable_gb),
            # the candidate's verdict PER GATE: no role may read another role's gate (BUG-1063 limb 1)
            "gates": {gid: (rows_for.get(name) or {}).get("pass") for gid, rows_for in gate_rows.items()},
            "decode_tps": best_decode,
            "prefill_tps": best_prefill,
            "source": "MEASURED" if usable else "UNMEASURED",
            "n_readings": n_readings,
            "roles": list(cand.get("roles") or []),
            "bytes_source": bytes_src,
        }
        if nbytes:
            row["prediction"] = predict_decode(hardware, cfg, nbytes, float(cand["moe_active_fraction"]),
                                               bandwidth)
        table.append(row)

    roles: dict[str, dict[str, Any]] = {}
    for role, spec in cfg["roles"].items():
        objective = str(spec["objective"])
        need_gate = spec.get("require_gate")
        pool = []
        for row in table:
            if role not in row["roles"]:
                continue  # a candidate may only take a role it DECLARES (checked against the candidate register)
            if not row["fits"]:
                continue
            if row["source"] != "MEASURED":
                continue  # fail-closed: a prediction never fills a role
            if need_gate and (row["gates"].get(str(need_gate)) is not True):
                continue
            if objective == "seconds_per_item":
                # the reviewer's real cost: a cold call is ~75% prefill, so the objective is total seconds
                value = row.get("decode_tps") and row.get("prefill_tps")
                if not value:
                    continue
                pool.append((row, 1.0 / (1.0 / row["prefill_tps"] * 100 + 1.0 / row["decode_tps"] * 100)))
            else:
                key = "prefill_tps" if objective == "prefill_tps" else "decode_tps"
                if row.get(key) is None:
                    continue
                pool.append((row, float(row[key])))
        if pool:
            pool.sort(key=lambda pair: pair[1], reverse=True)
            winner, value = pool[0]
            roles[role] = {
                "model": winner["model"],
                "objective": objective,
                "value": round(value, 3),
                "source": "MEASURED",
                "n_readings": winner["n_readings"],
                "gate": winner["gates"].get(str(need_gate)) if need_gate else None,
                "status": ("UNDER-SAMPLED" if winner["n_readings"] < int(cfg["min_readings_per_candidate"]) else
                       ("QUALIFIED" if need_gate and winner["gates"].get(str(need_gate)) is True
                        else "PROVISIONAL")),
                "decided_by": "governance/calibration_receipts.jsonl",
            }
        elif allow_predicted:
            # BUG-1063 limb 2: this pool used to filter on `fits` alone, so a model that declares NO role
            # (and a model with no gate row) could be seated by a roofline number - the exact slop the
            # eligibility rule above exists to prevent. A prediction prunes; it never confers eligibility.
            pred = [r for r in table if r["fits"] and r.get("prediction")
                    and role in r["roles"]
                    and (not need_gate or r["gates"].get(str(need_gate)) is True)]
            if pred:
                pred.sort(key=lambda r: r["prediction"]["predicted_tps"], reverse=True)
                roles[role] = {"model": pred[0]["model"], "objective": objective,
                               "value": pred[0]["prediction"]["predicted_tps"], "source": "PREDICTED",
                               "gate": pred[0]["gates"].get(str(need_gate)) if need_gate else None,
                               "decided_by": "roofline (NOT a reading)"}
            else:
                roles[role] = {"model": None, "source": "UNCALIBRATED",
                               "why": "no candidate fits this budget and none can be predicted"}
        else:
            roles[role] = {"model": None, "source": "UNCALIBRATED",
                           "why": "no MEASURED receipt on this hardware+engine passes the gates; run the "
                                  "calibration for a candidate before assigning this role"}
    return roles, table

def parse_size_gb(raw: Any) -> float | None:
    """A declared size STRING ('8GB', '512MB', 8589934592) -> GiB as float; None when it is not a size at all.

    The engine writes sizes as strings with a unit suffix, and `auto` / `null` are real values it uses. A parser
    that turned `auto` into 0.0 would print a zero reserve as if it were a reading, so an unparseable token
    returns None and the caller falls back WITH A NAMED REASON (BUG-1071).
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return round(float(raw) / 2**30, 2) if raw > 2**20 else round(float(raw), 2)  # bytes vs a bare number
    if not isinstance(raw, str):
        return None
    text = raw.strip().upper().replace(" ", "")
    for suffix, factor in (("TIB", 1024.0), ("TB", 1024.0), ("GIB", 1.0), ("GB", 1.0),
                           ("MIB", 1 / 1024), ("MB", 1 / 1024), ("KIB", 1 / 2**20), ("KB", 1 / 2**20)):
        if text.endswith(suffix):
            try:
                return round(float(text[: -len(suffix)]) * factor, 2)
            except ValueError:
                return None
    return None


def _engine_doc(cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The engine's OWN settings document, located through the declaration that names it.

    `config/engine.yaml#engine.settings` is the path (MEASURED: ~/.omlx/settings.json). This is the second
    segment of the `kv_headroom_source` pointer, so the pointer never hardcodes a location (C12).
    """
    import yaml  # noqa: PLC0415

    engine_cfg = ROOT / "config" / "engine.yaml"
    if not engine_cfg.is_file():
        return None, f"{engine_cfg.relative_to(ROOT)} is absent"
    engine = (yaml.safe_load(engine_cfg.read_text(encoding="utf-8")) or {}).get("engine") or {}
    raw = engine.get("settings")
    if not raw:
        return None, "config/engine.yaml#engine.settings is not declared"
    path = Path(os.path.expanduser(str(raw)))
    if not path.is_file():
        return None, f"the declared settings document {path} does not exist"
    try:
        return json.loads(path.read_text(encoding="utf-8")), str(path)
    except (OSError, ValueError) as exc:  # C16: log the cause, do not swallow it
        return None, f"{path} is not readable JSON ({exc})"


def kv_reserve(cfg: dict[str, Any]) -> dict[str, Any]:
    """The KV reserve, DERIVED from a declared pointer, or the declared FALLBACK with the reason it was used.

    WHY A POINTER AND NOT A NUMBER (BUG-1055 limb 4, D-3196). This engine PAGES its KV cache — a RAM hot tier
    plus an SSD tier — so the retained working set is a BUDGET, not a per-token slope. MEASURED on
    Qwen3.8-27B-MTP4: 0.14 GiB at 8,236 prompt tokens and 0.29 GiB at 32,813, i.e. a 4x context increase bought
    0.15 GiB. A per-token model would have predicted ~2.0 GiB at 32k and ~8 GiB at 131k; the engine's own
    architecture says otherwise. What must be reserved is therefore the ceiling the engine may hold IN RAM — its
    own declared hot-cache budget — and that budget is a CONFIGURED value the engine's document owns. Sizing it
    from a round number here would be a second, silent source of truth.

    A pointer is only worth what it RESOLVES to (D-3034). Every segment is walked; if any segment is absent the
    result is `kind: FALLBACK` and `why` names the segment that failed, so the report can say which one ran.
    """
    mem = cfg["memory"]
    fallback = round(float(mem.get("kv_headroom_gb") or 0.0), 2)
    pointer = str(mem.get("kv_headroom_source") or "").strip()
    if not pointer:
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": "no memory.kv_headroom_source pointer is declared", "raw": None}
    parts = pointer.split(".")
    if len(parts) < 4:
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": f"pointer {pointer!r} does not name <file>.<block>.<key...>", "raw": None}
    if parts[0] != "engine":
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": f"pointer {pointer!r} begins at unknown file alias {parts[0]!r}", "raw": None}
    doc, where = _engine_doc(cfg)
    if doc is None:
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": where, "raw": None}
    if parts[1] != "settings":
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": f"pointer {pointer!r} begins inside block {parts[1]!r}, which is not the settings document",
                "raw": None}
    node: Any = doc
    for depth, key in enumerate(parts[2:], start=2):
        if not isinstance(node, dict) or key not in node:
            walked = ".".join(parts[:depth])
            return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                    "why": f"the pointer stops resolving at {walked!r}: key {key!r} is absent from {where}",
                    "raw": None}
        node = node[key]
    gb = parse_size_gb(node)
    if gb is None:
        return {"gb": fallback, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                "why": f"{pointer} = {node!r}, which is not a parseable size", "raw": node}
    # The RAW token travels beside the GiB figure: `8GB` is the engine's own words, and a reader must be able to
    # see the declared token rather than only this file's unit conversion.
    return {"gb": gb, "kind": "DERIVED", "source": pointer, "why": f"read from {where}", "raw": node}


def usable_gb_for(cfg: dict[str, Any], budget_gb: float, reserve: dict[str, Any] | None = None) -> float:
    """THE one derivation of the usable budget (C12: no literal 0.8 / 3.0 anywhere else in this file).

    Every printed figure must come through here. Before this existed the report hardcoded `budget_gb * 0.8 - 3.0`
    while the JSON path read the config, so tuning `memory.kv_headroom_gb` moved one figure and not the other —
    a declaration that could not reach the surface it describes (BUG-1062). The reserve is now the RESOLVED one
    (kv_reserve), so a derived budget and a printed budget cannot disagree (BUG-1071).
    """
    mem = cfg["memory"]
    kv = reserve if reserve is not None else kv_reserve(cfg)
    return round(budget_gb * float(mem["max_resident_fraction"]) - float(kv["gb"]), 1)


def kv_measured(cfg: dict[str, Any]) -> dict[str, Any]:
    """What the KV receipt actually measured: CLEAN points only, and the largest measured context.

    A flagged row is EVIDENCE OF A BAD MEASUREMENT, never a data point: the 10.56 GiB row at 32,811 tokens was a
    NEIGHBOUR MODEL's load attributable to nothing but timing (BUG-1070), and computing a mean over it would be
    the slop the flag exists to prevent. Returns {} when the receipt is absent, so the note says NOT RECORDED
    rather than inventing a figure.
    """
    probe = (cfg.get("memory") or {}).get("kv_probe") or {}
    path = ROOT / str(probe.get("receipt") or "governance/kv_working_set.jsonl")
    if not path.is_file():
        return {}
    clean: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not row.get("flags") and int(row.get("prompt_tokens") or 0) > 0:
            clean.append(row)
    if not clean:
        return {}
    top = max(clean, key=lambda r: int(r["prompt_tokens"]))
    return {"n_clean": len(clean), "max_tokens": int(top["prompt_tokens"]),
            "kv_gib_at_max": round(float(top.get("kv_bytes") or 0) / 2**30, 2),
            "kib_per_token": (round(float(top.get("kv_kib_per_token") or 0), 2)
                              if top.get("kv_kib_per_token") else None),
            "receipt": str(path.relative_to(ROOT))}


def kv_text(reserve: dict[str, Any], measured: dict[str, Any], highest: int | None,
            at_ceiling: list[str], receipt: str) -> str:
    """The KV line: a BUDGET that was DERIVED (or a fallback that names its failure) plus what was MEASURED.

    The distinction this line exists to hold: the reserve is the worst case the engine may hold in RAM, and the
    measurement is what it actually retained. Printing only the reserve overstates the working set by ~20x, and
    printing only the measurement understates the budget a weights plan must leave free. Both, each labelled.
    """
    if not measured:
        return (f"NOT RECORDED: {receipt} has no clean point, so the retained working set is unmeasured; the "
                f"reserve in force is {reserve['gb']} GiB ({reserve['kind']} from {reserve['source']})")
    head = (f"the reserve is {reserve['gb']} GiB — the engine's own hot-cache BUDGET ({reserve['kind']} from "
            f"{reserve['source']}, declared {reserve['raw']!r}), NOT a per-token model: this engine PAGES KV "
            f"(SSD tier), so the retained set is a CAP")
    if reserve["kind"] != "DERIVED":
        head += f" — ⚠ FALLBACK RAN: {reserve['why']}"
    body = (f"MEASURED {measured['kv_gib_at_max']} GiB retained at {measured['max_tokens']} tokens over "
            f"{measured['n_clean']} clean point(s) in {measured['receipt']}")
    ctx = (f"; highest assigned min_ctx {highest} tokens — {', '.join(at_ceiling) or 'none'}"
           if highest else "; no assigned role declares a min_ctx")
    return f"{head}. {body}{ctx}"


def declared_min_ctx(cfg: dict[str, Any]) -> dict[str, dict[str, int]]:
    """role -> {model -> min_ctx} exactly as the candidate rows declare it (absent is absent, never inferred)."""
    out: dict[str, dict[str, int]] = {}
    for cand in cfg["candidates"]:
        for role, ctx in (cand.get("min_ctx") or {}).items():
            out.setdefault(str(role), {})[str(cand["model"])] = int(ctx)
    return out


def residency(roles: dict[str, dict[str, Any]], table: list[dict[str, Any]], usable_gb: float,
              mem: dict[str, Any] | None = None,
              min_ctx: dict[str, dict[str, int]] | None = None,
              kv: dict[str, Any] | None = None) -> dict[str, Any]:
    """Can the assigned portfolio be RESIDENT together?

    A per-role winner set that cannot co-reside is a plan that thrashes: every request crosses roles and pays a
    cold load (MEASURED 5.8-7.2 s per load on this host), which is exactly the kind of hidden cost a per-role
    table hides. Reported, never silently accepted.

    The sum is WEIGHTS ONLY, and the note now says so. It is also NOT a working-set claim: the KV term is the
    engine's own hot-cache BUDGET (`memory.kv_headroom_source`, DERIVED by kv_reserve) priced as the worst case it
    may hold in RAM, BESIDE what the receipt MEASURED it actually retained — because this engine pages KV, and a
    per-token model of the reserve would overstate the working set by an order of magnitude (D-3196). The roles at
    the highest declared min_ctx are still named on every report, so an uncovered context cannot be inferred as
    covered from a line that reads as a fit guarantee (BUG-1055 limb 4).
    """
    sizes = {row["model"]: (row["gb"] or 0.0) for row in table}
    needed = sorted({pick["model"] for pick in roles.values() if pick.get("model")})
    total = round(sum(sizes.get(name, 0.0) for name in needed), 1)
    note = ("weights of all assigned models fit at once (KV excluded)" if total <= usable_gb else
            "the assigned WEIGHTS exceed the budget: the engine evicts between roles, so a call that "
            "crosses roles pays a cold load")
    ctx_by_role = min_ctx or {}
    demanded = [(role, ctx_by_role.get(role, {}).get(str(pick.get("model"))))
                for role, pick in roles.items() if pick.get("model")]
    demanded = [(role, int(ctx)) for role, ctx in demanded if ctx]
    highest = max((ctx for _, ctx in demanded), default=None)
    kv_note: str | None = None
    if kv is not None:
        reserve = kv["reserve"]
        at_ceiling = sorted(role for role, ctx in demanded if ctx == highest)
        kv_note = kv_text(reserve, kv.get("measured") or {}, highest, at_ceiling, kv["receipt"])
    elif mem is not None and mem.get("kv_headroom_ctx") is None and not mem.get("kv_headroom_source"):
        # THE HONEST BRANCH SURVIVES for a config that declares NEITHER a pointer NOR a basis: a bare null with no
        # pointer is still a declaration with no referent and must say so (D-3189 limb c's shape applied to KV).
        reserve_gb = float(mem.get("kv_headroom_gb") or 0.0)
        at_ceiling = sorted(role for role, ctx in demanded if ctx == highest)
        kv_note = (f"NOT MODELLED: KV is a {reserve_gb} GiB flat reserve that declares NEITHER a context basis NOR "
                   f"a source pointer (memory.kv_headroom_ctx is null and memory.kv_headroom_source is absent), so "
                   f"no role is covered by it; highest declared min_ctx {highest} tokens — "
                   f"{', '.join(at_ceiling) or 'none'} (BUG-1055)")
    elif mem is not None and mem.get("kv_headroom_ctx") is not None:
        reserve_gb = float(mem.get("kv_headroom_gb") or 0.0)
        basis = int(mem["kv_headroom_ctx"])
        uncovered = sorted(role for role, ctx in demanded if ctx > basis)
        at_basis = sorted(role for role, ctx in demanded if ctx == basis)
        # THE RESERVE COVERS ONE ROLE, AND THE PORTFOLIO MAY HOLD SEVERAL AT THAT CONTEXT. A single reserve
        # subtracted once while N roles declare the same min_ctx understates the working set by (N-1) reserves,
        # so the count is printed rather than left to be multiplied by a reader who is already reading a
        # weights-only "fits" claim (BUG-1055 limb 4).
        multi = (f"; {len(at_basis)} role(s) declare that context ({', '.join(at_basis)}), and the reserve is "
                 f"subtracted ONCE, so the working set is {reserve_gb} GiB x {len(at_basis)} = "
                 f"{round(reserve_gb * len(at_basis), 1)} GiB if all are warm at once") if len(at_basis) > 1 else ""
        kv_note = (f"KV is a {reserve_gb} GiB reserve measured at ctx {basis} (governance/kv_working_set.jsonl); "
                   f"highest assigned min_ctx {highest} tokens; over-basis role(s): "
                   f"{', '.join(uncovered) or 'none'}{multi}")
    return {"models": needed, "total_gb": total, "usable_gb": round(usable_gb, 1),
            "co_resident": total <= usable_gb, "note": note, "kv_note": kv_note}



def record(cfg: dict[str, Any], hardware: dict[str, Any], models: list[str], budget_gb: float) -> list[dict[str, Any]]:
    """Measure each model with the OS's ONE cold-prefill instrument and APPEND a receipt row per reading.

    It shells `scripts/measure_prefill.py` (C21: one instrument, composed) so a receipt carries the server's own
    counters, and it refuses to write a row whose reading is not a sample (generation below the declared floor).
    """
    import subprocess as sp  # noqa: PLC0415

    bench = cfg["record"]
    out_path = ROOT / str(cfg["receipts"])
    written: list[dict[str, Any]] = []
    models_root = Path(os.path.expanduser(str(cfg["detect"]["paths"]["models_root"])))
    for name in models:
        cmd = [sys.executable, str(ROOT / "scripts" / "measure_prefill.py"), "--model", name,
               "--tokens", str(bench["prompt_tokens"]), "--max-tokens", str(bench["max_tokens"]), "--json"]
        proc = sp.run(cmd, capture_output=True, text=True, timeout=int(bench["timeout_s"]), check=False)
        if proc.returncode != 0:
            print(f"  SKIP {name}: instrument exit {proc.returncode} {proc.stderr.strip()[:120]}", file=sys.stderr)
            continue
        measured = json.loads(proc.stdout)
        counters = measured.get("counters") or {}
        generated = int(bench["max_tokens"])
        decode = counters.get("generation_tokens_per_second")
        if decode is None or generated < int(cfg["receipts_min_decode_tokens"]):
            print(f"  SKIP {name}: reading is not a sample ({generated} tokens)", file=sys.stderr)
            continue
        if (measured.get("cached_tokens") or 0) > 0:
            print(f"  SKIP {name}: cached_tokens>0 — that is a cache rate, not a prefill (BUG-1044)", file=sys.stderr)
            continue
        nbytes = model_bytes(models_root, name)
        row = {
            "schema_version": 1,
            "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "instrument": "scripts/measure_prefill.py",
            "hardware": {"chip": hardware["chip"], "ram_gb": hardware["ram_gb"],
                         "bf16_native": hardware["bf16_native"]},
            "engine": {"name": "omlx", "version": hardware["engine_version"]},
            "memory_budget_gb": budget_gb,
            "model": name,
            "bytes": nbytes,
            "prompt_tokens": measured.get("prompt_tokens"),
            "prefill_tps": counters.get("prompt_tokens_per_second"),
            "decode_tps": decode,
            "generation_tokens": generated,
            "cached_tokens": measured.get("cached_tokens"),
            "note": "cold prompt (declared nonce), server counters, max_tokens=" + str(generated),
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())  # C6: a receipt that is not durable did not happen
        written.append(row)
        print(f"  RECORDED {name}: prefill {row['prefill_tps']} t/s decode {row['decode_tps']} t/s", file=sys.stderr)
    return written


def write_atomic(path: Path, text: str) -> None:
    """Write a file so a reader never sees a partial one: tempfile -> fsync -> os.replace (C6).

    Args:
        path: destination; its parent must exist.
        text: the complete content. Written as UTF-8 with newlines preserved.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False)
    try:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def ungated_faults(cfg: dict[str, Any]) -> list[str]:
    """Roles that declare NO gate and record NO acceptance for that absence (D-3189 limb c).

    A bare `require_gate: null` used to be indistinguishable from a deliberate choice: four of six roles
    carried it, so "the best planner" collapsed to "the fastest model that declares plan" (BUG-1055). The
    absence is allowed, but it must be a DECLARATION with a referent - a date and what stands in for the
    gate - and a missing one is reported as a FAULT rather than passing as convention.
    """
    faults: list[str] = []
    for role, spec in cfg["roles"].items():
        if spec.get("require_gate"):
            continue
        accepted = spec.get("ungated_accepted") or {}
        if not (accepted.get("date") and accepted.get("reason")):
            faults.append(str(role))
    return faults


def render(cfg: dict[str, Any], hardware: dict[str, Any], budget_gb: float, budget_src: str,
           bandwidth: float | None, table: list[dict[str, Any]],
           roles: dict[str, dict[str, Any]], ceiling: dict[str, Any] | None = None,
           kv: dict[str, Any] | None = None) -> str:
    """Human report: facts, then candidates, then the assignment with its reason."""
    lines = ["HARDWARE (layer 1 — read, not claimed)"]
    for key in ("chip", "ram_gb", "perf_cores", "wired_limit_gb", "bf16_native", "os", "engine_version", "disk_free_gb"):
        lines.append(f"  {key:<16} {hardware.get(key)}")
    reserve = (kv or {}).get("reserve") or kv_reserve(cfg)
    usable_gb = usable_gb_for(cfg, budget_gb, reserve)
    mem = cfg["memory"]
    lines.append(f"  memory budget    {budget_gb} GiB ({budget_src}); usable after gates {usable_gb} GiB "
                 f"(= {budget_gb} x {mem['max_resident_fraction']} - {reserve['gb']} GiB KV reserve, "
                 f"{reserve['kind'].lower()} from {reserve['source']})")
    # BUG-1060: the ceiling is a READING. Its clock, a second sample and the observed range travel with it, so a
    # figure that moved 12 GiB within an hour cannot be printed as a property. The line is only added when the
    # caller passed a reading — a report that was handed no reading must not invent one.
    if ceiling is not None:
        lines.append(f"  ceiling          {ceiling_text(ceiling)}")
        if ceiling.get("planning_gb") is not None and float(ceiling["planning_gb"]) != float(ceiling["gb"]):
            lines.append(f"  planning on      {ceiling['planning_gb']} GiB — the LOWEST ceiling observed, not the "
                         f"current reading: an assignment that only holds at the top of a moving range would "
                         f"rewrite itself when another app holds RAM (BUG-1060)")
    lines.append("")
    lines.append("CANDIDATES")
    lines.append(f"  {'model':<42}{'GB':>7}{'fits':>6}{'gates':>19}{'decode':>9}{'prefill':>9}  source")
    for row in table:
        # ONE COLUMN PER GATE (BUG-1063 limb 1): a single pass/FAIL column hid WHICH gate was applied.
        gate = " ".join(f"{gid}={('pass' if v is True else ('FAIL' if v is False else '-'))}"
                        for gid, v in sorted(row["gates"].items())) or "-"
        lines.append(f"  {row['model']:<42}{row['gb'] if row['gb'] is not None else '-':>7}"
                     f"{('yes' if row['fits'] else 'NO'):>5} {gate:>18}"
                     f"{row['decode_tps'] if row['decode_tps'] is not None else '-':>9}"
                     f"{row['prefill_tps'] if row['prefill_tps'] is not None else '-':>9}  "
                     f"{row['source']} (n={row['n_readings']}) roles={','.join(row['roles']) or 'none'}")
        pred = row.get("prediction")
        if pred and row["source"] == "UNMEASURED":
            lines.append(f"  {'':<42}{'':>7}{'':>6}{'':>19}{pred['predicted_tps']:>9}{'-':>9}  PREDICTED "
                         f"(roofline {pred['roofline_tps']} at {pred['bandwidth_gbs']} GB/s)")
    lines.append("")
    lines.append(f"ROLE ASSIGNMENT (layer 3 — receipts only; bandwidth {bandwidth} GB/s)")
    for role, pick in roles.items():
        if pick.get("model"):
            lines.append(f"  {role:<10} {pick['model']:<42} {pick['objective']}={pick['value']} "
                         f"[{pick['source']} n={pick.get('n_readings')}] {pick.get('status')} gate={pick['gate']}")
        else:
            lines.append(f"  {role:<10} {'UNCALIBRATED':<42} {pick['why']}")
            spec = cfg["roles"].get(role) or {}
            gate = spec.get("require_gate")
            if gate:
                # An uncalibrated GATED role must hand over the exact command that produces its evidence: a
                # fail-closed refusal with no remedy is a dead end disguised as a verdict (D-3100).
                suite = str(((cfg.get("gates") or {}).get(str(gate)) or {}).get("suite") or gate)
                declaring = [str(r["model"]) for r in table if role in r["roles"]]
                lines.append(f"  {'':<10} {'':<42} to produce the evidence ({gate}): python3 "
                             f"tools/model_eval_suite.py --suites {suite} --models "
                             f"{' '.join(declaring) or '<candidate>'}")
    lines.append("")
    faults = ungated_faults(cfg)
    if faults:
        lines.append(f"UNGATED    FAULT: role(s) {', '.join(faults)} declare require_gate: null and no "
                     f"ungated_accepted {{date, reason}} - an ungated role with no stated substitute is a "
                     f"declaration with no referent (D-3189 limb c)")
    else:
        accepted = [r for r, spec in cfg["roles"].items() if not spec.get("require_gate")]
        lines.append(f"UNGATED    {len(accepted)} role(s) accepted-not-measured ({', '.join(accepted)}), each "
                     f"naming what stands in for the gate (D-3189 limb c)")
    res = residency(roles, table, usable_gb, mem, declared_min_ctx(cfg), kv)
    lines.append(f"RESIDENCY  {res['total_gb']} GiB of {res['usable_gb']} usable — {res['note']}")
    if ceiling is not None:
        # TWO QUANTITIES, TWO LINES (BUG-1060 limb 2): the sum is a WEIGHTS-ONLY arithmetic over the portfolio;
        # the engine figure is everything actually resident. Printing one beside the other is what makes a
        # weights-only "fits" claim falsifiable in the same breath.
        lines.append(f"MEASURED   {measured_text(ceiling, res['total_gb'], len(res['models']))}")
    if res.get("kv_note"):
        lines.append(f"KV         {res['kv_note']}")
    return "\n".join(lines)


def selftest() -> int:
    """Offline known-answer controls: the roofline arithmetic and the fail-closed rule."""
    cfg = _cfg()
    hardware = {"chip": "selftest"}
    pred = predict_decode(hardware, cfg, int(15.4e9), 1.0, 400.0)
    assert pred is not None
    expected = round(400.0 * 1e9 / 15.4e9, 1)
    assert pred["roofline_tps"] == expected, f"roofline must be bandwidth/bytes: {pred} != {expected}"
    want = expected * float(cfg["predict"]["decode_efficiency"])
    assert abs(pred["predicted_tps"] - want) < 0.05, f"efficiency must be applied to the ceiling: {pred} vs {want}"
    # fail-closed: with no receipts at all, EVERY role must be UNCALIBRATED
    roles, _ = resolve(cfg, hardware, 55.0, 400.0, [], {}, allow_predicted=False)
    assert all(r.get("model") is None for r in roles.values()), "no receipt must mean no assignment"
    # CONTROL (D-3189 limb c): a bare null gate with no recorded acceptance is a FAULT; a declared
    # acceptance clears it. Both directions, because a control that cannot fire proves nothing.
    bare = {"roles": {"x": {"objective": "decode_tps", "require_gate": None, "min_ctx": 1}}}
    assert ungated_faults(bare) == ["x"], "a role with no gate and no acceptance must be reported"
    accepted = {"roles": {"x": {"require_gate": None,
                                "ungated_accepted": {"date": "2026-10-27", "reason": "r"}}}}
    assert ungated_faults(accepted) == [], "a declared acceptance must clear the fault"
    # CONTROL (BUG-1063 limb 1): a row belonging to ONE gate never resolves ANOTHER gate, whichever way
    # the receipt is declared - the row carries its gate, and rows without the field fall back to the
    # receipt's DECLARED identity, never to a guess from the filename.
    with tempfile.TemporaryDirectory() as tmp:
        receipt = Path(tmp) / "rows.jsonl"
        receipt.write_text(json.dumps({"model": "m", "gate": "plan_quality", "pass": True,
                                       "ts": "2026-10-27T00:00:00"}) + "\n", encoding="utf-8")
        as_r5 = {"gates": {"r5_review": {"receipt": str(receipt), "row_gate_default": "r5_review"}}}
        as_pq = {"gates": {"plan_quality": {"receipt": str(receipt),
                                           "row_gate_default": "plan_quality"}}}
        assert gates(as_r5).get("r5_review") == {}, "a plan_quality row satisfied the r5_review gate"
        assert gates(as_pq).get("plan_quality", {}).get("m", {}).get("pass") is True, \
            "a plan_quality row must resolve its OWN gate"
        legacy = Path(tmp) / "legacy.jsonl"
        legacy.write_text(json.dumps({"model": "m", "pass": True}) + "\n", encoding="utf-8")
        as_legacy = {"gates": {"r5_review": {"receipt": str(legacy), "row_gate_default": "r5_review"}}}
        assert gates(as_legacy)["r5_review"]["m"]["pass"] is True, \
            "a row written before gate identity existed must resolve via the DECLARED default"
    # CONTROL (BUG-1063 limb 2): a prediction prunes, it never confers ELIGIBILITY - with every candidate
    # declaring no role, the predicted pool must stay empty instead of seating a roleless model.
    roleless = {"roles": cfg["roles"], "candidates": [dict(c, roles=[]) for c in cfg["candidates"]],
                "memory": cfg["memory"], "detect": cfg["detect"], "predict": cfg["predict"],
                "receipts_min_decode_tokens": cfg["receipts_min_decode_tokens"],
                "min_readings_per_candidate": cfg["min_readings_per_candidate"]}
    roles_p, _ = resolve(roleless, hardware, 55.0, 400.0, [], {}, allow_predicted=True)
    assert all(r.get("model") is None for r in roles_p.values()), \
        "a model that declares NO role must never be seated by a roofline prediction"
    # CONTROL (BUG-1060): a DYNAMIC ceiling may never be printed as a property. Two directions, because a
    # formatter that always adds a caveat is as uninformative as one that never does.
    moving = ceiling_text({"gb": 61.3, "at": "2026-10-27T14:20:00", "gb_second": 49.2,
                           "range_gb": (49.2, 61.3), "n_readings": 12, "receipt": "x.jsonl"})
    assert "read at 2026-10-27T14:20:00" in moving, "a ceiling figure must carry its reading clock"
    assert "MOVES" in moving and "observed range 49.2-61.3" in moving, \
        "a ceiling that moved between two samples must SAY so and quote the measured range"
    steady = ceiling_text({"gb": 61.3, "at": "2026-10-27T14:20:00", "gb_second": 61.3,
                           "range_gb": (61.3, 61.3), "n_readings": 3, "receipt": "x.jsonl"})
    assert "MOVES" not in steady, "a stable ceiling must not be dressed in a movement caveat"
    assert "read at" in steady, "even a stable reading carries its clock"
    # CONTROL (BUG-1060 limb 2): measured resident and the weights-only sum are TWO quantities and the face
    # must never present the weights-only sum as the resident footprint.
    assert min([48.8, 53.8, 56.7]) == 48.8, "the planning bound must be the LOWEST observed ceiling"
    face = measured_text({"resident_gb": 43.9, "at": "2026-10-27T14:20:00", "loaded": ["a", "b"]}, 40.0, 2)
    assert "43.9 GiB resident" in face and "2/2 of the assigned portfolio" in face and "WEIGHTS only" in face, face
    subset = measured_text({"resident_gb": 19.9, "at": "2026-10-27T14:31:00", "loaded": ["a", "b"]}, 43.7, 6)
    assert "2/6" in subset, "a partially loaded portfolio must never be printed as the whole set"
    assert "NOT READ" in measured_text({"resident_gb": None}, 40.0), \
        "an unread resident figure must be reported as NOT READ, never assumed equal to the sum"
    # CONTROL (BUG-1071, D-3196): the KV reserve is DERIVED from a pointer that is WALKED. Three directions,
    # because a resolver that always falls back and one that always resolves are equally blind: a pointer whose
    # every segment exists must resolve to the DECLARED value; a pointer naming a key that does not exist must
    # fall back AND name the segment that failed; and a config with neither pointer nor context basis must still
    # say NOT MODELLED rather than borrow the new text.
    assert parse_size_gb("8GB") == 8.0 and parse_size_gb("512MB") == 0.5, "a size token must parse"
    assert parse_size_gb("auto") is None and parse_size_gb(None) is None, \
        "`auto` is a real engine value and must never parse as a 0.0 reserve"
    real_order = kv_reserve(cfg)
    assert real_order["kind"] in ("DERIVED", "FALLBACK"), real_order
    if real_order["kind"] == "DERIVED":
        assert "hot_cache_max_size" in real_order["source"] and real_order["gb"] > 0, \
            f"a DERIVED reserve must name its pointer and carry a positive size: {real_order}"
    broken = dict(cfg, memory=dict(cfg["memory"], kv_headroom_source="engine.settings.cache.NO_SUCH_KEY"))
    assert kv_reserve(broken)["kind"] == "FALLBACK", "a pointer naming a missing key must not resolve"
    assert "NO_SUCH_KEY" in kv_reserve(broken)["why"], \
        "a fallback must name the segment that failed to resolve, not merely report a number"
    unsourced = kv_text({"gb": 3.0, "kind": "FALLBACK", "source": "memory.kv_headroom_gb",
                         "why": "the pointer stops resolving at 'engine.settings.cache'", "raw": None},
                        {"n_clean": 2, "max_tokens": 32813, "kv_gib_at_max": 0.29,
                         "kib_per_token": 9.33, "receipt": "r.jsonl"},
                        131072, ["analyze", "plan"], "r.jsonl")
    assert "FALLBACK RAN" in unsourced and "0.29 GiB" in unsourced, \
        "a fallback reserve must say it fell back AND still print what was measured"
    legacy_cfg_mem = {"kv_headroom_gb": 3.0, "max_resident_fraction": 0.8}
    legacy_roles = {"plan": {"model": "m", "objective": "x", "value": 1}}
    legacy_res = residency(legacy_roles, [{"model": "m", "gb": 1.0}], 30.0, legacy_cfg_mem,
                           {"plan": {"m": 131072}})
    assert "NOT MODELLED" in (legacy_res["kv_note"] or ""), \
        "a config with neither a pointer nor a basis must still declare the term unmodelled"
    print("ok hardware-calibrate --selftest: 13/13 controls green (roofline arithmetic, efficiency applied, "
          "no receipt => no assignment, bare-null gate is a fault, a declared acceptance clears it, a gate "
          "row never resolves another gate, a legacy row resolves its DECLARED default, a prediction never "
          "confers eligibility, a moving ceiling prints its clock and range, a stable one is not dressed in a "
          "movement caveat, measured resident is printed as its own quantity and a subset prints as n/N, a size "
          "token parses while `auto` never becomes 0.0, a KV pointer resolves its DERIVED value or falls back "
          "NAMING the segment that failed, and a config with neither pointer nor basis still says NOT MODELLED)")
    return OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Personal calibration: detect, predict, and assign roles from receipts")
    ap.add_argument("--json", action="store_true", help="emit the machine-readable report")
    ap.add_argument("--write", action="store_true", help="write config/model_roles.yaml")
    ap.add_argument("--bandwidth", action="store_true", help="re-measure streaming bandwidth (needs MLX)")
    ap.add_argument("--allow-predicted", action="store_true",
                    help="let a roofline PREDICTION fill an unmeasured role (never the default: D-3036)")
    ap.add_argument("--record", nargs="*", metavar="MODEL",
                    help="measure these models (default: every candidate that fits) and append receipts")
    ap.add_argument("--selftest", action="store_true", help="offline known-answer controls")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    cfg = _cfg()
    hardware = detect(cfg)
    ceiling = ceiling_reading(cfg, hardware)
    # PLAN ON THE LOW END. A role assignment that holds only at the top of a moving range is an assignment that
    # silently rewrites itself when another application holds RAM, so the resolver is given the LOWEST ceiling
    # this receipt has observed and the face prints the current reading beside it (BUG-1060 limb 3).
    budget_gb, budget_src = float(ceiling.get("planning_gb") or ceiling["gb"]), str(ceiling["source"])
    bandwidth = measure_bandwidth(cfg) if args.bandwidth else None
    if args.record is not None:
        wanted = args.record or [str(c["model"]) for c in cfg["candidates"]]
        fits = [m for m in wanted if (model_bytes(Path(os.path.expanduser(
            str(cfg["detect"]["paths"]["models_root"]))), m) or 0) / 2**30 <= budget_gb]
        print(f"recording {len(fits)} model(s) into {cfg['receipts']}", file=sys.stderr)
        record(cfg, hardware, fits, budget_gb)
    rows = receipts(cfg, hardware)
    gate_rows = gates(cfg)
    roles, table = resolve(cfg, hardware, budget_gb, bandwidth, rows, gate_rows, args.allow_predicted)
    # ONE RESOLUTION OF THE KV TERM, SHARED BY BOTH FACES (BUG-1071): the JSON and the human report must not be
    # able to disagree about which reserve ran, for the same reason BUG-1062 existed.
    probe = (cfg.get("memory") or {}).get("kv_probe") or {}
    kv = {"reserve": kv_reserve(cfg), "measured": kv_measured(cfg),
          "receipt": str(probe.get("receipt") or "governance/kv_working_set.jsonl")}
    usable_gb = usable_gb_for(cfg, budget_gb, kv["reserve"])
    report = {"hardware": hardware, "memory": {"budget_gb": budget_gb, "source": budget_src,
                                              "ceiling_reading": ceiling,
                                              "usable_gb": round(usable_gb, 1),
                                              "kv_reserve": kv["reserve"], "kv_measured": kv["measured"]},
              "bandwidth_gbs": bandwidth, "candidates": table, "roles": roles,
              "residency": {**residency(roles, table, usable_gb, cfg["memory"], declared_min_ctx(cfg), kv),
                            "measured": ceiling.get("resident_gb"),
                            "measured_at": ceiling.get("at"),
                            "measured_loaded": ceiling.get("loaded")},
              "ungated_faults": ungated_faults(cfg),
              "receipts_used": len(rows)}
    if args.write:
        out = ROOT / str(cfg["out"])
        # C6 CRASH-SAFE, and the reason it is not a plain write_text (raised by the R5 reviewer on
        # 2026-10-27, verdict REJECT, concern: "writes to external files ... but does not verify that the writes
        # succeeded"): a reader of config/model_roles.yaml must never see a half-written assignment, and a
        # truncated JSON file is indistinguishable from a deliberate one. tempfile -> fsync -> os.replace is the
        # repo's declared pattern, and reading the result BACK is what makes "written" a claim rather than a hope.
        text = ("# GENERATED by scripts/hardware_calibrate.py — do not hand-edit (D-3178)\n"
                + json.dumps({"hardware": hardware, "roles": roles}, indent=2) + "\n")
        write_atomic(out, text)
        if out.read_text(encoding="utf-8") != text:
            raise SystemExit("FAIL-CLOSED: " + str(out) + " does not read back as written - refusing to report it")
        report["written"] = str(out)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json
          else render(cfg, hardware, budget_gb, budget_src, bandwidth, table, roles, ceiling, kv))
    return OK if all(r.get("model") for r in roles.values()) else UNCALIBRATED


if __name__ == "__main__":
    sys.exit(main())
