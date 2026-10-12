#!/usr/bin/env python3
"""scripts/r5_review_gate.py - deterministic layers FIRST, then ONE advisory reviewer (D-2962, BUG-738).

THE PROBLEM THIS RETIRES (measured, not asserted). R5 review was a single LLM pass. governance/r5_reviews.jsonl
holds 43 verdicts: 30 APPROVE / 6 REJECT / 4 INSUFFICIENT / 3 UNPARSED. Seven of 43 (16%) were not decisions at
all, and every UNPARSED was a TRUNCATION of the verdict JSON. Two of those modes are mechanical, so the model
was being asked questions a machine answers exactly and for free.

THE ORDER IS THE FIX:
  1. DETERMINISTIC (0 LLM calls, declared in config/r5_review_gate.yaml): syntax (compile), lint (ruff),
     C11/C12 (scripts/pre_commit_gate.py). A fatal layer FAILS CLOSED - the file is never sent to a reviewer,
     because a file that does not compile is not reviewable.
  2. ADVISORY: scripts/r5_code_review.py is INVOKED (never re-implemented) with the deterministic evidence
     attached as context, and a budget large enough that the verdict JSON cannot be truncated.

WHY A SEPARATE SCRIPT AND NOT A FLAG ON r5_code_review.py: the verdict rule (a verdict is evidence only when
that script produced it) must not move. This gate is an ORCHESTRATOR plus a receipt, and it restates no verdict
of its own (D-2646).

USAGE
  python3 scripts/r5_review_gate.py --file scripts/foo.py                 # deterministic + reviewer
  python3 scripts/r5_review_gate.py --file scripts/foo.py --no-llm        # deterministic only (offline / CI)
  python3 scripts/r5_review_gate.py --selftest                            # known-answer controls, no LLM, no network
Exit: 0 all deterministic pass and the reviewer APPROVEd | 1 a fatal layer failed or the reviewer REJECTed |
      2 the reviewer was indecisive (INSUFFICIENT / UNPARSED) - LOUD, and never readable as approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from fnmatch import fnmatch
from pathlib import Path

import yaml

REPO: Path = Path(__file__).resolve().parents[1]
CONFIG: Path = REPO / "config" / "r5_review_gate.yaml"
SKIP_MARKERS: tuple = ("no module named", "command not found", "not found")
STATUS_PASS: str = "PASS"
STATUS_FINDINGS: str = "FINDINGS"
STATUS_FAIL: str = "FAIL"
STATUS_NA: str = "N/A"
STATUS_SKIPPED: str = "SKIPPED"
VERDICT_LAYER_FAIL: str = "LAYER_FAIL"
VERDICT_BY_RC: dict = {0: "APPROVE", 1: "REJECT", 2: "INDECISIVE"}
VERDICT_NO_VERDICT: str = "INDECISIVE"
VERDICT_SIZE_GUARD: str = "INDECISIVE(SIZE_GUARD)"


def verdict_of(rc: int, journal_gained_verdict: bool) -> str:
    """The VERDICT RULE: an exit code is not a verdict (D-2962/BUG-738, hardened by BUG-746).

    A reviewer's exit code says HOW its process ENDED, not WHAT it decided. The model call can raise (measured
    2026-10-12: HTTP 400 from the oMLX server on a 152,853-char source), time out, or die after printing nothing,
    and every one of those exits non-zero - so an rc-only rule records a CRASH as a REJECT. The other direction is
    worse: an rc with no verdict text would be read as an APPROVAL. A verdict exists ONLY when
    scripts/r5_code_review.py WROTE one to its journal for this file and digest, so:
      rc 0 + a journal verdict -> APPROVE | rc 1 + a journal verdict -> REJECT
      rc 2 + a journal verdict -> INDECISIVE | NO journal verdict -> INDECISIVE, whatever the rc
    """
    if not journal_gained_verdict:
        return VERDICT_NO_VERDICT
    return VERDICT_BY_RC.get(rc, "INDECISIVE")


def journal_has_verdict(journal: Path, rel: str, digest16: str) -> bool:
    """Whether the reviewer's journal holds a verdict line for THIS file and digest (the verdict's ONE home)."""
    if not journal.exists():
        return False
    for line in journal.read_text(encoding="utf-8").splitlines()[-50:]:
        if not line.strip():
            continue
        try:
            entry: dict = json.loads(line)
        except Exception:  # noqa: BLE001 - a malformed line is not a verdict, and must not stop the scan
            continue
        if str(entry.get("file")) == rel and str(entry.get("sha256_16")) == digest16:
            return True
    return False


def load_config(path: Path = CONFIG) -> dict:
    """Load the gate declaration. A missing or partial config is a FAULT, never a silent default (C12/C16)."""
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: " + str(path) + " missing - the gate has no declaration to run")
    cfg: dict = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("layers", "tiers", "tier_by_path", "reviewer_script", "verdict_journal", "receipt", "task", "exit"):
        if key not in cfg:
            raise SystemExit("FAIL-CLOSED: config key missing: " + key)
    for name, tier in cfg["tiers"].items():
        if not str(tier.get("reviewer") or "").strip():
            raise SystemExit("FAIL-CLOSED: tier has no reviewer: " + name)
        if int(tier.get("max_tokens") or 0) < 256:
            raise SystemExit("FAIL-CLOSED: tier budget too small to hold a verdict: " + name)
        if int(tier.get("max_source_chars") or 0) < 1000:
            raise SystemExit("FAIL-CLOSED: tier has no usable source cap (max_source_chars): " + name
                             + " - without it a source too large for the reviewer's context is sent anyway and the"
                             + " resulting HTTP 400 is indistinguishable from a rejection (BUG-746)")
    return cfg


def tier_for(rel: str, cfg: dict) -> str:
    """Path -> tier by the declared rules; the LAST match wins so the config can declare a catch-all first."""
    tier = None
    for rule in cfg["tier_by_path"]:
        if fnmatch(rel, rule["match"]):
            tier = rule["tier"]
    if tier is None or tier not in cfg["tiers"]:
        raise SystemExit("FAIL-CLOSED: no declared tier for " + rel)
    return tier


def digest(path: Path) -> str:
    """First 16 hex chars of the file sha256 - the identity a receipt and a verdict share."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run_layer(layer: dict, target: str) -> dict:
    """Run ONE declared deterministic layer and classify it. Never raises: a layer is data."""
    name: str = layer["name"]
    if not any(fnmatch(target, pat) for pat in layer.get("applies") or ["*"]):
        return {"name": name, "status": STATUS_NA, "rc": None, "detail": "not applicable to this path"}
    argv: list = [str(a).replace("{file}", target) for a in layer["argv"]]
    if shutil.which(argv[0]) is None and layer.get("optional"):
        return {"name": name, "status": STATUS_SKIPPED, "rc": None, "detail": argv[0] + " not on PATH"}
    try:
        proc = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        if layer.get("optional"):
            return {"name": name, "status": STATUS_SKIPPED, "rc": None, "detail": argv[0] + " not found"}
        return {"name": name, "status": STATUS_FAIL, "rc": 127, "detail": argv[0] + " not found"}
    stderr_tail: str = (proc.stderr or "").strip().splitlines()[-1] if (proc.stderr or "").strip() else ""
    detail: str = stderr_tail or ((proc.stdout or "").strip().splitlines()[0] if (proc.stdout or "").strip() else "")
    if proc.returncode == 0:
        return {"name": name, "status": STATUS_PASS, "rc": 0, "detail": detail}
    if layer.get("optional") and any(m in (proc.stderr or "").lower() for m in SKIP_MARKERS):
        return {"name": name, "status": STATUS_SKIPPED, "rc": proc.returncode, "detail": detail}
    return {"name": name, "status": STATUS_FAIL if layer.get("fatal") else STATUS_FINDINGS,
            "rc": proc.returncode, "detail": detail}


def append_jsonl(path: Path, record: dict) -> None:
    """Append ONE receipt line (fsync'd). The receipt is evidence, so it is appended, never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + chr(10))
        fh.flush()


def evidence_file(rel: str, layers: list, cfg: dict) -> Path:
    """Write the MACHINE-PROVED facts the reviewer is told, so it never spends budget re-deciding them."""
    lines: list = [
        "DETERMINISTIC LAYERS ALREADY RUN BY scripts/r5_review_gate.py on " + rel + " (do not re-report these):",
    ]
    for layer in layers:
        lines.append("  - " + layer["name"] + ": " + layer["status"]
                     + (" (rc " + str(layer["rc"]) + ")" if layer["rc"] is not None else "")
                     + (" - " + layer["detail"][:200] if layer.get("detail") else ""))
    lines.append("")
    lines.append("Reviewer question: " + str(cfg["task"]).strip())
    lines.append("Your job is the RESIDUE: semantics, safety, irreversibility, silent failure, self-verification.")
    handle = Path(tempfile.gettempdir()) / ("r5_gate_evidence_" + rel.replace("/", "_") + ".txt")
    handle.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    return handle


def gate_one(rel: str, cfg: dict, tier_name: str, no_llm: bool, context: list, max_tokens: int) -> dict:
    """Run the layers for ONE file, then invoke the declared reviewer unless a fatal layer failed."""
    path: Path = (REPO / rel).resolve()
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: no such file: " + rel)
    layers: list = [run_layer(layer, rel) for layer in cfg["layers"]]
    fatal: list = [layer["name"] for layer in layers if layer["status"] == STATUS_FAIL]
    record: dict = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "gate": "r5_review_gate",
        "decision": cfg["decision"],
        "file": rel,
        "sha256_16": digest(path),
        "tier": tier_name,
        "reviewer": cfg["tiers"][tier_name]["reviewer"],
        "layers": layers,
        "fatal_layers": fatal,
    }
    for layer in layers:
        print("  layer  " + layer["name"].ljust(9) + layer["status"].ljust(9)
              + ("rc=" + str(layer["rc"]) if layer["rc"] is not None else "")
              + ("  " + layer["detail"][:110] if layer.get("detail") else ""))
    if fatal:
        record["verdict"] = VERDICT_LAYER_FAIL
        record["verdict_exit"] = cfg["exit"]["fail"]
        append_jsonl(REPO / cfg["receipt"], record)
        print("  VERDICT  " + VERDICT_LAYER_FAIL + " (fatal layer: " + ", ".join(fatal)
              + ") - no verdict recorded, the file is not reviewable until it compiles and satisfies C11/C12")
        return record
    if no_llm:
        record["verdict"] = "LAYERS_ONLY"
        record["verdict_exit"] = cfg["exit"]["approve"]
        append_jsonl(REPO / cfg["receipt"], record)
        print("  VERDICT  LAYERS_ONLY (--no-llm: the reviewer was not invoked, this is NOT an approval of the code)")
        return record
    # BUG-746 (deterministic, 0 model calls): a source too large for the reviewer's context is REFUSED HERE rather
    # than sent. MEASURED 2026-10-12: 98,664 chars returned a verdict (pipeline/stage6_commit.py, APPROVE) while
    # 152,853 chars (pipeline/stage4_merge.py) returned HTTP 400 from the oMLX server - a crash whose exit code was
    # recorded as REJECT with no verdict text and no journal line, i.e. the repo's largest module could not be
    # reviewed at all and the failure looked like a decision. The cap is declared per tier (config-first) and sits
    # UNDER the largest measured success rather than guessing the true context limit: refusing is fail-safe,
    # fabricating a verdict is not. The unit of review for such a file is the CHANGE (a diff).
    cap: int = int(cfg["tiers"][tier_name]["max_source_chars"])
    source_chars: int = path.stat().st_size
    if source_chars > cap:
        record["verdict"] = VERDICT_SIZE_GUARD
        record["verdict_exit"] = cfg["exit"]["indecisive"]
        record["size_guard"] = {"source_chars": source_chars, "max_source_chars": cap}
        append_jsonl(REPO / cfg["receipt"], record)
        print("  VERDICT  " + VERDICT_SIZE_GUARD + " (0 model calls): " + str(source_chars) + " chars exceeds the"
              " declared cap " + str(cap) + " for tier '" + tier_name + "'. NO verdict was recorded: this source"
              " cannot be sent to " + str(cfg["tiers"][tier_name]["reviewer"]) + " without the model returning"
              " HTTP 400, and a crash is not a decision. Review the CHANGE (its diff) instead of the whole file.")
        return record
    evidence: Path = evidence_file(rel, layers, cfg)
    reviewer_argv: list = [
        sys.executable, str(REPO / cfg["reviewer_script"]),
        "--file", rel,
        "--reviewer", str(cfg["tiers"][tier_name]["reviewer"]),
        "--task", str(cfg["task"]).strip(),
        "--max-tokens", str(max_tokens),
        "--out", str(cfg["verdict_journal"]),
        "--context-file", str(evidence),
    ]
    for extra in context:
        reviewer_argv += ["--context-file", str(extra)]
    print("  reviewer " + str(cfg["tiers"][tier_name]["reviewer"]) + "  budget " + str(max_tokens) + " tokens")
    proc = subprocess.run(reviewer_argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
    for line in (proc.stdout or "").strip().splitlines():
        print("  " + line)
    # BUG-746: a VERDICT exists only if the reviewer WROTE one for this file+digest - never because a process
    # exited 0 or 1. A crash, a timeout or an empty stdout must not be readable as a decision in either direction.
    gained: bool = journal_has_verdict(REPO / cfg["verdict_journal"], rel, str(record["sha256_16"]))
    record["verdict"] = verdict_of(proc.returncode, gained)
    record["verdict_exit"] = (cfg["exit"]["approve"] if record["verdict"] == "APPROVE"
                              else cfg["exit"]["fail"] if record["verdict"] == "REJECT"
                              else cfg["exit"]["indecisive"])
    record["reviewer_rc"] = proc.returncode
    record["verdict_recorded_by_reviewer"] = gained
    record["verdict_journal"] = cfg["verdict_journal"]
    if not gained:
        for line in (proc.stderr or "").strip().splitlines()[-6:]:
            print("  reviewer stderr: " + line[:200])
        record["reviewer_stderr_tail"] = (proc.stderr or "").strip().splitlines()[-1:] or []
        print("  NOTICE (C16): the reviewer recorded NO verdict for this file+digest, so this is INDECISIVE - an"
              " exit code says how the process ENDED, not what it decided. A crash must never be read as a"
              " rejection (BUG-746).")
    append_jsonl(REPO / cfg["receipt"], record)
    print("  receipt  " + cfg["receipt"] + " (append-only)")
    return record


def selftest() -> int:
    """Known-answer controls (D-355: a control must assert the state it is in). No LLM, no network."""
    cfg: dict = load_config()
    tmp: Path = Path(tempfile.mkdtemp(prefix="r5_gate_selftest_"))
    good: Path = tmp / "good.py"
    good.write_text("def add(a: int, b: int) -> int:" + chr(10) + "    return a + b" + chr(10), encoding="utf-8")
    truncated: Path = tmp / "truncated.py"
    truncated.write_text("def add(a: int, b: int) -> int:" + chr(10) + "    return a + (b" + chr(10), encoding="utf-8")
    syntax_layer: dict = next(layer for layer in cfg["layers"] if layer["name"] == "syntax")
    results: list = []

    def check(label: str, ok: bool, got: object) -> None:
        results.append(ok)
        print(("  PASS  " if ok else "  FAIL  ") + label + "  (" + str(got) + ")")

    check("a good file PASSES the syntax layer", run_layer(syntax_layer, str(good))["status"] == STATUS_PASS,
          run_layer(syntax_layer, str(good))["status"])
    check("a TRUNCATED file FAILS the syntax layer (this is the 3 UNPARSED verdicts of BUG-738)",
          run_layer(syntax_layer, str(truncated))["status"] == STATUS_FAIL,
          run_layer(syntax_layer, str(truncated))["status"])
    check("an undeclared path still resolves to a declared tier (catch-all present)",
          tier_for("governance/whatever.md", cfg) in cfg["tiers"], tier_for("governance/whatever.md", cfg))
    check("scripts/* resolves to the DEEP tier", tier_for("scripts/r5_review_gate.py", cfg) == "deep",
          tier_for("scripts/r5_review_gate.py", cfg))
    check("every tier declares a reviewer and a budget that can hold a verdict",
          all(str(t.get("reviewer") or "").strip() and int(t.get("max_tokens") or 0) >= 256 for t in cfg["tiers"].values()),
          {name: t["max_tokens"] for name, t in cfg["tiers"].items()})
    check("the Qwen-lineage model is DECLARED not-a-candidate (R5 family rule)",
          "Qwen3.8-27B-MLX-4bit" in (cfg["tiers"]["deep"].get("not_candidates") or []),
          cfg["tiers"]["deep"].get("not_candidates"))
    check("the verdict journal is the ONE home the reviewer script writes",
          cfg["verdict_journal"] == "governance/r5_reviews.jsonl", cfg["verdict_journal"])
    # BUG-746: the verdict rule itself, both directions of the lie it had. An exit code is how a process ENDED.
    check("an exit code WITH a reviewer verdict is read as it reads (0 APPROVE / 1 REJECT / 2 INDECISIVE)",
          [verdict_of(0, True), verdict_of(1, True), verdict_of(2, True)] == ["APPROVE", "REJECT", "INDECISIVE"],
          [verdict_of(0, True), verdict_of(1, True), verdict_of(2, True)])
    check("a NON-ZERO exit with NO verdict is INDECISIVE, never a fabricated REJECT (the 2026-10-12 crash)",
          verdict_of(1, False) == "INDECISIVE", verdict_of(1, False))
    check("a ZERO exit with NO verdict is INDECISIVE, never a fabricated APPROVE",
          verdict_of(0, False) == "INDECISIVE", verdict_of(0, False))
    check("an unknown exit with NO verdict is INDECISIVE",
          verdict_of(137, False) == "INDECISIVE", verdict_of(137, False))
    check("every tier declares a source cap that a reviewer can actually be sent (BUG-746)",
          all(int(t.get("max_source_chars") or 0) >= 1000 for t in cfg["tiers"].values()),
          {n: t.get("max_source_chars") for n, t in cfg["tiers"].items()})
    check("the declared cap admits the largest source this host has ever reviewed (98,664 chars, measured)",
          all(int(t["max_source_chars"]) >= 98664 for t in cfg["tiers"].values()),
          {n: t["max_source_chars"] for n, t in cfg["tiers"].items()})
    check("layers are declared with a why (no unexplained control)",
          all(str(layer.get("why") or "").strip() for layer in cfg["layers"]), len(cfg["layers"]))
    shutil.rmtree(tmp, ignore_errors=True)
    print("  controls " + str(sum(1 for r in results if r)) + "/" + str(len(results)) + " held")
    return 0 if all(results) else 1


def main() -> int:
    """Gate one or more files. Returns the WORST exit code across them."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", action="append", default=[], help="repo-relative file to gate (repeatable)")
    ap.add_argument("--tier", default=None, help="override the declared tier")
    ap.add_argument("--context-file", action="append", default=[],
                    help="extra file the reviewer needs to judge this change (repeatable)")
    ap.add_argument("--no-llm", action="store_true", help="deterministic layers only; NEVER an approval")
    ap.add_argument("--max-tokens", type=int, default=None, help="override the declared reviewer budget")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls, no LLM")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.file:
        ap.error("--file is required (or --selftest)")
    cfg: dict = load_config()
    worst: int = cfg["exit"]["approve"]
    for rel in args.file:
        tier_name: str = args.tier or tier_for(rel, cfg)
        if tier_name not in cfg["tiers"]:
            raise SystemExit("FAIL-CLOSED: undeclared tier: " + tier_name)
        max_tokens: int = args.max_tokens or int(cfg["tiers"][tier_name]["max_tokens"])
        print("== " + rel + "  tier=" + tier_name)
        record: dict = gate_one(rel, cfg, tier_name, args.no_llm, args.context_file, max_tokens)
        worst = max(worst, int(record.get("verdict_exit") or 0))
    return worst


if __name__ == "__main__":
    sys.exit(main())
