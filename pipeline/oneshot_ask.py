#!/usr/bin/env python3
"""One deterministic question to one local model - the atom a fan-out is built from.

Why this exists rather than ten curl lines in a shell script: the engine contract (host, port, key
home) belongs in ONE place (C12), temperature is 0.0 always (R7), and the answer must land in a FILE
(an answer that exists only in stdout is lost the moment the terminal scrolls - BUG-809).

Usage:
    python3 pipeline/oneshot_ask.py --model gemma-4-E4B-it-MLX-4bit --prompt-file P.txt --out A.md
    python3 pipeline/oneshot_ask.py --model M --prompt "..." --max-tokens 256 --json-out meta.json

EXIT: 0 answer written; 1 the engine refused or returned nothing (fatal - never a silent empty file).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "engine.yaml"
TEMPERATURE = 0.0
OK, FATAL = 0, 1


def conf() -> dict:
    """Engine facts from their one home (C12)."""
    import yaml
    return yaml.safe_load(CONFIG.read_text(encoding='utf-8'))


def key() -> str:
    """The engine key from its one home."""
    sys.path.insert(0, str(ROOT))
    try:
        from pipeline.pipeline_paths import OMLX_API_KEY
        return str(OMLX_API_KEY)
    except Exception:
        return ""


def ask(model: str, prompt: str, max_tokens: int, timeout: int) -> tuple[str, dict]:
    """POST one chat completion and return (content, usage+timings)."""
    engine = conf()["engine"]
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": TEMPERATURE}
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", "POST",
           f"http://{engine['host']}:{engine['port']}/v1/chat/completions",
           "-H", f"Authorization: Bearer {key()}", "-H", "Content-Type: application/json",
           "-d", json.dumps(body)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20)
    try:
        doc = json.loads(proc.stdout)
    except Exception:
        return "", {"error": proc.stdout[:300] or proc.stderr[:300]}
    try:
        content = doc["choices"][0]["message"]["content"]
    except Exception:
        return "", {"error": json.dumps(doc)[:300]}
    return content, {"usage": doc.get("usage"), "time": {k: doc.get(k) for k in
            ("time_to_first_token", "total_time", "generation_tokens_per_second",
             "prompt_tokens_per_second", "model_load_duration")}}


def main(argv: list[str]) -> int:
    """Ask once, write the answer to a file, and say what it cost."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--max-tokens", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    fanout = conf().get("fanout")
    if not fanout or "default_max_tokens" not in fanout:
        print("FATAL: config/engine.yaml declares no fanout.default_max_tokens - refusing to invent one (C12)")
        return FATAL
    max_tokens = args.max_tokens or int(fanout["default_max_tokens"])
    prompt = args.prompt if args.prompt else pathlib.Path(args.prompt_file).read_text(encoding='utf-8')
    t0 = time.time()
    content, meta = ask(args.model, prompt, max_tokens, args.timeout)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content if content else "(no content returned)\n", encoding='utf-8')
    meta.update({"model": args.model, "wall_s": round(time.time() - t0, 2),
                 "prompt_chars": len(prompt), "answer_chars": len(content), "out": str(out)})
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(meta, indent=1), encoding='utf-8')
    if not content:
        print(f"FATAL: {args.model} returned no content: {meta.get('error', '')}")
        return FATAL
    print(f"ok: {args.model} answered {len(content)} chars in {meta['wall_s']}s -> {out}")
    return OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
