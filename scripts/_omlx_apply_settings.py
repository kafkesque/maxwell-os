#!/usr/bin/env python3
"""Apply the D-2637 decoder settings to oMLX (grammar ON, prefix cache ON, temp 0.0).

Backs both files up first. oMLX reads these at server start, so the change only
takes effect after the app is relaunched (the control socket is stale, so a
programmatic restart is not available — D2455/D2456 forbid spawning a second
managed server via `omlx-cli restart`).

Usage: python3 scripts/_omlx_apply_settings.py [--apply]
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

OMLX = Path.home() / ".omlx"
SETTINGS = OMLX / "settings.json"
MODEL_SETTINGS = OMLX / "model_settings.json"

# Models that must emit strict JSON somewhere in the pipeline.
GRAMMAR_MODELS = [
    "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",
    "Qwen3.8-27B-MLX-4bit",
    "gemma-4-E4B-it-MLX-4bit",
    "gemma-4-12B-it-qat-OptiQ-4bit",
    "gpt-oss-20b-MXFP4-Q8",
    "Phi-4-mini-instruct-8bit",
    "Ornith-1.5-9B-OptiQ-4bit",
]


def backup(p: Path) -> Path:
    """Copy p to a timestamped .bak next to it and return the backup path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = p.with_suffix(p.suffix + ".bak_" + ts)
    shutil.copy2(p, dst)
    return dst


def main() -> int:
    """Patch oMLX settings; with no --apply flag only reports the planned diff."""
    apply = "--apply" in sys.argv
    if not SETTINGS.exists() or not MODEL_SETTINGS.exists():
        print("ERR oMLX settings not found")
        return 1

    s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    m = json.loads(MODEL_SETTINGS.read_text(encoding="utf-8"))
    changes: list[str] = []

    if s.get("cache", {}).get("enabled") is not True:
        changes.append("settings.cache.enabled: " + str(s.get("cache", {}).get("enabled")) + " -> True")
        s.setdefault("cache", {})["enabled"] = True

    cur_t = s.get("sampling", {}).get("temperature")
    if cur_t != 0.0:
        changes.append("settings.sampling.temperature: " + str(cur_t) + " -> 0.0 (R7 default)")
        s.setdefault("sampling", {})["temperature"] = 0.0

    for name, cfg in m.get("models", {}).items():
        if name in GRAMMAR_MODELS and cfg.get("guided_grammar_enabled") is not True:
            changes.append("model_settings[" + name + "].guided_grammar_enabled: False -> True")
            cfg["guided_grammar_enabled"] = True

    if not changes:
        print("no changes needed")
        return 0

    print("planned changes (" + str(len(changes)) + "):")
    for c in changes:
        print("  - " + c)

    if not apply:
        print("\ndry run — re-run with --apply to write")
        return 0

    print("\nbackups:")
    print("  " + str(backup(SETTINGS)))
    print("  " + str(backup(MODEL_SETTINGS)))

    SETTINGS.write_text(json.dumps(s, indent=2) + chr(10), encoding="utf-8")
    MODEL_SETTINGS.write_text(json.dumps(m, indent=2) + chr(10), encoding="utf-8")
    print("written. Relaunch oMLX.app for the settings to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
