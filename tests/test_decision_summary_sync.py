"""Guard against drift in the derived census of config/decisions.yaml (D-2655).

`total_decisions`, the per-state and per-category counts and the content stamp are REDUNDANT DERIVED DATA:
they must equal values computed from the `decisions` list. Since D-2655 they live in
config/decisions_summary.json (the census) and NOT in the registry, because the registry is append_only with a
PREFIX receipt rule while every one of them changes on every mint (BUG-539).

This module independently recomputes the counts (deliberately NOT importing the sync script, so it acts as a
second oracle) and fails if they drift. The STATE vocabulary and the list of forbidden keys, by contrast, are
READ from their one home - the writer's own declaration - by AST, never copied: MEASURED 2026-09-26, a
hand-copied 12-item vocabulary here silently mismatched the writer's 14-item one, so this oracle failed for a
reason that had nothing to do with the census - and that failure was misread as proof that a DIFFERENT control
worked. A copy of a rule is a second declaration of one fact (D-2646): read it, do not restate it.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISIONS_YAML = ROOT / "config" / "decisions.yaml"
CENSUS_JSON = ROOT / "config" / "decisions_summary.json"
WRITER = ROOT / "scripts" / "recompute_decision_summary.py"

_DECL_CACHE: dict[str, list[str]] = {}


def _declared(name: str) -> list[str]:
    """Read a module-level literal declaration from the WRITER's own source - never a copy (D-2646).

    Fails closed when the declaration cannot be read: an oracle that cannot find the rule must not fall back to
    an empty vocabulary, which would compare a census against nothing and pass.
    """
    if name in _DECL_CACHE:
        return _DECL_CACHE[name]
    tree = ast.parse(WRITER.read_text(encoding="utf-8"))
    for node in tree.body:
        target: str | None = None
        if isinstance(node, ast.AnnAssign):
            target = getattr(node.target, "id", None)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = getattr(node.targets[0], "id", None)
        if target == name:
            _DECL_CACHE[name] = [str(v) for v in ast.literal_eval(node.value)]
            return _DECL_CACHE[name]
    raise AssertionError(
        f"{WRITER.name} declares no module-level {name!r} - this oracle reads the vocabulary from the writer "
        "rather than restating it (D-2646); if the declaration moved, point this at its new home"
    )


def _states() -> list[str]:
    return _declared("STATES")


def _load() -> dict:
    assert DECISIONS_YAML.exists(), f"missing {DECISIONS_YAML}"
    return yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}


def _census() -> dict:
    """The census, from its own home. ABSENT is a DEFECT, never an empty census (BUG-487)."""
    rel = CENSUS_JSON.relative_to(ROOT).as_posix()
    assert CENSUS_JSON.exists(), (
        f"missing {rel} - the registry's derived census has no home on disk (BUG-487). "
        "Run: python3 scripts/recompute_decision_summary.py"
    )
    return json.loads(CENSUS_JSON.read_text(encoding="utf-8"))


def _canonical_state(record: dict) -> str:
    """Fail closed: a record with no canonical `state:` key must not be defaulted to ACTIVE (BUG-483).

    The oracle must NOT share the producer's blind spot: copying `or "ACTIVE"` here would have made this
    test certify a wrong census instead of catching it (BUG-467 class - self-certifying evidence).
    """
    raw = record.get("state")
    assert raw is not None and str(raw).strip(), (
        f"decision {record.get('id')!r} carries no canonical 'state:' key - normalise it in "
        f"config/decisions.yaml (BUG-483)"
    )
    state = str(raw).strip().upper()
    assert state in _states(), f"decision {record.get('id')!r} state {raw!r} is not in {_states()} (BUG-483)"
    return state


def _recompute(data: dict) -> tuple[int, dict]:
    decisions = data.get("decisions") or []
    total = len(decisions)

    state_counts: dict[str, int] = {s.lower(): 0 for s in _states()}
    category_counts: dict[str, int] = {}
    for d in decisions:
        lk = _canonical_state(d).lower()
        state_counts[lk] = state_counts.get(lk, 0) + 1
        category = d.get("category")
        assert str(category or "").strip(), (
            f"decision {d.get('id')!r} carries no 'category' - it would be silently filed under GOV, so the "
            f"by_category census would be wrong (BUG-483)"
        )
        category_counts[str(category)] = category_counts.get(str(category), 0) + 1

    summary = {
        "total": total,
        **state_counts,
        "by_category": dict(sorted(category_counts.items())),
    }
    return total, summary


def _digest(decisions: list) -> str:
    """A SECOND implementation of the content stamp, on purpose (BUG-402).

    The producer's own canonicalisation is not evidence that its stamp is right - and this is the value the
    one-shot strip asserted unmoved, so it is re-derived here rather than taken on the producer's word.
    """
    payload = json.dumps(decisions, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def test_decision_ids_are_unique_under_one_namespace() -> None:
    """C21: one token, one namespace. `D-331` and `D331` are the same token (BUG-483)."""
    decisions = _load().get("decisions") or []
    seen: dict[str, int] = {}
    for d in decisions:
        key = str(d.get("id") or "").strip().replace("D-", "D").upper()
        seen[key] = seen.get(key, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    assert not dupes, f"duplicate decision id(s) under one normalised token: {dupes}"


def test_registry_carries_no_derived_field() -> None:
    """D-2655: the ABSENCE of the derived fields from the registry IS the contract.

    An independent oracle for the writer's registry_shape_problems(). If one of these keys comes back, the next
    mint would have to move bytes inside the receipted region of an append_only artifact (BUG-539). The remedy
    is NOT to normalise the field: the only sanctioned write to this file is --mint, an APPEND.
    """
    data = _load()
    back = sorted(k for k in _declared("REGISTRY_DERIVED_KEYS") if k in data)
    assert not back, (
        f"config/decisions.yaml carries derived key(s) {back} - it is append_only with a PREFIX receipt and "
        "those values change on every mint (D-2655/BUG-539). Take them out again: "
        "python3 scripts/recompute_decision_summary.py --strip-derived-head"
    )


def test_census_total_matches_decision_count() -> None:
    census = _census()
    total, _ = _recompute(_load())
    assert census.get("total_decisions") == total, (
        f"census.total_decisions={census.get('total_decisions')!r} but len(decisions)={total}. "
        "Run: python3 scripts/recompute_decision_summary.py"
    )


def test_census_counts_match_recomputed_counts() -> None:
    census = _census()
    total, expected = _recompute(_load())
    declared = census.get("summary") or {}

    assert declared.get("total") == total, (
        f"census.summary.total={declared.get('total')!r} != {total}. "
        "Run: python3 scripts/recompute_decision_summary.py"
    )

    extra = sorted(set(declared) - set(expected))
    assert not extra, (
        f"census.summary carries key(s) {extra} the writer's declared vocabulary does not derive - a counted "
        "state with no vocabulary entry (or a vocabulary this oracle cannot see) is a count nobody can explain"
    )

    for key in _states():
        lk = key.lower()
        assert declared.get(lk) == expected.get(lk), (
            f"census.summary.{lk}={declared.get(lk)!r} != {expected.get(lk)!r}. "
            "Run: python3 scripts/recompute_decision_summary.py"
        )

    declared_cats = declared.get("by_category") or {}
    assert declared_cats == expected.get("by_category"), (
        "census.summary.by_category drift:\n"
        f"  declared-only: {set(declared_cats) - set(expected.get('by_category', {}))}\n"
        f"  expected-only: {set(expected.get('by_category', {})) - set(declared_cats)}\n"
        "  run: python3 scripts/recompute_decision_summary.py"
    )


def test_census_artifact_describes_the_registry_bytes() -> None:
    """D-2655: the census is a SECOND home for the same counts, so something must PROVE they agree (D-2646).

    Otherwise the extraction would have replaced one drift with two. This oracle reads the census from its own
    home and re-derives the registry independently (it still does NOT import the writer), so a hand-edit of
    either side is caught. `source_sha256` pins the exact registry BYTES the document describes (D-382), and the
    content stamp is re-derived here rather than trusted.
    """
    rel = CENSUS_JSON.relative_to(ROOT).as_posix()
    census = _census()
    decisions = (_load().get("decisions")) or []
    total, expected = _recompute(_load())
    assert census.get("total_decisions") == total, (
        f"{rel}.total_decisions={census.get('total_decisions')!r} != {total} - run "
        "python3 scripts/recompute_decision_summary.py"
    )
    assert census.get("summary") == expected, f"{rel}.summary does not re-derive from the records"
    assert census.get("source_sha256") == hashlib.sha256(DECISIONS_YAML.read_bytes()).hexdigest(), (
        f"{rel}.source_sha256 does not match the registry ON DISK - the census describes other bytes (D-382)"
    )
    assert census.get("decisions_sha256_16") == _digest(decisions), (
        f"{rel}.decisions_sha256_16 does not re-derive from the records - a stamp is a proof, not a claim "
        "(BUG-402)"
    )
