#!/usr/bin/env python3
"""protect.py — Check if a domain is actively being converged before allowing destructive actions.
Run BEFORE any rm, kill, or overwrite on pipeline data.
Blocks if .running flag exists or checkpoint is recent.

Usage:
  python3 tools/protect.py domain_6_ai_computing --status   # Check if active
  python3 tools/protect.py domain_6_ai_computing --kill      # Allow kill with reason
  python3 tools/protect.py domain_6_ai_computing --rm-checkpoint  # Block if active
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from tools.pipeline_paths import RUNTIME_RUNNING_FLAG, STAGE_PATHS
from pipeline.io_guard import safe_write  # D2496: C6 crash-safe writes

RUNNING_FLAG = RUNTIME_RUNNING_FLAG


def domain_path(domain):
    return STAGE_PATHS["converged"] / domain


def is_running(domain):
    # Check 1: actual process
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    if f"s3_converge_local.py --domain {domain}" in r.stdout:
        return True
    # Check 2: .running flag
    if RUNNING_FLAG.exists() and domain in RUNNING_FLAG.read_text():
        return True
    # Check 3: checkpoint modified in last 30 min
    ck = domain_path(domain) / ".s3a_checkpoint.json"
    if ck.exists() and time.time() - os.path.getmtime(ck) < 1800:
        return True
    return False


def set_running(domain):
    """Call from s3_converge_local.py on start. Sets a domain-specific flag."""
    current = RUNNING_FLAG.read_text().strip().split("\n") if RUNNING_FLAG.exists() else []
    if domain not in current:
        safe_write(RUNNING_FLAG, "\n".join(current + [domain]))  # D2496: C6


def clear_running(domain):
    """Call from s3_converge_local.py on exit. Clears the flag."""
    if not RUNNING_FLAG.exists():
        return
    current = [l for l in RUNNING_FLAG.read_text().strip().split("\n") if l and l != domain]
    safe_write(RUNNING_FLAG, "\n".join(current) + "\n")  # D2496: C6


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: protect.py <domain> --status|--kill|--rm-checkpoint")
        sys.exit(1)

    domain = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--status"

    active = is_running(domain)

    if mode == "--status":
        print(f"{'⚠️  ACTIVE' if active else '✅ IDLE'}: {domain}")
        sys.exit(0 if not active else 1)

    elif mode == "--kill":
        if not active:
            print(f"✅ {domain} not active — safe to kill if process exists")
            sys.exit(0)
        if len(sys.argv) > 3:
            reason = sys.argv[3]
            print(f"⚠️  {domain} IS ACTIVE. Kill reason given: {reason}")
            print("Proceed with: kill -INT <PID>")
            sys.exit(0)
        else:
            print(f"❌ BLOCKED: {domain} is actively converging.")
            print(
                f"   Must provide reason: protect.py {domain} --kill 'checkpoint interval change'"
            )
            sys.exit(1)

    elif mode == "--rm-checkpoint":
        if active:
            print(f"❌ BLOCKED: {domain} is active. Cannot delete checkpoint.")
            sys.exit(1)
        print(f"✅ {domain} idle — checkpoint can be safely deleted")
        sys.exit(0)
