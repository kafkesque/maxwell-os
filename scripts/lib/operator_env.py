#!/usr/bin/env python3
"""operator_env.py - THE home for "the operator's key: flag, environment, or the repo's .env" (D-2646).

MEASURED 2026-09-26 (BUG-519): ONE rule had FIVE homes with THREE behaviours -
  * scripts/vote_anchor_domains.py:118 read `.env` with errors="ignore" - a byte that is not UTF-8 was DROPPED
    SILENTLY (the BUG-511/C16 class: no crash, changed text);
  * scripts/vote_flagged_core.py:77 read it with Path.read_text()'s PLATFORM-DEFAULT codec;
  * three shell copies (scripts/run_joint_vote.sh:32, run_remaining_axes_vote.sh:5, run_queue_59_vote.sh:7) grep
    the line and `tr -d '[:space:]'` the value, which is a DIFFERENT parse of the same line.
Nothing reported the divergence - and a second implementation of one rule IS the defect (D-2646, BUG-499/502 class).

THE BYTES ARE READ THROUGH THE ENCODING HOME. artifact_encoding.open_artifact() opens an artifact only in the
encoding the artifact DECLARES and fails CLOSED when the bytes are not UTF-8 and undeclared. `.env` carries no
declaration ON PURPOSE: it is gitignored, so a declaration in the tracked register would be a claim the repo cannot
verify, and an absent .env is normal. The measured path still decides utf-8 for utf-8 bytes and fails LOUDLY and
actionably otherwise - which is the point: no reader may drop a byte and carry on (C16).

THE KEY IS NEVER PRINTED, LOGGED, OR PUT IN AN ERROR MESSAGE. read_key() returns "" when the key is absent and
leaves each caller's own FATAL message in charge (the two callers differed there too; that difference is preserved).

RESIDUAL, DECLARED NOT HIDDEN: the three shell copies still parse .env themselves. They cannot import this module
without an `eval` of a secret (a shell-quoting hazard worse than the duplication); the follow-up is a shell-safe
one-home, recorded as owed in the buglog.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

PREFIX = "operator-env"
ENV_FILE = ".env"
DEFAULT_NAME = "DEEPSEEK_API_KEY"


def parse_env_text(text: str, name: str = DEFAULT_NAME) -> str:
    """The ONE parse of a KEY=value line: the first line whose STRIPPED form starts with `name=` wins.

    Behaviour-preserving relative to the copies it replaces: outer whitespace and one layer of quotes are
    stripped (inner whitespace is NOT - a shell copy's `tr -d '[:space:]'` is exactly the divergence this
    removes), a later duplicate never overrides the first, and a COMMENTED-OUT key is not a key.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(name + "="):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def read_key(name: str = DEFAULT_NAME, explicit: str = "", repo: Path | None = None) -> str:
    """The ONE resolution order: the explicit flag, then the environment, then the repo's .env. '' when absent.

    The .env bytes are decoded by the DECLARED-encoding home, so a non-UTF-8 byte fails CLOSED naming the
    artifact instead of being dropped - and a bad byte ANYWHERE in the file fails the read, because the whole
    file is decoded before it is parsed. Never prints the value.
    """
    if explicit:
        return explicit
    from_env = os.environ.get(name, "")
    if from_env:
        return from_env
    root = Path(repo) if repo is not None else REPO
    path = root / ENV_FILE
    if not path.exists():
        return ""
    return parse_env_text(artifact_encoding.open_artifact(path, root).read(), name)


def _fixture(raw: bytes) -> tuple[Path, object]:
    """A throwaway repo holding exactly one .env, so a control cannot touch the operator's real one."""
    root = Path(tempfile.mkdtemp(prefix="operator_env_"))
    (root / ENV_FILE).write_bytes(raw)
    return root, root


def controls() -> list[tuple[str, object]]:
    """Known-answer controls (BUG-492): each is handed a THUNK, so a control is not an eager value."""
    def raises(fn) -> bool:
        try:
            fn()
            return False
        except SystemExit:
            return True

    def _empty():
        """A fixture repo with no .env at all."""
        return Path(tempfile.mkdtemp(prefix="operator_env_none_"))

    def flag_wins() -> bool:
        return read_key(explicit="from-flag", repo=_empty()) == "from-flag"

    def env_beats_file() -> bool:
        root, _ = _fixture(b"DEEPSEEK_API_KEY=from-file\n")
        os.environ["DEEPSEEK_API_KEY"] = "from-env"
        try:
            return read_key(repo=root) == "from-env"
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

    def file_used_when_no_flag_no_env() -> bool:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        root, _ = _fixture(b"DEEPSEEK_API_KEY=from-file\n")
        return read_key(repo=root) == "from-file"

    def quoted_and_padded() -> bool:
        return parse_env_text('DEEPSEEK_API_KEY="abc123"   \n') == "abc123"

    def commented_out_is_not_a_key() -> bool:
        return parse_env_text("# DEEPSEEK_API_KEY=nope\nexport OTHER=1\n") == ""

    def first_duplicate_wins() -> bool:
        return parse_env_text("DEEPSEEK_API_KEY=a\nDEEPSEEK_API_KEY=b\n") == "a"

    def absent_file_is_not_an_error() -> bool:
        return read_key(repo=_empty()) == ""

    def bad_byte_after_the_key_fails_closed() -> bool:
        root, _ = _fixture(b"DEEPSEEK_API_KEY=secret\n\xd1\n")
        return raises(lambda: read_key(repo=root))

    def bad_byte_is_not_dropped() -> bool:
        root, _ = _fixture(b"DEEPSEEK_API_KEY=\xb1secret\n")
        return raises(lambda: read_key(repo=root))

    def utf8_file_with_a_non_ascii_comment_is_read() -> bool:
        root, _ = _fixture("# owner's key \u2014 do not commit\nDEEPSEEK_API_KEY=ok\n".encode("utf-8"))
        return read_key(repo=root) == "ok"

    return [
        ("the explicit flag wins and touches no file", flag_wins),
        ("the environment wins over the file (C22 opt-in order preserved)", env_beats_file),
        ("with no flag and no env, the file is used", file_used_when_no_flag_no_env),
        ("a quoted, padded line parses to the bare value", quoted_and_padded),
        ("a commented-out key is NOT a key", commented_out_is_not_a_key),
        ("a later duplicate does not override the first", first_duplicate_wins),
        ("an absent .env is not an error ('' leaves the caller's FATAL message in charge)", absent_file_is_not_an_error),
        ("a bad byte AFTER the key fails CLOSED (the file is decoded before it is parsed)", bad_byte_after_the_key_fails_closed),
        ("a bad byte is never DROPPED (errors='ignore' is gone)", bad_byte_is_not_dropped),
        ("a valid utf-8 .env with a non-ascii comment is still read", utf8_file_with_a_non_ascii_comment_is_read),
    ]


def main(argv: list[str]) -> int:
    """--selftest only. Any other argument is refused (C16: an ignored argument is a silent error)."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--selftest", action="store_true")
    args, unknown = ap.parse_known_args(argv)
    if unknown or not args.selftest:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): pass --selftest (unknown: " + str(unknown) + ")")
    rows = controls()
    for name, thunk in rows:
        print(("  ok  " if thunk() else "  !!  ") + name)
    failed = [n for n, t in rows if not t()]
    if failed:
        print("FAIL " + PREFIX + ": " + str(len(failed)) + " of " + str(len(rows)) + " control(s) did not fire")
        return 1
    print("ok " + PREFIX + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
