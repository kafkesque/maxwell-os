#!/usr/bin/env python3
"""yaml_guard.py - D-2648: text written to a YAML artifact is verified to PARSE before it is written.

WHY. MEASURED 2026-09-26: two artifacts were left UNPARSEABLE in one session by string surgery on YAML -
config/decisions.yaml (a record whose `decision:` value carried ": " inside an unquoted plain scalar) and
config/derivations.yaml (a sentence appended at END OF FILE, outside the folded block it belonged to, landing
after `enforcement.direction`). Neither writer checked the bytes it was about to write, so the defect surfaced
in the NEXT reader: recompute reported "not in sync" for a reason it could not name, and the homes rail died
inside yaml before it could even load its own registry. A writer that cannot verify its own output has moved the
failure downstream - the same class as a rail that prints ok while reading a stale artifact (D-2647).

TWO PRIMITIVES, ONE HOME (D-2646):
  assert_yaml     - parse the EXACT text about to be written; on failure name the artifact, the line, the column
                    and the line's own text, then refuse to write (C16: no silent error - and no
                    un-attributable one either).
  append_to_block - append lines INSIDE an existing block scalar (`>-`, `|`). Prose that contains ": " belongs
                    in a block scalar or in quotes; appending it at the end of the file is how a valid document
                    becomes an invalid one. The insertion point is computed from the file's OWN indentation,
                    never guessed.

The choice between quoting a scalar and moving it into a block is the ARTIFACT's own convention, not this
module's; this module only refuses to write what the next reader cannot load.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import yaml

BLOCK_MARKERS: tuple[str, ...] = (">-", ">", "|-", "|", ">+", "|+")

PREFIX = "yaml-guard"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
REGISTER = Path(__file__).resolve().parent.parent.parent / "config" / "yaml_guard.yaml"
SCAN_SUFFIXES = (".yaml", ".yml")
MIN_WHY = 20
MEMO_SCHEMA = "1"
MEMO_MAX_ENTRIES = 4000


def today() -> str:
    """The run date, DERIVED at run time. A date constant is a value that can only go stale (C12/C20)."""
    return time.strftime("%Y-%m-%d")


def duplicate_keys(text: str) -> list[tuple[str, int, int]]:
    """Every key declared MORE THAN ONCE inside the SAME mapping: [(key, first_line, second_line)].

    BUG-525 (measured 2026-09-26): PyYAML does not refuse a duplicate key - it SILENTLY keeps the last one, so a
    shadowed declaration is not a syntax error but a declared fact nobody reads (D-2649). Measured live the day
    this rule landed: config/pipeline_config.yaml#stage5.confidence was declared twice (the shadowed copy sat above
    `borp_bypass_types:`) and config/store_columns.yaml carried two `ceiling:` blocks, one written by the rail that
    had been asked to record the other. The rule is per-MAPPING: `stage5.confidence` and `test.x.confidence` are
    two homes for TWO facts and are legal; the same key twice in one mapping is one fact with two homes.

    An unparseable document returns [] - that is assert_yaml's subject, not this rule's (one rule, one home).
    """
    found: list[tuple[str, int, int]] = []

    class _Locate(yaml.SafeLoader):
        """A SafeLoader that keeps the source line of every key node."""

    def _mapping(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> dict:
        seen: dict[str, int] = {}
        for key_node, _value in node.value:
            try:
                key = str(loader.construct_object(key_node, deep=True))
            except yaml.YAMLError:
                continue
            line = key_node.start_mark.line + 1
            if key in seen:
                found.append((key, seen[key], line))
            else:
                seen[key] = line
        return yaml.SafeLoader.construct_mapping(loader, node)

    _Locate.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
    try:
        yaml.load(text, Loader=_Locate)
    except yaml.YAMLError:
        return []
    return found


def file_verdict(text: str) -> dict:
    """The RAW per-file measurement: does it parse (and WHY not), and which keys are declared twice.

    BUG-954. This is deliberately the SMALLEST thing that is a pure function of the bytes: everything a scan
    decides AROUND it - is the path exempt, is it declared `owed`, is an owed entry now stale, is a declared path
    unreachable, did the scan shrink - is REGISTER-level and is NEVER memoised, because those readings are about
    the register, not about the file. A cache that answered a register-level question would answer it about a
    register it never read.
    """
    try:
        yaml.safe_load(text)
        broken = ""
    except yaml.YAMLError as exc:
        broken = str(getattr(exc, "problem", exc))
    return {"broken": broken, "dups": [list(d) for d in duplicate_keys(text)]}


def source_digest() -> str:
    """A digest of every input to a per-file verdict that is NOT the artifact's own bytes.

    MEASURED (BUG-954): the verdict is two computations over the same text - `yaml.safe_load` and the
    `duplicate_keys` walk - over a set whose bytes are 98.7 % frozen pre-images, so the same bytes are re-decided
    every run. A memo keyed by bytes ALONE would keep answering with the OLD rule after the rule changed: a cache
    that outlives its own code is a silent verdict about code that no longer exists. PyYAML's own version is folded
    in because `broken` is PyYAML's sentence, not ours - a library upgrade can change it without this file moving.
    """
    own = Path(__file__).resolve().read_bytes()
    library = str(getattr(yaml, "__version__", "?"))
    return hashlib.sha256(own + b"\x00" + library.encode("utf-8")).hexdigest()


def memo_home(register: dict, root: Path) -> Path | None:
    """The memo's DECLARED home, or None when the register does not enable one (C12: never a literal path here)."""
    spec = register.get("memo") if isinstance(register.get("memo"), dict) else {}
    if not spec.get("enabled") or not spec.get("path"):
        return None
    return (root / str(spec["path"])).resolve()


def memo_read(path: Path | None) -> dict:
    """Every recorded verdict, or {} - an unreadable, foreign or older-schema memo is a MISS, never a verdict.

    Fail-OPEN toward recomputation (and closed toward trusting): the only cost of a miss is the time the memo
    exists to save, while the cost of trusting a corrupt book is a wrong verdict about the repository.
    """
    if path is None or not path.is_file():
        return {}
    try:
        book = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(book, dict) or str(book.get("schema")) != MEMO_SCHEMA:
        return {}
    entries = book.get("entries")
    return entries if isinstance(entries, dict) else {}


def memo_write(path: Path | None, entries: dict, ceiling: int) -> None:
    """Trim to the declared ceiling and persist crash-safely (C6): tempfile -> fsync -> os.replace.

    An unwritable memo is REPORTED and survived, never raised: the memo is an optimisation, and a cache whose
    failure breaks the rail would be a new single point of failure bought with an old one's time.
    """
    if path is None:
        return
    while len(entries) > ceiling:
        entries.pop(next(iter(entries)))          # json keeps insertion order, so this drops the LEAST recently used
    book = {"schema": MEMO_SCHEMA, "entries": entries}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".memo.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(book, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        print("  note memo NOT written (" + path.name + "): the scan is unaffected")


def memo_verdict(text: str, digest: str, entries: dict) -> tuple[dict, bool]:
    """(verdict, was_a_hit) for these bytes under these rules; records a computed verdict in `entries`.

    The key is content-addressed on purpose: two paths holding identical bytes hold one verdict, which is why the
    frozen pre-images that dominate this scan's byte volume cost the parse ONCE each rather than once per run.
    A hit is re-inserted so the ceiling drops the least recently USED entry, not the oldest written.
    """
    key = hashlib.sha256(digest.encode("utf-8") + b"\x00" + text.encode("utf-8")).hexdigest()
    hit = entries.pop(key, None)
    if (isinstance(hit, dict) and isinstance(hit.get("broken"), str)
            and isinstance(hit.get("dups"), list) and all(len(d) == 3 for d in hit["dups"])):
        entries[key] = hit
        return {"broken": hit["broken"], "dups": hit["dups"]}, True
    verdict = file_verdict(text)
    entries[key] = verdict
    return verdict, False


def assert_yaml(text: str, path: str, writer: str) -> None:
    """Fail closed unless `text` parses as YAML UNAMBIGUOUSLY, naming the artifact, the place and the line.

    A writer of YAML that does not parse its own bytes is not a writer but a hope (C16). D-2648 said the bytes
    must PARSE; BUG-525 (2026-09-26) showed that "parses" was too weak - a document in which PyYAML silently
    resolves a duplicate key parses and lies. The rule is therefore: the bytes must parse AND declare every key
    at most once per mapping (D-2649).
    """
    # R5 DISSENT (reviewed 2026-09-26 by gemma-4-E4B-it-MLX-4bit): the reviewer asked for a blanket
    # `except Exception` here. REJECTED, with the reason: C16 forbids an except that neither logs nor raises,
    # and a TypeError from a programming mistake must stay LOUD - a crash re-labelled "refused to write" HIDES
    # a bug. What is legitimate in the finding is the wrong TYPE, so the type is named instead:
    if not isinstance(text, str):
        raise SystemExit(
            "FAIL-CLOSED (" + PREFIX + "): " + writer + " handed " + path + " a non-str document ("
            + type(text).__name__ + ") - PyYAML would silently decode bytes, so a guard that parses the wrong"
              " type is not a guard (C16)")
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = "" if mark is None else (" at line " + str(mark.line + 1) + ", column " + str(mark.column + 1))
        shown = ""
        if mark is not None:
            rows = text.splitlines()
            if 0 <= mark.line < len(rows):
                shown = " || the line reads: " + rows[mark.line].strip()[:180]
        raise SystemExit(
            "FAIL-CLOSED (" + PREFIX + "): " + writer + " is about to write " + path + " that does NOT parse"
            + where + " || " + str(getattr(exc, "problem", exc)) + shown
            + " || a value carrying a colon-space is a PLAIN SCALAR: quote it or move it into a block scalar -"
              " refusing to write an artifact the next reader cannot load (D-2648)"
        ) from exc
    ambiguous = duplicate_keys(text)
    if ambiguous:
        key, first, later = ambiguous[0]
        rest = "" if len(ambiguous) == 1 else (" (+" + str(len(ambiguous) - 1) + " more)")
        raise SystemExit(
            "FAIL-CLOSED (" + PREFIX + "): " + writer + " is about to write " + path + " in which the key "
            + repr(key) + " is declared TWICE (lines " + str(first) + " and " + str(later) + ")" + rest
            + ". PyYAML does NOT refuse this - it silently keeps the LAST declaration, so the first is a fact"
              " nobody reads (D-2649: one declared fact, one declaration home). Delete the shadowed declaration;"
              " if the two genuinely disagree, THAT is the bug.")


def block_bounds(text: str, key: str) -> tuple[int, int, int]:
    """Return (end_index, content_indent, header_index) for the block scalar `key`, or fail closed.

    The insertion point is the index AFTER the block's last content line: blank lines are stepped over but never
    crossed, so prose is inserted among the prose and not after it.
    """
    rows = text.splitlines(keepends=True)
    header = -1
    for index, raw in enumerate(rows):
        body = raw.strip()
        if not body.startswith(key + ":"):
            continue
        if body[len(key) + 1:].strip() in BLOCK_MARKERS:
            header = index
            break
    if header < 0:
        raise SystemExit(
            "FAIL-CLOSED (" + PREFIX + "): " + key + " is not a block scalar (or is absent) - prose that belongs"
            " in a block may not be appended at the end of the file, where it is either meaningless or, when it"
            " carries a colon-space, a syntax error"
        )
    h_indent = len(rows[header]) - len(rows[header].lstrip(" \t"))
    c_indent = h_indent + 2
    for raw in rows[header + 1:]:
        if raw.strip():
            here = len(raw) - len(raw.lstrip(" \t"))
            if here > h_indent:
                c_indent = here
            break
    end = header + 1
    for index in range(header + 1, len(rows)):
        raw = rows[index]
        if not raw.strip():
            continue
        if (len(raw) - len(raw.lstrip(" \t"))) < c_indent:
            break
        end = index + 1
    return end, c_indent, header


def append_to_block(text: str, key: str, lines: list[str]) -> str:
    """Append `lines` INSIDE the block scalar `key`, at that block's own content indentation."""
    end, c_indent, _ = block_bounds(text, key)
    rows = text.splitlines(keepends=True)
    pad = " " * c_indent
    added = "".join(pad + line.rstrip() + chr(10) for line in lines)
    return "".join(rows[:end]) + added + "".join(rows[end:])


def _memo_case() -> str:
    """Bytes whose verdict is unambiguous and non-empty: it parses, and ONE key is declared twice."""
    return "a: 1" + chr(10) + "b: 2" + chr(10) + "a: 3" + chr(10)


def _memo_round_trip() -> bool:
    """A hit must return the verdict the walk computes - not merely SOME verdict."""
    entries: dict = {}
    text = _memo_case()
    first, hit_first = memo_verdict(text, "rule-a", entries)
    second, hit_second = memo_verdict(text, "rule-a", entries)
    return (not hit_first) and hit_second and first == second == file_verdict(text)


def _memo_digest_is_an_input() -> bool:
    """The control AGAINST staleness: same bytes under a moved rule must MISS, or the cache outlives its code."""
    entries: dict = {}
    text = _memo_case()
    memo_verdict(text, "rule-a", entries)
    _verdict, hit = memo_verdict(text, "rule-b", entries)
    return (not hit) and len(entries) == 2


def _memo_corrupt_is_a_miss() -> bool:
    """A book that cannot be read, or was written by another schema, is a MISS - never a verdict."""
    with tempfile.TemporaryDirectory() as tmp:
        book = Path(tmp) / "memo.json"
        book.write_text('{"schema": "1", "entries": ', encoding="utf-8")
        if memo_read(book) != {}:
            return False
        book.write_text('{"schema": "999", "entries": {"k": {}}}', encoding="utf-8")
        if memo_read(book) != {}:
            return False
        book.write_text('{"schema": "1", "entries": {"k": {"broken": "", "dups": [["a", 1, 3]]}}}',
                        encoding="utf-8")
        return memo_read(book) == {"k": {"broken": "", "dups": [["a", 1, 3]]}}


def _memo_survives_a_disk_round_trip() -> bool:
    """The memo exists to save time ACROSS runs, so the write/read pair is what has to work, not just the dict."""
    with tempfile.TemporaryDirectory() as tmp:
        book = Path(tmp) / "nested" / "memo.json"
        entries: dict = {}
        text = _memo_case()
        memo_verdict(text, "rule-a", entries)
        memo_write(book, entries, MEMO_MAX_ENTRIES)
        if not book.is_file():
            return False
        _verdict, hit = memo_verdict(text, "rule-a", memo_read(book))
        return hit


def _memo_respects_its_ceiling() -> bool:
    """Growth control: the ceiling must drop the least recently USED verdict, not the oldest written (D-3038)."""
    entries: dict = {}
    for index in range(5):
        memo_verdict("k: " + str(index) + chr(10), "rule-a", entries)
    memo_verdict("k: 0" + chr(10), "rule-a", entries)          # touch the oldest, so it is no longer least recently used
    with tempfile.TemporaryDirectory() as tmp:
        book = Path(tmp) / "memo.json"
        memo_write(book, entries, 3)
        kept = memo_read(book)
        _v1, kept_the_touched = memo_verdict("k: 0" + chr(10), "rule-a", dict(kept))
        _v2, kept_the_stale = memo_verdict("k: 1" + chr(10), "rule-a", dict(kept))
        return len(kept) == 3 and kept_the_touched and not kept_the_stale


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492: a detector nobody has seen fail is not a detector)."""
    # MEASURED 2026-09-26 by this rail's own first run: the control MUST be handed a THUNK, not a value. With
    # `refused(append_to_block(...))` the call was evaluated BEFORE refused() could catch anything, so the
    # SystemExit escaped the control list and the selftest died instead of reporting. An eager argument is not a
    # detector.
    def refused(thunk) -> bool:
        try:
            thunk()
            return False
        except SystemExit:
            return True

    doc = "a: 1" + chr(10) + "note: >-" + chr(10) + "  prose with a colon: inside it" + chr(10) + "b: 2" + chr(10)
    appended = append_to_block(doc, "note", ["and a second sentence: still prose"])
    return [
        ("an unquoted plain scalar carrying a colon-space does NOT parse",
         refused(lambda: assert_yaml("decision: measured, never guessed - state is owner judgement: a "
                                     "checkpoint", "control.yaml", PREFIX))),
        ("the SAME value single-quoted parses",
         not refused(lambda: assert_yaml("decision: 'state is owner judgement: a checkpoint'", "control.yaml",
                                         PREFIX))),
        ("a colon-space inside a BLOCK scalar parses (why prose belongs in a block)",
         not refused(lambda: assert_yaml(doc, "control.yaml", PREFIX))),
        ("appending inserts INSIDE the block, and the result still parses",
         yaml.safe_load(appended)["note"].endswith("still prose") and yaml.safe_load(appended)["b"] == 2),
        ("the append moves the file by exactly one line",
         len(appended.splitlines()) == len(doc.splitlines()) + 1),
        ("appending to a key that is not a block scalar fails CLOSED",
         refused(lambda: append_to_block("a: 1" + chr(10) + "b: 2" + chr(10), "b", ["x"]))),
        ("appending to an ABSENT key fails CLOSED",
         refused(lambda: append_to_block("a: 1" + chr(10), "zz", ["x"]))),
        ("the block is found at any indentation (a nested registry block)",
         yaml.safe_load(append_to_block("  note: >-" + chr(10) + "    deep" + chr(10),
                                        "note", ["deeper: still prose"]))["note"].endswith("still prose")),
        # BUG-525 controls. The second one is the control AGAINST overreach: a rule that fails on any repeated
        # key name anywhere would forbid legal YAML, so the tolerance for two DIFFERENT mappings is itself tested.
        ("a key declared twice in the SAME mapping is found, with BOTH line numbers",
         duplicate_keys("a: 1" + chr(10) + "b: 2" + chr(10) + "a: 3" + chr(10)) == [("a", 1, 3)]),
        ("the SAME key in TWO different mappings is NOT a duplicate",
         duplicate_keys("x:" + chr(10) + "  a: 1" + chr(10) + "y:" + chr(10) + "  a: 2" + chr(10)) == []),
        ("assert_yaml REFUSES a duplicate instead of letting last-wins decide",
         refused(lambda: assert_yaml("a: 1" + chr(10) + "a: 2" + chr(10), "control.yaml", PREFIX))),
        ("an unparseable document is NOT this rule's subject (assert_yaml owns it)",
         duplicate_keys("a: 1" + chr(10) + "  b: 2" + chr(10)) == []),
        # BUG-954 controls: five readings, and the third and fourth are the controls AGAINST the memo being
        # trusted - a corrupt book is a miss, and a book written under a DIFFERENT rule is a miss too. A cache
        # nobody has seen refuse is a cache that will one day answer for code that no longer exists.
        ("a memo HIT returns exactly the verdict the walk computes for the same bytes", _memo_round_trip()),
        ("a memo recorded under a MOVED rule is a MISS, not a verdict", _memo_digest_is_an_input()),
        ("a corrupt or foreign-schema memo file is a MISS, never a verdict", _memo_corrupt_is_a_miss()),
        ("the memo survives a DISK round trip (it is there to save the NEXT run)", _memo_survives_a_disk_round_trip()),
        ("the memo drops the LEAST RECENTLY USED verdict when it reaches its ceiling", _memo_respects_its_ceiling()),
    ]


def _artifacts(register: dict, root: Path) -> list[Path]:
    """Every YAML artifact the register declares, walked to each root's OWN depth (a bounded walk, not a crawl)."""
    found: list[Path] = []
    skips = {str(s) for s in (register.get("skip_dirs") or [])}
    for entry in (register.get("roots") or []):
        if isinstance(entry, dict):
            rel, depth = str(entry.get("path") or ""), int(entry.get("depth") or 0)
        else:
            rel, depth = str(entry), 0
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            below = len(Path(dirpath).resolve().relative_to(base).parts)
            if below >= depth:
                dirnames[:] = []
            dirnames[:] = [d for d in sorted(dirnames) if d not in skips]
            for name in sorted(filenames):
                if Path(name).suffix in SCAN_SUFFIXES:
                    found.append(Path(dirpath) / name)
    return sorted(set(found))


def scan(register: dict, root: Path) -> tuple[list[str], int, int]:
    """Report (faults, owed_debt, artifacts_scanned) for the declared roots.

    OWED debt is owed, not drift: an artifact whose ambiguity cannot be REMOVED by this rail (a snapshot with no
    original, a hand-authored prompt) is loud and rc=2, and the owner settles it. The owed list is shrink-only:
    an entry that now reads cleanly is STALE-OWED, so the ceiling can never be padded.

    BUG-954: the two PER-FILE computations (the parse and the duplicate-key walk) are memoised on the FILE'S OWN
    BYTES, because MEASURED they dominate this rail's cost over a set that is 98.7 % frozen pre-images. Everything
    decided ABOVE a file - exempt, owed, STALE-OWED, MISSING-WHY, UNSCOPED, SCAN-SHRANK, the artifact count - is
    register-level and is recomputed on EVERY run, so a memo can never answer a question about a register it did
    not read. The memo is reported, never gated on: it changes the time this rail takes and nothing it says.
    """
    faults: list[str] = []
    owed = {str(e.get("path")): str(e.get("why") or "") for e in (register.get("owed") or []) if isinstance(e, dict)}
    exempt = {str(e.get("path")): str(e.get("why") or "") for e in (register.get("exempt") or [])}
    files = _artifacts(register, root)
    seen = {path.relative_to(root).as_posix() for path in files}
    home = memo_home(register, root)
    digest = source_digest() if home is not None else ""
    entries = memo_read(home)
    ceiling = int((register.get("memo") or {}).get("max_entries") or MEMO_MAX_ENTRIES)
    hits = computed = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel in exempt:
            continue
        try:
            text = path.read_text(encoding="utf-8")  # BUG-521: a DECLARED codec, never the platform default
        except (UnicodeDecodeError, OSError) as exc:
            faults.append("UNREADABLE: " + rel + " cannot be read as UTF-8 (" + type(exc).__name__ + ") - an"
                          " artifact whose bytes cannot be decoded is an undeclared artifact (C16/BUG-521)")
            continue
        if home is None:
            verdict = file_verdict(text)
        else:
            verdict, was_hit = memo_verdict(text, digest, entries)
            hits, computed = hits + int(was_hit), computed + int(not was_hit)
        broken = verdict["broken"]
        if rel in owed:
            if not broken and not verdict["dups"]:
                faults.append("STALE-OWED: " + rel + " is declared `owed` but now reads cleanly - delete the entry"
                              " (the owed list is shrink-only, D-2642)")
            continue
        if broken:
            faults.append("UNPARSEABLE: " + rel + " does NOT parse (" + broken[:120] + ") - an artifact whose"
                          " declarations cannot be READ is an undeclared artifact (BUG-525/C16)")
        for key, first, later in verdict["dups"]:
            faults.append("DUP-KEY: " + rel + " declares " + repr(key) + " at line " + str(first) + " and AGAIN at"
                          " line " + str(later) + " - PyYAML keeps the LAST and silently drops the first, so a"
                          " declared fact has two homes (D-2649)")
    for rel, why in sorted(owed.items()):
        if len(why) < MIN_WHY:
            faults.append("MISSING-WHY: " + rel + " is declared `owed` with " + str(len(why)) + " char(s) of why"
                          " (min " + str(MIN_WHY) + ") - a declaration without a reason is a comment (C12)")
    for rel in sorted(set(owed) | set(exempt)):
        if rel not in seen:
            faults.append("UNSCOPED: " + rel + " is declared but NO declared root reaches it - a declaration the"
                          " scan cannot see is a self-declared gap (C12)")
    receipt = int((register.get("receipt") or {}).get("artifacts") or 0)
    if receipt and len(files) < receipt:
        faults.append("SCAN-SHRANK: the scan covered " + str(len(files)) + " artifact(s) and its receipt declares "
                      + str(receipt) + " - a scan that silently shrank is a blind spot reported as a clean scan")
    if home is not None:
        memo_write(home, entries, ceiling)
        print("  memo " + str(hits) + " hit(s) / " + str(computed) + " computed | " + str(len(entries))
              + " verdict(s) recorded (BUG-954: content-addressed on the BYTES + a digest of this module and of"
              " PyYAML; every register-level reading is recomputed every run)")
    return faults, len(owed), len(files)


def main(argv: list[str]) -> int:
    """--selftest runs the known-answer controls; --check scans the declared roots for ambiguous declarations."""
    modes = [a for a in argv if a in ("--selftest", "--check")]
    if len(argv) != 1 or len(modes) != 1:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): exactly ONE of --selftest | --check is required (C16); got "
                         + repr(argv))
    if modes[0] == "--check":
        register = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
        faults, debt, scanned = scan(register, REGISTER.parent.parent)
        for fault in faults:
            print("  DRIFT " + fault)
        print(("FAIL " if faults else ("OWED " if debt else "ok ")) + PREFIX + ": " + str(scanned)
              + " artifact(s) scanned | owed " + str(debt) + " | " + str(len(register.get("skip_dirs") or []))
              + " dir name(s) skipped BY DECLARATION")
        return EXIT_DRIFT if faults else (EXIT_OWED if debt else EXIT_CLEAN)
    rows = controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [name for name, ok in rows if not ok]
    if failed:
        print("FAIL " + PREFIX + ": " + str(len(failed)) + " of " + str(len(rows))
              + " known-answer control(s) did not fire")
        return EXIT_DRIFT
    print("ok " + PREFIX + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
    return EXIT_CLEAN


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
