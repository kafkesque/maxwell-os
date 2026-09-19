#!/usr/bin/env python3
"""Restart the oMLX GUI app via its documented control socket (D2455).

The GUI app is the single source of truth for the oMLX server (the homebrew
formula was removed, D2455). Restarting through the control socket — rather than
`omlx restart` — avoids spawning a second managed server, which is the
D2455/D2456 duplicate-install failure mode that
scripts/guard_stacks_single_source.py exists to catch.

Usage: python3 scripts/_omlx_restart.py
"""
from __future__ import annotations

import json
import socket
from pathlib import Path

SOCK = Path.home() / "Library/Application Support/oMLX/control.sock"
NEWLINE = chr(10)


def main() -> int:
    """Send a restart command to the oMLX control socket and print the reply."""
    if not SOCK.exists():
        print("ERR control socket missing: " + str(SOCK))
        return 1
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(15)
            s.connect(str(SOCK))
            s.sendall((json.dumps({"command": "restart"}) + NEWLINE).encode())
            reply = s.recv(4096)
        print("sent restart; reply: " + (reply.decode(errors="replace")[:300] or "(empty)"))
        return 0
    except Exception as exc:
        print("ERR " + type(exc).__name__ + ": " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
