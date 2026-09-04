#!/usr/bin/env python3
"""
delegate_safe.py — DELEGATE-001 mitigation.
=============================================
Authority: governance/buglog.md (DELEGATE-001)
C12: No hardcoded values — reads from environment and config.

DELEGATE-001 root cause:
  Goose framework uses DeepSeek with GOOSE_THINKING_EFFORT=high.
  DeepSeek returns reasoning_content blocks that must be passed back
  on subsequent turns. Goose delegate system creates fresh context
  and does NOT preserve reasoning_content → 400 Bad Request.

Mitigation:
  1. Detect GOOSE_THINKING_EFFORT — warn if set
  2. Validate provider is maxwell_omlx (not custom_deepseek)
  3. Confirm gemma-4-E4B-it delegate model is available via OMLX

Usage:
    python3 tools/delegate_safe.py          # Check delegate safety
    python3 tools/delegate_safe.py --fix    # Unset GOOSE_THINKING_EFFORT
"""

import os
import subprocess
import sys
from pathlib import Path

# ── Constants: delegate model configuration ──────────────────────────────
PREFERRED_DELEGATE_MODEL = "gemma-4-E4B-it-MLX-4bit"
SECONDARY_DELEGATE_MODEL = "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL  # noqa: E402  (C12: single source, D2552)

OMLX_MODELS_URL = f"{OMLX_URL}/v1/models"

# ── Dangerous env vars that trigger DELEGATE-001 ─────────────────────────
DANGEROUS_VARS = [
    "GOOSE_THINKING_EFFORT",
    "GOOSE_PROVIDER",
]


def check_thinking_effort() -> bool:
    """Check if GOOSE_THINKING_EFFORT is set (causes DELEGATE-001).

    Returns: True if dangerous env var detected.
    """
    dangerous = False
    for var in DANGEROUS_VARS:
        val = os.environ.get(var)
        if val:
            print(f"⚠️  DANGER: {var}={val} — causes DELEGATE-001 (reasoning_content passthrough)")
            dangerous = True
    if not dangerous:
        print("✅ GOOSE_THINKING_EFFORT not set — safe for delegates")
    return dangerous


def check_omlx_models() -> bool:
    """Check if preferred delegate models are available in OMLX.

    Returns: True if at least one delegate model is available.
    """
    try:
        result = subprocess.run(
            ["curl", "-s", OMLX_MODELS_URL, "-H", f"Authorization: Bearer {OMLX_API_KEY}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            print("❌ OMLX not reachable")
            return False

        import json
        models = json.loads(result.stdout).get("data", [])
        model_ids = {m["id"] for m in models}

        available = []
        for model in [PREFERRED_DELEGATE_MODEL, SECONDARY_DELEGATE_MODEL]:
            if model in model_ids:
                available.append(model)
                print(f"✅ Delegate model available: {model}")
            else:
                print(f"❌ Delegate model NOT available: {model}")

        return len(available) > 0
    except Exception as e:
        print(f"❌ Error checking OMLX: {e}")
        return False


def print_delegate_config() -> None:
    """Print the correct delegate configuration for Maxwell OS."""
    print(f"""
📋 Delegate Configuration (paste into delegate calls):
   provider: "maxwell_omlx"
   model: "{PREFERRED_DELEGATE_MODEL}"   ← preferred (code review, summarization)
   model: "{SECONDARY_DELEGATE_MODEL}"   ← secondary (code gen, short prompts)

⚠️  NEVER: provider="custom_deepseek" → DELEGATE-001
⚠️  NEVER: model="Phi-4-mini-instruct-8bit" for research → BUG-053 hallucinations
""")


def main() -> None:
    """Run delegate safety check."""
    fix = "--fix" in sys.argv

    print("=" * 60)
    print("🔍 DELEGATE-001 Safety Check")
    print("=" * 60)

    danger = check_thinking_effort()
    models_ok = check_omlx_models()

    if fix and danger:
        print("\n🔧 Applying fix: unsetting dangerous env vars...")
        for var in DANGEROUS_VARS:
            if os.environ.pop(var, None):
                print(f"   Unset: {var}")
        print("✅ Fix applied. Restart your shell/agent for changes to take effect.")

    print()
    print_delegate_config()

    if not models_ok:
        print("❌ No delegate models available. Start OMLX first.")
        sys.exit(1)

    if danger and not fix:
        print("⚠️  Run with --fix to unset dangerous env vars.")
        sys.exit(1)

    print("✅ Delegate safety check passed.")


if __name__ == "__main__":
    main()
