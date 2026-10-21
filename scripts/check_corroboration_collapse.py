#!/usr/bin/env python3
"""T-119 - THE CORROBORATION COLLAPSE: how many ">=2 independent sources" rows are really ONE VOICE?

READ-ONLY RAIL. It measures, it never writes and it never repairs. The rule it re-measures lives in
`config/corroboration_collapse.yaml` (ONE HOME for the thresholds and for the census, C12/C12c).

WHY THIS EXISTS. The retired `borp_score` scalar (D-2994/D-2995, BUG-767) was a boolean wearing a
ratio's name. What replaced it - `is_convergent` plus the graded ISOR block - is a real measure, but it
is still a COUNT of SOURCES, and a source is not a VOICE: two works by the same author, or two excerpts
of one work, both count as two. T-119 asks how deep that collapse goes - and is required to be able to
answer "NO FINDING", because a measurement that cannot say "no finding" is not a measurement.

THE THREE LIMBS (2026-10-14: the limb reported BLOCKED probed the WRONG ARTIFACT):
  limb_identity  COMPUTABLE. `source_books` -> isor_score() (D2284/D2309). The rail IMPORTS the
                 existing home (`pipeline.schema_accessor.isor_score`); it does not reimplement it,
                 because one derived value has ONE home (D-2646). Reimplementing it here would create
                 a second truth about the same column - the exact defect class this work retires.
  limb_voice     COMPUTABLE (`--voice`). `n_voices` by a LEXICAL screen over the row's OWN segment
                 texts: identical normalised text, or bottom-k shingle containment at/above the bar.
                 $0, local CPU, no model, READ-ONLY. The limb that was BLOCKED probed for persisted
                 EMBEDDINGS; the artifact it needs is the segment TEXT, which the S1 chunk store
                 persists (stage1_chunk/<run>/checkpoint.jsonl, measured 730 MB on the canonical run).
                 All 148,831 referenced segment ids matched. It was never blocked - it was looking in
                 the wrong place, and that lesson is the reusable half of the finding (BUG-780).
                 It can CERTIFY a collapse and can NEVER certify independence, so its share is a
                 LOWER BOUND.
  limb_semantic  BLOCKED BY DESIGN (the RESIDUAL, not the answer). The embedding/NLI refinement for
                 the paraphrase+translation class limb_voice cannot see: the S1.5 index persists no
                 embeddings, so the rail PROBES and reports `blocked`. It must NEVER report `0 voices`
                 - ABSENT IS NOT ZERO (D-2957), and a fabricated 0 is precisely BUG-767. Now OPTIONAL:
                 the declared question was answered lexically at $0.

EXIT CODES (declared in the rule file, not here):
  0  finding measured   - the count-certified population carries a measurable collapse
  1  error              - fail-closed; the measurement could not be taken (C16)
  2  NO FINDING         - the falsifier fired: the count is NOT contaminated in this corpus

Usage:
    python3 scripts/check_corroboration_collapse.py --selftest
    python3 scripts/check_corroboration_collapse.py
    python3 scripts/check_corroboration_collapse.py --json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_PATH: Path = PROJECT_ROOT / "config" / "corroboration_collapse.yaml"
PIPELINE_CONFIG_PATH: Path = PROJECT_ROOT / "config" / "pipeline_config.yaml"

#: Ordered candidates for the committed store. Declared as a SEARCH, not a constant, so the rail
#: survives the store moving without a code edit - and reports which one it resolved.
DB_KEYS: tuple[str, ...] = ("db_path", "stage6_db")

EXIT_FINDING: int = 0
EXIT_ERROR: int = 1
EXIT_NO_FINDING: int = 2


# ── rule loading ─────────────────────────────────────────────────────────────


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping, failing closed (C16) rather than returning an empty default."""
    try:
        import yaml  # local import: keeps --selftest runnable without the pipeline venv
    except ImportError as exc:  # pragma: no cover - environment fault, not logic
        print(f"!! cannot import yaml: {exc}", file=sys.stderr)
        raise
    if not path.exists():
        raise FileNotFoundError(f"rule file missing: {path}")
    with path.open(encoding='utf-8') as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict):
        raise ValueError(f"rule file is not a mapping: {path}")
    return doc


def population_predicate(rule: dict[str, Any]) -> str:
    """The declared WHERE clause for the measured population.

    DECLARED, never defaulted: a population the rail chose for itself is a population the rail cannot
    be held to (BUG-588/D-2692 - a count carries its denominator or it is not a count).
    """
    pred = str(rule.get("population", {}).get("predicate", "")).strip()
    if not pred:
        raise ValueError("config/corroboration_collapse.yaml: population.predicate is not declared")
    return pred


def resolve_db(rule: dict[str, Any], override: str | None) -> Path:
    """Resolve the committed store, honouring an explicit --db, else the declared config keys."""
    if override:
        p = Path(override).expanduser()
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p
    cfg = load_yaml(PIPELINE_CONFIG_PATH)
    paths = cfg.get("paths", {}) if isinstance(cfg.get("paths"), dict) else {}
    for key in DB_KEYS:
        raw = paths.get(key)
        if raw:
            cand = Path(str(raw))
            return cand if cand.is_absolute() else PROJECT_ROOT / cand
    raise ValueError(f"no DB path found under paths{list(DB_KEYS)} in {PIPELINE_CONFIG_PATH}")


# ── store access ─────────────────────────────────────────────────────────────


def fetch_population(db: Path, predicate: str, fields: Sequence[str]) -> list[dict[str, Any]]:
    """Read the measured population as fb-shaped dicts for the ISOR home to consume.

    Read-only by construction: the SQL is a SELECT built from DECLARED names only.
    """
    if not db.exists():
        raise FileNotFoundError(f"store not found: {db}")
    cols = ", ".join(fields)
    sql = f"SELECT {cols} FROM fbs WHERE {predicate}"  # noqa: S608 - names are declared in the rule file
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(sql)]
    finally:
        conn.close()
    return [_coerce_list_fields(r) for r in rows]


def _coerce_list_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise JSON-array TEXT columns (the shape the store persists) into python lists."""
    out: dict[str, Any] = {}
    for key, val in row.items():
        if isinstance(val, str) and val.strip().startswith("["):
            try:
                parsed = json.loads(val)
                out[key] = parsed if isinstance(parsed, list) else [val]
                continue
            except json.JSONDecodeError:
                pass  # C16: not a JSON array after all - keep the raw string, do not swallow silently
        out[key] = val
    return out


# ── the measurement ──────────────────────────────────────────────────────────


def collapse_stats(isor_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the ISOR verdicts into the collapse census.

    PURE: it takes ISOR results and returns counts. It never touches the store or the ISOR home, so the
    falsifier and the selftest can exercise the same code path the live run uses.
    """
    total = len(isor_rows)
    one_author = sum(1 for r in isor_rows if int(r.get("n_authors", 0)) <= 1)
    one_domain = sum(1 for r in isor_rows if int(r.get("n_domains", 0)) <= 1)
    weak = sum(1 for r in isor_rows if str(r.get("rating", "")) == "weak")
    return {
        "population": total,
        "one_author": one_author,
        "one_domain": one_domain,
        "rated_weak": weak,
        "p_multi_author": (total - one_author) / total if total else 0.0,
        "p_multi_domain": (total - one_domain) / total if total else 0.0,
    }


def falsifier_verdict(stats: dict[str, Any], falsifier: dict[str, Any]) -> tuple[int, list[str]]:
    """Decide FINDING vs NO FINDING from the two declared controls.

    The falsifier is the whole point of the task: it must be ABLE to fire. When both controls clear
    their bar the count is not contaminated in this corpus and the rail says NO FINDING rather than
    manufacturing a finding out of a denominator.
    """
    bars: dict[str, float] = {}
    for ctl in falsifier.get("controls", []):
        bars[str(ctl.get("name"))] = float(ctl.get("no_finding_if_gte", 1.0))
    if not bars:
        raise ValueError("config/corroboration_collapse.yaml: falsifier.controls is not declared")

    below: list[str] = []
    for name, bar in bars.items():
        observed = float(stats.get(name, 0.0))
        if observed < bar:
            below.append(f"{name}={observed:.4f} < bar {bar:.4f}")
    if below:
        return EXIT_FINDING, below
    return EXIT_NO_FINDING, []


def probe_semantic_limb(rule: dict[str, Any]) -> dict[str, Any]:
    """Probe for the artifacts the `n_voices` limb needs. Report `blocked`, NEVER `0`.

    ABSENT IS NOT ZERO (D-2957). A missing index means we cannot count voices - it does not mean the
    rows have one voice. Conflating those two states is the BUG-767 defect class.
    """
    semantic = rule.get("semantic_limb", {})
    roots = [PROJECT_ROOT / str(r) for r in semantic.get("probe_roots", [])]
    globs = [str(g) for g in semantic.get("probe_globs", [])]
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in globs:
            for hit in root.glob(pattern):
                if hit.is_file():
                    found.append(str(hit.relative_to(PROJECT_ROOT)))
    state = "persisted" if found else "blocked"
    why = (
        f"{len(found)} embedding artifact(s) found - n_voices is computable"
        if found
        else (
            "the S1.5 index does not persist its embeddings (declared probe roots/globs found none), "
            "so n_voices cannot be counted read-only; persisting the index (or a re-embed pass) is a "
            "DECISION, not an edit. Reported BLOCKED, never 0"
        )
    )
    return {
        "state": state,
        "artifacts_found": len(found),
        "sample": found[:3],
        "threshold_from": semantic.get("similarity_threshold_from"),
        "min_voices_to_clear": semantic.get("min_voices_to_clear"),
        "why": why,
    }


# ── limb_voice: the LEXICAL screen (pure core + one read-only streaming wrapper) ──

_WORD = re.compile(r"[a-z0-9]+")


def normalized_words(text: str) -> list[str]:
    """Lower-case alphanumerics, single-spaced: the shape two copies of ONE VOICE share."""
    return _WORD.findall(str(text).lower())


def bottom_k_sketch(words: list[str], shingle: int, width: int) -> set[int]:
    """The bottom-`width` smallest 32-bit shingle hashes: a bottom-k MinHash sketch.

    Bottom-k (not k independent permutations) because it is one pass per shingle and its containment
    estimate is unbiased for OUR question - "is this text already inside that text?" - which is a
    containment question, not a symmetric similarity one.
    """
    if len(words) < shingle:
        return set()
    out: set[int] = set()
    for i in range(len(words) - shingle + 1):
        h = zlib.crc32(" ".join(words[i:i + shingle]).encode("utf-8"))
        if len(out) < width:
            out.add(h)
        elif h < max(out):
            out.discard(max(out))
            out.add(h)
    return out


def containment(left: set[int], right: set[int]) -> float:
    """Share of the SMALLER sketch present in the larger. PURE. Never raises on an empty sketch."""
    if not left or not right:
        return 0.0
    small, large = (left, right) if len(left) <= len(right) else (right, left)
    return len(small & large) / len(small)


def voice_stats(cells: dict[str, dict[str, dict[str, Any]]], bar: float, min_words: int,
                meta: dict[str, dict[str, str]] | None = None, served: str = "",
                advertised: str = "", pair_sink: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Count ONE-VOICE collapse from per-(row, work) evidence cells. PURE - no store, no model.

    `cells` is `{fb_id: {work: {"sk": set, "dg": set, "words": int}}}`: the row's OWN evidence, which
    is the doctrine T-120 established (independence is re-derived from the evidence the row holds,
    never from the run that happened to cluster it). A pair is COLLAPSED when the two sides are
    identical after normalisation (the `certain_class` - no threshold involved) or when containment
    is at/above `bar` with BOTH sides clearing the boilerplate screen.
    """
    hits: set[tuple[str, str]] = set()
    certain: set[tuple[str, str]] = set()
    row_best: dict[str, float] = {}
    pair_rows: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    pair_sim: dict[tuple[str, str], float] = {}
    for fb, works in cells.items():
        names = sorted(works)
        if len(names) < 2:
            continue
        best = 0.0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = works[names[i]], works[names[j]]
                if int(a.get("words", 0)) < min_words or int(b.get("words", 0)) < min_words:
                    continue
                if set(a.get("dg", ())) & set(b.get("dg", ())):
                    c, exact = 1.0, True
                else:
                    c, exact = containment(set(a.get("sk", ())), set(b.get("sk", ()))), False
                if c >= bar:
                    hit_key = (names[i], names[j])
                    hits.add(hit_key)
                    pair_rows[hit_key].add(fb)
                    pair_sim[hit_key] = max(pair_sim.get(hit_key, 0.0), c)
                    if exact:
                        certain.add(hit_key)
                best = max(best, c)
        row_best[fb] = best

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in hits:
        parent[find(a)] = find(b)
    groups = {find(n) for n in list(parent)}

    collapsed = {fb for fb, c in row_best.items() if c >= bar}
    stats: dict[str, Any] = {
        "rows_tested": len(row_best),
        "pairs_at_bar": len(hits),
        "pairs_identical_text": len(certain),
        "groups": len(groups),
        "rows_collapsed": len(collapsed),
        "collapsed_share": (len(collapsed) / len(row_best)) if row_best else 0.0,
        "bar": bar,
    }
    if meta:
        stats["served_rows_collapsed"] = sum(1 for fb in collapsed if meta.get(fb, {}).get("status") == served)
        stats["advertised_rows_collapsed"] = sum(
            1 for fb in collapsed if meta.get(fb, {}).get("epistemic_status") == advertised)
        stats["population_served"] = sum(1 for m in meta.values() if m.get("status") == served)
        stats["population_advertised"] = sum(
            1 for m in meta.values() if m.get("epistemic_status") == advertised)
    if pair_sink is not None:
        pair_sink.extend(
            {"a": a, "b": b, "identical": (a, b) in certain, "similarity": pair_sim.get((a, b), 1.0),
             "rows": sorted(pair_rows[(a, b)])}
            for a, b in sorted(hits))
    return stats


def voice_limb(rule: dict[str, Any], limit: int = 0,
               pair_sink: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Measure `voice_stats` against the declared corpus. READ-ONLY; streams the S1 chunk store.

    The store path is RESOLVED from the pipeline's own declaration (`stage1.checkpoint` under
    `S1_DIR/<CANONICAL_RUN>`), never typed twice: a second copy of a path is a second truth (C12).
    Every threshold comes from the rule file; nothing here is a literal.
    """
    limb = rule.get("lexical_limb", {})
    shingle = int(limb.get("shingle_words", 0))
    width = int(limb.get("sketch_width", 0))
    min_words = int(limb.get("min_words_per_side", 0))
    bar = float(limb.get("collapse_at_or_above", 1.0))
    if not (shingle and width and bar):
        raise ValueError("config/corroboration_collapse.yaml: lexical_limb is not fully declared (C12)")

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from pipeline.pipeline_paths import CANONICAL_RUN, S1_DIR, STAGE1_CHECKPOINT  # ONE HOME

    store = Path(str(STAGE1_CHECKPOINT))
    if not store.exists():
        store = S1_DIR / str(CANONICAL_RUN) / "checkpoint.jsonl"
    if not store.exists():
        return {"state": "blocked", "why": f"the S1 chunk store does not exist at {store}",
                "artifacts_found": 0, "rows_tested": None}

    rule_pop = rule.get("population", {})
    db = resolve_db(rule, None)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    pop = con.execute(
        f"SELECT fb_id, {rule_pop['status_field']}, {rule_pop['epistemic_field']}, source_segments "
        f"FROM {rule_pop['table']} WHERE {population_predicate(rule)}").fetchall()
    if limit:
        pop = pop[:limit]

    wanted: dict[str, list[str]] = collections.defaultdict(list)
    meta: dict[str, dict[str, str]] = {}
    for fb, status, epi, segs in pop:
        meta[str(fb)] = {"status": str(status or ""), "epistemic_status": str(epi or "")}
        for sid in _coerce_list_fields({"segs": segs}).get("segs", ()):
            wanted[str(sid)].append(str(fb))

    cells: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    matched = 0
    with store.open(encoding="utf-8") as fh:
        for line in fh:
            if '"segment_id"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            owners = wanted.get(str(obj.get("segment_id")))
            if not owners:
                continue
            matched += 1
            words = normalized_words(obj.get("text") or "")
            work = str(obj.get("source_book") or "?")
            digest = hashlib.blake2b(" ".join(words).encode("utf-8"), digest_size=8).hexdigest()
            sketch = bottom_k_sketch(words, shingle, width)
            for fb in owners:
                cell = cells[fb].setdefault(work, {"sk": set(), "dg": set(), "words": 0})
                cell["sk"] |= sketch
                cell["dg"].add(digest)
                cell["words"] += len(words)

    stats = voice_stats(dict(cells), bar, min_words, meta=meta,
                        served=str(rule_pop.get("served_value", "")),
                        advertised=str(rule_pop.get("advertised_value", "")), pair_sink=pair_sink)
    stats["state"] = "measured"
    stats["segments_matched"] = matched
    stats["store"] = str(store.relative_to(PROJECT_ROOT)) if str(store).startswith(str(PROJECT_ROOT)) else str(store)
    return stats


# ── selftest ─────────────────────────────────────────────────────────────────

CONTROL_LABELS: tuple[str, ...] = (
    "the_falsifier_can_say_no_finding",
    "the_falsifier_says_finding_when_the_population_collapses",
    "absent_artifacts_are_blocked_never_zero",
    "the_population_predicate_is_declared_not_defaulted",
    "the_census_is_arithmetic_on_its_own_denominator",
    "the_lexical_limb_certifies_a_collapse",
    "the_boilerplate_screen_ignores_a_short_side",
    "the_voice_census_is_arithmetic_on_its_own_denominator",
)


def selftest() -> int:
    """Exercise the pure parts with no store and no LLM. Returns EXIT_FINDING on success."""
    bars = {"controls": [{"name": "p_multi_author", "no_finding_if_gte": 0.95},
                         {"name": "p_multi_domain", "no_finding_if_gte": 0.95}]}
    checks: list[tuple[str, bool]] = []

    healthy = collapse_stats([{"n_authors": 2, "n_domains": 2, "rating": "strong"} for _ in range(20)])
    rc, below = falsifier_verdict(healthy, bars)
    checks.append((CONTROL_LABELS[0], rc == EXIT_NO_FINDING and below == []))

    collapsed = collapse_stats([{"n_authors": 1, "n_domains": 1, "rating": "weak"} for _ in range(20)])
    rc2, below2 = falsifier_verdict(collapsed, bars)
    checks.append((CONTROL_LABELS[1], rc2 == EXIT_FINDING and len(below2) == 2))

    probe = probe_semantic_limb({"semantic_limb": {"probe_roots": ["archive/__no_such_root__"],
                                                   "probe_globs": ["**/*.index"]}})
    # The property under test is a TYPE distinction, not a value: an unprobeable limb reports the
    # STRING "blocked", never the NUMBER 0. Absent must not be readable as zero (D-2957/BUG-767).
    checks.append((CONTROL_LABELS[2],
                   probe["state"] == "blocked" and isinstance(probe["state"], str)
                   and probe["artifacts_found"] == 0))

    try:
        population_predicate({"population": {}})
        declared_guard = False
    except ValueError:
        declared_guard = True
    checks.append((CONTROL_LABELS[3], declared_guard))

    mixed = collapse_stats([{"n_authors": 1, "n_domains": 2, "rating": "medium"},
                            {"n_authors": 3, "n_domains": 1, "rating": "weak"}])
    checks.append((CONTROL_LABELS[4],
                   mixed["population"] == 2 and mixed["one_author"] == 1 and mixed["one_domain"] == 1
                   and abs(mixed["p_multi_author"] - 0.5) < 1e-9))

    # limb_voice, PURE. (a) identical normalised text under two names is a COLLAPSE with no threshold
    # involved - the certain class; (b) a short side is boilerplate, not a shared voice, so the screen
    # must be able to say NOT collapsed; (c) the census divides by its OWN denominator.
    same = {"A": {"words": 400, "dg": {"x"}, "sk": {1, 2, 3}},
            "B": {"words": 400, "dg": {"x"}, "sk": {1, 2, 3}}}
    v1 = voice_stats({"fb1": same}, bar=0.80, min_words=120)
    checks.append((CONTROL_LABELS[5],
                   v1["rows_tested"] == 1 and v1["rows_collapsed"] == 1
                   and v1["pairs_identical_text"] == 1 and v1["groups"] == 1))

    short = {"A": {"words": 400, "dg": {"x"}, "sk": {1, 2, 3}},
             "B": {"words": 5, "dg": {"x"}, "sk": {1, 2, 3}}}
    v2 = voice_stats({"fb1": short}, bar=0.80, min_words=120)
    checks.append((CONTROL_LABELS[6], v2["rows_collapsed"] == 0 and v2["pairs_at_bar"] == 0))

    near = {"A": {"words": 400, "dg": {"a"}, "sk": set(range(1000, 1100))},
            "B": {"words": 400, "dg": {"b"}, "sk": set(range(1000, 1090)) | set(range(2000, 2010))}}
    twin = {"C": {"words": 400, "dg": {"y"}, "sk": {7, 8, 9}},
            "D": {"words": 400, "dg": {"y"}, "sk": {7, 8, 9}}}
    v3 = voice_stats({"fb1": near, "fb2": twin}, bar=0.80, min_words=120)
    checks.append((CONTROL_LABELS[7],
                   v3["rows_tested"] == 2 and v3["rows_collapsed"] == 2 and v3["groups"] == 2
                   and v3["pairs_identical_text"] == 1 and abs(v3["collapsed_share"] - 1.0) < 1e-9))

    ok = sum(1 for _, passed in checks if passed)
    for label, passed in checks:
        print(f"   {'ok ' if passed else 'RED'} {label}")
    print(f"{'ok' if ok == len(checks) else '!!'} corroboration-collapse selftest: {ok}/{len(checks)}")
    return EXIT_FINDING if ok == len(checks) else EXIT_ERROR


# ── main ─────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """CLI surface: read-only by construction - there is no write flag to add by accident."""
    p = argparse.ArgumentParser(description="T-119 corroboration collapse (read-only measurement)")
    p.add_argument("--selftest", action="store_true", help="exercise the pure parts, no store needed")
    p.add_argument("--json", action="store_true", help="emit the census as JSON")
    p.add_argument("--voice", action="store_true",
                   help="also measure limb_voice: streams the S1 chunk store (~730 MB, ~1 min, $0, read-only)")
    p.add_argument("--limit", type=int, default=0, help="rows to test (0 = all); shortens a --voice run")
    p.add_argument("--db", default=None, help="override the store path (default: config)")
    p.add_argument("--quiet", action="store_true", help="suppress the human summary")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Measure. Read-only. Fail-closed. Never reports a fabricated zero."""
    args = _build_parser().parse_args(argv)
    if args.selftest:
        return selftest()

    try:
        rule = load_yaml(CONFIG_PATH)
        predicate = population_predicate(rule)
        db = resolve_db(rule, args.db)
        fields = [str(rule["population"]["source_books_field"]), str(rule["population"]["domains_field"])]

        # The rail is invoked as a path, not as a module, so PROJECT_ROOT is not on sys.path yet.
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from pipeline.schema_accessor import isor_score  # ONE HOME (D-2646): import, never reimplement

        rows = fetch_population(db, predicate, fields)
        isor_rows = [isor_score(r) for r in rows]
        stats = collapse_stats(isor_rows)
        rc, below = falsifier_verdict(stats, rule.get("falsifier", {}))
        semantic = probe_semantic_limb(rule)
        voice = (voice_limb(rule, args.limit) if args.voice else
                 {"state": "not_run",
                  "why": "limb_voice is OPT-IN (--voice): it streams the S1 chunk store (~730 MB, ~1 min, $0)"})
    except Exception as exc:  # C16: log AND raise the exit - never a silent zero
        print(f"!! corroboration-collapse: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    payload = {
        "population": predicate,
        "db": str(db),
        "limb_identity": stats,
        "limb_voice": voice,
        "limb_semantic": semantic,
        "falsifier": {"verdict": "no_finding" if rc == EXIT_NO_FINDING else "finding", "below": below},
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    elif not args.quiet:
        s = stats
        print(f"population      : {predicate}  ({s['population']} rows, {db.name})")
        print(f"limb_identity   : one_author={s['one_author']} one_domain={s['one_domain']} "
              f"weak={s['rated_weak']}")
        print(f"                  p_multi_author={s['p_multi_author']:.4f} "
              f"p_multi_domain={s['p_multi_domain']:.4f}")
        if voice.get("state") == "measured":
            print(f"limb_voice      : one voice on {voice['rows_collapsed']}/{voice['rows_tested']} rows "
                  f"({voice['collapsed_share']:.4f}) - {voice['pairs_at_bar']} pair(s), "
                  f"{voice['pairs_identical_text']} identical text, {voice['groups']} duplicate-work group(s)")
            if "served_rows_collapsed" in voice:
                print(f"                  served {voice['served_rows_collapsed']}/{voice['population_served']} "
                      f"| advertised-corroborated {voice['advertised_rows_collapsed']}"
                      f"/{voice['population_advertised']}  (LOWER BOUND: lexical only)")
        else:
            print(f"limb_voice      : {voice['state']} - {voice['why']}")
        print(f"limb_semantic   : {semantic['state']} - {semantic['why']}")
        if rc == EXIT_NO_FINDING:
            print("falsifier       : NO FINDING - the count is not contaminated in this corpus")
        else:
            print(f"falsifier       : FINDING - {', '.join(below)}")

    if rc == EXIT_NO_FINDING:
        print("ok corroboration-collapse: NO FINDING (falsifier fired) - rc=2, documentation-only hardening")
    else:
        print(f"ok corroboration-collapse: measured rc=0 (limb_voice {voice['state']}, "
              f"limb_semantic {semantic['state']})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
