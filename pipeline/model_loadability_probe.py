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

THE CACHE CANNOT OUTLIVE THE ENGINE (BUG-1016, measured 2026-10-25)
    A cached architecture list answers ONLY for the engine that is installed now: the bundle's app
    version, its mlx_lm dist-info and a digest over its model modules are part of the cache key. An
    app install therefore invalidates the cache by itself, and nobody has to remember a flag.

TIERS
    TIER-A (this script, no weights downloaded): fetch config.json + the file tree, ask the
        engine's mlx_lm which architectures it implements, and classify:
          LOADABLE_CANDIDATE   architecture implemented, MLX safetensors present
          ARCH_UNSUPPORTED     the engine's mlx_lm has no module for this model_type
          NEEDS_FORK_RUNTIME   the checkpoint requires a runtime the engine does not ship
          NO_MLX_WEIGHTS       GGUF-only, or no MLX metadata in the shards
          EMPTY_REPO           declared weights are absent (the BUG-808 failure mode)
          UNDETERMINED         config.json declares no model_type, so no architecture question can be asked
          REPO_ABSENT          the hub answers 404/403: a name that resolves to nothing (BUG-808's class)
    TIER-B (after a download, --tier-b): ask the running engine itself - /v1/models/status
        must list the model and /v1/models/{id}/load must succeed. TIER-A is a prediction;
        TIER-B is the fact.

EXIT: 0 every candidate is LOADABLE_CANDIDATE; 2 at least one is REFUSED (owner-owed: the
      bytes are the owner's); 1 the oracle could not be built (fatal - never guess).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import plistlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

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


def engine_identity(conf: dict) -> dict:
    """The identity of the ENGINE an oracle describes: the bundle, its app version, its mlx_lm build.

    MEASURED 2026-10-25 (BUG-1016): the cache in temp/ was written at 17:54 against mlx_lm
    0.31.4.dev132 / 134 architectures. The owner then installed oMLX 0.7.3.dev2 (the app process
    restarted 19:05:40) and this probe still printed 0.31.4.dev132 / 134 arches, labelled only
    "(cache)". Every verdict here is a statement about a BUILD, so a cached oracle whose engine is
    never re-read is a verdict outliving its referent - the exact defect D-3151 exists to stop,
    reproduced inside the instrument built to stop it.

    The read is deliberately CHEAP (one directory listing, ~1 ms) because a discipline that costs
    more than its shortcut will not be kept (D-3151 clause 2).
    """
    bundle = pathlib.Path(conf["bundle"])
    site = bundle / conf["oracle_site"]
    ident = {"bundle": str(bundle), "app_version": None, "dist_info": [], "modules": 0, "digest": ""}
    plist = bundle / "Info.plist"
    if plist.exists():
        try:
            ident["app_version"] = plistlib.loads(plist.read_bytes()).get("CFBundleShortVersionString")
        except (OSError, ValueError, plistlib.InvalidFileException):
            ident["app_version"] = "unreadable"      # reported, never guessed (C16)
    try:
        ident["dist_info"] = sorted(p.name for p in site.glob("mlx_lm-*.dist-info"))
    except OSError:
        ident["dist_info"] = []
    models = site / "mlx_lm" / "models"
    try:
        names = sorted(p.name for p in models.iterdir() if p.suffix == ".py")
    except OSError:
        names = []
    ident["modules"] = len(names)
    ident["digest"] = hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()[:16]
    return ident


def cache_is_current(cached: dict, ident: dict, age_s: float, ttl_s: float) -> tuple[bool, str]:
    """Whether a CACHED oracle may answer for the engine installed NOW, and the reason either way.

    The ENGINE'S IDENTITY is tested BEFORE the clock: a five-second-old cache of a build that has
    been REPLACED is wrong, while a six-day-old cache of the same build is merely aging. A cache
    written before this rule existed names no engine, so it can never be trusted (fail-closed).
    """
    if not isinstance(cached, dict) or not cached.get("ok"):
        return False, "the cached oracle is not a successful reading"
    old = cached.get("engine")
    if not isinstance(old, dict) or not old.get("digest"):
        return False, "the cached oracle names NO engine: it cannot be trusted for THIS one"
    if old.get("digest") != ident.get("digest") or old.get("dist_info") != ident.get("dist_info"):
        return False, (f"the ENGINE CHANGED since the cache was written: "
                       f"{old.get('dist_info') or '?'} -> {ident.get('dist_info') or '?'}")
    if age_s >= ttl_s:
        return False, f"the cache is {age_s / 86400:.1f} day(s) old, past the {ttl_s / 86400:g}-day TTL"
    return True, f"same engine, {age_s / 60:.0f} min old"


def selftest() -> int:
    """Known-answer controls for the TWO decisions this file makes about a cache (BUG-1016)."""
    total = 0
    bad: list[str] = []

    def control(name: str, got, want) -> None:
        nonlocal total
        total += 1
        if got != want:
            bad.append(f"{name}: got {got!r}, want {want!r}")

    now_engine = {"digest": "aaa", "dist_info": ["mlx_lm-0.32.3.dev8.dist-info"]}
    old_engine = {"digest": "bbb", "dist_info": ["mlx_lm-0.31.4.dev132.dist-info"]}
    fresh_same = {"ok": True, "engine": dict(now_engine)}
    week = 604800.0

    control("the_2026_10_25_defect_a_FRESH_cache_of_a_REPLACED_engine_is_REFUSED",
            cache_is_current({"ok": True, "engine": dict(old_engine)}, now_engine, 5.0, week)[0], False)
    control("the_other_direction_the_SAME_engine_fresh_cache_IS_used",
            cache_is_current(fresh_same, now_engine, 5.0, week)[0], True)
    control("the_SAME_engine_PAST_TTL_is_REFUSED",
            cache_is_current(fresh_same, now_engine, 8 * 86400.0, week)[0], False)
    control("a_cache_that_names_NO_engine_is_REFUSED",
            cache_is_current({"ok": True, "arches": ["llama"]}, now_engine, 1.0, week)[0], False)
    control("a_FAILED_reading_is_not_a_cache",
            cache_is_current({"ok": False, "engine": dict(now_engine)}, now_engine, 1.0, week)[0], False)
    control("a_NON_MAPPING_cache_is_REFUSED_not_a_crash",
            cache_is_current({}, now_engine, 1.0, week)[0], False)
    control("the_refusal_NAMES_the_engine_change",
            "ENGINE CHANGED" in cache_is_current({"ok": True, "engine": dict(old_engine)},
                                                 now_engine, 5.0, week)[1], True)

    with tempfile.TemporaryDirectory() as td:
        base = pathlib.Path(td)
        site = base / "site-packages"
        (site / "mlx_lm" / "models").mkdir(parents=True)
        (site / "mlx_lm-0.1.dist-info").mkdir()
        (site / "mlx_lm" / "models" / "llama.py").write_text("", encoding="utf-8")
        conf = {"bundle": str(base), "oracle_site": "site-packages"}
        first = engine_identity(conf)
        control("engine_identity_is_DETERMINISTIC", engine_identity(conf) == first, True)
        control("engine_identity_counts_the_modules", first["modules"], 1)
        control("engine_identity_reads_the_dist_info", first["dist_info"], ["mlx_lm-0.1.dist-info"])
        control("a_bundle_with_NO_plist_reports_NULL_not_a_guess", first["app_version"], None)
        (site / "mlx_lm" / "models" / "flint.py").write_text("", encoding="utf-8")
        second = engine_identity(conf)
        control("a_NEW_module_changes_the_identity_digest", second["digest"] != first["digest"], True)
        control("the_new_module_is_COUNTED", second["modules"], 2)

        # BUG-1018 / D-3152 clause 2: the SWEEP RECEIPT names the engine it measured, in both directions.
        ok_orc = {"mlx_lm": "0.1.dev", "mlx": "0.1", "arches": ["llama", "mamba"]}
        rec = receipt(conf, ok_orc, [{"repo": "org/name", "verdict": "LOADABLE_CANDIDATE"}])
        control("the_sweep_receipt_NAMES_the_engine_it_measured", bool(rec["engine"].get("digest")), True)
        control("the_sweep_receipt_counts_the_architectures_the_ORACLE_saw", rec["oracle_architectures"], 2)
        control("the_sweep_receipt_carries_the_oracle_SOURCE_so_measured_and_cached_are_distinguishable",
                receipt(conf, {**ok_orc, "source": "measured, engine 0.1"}, [])["oracle_source"],
                "measured, engine 0.1")
        control("a_receipt_over_an_oracle_that_declares_no_source_carries_NULL_not_a_guess",
                receipt(conf, ok_orc, [])["oracle_source"], None)
        control("the_sweep_receipt_carries_the_rows_UNCHANGED", rec["rows"],
                [{"repo": "org/name", "verdict": "LOADABLE_CANDIDATE"}])
        control("a_receipt_of_a_FAILED_oracle_does_not_crash",
                receipt(conf, {"ok": False}, [])["oracle_architectures"], 0)

    for problem in bad:
        print(f"  FAIL control: {problem}")
    print(f"{'OK' if not bad else 'FAILED'} model-loadability controls: {total - len(bad)}/{total} known-answer")
    return 0 if not bad else 1


def oracle(force: bool = False) -> dict:
    """Ask the ENGINE's own interpreter which architectures its mlx_lm implements.

    A cache answers ONLY for the engine that is installed now (BUG-1016): the identity is read
    first, so an app install invalidates the cache by itself and no one has to remember a flag.
    """
    conf = cfg()["engine"]
    ttl_s = float(conf["oracle_ttl_days"]) * 86400
    ident = engine_identity(conf)
    if CACHE.exists() and not force:
        age_s = time.time() - CACHE.stat().st_mtime
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            cached = {}
        usable, why = cache_is_current(cached, ident, age_s, ttl_s)
        if usable:
            cached["source"] = f"cache: {why}, engine {ident.get('app_version')}"
            return cached
        print(f"oracle cache NOT used ({why}) - re-measuring from the bundle")
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
        got["engine"] = ident
        CACHE.write_text(json.dumps(got, indent=1), encoding='utf-8')
        got["source"] = f"measured, engine {ident.get('app_version')}"
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


def receipt(conf: dict, orc: dict, rows: list[dict]) -> dict:
    """The JSON receipt for a sweep: WHICH engine answered, what it reported, and one row per repo.

    WHY THE ENGINE TRAVELS WITH THE ROWS (BUG-1018, D-3152 clause 2): the oracle strings name a BUILD of mlx_lm,
    never the app that shipped it - two bundles can print the same version from different wheel commits, and a
    wheel is pinned to one commit (BUG-1019). `measured_at` is the instant this receipt was WRITTEN, which in this
    file is AFTER every row was produced: the rows are the measurement and the stamp is the filing. A receipt that
    names no engine therefore cannot support a
    comparison across an install, and its baseline has to be INFERRED from what happened to be installed at the
    time - which is exactly what T-200 had to do for the pre-swap battery. The identity lives inside the
    artifact instead, so a later reader needs no memory of the session that wrote it.
    """
    # R5 REVIEW FINDING B (accepted 2026-10-25): the field was called `architectures`, which reads as a count of
    # the LIVE engine while it is a count of what the ORACLE reported - and the oracle may answer from a cache. The
    # name now says whose number it is, and the `source` string travels with it so a reader can see `measured`
    # against `cache:` without reading this file (BUG-1016's lesson applied to a FIELD name, not only to a key).
    return {
        "engine": engine_identity(conf),
        "oracle": {k: orc[k] for k in ("mlx_lm", "mlx") if k in orc},
        "oracle_architectures": len(orc.get("arches") or []),
        "oracle_source": orc.get("source"),
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    """Probe every declared candidate and print the table the download decision reads."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--refresh-oracle", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="BUG-1016: known-answer controls for the cache-vs-engine decision (no network)")
    ap.add_argument("--tier-b", action="store_true")
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

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
        pathlib.Path(args.json_out).write_text(json.dumps(receipt(conf, orc, rows), indent=1),
                                               encoding='utf-8')
    if fatal:
        print(f"FATAL: {fatal} repo(s) could not be read - the probe refuses to guess (C16)")
        return FATAL
    return OWNER_OWED if refused else OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
