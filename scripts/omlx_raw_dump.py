#!/usr/bin/env python3
"""Dump the FULL oMLX response for one suite item: content vs tool_calls vs reasoning_content.

WHY: the harness reads response[choices][0][message][content] and nothing else. If a model returns
its answer in a native tool_calls field, or only in reasoning_content, then content is EMPTY and the
harness records a failure that says nothing about the model. gemma-4-E4B returned 0 characters in
1.8s on four consecutive toolcalling attempts - far too fast to be thinking - which is the signature
of an answer arriving in a field nobody reads. This shows exactly which field carries the answer.

    python3 scripts/omlx_raw_dump.py --suite toolcalling --model gemma-4-E4B-it-MLX-4bit
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from model_eval_suite import SUITES  # noqa: E402
from bench_preflight import load_config  # noqa: E402


def dump(cfg: dict, model: str, suite: str, index: int) -> dict:
    """POST one item and return the parsed response plus a field-level summary."""
    item = SUITES[suite]()[index]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": item["system"]},
                     {"role": "user", "content": item["user"]}],
        "max_tokens": int(item.get("max_tokens", 512)),
        "temperature": 0.0,
    }
    url = cfg["omlx"]["base_url"].rstrip("/") + "/v1/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + cfg["omlx"]["api_key"]})
    with urllib.request.urlopen(req, timeout=int(cfg["omlx"]["timeout_s"])) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    msg = ((body.get("choices") or [{}])[0].get("message") or {})
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    tool_calls = msg.get("tool_calls") or []
    return {
        "item_id": item.get("id"), "max_tokens": payload["max_tokens"],
        "top_level_keys": sorted(body.keys()),
        "message_keys": sorted(msg.keys()),
        "content_chars": len(content),
        "reasoning_chars": len(reasoning),
        "n_tool_calls": len(tool_calls),
        "content_head": content.strip().replace(chr(10), " ")[:300],
        "reasoning_head": reasoning.strip().replace(chr(10), " ")[:200],
        "tool_calls": json.dumps(tool_calls)[:300],
        "finish_reason": ((body.get("choices") or [{}])[0].get("finish_reason")),
    }


def main() -> int:
    """Dump one or more models and print the field-level summary."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--models", nargs="*", required=True, help="comma or space separated")
    ap.add_argument("--index", type=int, default=0)
    args = ap.parse_args()

    cfg = load_config()
    models = [m for chunk in args.models for m in chunk.split(",") if m.strip()]
    out = []
    for model in models:
        print("=" * 88)
        print(model + "   suite=" + args.suite + "  item=" + str(args.index))
        print("=" * 88)
        try:
            rec = dump(cfg, model, args.suite, args.index)
        except Exception as exc:
            print("  CALL FAILED: " + type(exc).__name__ + ": " + str(exc)[:150])
            continue
        for key in ("finish_reason", "content_chars", "reasoning_chars", "n_tool_calls"):
            print("  " + key.ljust(18) + str(rec[key]))
        print("  message_keys      " + str(rec["message_keys"]))
        if rec["content_head"]:
            print("  content_head      " + rec["content_head"][:120])
        if rec["reasoning_head"]:
            print("  reasoning_head    " + rec["reasoning_head"][:120])
        if rec["n_tool_calls"]:
            print("  tool_calls        " + rec["tool_calls"][:150])
        out.append({"model": model, **rec})

    path = REPO / "governance" / ("omlx_raw_dump_" + args.suite + "_" + str(args.index) + ".json")
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  artifact: " + str(path.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
