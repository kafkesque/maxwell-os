#!/usr/bin/env python3
"""check_model_claims.py — a model REFUSAL must resolve to an engine reading, never to a recollection.

WHY THIS EXISTS (2026-10-25, D-3151). The agent told the owner "Flint is not available in oMLX". The owner
answered with two repo names — `flint-OptiQ-4bit` and `flint mixed 3 4 bit` — and asked how future market
research would be enforced. BOTH names are real upstream. The research register R-14 had itself recorded the
opposite ("Both target runtimes EXIST", "a validated MLX conversion exists"), so the drift was in the SUMMARY,
not in the record: a register that is right cannot defend itself against a reader who does not read it.

MEASURED that day (governance/evidence/MODEL_AVAILABILITY_FLINT_20261025.json), four propositions ONE sentence
had fused: P1/P2 the repos EXIST upstream (TRUE), P3 their BYTES are on this box (FALSE — the hub entry holds
12 K of README), P4 this engine can SERVE them (FALSE — `ARCH_UNSUPPORTED`, model_type=flint absent from the
bundle's 134-architecture mlx_lm). Only P4 was ever measured, and it was spoken as if it were P1.

THE FIX IS NOT A PROMISE TO BE CAREFUL. `python3 pipeline/model_loadability_probe.py <org/name>` is TIER-A, needs
no download, runs in ~2 s and answers in the engine's own runtime. The honest read was CHEAPER than the
recollection, so what is enforced here is the RESOLUTION, not the honesty (D-3034):

  R1 a refusal's subject is a REPO ID (`org/name`, quoted exactly) — a bare name or a sentence declares nothing
  R2 `refused_by` RESOLVES to a decision in config/decisions.yaml or a row in the research register
  R3 a measured verdict's `probe.evidence` is a PATH that EXISTS and HOLDS that repo id (D-405: a citation whose
     subject is absent is an assertion)
  R4 the verdict is one the engine can actually emit (the vocabulary is DECLARED in config/engine.yaml, so this
     rail holds no literal — C12)
  R5 both availability AXES are stated (`exists_upstream`, `bytes_local`): the whole defect was fusing them
  R6 a refused repo may not also be `served_now` — a contradiction is a fault, not a preference
  R7 `verdict: NEVER` is OWNER-OWED, loud (rc=2): refused on judgement with no engine reading on file is a
     RECOLLECTION, and it is never a pass

Usage:
  python3 scripts/check_model_claims.py --check
  python3 scripts/check_model_claims.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "config" / "engine.yaml"
DECISIONS = ROOT / "config" / "decisions.yaml"
RESEARCH = ROOT / "governance" / "NOT-YET-EVALUATED-RESEARCH.md"
#: A model id is `org/name` — two path segments, no spaces. A sentence can never match this, which is the point
#: (D-3034: an entry whose value is a SENTENCE declares no bytes). This is LOGIC, not a tunable value (C12).
REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*/[A-Za-z0-9][A-Za-z0-9_.\-]*$")
DECISION_ID = re.compile(r"^D-\d{4}$")
RESEARCH_ID = re.compile(r"^R-\d{2}$")
ROW = re.compile(r"^\|\s*\*\*(R-\d{2})\*\*", re.M)

EXIT_CLEAN = 0
EXIT_FAULT = 1
EXIT_OWED = 2


def refused_block(config: dict) -> dict:
    """The declared refusal register, refused LOUDLY if absent or of the wrong SHAPE.

    An absent register would read as "nothing refused"; a register whose `entries` is a MAPPING would iterate its
    KEY STRINGS and a `verdicts` that is a string would iterate its CHARACTERS. Both shapes are refused here rather
    than reported member-by-member, because a rule read from the wrong container is not a stricter rule (C16).
    """
    block = ((config.get("candidates") or {}).get("refused")) or {}
    if not isinstance(block, dict) or not block.get("verdicts") or block.get("entries") is None:
        raise SystemExit("FAIL-CLOSED (model-claims): config/engine.yaml#candidates.refused must declare "
                         "`verdicts` and `entries` (C12/C16) — an absent register would read as 'nothing refused'")
    if not isinstance(block["verdicts"], list) or any(not isinstance(v, str) for v in block["verdicts"]):
        raise SystemExit("FAIL-CLOSED (model-claims): candidates.refused.verdicts must be a LIST of strings; got "
                         + type(block["verdicts"]).__name__ + " — a string here would be read one CHARACTER at a time")
    if not isinstance(block["entries"], list):
        raise SystemExit("FAIL-CLOSED (model-claims): candidates.refused.entries must be a LIST of mappings; got "
                         + type(block["entries"]).__name__ + " — a mapping here would iterate its KEY STRINGS")
    return block


def served_now(config: dict) -> set[str]:
    """The engine's own served list, as declared."""
    return {str(n) for n in ((config.get("candidates") or {}).get("served_now") or [])}


def decision_ids(path: Path = DECISIONS) -> set[str]:
    """Every decision id the decision register holds.

    The register is a MAPPING with a `decisions` list (BUG-419's class: a reader that assumes the wrong shape and
    returns an empty set makes every citation UNRESOLVED — a false RED, which D-3150 says is worse than an
    UNKNOWN). So an unexpected shape REFUSES loudly instead of reading as "the register is empty".
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("decisions") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise SystemExit("FAIL-CLOSED (model-claims): " + str(path) + " is not a decision register this reader"
                         " understands (expected {decisions: [...]} or a list); got " + type(data).__name__)
    found = {str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id")}
    if not found:
        raise SystemExit("FAIL-CLOSED (model-claims): " + str(path) + " yielded ZERO decision ids — an empty"
                         " register would read as 'every citation is wrong'")
    return found


def research_ids(path: Path = RESEARCH) -> set[str]:
    """Every `| **R-nn** |` verdict row id in the research register."""
    return {m.group(1) for m in ROW.finditer(path.read_text(encoding="utf-8"))}


def check_entry(entry: object, verdicts: list[str], decisions: set[str], research: set[str],
                served: set[str], root: Path, exists: Callable[[Path], bool],
                held: Callable[[Path, str], bool]) -> tuple[list[str], bool]:
    """Return (faults, owed) for ONE refusal entry."""
    if not isinstance(entry, dict):
        return ["ENTRY-NOT-A-MAP: " + repr(entry)[:80] + " — a refusal is a record, not a bare string"], False
    repo = str(entry.get("repo") or "")
    faults: list[str] = []
    if not REPO.match(repo):
        faults.append("NOT-A-REPO-ID: " + repr(repo)[:80] + " — a model id is `org/name` quoted exactly; a bare "
                      "name or a sentence declares nothing (D-3034)")
    by = str(entry.get("refused_by") or "")
    if DECISION_ID.match(by):
        if by not in decisions:
            faults.append("UNRESOLVED-REFUSED-BY: " + repo + " names " + by + " which is NOT in "
                          "config/decisions.yaml — a refusal citing a record that does not exist has no reason")
    elif RESEARCH_ID.match(by):
        if by not in research:
            faults.append("UNRESOLVED-REFUSED-BY: " + repo + " names " + by + " which has NO verdict row in "
                          "governance/NOT-YET-EVALUATED-RESEARCH.md")
    else:
        faults.append("NO-REFUSED-BY: " + repo + " names " + repr(by)[:40] + " — a refusal must resolve to D-nnnn "
                      "or R-nn (D-3038: what we reject we register, with its reason)")
    for axis in ("exists_upstream", "bytes_local"):
        if not isinstance(entry.get(axis), bool):
            faults.append("AXIS-MISSING: " + repo + " does not state `" + axis + "` as a boolean — the defect being "
                          "retired is the FUSING of existence with local bytes with servability")
    if repo and repo in served:
        faults.append("CONTRADICTION: " + repo + " is BOTH refused and candidates.served_now — the engine either "
                      "serves it or it is refused")
    probe = entry.get("probe") or {}
    if not isinstance(probe, dict):
        faults.append("PROBE-NOT-A-MAP: " + repo + " declares probe as " + repr(probe)[:40] + " — a verdict is a"
                      " mapping (verdict/evidence/date); a bare string carries no receipt and cannot resolve")
        return faults, False
    verdict = str(probe.get("verdict") or "")
    if not verdict:
        faults.append("NO-VERDICT: " + repo + " carries no probe.verdict (one of " + ", ".join(verdicts) + ")")
    elif verdict not in verdicts:
        faults.append("UNDECLARED-VERDICT: " + repo + " says " + repr(verdict) + " which is not in "
                      "config/engine.yaml#candidates.refused.verdicts")
    owed = False
    if verdict == "NEVER":
        owed = True
    elif verdict:
        evidence = probe.get("evidence")
        if not evidence:
            faults.append("NO-EVIDENCE: " + repo + " carries verdict " + verdict + " with `evidence: null` — a "
                          "measured verdict without a receipt is a recollection")
        else:
            path = root / str(evidence) if not str(evidence).startswith("/") else Path(str(evidence))
            try:
                if not exists(path):
                    faults.append("MISSING-EVIDENCE: " + repo + " cites " + str(evidence) + " which does not EXIST"
                                  " — a citation whose subject is absent is an assertion (D-405)")
                elif not held(path, repo):
                    faults.append("EVIDENCE-SILENT: " + str(evidence) + " does not name " + repo + " — a receipt"
                                  " that does not carry the subject it is cited for proves nothing about it")
            except OSError as exc:
                # An evidence file this rail cannot READ is a fault it must REPORT, never a traceback: a crash
                # exits 1 with a stack, which reads as a broken rail rather than as a bad receipt (C16/D-3150).
                faults.append("UNREADABLE-EVIDENCE: " + repo + " cites " + str(evidence) + " and the read failed ("
                              + type(exc).__name__ + ")")
        if not probe.get("date"):
            faults.append("NO-DATE: " + repo + " carries a verdict with no date — a reading with no date cannot "
                          "age, and evidence ages (D-3060)")
    return faults, owed


def scan(config: dict, decisions: set[str], research: set[str], root: Path = ROOT,
         exists: Callable[[Path], bool] = Path.exists,
         held: Callable[[Path, str], bool] = lambda p, r: r in p.read_text(encoding="utf-8", errors="replace")) -> tuple[list[str], list[str]]:
    """Return (faults, owner_owed_repo_ids) for the whole declared register."""
    block = refused_block(config)
    served = served_now(config)
    faults: list[str] = []
    owed: list[str] = []
    seen: dict[str, int] = {}
    for entry in block["entries"]:
        entry_faults, entry_owed = check_entry(entry, [str(v) for v in block["verdicts"]], decisions, research,
                                               served, root, exists, held)
        faults.extend(entry_faults)
        repo = str((entry or {}).get("repo") or "") if isinstance(entry, dict) else ""
        if repo:
            if repo in seen:
                faults.append("DUPLICATE: " + repo + " is registered twice — one refusal, one home (D-2646)")
            seen[repo] = 1
        if entry_owed and repo:
            owed.append(repo)
    return faults, owed


# --- the controls ---------------------------------------------------------------------------------------------

CONTROL_VERDICTS = ["LOADABLE_CANDIDATE", "ARCH_UNSUPPORTED", "NEVER"]
CONTROL_DECISIONS = {"D-3013"}
CONTROL_RESEARCH = {"R-14"}
CONTROL_SERVED: set[str] = {"gemma-4-E4B-it-MLX-4bit"}


def _entry(**over: object) -> dict:
    """A valid refusal entry, with any field overridden — the known-answer base for the controls."""
    base = {"repo": "mlx-community/flint-mixed-3-4bit", "refused_by": "R-14",
            "refused_because": "four measured blockers", "exists_upstream": True, "bytes_local": False,
            "probe": {"verdict": "ARCH_UNSUPPORTED", "evidence": "governance/evidence/X.json",
                      "date": "2026-10-25"}}
    base.update(over)
    return base


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls: each one MUST fire, in both directions (a control that cannot refuse is not one)."""
    def always(_p: Path) -> bool:
        """A path that always exists — the control's faked filesystem."""
        return True

    def holds(_p: Path, _r: str) -> bool:
        """A receipt that always names its subject — the control's faked evidence."""
        return True

    def ask(entry: object, exists: Callable[[Path], bool] = always,
            held: Callable[[Path, str], bool] = holds, served: set[str] = CONTROL_SERVED) -> tuple[list[str], bool]:
        """One entry through the rule, with the fakes a control needs."""
        return check_entry(entry, CONTROL_VERDICTS, CONTROL_DECISIONS, CONTROL_RESEARCH, served, ROOT, exists, held)

    def fires(**over: object) -> bool:
        return bool(ask(_entry(**over))[0])

    rows: list[tuple[str, bool]] = []
    rows.append(("a_valid_measured_refusal_PASSES", not ask(_entry())[0]))
    rows.append(("a_bare_name_is_NOT_a_repo_id", fires(repo="flint-mixed-3-4bit")))
    rows.append(("a_SENTENCE_is_NOT_a_repo_id", fires(repo="Flint is not available in oMLX")))
    rows.append(("a_refused_by_that_does_not_resolve_is_a_fault", fires(refused_by="R-99")))
    rows.append(("a_refused_by_decision_that_does_not_exist_is_a_fault", fires(refused_by="D-9999")))
    rows.append(("a_refused_by_that_is_neither_form_is_a_fault", fires(refused_by="because it overthinks")))
    rows.append(("a_missing_availability_axis_is_a_fault", fires(bytes_local=None)))
    rows.append(("a_missing_existence_axis_is_a_fault", fires(exists_upstream=None)))
    rows.append(("a_measured_verdict_with_null_evidence_is_a_fault",
                 fires(probe={"verdict": "ARCH_UNSUPPORTED", "evidence": None, "date": "2026-10-25"})))
    rows.append(("a_verdict_outside_the_declared_vocabulary_is_a_fault",
                 fires(probe={"verdict": "PROBABLY_FINE", "evidence": "governance/evidence/X.json",
                              "date": "2026-10-25"})))
    rows.append(("a_verdict_with_no_date_is_a_fault",
                 fires(probe={"verdict": "ARCH_UNSUPPORTED", "evidence": "governance/evidence/X.json"})))
    rows.append(("an_evidence_PATH_that_does_not_exist_is_a_fault",
                 bool(ask(_entry(), exists=lambda p: False)[0])))
    rows.append(("an_evidence_file_that_does_not_NAME_the_repo_is_a_fault",
                 bool(ask(_entry(), held=lambda p, r: False)[0])))
    rows.append(("a_refused_repo_that_is_ALSO_served_now_is_a_fault",
                 any("CONTRADICTION" in f for f in
                     ask(_entry(), served={"mlx-community/flint-mixed-3-4bit"})[0])))
    rows.append(("a_refused_repo_NOT_in_served_now_raises_no_contradiction",
                 not any("CONTRADICTION" in f for f in ask(_entry())[0])))
    never_faults, never_owed = ask(_entry(probe={"verdict": "NEVER", "evidence": None, "date": None}))
    rows.append(("verdict_NEVER_is_OWNER_OWED_not_a_pass", never_owed and not never_faults))
    rows.append(("an_entry_that_is_a_bare_string_is_a_fault", bool(ask("mlx-community/flint")[0])))
    rows.append(("a_probe_given_as_a_bare_string_is_a_FAULT_not_a_crash",
                 bool(ask(_entry(probe="ARCH_UNSUPPORTED"))[0])))
    rows.append(("an_UNREADABLE_evidence_file_is_a_REPORTED_fault_not_a_traceback",
                 any("UNREADABLE-EVIDENCE" in f for f in ask(
                     _entry(), exists=lambda p: True,
                     held=lambda p, r: (_ for _ in ()).throw(OSError("denied")))[0])))
    rows.append(("a_verdicts_STRING_is_REFUSED_rather_than_read_one_character_at_a_time",
                 _refuses(lambda: scan({"candidates": {"refused": {
                     "verdicts": "ARCH_UNSUPPORTED", "entries": []}}}, set(), set()))))
    rows.append(("an_entries_MAPPING_is_REFUSED_rather_than_iterating_its_key_strings",
                 _refuses(lambda: scan({"candidates": {"refused": {
                     "verdicts": ["ARCH_UNSUPPORTED"], "entries": {"a": "b"}}}}, set(), set()))))
    rows.append(("an_ABSENT_register_is_REFUSED_rather_than_read_as_nothing_refused",
                 _refuses(lambda: scan({"candidates": {}}, set(), set()))))
    rows.append(("the_LIVE_register_passes_its_own_rule", not scan(
        yaml.safe_load(ENGINE.read_text(encoding="utf-8")) or {}, decision_ids(), research_ids())[0]))
    return rows


def _refuses(fn: Callable[[], object]) -> bool:
    """True when fn REFUSES loudly. A fail-closed rule that cannot be SEEN to refuse is not a control (C16)."""
    try:
        fn()
    except SystemExit:
        return True
    return False


def main(argv: list[str]) -> int:
    """--check scans the declared refusal register; --selftest runs the known-answer controls."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        raise SystemExit("FAIL-CLOSED (model-claims): exactly ONE of --check | --selftest is required (C16)") from None
    if args.check == args.selftest:
        raise SystemExit("FAIL-CLOSED (model-claims): exactly ONE of --check | --selftest is required (C16)")
    if args.selftest:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [n for n, ok in rows if not ok]
        if failed:
            print("FAIL model-claims: " + str(len(failed)) + " of " + str(len(rows))
                  + " known-answer control(s) did not fire")
            return EXIT_FAULT
        print("ok model-claims: " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
        return EXIT_CLEAN
    config = yaml.safe_load(ENGINE.read_text(encoding="utf-8")) or {}
    faults, owed = scan(config, decision_ids(), research_ids())
    for fault in faults:
        print("  DRIFT " + fault)
    total = len((((config.get("candidates") or {}).get("refused") or {}).get("entries")) or [])
    if faults:
        print("FAIL model-claims: " + str(len(faults)) + " fault(s) over " + str(total) + " declared refusal(s)")
        return EXIT_FAULT
    if owed:
        print("OWED model-claims: " + str(total) + " declared refusal(s) | " + str(len(owed))
              + " refused on JUDGEMENT with no engine reading on file: " + ", ".join(owed)
              + " — one command settles each: python3 pipeline/model_loadability_probe.py <org/name>")
        return EXIT_OWED
    print("ok model-claims: " + str(total) + " declared refusal(s), every verdict resolves to an engine reading")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
