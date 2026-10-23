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
    # The MEASURED sheet the walk shows (scripts/tier_b_evidence.py). Optional on purpose: a ruling must
    # never be BLOCKED by a missing evidence sheet, but its absence is SAID OUT LOUD per candidate rather
    # than silently rendering a bare question (D-3100: a ruling rests on a reading, not on a recollection).
    cfg["evidence_path"] = (data["extraction_recall"].get("tier_b_evidence") or {}).get("path")
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


def load_evidence(cfg: dict) -> dict[tuple[str, str], dict]:
    """Index the evidence sheet by (source_id, name). Absent/undeclared -> empty (the walk says so)."""
    rel = cfg.get("evidence_path")
    if not rel:
        return {}
    path = PROJECT_ROOT / str(rel)
    if not path.exists():
        return {}
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL-CLOSED: evidence sheet {rel} is not valid JSON: {e} (C16)") from e
    band = (envelope.get("method") or {}).get("reference_band") or {}
    band_v = band.get("semantic_near_threshold")
    rows = envelope.get("rows", [])
    if isinstance(band_v, (int, float)):
        for r in rows:
            r["_band"] = float(band_v)
    return {(str(r.get("source_id")), str(r.get("name"))): r for r in rows}


def evidence_lines(cfg: dict, ev: dict[tuple[str, str], dict], source_id: str, name: str) -> list[str]:
    """Render the MEASURED evidence for one candidate: grounding, store proximity, and the reading itself."""
    row = ev.get((source_id, name))
    if row is None:
        return ["   EVIDENCE: none recorded — run `python3 scripts/tier_b_evidence.py` for the reading"]
    g = row.get("grounding") or {}
    band = float(row.get("_band") or 0.0)
    out = [f"   EVIDENCE (measured, advisory — the ruling is yours): source {g.get('name_tokens_present')} "
           f"concept token(s), {g.get('name_verbatim_hits')} verbatim hit(s)"]
    best = row.get("store_best") or []
    if best:
        top = best[0]
        near = float(top.get("cos") or 0.0)
        mark = "≈ at/above the store's semantic_near band — the store may already carry it" if band and near >= band else "below the store's semantic_near band"
        out.append(f"   store: {top.get('cos')} {str(top.get('name'))[:44]!r} ({mark})")
    elif row.get("store_novelty"):
        out.append(f"   store: {row['store_novelty']}")
    if g.get("excerpt"):
        out.append(f"   reading: {g['excerpt']}")
    return out


def run_interactive(cfg: dict) -> None:
    cands = list_candidates(cfg)
    if not cands:
        print("No unruled tier-B candidates remain.")
        return
    ev = load_evidence(cfg)
    print(f"{len(cands)} unruled candidate(s). For each, type MATCH / NONE / skip (m/n/s), then Enter.")
    print("The evidence line is MEASURED (source tokens, verbatim hits, closest stored row, the reading). "
          "It carries no verdict: MATCH/NONE is yours (D-2658/D-2898).\n")
    for idx, c in enumerate(cands, 1):
        name = c.get("name", "")
        sid = c.get("source_id", "")
        rationale = c.get("rationale", "")
        print(f"[{idx}/{len(cands)}] ── {name}  ({sid})")
        print(f"   rationale: {rationale}")
        for line in evidence_lines(cfg, ev, sid, name):
            print(line)
        while True:
            try:
                ans = input("   MATCH / NONE / skip? [m/n/s]: ").strip().lower()
            except EOFError:
                # D-3100 (MEASURED 2026-10-23): this walker is an OWNER tool, and run with stdin closed it died with
                # a traceback instead of saying what was left. A manual step that crashes is a step the owner
                # cannot run, so EOF now STOPS the walk cleanly and names the remainder: every ruling already
                # given is on disk (atomic append per ruling), so nothing is lost.
                remaining = len(cands) - idx + 1
                print(f"\nEOF: the walk stopped. {remaining} candidate(s) still unruled; "
                      f"nothing was lost (each ruling appends as you type it).")
                return
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


USAGE = """usage: python3 scripts/rule_tier_b.py [--walk | --list | --count | --rule <source_id> <name> MATCH|NONE | --selftest]

  (no flag)   walk the unruled tier-B candidates, one typed ruling each (MATCH / NONE / skip)
  --count     print "<unruled> unruled / <total> total" and exit
  --list      print one candidate per line, tab-separated: source_id, name, rationale
  --rule      record ONE ruling non-interactively (the walk's equivalent, for a single candidate)
  --selftest  known-answer controls only (no store, no prompt)

The ruling sheet is governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl (append-only, one line per ruling).
Rulings carry PRESENCE only (MATCH = the concept is in the source and must be expected; NONE = it is not)."""


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(USAGE)
        return 0
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
