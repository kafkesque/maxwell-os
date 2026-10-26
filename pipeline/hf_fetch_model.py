#!/usr/bin/env python3
"""Fetch one HuggingFace repo into the engine's model directory, and PROVE it landed.

Why a script and not a shell one-liner: the download is the part of a model decision that can be
interrupted (an hour of bytes, a dropped connection, a reboot). This one is resumable
(huggingface_hub caches by blob), it verifies the artefacts BEFORE it publishes a symlink, and it
writes a receipt. A symlink whose target is absent is the BUG-808 failure mode: a name that reads
as a model and is not one.

T-141 (D-3015: a DOWNLOAD is one per repo). Measured 2026-10-15 (BUG-814): one hub repo held SIX
.incomplete blobs in which three target hashes each appeared TWICE - the fingerprint of two
overlapping attempts at one repo. huggingface_hub resumes its OWN fragments and cannot assemble a
foreign one, so those bytes were 4.0 GB of nothing that no tool could ever finish. Two guards,
both cheap, and both here rather than in a runbook:
  * an EXCLUSIVE per-repo lock (flock, non-blocking). A second fetch REFUSES and NAMES the holder.
  * a DUPLICATE-TARGET-FRAGMENT check before any bytes move: duplicates are unassemblable BY
    CONSTRUCTION, while a single fragment per target is a real resume and is reported as one.
Nothing is deleted silently. The duplicate case needs --discard-fragments, and the discard is
written into the receipt with the bytes it removed.

The engine serves the DIRECTORIES under engine.model_dir; the convention on this machine is a
symlink from that directory into the hub snapshot, so the hub stays the single byte store and the
engine directory stays a list of names.

Usage:
    python3 pipeline/hf_fetch_model.py --repo openbmb/MiniCPM5-2B-MLX [--link-name NAME]
    python3 pipeline/hf_fetch_model.py --repo ... --verify-only
    python3 pipeline/hf_fetch_model.py --repo ... --discard-fragments   # duplicate targets only

EXIT: 0 fetched and verified; 2 already present and verified (no bytes moved); 1 fatal.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "engine.yaml"
RECEIPT = ROOT / "governance" / "hf_fetch_receipt.json"
REQUIRED = ("config.json",)
WEIGHT_SUFFIX = ".safetensors"
FRAGMENT_SUFFIX = ".incomplete"
INDEX_NAME = "model.safetensors.index.json"
OK, FATAL, PRESENT = 0, 1, 2

#: huggingface_hub names a partial blob "<sha256-of-target>.<random>.incomplete". The random part is
#: PER ATTEMPT, so two fragments sharing a target hash are two attempts at ONE blob - the BUG-814
#: fingerprint, and the only case that can never assemble.
FRAGMENT = re.compile(r"^([0-9a-f]{64})\.[0-9a-zA-Z_.-]+" + re.escape(FRAGMENT_SUFFIX) + r"$")


class LockHeld(Exception):
    """Another process holds this repo's fetch lock; its payload names it."""

    def __init__(self, path: pathlib.Path, holder: str) -> None:
        super().__init__(f"{path} is held")
        self.path = path
        self.holder = holder


def engine_conf() -> dict:
    """Read the engine's declared facts from their one home (C12)."""
    import yaml
    return yaml.safe_load(CONFIG.read_text(encoding='utf-8'))


def hf_setting(conf: dict, key: str) -> str:
    """One declared hf.* value, or FATAL - this tool never invents a default (C12/C16)."""
    block = conf.get("hf")
    if not isinstance(block, dict) or key not in block:
        raise SystemExit(f"FATAL: config/engine.yaml declares no hf.{key} - refusing to invent one (C12)")
    return str(block[key])


def repo_dir(repo: str) -> pathlib.Path:
    """The hub cache directory for a repo, models or datasets (measurement home, not a guess)."""
    from huggingface_hub import constants
    hub = pathlib.Path(constants.HF_HUB_CACHE)
    for prefix in ("models--", "datasets--"):
        candidate = hub / (prefix + repo.replace("/", "--"))
        if candidate.is_dir():
            return candidate
    return hub / ("models--" + repo.replace("/", "--"))


class RepoLock:
    """The exclusive per-repo fetch lock. Non-blocking: a second fetch REFUSES, it does not queue.

    flock is released by the KERNEL when the holding process dies, so a crashed fetch cannot leave a
    lock that needs manual clearing. The payload exists only to NAME the holder in the refusal.
    """

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "RepoLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = self.path.read_text(errors="ignore", encoding='utf-8').strip() or "(no payload was written)"
            os.close(self.fd)
            self.fd = None
            raise LockHeld(self.path, holder)
        self.path.write_text(json.dumps({"pid": os.getpid(), "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                         "cmd": " ".join(sys.argv)}), encoding='utf-8')
        return self

    def __exit__(self, *exc: object) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def fragments(blobs: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """Group this repo's .incomplete blobs by the TARGET hash their name carries."""
    found: dict[str, list[pathlib.Path]] = {}
    if not blobs.is_dir():
        return found
    for path in sorted(blobs.iterdir()):
        if not path.name.endswith(FRAGMENT_SUFFIX):
            continue
        match = FRAGMENT.match(path.name)
        found.setdefault(match.group(1) if match else path.name, []).append(path)
    return found


def report_fragments(found: dict[str, list[pathlib.Path]]) -> tuple[list[pathlib.Path], int]:
    """Print the fragment reading and return (duplicate files, bytes they occupy)."""
    duplicates: list[pathlib.Path] = []
    duplicate_bytes = 0
    for target, paths in sorted(found.items()):
        if len(paths) > 1:
            print(f"  UNASSEMBLABLE: {len(paths)} fragments for ONE target {target[:16]}.. - two "
                  f"attempts at one blob, and huggingface_hub resumes only its own (BUG-814)")
            for path in paths:
                size = path.stat().st_size
                duplicate_bytes += size
                duplicates.append(path)
                print(f"    {size / 1e6:10.1f} MB  {path.name}")
        else:
            print(f"  resumable: 1 fragment for target {target[:16]}.. ({paths[0].stat().st_size / 1e6:.1f} MB)")
    return duplicates, duplicate_bytes


def progress(snapshot: pathlib.Path) -> str:
    """Say RESUME or FRESH, counted against the shard index when the repo declares one."""
    index = snapshot / INDEX_NAME
    if index.exists():
        try:
            expected = sorted(set(json.loads(index.read_text(encoding='utf-8'))["weight_map"].values()))
        except Exception as exc:
            return f"index present but unreadable ({type(exc).__name__}) - shard count unknown"
        present = [n for n in expected
                   if (snapshot / n).exists() and (snapshot / n).stat().st_size > 0]
        return f"resume: {len(present)}/{len(expected)} declared shards already on disk"
    have = [p for p in snapshot.glob("*" + WEIGHT_SUFFIX) if p.stat().st_size > 0] if snapshot.is_dir() else []
    return f"{'resume' if have else 'fresh'}: {len(have)} shard(s) on disk, no index to count against"


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


def append_receipt(record: dict) -> None:
    """One line per fetch, appended, so the store's history is evidence and not a memory."""
    receipt = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else []
    receipt.append(record)
    RECEIPT.write_text(json.dumps(receipt, indent=1), encoding='utf-8')


def main(argv: list[str]) -> int:
    """Fetch, verify, link, receipt. Prints STEP lines so a runner can watch it."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--link-name")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--discard-fragments", action="store_true",
                    help="delete the UNASSEMBLABLE duplicate-target fragments before fetching")
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

    workers = int(hf_setting(conf, "download_workers"))
    held = repo_dir(args.repo)
    step(f"this repo's hub directory is {held}")

    # ── the T-141 guards, BEFORE a byte moves ───────────────────────────────────────────────────
    blobs = held / "blobs"
    found = fragments(blobs)
    discarded: list[str] = []
    discarded_bytes = 0
    if found:
        print(f"fragments: {len(found)} target(s) with {FRAGMENT_SUFFIX} bytes in {blobs}")
        duplicates, duplicate_bytes = report_fragments(found)
        if duplicates and not args.discard_fragments:
            print(f"FATAL: {len(duplicates)} UNASSEMBLABLE fragment(s) occupying {duplicate_bytes / 1e9:.2f} GB. "
                  f"A fetch started now would fetch these blobs again and leave the duplicates in place "
                  f"forever. Remove them explicitly with --discard-fragments (the discard is receipted).")
            return FATAL
        for path in duplicates:
            discarded_bytes += path.stat().st_size
            discarded.append(path.name)
            path.unlink()
        if discarded:
            step(f"discarded {len(discarded)} duplicate-target fragment(s), {discarded_bytes / 1e9:.2f} GB")
    else:
        print(f"fragments: none in {blobs} (a fresh or a fully-assembled repo)")
    if held.is_dir():
        print(f"progress: {progress(held / 'snapshots' / 'main') if (held / 'snapshots' / 'main').is_dir() else progress(held)}")

    lock = pathlib.Path(os.path.expanduser(hf_setting(conf, "lock_dir"))) / (
        args.repo.replace("/", "--") + hf_setting(conf, "lock_suffix"))
    try:
        lock_ctx = RepoLock(lock)
        lock_ctx.__enter__()
    except LockHeld as exc:
        print("FATAL: another fetch holds this repo - refusing to overlap (T-141/D-3015, BUG-814).")
        print(f"       lock:   {exc.path}")
        print(f"       holder: {exc.holder}")
        print("       Two overlapping attempts at one repo leave unassemblable fragments; wait for it, "
              "or kill it, and try again.")
        return FATAL

    code = FATAL
    try:
        step(f"fetching {args.repo} with {workers} workers into the hub cache (lock held)")
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
                code = PRESENT
                return code
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
        append_receipt({"repo": args.repo, "link": str(link), "snapshot": str(snapshot),
                        "verified": ok, "detail": why, "lock": str(lock),
                        "discarded_fragments": discarded, "discarded_bytes": discarded_bytes,
                        "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        if not ok:
            print(f"FATAL: the link does not verify: {why}")
            return FATAL
        print(f"ok: {link_name} is fetched, verified and linked ({why})")
        code = OK
        return code
    finally:
        lock_ctx.__exit__(None, None, None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
