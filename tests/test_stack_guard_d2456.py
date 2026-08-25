"""Tests for scripts/guard_stacks_single_source.py shim-vs-homebrew discrimination (D2456).

The 2026-08-24 forensic audit found the OMLX guard's original "forbidden binary
exists → fail" check produced a FALSE POSITIVE: the app 0.6.2 itself writes a CLI
shim at /opt/homebrew/bin/omlx -> ~/.omlx/bin/omlx -> omlx-cli. The fixed guard
distinguishes:
  - forbidden_bins (Cellar/opt) — unambiguous homebrew markers, must NOT exist
  - shim_paths — flag ONLY if they RESOLVE into a homebrew Cellar/opt install
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.guard_stacks_single_source as g


def test_resolves_to_homebrew_install_detects_cellar() -> None:
    """A shim resolving into /opt/homebrew/Cellar/ is a homebrew re-install."""
    # The resolve target contains Cellar (don't touch real FS).
    assert g._resolves_to_homebrew_install(Path("/opt/homebrew/Cellar/omlx/0.5.1/bin/omlx"))


def test_resolves_to_homebrew_install_rejects_app_shim() -> None:
    """An app shim resolving to ~/.omlx/bin/omlx is NOT homebrew."""
    p = Path.home() / ".omlx" / "bin" / "omlx"
    assert not g._resolves_to_homebrew_install(p)


def test_resolves_to_homebrew_install_detects_opt() -> None:
    """A shim resolving into /opt/homebrew/opt/ is a homebrew re-install."""
    assert g._resolves_to_homebrew_install(Path("/opt/homebrew/opt/ollama/bin/ollama"))


def test_guard_config_has_both_stacks() -> None:
    """Both OMLX and Ollama declare a single_source_guard block."""
    stacks = g._load_guarded_stacks()
    assert {"omlx", "ollama"} <= set(stacks)
    for name in ("omlx", "ollama"):
        assert "forbidden_bins" in stacks[name]
        assert "shim_paths" in stacks[name]
        assert "forbidden_launchd_labels" in stacks[name]


def test_verdict_comparison() -> None:
    """Version drift verdict logic in monitor_stacks."""
    import scripts.monitor_stacks as m
    assert m._verdict("0.6.2", "0.4.0") == "PASS"
    assert m._verdict("0.30.0", "0.32.0") == "DRIFT"
    assert m._verdict(None, "0.4.0") == "UNKNOWN"
    assert m._verdict("0.32.15", "0.32.0") == "PASS"
