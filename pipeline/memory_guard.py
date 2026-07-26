#!/usr/bin/env python3
"""
memory_guard.py — Prevent OMLX kernel-level wired memory leaks.

GitHub #2184: macOS jetsam kills leak wired memory → reboot-only recovery.
GitHub #702:  OMLX process memory enforcer can't prevent jetsam kills.

This module adds a pre-flight memory check to the pipeline — refuse to
run if free memory is below the safety threshold.
"""

import sys


def _free_memory_gb() -> float:
    """Get free memory in GB from vm_stat."""
    try:
        import subprocess
        result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return -1.0
        stats = {}
        for line in result.stdout.splitlines():
            if ":" in line:
                key, val = line.rsplit(":", 1)
                try:
                    stats[key.strip()] = int(val.strip().rstrip("."))
                except ValueError:
                    pass
        page_size = stats.get("page size of", 16384)
        free_pages = stats.get("Pages free", 0)
        return (free_pages * page_size) / (1024 ** 3)
    except Exception:
        return -1.0


def check_memory(min_free_gb: float = 8.0, verbose: bool = True) -> bool:
    """Check if enough free memory is available for OMLX pipeline work.

    Refuses to proceed if free memory is below min_free_gb — this prevents
    macOS jetsam from killing OMLX and leaking wired memory (reboot-only fix).

    Args:
        min_free_gb: Minimum free memory in GB (default 8.0 — enough for
                     KV cache headroom on top of 21GB models).
        verbose: Print status to stdout.

    Returns:
        True if safe to proceed.
    """
    free = _free_memory_gb()
    if verbose:
        print(f"  Free memory: {free:.1f} GB (need ≥{min_free_gb:.0f} GB)")

    if free < 0:
        if verbose:
            print("  ⚠️  Could not determine free memory — proceeding with caution")
        return True  # Don't block if we can't measure

    if free < min_free_gb:
        if verbose:
            print(f"  ❌ INSUFFICIENT MEMORY — {free:.1f} GB free, need ≥{min_free_gb:.0f} GB")
            print("  Risk: macOS jetsam may kill OMLX → wired memory leak → reboot required")
            print("  Action: Close applications or reboot before running pipeline")
        return False

    if verbose:
        print(f"  ✅ Memory OK ({free:.1f} GB free)")
    return True


# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Check memory before pipeline run")
    p.add_argument("--min-gb", type=float, default=8.0, help="Min free memory in GB")
    args = p.parse_args()
    ok = check_memory(min_free_gb=args.min_gb, verbose=True)
    sys.exit(0 if ok else 1)
