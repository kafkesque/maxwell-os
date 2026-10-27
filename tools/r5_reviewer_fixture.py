#!/usr/bin/env python3
"""r5_reviewer_fixture.py — the VERDICT fixture the R5 reviewer bench was missing.

WHY THIS FILE EXISTS (measured, 2026-10-26)
-------------------------------------------
`config/r5_review_gate.yaml` declares the deep-tier reviewer gate as
`harness: tools/model_eval_suite.py, suite: reviewing, min_n: 20, baseline: constant-answer,
min_margin_over_baseline: 0.15`. But `suite_reviewing` grades a reviewer by SUBSTRING MATCH
(`any(w in pred.lower() for w in want)`) on 10 hand-written bug-spotting prompts and contains
ZERO verdict tokens — `grep -c "APPROVE|REJECT" tools/model_eval_suite.py` = 0. The reviewer's
actual job (scripts/r5_code_review.py) is to emit `{"verdict": APPROVE|REJECT|INSUFFICIENT}`.

Running the declared bench and calling the result green would have been a FAKE UNBLOCK: a
promotion of the deep-tier reviewer on evidence that never tested a verdict. This module is the
missing instrument, so the config's declared `constant-answer` baseline finally means what it
says: a reviewer that always answers APPROVE (the rubber stamp) scores exactly the share of
APPROVE-gold items, and a candidate must beat that by the declared margin.

V2 (2026-10-27, BUG-1038) — WHOLE-SCRIPT GRANULARITY
-----------------------------------------------------
v1 presented single FUNCTIONS. That made the rubric clause "does it verify its own work"
UNDECIDABLE at function granularity, so a literal reviewer (gpt-oss-20b-MXFP4-Q8) rejected
10/12 CLEAN functions as "the function does not verify its own work; it merely counts
non-empty lines". That clause is a property of a WHOLE script that ACTS ON THE WORLD, not of a
single function. v2 therefore presents each item as a COMPLETE script — module docstring +
`main()` + `if __name__ == "__main__"` — which is the unit the gate actually reviews
(`scripts/*`, `pipeline/*`, `tools/*`). The gate's declared `task` scopes "verify its own work"
to scripts that act on the world, so the clause is now answerable for every item and a clean
pure-compute script cannot be rejected on that ground.

DESIGN RULES
------------
* DETERMINISTIC GROUND TRUTH. Every item carries a gold verdict written by the item's author,
  not by an LLM judge. There is no second model in the grading path (same rule as
  `suite_summ_extractive`), so the grader cannot drift.
* NO SECOND PARSER. The verdict is parsed by `scripts/r5_code_review.extract_verdict` — the
  single source of truth used in production — imported lazily to avoid the import cycle
  (`r5_code_review` imports `model_eval_suite.call`).
* THE PRODUCTION PROMPT, VERBATIM. System prompt and prompt scaffolding mirror
  `scripts/r5_code_review.py`, and the reviewer question is read from
  `config/r5_review_gate.yaml` (`task`), never retyped here (C12).
* BALANCED. 12 APPROVE-gold and 12 REJECT-gold items, so the constant-answer baseline is 0.50
  and cannot be gamed by priors.
* ONTOLOGICALLY ALIGNED. The seeded defects are the OS's OWN iron-rule violations (C6 crash-safe
  writes, C12 hardcoded values, C16 silent errors, R-D410 data loss), because those are the
  failures this gate will actually be asked to catch.

WHAT IS MEASURED
----------------
`acc`            exact gold-verdict match (out of 24)
`false_approve`  share of REJECT-gold items answered APPROVE — the rubber-stamp rate
`false_reject`   share of APPROVE-gold items answered REJECT — the over-block rate
`unparsed`       share of rows whose reply carried no parseable verdict JSON (BUG-738's mode)

A reviewer that scores well on `acc` while approving seeded defects is not a reviewer.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Callable

REPO: Path = Path(__file__).resolve().parents[1]
_CONFIG: Path = REPO / "config" / "r5_review_gate.yaml"

# Budget for the fixture call. The deep tier is the path `scripts/*` resolves to, so its declared
# budget is the honest one to measure against (BUG-738: too small a budget truncates the verdict
# JSON and is scored as a model failure).
_DEFAULT_MAX_TOKENS: int = 2600


def _gate_config() -> dict:
    """Load the R5 gate config, fail-closed (a missing gate must not pass silently, C16)."""
    import yaml  # local import: the harness must import even where yaml is absent

    if not _CONFIG.is_file():
        raise RuntimeError("r5 reviewer fixture: gate config missing at " + str(_CONFIG))
    with _CONFIG.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _review_task() -> str:
    """Return the reviewer question DECLARED by the gate, so the fixture cannot drift from it."""
    cfg = _gate_config()
    task = str(cfg.get("task") or "").strip()
    if not task:
        raise RuntimeError("r5 reviewer fixture: config declares no 'task' for the reviewer")
    return task


def _deep_budget() -> int:
    """Return the deep tier's declared output budget (the reviewer budget under test)."""
    cfg = _gate_config()
    tiers = cfg.get("tiers") or {}
    deep = tiers.get("deep") or {}
    return int(deep.get("max_tokens") or _DEFAULT_MAX_TOKENS)


SYSTEM: str = (
    "You review Python scripts for correctness and safety. "
    "Judge only what the source supports; if the question cannot be decided from the code "
    "alone, the verdict MUST be \"INSUFFICIENT\". "
    "Reply with JSON only: {\"verdict\": \"APPROVE\" or \"REJECT\" or \"INSUFFICIENT\", "
    "\"concerns\": [\"...\"], \"confidence\": 0.0-1.0}"
)

# --------------------------------------------------------------------------------------------
# SEEDED-DEFECT ITEMS (gold REJECT). Each is a WHOLE script whose module docstring states the
# purpose the code VIOLATES, so the verdict is decidable from the source alone — no INSUFFICIENT
# is defensible. The `if __name__ == "__main__"` entry makes it the unit the gate reviews.
# --------------------------------------------------------------------------------------------
REJECT_CASES: list[dict] = [
    {
        "id": "rvv3-hardcoded-path",
        "name": "collect_reports.py",
        "why": "C12 violation: the output root is a hardcoded absolute path although the docstring says it comes from config.",
        "text": '''"""Collect report files into the archive directory (path comes from config)."""
import shutil
import sys
from pathlib import Path

ARCHIVE_ROOT = "/srv/maxwell/reports/archive"


def collect(paths: list[str]) -> int:
    """Copy each path into the archive root and return how many were copied."""
    copied = 0
    for raw in paths:
        target = Path(ARCHIVE_ROOT) / Path(raw).name
        shutil.copy2(raw, target)
        copied += 1
    return copied


def main() -> int:
    print("copied " + str(collect(sys.argv[1:])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-bare-except",
        "name": "refresh_index.py",
        "why": "C16 violation: a bare except swallows every failure silently; the docstring promises failures are reported.",
        "text": '''"""Refresh the search index and REPORT any file that could not be indexed."""
import json
import sys
from pathlib import Path


def refresh(root: str) -> dict:
    """Index every json file under root; failures are reported in the returned tally."""
    tally = {"ok": 0, "failed": 0}
    for path in Path(root).rglob("*.json"):
        try:
            json.loads(path.read_text())
            tally["ok"] += 1
        except:
            pass
    return tally


def main() -> int:
    print(refresh(sys.argv[1] if len(sys.argv) > 1 else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-unsafe-write",
        "name": "save_state.py",
        "why": "C6 violation: writes in place, so a crash mid-write leaves a truncated state file, while the docstring claims crash-safety.",
        "text": '''"""Persist state crash-safely so a killed process never leaves a truncated file."""
import json
import sys
from pathlib import Path


def save(state: dict, path: Path) -> None:
    """Write state atomically: a reader sees either the old file or the new one."""
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    save({"ok": True}, Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-sql-injection",
        "name": "lookup_book.py",
        "why": "Unparameterised SQL: the title is interpolated, so a quote in the input breaks or subverts the query.",
        "text": '''"""Look up one book by title in the catalogue database."""
import sqlite3
import sys


def find(conn: sqlite3.Connection, title: str) -> tuple | None:
    """Return the row for exactly this title, or None."""
    cursor = conn.execute("SELECT id, title FROM books WHERE title = '" + title + "'")
    return cursor.fetchone()


def main() -> int:
    conn = sqlite3.connect(sys.argv[1])
    print(find(conn, sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-mutable-default",
        "name": "tag_batch.py",
        "why": "Mutable default argument: the list is shared across calls, so each call accumulates the previous call's tags.",
        "text": '''"""Tag batches of documents; every call returns a list holding ONLY that call's tags."""
import sys
from typing import Any


def tag_batch(docs: list[dict[str, Any]], tags: list[str] = []) -> list[str]:
    """Return the tags for this batch alone."""
    for doc in docs:
        tags.append(doc["kind"])
    return tags


def main() -> int:
    print(tag_batch([{"kind": sys.argv[1]}]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-missing-return",
        "name": "normalize_units.py",
        "why": "The function computes the converted list but returns None, so every caller raises TypeError.",
        "text": '''"""Convert a list of measurements from grams to kilograms."""
import sys
from typing import Iterable


def to_kilograms(values: Iterable[float]) -> list[float]:
    """Return the values converted from grams to kilograms."""
    converted = [value / 1000.0 for value in values]


def main() -> int:
    print(to_kilograms([float(x) for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-off-by-one",
        "name": "pairwise_deltas.py",
        "why": "Off-by-one: range(len(xs)) reads xs[i + 1] past the end, so the last iteration raises IndexError.",
        "text": '''"""Compute the difference between consecutive samples."""
import sys
from typing import Sequence


def deltas(xs: Sequence[float]) -> list[float]:
    """Return xs[i+1] - xs[i] for every consecutive pair."""
    out: list[float] = []
    for i in range(len(xs)):
        out.append(xs[i + 1] - xs[i])
    return out


def main() -> int:
    print(deltas([float(x) for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-empty-division",
        "name": "mean_metric.py",
        "why": "No empty guard: an empty input raises ZeroDivisionError although the docstring promises empty input is handled.",
        "text": '''"""Summarise a metric series; an empty series is handled and returns 0.0."""
import sys
from typing import Sequence


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, or 0.0 when the series is empty."""
    total = sum(values)
    return total / len(values)


def main() -> int:
    print(mean([float(x) for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-unclosed-file",
        "name": "line_counter.py",
        "why": "File handle is never closed: the descriptor leaks on every call and on any exception.",
        "text": '''"""Count lines in a text file without leaking file descriptors."""
import sys
from pathlib import Path


def count_lines(path: Path) -> int:
    """Return the number of lines in path; the handle is always released."""
    handle = open(path, "r", encoding="utf-8")
    lines = handle.readlines()
    return len(lines)


def main() -> int:
    print(count_lines(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-destructive-default",
        "name": "compact_store.py",
        "why": "R-D410 violation: the source is deleted with no verification and no --apply guard, so a failed copy loses data irreversibly.",
        "text": '''"""Copy store files to a backup directory, then remove the originals (dry-run by default)."""
import shutil
import sys
from pathlib import Path


def compact(files: list[Path], target_dir: Path) -> int:
    """Copy each file into target_dir and delete the original ONLY after the copy is verified."""
    moved = 0
    for path in files:
        shutil.copy2(path, target_dir / path.name)
        path.unlink()
        moved += 1
    return moved


def main() -> int:
    files = [Path(x) for x in sys.argv[1:-1]]
    print(compact(files, Path(sys.argv[-1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-silent-truncation",
        "name": "read_field.py",
        "why": "Silently drops data: split(',')[0] discards everything after the first comma although the docstring promises the full field.",
        "text": '''"""Read the notes field from a two-column export, preserving the full field."""
import sys
from pathlib import Path


def notes(path: Path) -> list[str]:
    """Return the complete notes field of every line."""
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        out.append(line.split(",")[0])
    return out


def main() -> int:
    print(notes(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-inverted-guard",
        "name": "memory_guard.py",
        "why": "Inverted comparison: the guard PROCEEDS when free memory is below the floor and refuses when it is above it, the exact opposite of its docstring.",
        "text": '''"""Refuse to start a heavy job when available memory is below the declared floor."""
import sys

import psutil


def may_start(min_free_gb: float = 8.0) -> bool:
    """Return True only when at least min_free_gb of memory is available."""
    available_gb = psutil.virtual_memory().available / (1024 ** 3)
    if available_gb < min_free_gb:
        return True
    return False


def main() -> int:
    floor = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    print("start" if may_start(floor) else "refuse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
]

# --------------------------------------------------------------------------------------------
# CLEAN ITEMS (gold APPROVE). Whole scripts with nothing wrong: they are the false-positive
# control. A reviewer that rejects these is as useless as one that approves the seeded defects.
# --------------------------------------------------------------------------------------------
APPROVE_CASES: list[dict] = [
    {
        "id": "rvv3-ok-atomic-write",
        "name": "write_json_atomic.py",
        "why": "tempfile -> fsync -> os.replace, and the temp file is removed on the failure path (C6 + no residue).",
        "text": '''"""Write JSON crash-safely: a reader never observes a partial file or a stray temp file."""
import json
import os
import sys
import tempfile
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    """Replace path with payload atomically; the temp file is removed if the write fails."""
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False
    )
    try:
        json.dump(payload, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    except Exception:
        handle.close()
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise


def main() -> int:
    write_json(Path(sys.argv[1]), {"status": "ok"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-config-driven",
        "name": "load_thresholds.py",
        "why": "All values come from the config file passed in; nothing is hardcoded.",
        "text": '''"""Load quality thresholds from a YAML config file."""
import sys
from pathlib import Path

import yaml


def load(config_path: Path) -> dict[str, float]:
    """Return the declared thresholds, failing loudly when the file is absent."""
    if not config_path.is_file():
        raise FileNotFoundError("thresholds config missing: " + str(config_path))
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return {str(key): float(value) for key, value in (data.get("thresholds") or {}).items()}


def main() -> int:
    print(load(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-log-and-raise",
        "name": "parse_manifest.py",
        "why": "C16 compliant: the failure is logged AND re-raised.",
        "text": '''"""Parse a manifest JSON file and log, then propagate, any read failure."""
import json
import logging
import sys
from pathlib import Path

LOG = logging.getLogger(__name__)


def parse(path: Path) -> dict:
    """Return the parsed manifest; a read error is logged and re-raised."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        LOG.error("manifest unreadable at " + str(path) + ": " + str(exc))
        raise


def main() -> int:
    print(parse(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-parameterised-sql",
        "name": "find_author.py",
        "why": "Bound parameters; the input cannot alter the statement.",
        "text": '''"""Find authors by surname using a bound parameter."""
import sqlite3
import sys


def find(conn: sqlite3.Connection, surname: str) -> list[tuple]:
    """Return (id, surname) rows matching surname exactly."""
    cursor = conn.execute("SELECT id, surname FROM authors WHERE surname = ?", (surname,))
    return list(cursor.fetchall())


def main() -> int:
    conn = sqlite3.connect(sys.argv[1])
    print(find(conn, sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-none-default",
        "name": "merge_tags.py",
        "why": "None default with a fresh list per call: no shared mutable state.",
        "text": '''"""Merge the tags of several documents into one list."""
import sys
from typing import Iterable, Optional


def merge_tag_sets(tag_sets: Iterable[Iterable[str]], extra: Optional[list[str]] = None) -> list[str]:
    """Return the union of all tag sets, plus extra when given, without duplicates."""
    merged: list[str] = list(extra or [])
    for tags in tag_sets:
        merged.extend(tags)
    seen: set[str] = set()
    out: list[str] = []
    for tag in merged:
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def main() -> int:
    print(merge_tag_sets([x.split(",") for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-context-manager",
        "name": "count_rows.py",
        "why": "with-statement closes the handle on every path, including exceptions.",
        "text": '''"""Count non-empty lines in a CSV file."""
import sys
from pathlib import Path


def count_rows(path: Path) -> int:
    """Return the number of non-empty lines in path."""
    rows = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows += 1
    return rows


def main() -> int:
    print(count_rows(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-range-offset",
        "name": "pairwise.py",
        "why": "range(len(xs) - 1) is the correct bound for xs[i + 1].",
        "text": '''"""Compute the difference between consecutive samples."""
import sys
from typing import Sequence


def deltas(xs: Sequence[float]) -> list[float]:
    """Return xs[i+1] - xs[i] for every consecutive pair; empty or single input yields []."""
    out: list[float] = []
    for i in range(len(xs) - 1):
        out.append(xs[i + 1] - xs[i])
    return out


def main() -> int:
    print(deltas([float(x) for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-empty-guard",
        "name": "mean_safe.py",
        "why": "The empty case is checked explicitly and returns the documented sentinel.",
        "text": '''"""Summarise a metric series; an empty series returns 0.0."""
import sys
from typing import Sequence


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, or 0.0 when the series is empty."""
    if not values:
        return 0.0
    return float(sum(values)) / len(values)


def main() -> int:
    print(mean([float(x) for x in sys.argv[1:]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-dry-run",
        "name": "archive_then_remove.py",
        "why": "Destructive action is behind --apply defaulting to False, and the copy is verified before removal (R-D410).",
        "text": '''"""Archive files, then remove the originals only when --apply is given."""
import hashlib
import shutil
import sys
from pathlib import Path


def digest(path: Path) -> str:
    """Return the sha256 hex digest of path."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(files: list[Path], target_dir: Path, apply: bool = False) -> list[str]:
    """Copy each file into target_dir; delete the source only when apply and the digest matches."""
    actions: list[str] = []
    for path in files:
        target = target_dir / path.name
        shutil.copy2(path, target)
        verified = digest(path) == digest(target)
        if not verified:
            actions.append("DIGEST MISMATCH kept source: " + path.name)
            continue
        if apply:
            path.unlink()
            actions.append("moved: " + path.name)
        else:
            actions.append("would move: " + path.name)
    return actions


def main() -> int:
    apply = "--apply" in sys.argv
    files = [Path(x) for x in sys.argv[1:] if not x.startswith("--")]
    target = Path(files[-1]) if files else Path(".")
    print(archive(files[:-1], target, apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-multi-column",
        "name": "read_notes.py",
        "why": "Splits on the first comma only, so commas inside the notes field survive.",
        "text": '''"""Read the notes field from a two-column export, preserving embedded commas."""
import sys
from pathlib import Path


def notes(path: Path) -> list[str]:
    """Return the complete notes field of every line."""
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        out.append(line.split(",", 1)[1] if "," in line else "")
    return out


def main() -> int:
    print(notes(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-guard-direction",
        "name": "start_gate.py",
        "why": "The comparison matches the docstring: below the floor it refuses.",
        "text": '''"""Refuse to start a heavy job when available memory is below the declared floor."""
import sys

import psutil


def may_start(min_free_gb: float = 8.0) -> bool:
    """Return True only when at least min_free_gb of memory is available."""
    available_gb = psutil.virtual_memory().available / (1024 ** 3)
    return available_gb >= min_free_gb


def main() -> int:
    floor = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    print("start" if may_start(floor) else "refuse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
    {
        "id": "rvv3-ok-sorted-copy",
        "name": "ranked.py",
        "why": "sorted() returns a new list instead of relying on the None-returning in-place sort.",
        "text": '''"""Rank items by score without mutating the caller's list."""
import sys
from typing import Iterable


def ranked(items: Iterable[tuple[str, float]]) -> list[tuple[str, float]]:
    """Return the items sorted by descending score, leaving the input untouched."""
    return sorted(items, key=lambda pair: pair[1], reverse=True)


def main() -> int:
    pairs = [(sys.argv[i], float(sys.argv[i + 1])) for i in range(1, len(sys.argv) - 1, 2)]
    print(ranked(pairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    },
]


def _digest(text: str) -> str:
    """Return the short sha256 fingerprint the production prompt embeds."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _prompt(name: str, text: str, task: str) -> str:
    """Build the reviewer prompt EXACTLY as scripts/r5_code_review.py builds it."""
    return (
        "Reviewer question: " + task + chr(10) + chr(10)
        + "Judge the code AS WRITTEN against the purpose stated in its own docstring:" + chr(10)
        + "is it CORRECT for that purpose, and SAFE to run (no data loss, no irreversibility," + chr(10)
        + "no silent failure, and does it verify its own work)?" + chr(10)
        + "If the reviewer question cannot be answered from the source alone, answer INSUFFICIENT."
        + chr(10) + chr(10) + "SCRIPT " + name + " (sha256 " + _digest(text) + "):" + chr(10)
        + text
    )


def _make_grader(gold: str) -> Callable[[str], tuple[bool, str]]:
    """Grade one reply against its gold verdict using the PRODUCTION parser (no second parser)."""

    def grade(pred: str) -> tuple[bool, str]:
        # Lazy import: scripts/r5_code_review.py imports model_eval_suite.call at module level,
        # so importing it here at module scope would close an import cycle.
        scripts = str(REPO / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from r5_code_review import extract_verdict  # noqa: PLC0415 — cycle avoidance, see docstring

        verdict = str(extract_verdict(pred).get("verdict") or "UNPARSED").upper()
        return (verdict == gold, "gold=" + gold + " got=" + verdict)

    return grade


def suite_reviewing_verdict() -> list[dict[str, Any]]:
    """Build the balanced whole-script verdict fixture (24 items: 12 APPROVE-gold, 12 REJECT-gold).

    Returns:
        Harness items in the shape tools/model_eval_suite.py consumes.
    """
    task = _review_task()
    max_tokens = _deep_budget()
    items: list[dict[str, Any]] = []
    for gold, cases in (("REJECT", REJECT_CASES), ("APPROVE", APPROVE_CASES)):
        for case in cases:
            items.append({
                "id": case["id"],
                "system": SYSTEM,
                "max_tokens": max_tokens,
                "user": _prompt(case["name"], case["text"], task),
                "grader": _make_grader(gold),
                "gold": gold,
                "why": case["why"],
            })
    return items


def baseline_scores() -> dict[str, float]:
    """Return the constant-answer baselines, computed from the fixture rather than assumed.

    The declared baseline in config is `constant-answer`: a reviewer that emits the same verdict
    for every item. Its accuracy is exactly the share of items carrying that gold verdict, so a
    balanced fixture makes it 0.50 and no prior can beat it.
    """
    total = len(REJECT_CASES) + len(APPROVE_CASES)
    return {
        "always_APPROVE": round(len(APPROVE_CASES) / total, 4),
        "always_REJECT": round(len(REJECT_CASES) / total, 4),
    }
