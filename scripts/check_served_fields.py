#!/usr/bin/env python3
"""check_served_fields.py - D-2989: AN ADVERTISED FIELD IS A CLAIM.

WHY (the class, not the instances). A serving surface that publishes a store column is making a CLAIM about the
store. Nothing joined the claim to the registers that already own its truth, so an agent could be told a
fabricated measurement and every rail stayed green. MEASURED 2026-10-13: the MCP payload advertises 20 fields that
name `fbs` columns and THREE of them are flagged by a register that owns the fact - `borp_score` (a constant 0.0
nothing writes, `derivations: dead_but_read` + `store_columns: debt`), `feedback_score` (NULL on every row,
`declared_but_empty`) and `classification_status` (a constant 'CLEAN' while 2,972 rows are QUARANTINE). The
`borp_score` case is the BUG-511 family with outward harm: the fabricated value also leaves the machine through the
OKF export and the Anytype push.

WHAT IT IS NOT. This rail is a JOIN, never a census: the truth about a column lives in `config/derivations.yaml`
(home + status, D-2646) and `config/store_columns.yaml` (role + status, D-2960). A second census of the same fact
is the defect those registers exist to prevent, so this file measures only what they cannot: whether the SURFACE
publishes it, and whether a declaration says what is owed.

POPULATION (stated, so the number is reproducible). The advertised set = the string KEYS of the dicts in each
declared surface (`kind: dict_keys`) or the string constants that name a field (`kind: string_mentions`),
INTERSECTED with `PRAGMA table_info(fbs)` - an advertised key that names a store column is a claim about the store;
a key that does not (rank, fb_id-as-structure, error) is payload structure. The store measurement uses the DECLARED
population (canonical run, status = PASS), read from pipeline.pipeline_paths, never restated as a literal.

THE RULE. A flagged advertised field MUST carry a declaration in config/served_fields.yaml with the owner word that
closes it. Undeclared = DEFECT. Declared but no longer advertised = DEFECT (an assertion whose subject is gone,
BUG-488/D-405). A word outside the vocabulary, or a word with no anchor, or a promotion whose home does not exist =
DEFECT, fail closed (T-101: an unsigned decision is not a rule). Debt = the declared-and-still-advertised count, and
its ceiling is SHRINK-ONLY (D-2644).

Exit: 0 clean | 1 defect | 2 declared owner-owed debt (loud, NOT fatal - the BUG-457 tri-state).
"""
from __future__ import annotations

import argparse
import ast
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml

REPO: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

DECLARATION: Path = REPO / "config" / "served_fields.yaml"
PREFIX: str = "check-served-fields"

OK = "OK"
ACKNOWLEDGED = "ACKNOWLEDGED"
OWNER_OWED = "OWNER_OWED"
DEFECT_UNDECLARED = "DEFECT_UNDECLARED_ADVERT"
DEFECT_STALE = "DEFECT_STALE_DECLARATION"
DEFECT_WORD = "DEFECT_UNDECLARED_WORD"
DEFECT_ANCHOR = "DEFECT_UNSIGNED_WORD"
DEFECT_HOME = "DEFECT_MISSING_HOME"
DEFECT_CEILING = "DEFECT_CEILING_EXCEEDED"
DEFECT_SURFACE = "DEFECT_MISSING_SURFACE"
DEFECT_TIER = "DEFECT_TIER_POLICY_UNJOINED"
DEFECT_UNJOINED = "DEFECT_DECLARATION_UNJOINED"
EXIT_OK, EXIT_DEFECT, EXIT_OWNER_OWED = 0, 1, 2
PROMOTE_PREFIX = "promote "
PENDING = "pending"
#: T-118: the three dispositions the owner was offered. `tier` is the granted word; the other two are declared so a
#: near-miss token (`withold`, `keep`) is refused BY NAME rather than accepted as an unknown string (the T-101 rule).
TIER_WORDS: tuple[str, ...] = ("tier", "withhold", "leave")
DEFECTS = (
    DEFECT_UNDECLARED,
    DEFECT_STALE,
    DEFECT_WORD,
    DEFECT_ANCHOR,
    DEFECT_HOME,
    DEFECT_CEILING,
    DEFECT_SURFACE,
    DEFECT_TIER,
)


def load_declaration() -> dict[str, Any]:
    """Read the ONE home of the advertised-field dispositions (fail-closed: no code default)."""
    doc = yaml.safe_load(DECLARATION.read_text())
    if not isinstance(doc, dict):
        raise ValueError(f"{DECLARATION} must be a mapping")
    return doc


def columns_of_store() -> set[str]:
    """The store's column names - the vocabulary an advertised key must name to be a CLAIM (read-only)."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return {str(r[1]) for r in con.execute("PRAGMA table_info(fbs)")}
    finally:
        con.close()


def advertised_fields(rel: str, kind: str, columns: set[str]) -> set[str]:
    """The store fields THIS surface publishes. A comment or a docstring can never satisfy the scan.

    Args:
        rel: the surface file, relative to the repo root.
        kind: 'dict_keys' (a string key of any dict in the file) or 'string_mentions' (a string constant that
            names a field, e.g. the OKF export's f-string line).
        columns: the store's columns - the join that turns an advertised key into a claim.

    Returns:
        The advertised store fields.

    Raises:
        FileNotFoundError: the declared surface does not exist (C16: a surface that is missing is not a clean scan).
    """
    path: Path = REPO / rel
    if not path.exists():
        raise FileNotFoundError(f"the declared surface {rel} does not exist")
    tree: ast.Module = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if kind == "dict_keys" and isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    found.add(key.value)
        elif kind == "string_mentions" and isinstance(node, ast.Constant) and isinstance(node.value, str):
            for col in columns:
                if re.search(rf"\b{re.escape(col)}\b", node.value):
                    found.add(col)
    if kind not in ("dict_keys", "string_mentions"):
        raise ValueError(f"unknown surface kind {kind!r} (C16: an unreadable kind is not a clean scan)")
    return found & columns


def register_flags(declaration: dict[str, Any]) -> dict[str, list[str]]:
    """field -> every reason a register that OWNS the column's truth flags it (empty = the registers call it healthy).

    The registers are read, never re-derived: a rival verdict here would be the BUG-502 class.
    """
    regs: dict[str, Any] = declaration["registers"]
    flagged: dict[str, list[str]] = {}
    derived_doc: dict[str, Any] = yaml.safe_load((REPO / regs["derived"]).read_text())
    derived_bad: set[str] = set(declaration["flagged_status"]["derived"])
    for row in derived_doc.get("derivations") or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        status: str = str(row.get("status"))
        if status in derived_bad:
            leaf: str = str(row["name"]).split(".")[-1]
            flagged.setdefault(leaf, []).append(f"derivations:{status}")
    shape_doc: dict[str, Any] = yaml.safe_load((REPO / regs["shape"]).read_text())
    shape_bad: set[str] = set(declaration["flagged_status"]["shape"])
    for col, info in (shape_doc.get("columns") or {}).items():
        if isinstance(info, dict) and str(info.get("status")) in shape_bad:
            flagged.setdefault(str(col), []).append(f"store_columns:status={info.get('status')}")
    return flagged


def home_exists(home: str) -> bool:
    """Whether a declared home RESOLVES: 'path.py::symbol'. A promotion may not name a hope."""
    if "::" not in home:
        return False
    rel, _, symbol = home.partition("::")
    path: Path = REPO / rel
    if not path.exists():
        return False
    src: str = path.read_text()
    return f"def {symbol}" in src or f"class {symbol}" in src or f"{symbol}:" in src


def symbol_literals(rel: str, symbol: str) -> set[str]:
    """The string CONSTANTS inside one declared FUNCTION - the vocabulary a policy may borrow must exist in its home.

    Why the FUNCTION and not the file: a token that appears only in a docstring or a comment is a mention, and a
    mention is not the rule (D-2662). Reading the function's own body is what makes "the tier vocabulary lives in
    the measure" a machine fact rather than a claim (C12/D-2642).

    Args:
        rel: repo-relative path of the home file.
        symbol: the function whose body declares the vocabulary.

    Returns:
        The set of string constants inside that function, empty when the file or the symbol does not resolve.
    """
    path: Path = REPO / rel
    if not path.exists():
        return set()
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            inner: set[str] = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    inner.add(sub.value)
            return inner
    return set()


def tier_faults(
    policy: dict[str, Any] | None,
    measure_tokens: set[str],
    home_ok: bool,
    accessor_ok: bool,
) -> list[str]:
    """PURE guard for the T-118 tier policy (the known-answer control surface for the granted owner word).

    Four things are checked, and each one is a way the owner's word could be silently UNJOINED: a policy that names a
    word the owner never granted; a grant with no signature (T-101: an unsigned decision is not a rule); a tier
    vocabulary that is a RIVAL DEFINITION rather than the measure's own (C12); and a rule with no statement of what
    it does with a single-source row.

    Args:
        policy: the declared `tier_policy` block, or None when it is missing.
        measure_tokens: the string constants inside the measure's own home function.
        home_ok: whether `vocabulary_home` resolves (file + symbol).
        accessor_ok: whether `accessor` resolves (file + symbol).

    Returns:
        One message per fault; empty when the word is joined.
    """
    if policy is None:
        return [
            "no `tier_policy` block: T-118 is GRANTED, so a declaration that omits it leaves the single-source policy"
            " undeclared while 6,247 of 7,640 rows carry one source work"
        ]
    faults: list[str] = []
    word: str = str(policy.get("word", "")).strip()
    if word not in TIER_WORDS:
        faults.append(f"tier word {word!r} is outside the declared dispositions {list(TIER_WORDS)}")
    if not str(policy.get("granted") or "").strip() or not str(policy.get("granted_by") or "").strip():
        faults.append("the tier word carries no grant (date + granted_by): an unsigned word is not a rule (T-101)")
    if not home_ok:
        faults.append(f"vocabulary_home {policy.get('vocabulary_home')!r} does not resolve (file + symbol)")
    if not accessor_ok:
        faults.append(f"accessor {policy.get('accessor')!r} does not resolve (file + symbol)")
    vocabulary: list[str] = [str(v) for v in (policy.get("vocabulary") or [])]
    if not vocabulary:
        faults.append("the tier vocabulary is empty: a tier that names no tier cannot be published")
    missing: list[str] = sorted(set(vocabulary) - measure_tokens)
    if missing:
        faults.append(
            f"tier token(s) {missing} appear NOWHERE in the measure's own home function - a tier defined in config is"
            " a RIVAL definition of the value it claims to read (C12/D-2642)"
        )
    if not str(policy.get("rule") or "").strip():
        faults.append("the tier policy states no rule about a single-source row")
    return faults


def module_tuple(rel: str, name: str) -> list[str]:
    """The string elements of a module-level tuple/list constant - the SHAPE a contract declares in CODE.

    Args:
        rel: repo-relative path of the module.
        name: the constant's name.

    Returns:
        Its string elements, or [] when the module or the constant does not resolve (the caller fails closed).
    """
    path: Path = REPO / rel
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and target.id == name and isinstance(value, (ast.Tuple, ast.List)):
            return [str(e.value) for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return []


def retired_faults(rows: list[dict[str, Any]], advertised: set[str]) -> list[str]:
    """PURE guard for the COMPLETED owner words (D-2993/D-2994): a retirement that did not LAND is a defect.

    Args:
        rows: the declaration's `retired` rows.
        advertised: the fields the declared surfaces still advertise.

    Returns:
        One message per fault; empty when every completed word is signed and has actually left the wire.
    """
    faults: list[str] = []
    for row in rows:
        field: str = str(row.get("field") or "").strip()
        if not field:
            faults.append("a `retired` row names no field")
            continue
        if not str(row.get("word") or "").strip():
            faults.append(f"{field}: retired with no word - a completed act must name its disposition")
        if not str(row.get("anchor") or "").strip():
            faults.append(f"{field}: the retiring word carries no anchor - an unsigned act is not an act (T-101)")
        if field in advertised:
            faults.append(
                f"{field}: declared RETIRED while {sorted(advertised)} still advertise it - the retirement did not"
                " land, so the field is still a live claim about the store"
            )
    return faults


def shape_faults(
    declaration: dict[str, Any],
    feedback_policy: dict[str, Any],
    tuple_keys: list[str],
    wire_keys: list[str],
) -> list[str]:
    """PURE guard for the WIRE SHAPES (D-2993/D-2994): the declared contract must EQUAL the builder that emits it.

    Args:
        declaration: config/served_fields.yaml.
        feedback_policy: config/feedback.yaml.
        tuple_keys: the keys the corroboration builder emits (read from its own module).
        wire_keys: the keys the feedback builder emits (read from its own module).

    Returns:
        One message per fault; empty when both contracts have one home, one builder and a resolvable consumer set.
    """
    faults: list[str] = []
    promo: dict[str, Any] = (declaration.get("promotions") or {}).get("corroboration") or {}
    declared_keys: list[str] = [str(k) for k in (promo.get("keys") or [])]
    if declared_keys != list(tuple_keys):
        faults.append(
            f"promotions.corroboration.keys {declared_keys} != the builder's own keys {list(tuple_keys)}"
            " (pipeline/corroboration.py::TUPLE_KEYS) - a contract restated in config is the BUG-499 class"
        )
    builder: str = str(promo.get("builder") or "")
    if not builder or not home_exists(builder):
        faults.append(f"promotions.corroboration.builder {builder!r} does not resolve (file + symbol)")
    for consumer in promo.get("consumers") or []:
        if not (REPO / str(consumer)).exists():
            faults.append(f"promotions.corroboration.consumers names {consumer!r}, which does not exist")
    wire_declared: list[str] = [str(k) for k in ((feedback_policy.get("wire") or {}).get("keys") or [])]
    if wire_declared != list(wire_keys):
        faults.append(
            f"config/feedback.yaml#wire.keys {wire_declared} != pipeline/feedback.py::WIRE_KEYS {list(wire_keys)}"
            " - the feedback contract must have ONE home"
        )
    return faults


def word_declared(word: str, vocabulary: set[str]) -> bool:
    """Whether an owner word is INSIDE the declared vocabulary (a `promote <field>` word matches its pattern).

    Fail-closed: the vocabulary is declarations, so `drop` and `keep-as-is` are refused BY NAME rather than guessed
    at (the T-101 lesson: a token that no reader accepts is not a token).

    Args:
        word: the declared word.
        vocabulary: the declared vocabulary.

    Returns:
        True when the word is declared.
    """
    if word in vocabulary:
        return True
    return word.startswith(PROMOTE_PREFIX) and any(v.startswith(PROMOTE_PREFIX) for v in vocabulary)


def verdict_for(state: dict[str, Any], vocabulary: set[str]) -> tuple[str, str]:
    """PURE verdict for ONE field - the known-answer control surface.

    state keys: field, surfaces (list of files advertising it), flags (register reasons), declared (owner-word row
    or None), acknowledged (source-owned row or None), home_ok (only consulted for a `promote <field>` word).

    Args:
        state: the field's measured + declared state.
        vocabulary: the declared owner-word vocabulary.

    Returns:
        (verdict, detail).
    """
    field: str = str(state["field"])
    surfaces: list[str] = list(state.get("surfaces") or [])
    flags: list[str] = list(state.get("flags") or [])
    declared: dict[str, Any] | None = state.get("declared")
    acknowledged: dict[str, Any] | None = state.get("acknowledged")
    if not surfaces:
        if declared is not None or acknowledged is not None:
            return DEFECT_STALE, (
                f"{field} carries a declaration but NO declared surface advertises it - an assertion whose subject"
                " is gone (BUG-488/D-405)"
            )
        return OK, f"{field}: not advertised by any declared surface"
    if not flags:
        return OK, f"{field}: advertised and no register flags it ({', '.join(surfaces)})"
    if declared is None:
        if acknowledged is not None:
            return ACKNOWLEDGED, (
                f"{field}: advertised by {', '.join(surfaces)} and flagged by {', '.join(flags)}, but the debt is"
                f" SOURCE-owned - {acknowledged.get('owned_by')} - so no owner word is owed"
            )
        return DEFECT_UNDECLARED, (
            f"{field} is ADVERTISED by {', '.join(surfaces)} and flagged by {', '.join(flags)}, but no disposition"
            " is declared - an agent is reading a value a register calls defective (BUG-511 family)"
        )
    word: str = str(declared.get("word", PENDING)).strip()
    if word != PENDING and not word_declared(word, vocabulary):
        return DEFECT_WORD, f"{field}: word {word!r} is outside the declared vocabulary {sorted(vocabulary)}"
    anchor: str = str(declared.get("anchor") or "").strip()
    if word != PENDING and not anchor:
        return DEFECT_ANCHOR, f"{field}: word {word!r} carries no anchor - an unsigned decision is not a rule (T-101)"
    if word.startswith(PROMOTE_PREFIX) and not state.get("home_ok", True):
        target: str = word[len(PROMOTE_PREFIX):].strip()
        return DEFECT_HOME, f"{field}: the promotion target {target!r} has no home that resolves"
    if word == PENDING:
        return OWNER_OWED, (
            f"{field}: advertised by {', '.join(surfaces)}, flagged by {', '.join(flags)}, and the OWNER WORD is"
            f" still pending ({declared.get('owed')})"
        )
    return OWNER_OWED, (
        f"{field}: word {word!r} is written, but the change-set has not landed - the field is still advertised by"
        f" {', '.join(surfaces)}"
    )


def controls() -> list[tuple[str, dict[str, Any], str]]:
    """The known-answer controls, one per named guard (a guardrail never seen failing is not a guardrail)."""
    return [
        ("advertised_and_healthy_is_ok",
         {"field": "confidence_score", "surfaces": ["mcp"], "flags": []}, OK),
        ("advertised_flagged_undeclared_is_a_defect",
         {"field": "borp_score", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"]}, DEFECT_UNDECLARED),
        ("a_declared_word_with_the_change_set_owed_is_owner_owed",
         {"field": "borp_score", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"],
          "declared": {"word": "retire", "anchor": "owner 2026-10-13", "owed": "T-107"}}, OWNER_OWED),
        ("a_pending_word_is_owner_owed_not_a_defect",
         {"field": "feedback_score", "surfaces": ["mcp"], "flags": ["derivations:declared_but_empty"],
          "declared": {"word": "pending", "anchor": "", "owed": "T-107"}}, OWNER_OWED),
        ("a_declaration_no_surface_advertises_is_stale",
         {"field": "ghost", "surfaces": [], "declared": {"word": "retire", "anchor": "x"}}, DEFECT_STALE),
        ("a_word_outside_the_vocabulary_is_refused",
         {"field": "borp_score", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"],
          "declared": {"word": "drop", "anchor": "x"}}, DEFECT_WORD),
        ("an_unsigned_word_is_refused",
         {"field": "borp_score", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"],
          "declared": {"word": "retire", "anchor": ""}}, DEFECT_ANCHOR),
        ("a_promotion_with_no_resolving_home_is_refused",
         {"field": "borp_score", "surfaces": ["mcp"], "flags": ["derivations:dead_but_read"], "home_ok": False,
          "declared": {"word": "promote corroboration", "anchor": "x"}}, DEFECT_HOME),
        ("a_source_owned_debt_acknowledged_is_not_a_defect",
         {"field": "jargon", "surfaces": ["okf"], "flags": ["store_columns:status=debt"],
          "acknowledged": {"owned_by": "config/store_columns.yaml#ceiling"}}, ACKNOWLEDGED),
        ("an_acknowledgement_no_surface_advertises_is_stale",
         {"field": "ghost", "surfaces": [], "acknowledged": {"owned_by": "config/store_columns.yaml#ceiling"}},
         DEFECT_STALE),
    ]


def tier_controls() -> list[tuple[str, dict[str, Any] | None, set[str], bool, bool, bool]]:
    """The T-118 known-answer controls: one per way a granted owner word can be UNJOINED (D-2990's guard list)."""
    healthy: dict[str, Any] = {
        "word": "tier",
        "vocabulary": ["weak", "medium", "strong"],
        "vocabulary_home": "pipeline/schema_accessor.py::isor_score",
        "accessor": "pipeline/schema_accessor.py::isor_rating",
        "granted": "2026-10-14",
        "granted_by": "owner",
        "rule": "every row publishes the tier it measured",
    }
    tokens: set[str] = {"weak", "medium", "strong", "No source books"}
    return [
        ("a_granted_tier_word_is_joined", healthy, tokens, True, True, False),
        ("a_tier_word_the_owner_never_granted_is_refused",
         {**healthy, "word": "withold"}, tokens, True, True, True),
        ("an_unsigned_tier_word_is_refused",
         {**healthy, "granted": ""}, tokens, True, True, True),
        ("a_tier_defined_in_config_is_a_rival_definition",
         {**healthy, "vocabulary": ["weak", "medium", "strong", "gold"]}, tokens, True, True, True),
        ("a_tier_home_that_does_not_resolve_is_refused", healthy, tokens, False, True, True),
        ("an_accessor_that_does_not_resolve_is_refused", healthy, tokens, True, False, True),
        ("a_missing_tier_policy_is_a_fault_and_not_a_silence", None, tokens, False, False, True),
    ]


def retired_controls() -> list[tuple[str, list[dict[str, Any]], set[str], bool]]:
    """The completed-word controls: one per way a retirement can be a LIE rather than an act (D-2994)."""
    signed: dict[str, Any] = {
        "field": "borp_score",
        "word": "retire",
        "anchor": "owner 2026-10-14",
        "granted": "2026-10-14",
    }
    return [
        ("a_signed_retirement_that_left_the_wire_is_joined", [signed], set(), False),
        ("a_retirement_still_advertised_is_a_defect", [signed], {"borp_score"}, True),
        ("an_unsigned_retirement_is_a_defect", [{**signed, "anchor": ""}], set(), True),
        ("a_retirement_with_no_word_is_a_defect", [{**signed, "word": ""}], set(), True),
    ]


def shape_controls() -> list[tuple[str, dict[str, Any], dict[str, Any], list[str], list[str], bool]]:
    """The wire-shape controls: a contract restated in config cannot be told from the builder (C12/D-2642)."""
    keys: list[str] = ["sources", "convergent", "independence", "independence_score", "home"]
    wire: list[str] = ["score", "count", "state", "prior", "effective"]
    healthy: dict[str, Any] = {
        "promotions": {
            "corroboration": {
                "keys": keys,
                "builder": "pipeline/corroboration.py::corroboration_tuple",
                "consumers": ["maxwell_mcp_server.py"],
            }
        }
    }
    policy: dict[str, Any] = {"wire": {"keys": wire}}
    return [
        ("a_declared_shape_equal_to_its_builder_is_joined", healthy, policy, keys, wire, False),
        ("a_shape_differing_from_the_builder_is_a_defect", healthy, policy, keys, [*wire, "extra"], True),
        ("a_shape_with_no_builder_is_a_defect",
         {"promotions": {"corroboration": {"keys": keys, "builder": "", "consumers": []}}}, policy, keys, wire, True),
    ]


def run_selftest() -> int:
    """Drive every known-answer control through the SAME classifier the verdict comes from."""
    declaration: dict[str, Any] = load_declaration()
    vocabulary: set[str] = set(declaration["owner_word"]["vocabulary"])
    bad: list[str] = []
    total: int = 0
    for label, state, expected in controls():
        total += 1
        got, detail = verdict_for(state, vocabulary)
        if got != expected:
            bad.append(f"{label}: expected {expected}, got {got} ({detail})")
    for label, policy, tokens, home_ok, accessor_ok, expected_fault in tier_controls():
        total += 1
        got_faults: list[str] = tier_faults(policy, tokens, home_ok, accessor_ok)
        if bool(got_faults) != expected_fault:
            bad.append(f"{label}: expected fault={expected_fault}, got {got_faults}")
    for label, rows, advertised, expected_fault in retired_controls():
        total += 1
        found: list[str] = retired_faults(rows, advertised)
        if bool(found) != expected_fault:
            bad.append(f"{label}: expected fault={expected_fault}, got {found}")
    for label, decl, pol, tkeys, wkeys, expected_fault in shape_controls():
        total += 1
        shaped: list[str] = shape_faults(decl, pol, tkeys, wkeys)
        if bool(shaped) != expected_fault:
            bad.append(f"{label}: expected fault={expected_fault}, got {shaped}")
    if bad:
        for line in bad:
            print(f"  !!  {line}")
        print(f"FAIL {PREFIX} selftest: {len(bad)} of {total} known-answer control(s) failed")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {total}/{total} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    """Join the surfaces to the registers and to the declared dispositions; print the debt and the owed words."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()

    declaration: dict[str, Any] = load_declaration()
    vocabulary: set[str] = set(declaration["owner_word"]["vocabulary"])
    columns: set[str] = columns_of_store()
    surfaces: dict[str, list[str]] = {}
    faults: list[str] = []
    for surface in declaration["surfaces"]:
        rel: str = str(surface["file"])
        try:
            for field in advertised_fields(rel, str(surface["kind"]), columns):
                surfaces.setdefault(field, []).append(rel)
        except (FileNotFoundError, ValueError) as exc:
            faults.append(f"{DEFECT_SURFACE}: {exc}")
    flags: dict[str, list[str]] = register_flags(declaration)
    declared: dict[str, dict[str, Any]] = {str(d["field"]): d for d in declaration.get("declared") or []}
    acknowledged: dict[str, dict[str, Any]] = {str(a["field"]): a for a in declaration.get("acknowledged") or []}
    promo_homes: dict[str, bool] = {
        name: home_exists(str(spec["home"])) for name, spec in (declaration.get("promotions") or {}).items()
    }
    #: T-118 - the granted tier word joins the MEASURE's own home: the vocabulary must be the one that function
    #: declares, so a tier that exists only in config is refused (C12/D-2642; the BUG-499/BUG-502 class).
    tier_policy: dict[str, Any] | None = declaration.get("tier_policy")
    tier_home: str = str((tier_policy or {}).get("vocabulary_home", ""))
    tier_accessor: str = str((tier_policy or {}).get("accessor", ""))
    measure_tokens: set[str] = set()
    if "::" in tier_home:
        home_file, _, home_symbol = tier_home.partition("::")
        measure_tokens = symbol_literals(home_file, home_symbol)
    tier_problems: list[str] = tier_faults(
        tier_policy, measure_tokens, home_exists(tier_home), home_exists(tier_accessor)
    )
    for problem in tier_problems:
        print(f"FAIL {PREFIX}: {DEFECT_TIER} - {problem}")
    faults += tier_problems
    #: D-2993/D-2994 - the COMPLETED words and the two WIRE SHAPES are joined to reality the same way the tier word
    #: is: a retirement that did not leave the wire, and a contract restated in config, are both DEFECTS.
    retired_problems: list[str] = retired_faults(list(declaration.get("retired") or []), set(surfaces))
    feedback_policy: dict[str, Any] = yaml.safe_load((REPO / "config" / "feedback.yaml").read_text()) or {}
    shape_problems: list[str] = shape_faults(
        declaration,
        feedback_policy,
        module_tuple("pipeline/corroboration.py", "TUPLE_KEYS"),
        module_tuple("pipeline/feedback.py", "WIRE_KEYS"),
    )
    for problem in retired_problems + shape_problems:
        print(f"FAIL {PREFIX}: {DEFECT_UNJOINED} - {problem}")
    faults += retired_problems + shape_problems

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    tally: dict[str, int] = {}
    notices: list[str] = []
    owed_lines: list[str] = []
    for field in sorted(set(surfaces) | set(declared) | set(acknowledged)):
        state = {
            "field": field,
            "surfaces": surfaces.get(field, []),
            "flags": flags.get(field, []),
            "declared": declared.get(field),
            "acknowledged": acknowledged.get(field),
        }
        word: str = str((declared.get(field) or {}).get("word", PENDING)).strip()
        if word.startswith(PROMOTE_PREFIX):
            state["home_ok"] = promo_homes.get(word[len(PROMOTE_PREFIX):].strip(), False)
        verdict, detail = verdict_for(state, vocabulary)
        tally[verdict] = tally.get(verdict, 0) + 1
        if verdict in DEFECTS:
            print(f"FAIL {PREFIX}: {verdict} - {detail}")
        elif verdict == OWNER_OWED:
            owed_lines.append(f"   owed: {detail}")
        elif verdict == ACKNOWLEDGED:
            owed_lines.append(f"   acknowledged: {detail}")
        if flags.get(field):
            rows, nonnull, distinct = con.execute(
                f"SELECT count(*), count({field}), count(DISTINCT {field}) FROM fbs"
                f" WHERE pipeline_run_id = ? AND status = 'PASS'",
                (CANONICAL_RUN,),
            ).fetchone()
            if nonnull == rows and distinct == 1:
                notices.append(
                    f"   note: {field} holds a CONSTANT on every served row ({nonnull}/{rows}, distinct {distinct})"
                    " - a false absence (D-2957); the shape defect is owned by config/store_columns.yaml"
                )
            elif nonnull == 0:
                notices.append(f"   note: {field} is NULL on every served row ({rows}) - the absence is TRUE (D-2957)")
    con.close()

    debt: int = tally.get(OWNER_OWED, 0)
    ceiling: int = int(declaration["coverage"]["max_declared_debt"])
    floor: int = int(declaration["coverage"]["min_declared_debt"])
    for line in owed_lines:
        print(line)
    for line in notices:
        print(line)
    defects: int = sum(tally.get(d, 0) for d in DEFECTS) + len(faults)
    if defects:
        print(f"FAIL {PREFIX}: {defects} defect(s) - an advertised field must be TRUE or DECLARED with an owed word")
        return EXIT_DEFECT
    if debt > ceiling:
        print(
            f"FAIL {PREFIX}: {DEFECT_CEILING} - {debt} declared-absent advertised field(s) exceed the ceiling"
            f" {ceiling}; the ceiling is SHRINK-ONLY (D-2644: the only act that may raise it is a DECISION)"
        )
        return EXIT_DEFECT
    print(
        f"ok {PREFIX}: {len(set(surfaces) | set(declared) | set(acknowledged))} field(s) joined -"
        f" {tally.get(OK, 0)} advertised-and-true, {tally.get(ACKNOWLEDGED, 0)} source-owned debt acknowledged,"
        f" {debt} declared-absent advertised (ceiling {ceiling}, floor {floor}), 0 undeclared, 0 stale"
    )
    print(f"   surfaces scanned: {', '.join(str(s['file']) for s in declaration['surfaces'])}")
    print("   the debt is the OWNER LANE's (T-107): the words are written in config/served_fields.yaml#declared")
    return EXIT_OWNER_OWED if debt > floor else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
