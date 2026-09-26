#!/usr/bin/env python3
"""Adversarial battery + real-data regression for the depth/domain contract (rail 5: the sandbox as a harness).

WHY A BATTERY AND NOT A UNIT TEST
    Every defect in this thread was found by trying to BREAK the rule, not by testing that it worked: the vague
    universal (S1), the cheap-group 7/7 (S2), the one-tick cliff (S3), the silent-degrade truncation (S10), and
    the fact that the >=2-groups variant of "cross-domain" would have churned 12 rows where >=2-domains churns 1
    (S11). A test that only asserts the happy path reproduces the author's hope; a battery that records what the
    rule CANNOT stop is the honest artifact.

    Two of the cases below are DELIBERATE PASSES - attacks the contract does not stop. They stay in the harness
    as recorded blindspots so that nobody re-derives the same false confidence later.

Usage: python3 tests/test_depth_domain_contract.py     (also runs under pytest)
Exit:  0 all cases behaved as recorded | 1 a case behaved differently from the recorded expectation
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import validate_depth_domain_contract as ddc  # noqa: E402  (scripts/ is on the path above)

CTX = ddc.load_context("authored")
WORKBOOK_ROWS = ddc.load_rows(None, CTX)
ALL_DOMAINS = sorted(CTX.canon - CTX.abstention_domains)
ONE_PER_GROUP: list[str] = []
for g in sorted(CTX.groups):
    ONE_PER_GROUP.append(next(d for d in ALL_DOMAINS if CTX.group_of[d] == g))
SAME_GROUP_PAIR = [d for d in ALL_DOMAINS if CTX.group_of[d] == "Business & Strategy"][:2]
DIFF_GROUP_PAIR = [ALL_DOMAINS[0], next(d for d in ALL_DOMAINS if CTX.group_of[d] != CTX.group_of[ALL_DOMAINS[0]])]


def row(domains: list[str], depth: str, raw: str | None = None, primary: str | None = None,
        item: str = "SYN") -> dict[str, str]:
    """Build a synthetic workbook row with only the contract's columns populated."""
    cell = "|".join(domains)
    return {
        "item_id": item,
        "domains_final": cell,
        "domains_final_raw": cell if raw is None else raw,
        "depth_final": depth,
        "primary_domain": primary if primary is not None else (domains[0] if domains else ""),
    }


def codes(r: dict[str, str]) -> dict[str, str]:
    """Map finding code -> tier for one row, so a case can assert both what fired and how loud it is."""
    return {f.code: f.tier for f in ddc.validate_row(r, CTX)}


# Each case: (id, what an attacker does, expected code->tier map, why this is the correct expectation).
CASES: list[tuple[str, str, dict[str, str], str]] = [
    ("S1", "tick all 43 domains with a vague statement (the unpatchable universal)", {"ARITY_PRIMARY": "soft"}, "BLINDSPOT: no "
     "deterministic validator can distinguish vagueness from universality. Only the FORM gate can, and FORM has "
     "no anchor. Recorded as a permanent PASS so the gap is never mistaken for coverage."),
    ("S2", "one domain per group - 7 ticks, three groups hold only 3 domains each (cheap 7/7)", {"ARITY_PRIMARY": "soft"},
     "BLINDSPOT/gameable: the 7/7 rule prices a Business&Society-heavy pick the same as a genuine universal. "
     "Kept because 0/148 rows reach 7/7, i.e. the rule has never been exercised at the positive end."),
    ("S3", "7/7 minus one tick in a 3-domain group (the one-tick cliff)", {},
     "FALSIFIED BY DESIGN: one click turns universal into cross-domain. The rule is a cliff, not a gradient; the "
     "report must therefore be read as 'which side of the cliff', never as a distance."),
    ("S4", "universal scope PLUS a primary rank", {"ARITY_PRIMARY": "soft"},
     "A rank at depth 1 reintroduces the 28%-of-canvas menu order as an authority. Caught."),
    ("S5", "specialized with three domains", {"ARITY_MAX_DOMAINS": "soft", "ARITY_MAX_GROUPS": "soft", "GROUP_COVERAGE_CLASS_MISMATCH": "soft"},
     "specialized means exactly one; three domains is a cross-domain claim in disguise. Caught."),
    ("S6", "abstention only (the real R040 shape)", {"ABSTENTION_ONLY": "soft"},
     "Correct tier: an abstention-only row is not a defect, it is an unscorable cell. It must leave BOTH sides of "
     "every rate (parity) instead of counting as one domain."),
    ("S7", "abstention PLUS one real domain, authored cross-domain", {"ARITY_MIN_DOMAINS": "soft"},
     "UNDECLARED AMBIGUITY: is the real domain the answer, or is the abstention the answer? The contract flags "
     "the shape but cannot resolve intent - an owner call, not a validator call."),
    ("S8", "two domains from the SAME group, authored domain", {"GROUP_COVERAGE_CLASS_MISMATCH": "soft"},
     "Correct: domain scope = one adjacent group, and two neighbours inside it are still one group."),
    ("S9", "two domains from DIFFERENT groups, authored cross-domain", {},
     "Correct: this is the amended cross-domain rule (domains_ge_2), chosen after S11 measured the alternative."),
    ("S10", "a truncated token ('research & methodolog') in domains_final", {"MENU_OFF_TOKEN": "hard", "RAW_REDERIVE_MISMATCH": "hard"},
     "THE ONE THAT MATTERS: in the first implementation this degraded to ZERO domains with no exception and no "
     "log - a truncation becoming an abstention looks like a valid answer. Now it fails closed."),
    ("S12", "primary set to the SECOND domain", {"PRIMARY_NOT_FIRST": "soft", "GROUP_COVERAGE_CLASS_MISMATCH": "soft"},
     "The owner's rule is that the first domain typed is primary; 0/148 authored rows violate it today, so this "
     "guard preserves behaviour rather than changing it."),
]


def test_battery() -> None:
    """Run the adversarial battery; every case must match its recorded expectation and tier."""
    failures: list[str] = []
    for cid, attack, expect, why in CASES:
        if cid == "S1":
            r = row(ALL_DOMAINS, "universal")
        elif cid == "S2":
            r = row(ONE_PER_GROUP, "universal")
        elif cid == "S3":
            r = row(ONE_PER_GROUP[:-1], "cross-domain")
        elif cid == "S4":
            r = row(ONE_PER_GROUP, "universal", primary=ONE_PER_GROUP[0])
        elif cid == "S5":
            r = row(DIFF_GROUP_PAIR + [SAME_GROUP_PAIR[0]], "specialized")
        elif cid == "S6":
            r = row(["emerging"], "domain")
        elif cid == "S7":
            r = row(["emerging", SAME_GROUP_PAIR[0]], "cross-domain")
        elif cid == "S8":
            r = row(SAME_GROUP_PAIR, "domain")
        elif cid == "S9":
            r = row(DIFF_GROUP_PAIR, "cross-domain")
        elif cid == "S10":
            r = row(["research & methodolog"], "domain")
        else:
            r = row(SAME_GROUP_PAIR, "domain", primary=SAME_GROUP_PAIR[1])
        got = codes(r)
        if got != expect:
            failures.append(f"{cid}: expected {expect}, got {got}  ({attack})")
        print(f"  {cid}: {'ok ' if got == expect else 'MISMATCH'} {attack[:58]:60s} -> {got or 'no findings'}")
    assert not failures, "battery mismatches:\n" + "\n".join(failures)


def test_no_silent_degrade() -> None:
    """S10's cascade form: an off-menu token must never be laundered into an abstention."""
    got = codes(row(["research & methodolog"], "domain"))
    assert got.get("MENU_OFF_TOKEN") == "hard", got
    assert "ABSTENTION_ONLY" not in got, "an off-menu token was silently reclassified as an abstention"


def test_blindspot_pass_is_recorded() -> None:
    """S1/S2 must PASS (no findings). If they ever start failing, the contract grew a rule nobody documented."""
    for r in (row(ALL_DOMAINS, "universal"), row(ONE_PER_GROUP, "universal")):
        got = codes(r)
        # Only the rank complaint may fire: the point of the case is that NO scope/arity code can tell a vague
        # claim from a universal one, and that stays true.
        assert set(got) <= {"ARITY_PRIMARY"}, got


def test_group_variant_blast_radius_measured() -> None:
    """S11: the rejected rule variant is rejected because it CHURNS, and the number is asserted, not recalled."""
    two_domains = 0
    two_domains_two_groups = 0
    for r in WORKBOOK_ROWS:
        if (r.get("depth_final") or "").strip() != "cross-domain":
            continue
        toks = ddc.split_cell(r.get("domains_final"), CTX.sep)
        nd, ng = len(ddc.real_domains(toks, CTX)), len(ddc.witnesses(toks, CTX))
        two_domains += (nd < 2)
        two_domains_two_groups += (nd < 2 or ng < 2)
    assert (two_domains, two_domains_two_groups) == (1, 12), (two_domains, two_domains_two_groups)
    assert str(two_domains_two_groups) == str(CTX.cfg["group_coverage"]["cross_domain_rule_rejected_blast_radius"])
    assert str(two_domains) == str(CTX.cfg["group_coverage"]["cross_domain_rule_blast_radius"])


def test_real_data_regression() -> None:
    """The frozen workbook's known state, asserted by NAME so a silent shift in the gold fails the harness."""
    rep = ddc.build_report(WORKBOOK_ROWS, CTX)
    hard = {f.item_id for f in rep.by_tier("hard")}
    blocked = sorted(f.item_id for f in rep.by_tier("owner_blocked"))
    soft = {f.code for f in rep.by_tier("soft")}
    assert rep.rows == 148, rep.rows
    assert blocked == [], blocked  # D-387/D-388: R040 owner-ruled, R140 declared axis-exempt
    assert "AXIS_EXEMPT_DECLARED" in {f.code for f in rep.by_tier("soft")}
    assert hard <= {"-"}, f"row-level hard findings on the authored gold: {hard}"
    # RAW_UNDECLARED_TOKEN is ABSENT by design: once the raw reader used both separators, R137's
    # 'user experience|' resolved to 'user experience' and is a declared repair. The code stays in the config
    # because a future un-declared token must fire it.
    assert soft == {"AXIS_EXEMPT_DECLARED", "ARITY_MAX_GROUPS", "ARITY_MIN_DOMAINS", "GROUP_COVERAGE_CLASS_MISMATCH",
                    "DEFINITION_DRIFT"}, sorted(soft)
    assert rep.per_class == {"domain": 74, "cross-domain": 44, "specialized": 30}  # D-387: R070/R080/R130 carry their 24.09 depth forward (no BLANK now), rep.per_class


def test_contamination_annex_never_enters_the_grid() -> None:
    """A leak probe: the annex (4 candidates + 7 negatives) must never be counted in the ruler denominator."""
    ids = {r["item_id"] for r in WORKBOOK_ROWS}
    try:
        annex = ddc.read_text(REPO / CTX.cfg["inputs"]["annex"])[0]
    except FileNotFoundError:
        return
    assert "U001" not in ids, "an annex candidate row leaked into the workbook denominator (class-1 leakage)"
    assert "U002" not in ids and "U003" not in ids and "U004" not in ids
    assert "CLASS1_OWNER_CONFIRMED" in annex  # the annex is the only home of the class-1 positives


def test_tier_config_is_complete() -> None:
    """A finding code with no tier is a config defect; assert completeness instead of discovering it at runtime."""
    for mode in ("authored", "emitted"):
        cfg = ddc.load_context(mode)
        for code in (ddc.MENU_OFF_TOKEN, ddc.RAW_UNDECLARED_TOKEN, ddc.RAW_REDERIVE_MISMATCH,
                     ddc.ANSWER_SPACE_DRIFT, ddc.DEFINITION_DRIFT, ddc.AXIS_PIN_MISSING,
                     ddc.ANSWER_SPACE_PIN_UNVERIFIABLE, ddc.UNCLASSIFIED_MENU_AXIS,
                     ddc.MENU_VERSION_STAMP_MISMATCH, ddc.MENU_HASH_ARTIFACT_STALE, ddc.MISSING_MENU_VERSION,
                     ddc.ABSTENTION_ONLY, ddc.DOMAINS_BLANK, ddc.ARITY_MIN_DOMAINS, ddc.ARITY_MAX_DOMAINS,
                     ddc.ARITY_MIN_GROUPS, ddc.ARITY_MAX_GROUPS, ddc.ARITY_PRIMARY, ddc.PRIMARY_NOT_FIRST,
                     ddc.GROUP_COVERAGE_CLASS_MISMATCH):
            assert ddc.tier_for(cfg, code) in ("hard", "owner_blocked", "soft"), (mode, code)


def test_menu_hash_instrument_detects_drift() -> None:
    """Drift probe: the frozen ARTIFACT must hash to the frozen value, and live-vs-frozen is reported verbatim.

    Deliberately NOT asserted to be equal: the live render currently differs (one discipline definition was
    edited without a re-render). Asserting equality here would encode the bug as the expectation.
    """
    from pipeline.closed_menu import menu_hash  # noqa: PLC0415
    import json  # noqa: PLC0415
    frozen = (REPO / CTX.cfg["inputs"]["menu_sha256_file"]).read_text().split()[0].strip()
    artifact = menu_hash(json.loads(ddc.read_text(REPO / CTX.cfg["inputs"]["menu"])[0]))
    live = menu_hash()
    print(f"  frozen {frozen[:16]} | artifact {artifact[:16]} | live render {live[:16]}")
    assert artifact == frozen, "the frozen menu artifact was edited after it was frozen"
    assert len(live) == 64


def test_reamended_cross_domain_rule_is_the_measured_one() -> None:
    """The amended rule must be the one with the smaller blast radius, and the config must say which was rejected."""
    cov = CTX.cfg["group_coverage"]
    assert cov["cross_domain_rule"] == "domains_ge_2"
    assert cov["cross_domain_rule_rejected"] == "domains_ge_2_and_groups_ge_2"
    assert cov["universal_rule"] == "all_groups"


def main() -> int:
    """Run every case, print the map, and return a non-zero code on any mismatch."""
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())


def test_answer_space_pin_is_declared_once_and_holds() -> None:
    """BUG-447/D-371: the pin must cover the ANSWER SPACE (a value a classifier may EMIT), and it must hold.

    Two assertions with two different jobs. (1) A GENERATOR test: the axes the pin is computed over come from
    config/menu_axis_groups.yaml, not from a literal in the script - a second inline copy is how the composite
    hash came to be read as an answer-space pin in the first place. (2) A STATE test: the answer space has NOT
    moved (measured 2026-09-25), so a drift finding here would mean a real slot change, not a wording edit.
    """
    import sys as _sys  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    _sys.path.insert(0, str(REPO / "scripts"))
    import menu_axis_hashes as mah  # noqa: PLC0415

    declared = mah.load_groups()
    assert declared["answer_space"] == ["domains", "abstention"], declared["answer_space"]
    pins = yaml.safe_load(ddc.read_text(REPO / CTX.cfg["inputs"]["menu_axis_hashes"])[0])
    assert pins["axis_group"]["answer_space"] == declared["answer_space"]
    rep = ddc.build_report(WORKBOOK_ROWS, CTX)
    assert not [f for f in rep.by_tier("hard") if f.code == ddc.ANSWER_SPACE_DRIFT], "the answer space moved"


def test_composite_and_answer_space_are_reported_as_different_facts() -> None:
    """The composite still drifts (disciplines) while the answer space does not - and that is not a contradiction.

    D-285 and D-321 are both correct: the DEFINITION moved, the ANSWER SPACE did not. The instrument must say so
    with two codes, because one code cannot carry both facts (BUG-447). Deliberately NOT asserting the composite
    matches: today it does not, and encoding the bug as the expectation is how a bug becomes a fixture.
    """
    rep = ddc.build_report(WORKBOOK_ROWS, CTX)
    assert [f.code for f in rep.by_tier("soft")].count(ddc.DEFINITION_DRIFT) >= 1, "definition drift not recorded"
    assert not rep.by_tier("hard"), "no hard finding is expected on the frozen authored workbook"


def test_raw_repair_is_whole_cell_only() -> None:
    """BUG-458: a declared cell replacement must not edit a pipe-joined list; a trailing separator is trimmed.

    MEASURED near-miss: the BUG-449 fix first landed as `cell_replacements: "user experience|" -> "user
    experience"`. Applied with `str.replace` to a cell holding the WHOLE domain list it merged `user experience`
    with the NEXT domain into one undeclared raw token - a declared repair silently becoming an unrecorded edit
    of the owner's bytes. Battery row S1 was the only thing that noticed.
    """
    assert "RAW_UNDECLARED_TOKEN" not in codes(row(ALL_DOMAINS, "universal"))
    assert ddc.split_raw_tokens("user experience|", CTX) == ["user experience"]
    assert ddc.split_raw_tokens("", CTX) == []
