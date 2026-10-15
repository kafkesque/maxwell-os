#!/usr/bin/env python3
"""BUG-802 - THE ENGINE'S SURVIVAL, AS A READING.

MEASURED 2026-10-15: the engine was DOWN at session start after a CLEAN 02:11 shutdown, and nothing
starts it, so the whole local-capability layer (C1/C3) is absent until a human types a command. A
per-request failure discovered hours later is the wrong detector: this is the reading that reports the
engine's state, and whether a boot agent exists to bring it back, as a LADDER line.

Tri-state, by the repo's own convention (BUG-457): 0 = engine up AND a boot agent is declared/loaded;
2 = OWNER-OWED (engine down, or no boot agent installed - loud, not fatal); 1 = the engine answers but
DEGRADED (a model list that cannot be read is not an empty list).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2
PROBE = ["curl", "-sS", "-m", "6", "-o", "/dev/null", "-w", "%{http_code}"]
LABEL = "com.maxwell.omlx-engine"
TEMPLATE = Path("pipeline/com.maxwell.omlx-engine.plist")


def engine_state(url: str) -> str:
    """UP / DOWN - read from the engine's own health endpoint, never inferred from a log file."""
    try:
        out = subprocess.run(PROBE + [url], capture_output=True, text=True, check=False).stdout.strip()
    except OSError as exc:
        return f"UNKNOWN({exc})"
    return "UP" if out == "200" else f"DOWN({out or 'no response'})"


def boot_agent_state() -> dict[str, bool]:
    """Where the boot agent stands: the TEMPLATE is in the repo, the JOB is loaded or it is not.

    A launchd query that cannot be run is reported as False, never as True (fail-closed).
    """
    loaded = subprocess.run(["launchctl", "print", f"gui/{__import__('os').getuid()}/{LABEL}"],
                            capture_output=True, text=True, check=False).returncode == 0
    return {"template_in_repo": TEMPLATE.exists(), "job_loaded": loaded}


def main() -> int:
    """Report the engine's survival state; 2 when it is owner-owed, never silently 0."""
    ap = argparse.ArgumentParser(description="BUG-802 engine survival reading.")
    ap.add_argument("--url", default="http://127.0.0.1:11435/health")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    state = {"engine": engine_state(args.url), "boot_agent": boot_agent_state(), "url": args.url}
    if args.json:
        print(json.dumps(state, indent=1))
    else:
        print(f"  engine    {state['engine']} ({args.url})")
        ba = state["boot_agent"]
        print(f"  boot agent template_in_repo={ba['template_in_repo']} job_loaded={ba['job_loaded']}")
    if state["engine"].startswith("UNKNOWN"):
        print("FAIL engine-boot: the health endpoint could not be probed")
        return RC_FATAL
    if state["engine"] != "UP":
        print("OWNER-OWED engine-boot: the $0 engine is DOWN - every delegate lane, the S4 classifier and the pipeline generator depend on it")
        return RC_OWNER_OWED
    if not state["boot_agent"]["job_loaded"]:
        print("OWNER-OWED engine-boot: the engine is UP but NOTHING starts it after a reboot (BUG-802) - run pipeline/install_omlx_engine_agent.sh --confirm")
        return RC_OWNER_OWED
    return RC_OK


if __name__ == "__main__":
    raise SystemExit(main())
