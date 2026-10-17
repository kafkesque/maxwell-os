#!/usr/bin/env python3
"""check_ingest_identity_gate.py — the INGEST DOOR, read as a rail (D-2997 / BUG-781).

WHAT IT IS. The enforcement point the identity machinery never had (see pipeline/ingest_gate.py for the
measured why). It composes what already exists — the two detectors' reports (D-2736/D-2737), the ONE owner
ledger (D-2738), T-129's collapse sheet, and `book_metadata`'s identity + sanitizer (D2176/D2449) — and answers
two questions the corpus could not answer before:

  `--check`      (just health) the STANDING debt: how many pairs wait for an owner word, whether the ledger is
                 STALE against the detector (a candidate the ledger never saw), whether the content screen is
                 older than the corpus, and how much name noise the corpus carries. TRI-STATE, BUG-457:
                 0 clean | 1 FATAL (machine-decidable: unreadable input, undeclared verdict, stale ledger or
                 report — the door would be blind) | 2 OWNER-OWED (a pair with no word; a name defect whose fix
                 is a write). rc 2 is loud and NOT fatal here; a class DECLARED as accepted debt is printed and
                 counted in the same reading but is not an rc 2 trigger (T-130 option B), and since T-173/D-3043
                 the marker class is accepted too — the reading names, PER CLASS, what it is, how many, the row
                 it names and the owner word that accepted it (one class, one line, DERIVED from the report).
  `--gate`       (ingest step, pre-S1.5) the DOOR's reading of the SAME facts. rc 2 here REFUSES the run: a run
                 that proceeded would mint the claim (corroboration by two VOICES) that the unresolved identity
                 makes false. The difference is DECLARED in config (`door.ingest_reading`), never accidental:
                 the same number means two things by declaration, which is why the health line and this line are
                 both declared in config/rail_registry.yaml.
  `--preflight`  P1: the delta-scoped per-candidate decision (defer/admit) + the deferral RECEIPT.
  `--selftest`   known-answer controls; a control nothing runs is a comment (BUG-492).

Exit codes: 0 clean; 1 FATAL/unreadable input; 2 owner-owed (loud; at the door: REFUSED); --selftest 0/1.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline import ingest_gate as gate  # noqa: E402

CONTROL_LABELS = (
    "a_noise_suffixed_candidate_is_deferred_on_the_identity_its_canonical_lookup_resolves",
    "a_candidate_with_a_new_identity_is_admitted",
    "a_byte_identical_candidate_is_deferred_under_a_new_name",
    "an_already_cached_file_is_not_a_candidate_at_all",
    "an_undeclared_ledger_verdict_is_fatal_not_owner_owed",
    "a_missing_content_report_is_fatal_not_clean",
    "a_content_candidate_absent_from_the_ledger_is_fatal",
    "a_ruled_collapse_row_is_not_counted_as_owed",
    "a_word_with_no_provenance_is_owed_not_ruled",
    "a_whitespace_defective_name_resolves_by_the_declared_canonical_lookup",
    "an_exact_name_match_is_preferred_over_the_canonical_fallback",
    "a_variant_name_stays_a_candidate_and_is_deferred_when_its_record_is_found_only_canonically",
    "a_defect_class_with_no_declared_disposition_is_fatal_not_silently_accepted",
    "an_accepted_debt_with_no_named_owner_word_is_fatal",
    "a_record_without_author_or_title_still_defers_on_its_sanitized_stem",
    "an_accepted_class_is_counted_printed_and_not_an_rc_2_trigger",
    "an_accepted_class_without_its_own_word_is_fatal",
    "a_same_as_pointer_that_does_not_resolve_is_not_an_acceptance",
    "an_accepted_debt_declaration_for_a_class_that_is_not_accepted_is_a_fault",
    "every_citation_an_acceptance_makes_resolves",
    "a_stale_content_screen_is_owed_in_the_reading_and_fatal_at_the_door",
)


TASKS = Path("config/task_register.yaml")
DECISIONS = Path("config/decisions.yaml")


def _debt_reading(rep: dict[str, Any]) -> list[str]:
    """The name-class reading, DERIVED from the report: every counted class with its disposition, its count and —
    when the class is ACCEPTED — the owner word that accepted it and the row that word names.

    WHY DERIVED AND NOT WRITTEN HERE (T-173/D-3043): this line used to say "ingest-site markers 459 (OWNER-OWED,
    T-173)" as a LITERAL. The moment the register said something else (the owner accepted the class) the reading
    would have kept printing OWNER-OWED — a reader disagreeing with the register is exactly the drift D-3034
    exists to catch. Nothing is invented here and nothing is omitted: every counted class is printed, whether it
    is accepted, owed or clean.
    """
    dispositions = rep["defect_dispositions"]
    counts = dict(rep["name_defects"])
    counts[gate.MARKER_CLASS] = rep["marker_names"]
    accepted = rep["accepted_debt"]
    lines: list[str] = []
    for name in sorted(counts):
        token = dispositions.get(name, "<undeclared>")
        if accepted["classes"].get(name):
            word = accepted["words"].get(name, "")
            row = accepted["rows"].get(name, "") or "no row"
            short = (word[:64] + "...") if len(word) > 64 else word
            lines.append(f"  name class {name}: {counts[name]} — {token} ({row}) owner word: {short}")
        else:
            lines.append(f"  name class {name}: {counts[name]} — {token}")
    lines.append(f"  accepted as DECLARED DEBT: {accepted['classes']} (total {accepted['total']}), "
                 f"never an rc 2 trigger; declared by {accepted['declared_by']}")
    return lines


def _unresolved_citations(policy: dict[str, Any], tasks: Path = TASKS, decisions: Path = DECISIONS) -> list[str]:
    """Every citation an accepted-debt declaration makes must RESOLVE (D-3034): its row, and its decisions.

    A declaration that NAMES a row and a decision declares that those exist; a citation that resolves to nothing
    is a claim with no owner (the D-3034 class, and the fault scripts/check_agent_surface.py catches on the
    adapter surface). The check lives in the READER and not in the door: the door's job is identity, and a second
    home for the registers would be exactly the drift this rail exists to prevent (C12). A register that cannot be
    READ is FATAL, never silently empty (C16).
    """
    import yaml

    def _ids(path: Path, key: str) -> set[str]:
        if not path.exists():
            raise gate.GateInputError(f"FATAL: {path} does not exist, so its citations cannot resolve (C16)")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        rows = doc.get(key) if isinstance(doc, dict) else doc
        if not isinstance(rows, list):
            raise gate.GateInputError(f"FATAL: {path} carries no list under {key!r} (C16)")
        return {str(r["id"]) for r in rows if isinstance(r, dict) and r.get("id")}

    row_ids = _ids(tasks, "tasks")
    decision_ids = _ids(decisions, "decisions")
    raw = (policy["identity"].get("accepted_debt") or {}).get("declarations") or {}
    faults: list[str] = []
    for name, decl in sorted(raw.items()):
        if not isinstance(decl, dict) or decl.get("same_as"):
            continue  # a pointer is checked at the entry that carries the word (and a cycle is a fault there)
        row = str(decl.get("row") or "").strip()
        if row and row not in row_ids:
            faults.append(f"{name}: the row it names does not exist in {tasks}: {row}")
        for cited in decl.get("declared_by") or []:
            if str(cited) not in decision_ids:
                faults.append(f"{name}: the decision it names does not exist in {decisions}: {cited}")
    return faults


def _report(rep: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Print the standing debt in the units the owner acts on (no counts invented, none omitted)."""
    ledger, collapse, content = rep["ledger"], rep["collapse"], rep["content"]
    print(f"corpus files: {rep['corpus_files']} | candidates (delta): {rep['candidates']}", file=stream)
    print(f"owner ledger {ledger['file']}: {ledger['pairs']} pair(s) | open {ledger['open']} | closed {ledger['closed']}",
          file=stream)
    if not collapse["missing"]:
        print(f"collapse sheet {collapse['file']}: {collapse['rows']} row(s) | ruled {collapse['ruled']} | owed {collapse['outstanding']}",
              file=stream)
    print(f"content report {content['file']}: {content['candidates']} candidate(s) | stale {content['stale']}", file=stream)
    for line in _debt_reading(rep):
        print(line, file=stream)
    for line in rep["fatal"]:
        print(f"FATAL: {line}", file=stream)
    for line in rep["owner_owed"]:
        print(f"OWNER-OWED: {line}", file=stream)


def _run_check(as_json: bool) -> int:
    """`--check`: the standing census (health reading)."""
    try:
        citations = _unresolved_citations(gate.load_policy())
    except gate.GateInputError as exc:
        print(str(exc), file=sys.stderr)
        return gate.RC_FATAL
    for line in citations:
        print(f"FATAL: an accepted-debt citation does not resolve: {line}", file=sys.stderr)
    if citations:
        return gate.RC_FATAL
    try:
        rep = gate.standing()
    except gate.GateInputError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return gate.RC_FATAL
    if as_json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        _report(rep)
    return int(rep["rc"])


def _run_preflight(run_id: str, as_json: bool) -> int:
    """`--preflight`: P1 per-candidate decision + the deferral receipt (writes runtime state only)."""
    try:
        rep = gate.preflight(run_id=run_id)
    except gate.GateInputError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return gate.RC_FATAL
    if as_json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"candidates: {rep['candidates']} | admitted {rep['admitted']} | deferred {len(rep['deferrals'])} "
              f"| action {rep['action']} | receipt {rep['receipt']}")
        for item in rep["deferrals"]:
            print(f"  DEFERRED [{item['defer_reason']}] {item['name']} -> collides with {item['matched']} "
                  f"(canonical name: {item['canonical_name']})")
    return int(rep["rc_owner_owed"])


def _run_gate(as_json: bool) -> int:
    """`--gate`: the DOOR's reading. rc 2 REFUSES; rc 1 means the door cannot see (blind)."""
    try:
        citations = _unresolved_citations(gate.load_policy())
    except gate.GateInputError as exc:
        print(str(exc), file=sys.stderr)
        return gate.RC_FATAL
    for line in citations:
        print(f"FATAL: an accepted-debt citation does not resolve: {line}", file=sys.stderr)
    if citations:
        return gate.RC_FATAL
    try:
        rep = gate.standing(mode="door")  # D-3085/BUG-916: the door DECLARES which caller it is
        delta = gate.preflight(write_receipt=False)
    except gate.GateInputError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return gate.RC_FATAL
    if as_json:
        print(json.dumps({"standing": rep, "preflight": delta}, indent=2, ensure_ascii=False))
        return int(rep["rc"])
    _report(rep)
    print(f"delta: {delta['candidates']} candidate(s), {len(delta['deferrals'])} deferred", file=sys.stdout)
    for item in delta["deferrals"]:
        print(f"  DEFERRED [{item['defer_reason']}] {item['name']} -> collides with {item['matched']}", file=sys.stdout)
    if rep["rc"] == gate.RC_FATAL:
        print("REFUSED: the door is blind (see FATAL above) - no ingest, no certification (C16)", file=sys.stderr)
        return gate.RC_FATAL
    if rep["rc"] == gate.RC_OWNER_OWED:
        print("REFUSED at the door: identity is unresolved, so a run would mint a corroboration claim its own "
              "evidence contradicts (task T-129/T-131). The owner words ARE the release.", file=sys.stderr)
        return gate.RC_OWNER_OWED
    print("door open: no unresolved identity, no stale screen", file=sys.stdout)
    return gate.RC_CLEAN


def _selftest() -> int:
    """Known-answer controls over a SYNTHETIC corpus in a temp dir (no repo fixture, BUG-577)."""
    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        """Record a failed control by its published label (a control nothing runs is a comment, BUG-492)."""
        failures.append((label, detail))
    with tempfile.TemporaryDirectory(prefix="ingest_gate_") as tmp:
        root = Path(tmp)
        books, cache_dir = root / "books", root / "ckpt"
        books.mkdir()
        cache_dir.mkdir()
        (books / "Alpha Book.md").write_text("alpha body " * 50, encoding="utf-8")
        (books / "Beta Book.md").write_text("beta body " * 50, encoding="utf-8")
        cache = cache_dir / "book_metadata.jsonl"
        cache.write_text("\n".join(json.dumps(rec) for rec in (
            {"source_book": "Alpha Book.md", "author": "Jane Roe", "title": "Alpha Book",
             "source_path": str(books / "Alpha Book.md")},
            {"source_book": "Beta Book.md", "author": "John Doe", "title": "Beta Book",
             "source_path": str(books / "Beta Book.md")},
        )) + "\n", encoding="utf-8")
        policy = deepcopy(gate.load_policy())
        policy["door"]["deferral_dir"] = str(root / "deferrals")
        ledger_path, collapse_path, content_path = root / "ledger.json", root / "sheet.csv", root / "content.json"
        policy["ledger"]["file"], policy["ledger"]["collapse_sheet"] = str(ledger_path), str(collapse_path)
        policy["content"]["report"] = str(content_path)

        # C1/C2: a noise-suffixed candidate collapses to its corpus stem; a new identity is admitted.
        noise = books / "Alpha Book (z-library.sk, 1lib.sk, z-lib.sk).md"
        noise.write_text("alpha body " * 50, encoding="utf-8")
        (books / "Gamma Notes.md").write_text("gamma body " * 50, encoding="utf-8")
        rep = gate.preflight(books_dir=books, cache_path=cache, policy=policy, run_id="c1")
        by_name = {d["name"]: d for d in rep["decisions"]}
        # T-130 option B / BUG-799: the refusal is now grounded in the IDENTITY the canonical lookup resolves
        # (that fixture record carries author|title), not in the stem the two names happen to share. The pre-B
        # reading fell through to the stem only because the exact-bytes lookup could not find the record at all:
        # the reason got STRONGER, and control 15 below proves the stem path is still alive without author|title.
        reason_zero = by_name.get(noise.name, {}).get("defer_reason")
        if reason_zero != "same_work_identity":
            mark(CONTROL_LABELS[0],
                 f"noise-suffixed candidate deferred as {reason_zero!r}, expected same_work_identity")
        if not by_name.get("Gamma Notes.md", {}).get("admitted"):
            mark(CONTROL_LABELS[1], "a candidate with a new identity was NOT admitted")

        # C3: byte-identical under a NEW name is deferred by hash (size+digest), not by name.
        twin = books / "Totally Different Title.md"
        twin.write_bytes((books / "Beta Book.md").read_bytes())
        rep = gate.preflight(books_dir=books, cache_path=cache, policy=policy, run_id="c3")
        reasons = {d["name"]: d["defer_reason"] for d in rep["decisions"]}
        if reasons.get(twin.name) != "byte_identical":
            mark(CONTROL_LABELS[2], f"byte-identical twin reason was {reasons.get(twin.name)!r}")

        # C4: the DELTA RULE — the cached corpus files are never candidates (no cascade possible).
        if {"Alpha Book.md", "Beta Book.md"} & {d["name"] for d in rep["decisions"]}:
            mark(CONTROL_LABELS[3], "an already-cached file was treated as a candidate (cascade rule broken)")

        # C5: an UNDECLARED verdict is machine-decidable: fatal class, never an owner question.
        ledger_path.write_text(json.dumps({"pairs": [{"pair_id": "p1", "verdict": "MAYBE"}]}), encoding="utf-8")
        debt = gate.ledger_debt(policy)
        if debt["undeclared_verdicts"] != ["p1"]:
            mark(CONTROL_LABELS[4], "an undeclared ledger verdict was not reported")

        # C6: a MISSING content report is FATAL, never "clean" (a blind door admits anything).
        try:
            gate.content_debt(policy, corpus=[])
            mark(CONTROL_LABELS[5], "a missing content report did NOT raise (blind door admitted)")
        except gate.GateInputError:
            pass

        # C7: a detector pair the ledger never saw is FATAL (the ledger is stale). Keys, not ids: the two
        # surfaces carry DIFFERENT id namespaces (measured 2026-10-14) and the pair key is the only join.
        if gate.uncovered_candidates([gate.pair_key("a", "b"), gate.pair_key("c", "d")], {gate.pair_key("b", "a")}) \
                != [gate.pair_key("c", "d")]:
            mark(CONTROL_LABELS[6], "an uncovered content candidate was not reported as stale-ledger")
        if gate.uncovered_candidates([gate.pair_key("a", "b")], {gate.pair_key("b", "a")}):
            mark(CONTROL_LABELS[6], "a covered candidate was wrongly reported (pair key is not order-free)")

        # C8: an owner word ENDS the debt for that row; a blank row stays owed.
        collapse_path.write_text("group,work_a,work_b,owner_ruling,ruling_source\n"
                                 "1,a,b,CONFIRM-ONE-WORK,signature:A@2026-10-14\n2,c,d,,\n", encoding="utf-8")
        collapse = gate.collapse_debt(policy)
        if (collapse["ruled"], collapse["outstanding"]) != (1, 1):
            mark(CONTROL_LABELS[7], f"collapse debt was {collapse['ruled']}/{collapse['outstanding']}, expected 1/1")

        # C9 (BUG-786, MEASURED 2026-10-14): a WORD IN THE DERIVED COLUMN IS NOT AN OWNER ACT. The live sheet carried
        # a word in all 84 rows with `ruling_source = none` (typed by hand into the column `--apply` writes) and this
        # reader counted them as ruled. Without provenance the row stays OWED - and the reading must say so.
        collapse_path.write_text("group,work_a,work_b,owner_ruling,ruling_source\n"
                                 "1,a,b,CONFIRM-ONE-WORK,none\n2,c,d,CONFIRM-ONE-WORK,\n", encoding="utf-8")
        unprovenanced = gate.collapse_debt(policy)
        if (unprovenanced["ruled"], unprovenanced["unprovenanced"], unprovenanced["outstanding"]) != (0, 2, 2):
            mark(CONTROL_LABELS[8],
                 f"provenance-less words were {unprovenanced['ruled']} ruled / "
                 f"{unprovenanced['unprovenanced']} unprovenanced, expected 0 ruled / 2 unprovenanced")
        # ... and the SAME rows WITH provenance ARE ruled, so the control cannot pass by refusing every word.
        collapse_path.write_text("group,work_a,work_b,owner_ruling,ruling_source\n"
                                 "1,a,b,CONFIRM-ONE-WORK,none\n2,c,d,CONFIRM-ONE-WORK,row\n", encoding="utf-8")
        mixed = gate.collapse_debt(policy)
        if (mixed["ruled"], mixed["outstanding"]) != (1, 1):
            mark(CONTROL_LABELS[8],
                 f"a provenance-carrying word was not ruled ({mixed['ruled']}/{mixed['outstanding']}, expected 1/1)")

        # ── T-130 OPTION (B) / BUG-799: THE DECLARED CANONICAL LOOKUP AND THE CASCADE RULE THAT MUST USE IT ──
        # The fixture is the live defect's exact shape: the CACHE names one work with a repeated internal space
        # while the corpus file carries the clean name. Before B the door declared such a name defective and
        # then resolved its record by those same defective bytes, so the DECISION could not see the identity the
        # door's own key already collapses. The delta rule is deliberately NOT the place that fixes it (BUG-848):
        # a file the cache cannot name by exact bytes stays a CANDIDATE and is then deferred on identity.
        with cache.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"source_book": "Epsilon  Book.md", "author": "Ann Lee",
                                     "title": "Epsilon Book",
                                     "source_path": str(books / "Epsilon  Book.md")}) + "\n")
            handle.write(json.dumps({"source_book": "Delta Book.md", "author": "Bo Reid",
                                     "title": "Delta Book",
                                     "source_path": str(books / "Delta Book.md")}) + "\n")
            handle.write(json.dumps({"source_book": "Delta  Book.md", "author": "Bo Reid",
                                     "title": "Delta Book",
                                     "source_path": str(books / "Delta  Book.md")}) + "\n")
        (books / "Epsilon Book.md").write_text("epsilon body " * 50, encoding="utf-8")
        (books / "Delta Book.md").write_text("delta body " * 50, encoding="utf-8")
        (books / "Zeta Book.md").write_text("zeta body " * 50, encoding="utf-8")
        corpus = gate.corpus_files(books_dir=books)
        census = gate.corpus_census(corpus, gate.cache_records(cache), policy)

        # C10: the canonical fallback RESOLVES a whitespace-defective name, and SAYS that it did (evidence).
        record, method = census["resolve"](books / "Epsilon Book.md")
        if not record or method != "canonical_name":
            mark(CONTROL_LABELS[9],
                 f"a whitespace-defective name resolved as {method!r} (expected canonical_name)")

        # C11: an EXACT match still WINS — the fallback may not quietly overrule the declared order.
        record2, method2 = census["resolve"](books / "Delta Book.md")
        if method2 != "exact_name" or not record2 or record2["source_book"] != "Delta Book.md":
            mark(CONTROL_LABELS[10],
                 f"an exact name match lost to the fallback ({method2!r}, "
                 f"{record2 and record2.get('source_book')!r})")

        # C12 (BUG-848): CANDIDACY IS VISIBILITY. A variant the cache does not name by EXACT bytes stays a
        # candidate — it must be DECIDED, because stage0 converts the corpus minus the deferrals — and the
        # canonical lookup is what turns it into a RECORDED, identity-grounded deferral rather than an
        # invisible file that would be converted a second time.
        delta_names = {path.name for path in gate.candidates(corpus, census, policy)}
        if "Epsilon Book.md" not in delta_names:
            mark(CONTROL_LABELS[11],
                 f"a whitespace variant was silently absorbed by the delta rule: {sorted(delta_names)}")
        variant = {d["name"]: d for d in gate.preflight(books_dir=books, cache_path=cache, policy=policy,
                                                        run_id="c12", write_receipt=False)["decisions"]}
        epsilon = variant.get("Epsilon Book.md") or {}
        if epsilon.get("admitted") or epsilon.get("defer_reason") != gate.REASON_ALREADY_INGESTED:
            mark(CONTROL_LABELS[11],
                 f"a file whose record is found ONLY canonically was not deferred: {epsilon!r}")
        if epsilon.get("record_resolution") != "canonical_name":
            mark(CONTROL_LABELS[11],
                 f"the deferral does not NAME the lookup it used: {epsilon.get('record_resolution')!r}")
        # ... and the SAME control must not pass by refusing everything: a genuinely new name IS admitted.
        if not (variant.get("Zeta Book.md") or {}).get("admitted"):
            mark(CONTROL_LABELS[11],
                 "a genuinely new name was NOT admitted (the delta rule refuses everything)")

        # C13: a counted defect class with NO declared disposition is FATAL, never a silent acceptance.
        policy_without_disposition = deepcopy(policy)
        del policy_without_disposition["identity"]["defect_disposition"]["repeated_internal_whitespace"]
        faults = gate.undeclared_defect_dispositions(policy_without_disposition)
        if not any("repeated_internal_whitespace" in fault for fault in faults):
            mark(CONTROL_LABELS[12],
                 f"a class with no declared disposition was silently accepted (faults: {faults})")
        tokens_outside = deepcopy(policy)
        tokens_outside["identity"]["defect_disposition"]["ingest_site_marker"] = "probably_fine"
        if not any("outside" in fault for fault in gate.undeclared_defect_dispositions(tokens_outside)):
            mark(CONTROL_LABELS[12], "a disposition outside the declared vocabulary was accepted")

        # C14: an ACCEPTED debt with NO named owner word is FATAL — the acceptance must be a word, not a default.
        policy_without_word = deepcopy(policy)
        policy_without_word["identity"]["accepted_debt"] = {}
        if not any("owner word" in fault for fault in gate.undeclared_defect_dispositions(policy_without_word)):
            mark(CONTROL_LABELS[13], "an accepted_debt with no owner word was not refused")

        # C15 (BUG-848 / BUG-492): the WEAKER path must stay alive. With no author|title a record carries no
        # honest identity, so the refusal falls back to the sanitized stem — the rule that was already there.
        # A control that proves only the NEW path can pass while the old one dies silently is not a control.
        with cache.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"source_book": "Eta.md"}) + "\n")
        (books / "Eta.md").write_text("eta body " * 51, encoding="utf-8")
        (books / "Eta (z-lib.sk).md").write_text("eta body " * 52, encoding="utf-8")
        stem_only = {d["name"]: d for d in gate.preflight(books_dir=books, cache_path=cache, policy=policy,
                                                          run_id="c15", write_receipt=False)["decisions"]}
        eta = stem_only.get("Eta (z-lib.sk).md") or {}
        if eta.get("defer_reason") != "same_sanitized_stem":
            mark(CONTROL_LABELS[14],
                 f"a record with no author|title did not defer on its stem: {eta.get('defer_reason')!r}")

        # C16-C19 (T-173/D-3043): AN ACCEPTANCE IS A WORD ABOUT A CLASS. The class stays counted and printed, a
        # word belongs to the class it is about, a pointer must resolve, and a stale acceptance is a fault.
        accepted = deepcopy(policy)
        accepted["identity"]["defect_disposition"]["ingest_site_marker"] = "accepted_debt"
        accepted["identity"]["accepted_debt"]["declarations"]["ingest_site_marker"] = {
            "owner_word": "OWNER WORD 2026-10-16 (verbatim): \"T-173 accept\"",
            "declared_by": ["D-3043"], "row": "T-173", "because": "a control fixture"}
        (books / "Marker Book (z-lib.org).md").write_text("marker body " * 51, encoding="utf-8")
        # The fixtures the census needs, written HERE so this control reads exactly what it asserts: an empty
        # ledger, an empty ruler sheet, and a content report NEWER than the corpus (a stale screen is a
        # different fault and would mask the one under control).
        ledger_path.write_text(json.dumps({"pairs": []}), encoding="utf-8")
        collapse_path.write_text("", encoding="utf-8")
        (root / "content.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
        accepted_rep = gate.standing(policy=accepted, books_dir=books)
        if accepted_rep["marker_names"] < 1:
            mark(CONTROL_LABELS[15], "the accepted class was no longer counted (a quiet green)")
        if accepted_rep["accepted_debt"]["classes"].get(gate.MARKER_CLASS, 0) < 1:
            mark(CONTROL_LABELS[15], "the accepted class did not appear in the accepted-debt census")
        if any("marker" in line.lower() for line in accepted_rep["owner_owed"]):
            mark(CONTROL_LABELS[15], "an ACCEPTED class was still reported as OWNER-OWED")
        if accepted_rep["accepted_debt"]["rows"].get(gate.MARKER_CLASS) != "T-173":
            mark(CONTROL_LABELS[15], "the accepted class does not name the row that accepted it")
        # ... and the SAME fixture must OWE the class while it is declared owner_owed: a control that cannot see
        # the difference between the two dispositions would pass by counting nothing at all.
        owed_class = deepcopy(accepted)
        owed_class["identity"]["defect_disposition"]["ingest_site_marker"] = "owner_owed"
        owed_class["identity"]["accepted_debt"]["declarations"].pop("ingest_site_marker")
        if not any("marker" in line.lower()
                   for line in gate.standing(policy=owed_class, books_dir=books)["owner_owed"]):
            mark(CONTROL_LABELS[15], "the same fixture did NOT owe the class while it was declared owner_owed")
        owed = deepcopy(accepted)
        del owed["identity"]["accepted_debt"]["declarations"]["ingest_site_marker"]
        if not any("owner word" in fault and "ingest_site_marker" in fault
                   for fault in gate.undeclared_defect_dispositions(owed)):
            mark(CONTROL_LABELS[16], "an accepted class with no word OF ITS OWN was not refused")
        pointed = deepcopy(accepted)
        pointed["identity"]["accepted_debt"]["declarations"]["ingest_site_marker"] = {
            "same_as": "a_class_that_does_not_exist"}
        if not any("owner word" in fault and "ingest_site_marker" in fault
                   for fault in gate.undeclared_defect_dispositions(pointed)):
            mark(CONTROL_LABELS[17], "a `same_as` pointer to a missing class accepted the class anyway")
        cycle = deepcopy(accepted)
        cycle["identity"]["accepted_debt"]["declarations"]["ingest_site_marker"] = {"same_as": "ingest_site_marker"}
        if not any("owner word" in fault for fault in gate.undeclared_defect_dispositions(cycle)):
            mark(CONTROL_LABELS[17], "a `same_as` CYCLE accepted the class")
        stale = deepcopy(accepted)
        stale["identity"]["defect_disposition"]["ingest_site_marker"] = "owner_owed"
        if not any("NOT declared" in fault for fault in gate.undeclared_defect_dispositions(stale)):
            mark(CONTROL_LABELS[18], "a stale acceptance of a non-accepted class was not refused")

        # C20: a citation an acceptance makes must RESOLVE (D-3034) — the row and the decisions it names.
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "tasks.yaml").write_text(
                "tasks:\n- id: T-130\n  state: done\n- id: T-173\n  state: done\n", encoding="utf-8")
            (tmpdir / "decisions.yaml").write_text(
                "decisions:\n- id: D-3040\n- id: D-3043\n", encoding="utf-8")
            if _unresolved_citations(accepted, tmpdir / "tasks.yaml", tmpdir / "decisions.yaml"):
                mark(CONTROL_LABELS[19], "a citation that DOES resolve was reported unresolved")
            (tmpdir / "tasks.yaml").write_text("tasks:\n- id: T-999\n", encoding="utf-8")
            if not any("T-173" in fault
                       for fault in _unresolved_citations(accepted, tmpdir / "tasks.yaml",
                                                          tmpdir / "decisions.yaml")):
                mark(CONTROL_LABELS[19], "a row that does not exist was accepted as a citation")
            (tmpdir / "decisions.yaml").write_text("decisions: []\n", encoding="utf-8")
            (tmpdir / "tasks.yaml").write_text("tasks:\n- id: T-130\n- id: T-173\n", encoding="utf-8")
            if not any("D-3043" in fault
                       for fault in _unresolved_citations(accepted, tmpdir / "tasks.yaml",
                                                          tmpdir / "decisions.yaml")):
                mark(CONTROL_LABELS[19], "a decision that does not exist was accepted as a citation")

    # C21 — D-3085/BUG-916: A STALE CONTENT SCREEN EARNS TWO DECLARED rcs, and the DECLARATION is what decides.
    # MEASURED 2026-10-17: the health ladder was dead at ONE line for the whole length of a legitimate S0 run,
    # because the class was hardcoded FATAL for every caller - and a prefix ladder hides every rail after it.
    with tempfile.TemporaryDirectory(prefix="stale_screen_") as stale_tmp:
        stale_root = Path(stale_tmp)
        stale_books = stale_root / "books"
        stale_books.mkdir()
        stale_policy = deepcopy(gate.load_policy())
        stale_policy["content"]["report"] = str(stale_root / "content.json")
        (stale_root / "content.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
        screened_after = stale_books / "Screen Me.md"
        screened_after.write_text("screen body " * 50, encoding="utf-8")   # written AFTER the report: the corpus moved on
        reading_rep = gate.standing(policy=stale_policy, books_dir=stale_books, mode="reading")
        door_rep = gate.standing(policy=stale_policy, books_dir=stale_books, mode="door")
        if not any("older than the newest corpus file" in line for line in reading_rep["owner_owed"]):
            mark(CONTROL_LABELS[20], "the READING did not OWE a stale content screen (it went dark instead)")
        if reading_rep["rc"] != gate.RC_OWNER_OWED:
            mark(CONTROL_LABELS[20], f"the READING rc was {reading_rep['rc']}, expected OWNER-OWED")
        if not any("older than the newest corpus file" in line for line in door_rep["fatal"]):
            mark(CONTROL_LABELS[20], "the DOOR did not read a stale content screen as FATAL (it would have opened blind)")
        if door_rep["rc"] != gate.RC_FATAL:
            mark(CONTROL_LABELS[20], f"the DOOR rc was {door_rep['rc']}, expected FATAL")
        # ... and a disposition the config does not declare is REFUSED, never defaulted (the retired scalar's fault)
        undeclared = deepcopy(stale_policy)
        undeclared["content"]["staleness"] = "fatal"
        try:
            gate.standing(policy=undeclared, books_dir=stale_books, mode="reading")
            mark(CONTROL_LABELS[20], "the RETIRED scalar disposition was accepted instead of refused")
        except gate.GateInputError:
            pass

    failed = {label for label, _ in failures}
    for label in CONTROL_LABELS:
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    if failures:
        for label, detail in failures:
            print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
        return gate.RC_FATAL
    print(f"selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} controls green")
    return gate.RC_CLEAN


def main(argv: list[str] | None = None) -> int:
    """CLI: --check (default) | --gate | --preflight | --selftest, with --json and --run-id."""
    parser = argparse.ArgumentParser(description="The ingest door's rail (D-2997 / BUG-781).")
    parser.add_argument("--check", action="store_true", help="standing debt census (health reading, tri-state)")
    parser.add_argument("--gate", action="store_true", help="the DOOR's reading: rc 2 REFUSES the run")
    parser.add_argument("--preflight", action="store_true", help="P1 per-candidate decision + deferral receipt")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls (synthetic corpus)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--run-id", default="", help="batch id stamped into the deferral receipt")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.gate:
        return _run_gate(args.json)
    if args.preflight:
        return _run_preflight(args.run_id, args.json)
    return _run_check(args.json)


if __name__ == "__main__":
    sys.exit(main())
