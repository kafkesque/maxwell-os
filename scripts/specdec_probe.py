#!/usr/bin/env python3
"""Speculative-decoding probe for MLX on Apple Silicon (M1 Max).

WHY THIS SCRIPT EXISTS (D-3170 / BUG-1040)
    The owner asked for a VERIFIED speculative-decoding configuration that makes decode faster on this machine.
    `governance/SPECULATIVE_DECODING_M1_20261027.md` declared `mlx_lm` draft+verify the only M1-eligible route
    (mtplx native MTP is M5-TensorOps-only and its own hardware gate refuses this chip) and left the measurement
    OWED. This script is the instrument that pays that debt, in three separately failing steps:

      verify   — is the draft even a legal draft? (token->id map identical; weights load strict=True)
      convert  — quantise the draft with the UPSTREAM converter, from a normalised staging copy
      bench    — measure baseline vs draft+verify on the SAME loaded target, at two declared context lengths

WHY THE STEPS ARE SEPARATE
    The first attempt failed at step 2 with `ValueError: Model type qwen3_5_moe_text not supported.` — a NAME
    mismatch, not an architecture gap (the draft loads strict=True once aliased). Folding the three steps into
    one command is how such a failure gets reported as "speculative decoding does not work here", which would be
    a false negative (BUG-257's shape: a harness artifact scored as a model fact).

WHAT THIS SCRIPT REFUSES TO DO
    - It never edits site-packages. The alias is config data (`config/specdec_m1.yaml#draft.normalisation`),
      applied to a config dict in memory and, for conversion, to a staging copy of the artifact.
    - It never compares a prefill rate taken below the declared `seen_floor` (BUG-803/BUG-805): such a reading is
      reported INCOMPARABLE, because a 30-token prompt prefills ~1.4x faster than a 4.5k one on the same model.
    - It never reports a decode figure without its context length, and never a single reading as a fact.

USAGE
    python3 scripts/specdec_probe.py verify
    python3 scripts/specdec_probe.py convert
    python3 scripts/specdec_probe.py bench
    python3 scripts/specdec_probe.py bench --draft-tokens 3 --repeats 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "specdec_m1.yaml"


def _cfg() -> dict[str, Any]:
    """Load and return the probe configuration (C12: no value in this file is a default)."""
    import yaml

    if not CFG_PATH.exists():
        raise SystemExit("specdec_probe: missing config " + str(CFG_PATH))
    data = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("specdec_probe: config is not a mapping")
    return data


def _expand(p: str) -> Path:
    """Expand a config path (tilde + env) into an absolute Path."""
    return Path(os.path.expandvars(str(p))).expanduser()


def _model_dir(model_id: str) -> Path:
    """Resolve an oMLX model id through the single declaration rule (scripts/list_model_phantoms.py).

    WHY reuse instead of re-deriving: D-3034 — a second resolution rule is a second truth. The phantom tool
    already owns "what does this registered id point at", so the probe asks it.
    """
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from list_model_phantoms import _engine_paths  # noqa: PLC0415

    model_dir, _settings = _engine_paths()
    path = Path(model_dir) / model_id
    if not path.exists():
        raise SystemExit("specdec_probe: target model dir does not exist: " + str(path))
    return path


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, raising a named error rather than returning {} (C16)."""
    if not path.exists():
        raise SystemExit("specdec_probe: expected file missing: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(obj: Any) -> str:
    """Stable sha256 over a JSON-serialisable object (key order independent)."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _tokenizer_fingerprint(model_path: Path) -> dict[str, Any]:
    """Fingerprint the three maps that decide token-id agreement: vocab, merges, added tokens.

    WHY exactly these three: a draft whose vocab ids differ cannot propose a token the target can verify, and a
    differing merge table yields different ids for the same text. Nothing else in tokenizer.json affects the
    accept/verify contract.
    """
    tok = _read_json(model_path / "tokenizer.json")
    model_part = tok.get("model", {}) or {}
    added = tok.get("added_tokens", []) or []
    return {
        "path": str(model_path),
        "vocab_sha": _sha(model_part.get("vocab", {})),
        "vocab_size": len(model_part.get("vocab", {}) or {}),
        "merges_sha": _sha(model_part.get("merges", [])),
        "merges_n": len(model_part.get("merges", []) or []),
        "added_sha": _sha(sorted((int(t.get("id", -1)), str(t.get("content", ""))) for t in added)),
        "added_n": len(added),
    }


def _gate_tokenizers(target: Path, draft: Path) -> dict[str, Any]:
    """Refuse a draft whose token->id maps differ from the target's — the hard gate for speculative decoding."""
    t = _tokenizer_fingerprint(target)
    d = _tokenizer_fingerprint(draft)
    same = {
        "vocab": t["vocab_sha"] == d["vocab_sha"],
        "merges": t["merges_sha"] == d["merges_sha"],
        "added_tokens": t["added_sha"] == d["added_sha"],
    }
    return {"target": t, "draft": d, "identical": all(same.values()), "same": same}


def _alias(cfg: dict[str, Any]) -> Optional[dict[str, str]]:
    """Return the declared model_type normalisation, or None when the artifact declares none."""
    norm = (cfg["draft"].get("normalisation") or {}).get("model_type") or {}
    if not norm.get("from") or not norm.get("to"):
        return None
    return {"from": str(norm["from"]), "to": str(norm["to"])}


def _draft_model_config(cfg: dict[str, Any], draft_path: Path) -> Optional[dict[str, Any]]:
    """Return a model_config override when the artifact's declared model_type needs the declared alias.

    WHY an override and not a rewrite: the artifact stays byte-identical to what was downloaded, so a future
    upstream release that learns the alias changes nothing here, and nothing on this machine is left patched.
    """
    declared = str(_read_json(draft_path / "config.json").get("model_type") or "")
    alias = _alias(cfg)
    if alias is None or declared != alias["from"]:
        return None
    patched = _read_json(draft_path / "config.json")
    patched["model_type"] = alias["to"]
    return patched


def _stage_draft(cfg: dict[str, Any]) -> Path:
    """Build a staging copy whose config declares the aliased model_type, with weights symlinked (no copy)."""
    draft_cfg = cfg["draft"]
    src = _expand(draft_cfg["source_dir"])
    stage = _expand(draft_cfg["staging_dir"])
    alias = _alias(cfg)
    if alias is None:
        raise SystemExit("specdec_probe: convert without a declared alias is not supported by this probe")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    declared = _read_json(src / "config.json")
    if str(declared.get("model_type")) != alias["from"]:
        raise SystemExit(
            "specdec_probe: artifact declares model_type="
            + str(declared.get("model_type"))
            + ", config expects "
            + alias["from"]
            + " — the normalisation is stale, fix config/specdec_m1.yaml"
        )
    declared["model_type"] = alias["to"]
    (stage / "config.json").write_text(json.dumps(declared, indent=2) + "\n", encoding="utf-8")
    for name in draft_cfg["tokenizer_files"]:
        if (src / name).exists():
            shutil.copy2(src / name, stage / name)
    for weight in sorted(src.glob(draft_cfg["weight_glob"])):
        os.symlink(weight, stage / weight.name)
    return stage


def _cmd_convert(cfg: dict[str, Any]) -> int:
    """Quantise the draft with the upstream mlx_lm converter, from the normalised staging copy."""
    draft_cfg = cfg["draft"]
    stage = _stage_draft(cfg)
    out = _expand(draft_cfg["mlx_out_dir"])
    cmd = [
        sys.executable, "-m", "mlx_lm.convert",
        "--hf-path", str(stage),
        "--mlx-path", str(out),
        "-q",
        "--q-bits", str(int(draft_cfg["q_bits"])),
        "--q-group-size", str(int(draft_cfg["group_size"])),
        "--q-mode", str(draft_cfg["q_mode"]),
    ]
    print("run:", " ".join(cmd))
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout[-2000:])
    if proc.returncode != 0:
        print(proc.stderr[-4000:])
        raise SystemExit("specdec_probe: convert FAILED (rc=" + str(proc.returncode) + ")")
    written = _read_json(out / "config.json")
    total = sum(f.stat().st_size for f in out.glob("*.safetensors"))
    print(
        "OK convert | model_type=" + str(written.get("model_type"))
        + " | quant=" + json.dumps(written.get("quantization"))
        + " | bytes=" + str(total)
        + " | s=" + str(round(time.perf_counter() - started, 1))
    )
    return 0


def _cmd_verify(cfg: dict[str, Any]) -> int:
    """Prove the draft is a legal draft: identical token maps, both models load with strict weights."""
    from mlx_lm.utils import load_model  # noqa: PLC0415

    target = _model_dir(str(cfg["target"]["model_id"]))
    draft_src = _expand(cfg["draft"]["source_dir"])
    print("target:", target)
    print("draft :", draft_src)

    tgt_cfg = _read_json(target / "config.json")
    print("target model_type=" + str(tgt_cfg.get("model_type"))
          + " text.model_type=" + str((tgt_cfg.get("text_config") or {}).get("model_type"))
          + " expect=" + str(cfg["target"]["expect_model_type"]))
    text_cfg = tgt_cfg.get("text_config") or {}
    print("target vocab_size=" + str(text_cfg.get("vocab_size")) + " expect=" + str(cfg["target"]["expect_vocab"]))
    if text_cfg.get("vocab_size") != int(cfg["target"]["expect_vocab"]):
        raise SystemExit("specdec_probe: target vocab drifted from the declared reading")

    gate = _gate_tokenizers(target, draft_src)
    print("tokenizer vocab  : target n=" + str(gate["target"]["vocab_size"]) + " draft n=" + str(gate["draft"]["vocab_size"])
          + " identical=" + str(gate["same"]["vocab"]))
    print("tokenizer merges : target n=" + str(gate["target"]["merges_n"]) + " draft n=" + str(gate["draft"]["merges_n"])
          + " identical=" + str(gate["same"]["merges"]))
    print("added tokens     : target n=" + str(gate["target"]["added_n"]) + " draft n=" + str(gate["draft"]["added_n"])
          + " identical=" + str(gate["same"]["added_tokens"]))
    if not gate["identical"]:
        raise SystemExit("specdec_probe: REFUSED — draft tokenizer is not the target's tokenizer")

    started = time.perf_counter()
    _model, _tcfg = load_model(target, lazy=True)
    print("target strict load: OK | s=" + str(round(time.perf_counter() - started, 1)))

    override = _draft_model_config(cfg, draft_src)
    started = time.perf_counter()
    dm, _ = load_model(draft_src, lazy=False, strict=True, model_config=override)
    import mlx.utils as mxu  # noqa: PLC0415

    n_params = sum(v.size for _, v in mxu.tree_flatten(dm.parameters()))
    print("draft strict load : OK | params=" + str(round(n_params / 1e6, 1)) + "M | alias="
          + (json.dumps(_alias(cfg)) if override is not None else "not needed")
          + " | s=" + str(round(time.perf_counter() - started, 1)))
    print("VERIFY PASS")
    return 0


def _pool_residency() -> dict[str, Any]:
    """Record what was resident during the reading (BUG-803: a bill taken against a crowded pool is pessimistic)."""
    import psutil  # noqa: PLC0415

    rss_gb = 0.0
    for proc in psutil.process_iter(["name", "cmdline", "memory_info"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or [])
            if "omlx" in cmd.lower():
                rss_gb += (proc.info.get("memory_info").rss if proc.info.get("memory_info") else 0) / 1e9
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"omlx_rss_gb": round(rss_gb, 2), "host_available_gb": round(psutil.virtual_memory().available / 1e9, 2)}


def _prompts(cfg: dict[str, Any], tokenizer: Any) -> list[dict[str, Any]]:
    """Materialise the declared prompts; `file_head` is truncated to the declared token budget.

    A wrapped prompt (prefix/suffix) is required for a file_head: MEASURED 2026-10-27, a bare source-file head
    makes a chat model emit EOS at token 1, and a 1-token generation yields a nonsense decode rate.
    """
    out: list[dict[str, Any]] = []
    for spec in cfg["bench"]["prompts"]:
        if spec["kind"] == "literal":
            text = str(spec["text"])
        elif spec["kind"] == "file_head":
            body = (ROOT / str(spec["path"])).read_text(encoding="utf-8")
            budget = int(spec["target_tokens"])
            while len(tokenizer.encode(body)) > budget and body:
                body = body[: int(len(body) * 0.95)]
            text = str(spec["prefix"]) + body + str(spec["suffix"])
        else:
            raise SystemExit("specdec_probe: unknown prompt kind " + str(spec["kind"]))
        out.append({"name": str(spec["name"]), "text": text})
    return out


def _cache_refusal(model: Any) -> Optional[str]:
    """Return WHY speculative decoding cannot run on this model, or None when the cache is trimmable.

    WHY this is a measurement and not a guess: `speculative_generate_step` rewinds the cache after a partial
    acceptance, so it hard-refuses a non-trimmable cache. Qwen3.8's hybrid linear-attention layers use
    ArraysCache, which declares no `is_trimmable`, so the refusal is structural — not a flag to flip.
    """
    from mlx_lm.models import cache as mlx_cache  # noqa: PLC0415

    model_cache = mlx_cache.make_prompt_cache(model)
    if mlx_cache.can_trim_prompt_cache(model_cache):
        return None
    blocked = sorted({type(c).__name__ for c in model_cache if not c.is_trimmable()})
    return (
        "REFUSED: target prompt cache is not trimmable ("
        + ", ".join(blocked)
        + ") — mlx_lm speculative draft+verify requires cache rewind after partial acceptance"
    )


def _run_once(model: Any, tokenizer: Any, prompt: str, max_tokens: int, draft_model: Any, num_draft: int) -> dict[str, Any]:
    """One generation, returning the runtime's own prefill/decode readings (never a stopwatch guess)."""
    import mlx.core as mx  # noqa: PLC0415
    from mlx_lm import stream_generate  # noqa: PLC0415

    kwargs: dict[str, Any] = {"max_tokens": max_tokens}
    if draft_model is not None:
        kwargs["draft_model"] = draft_model
        kwargs["num_draft_tokens"] = num_draft
    from_draft = 0
    total = 0
    last = None
    for resp in stream_generate(model, tokenizer, prompt, **kwargs):
        last = resp
        total += 1
        from_draft += 1 if getattr(resp, "from_draft", False) else 0
    mx.clear_cache()
    if last is None:
        raise SystemExit("specdec_probe: stream_generate yielded nothing")
    return {
        "prompt_tokens": int(last.prompt_tokens),
        "prompt_tps": float(last.prompt_tps),
        "generation_tokens": int(last.generation_tokens),
        "generation_tps": float(last.generation_tps),
        "peak_memory_gb": round(float(getattr(last, "peak_memory", 0.0)), 2),
        "draft_share": round(from_draft / total, 4) if total else 0.0,
        "decode_context_tokens": int(last.prompt_tokens) + int(last.generation_tokens),
    }


def _append_receipt(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append rows to the JSONL receipt with an fsync, so a crash cannot leave a half-line (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _cmd_bench(cfg: dict[str, Any], args: argparse.Namespace) -> int:
    """Measure baseline vs draft+verify on the SAME loaded target, at the declared context lengths."""
    from mlx_lm import load  # noqa: PLC0415

    bench = cfg["bench"]
    target = _model_dir(str(cfg["target"]["model_id"]))
    draft_path = _expand(cfg["draft"]["mlx_out_dir"])
    if args.no_draft:
        draft_path = None
    elif not draft_path.exists():
        raise SystemExit(
            "specdec_probe: converted draft missing at " + str(draft_path) + " — run: python3 scripts/specdec_probe.py convert"
        )

    gate = _gate_tokenizers(target, _expand(cfg["draft"]["source_dir"]))
    if not gate["identical"]:
        raise SystemExit("specdec_probe: REFUSED — draft tokenizer differs from the target's")

    print("loading target:", target)
    started = time.perf_counter()
    model, tokenizer = load(str(target))
    print("target loaded | s=" + str(round(time.perf_counter() - started, 1)))

    draft_model = None
    if draft_path is not None:
        print("loading draft:", draft_path)
        started = time.perf_counter()
        draft_model, _ = load(str(draft_path), model_config=_draft_model_config(cfg, draft_path))
        print("draft loaded | s=" + str(round(time.perf_counter() - started, 1)))

    max_tokens = int(args.max_tokens or bench["max_tokens"])
    num_draft = int(args.draft_tokens or bench["num_draft_tokens"])
    repeats = int(args.repeats or bench["repeats"])
    seen_floor = int(bench["seen_floor"])
    min_decode = int(bench["min_decode_tokens"])
    residency = _pool_residency()
    prompts = _prompts(cfg, tokenizer)

    # A refusal is a READING, not a crash: it is recorded in the receipt so nobody can claim draft+verify ran.
    refusal = _cache_refusal(model) if draft_model is not None else None
    if refusal is not None:
        print("DRAFT MODE " + refusal)
    modes: list[tuple[str, Any]] = [("baseline", None)]
    if draft_model is not None and refusal is None:
        modes.append(("draft", draft_model))
    elif draft_model is not None:
        rows_refused = [{
            "name": "*", "mode": "draft", "rep": 0, "num_draft_tokens": num_draft,
            "prompt_tokens": 0, "prompt_tps": None, "prefill_verdict": "n/a",
            "generation_tokens": 0, "decode_context_tokens": 0, "generation_tps": None,
            "draft_share": 0.0, "peak_memory_gb": 0.0, "pool_residency": residency,
            "status": refusal, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }]
        _append_receipt(ROOT / str(bench["receipt"]), rows_refused)
        print("refusal row appended:", ROOT / str(bench["receipt"]))

    rows: list[dict[str, Any]] = []
    for prompt in prompts:
        for mode, dm in modes:
            _run_once(model, tokenizer, prompt["text"], int(bench["warmup_tokens"]), dm, num_draft)
            readings = [
                _run_once(model, tokenizer, prompt["text"], max_tokens, dm, num_draft) for _ in range(repeats)
            ]
            med = {k: statistics.median([r[k] for r in readings]) for k in readings[0]}
            enough = int(med["generation_tokens"]) >= min_decode
            rows.append({
                "name": prompt["name"],
                "mode": mode,
                "rep": repeats,
                "num_draft_tokens": num_draft if dm is not None else 0,
                "prompt_tokens": int(med["prompt_tokens"]),
                "prompt_tps": round(med["prompt_tps"], 2),
                "prefill_verdict": "comparable" if med["prompt_tokens"] >= seen_floor else "INCOMPARABLE (<seen_floor)",
                "generation_tokens": int(med["generation_tokens"]),
                "decode_context_tokens": int(med["decode_context_tokens"]),
                "generation_tps": round(med["generation_tps"], 3) if enough else None,
                "draft_share": round(med["draft_share"], 4),
                "peak_memory_gb": med["peak_memory_gb"],
                "pool_residency": residency,
                "status": "OK" if enough else "INSUFFICIENT: generation ended at " + str(int(med["generation_tokens"])) + " tokens",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

    print("\n| prompt | mode | prompt_tok | prefill t/s | prefill verdict | decode t/s | decode ctx | draft share | peak GB |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        tps = "n/a" if r["generation_tps"] is None else str(r["generation_tps"])
        print(f"| {r['name']} | {r['mode']} | {r['prompt_tokens']} | {r['prompt_tps']} | {r['prefill_verdict']} | "
              f"{tps} | {r['decode_context_tokens']} | {r['draft_share']} | {r['peak_memory_gb']} |")

    print("\nspeedup (draft / baseline), same prompt:")
    for prompt in prompts:
        pair = {r["mode"]: r for r in rows if r["name"] == prompt["name"]}
        if "draft" in pair and "baseline" in pair:
            base = pair["baseline"]["generation_tps"]
            spec = pair["draft"]["generation_tps"]
            if base and spec:
                print(f"  {prompt['name']}: decode {base} -> {spec} = {round(spec / base, 3)}x | "
                      f"prefill {pair['baseline']['prompt_tps']} -> {pair['draft']['prompt_tps']} = "
                      f"{round(pair['draft']['prompt_tps'] / pair['baseline']['prompt_tps'], 3)}x")
    if refusal is not None:
        print("  no draft mode measured: " + refusal)

    _append_receipt(ROOT / str(bench["receipt"]), rows)
    print("\nreceipt appended:", ROOT / str(bench["receipt"]))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """Dispatch the three probe steps."""
    cfg = _cfg()
    parser = argparse.ArgumentParser(description="speculative-decoding probe (MLX, Apple Silicon)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="tokenizer gate + strict loads")
    sub.add_parser("convert", help="quantise the draft from a normalised staging copy")
    bench = sub.add_parser("bench", help="measure baseline vs draft+verify")
    bench.add_argument("--draft-tokens", type=int, default=None)
    bench.add_argument("--max-tokens", type=int, default=None)
    bench.add_argument("--repeats", type=int, default=None)
    bench.add_argument("--no-draft", action="store_true", help="baseline only (control run)")
    args = parser.parse_args(argv)

    if args.cmd == "verify":
        return _cmd_verify(cfg)
    if args.cmd == "convert":
        return _cmd_convert(cfg)
    return _cmd_bench(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
