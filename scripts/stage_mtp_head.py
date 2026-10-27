#!/usr/bin/env python3
"""stage_mtp_head.py — build a checkpoint that CARRIES the published Qwen3.8 MTP head (D-3177).

WHY THIS SCRIPT EXISTS (MEASURED 2026-10-27)
    Native MTP speculative decoding DOES work on this M1 Max, but only for a checkpoint that physically
    ships ``mtp.*`` tensors. Three separate facts had to be established, each one costing a wrong reading:

    1. ``Qwen/Qwen3.8-27B`` ships the head (15 tensors, ``mtp_num_hidden_layers: 1``); the MLX 4-bit
       conversions strip it — ``mlx_lm/models/qwen3_5.py#sanitize`` deletes every ``mtp.`` weight.
    2. ``mlx-community/Qwen3.8-27B-MTP-4bit`` publishes the head ALONE (238 MB, 31 already-4-bit
       tensors: fc / layers.0 / norm / pre_fc_norm_{hidden,embedding}). Nothing attaches it to a base.
    3. An index-only rename is SILENTLY IGNORED: ``mlx_lm.utils.load_model`` globs
       ``model*.safetensors`` and takes tensor names from the FILES, never from
       ``model.safetensors.index.json``. A fixture that renames keys in the index therefore loads
       with "Checkpoint configuration declares an MTP head, but no MTP tensors were found" and the
       speedup measures 1.00x — a harness artifact that reads exactly like "MTP does not work here"
       (BUG-257's shape). This script writes the prefix into the SAFETENSORS HEADER and names the
       shard to match the loader's glob, so the head binds.

WHAT IT PRODUCES
    <out_dir>/  — every base file symlinked (no copy), config.json copied, the head written as
    ``model-<N+1>-of-<N+1>.safetensors`` with ``mtp.``-prefixed keys, and an index that names it.
    The base artifact is never modified (D-3034: the declaration resolves, the bytes stay untouched).

C12: every value comes from config/specdec_m1.yaml#mtp_head. No path, repo, prefix or shard name is
written here as a literal.

Usage:
    python3 scripts/stage_mtp_head.py            # build (refuses an existing out_dir)
    python3 scripts/stage_mtp_head.py --force    # rebuild
    python3 scripts/stage_mtp_head.py --check    # verify an existing stage binds without loading mlx
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "specdec_m1.yaml"


def _cfg() -> dict[str, Any]:
    """Load the MTP-head staging declaration (C12: no value in this file is a default)."""
    import yaml  # noqa: PLC0415

    if not CFG_PATH.exists():
        raise SystemExit("stage_mtp_head: missing config " + str(CFG_PATH))
    doc = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "mtp_head" not in doc:
        raise SystemExit("stage_mtp_head: config has no #mtp_head block")
    return doc["mtp_head"]


def _head_file(cfg: dict[str, Any], force: bool) -> Path:
    """Resolve the published head, downloading it once if the declared cache file is absent."""
    cache = Path(os.path.expanduser(str(cfg["head_cache_file"])))
    if cache.is_file() and not force:
        return cache
    from huggingface_hub import hf_hub_download  # noqa: PLC0415 - only the download path needs it

    cache.parent.mkdir(parents=True, exist_ok=True)
    got = hf_hub_download(
        repo_id=str(cfg["head_repo"]),
        filename=str(cfg["head_filename"]),
        local_dir=str(cache.parent),
    )
    src = Path(got)
    if src != cache:
        shutil.copy2(src, cache)
    return cache


def _prefix_keys(src: Path, dst: Path, prefix: str) -> dict[str, Any]:
    """Rewrite a safetensors HEADER so every tensor carries `prefix`; data bytes are copied verbatim.

    The header is the only thing that names tensors, so a rename here is what a loader actually sees.
    Offsets are preserved: the data section is byte-identical to the source.
    """
    with src.open("rb") as fh:
        header_len = struct.unpack("<Q", fh.read(8))[0]
        header = json.loads(fh.read(header_len))
        data = fh.read()
    out: dict[str, Any] = {}
    meta = header.get("__metadata__")
    if meta:
        out["__metadata__"] = meta
    for key, value in header.items():
        if key == "__metadata__":
            continue
        out[prefix + key] = value
    blob = json.dumps(out, separators=(",", ":")).encode()
    blob += b" " * ((-len(blob)) % 8)  # safetensors requires an 8-byte aligned header
    with dst.open("wb") as fh:
        fh.write(struct.pack("<Q", len(blob)))
        fh.write(blob)
        fh.write(data)
    return out


def build(cfg: dict[str, Any], force: bool) -> dict[str, Any]:
    """Stage a checkpoint that resolves the MTP head (symlinked base + one real head shard)."""
    base = Path(os.path.expanduser(str(cfg["base_model"])))
    out = Path(os.path.expanduser(str(cfg["out_dir"])))
    prefix = str(cfg["weight_prefix"])
    if not (base / "model.safetensors.index.json").is_file():
        raise SystemExit("stage_mtp_head: base has no index: " + str(base))
    if out.exists():
        if not force:
            raise SystemExit("stage_mtp_head: " + str(out) + " exists (use --force to rebuild)")
        shutil.rmtree(out)
    out.mkdir(parents=True)

    index = json.loads((base / "model.safetensors.index.json").read_text())
    weight_map = dict(index["weight_map"])
    shard_names = sorted(set(weight_map.values()))
    head_shard = f"model-{len(shard_names) + 1:05d}-of-{len(shard_names) + 1:05d}.safetensors"

    for item in base.iterdir():
        if item.name in ("config.json", "model.safetensors.index.json") or item.name.startswith("model-"):
            # the big shards are symlinked below, not copied; the index is rewritten
            if item.suffix == ".safetensors" and item.name.startswith("model-"):
                os.symlink(item, out / item.name)
            continue
        os.symlink(item, out / item.name)

    src_head = _head_file(cfg, force)
    header = _prefix_keys(src_head, out / head_shard, prefix)
    for key in header:
        if key != "__metadata__":
            weight_map[key] = head_shard
    index["weight_map"] = weight_map
    (out / "model.safetensors.index.json").write_text(json.dumps(index, indent=1))

    # NOT named `config` (BUG-1083): the config-defaults census resolves a RECEIVER BY NAME, so a local called
    # `config` holding a Hugging Face checkpoint's own config.json was counted as a Maxwell config receiver and
    # its keys (`text_config`, `mtp_num_hidden_layers`) were reported as UNDECLARED config defaults. They are
    # neither - they belong to the model's own artifact. The name now says which document is being read.
    model_config = json.loads((base / "config.json").read_text())
    text_cfg = model_config.get("text_config", model_config)
    if int(text_cfg.get("mtp_num_hidden_layers", 0)) < 1:
        raise SystemExit("stage_mtp_head: base config does not declare an MTP head")
    (out / "config.json").write_text(json.dumps(model_config, indent=4))
    return {
        "out_dir": str(out),
        "head_shard": head_shard,
        "head_tensors": len(header) - (1 if "__metadata__" in header else 0),
        "base_shards": len(shard_names),
        "mtp_num_hidden_layers": int(text_cfg["mtp_num_hidden_layers"]),
    }


def check(cfg: dict[str, Any]) -> dict[str, Any]:
    """Verify the staged checkpoint RESOLVES: a `model*.safetensors` file really carries `mtp.*` keys."""
    out = Path(os.path.expanduser(str(cfg["out_dir"])))
    prefix = str(cfg["weight_prefix"])
    found: list[str] = []
    for shard in sorted(out.glob("model*.safetensors")):
        with shard.open("rb") as fh:
            header_len = struct.unpack("<Q", fh.read(8))[0]
            keys = json.loads(fh.read(header_len)).keys()
        found.extend(k for k in keys if k.startswith(prefix))
    if not found:
        raise SystemExit("stage_mtp_head --check FAILED: no tensor named '" + prefix
                         + "*' is reachable through the loader's model*.safetensors glob")
    return {"out_dir": str(out), "mtp_tensors_visible_to_loader": len(found), "sample": found[:2]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage a Qwen3.8 checkpoint that carries the published MTP head")
    ap.add_argument("--force", action="store_true", help="rebuild an existing out_dir")
    ap.add_argument("--check", action="store_true", help="verify only (no write)")
    args = ap.parse_args(argv)
    cfg = _cfg()
    result = check(cfg) if args.check else build(cfg, args.force)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
