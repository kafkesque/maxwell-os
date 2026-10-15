#!/usr/bin/env python3
"""Fetch one HuggingFace repo into the engine's model directory, and PROVE it landed.

Why a script and not a shell one-liner: the download is the part of a model decision that can be
interrupted (an hour of bytes, a dropped connection, a reboot). This one is resumable
(huggingface_hub caches by blob), it verifies the artefacts BEFORE it publishes a symlink, and it
writes a receipt. A symlink whose target is absent is the BUG-808 failure mode: a name that reads
as a model and is not one.

The engine serves the DIRECTORIES under engine.model_dir; the convention on this machine is a
symlink from that directory into the hub snapshot, so the hub stays the single byte store and the
engine directory stays a list of names.

Usage:
    python3 pipeline/hf_fetch_model.py --repo openbmb/MiniCPM5-2B-MLX [--link-name NAME]
    python3 pipeline/hf_fetch_model.py --repo ... --verify-only

EXIT: 0 fetched and verified; 2 already present and verified (no bytes moved); 1 fatal.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "engine.yaml"
RECEIPT = ROOT / "governance" / "hf_fetch_receipt.json"
REQUIRED = ("config.json",)
WEIGHT_SUFFIX = ".safetensors"
OK, FATAL, PRESENT = 0, 1, 2


def engine_conf() -> dict:
    """Read the engine's declared facts from their one home (C12)."""
    import yaml
    return yaml.safe_load(CONFIG.read_text())


def verify(snapshot: pathlib.Path) -> tuple[bool, str]:
    """Prove a snapshot can be served: a config plus at least one non-empty shard."""
    if not snapshot.exists():
        return False, f"snapshot path does not exist: {snapshot}"
    names = [p.name for p in snapshot.iterdir()]
    for req in REQUIRED:
        if req not in names:
            return False, f"{req} is absent from the snapshot"
    shards = [p for p in snapshot.iterdir() if p.suffix == WEIGHT_SUFFIX]
    if not shards:
        return False, "no .safetensors shard landed - the engine serves MLX safetensors"
    if any(p.stat().st_size == 0 for p in shards):
        return False, "a shard is zero bytes - the download did not complete"
    total = sum(p.stat().st_size for p in shards)
    return True, f"{len(shards)} shard(s), {total / 1e9:.2f} GB"


def main(argv: list[str]) -> int:
    """Fetch, verify, link, receipt. Prints STEP lines so a runner can watch it."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--link-name")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args(argv)
    conf = engine_conf()
    model_dir = pathlib.Path(conf["engine"]["model_dir"])
    link_name = args.link_name or args.repo.split("/")[-1]
    link = model_dir / link_name

    def step(msg: str) -> None:
        print(f"STEP {msg}", flush=True)

    if args.verify_only:
        if not link.exists():
            print(f"FATAL: {link} is absent")
            return FATAL
        ok, why = verify(link.resolve())
        print(f"{'ok' if ok else 'FAIL'}: {link} -> {why}")
        return OK if ok else FATAL

    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        print(f"FATAL: huggingface_hub is unavailable ({type(exc).__name__}: {exc})")
        return FATAL

    if not conf.get("hf") or "download_workers" not in conf["hf"]:
        print("FATAL: config/engine.yaml declares no hf.download_workers - refusing to invent one (C12)")
        return FATAL
    workers = int(conf["hf"]["download_workers"])
    step(f"fetching {args.repo} with {workers} workers into the hub cache")
    t0 = time.time()
    try:
        snapshot = pathlib.Path(snapshot_download(repo_id=args.repo, max_workers=workers))
    except Exception as exc:
        print(f"FATAL: the fetch failed: {type(exc).__name__}: {exc}")
        return FATAL
    step(f"hub snapshot at {snapshot} after {time.time() - t0:.0f}s")
    ok, why = verify(snapshot)
    if not ok:
        print(f"FATAL: verification failed: {why}")
        return FATAL
    step(f"verified: {why}")

    if link.is_symlink() or link.exists():
        if link.exists() and verify(link.resolve())[0]:
            print(f"present: {link} already resolves to a verified snapshot - no bytes moved")
            return PRESENT
        print(f"note: {link} exists but does not resolve to a verified model - replacing it")
        if link.is_symlink():
            link.unlink()
        else:
            print(f"FATAL: {link} is a real directory; refusing to touch an owner's directory")
            return FATAL
    model_dir.mkdir(parents=True, exist_ok=True)
    link.symlink_to(snapshot)
    ok, why = verify(link.resolve())
    step(f"linked: {link} -> {snapshot}")
    receipt = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else []
    receipt.append({"repo": args.repo, "link": str(link), "snapshot": str(snapshot),
                    "verified": ok, "detail": why, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    RECEIPT.write_text(json.dumps(receipt, indent=1))
    if not ok:
        print(f"FATAL: the link does not verify: {why}")
        return FATAL
    print(f"ok: {link_name} is fetched, verified and linked ({why})")
    return OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
