"""D-2982 contract for the config-default census INSTRUMENT.

Paired 1:1 with specs/config_defaults_census.spec.md (D-2978: one governed surface, one spec, one contract).
The machine runner is the grader; the spec is the definition, not a report. Every INV in the spec names the
test that decides it, and test_the_spec_is_paired_1to1_with_its_contract enforces that pairing.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAIL = PROJECT_ROOT / "scripts" / "check_config_defaults.py"
REGISTRY = PROJECT_ROOT / "config" / "derivations.yaml"
RECEIPT = PROJECT_ROOT / "config" / "config_defaults_census.json"
SPEC = PROJECT_ROOT / "specs" / "config_defaults_census.spec.md"
JUSTFILE = PROJECT_ROOT / "justfile"

# The twelve keys PAID by D-2982: they may not return as shadowed-declared SITEs (INV-8).
PAID_KEYS = {
    "commit_scope", "dedup_gate", "growth_edge_output", "process_instance_output",
    "process_template_output", "quarantine_output", "require_both", "s5_owned_columns", "serving",
    "symmetric_relationship_types", "taxonomy_dependent_columns", "tool_instruction_output",
}


def _rail():
    """The rail under test, loaded from its path (it is a script, not an installed module)."""
    spec = importlib.util.spec_from_file_location("census_under_test", RAIL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _declared():
    """The declared half: receivers, glob, roots and the declared coverage fingerprint."""
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    reads = registry["config_reads"]
    return reads, {str(r) for r in reads["receivers"]}, str(reads["config_glob"]), \
        [str(r) for r in registry["scan_roots"]]


def _measure(module):
    """Measure the tree exactly as the rail does (one definition, used by the invariant tests)."""
    _reads, receivers, config_glob, roots = _declared()
    keys = module.declared_keys(config_glob)
    shadowed, undeclared, sites, files, _locations = module.scan(receivers, keys, roots, aliases=True)
    return shadowed, undeclared, sites, files


def test_the_spec_is_paired_1to1_with_its_contract():
    """D-2978: every invariant in the spec names the test that decides it, and every named test exists."""
    spec_text = SPEC.read_text(encoding="utf-8")
    named = re.findall(r"\*\*Test:\*\*\s*`([a-z0-9_]+)`", spec_text)
    invariants = re.findall(r"(?m)^### (INV-\d+)", spec_text)
    assert invariants, "the spec declares no invariants"
    assert len(named) == len(invariants), (
        f"{len(invariants)} invariant(s) but {len(named)} named test(s): an invariant without a test is a claim.")
    defined = set(re.findall(r"(?m)^def (test_[a-z0-9_]+)\(", Path(__file__).read_text(encoding="utf-8")))
    missing = [n for n in named if n not in defined]
    assert not missing, f"the spec names test(s) that do not exist here: {missing}"


def test_the_idiom_cannot_express_a_default():
    """INV-1: the loud-read helper exposes no way to supply a value for an absent key."""
    module = _rail()
    import pipeline.pipeline_paths as pp  # the ONE home of the idiom (D-2982)

    assert module is not None
    for fn in (pp.required, pp.required_mapping, pp.required_sequence):
        params = set(inspect.signature(fn).parameters)
        assert not (params & {"default", "fallback", "if_missing"}), f"{fn.__name__} can express a default"
    assert issubclass(pp.MissingDeclaredKey, KeyError), "callers that catch KeyError must keep failing closed"
    with pytest.raises(pp.MissingDeclaredKey):
        pp.required({}, "absent", where="config/x.yaml")


def test_a_missing_declared_value_names_the_remedy():
    """INV-2: the error names the walked path, the home, and the instruction to declare it."""
    import pipeline.pipeline_paths as pp

    with pytest.raises(pp.MissingDeclaredKey) as excinfo:
        pp.required({"stage6": {}}, "stage6", "commit_scope", where="config/pipeline_config.yaml")
    message = str(excinfo.value)
    assert "stage6.commit_scope" in message
    assert "config/pipeline_config.yaml" in message
    assert "DECLARE" in message.upper()


def test_the_instrument_declares_its_coverage():
    """INV-3: the declared fingerprint equals the fingerprint of the declared coverage (BUG-758)."""
    module = _rail()
    reads, receivers, config_glob, roots = _declared()
    declared = str(reads.get("coverage_fingerprint") or "").strip()
    computed = module.fingerprint(module.coverage_of(receivers, config_glob, roots))
    assert declared, ("config_reads.coverage_fingerprint is not declared - a measurement with no stated "
                      "coverage cannot be compared to anything (run --rebaseline --because <D-id>)")
    assert declared == computed, (
        f"the declared coverage {declared} does not describe the coverage in force {computed}: a count taken "
        "under one instrument must never be compared to a ceiling taken under another (D-2982)")


def test_alias_rule_resolves_both_directions():
    """INV-4: a block alias is seen; a reused local, a non-config binding and a shadow are not (BUG-758)."""
    module = _rail()
    receivers = {"_CFG"}
    keys = {"alpha", "beta"}
    assert module.census('_S = _CFG.get("alpha", {})\n_S.get("beta", 2)', receivers, keys) == (
        {"alpha", "beta"}, set(), 2), "a name bound once to a config block must resolve as an alias"
    assert module.census('_S = _CFG.get("alpha", {})\n_S = other()\n_S.get("beta", 2)', receivers, keys) == (
        {"alpha"}, set(), 1), "a rebound local must NOT be counted as debt"
    assert module.census('_S = other.load()\n_S.get("beta", 2)', receivers, keys) == (
        set(), set(), 0), "a non-config local must NOT be counted as debt"
    assert module.census('_S = _load_yaml(PATH)\n_S.get("beta", 2)', receivers, keys) == (
        set(), set(), 0), "a loader call must not resolve as a config alias"
    failed = [name for name, ok in module.controls() if not ok]
    assert not failed, f"known-answer control(s) stopped firing: {failed}"


def test_the_receipt_equals_the_measurement():
    """INV-5: the receipt is the baseline - its counts AND its key set equal the live measurement."""
    module = _rail()
    assert RECEIPT.exists(), ("config/config_defaults_census.json does not exist: the debt is a SET (D-2982), "
                              "so run the rail (--rebaseline --because <D-id>) to record it")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    shadowed, undeclared, sites, files = _measure(module)
    assert receipt["counts"]["shadowed_declared"] == len(shadowed)
    assert receipt["counts"]["undeclared"] == len(undeclared)
    assert receipt["counts"]["sites"] == sites
    assert receipt["counts"]["modules"] == files
    assert set(receipt["keys"]["shadowed_declared"]) == shadowed, (
        "the receipt's KEY SET differs from the measurement - the debt changed, and a count alone would have "
        "hidden it (BUG-758)")


def test_a_raise_needs_a_decision_that_exists(tmp_path, monkeypatch, capsys):
    """INV-6: no route can raise a ceiling without citing a decision that is already in the registry.

    The licence is only EXERCISABLE in a mismatched-coverage state (once the fingerprint matches, an uncited
    --rebaseline is a no-op, not a raise). So the test builds that state in a TEMP registry and drives the
    rail in-process: a refusal must happen BEFORE any write, and the temp registry must be left untouched -
    a contract that mutates a protected registry to prove a point is not a contract.
    """
    module = _rail()
    raw = REGISTRY.read_text(encoding="utf-8")
    stale_text, substituted = re.subn(r"(?m)^  coverage_fingerprint: .*$",
                                      "  coverage_fingerprint: 0000000000000000", raw, count=1)
    assert substituted == 1, "the declared fingerprint line must be findable for this test to mean anything"
    stale = tmp_path / "derivations.yaml"
    stale.write_text(stale_text, encoding="utf-8")
    monkeypatch.setattr(module, "REGISTRY", stale)

    assert module.main(["--rebaseline"]) == module.EXIT_DRIFT, "an uncited raise must be refused"
    assert "--because" in capsys.readouterr().out

    assert module.main(["--rebaseline", "--because", "D-99999"]) == module.EXIT_DRIFT
    assert "not an id in config/decisions.yaml" in capsys.readouterr().out

    # The CITED act itself was performed once, in the tree, and its consequence is on disk: the ledger line
    # names the decision that justified the wider instrument. Re-running it here would need a write outside
    # the audited tree, which write_guard refuses by design (BUG-560: a temp pre-image is evidence of
    # nothing). So the contract asserts the RECORD of the act, not a re-enactment of it.
    ledger = str(yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["config_reads"]["ceiling_changed"])
    assert "COVERAGE CHANGE" in ledger and "cited D-2982" in ledger, (
        "the ledger carries no cited COVERAGE CHANGE line: a raise that is not attributable is the defect "
        "D-2982 exists to stop")

    source = RAIL.read_text(encoding="utf-8")
    assert source.count("record_rebaseline(") == 2, "exactly one definition and one call site may exist"


def test_the_delta_is_attributed_two_ways():
    """INV-7: coverage growth and code growth are separated by RE-MEASURING under the previous coverage."""
    module = _rail()
    _reads, receivers, config_glob, roots = _declared()
    shadowed, _undeclared, _sites, _files = _measure(module)
    coverage = module.coverage_of(receivers, config_glob, roots)

    same = {"coverage": dict(coverage, fingerprint="x"), "keys": {"shadowed_declared": sorted(shadowed)}}
    split = module.attribute_delta(shadowed, same, module.declared_keys(config_glob), roots)
    assert split["new"] == [] and split["visible"] == [] and split["paid"] == []

    one_paid = sorted(shadowed)[0]
    thinner = {"coverage": dict(coverage, fingerprint="x"),
               "keys": {"shadowed_declared": [k for k in sorted(shadowed) if k != one_paid]}}
    split = module.attribute_delta(shadowed, thinner, module.declared_keys(config_glob), roots)
    assert split["new"] == [one_paid], "a key the receipt never saw is NEW code debt, not coverage"
    assert split["visible"] == []

    narrower = {"coverage": {"receivers": [], "aliases": False, "fingerprint": "old"},
                "keys": {"shadowed_declared": []}}
    split = module.attribute_delta(shadowed, narrower, module.declared_keys(config_glob), roots)
    assert split["visible"] == sorted(shadowed), "a wider instrument must report the keys as VISIBLE"
    assert split["new"] == [], "a wider instrument must not report coverage as code debt"

    no_receipt = module.attribute_delta(shadowed, {}, module.declared_keys(config_glob), roots)
    assert no_receipt == {"previous": "", "visible": [], "new": [], "paid": []}


def test_the_paid_keys_stay_paid():
    """INV-8: the twelve keys D-2982 paid may not return as shadowed-declared sites."""
    module = _rail()
    shadowed, _undeclared, _sites, _files = _measure(module)
    returned = sorted(PAID_KEYS & shadowed)
    assert not returned, (
        f"key(s) that D-2982 removed have a code default again: {returned} - read them loudly "
        "(pipeline/pipeline_paths.required), do not restore the second home (C16/D-2644)")


def test_the_ladder_runs_both_halves():
    """INV-9: the health recipe runs the controls AND the check, so a blind detector is itself detected."""
    justfile = JUSTFILE.read_text(encoding="utf-8")
    assert "scripts/check_config_defaults.py --selftest" in justfile
    assert "scripts/check_config_defaults.py --check" in justfile
