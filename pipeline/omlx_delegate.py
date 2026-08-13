#!/usr/bin/env python3
"""omlx_delegate.py — local-LLM file-grounded delegation (BUG-063 fix).

BUG-063: the agent `delegate()` tool routes every provider through a
Deno/TypeScript sandbox with NO filesystem access, so
`delegate({provider: "maxwell_omlx", ...})` cannot read project files and fails
silently for any file-analysis task. The workaround was ad-hoc `curl` calls.

This module is the permanent fix (per BUG-063's own "Fix needed" note): a
`delegate_omlx()` function + CLI that runs in-process with REAL file access,
reads the files you name, injects them into the prompt, and calls the local
OMLX API directly via `pipeline.omlx_call.call_omlx`.

C12 config-first: the default model comes from `models.generator.model`
(GEN_MODEL); every model/URL/timeout is sourced from config, never hardcoded.

Usage (CLI):
    # Ask about one file:
    python3 pipeline/omlx_delegate.py --file pipeline/stage2_extract.py \
        --prompt "Summarize the fail-closed resume logic"

    # Multiple files + a system role + explicit model:
    python3 pipeline/omlx_delegate.py --model gemma-4-E4B-it-MLX-4bit \
        --file a.py --file b.py --system "You are a C12 auditor" \
        --prompt "Find hardcoded strings"

    # Prompt from stdin (no --prompt):
    printf "Classify this pipeline stage" | python3 pipeline/omlx_delegate.py \
        --file pipeline/stage4_merge.py

    # JSON output (parses the response, raises on malformed JSON):
    python3 pipeline/omlx_delegate.py --file config/pipeline_config.yaml \
        --json --prompt "Return the models section as JSON"

Importable:
    from pipeline.omlx_delegate import delegate_omlx
    text = delegate_omlx("Summarize this", files=["pipeline/runner.py"], model=GEN_MODEL)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow direct execution (`python3 pipeline/omlx_delegate.py`) without the
# project root on PYTHONPATH — mirrors the bootstrap in stage2_extract.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# NOTE: pipeline_paths materializes run-scoped paths on import; importing it here
# is safe (no run-id side effect for a read-only helper). omlx_call imports it too.
from pipeline.omlx_call import call_omlx, call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL, GEN_MAX_TOKENS

# D2344: file-injection markers — config-free but stable; used only to delimit
# injected file contents in the prompt (not a magic threshold/path/model).
_FILE_BLOCK_FENCE = "```"


def delegate_omlx(
    prompt: str,
    *,
    files: list[str] | None = None,
    model: str = GEN_MODEL,
    system: str | None = None,
    max_tokens: int = GEN_MAX_TOKENS,
    as_json: bool = False,
) -> str:
    """Call a local OMLX model with filesystem-grounded context (BUG-063).

    Reads each path in `files`, injects their contents as fenced blocks, and
    sends the combined prompt to the local OMLX API. Unlike `delegate()`, this
    runs with real file access.

    Args:
        prompt: The instruction/question for the model.
        files: Optional paths to read and inject as context (relative to CWD).
        model: OMLX model name (default GEN_MODEL from config).
        system: Optional system message.
        max_tokens: Max tokens to generate.
        as_json: If True, parse the response as JSON (raises on malformed output).

    Returns:
        Generated text (or, when as_json=True, the JSON text — callers may
        `json.loads` the result).

    Raises:
        FileNotFoundError: If any `files` path does not exist.
        RuntimeError: If the OMLX call fails (circuit breaker / retries exhausted).
        ValueError: If as_json=True and the response is not parseable JSON.
    """
    files = files or []
    context_blocks: list[str] = []
    for path_str in files:
        p = Path(path_str)
        if not p.exists():
            raise FileNotFoundError(f"delegate_omlx: file not found: {path_str}")
        # read_text errors propagate (no silent swallow, C16).
        text = p.read_text(encoding="utf-8")
        context_blocks.append(
            f"{_FILE_BLOCK_FENCE} {p.name}\n{text}\n{_FILE_BLOCK_FENCE}"
        )

    full_prompt: str
    if context_blocks:
        full_prompt = (
            "The following files are provided as context. Answer using ONLY what "
            "is shown; do not fabricate file contents.\n\n"
            + "\n\n".join(context_blocks)
            + f"\n\nTask: {prompt}"
        )
    else:
        full_prompt = prompt

    if as_json:
        # call_omlx_json sets its own JSON system prompt when system is None.
        result = call_omlx_json(
            prompt=full_prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
        )
        import json

        return json.dumps(result, ensure_ascii=False, indent=2)

    return call_omlx(
        prompt=full_prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser (no hardcoded defaults — from config)."""
    parser = argparse.ArgumentParser(
        description="File-grounded local-LLM delegation (BUG-063 fix).",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Instruction/question. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Path to inject as context. Repeatable.",
    )
    parser.add_argument(
        "--model",
        default=GEN_MODEL,
        help=f"OMLX model name (default: {GEN_MODEL}).",
    )
    parser.add_argument(
        "--system",
        default=None,
        help="Optional system message.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=GEN_MAX_TOKENS,
        help=f"Max tokens to generate (default: {GEN_MAX_TOKENS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Parse the response as JSON (raises on malformed output).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    prompt = args.prompt
    if prompt is None:
        prompt = sys.stdin.read().strip()
    if not prompt:
        parser.error("--prompt is required when stdin is empty")

    try:
        result = delegate_omlx(
            prompt,
            files=args.file,
            model=args.model,
            system=args.system,
            max_tokens=args.max_tokens,
            as_json=args.json,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
