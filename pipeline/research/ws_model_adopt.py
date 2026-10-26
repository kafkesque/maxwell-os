#!/usr/bin/env python3
"""W4 - ADOPT A MODEL: fetch it, make the engine see it, prove it can serve, leave the pool as found.

A download is not adoption. Adoption is: bytes verified on disk, the engine's registry re-read
(scripts/omlx_reload.py - POST /admin/api/reload; the app caches its registry at start, D2637),
the model LOADED once (the only proof that it can serve), a spot decode measured, and then
UNLOADED again so the pool the owner was using is exactly the pool they get back.

Every step is timeout-bounded and printed as a STEP line, so pipeline/research_run.py can stop
waiting the moment this declares TERMINAL - and a hung download cannot hang the harness.

Usage: python3 pipeline/research/ws_model_adopt.py --repo REPO --report FILE [--json-out f] [--no-load]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
FETCH_S = 1800
RELOAD_S = 300
LOAD_S = 600
MEASURE_TOKENS = 64
PROMPT_WORDS = 24


def conf() -> dict:
    """Engine facts from their one home (C12)."""
    import yaml
    return yaml.safe_load((ROOT / "config" / "engine.yaml").read_text(encoding='utf-8'))["engine"]


def token() -> str:
    """The engine key from its one home."""
    sys.path.insert(0, str(ROOT))
    try:
        from pipeline.pipeline_paths import OMLX_API_KEY
        return str(OMLX_API_KEY)
    except Exception as exc:
        print(f"note: could not resolve the engine key ({type(exc).__name__}); calls go unauthenticated")
        return ""


def api(path: str, method: str = "GET", body: dict | None = None, timeout: int = 60) -> tuple[int, str]:
    """Call the local engine with curl (the transport that measurably works here)."""
    engine = conf()
    url = f"http://{engine['host']}:{engine['port']}{path}"
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, "-w", chr(10) + "%{http_code}",
           "-H", f"Authorization: Bearer {token()}", "-H", "Content-Type: application/json", url]
    if body is not None:
        cmd[5:5] = ["-d", json.dumps(body)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20)
    out, _, code = proc.stdout.rpartition(chr(10))
    try:
        return int(code.strip() or 0), out
    except ValueError:
        return 0, proc.stdout


def find_id(needle: str) -> str | None:
    """Find the engine's own id for a model, from /v1/models/status."""
    code, body = api("/v1/models/status")
    if code != 200:
        return None
    try:
        ids = [m.get("id") for m in json.loads(body).get("models", [])]
    except Exception:
        return None
    hits = [i for i in ids if i and (needle.lower() in i.lower() or i.lower() in needle.lower())]
    return hits[0] if hits else None


def main(argv: list[str]) -> int:
    """Run the adoption ladder and append the verdict to the run's report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--json-out")
    ap.add_argument("--no-load", action="store_true")
    args = ap.parse_args(argv)
    report = pathlib.Path(args.report)
    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)
        with open(report, "a", encoding='utf-8') as fh:
            fh.write(line.rstrip() + chr(10))
            fh.flush()

    result: dict = {"repo": args.repo}
    emit("")
    emit(f"## W4 adopt {args.repo}")
    emit("STEP 1: fetch (resumable, verified)")
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, str(ROOT / "pipeline" / "hf_fetch_model.py"), "--repo", args.repo],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    deadline = time.time() + FETCH_S
    for line in proc.stdout or []:
        emit("  " + line.rstrip())
        if time.time() > deadline:
            proc.kill()
            emit("TERMINAL: FAILED - the fetch exceeded its declared budget")
            return 1
    proc.wait()
    result["fetch_rc"] = proc.returncode
    if proc.returncode not in (0, 2):
        emit("TERMINAL: FAILED - the fetch did not complete (rc=" + str(proc.returncode) + ")")
        return 1
    emit("STEP 2: engine registry reload (the app caches it at start - D2637)")
    reloader = str(ROOT / "scripts" / "omlx_reload.py")
    if pathlib.Path(reloader).exists():
        rel = subprocess.run([sys.executable, reloader, "--json"], capture_output=True, text=True, timeout=RELOAD_S)
        result["reload_rc"] = rel.returncode
        emit(f"  reload rc={rel.returncode}; {len(rel.stdout)} bytes of registry")
    else:
        emit("  note: scripts/omlx_reload.py is absent - the engine will only re-read its registry at app start")
        result["reload_rc"] = None

    name = args.repo.split("/")[-1]
    mid = find_id(name)
    result["engine_id"] = mid
    if not mid:
        code, body = api("/v1/models/status")
        emit(f"STEP 3: the engine did not discover {name} (status http {code})")
        emit("  raw: " + body[:400].replace(chr(10), " "))
        emit("TERMINAL: FAILED - fetched and linked, but the engine's registry does not list it")
        return 1
    emit(f"STEP 3: the engine discovered it as '{mid}'")

    if args.no_load:
        emit("STEP 4: skipped (--no-load)")
    else:
        emit("STEP 4: load it once - the only proof that it can serve")
        code, body = api(f"/v1/models/{mid}/load", method="POST", timeout=LOAD_S)
        loaded = False
        deadline = time.time() + LOAD_S
        while time.time() < deadline:
            c, b = api("/v1/models/status")
            try:
                rows = [m for m in json.loads(b).get("models", []) if m.get("id") == mid]
            except Exception:
                rows = []
            loaded = bool(rows and rows[0].get("loaded"))
            if loaded:
                break
            time.sleep(5)
        result["loaded"] = loaded
        emit(f"  load http={code} loaded={loaded}")
        if not loaded:
            emit("TERMINAL: FAILED - the engine never reported it loaded")
            return 1

        emit("STEP 5: spot decode measurement (NOT a bench - a bench is T-131)")
        prompt = " ".join(["measurement"] * PROMPT_WORDS)
        t1 = time.time()
        code, body = api("/v1/chat/completions", method="POST", timeout=LOAD_S,
                         body={"model": mid, "messages": [{"role": "user", "content": prompt}],
                               "max_tokens": MEASURE_TOKENS, "temperature": 0.0})
        dt = time.time() - t1
        usage = {}
        try:
            usage = json.loads(body).get("usage", {})
        except Exception:
            pass
        ct = usage.get("completion_tokens") or 0
        tps = round(ct / dt, 2) if ct and dt else None
        result.update({"spot_s": round(dt, 2), "spot_completion_tokens": ct, "spot_tps": tps})
        emit(f"  {ct} tokens in {dt:.2f}s -> {tps} tok/s (prompt {usage.get('prompt_tokens')})")
        if not ct:
            # No tokens is not a decode figure. Say what the engine actually said (C16).
            result["spot_unmeasured"] = True
            emit("  UNMEASURED: the engine returned no completion tokens. Raw body:")
            emit("    " + body[:400].replace(chr(10), " "))

        emit("STEP 6: unload - the pool the owner was using is the pool they get back")
        code, _ = api(f"/v1/models/{mid}/unload", method="POST", timeout=120)
        emit(f"  unload http={code}")

    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(result, indent=1), encoding='utf-8')
    emit(f"STEP total: {time.time() - t0:.0f}s")
    emit("TERMINAL: DONE - fetched, discovered by the engine, exercised and released")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
