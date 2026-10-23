#!/usr/bin/env python3
"""rule_tier_b.py — noob-proof owner ruling of tier-B candidates (T-195 step c, D-3100).

WHY THIS EXISTS (D-3100). The owner's rulings on tier-B candidates are the ONE human gate in
the completeness arm (D-2898: never auto-certified). The first hand-off told the owner to
"append a line" to a JSONL — the owner pasted the JSON into a shell and got
`zsh: command not found`. A manual step named only in prose is a step the owner cannot run
(BUG-588's shape). This script turns the ruling into a typed MATCH/NONE/skip per candidate,
so there is no JSON to paste, no file to edit, and no way to corrupt the sheet.

Output is APPENDED to the ruling sheet (config/extraction_recall.yaml → golden.tier_b_ruling_sheet)
in the exact shape check_extraction_recall.py::load_tier_b_rulings expects, one line each:
    {"source_id": "<id>", "name": "<concept name>", "owner_ruling_note": "MATCH"|"NONE"}

Safety (D-3034 / C6 / C16):
  * Every append is atomic: tempfile -> fsync -> os.replace.
  * Placeholder tokens (<...>) in a ruling are REFUSED (same fail-closed guard as the reader).
  * A duplicate (source_id, name) ruling is refused, not silently doubled.
  * Empty/unknown input refuses loudly; nothing is ever written on an error.

No LLM anywhere (D-343). Deterministic.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "extraction_recall.yaml"

VALID_NOTES = {"MATCH", "NONE"}


def load_cfg() -> dict:
    import yaml

    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = data["extraction_recall"]["golden"]
    if not cfg.get("tier_b_sheet") or not cfg.get("tier_b_ruling_sheet"):
        raise SystemExit("FAIL-CLOSED: golden.tier_b_sheet / tier_b_ruling_sheet missing in config (C12)")
    return cfg


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"FAIL-CLOSED: {path}:{i} is not valid JSONL: {e} (C16)")
    return out


def _has_placeholder(obj: dict) -> bool:
    return any("<" in str(v) or ">" in str(v) for v in obj.values())


def atomic_append(path: Path, line: str) -> None:
    """Append one line atomically (C6: tempfile -> fsync -> os.replace)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    body = (existing.rstrip("\n") + "\n" + line.rstrip("\n") + "\n").lstrip("\n")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def list_candidates(cfg: dict) -> list[dict]:
    cands = _read_jsonl(PROJECT_ROOT / cfg["tier_b_sheet"])
    rulings = _read_jsonl(PROJECT_ROOT / cfg["tier_b_ruling_sheet"])
    ruled = {(r.get("source_id"), r.get("name")) for r in rulings if r.get("source_id") and r.get("name")}
    return [c for c in cands if (c.get("source_id"), c.get("name")) not in ruled]


def count_candidates(cfg: dict) -> tuple[int, int]:
    cands = _read_jsonl(PROJECT_ROOT / cfg["tier_b_sheet"])
    rulings = _read_jsonl(PROJECT_ROOT / cfg["tier_b_ruling_sheet"])
    ruled = {(r.get("source_id"), r.get("name")) for r in rulings if r.get("source_id") and r.get("name")}
    total = len(cands)
    unruled = sum(1 for c in cands if (c.get("source_id"), c.get("name")) not in ruled)
    return unruled, total


def record_ruling(cfg: dict, source_id: str, name: str, note: str) -> None:
    note = note.strip().upper()
    if note not in VALID_NOTES:
        raise SystemExit(f"FAIL-CLOSED: ruling note {note!r} is not one of {sorted(VALID_NOTES)}")
    obj = {"source_id": source_id.strip(), "name": name.strip(), "owner_ruling_note": note}
    if _has_placeholder(obj):
        raise SystemExit(f"FAIL-CLOSED: ruling carries a placeholder token (D-3034): {obj!r}")
    if not obj["source_id"] or not obj["name"]:
        raise SystemExit(f"FAIL-CLOSED: ruling missing source_id/name: {obj!r} (D-3034)")
    out_path = PROJECT_ROOT / cfg["tier_b_ruling_sheet"]
    # refuse a duplicate for the same (source_id, name)
    for r in _read_jsonl(out_path):
        if r.get("source_id") == obj["source_id"] and r.get("name") == obj["name"]:
            raise SystemExit(f"ALREADY RULED: {obj['source_id']} / {obj['name']!r} — remove the old line to re-rule")
    atomic_append(out_path, json.dumps(obj, ensure_ascii=False))
    print(f"  ✓ recorded {note}: {obj['name']!r} ({obj['source_id']})")


def run_interactive(cfg: dict) -> None:
    cands = list_candidates(cfg)
    if not cands:
        print("No unruled tier-B candidates remain.")
        return
    print(f"{len(cands)} unruled candidate(s). For each, type MATCH / NONE / skip (m/n/s), then Enter.\n")
    for c in cands:
        name = c.get("name", "")
        sid = c.get("source_id", "")
        rationale = c.get("rationale", "")
        print(f"── {name}  ({sid})")
        print(f"   rationale: {rationale}")
        while True:
            ans = input("   MATCH / NONE / skip? [m/n/s]: ").strip().lower()
            if ans in ("m", "match"):
                record_ruling(cfg, sid, name, "MATCH")
                break
            if ans in ("n", "none"):
                record_ruling(cfg, sid, name, "NONE")
                break
            if ans in ("s", "skip", ""):
                print("   skipped")
                break
            print("   (type m, n, or s)")


def selftest() -> int:
    import tempfile as _tf
    import yaml

    with _tf.TemporaryDirectory() as td:
        td = Path(td)
        (td / "cands.jsonl").write_text(
            json.dumps({"source_id": "abc123", "name": "Concept One", "rationale": "r"}) + "\n"
            + json.dumps({"source_id": "abc123", "name": "Concept Two", "rationale": "r"}) + "\n",
            encoding="utf-8",
        )
        (td / "rulings.jsonl").write_text("", encoding="utf-8")
        cfg = {"tier_b_sheet": str(td / "cands.jsonl"), "tier_b_ruling_sheet": str(td / "rulings.jsonl")}

        assert count_candidates(cfg) == (2, 2), "selftest: expected 2 unruled"
        record_ruling(cfg, "abc123", "Concept One", "MATCH")
        assert count_candidates(cfg) == (1, 2), "selftest: expected 1 unruled after MATCH"
        # duplicate refusal
        try:
            record_ruling(cfg, "abc123", "Concept One", "NONE")
            raise AssertionError("selftest: duplicate ruling was not refused")
        except SystemExit as e:
            assert "ALREADY RULED" in str(e), f"selftest: wrong refusal reason: {e}"
        # placeholder refusal
        try:
            record_ruling(cfg, "<id>", "<concept name>", "MATCH")
            raise AssertionError("selftest: placeholder ruling was not refused")
        except SystemExit as e:
            assert "placeholder" in str(e), f"selftest: placeholder guard missing: {e}"
        lines = [json.loads(l) for l in (td / "rulings.jsonl").read_text().splitlines() if l.strip()]
        assert lines == [{"source_id": "abc123", "name": "Concept One", "owner_ruling_note": "MATCH"}], lines
    print("selftest OK: count / MATCH / duplicate-refusal / placeholder-refusal / atomic append")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    cfg = load_cfg()
    if "--list" in sys.argv:
        for c in list_candidates(cfg):
            print(f"{c.get('source_id')}\t{c.get('name')}\t{c.get('rationale','')}")
        return 0
    if "--count" in sys.argv:
        u, t = count_candidates(cfg)
        print(f"{u} unruled / {t} total")
        return 0
    if "--rule" in sys.argv:
        # non-interactive: --rule "<source_id>" "<name>" MATCH|NONE
        try:
            i = sys.argv.index("--rule")
            sid, name, note = sys.argv[i + 1], sys.argv[i + 2], sys.argv[i + 3]
        except (ValueError, IndexError):
            raise SystemExit('usage: --rule "<source_id>" "<name>" MATCH|NONE')
        record_ruling(cfg, sid, name, note)
        return 0
    run_interactive(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
