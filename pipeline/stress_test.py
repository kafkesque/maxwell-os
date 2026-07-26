#!/usr/bin/env python3
"""stress_test.py — Full OMLX pipeline readiness check.

Called by `just stress`. Tests:
  1. Memory check (≥6 GB free)
  2. OMLX chat at 50/1K/5K chars
  3. JSON extraction with pipeline-sized prompts

Exit 0 = ready, Exit 1 = not ready.
"""
import sys

from pipeline.memory_guard import check_memory
from pipeline.omlx_call import stress_test_omlx


def main():
    print("=== Memory Check ===")
    if not check_memory(min_free_gb=6.0):
        sys.exit(1)

    print("\n=== OMLX Chat Stress Test ===")
    result = stress_test_omlx(prompt_sizes=[50, 1000, 5000], verbose=True)
    if not result["healthy"]:
        print(f"\n❌ OMLX chat FAILED. Verdict: {result['verdict']}")
        print("   Restart OMLX and re-run: just stress")
        sys.exit(1)

    print(f"\n✅ OMLX pipeline-ready: {result['verdict']} (tested up to 5000 chars)")

if __name__ == "__main__":
    main()
