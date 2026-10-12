"""tests/test_handoff_rebaseline.py - D-2971 / BUG-376: a rewritten receipt region is RE-BASELINED, named.

WHY THIS FILE EXISTS
--------------------
MEASURED 2026-10-12. `scripts/verify_handoffs.py --check` refused the decisions registry:

    decisions_registry: config/decisions.yaml is declared append_only but its receipted bytes are not a
    prefix of the current bytes (rewritten): the first 979096 bytes hash to 7be564ac6b539269, not the
    receipted de3acd304b638fdd

Byte-exact bisect: commit `d149809` (2026-10-10) edited ONE `state:` cell at line 573 and inserted 52 lines
(D-2905/D-2907/D-2908) at line 15,585 - not an append - and commit `3db009e` (2026-10-12) re-serialised the
whole registry. The rail was right and had NO remedy that was not a quiet re-hash: `--backfill` re-cuts EVERY
declared path (moving baselines nobody measured as broken) and remembers nothing about the rewrite.

These controls pin the three things that make the new act (scripts/lib/handoff.py `--rebaseline`) a repair
rather than a laundry: it can only run where a rewrite was MEASURED, it must NAME the rewrite and its owner,
and the receipt it appends carries what it superseded - so the journal keeps the record the re-hash would
have deleted (D-382/BUG-535). They also pin the rule's ONE home, because the act and the rail must ask the
identical question or they drift apart (D-274a).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib import handoff  # noqa: E402

OLD = b"- id: D-1\n  state: PROPOSED\n"
#: A REAL rewrite for the fixture: the SAME length with one byte moved inside the receipted region. `OLD + b"x"`
#: would be an APPEND, and a fixture that cannot tell the two apart would let the positive control below pass
#: through the wrong door.
REWRITTEN = OLD.replace(b"PROPOSED", b"RESOLVED")
RECEIPT = {"bytes": len(OLD), "sha256": handoff.sha256_bytes(OLD), "mutability": "append_only"}


def _problems(cur: bytes, head: bytes | None, because: str = "D-2971", commits: list[str] | None = None,
              decisions: set[str] | None = None) -> list[str]:
    """The act's refusal list for one fixture: [] means the act would proceed."""
    return handoff.rebaseline_problems(RECEIPT, cur, head, because,
                                       ["d149809"] if commits is None else commits,
                                       {"D-2971"} if decisions is None else decisions)


def test_the_append_only_rule_has_ONE_home_shared_by_the_rail_and_the_act() -> None:
    """D-274a: the state rule is asked by the rail AND by the act, so it may exist exactly once."""
    assert callable(handoff.prefix_state), "the rule's home is scripts/lib/handoff.py (D-2971)"
    rail = (ROOT / "scripts" / "verify_handoffs.py").read_text(encoding="utf-8")
    assert "def prefix_state" not in rail, "the rail grew a SECOND implementation of the rule (D-274a)"
    assert rail.count("handoff.prefix_state(") >= 2, "the rail must MEASURE with the rule's one home"


def test_the_act_accepts_a_measured_rewrite_that_is_named_and_owned() -> None:
    """The positive: a gate that only ever refuses could not have repaired BUG-376 at all."""
    assert _problems(REWRITTEN, REWRITTEN) == []


def test_the_act_refuses_every_state_that_is_not_a_measured_rewrite() -> None:
    """A legal append needs no repair; a truncation is restored, never re-baselined (D-2642)."""
    assert _problems(OLD + b"- id: D-2\n", REWRITTEN), "a legal APPEND must be refused"
    assert _problems(OLD, REWRITTEN), "an UNCHANGED file must be refused"
    assert _problems(OLD[:-6], REWRITTEN), "a TRUNCATION must be refused"
    assert _problems(REWRITTEN, REWRITTEN, because=""), "a missing owner must be refused"
    assert _problems(REWRITTEN, REWRITTEN, because="D-9999"), "an owner that names no record must be refused"
    assert _problems(REWRITTEN, REWRITTEN, commits=[]), "an invisible rewrite must be refused"


def test_the_act_refuses_bytes_no_store_holds_at_the_revision() -> None:
    """BUG-559: a receipt over uncommitted (or foreign) bytes certifies a body no store can re-derive."""
    assert _problems(REWRITTEN, None), "bytes with no revision at git HEAD must be refused"
    assert _problems(REWRITTEN, OLD), "bytes that differ from git HEAD must be refused"


def test_the_act_refuses_a_path_with_no_prior_receipt() -> None:
    """A re-baseline SUPERSEDES a receipt: it cannot invent one, so there is nothing to name."""
    problems = handoff.rebaseline_problems(None, REWRITTEN, REWRITTEN, "D-2971", ["d149809"], {"D-2971"})
    assert problems and "no prior receipt" in problems[0]


def test_the_superseding_receipt_carries_what_it_replaced() -> None:
    """The anti-laundering clause: a re-baseline that hides its predecessor is the quiet re-hash (D-382)."""
    extra = handoff.rebaseline_extra("ab" * 32, 979096, "D-2971", ["d149809", "3db009e"], "git:98471a36")
    assert tuple(extra) == handoff.REBASELINE_META_FIELDS, "the published shape is DECLARED, not improvised"
    assert extra["supersedes_sha256"] == "ab" * 32 and extra["supersedes_bytes"] == 979096
    assert extra["rewrite_named"] == ["d149809", "3db009e"] and extra["because"] == "D-2971"
    assert extra["supersedes_bytes_at"] == "git:98471a36", "the superseded bytes name the store that holds them"
    assert handoff.rebaseline_extra("ab" * 32, 5, "D-1", [], "")["supersedes_bytes_at"] == "", \
        "no store: the limit is NAMED as an empty field, never hidden (D-403)"
    assert not (set(extra) & set(handoff.RECEIPT_MEASURED_KEYS)), \
        "the supersession may not shadow a field the receipt MEASURES"
    assert handoff.REBASELINE_ORIGIN not in handoff.RECEIPT_MEASURED_KEYS, \
        "the origin is the receipt's own to set - a caller must not be able to fake a re-baseline"


def test_a_receipt_may_not_be_told_what_it_measured_and_refuses_BEFORE_writing() -> None:
    """C16/BUG-491: the refusal is the FIRST statement, so nothing reaches the journal it calibrates."""
    journal = handoff.journal_path()
    before = handoff.sha256_file(journal) if journal.exists() else "absent"
    with pytest.raises(ValueError, match="measured field"):
        handoff.receipt("selftest", {"id": "selftest", "mutability": "immutable", "paths": []},
                        "config/handoffs.yaml", "selftest", extra={"sha256": "0" * 64, "bytes": 1})
    after = handoff.sha256_file(journal) if journal.exists() else "absent"
    assert after == before, "the refused receipt was written anyway - the guard fires too late"


def test_the_act_previews_by_default_and_refuses_an_unknown_owner() -> None:
    """Integration, read-only: the CLI must refuse an act attributed to a decision that does not exist."""
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "lib" / "handoff.py"), "--rebaseline",
                           "decisions_registry", "--because", "D-0000", "--commit", "d149809"],
                          capture_output=True, text=True, cwd=str(ROOT))
    assert proc.returncode != 0, "an unattributable act must not be runnable"
    assert "names no record" in (proc.stdout + proc.stderr), proc.stdout + proc.stderr


def test_the_superseded_bytes_name_the_EXACT_revision_when_one_exists() -> None:
    """MEASURED against this repo's own history: 98471a36 IS the superseded 979,096 B; b5ce8ae only RETAINS them.

    A newest-first search finds the weaker witness first, so the act scans the whole history and lets the EXACT
    revision win, marking a retained-prefix answer '#prefix'. Without this control the first applied receipt
    named `b5ce8ae` (true, but a prefix) while the exact revision is `98471a36` - both facts true, and a field
    that cannot say which one it is making is the ambiguity that makes a provenance rail useless.
    """
    old = [r for r in handoff.read_receipts()
           if r.get("path") == "config/decisions.yaml" and int(r.get("bytes") or 0) == 979096]
    assert old, "the superseded receipt must still be in the append-only journal"
    where = handoff.superseded_bytes_at(str(old[-1]["sha256"]), "config/decisions.yaml", int(old[-1]["bytes"]))
    assert where.startswith("git:98471a36"), where
    assert not where.endswith("#prefix"), "a newer revision that merely RETAINS the bytes must not win"
    assert handoff.superseded_bytes_at("0" * 64, "config/decisions.yaml", 979096) == "", \
        "no store re-derives it: the field is EMPTY, never a guess"


def test_the_cli_publishes_its_default_and_its_guards() -> None:
    """The default is a PREVIEW and the help says so: the only write is the receipt appended under --apply."""
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "lib" / "handoff.py"), "--help"],
                          capture_output=True, text=True, cwd=str(ROOT))
    assert "--rebaseline" in proc.stdout and "--because" in proc.stdout and "--apply" in proc.stdout
    assert "preview" in proc.stdout, "the default must be a preview, and the help must say so"
