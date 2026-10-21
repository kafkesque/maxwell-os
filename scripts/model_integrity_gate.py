#!/usr/bin/env python3
"""The model-integrity gate (D-3036 red loop, D-3105 red loop + post-red-loop controls).

One named command that answers, for a single model file: may this payload be
loaded into the inference engine, or must it be refused?

Three tiers, each fail-closed:

  1. FORMAT (always on): pickle = arbitrary code on load -> RED; safetensors ->
     allowed. The gate NEVER unpickles a payload: it refuses on the format before
     any byte is executed.
  2. PROVENANCE (SHA-256 pinning, active once `sha256_pins` is provisioned): a
     pinned file whose digest differs was tampered -> RED; an unpinned file is
     QUARANTINED -> RED when `quarantine_unknown` is true. An EMPTY pin table
     means "pinning not yet provisioned", so the tier is inactive (format-only) —
     reported loudly, never silent (C16). The owner flips to strict fail-closed
     by adding the first pin.
  3. TEMPLATE (Jinja chat-template denylist, on demand via --chat-template): a
     template carrying a denied pattern (the object.__subclasses__ / __import__ /
     eval / exec chain) -> RED.

RED (exit 1) — refused. GREEN (exit 0) — allowed.

Every knob is read from config/model_integrity.yaml (C12): the gate names no
format, path, pattern or digest of its own.

Usage:
  scripts/model_integrity_gate.py <model_file>              # tiers 1 + 2
  scripts/model_integrity_gate.py --chat-template <file>    # tier 3 only
  scripts/model_integrity_gate.py --selftest                # re-runnable red loop, all tiers
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "model_integrity.yaml"


def _load_config() -> dict:
    """Read the gate's single source of truth (C12)."""
    if not CONFIG_PATH.exists():
        print(f"RED: gate config missing: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _is_pickle(path: Path) -> bool:
    """Return True if the file is a pickle payload (refuse on sight).

    pickle streams begin with the PROTO opcode 0x80 (protocol 2+) or one of the
    ASCII opcodes the default protocol-0 encoder emits ('c', '(', 'S'). We read the
    magic only — we NEVER unpickle the payload, because unpickling is the threat.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(64)
        return head[:1] == b"\x80" or head.startswith((b"c", b"(", b"S'", b"\x00"))
    except OSError:
        return False


def _is_safetensors(path: Path) -> bool:
    """Return True if the file carries the safetensors magic (8-byte little-endian
    header length followed by a '{'-opening JSON header)."""
    try:
        with open(path, "rb") as fh:
            header_len_bytes = fh.read(8)
            if len(header_len_bytes) < 8:
                return False
            header_len = int.from_bytes(header_len_bytes, "little")
            if header_len <= 0 or header_len > 100_000_000:
                return False
            header = fh.read(header_len)
            return header.lstrip().startswith(b"{")
    except OSError:
        return False


def classify(path: Path, refused: Sequence[str], allowed: Sequence[str]) -> str:
    """Classify a payload into one format the gate knows, or '' if unclassifiable."""
    if _is_pickle(path):
        return "pickle"
    if _is_safetensors(path):
        return "safetensors"
    # File extension as a fallback signal when magic is inconclusive.
    ext = path.suffix.lower().lstrip(".")
    if ext in refused:
        return ext
    if ext in allowed:
        return ext
    return ""


def sha256_hex(path: Path) -> str:
    """Return the SHA-256 digest of a file's bytes as a hex string."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_provenance(path: Path, pins: dict, quarantine_unknown: bool) -> tuple[bool, str]:
    """Apply SHA-256 pinning. Return (ok, message).

    Pin enforcement is ACTIVE only once the owner has provisioned at least one pin:
    an empty pin table means "pinning not yet provisioned", so the gate stays
    format-only rather than refusing every model on a bootstrap machine. This is
    reported, not silent (C16). The first pin the owner adds flips the gate to
    strict fail-closed.
    """
    if not pins:
        return True, "provenance inactive (sha256_pins empty; format-only)"
    digest = sha256_hex(path)
    name = path.name
    if name in pins:
        if pins[name] == digest:
            return True, f"pinned digest matches ({name})"
        return False, (f"tampered payload: sha256 mismatch for {name} "
                       f"(expected {pins[name][:12]}… got {digest[:12]}…)")
    if quarantine_unknown:
        return False, (f"unpinned payload quarantined ({name}) — add its sha256 "
                       f"to config/model_integrity.yaml#sha256_pins (C16)")
    return True, f"unpinned payload admitted ({name}; quarantine_unknown=false)"


def scan_chat_template(template: str, deny_patterns: Sequence[str]) -> list[str]:
    """Return the deny patterns present in a chat-template (Jinja) string."""
    return [p for p in deny_patterns if p and p in template]


def check_template(text: str, deny_patterns: Sequence[str]) -> tuple[bool, str]:
    """Scan a chat template for denied patterns. Return (ok, message)."""
    hits = scan_chat_template(text, deny_patterns)
    if hits:
        return False, f"poisoned chat template: denied pattern(s) {hits}"
    return True, "chat template clean (no denied pattern)"


def _chat_template_mode(path_str: str, cfg: dict) -> int:
    """Run tier 3 (Jinja denylist) against a template file and exit."""
    deny: Sequence[str] = cfg["chat_template_scan"]["deny_patterns"]
    p = Path(path_str).resolve()
    if not p.exists():
        print(f"RED: template file not found: {p}", file=sys.stderr)
        return 1
    text = p.read_text(encoding="utf-8", errors="replace")
    ok, msg = check_template(text, deny)
    print(f"{'GREEN' if ok else 'RED'}: {msg}: {p}")
    return 0 if ok else 1


def selftest(cfg: dict) -> int:
    """Re-runnable red loop over all three tiers (D-3036). Exit 0 iff every control
    goes RED on its threat and GREEN on its clean payload."""
    import tempfile

    faults: list[str] = []

    def check(desc: str, got_ok: bool, want_ok: bool) -> None:
        if got_ok != want_ok:
            faults.append(f"{desc}: got {'GREEN' if got_ok else 'RED'}, "
                          f"want {'GREEN' if want_ok else 'RED'}")

    allowed: Sequence[str] = cfg["allowed_load_formats"]
    refused: Sequence[str] = cfg["refused_load_formats"]
    deny: Sequence[str] = cfg["chat_template_scan"]["deny_patterns"]
    quarantine: bool = bool(cfg["quarantine_unknown"])
    fixtures = cfg["red_loop_fixtures"]
    red_pkl = REPO_ROOT / str(fixtures["red"])
    green_st = REPO_ROOT / str(fixtures["green"])

    # Tier 1 — format.
    check("format: pickle refused (RED)", classify(red_pkl, refused, allowed) in refused, True)
    check("format: safetensors allowed (GREEN)", classify(green_st, refused, allowed) in allowed, True)

    # Tier 2 — provenance. Proven in-memory (injected pins), so no digest leaks into
    # the production config; the owner still fills sha256_pins themselves.
    with tempfile.NamedTemporaryFile(suffix=".safetensors", delete=False) as fh:
        fh.write(green_st.read_bytes())
        tmp = Path(fh.name)
    try:
        digest = sha256_hex(tmp)
        check("provenance: empty pins -> format-only (GREEN)", check_provenance(tmp, {}, quarantine)[0], True)
        check("provenance: pin match (GREEN)", check_provenance(tmp, {tmp.name: digest}, quarantine)[0], True)
        check("provenance: pin mismatch (RED)", check_provenance(tmp, {tmp.name: "0" * 64}, quarantine)[0], False)
        check("provenance: unpinned quarantined (RED)", check_provenance(tmp, {"other.safetensors": "0" * 64}, True)[0], False)
        check("provenance: unpinned admitted (GREEN)", check_provenance(tmp, {"other.safetensors": "0" * 64}, False)[0], True)
    finally:
        tmp.unlink(missing_ok=True)

    # Tier 3 — chat-template denylist.
    check("template: poisoned (RED)",
          check_template("{{ ''.__class__.__subclasses__() }}", deny)[0], False)
    check("template: import chain (RED)",
          check_template("{% set x = __import__('os') %}", deny)[0], False)
    check("template: clean (GREEN)",
          check_template("{% for m in messages %}{{ m.content }}{% endfor %}", deny)[0], True)

    if faults:
        print("SELFTEST FAIL:")
        for f in faults:
            print("  - " + f)
        return 1
    print("SELFTEST OK — 9 controls RED/GREEN as expected (format, provenance, template)")
    return 0


def main(argv: Sequence[str]) -> int:
    """Run the gate and exit 0 (GREEN) or 1 (RED)."""
    cfg = _load_config()
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest(cfg)
    if len(argv) == 3 and argv[1] == "--chat-template":
        return _chat_template_mode(argv[2], cfg)
    if len(argv) != 2:
        prog = Path(argv[0]).name if argv else "model_integrity_gate.py"
        print(f"Usage: {prog} <model_file> | --chat-template <file> | --selftest",
              file=sys.stderr)
        return 1

    allowed: Sequence[str] = cfg["allowed_load_formats"]
    refused: Sequence[str] = cfg["refused_load_formats"]
    pins: dict = cfg["sha256_pins"] or {}
    quarantine: bool = bool(cfg["quarantine_unknown"])

    path = Path(argv[1]).resolve()
    if not path.exists():
        print(f"RED: file not found: {path}", file=sys.stderr)
        return 1

    fmt = classify(path, refused, allowed)
    if fmt in refused:
        print(f"RED: refused format '{fmt}' (arbitrary-code risk): {path}")
        return 1
    if fmt not in allowed:
        print(f"RED: unclassifiable payload (fail-closed): {path}")
        return 1

    ok, msg = check_provenance(path, pins, quarantine)
    if not ok:
        print(f"RED: {msg}: {path}")
        return 1
    print(f"GREEN: allowed format '{fmt}'; {msg}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
