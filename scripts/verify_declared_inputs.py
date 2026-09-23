#!/usr/bin/env python3
"""scripts/verify_declared_inputs.py - a declared stage input must still resolve by hash (C-3).

Every ``*.input_fingerprint.json`` written by a long stage is a CLAIM: "these outputs were computed
against this exact input file, byte for byte". Repair scripts rewrite such inputs in place, which
makes the claim silently false and makes the next run archive the work and start over (~1.3 h of GPU
for S5). This check turns that silent future tax into a loud one (C16 fail-loud).

Convention (no values hardcoded, C12): inside the fingerprint's ``input`` mapping a key ``X`` whose
value is a repo-relative path pairs with ``X_sha256``; both must agree with the file on disk. Roots
and the list of already-known moves live in ``config/verify_declared_inputs.yaml``.

Exit 1 on any UNACKNOWLEDGED move, so ``just health`` fails loudly. Acknowledged moves are printed as
``warn`` and keep the exit code 0 - a declared exception, never a hidden one.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "config/verify_declared_inputs.yaml"


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file, streamed so a 100MB checkpoint does not blow memory."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_fingerprint(fp: Path, cfg: dict[str, Any], warnings: list[str],
                     red: list[str], ack: dict[str, dict[str, Any]]) -> int:
    """Verify one fingerprint file; append findings to warnings/red. Returns count checked."""
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - reported with the path (C16)
        red.append(f"{fp}: unreadable fingerprint ({type(exc).__name__}: {exc})")
        return 0
    rel = str(fp.relative_to(PROJECT_ROOT))
    n = 0
    for key, value in (doc.get("input") or {}).items():
        if not (isinstance(value, str) and key + "_sha256" in (doc.get("input") or {})):
            continue
        if not key.endswith(("checkpoint", "path", "file")) and "/" not in value:
            continue
        target = PROJECT_ROOT / value
        declared = doc["input"][key + "_sha256"]
        n += 1
        if not target.exists():
            red.append(f"{rel}: declared input {value} does not exist")
            continue
        observed = sha256_file(target)
        if observed == declared:
            continue
        known = ack.get(rel)
        if known and known.get("declared_input_sha256") == declared:
            warnings.append(f"{rel}: input {Path(value).name} MOVED (declared {declared[:12]}..., "
                            f"on disk {observed[:12]}...) - acknowledged {known.get('ref')}: "
                            f"{' '.join(str(known.get('reason', '')).split())[:160]}")
        else:
            red.append(f"{rel}: input {value} MOVED (declared {declared[:12]}..., on disk "
                       f"{observed[:12]}...) with NO acknowledgement (C-3 class: a completed run is "
                       f"no longer citable and the next run will discard it)")
    return n


def main() -> int:
    """Scan the configured roots for fingerprint files and verify every declared input hash."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    ack = {str(a.get("fingerprint")): a for a in (cfg.get("acknowledged_moves") or [])}
    warnings: list[str] = []
    red: list[str] = []
    checked = 0
    files = 0
    for root in cfg.get("roots", []):
        for fp in sorted((PROJECT_ROOT / root).rglob("*" + str(cfg.get("fingerprint_suffix", "")))):
            files += 1
            checked += check_fingerprint(fp, cfg, warnings, red, ack)
    print(f"declared inputs: {checked} hash claim(s) across {files} fingerprint file(s) - "
          f"{len(red)} RED, {len(warnings)} acknowledged move(s)")
    for w in warnings:
        print(f"  warn {w}")
    for r in red:
        print(f"  RED  {r}")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
