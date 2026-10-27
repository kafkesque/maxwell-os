#!/usr/bin/env python3
"""measure_prefill.py — THE COLD-PREFILL RECEIPT (BUG-793, measurement-gated D-332).

WHY. The one number that decides whether a model can host an agent loop is its PREFILL throughput:
how many prompt tokens it ingests per second on a COLD prompt (no prefix cache). MEASURED 2026-10-14,
Qwen3.8-27B-MLX-4bit ingests 39 tok/s where gpt-oss-20b-MXFP4-Q8 ingests 210 — but every re-check was
a hand-rolled curl, and a hand-rolled curl is the reason the first attempt at this used a flag that
does not exist. This script is the PERMANENT instrument: one command, the server's OWN counters, a
receipt that decides.

WHAT IT DOES. Sends ONE chat completion (max_tokens=1, temperature=0.0) whose prompt is a declared
filler repeated to the requested token count, then prints the server's own counters verbatim:
prompt_tokens_per_second (the prefill rate), time_to_first_token, generation_tokens_per_second and
model_load_duration. It writes nothing and sends one prompt.

WHY THE PROMPT NOW CARRIES A NONCE (BUG-1044, MEASURED 2026-10-27). The prompt this script built was
DETERMINISTIC, and the engine caches prompt prefixes: two consecutive runs of the same command returned
39.22 s (cold) and 0.54 s (a prefix-cache hit) for the same 2060-token prompt. An A/B that measures a
COLD baseline and then a CACHED post-change run reports a ~70x "speedup" that is pure cache. So every
call now prepends a random tag (`nonce_chars`, config/agent_context.yaml#prefill_budget.ab_probe) and the
server's own `prompt_tokens_details.cached_tokens` is reported with the reading; a cached reading is
UNMEASURED (exit 2), never a rate. --allow-cached reproduces the old behaviour deliberately.

C12. This file names no host, no port, no key, no filler and no token-per-char rate of its own: the
host/port come from config/engine.yaml (the engine's one home), the key from
pipeline.pipeline_paths.OMLX_API_KEY, and the filler + chars-per-token rate from
config/agent_context.yaml#prefill_budget.ab_probe. --selftest proves that by reading its own bytes.

Usage:
    python3 scripts/measure_prefill.py --model Qwen3.8-27B-MLX-4bit --tokens 26214
    python3 scripts/measure_prefill.py --model Qwen3.8-27B-MLX-4bit --tokens 4000 --json
    python3 scripts/measure_prefill.py --selftest

Exit: 0 measured | 2 the server returned no counters (unmeasured) | 1 the probe itself failed
"""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:                      # the repo idiom: runnable AND importable (C21)
    sys.path.insert(0, str(ROOT))

ENGINE_CFG = ROOT / "config" / "engine.yaml"
AGENT_CFG = ROOT / "config" / "agent_context.yaml"

OK, UNMEASURED, FATAL = 0, 2, 1

#: The tokens this file must never write down as literals (C12 self-scan): a host, a port, a filler
#: unit, a chars-per-token rate. They all live in config/.
FORBIDDEN = ("127.0.0.1", "11435", "the quick brown fox", "4.5")


class ProbeFault(SystemExit):
    """Fail-closed: an unreadable declaration is a fault, never a silent pass (C16)."""


def _yaml(path: pathlib.Path) -> dict:
    import yaml

    if not path.is_file():
        raise ProbeFault(f"FATAL: {path} is absent — it is the one home of these facts (C12)")
    doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(doc, dict):
        raise ProbeFault(f"FATAL: {path} does not parse to a mapping")
    return doc


def engine_endpoint() -> tuple[str, str]:
    """Host and port from the engine's ONE home (config/engine.yaml)."""
    engine = _yaml(ENGINE_CFG)["engine"]
    return str(engine["host"]), str(engine["port"])


def api_key() -> str:
    """The engine key from its one home (a pointer, never a literal)."""
    from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: PLC0415 - kept out of import surface

    return str(OMLX_API_KEY)


def filler_unit() -> tuple[str, float]:
    """The declared filler and its MEASURED chars-per-token rate (config/agent_context.yaml)."""
    cfg = _yaml(AGENT_CFG)
    ab = cfg["prefill_budget"]["ab_probe"]
    return str(ab["filler"]), float(ab["chars_per_token_measured"])


def nonce_chars() -> int:
    """Length of the uniqueness tag that makes a run cold (config/agent_context.yaml#prefill_budget.ab_probe).

    BUG-1044: without it the prompt is byte-identical between runs and the engine answers the second
    call from its prefix cache -- a reading that looks like a 70x speedup and measures nothing."""
    cfg = _yaml(AGENT_CFG)
    return int(cfg["prefill_budget"]["ab_probe"]["nonce_chars"])


def build_prompt(tokens: int, filler: str, per_unit: float, tag: str = "") -> str:
    """Repeat the declared filler to the requested token count (the same arithmetic the probe uses).

    `tag`, when given, is prepended so the prefix cache cannot serve this call (BUG-1044). It is counted
    against the budget so the prompt keeps its declared size (the ANE/fixed-shape path needs a stable one)."""
    if tag:
        tokens = max(1, tokens - 1)  # the tag is one short line; its tokens come out of the declared budget
    chars = int(tokens * per_unit)
    body = (filler * (chars // len(filler) + 1))[:chars]
    return (tag + "\n" + body) if tag else body


def measure(model: str, tokens: int, timeout: int, max_tokens: int = 1,
            cold: bool = True, allow_cached: bool = False) -> dict:
    """Send ONE prompt and return the server's own counters, verbatim.

    max_tokens=1 is the PREFILL receipt; a decode rate read at max_tokens=1 is a single-token artifact
    (D-3102), so a real decode rate is read with --max-tokens >= 128.

    `cold` prepends a random tag so the engine cannot serve the call from its prefix cache (BUG-1044);
    `allow_cached` keeps the reading but marks it, for the deliberate case where a cache hit IS the subject.
    """
    filler, per_unit = filler_unit()
    if not filler or per_unit <= 0:
        raise ProbeFault("FATAL: the declaration names no filler or its chars-per-token rate (C12)")
    host, port = engine_endpoint()
    url = f"http://{host}:{port}/v1/chat/completions"
    tag = "run-tag " + secrets.token_hex(nonce_chars() // 2) if cold else ""
    prompt = build_prompt(tokens, filler, per_unit, tag)
    payload = {
        "model": model, "max_tokens": max_tokens, "temperature": 0.0, "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key()}"}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - declared home
            doc = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        raise ProbeFault(f"FATAL: the engine refused or did not answer ({exc})") from exc
    usage = doc.get("usage") or {}
    #: the server's OWN counters live inside `usage`, not at the top level (measured live).
    counters = {k: usage.get(k) for k in (
        "time_to_first_token", "total_time", "generation_tokens_per_second",
        "prompt_tokens_per_second", "model_load_duration")}
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    return {
        "model": model, "prompt_chars": len(prompt),
        "prompt_tokens": usage.get("prompt_tokens"),
        "cached_tokens": cached,
        "cold": bool(cold),
        "wall_seconds": round(time.time() - started, 1),
        "counters": counters,
    }


def render(result: dict) -> str:
    c = result["counters"]
    lines = [
        f"model: {result['model']}",
        f"prompt: {result['prompt_chars']:,} chars ~ {result['prompt_tokens']} tokens "
        f"(server-echoed) in {result['wall_seconds']} s wall",
        f"CACHE    : cached_tokens={result.get('cached_tokens')} "
        f"(cold_requested={result.get('cold')}) — 0 is a real prefill, anything else is NOT a rate",
        f"PREFILL  : {c.get('prompt_tokens_per_second')} tok/s   <-- the number that decides a loop",
        f"TTFT     : {c.get('time_to_first_token')} s",
        f"decode   : {c.get('generation_tokens_per_second')} tok/s",
        f"model ld : {c.get('model_load_duration')} s",
    ]
    return "\n".join(lines)


def selftest() -> int:
    """Known-answer controls: the filler arithmetic, and that THIS file hardcodes no forbidden value."""
    filler, per_unit = filler_unit()
    p = build_prompt(10, filler, per_unit)
    assert len(p) == 45 and p == filler, "10 declared tokens must build to exactly the 45-char unit"
    p2 = build_prompt(26214, filler, per_unit)
    assert len(p2) == int(26214 * per_unit), "the char count must be tokens * declared rate"
    # BUG-1044 control: a tagged prompt MUST differ between calls, or the engine serves it from cache
    tag_a, tag_b = "run-tag a", "run-tag b"
    assert build_prompt(2048, filler, per_unit, tag_a) != build_prompt(2048, filler, per_unit, tag_b), \
        "two tagged prompts must not be byte-identical (the cold guarantee is worthless if they are)"
    assert nonce_chars() >= 8, "a uniqueness tag shorter than 8 chars risks token-level prefix reuse"
    src = pathlib.Path(__file__).read_text(encoding='utf-8').split("#: The tokens this file must never", 1)[0]
    leaked = [lit for lit in FORBIDDEN if lit in src]
    assert not leaked, f"hardcoded value leaked into source: {leaked}"
    print("ok measure-prefill --selftest: 5/5 controls green "
          "(filler unit, chars-per-token rate, cold-tag uniqueness, tag length, no hardcoded value in source)")
    return OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cold-prefill receipt (BUG-793, D-332 measurement-gated)")
    ap.add_argument("--model", default="Qwen3.8-27B-MLX-4bit", help="the served model to measure")
    ap.add_argument("--tokens", type=int, default=26214, help="cold-prompt size in tokens")
    ap.add_argument("--max-tokens", type=int, default=1,
                    help="answer size; 1 = prefill receipt, >=128 = a real decode-rate benchmark (D-3102)")
    ap.add_argument("--timeout", type=int, default=1200, help="wall-clock ceiling for the one call")
    ap.add_argument("--json", action="store_true", help="emit the receipt as JSON")
    ap.add_argument("--no-cold", dest="cold", action="store_false",
                    help="do NOT prepend the uniqueness tag (reproduces the pre-BUG-1044 behaviour)")
    ap.add_argument("--allow-cached", action="store_true",
                    help="accept a reading whose cached_tokens > 0 instead of reporting it UNMEASURED")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls (offline)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    result = measure(args.model, args.tokens, args.timeout, args.max_tokens, args.cold, args.allow_cached)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(result))
    prefill = result["counters"].get("prompt_tokens_per_second")
    if prefill is None:
        print("UNMEASURED: the server returned no prompt_tokens_per_second counter", file=sys.stderr)
        return UNMEASURED
    cached = result.get("cached_tokens") or 0
    if cached and not args.allow_cached:
        print(f"UNMEASURED: cached_tokens={cached} of {result['prompt_tokens']} — the engine served this "
              f"from its prefix cache, so the rate above is a cache rate, not a prefill rate (BUG-1044)",
              file=sys.stderr)
        return UNMEASURED
    return OK


if __name__ == "__main__":
    sys.exit(main())
