#!/usr/bin/env python3
"""declare_encoding.py — T-114: add `encoding='utf-8'` to UNDECLARED text WRITE sites (D-2644).

WHY WRITES FIRST (C3/C26/R14): a write without a named codec emits bytes the ENVIRONMENT decides
(locale.getpreferredencoding). Under LC_ALL=C a non-ASCII byte raises a UnicodeEncodeError that names no
artifact, and on Windows cp1252 a 0xD1 em dash is written as two different bytes per machine — so a
sha256 pin does not pin the same bytes. The 310 READ sites are lower risk (they fail CLOSED on decode,
not silently) and are the next slice.

REUSES THE RAIL'S DETECTOR: this rewriter imports check_undeclared_encoding.py's own walk so the thing
that decides "this is an undeclared WRITE site" is the SAME code the rail runs. The two can never disagree
about what is a write site (D-2646: never re-implement a reader).

SAFETY: reads as BYTES (ast col_offset is a UTF-8 byte offset), replaces ONLY the call span, preserves all
comments and formatting (a multi-line call gets the keyword on its content line, not the closing-paren line),
and writes crash-safe (tempfile -> fsync -> os.replace, C6). Idempotent: a second run changes nothing.

CLI: (no flag = dry-run) | --apply | --selftest. Exactly one action.
"""
from __future__ import annotations

import argparse
import ast
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_undeclared_encoding as cue  # noqa: E402
import yaml  # noqa: E402

REGISTER = ROOT / "config" / "undeclared_encoding.yaml"


def _write_calls(source: str, non_text_open: tuple[str, ...]) -> list[ast.Call]:
    """Every undeclared WRITE call in one module, as the AST node (same walk as the rail, node-returning)."""
    out: list[ast.Call] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
        if name not in ("open",) + cue.TEXT_CALLS:
            continue
        if (name == "open" and isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name) and func.value.id in non_text_open):
            continue
        if cue._names_encoding(node, name):
            continue
        if name in cue.TEXT_CALLS:
            if name == "write_text":
                out.append(node)
            continue
        literal, mode = cue._literal_mode(node, name)
        if not literal:
            continue  # unresolvable: a non-literal mode is not proof of text, never auto-repaired
        if "b" in mode:
            continue  # binary: no codec
        if any(c in mode for c in cue.WRITE_MODES):
            out.append(node)
    return out


def _insert_encoding(call_span: bytes, has_args: bool) -> bytes:
    """Insert `encoding='utf-8'` before the closing paren, preserving every argument byte-for-byte.

    A SURGICAL insertion (not ast.unparse): unparse re-quotes string literals (`"x"` -> `'x'`), which is
    needless churn on the data arguments of `write_text`. This walks back over trailing whitespace — INCLUDING
    newlines, so a multi-line call whose closing paren is on its own line lands the keyword on the content line —
    so the result reads `open(p, 'w', encoding='utf-8')` with no stray space before the comma.
    """
    close = len(call_span) - 1  # call_span[-1] is the closing ')'
    j = close
    while j > 0 and call_span[j - 1:j] in (b" ", b"\t", b"\n", b"\r"):
        j -= 1
    sep = b", " if has_args else b""
    return call_span[:j] + sep + b"encoding='utf-8'" + call_span[j:]


def rewrite(source: str, non_text_open: tuple[str, ...]) -> tuple[str, int]:
    """Rewrite the module, replacing each undeclared write call with its utf-8-declared form.

    Returns (new_source, changed_count). Byte spans are computed from the AST col offsets (UTF-8 byte
    offsets), so multi-byte characters do not shift the edits; a multi-line call is handled by walking
    back over its trailing whitespace in `_insert_encoding` (no call is skipped).
    """
    calls = _write_calls(source, non_text_open)
    if not calls:
        return source, 0
    lines = source.splitlines(keepends=True)
    # byte offset of the start of each line (col_offset is a UTF-8 byte offset)
    line_start: list[int] = [0]
    for ln in lines:
        line_start.append(line_start[-1] + len(ln.encode("utf-8")))
    raw = source.encode("utf-8")
    edits: list[tuple[int, int, bytes]] = []
    for node in calls:
        start = line_start[node.lineno - 1] + node.col_offset
        end = line_start[node.end_lineno - 1] + node.end_col_offset
        edits.append((start, end, _insert_encoding(raw[start:end], bool(node.args or node.keywords))))
    # apply from the END so earlier offsets stay valid
    buf = raw
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        buf = buf[:start] + repl + buf[end:]
    return buf.decode("utf-8"), len(edits)


def _crash_safe_write(path: Path, data: bytes) -> None:
    """C6: tempfile in the same directory -> fsync -> os.replace (atomic on POSIX), preserving mode.

    `tempfile.mkstemp` mints a 0600 file and `os.replace` carries THAT mode forward, so rewriting an
    executable module would silently drop its exec bit — a declared command written as a BARE path must
    stay executable (BUG-842/T-146). The original mode is read first and re-applied to the tempfile
    before the atomic replace.
    """
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def run(apply: bool) -> int:
    """Scan, rewrite, and (with --apply) write back each module with at least one write site."""
    reg = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    non_text_open = tuple(str(x) for x in cue.declared(reg, "non_text_open"))
    found, _ = cue.scan(reg, ROOT)
    total = 0
    changed_files = 0
    for rel, sites in found.items():
        if not any(k == "write" for _, k in sites):
            continue
        path = ROOT / rel
        source = path.read_text(encoding="utf-8")
        new, n = rewrite(source, non_text_open)
        if n == 0:
            continue
        total += n
        changed_files += 1
        print(f"  {'APPLY' if apply else 'dry  '} {rel}: {n} write site(s)")
        if apply:
            _crash_safe_write(path, new.encode("utf-8"))
    print(f"declare-encoding: {total} write site(s) across {changed_files} file(s)"
          + (" (DRY RUN — no file changed)" if not apply else " (written, crash-safe C6)"))
    return 0


def selftest() -> int:
    """Known-answer controls: the rewriter must add exactly one keyword and never touch reads/binary."""
    def r(src: str) -> str:
        return rewrite(src, ())[0]

    checks = [
        ("write_text gets encoding",
         r('p.write_text("x")\n') == 'p.write_text("x", encoding=\'utf-8\')\n'),
        ("builtin open('w') gets encoding",
         r("open(p, 'w')\n") == "open(p, 'w', encoding='utf-8')\n"),
        ("Path.open('a') gets encoding",
         r("p.open('a')\n") == "p.open('a', encoding='utf-8')\n"),
        ("read is untouched",
         r("p.read_text()\n") == "p.read_text()\n"),
        ("binary is untouched",
         r("open(p, 'rb')\n") == "open(p, 'rb')\n"),
        ("already-declared is untouched",
         r("p.write_text('x', encoding='utf-8')\n") == "p.write_text('x', encoding='utf-8')\n"),
        ("idempotent",
         r(r('p.write_text("x")\n')) == 'p.write_text("x", encoding=\'utf-8\')\n'),
        ("trailing comment is preserved",
         r("open(p, 'w')  # note\n") == "open(p, 'w', encoding='utf-8')  # note\n"),
        ("multi-line write_text lands the keyword on the content line",
         r('p.write_text(\n    json.dumps({"a": 1}) + "\\n"\n)\n')
         == 'p.write_text(\n    json.dumps({"a": 1}) + "\\n", encoding=\'utf-8\'\n)\n'),
    ]
    ok = True
    for name, passed in checks:
        print(("  ok   " if passed else "  FAIL ") + name)
        ok = ok and passed
    # C6/BUG-842 control: the crash-safe write must PRESERVE the executable bit (a declared bare-path
    # command that loses its +x on rewrite is a silent break, T-146), and stay so on a second write.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exe_mod.py"
        p.write_bytes(b"x = 1\n")
        p.chmod(0o755)
        _crash_safe_write(p, b"x = 2\n")
        preserved = stat.S_IMODE(p.stat().st_mode) == 0o755
        _crash_safe_write(p, b"x = 3\n")
        preserved = preserved and stat.S_IMODE(p.stat().st_mode) == 0o755
    mode_ok = preserved
    print(("  ok   " if mode_ok else "  FAIL ") + "crash-safe write preserves the executable bit")
    ok = ok and mode_ok
    print("declare-encoding selftest: " + ("all ok" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="T-114: declare utf-8 on undeclared text WRITE sites (D-2644)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="write the changes (default is dry-run)")
    group.add_argument("--selftest", action="store_true", help="known-answer controls on the rewriter")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
