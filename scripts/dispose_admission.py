#!/usr/bin/env python3
"""dispose_admission.py — the OWNER's disposition writer (BUG-973 limb 1).

Records one JSONL line per SETTLED object under the declared `admission_disposition_prefix`, so
scripts/plan_admission.py's `disposed_sets()` reads it and a settled row is counted ONCE as `disposed`
and never re-raised (never a refusal, never a candidate). A lane whose number can never move becomes a
decision the owner records and the counter can finish.

Single source of truth = config/ingest_identity_gate.yaml#source_library.admission:
  - `disposition_reasons`          — the CLOSED reason vocabulary (a reason outside it is FATAL, D-3038)
  - `admission_disposition_prefix` — where the record lives (one stamped file per run, crash-safe)

REASONS:
  out_of_scope_by_kind           — `--kind .png` settles EVERY source of that suffix forever. The 241
                                    design assets are settled by a handful of suffix lines, never 241 rows.
  not_a_work                     — `--source <path>` settles one source the owner has judged not a work.
  conversion_refused_permanently — `--source <path>` settles one source whose conversion is permanently
                                    refused (the applier writes this automatically, limb 2; the owner may
                                    write it by hand for a source S0 has already deterministically failed).

--dry-run prints the exact line(s) and writes nothing. The disposition `source` must be the ABSOLUTE
path the admission plan prints for the row (plan_admission matches `str(path)` exactly), and the
`--kind` is a suffix like `.png` (the reader normalises case and the leading dot).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import yaml

_CFG = Path(__file__).resolve().parent.parent / "config" / "ingest_identity_gate.yaml"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _find_key(doc: Any, key: str) -> Any:
    """The first value of `key` anywhere in the document (the declared single home, C12)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k == key:
                return v
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(doc, list):
        for item in doc:
            found = _find_key(item, key)
            if found is not None:
                return found
    return None


def disposition_vocabulary() -> list[str]:
    """The DECLARED reason vocabulary, fail-closed: an absent list is a fault, never a guessed zero (C16)."""
    doc = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    reasons = _find_key(doc, "disposition_reasons")
    if not isinstance(reasons, list) or not reasons:
        raise SystemExit(
            f"FATAL: {_CFG.name}#disposition_reasons is EMPTY — the disposed vocabulary must be DECLARED "
            f"and never guessed (BUG-973)"
        )
    return [str(r) for r in reasons]


def disposition_prefix() -> str:
    """The declared record home, fail-closed (C16)."""
    doc = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    prefix = _find_key(doc, "admission_disposition_prefix")
    if not isinstance(prefix, str) or not prefix.strip():
        raise SystemExit(f"FATAL: {_CFG.name}#admission_disposition_prefix is not declared (BUG-973)")
    return prefix


def build_line(reason: str | None, kind: str | None, source: str | None) -> dict[str, Any]:
    """One disposition line, fail-closed against the DECLARED vocabulary (a reason outside it is FATAL, D-3038)."""
    vocab = disposition_vocabulary()
    if not reason or reason not in vocab:
        raise SystemExit(f"FATAL: reason {reason!r} is outside the declared vocabulary {vocab} (BUG-973)")
    if reason == "out_of_scope_by_kind":
        if not kind or source:
            raise SystemExit("FATAL: out_of_scope_by_kind takes --kind (a suffix) and NOT --source")
        kind = kind.strip().lstrip(".").lower()
        if not kind:
            raise SystemExit("FATAL: --kind may not be empty")
        rec: dict[str, Any] = {"reason": reason, "kind": kind}
    else:
        if kind or not source:
            raise SystemExit(f"FATAL: {reason} takes --source (an absolute path) and NOT --kind")
        rec = {"reason": reason, "source": source}
    rec["schema"] = "1.0"
    rec["ts"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return rec


def disposition_record_path(prefix: str, stamp: str) -> Path:
    """One stamped file per run under the declared prefix's folder (the reader globs `PREFIX_*.jsonl`)."""
    base = _PROJECT_ROOT / prefix
    return base.parent / f"{base.name}{stamp}.jsonl"


def write_disposition(lines: list[dict[str, Any]], prefix: str) -> list[Path]:
    """Crash-safe write of one or more disposition lines (tempfile -> fsync -> os.replace, C6)."""
    if not lines:
        return []
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = disposition_record_path(prefix, stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(line, ensure_ascii=False, sort_keys=False) + "\n" for line in lines)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return [path]


def _lines_from_file(path: str) -> list[dict[str, Any]]:
    """Bulk JSONL: one `{reason, kind|source}` per line, each validated (an out-of-vocab line is FATAL)."""
    raw = Path(path)
    if not raw.is_file():
        raise SystemExit(f"FATAL: --file {path!r} does not exist")
    lines: list[dict[str, Any]] = []
    for i, text in enumerate(raw.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FATAL: --file line {i} is not JSON: {text[:80]!r}") from exc
        lines.append(build_line(str(spec.get("reason") or ""), spec.get("kind"), spec.get("source")))
    return lines


def selftest() -> int:
    """Known-answer controls: the vocabulary is read not guessed, the reason gate is fail-closed, and the
    write is crash-safe and round-trips (a red loop must be seen green before limb 2 leans on it)."""
    import tempfile as _tempfile

    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    vocab = disposition_vocabulary()
    expect("vocabulary declared", vocab == ["out_of_scope_by_kind", "not_a_work", "conversion_refused_permanently"],
           f"read {vocab}")

    #: kind normalises the leading dot and case (the reader does the same, so the two sides must agree).
    line = build_line("out_of_scope_by_kind", ".PNG", None)
    expect("kind normalised", line["kind"] == "png" and line["reason"] == "out_of_scope_by_kind"
           and "source" not in line, f"read {line}")

    line = build_line("not_a_work", None, "/abs/path/Work.docx")
    expect("source kept", line["source"] == "/abs/path/Work.docx" and "kind" not in line, f"read {line}")

    def raises(reason: str | None, kind: str | None, source: str | None) -> bool:
        try:
            build_line(reason, kind, source)
            return False
        except SystemExit:
            return True

    expect("reason gate closed", raises("made_up_reason", None, None), "a reason outside the vocabulary did not raise")
    expect("kind/source mutex (kind)", raises("out_of_scope_by_kind", None, "/x"), "kind reason took a source")
    expect("kind/source mutex (source)", raises("not_a_work", ".png", None), "source reason took a kind")

    #: crash-safe write + round-trip into a THROWAWAY folder (a selftest never writes the live record).
    with _tempfile.TemporaryDirectory(prefix="dispose_") as tmp:
        paths = write_disposition([build_line("out_of_scope_by_kind", ".png", None),
                                   build_line("not_a_work", None, "/abs/Work.docx")],
                                  str(Path(tmp) / "ADMISSION_DISPOSITION_"))
        expect("one stamped file", len(paths) == 1 and paths[0].is_file(), f"wrote {paths}")
        got = [json.loads(t) for t in paths[0].read_text(encoding="utf-8").splitlines() if t.strip()]
        expect("round-trip", len(got) == 2 and got[0]["kind"] == "png" and got[1]["source"] == "/abs/Work.docx",
               f"read {got}")

    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    print("selftest: disposition writer green")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The owner's disposition writer (BUG-973): settle a lane for good.")
    parser.add_argument("--reason", help="one of the declared disposition_reasons")
    parser.add_argument("--kind", help="the suffix (e.g. .png) — for out_of_scope_by_kind")
    parser.add_argument("--source", help="the absolute source path — for not_a_work / conversion_refused_permanently")
    parser.add_argument("--file", help="bulk JSONL: one {'reason','kind'|'source'} per line")
    parser.add_argument("--dry-run", action="store_true", help="print the exact line(s), write nothing")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.file:
        lines = _lines_from_file(args.file)
    else:
        lines = [build_line(args.reason, args.kind, args.source)]

    if args.dry_run:
        for line in lines:
            print(json.dumps(line))
        return 0

    written = write_disposition(lines, disposition_prefix())
    print(f"disposed {len(lines)} object(s) -> {' '.join(str(p) for p in written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
