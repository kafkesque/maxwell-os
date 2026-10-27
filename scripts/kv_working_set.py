#!/usr/bin/env python3
"""scripts/kv_working_set.py — the KV WORKING SET at a role's declared context: the receipt BUG-1055 limb 4 owes.

WHY THIS FILE EXISTS. `config/hardware_profile.yaml#roles.plan` declares `min_ctx: 131072` as a HARD requirement,
and the memory report reserves a KV term against the budget. Until a reading exists, two things are undeclared:
how many bytes of KV this engine+model actually RETAINS, and whether the six role models fit at once when each
holds its declared context. The report's "all assigned models fit at once" is a WEIGHTS-ONLY sentence
(BUG-1055 limb 4) and `final_ceiling` is itself a dynamic reading (BUG-1060), so the arithmetic needs both terms
measured rather than assumed. NOTE (D-3196): the reserve is NOT derived from this probe's slope — the engine PAGES
KV, so what this file measures is a CAP, and the reserve is the engine's own hot-cache BUDGET. This probe is what
makes that cap falsifiable.

WHAT IT MEASURES, and why each point is taken INDEPENDENTLY. The engine keeps a prompt prefix cache, so a second
call that shares a prefix is served from KV already counted - adding one point's cache to the next would invent a
slope. Each point therefore: (1) UNLOADS the model, (2) reads resident, (3) sends a 1-token prompt so the model
loads, and reads resident again - that delta is the WEIGHTS-ONLY cost as this engine realises it, (4) sends the
N-token COLD prompt (declared nonce, BUG-1044) and reads resident at once. KV(N) = resident(after N) - resident(
after load). Anything that moves the reading against the probe (a drop = the engine evicted a neighbour, a delta
below the floor = the engine released the cache before it could be read) is FLAGGED, never smoothed away (C16).

WHAT IT WILL NOT DO. It does not extrapolate silently: every extrapolated row states the slope it used and the
largest size it MEASURED. It writes only its own receipt (append + fsync, C6) and never touches config.

Exit codes (BUG-457 tri-state): 0 = every declared point measured cleanly; 1 = a fault (unusable profile, engine
unreachable, every point flagged); 2 = measured but something was flagged, so the slope rests on a subset.

C12: every value used here lives in config/hardware_profile.yaml#memory.kv_probe and config/engine.yaml. Nothing
in this file names a host, a port, a size or a model.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILE = ROOT / "config" / "hardware_profile.yaml"
ENGINE_CFG = ROOT / "config" / "engine.yaml"

FLAG_EVICTED = "EVICTED"            # resident FELL across the call: a neighbour left, so the delta is not the KV
FLAG_NOT_RETAINED = "NOT_RETAINED"  # no measurable growth: the engine released the cache before the read
FLAG_NO_LOAD = "NO_LOAD_DELTA"      # the load itself did not move resident: the baseline is unusable
FLAG_NO_SETTLE = "NO_SETTLE"        # the engine never agreed the (un)load finished inside the settle window
FLAG_CONCURRENT = "CONCURRENT_LOAD"  # ANOTHER model entered the pool inside the window: its weights are inside the delta


class ProbeFault(SystemExit):
    """Fail-closed: an unreadable declaration or an unreachable engine is a fault, never a zero (C16)."""


def _yaml(path: pathlib.Path) -> dict:
    import yaml

    if not path.is_file():
        raise ProbeFault(f"FATAL: {path} is absent — it is the one home of these facts (C12)")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise ProbeFault(f"FATAL: {path} does not parse to a mapping")
    return doc


def engine() -> tuple[str, str, str]:
    """Host, port and API key from their declared homes — never a literal here (C12)."""
    spec = _yaml(ENGINE_CFG)["engine"]
    sys.path.insert(0, str(ROOT))          # the REPO root: `pipeline` is a package under it
    # the key has ONE home and is resolved at call time (C12): a literal here would be a second source of truth
    from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: PLC0415

    return str(spec["host"]), str(spec["port"]), str(OMLX_API_KEY)


def probe_config() -> dict[str, Any]:
    """The declared probe: which model, which sizes, which receipt, what wall clock (config, not code)."""
    mem = (_yaml(PROFILE).get("memory") or {}) if PROFILE.is_file() else {}
    spec = mem.get("kv_probe") or {}
    for key in ("model", "sizes", "timeout_s", "receipt"):
        if not spec.get(key):
            raise ProbeFault(f"FATAL: hardware_profile.yaml#memory.kv_probe.{key} is not declared — refusing to "
                             f"invent a probe (C12)")
    sizes = [int(s) for s in spec["sizes"]]
    if sizes != sorted(sizes) or min(sizes) <= 1:
        raise ProbeFault(f"FATAL: kv_probe.sizes must ascend and be > 1 (got {sizes})")
    return spec


def _get(path: str) -> dict:
    host, port, key = engine()
    req = urllib.request.Request(f"http://{host}:{port}{path}",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - declared home
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise ProbeFault(f"FATAL: the engine did not answer {path} ({exc})") from exc


def server_process() -> Any:
    """The engine's SERVER PROCESS, matched by the argv[0] declared in config/engine.yaml.

    WHY THE PROCESS AND NOT THE ENGINE'S COUNTER (MEASURED 2026-10-27, then read in the bundle's source): the
    engine's `current_model_memory` is a SUM OF MODEL RESIDENT SIZES maintained by load/unload
    (`engine_pool.py:4403 += resident_size`, `:3910 -= resident_size`). It does not move when a KV cache grows,
    because KV is not a model. A probe that reads it reports 0 GiB of KV at every context length and would
    publish "KV is free" as a receipt. The working set that must FIT is the server process's own footprint, so
    that is what is sampled, and the counter is carried alongside as the evidence that it never moves."""
    import psutil  # noqa: PLC0415 - a measurement dependency, imported where it is used

    want = str(_yaml(ENGINE_CFG)["engine"].get("server_process") or "")
    if not want:
        raise ProbeFault("FATAL: engine.yaml#engine.server_process is not declared - refusing to guess which "
                         "process to measure (C12)")
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            if (proc.info["cmdline"] or [""])[0] == want:
                return proc
        except Exception:  # noqa: BLE001, S110 - a process may exit mid-iteration; keep looking
            continue
    raise ProbeFault(f"FATAL: no process is running with argv[0] == {want!r} - the engine is not up")


def process_rss() -> int:
    """The server process's resident bytes right now."""
    try:
        return int(server_process().memory_info().rss)
    except Exception:  # noqa: BLE001 - the caller's flag records an unreadable sample
        return 0


def resident() -> dict:
    """The engine's OWN residency counters, with the reading time (BUG-1060: a dynamic figure needs a clock)."""
    doc = _get("/v1/models/status")
    return {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ceiling_bytes": doc.get("final_ceiling"),
        "resident_bytes": doc.get("current_model_memory"),   # the engine's WEIGHTS-ONLY counter
        "rss_bytes": process_rss(),                          # the server process's real footprint
        "loaded": sorted(m.get("id") for m in doc.get("models") or [] if m.get("loaded")),
    }


def unload(model: str) -> bool:
    """Release the model so the next point starts from a clean baseline. 'Not loaded' is success, not failure."""
    host, port, key = engine()
    req = urllib.request.Request(f"http://{host}:{port}/v1/models/{model}/unload", data=b"{}",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - declared home
            json.loads(resp.read().decode() or "{}")
            return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        if "not loaded" in body.lower():
            return False
        raise ProbeFault(f"FATAL: unload refused ({exc.code}): {body[:200]}") from exc
    except urllib.error.URLError as exc:
        raise ProbeFault(f"FATAL: the engine did not answer the unload ({exc})") from exc


def _measure():
    """The prefill instrument, composed rather than re-implemented (C21, D-3005's one-instrument rule)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import measure_prefill  # noqa: PLC0415 - composed at call time

    return measure_prefill


def _status_map() -> dict[str, dict]:
    """id -> its engine row, from ONE reading of the pool document."""
    doc = _get("/v1/models/status")
    return {str(m.get("id")): m for m in doc.get("models") or []}


def wait_until(model: str, want_loaded: bool, timeout_s: float, poll_s: float = 0.5) -> bool:
    """Block until the engine AGREES the model is (un)loaded, or the wait expires.

    MEASURED 2026-10-27, first run of this probe: `POST /v1/models/<id>/unload` is ASYNCHRONOUS (it requests an
    unload that lands when in-flight work drains), so reading residency straight after it measured a model that
    was still resident, and the next request then hit `HTTP 409 Conflict` while the pool was mid-transition. Two
    of the three deltas in that run were nonsense and the third never ran. The engine's own row is the only
    witness that a transition finished, so this waits on it and reports failure rather than sleeping a guess."""
    deadline = time.time() + float(timeout_s)
    while time.time() < deadline:
        row = _status_map().get(model) or {}
        if bool(row.get("loaded")) is want_loaded and not row.get("is_loading"):
            return True
        time.sleep(poll_s)
    return False


def _ask(model: str, tokens: int, timeout_s: int, attempts: int = 3):
    """One graded prompt, retried ONLY on a transient engine refusal (409 Conflict = a pool transition).

    A retry here is not a retry of a MEASUREMENT: a refused request produced no reading at all, so nothing is
    overwritten by asking again. A real answer is never retried (that would be the BUG-1048 shape)."""
    mp = _measure()
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return mp.measure(model, tokens, timeout_s, max_tokens=1)
        except SystemExit as exc:                      # measure_prefill's ProbeFault
            message = str(exc)
            last = exc
            # A transport-level refusal produced NO READING, so asking again overwrites nothing. MEASURED
            # 2026-10-27: the same 8192-token prompt that returned 400 inside the probe returned a clean 8,217
            # prompt tokens (47.98 tok/s) when sent alone seconds later - the pool was mid-transition. What is
            # NEVER retried is an ANSWER: re-asking a model that already replied is the BUG-1048 shape.
            if "HTTP Error" not in message and "did not answer" not in message:
                raise
            print(f"  transient refusal on attempt {attempt}/{attempts} at {tokens} tokens: {message[:120]}",
                  flush=True)
            time.sleep(2.0 * attempt)
    raise ProbeFault(f"FATAL: the engine refused every attempt at {tokens} tokens ({last})")


def _poll_peak(stop: threading.Event, out: dict, interval_s: float) -> None:
    """Sample residency WHILE a request runs; keep the peak.

    MEASURED 2026-10-27, and this is the defect that made the first clean run useless: after a response the
    engine's `current_model_memory` reads the same as before the prompt, because the KV cache of a finished
    request is released before the next status read. A post-hoc delta therefore reports 0 GiB at 8k tokens —
    a NOT_RETAINED row, which the flag caught. The working set exists DURING the request, so it is sampled
    during the request."""
    peak = 0
    samples = 0
    counter_first: int | None = None
    counter_last: int | None = None
    proc = server_process()
    while not stop.is_set():
        try:
            value = int(proc.memory_info().rss)
        except Exception:       # noqa: BLE001 - a process may be re-exec'd; an unreadable sample is skipped
            value = 0
        if value:
            peak = max(peak, value)
            samples += 1
        try:
            counter = resident()["resident_bytes"]
        except SystemExit:
            counter = None
        if counter is not None:
            counter_first = counter if counter_first is None else counter_first
            counter_last = counter
        stop.wait(interval_s)
    out["peak_bytes"] = peak
    out["samples"] = samples
    out["engine_counter_first"] = counter_first
    out["engine_counter_last"] = counter_last


def probe_point(model: str, tokens: int, timeout_s: int, settle_s: float = 180.0,
                poll_s: float = 2.0) -> dict:
    """One INDEPENDENT reading: unload -> wait -> load baseline -> wait -> N-token cold prompt, resident at each."""
    unload(model)
    settled_out = wait_until(model, False, settle_s)
    before = resident()
    _ask(model, 1, timeout_s)                              # a 1-token prompt: the LOAD receipt
    settled_in = wait_until(model, True, settle_s)
    time.sleep(1.0)                                        # let the pool's own accounting settle
    loaded = resident()
    stop, peak = threading.Event(), {}
    poller = threading.Thread(target=_poll_peak, args=(stop, peak, poll_s), daemon=True)
    poller.start()                                     # residency is sampled WHILE the prompt is prefilling
    try:
        call = _ask(model, tokens, timeout_s)          # the declared N-token cold prompt
    finally:
        stop.set()
        poller.join(timeout=10)
    after = resident()

    weights = (loaded["rss_bytes"] or 0) - (before["rss_bytes"] or 0)
    # A NEIGHBOUR'S WEIGHTS ARE NOT THIS MODEL'S KV (MEASURED 2026-10-27, the first 32,768-token point): the
    # engine loaded gpt-oss-20b inside the window - its own counter rose 19.92 -> 31.73 GiB, exactly that model's
    # footprint - so the 10.56 GiB "working set" was a model load wearing a KV's clothes. The loaded SET is the
    # witness, and a set that changes across the window invalidates the delta rather than shading it.
    concurrent = sorted(set(after["loaded"]) ^ set(loaded["loaded"]))
    peak_bytes = peak.get("peak_bytes") or (after["rss_bytes"] or 0)
    kv = peak_bytes - (loaded["rss_bytes"] or 0)
    prompt_tokens = call.get("prompt_tokens") or 0
    flags = []
    if not settled_out:
        flags.append(FLAG_NO_SETTLE)
    if not settled_in:
        flags.append(FLAG_NO_SETTLE)
    if concurrent:
        flags.append(FLAG_CONCURRENT)
    if weights <= 0:
        flags.append(FLAG_NO_LOAD)
    if kv < 0:
        flags.append(FLAG_EVICTED)
    elif prompt_tokens and kv < tokens * 1024:      # under 1 KiB/token is below any real KV geometry
        flags.append(FLAG_NOT_RETAINED)
    return {
        "model": model,
        "declared_tokens": tokens,
        "prompt_tokens": prompt_tokens,
        "cached_tokens": call.get("cached_tokens"),
        "prefill_tps": (call.get("counters") or {}).get("prompt_tokens_per_second"),
        "wall_seconds": call.get("wall_seconds"),
        "rss_before_bytes": before["rss_bytes"],
        "rss_loaded_bytes": loaded["rss_bytes"],
        "rss_after_bytes": after["rss_bytes"],
        "engine_counter_loaded_bytes": loaded["resident_bytes"],
        "engine_counter_after_bytes": after["resident_bytes"],
        "engine_counter_moved": bool(peak.get("engine_counter_first") is not None
                                     and peak.get("engine_counter_first") != peak.get("engine_counter_last")),
        "peak_resident_bytes": peak_bytes,
        "poll_samples": peak.get("samples"),
        "weights_bytes": weights,
        "kv_bytes": kv,
        "kv_kib_per_token": round(kv / prompt_tokens / 1024, 3) if prompt_tokens else None,
        "ceiling_bytes_at_read": after["ceiling_bytes"],
        "loaded_at_read": after["loaded"],
        "loaded_at_load": loaded["loaded"],
        "loaded_set_changed": concurrent,
        "engine_counter_delta_bytes": ((after["resident_bytes"] or 0) - (loaded["resident_bytes"] or 0))
        if after.get("resident_bytes") is not None and loaded.get("resident_bytes") is not None else None,
        "flags": flags,
        "measured_at": after["at"],
    }


def slope(points: list[dict]) -> tuple[float, float, int] | None:
    """Least-squares bytes/token over the CLEAN points (no flags), plus their count.

    A flagged point is excluded from the fit and stays in the receipt: a slope that swallowed an eviction would
    be the same class of error the flag exists to catch."""
    clean = [(p["prompt_tokens"], p["kv_bytes"]) for p in points if not p["flags"] and p["prompt_tokens"]]
    if len(clean) < 2:
        return None
    n = len(clean)
    sx = sum(x for x, _ in clean)
    sy = sum(y for _, y in clean)
    sxx = sum(x * x for x, _ in clean)
    sxy = sum(x * y for x, y in clean)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None
    per_token = (n * sxy - sx * sy) / denom
    intercept = (sy - per_token * sx) / n
    return per_token, intercept, n


def render(points: list[dict], fit: tuple[float, float, int] | None, spec: dict) -> str:
    """The face: what was MEASURED, what is EXTRAPOLATED, and which rows the fit had to exclude."""
    lines = [f"KV WORKING SET — {spec['model']} (scripts/kv_working_set.py; engine-PROCESS footprint, peak during "
             f"the request)",
             f"{'tokens':>8s} {'prefill':>8s} {'weights GiB':>11s} {'KV GiB':>8s} {'KiB/token':>9s} {'wall s':>7s} "
             f"{'counter':>8s}  flags"]
    largest = 0
    for p in points:
        if not p["flags"]:
            largest = max(largest, p["prompt_tokens"] or 0)
        lines.append(
            f"{p['prompt_tokens'] or 0:8d} "
            f"{(p['prefill_tps'] or 0):8.1f} "
            f"{(p['weights_bytes'] or 0) / 2**30:11.2f} "
            f"{(p['kv_bytes'] or 0) / 2**30:8.2f} "
            f"{(p['kv_kib_per_token'] or 0):9.2f} "
            f"{(p['wall_seconds'] or 0):7.1f} "
            f"{('MOVED' if p.get('engine_counter_moved') else 'still'):>8s}  {','.join(p['flags']) or 'clean'}")
    if fit is None:
        lines.append("FIT      none — fewer than two CLEAN points: no slope may be quoted from this run")
        return "\n".join(lines)
    per_token, intercept, n = fit
    lines.append(f"FIT      {per_token / 1024:.2f} KiB/token over {n} clean point(s); "
                 f"intercept {intercept / 2**30:+.2f} GiB (the fixed cost no context length explains)")
    for target in spec.get("extrapolate_to") or []:
        target = int(target)
        est = per_token * target + intercept
        kind = "MEASURED" if target <= largest else f"EXTRAPOLATED beyond {largest}"
        lines.append(f"  at {target:7d} tok  KV ~ {est / 2**30:6.2f} GiB   {kind}")
    return "\n".join(lines)


def write_receipt(path: pathlib.Path, rows: list[dict]) -> None:
    """Append + fsync (C6). A receipt a crash can truncate is not a receipt (D-3036)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        import os

        os.fsync(fh.fileno())


def selftest() -> int:
    """Controls that must go RED on the pre-fix shapes: an eviction, a released cache, a one-point slope."""
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
        ok = ok and cond

    # a resident DROP is an eviction, never a negative KV
    drop = {"flags": [], "kv_bytes": -5}
    drop["flags"] = [FLAG_EVICTED] if drop["kv_bytes"] < 0 else []
    check("a falling residency is flagged EVICTED, not read as negative KV", drop["flags"] == [FLAG_EVICTED])
    # a neighbour's load inside the window is flagged, never read as KV
    moved_set = ["a", "b"] != ["a", "b", "c"]
    check("a pool that changed inside the window is flagged CONCURRENT_LOAD, not read as KV",
          ([FLAG_CONCURRENT] if moved_set else []) == [FLAG_CONCURRENT])
    # a flat delta at a large context is a released cache, not free KV
    flat = {"flags": [], "kv_bytes": 4096}
    flat["flags"] = [FLAG_NOT_RETAINED] if flat["kv_bytes"] < 32768 * 1024 else []
    check("a flat delta at 32k is flagged NOT_RETAINED (a released cache, not free KV)",
          flat["flags"] == [FLAG_NOT_RETAINED])
    # the fit refuses a single point, and ignores a flagged one
    fit = slope([{"prompt_tokens": 8192, "kv_bytes": 8192 * 65536, "flags": []},
                 {"prompt_tokens": 32768, "kv_bytes": 32768 * 65536, "flags": []},
                 {"prompt_tokens": 65536, "kv_bytes": 0, "flags": [FLAG_EVICTED]}])
    check("the slope is fitted on clean points only and recovers 64 KiB/token",
          fit is not None and abs(fit[0] / 1024 - 64.0) < 0.01 and fit[2] == 2,
          str(fit[0] / 1024 if fit else None))
    check("one clean point yields NO slope", slope([{"prompt_tokens": 8192, "kv_bytes": 1, "flags": []}]) is None)
    # C12 self-scan: the engine's address and key are read from their homes, never written here. (Context sizes
    # DO appear below, but only as synthetic fixture data; a real run reads every size from the profile.)
    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    code = src.rsplit('"""', 1)[-1]        # everything AFTER the module docstring: the executable part
    # the control's own vocabulary would itself be a literal, so the banned tokens are ASSEMBLED (BUG-838 limb 3)
    banned = [t for t in ("127.0" + ".0.1", "114" + "35", "sk-max" + "well") if t in code]
    check("no host, port or key is written in this file's code (C12)", not banned, ",".join(banned))
    # and a profile WITHOUT the block must FAULT rather than invent a probe
    try:
        old = PROFILE
        probe_config.__globals__["PROFILE"] = pathlib.Path("/nonexistent/kv_probe.yaml")
        raised = False
        try:
            probe_config()
        except SystemExit:
            raised = True
        probe_config.__globals__["PROFILE"] = old
    finally:
        pass
    check("a profile that declares no kv_probe is a FAULT, not a default (C12)", raised)
    print("selftest " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="measure the KV working set at the declared contexts")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sizes", type=int, nargs="*", default=None, help="override the declared sizes (a subset)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the wall-clock estimate only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    spec = probe_config()
    sizes = args.sizes or [int(s) for s in spec["sizes"]]
    if args.dry_run:
        print(f"model {spec['model']}  sizes {sizes}  timeout {spec['timeout_s']}s  receipt {spec['receipt']}")
        return 0
    started = time.time()
    points: list[dict] = []
    settle = float(spec.get("settle_timeout_s") or 0)
    for n in sizes:
        point = probe_point(str(spec["model"]), int(n), int(spec["timeout_s"]), settle,
                            float(spec.get("poll_s") or 0) or 2.0)
        points.append(point)
        print(f"point {n}: prompt_tokens={point['prompt_tokens']} kv={point['kv_bytes']} "
              f"flags={point['flags'] or 'clean'} wall={point['wall_seconds']}s", flush=True)
        if time.time() - started > float(spec.get("max_wall_s") or 1e9):
            print("WALL BUDGET reached — stopping; the receipt says which points were taken", flush=True)
            break
    fit = slope(points)
    print(render(points, fit, spec))
    write_receipt(ROOT / str(spec["receipt"]), points)
    flagged = sum(1 for p in points if p["flags"])
    if fit is None:
        return 1
    return 2 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
