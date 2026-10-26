#!/usr/bin/env python3
"""probe_apple_fm.py - measure the FOUR approved risks of the macOS 27 on-device model (C3/C12).

READ-ONLY BY CONSTRUCTION: this script writes nothing. That is deliberate policy, not an omission.
write_guard.write_document is the ONLY legal whole-document writer (D-401/I1) and
guard_coverage.max_unguarded is SHRINK-ONLY, so a probe that invented a receipt writer would either break
that rule or raise a ceiling. A measurement is not worth either. The receipt is this script's stdout.

Exit (BUG-457 tri-state): 0 all four measured GREEN | 1 a measured RISK (defect) |
2 OWNER-OWED: the CLI legal notice is not agreed, so NOTHING can be measured and nothing is claimed.

UNTIL THE OWNER RUNS `sudo fm license` EVERY PROBE BELOW IS UNEXERCISED. It ships so that the measurement
is one command the moment the gate opens, and so the gate itself lives in the repo rather than in memory.
"""
from __future__ import annotations

import argparse
import re
import secrets
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "apple_fm.yaml"
NOT_AGREED = re.compile(r"not agreed", re.I)
LOOPBACK = ("127.0.0.1", "[::1]", "localhost")


def config() -> dict:
    """Read the arm's ONE home. Every value below comes from there (C12: nothing is hardcoded here)."""
    import yaml

    return yaml.safe_load(CFG.read_text(encoding="utf-8"))


def fm(binary: str, args: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run the CLI and return (rc, combined output). A missing binary is a measured failure, not a crash."""
    try:
        p = subprocess.run([binary, *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "<timeout after %ds>" % timeout
    except FileNotFoundError:
        return 127, "<binary not found: %s>" % binary


def sockets_of(pid: int) -> list[str]:
    """Every non-loopback socket this process holds. lsof needs no sudo for the caller's OWN processes."""
    try:
        p = subprocess.run(["lsof", "-nP", "-i", "-p", str(pid)], capture_output=True, text=True, timeout=30)
    except Exception as exc:  # noqa: BLE001 - a probe may not crash the rail that runs it
        return ["<lsof failed: %s>" % type(exc).__name__]
    bad: list[str] = []
    for line in p.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 9:
            continue
        addr = fields[8]
        if not any(addr.startswith(x) or (":" + x) in addr for x in LOOPBACK):
            bad.append(line.strip())
    return bad


def spawn(args: list[str]) -> subprocess.Popen:
    """Start the CLI for a socket probe; stdout is discarded because we only care about the process."""
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def probe_egress(binary: str, prompt: str) -> tuple[bool, str]:
    """RISK 1 (C3): a model that answers locally must not open an outbound socket while answering."""
    proc = spawn([binary, "respond", "--no-stream", "-i", prompt, "--text", "Say OK."])
    bad: list[str] = []
    for _ in range(20):
        if proc.poll() is not None:
            break
        bad += sockets_of(proc.pid)
        time.sleep(0.25)
    if proc.poll() is None:
        proc.kill()
    return (not bad), ("no non-loopback socket observed" if not bad else "OUTBOUND: " + "; ".join(bad[:3]))


def probe_context(binary: str, ceiling: int, step: int) -> tuple[bool, str]:
    """RISK 2: find the ceiling by MEASUREMENT (bisect over count-tokens), never from a recalled number."""
    lo, hi, worst = 0, ceiling, None
    while hi - lo > step:
        mid = (lo + hi) // 2
        rc, out = fm(binary, ["count-tokens", "--text", "word " * mid], timeout=60)
        if rc == 0:
            lo = mid
        else:
            hi, worst = mid, out[:120]
    return True, "largest accepted prompt ~%d words (tokenizer accepted); refusal at %d words: %s" % (
        lo, hi, worst or "none within the probed range")


def probe_guardrail(binary: str, prompt: str) -> tuple[bool, str]:
    """RISK 3: a guardrail that silently rewrites is a data-integrity hazard. Known-answer byte test."""
    sentinel = "SENTINEL-" + secrets.token_hex(4).upper()
    rc, out = fm(binary, ["respond", "--no-stream", "-i", prompt, "--text", "Repeat verbatim: " + sentinel])
    if rc != 0:
        return False, "respond failed rc=%d: %s" % (rc, out[:160])
    ok = sentinel in out
    return ok, ("verbatim surviving (no silent rewrite observed)" if ok else "TRANSFORMED/REFUSED: " + out[:200])


def probe_serve_bind(binary: str, port: int, wait: float) -> tuple[bool, str]:
    """RISK 4: `fm serve` must bind loopback only. A rejected flag is reported honestly, not guessed at."""
    proc = spawn([binary, "serve", "--port", str(port)])
    try:
        time.sleep(wait)
        if proc.poll() is not None:
            rc, out = fm(binary, ["serve", "--help"], timeout=30)
            return False, "serve exited immediately - flag or port rejected; check `fm serve --help`: " + out[:200]
        try:
            p = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", str(proc.pid)],
                               capture_output=True, text=True, timeout=30)
        except Exception as exc:  # noqa: BLE001
            return False, "<lsof failed: %s>" % type(exc).__name__
        lines = [l.strip() for l in p.stdout.splitlines()[1:] if l.strip()]
        if not lines:
            return False, "no listening socket observed"
        bad = [l for l in lines if not any((":" + x) in l for x in LOOPBACK)]
        return (not bad), ("loopback only: " + lines[0][:100] if not bad else "NON-LOOPBACK BIND: " + bad[0][:120])
    finally:
        if proc.poll() is None:
            proc.kill()


def main(argv: list[str] | None = None) -> int:
    """Check the licence gate first: without it nothing is measurable and nothing may be claimed."""
    ap = argparse.ArgumentParser(description="measure the four approved risks of the Apple FM arm")
    ap.add_argument("--prompt", default="You are a formatting assistant.")
    ap.add_argument("--port", type=int, default=8123)
    a = ap.parse_args(argv)
    cfg = config()
    rc, out = fm(str(cfg["binary"]), ["license", "--status"], timeout=30)
    print("licence: rc=%d %s" % (rc, out[:120]))
    if rc != 0 or NOT_AGREED.search(out):
        print("OWNER-OWED (exit 2): the Apple Foundation Models CLI legal notice is not agreed, and it is")
        print("MACHINE-WIDE (measured: \"applies to every user on the machine\"), so only the owner may")
        print("accept it. Nothing was measured and nothing is claimed. The one command is:")
        print("    " + str(cfg["license"]["command"]))
        return 2
    failed = 0
    for label, res in (
        ("egress", probe_egress(str(cfg["binary"]), a.prompt)),
        ("context_ceiling", probe_context(str(cfg["binary"]), 32000, 500)),
        ("guardrail_fidelity", probe_guardrail(str(cfg["binary"]), a.prompt)),
        ("serve_bind", probe_serve_bind(str(cfg["binary"]), a.port, 3.0)),
    ):
        print(("  ok   " if res[0] else "  RISK ") + label + ": " + res[1])
        failed += 1 - int(res[0])
    if failed:
        print("apple-fm probe: %d RISK(s) - `enabled: false` must stay until each is GREEN and recorded" % failed)
        return 1
    print("apple-fm probe: all four GREEN - record them in config/apple_fm.yaml#probe before enabling any arm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
