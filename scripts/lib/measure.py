#!/usr/bin/env python3
"""measure - every number must travel with its ruler (D-404, the RC-4/RC-5 gate).

WHY. BUG-391 is the purest instance in the register: a RATIFIED operating point (0.4741 on n=116) that
cannot be reproduced from anything on disk, because the artifact naming the 6 excluded rows is gone. BUG-334
(a pre-registered n is not the measurable n), BUG-336 (an agent's measurement claim is not evidence),
BUG-422/426 (a claim about a missing signal, measured on a derived copy) are the same mechanism: a number
with no population, no denominator, no artifact hash and no generator code hash is not a measurement - it is
a number, and it is indistinguishable from a good one.

THE INVARIANT: a metric is emitted through emit_metric() and carries {population, denominator, ruler_sha,
code_sha, ci}. A governance document may not quote a figure that has no envelope - check_metric_envelopes.py
enforces that, and this module is the only sanctioned producer.

Usage:
    from scripts.lib.measure import emit_metric
    emit_metric("depth_alpha_nominal", 0.4004, population="depth_axis_panel", denominator=148,
                ruler="config/agreement_floor.yaml")

Self-test:  python3 scripts/lib/measure.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import pathlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "governance" / "METRICS.jsonl"
FLOOR_PATH = REPO / "governance" / "METRICS.jsonl.floor"
FLOORS = REPO / "config" / "evidence_floors.yaml"
DOMAINS = REPO / "config" / "resolution_domains.yaml"
REQUIRED = ("name", "value", "population", "denominator", "ruler_sha", "code_sha", "stamp")
#: A resolver metric must also carry the domain it was resolved against (BUG-489). These are the fields that
#: make a coverage claim checkable; a number without them says "nothing was missed" without naming what was read.
DOMAIN_REQUIRED = ("identifier", "stores", "searched", "resolved")
#: BUG-490: the rails `just health` invokes, IN ORDER, DERIVED from the recipe itself. A checker has to know
#: where it sits relative to the rails that publish what it checks, or "has not run yet" and "never published"
#: are indistinguishable - which is how reconcile reported ITSELF as an unpublished metric on its first run.
JUSTFILE = REPO / "justfile"
INVOKE_RE = re.compile(r"^\s*python3\s+(\S+\.py)")
CHECKER = "scripts/lib/measure.py"


def health_chain() -> list[str]:
    """Every rail `just health` invokes, in order, read from the recipe (fail closed when unreadable)."""
    if not JUSTFILE.exists():
        raise SystemExit("FAIL-CLOSED (BUG-490): justfile is absent - the rail order cannot be derived, so "
                         "'not yet published' and 'never published' cannot be told apart")
    out: list[str] = []
    inside = False
    for line in JUSTFILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("health:"):
            inside = True
            continue
        if not inside:
            continue
        if line and not line[0].isspace():
            break
        m = INVOKE_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def chain_index(chain: list[str], rail: str) -> int:
    """The position of a rail in the chain, or -1 when the chain never invokes it."""
    return chain.index(rail) if rail in chain else -1


def floor_entry(store_rel: str) -> dict:
    """The WHOLE declared floor entry for a store, or {} when undeclared (BUG-491).

    A floor is not only a number: it also says WHICH records count (a control's fixture is not evidence) and
    which POPULATION the count is over (a record count over an append-per-run log is a run counter).
    """
    import yaml
    if not FLOORS.exists():
        raise SystemExit("FAIL-CLOSED (D-404/BUG-487): config/evidence_floors.yaml is absent - a registry with "
                         "no declared floor cannot tell 'nothing was missed' from 'nothing was read'")
    doc = yaml.safe_load(FLOORS.read_text(encoding="utf-8")) or {}
    for entry in (doc.get("journals") or []) + (doc.get("stores") or []):
        if str(entry.get("store")) == store_rel:
            return dict(entry)
    return {}


def counted_records(store_rel: str, records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split a store into the COUNTED population and the CONTROL-FIXTURE records (BUG-491).

    THE one place that decides what counts. A rail that counts raw records while another rail counts counted
    ones holds one fact in two homes: reconcile printed "20 >= 6" while verify_handoffs printed "6 >= 6" for
    the same store, and a reader could not tell which number was the floor's.
    """
    entry = floor_entry(store_rel)
    exclude = [str(o) for o in (entry.get("exclude_origins") or [])]
    counted = [r for r in records if str(r.get("origin")) not in exclude]
    fixtures = [r for r in records if str(r.get("origin")) in exclude]
    return counted, fixtures


def distinct_floor(entry: dict) -> tuple[str, int]:
    """The declared POPULATION floor as (field, minimum) - BUG-491b.

    A floor over an append-per-run log is a RUN counter: re-running the rail satisfies it without measuring
    anything. So a journal floor must name the field whose DISTINCT values are the population it has to cover.
    """
    field = str(entry.get("min_distinct_field") or "")
    return field, int(entry.get("min_distinct_values", -1))


def _store_count(p: Path, entry: dict, field: str) -> tuple[int, int, int]:
    """Count one declared store: (counted, excluded control fixtures, distinct values of `field`)."""
    if p.is_dir():
        return len([q for q in p.glob("*") if q.is_file()]), 0, 0
    if p.suffix == ".jsonl":
        recs = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        counted, fixtures = counted_records(str(entry.get("store")), recs)
        return len(counted), len(fixtures), (len({str(r.get(field)) for r in counted}) if field else 0)
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip()), 0, 0


def floor_check(store_rel: str) -> tuple[list[str], list[str], list[str]]:
    """Check ONE declared floor against reality: (drift, owed, rows). THE one definition of what counts.

    A floor is four facts, not one number: WHAT is counted (exclude_origins), the POPULATION the count is over
    (min_distinct_field), the minimum (min_records), and who enforces it (enforced_by). A store that is
    declared vacuous must stay vacuous: silence and emptiness look alike (BUG-487), so a vacuity declaration
    that reality now contradicts is DRIFT, not a stale comment.
    """
    entry = floor_entry(store_rel)
    if not entry:
        return ([store_rel + ": stored nowhere in config/evidence_floors.yaml - a store no declaration covers "
                 "reads as 'nothing to check' (BUG-487)"], [], [])
    drift: list[str] = []
    rows: list[str] = []
    p = REPO / store_rel
    floor = int(entry.get("min_records", entry.get("min_entries", -1)))
    field, need = distinct_floor(entry)
    if not (REPO / str(entry.get("enforced_by") or "")).exists():
        drift.append("floors: " + store_rel + " is declared to be enforced by " + str(entry.get("enforced_by"))
                     + ", which does not exist - a floor with no enforcer is a comment")
    if not p.exists():
        if entry.get("vacuous"):
            rows.append("floor " + store_rel + ": ABSENT (declared vacuous - "
                        + str(entry.get("vacuity_reason"))[:70] + "...)")
        else:
            drift.append("floors: declared store " + store_rel + " is ABSENT - 0 of 0 reads as ok and an "
                         "absent registry passes every check ever written (BUG-487)")
        return drift, [], rows
    n, n_fix, n_distinct = _store_count(p, entry, field)
    if entry.get("vacuous") and n > 0:
        drift.append("floors: " + store_rel + " declares vacuous: true but holds " + str(n) + " record(s) - the "
                     "vacuity declaration is STALE and must be replaced by a real floor (BUG-487); a store that "
                     "was legitimately empty and no longer is must say so")
    if floor == 0 and not entry.get("vacuous"):
        drift.append("floors: " + store_rel + " declares floor 0 with no vacuity declaration - silence and "
                     "emptiness look alike (BUG-487)")
    elif n < floor:
        drift.append("floors: " + store_rel + " holds " + str(n) + " < declared floor " + str(floor)
                     + ("" if not n_fix else " (" + str(n) + " counted of " + str(n + n_fix) + " record(s), "
                        + str(n_fix) + " control fixture(s) EXCLUDED - BUG-491)")
                     + " - a truncated store is not a clean rail (BUG-487)")
    if p.suffix == ".jsonl" and not field:
        drift.append("floors: " + store_rel + " declares NO min_distinct_field - a record count over an "
                     "append-per-run store is a RUN counter, satisfied by re-running rather than by measuring "
                     "(BUG-491)")
    elif field and need < 1:
        drift.append("floors: " + store_rel + " declares min_distinct_field " + repr(field) + " with no "
                     "min_distinct_values - a population floor with no minimum is a comment (BUG-491)")
    elif field and n_distinct < need:
        drift.append("floors: " + store_rel + " covers " + str(n_distinct) + " distinct " + field + "(s), below "
                     "the declared " + str(need) + " - the population this store must cover is the set of "
                     + field + "s, not the number of times a rail ran (BUG-491)")
    row = "floor " + store_rel + ": " + str(n) + " >= " + str(floor)
    if n_fix:
        row += " (" + str(n_fix) + " control fixture(s) EXCLUDED: counted population " + str(n) + " - BUG-491)"
    if field:
        row += ", " + str(n_distinct) + " distinct " + field + "(s) >= " + str(need)
    if entry.get("vacuous"):
        row += " (vacuous: " + str(entry.get("vacuity_reason"))[:60] + "...)"
    rows.append(row)
    return drift, [], rows


def contaminant_drift(store_rel: str, records: list[dict]) -> tuple[list[str], list[str], int, int]:
    """Split a journal into COUNTED records and CONTROL-FIXTURE records; enforce the shrink-only ceiling.

    BUG-491: a rail's known-answer control must not write into the journal it calibrates, because the fixture
    inflates the population its floor is counted over and the floor then cannot fail - the guard goes green by
    construction. Returns (drift, notes, counted, fixtures).
    """
    entry = floor_entry(store_rel)
    exclude = [str(o) for o in (entry.get("exclude_origins") or [])]
    counted, fixtures = counted_records(store_rel, records)
    drift: list[str] = []
    notes: list[str] = []
    ceil = entry.get("contaminant_ceiling") or {}
    if exclude and not ceil:
        drift.append(store_rel + ": declares exclude_origins " + str(exclude) + " but NO contaminant_ceiling - an "
                     "exclusion without a ceiling cannot separate a grandfathered fixture from a new one (BUG-491)")
    if ceil:
        origin = str(ceil.get("origin"))
        max_n = int(ceil.get("max", -1))
        n = len([r for r in records if str(r.get("origin")) == origin])
        sealed = ceil.get("sealed_set") or {}
        if sealed and "max" in ceil:
            # TWO HOMES FOR ONE BOUND (C12/C21, BUG-491). Declaring a count ceiling AND a sealed set is a
            # declaration that contradicts itself, and the looser rule would win by accident: the count would
            # silently re-legalise any new fixture while the sealed set says it is DRIFT.
            drift.append(store_rel + ": contaminant_ceiling declares BOTH max (" + str(ceil.get("max"))
                         + ") and a sealed_set - two homes for one bound, so the looser one wins by accident "
                         "(C12/C21, BUG-491). The sealed set IS the bound; a count that survives must be "
                         "max_records, which only CAPS the sealed population.")
        if sealed:
            # SEALED SET (owner gate accepted 2026-09-25). A count ceiling "grandfathers" a fixture: any control
            # record is legal while n <= max, so the allowance cannot tell a grandfathered record from a NEW one,
            # and 14 could silently become 13 or 15. A sealed set names the exact digests that were grandfathered,
            # so BOTH directions are falsifiable: an unsealed control record is DRIFT, and a sealed digest that has
            # VANISHED is DRIFT too (R-D410: a removed record cannot be audited). It is not lossless to move the
            # records, so nothing is moved - the allowance is only tightened.
            field = str(sealed.get("digest_field") or "sha256")
            want = [str(h) for h in (sealed.get("grandfathered_sha16") or [])]
            seen: dict[str, int] = {}
            for r in records:
                if str(r.get("origin")) != origin:
                    continue
                h = str(r.get(field) or "")[:16]
                seen[h] = seen.get(h, 0) + 1
                if h not in want:
                    drift.append(store_rel + ": a record with origin " + repr(origin) + " carries digest " + h
                                 + ", which is NOT in the sealed set - a control that is not sealed is writing "
                                 "into the ruler it calibrates (BUG-491). Seal it by decision, never by edit.")
            for h in want:
                if h not in seen:
                    drift.append(store_rel + ": sealed " + repr(origin) + " digest " + h + " has VANISHED from the "
                                 "store - a grandfathered record was deleted or rewritten, and a removed record "
                                 "cannot be audited (R-D410). Restore it; do not re-seal around the gap.")
            cap = int(ceil.get("max_records", -1))
            if cap >= 0 and n > cap:
                drift.append(store_rel + ": " + str(n) + " record(s) with origin " + repr(origin) + " exceed the "
                             "SHRINK-ONLY max_records " + str(cap) + " - the sealed set bounds WHICH digests are "
                             "legal, not how many times each may appear")
            notes.append(str(n) + " " + origin + " record(s), " + str(len(want)) + " sealed digest(s) present, "
                         + str(len(want) - sum(1 for h in want if h in seen)) + " sealed digest(s) MISSING")
            max_n = n  # the sealed set IS the bound; the count-ceiling path below must not re-judge it
        if max_n < 0:
            drift.append(store_rel + ": contaminant_ceiling for origin " + repr(origin) + " declares no max")
        elif n > max_n:
            drift.append(store_rel + ": " + str(n) + " record(s) with origin " + repr(origin) + " exceed the "
                         "SHRINK-ONLY ceiling " + str(max_n) + " - a control is writing into the ruler it "
                         "calibrates (BUG-491)")
        elif not sealed:
            # A SEALED declaration already printed its own note (which digests are present, which are missing).
            # Printing "14 <= ceiling 14" beside it would re-state the bound as a COUNT and re-teach the reader
            # the exact reading the sealed set replaced (BUG-491c: a rationale that does not match its code).
            notes.append(str(n) + " " + origin + " record(s) <= ceiling " + str(max_n))
    return drift, notes, len(counted), len(fixtures)


def min_records(store_rel: str) -> int:
    """The declared record floor for a store, or -1 when the store is not declared (fail closed upstream)."""
    entry = floor_entry(store_rel)
    if not entry:
        return -1
    return int(entry.get("min_records", entry.get("min_entries", -1)))


def declared_resolver_metrics() -> dict[str, dict]:
    """Map every metric a declared resolver must publish to its resolver (config/resolution_domains.yaml)."""
    import yaml
    if not DOMAINS.exists():
        raise SystemExit("FAIL-CLOSED (BUG-489): config/resolution_domains.yaml is absent - a resolver whose "
                         "domain is undeclared reports its join misses as facts about the world")
    doc = yaml.safe_load(DOMAINS.read_text(encoding="utf-8")) or {}
    out: dict[str, dict] = {}
    for res in doc.get("resolvers") or []:
        for name in res.get("metrics") or []:
            out[str(name)] = res
    return out


def _sha16_of_file(path: Path) -> str:
    """Return sha256[:16] of a repo-relative file, or 'absent' (a missing ruler is a fact, not a crash)."""
    p = pathlib.Path(path)
    p = p if p.is_absolute() else REPO / p
    if not p.exists():
        return "absent"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def code_sha() -> str:
    """Identify the generator CODE, not just the data: the HEAD commit plus a dirty flag (R14)."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True)
        head = r.stdout.strip() or "unknown"
        d = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True)
        return f"{head}{'+dirty' if d.stdout.strip() else ''}"
    except OSError as exc:  # no git in this environment: record it rather than guessing
        return f"no-git ({exc.__class__.__name__})"


def _count_records(path: Path) -> int:
    """Count non-empty records (matches read_metrics' skip-blank semantics)."""
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _read_floor() -> int | None:
    """Return the recorded record-count floor, or None if never written / corrupt.

    A missing/corrupt floor is NOT evidence of truncation — it is re-established on
    the next successful append (bootstrap). It disarms the guard for exactly ONE
    append, never permanently (BUG-638: the floor must not silently accept a shrink).
    """
    if not FLOOR_PATH.exists():
        return None
    try:
        return int(json.loads(FLOOR_PATH.read_text(encoding="utf-8")).get("record_count", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _write_all(fd: int, data: bytes) -> None:
    """Loop os.write until all bytes are written (C16 fail-loud; macOS caps a single call)."""
    view = memoryview(data)
    written = 0
    while written < len(view):
        n = os.write(fd, view[written:])
        if n <= 0:
            raise OSError(f"os.write stalled after {written}/{len(view)} bytes")
        written += n


def _write_floor(count: int) -> None:
    """Crash-safe floor write (tempfile → fsync → os.replace, C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(FLOOR_PATH.parent), prefix=".metrics.floor.", suffix=".tmp")
    try:
        payload = json.dumps({
            "record_count": int(count),
            "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, sort_keys=True)
        _write_all(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, FLOOR_PATH)


def emit_metric(name: str, value: float, *, population: str, denominator: int, ruler: str,
                ci: tuple[float, float] | None = None, note: str = "",
                domain: dict | None = None) -> dict:
    """
    Return and append a metric envelope. `population` names the set the number is over (never a bare count);
    `denominator` is the measurable n; `ruler` is the config/artifact the number is measured AGAINST.

    `domain` is REQUIRED for a metric declared in config/resolution_domains.yaml (BUG-489): it records what the
    resolver searched (identifier kind, stores, searched, resolved), so a coverage number inherits a stated
    premise instead of an unstated one. It is refused rather than defaulted - a defaulted domain is the defect.
    """
    if not population or denominator in (None, 0):
        raise SystemExit(f"FAIL-CLOSED (D-404): metric {name!r} has no population/denominator - "
                         f"a number without its ruler is not a measurement (BUG-391 class)")
    resolver = declared_resolver_metrics().get(name)
    if resolver is not None and domain is None:
        raise SystemExit(f"FAIL-CLOSED (BUG-489): {name!r} is a declared resolver metric "
                         f"(resolver {resolver.get('id')!r}, rail {resolver.get('rail')!r}) emitted with NO "
                         f"resolution domain - a coverage claim that does not name what it searched reports "
                         f"its join misses as facts about the world")
    if domain is not None:
        missing = [k for k in DOMAIN_REQUIRED if domain.get(k) in (None, "", [], {})]
        if missing:
            raise SystemExit(f"FAIL-CLOSED (BUG-489): the resolution domain for {name!r} is missing {missing} - "
                             f"identifier/stores/searched/resolved are all required")
    rec = {"name": name, "value": value, "population": population, "denominator": int(denominator),
           "ruler": ruler, "ruler_sha": _sha16_of_file(ruler), "code_sha": code_sha(),
           "ci": list(ci) if ci else None, "note": note, "domain": domain,
           "stamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # BUG-638: shrink-only floor guard. An append-only journal can only GROW; a
    # record-count floor recorded on the prior append makes a silent truncation
    # (the 817->70 loss) loud. Fail-closed BEFORE appending onto a truncated journal.
    _floor = _read_floor()
    _current = _count_records(OUT)
    if _floor is not None and _current < _floor:
        raise SystemExit(
            f"FAIL-CLOSED (BUG-638): {OUT.name} SHRANK {_floor} -> {_current} records — "
            f"append-only journal truncated. Restore from backup before re-emitting.")
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())  # C6: durable append, not left in the OS buffer
    _write_floor(_current + 1)
    return rec


def read_metrics() -> list[dict]:
    """Read the metrics journal, skipping nothing: a malformed line is a defect, so it raises."""
    if not OUT.exists():
        return []
    out = []
    for i, line in enumerate(OUT.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FAIL-CLOSED: {OUT.name} line {i} is not JSON: {exc}") from exc
    return out


def envelope_gaps() -> list[str]:
    """Return every stored metric missing a required envelope field, and every declared resolver metric whose
    most recent record carries no resolution domain (BUG-489: the premise must be published, not implied)."""
    gaps = []
    recs = read_metrics()
    for rec in recs:
        missing = [k for k in REQUIRED if rec.get(k) in (None, "")]
        if missing:
            gaps.append(f"{rec.get('name', '?')}: missing {missing}")
    declared = declared_resolver_metrics()
    latest: dict[str, dict] = {}
    for rec in recs:
        latest[str(rec.get("name"))] = rec
    chain = health_chain()
    here = chain_index(chain, CHECKER)
    for name, resolver in sorted(declared.items()):
        rec = latest.get(name)
        rail = str(resolver.get("rail"))
        pos = chain_index(chain, rail)
        if pos >= 0 and here >= 0 and pos > here:
            gaps.append(f"{name}: the chain runs its rail {rail} at position {pos}, AFTER this checker "
                        f"(position {here}) - the check reads a premise that rail has not written yet "
                        f"(BUG-490); move `measure --gaps` after it")
            continue
        if rec is None:
            if pos < 0:
                gaps.append(f"{name}: declared resolver metric (rail {rail}) is NEVER invoked by `just health` "
                            f"- a metric no rail emits is a comment (BUG-482 class)")
            else:
                gaps.append(f"{name}: declared resolver metric (rail {rail}, chain position {pos}) has NEVER "
                            f"been published - a declared coverage that nobody emits is a comment (BUG-482)")
        elif rec.get("domain") in (None, ""):
            gaps.append(f"{name}: latest record carries NO resolution domain (BUG-489) - re-run " + rail)
    return gaps


def selftest() -> int:
    """Assert that a ruler-less metric is refused, and that a good one carries its envelope."""
    try:
        emit_metric("selftest_bad", 1.0, population="", denominator=0, ruler="config/bench_preflight.yaml")
        raise AssertionError("a ruler-less metric was accepted")
    except SystemExit:
        pass
    print("ok measure selftest: a metric with no population/denominator is refused (BUG-391 class)")
    return 0


def main() -> int:
    """CLI: --selftest, or --gaps to print stored metrics missing their envelope."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--gaps", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    gaps = envelope_gaps()
    # FLOORS (BUG-487): 0 of 0 reads as "ok", so a registry that is absent or below its declared floor is DRIFT,
    # never a clean rail. ONE definition of what counts: this rail delegates to the SAME floor_check() that
    # scripts/reconcile.py calls, so two rails can never print different numbers for one store (C12/C21). This
    # block used to re-implement the METRICS count over RAW records - which diverges silently the moment the
    # store declares exclude_origins and a control fixture writes into the journal it calibrates (BUG-491).
    recs = read_metrics()
    METRICS_STORE = str(OUT.relative_to(REPO))
    fl_drift, _fl_owed, fl_rows = floor_check(METRICS_STORE)
    gaps.extend(fl_drift)
    if gaps:
        print("FAIL metric envelopes:")
        for g in gaps:
            print("  !!", g)
        return 1
    for r in fl_rows:
        print("  ok  " + r)
    entry = floor_entry(METRICS_STORE)
    n = len(recs)
    floor = int(entry.get("min_records", entry.get("min_entries", -1)))
    d_field, need_names = distinct_floor(entry)      # BUG-491b: a floor is over a POPULATION, not over runs
    counted, _fixtures = counted_records(METRICS_STORE, recs)   # the SAME population floor_check counted
    names = {str(r.get(d_field)) for r in counted} if d_field else set()
    if gaps:
        print("FAIL metric envelopes:")
        for g in gaps:
            print("  !!", g)
        return 1
    n_dom = len([r for r in recs if r.get("domain")])
    chain = health_chain()
    rails = sorted({str(v.get("rail")) for v in declared_resolver_metrics().values()})
    pos = ", ".join(r + "@" + str(chain_index(chain, r)) for r in rails)
    print(f"ok metric envelopes: {n} record(s) (floor {floor}), {len(names)} distinct {d_field or 'metric'}(s) "
          f"(floor {need_names}) carry population/denominator/ruler/code_sha; {n_dom} carry a declared "
          f"resolution domain (BUG-489); checker at chain position {chain_index(chain, CHECKER)}, declared "
          f"resolver rails [{pos}] - every one precedes it (BUG-490)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
