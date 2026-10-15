#!/usr/bin/env python3
"""Fan independent sub-tasks out to local models - the DURABLE delegation executor (BUG-809).

WHY THE OLD VERSION WAS NOT ENOUGH
    It already ran tasks DETACHED (pipeline/research_run.py), but it had three ways to lie,
    and all three were measured in this repo on 2026-10-15:
      (1) A FALSE SUCCESS. Every task's command ended with `TERMINAL: DONE - oneshot rc=$?`, so a
          oneshot that exited 1 (engine refused, no content) was recorded as DONE. That is BUG-817's
          class - a failed answer read as a success - living inside the instrument that reports
          delegation health. The terminal word is now DERIVED from the answer (_grade), never asserted.
      (2) NO REAPER. `timeout_s` was only consulted when somebody happened to call status(). A run
          nobody polled therefore stayed RUNNING forever: "it runs so long without any result, it
          seems stuck". `run` now watches its own run to a declared deadline (research_run watch).
      (3) NO LIVENESS. A hung child and a working child looked identical. Stalled is now measured
          (idle_s against a declared stall_s) and published; only a task declared kill_on_stall is
          killed on suspicion, but silence is never a secret.
      (4) A TRUE LISTING READ AS A REVIEW (T-163/BUG-836, measured 2026-10-15). gemma-4-E4B answered a 22 KB
          review request with 2,294 chars of `file:line` lines and NOTHING ELSE - no finding, no claim. Every
          one of its 82 citations RESOLVED, so the citation reader of D-3022 CERTIFIED it (`82 checked, 0
          refuted`) and the 80-char floor let it through: the chain asked how LONG the answer was and never
          what it CONTAINED. A task may now declare a `shape`, and a review-shaped answer must CARRY a finding
          - a citation into the artifact under review PLUS reasoning beside it stating what is WRONG there.
          SHAPE IS NOT TRUTH: this gate decides whether an answer EXISTS; the verifier (R5) decides whether
          it is RIGHT.
    On top of that: an empty/stub answer is retried ONCE on a DIFFERENT declared model (a second
    attempt by the model that just failed adds no information), and every run writes a RECEIPT.

THE ONE ENTRY POINT (guarded, bounded, honest)
    python3 pipeline/subagent_fanout.py doctor --tasks T.yaml     # preflight: refuse to start unsound
    python3 pipeline/subagent_fanout.py run    --tasks T.yaml --run ID [--deadline S]
    ... plan | start | status | retry | verify | citations | shape | _grade   # manual / forensic use

WHAT A TASK IS (one question, one artefact, one file)  -  temp/runs/<run>/fan_<id>/
      - id: t1                       # a slug; the workstream name is fan_<id>
        model: gemma-4-E4B-it-MLX-4bit
        question: "Which function decides a workstream's state, and on which line?"
        files: [pipeline/research_run.py]
        mode: oneshot                # oneshot = one deterministic call (temp 0.0, no tools)
                                     # agent   = goose run -t, which HAS tools (slower, less predictable)
        max_tokens: 400
        timeout_s: 60                # OPTIONAL: this task's own budget (tighter than the mode default;
                                     # a retry never inherits one that just proved insufficient)
        shape: review                # OPTIONAL: what the answer must CONTAIN - declared in
                                     # config/engine.yaml#fanout.answer_shapes, DISCLOSED to the model in the
                                     # prompt and read by the grader. Omit it for a question that only asks
                                     # WHERE something is: that answer stays gated by length alone.

EXIT: 0 every task DONE | 1 a task FAILED/EMPTY after its attempts, or the config is unsound
      | 2 tasks still RUNNING when the deadline was spent (owner-owed, never silently waited on)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# ONE class resolver (C21): the workstream contract lives in pipeline/research_run.py, which reads it from
# config/agent_context.yaml. A second reader here would be a second home for the same vocabulary (C12).
from pipeline.research_run import class_for_mode, resolve_class  # noqa: E402

RUNS = ROOT / "temp" / "runs"
RUNNER = ROOT / "pipeline" / "research_run.py"
ASKER = ROOT / "pipeline" / "oneshot_ask.py"
OK, FATAL, PENDING = 0, 1, 2
STUB_PREFIX = "(no content returned"
GUARDS_REQUIRED = ("default_timeout_s", "agent_timeout_s", "deadline_s", "stall_s", "kill_on_stall",
                   "max_attempts", "retry_on", "fallback_model", "min_answer_chars")


def conf() -> dict:
    """The declared engine facts, or a FATAL.

    A missing home is NOT a reason to fall back to a number this module likes: on 2026-10-15 this
    executor ran with its own hardcoded defaults because the declared block had never landed, and a
    sub-agent was blamed for correctly reporting that the setting did not exist (BUG-817).
    """
    import yaml
    doc = yaml.safe_load((ROOT / "config" / "engine.yaml").read_text())
    if not doc.get("fanout"):
        raise SystemExit("FATAL: config/engine.yaml declares no fanout block - refusing to invent a cap (C12)")
    return doc


def guards() -> dict:
    """The declared delegation guards, or a FATAL naming every missing key.

    These are the numbers that decide whether a delegation can be trusted: its budget, its stall
    threshold, whether silence is fatal, how many attempts it gets, on which model it retries, and
    the smallest answer that counts as an answer. Inventing any one of them at runtime is the
    BUG-817 defect, so a missing key stops the run instead of being filled in (C12/C16).
    """
    g = conf().get("fanout", {}).get("guards")
    if not isinstance(g, dict):
        raise SystemExit("FATAL: config/engine.yaml declares no fanout.guards block - a delegation "
                         "without guards is the BUG-809 defect (C12)")
    missing = [k for k in GUARDS_REQUIRED if k not in g]
    if missing:
        raise SystemExit(f"FATAL: config/engine.yaml#fanout.guards is incomplete, missing {missing} - "
                         f"refusing to invent a delegation guard (C12)")
    if int(g["min_answer_chars"]) <= 0:
        raise SystemExit("FATAL: fanout.guards.min_answer_chars must be > 0 - a zero floor accepts an "
                         "empty answer as an answer")
    if int(g["stall_s"]) >= int(g["default_timeout_s"]):
        raise SystemExit("FATAL: fanout.guards.stall_s must be BELOW default_timeout_s, or a silent child "
                         "is reported for the first time at the moment it is killed - the guard would be dead")
    return g


def answer_verdict(path: pathlib.Path, min_chars: int, shape: str = "", artifacts: list | tuple = ()) -> tuple[bool, str]:
    """Did a usable answer actually arrive? One rule, one home (C12/C16).

    The failure this exists for: an engine that returns HTTP 200 with no content, or the stub
    oneshot_ask.py writes when it got nothing, must never be read as a deliverable.

    T-163: when the task declares a SHAPE, the answer is judged by what it CONTAINS and not only by how long it
    is. MEASURED (BUG-836): a 2,294-char list of `file:line` lines cleared the 80-char floor and was graded
    DONE, and every one of its citations was TRUE - so the citation reader could not refuse it either. A length
    floor cannot tell a review from a table of contents; a shape can.
    """
    if not path.exists():
        return False, "no answer file"
    text = path.read_text(errors="replace").strip()
    if not text:
        return False, "the answer is empty"
    if text.startswith(STUB_PREFIX):
        return False, "the model returned no content"
    if len(text) < min_chars:
        return False, f"the answer is {len(text)} chars, below the declared floor of {min_chars}"
    if shape:
        findings, defects = shape_defects(text, shape, artifacts)
        if defects:
            return False, f"not a {shape}: {defects[0]}"
        return True, f"ok, {len(text)} chars, {findings} finding(s) for the declared {shape} shape"
    return True, f"ok, {len(text)} chars"


CITATION = re.compile(r"(?<![\w/])([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|toml|txt)):(\d{1,6})")
PATHISH = re.compile(r"(?<![\w/])([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|toml|txt))")
# `Line 111`, `lines 349-351` - the SECOND form is not decoration: MEASURED 2026-10-15 (T-163's own R5 review),
# a model named its finding as a RANGE ("the most critical line ... is **338-342**", "(lines 349-351)"), and a
# grammar that reads only a single line refuses a located, predicated finding as if no location were given. The
# FIRST line of a range is the location; the rest of the range is prose about it.
LINE_ONLY = re.compile(r"\bLines?\s+(\d{1,6})\b", re.I)
LINE_RANGE = re.compile(r"\bLines?\s+(\d{1,6})\s*[-\u2013]\s*(\d{1,6})\b", re.I)
# A BOLDED range with no word at all ("**338-342**"). Accepted ONLY where a caller supplies the file the answer
# was about (default_path), because bolded numerals are a location only by presentation - see citation_sites.
BOLD_RANGE = re.compile(r"\*\*\s*(\d{1,6})\s*[-\u2013]\s*(\d{1,6})\s*\*\*")
BACKTICK = re.compile(r"`([^`\n]+)`")
CODEY = re.compile(r"[^A-Za-z0-9\s]|_")     # a fragment with punctuation or an underscore is a QUOTE
# A LABEL is how a model announces that the next line is the code it means: "**Exact Code:** `frag`".
# Requiring a label is what keeps the lookahead below from turning ordinary prose into a failed citation.
QUOTE_LABEL = re.compile(r"^\s*[>*-]*\s*(?:\*\*)?\s*(?:exact\s+code|code|quoted?|reads|says|exact)\b", re.I)


def citation_sites(answer_lines: list[str], default_path: str = "") -> list[list[tuple[str, int, int, int]]]:
    """Every `file:line` each line of an answer cites, in the shapes models actually write. PURE.

    ONE reader of "what counts as a citation" (C21/C12): the quote refuter (citation_defects), the SHAPE reader
    (shape_defects, T-163) and the manual verb all read citations THROUGH this function, so a shape the grammar
    learns is learned everywhere at once. A line that names a file and nothing else sets the CONTEXT for the
    `Line N:` bullets under it; a line that names its own file always beats that context, or a heading over file
    A would check a citation to file B against file A (a false refutation).

    `default_path` is the file the answer was TOLD it is about, and it is supplied ONLY by the SHAPE reader, for
    a shaped answer with exactly one declared artefact - never by the quote refuter, whose behaviour is therefore
    unchanged by this parameter (proved by measurement: `citations` on the BUG-836 bytes still reads 82 checked /
    0 refuted). It exists because a model asked about ONE file names its location as a bare line or a RANGE
    ("**338-342**", "(lines 349-351)"), and refusing that as "no location given" is a FALSE NEGATIVE - the costly
    direction (an over-strict guard is a disabled guard, D-3022). It cannot loosen the degenerate answer: a bare
    line still counts for nothing without prose beside it and a stated defect, and a range is read by its FIRST
    line, which must exist in the file.
    """
    out: list[list[tuple[str, int, int, int]]] = []
    context = None
    for raw in answer_lines:
        targets = [(m.group(1), int(m.group(2)), m.start(), m.end()) for m in CITATION.finditer(raw)]
        if not targets:
            line_only = LINE_ONLY.search(raw)
            line_range = LINE_RANGE.search(raw)
            bare_range = BOLD_RANGE.search(raw) if default_path else None
            named = PATHISH.findall(raw)
            if line_range and len(set(named)) <= 1:
                # a range names its location by its FIRST line, and only when the file is unambiguous
                targets = [(named[0] if named else (context or default_path), int(line_range.group(1)),
                            line_range.start(), line_range.end())]
                targets = [t for t in targets if t[0]]
            elif line_only and len(set(named)) == 1:
                targets = [(named[0], int(line_only.group(1)), line_only.start(), line_only.end())]
            elif line_only and context:
                targets = [(context, int(line_only.group(1)), line_only.start(), line_only.end())]
            elif bare_range is not None and len(set(named)) <= 1:
                path = named[0] if named else (context or default_path)
                targets = [(path, int(bare_range.group(1)), bare_range.start(), bare_range.end())] if path else []
            elif len(set(named)) == 1 and not line_only:
                context = named[0]         # a heading names the file the following Line N: refer to
        out.append(targets)
    return out


def resolve_location(path: str, line_no: int) -> tuple[str, str]:
    """Read a cited location back: (how that line reads NOW, "") or ("", the reason it does not check out).

    The ONE home of "does this location exist, and what does it say" (C21/D-3022): a citation is a claim about a
    file, and both the quote refuter and the SHAPE reader must ask the file the same question. Everything is read
    against the tree AS IT IS NOW, so a refutation of an answer written BEFORE an edit means the file MOVED - the
    guard is meant for a receipt minutes after the answer, not for archaeology.
    """
    target = ROOT / path
    if not target.exists():
        alt = pathlib.Path(path)
        if not alt.exists():
            return "", f"cites {path}:{line_no} and no such file exists"
        target = alt
    lines = target.read_text(errors="replace").splitlines()
    if line_no > len(lines):
        return "", f"{path}:{line_no} is past the end of the file ({len(lines)} lines)"
    return " ".join(lines[line_no - 1].split()), ""


def citation_defects(text: str) -> tuple[int, list[str]]:
    """Check every file:line an answer cites, against the file itself. Returns (checked, defects).

    WHY THIS EXISTS (BUG-721, re-measured live on the FIRST harness job, 2026-10-15): asked to find
    assertions in two files, the deployed agent_loop model returned EIGHT file:line citations and
    every one pointed at unrelated code - it "quoted" `word = "DONE"` at a line that reads
    `if len(text) < min_chars:`. The answer was 1,737 chars, exited 0, cleared the length floor and
    was graded DONE. Nothing in the guard chain could see it, because not one of them READ THE FILE.

    A citation is a claim about a file, and a claim about a file is decidable in one second. This is
    the R5 duty made mechanical: the verifier of a citation need not be a smarter model, it must be a
    reader. THREE SHAPES are read, because all three are what models actually write: `path.py:111` inline,
    a `path.py (line 111)` pair, and a `path.py` heading followed by `Line 111:` bullets. A quote on the
    NEXT line is read only when that line LABELS itself as the code (`**Exact Code:**`) and carries no
    citation of its own. Everything is checked against the file AS IT IS NOW, so a refutation of an answer
    written BEFORE an edit means the file MOVED - the guard is meant for a receipt minutes after the answer,
    not for archaeology. A prose reference (no punctuation, like `the grader`) is never treated as a quote,
    so a loose answer is not failed for being loose.
    """
    checked, defects = 0, []
    answer_lines = text.splitlines()
    sites = citation_sites(answer_lines)
    for i, raw in enumerate(answer_lines):
        targets = sites[i]
        if not targets:
            continue
        for index, (path, line_no, _, end) in enumerate(targets):
            window_end = targets[index + 1][2] if index + 1 < len(targets) else len(raw)
            frags = [f for f in BACKTICK.findall(raw[end:window_end]) if CODEY.search(f)]
            if not frags and i + 1 < len(answer_lines):
                # THE LABELLED ADJACENT QUOTE, and it is not a hypothetical: measured 2026-10-15, an R5
                # reviewer wrote `**File:line:** pipeline/config_audit.py (line 110)` followed by
                # `**Exact Code:** if not path.exists(): raise SystemExit(...)` - and line 110 actually
                # reads `ACKNOWLEDGED_HARDCODED: set[str] = {`. Without this lookahead the checker
                # certified the line, never read the quote, and reported `0 refuted` on a fabrication
                # (BUG-831). The label is required so that a merely NEARBY fragment is not guessed at;
                # and a line that carries its own citation is never borrowed.
                nxt = answer_lines[i + 1]
                if QUOTE_LABEL.match(nxt) and not CITATION.search(nxt) and not LINE_ONLY.search(nxt):
                    frags = [f for f in BACKTICK.findall(nxt) if CODEY.search(f)]
            checked += 1
            actual, why = resolve_location(path, line_no)
            if why:
                defects.append(why)
                continue
            for frag in frags:
                quote = " ".join(frag.split())
                if quote and quote not in actual:
                    defects.append(f"{path}:{line_no} is quoted as `{quote}` but that line reads: {actual[:120] or '(blank)'}")
    return checked, defects


# ── THE SHAPE OF AN ANSWER (T-163 / BUG-836) ─────────────────────────────────────────────────────────
# A citation that RESOLVES is not yet a claim. MEASURED 2026-10-15: gemma-4-E4B answered a 22 KB review request
# with 2,294 chars of `path.py:NN` lines and NOTHING else; all 82 citations resolved, so the citation reader
# certified it (`82 checked, 0 refuted`) and the 80-char floor let it through. D-3022 reads a LOCATION back; the
# rule below reads the PREDICATION a review exists to make. The requirement is DECLARED per shape in
# config/engine.yaml#fanout.answer_shapes - never assembled here (C12) - and it is DISCLOSED to the model in the
# prompt (shape_instruction), because a gate the answer was never told about is a trap, not a guard.
SHAPE_REQUIRED = ("min_findings", "min_finding_chars", "artifact_required", "defect_markers")
SHAPE_CONTROL_REQUIRED = ("name", "path", "shape", "artifact", "expect")
SHAPE_EXPECT = ("an_answer", "not_an_answer")


def answer_shapes() -> dict:
    """Every DECLARED answer shape. The numbers live in config (C12), so this only reads them."""
    decl = (conf().get("fanout") or {}).get("answer_shapes") or {}
    if not isinstance(decl, dict):
        raise SystemExit("FATAL: config/engine.yaml#fanout.answer_shapes must be a mapping of shape -> its "
                         "requirement - refusing to read a shape out of a malformed declaration (C12/C16)")
    return decl


def shape_spec(shape: str) -> dict:
    """The requirement ONE declared shape carries, or a FATAL naming every declared shape (fail closed, C16).

    A task that declares a shape nobody declared would be graded against a requirement invented at runtime - the
    BUG-817 defect one layer up: the number that decides a verdict must have a HOME. Every declared shape is
    checked for the four things a reader needs, and the two floors are checked for the failures they prevent: a
    shape requiring no finding accepts the very listing it exists to refuse, and a zero prose floor lets a bare
    citation count as the reasoning beside it.
    """
    decl = answer_shapes()
    spec = decl.get(shape)
    if not isinstance(spec, dict):
        raise SystemExit(f"FATAL: shape {shape!r} is not declared in config/engine.yaml#fanout.answer_shapes "
                         f"(declared: {sorted(decl) or 'none'}) - refusing to invent what an answer must "
                         f"contain (C12)")
    missing = [k for k in SHAPE_REQUIRED if k not in spec]
    if missing:
        raise SystemExit(f"FATAL: answer_shapes.{shape} is incomplete, missing {missing} - a shape with no "
                         f"requirement is an answer nobody grades (C12)")
    if int(spec["min_findings"]) < 1:
        raise SystemExit(f"FATAL: answer_shapes.{shape}.min_findings must be >= 1 - a shape that requires no "
                         f"finding accepts the very listing it exists to refuse (T-163)")
    if int(spec["min_finding_chars"]) < 1:
        raise SystemExit(f"FATAL: answer_shapes.{shape}.min_finding_chars must be >= 1 - a zero floor lets a "
                         f"bare citation count as the reasoning beside it (T-163)")
    if not [m for m in (spec["defect_markers"] or []) if str(m).strip()]:
        raise SystemExit(f"FATAL: answer_shapes.{shape}.defect_markers is empty - nothing would state a DEFECT, "
                         f"so every located sentence would read as a finding (T-163)")
    return spec


def _marker_re(spec: dict) -> re.Pattern:
    """The declared defect markers as ONE word-boundary regex, assembled HERE and declared in config (C12)."""
    words = "|".join(re.escape(str(m).strip().lower()) for m in spec["defect_markers"] if str(m).strip())
    return re.compile(rf"(?<![\w-])(?:{words})(?![\w-])", re.I)


def _artifact_keys(artifacts: list | tuple) -> tuple[set[str], set[str]]:
    """An artefact's keys: the FULL declared path and its basename.

    A model names a file the way the prompt printed it, so `research_run.py` counts as
    `pipeline/research_run.py`. The gate deliberately errs toward reading a citation as being about the artefact
    the answer was GIVEN: refusing an honest finding is the costly direction (an over-strict guard is a disabled
    guard, D-3022).
    """
    full: set[str] = set()
    base: set[str] = set()
    for a in artifacts or ():
        p = str(a).strip().lstrip("./")
        if not p:
            continue
        full.add(p)
        base.add(pathlib.PurePosixPath(p).name)
    return full, base


def _in_artifact(path: str, keys: tuple[set[str], set[str]]) -> bool:
    """Is this cited path the artefact under review (by full path or by basename)?"""
    full, base = keys
    p = str(path).strip().lstrip("./")
    return p in full or pathlib.PurePosixPath(p).name in base


def shape_defects(text: str, shape: str, artifacts: list | tuple = ()) -> tuple[int, list[str]]:
    """Read an answer's SHAPE: does it CARRY a finding, or is it a listing of locations? Returns (findings, defects).

    WHAT THIS EXISTS FOR (BUG-836/T-163, MEASURED): gemma-4-E4B answered a 22 KB review request with 2,294 chars
    of `path.py:NN` lines and nothing else. `python3 pipeline/subagent_fanout.py citations` on those exact bytes
    returns **82 citations checked, 0 refuted** - every location exists - so D-3022's reader CERTIFIES it and the
    80-char floor passes it. The answer was not FALSE, it was EMPTY OF ANY CLAIM: a table of contents for a
    review that was never written.

    A FINDING is a citation into the artefact under review PLUS reasoning beside it that states what is wrong
    there. Three limbs, each with its own failure:
      (1) LOCATION   - the citation resolves (one reader: resolve_location), or the finding is about nothing;
      (2) ARTEFACT   - it points at the artefact the answer was GIVEN, so "I reviewed this" is bounded by what
                       was actually put in front of the model (the T-163 gate's "in the artefact under review");
      (3) PREDICATION - the segment carries at least `min_finding_chars` of prose BESIDE the citation and names
                       a defect from the DECLARED vocabulary. Prose alone is not enough (an account of what a
                       function DOES is not a finding) and a marker alone is not enough (a heading is not one).
    A finding may be stated on the line AFTER its citation, which is how markdown reviews are actually written; a
    line that carries a citation of its own is never borrowed (the BUG-831 discipline).

    SHAPE IS NOT TRUTH, AND THE BOUNDARY IS THE POINT. This decides whether an answer EXISTS; whether the finding
    is CORRECT is the verifier's job (R5/D-3022). A gate that tried to judge quality with a vocabulary list would
    be the very thing it exists to prevent - a form check wearing a truth check's name.
    """
    spec = shape_spec(shape)
    markers = _marker_re(spec)
    keys = _artifact_keys(artifacts)
    lines = text.splitlines()
    # A bare line reference can only be attributed when the answer was about ONE file - which is exactly what a
    # shaped task declares. Two artefacts and a bare `338-342` is ambiguous, so it is not counted.
    declared = [str(a) for a in (artifacts or ()) if str(a).strip()]
    sites = citation_sites(lines, declared[0] if len(declared) == 1 else "")
    findings, cited_in_artifact, cited_anywhere, bad = 0, 0, 0, []
    for i, raw in enumerate(lines):
        here = sites[i]
        cited_anywhere += len(here)
        into = [(p, n) for (p, n, _, _) in here if _in_artifact(p, keys)]
        cited_in_artifact += len(into)
        if not into:
            continue
        window = raw if (i + 1 >= len(lines) or sites[i + 1]) else raw + "\n" + lines[i + 1]
        prose = " ".join(CITATION.sub(" ", window).split())
        if len(prose) < int(spec["min_finding_chars"]) or not markers.search(prose):
            continue
        located = 0
        for path, line_no in into:
            _, why = resolve_location(path, line_no)
            if why:
                bad.append(why)
                continue
            located += 1
        findings += 1 if located else 0
    defects = list(dict.fromkeys(bad))
    if findings < int(spec["min_findings"]):
        arts = ", ".join(sorted(str(a) for a in (artifacts or ()))) or "(none declared)"
        note = ("; every citation RESOLVED, so this is a LISTING of true locations and not a review"
                if cited_in_artifact and not bad else "")
        defects.insert(0, f"the answer carries {findings} finding(s) stating a defect about {arts} - a {shape} "
                          f"must carry {spec['min_findings']} - across {cited_in_artifact} citation(s) into the "
                          f"artefact and {cited_anywhere} in total{note}")
    return findings, defects


def answer_shape_controls() -> list[dict]:
    """The FROZEN known-answer controls for the shape reader, DECLARED in config (C12: no path in code).

    Each control is a MEASUREMENT kept falsifiable: `expect: not_an_answer` means those declared bytes must STILL
    read as not being the declared shape. A control whose subject is ABSENT is a FAIL and never a skip - a check
    that decided nothing must not print as a pass (BUG-826).
    """
    controls = (conf().get("fanout") or {}).get("answer_shape_controls") or []
    if not isinstance(controls, list):
        raise SystemExit("FATAL: config/engine.yaml#fanout.answer_shape_controls must be a list - a control "
                         "nobody can read is not a control (C16)")
    out = []
    for c in controls:
        if not isinstance(c, dict):
            raise SystemExit(f"FATAL: an answer_shape_controls entry is not a mapping: {c!r} (C16)")
        missing = [k for k in SHAPE_CONTROL_REQUIRED if not c.get(k)]
        if missing:
            raise SystemExit(f"FATAL: answer_shape_controls[{c.get('name') or c!r}] is incomplete, missing "
                             f"{missing} - a control with no declared expectation decides nothing (C16)")
        if str(c["expect"]) not in SHAPE_EXPECT:
            raise SystemExit(f"FATAL: answer_shape_controls[{c['name']}] declares expect={c['expect']!r}, not one "
                             f"of {list(SHAPE_EXPECT)} - an unreadable expectation is a silent pass (C16)")
        out.append(c)
    return out


def shape_instruction(task: dict) -> str:
    """What the task's declared SHAPE must contain, TOLD TO THE MODEL by the same declaration that grades it.

    A gate the answer was never told about is a trap, and this repository has already paid for one (BUG-816: a
    task asked about a setting that did not exist, the model said so, and the answer was read as a model
    failure). So the requirement is derived from the declaration - one home (C12) - and appended to the prompt.
    """
    shape = str(task.get("shape") or "")
    if not shape:
        return ""
    spec = shape_spec(shape)
    arts = ", ".join(str(f) for f in (task.get("files") or [])) or "the files given"
    artefact = (" (each finding must cite a location in the artefact under review; other citations do not count)"
                if spec["artifact_required"] else "")
    return (f"Your answer must be a {shape}: at least {spec['min_findings']} FINDING(s), each naming a location "
            f"in {arts} and stating what is WRONG there{artefact}, with at least "
            f"{spec['min_finding_chars']} characters of reasoning beside the citation. A list of locations with "
            f"no finding - or a description of what the code does - is NOT an answer.")


def grade(answer: pathlib.Path, rc: int, min_chars: int, report: pathlib.Path,
          shape: str = "", artifacts: list | tuple = ()) -> int:
    """Write the workstream's OWN terminal line from the evidence, never from an expectation.

    This runs INSIDE the workstream (it is the last line of cmd.sh), so it is the only writer of the
    terminal word. A non-zero rc with a real answer is still a partial result worth keeping, and it is
    reported as FAILED with the answer on disk - the point is that the WORD may not be guessed.

    T-163: a task's declared SHAPE is passed through, so a long answer that carries no finding reads FAILED and
    not DONE. It is deliberately NOT EMPTY: content ARRIVED, and it was not the answer. EMPTY means "nothing came
    back" (a capacity accident - gpt-oss-20b spent the whole budget inside reasoning_content, BUG-836 limb 2),
    while a shape failure is a MEASUREMENT of the wrong model on the wrong class of work - which is exactly what
    the capability registry needs (T-156), and `retry_on` already carries FAILED, so one retry on a DIFFERENT
    family still happens.
    """
    ok, why = answer_verdict(answer, min_chars, shape, artifacts)
    if ok and rc == 0:
        word = "DONE"
    elif "no content" in why or "empty" in why or "no answer file" in why:
        word = "EMPTY"
    else:
        word = "FAILED"
    line = f"TERMINAL: {word} - rc={rc}, {why}"
    with open(report, "a") as fh:
        fh.write(line + "\n")
        fh.flush()
    return 0 if word == "DONE" else 1


def _rows(run_id: str) -> list[dict]:
    """Every workstream's reconciled state, read from the runner that owns that state (one home)."""
    proc = subprocess.run([sys.executable, str(RUNNER), "status", "--run", run_id, "--json"],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        return json.loads(proc.stdout or "[]")
    except Exception:
        print(f"FATAL: could not read the run state: {proc.stdout[:200]}{proc.stderr[:200]}")
        return []


def _watch(run_id: str, budget_s: int) -> int:
    """Enforce the declared budgets for this run. Returns the runner's honest exit code."""
    return subprocess.run([sys.executable, str(RUNNER), "watch", "--run", run_id,
                           "--budget", str(int(budget_s))], cwd=str(ROOT)).returncode


def _write_json(path: pathlib.Path, obj: dict) -> None:
    """Crash-safe JSON write: tempfile -> fsync -> os.replace (C6)."""
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _job_row(ws_class: str) -> dict:
    """The declared deployment for a workstream class - its one home is engine.yaml#harnesses.jobs (D-3017).

    A class whose row names no harness is not deployable AS a harness, and a row with no declared args is
    refused rather than assembled here: the command the owner runs and the command a workstream runs must
    be the same declared bytes, or the measurement describes a deployment nobody uses (C12).
    """
    rows = (conf().get("harnesses") or {}).get("jobs") or {}
    row = rows.get(ws_class)
    if not isinstance(row, dict) or not row.get("harness"):
        raise SystemExit(f"FATAL: config/engine.yaml#harnesses.jobs declares no harness for class "
                         f"'{ws_class}' - a harness workstream in a class that has none is a deployment "
                         f"nobody decided (D-3017)")
    if not row.get("args"):
        raise SystemExit(f"FATAL: the harness row for '{ws_class}' declares no args - refusing to assemble a "
                         f"deployment command that no declaration owns (C12)")
    return row


def _cmd_for(task: dict, wsd: str, g: dict, model: str) -> str:
    """The exact bytes a workstream runs: the task, then the GRADER that decides its terminal word."""
    mode = str(task.get("mode", "oneshot"))
    lines = [f'echo "STEP 1: {model} starts" >> "$WS_REPORT"']
    if mode == "harness":
        # T-154: a harness workstream is launched through the ENGINE's own wiring (`omlx launch <tool>`),
        # with the class's transcript binding set by the runner from the class's declared env. Its answer
        # is its stdout; the launcher's banner lines are stripped by the DECLARED regex, and both byte
        # counts are reported so a reader can see whether stripping removed anything at all.
        row = _job_row(class_for_mode(mode))
        launch = str((conf().get("engine") or {}).get("launch_cli") or "")
        if not launch:
            raise SystemExit("FATAL: config/engine.yaml declares no engine.launch_cli - refusing to invent "
                             "a deployment command (C12)")
        args = " ".join(str(a) for a in row["args"])
        lines.append(f'"{launch}" launch {row["harness"]} --model {model} -- {args} '
                     f'"$(cat "$WS_DIR/00_prompt.txt")" > "$WS_DIR/20_answer_raw.md" 2> "$WS_DIR/30_harness.err"')
        noise = str(row.get("stdout_noise_regex") or "")
        if noise:
            lines.append(f"grep -vE {_shq(noise)} \"$WS_DIR/20_answer_raw.md\" > \"$WS_DIR/20_answer.md\" || true")
            lines.append('[ -s "$WS_DIR/20_answer.md" ] || cp "$WS_DIR/20_answer_raw.md" "$WS_DIR/20_answer.md"')
            lines.append('{ echo "HARNESS_STDOUT: raw=$(wc -c < "$WS_DIR/20_answer_raw.md")B '
                         'answer=$(wc -c < "$WS_DIR/20_answer.md")B"; } >> "$WS_REPORT"')
        else:
            lines.append('cp "$WS_DIR/20_answer_raw.md" "$WS_DIR/20_answer.md"')
    elif mode == "agent":
        lines.append('GOOSE=$(command -v goose || echo /Applications/Goose.app/Contents/Resources/bin/goose)')
        lines.append('"$GOOSE" run -t "$(cat "$WS_DIR/00_prompt.txt")" > "$WS_DIR/20_answer.md" 2>&1')
    else:
        mt = int(task.get("max_tokens", conf().get("fanout", {}).get("default_max_tokens", 512)))
        lines.append(f'python3 pipeline/oneshot_ask.py --model {model} --prompt-file "$WS_DIR/00_prompt.txt" '
                     f'--max-tokens {mt} --out "$WS_DIR/20_answer.md" --json-out "$WS_DIR/21_meta.json" '
                     f'>> "$WS_REPORT" 2>&1')
    lines.append("RC=$?")
    grade_cmd = (f'python3 pipeline/subagent_fanout.py _grade --answer "$WS_DIR/20_answer.md" --rc "$RC" '
                 f'--min-chars {int(g["min_answer_chars"])} --report "$WS_REPORT"')
    # T-163: a task that declares a SHAPE is graded against that shape, and the artefact it was given is named in
    # the command. ONE declaration decides what the prompt asks for and what the grader reads back.
    shape = str(task.get("shape") or "")
    if shape:
        artefacts = ",".join(str(f) for f in (task.get("files") or []))
        grade_cmd += f" --shape {_shq(shape)} --artifact {_shq(artefacts)}"
    lines.append(grade_cmd)
    return "\n".join(lines) + "\n"


def _shq(text: str) -> str:
    """Single-quote a value for the shell: the command carries a DECLARED regex, never a literal."""
    return "'" + str(text).replace("'", "'\\''") + "'"


def _excerpt(path: pathlib.Path, cap: int) -> tuple[str, str]:
    """The artefact text a model gets, and the reason it is not the WHOLE artefact ("" when it is).

    T-163: a review is a review OF WHAT WAS GIVEN. The cap is declared (engine.yaml#fanout.excerpt_bytes), so a
    truncation must be said OUT LOUD - to the model, which otherwise cannot know that a line it cannot see was
    never shown to it, and to the owner, for whom a finding below the cut is impossible in a way nobody sees.
    That is the BUG-816 class: the premise and the task disagreeing SILENTLY.
    """
    body = path.read_text(errors="replace")
    if len(body) <= cap:
        return body, ""
    why = (f"TRUNCATED: the file is {len(body)} chars and the declared excerpt is {cap}; anything below the cut "
           f"was never shown to you, so a finding about it cannot be justified - say so instead of guessing")
    return body[:cap] + f"\n[... {why}]", why


def _prompt_for(task: dict, cap: int) -> str:
    """The question plus its evidence, with an explicit permission to say NO EVIDENCE - and, when the task
    declares one, the SHAPE its answer must have (T-163: a requirement DISCLOSED, never a hidden trap)."""
    parts = [str(task.get("question", "")).strip()]
    for f in task.get("files", []):
        p = ROOT / f
        if not p.exists():
            parts.append(f"\n### {f}\n(file absent - say so, do not guess)")
            continue
        body, _ = _excerpt(p, cap)
        parts.append(f"\n### {f}\n{body}")
    parts.append("\nAnswer in <=12 lines. Cite file:line where it helps. If the files do not "
                 "contain the answer, say NO EVIDENCE rather than guessing.")
    note = shape_instruction(task)
    if note:
        parts.append("\nSHAPE REQUIREMENT - " + note)
    return "\n".join(parts)


def plan(tasks_file: pathlib.Path, run_id: str) -> int:
    """Validate a task file and freeze one command + one prompt per task (artefact-partitioned).

    A task that declares a SHAPE is refused HERE if the shape is not declared or is malformed (T-163), on the
    same principle as the PREMISE gate below: a task nobody can grade must not cost a model call to discover.
    """
    import yaml
    g = guards()
    doc = yaml.safe_load(tasks_file.read_text()) or {}
    tasks = doc.get("tasks") or []
    if not tasks:
        print("FATAL: the task file declares no tasks")
        return FATAL
    cap = int(conf().get("fanout", {}).get("excerpt_bytes", 24000))
    subprocess.run([sys.executable, str(RUNNER), "new", "--run", run_id,
                    "--brief-text", tasks_file.read_text()], check=True, cwd=str(ROOT))
    for t in tasks:
        wid = str(t["id"])
        # THE PREMISE GATE. A fan-out verifies ANSWERS; nothing in it verifies the PREMISE of a task.
        # On 2026-10-15 a task asked about a setting that did not exist, the sub-agent correctly said so,
        # and the answer was read as a model failure (BUG-816/BUG-817). If a task declares expect=REGEX,
        # one of its files must contain it or the task is refused before any model is called.
        expect = t.get("expect")
        if expect:
            hit = [f for f in t.get("files", [])
                   if (ROOT / f).exists() and re.search(str(expect), (ROOT / f).read_text(errors="replace"))]
            if not hit:
                print(f"FATAL: task {wid} declares expect={expect!r} and no listed file contains it - "
                      f"the PREMISE is wrong, so no model should be asked")
                return FATAL
            print(f"premise ok: task {wid} expect={expect!r} found in {hit}")
        wsd = RUNS / run_id / f"fan_{wid}"
        wsd.mkdir(parents=True, exist_ok=True)
        # T-163: a declared SHAPE is resolved before anything is launched, and the artefact it will be judged
        # against is FROZEN into task.json - so the receipt, the retry and the verifier all judge the answer by
        # the shape the task was ASKED for, not by whatever a later reader assumes.
        shape = str(t.get("shape") or "")
        if shape:
            spec = shape_spec(shape)
            files = [str(f) for f in (t.get("files") or [])]
            if spec["artifact_required"] and not files:
                print(f"FATAL: task {wid} declares shape {shape!r}, which requires an artefact under review, and "
                      f"declares no files - a finding would have nothing to cite (T-163)")
                return FATAL
            print(f"shape: task {wid} is a {shape} - it must carry {spec['min_findings']} finding(s) about "
                  f"{', '.join(files)}")
            for f in files:
                p = ROOT / f
                if p.exists() and len(p.read_text(errors="replace")) > cap:
                    print(f"warn: task {wid} reviews {f}, which is longer than the declared excerpt of {cap} "
                          f"chars - this is a PARTIAL review by construction and the prompt SAYS SO to the "
                          f"model; refusing a review whose prompt exceeds a measured size is the registry's job "
                          f"(T-156/BUG-836)")
        (wsd / "00_prompt.txt").write_text(_prompt_for(t, cap))
        _write_json(wsd / "task.json", {"id": wid, "model": t["model"], "mode": str(t.get("mode", "oneshot")),
                                        "class": class_for_mode(str(t.get("mode", "oneshot"))),
                                        "max_tokens": t.get("max_tokens"), "attempt": 1,
                                        "timeout_s": t.get("timeout_s"), "shape": shape or None,
                                        "files": [str(f) for f in (t.get("files") or [])],
                                        "retry_of": None, "question": str(t.get("question", ""))})
        (wsd / "cmd.sh").write_text(_cmd_for(t, str(wsd), g, str(t["model"])))
    print(f"planned {len(tasks)} task(s) for run {run_id}")
    return OK


def _timeout_for(task: dict, g: dict) -> int:
    """The declared budget for THIS task's CLASS - read from the guard the class names, never a mode guess.

    T-154: the mapping mode -> class -> guard is DECLARED in config/agent_context.yaml (workstreams.mode_class
    and classes.<class>.timeout_guard). A oneshot therefore cannot inherit an agent's minutes by falling
    through a ternary, and a new mode cannot silently take the default: an undeclared mode is FATAL.

    A task may still declare its own `timeout_s`, which is how a KNOWN-fast task is kept honest: expecting
    a 6 s answer and killing at 120 s is 114 s of silence nobody reads.
    """
    own = task.get("timeout_s")
    if own not in (None, ""):
        if int(own) <= 0:
            raise SystemExit(f"FATAL: task {task.get('id')!r} declares timeout_s={own!r} - a budget of zero "
                             f"kills the task it was meant to bound")
        return int(own)
    spec = resolve_class(class_for_mode(str(task.get("mode", "oneshot"))))
    return int(g[str(spec["timeout_guard"])])


def _start_one(run_id: str, wid: str, g: dict, task: dict, note: str = "") -> None:
    """Launch one planned workstream as its declared CLASS, with that class's budget and stall floor.

    The stall threshold is no longer passed from here: the runner resolves it from the class the task
    declares, so a harness cannot be measured against a one-shot's 45 s threshold (BUG-828).
    """
    wsd = RUNS / run_id / f"fan_{wid}"
    mode = str(task.get("mode", "oneshot"))
    cmd = [sys.executable, str(RUNNER), "start", "--run", run_id, "--ws", f"fan_{wid}",
           "--timeout", str(_timeout_for(task, g)), "--class", class_for_mode(mode),
           "--cmd-file", str(wsd / "cmd.sh"), "--note", note]
    if g.get("kill_on_stall"):
        cmd.append("--kill-on-stall")
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def _running(run_id: str) -> int:
    """How many workstreams of this run are RUNNING right now (the pool cap is theirs)."""
    return sum(1 for r in _rows(run_id) if r["state"] == "RUNNING")


def start(run_id: str, watch: bool = True) -> int:
    """Start tasks under the DECLARED cap, then hand the run to the reaper.

    The reaper is what makes the declared budgets real for a run nobody is polling: a run that is
    started and walked away from is the exact shape of the 2026-10-15 stall (BUG-809).
    """
    g = guards()
    cap = int(conf().get("fanout", {}).get("max_parallel", 3))
    _rows(run_id)                       # reconcile before deciding what to launch
    started, waiting = 0, []
    for t in sorted([p for p in (RUNS / run_id).glob("fan_*") if p.is_dir()]):
        state = {}
        sp = t / "state.json"
        if sp.exists():
            try:
                state = json.loads(sp.read_text())
            except Exception as exc:  # reported, never swallowed (C16)
                print(f"FATAL: unreadable state for {t.name}: {type(exc).__name__}: {exc}")
                return FATAL
        if state.get("state") in ("RUNNING", "DONE", "FAILED", "TIMEOUT", "EMPTY", "STALLED"):
            continue
        if _running(run_id) >= cap:
            # The cap counts workstreams that are ALREADY RUNNING, and only those. Adding `started`
            # on top double-books every launch in this loop and silently strands the last task in
            # PENDING - measured live: 3 tasks, cap 3, started 2 (BUG-825).
            waiting.append(t.name)
            continue
        meta = t / "task.json"
        task = json.loads(meta.read_text()) if meta.exists() else {"mode": "oneshot"}
        _start_one(run_id, t.name.removeprefix("fan_"), g, task)
        started += 1
    print(f"started {started} (cap {cap})")
    if waiting:
        print(f"waiting on the declared cap of {cap}: {waiting} - retry/run will pick them up")
    if watch:
        budget = int(g["agent_timeout_s"]) + int(g["deadline_s"])
        subprocess.Popen([sys.executable, str(RUNNER), "watch", "--run", run_id, "--budget", str(budget)],
                         cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        print(f"reaper attached (budget {budget}s): timeouts and stalls are enforced without polling")
    return OK


RETRYABLE = ("FAILED", "EMPTY", "TIMEOUT", "STALLED")


def retry(run_id: str) -> int:
    """One bounded retry pass: a failed task is re-asked ONCE on a DIFFERENT declared model.

    Two rules make this a guard rather than a loop. (1) The retry model may not be the model that
    just failed - a second identical attempt duplicates the blindspot that produced the failure
    (R5's reasoning applied to delegation). (2) The attempt count is declared, so this can never
    become an unbounded restart loop that burns the pool.
    """
    g = guards()
    retry_on = set(g["retry_on"])
    fallback = str(g["fallback_model"])
    cap = int(conf().get("fanout", {}).get("max_parallel", 3))
    launched = 0
    for t in sorted([p for p in (RUNS / run_id).glob("fan_*") if p.is_dir()]):
        if re.search(r"_r\d+$", t.name):
            continue                                  # already a retry: attempts are declared
        meta = t / "task.json"
        if not meta.exists():
            continue
        try:
            task = json.loads(meta.read_text())
        except Exception as exc:
            print(f"FATAL: unreadable task.json for {t.name}: {type(exc).__name__}: {exc}")
            return 0
        rows = {r["ws"]: r for r in _rows(run_id)}
        state = rows.get(t.name, {}).get("state")
        if state not in retry_on:
            continue
        # R5 FINDING, ACTED ON (review by gemma-4-E4B, 2026-10-15): a non-zero exit with a perfectly
        # USABLE answer is reported FAILED, which then bought a retry nobody needed. A usable answer
        # already in hand is judged by the verifier, not re-purchased from the pool.
        # T-163 REFINES "usable" for a shaped task: an answer that carries no finding is NOT usable, so it
        # IS re-asked - on a DIFFERENT declared model, which is the only thing that buys information when the
        # failure was the model's shape and not its clock (BUG-836).
        usable, why = answer_verdict(t / "20_answer.md", int(g["min_answer_chars"]),
                                     str(task.get("shape") or ""), task.get("files") or [])
        if usable:
            print(f"retry: {task['id']} is {state} but already has a usable answer ({why}) - NOT re-asked; "
                  f"judging it is the verifier's job (R5), not the pool's")
            continue
        if int(task.get("attempt", 1)) >= int(g["max_attempts"]):
            print(f"retry: {task['id']} is {state} and has spent its {g['max_attempts']} attempt(s) - not retried")
            continue
        if fallback == task["model"]:
            # NOT fatal to the run: this is a REFUSAL of one retry, and the run's honest exit is decided by the
            # receipt (a task with no usable answer still fails there). MEASURED 2026-10-15: the word "FATAL"
            # here printed a verdict the CODE never carried - an error leak in the instrument's own voice.
            print(f"retry refused: the retry model for {task['id']} ({fallback}) IS the model that failed - "
                  f"a second attempt by the same model adds no information (declare another fallback)")
            return 0
        if _running(run_id) >= cap:
            print(f"retry: {task['id']} waits - the pool cap of {cap} is in use")
            break
        wid = f"{task['id']}_r2"
        wsd = RUNS / run_id / f"fan_{wid}"
        wsd.mkdir(parents=True, exist_ok=True)
        (wsd / "00_prompt.txt").write_text((t / "00_prompt.txt").read_text())
        retried = dict(task, model=fallback, attempt=int(task.get("attempt", 1)) + 1, retry_of=t.name)
        # A retry does NOT inherit the per-task budget that just proved insufficient: re-asking the
        # same question with the same impossible clock is a way to spend the pool twice and call it
        # resilience. The attempt gets its mode's declared budget instead, and the relaxation is recorded.
        relaxed = retried.pop("timeout_s", None)
        retried["timeout_relaxed_from"] = relaxed
        _write_json(wsd / "task.json", retried)
        (wsd / "cmd.sh").write_text(_cmd_for(retried, str(wsd), g, fallback))
        _start_one(run_id, wid, g, retried, note=f"retry of {t.name} after {state}")
        print(f"retry: {task['id']} ({state}) re-asked on {fallback} as fan_{wid}")
        launched += 1
    return launched


def task_state(attempts: list[dict]) -> str:
    """A TASK's state, rolled up from its attempts: any usable answer makes it DONE.

    Reporting per-WORKSTREAM instead of per-TASK reads as failure when the run actually succeeded:
    the live proof printed "2/4 usable" for a run that answered all three questions, because the
    retried task's first attempt (TIMEOUT) and second attempt (DONE) were counted as two tasks.
    A receipt that under-reports success is as unusable as one that over-reports it.
    """
    if not attempts:
        return "PENDING"
    for a in attempts:
        if a["answer_usable"]:
            return "DONE"
    return attempts[-1]["state"]


def receipt(run_id: str) -> int:
    """Write the run's receipt and return an honest exit code (never a green light on a failure)."""
    rows = _rows(run_id)
    if not rows:
        print("FATAL: no workstreams in this run")
        return FATAL
    floor = int(guards()["min_answer_chars"])
    by_id: dict[str, dict] = {}
    for r in sorted(rows, key=lambda x: x["ws"]):
        wsd = RUNS / run_id / r["ws"]
        meta = {}
        if (wsd / "task.json").exists():
            try:
                meta = json.loads((wsd / "task.json").read_text())
            except Exception as exc:  # reported, never swallowed (C16)
                print(f"warn: unreadable task.json for {r['ws']}: {type(exc).__name__}: {exc}")
        ans = wsd / "20_answer.md"
        answer_text = ans.read_text(errors="replace") if ans.exists() else ""
        shape = str(meta.get("shape") or "")
        artefacts = [str(f) for f in (meta.get("files") or [])]
        ok, why = answer_verdict(ans, floor, shape, artefacts)
        # A DELIVERABLE WHOSE CITATIONS ARE REFUTED IS NOT A DELIVERABLE (BUG-721). The verdict above
        # cannot see it: a fabricated answer is long, exits 0 and reads DONE.
        cited, cdefs = citation_defects(answer_text) if answer_text else (0, [])
        # AND A LISTING OF TRUE LOCATIONS IS NOT A REVIEW (T-163/BUG-836), which the two checks above are
        # jointly blind to: every citation resolves and the answer is long. So the SHAPE is read here too -
        # the receipt may not report as usable what the workstream's own grader refused.
        sfind, sdefs = shape_defects(answer_text, shape, artefacts) if (answer_text and shape) else (0, [])
        tid = str(meta.get("id") or r["ws"])
        entry = by_id.setdefault(tid, {"id": tid, "state": "PENDING", "attempts": []})
        entry["attempts"].append({"ws": r["ws"], "state": r["state"], "model": meta.get("model"),
                                  "attempt": meta.get("attempt", 1), "elapsed_s": r["elapsed_s"],
                                  "idle_s": r.get("idle_s"), "terminal": r.get("terminal"),
                                  "answer_usable": ok, "answer_note": why,
                                  "shape": shape or None, "shape_findings": sfind if shape else None,
                                  "shape_defects": sdefs[:3],
                                  "citations_checked": cited, "citations_refuted": len(cdefs),
                                  "citation_defects": cdefs[:5]})
    for entry in by_id.values():
        entry["state"] = task_state(entry["attempts"])
    tasks = [by_id[k] for k in sorted(by_id)]
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t["state"]] = counts.get(t["state"], 0) + 1
    rec = {"run": run_id, "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "tasks": tasks,
           "counts": counts, "done": counts.get("DONE", 0), "total": len(tasks)}
    _write_json(RUNS / run_id / "98_receipt.json", rec)
    print(f"\nreceipt: temp/runs/{run_id}/98_receipt.json")
    for t in tasks:
        trail = " -> ".join(f"{a['state']}({a['model']})" for a in t["attempts"])
        print(f"  {t['id']:<20} {t['state']:<8} {len(t['attempts'])} attempt(s): {trail}")
    print(f"  {rec['done']}/{rec['total']} task(s) DONE")
    refuted = [(t["id"], a) for t in tasks for a in t["attempts"] if a.get("citations_refuted")]
    for tid, a in refuted:
        print(f"  REFUTED CITATION  {tid}/{a['ws']}: {a['citations_refuted']} refuted claim(s) across "
              f"{a['citations_checked']} citation(s) - the answer is not a deliverable")
        for d in a.get("citation_defects", [])[:2]:
            print(f"      {d}")
    # T-163: a shaped answer that carries no finding is reported in its own words, so the owner reads WHAT was
    # missing (a finding about a named artefact) and not only that something failed.
    for t in tasks:
        for a in t["attempts"]:
            if a.get("shape") and a.get("shape_defects"):
                print(f"  NOT A {str(a['shape']).upper()}  {t['id']}/{a['ws']}: {a['shape_defects'][0]}")
    if counts.get("RUNNING") or counts.get("PENDING"):
        return PENDING
    if refuted:
        return FATAL
    if rec["done"] < rec["total"]:
        return FATAL
    return OK


def run_task_file(tasks_file: pathlib.Path, run_id: str, deadline_s: int | None) -> int:
    """The guarded front door: plan -> start -> reap -> retry ONCE -> receipt. Bounded, always."""
    g = guards()
    deadline = int(deadline_s or g["deadline_s"])
    rc = plan(tasks_file, run_id)
    if rc != OK:
        return rc
    rc = start(run_id)
    if rc != OK:
        return rc
    t0 = time.time()
    _watch(run_id, deadline)
    left = max(30, deadline - int(time.time() - t0))
    # A task that waited on the pool cap has not had its turn yet: it is PENDING, not failed, and
    # leaving it behind is the silent gap the cap fix exists for. Sweep, then reap again.
    start(run_id, watch=False)
    retry(run_id)
    _watch(run_id, left)
    return receipt(run_id)


def verify(run_id: str, model: str, out: pathlib.Path) -> int:
    """Cross-family check of the collected answers (R5): the generator never checks itself."""
    g = guards()
    answers = []
    for t in sorted((RUNS / run_id).glob("fan_*")):
        a = t / "20_answer.md"
        meta = {}
        if (t / "task.json").exists():
            try:
                meta = json.loads((t / "task.json").read_text())
            except Exception as exc:  # reported, never swallowed (C16)
                print(f"warn: unreadable task.json for {t.name}: {type(exc).__name__}: {exc}")
        ok, why = answer_verdict(a, int(g["min_answer_chars"]),
                                 str(meta.get("shape") or ""), meta.get("files") or [])
        if ok:
            answers.append(f"## {t.name}\n{a.read_text(errors='replace')[:4000]}")
        elif a.exists():
            answers.append(f"## {t.name}\n[UNUSABLE ANSWER - {why}; the verifier must not treat this as "
                           f"a claim to check]")
    if not answers:
        print("FATAL: no answers to verify")
        return FATAL
    prompt = ("You are the VERIFIER, not the author. Below are independent answers produced by other "
              "models. For each: state whether it answers its question, quote the strongest evidence, "
              "and name any claim that the cited file would contradict. End with a table "
              "(task | verdict | one-line reason).\n\n" + "\n\n".join(answers))
    tmp = RUNS / run_id / "99_verify_prompt.txt"
    tmp.write_text(prompt)
    rc = subprocess.run([sys.executable, str(ASKER), "--model", model, "--prompt-file", str(tmp),
                         "--max-tokens", "1200", "--out", str(out)], cwd=str(ROOT)).returncode
    print("verify: " + ("ok" if rc == 0 else "FAILED") + f" -> {out}")
    return rc


def _served() -> set[str]:
    """The ids the engine is actually serving right now (never a list copied by hand - BUG-819)."""
    sys.path.insert(0, str(ROOT))
    try:
        import json as _json
        import urllib.request

        from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL
        req = urllib.request.Request(f"{OMLX_URL}/v1/models",
                                     headers={"Authorization": f"Bearer {OMLX_API_KEY}"})
        with urllib.request.urlopen(req, timeout=10) as fh:
            return {m["id"] for m in _json.loads(fh.read().decode()).get("data", [])}
    except Exception as exc:
        print(f"  [FAIL] the engine could not be asked what it serves: {type(exc).__name__}: {exc}")
        return set()


def _plan_models(tasks_file: pathlib.Path | None) -> list[str]:
    """The models a PLAN will use. No plan -> the empty list: history is not a plan (see doctor)."""
    if not tasks_file:
        return []
    import yaml
    return [str(t["model"]) for t in (yaml.safe_load(tasks_file.read_text()) or {}).get("tasks", [])]


def _served_check(models: list[str], served: set[str]) -> tuple[bool | None, str]:
    """Is every model the plan names actually served? UNDECIDED (None) when there is no plan."""
    if not models:
        return None, "no plan given - pass --tasks to decide this"
    unserved = sorted({m for m in models if served and m not in served})
    return (not unserved), (f"not served: {unserved}" if unserved else f"{len(set(models))} distinct model(s) checked")


def _retry_check(fallback: str, models: list[str]) -> tuple[bool | None, str]:
    """R5: is the retry target DIFFERENT from the model(s) the plan will use? None = no plan to ask about."""
    if not models:
        return None, f"no plan given - fallback is {fallback}, nothing to compare it against"
    return (fallback not in set(models)), f"fallback={fallback}"


def doctor(tasks_file: pathlib.Path | None = None) -> int:
    """Preflight: refuse to start a delegation that cannot be sound. Print every check, fail on any.

    This is the guard against the whole BLINDSPOT/GAP class the owner asked for - an unguarded run
    (missing config), an unserved model (a 404 discovered halfway), a stuck ledger (a RUNNING entry
    whose process is dead, which reads forever as "still working"), and a retry target that is the
    model that failed. An instrument that cannot decide says so and stops (D-3015).
    """
    bad = 0
    # ok is TRI-STATE: True / False / None. None means UNDECIDED - the check had nothing to decide,
    # which is a verdict and must be printed as one. A check that cannot decide must never print as
    # a pass (measured 2026-10-15: doctor read 7/8 against the LEDGER OF EVERY RUN EVER, so the R5
    # retry check failed against a historical plan while the check that "passed" had checked nothing).
    checks: list[tuple[str, bool | None, str]] = []

    def add(name: str, ok: bool | None, why: str = "") -> None:
        checks.append((name, ok, why))

    try:
        g = guards()
        add("fanout.guards is declared and complete (C12)", True,
            f"timeout={g['default_timeout_s']}s stall={g['stall_s']}s attempts={g['max_attempts']}")
    except SystemExit as exc:
        add("fanout.guards is declared and complete (C12)", False, str(exc).split("\n")[0])
        g = {}

    # T-163: a declared SHAPE is a requirement, so a half-declared or malformed one would be read as a pass by
    # every task that declares it - checked here because it is a property of the DECLARATION itself, decidable
    # with no plan in hand. TRI-STATE (BUG-826): with no shape declared there is nothing to decide, and a check
    # that decided nothing must never print as a pass.
    declared = answer_shapes()
    shape_faults = []
    for name in sorted(declared):
        try:
            shape_spec(name)
        except SystemExit as exc:
            shape_faults.append(str(exc).split("\n")[0])
    add("every declared answer shape is well-formed (T-163)", (not shape_faults) if declared else None,
        " | ".join(shape_faults) if shape_faults else f"{len(declared)} declared: {sorted(declared)}")
    try:
        controls = answer_shape_controls()
    except SystemExit as exc:
        controls, shape_faults = [], shape_faults + [str(exc).split("\n")[0]]
    missing_controls = [c["path"] for c in controls if not (ROOT / str(c["path"])).exists()]
    add("every declared answer-shape control EXISTS (T-163: a control whose subject is absent is a FAIL)",
        (not missing_controls and not shape_faults) if controls else None,
        f"absent: {missing_controls}" if missing_controls else f"{len(controls)} frozen control(s)")

    served = _served()
    add("the engine answers /v1/models", bool(served), f"{len(served)} served id(s)")
    # THE PLAN, OR NOTHING. R5's retry question ("is the retry model the model that failed?") is a
    # property of a PLAN. Reading it off every run directory instead asks the question of delegations
    # that already finished, so a fallback model that was some task's model YESTERDAY fails a doctor
    # run for a plan that does not exist yet - a false FAIL, which teaches an operator to ignore the
    # guard. With no plan in hand the honest verdict is UNDECIDED, and a check that decided nothing
    # must never print as a pass either.
    models = _plan_models(tasks_file)
    add("every task model is served by the engine", *_served_check(models, served))
    if g:
        fallback = str(g["fallback_model"])
        add("the retry model is not a task model (R5: a retry may not repeat the failing model)",
            *_retry_check(fallback, models))
        add("the retry model itself is served", bool(served) and str(g["fallback_model"]) in served,
            str(g["fallback_model"]))
    add("the run root is writable", RUNS.exists() and RUNS.is_dir(), str(RUNS))
    add("both instruments are present", RUNNER.exists() and ASKER.exists())

    # T-154: the CLASS bounds, recomputed from their declared sources by the one instrument that owns them.
    # rc 2 (a bound declared but not bound) is the SAME tri-state the harness contract uses: loud, and NOT a
    # false FAIL - the engine's per-model fallback is the live server's home, so binding it is the owner's act.
    cls = subprocess.run([sys.executable, str(RUNNER), "--check"], capture_output=True, text=True, cwd=str(ROOT))
    tail = [ln for ln in cls.stdout.strip().splitlines() if "CONTRADICTION" in ln or "OWNER-OWED" in ln]
    add("every class bound recomputes without a contradiction (T-154/BUG-828)", cls.returncode != 1,
        " | ".join(tail[:2]) or f"rc={cls.returncode}")
    if cls.returncode == 2:
        add("the harness class ceiling is DECLARED and NOT BOUND in the engine's own home (owner act)", None,
            " | ".join(tail[:1]) or "OWNER-OWED")

    stuck = []
    for r in _rows_present():
        if r["state"] == "RUNNING" and not r.get("process_alive"):
            stuck.append(f"{r['run']}/{r['ws']}")
    add("no workstream reads RUNNING with a dead process (a stuck ledger, BUG-809)", not stuck,
        f"stuck: {stuck[:5]}" if stuck else "ledger reconcilable")

    for name, ok, why in checks:
        verdict = "undecided" if ok is None else ("ok" if ok else "FAIL")
        print(f"  [{verdict}] {name}{'  ' + why if why else ''}")
        bad += 0 if ok is not False else 1
    und = sum(1 for _, ok, _ in checks if ok is None)
    decided_n = len(checks) - und
    print(f"doctor: {decided_n - bad}/{decided_n} decided" + (f", {und} undecided (nothing to decide)" if und else ""))
    return FATAL if bad else OK


def _rows_present() -> list[dict]:
    """Every workstream of every run, reconciled (the ledger's own view)."""
    if not RUNS.exists():
        return []
    proc = subprocess.run([sys.executable, str(RUNNER), "status", "--json"],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        return json.loads(proc.stdout or "[]")
    except Exception:
        return []


def selftest() -> int:
    """The controls that would have caught the three lies, plus the config guard itself."""
    g = guards()
    checks: list[tuple[str, bool]] = []
    tmp = RUNS / "selftest_fanout"
    tmp.mkdir(parents=True, exist_ok=True)

    stub = tmp / "stub.md"
    stub.write_text(STUB_PREFIX + ")\n")
    ok, why = answer_verdict(stub, 10)
    checks.append(("the_no_content_stub_is_NOT_an_answer", not ok))
    empty = tmp / "empty.md"
    empty.write_text("   \n")
    checks.append(("a_whitespace_answer_is_NOT_an_answer", not answer_verdict(empty, 10)[0]))
    short = tmp / "short.md"
    short.write_text("yes")
    checks.append(("an_answer_below_the_declared_floor_is_NOT_an_answer",
                   not answer_verdict(short, int(g["min_answer_chars"]))[0]
                   or int(g["min_answer_chars"]) <= 3))
    real = tmp / "real.md"
    real.write_text("x" * (int(g["min_answer_chars"]) + 5))
    checks.append(("a_real_answer_is_an_answer", answer_verdict(real, int(g["min_answer_chars"]))[0]))
    checks.append(("a_missing_answer_file_is_NOT_an_answer",
                   not answer_verdict(tmp / "nope.md", 10)[0]))

    # THE BUG-817 CLASS: the terminal word must be DERIVED, never asserted. A non-zero rc with a stub
    # answer must read EMPTY; a non-zero rc with a real answer must read FAILED, not DONE.
    rep = tmp / "10_report.md"
    rep.unlink(missing_ok=True)
    grade(stub, 1, int(g["min_answer_chars"]), rep)
    checks.append(("a_failed_oneshot_with_a_stub_reads_EMPTY_not_DONE",
                   rep.read_text().startswith("TERMINAL: EMPTY")))
    rep.unlink(missing_ok=True)
    grade(real, 1, int(g["min_answer_chars"]), rep)
    checks.append(("a_failed_oneshot_with_an_answer_reads_FAILED_not_DONE",
                   rep.read_text().startswith("TERMINAL: FAILED")))
    rep.unlink(missing_ok=True)
    grade(real, 0, int(g["min_answer_chars"]), rep)
    checks.append(("a_successful_oneshot_with_an_answer_reads_DONE",
                   rep.read_text().startswith("TERMINAL: DONE")))

    # NO COMMAND MAY CARRY A BAKED-IN VERDICT (the exact defect: `TERMINAL: DONE - rc=$?`).
    cmd = _cmd_for({"id": "x", "mode": "oneshot", "max_tokens": 8}, "/tmp", g, "M")
    checks.append(("no_generated_command_asserts_its_own_terminal_word",
                   "TERMINAL: DONE" not in cmd and "_grade" in cmd))
    checks.append(("every_generated_command_grades_the_answer_it_got", "--min-chars " in cmd))
    checks.append(("the_whole_run_is_bounded_by_a_deadline_the_parent_obeys",
                   int(g["deadline_s"]) > 0))
    checks.append(("a_oneshot_is_budgeted_FAR_MORE_TIGHTLY_than_an_agent_loop",
                   _timeout_for({"mode": "oneshot"}, g) < _timeout_for({"mode": "agent"}, g)))
    checks.append(("the_oneshot_budget_is_not_a_blanket_1800s",
                   _timeout_for({"mode": "oneshot"}, g) <= 300))
    # T-154: the harness class is measured against ITS OWN threshold, its deployment is the ENGINE's, and
    # its transcript binding is the RUNNER's - never a literal path baked into a command.
    spec = resolve_class(class_for_mode("harness"))
    longest = float((spec.get("evidence") or {}).get("longest_turn_measured_s") or 0)
    checks.append(("a_harness_is_measured_against_a_threshold_above_its_longest_measured_turn_T154",
                   longest > 0 and float(spec["stall_s"]) > longest))
    checks.append(("the_harness_class_is_not_measured_against_a_one_shot_threshold_T154",
                   int(spec["stall_s"]) > int(g["stall_s"])))
    hcmd = _cmd_for({"id": "h", "mode": "harness"}, "/tmp", g, "M")
    row = _job_row(class_for_mode("harness"))
    launch = str((conf().get("engine") or {}).get("launch_cli") or "")
    checks.append(("a_harness_command_is_launched_through_the_ENGINE_own_wiring_T154",
                   launch in hcmd and f"launch {row['harness']}" in hcmd))
    checks.append(("a_harness_command_bakes_in_no_transcript_path_T154",
                   "PI_CODING_AGENT_DIR" not in hcmd and str(RUNS) not in hcmd))
    checks.append(("a_harness_command_is_graded_like_every_other_answer", "_grade" in hcmd and "TERMINAL:" not in hcmd))
    checks.append(("the_harness_and_the_agent_share_a_class_but_a_oneshot_does_not_T154",
                   class_for_mode("harness") == class_for_mode("agent") != class_for_mode("oneshot")))
    try:
        class_for_mode("SELFTEST-NO-SUCH-MODE")
        checks.append(("an_undeclared_mode_is_FATAL_in_the_front_door_too_T154", False))
    except SystemExit:
        checks.append(("an_undeclared_mode_is_FATAL_in_the_front_door_too_T154", True))
    checks.append(("the_retry_count_is_bounded", int(g["max_attempts"]) >= 1))
    checks.append(("a_retried_task_cannot_be_retried_again_by_construction",
                   r'if re.search(r"_r\d+$", t.name)' in pathlib.Path(__file__).read_text()))
    # The receipt must roll attempts up to the TASK, or a successful retry is reported as a failure.
    checks.append(("a_task_that_succeeded_on_its_retry_reads_DONE_not_TIMEOUT",
                   task_state([{"state": "TIMEOUT", "answer_usable": False},
                               {"state": "DONE", "answer_usable": True}]) == "DONE"))
    checks.append(("a_task_whose_attempts_all_failed_reads_its_last_attempt",
                   task_state([{"state": "EMPTY", "answer_usable": False},
                               {"state": "FAILED", "answer_usable": False}]) == "FAILED"))
    checks.append(("a_task_with_no_attempt_yet_reads_PENDING", task_state([]) == "PENDING"))
    # R5 finding: a task that already holds a usable answer must not buy a retry (the pool is a resource,
    # and the verifier - not the pool - decides whether a usable-but-odd answer is good enough).
    checks.append(("a_usable_answer_is_not_re_bought_from_the_pool",
                   "already has a usable answer" in pathlib.Path(__file__).read_text()))
    # The cap may not double-book a launch: counting `started` on top of the ledger stranded a task.
    # The literal is assembled at run time because a control may not CONTAIN what it forbids.
    cap_leak = "started" + " + _running"
    checks.append(("the_pool_cap_counts_each_running_workstream_exactly_once",
                   cap_leak not in pathlib.Path(__file__).read_text()))

    # A CHECK THAT DECIDED NOTHING MUST NOT READ AS A PASS (BUG-826). doctor was reading the LEDGER OF
    # EVERY RUN EVER as if it were the plan, so the R5 check failed against a historical plan while the
    # check beside it "passed" having checked nothing.
    checks.append(("a_doctor_with_no_plan_reads_UNDECIDED_not_FAIL", _retry_check("m", [])[0] is None))
    checks.append(("a_plan_whose_task_model_IS_the_retry_model_reads_FAIL", _retry_check("m", ["m"])[0] is False))
    checks.append(("a_plan_whose_task_model_differs_from_the_retry_model_reads_ok", _retry_check("m", ["n"])[0] is True))
    checks.append(("a_served_check_with_no_plan_reads_UNDECIDED", _served_check([], {"a"})[0] is None))
    checks.append(("a_served_check_still_fails_on_an_unserved_plan_model", _served_check(["ghost"], {"a"})[0] is False))

    # BUG-721, MADE MECHANICAL: a citation is a claim about a file, so it is checkable without a model.
    bad_ans = 'pipeline/subagent_fanout.py:1 `word = "DONE"` asserts the terminal word'
    checks.append(("a_fabricated_citation_is_refuted", len(citation_defects(bad_ans)[1]) == 1))
    src = (ROOT / "pipeline/subagent_fanout.py").read_text().splitlines()
    n = next(i for i, line in enumerate(src, 1) if "def grade(" in line)
    good_ans = f"see pipeline/subagent_fanout.py:{n} `def grade(` for the only writer of the word"
    checks.append(("a_true_citation_passes", citation_defects(good_ans)[1] == []))
    checks.append(("a_citation_past_the_end_of_the_file_is_refuted",
                   len(citation_defects("pipeline/subagent_fanout.py:999999 `x = 1`")[1]) == 1))
    checks.append(("a_citation_to_a_file_that_does_not_exist_is_refuted",
                   len(citation_defects("pipeline/no_such_module_xyz.py:3 `x = 1`")[1]) == 1))
    checks.append(("an_answer_with_no_citation_checks_nothing_not_passing",
                   citation_defects("the code looks fine to me")[0] == 0))
    checks.append(("a_prose_reference_is_never_read_as_a_quote",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n} for the grader")[1] == []))
    # BUG-831: the quote that sits on a LABELLED NEXT LINE must be tied to the citation, or a fabricated
    # "Exact Code:" walks through - which it did, in the R5 review of this very function.
    checks.append(("a_fabricated_quote_on_a_labelled_next_line_is_refuted",
                   len(citation_defects(f"File:line: pipeline/subagent_fanout.py (line {n})\n"
                                        'Exact Code: `word = "DONE"`')[1]) == 1))
    checks.append(("an_honest_quote_on_a_labelled_next_line_is_not_refuted",
                   citation_defects(f"File:line: pipeline/subagent_fanout.py (line {n})\n"
                                    "Exact Code: `def grade(`")[1] == []))
    checks.append(("a_fragment_on_an_UNLABELLED_next_line_is_not_guessed_at",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n}\n"
                                    "and `something_else_entirely` elsewhere")[1] == []))
    checks.append(("a_next_line_with_its_own_citation_is_never_borrowed",
                   citation_defects(f"see pipeline/subagent_fanout.py:{n}\n"
                                    "Exact Code: `def grade(` (pipeline/research_run.py:1)")[1] == []))
    checks.append(("a_line_naming_its_own_file_is_checked_against_THAT_file",
                   len(citation_defects("### 1. `pipeline/research_run.py`\n"
                                        "File:line: `pipeline/subagent_fanout.py` (line 1)\n"
                                        'Exact Code: `word = "DONE"`')[1]) == 1))

    # T-163/BUG-836: A CITATION LIST IS NOT A REVIEW. This is the pair the whole rule rests on: the citation
    # reader CERTIFIED the measured answer (82 checked, 0 refuted - every location exists), so the SHAPE reader
    # is the only thing that can refuse it - while a real finding about the same artefact must still PASS, or
    # the gate is a disabled guard.
    try:
        controls = answer_shape_controls()
    except SystemExit:
        controls = []
        checks.append(("the_declared_shape_controls_are_readable_T163", False))
    for ctl in controls:
        cp = ROOT / str(ctl["path"])
        if not cp.exists():
            checks.append((f"{ctl['name']}[subject_ABSENT]", False))
            continue
        cfind, cdefs = shape_defects(cp.read_text(errors="replace"), str(ctl["shape"]), ctl["artifact"])
        checks.append((str(ctl["name"]),
                       (cfind >= 1 and not cdefs) if str(ctl["expect"]) == "an_answer" else bool(cdefs)))
    checks.append(("at_least_one_shape_control_is_DECLARED_T163", bool(controls)))
    listing = "\n".join(f"pipeline/subagent_fanout.py:{i}" for i in (1, 2, 3)) + "\n"
    listing_file = tmp / "listing.md"
    listing_file.write_text(listing)
    checks.append(("a_citation_list_with_no_finding_is_NOT_an_answer_T163",
                   shape_defects(listing, "review", ["pipeline/subagent_fanout.py"])[1] != []))
    finding = (f"FINDING: pipeline/subagent_fanout.py:{n} is the only writer of the terminal word, but nothing "
               f"reads the shape of the answer, so a listing of locations is graded DONE. `def grade(` must "
               f"read it, or the run reports success for a review nobody wrote.")
    checks.append(("a_real_finding_citing_the_artefact_IS_a_review_T163",
                   shape_defects(finding, "review", ["pipeline/subagent_fanout.py"])[1] == []))
    checks.append(("a_finding_stated_on_the_NEXT_line_of_its_citation_is_read_T163",
                   shape_defects(f"pipeline/subagent_fanout.py:{n}\n"
                                 "  The grader never reads the answer's shape, so a listing is recorded as DONE.",
                                 "review", ["pipeline/subagent_fanout.py"])[1] == []))
    checks.append(("a_finding_that_cites_only_a_file_OUTSIDE_the_artefact_is_not_a_finding_T163",
                   shape_defects(f"FINDING: pipeline/research_run.py:{n} never bounds its budget, so a slow "
                                 f"turn outlives the wall.", "review",
                                 ["pipeline/subagent_fanout.py"])[1] != []))
    checks.append(("a_description_of_what_a_line_DOES_is_not_a_finding_T163",
                   shape_defects(f"pipeline/subagent_fanout.py:{n} is the function that writes the terminal "
                                 f"word of the workstream.", "review",
                                 ["pipeline/subagent_fanout.py"])[1] != []))
    checks.append(("a_finding_whose_location_does_not_EXIST_is_not_a_finding_T163",
                   shape_defects("pipeline/subagent_fanout.py:999999 fails and must be bounded (T-163)",
                                 "review", ["pipeline/subagent_fanout.py"])[1] != []))
    # THE FALSE NEGATIVE THE GATE'S OWN R5 RUN FOUND (2026-10-15, run t163_r5b): a model that is told which ONE
    # file it is reviewing names its location as a RANGE - "**338-342**" and "(lines 349-351)". A grammar that
    # reads only `path.py:111` refused a located, predicated finding as if no location had been given, which is
    # the costly direction (D-3022: an over-strict guard is a disabled guard). The attribution is allowed ONLY
    # for a bare reference when exactly ONE artefact is declared - and it must not let a listing through.
    _r = f"the most critical line is **{n}-{n + 4}**: this is wrong because the guard is never reached"
    checks.append(("a_BOLDED_line_RANGE_is_read_as_a_location_in_the_declared_artefact_T163",
                   shape_defects(_r, "review", ["pipeline/subagent_fanout.py"])[1] == []))
    checks.append(("a_line_RANGE_named_with_the_word_lines_is_read_T163",
                   shape_defects(f"see (lines {n}-{n + 4}): the check is never reached, so a bad answer passes",
                                 "review", ["pipeline/subagent_fanout.py"])[1] == []))
    checks.append(("a_bare_range_is_NOT_attributed_when_TWO_artefacts_are_declared_T163",
                   shape_defects(_r, "review", ["pipeline/subagent_fanout.py",
                                                "pipeline/research_run.py"])[1] != []))
    checks.append(("a_bare_line_with_NO_prose_beside_it_is_still_not_a_finding_T163",
                   shape_defects(f"**{n}-{n + 4}**\n", "review", ["pipeline/subagent_fanout.py"])[1] != []))
    checks.append(("a_range_whose_first_line_does_not_exist_is_not_a_finding_T163",
                   shape_defects("**999998-999999** fails and must be bounded", "review",
                                 ["pipeline/subagent_fanout.py"])[1] != []))
    checks.append(("the_same_answer_passes_ungated_and_FAILS_when_a_shape_is_declared_T163",
                   answer_verdict(real, int(g["min_answer_chars"]))[0]
                   and not answer_verdict(real, int(g["min_answer_chars"]), "review",
                                          ["pipeline/subagent_fanout.py"])[0]))
    rep.unlink(missing_ok=True)
    grade(listing_file, 0, int(g["min_answer_chars"]), rep, "review", ["pipeline/subagent_fanout.py"])
    checks.append(("a_long_answer_with_no_finding_reads_FAILED_and_not_EMPTY_T163",
                   rep.read_text().startswith("TERMINAL: FAILED")))
    try:
        shape_spec("T163-NO-SUCH-SHAPE")
        checks.append(("an_undeclared_shape_is_REFUSED_not_invented_T163", False))
    except SystemExit:
        checks.append(("an_undeclared_shape_is_REFUSED_not_invented_T163", True))
    checks.append(("the_shape_requirement_is_READ_from_the_declaration_and_never_restated_T163",
                   int(shape_spec("review")["min_findings"]) == int(answer_shapes()["review"]["min_findings"])))
    checks.append(("the_shape_requirement_is_DISCLOSED_to_the_model_T163",
                   "FINDING" in _prompt_for({"question": "q", "shape": "review",
                                             "files": ["pipeline/subagent_fanout.py"]}, 10)))
    shaped_cmd = _cmd_for({"id": "s", "mode": "oneshot", "max_tokens": 8, "shape": "review",
                           "files": ["pipeline/subagent_fanout.py"]}, "/tmp", g, "M")
    checks.append(("a_shaped_task_grades_with_its_shape_and_artefact_T163",
                   "--shape 'review'" in shaped_cmd
                   and "--artifact 'pipeline/subagent_fanout.py'" in shaped_cmd))
    checks.append(("an_UNshaped_task_still_generates_the_command_it_always_did_T163", "--shape" not in cmd))

    bad = 0
    for name, ok_ in checks:
        print(f"  [{'ok' if ok_ else 'FAIL'}] {name}")
        bad += 0 if ok_ else 1
    print(f"selftest: {len(checks) - bad}/{len(checks)}")
    return FATAL if bad else OK


def main(argv: list[str]) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="verb")
    d = sub.add_parser("doctor"); d.add_argument("--tasks")
    r = sub.add_parser("run"); r.add_argument("--tasks", required=True); r.add_argument("--run", required=True)
    r.add_argument("--deadline", type=int)
    p = sub.add_parser("plan"); p.add_argument("--tasks", required=True); p.add_argument("--run", required=True)
    s = sub.add_parser("start"); s.add_argument("--run", required=True); s.add_argument("--no-watch", action="store_true")
    for verb in ("status", "retry"):
        q = sub.add_parser(verb); q.add_argument("--run", required=True)
    v = sub.add_parser("verify"); v.add_argument("--run", required=True)
    v.add_argument("--model", required=True); v.add_argument("--out", required=True)
    gr = sub.add_parser("_grade"); gr.add_argument("--answer", required=True); gr.add_argument("--rc", required=True)
    gr.add_argument("--min-chars", required=True); gr.add_argument("--report", required=True)
    gr.add_argument("--shape", default="")
    gr.add_argument("--artifact", default="", help="comma-separated: the artefact(s) a shaped answer is about")
    ci = sub.add_parser("citations"); ci.add_argument("--answer", required=True)
    sh = sub.add_parser("shape"); sh.add_argument("--answer", required=True)
    sh.add_argument("--shape", required=True); sh.add_argument("--artifact", default="")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.verb == "_grade":
        return grade(pathlib.Path(args.answer), int(args.rc), int(args.min_chars), pathlib.Path(args.report),
                     str(args.shape), [a for a in str(args.artifact).split(",") if a.strip()])
    if args.verb == "citations":
        a = pathlib.Path(args.answer)
        if not a.exists():
            print(f"FATAL: no answer file at {a}")
            return FATAL
        checked, defects = citation_defects(a.read_text(errors="replace"))
        for d in defects:
            print(f"  REFUTED  {d}")
        if not checked:
            print("citations: none to check - this answer makes no checkable claim about a file")
            return PENDING
        print(f"citations: {checked} citation(s) checked, {len(defects)} refuted claim(s)")
        return FATAL if defects else OK
    if args.verb == "shape":
        a = pathlib.Path(args.answer)
        if not a.exists():
            print(f"FATAL: no answer file at {a}")
            return FATAL
        arts = [x for x in str(args.artifact).split(",") if x.strip()]
        findings, defects = shape_defects(a.read_text(errors="replace"), str(args.shape), arts)
        for d in defects:
            print(f"  NOT A {str(args.shape).upper()}  {d}")
        print(f"shape: {findings} finding(s) about {arts or '(no artefact declared)'}")
        return FATAL if defects else OK
    if args.verb == "doctor":
        return doctor(pathlib.Path(args.tasks) if args.tasks else None)
    if args.verb == "run":
        return run_task_file(pathlib.Path(args.tasks), args.run, args.deadline)
    if args.verb == "plan":
        return plan(pathlib.Path(args.tasks), args.run)
    if args.verb == "start":
        return start(args.run, watch=not args.no_watch)
    if args.verb == "status":
        rows = _rows(args.run)
        for r in rows:
            print(f"{r['ws']:<20} {r['state']:<8}{' STALLED' if r.get('stalled') else '        '}"
                  f" {r['elapsed_s']:>7.1f}s idle={r.get('idle_s', 0):>6.1f}s"
                  f" progress={r.get('progress_bytes', 0):>7}B")
        return OK
    if args.verb == "retry":
        return OK if retry(args.run) >= 0 else FATAL
    if args.verb == "verify":
        return verify(args.run, args.model, pathlib.Path(args.out))
    ap.print_help()
    return FATAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
