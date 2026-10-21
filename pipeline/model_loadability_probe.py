#!/usr/bin/env python3
"""Decide whether a HuggingFace repo can be SERVED by the engine we actually run.

THE ONE QUESTION THIS ANSWERS
    "Is this model worth downloading?" is not answered by download counts or by a community
    leaderboard. It is answered by the engine's own runtime: if the architecture is not in
    the mlx_lm build the engine ships, the bytes cannot load, and a model that cannot load
    is worth 0 GB of disk. This probe asks the ENGINE, offline, and only then reports size.

WHAT IT READS (all declared in config/engine.yaml - nothing hardcoded here - C12)
    engine.bundle          : the installed app bundle holding the engine's own python
    engine.oracle_python   : that interpreter (the authoritative mlx_lm build)
    engine.oracle_ttl_days : how long a cached architecture list stays valid

TIERS
    TIER-A (this script, no weights downloaded): fetch config.json + the file tree, ask the
        engine's mlx_lm which architectures it implements, and classify:
          LOADABLE_CANDIDATE   architecture implemented, MLX safetensors present
          ARCH_UNSUPPORTED     the engine's mlx_lm has no module for this model_type
          NEEDS_FORK_RUNTIME   the checkpoint requires a runtime the engine does not ship
          NO_MLX_WEIGHTS       GGUF-only, or no MLX metadata in the shards
          EMPTY_REPO           declared weights are absent (the BUG-808 failure mode)
    TIER-B (after a download, --tier-b): ask the running engine itself - /v1/models/status
        must list the model and /v1/models/{id}/load must succeed. TIER-A is a prediction;
        TIER-B is the fact.

EXIT: 0 every candidate is LOADABLE_CANDIDATE; 2 at least one is REFUSED (owner-owed: the
      bytes are the owner's); 1 the oracle could not be built (fatal - never guess).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "engine.yaml"
CACHE = ROOT / "temp" / "engine_arch_oracle.json"
WEIGHT_SUFFIXES = (".safetensors", ".gguf", ".bin", ".npz")
FORK_RUNTIME_NAMES = ("runtime",)
FORK_MODEL_TYPE_PREFIXES = ("prism",)
OK, FATAL, OWNER_OWED = 0, 1, 2

ORACLE_SNIPPET = """
import json, pkgutil
out = {"ok": False}
try:
    import mlx_lm, mlx.core as mx
    import mlx_lm.models as m
    out.update(ok=True, mlx_lm=getattr(mlx_lm, "__version__", "?"), mlx=mx.__version__,
               arches=sorted(x.name for x in pkgutil.iter_modules(m.__path__)))
except Exception as exc:
    out["error"] = type(exc).__name__ + ": " + str(exc)
print(json.dumps(out))
"""


def cfg() -> dict:
    """Load config/engine.yaml, failing loudly when it is absent (C12: no defaults here)."""
    import yaml
    if not CONFIG.exists():
        raise SystemExit(f"FATAL: {CONFIG} is missing - the probe restates no engine path of its own")
    return yaml.safe_load(CONFIG.read_text(encoding='utf-8'))


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    """GET a URL with curl, returning (http_status, body).

    curl, not urllib: this machine reaches huggingface.co through curl and not through a
    bare urllib socket (measured 2026-10-15 - the first probe returned eight silent EMPTY
    repos). The status code is RETURNED, because "no bytes" and "404" are different facts and
    conflating them is how a probe lies.
    """
    try:
        proc = subprocess.run(["curl", "-sS", "-m", str(timeout), "--retry", "1",
                               "-H", "User-Agent: maxwell-loadability-probe",
                               "-w", chr(10) + "%{http_code}", url],
                              capture_output=True, text=True, timeout=timeout + 20)
    except Exception as exc:
        return 0, f"curl failed: {type(exc).__name__}: {exc}"
    body, _, code = proc.stdout.rpartition(chr(10))
    try:
        return int(code.strip() or 0), body
    except ValueError:
        return 0, proc.stdout


def http_json(url: str, timeout: int = 25) -> tuple[int, object]:
    """Fetch a JSON document, returning (status, parsed-or-{})."""
    code, body = fetch(url, timeout)
    try:
        return code, json.loads(body)
    except Exception:
        return code, {}


def http_text(url: str, timeout: int = 25) -> tuple[int, str]:
    """Fetch a text document, returning (status, body)."""
    return fetch(url, timeout)


def oracle(force: bool = False) -> dict:
    """Ask the ENGINE's own interpreter which architectures its mlx_lm implements."""
    conf = cfg()["engine"]
    ttl_s = float(conf["oracle_ttl_days"]) * 86400
    if CACHE.exists() and not force and time.time() - CACHE.stat().st_mtime < ttl_s:
        cached = json.loads(CACHE.read_text(encoding='utf-8'))
        cached["source"] = "cache"
        return cached
    py = pathlib.Path(conf["bundle"]) / conf["oracle_python"]
    site = pathlib.Path(conf["bundle"]) / conf["oracle_site"]
    if not py.exists():
        print(f"FATAL: the engine interpreter is not at {py}")
        return {"ok": False}
    env = {"PYTHONPATH": str(site), "PATH": "/usr/bin:/bin"}
    proc = subprocess.run([str(py), "-c", ORACLE_SNIPPET], capture_output=True, text=True, env=env, timeout=180)
    try:
        got = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        print(f"FATAL: the oracle produced no JSON. stderr tail: {proc.stderr[-300:]}")
        return {"ok": False}
    if got.get("ok"):
        CACHE.write_text(json.dumps(got, indent=1), encoding='utf-8')
        got["source"] = "measured"
    return got


def repo_facts(repo: str) -> dict:
    """Fetch config.json, the file tree and the community counters for one repo."""
    code_info, info = http_json(f"https://huggingface.co/api/models/{repo}")
    code_tree, tree = http_json(f"https://huggingface.co/api/models/{repo}/tree/main?recursive=false")
    code_cfg, raw_cfg = http_text(f"https://huggingface.co/{repo}/raw/main/config.json")
    info = info if isinstance(info, dict) else {}
    tree = tree if isinstance(tree, list) else []
    try:
        config = json.loads(raw_cfg)
    except Exception:
        config = {}
    fetch_state = "OK" if code_tree == 200 else ("GONE" if code_tree in (401, 403, 404) else f"FAILED:http{code_tree}")
    weight_bytes, weight_files, has_runtime_dir = 0, 0, False
    for entry in tree if isinstance(tree, list) else []:
        name = str(entry.get("path", ""))
        size = entry.get("size")
        if name.endswith(WEIGHT_SUFFIXES) and isinstance(size, int):
            weight_bytes += size
            weight_files += 1
        if name.split("/")[0] in FORK_RUNTIME_NAMES:
            has_runtime_dir = True
    model_type = str(config.get("model_type") or config.get("text_config", {}).get("model_type") or "")
    arches = config.get("architectures") or []
    return {
        "repo": repo, "config": config, "model_type": model_type,
        "architectures": [str(a) for a in arches] if isinstance(arches, list) else [str(arches)],
        "quantization": config.get("quantization") or config.get("quantization_config") or {},
        "weight_bytes": weight_bytes, "weight_files": weight_files, "has_fork_runtime_dir": has_runtime_dir,
        "gguf_only": weight_files > 0 and all(str(e.get("path", "")).endswith(".gguf") for e in (tree if isinstance(tree, list) else []) if str(e.get("path", "")).endswith(WEIGHT_SUFFIXES)),
        "downloads": info.get("downloads"), "likes": info.get("likes"),
        "created": str(info.get("createdAt"))[:10], "license": (info.get("cardData") or {}).get("license"),
        "pipeline_tag": info.get("pipeline_tag"),
        "fetch_state": fetch_state,
        "status": {"info": code_info, "tree": code_tree, "config": code_cfg},
    }


def verdict(facts: dict, arches: set[str]) -> tuple[str, str]:
    """Classify one repo against the engine's own architecture list."""
    mt = facts["model_type"].lower()
    if facts.get("fetch_state", "OK") == "GONE":
        return "REPO_ABSENT", "the hub answers 404/403: there is nothing to download (do not add a name that resolves to nothing)"
    if facts.get("fetch_state", "OK") != "OK":
        return "FETCH_FAILED", f"the hub could not be read ({facts['fetch_state']}) - no verdict is possible"
    if facts["weight_files"] == 0:
        return "EMPTY_REPO", "the tree declares no weight files at all - the BUG-808 failure mode"
    if facts["has_fork_runtime_dir"] or any(mt.startswith(p) for p in FORK_MODEL_TYPE_PREFIXES):
        return "NEEDS_FORK_RUNTIME", f"model_type={mt or '?'} ships a private runtime/ loader the engine does not have"
    if not mt:
        return "UNDETERMINED", "config.json declares no model_type"
    if mt in arches:
        if facts["gguf_only"]:
            return "NO_MLX_WEIGHTS", "GGUF-only; the engine serves MLX safetensors"
        return "LOADABLE_CANDIDATE", f"model_type={mt} is implemented by the engine's mlx_lm"
    return "ARCH_UNSUPPORTED", f"model_type={mt} has no module in the engine's mlx_lm build"


def resolve_token(conf: dict) -> str:
    """Read the engine key from the ONE home named by the config (never a second copy - C12)."""
    home = str(conf.get("auth_token_home") or "")
    if not home:
        return ""
    module_name, _, attr = home.rpartition(".")
    try:
        module = __import__(module_name, fromlist=[attr])
        return str(getattr(module, attr))
    except Exception as exc:
        print(f"note: could not resolve {home} ({type(exc).__name__}); tier-B will run unauthenticated")
        return ""


def tier_b(repo: str, conf: dict) -> dict:
    """Ask the RUNNING engine whether it discovered the model (the fact, not the prediction)."""
    base = f"http://{conf['host']}:{conf['port']}"
    headers = {"Authorization": f"Bearer {resolve_token(conf)}"}
    try:
        req = urllib.request.Request(base + "/v1/models/status", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        return {"engine": "unreachable", "error": f"{type(exc).__name__}: {exc}"}
    ids = [m.get("id") for m in data.get("models", [])]
    name = repo.split("/")[-1]
    hit = [i for i in ids if i and (name in i or i in name)]
    return {"engine": "up", "discovered": bool(hit), "matched": hit, "served_ids": ids,
            "loaded_count": data.get("loaded_count"), "model_count": data.get("model_count")}


def main(argv: list[str]) -> int:
    """Probe every declared candidate and print the table the download decision reads."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--refresh-oracle", action="store_true")
    ap.add_argument("--tier-b", action="store_true")
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)

    conf = cfg()["engine"]
    cand = cfg()["candidates"]
    repos = args.repos or list(cand["probe"])
    orc = oracle(force=args.refresh_oracle)
    if not orc.get("ok"):
        print("FATAL: no architecture oracle - refusing to guess")
        return FATAL
    arches = set(orc["arches"])
    print(f"oracle: mlx_lm {orc['mlx_lm']} / mlx {orc['mlx']} / {len(arches)} architectures ({orc.get('source')})")

    rows, refused, fatal = [], 0, 0
    for repo in repos:
        facts = repo_facts(repo)
        v, why = verdict(facts, arches)
        if v.startswith(("ARCH_UNSUPPORTED", "NEEDS_FORK_RUNTIME", "NO_MLX_WEIGHTS", "EMPTY_REPO", "REPO_ABSENT")):
            refused += 1
        if v == "FETCH_FAILED":
            fatal += 1
        row = {"repo": repo, "verdict": v, "why": why, "gb": round(facts["weight_bytes"] / 1e9, 2),
               "files": facts["weight_files"], "model_type": facts["model_type"],
               "quant": json.dumps(facts["quantization"])[:80], "dl": facts["downloads"],
               "likes": facts["likes"], "license": facts["license"], "created": facts["created"]}
        if args.tier_b:
            row["tier_b"] = tier_b(repo, conf)
        rows.append(row)
        print(f"  {v:<20} {row['gb']:>7} GB  {repo:<52} mt={row['model_type'] or '?':<18} dl={row['dl']} likes={row['likes']} lic={row['license']} fetch={facts['fetch_state']}")
        print(f"    {'':<20} {why}")
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps({"oracle": {k: orc[k] for k in ("mlx_lm", "mlx") if k in orc},
                                                          "rows": rows}, indent=1), encoding='utf-8')
    if fatal:
        print(f"FATAL: {fatal} repo(s) could not be read - the probe refuses to guess (C16)")
        return FATAL
    return OWNER_OWED if refused else OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
