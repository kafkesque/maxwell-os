#!/usr/bin/env python3
"""Re-derive the fields that DESCRIBE config/decisions.yaml - in the census, never in the registry.

BUG-402 (owner-approved 2026-09-23) established that total_decisions, the summary block, the content stamp
(decisions_sha256_16) and written_by are REDUNDANT DERIVED DATA: they MUST equal values computed from the
decisions list, which is the single source of truth. D-2655 (2026-09-26) then moved them OUT of
config/decisions.yaml, because that file declares mutability: append_only and its handoff receipt is a PREFIX
rule: the receipted bytes must remain a prefix of the bytes on disk. Every field above changes on every mint,
so NO position inside an append-only file is compatible with that rule - the mint's mid-file insert was the
SYMPTOM (BUG-539), not the disease.

WHERE THEY LIVE NOW. config/decisions_summary.json (the census), declared in config/artifact_ownership.yaml and
registered in config/derivations.yaml. It is a PURE FUNCTION of the registry bytes: it carries no generation
timestamp, so re-running this script on an unchanged registry is a byte-identical no-op (a volatile field in a
compared document makes every comparison a false witness). config/decisions.yaml is now RECORDS ONLY and its
records list extends to end-of-file, so:

    --mint <file|-> [--apply]       APPENDS validated record(s). The append is CHECKED (the new text must have
                                    the old text as a prefix), which is exactly what the append-only receipt
                                    demands; the census is rewritten in the same invocation. D-2660: the record's
                                    OWN FIELDS are joined to reality FIRST - the id is the next free one, its bugs
                                    exist in governance/bug_status.json, its payload NAMES its own bugs, every cited
                                    file EXISTS, and a whole-payload clone of a record on disk is REFUSED.
    --selftest                      run the MINT gate's known-answer controls (BUG-492); a control that has never
                                    been seen to fire is a comment. Wired into just health.
    --strip-derived-head --because <D-id> [--apply]
                                    the ONE-SHOT migration that removed the derived head and the summary block
                                    by BYTE SPLICE, so the record bytes were never re-rendered. D-2972: an
                                    in-place route moves bytes INSIDE a receipted region, so it REFUSES without
                                    the decision that orders the edit and prints the act that discharges it.

BUG-402 design note: a timestamp alone is a DECLARATION, not a control - a human can edit it and no tool can
verify it. The stamp is therefore CONTENT-derived: decisions_sha256_16 is the sha256 (16 hex chars) of the
canonical JSON of the decisions list, so it proves WHAT was written, not just WHEN. A WHEN belongs in an
append-only journal (the handoff receipts, the write journal), which cannot lie about the past because it is
never rewritten. --check fails on a missing or mismatched stamp, which is what lets just health catch drift
loudly instead of silently (D-355).

Modes:
    (default)   re-derive the census and repair ONLY it; a registry that is not records-only is a NAMED refusal
    --check     exit 1 if the registry shape or the census has drifted (no write) - wired into just health
    --mint      see above
    --strip-derived-head    see above (one-shot; already applied 2026-09-26)

IMPORTANT - this is NOT tools/sync_decisions.py. That tool treats DECISION-LOG.md as the source
of truth, which is INVERTED: DECISION-LOG.md has ~154 heading blocks vs 736 decision records here,
so running it would corrupt hand-curated records via its "No heading in DECISION-LOG.md" fallback
and heuristic state/category detection. It is now a hard-fail stub (BUG-402).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 - D-401/I1 (C6: crash-safe registry write)
from lib import yaml_guard  # noqa: E402 - D-2648: verify the bytes before writing them
from lib import handoff  # noqa: E402 - D-2971/D-2972: the decision ids, the act and the obligation text

#: The `--because <D-id>` licence an in-place route must name BEFORE it may move bytes inside a receipted region.
LICENCE_FLAG: str = "--because"
#: The route argument whose presence means "write" (preview is the default everywhere in this repo).
APPLY_FLAG: str = "--apply"

DECISIONS_YAML = ROOT / "config" / "decisions.yaml"
#: The writer name declared in config/artifact_ownership.yaml - DERIVED, never typed twice.
WRITER = Path(__file__).resolve().relative_to(ROOT).as_posix()

# Canonical state keys (lowercased in the summary block), in stable order so the
# summary renders consistently and future diffs are minimal.
STATES: list[str] = [
    "PROPOSED",
    "DRAFT",
    "ACTIVE",
    "STALE",
    "SUPERSEDED",
    "ARCHIVED",
    "REJECTED",
    "DEFERRED",
    "RESOLVED",
    "OPEN",   # in use by 17 record(s) but UNDECLARED until 2026-09-25 (BUG-483)
    "RATIFIED",   # in use by 15 record(s) but UNDECLARED until 2026-09-25 (BUG-483)
    "PLANNED",
    # D-2645 (2026-09-25): the WHOLESALE states of the revocation ontology. A whole-record withdrawal is a
    # STATE (counted here); revoking ONE SCOPE of a live decision is a SUB-FACT on the record, never a state -
    # D2205's roadmap stays ACTIVE while ONE of its migrations is revoked. Declared here because
    # config/decisions_policy.yaml#revocation.whole_record_states names them, and two declarations of one fact
    # is the defect D-2646 forbids: vocabulary_problems() joins the two and fails on a mismatch.
    "REVOKED",
    "ABANDONED",
]

WRITTEN_BY: str = "scripts/recompute_decision_summary.py"
STAMP_KEYS: tuple[str, ...] = ("decisions_sha256_16", "written_by")
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"

#: D-2655: the census LEAVES the append-only registry and lives here (config/*.json is inside may_touch;
#: governance/*.json is NOT - a plan may not be widened so an assistant may write it, BUG-528/BUG-445).
CENSUS_JSON = ROOT / "config" / "decisions_summary.json"
CENSUS_SCHEMA_VERSION: str = "1.0"
#: Every key a reader MUST be able to find: an absent one is an error, never a default (D-2644/BUG-487).
CENSUS_REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "source_path",
    "source_sha256",
    "written_by",
    "decisions_sha256_16",
    "total_decisions",
    "summary",
)


def normalized_id(record: dict) -> str:
    """Return the record's id with the dash spelling collapsed: `D-331` and `D331` are ONE token (C21)."""
    return str(record.get("id") or "").strip().replace("D-", "D").upper()


def canonical_state(record: dict) -> str:
    """Return the record's canonical state, or FAIL CLOSED (BUG-483).

    The previous `or "ACTIVE"` default silently re-labelled 62 of 766 records - 59 carried their state
    under a legacy `status:` key and 3 carried none - so the census block was wrong while the rail
    reported "in sync". A defaulted ruler is not a ruler (D-404); an uncounted record is not a record.
    """
    raw = record.get("state")
    if raw is None or not str(raw).strip():
        legacy = sorted(set(record) & {"status", "decision_state"})
        raise SystemExit(
            f"FAIL-CLOSED (BUG-483): decision {record.get('id')!r} carries no canonical 'state:' key "
            f"(legacy keys present: {legacy or 'none'}) - it would be silently counted as ACTIVE. "
            f"Normalise the record; do not re-introduce a default."
        )
    state = str(raw).strip().upper()
    if state not in STATES:
        raise SystemExit(
            f"FAIL-CLOSED (BUG-483): decision {record.get('id')!r} state {raw!r} is not canonical; "
            f"one of {STATES}"
        )
    return state


POLICY_YAML = ROOT / "config" / "decisions_policy.yaml"


def vocabulary_problems() -> list[str]:
    """Join the canonical STATE vocabulary to the revocation ontology's DECLARED states (D-2646).

    A rule about which whole-record states exist has exactly ONE implementation. If the policy declares a state
    this vocabulary cannot count, a record carrying it would be counted as nothing while the rail printed
    "in sync" - the BUG-483 shape (a defaulted ruler is not a ruler). So the join fails LOUDLY in both
    directions, and an ABSENT rules file is the error rather than a default (D-2644).
    """
    if not POLICY_YAML.exists():
        return [POLICY_YAML.relative_to(ROOT).as_posix() + ": absent - the revocation ontology's RULES file is "
                "missing, so the state vocabulary cannot be joined to anything (D-2645)"]
    policy = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    revocation = policy.get("revocation") or {}
    if "whole_record_states" not in revocation:
        return [POLICY_YAML.relative_to(ROOT).as_posix() + "#revocation.whole_record_states: not declared - the "
                "set of whole-record states must be declared where a reader can FAIL on it (D-2644)"]
    problems: list[str] = []
    for state in [str(v).strip().upper() for v in (revocation.get("whole_record_states") or [])]:
        if state not in STATES:
            problems.append(
                POLICY_YAML.relative_to(ROOT).as_posix() + " declares whole-record state " + repr(state)
                + " that the canonical vocabulary does not carry - add it to STATES or drop the rule "
                "(two declarations of one fact is the defect, D-2646)"
            )
    return problems


def control_slug(name: str) -> str:
    """The control's name as a marker a mutation can be SEEN to red through (D-2676 iv)."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def legacy_spelling_ids() -> list[str] | None:
    """The identity-pinned legacy state spellings, read from the RULES file; None when the block is absent."""
    if not POLICY_YAML.exists():
        return None
    policy = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    ids = (policy.get("state_vocabulary") or {}).get("legacy_non_canonical_ids")
    return None if ids is None else [normalized_id({"id": v}) for v in ids]


def spelling_problems(decisions: list, pinned: list[str] | None = None) -> list[str]:
    """BUG-583: a state is ONE value with ONE spelling, and a second spelling is a fault a reader can FAIL on.

    canonical_state() upper-cases, so the census was right while the BYTES carried two forms of one state - the
    BUG-572 family one level down. Rules live in config/decisions_policy.yaml#state_vocabulary (ONE home, C12);
    the spellings already on disk are pinned BY IDENTITY and the pin is SHRINK-ONLY: a pinned id that is
    canonical now is a STALE declaration (D-405), which is the other direction of the same join.
    """
    if pinned is None:
        pinned = legacy_spelling_ids()
        if pinned is None:
            return [POLICY_YAML.relative_to(ROOT).as_posix() + "#state_vocabulary.legacy_non_canonical_ids: not "
                    "declared - the rule that a state has ONE spelling must live where a reader can FAIL on it "
                    "(D-2644/BUG-583)"]
    pin = set(pinned)
    problems: list[str] = []
    for record in decisions:
        raw = str(record.get("state") or "").strip()
        if not raw:
            continue  # canonical_state() refuses a record with no state at all (BUG-483)
        if raw == canonical_state(record):
            if normalized_id(record) in pin:
                problems.append(normalized_id(record) + ": pinned as a legacy non-canonical spelling, but the "
                                "record is canonical now - a pin that describes nothing is a STALE declaration "
                                "(D-405/BUG-583)")
            continue
        if normalized_id(record) not in pin:
            problems.append(normalized_id(record) + ": state " + repr(raw) + " is a SECOND spelling of "
                            + repr(canonical_state(record)) + " - canonicalise it, or pin the id BY IDENTITY in "
                            "config/decisions_policy.yaml#state_vocabulary.legacy_non_canonical_ids (BUG-583)")
    return problems


CANONICALISE_FLAG: str = "--canonicalise-states"
#: The route a STATE TRANSITION takes (D-3035/M2, 2026-10-16). A state is a governed value inside a receipted
#: region, so changing one is an in-place edit like any other: it needs the decision that ORDERS it (--because),
#: it splices exactly ONE cell, and it prints the act and the obligation it leaves. Declared in
#: config/decisions_policy.yaml#state_vocabulary.transition_route, read by this module, never remembered (C12).
SET_STATE_FLAG: str = "--set-state"
#: The SUPERSESSION LINK, and the reason it is a FLAG on the transition rather than a second act (BUG-1099/D-3216):
#: MEASURED 2026-10-28 that `--set-state <D> SUPERSEDED` spliced the state ALONE while reconcile demanded a
#: RESOLVABLE `superseded_by` and the only escape - the pin list - may only SHRINK (D-2645). The two obligations
#: were jointly unsatisfiable for any record retired after the 2026-09-27 pin measurement, and an append_only
#: registry cannot be repaired by a later act. So the link moves in the SAME governed write as the state.
SUPERSEDOR_FLAG: str = "--superseded-by"
ID_LINE_RE = re.compile(r"^- id: (D-?\d+[a-z]?)$")


def legacy_spelling_route() -> str | None:
    """The DECLARED home of the in-place route, read from the RULES file; None when it is not declared (C12).

    An in-place edit of an append_only artifact is a RULE, not a capability: it lives where a reader can FAIL on
    it, so a writer cannot grant itself the exception by being willing to take it (D-2655/BUG-583).
    """
    if not POLICY_YAML.exists():
        return None
    policy = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    route = (policy.get("state_vocabulary") or {}).get("canonicalisation_route")
    return None if route is None else str(route)


def state_cell_problems(decisions: list, targets: list[str]) -> list[str]:
    """Every reason a set of PINNED ids may NOT be canonicalised - asked of the record BEFORE a byte moves.

    The pin in config/decisions_policy.yaml#state_vocabulary is a DEBT declaration and SHRINK-ONLY: a target that
    no longer exists, or that is canonical already, must RED rather than be silently satisfied - a pin that can
    never be paid down is a permanent exemption wearing a debt's clothes (D-405/BUG-583).
    """
    problems: list[str] = []
    want = [str(t) for t in targets]
    if len(set(want)) != len(want):
        problems.append("the pin names an id twice: " + str(sorted(want)))
    index = {normalized_id(r): r for r in decisions if isinstance(r, dict)}
    for target in want:
        record = index.get(target)
        if record is None:
            problems.append(target + ": pinned as a legacy spelling, but no record carries that id - a pin that "
                            "names nothing cannot be canonicalised (D-405/BUG-583)")
            continue
        if str(record.get("state") or "").strip() == canonical_state(record):
            problems.append(target + ": is canonical ALREADY - the pin describes nothing now, so shrink the pin "
                            "rather than rewriting a canonical cell (D-405/BUG-583)")
    return problems


def splice_problems(pre_decls: list, post_decls: list, targets: list[str]) -> list[str]:
    """Prove a canonicalising splice touched the PINNED state cells and NOTHING else.

    WHY THIS FUNCTION IS THE WHOLE LICENCE. config/decisions.yaml is append_only with a PREFIX receipt and no
    writer may rewrite a key in place (D-2655). An in-place route therefore has to EARN the exception instead of
    being granted one, and it earns it by proving three things about the WOULD-BE bytes BEFORE the write: the id
    set is unmoved (a canonicalisation may touch a state, never a record); no cell moved that the pin did not name
    (a route that can move an unpinned cell is a licence to rewrite the registry); and the registry is canonical
    EVERYWHERE afterwards, which is what lets the pin shrink to empty and the reader's rule become universal.
    """
    problems: list[str] = []
    pin = {str(t) for t in targets}
    pre = {normalized_id(r): r for r in pre_decls if isinstance(r, dict)}
    post = {normalized_id(r): r for r in post_decls if isinstance(r, dict)}
    if set(pre) != set(post):
        return ["the splice moved the registry's ID SET (" + str(sorted(set(pre) ^ set(post))) + ") - a "
                "canonicalisation may touch a state, never a record (C21/BUG-583)"]
    moved = sorted(i for i in post if str(pre[i].get("state")) != str(post[i].get("state")))
    extra = [i for i in moved if i not in pin]
    if extra:
        problems.append("the splice moved the state of " + str(extra) + ", which the pin never named - an in-place "
                        "route that can move a cell nobody pinned is a licence to rewrite an append_only registry "
                        "(D-2655/BUG-583)")
    unpinned = [i for i in sorted(post) if str(post[i].get("state") or "").strip() != canonical_state(post[i])]
    if unpinned:
        problems.append("the would-be registry still spells " + str(unpinned) + " non-canonically, so the pin "
                        "could NOT shrink after this write - the only reason this route exists would not be met "
                        "(BUG-583)")
    for i in sorted(post):
        rest_pre = {k: v for k, v in pre[i].items() if k != "state"}
        rest_post = {k: v for k, v in post[i].items() if k != "state"}
        if rest_pre != rest_post:
            problems.append(i + ": the splice moved a key OTHER than `state:` - a canonicalisation edits ONE "
                            "governed value, never a record (D-2655/BUG-583)")
    return problems


def canonicalise_plan(text: str, targets: list[str]) -> tuple[str, list[str]]:
    """Return (would-be registry text, problems): the PINNED `state:` cells replaced by BYTE SPLICE.

    WHY A SPLICE AND NOT A RE-RENDER (the D-2655 HALF B lesson). Re-emitting the registry through the YAML
    emitter would produce a document that merely happens to parse: every line of 9,800 would be a new byte, the
    diff would be unreadable, and any hand-authored formatting or ordering would be lost. The splice rewrites the
    `state:` LINE of a pinned record and nothing else, so THE DIFF IS THE PROOF - which is exactly what a writer
    touching a cell of an append_only artifact has to show before it may write.
    """
    data = yaml.safe_load(text) or {}
    decisions = [r for r in (data.get("decisions") or []) if isinstance(r, dict)]
    problems = state_cell_problems(decisions, targets)
    if problems:
        return text, problems
    pin = {str(t) for t in targets}
    index = {normalized_id(r): r for r in decisions}
    lines = text.split(chr(10))
    starts = [i for i, ln in enumerate(lines) if ln.startswith("- id: ")]
    blocks: dict[str, tuple[int, int]] = {}
    for at, start in enumerate(starts):
        end = starts[at + 1] if at + 1 < len(starts) else len(lines)
        match = ID_LINE_RE.match(lines[start])
        if match:
            blocks[normalized_id({"id": match.group(1)})] = (start, end)
    missing = sorted(pin - set(blocks))
    if missing:
        problems.append(str(missing) + ": pinned id(s) whose bare `- id:` record block this route cannot locate - "
                        "refusing rather than rewriting a cell by guesswork (C16/BUG-583)")
        return text, problems
    moves: list[tuple[int, str]] = []
    for target in sorted(pin):
        start, end = blocks[target]
        cells = [i for i in range(start, end) if lines[i].startswith("  state: ")]
        if len(cells) != 1:
            problems.append(target + ": carries " + str(len(cells)) + " `  state: ` cell(s) at record indent - the "
                            "route replaces exactly one cell per pinned record (C16/BUG-583)")
            continue
        cell = cells[0]
        try:
            raw = yaml.safe_load(lines[cell][len("  state: "):].strip())
        except yaml.YAMLError as exc:
            problems.append(target + ": the `state:` cell does not parse (" + type(exc).__name__ + ") - a cell "
                            "this route cannot read is not a cell it may rewrite (C16)")
            continue
        if str(raw) != str(index[target].get("state")):
            problems.append(target + ": the `state:` line parses to " + repr(raw) + " but the record's state is "
                            + repr(index[target].get("state")) + " - refusing to rewrite a cell that does not "
                            "match the record (C16/BUG-583)")
            continue
        moves.append((cell, "  state: " + canonical_state(index[target])))
    if problems:
        return text, problems
    out = list(lines)
    for cell, new_line in moves:
        out[cell] = new_line
    touched = sum(1 for a, b in zip(lines, out) if a != b)
    if len(out) != len(lines) or touched != len(moves):
        return text, ["the splice moved " + str(touched) + " line(s), not the " + str(len(moves)) + " pinned "
                      "cell(s) - an edit that changes a line it did not declare is not a canonicalisation (C16)"]
    new_text = chr(10).join(out)
    post = [r for r in ((yaml.safe_load(new_text) or {}).get("decisions") or []) if isinstance(r, dict)]
    return new_text, splice_problems(decisions, post, targets)


def in_place_licence(argv: list[str], flag: str) -> tuple[str, bool]:
    """Read and VALIDATE `FLAG --because <D-id> [--apply]` for an in-place route; return (because, apply).

    WHY A LICENCE AT THE DOOR (D-2972, the class D-2971 left OWED). An in-place edit of an append_only artifact
    moves bytes INSIDE a receipted region, so it leaves a receipt obligation behind - and MEASURED 2026-10-12 that
    obligation was discharged in PROSE ("NEXT (same sitting): re-baseline the receipt"), which is a favour, not a
    rule (C12/D-2655), so nobody paid it and the rail stayed RED for five days (BUG-376). The ordering is
    structural: the edit must be COMMITTED before the receipt can be re-cut over it (a receipt over a dirty
    worktree is UNREVISIONED, BUG-559), so no route can discharge the obligation itself. What a route CAN do is
    refuse to be ANONYMOUS: it will not move a receipted region unless the decision that orders the edit is named,
    and that name is what the printed act command carries. The refusal comes FIRST - before the no-op branches -
    so "there is nothing to do" can never be the door a licence is walked past.
    """
    args = list(argv[1:])
    if not args or args[0] != flag:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: " + flag + " " + LICENCE_FLAG + " <D-id> ["
                         + APPLY_FLAG + "]")
    because = ""
    apply_now = False
    tokens = args[1:]
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == APPLY_FLAG and not apply_now:
            apply_now = True
        elif tok == LICENCE_FLAG and not because and i + 1 < len(tokens):
            because = tokens[i + 1]
            i += 1
        else:
            raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: " + flag + " " + LICENCE_FLAG + " <D-id> ["
                             + APPLY_FLAG + "] - got " + repr(tok))
        i += 1
    if not because:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + flag + " requires " + LICENCE_FLAG + " <D-id>: it "
                         "moves bytes INSIDE the receipted region of an append_only artifact, and an act with no "
                         "owner is a favour (C12/D-2655/D-2972)")
    if because not in handoff.decision_ids():
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + LICENCE_FLAG + " " + because + " names no record in "
                         + DECISIONS_YAML.relative_to(ROOT).as_posix() + " - the edit would be attributable to a "
                           "decision that does not exist")
    return because, apply_now


def print_obligation(because: str) -> None:
    """State the obligation a completed in-place edit leaves - from the receipt module's ONE home (D-2972).

    It prints TWO facts and no prose of its own: WHO the mutation journal says moved these bytes (joined by
    CONTENT, so an unrecorded write says UNATTRIBUTED instead of blaming the newest record), and the act the next
    reader owes, carrying the licence this run was given.
    """
    artifact = handoff.artifact_of(DECISIONS_YAML.relative_to(ROOT).as_posix())
    print("     " + handoff.attribution_line(DECISIONS_YAML.relative_to(ROOT).as_posix()))
    print("     " + handoff.rebaseline_next_steps(artifact, because))


def canonicalise_main(argv: list[str]) -> int:
    """`--canonicalise-states --because <D-id> [--apply]`: pay the spelling debt down by an in-place splice (BUG-583).

    THE DECLARED SEQUENCE (three obligations, all LOUD): the splice; then the pin shrinks to empty in the SAME
    sitting, because a pin over a canonical cell is a STALE declaration the spelling reader FAILS on; then the
    decisions_registry receipt is RE-CUT, because the splice moved bytes inside the receipted region by
    construction. D-2972 makes the first obligation refused (no `--because`, no edit), the second printed, and the
    third found by a HARD rail whose finding names the act - never by silence, and never in the receipt's own home.
    """
    because, apply_now = in_place_licence(argv, CANONICALISE_FLAG)
    route = legacy_spelling_route()
    if route is None or WRITER not in route:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): "
                         + POLICY_YAML.relative_to(ROOT).as_posix()
                         + "#state_vocabulary.canonicalisation_route is " + repr(route) + ", which does not name "
                         + WRITER + " - an in-place edit of an append_only artifact is a RULE, and a rule with no "
                         "home is a favour (C12/D-2655/BUG-583)")
    targets = legacy_spelling_ids() or []
    if not targets:
        print("ALREADY CANONICALISED - nothing to do: the pin is empty and every state on disk spells the "
              "canonical form (BUG-583)")
        return 0
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    new_text, problems = canonicalise_plan(text, targets)
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): refusing to canonicalise: " + "; ".join(map(str, problems)))
    pre_data = yaml.safe_load(text) or {}
    post_data = yaml.safe_load(new_text) or {}
    pre_total, _pre_summary, pre_stamp = recompute(pre_data)
    post_total, _post_summary, post_stamp = recompute(post_data)
    if post_total != pre_total:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the splice moved the RECORD COUNT (" + str(pre_total)
                         + "->" + str(post_total) + ") - refusing")
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    # The postcondition is asked with the pin EMPTIED (pinned=[]), never with the live pin: the whole point of a
    # canonicalisation is that the pin SHRINKS to nothing, so asking the live pin would make this route refuse by
    # construction - MEASURED on the first run, which is how this clause came to read the pin it will leave
    # behind rather than the one it found (a check that cannot distinguish its two reasons proves neither).
    post_records = [r for r in (post_data.get("decisions") or []) if isinstance(r, dict)]
    shape = ["derived key " + repr(k) + " came back into the append_only registry (D-2655)"
             for k in REGISTRY_DERIVED_KEYS if k in post_data]
    shape += record_problems(post_records) + spelling_problems(post_records, pinned=[]) + vocabulary_problems()
    if shape:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the spliced registry does not re-derive cleanly: "
                         + "; ".join(map(str, shape)))
    print("PRE  " + str(len(text.encode("utf-8"))) + " B sha256 " + hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("SPLICE " + str(len(targets)) + " pinned `state:` cell(s): " + ", ".join(targets))
    print("POST " + str(len(new_text.encode("utf-8"))) + " B sha256 "
          + hashlib.sha256(new_text.encode("utf-8")).hexdigest() + " - stamp " + pre_stamp + " -> " + post_stamp
          + " (it MOVES: a state is part of the content stamp, unlike the strip's unmoved stamp)")
    if "--apply" not in argv and not apply_now:
        print("PREVIEW (nothing written): re-run with " + APPLY_FLAG)
        return 0
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    disk = DECISIONS_YAML.read_text(encoding="utf-8")
    disk_data = yaml.safe_load(disk) or {}
    d_total, d_summary, d_digest = recompute(disk_data)
    write_census(census_document(disk_data, d_total, d_summary, d_digest, disk))
    print("ok " + str(d_total) + " record(s), stamp " + d_digest + ", census re-derived from the bytes ON DISK")
    print("OWED (SAME sitting, the readers are LOUD otherwise): (1) shrink "
          + POLICY_YAML.relative_to(ROOT).as_posix() + "#state_vocabulary.legacy_non_canonical_ids to []")
    print_obligation(because)
    return 0


def policy_states(kind: str) -> list:
    """The states config/decisions_policy.yaml DECLARES - read from its ONE home, never re-typed here (C12).

    kind='graph' answers what a reader may REST on (in_force_states + not_in_force_states, D-2682); anything else
    answers what the revocation ontology recognises as a whole-record withdrawal (D-2645). One home, one reader.
    """
    doc = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    if kind == "graph":
        graph = doc.get("graph") or {}
        return list(graph.get("in_force_states") or []) + list(graph.get("not_in_force_states") or [])
    return list((doc.get("revocation") or {}).get("whole_record_states") or [])


def graph_rules() -> dict:
    """config/decisions_policy.yaml#graph - the ONE home of the supersession vocabulary (C12/D-2642).

    Read, never re-typed: this module already refuses to hold a second copy of a STATE vocabulary (policy_states),
    and BUG-1099 is what a writer and a reader holding two halves of one fact on their own terms costs - the writer
    moved a state, the reader demanded a link, and nothing joined the two.
    """
    return dict((yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}).get("graph") or {})


def successor_field() -> str:
    """The field a retirement names its replacement in, read from the policy (D-2642/D-3216)."""
    return str(graph_rules().get("successor_field") or "superseded_by")


def supersession_state() -> str:
    """The state word whose transitions MUST carry a successor, read from the policy (BUG-1099/D-3216)."""
    return str(graph_rules().get("supersession_state") or "SUPERSEDED").strip().upper()


def successor_problems(decisions: list, target: str, state: str, successor: str) -> list:
    """Every reason a supersession LINK may not be written - asked BEFORE the state cell moves (D-3216/BUG-1099).

    Five clauses, each one a way a retirement can lie: the state that carries a link must carry one (a SUPERSEDED
    record naming no successor IS BUG-1099, and no later act can supply it); no other state may carry a link (a
    field no reader consults is a declaration with no referent, D-3034); the successor must EXIST (a link to
    nothing answers "what replaced it" with silence); it must not be the record itself (a self-link is a chain that
    goes nowhere); and it must not silently REPLACE a link already written (one supersession, one successor - a
    second link makes the first false without saying so).
    """
    index = {normalized_id(r): r for r in decisions if isinstance(r, dict)}
    key = normalized_id({"id": target})
    record = index.get(key) or {}
    field = successor_field()
    want = str(state).strip().upper()
    link = str(successor or "").strip()
    if want == supersession_state():
        if not link:
            return [target + ": a transition to " + want + " must CARRY its successor (" + SUPERSEDOR_FLAG
                    + " <D-id>) - a retirement that names no replacement is the BUG-1099 defect, and an "
                    "append_only registry has no later act that could supply one (D-3216)"]
    elif link:
        return [SUPERSEDOR_FLAG + " is the SUPERSESSION link and " + target + " moves to " + want + ", a state "
                "that reads no successor - a link no state consults is a declaration with no referent (D-3034)"]
    else:
        return []
    successor_key = normalized_id({"id": link})
    if successor_key not in index:
        return [target + ": the successor " + link + " names no record in this registry - a link that resolves to "
                "nothing answers 'what replaced it' with silence (D-3034/D-3216)"]
    if successor_key == key:
        return [target + ": the successor is the record itself - a supersession pointing at its own subject is a "
                "chain that goes nowhere (D-3216)"]
    current = str(record.get(field) or "").strip()
    if current and normalized_id({"id": current}) != successor_key:
        return [target + ": already carries " + field + " " + current + " and this transition would write "
                + str(index[successor_key].get("id")) + " - one supersession, one successor; a second link makes "
                "the first false without saying so (D-3216)"]
    return []


def link_only_repair(record: dict, state: str, successor: str) -> bool:
    """True when a transition moves NO state word but writes the MISSING successor (D-3216 legacy discharge).

    MEASURED 2026-10-28 while building this route: D-3170 and D-3171 already READ the supersession state, so the
    "a transition that moves nothing is a stale declaration (D-405)" clause would refuse the only two records this
    fix exists to repair - the defect would be prevented for the future and left unrepairable in the past. It is
    NOT a transition that moves nothing: the LINK is what moves, and it is the cell the reader was missing.
    """
    want = str(state).strip().upper()
    if want != supersession_state() or not str(successor or "").strip():
        return False
    return (str(record.get("state") or "").strip().upper() == want
            and not str(record.get(successor_field()) or "").strip())


def state_target_problems(decisions: list, target: str, state: str, successor: str = "") -> list:
    """Every reason a requested STATE TRANSITION may not be made - asked of the RECORD before a byte moves.

    Four clauses, each one a defect this registry has carried: the record must exist (a transition of nothing is
    a sentence); the requested state must be in the canonical vocabulary (an undeclared state word is the BUG-483
    defect); the state must actually CHANGE - unless the one cell being written is the missing successor link
    (D-3216, link_only_repair) - (a transition that moves nothing is a stale declaration, D-405); and the new value
    must be a state some reader CLASSIFIES, so it cannot enter the register silently (D-2645).
    """
    problems: list = []
    index = {normalized_id(r): r for r in decisions if isinstance(r, dict)}
    record = index.get(normalized_id({"id": target}))
    if record is None:
        return [target + ": no record carries that id - a transition of nothing cannot be ordered (D-405)"]
    want = str(state).strip().upper()
    if want not in STATES:
        return [want + " is not in the declared state vocabulary - an undeclared state word would be counted "
                       "while saying nothing (BUG-483/C12)"]
    now = str(record.get("state") or "").strip()
    if now == want and not link_only_repair(record, want, successor):
        problems.append(target + ": already reads " + want + " - a transition that moves nothing is a stale "
                        "declaration, and a stale declaration is a fault (D-405)")
    classified = policy_states("graph") + policy_states("whole")
    if classified and want not in classified:
        problems.append(want + " is classified by neither graph.in_force_states nor not_in_force_states in "
                        + POLICY_YAML.relative_to(ROOT).as_posix() + " - a state no reader classifies cannot "
                        "enter the register silently (D-2645/BUG-483)")
    return problems


def licence_names_target(because: str, target: str) -> bool:
    """True when the ORDERING decision's own payload NAMES the record it moves.

    WHY (D-2972 generalised): a licence proves an act is ATTRIBUTABLE; it does not prove the act is the one the
    decision ordered. A licence naming no target would let one order cover any record, so the ordering record
    must SPEAK the id it orders - the discipline the mint gate already applies to a decision and its bugs.
    """
    decisions = [r for r in ((yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {})
                             .get("decisions") or []) if isinstance(r, dict)]
    index = {normalized_id(r): r for r in decisions}
    record = index.get(normalized_id({"id": because}))
    return bool(record) and target in payload_text(record)


def set_state_plan(text: str, target: str, state: str, successor: str = "") -> tuple:
    """Return (would-be registry text, problems): ONE transition, its DECLARED cells, replaced by BYTE SPLICE.

    THE DIFF IS THE PROOF, the same reasoning as the canonicalisation route: re-emitting the registry would make
    every line a new byte, while the only write an append_only artifact tolerates is one whose touched cells can
    be COUNTED. A transition now moves TWO cells of ONE record when it carries a successor (D-3216/BUG-1099) and
    one when it does not, so this plan proves the same facts as before, plus one: exactly ONE line is REPLACED and
    at most ONE line is INSERTED; the registry ID SET did not move; NO other record changed by any key; NO key of
    the target moved outside the declared cells ({state} or {state, <successor field>}); and the record PARSES BACK
    carrying the successor it was given, and a SUPERSEDED record always reads one. A cell this route cannot read
    is still a cell it refuses to rewrite (C16).
    """
    data = yaml.safe_load(text) or {}
    decisions = [r for r in (data.get("decisions") or []) if isinstance(r, dict)]
    want = str(state).strip().upper()
    problems = state_target_problems(decisions, target, want, successor)
    if problems:
        return text, problems
    problems = successor_problems(decisions, target, want, successor)
    if problems:
        return text, problems
    field = successor_field()
    key = normalized_id({"id": target})
    index = {normalized_id(r): r for r in decisions}
    link = str(successor or "").strip()
    link_key = normalized_id({"id": link}) if link else ""
    link_id = str(index[link_key].get("id")).strip() if link_key in index else ""
    #: A record that ALREADY carries the very successor it is being given must not be handed a second copy of it:
    #: the state cell still moves, the link does not (C21 - one fact, one place, however often the act is replayed).
    insert = bool(link_key) and normalized_id({"id": str(index[key].get(field) or "")}) != link_key
    lines = text.split(chr(10))
    starts = [i for i, ln in enumerate(lines) if ln.startswith("- id: ")]
    block = None
    for at, start in enumerate(starts):
        end = starts[at + 1] if at + 1 < len(starts) else len(lines)
        match = ID_LINE_RE.match(lines[start])
        if match and normalized_id({"id": match.group(1)}) == key:
            block = (start, end)
            break
    if block is None:
        return text, [target + ": whose bare record block this route cannot locate - refusing rather than "
                               "rewriting a cell by guesswork (C16)"]
    cells = [i for i in range(block[0], block[1]) if lines[i].startswith("  state: ")]
    if len(cells) != 1:
        return text, [target + ": carries " + str(len(cells)) + " state cell(s) at record indent - this route "
                       "replaces exactly one cell (C16)"]
    cell = cells[0]
    try:
        raw = yaml.safe_load(lines[cell][len("  state: "):].strip())
    except yaml.YAMLError as exc:
        return text, [target + ": the state cell does not parse (" + type(exc).__name__ + ") (C16)"]
    if str(raw) != str(index[key].get("state")):
        return text, [target + ": the state line parses to " + repr(raw) + " but the record reads "
                      + repr(index[key].get("state")) + " - refusing to rewrite a cell that does not match the "
                      "record (C16)"]
    if insert:
        # ONE line REPLACED, ONE line INSERTED, and the two untouched regions compared as REGIONS rather than by a
        # zip that a shift would silently re-align (which is how a moved line hides from a diff). The state cell is
        # rewritten in every case and must CHANGE exactly when the transition declared a state change - so the
        # LINK-ONLY repair (an already-SUPERSEDED record given its missing successor, D-3216) is distinguishable
        # from a splice that quietly failed to move the state.
        out = lines[:cell] + ["  state: " + want, "  " + field + ": " + link_id] + lines[cell + 1:]
        state_changed = out[cell] != lines[cell]
        if (len(out) != len(lines) + 1 or out[:cell] != lines[:cell] or out[cell + 2:] != lines[cell + 1:]
                or state_changed != (str(raw).strip().upper() != want)):
            return text, ["the splice did not move exactly one REPLACED cell and one INSERTED link line, in the "
                          "one record it declared - an edit that changes a line it did not declare is not a "
                          "transition (C16)"]
    else:
        out = list(lines)
        out[cell] = "  state: " + want
        touched = sum(1 for a, b in zip(lines, out) if a != b)
        if len(out) != len(lines) or touched != 1:
            return text, ["the splice moved " + str(touched) + " line(s), not the ONE named cell - an edit that "
                          "changes a line it did not declare is not a transition (C16)"]
    new_text = chr(10).join(out)
    post = [r for r in ((yaml.safe_load(new_text) or {}).get("decisions") or []) if isinstance(r, dict)]
    pre_index = {normalized_id(r): r for r in decisions}
    post_index = {normalized_id(r): r for r in post}
    if set(pre_index) != set(post_index):
        return text, ["the splice moved the registry ID SET - a transition may touch a state, never a record (C21)"]
    declared_cells = {"state", field} if insert else {"state"}
    for ident in sorted(post_index):
        if ident == key:
            before = {k: v for k, v in pre_index[ident].items() if k not in declared_cells}
            after = {k: v for k, v in post_index[ident].items() if k not in declared_cells}
            moved = ("the splice moved a key OTHER than the declared cells " + str(sorted(declared_cells))
                     + " - a transition edits its own governed values and nothing else (D-2655/D-3216)")
        else:
            before, after = pre_index[ident], post_index[ident]
            moved = ("the splice moved a key of a record it did NOT declare - a transition edits one record "
                     "(D-2655)")
        if before != after:
            return text, [ident + ": " + moved]
    if str(post_index[key].get("state")) != want:
        return text, [target + ": the splice did not produce " + want + " - a route that cannot reach its own "
                               "declared postcondition is not a route (C16)"]
    if want == supersession_state() and not str(post_index[key].get(field) or "").strip():
        return text, [target + ": the splice produced " + want + " with no " + field + " - the exact defect this "
                               "route exists to make impossible (BUG-1099/D-3216)"]
    if insert and normalized_id({"id": str(post_index[key].get(field) or "")}) != link_key:
        return text, [target + ": the record does not read back the successor this plan was given (" + link_id
                      + ") - a write that cannot be read back is not a write (C16)"]
    return new_text, []


def _take_successor(rest: list) -> tuple:
    """Peel the supersession LINK out of a `--set-state` argument tail (BUG-1099/D-3216).

    The link is taken out BEFORE the licence is read, because that route refuses every token it does not declare -
    so a link left in the tail would be refused as a typo rather than read as a supersession. Arity and repetition
    are refused HERE, so a half-written link can never reach the splice that would write it.
    """
    extra = list(rest)
    if SUPERSEDOR_FLAG not in extra:
        return "", extra
    at = extra.index(SUPERSEDOR_FLAG)
    if at + 1 >= len(extra) or str(extra[at + 1]).startswith("--"):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + SUPERSEDOR_FLAG + " needs a <D-id> - a link with no "
                         "referent is the BUG-1099 defect wearing a flag (D-3216)")
    link = str(extra[at + 1])
    del extra[at:at + 2]
    if SUPERSEDOR_FLAG in extra:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + SUPERSEDOR_FLAG + " given twice - one supersession, one "
                         "successor, and a second link would make the first false without saying so (D-3216)")
    return link, extra


def set_state_main(argv: list) -> int:
    """`--set-state <D-id> <STATE> [--superseded-by <D-id>] --because <D-id> [--apply]`: ONE declared transition.

    THE DECLARED SEQUENCE (the three obligations the canonicalisation route carries, D-2972): the splice; the
    obligation PRINTED, because the registry receipt must be re-cut in the same sitting (the splice moved bytes
    INSIDE the receipted region by construction); and the act NAMED so a reader can join it. A transition to the
    supersession state CARRIES its successor in the same write (D-3216), so there is never a moment when the
    registry holds a retirement whose replacement cannot be named. The licence is checked FIRST - before any no-op
    branch - so nothing-to-do can never be the door a licence walks past.
    """
    tokens = list(argv[2:])   # argv[0] is this script and argv[1] is the flag (main reads sys.argv whole)
    if len(tokens) < 2:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: " + SET_STATE_FLAG + " <D-id> <STATE> ["
                         + SUPERSEDOR_FLAG + " <D-id>] --because <D-id> [--apply]")
    target, state, rest = tokens[0], tokens[1], tokens[2:]
    successor, rest = _take_successor(rest)
    # in_place_licence reads argv[1:], i.e. its caller's own argv with the script name at position 0, so the
    # licence is asked with a two-token head: [script-name slot, flag] - then the licence's own tokens.
    because, apply_now = in_place_licence([WRITER, SET_STATE_FLAG] + rest, SET_STATE_FLAG)
    if not licence_names_target(because, target):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + because + " does not NAME " + target + " in its own "
                         "payload - an ordering decision must speak the record it moves, or one order would "
                         "cover any record (D-2972/D-3035)")
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    new_text, problems = set_state_plan(text, target, state, successor)
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): refusing to move " + target + ": " + "; ".join(problems))
    pre_data = yaml.safe_load(text) or {}
    post_data = yaml.safe_load(new_text) or {}
    pre_total, _pre_summary, pre_stamp = recompute(pre_data)
    post_total, _post_summary, post_stamp = recompute(post_data)
    if post_total != pre_total:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the splice moved the RECORD COUNT (" + str(pre_total)
                         + "->" + str(post_total) + ") - refusing")
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    post_records = [r for r in (post_data.get("decisions") or []) if isinstance(r, dict)]
    shape = ["derived key " + repr(k) + " came back into the append_only registry (D-2655)"
             for k in REGISTRY_DERIVED_KEYS if k in post_data]
    shape += record_problems(post_records) + vocabulary_problems()
    if shape:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the spliced registry does not re-derive cleanly: "
                         + "; ".join(map(str, shape)))
    print("PRE  " + str(len(text.encode("utf-8"))) + " B sha256 " + hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("SPLICE " + target + " -> " + str(state).strip().upper()
          + (" (successor " + successor + ")" if str(successor or "").strip() else "")
          + " (licence " + because + ")")
    print("POST " + str(len(new_text.encode("utf-8"))) + " B sha256 "
          + hashlib.sha256(new_text.encode("utf-8")).hexdigest() + " - stamp " + pre_stamp + " -> " + post_stamp
          + " (it MOVES: a state is part of the content stamp)")
    if not apply_now:
        print("PREVIEW (nothing written): re-run with " + APPLY_FLAG)
        return 0
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    disk = DECISIONS_YAML.read_text(encoding="utf-8")
    disk_data = yaml.safe_load(disk) or {}
    d_total, d_summary, d_digest = recompute(disk_data)
    write_census(census_document(disk_data, d_total, d_summary, d_digest, disk))
    print("ok " + str(d_total) + " record(s), stamp " + d_digest + ", census re-derived from the bytes ON DISK")
    print_obligation(because)
    return 0


def record_problems(decisions: list) -> list[str]:
    """Well-formedness: duplicate normalised ids, duplicate spellings of the same fact, missing fields."""
    problems: list[str] = []
    seen: dict[str, list[str]] = {}
    for d in decisions:
        seen.setdefault(normalized_id(d), []).append(str(d.get("id")))
        if "status" in d:
            problems.append(
                f"{d.get('id')}: carries a redundant legacy 'status:' key alongside 'state:' - one fact in "
                f"two places with nothing reconciling them (BUG-483/RC-2)"
            )
        # Only the fields the census and the id namespace DEPEND on are required. `title` is NOT one of
        # them: ~558 records legitimately describe themselves with `description:`/`decision:` - asserting a
        # schema I cannot back is the same error this bug is about (a declaration not grounded in reality).
        if not str(d.get("id") or "").strip():
            problems.append("a record carries no id - it cannot be cited, counted, or reconciled")
        if not str(d.get("category") or "").strip():
            problems.append(f"{d.get('id')}: no 'category' - it would be silently filed under GOV")
    for key, spellings in seen.items():
        if len(spellings) > 1:
            problems.append(f"duplicate decision id {key} under {spellings} (C21: one token, one namespace)")
    return problems


def decisions_digest(decisions: list) -> str:
    """Return the 16-hex-char content digest of the decisions list (BUG-402).

    The digest is taken over the RECORDS ONLY, never over the file, so writing the stamp cannot
    change the value it stamps.
    """
    payload = json.dumps(decisions, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def recompute(data: dict) -> tuple[int, dict, str]:
    """Return (total, summary, decisions_digest) computed from data["decisions"]."""
    decisions = data.get("decisions") or []
    total = len(decisions)

    state_counts: dict[str, int] = {s.lower(): 0 for s in STATES}
    category_counts: dict[str, int] = {}
    for d in decisions:
        state = canonical_state(d).lower()
        state_counts[state] = state_counts.get(state, 0) + 1
        category = d.get("category")
        if not str(category or "").strip():
            raise SystemExit(
                f"FAIL-CLOSED (BUG-483): decision {d.get('id')!r} carries no 'category' - it would be "
                f"silently filed under GOV, so the by_category census would be wrong (D-404)"
            )
        category_counts[category] = category_counts.get(category, 0) + 1

    summary: dict = {
        "total": total,
        **state_counts,
        "by_category": dict(sorted(category_counts.items())),
    }
    return total, summary, decisions_digest(decisions)


def census_document(data: dict, total: int, summary: dict, digest: str, registry_text: str) -> dict:
    """The D-2655 census artifact: a PURE FUNCTION of the registry bytes, so a re-run is a no-op (D-2646).

    WHY A SECOND FILE EXISTS AT ALL. config/decisions.yaml is append_only and its handoff receipt is a PREFIX
    rule: the receipted bytes must be a prefix of the bytes on disk. `total_decisions`, `summary`,
    `decisions_sha256_16` and `last_sync` ALL change on every mint, so NO position inside an append-only file is
    compatible with a prefix rule while a derived value lives there (BUG-539) - the mint's mid-file insert is the
    symptom, not the disease. The census therefore leaves the registry.

    `source_sha256` is the sha256 of the WHOLE registry file, so a reader can prove WHICH bytes this document
    describes (D-382: a pin is bytes-on-disk -> digest, never a remembered string). NO generation timestamp is
    carried: a volatile field in a compared document makes every comparison a false witness. `last_sync` was REMOVED from this document in D-2655 HALF B for
    the same reason: a WHEN belongs in an append-only journal (the handoff receipts, the write journal),
    which cannot lie about the past because it is never rewritten. Post-D-2655 this document is the ONLY
    home of the census: the registry carries no derived field at all.

    `written_by` is the DECLARED writer of record for this artifact (config/artifact_ownership.yaml), which is
    this script - two declarations of one fact are joined here rather than trusted twice.
    """
    return {
        "schema_version": CENSUS_SCHEMA_VERSION,
        "source_path": DECISIONS_YAML.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(registry_text.encode("utf-8")).hexdigest(),
        "written_by": WRITER,
        "decisions_sha256_16": digest,
        "total_decisions": total,
        "summary": summary,
    }


CENSUS_COMPARED_KEYS: tuple[str, ...] = tuple(k for k in CENSUS_REQUIRED_KEYS if k != "source_path")


def census_text(document: dict) -> str:
    """Render the census deterministically: fixed key order, 2-space indent, trailing newline."""
    ordered = {key: document[key] for key in CENSUS_REQUIRED_KEYS}
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def census_problems(document: dict, path: Path = CENSUS_JSON) -> list[str]:
    """Drift between the census ON DISK and the census DERIVED from the registry (D-2655, D-2646).

    ABSENT is the error, never an empty census (BUG-487): a derived artifact nobody can read is a defect that
    must fail loudly, and 'nothing found' has never been 'clean' here. Every broken shape gets a NAMED refusal,
    because 'exit != 0' alone cannot tell a named refusal from a traceback (the BUG-541/BUG-544 class). The key
    SET is checked in BOTH directions: a key this writer does not derive cannot be compared, so it is NAMED
    rather than ignored - an undetected extra key is how a stale count survives every comparison.
    """
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = str(path)   # out-of-tree (a control fixture): DECIDE, never raise (BUG-541)
    if not path.exists():
        return [rel + ": ABSENT - the registry's derived census has no home on disk; re-derive it with "
                + WRITER + " (a missing derived artifact is a defect, never an empty one - BUG-487)"]
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [rel + ": UNREADABLE (" + type(exc).__name__ + "): " + str(exc)]
    try:
        on_disk = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [rel + ": does not parse as JSON at line " + str(exc.lineno) + " column " + str(exc.colno)
                + " (" + exc.msg + ")"]
    if not isinstance(on_disk, dict):
        return [rel + ": is a " + type(on_disk).__name__ + ", not a mapping - the census is a document"]
    missing = [k for k in CENSUS_REQUIRED_KEYS if k not in on_disk]
    if missing:
        return [rel + ": declares no " + ", ".join(repr(k) for k in missing) + " - a census missing a key cannot "
                "be compared field by field, and a defaulted census is not a census (D-2644)"]
    stray = sorted(k for k in on_disk if k not in CENSUS_REQUIRED_KEYS)
    if stray:
        return [rel + ': carries key(s) ' + str(stray) + ' that this writer does not derive - it emits exactly '
                + str(len(CENSUS_REQUIRED_KEYS)) + ' key(s) in a fixed order, so an extra key came from a hand '
                'edit or from an older schema, and a census nobody derives is how a stale count survives every '
                'comparison (D-2646/BUG-540). Re-derive with ' + WRITER]
    problems: list[str] = []
    for key in CENSUS_COMPARED_KEYS:
        if on_disk.get(key) != document.get(key):
            problems.append(rel + "." + key + ": declared " + str(on_disk.get(key)) + ", actual "
                            + str(document.get(key)) + " - re-derive with " + WRITER)
    return problems


def write_census(document: dict) -> None:
    """One crash-safe write of the census, verified against the bytes on disk (C6).

    `backup=False` is deliberate and declared: this artifact is derived_regenerable, so its pre-image is
    regenerable by its own contract (write_document's own words); the write still records the pre-image it
    replaced in the journal, which is what R-D410 requires of derived output - a pre-image is kept for a
    record, not for output that a deterministic re-run recreates byte for byte.
    """
    write_document(CENSUS_JSON, census_text(document), writer=WRITER, owned_keys={OWNED_ANY}, backup=False,
                   journal=True)
    post = census_problems(document)
    if post:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the census does not re-derive after writing: "
                         + "; ".join(post))


REGISTRY_DERIVED_KEYS: tuple[str, ...] = (
    "total_decisions", "summary", "last_sync", "decisions_sha256_16", "written_by",
)


def registry_shape_problems(data: dict) -> list[str]:
    """The POST-D-2655 contract of config/decisions.yaml: RECORDS ONLY, and the records well formed.

    D-2655 HALF B (2026-09-26). The derived fields left this file because it is append_only and its handoff
    receipt is a PREFIX rule, while total_decisions / summary / last_sync change on every mint - no position
    inside an append-only file is compatible with that (BUG-539). The ABSENCE of those keys is therefore not
    "nothing to check": it IS the contract, and a key that comes back is DRIFT, because the next mint would have
    to move bytes inside the receipted region. A rule that can never fire would be a comment (BUG-540), so this
    one was SEEN to refuse: with total_decisions restored to a copy of the registry, --check exits 1 naming it.
    """
    problems: list[str] = []
    back = sorted(k for k in REGISTRY_DERIVED_KEYS if k in data)
    if back:
        problems.append("derived key(s) " + str(back) + ": config/decisions.yaml is append_only with a PREFIX"
                        " receipt, so a derived field inside it makes every mint a mid-file rewrite"
                        " (BUG-539/D-2655) - the census is config/decisions_summary.json"
                        " (run: --strip-derived-head to restore the declared shape)")
    records = data.get("decisions")
    if not isinstance(records, list) or not records:
        problems.append("decisions: not a non-empty list of records - an empty registry is a defect, never an"
                        " empty success (BUG-487)")
        return problems
    problems.extend(record_problems(records))
    problems.extend(spelling_problems(records))
    problems.extend(vocabulary_problems())
    return problems

def _diff(data: dict, total: int, summary: dict, digest: str) -> list[str]:
    """The PRE-D-2655 head check: LIVE ONLY as the one-shot strip's precondition (D-2655 HALF B).

    Post-strip this file carries no derived field, so there is nothing here to diff. It is kept, and
    kept honest, because --strip-derived-head must refuse to migrate a header that is ALREADY wrong.
    """
    problems: list[str] = []
    if data.get("total_decisions") != total:
        problems.append(
            f"total_decisions: declared {data.get('total_decisions')!r}, actual {total}"
        )
    declared = data.get("summary") or {}
    for key, actual in summary.items():
        if key == "by_category":
            declared_cats = declared.get("by_category") or {}
            all_keys = sorted(set(declared_cats) | set(actual))
            for ck in all_keys:
                if declared_cats.get(ck) != actual.get(ck):
                    problems.append(
                        f"summary.by_category[{ck!r}]: declared "
                        f"{declared_cats.get(ck)!r}, actual {actual.get(ck)!r}"
                    )
        elif declared.get(key) != actual:
            problems.append(
                f"summary.{key}: declared {declared.get(key)!r}, actual {actual!r}"
            )
    # ONE-WAY IS NOT A JOIN (audit F6, MEASURED 2026-09-25): iterating only over the DERIVED keys let a
    # declared key that is no longer canonical survive every run without a word, so a state removed from the
    # vocabulary would keep reporting a count nobody re-derives. Removal may not happen by silence (D-2645).
    for stray in sorted(k for k in declared if k not in summary):
        problems.append(
            f"summary.{stray}: declared but NOT a canonical key - a key the reader no longer derives must be "
            f"removed, not left reporting (D-2645/D-2646)"
        )

    # BUG-402 integrity stamp: a declaration with no writer cannot fail loudly, so it is checked.
    declared_digest = data.get("decisions_sha256_16")
    if declared_digest != digest:
        problems.append(
            f"decisions_sha256_16: declared {declared_digest!r}, actual {digest!r} "
            "(the record set changed or the stamp was hand-edited)"
        )
    if not str(data.get("last_sync") or "").strip():
        problems.append("last_sync: missing or blank (no sanctioned writer ran)")
    if data.get("written_by") != WRITTEN_BY:
        problems.append(
            f"written_by: declared {data.get('written_by')!r}, expected {WRITTEN_BY!r}"
        )
    # BUG-483: the well-formedness of the RECORDS is part of "in sync", so --check reports it.
    problems.extend(record_problems(data.get("decisions") or []))
    # D-2645/D-2646: the RULE side is part of "in sync" too - a policy state the vocabulary cannot count.
    problems.extend(vocabulary_problems())
    return problems


MINT_REQUIRED: tuple[str, ...] = ("id", "state", "category", "title", "decision")

# D-2660 - THE MINT GATE JOINS A RECORD'S OWN FIELDS TO REALITY. BUG-550 was a record that named the wrong
# module and the wrong bug and stayed invisible: every rail read a record's VERDICT, no rail read two of its
# FIELDS together. MEASURED 2026-09-26 on the 790 records already on disk: 559 carry no `title`, 128 name no
# payload key at all, 26 file citations do not resolve and one `files:` value is a comma-joined BLOB - so this
# rule is FORWARD-ONLY, applied at the MOMENT OF MINT. It never rewrites history (the registry is append_only
# and its receipt is a PREFIX rule, BUG-539) and it never counts it. Existence of a cited FILE is checked on
# the machine that mints: a citation is a claim about the tree NOW, and the mint is the moment it is authored.
MINT_BUGS_KEY: str = "bugs"
MINT_PAYLOAD_KEYS: tuple[str, ...] = ("title", "decision", "rationale", "measured", "description", "verification")
MINT_CLONE_PREFIX: int = 200
BUG_REGISTER: Path = ROOT / "governance" / "bug_status.json"


def bug_register_ids() -> set[str]:
    """Return every bug id the register carries, or FAIL CLOSED - a citation checked against nothing is unchecked."""
    if not BUG_REGISTER.exists():
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + BUG_REGISTER.relative_to(ROOT).as_posix()
                         + " is absent - a bug citation checked against nothing is a citation nobody checked (C16)")
    doc = json.loads(BUG_REGISTER.read_text(encoding="utf-8"))
    ids = {str(b.get("id")) for b in (doc.get("open") or []) if isinstance(b, dict)}
    ids |= {str(b) for b in (doc.get("closed") or [])}
    if not ids:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): " + BUG_REGISTER.relative_to(ROOT).as_posix()
                         + " carries no bug id - an EMPTY register would refuse every honest mint or, worse, "
                         "pass every dishonest one (D-2659: a store named by its CAUSE)")
    return ids


def next_free_decision_id(decisions: list) -> str:
    """Return D-<max+1>: an id is a POSITION in the namespace, so a mint may only extend it by one."""
    nums: list[int] = []
    for d in decisions:
        body = str(d.get("id") or "").strip()
        if body.startswith("D"):
            body = body[1:].lstrip("-")
            if body.isdigit():
                nums.append(int(body))
    if not nums:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the registry carries no D-NNNN id - the next free id "
                         "cannot be derived from an empty namespace (C16)")
    return "D-" + str(max(nums) + 1)


def payload_text(record: dict) -> str:
    """Return every prose field of one record, joined: the payload a CLONE would have copied verbatim (BUG-550)."""
    return " ".join(str(record.get(k) or "") for k in MINT_PAYLOAD_KEYS).strip()


def _file_list(record: dict) -> list[str]:
    """Return the cited files as a list of strings - anything else is NOT a list and is reported as such."""
    files = record.get("files")
    return [str(f) for f in files] if isinstance(files, list) else []


def _bug_list(record: dict) -> list[str]:
    """Return the cited bugs as a list of strings - anything else is NOT a list and is reported as such."""
    bugs = record.get(MINT_BUGS_KEY)
    return [str(b) for b in bugs] if isinstance(bugs, list) else []


def mint_validate(record: dict, decisions: list, allow_gap: bool = False) -> list[str]:
    """Every reason a record may NOT be inserted - checked BEFORE a byte is written (D-2648/D-2649).

    allow_gap (BUG-989, D-3141): True ONLY on the declared `--restore-ids` route, which restores ids the LOG already
    names but the registry never minted (D-3134..D-3137). It relaxes the NEXT-FREE clause alone - a known,
    DECLARED gap is not a silent hole - while every other check (canonical state, no duplicate, bugs exist, files
    exist, no whole-payload clone) still runs. The default path is unchanged: forward-only, next-free enforced.
    """
    problems: list[str] = []
    if not isinstance(record, dict):
        return ["the minted record is " + type(record).__name__ + ", not a mapping"]
    missing = [k for k in MINT_REQUIRED if not str(record.get(k) or "").strip()]
    if missing:
        problems.append("missing required key(s) " + str(missing) + " - the census and the id namespace depend on "
                        "them, so an incomplete record would be counted while saying nothing")
        return problems
    canonical_state(record)   # FAIL CLOSED on a non-canonical state (BUG-483) rather than miscount it
    norm = normalized_id(record)
    same = [str(d.get("id")) for d in decisions if normalized_id(d) == norm]
    if same:
        problems.append(record.get("id") + " is already minted as " + ", ".join(same)
                        + " - a registry that can hold one id twice cannot answer what is decided (C21)")
    if "status" in record:
        problems.append("carries a legacy `status:` key alongside `state:` - one fact in two places (BUG-483)")
    # D-2660 CLAUSE 1 - the id is the NEXT FREE id. A namespace is extended, never sampled: a skipped id is a hole
    # that cannot be told apart from a record somebody removed (C21), and BUG-550 was found by reading ids in order.
    # Relaxed ONLY on the declared --restore-ids route (BUG-989): the ids being restored are ALREADY named in the log,
    # so the gap is a KNOWN omission, not a silent hole - and the authorising decision (D-3141) records it as such.
    if not allow_gap:
        expected = next_free_decision_id(decisions)
        if normalized_id(record) != normalized_id({"id": expected}):
            problems.append("id " + str(record.get("id")) + " is not the next FREE id (" + expected + ") - the mint "
                            "APPENDS, so an id that skips one is a hole indistinguishable from a deleted record "
                            "(D-2660); use --restore-ids only to restore an id the log already names")
    # CLAUSE 2 - the bugs it names EXIST in the register, and its own payload NAMES at least one of them. A record
    # whose payload names a bug it does not cite IS the BUG-550 signature (D-2659 carried BUG-542's rationale).
    bugs = _bug_list(record)
    if not [b for b in bugs if b.strip()]:
        problems.append("names no `bugs:` list - a decision that fixes nothing cannot be joined to the register "
                        "(D-2660)")
    else:
        known = bug_register_ids()
        unknown = [b for b in bugs if b not in known]
        if unknown:
            problems.append("cites bug(s) that are NOT in the register: " + ", ".join(unknown)
                            + " - register the bug BEFORE the decision that cites it, or the citation names nothing "
                            "(D-2660)")
        payload = payload_text(record)
        if payload and not any(b in payload for b in bugs):
            problems.append("its payload names NONE of its own bugs " + str(bugs) + " - the tell of a CLONED record "
                            "(BUG-550); a decision must say what it fixes")
    # CLAUSE 3 - every cited FILE exists, and `files` is a LIST. A comma-joined blob is one path that exists
    # nowhere: MEASURED on 1 of the 790 records on disk, which is why the rule is forward-only.
    files = _file_list(record)
    if not files:
        problems.append("names no `files:` list - a decision with no artifact cannot be joined to the tree (D-2660)")
    else:
        absent = [f for f in files if not Path(f).expanduser().exists()]
        if absent:
            problems.append("cites file(s) that do NOT exist: " + ", ".join(absent)
                            + " - a citation is a claim about the tree at the MOMENT OF MINT (D-2660)")
    # CLAUSE 4 - a WHOLE-PAYLOAD CLONE of a record already on disk is REFUSED. Same files AND same bugs AND the
    # same payload opening is not a coincidence: it is BUG-550, where a cloned record named the wrong module and
    # the wrong bug while EVERY rail stayed green, because no rail read two fields of one record together.
    mine = (sorted(files), sorted(bugs), payload_text(record)[:MINT_CLONE_PREFIX])
    for other in decisions:
        theirs = (sorted(_file_list(other)), sorted(_bug_list(other)),
                  payload_text(other)[:MINT_CLONE_PREFIX])
        if mine[2] and mine == theirs:
            problems.append("is a WHOLE-PAYLOAD CLONE of " + str(other.get("id")) + " (same files, same bugs, same "
                            "payload opening) - that is the BUG-550 signature, not a coincidence (D-2660)")
            break
    return problems



def arrival_problems(total_before: int, decisions_after: list, minted_ids: list[str]) -> list[str]:
    """BUG-587 (D-2690): every minted id must be a TOP-LEVEL record, and the count must move by the mint size.

    WHY. MEASURED 2026-09-27: a hand-rolled append of ONE record to config/decisions.yaml added 32 lines and
    deleted none - and the census did NOT move (819 records, last D-2688). A record's files: items emit at indent
    2, the SAME column a record's own '- id:' marker takes when a writer re-indents the dumped block, so the new
    record parsed as ONE MORE ENTRY of the PREVIOUS record's files: list. The file LOADED, every rail stayed
    GREEN, and the decision was INVISIBLE. The write path validated the record BEFORE the write and re-derived
    the registry SHAPE after it - but nothing ever asked whether the mint ARRIVED. That is the BUG-492 class
    aimed at the registry: a write that cannot be SEEN to fail.

    Checked on the WOULD-BE bytes BEFORE the write, so a record that would be absorbed is REFUSED rather than
    landed invisibly, and again on the bytes ON DISK after it.
    """
    problems: list[str] = []
    expected = total_before + len(minted_ids)
    if len(decisions_after) != expected:
        problems.append("the registry holds " + str(len(decisions_after)) + " record(s) after the write, expected "
                        + str(expected) + " (" + str(total_before) + " before + " + str(len(minted_ids))
                        + " minted) - a mint that moves the count by anything else did NOT arrive (BUG-587)")
    top = top_level_ids(decisions_after)
    for minted in minted_ids:
        norm = normalized_id({"id": minted})
        hits = [t for t in top if t == norm]
        if not hits:
            problems.append(str(minted) + ": the minted id is NOT a TOP-LEVEL record after the write - the record "
                            "was ABSORBED into another record's list (its bytes are in the file, the file parses, "
                            "and the decision is invisible; MEASURED 2026-09-27, BUG-587)")
        elif len(hits) > 1:
            problems.append(str(minted) + ": appears " + str(len(hits)) + " time(s) as a TOP-LEVEL record, expected "
                            "exactly once - a registry that can hold one id twice cannot answer what is decided")
    return problems


def top_level_ids(decisions: list) -> list[str]:
    """The NORMALISED ids of the TOP-LEVEL records: an id nested inside a record's list is not a record (BUG-587)."""
    return [normalized_id(r) for r in decisions if isinstance(r, dict)]


def mint_controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the D-2660 MINT gate (BUG-492: a detector nobody has seen fail is not a detector)."""
    live = (yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}).get("decisions") or []
    good = {
        "id": next_free_decision_id(live),
        "state": "OPEN",
        "category": "GOVERNANCE / RULES",
        "title": "control record - never written",
        "decision": "a control payload naming BUG-549 and scripts/recompute_decision_summary.py",
        "bugs": ["BUG-549"],
        "files": ["scripts/recompute_decision_summary.py"],
    }

    def rec(**kw) -> dict:
        """One mutated copy of the control record: a control must be able to fire on ONE field change."""
        base = dict(good)
        base.update(kw)
        return base

    def fires(record: dict) -> bool:
        """True when the gate REFUSES the record (the only evidence a gate exists)."""
        return bool(mint_validate(dict(record), live))

    last = live[-1] if live else {"id": "D-0"}
    # BUG-587: the ABSORBED shape - the minted record lands as ONE MORE ENTRY of the previous record's files: list.
    absorbed_after = live[:-1] + [dict(live[-1], files=list(_file_list(live[-1])) + [dict(good)])] if live else [dict(good)]
    skipped = "D-" + str(int(next_free_decision_id(live).split("-")[1]) + 1)
    return [
        ("the control record itself PASSES - a gate that refuses everything proves nothing", not fires(good)),
        ("an id that SKIPS the next free one fires", fires(rec(id=skipped))),
        ("an id already minted fires", fires(rec(id=str(last.get("id"))))),
        ("a bug that is NOT in the register fires", fires(rec(bugs=["BUG-9999"], decision="naming BUG-9999"))),
        ("no `bugs:` list fires", fires(rec(bugs=[]))),
        ("a payload naming NONE of its own bugs fires (the BUG-550 tell)",
         fires(rec(bugs=["BUG-549"], decision="a record about nothing in particular"))),
        ("a cited FILE that does not exist fires", fires(rec(files=["scripts/does_not_exist_9f3.py"]))),
        ("a comma-joined `files` BLOB fires", fires(rec(files="scripts/a.py, scripts/b.py"))),
        ("a WHOLE-PAYLOAD CLONE of the last record on disk fires",
         fires(dict(last, id=next_free_decision_id(live)))),
        ("a missing required key fires", fires(rec(title=""))),
        ("a mint that ARRIVES is accepted - the count moves by exactly the mint size and the id is TOP-LEVEL",
         not arrival_problems(len(live), live + [dict(good)], [good["id"]])),
        ("a mint whose id is ABSENT from the top level fires (the BUG-587 ABSORBED shape)",
         bool(arrival_problems(len(live) - 1, absorbed_after, [good["id"]]))),
    # BUG-590 (D-2690): the COUNT is landed EXACTLY here (len(live) - 1 before + 1 minted == len(absorbed_after)),
    # so this control can only PASS or FAIL through the TOP-LEVEL clause it names. MEASURED by the mutation gate:
    # with len(live) the control fired through the COUNT clause instead, and the arrival mutation could not be
    # seen to red it - a control whose NAME and REASON disagree is not a control (D-2676 iv, one level down).
        ("a minted id that lands TWICE as a top-level record fires",
         bool(arrival_problems(len(live) + 1, live + [dict(good), dict(good)], [good["id"]]))),
        ("a mint that does not move the count by its own size fires",
         bool(arrival_problems(len(live), live, [good["id"]]))),
        ("a state spelled in a NON-CANONICAL case with no pin is a NAMED fault (BUG-583)",
         bool(spelling_problems([{"id": "D-9001", "state": "active"}], pinned=[]))),
        ("the same spelling is TOLERATED while pinned BY IDENTITY, and the pin goes STALE once canonical",
         not spelling_problems([{"id": "D-9001", "state": "active"}], pinned=["D9001"])
         and bool(spelling_problems([{"id": "D-9001", "state": "ACTIVE"}], pinned=["D9001"]))),
        ("a splice that moves a state the PIN never named is a NAMED fault (D-2655/BUG-583)",
         bool(splice_problems([{"id": "D-9001", "state": "active"}, {"id": "D-9002", "state": "ACTIVE"}],
                              [{"id": "D-9001", "state": "ACTIVE"}, {"id": "D-9002", "state": "PROPOSED"}],
                              ["D9001"]))),
        ("a splice that canonicalises the PINNED cell and NOTHING else is accepted, so the pin may shrink to empty",
         not splice_problems([{"id": "D-9001", "state": "active"}], [{"id": "D-9001", "state": "ACTIVE"}],
                             ["D9001"])),
    ]


def state_controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the STATE TRANSITION route (D-3035/M2) - every one SEEN to fire or accept."""
    text = ("schema_version: '1'\ndecisions:\n"
            "- id: D-9001\n  state: PROPOSED\n  category: X\n  title: control\n  decision: control\n"
            "- id: D-9002\n  state: ACTIVE\n  category: X\n  title: control\n  decision: control\n")
    twice = ("schema_version: '1'\ndecisions:\n"
             "- id: D-9001\n  state: PROPOSED\n  state: PROPOSED\n  category: X\n")
    carrying = ("schema_version: '1'\ndecisions:\n"
                "- id: D-9001\n  state: PLANNED\n  superseded_by: D-9003\n  category: X\n"
                "- id: D-9002\n  state: ACTIVE\n  category: X\n"
                "- id: D-9003\n  state: RESOLVED\n  category: X\n")
    linking = ("schema_version: '1'\ndecisions:\n"
               "- id: D-9001\n  state: SUPERSEDED\n  category: X\n"
               "- id: D-9002\n  state: ACTIVE\n  category: X\n")
    decisions = [{"id": "D-9001", "state": "PROPOSED"}, {"id": "D-9002", "state": "ACTIVE"}]

    def refuses(problems) -> bool:
        return bool(problems)

    def moves_exactly_one_line() -> bool:
        new_text, problems = set_state_plan(text, "D-9001", "RATIFIED")
        if problems:
            return False
        lines_before, lines_after = text.split(chr(10)), new_text.split(chr(10))
        return (sum(1 for a, b in zip(lines_before, lines_after) if a != b) == 1
                and len(lines_before) == len(lines_after)
                and "  state: RATIFIED" in new_text
                and [r for r in (yaml.safe_load(new_text) or {})["decisions"] if r["id"] == "D-9002"][0]["state"]
                == "ACTIVE")

    def carries_its_successor() -> bool:
        """BUG-1099/D-3216: the accepted supersession must move ONE replaced line and ONE inserted link, and the
        record must READ BACK the successor it was given - a write nobody can read back is not a write."""
        new_text, problems = set_state_plan(text, "D-9001", "SUPERSEDED", "D-9002")
        if problems:
            return False
        post = {r["id"]: r for r in (yaml.safe_load(new_text) or {})["decisions"]}
        return (len(new_text.split(chr(10))) == len(text.split(chr(10))) + 1
                and post["D-9001"].get("state") == "SUPERSEDED"
                and post["D-9001"].get(successor_field()) == "D-9002"
                and post["D-9002"].get("state") == "ACTIVE"
                and "  " + successor_field() + ": D-9002" in new_text)

    def link_only_repair_moves_the_link_and_not_the_state() -> bool:
        """D-3216 legacy discharge: a record ALREADY reading SUPERSEDED gets its missing successor, and the state
        cell is rewritten in place without changing - so the repair is provable and not a silent no-op."""
        new_text, problems = set_state_plan(linking, "D-9001", "SUPERSEDED", "D-9002")
        if problems:
            return False
        post = {r["id"]: r for r in (yaml.safe_load(new_text) or {})["decisions"]}
        return (len(new_text.split(chr(10))) == len(linking.split(chr(10))) + 1
                and post["D-9001"].get("state") == "SUPERSEDED"
                and post["D-9001"].get(successor_field()) == "D-9002"
                and post["D-9002"].get("state") == "ACTIVE")


    return [
        ("a_state_word_not_in_the_declared_vocabulary_is_REFUSED",
         lambda: refuses(state_target_problems(decisions, "D-9001", "BANANA"))),
        ("a_transition_to_the_state_a_record_ALREADY_reads_is_REFUSED_as_a_stale_declaration",
         lambda: refuses(state_target_problems(decisions, "D-9002", "ACTIVE"))),
        ("a_transition_of_a_record_that_does_NOT_exist_is_REFUSED",
         lambda: refuses(state_target_problems(decisions, "D-9999", "RATIFIED"))),
        ("a_record_carrying_TWO_state_cells_is_REFUSED_rather_than_guessed",
         lambda: refuses(set_state_plan(twice, "D-9001", "RATIFIED")[1])),
        ("a_state_of_a_record_this_registry_does_NOT_carry_is_REFUSED",
         lambda: refuses(set_state_plan(text, "D-9999", "RATIFIED")[1])),
        ("a_valid_transition_moves_EXACTLY_ONE_line_and_leaves_every_other_record_alone",
         moves_exactly_one_line),
        ("every_state_the_vocabulary_declares_is_classified_by_the_policy_so_none_can_enter_silently",
         lambda: all(s in (policy_states("graph") + policy_states("whole")) for s in STATES)),
        ("a_transition_to_the_SUPERSESSION_state_WITHOUT_a_successor_is_REFUSED_that_is_the_BUG-1099_defect",
         lambda: refuses(set_state_plan(text, "D-9001", "SUPERSEDED")[1])),
        ("a_successor_naming_no_record_is_REFUSED_rather_than_written_as_a_link_to_nothing",
         lambda: refuses(set_state_plan(text, "D-9001", "SUPERSEDED", "D-9999")[1])),
        ("a_SELF_LINK_supersession_is_REFUSED_a_chain_that_goes_nowhere",
         lambda: refuses(set_state_plan(text, "D-9001", "SUPERSEDED", "D-9001")[1])),
        ("a_successor_on_a_transition_to_a_state_that_reads_none_is_REFUSED_a_link_no_reader_consults",
         lambda: refuses(set_state_plan(text, "D-9001", "RATIFIED", "D-9002")[1])),
        ("a_record_already_carrying_a_DIFFERENT_successor_is_REFUSED_one_supersession_one_link",
         lambda: refuses(set_state_plan(carrying, "D-9001", "SUPERSEDED", "D-9002")[1])),
        ("a_supersession_WITH_its_successor_is_ACCEPTED_and_the_record_READS_BACK_the_link",
         carries_its_successor),
        ("an_ALREADY_superseded_record_given_its_MISSING_successor_is_ACCEPTED_as_a_LINK_ONLY_repair",
         link_only_repair_moves_the_link_and_not_the_state),
        ("an_ALREADY_superseded_record_given_the_SAME_successor_again_is_REFUSED_as_a_stale_no_op",
         lambda: refuses(set_state_plan(linking, "D-9001", "SUPERSEDED", "D-9002")[1]) is False
         and refuses(set_state_plan(
             set_state_plan(linking, "D-9001", "SUPERSEDED", "D-9002")[0], "D-9001", "SUPERSEDED", "D-9002")[1])),
    ]


def mint_selftest() -> int:
    """Run the mint gate's known-answer controls; return 1 if any control did NOT fire."""
    rows = mint_controls() + state_controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [n for n, ok in rows if not ok]
    if failed:
        for name in failed:
            print("  FAIL selftest/" + control_slug(name))
        print("FAIL (" + WRITER + ") --selftest: " + str(len(failed)) + " of " + str(len(rows))
              + " known-answer control(s) did not fire - a mint gate nobody has seen refuse is a comment (BUG-492)")
        return 1
    print("ok (" + WRITER + ") --selftest: " + str(len(rows)) + "/" + str(len(rows))
          + " known-answer control(s) fire")
    return 0


def mint_main(argv: list[str]) -> int:
    """`--mint <file|-> [--apply]`: insert record(s) that were VALIDATED and RENDERED, never hand-typed.

    WHY (D-2648/D-2649). MEASURED 2026-09-26: two YAML artifacts were left unparseable inside one session by string
    surgery on YAML - one of them this registry, whose line 8667 carried a hand-written `decision:` value with an
    unquoted colon-space. The remedy for the WRITER is not a rule it must remember, it is a path where the failure
    cannot be authored: the record is dumped by the YAML emitter (which quotes what needs quoting), the resulting
    bytes are parsed back in full, and only then are they written through write_guard. A caller can still write a
    bad record BY HAND; it cannot make this path emit one. Preview is the default; --apply writes. The file is read
    as YAML, so the same path accepts JSON (JSON is a subset of YAML).
    """
    allow_gap = "--restore-ids" in argv
    args = [a for a in argv[1:] if a not in ("--mint", "--apply", "--restore-ids")]
    unknown = [a for a in argv[1:] if a.startswith("--") and a not in ("--mint", "--apply", "--restore-ids")]
    if unknown or len(args) != 1:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): usage: --mint <record.yaml|record.json|-> [--apply]"
                         + " [--restore-ids]"
                         + (" - unknown flag(s) " + str(unknown) if unknown else "")
                         + " - one record file, refusing rather than guessing")
    if allow_gap and "--apply" not in argv:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): --restore-ids is a declared RESTORE route (BUG-989/D-3141) and "
                         "must be applied in the same invocation it is previewed - refuse rather than preview a gap "
                         "restoration that is not written")
    raw = sys.stdin.read() if args[0] == "-" else Path(args[0]).read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    records = doc if isinstance(doc, list) else [doc]

    text = DECISIONS_YAML.read_text(encoding="utf-8")
    decisions = (yaml.safe_load(text) or {}).get("decisions") or []
    problems: list[str] = []
    for record in records:
        problems += [str(p) for p in mint_validate(record, decisions, allow_gap=allow_gap)]
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the record was NOT written: " + "; ".join(problems))

    block = yaml.dump(records, default_flow_style=False, sort_keys=False, allow_unicode=True, width=110,
                      indent=2).rstrip(chr(10))
    # D-2655 HALF B: a mint is an APPEND, and it is checked as one rather than asserted. The registry is
    # records-only and extends to EOF, so the new bytes have the old bytes as a PREFIX - which is exactly what the
    # decisions_registry receipt demands. MEASURED BEFORE: the mid-file insert moved bytes inside the receipted
    # region and the rail reported the registry as 'rewritten' (BUG-539); a record appended after a later
    # top-level key is what left config/derivations.yaml unparseable (BUG-505), and records-only removes both
    # failure modes at once (there is no later top-level key).
    new_text = (text if text.endswith(chr(10)) else text + chr(10)) + block + chr(10)
    if not new_text.startswith(text):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the minted text is not an APPEND of the registry on disk, "
                         "so the append-only receipt could not survive it - refusing by construction (D-2655)")
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    if "--apply" not in argv:
        print("PREVIEW (nothing written) - " + str(len(records)) + " record(s) would be inserted:")
        print(block)
        print("re-run with --apply to write, then the derived fields are recomputed in the same invocation.")
        return 0

    # ONE write (D-2648): the inserted record and the derived fields it invalidates go to disk TOGETHER.
    # MEASURED 2026-09-26 by this path's own first run: writing the record on its own left 784 records under a
    # 783 header, and the rail that caught it was the NEXT reader, not this writer.
    yaml_guard.assert_yaml(new_text, "config/decisions.yaml", WRITER)
    would_be = yaml.safe_load(new_text) or {}
    post = registry_shape_problems(would_be)
    if post:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the minted registry does not re-derive cleanly: "
                         + "; ".join(map(str, post)))
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    # D-2655: the census is derived from the registry, so a mint that moved the registry MUST carry the census
    # with it in the SAME invocation - otherwise the mint succeeds and leaves the second home describing bytes
    # that no longer exist, and the reader that catches it is the NEXT one (the D-2648 lesson).
    post_text = DECISIONS_YAML.read_text(encoding="utf-8")
    post_data = yaml.safe_load(post_text) or {}
    post_total, post_summary, post_digest = recompute(post_data)
    write_census(census_document(post_data, post_total, post_summary, post_digest, post_text))
    print("merged " + str(len(records)) + " record(s): " + ", ".join(str(r.get("id")) for r in records)
          + " - total=" + str(post_total) + ", stamp " + post_digest
          + ", census " + CENSUS_JSON.relative_to(ROOT).as_posix())
    return 0



STRIP_FLAG: str = "--strip-derived-head"


def strip_main(argv: list[str]) -> int:
    """ONE-SHOT (D-2655 HALF B): take the derived fields OUT of the append-only registry, by BYTE SPLICE.

    WHY A SPLICE AND NOT A REWRITE. The records are never re-rendered: the new text is
    `version/ratified + registry[decisions: up to the summary block]`, so the record BYTES are the bytes that were
    already on disk. The proof is the content stamp, which must not move (asserted below, not assumed); a YAML
    re-dump would have produced a NEW document that merely happens to parse - the D-2655 HALF A lesson.

    IT REFUSES UNLESS THE REGISTRY IS ALREADY COHERENT (C16, fail closed): the derived fields must re-derive with
    zero drift AND the census on disk must already describe these exact bytes. Stripping a registry whose header is
    already wrong would delete the disagreement instead of reporting it. A second run refuses as ALREADY STRIPPED.

    THE ROUTE SHRINKS THE RECEIPTED REGION BY CONSTRUCTION (D-2972), which the re-baseline act deliberately REFUSES
    when it is UNLICENSED: a truncation loses every record after the cut, so it is RESTORED, never re-baselined
    (D-2971). Here the cut removes DERIVED bytes under a decision, not records (the record count and the content
    stamp are asserted UNMOVED below), so the obligation this route leaves is discharged by the act - and the
    route says so in the ACT's words, from the receipt module's one home, carrying the licence it was given.
    """
    because, apply_now = in_place_licence(argv, STRIP_FLAG)
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not [k for k in REGISTRY_DERIVED_KEYS if k in data]:
        print("ALREADY STRIPPED - nothing to do: the registry carries no derived key")
        return 0
    total, summary, digest = recompute(data)
    want = census_document(data, total, summary, digest, text)
    on_disk = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))
    bad = [k for k in ("written_by", "source_sha256", "total_decisions", "summary", "decisions_sha256_16")
           if on_disk.get(k) != want[k]]
    problems = _diff(data, total, summary, digest) + (
        ["census " + str(bad) + ": the census on disk does not describe these bytes, so the strip would delete a "
         "disagreement instead of reporting it"] if bad else [])
    if problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): refusing to strip a registry that is not ALREADY coherent: "
                         + "; ".join(problems))
    head_end = text.index(chr(10), text.index(chr(10)) + 1) + 1
    body_at = text.index(chr(10) + "decisions:" + chr(10)) + 1
    cut_at = text.rindex(chr(10) + "summary:")
    new_text = text[:head_end] + text[body_at:cut_at] + chr(10)
    stripped = text[head_end:body_at]
    post = yaml.safe_load(new_text) or {}
    post_total, post_summary, post_digest = recompute(post)
    if post_total != total or post_digest != digest:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the splice MOVED the records (" + str(total) + "->"
                         + str(post_total) + ", stamp " + digest + "->" + post_digest + ") - refusing")
    if registry_shape_problems(post):
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the spliced text is not records-only: "
                         + "; ".join(registry_shape_problems(post)))
    print("PRE  " + str(len(text)) + " B sha256 " + hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("DROP " + str(len(stripped)) + " B of derived head: " + stripped.replace(chr(10), " | "))
    print("DROP " + str(len(text) - cut_at) + " B of summary block")
    if not apply_now:
        print("PREVIEW (nothing written): re-run with " + APPLY_FLAG)
        return 0
    write_document(DECISIONS_YAML, new_text, writer=WRITER, owned_keys={OWNED_ANY}, backup=True, journal=True)
    disk = DECISIONS_YAML.read_text(encoding="utf-8")
    disk_data = yaml.safe_load(disk) or {}
    d_total, d_summary, d_digest = recompute(disk_data)
    write_census(census_document(disk_data, d_total, d_summary, d_digest, disk))
    print("POST " + str(len(disk)) + " B sha256 " + hashlib.sha256(disk.encode("utf-8")).hexdigest())
    print("     records " + str(d_total) + ", stamp " + d_digest + " (stamp UNMOVED: " + str(d_digest == digest)
          + ") - census re-derived from the bytes ON DISK")
    print_obligation(because)
    return 0


def main(argv: list[str]) -> int:
    """Recompute, --check, --mint a validated record, or --strip-derived-head; keep the census in step.

    D-2655 HALF B: the registry is RECORDS ONLY, so the steady-state repair below touches the CENSUS
    ONLY. A drifted registry is repaired by --mint (an APPEND) or by a person, never by a convenience
    write. The HALF A paragraph that follows is kept for the record of that reasoning.

    SELF-HEALING PER ARTIFACT (and this matters for the receipt). The write branch fixes ONLY what is actually
    wrong: a drift-free registry is NEVER rewritten, so the registry bytes do not move and the
    `decisions_registry` prefix receipt is untouched. Writing the registry whenever the census is merely absent
    would move `last_sync` on a healthy registry and turn that receipt into 'rewritten' - a repair that breaks a
    guarantee is not a repair.
    """
    if "--selftest" in argv:
        return mint_selftest()
    if "--mint" in argv:
        return mint_main(argv)
    if STRIP_FLAG in argv:
        return strip_main(argv)
    if CANONICALISE_FLAG in argv:
        return canonicalise_main(argv)
    if SET_STATE_FLAG in argv:
        return set_state_main(argv)
    check_only = "--check" in argv
    text = DECISIONS_YAML.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    total, summary, digest = recompute(data)
    registry_problems = registry_shape_problems(data)
    census = census_document(data, total, summary, digest, text)
    problems = registry_problems + census_problems(census)

    if not problems:
        print(f"✅ {DECISIONS_YAML.relative_to(ROOT).as_posix()} is records-only (D-2655) — {total} decisions, stamp {digest}.")
        print(f"✅ {CENSUS_JSON.relative_to(ROOT).as_posix()} describes those exact bytes "
              f"({len(CENSUS_REQUIRED_KEYS)} key(s), source_sha256 {census['source_sha256'][:16]}).")
        return 0

    print(f"⚠️  {len(problems)} drift(s) detected:")
    for p in problems:
        print(f"   - {p}")

    if check_only:
        return 1

    # D-2655 HALF B: this branch repairs the CENSUS ONLY. It may never write the registry, because the registry
    # is append_only and the only write that preserves its prefix receipt is an APPEND - and the only sanctioned
    # append is --mint. A repair that breaks a guarantee is not a repair (BUG-539).
    if registry_problems:
        raise SystemExit("FAIL-CLOSED (" + WRITER + "): the registry is not in its declared records-only shape, "
                         "and this branch may not rewrite an append_only artifact: " + "; ".join(registry_problems))
    write_census(census)
    print(f"✅ census written: {CENSUS_JSON.relative_to(ROOT).as_posix()} — {total} decisions, "
          f"stamp {digest}, source_sha256 {census['source_sha256'][:16]}")
    print("   (registry untouched: records-only and byte-identical, so its prefix receipt still holds)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
