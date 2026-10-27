#!/usr/bin/env python3
"""check_delete_target.py — refuse to delete model bytes that something still needs.

WHY THIS EXISTS
  Three deletions were attempted in one day and each was aimed with a wrong number:
  `hf cache prune` named the SERVED snapshot of the code role "detached" (BUG-1050), `du -shL`
  reported 48G for a 16G model (BUG-1050), and after a real 14G delete the engine still ADVERTISED
  the deleted model and kept its flag set in model_settings.json (BUG-1057). The trap none of those
  checks can see is cross-root: ~/.omlx/models_staged/Qwen3.8-27B-MTP4 is a symlink farm whose three
  main weight shards point INTO ~/.omlx/models/Qwen3.8-27B-MLX-4bit, so deleting the roleless 15 GB
  base model would silently break a model that is not in its root.

WHAT IT DOES (read-only — it never deletes)
  For each candidate path it answers four questions, in order, and refuses on any YES:
    1. IS IT SERVED?      its realpath is a root entry's realpath (or contains one).
    2. IS IT REFERENCED?  some symlink anywhere under the model roots resolves INSIDE it.
    3. IS IT SHARED?      a file in it shares (device, inode) with a file outside it (hardlink axis).
    4. IS IT IN FLIGHT?   it carries an incomplete-download marker, or the engine still advertises it.
  Only a candidate that survives all four prints SAFE_TO_DELETE with the size that would actually be
  freed. `du -sh` is reported beside it because the two numbers disagree on symlink farms.
  Exit 0 = every candidate safe, 2 = at least one referenced, 3 = undetermined (engine unreachable:
  fail-closed, no receipt => no deletion), 4 = usage error.

CONFIG: config/delete_safety.yaml declares the roots, the id forms and the engine (C12).
USAGE:  python3 scripts/check_delete_target.py ~/.cache/huggingface/hub/models--org--name [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator

import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config" / "delete_safety.yaml"
BYTES_PER_MIB = 1024 * 1024
EXIT_SAFE = 0
EXIT_REFERENCED = 2
EXIT_UNDETERMINED = 3
EXIT_USAGE = 4

VERDICT_SAFE = "SAFE_TO_DELETE"
VERDICT_REFUSED = "REFUSE"
VERDICT_ABSENT = "ABSENT_ALREADY"
VERDICT_UNKNOWN = "UNDETERMINED"


def _cfg() -> dict[str, Any]:
    """Load the delete-safety config; a missing file is a usage error, never a silent default."""
    if not CFG_PATH.is_file():
        raise SystemExit(f"FAIL: missing {CFG_PATH} — the rail has no declared roots (C12)")
    with CFG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def _expand(raw: str) -> Path:
    """Expand ~ and make a root absolute without requiring it to exist."""
    return Path(os.path.expanduser(raw)).absolute()


def _is_inside(child: Path, parent: Path) -> bool:
    """True when child == parent or child sits below parent (pure path test, no IO)."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _iter_files(base: Path) -> Iterator[Path]:
    """Yield every regular file under base without following directory symlinks."""
    for dirpath, _dirnames, filenames in os.walk(base, followlinks=False):
        for name in filenames:
            yield Path(dirpath) / name


def _size_report(base: Path, min_inode_bytes: int) -> dict[str, Any]:
    """Size the candidate the two ways that disagree: apparent bytes (deduped) and provisioned blocks.

    Apparent bytes de-duplicate by (device, inode) so a hardlinked blob is counted once; provisioned
    bytes are what the filesystem would actually give back. Symlinks are followed for the apparent
    figure because a symlink farm's payload is its target's payload.
    """
    seen: set[tuple[int, int]] = set()
    apparent = 0
    provisioned = 0
    big: list[tuple[int, int, Path]] = []
    for path in _iter_files(base):
        try:
            st = path.stat()  # follows symlinks: a shard symlink costs its target's bytes
        except OSError:
            continue
        key = (st.st_dev, st.st_ino)
        if key in seen:
            continue
        seen.add(key)
        apparent += st.st_size
        provisioned += getattr(st, "st_blocks", 0) * 512
        if st.st_size >= min_inode_bytes and not path.is_symlink():
            # Symlinks are excluded from the inode axis on purpose: stat() follows them, so their
            # inode IS the target's and the symlink axis already reports that reference.
            big.append((st.st_dev, st.st_ino, path))
    return {"apparent_bytes": apparent, "provisioned_bytes": provisioned, "file_count": len(seen), "big": big}


def _referrers(candidate: Path, roots: list[Path]) -> list[str]:
    """Return every path under the model roots whose symlink resolves INSIDE candidate.

    This is the axis a per-root existence test cannot see: the referrer does not have to be a
    sibling of the candidate, and the candidate does not have to be a model directory.
    """
    found: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            for name in dirnames + filenames:
                path = Path(dirpath) / name
                if not path.is_symlink():
                    continue
                real = Path(os.path.realpath(path))
                if _is_inside(real, candidate):
                    try:
                        path.relative_to(candidate)
                        continue  # a link inside the candidate pointing to itself
                    except ValueError:
                        pass
                    found.append(f"{path} -> {real}")
    return found


def _shared_inodes(big: list[tuple[int, int, Path]], candidate: Path, roots: list[Path]) -> list[str]:
    """Return outside files that share (device, inode) with a large file inside the candidate.

    Hardlinked weights break exactly as silently as symlinked ones, and `du` cannot tell you which
    of two hardlinks is the reference.
    """
    wanted = {(dev, ino): str(path) for dev, ino, path in big}
    if not wanted:
        return []
    hits: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in _iter_files(root):
            if _is_inside(path, candidate) or path.is_symlink():
                # A symlink is already reported by the symlink axis; stat() follows it, so counting it
                # here would re-report the same reference as a hardlink and inflate the evidence.
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            key = (st.st_dev, st.st_ino)
            if key in wanted:
                hits.append(f"{path} shares bytes with {wanted[key]}")
    return hits


def _incomplete(base: Path, markers: list[str]) -> list[str]:
    """Return any path under base carrying an in-flight download marker."""
    hits: list[str] = []
    for path in _iter_files(base):
        name = path.name
        if any(marker in name for marker in markers):
            hits.append(str(path))
    return hits


def _advertised(cfg: dict[str, Any]) -> set[str]:
    """Read the engine's advertised model ids; raise on any failure (fail-closed, never assume)."""
    engine = cfg.get("omlx") or {}
    url = f"{engine.get('base_url', '')}{engine.get('models_path', '/v1/models')}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {engine.get('api_key', '')}"})
    with urllib.request.urlopen(request, timeout=engine.get("timeout_s", 30)) as response:
        payload = json.load(response)
    return {str(entry.get("id")) for entry in payload.get("data", []) if entry.get("id")}


def _candidate_ids(candidate: Path, forms: list[str]) -> set[str]:
    """Derive the ids the engine might use for this path, per the declared id forms.

    Two id forms exist because discovery serves a root entry by its basename while an HF-cache entry
    is served by its repo slug ("models--<org>--<name>" -> "<org>--<name>"). One model therefore has
    two ids, and matching only one form reads a live model as unused (BUG-1054).
    """
    ids: set[str] = set()
    name = candidate.name
    if "basename" in forms:
        ids.add(name)
    if "hf_repo_slug" in forms and name.startswith("models--"):
        ids.add(name[len("models--"):])
    if "hf_repo_slug" in forms:
        # A snapshot dir is served under the repo's slug, so also derive it from /models--<x>/snapshots/
        for parent in candidate.parents:
            if parent.name.startswith("models--"):
                ids.add(parent.name[len("models--"):])
                break
    return ids


def _fmt(num: int) -> str:
    """Human-readable size with one decimal, in the unit `du -sh` would use."""
    value = float(num)
    for unit in ("B", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}T"


def _extend_capped(reasons: list[str], axis: str, hits: list[str], cap: int) -> None:
    """Append at most `cap` evidence lines for one axis, plus a count of what was withheld."""
    for hit in hits[:cap]:
        reasons.append(f"{axis}: {hit}")
    if len(hits) > cap:
        reasons.append(f"{axis}: ... and {len(hits) - cap} more (count is complete, examples are capped)")


def check(candidate_raw: str, cfg: dict[str, Any], advertised: set[str]) -> dict[str, Any]:
    """Judge one candidate path and return a verdict record (never deletes anything)."""
    candidate = _expand(candidate_raw)
    model_roots = [_expand(raw) for raw in cfg.get("model_roots", [])]
    storage_roots = [_expand(raw) for raw in cfg.get("storage_roots", [])]
    roots = model_roots + storage_roots
    markers = [str(m) for m in cfg.get("incomplete_markers", [])]
    inode_cfg = cfg.get("inode_check") or {}
    min_inode = int(inode_cfg.get("min_bytes", BYTES_PER_MIB))
    forms = [str(f) for f in cfg.get("id_forms", [])]
    ids = _candidate_ids(candidate, forms)
    live_ids = sorted(ids & advertised)

    real = Path(os.path.realpath(candidate))
    record: dict[str, Any] = {
        "candidate": str(candidate),
        "realpath": str(real),
        "candidate_ids": sorted(ids),
        "advertised_ids": live_ids,
        "du_h": None,
        "apparent": None,
        "provisioned": None,
        "reasons": [],
        "verdict": VERDICT_SAFE,
    }

    if not real.exists():
        record["verdict"] = VERDICT_ABSENT
        if live_ids:
            record["verdict"] = VERDICT_REFUSED
            record["reasons"].append(
                "bytes are GONE but the engine still advertises the id — reload the engine, "
                "then remove the dead key from ~/.omlx/model_settings.json (BUG-1057)"
            )
        return record

    sizes = _size_report(real, min_inode)
    record["du_h"] = _fmt(sizes["apparent_bytes"])
    record["apparent"] = sizes["apparent_bytes"]
    record["provisioned"] = sizes["provisioned_bytes"]

    # 1. IS IT SERVED? — a LOADABLE entry (model root only; storage roots confer no servability).
    for root in model_roots:
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            entry_real = Path(os.path.realpath(entry))
            if entry_real == real or _is_inside(entry_real, real):
                record["reasons"].append(f"SERVED: {entry} resolves to {entry_real}")

    # 2. IS IT REFERENCED? — the cross-root symlink axis (the MTP4 trap).
    cap = int(cfg.get("max_examples", 4))
    _extend_capped(record["reasons"], "SYMLINK-REFERENCED", _referrers(real, roots), cap)

    # 3. IS IT SHARED? — hardlink axis, large files only.
    if inode_cfg.get("enabled", True):
        _extend_capped(record["reasons"], "INODE-SHARED", _shared_inodes(sizes["big"], real, roots), cap)

    # 4. IS IT IN FLIGHT, or still promised by the engine?
    _extend_capped(record["reasons"], "INCOMPLETE-DOWNLOAD", _incomplete(real, markers), cap)
    if live_ids:
        record["reasons"].append(
            f"ADVERTISED: engine serves {live_ids} — deleting now leaves a phantom id until a reload "
            f"(BUG-1057); delete, then reload, then re-run this rail"
        )

    record["reasons"] = list(dict.fromkeys(record["reasons"]))
    if record["reasons"]:
        record["verdict"] = VERDICT_REFUSED
    return record


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: judge every candidate, print the evidence, return the refusal code."""
    cfg = _cfg()
    parser = argparse.ArgumentParser(description="Refuse to delete model bytes something still needs (read-only).")
    parser.add_argument("paths", nargs="+", help="candidate paths (files or directories)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--config", default=None, help="override config path (default config/delete_safety.yaml)")
    args = parser.parse_args(argv)

    global CFG_PATH
    if args.config:
        CFG_PATH = Path(args.config).expanduser().absolute()

    try:
        advertised = _advertised(cfg)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"FAIL-CLOSED: engine unreachable, so 'still advertised' cannot be ruled out: {exc}", file=sys.stderr)
        for raw in args.paths:
            print(f"{VERDICT_UNKNOWN}  {raw}  (engine unreachable — no receipt, no deletion)", file=sys.stderr)
        return EXIT_UNDETERMINED

    records = [check(raw, cfg, advertised) for raw in args.paths]

    if args.json:
        print(json.dumps({"engine_model_count": len(advertised), "records": records}, indent=2))
    else:
        print(f"engine advertises {len(advertised)} id(s)")
        for rec in records:
            print()
            print(f"[{rec['verdict']}] {rec['candidate']}")
            print(f"  realpath   : {rec['realpath']}")
            print(f"  engine ids : {rec['candidate_ids']} -> advertised={rec['advertised_ids']}")
            if rec["apparent"] is not None:
                print(f"  size       : du-style {rec['du_h']}  (apparent {rec['apparent']} B, "
                      f"provisioned {rec['provisioned']} B)")
            for reason in rec["reasons"]:
                print(f"  - {reason}")
            if not rec["reasons"] and rec["verdict"] == VERDICT_SAFE:
                print("  - nothing serves it, nothing links to it, nothing shares its bytes")

    codes = cfg.get("exit_codes") or {}
    if any(rec["verdict"] == VERDICT_REFUSED for rec in records):
        return int(codes.get("referenced", EXIT_REFERENCED))
    return int(codes.get("safe", EXIT_SAFE))


if __name__ == "__main__":
    sys.exit(main())
