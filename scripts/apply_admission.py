#!/usr/bin/env python3
"""apply_admission.py — THE ADMIT APPLIER: put ONE library work into the corpus through S0 (T-183/D-3051/D-3068).

WHAT THIS ACT IS, AND WHAT IT IS NOT. The admission PLAN (`scripts/plan_admission.py`, T-181) classifies every
file in the declared library kind roots and proposes, for each candidate, the corpus path its own arrangement
implies. It ADMITS NOTHING. This file is the other half: the ONE writer that turns an ACCEPTED plan row into a
work the pipeline can read, and it DECIDES NOTHING.

    * it applies an ACCEPTED plan — a plan is not accepted because it exists, but because a separate file, signed
      by the owner, names it by DIGEST and says which rows are in scope (`governance/ADMISSION_ACCEPTED_*.yaml`);
    * it refuses a row absent from that signed set, a target that already exists with nothing accounting for it,
      a row whose source bytes changed since the plan was derived, and a row whose name a declared defect pattern
      still matches (an admitted name becomes the CORPUS NAME and the DOOR KEY — the repair rides first, T-176);
    * it writes NOTHING without `--apply` (dry run is the default, and the dry run is the owner's cost estimate);
    * it copies crash-safe (C6: tempfile -> fsync -> os.replace in the TARGET directory, so a crash leaves either
      the old tree or a complete new file — never a half one), and it never deletes anything (R-D410);
    * it receipts every row as it lands, one JSON line per row, appended and fsync'd immediately, so an
      interrupted batch is readable instead of ambiguous (D-3036). A row that S0 could not convert is a NAMED
      failure, never a silence (C16).

HOW THE BATCH IS RESUMED. A target that exists AND whose digest a receipt accounts for is `already_applied` — the
honest reading of a second run, not a refusal. A target that exists with NO receipt accounting for it is REFUSED:
something else put a work there, and this writer may not overwrite an act it cannot explain.

Exit: 0 nothing owed / every selected row already applied | 2 OWNER-OWED (no signed acceptance yet, or rows
waiting) — loud, never fatal (BUG-457) | 1 FATAL (an undeclared or unreadable declaration, a digest mismatch, a
refused row, a failed conversion, an escape from the corpus home).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import plan_admission  # noqa: E402 — the reader whose rows this writer applies (never a second derivation)
import census_source_names as census  # noqa: E402 — the library reader: roots, name classes, the cache join
from pipeline.book_metadata import sanitize_source_book  # noqa: E402 — the door's OWN key (D-3045)

POLICY = census.POLICY
RC_OK, RC_FATAL, RC_OWNER_OWED = 0, 1, 2
CHUNK = 1024 * 1024
#: A conversion output smaller than this is not a work (the same floor S0 applies to a native .md).
MIN_WORK_BYTES = 100
SCHEMA_VERSION = "1.0"
GEN_MODEL = "deterministic"  # R14: this act is not a model's — it is a repeated derivation, and it says so


class ApplierError(SystemExit):
    """Fail-closed: an undeclared, absent or unresolvable input is a fault, never a silent zero (C16/D-795)."""


def applier_rc(exc: SystemExit) -> int:
    """The exit code of a refusal — BUG-884: a message passed to SystemExit lands in `.code` as a STRING, so the
    first handler turned every governed refusal ("the acceptance pins digest X but Y hashes to Z") into
    `ValueError: invalid literal for int()`. Fail-closed held — nothing was written — but the operator got a
    traceback instead of the refusal, which is the one thing a refusal exists to say."""
    return exc.code if isinstance(exc.code, int) else RC_FATAL


# ---------------------------------------------------------------------------------------------------------------------
# THE DECLARATION — every path, prefix and vocabulary this writer obeys comes from its ONE home (C12)
# ---------------------------------------------------------------------------------------------------------------------
def applier_policy(doc: dict[str, Any]) -> dict[str, Any]:
    """The declared applier contract: where a signature lives, where a receipt lands, and what a signature carries."""
    decl = ((doc["source_library"].get("admission") or {}).get("applier"))
    if not isinstance(decl, dict) or not decl:
        raise ApplierError(
            f"FATAL: {POLICY}#source_library.admission.applier is not declared — the acceptance home, the receipt "
            f"home and the signature's required keys must come from the declaration, never from this writer (C12)"
        )
    for key in ("authority", "command", "accept_prefix", "accept_extension", "receipt_prefix",
                "receipt_extension", "accept_modes", "accept_required", "states"):
        if key not in decl:
            raise ApplierError(
                f"FATAL: {POLICY}#source_library.admission.applier does not declare {key!r} (C12: an absent "
                f"value is FATAL and never defaulted)"
            )
    return decl


def resolve_root(value: str) -> Path:
    """A declared path, relative to the repository root when it is not absolute (one rule for every declaration)."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else _PROJECT_ROOT / path


def newest(prefix: str, extension: str) -> Path | None:
    """The newest declared artifact by its own stamp — the plan and the signature are both dated files."""
    base = resolve_root(prefix)
    folder, stem = base.parent, base.name
    if not folder.is_dir():
        return None
    found = sorted(folder.glob(f"{stem}*{extension}"))
    return found[-1] if found else None


def sha256_bytes(path: Path) -> str:
    """The digest of a file's BYTES — the only identity a plan row and a receipt can be compared by."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def pipeline_commit() -> str:
    """R14: every persistent object names the code that produced it. A missing git is NAMED, not defaulted."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_PROJECT_ROOT), capture_output=True, text=True,
                             timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARN: git is unavailable ({type(exc).__name__}: {exc}) — the receipt will stamp 'unavailable'")
        return "unavailable"
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else "unavailable"


# ---------------------------------------------------------------------------------------------------------------------
# THE PLAN AND THE SIGNATURE
# ---------------------------------------------------------------------------------------------------------------------
def load_plan(path: Path) -> dict[str, Any]:
    """Read the accepted-candidate plan; a document that is not a plan is FATAL, never an empty worklist."""
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — any failure means this writer cannot know the plan
        raise ApplierError(f"FATAL: the plan {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(plan, dict) or not isinstance(plan.get("rows"), list):
        raise ApplierError(f"FATAL: {path} carries no 'rows' list — it is not an admission plan")
    if not plan["rows"]:
        raise ApplierError(f"FATAL: {path} carries ZERO candidate rows — an empty plan is not an accepted batch")
    return plan


def load_acceptance(path: Path, plan_path: Path, plan_digest: str, decl: dict[str, Any]) -> dict[str, Any]:
    """Read the owner's signature: the plan it names, the digest it pins, and the rows it puts in scope."""
    import yaml

    try:
        acc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — an unreadable signature signs nothing
        raise ApplierError(f"FATAL: the acceptance {path} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(acc, dict):
        raise ApplierError(f"FATAL: {path} is not a mapping — an acceptance names a plan and its rows")
    missing = [key for key in decl["accept_required"] if key not in acc]
    if missing:
        raise ApplierError(f"FATAL: {path} does not carry {missing} — a signature missing a field signs nothing")
    if acc["mode"] not in decl["accept_modes"]:
        raise ApplierError(
            f"FATAL: {path} declares mode {acc['mode']!r}, outside the declared vocabulary "
            f"{decl['accept_modes']} (C12)"
        )
    named = resolve_root(str(acc["plan"]))
    if named.resolve() != plan_path.resolve():
        raise ApplierError(
            f"FATAL: the acceptance names {named.name} but this run applies {plan_path.name} — a signature for "
            f"another plan authorises nothing (D-3034)"
        )
    if str(acc["plan_sha256"]).strip().lower() != plan_digest:
        raise ApplierError(
            f"FATAL: the acceptance pins digest {acc['plan_sha256']} but {plan_path.name} hashes to {plan_digest} "
            f"— the plan moved after it was signed, so the signature is about DIFFERENT bytes"
        )
    if acc["mode"] == "listed" and not isinstance(acc.get("rows"), list):
        raise ApplierError(f"FATAL: {path} declares mode=listed but carries no rows list")
    return acc


def acceptance_template(plan_path: Path, digest: str, rows: int) -> str:
    """A ready-to-sign acceptance, with the LIVE digest already in it — so signing cannot fail on a copied hash.

    The template is deliberately `mode: all` with `rows: []` and a comment naming the alternative: a signature that
    silently selected nothing would look like an authorisation while authorising nothing (D-3034).
    """
    import yaml

    try:  # a signature is more portable when it names the plan RELATIVE to the tree it governs
        plan_ref = plan_path.resolve().relative_to(_PROJECT_ROOT).as_posix()
    except ValueError:  # a plan outside the repo keeps its own absolute path
        plan_ref = str(plan_path)
    body = {
        "schema_version": SCHEMA_VERSION,
        "plan": plan_ref,
        "plan_sha256": digest,
        "accepted_by": "<your name>",
        "accepted_on": datetime.now(UTC).strftime("%Y-%m-%d"),
        "mode": "all",
        "rows": [],
    }
    return (
        f"# THE SIGNATURE THIS PLAN NEEDS (T-183/D-3068).\n"
        f"# It authorises {rows} row(s). `mode: all` covers them; for a TRANCHE change to `mode: listed` and list the\n"
        f"# `rel` labels exactly as the plan prints them.\n"
        f"# The digest below pins the BYTES: if the plan is re-derived, this signature stops matching and is REFUSED.\n"
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
    )


def selected_rows(plan: dict[str, Any], acc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """The rows this signature puts in scope. A row the signature names but the plan does not hold is FATAL."""
    rows = plan["rows"]
    if acc["mode"] == "all":
        return list(rows), []
    wanted = [str(item) for item in acc.get("rows") or []]
    by_rel = {str(row["rel"]): row for row in rows}
    unknown = [rel for rel in wanted if rel not in by_rel]
    if unknown:
        raise ApplierError(
            f"FATAL: the acceptance names {len(unknown)} row(s) the plan does not carry: {unknown[:3]} — an "
            f"approved row that cannot RESOLVE is a wish, not a grant (D-3034)"
        )
    seen: set[str] = set()
    chosen: list[dict[str, Any]] = []
    for rel in wanted:
        if rel not in seen:  # a duplicated line in a signature is one row, not two copies
            chosen.append(by_rel[rel])
            seen.add(rel)
    return chosen, []


def derive() -> dict[str, str]:
    """The CURRENT classification of every file, by the reader's own derivation — never a second opinion."""
    plan = plan_admission.build()
    return {str(row["rel"]): str(row["key"]) for row in plan["rows"]}


def verify_rows(rows: list[dict[str, Any]], derived: dict[str, str]) -> list[str]:
    """A row must STILL read as an admission candidate, by the same key, or it is not applied.

    This is the plan-keyed guard that a stale plan cannot walk through: the plan is a snapshot, the derivation is
    today, and the writer obeys the one that describes the tree it is about to write into.
    """
    faults: list[str] = []
    for row in rows:
        rel = str(row["rel"])
        if rel not in derived:
            faults.append(f"{rel}: no longer classifies as an admission candidate (the plan is stale for this row)")
        elif derived[rel] != str(row["key"]):
            faults.append(f"{rel}: the door's key moved ({derived[rel]!r} != {row['key']!r})")
    return faults


# ---------------------------------------------------------------------------------------------------------------------
# THE RECEIPT — an act that leaves no trace did not happen (D-3036)
# ---------------------------------------------------------------------------------------------------------------------
def receipt_path(decl: dict[str, Any], stamp: str | None = None) -> Path:
    """The declared receipt home, one JSONL per run (never a single file this writer keeps appending to)."""
    when = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return resolve_root(f"{decl['receipt_prefix']}{when}{decl['receipt_extension']}")


def append_receipt(path: Path, record: dict[str, Any]) -> None:
    """Append ONE line and fsync — a crash between two rows leaves the first row proved, not lost."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def receipt_index(decl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every target a previous run accounted for, by target path — the only thing that makes a rerun honest."""
    base = resolve_root(decl["receipt_prefix"])
    folder, stem = base.parent, base.name
    index: dict[str, dict[str, Any]] = {}
    if not folder.is_dir():
        return index
    for path in sorted(folder.glob(f"{stem}*{decl['receipt_extension']}")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            # C16: a receipt this writer cannot read is LOUD - it may not be treated as "no receipt".
            raise ApplierError(f"FATAL: receipt {path} cannot be read ({type(exc).__name__}: {exc})") from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ApplierError(f"FATAL: receipt {path} carries a line that is not JSON: {line[:80]!r}") from exc
            if record.get("state") in ("applied", "failed", "refused"):
                index[str(record.get("md_target") or "")] = record
                if record.get("container_target"):
                    index[str(record["container_target"])] = record
    return index


# ---------------------------------------------------------------------------------------------------------------------
# THE WRITE — crash-safe copy (C6), then S0 turns the container into the work
# ---------------------------------------------------------------------------------------------------------------------
def copy_atomic(source: Path, target: Path) -> None:
    """tempfile -> fsync -> os.replace IN THE TARGET DIRECTORY, so a crash leaves one whole file or none."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.stem}.", suffix=target.suffix + ".tmp")
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as src:
            shutil.copyfileobj(src, out, CHUNK)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)  # the only deletion here: this writer's OWN half-written temp file
        raise


def conversion_argv(container: Path, corpus: Path) -> list[str]:
    """The declared conversion entrypoint, given the row's OWN path below the corpus home (never a bare name)."""
    rel = container.relative_to(corpus)
    return [sys.executable, str(_PROJECT_ROOT / "pipeline" / "stage0_convert.py"), "--book", str(rel)]


def target_paths(row: dict[str, Any], corpus: Path) -> tuple[Path, Path]:
    """(container target, markdown target) for one row, both INSIDE the declared corpus home or FATAL."""
    md_target = Path(str(row["target"]))
    container_target = md_target if str(row["kind"]) == "md" else md_target.with_suffix(f".{row['kind']}")
    root = corpus.resolve()
    for path in (md_target, container_target):
        if not path.resolve().is_relative_to(root):
            raise ApplierError(
                f"FATAL: {path} escapes the declared corpus home {corpus} — a row may not write outside the one "
                f"tree the pipeline reads (D-3034)"
            )
    return container_target, md_target


def apply_row(row: dict[str, Any], corpus: Path, decl: dict[str, Any], index: dict[str, dict[str, Any]],
              *, apply: bool, convert: bool) -> dict[str, Any]:
    """Decide and (when `apply`) perform ONE row. Returns the receipt record; never raises for a refusal."""
    source = Path(str(row["path"]))
    container_target, md_target = target_paths(row, corpus)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plan_row": str(row["rel"]),
        "key": str(row["key"]),
        "source": str(source),
        "container_target": str(container_target),
        "md_target": str(md_target),
        "state": "",
        "reason": "",
    }
    if not source.is_file():
        record.update(state="refused", reason="the source file is gone (the plan names bytes that no longer exist)")
        return record
    source_digest = ""
    if int(row.get("bytes") or -1) != source.stat().st_size:
        record.update(state="refused",
                      reason=f"the source changed since the plan was derived ({row.get('bytes')} -> "
                             f"{source.stat().st_size} bytes)")
        return record
    # BUG-882: a DRY RUN PRICES the work. Hashing here read every source in full — 8.0 GiB over 479 rows, and on
    # this Dropbox-backed library an unmaterialised PDF STALLED the reading for minutes (row 309, 2026-10-17).
    # `stat` answers "did it change" in microseconds; the digest is EVIDENCE of the ACT and is taken only when acting.
    if apply:
        source_digest = sha256_bytes(source)
    record["source_sha256"] = source_digest
    #: The rename rides FIRST (T-176): an admitted name is the corpus name AND the door's key.
    patterns = plan_admission.name_patterns(census.policy(POLICY))
    if census.classify(source.name, patterns):
        record.update(state="refused", reason="the name still matches a declared defect pattern (repair first, T-176)")
        return record
    #: A target this writer cannot account for is not overwritten.
    for path, label in ((md_target, "markdown target"), (container_target, "container target")):
        if path.exists():
            prior = index.get(str(path)) or {}
            if prior.get("state") == "applied" and str(prior.get("md_sha256") or "") == sha256_bytes(path):
                record.update(state="already_applied", reason=f"the {label} is on disk and a receipt accounts for it")
                record["md_sha256"] = prior.get("md_sha256", "")
                return record
            record.update(state="refused",
                          reason=f"the {label} already exists and NO receipt accounts for it: {path}")
            return record
    if path_inside(corpus, source):
        record.update(state="already_applied", reason="the source ALREADY lives inside the corpus home")
        return record
    if not apply:
        record.update(state="would_apply", reason="dry run: nothing was written")
        return record
    try:
        copy_atomic(source, container_target)
    except OSError as exc:
        record.update(state="failed", reason=f"the crash-safe copy failed ({type(exc).__name__}: {exc})")
        return record
    record["container_sha256"] = sha256_bytes(container_target)
    if str(row["kind"]) == "md":
        record.update(state="applied", md_sha256=record["container_sha256"],
                      reason="native markdown: copied, no conversion stage reads it")
        return record
    if not convert:
        record.update(state="failed", reason="--no-convert was given: the container landed but is NOT a work yet")
        return record
    argv = conversion_argv(container_target, corpus)
    try:
        done = subprocess.run(argv, cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as exc:
        record.update(state="failed", reason=f"S0 could not be run ({type(exc).__name__}: {exc})")
        return record
    tail = " | ".join(line.strip() for line in (done.stdout or done.stderr or "").strip().splitlines()[-3:])
    if done.returncode != 0 or not md_target.is_file() or md_target.stat().st_size < MIN_WORK_BYTES:
        record.update(state="failed",
                      reason=f"S0 rc={done.returncode}, markdown {'absent' if not md_target.is_file() else 'too small'}"
                             f" — {tail[:400]}")
        return record
    record.update(state="applied", md_sha256=sha256_bytes(md_target), reason=f"S0 rc=0 — {tail[:200]}")
    return record


def stamp(record: dict[str, Any], header: dict[str, Any]) -> dict[str, Any]:
    """Carry the RUN's identity onto a row: a receipt line without the plan digest cannot be tied to a signature."""
    record.update(plan=header["plan"], plan_sha256=header["plan_sha256"], accept=header["accept"],
                  pipeline_commit=header["pipeline_commit"])
    return record


def path_inside(root: Path, path: Path) -> bool:
    """True when `path` already resolves inside `root` (a source in the corpus is not an admission)."""
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def shadowed_module_names(source: str) -> list[str]:
    """Local bindings that shadow a module-level callable of the SAME file — the defect class of BUG-881.

    WHY a class and not the instance: `stamp = datetime.now(...)` inside `run()` made the module's own
    `stamp(...)` call a `TypeError: 'str' object is not callable` at the moment the operator ran the ACT.
    No control caught it because the controls called `stamp()` directly — they tested the UNIT, the crash lived
    in the COMPOSITION. A name bound locally over a module-level callable is unreachable from that point on, and
    Python reports it only when that line finally executes. So the check is static, whole-file, and reads the
    file's own bytes: it names every function/class of module scope that some function binds over.
    """
    tree = ast.parse(source)
    module_level = {node.name for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    findings: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                targets: list[ast.expr] = list(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For)):
                targets = [node.target]
            else:
                continue
            bound.update(t.id for t in targets if isinstance(t, ast.Name))
        findings += [f"{fn.name}:{name}" for name in sorted((bound & module_level) - {fn.name})]
    return findings


# ---------------------------------------------------------------------------------------------------------------------
# THE RUN
# ---------------------------------------------------------------------------------------------------------------------
def run(plan_path: Path | None, accept_path: Path | None, *, apply: bool, convert: bool, limit: int | None,
        json_out: bool) -> int:
    """One batch: read the plan, read the signature, verify, then apply (or say exactly what would happen)."""
    doc = census.policy(POLICY)
    decl = applier_policy(doc)
    corpus = plan_admission.home_path(doc["source_library"]["arrangement"], "corpus_home")

    plan_path = plan_path or newest(str(plan_admission.admission_policy(doc)["plan_prefix"]), ".json")
    if plan_path is None or not plan_path.is_file():
        raise ApplierError(
            f"FATAL: no plan found under {plan_admission.admission_policy(doc)['plan_prefix']}*.json — derive one "
            f"first: {plan_admission.admission_policy(doc)['reading'].split('|')[2].strip()}"
        )
    plan = load_plan(plan_path)
    plan_digest = sha256_bytes(plan_path)

    accept_path = accept_path or newest(str(decl["accept_prefix"]), str(decl["accept_extension"]))
    if accept_path is None or not accept_path.is_file():
        rows = plan["rows"]
        total = sum(int(row.get("bytes") or 0) for row in rows)
        print(f"OWNER-OWED: no signed acceptance under {decl['accept_prefix']}*{decl['accept_extension']}")
        print(f"            {plan_path.name} holds {len(rows)} candidate row(s), {total / 2**20:.1f} MiB to copy")
        print(f"            a signature names the plan's digest ({plan_digest}) and the rows it puts in scope;")
        print(f"            nothing is written until one exists (mode is declared in {POLICY})")
        return RC_OWNER_OWED
    acc = load_acceptance(accept_path, plan_path, plan_digest, decl)
    rows, _ = selected_rows(plan, acc)
    if limit is not None:
        rows = rows[:limit]

    faults = verify_rows(rows, derive())
    if faults:
        for fault in faults:
            print(f"REFUSED  {fault}")
        raise ApplierError(
            f"FATAL: {len(faults)} accepted row(s) no longer read as admission candidates — re-derive the plan and "
            f"re-sign it (a plan is a snapshot; the tree is the authority)"
        )

    free = shutil.disk_usage(str(corpus)).free
    need = sum(int(row.get("bytes") or 0) for row in rows)
    if apply and free < need:
        raise ApplierError(f"FATAL: {need / 2**30:.2f} GiB to copy but {free / 2**30:.2f} GiB free in {corpus}")

    index = receipt_index(decl)
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")  # BUG-881: never `stamp` — that name is the FUNCTION below
    out_path = receipt_path(decl, run_stamp)
    header = {"schema_version": SCHEMA_VERSION, "gen_model": GEN_MODEL, "state": "run",
              "ts": run_stamp, "plan": str(plan_path), "plan_sha256": plan_digest,
              "accept": str(accept_path), "accept_sha256": sha256_bytes(accept_path),
              "mode": acc["mode"], "apply": apply, "convert": convert, "rows": len(rows),
              "bytes": need, "pipeline_commit": pipeline_commit()}
    if apply:
        append_receipt(out_path, header)

    counts: dict[str, int] = {}
    for row in rows:
        record = stamp(apply_row(row, corpus, decl, index, apply=apply, convert=convert), header)
        counts[record["state"]] = counts.get(record["state"], 0) + 1
        if apply:
            append_receipt(out_path, record)
        if json_out:
            print(json.dumps(record, ensure_ascii=False))
        else:
            mark = {"applied": "ADMIT", "already_applied": "  ok", "would_apply": "would",
                    "refused": " NO ", "failed": "FAIL"}.get(record["state"], record["state"].upper()[:5])
            detail = record["reason"] if record["state"] in ("refused", "failed") else record["md_target"]
            print(f"{mark} {record['plan_row'][:96]} -> {detail[:140]}")

    summary = {"state": "summary", "counts": counts, "receipt": str(out_path) if apply else None,
               "rows": len(rows), "bytes": need}
    if apply:
        append_receipt(out_path, summary)
        print(f"\n{counts} | receipt: {out_path}")
    else:
        print(f"\nDRY RUN {counts} | nothing written | --apply to perform | receipt would be {out_path}")

    if counts.get("failed") or counts.get("refused"):
        return RC_FATAL
    return RC_OK


# ---------------------------------------------------------------------------------------------------------------------
# CONTROLS — known answers only (BUG-492: a control nothing runs is a comment)
# ---------------------------------------------------------------------------------------------------------------------
def selftest() -> int:
    """Known-answer controls over a FIXTURE tree: no library file and no receipt of the owner's is touched."""
    checks: list[tuple[str, bool]] = []

    def expect(label: str, condition: bool, detail: str = "") -> None:
        checks.append((label, bool(condition)))
        if not condition:
            print(f"FAIL {label} {detail}")

    import yaml

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        corpus = tmp_root / "corpus"
        library = tmp_root / "library"
        (corpus / "DOMAIN 1 Test").mkdir(parents=True)
        (library / "epub" / "DOMAIN 1 Test").mkdir(parents=True)
        source = library / "epub" / "DOMAIN 1 Test" / "A Work.epub"
        source.write_bytes(b"EPUB-BYTES" * 100)
        md_source = library / "epub" / "DOMAIN 1 Test" / "A Note.md"
        md_source.write_text("# a note\n" + "text " * 200, encoding="utf-8")

        rows = [
            {"path": str(source), "rel": "books/epub/DOMAIN 1 Test/A Work.epub", "root": "books", "kind": "epub",
             "key": "a work", "bytes": source.stat().st_size,
             "target": str(corpus / "DOMAIN 1 Test" / "A Work.md")},
            {"path": str(md_source), "rel": "books/epub/DOMAIN 1 Test/A Note.md", "root": "books", "kind": "md",
             "key": "a note", "bytes": md_source.stat().st_size,
             "target": str(corpus / "DOMAIN 1 Test" / "A Note.md")},
        ]
        plan_file = tmp_root / "ADMISSION_PLAN_TEST.json"
        plan_file.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        digest = sha256_bytes(plan_file)
        decl = {"accept_modes": ["all", "listed"],
                "accept_required": ["schema_version", "plan", "plan_sha256", "accepted_by", "accepted_on", "mode"],
                "accept_extension": ".yaml", "receipt_prefix": str(tmp_root / "receipts" / "ADMISSION_APPLIED_"),
                "receipt_extension": ".jsonl", "command": "python3 scripts/apply_admission.py",
                "authority": "D-3068", "accept_prefix": str(tmp_root / "ADMISSION_ACCEPTED_"), "states": []}

        accept_file = tmp_root / "ADMISSION_ACCEPTED_TEST.yaml"
        base_accept = {"schema_version": "1.0", "plan": str(plan_file), "plan_sha256": digest,
                       "accepted_by": "selftest", "accepted_on": "2026-10-17", "mode": "all"}
        accept_file.write_text(yaml.safe_dump(base_accept), encoding="utf-8")

        # 1. a digest mismatch is FATAL
        bad = dict(base_accept, plan_sha256="0" * 64)
        bad_file = tmp_root / "BAD.yaml"
        bad_file.write_text(yaml.safe_dump(bad), encoding="utf-8")
        refused = False
        try:
            load_acceptance(bad_file, plan_file, digest, decl)
        except ApplierError:
            refused = True
        expect("a_plan_digest_mismatch_is_FATAL", refused)

        # 2. a row the signature names but the plan does not hold is FATAL
        listed = dict(base_accept, mode="listed", rows=["books/epub/DOMAIN 1 Test/GHOST.epub"])
        listed_file = tmp_root / "LISTED.yaml"
        listed_file.write_text(yaml.safe_dump(listed), encoding="utf-8")
        acc = load_acceptance(listed_file, plan_file, digest, decl)
        refused = False
        try:
            selected_rows({"rows": rows}, acc)
        except ApplierError:
            refused = True
        expect("a_row_absent_from_a_LISTED_acceptance_is_FATAL", refused)

        # 3. dry run writes nothing
        before = sorted(str(p) for p in tmp_root.rglob("*"))
        index = receipt_index(decl)
        dry = apply_row(rows[0], corpus, decl, index, apply=False, convert=False)
        after = sorted(str(p) for p in tmp_root.rglob("*"))
        expect("a_dry_run_writes_no_file_and_no_receipt", before == after and dry["state"] == "would_apply",
               dry["state"])

        # 3b. BUG-882: the DRY RUN prices the work — it does not READ it. A source rewritten to the SAME size with
        #     different bytes stays invisible to the dry run (empty digest) and is caught by the ACT, which takes
        #     the digest because the digest is EVIDENCE of the act. This is the control that a hash cannot creep
        #     back in front of `apply`: on this Dropbox-backed library it read 8.0 GiB and STALLED a pricing run.
        twin = library / "epub" / "DOMAIN 1 Test" / "A Twin.md"
        twin.write_text("AAAA" * 100, encoding="utf-8")
        twin_row = dict(rows[0], path=str(twin), rel="books/epub/DOMAIN 1 Test/A Twin.md", key="a twin", kind="md",
                        bytes=twin.stat().st_size, target=str(corpus / "DOMAIN 1 Test" / "A Twin.md"))
        twin.write_text("BBBB" * 100, encoding="utf-8")  # same size, different bytes
        index = receipt_index(decl)
        priced = apply_row(twin_row, corpus, decl, index, apply=False, convert=False)
        expect("a_dry_run_does_NOT_read_the_source_bytes",
               priced["state"] == "would_apply" and priced["source_sha256"] == "",
               (priced["state"], priced["source_sha256"]))
        index = receipt_index(decl)
        acted = apply_row(twin_row, corpus, decl, index, apply=True, convert=False)
        expect("the_ACT_takes_the_source_digest", acted["state"] == "applied"
               and acted["source_sha256"] == sha256_bytes(twin), (acted["state"], acted["source_sha256"][:12]))

        # 4. a defective name is refused even when the plan carries it — through the WRITER, not a lookup
        bad_source = library / "epub" / "DOMAIN 1 Test" / "A Work (z-lib.org).epub"
        bad_source.write_bytes(b"EPUB-BYTES" * 100)
        bad_row = dict(rows[0], path=str(bad_source), rel="books/epub/DOMAIN 1 Test/A Work (z-lib.org).epub",
                       key="a work (z-lib.org)", bytes=bad_source.stat().st_size,
                       target=str(corpus / "DOMAIN 1 Test" / "A Work (z-lib.org).md"))
        patterns = plan_admission.name_patterns(census.policy(POLICY))
        expect("the_declared_pattern_set_matches_a_marker_name", bool(census.classify(bad_source.name, patterns)))
        expect("a_clean_name_is_not_refused_by_the_pattern_set", not census.classify("A Work.epub", patterns))
        index = receipt_index(decl)
        defective = apply_row(bad_row, corpus, decl, index, apply=True, convert=False)
        expect("a_defective_name_is_REFUSED_even_if_the_plan_carries_it",
               defective["state"] == "refused" and "repair first" in defective["reason"], defective["state"])

        # 5. apply copies the bytes and KEEPS the source
        index = receipt_index(decl)
        done = apply_row(rows[1], corpus, decl, index, apply=True, convert=False)  # native markdown: no S0
        md_target = corpus / "DOMAIN 1 Test" / "A Note.md"
        expect("an_applied_row_copies_the_bytes_and_KEEPS_the_source",
               done["state"] == "applied" and md_target.read_bytes() == md_source.read_bytes()
               and md_source.is_file(), done["state"])

        # 6. the receipt accounts for it, so a rerun is already_applied, not a refusal
        tmp_receipt = receipt_path(decl, "TEST")
        append_receipt(tmp_receipt, done)
        index = receipt_index(decl)
        again = apply_row(rows[1], corpus, decl, index, apply=False, convert=False)
        expect("a_target_a_receipt_accounts_for_is_already_applied", again["state"] == "already_applied",
               again["state"])

        # 7. an unexplained target is REFUSED and its bytes survive
        unexplained = corpus / "DOMAIN 1 Test" / "A Work.md"
        unexplained.write_text("SOMEONE ELSE WROTE THIS", encoding="utf-8")
        index = receipt_index(decl)
        blocked = apply_row(rows[0], corpus, decl, index, apply=True, convert=False)
        expect("an_existing_target_with_no_receipt_is_REFUSED_and_its_bytes_survive",
               blocked["state"] == "refused" and unexplained.read_text(encoding="utf-8") == "SOMEONE ELSE WROTE THIS",
               blocked["state"])

        # 8. a source whose bytes changed is refused
        changed = dict(rows[1], bytes=1)
        index = receipt_index(decl)
        stale = apply_row(changed, corpus, decl, index, apply=False, convert=False)
        expect("a_source_whose_bytes_changed_is_REFUSED", stale["state"] == "refused", stale["state"])

        # 9. an escape from the corpus home is FATAL
        escaped = False
        try:
            target_paths(dict(rows[0], target=str(tmp_root / "elsewhere" / "x.md")), corpus)
        except ApplierError:
            escaped = True
        expect("a_target_outside_the_declared_corpus_home_is_FATAL", escaped)

        # 10. the conversion command names S0 and the row's OWN path below the corpus home
        argv = conversion_argv(corpus / "DOMAIN 1 Test" / "A Work.epub", corpus)
        expect("the_conversion_command_names_S0_and_the_row_own_path",
               argv[-1] == str(Path("DOMAIN 1 Test") / "A Work.epub") and argv[1].endswith("stage0_convert.py"),
               argv)

        # 11. the receipt carries what a later reader needs — including the RUN's identity, via stamp()
        stamped = stamp(done, {"plan": str(plan_file), "plan_sha256": digest, "accept": str(accept_file),
                               "pipeline_commit": "selftest"})
        expect("the_receipt_carries_source_target_key_and_digests",
               all(key in stamped for key in ("source", "container_target", "md_target", "key", "md_sha256",
                                              "pipeline_commit", "plan_sha256", "schema_version", "gen_model")),
               sorted(stamped))

        # 12. the writer owns no prefix of its own: both come from the declaration it was handed
        expect("the_accept_and_receipt_prefixes_come_from_the_declaration",
               str(resolve_root(decl["receipt_prefix"])).startswith(str(tmp_root))
               and str(resolve_root(decl["accept_prefix"])).startswith(str(tmp_root)))

        # 13. the printed template is a VALID signature for THIS plan, pinned to the live digest
        rendered = yaml.safe_load(acceptance_template(plan_file, digest, len(rows)))
        expect("the_acceptance_template_parses_and_pins_the_live_digest",
               rendered["plan_sha256"] == digest and rendered["mode"] == "all"
               and rendered["plan"] == str(plan_file), rendered)

        # 14. BUG-881: no local binding shadows a module-level callable of THIS file (the class, not the instance).
        #     The instance was `stamp = <str>` inside run(), which made the module's own stamp() uncallable — and
        #     control 11 below WOULD NOT SEE IT, because it called stamp() directly: the unit, not the composition.
        planted = ("def stamp(r, h):\n    return r\n\n\ndef run():\n    stamp = 'a string'\n"
                   "    return stamp({}, {})\n")
        expect("the_shadow_detector_FINDS_a_planted_shadow",
               shadowed_module_names(planted) == ["run:stamp"], shadowed_module_names(planted))
        expect("a_clean_module_reports_no_shadow", shadowed_module_names("def f():\n    return 1\n") == [])
        own = Path(__file__).read_text(encoding="utf-8")
        expect("THIS_file_binds_no_local_that_shadows_a_module_callable",
               shadowed_module_names(own) == [], shadowed_module_names(own))

        # 15. BUG-884: a REFUSAL prints its message and exits RC_FATAL — never a traceback. A message string handed
        #     to SystemExit lands in `.code`, so `int(exc.code)` turned the digest-mismatch refusal into a
        #     ValueError. Both branches are asserted: a message string AND a declared integer code.
        expect("a_refusal_exits_RC_FATAL_when_its_code_is_a_message",
               applier_rc(ApplierError("FATAL: the acceptance pins a different digest")) == RC_FATAL)
        expect("a_refusal_keeps_a_declared_INTEGER_code", applier_rc(ApplierError(RC_OWNER_OWED)) == RC_OWNER_OWED)

    passed = sum(1 for _label, ok in checks if ok)
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    print(f"\n{passed}/{len(checks)} controls")
    return RC_OK if passed == len(checks) else RC_FATAL


def main(argv: list[str] | None = None) -> int:
    """Dispatch the readings; an unknown flag is fatal rather than silently ignored (C16)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    if "--template" in argv:
        # The signature, pre-pinned to the plan's LIVE digest: the one step a human could get wrong is removed.
        doc = census.policy(POLICY)
        plan_path = newest(str(plan_admission.admission_policy(doc)["plan_prefix"]), ".json")
        if plan_path is None or not plan_path.is_file():
            print(f"FATAL: no plan found under {plan_admission.admission_policy(doc)['plan_prefix']}*.json")
            return RC_FATAL
        plan = load_plan(plan_path)
        print(acceptance_template(plan_path, sha256_bytes(plan_path), len(plan["rows"])), end="")
        return RC_OK
    parser = argparse.ArgumentParser(
        description="The admit applier (T-183): apply an ACCEPTED admission plan, crash-safe, dry run by default.")
    parser.add_argument("--plan", type=Path, help="the plan JSON (default: the newest under the declared prefix)")
    parser.add_argument("--accept", type=Path, help="the signed acceptance YAML (default: the newest)")
    parser.add_argument("--apply", action="store_true", help="write; without it NOTHING is copied or converted")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview from the same door: wins over --apply, writes nothing")
    parser.add_argument("--no-convert", action="store_true", help="copy the container only and leave it UNREAD")
    parser.add_argument("--limit", type=int, help="apply at most N rows (a tranche, counted)")
    parser.add_argument("--json", action="store_true", help="one JSON record per row")
    args = parser.parse_args(argv)
    try:
        return run(args.plan, args.accept, apply=args.apply and not args.dry_run, convert=not args.no_convert,
                   limit=args.limit, json_out=args.json)
    except ApplierError as exc:
        print(str(exc))
        return applier_rc(exc)


if __name__ == "__main__":
    sys.exit(main())
