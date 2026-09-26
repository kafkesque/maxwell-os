#!/usr/bin/env python3
"""Deterministic contract between the DEPTH axis and the DOMAIN axis.

WHY THIS EXISTS
    Depth and domains are two readouts of ONE measurement (the row's domain profile). Nothing asserted that
    they agreed, so:
      - a row with ZERO real domains could carry depth=domain and be counted in every depth statistic
        (measured: R040 `emerging`, R140 blank - both `depth_final_class=3`), and
      - an off-menu token could normalise to zero domains with no exception and no log (sandbox S10), i.e. a
        truncation DEGRADING INTO A VALID-LOOKING ABSTENTION.
    This module turns "these two columns agree" into an assertion with an exit code.

THE THREE TIERS (see config/depth_domain_contract.yaml `tiers_by_mode`)
    hard          invalid BY CONSTRUCTION (off-menu value; undeclared raw token; missing provenance stamp)
    owner_blocked the cell cannot be scored at all (abstention-only; blank). Loud, but NOT a build failure:
                  a blank is a fact about the review, and inventing a value would corrupt the gold.
    soft          a judgement the owner is allowed to make (D2130). Reported and counted; never rewritten.
    The same rule is HARD for an EMITTED value and SOFT for an AUTHORED one. A validator that hard-fails the
    owner's gold is corrupting the gold.

WHAT IT WILL NOT DO
    Decide a depth class. Choose which domains apply (that collapses the two axes - the R049 error). Rewrite
    any owner cell. Separate `domain` from `specialized` on the domain vector alone (it cannot - see GAP note
    in the report; only adjacency/narrowness can, and that is not in the vector).

Usage
    python3 scripts/validate_depth_domain_contract.py                 # report on the authored workbook
    python3 scripts/validate_depth_domain_contract.py --json out.json  # machine-readable counts
    python3 scripts/validate_depth_domain_contract.py --strict-owner   # promote owner_blocked to exit 1
    python3 scripts/validate_depth_domain_contract.py --mode emitted --rows synthetic.json
Exit codes: 0 clean | 1 contract defect (hard) | 2 owner-owed cells present (loud, not fatal)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
CONFIG = REPO / "config" / "depth_domain_contract.yaml"

# Finding codes. Stable strings: they are referenced from config `tiers_by_mode` and from the regression
# harness, so they are an interface, not prose.
MENU_OFF_TOKEN = "MENU_OFF_TOKEN"
RAW_UNDECLARED_TOKEN = "RAW_UNDECLARED_TOKEN"
MISSING_MENU_VERSION = "MISSING_MENU_VERSION"
ABSTENTION_ONLY = "ABSTENTION_ONLY"
DOMAINS_BLANK = "DOMAINS_BLANK"
AXIS_EXEMPT_DECLARED = "AXIS_EXEMPT_DECLARED"
ARITY_MIN_DOMAINS = "ARITY_MIN_DOMAINS"
ARITY_MAX_DOMAINS = "ARITY_MAX_DOMAINS"
ARITY_MIN_GROUPS = "ARITY_MIN_GROUPS"
ARITY_MAX_GROUPS = "ARITY_MAX_GROUPS"
ARITY_PRIMARY = "ARITY_PRIMARY"
PRIMARY_NOT_FIRST = "PRIMARY_NOT_FIRST"
GROUP_COVERAGE_CLASS_MISMATCH = "GROUP_COVERAGE_CLASS_MISMATCH"
MENU_HASH_MISMATCH = "MENU_HASH_MISMATCH"

AMBIGUOUS_NARROW = "ambiguous-class-3-or-4"
RAW_REDERIVE_MISMATCH = "RAW_REDERIVE_MISMATCH"
# MENU_HASH_DRIFT was RETIRED 2026-09-25 (D-371): ONE code carried TWO meanings (a slot moved / a definition
# was reworded). Replaced by ANSWER_SPACE_DRIFT (a classifier may EMIT something different -> hard) and
# DEFINITION_DRIFT (wording moved, the answer set did not -> recorded, not fatal). SEVERITY still lives in
# config `tiers_by_mode`; nothing in this file decides a tier.
ANSWER_SPACE_DRIFT = "ANSWER_SPACE_DRIFT"
DEFINITION_DRIFT = "DEFINITION_DRIFT"
AXIS_PIN_MISSING = "AXIS_PIN_MISSING"
ANSWER_SPACE_PIN_UNVERIFIABLE = "ANSWER_SPACE_PIN_UNVERIFIABLE"
UNCLASSIFIED_MENU_AXIS = "UNCLASSIFIED_MENU_AXIS"
MENU_VERSION_STAMP_MISMATCH = "MENU_VERSION_STAMP_MISMATCH"
MENU_HASH_ARTIFACT_STALE = "MENU_HASH_ARTIFACT_STALE"


@dataclass(frozen=True)
class Finding:
    """One contract observation about one row (or about the sheet when item_id is '-').

    Attributes:
        code: stable machine code, e.g. `MENU_OFF_TOKEN`.
        tier: `hard` | `owner_blocked` | `soft`.
        item_id: the row this is about, or "-" for a sheet-level observation.
        detail: human-readable evidence.
    """

    code: str
    tier: str
    item_id: str
    detail: str


@dataclass
class Context:
    """Everything the row validator needs, loaded once from config-declared paths."""

    cfg: dict[str, Any]
    canon: set[str]
    group_of: dict[str, str]
    groups: set[str]
    abstention_domains: set[str]
    axis_exempt_rows: set[str]
    depth_label_to_id: dict[str, int]
    token_fixes: dict[str, str]
    declared_unresolved: set[str]
    sep: str
    tiers: dict[str, str]
    cell_replacements: tuple[tuple[str, str], ...]
    # Trailing separators the OWNER typed. Declared, so the repair is written down; TRIMMED, never replaced -
    # a replacement is a substring edit, and a substring edit on a joined list merges two tokens (BUG-458).
    trailing_sep_trim: tuple[str, ...]
    # YAML parses `1:` as an INT key, and the depth class id is a str everywhere else. Normalising the keys
    # here (once) is what stops `cfg["arity"][str(cid)]` from raising KeyError: '4' deep inside the row loop.
    arity: dict[str, dict[str, Any]]


@dataclass
class Report:
    """Accumulated findings plus the counts a reader actually needs."""

    findings: list[Finding]
    rows: int
    per_class: dict[str, int]
    computed_class: dict[str, int]

    def by_tier(self, tier: str) -> list[Finding]:
        """All findings in one tier, in insertion order."""
        return [f for f in self.findings if f.tier == tier]


def read_text(path: Path) -> tuple[str, str]:
    """Decode a file with the repo's declared order, failing loudly on the last encoding.

    Returns:
        (text, encoding_used)

    Raises:
        UnicodeDecodeError: if no declared encoding can read the file.
    """
    # D-2646/BUG-516: the decode rule has ONE home. Delegating wrapper - no codec list lives here.
    return artifact_encoding.open_artifact(path, REPO).read(), artifact_encoding.read_encoding(path, REPO)


def load_context(mode: str) -> Context:
    """Load the contract config and every input it declares.

    Raises:
        FileNotFoundError: if a declared input is missing (fail closed - never proceed on a partial context).
        KeyError: if the config lacks a section the validator needs.
    """
    cfg = yaml.safe_load(read_text(CONFIG)[0])
    inp = cfg["inputs"]
    menu_doc = json.loads(read_text(REPO / inp["menu"])[0])
    menu = menu_doc["domains"]
    canon = {d["value"] for d in menu}
    group_of = {d["value"]: (d.get("group") or "") for d in menu}
    groups = {g for g in group_of.values() if g}
    fixes = yaml.safe_load(read_text(REPO / inp["raw_repair_declaration"])[0]) or {}
    depth_cfg = yaml.safe_load(read_text(REPO / inp["depth_menu"])[0])
    label_to_id = {c["label"]: int(c["id"]) for c in depth_cfg["classes"]}
    arity = {str(k): v for k, v in cfg["arity"].items() if isinstance(v, dict)}
    if len(arity) != len(label_to_id):
        raise KeyError(f"arity table covers {sorted(arity)} but {inp['depth_menu']} declares "
                       f"{sorted(label_to_id.values())} classes - the contract must cover the whole axis")
    for cid, spec in arity.items():
        if spec.get("label") not in label_to_id:
            raise KeyError(f"arity class {cid} names label {spec.get('label')!r} absent from {inp['depth_menu']}")
    return Context(
        arity=arity,
        cfg=cfg,
        canon=canon,
        group_of=group_of,
        groups=groups,
        abstention_domains=set(cfg["abstention"]["domain_vocabulary"]),
        axis_exempt_rows=set(cfg["abstention"].get("axis_exempt_rows") or []),
        depth_label_to_id=label_to_id,
        token_fixes=dict(fixes.get("token_fixes") or {}),
        cell_replacements=tuple((c["from"], c["to"]) for c in (fixes.get("cell_replacements") or [])),
        trailing_sep_trim=tuple(fixes.get("trailing_separator_trim") or ()),
        declared_unresolved=set(fixes.get("unresolved_allowed") or []),
        sep=cfg["columns"]["separator"],
        tiers=cfg["tiers_by_mode"][mode],
    )


def split_cell(cell: str | None, sep: str) -> list[str]:
    """Split one owner cell into tokens, preserving typed order (order carries the PRIMARY)."""
    if not cell:
        return []
    return [t.strip() for t in cell.split(sep) if t.strip()]


def tier_for(ctx: Context, code: str) -> str:
    """Return the tier of a finding code from the CONFIG, never from a literal in the code.

    Raises:
        KeyError: if the mode's tier map does not classify the code. That is a config defect, and raising is
            the point: a finding whose severity is hardcoded cannot be re-graded by the owner.
    """
    for tier in ("hard", "owner_blocked", "soft"):
        if code in ctx.tiers.get(tier, []):
            return tier
    raise KeyError(f"finding code {code} has no tier in config tiers_by_mode - the config owns the tiers")


def split_raw_tokens(cell: str | None, ctx: Context) -> list[str]:
    """Tokenise the byte-faithful provenance column: declared cell repairs FIRST, then the OWNER's separator.

    The owner separated with commas; `domains_final` is written with the output separator. Splitting the raw
    column on the OUTPUT separator made one comma-cell look like a single off-menu token and produced 48 false
    positives in the first run of this check. A provenance column must be read with the separator its author
    used, which is why the raw separator is a declared value and not assumed to equal the output one.
    """
    text = (cell or "").strip()
    for old, new in ctx.cell_replacements:
        # WHOLE-CELL ONLY (BUG-458): `text.replace(old, new)` on a pipe-joined list merges the last two domains
        # into ONE undeclared token, turning a declared repair into an unrecorded edit of the owner's bytes.
        if text == old.strip():
            text = new.strip()
    for sep in ctx.trailing_sep_trim:
        while text.endswith(sep):
            text = text[: -len(sep)].rstrip()
    parts = [text]
    for sep in ctx.cfg["raw_provenance"]["separators"]:
        parts = [piece for chunk in parts for piece in chunk.split(sep)]
    return [t.strip() for t in parts if t.strip()]


def real_domains(tokens: list[str], ctx: Context) -> list[str]:
    """Domains that are actual domain-scope readings: on the menu and not the abstention slot."""
    return [t for t in tokens if t in ctx.canon and t not in ctx.abstention_domains]


def witnesses(tokens: list[str], ctx: Context) -> set[str]:
    """Groups witnessed by the row's real domains (an abstention is never a witness)."""
    return {ctx.group_of[t] for t in real_domains(tokens, ctx) if ctx.group_of.get(t)}


def computed_class(n_domains: int, n_groups: int, ctx: Context) -> str:
    """The class the DOMAIN VECTOR alone can defend, or `ambiguous-class-3-or-4`.

    The vector cannot separate `domain` from `specialized` (both are 1 domain in 1 group): the difference is
    adjacency/narrowness, which the vector does not carry. This function therefore refuses to guess, and the
    report surfaces the refusal as a GAP rather than hiding it behind a plausible number.
    """
    if n_domains == 0:
        return "abstained"
    if n_groups == len(ctx.groups):
        return "1"
    if n_domains >= 2:
        return "2"
    return AMBIGUOUS_NARROW


def validate_row(row: dict[str, str], ctx: Context) -> list[Finding]:
    """Validate one row against the contract. Pure: no writes, no config mutation.

    Returns:
        Findings in tier order (hard, owner_blocked, soft) - the caller decides the exit code.
    """
    col = ctx.cfg["columns"]
    item = row.get(col["id"], "?")
    out: list[Finding] = []

    finals = split_cell(row.get(col["domains_final"]), ctx.sep)
    raws = split_raw_tokens(row.get(col["domains_final_raw"]), ctx)
    off = [t for t in finals if t not in ctx.canon]
    for tok in off:
        out.append(Finding(MENU_OFF_TOKEN, tier_for(ctx, MENU_OFF_TOKEN), item,
                           f"domains_final token {tok!r} is outside the closed menu - NEVER normalise it "
                           f"to zero domains (S10: a truncation must not degrade into an abstention)"))
    undeclared = [t for t in raws
                  if t not in ctx.canon and t not in ctx.token_fixes and t not in ctx.declared_unresolved]
    for tok in undeclared:
        out.append(Finding(RAW_UNDECLARED_TOKEN, tier_for(ctx, RAW_UNDECLARED_TOKEN), item,
                           f"domains_final_raw token {tok!r} is neither canonical nor declared in "
                           f"config/anchor_workbook_fixes.yaml - the declaration does not cover the owner's "
                           f"bytes, so this cell's repair is undocumented"))
    if raws and not undeclared:
        # Generator equivalence: the declared repairs must REPRODUCE domains_final. If they cannot, the
        # normalisation is not a declared transformation but an unrecorded edit - and an unrecorded edit of
        # gold is the failure this whole contract exists to prevent.
        rederived = [ctx.token_fixes.get(t, t) for t in raws]
        if rederived != finals:
            out.append(Finding(RAW_REDERIVE_MISMATCH, tier_for(ctx, RAW_REDERIVE_MISMATCH), item,
                               f"declared repairs reproduce {rederived} but domains_final is {finals}"))
    if item in ctx.axis_exempt_rows:
        # BUG-465/D-387: DECLARED not-applicable. Reported (soft), leaves every rate with parity, never owed.
        return [Finding(AXIS_EXEMPT_DECLARED, tier_for(ctx, AXIS_EXEMPT_DECLARED), item,
                        "declared axis-exempt (config abstention.axis_exempt_rows): both axes abstain with "
                        "parity; the cells on this row are recorded, not scored")]
    real = real_domains(finals, ctx)
    if not finals:
        out.append(Finding(DOMAINS_BLANK, tier_for(ctx, DOMAINS_BLANK), item, "domains_final is blank (declared blank)"))
    elif not real and not off:
        # An off-menu token is a DEFECT, never an abstention. Without this guard a truncated token reduced to
        # zero real domains and was then CLASSIFIED AS A LAWFUL ABSTENTION - the silent-degrade cascade this
        # contract exists to stop, reproduced inside the contract itself (caught by test_no_silent_degrade).
        out.append(Finding(ABSTENTION_ONLY, tier_for(ctx, ABSTENTION_ONLY), item,
                           f"only abstention values {finals} - parity: this row leaves the numerator AND the "
                           f"denominator of every domain rate, and cannot carry a non-abstention depth"))

    depth_word = (row.get(col["depth_word"]) or "").strip()
    cid = ctx.depth_label_to_id.get(depth_word)
    if real and cid is not None:
        spec = ctx.arity[str(cid)]
        nd, ng = len(real), len(witnesses(finals, ctx))
        if "min_domains" in spec and nd < spec["min_domains"]:
            out.append(Finding(ARITY_MIN_DOMAINS, tier_for(ctx, ARITY_MIN_DOMAINS), item,
                               f"depth={depth_word} needs >= {spec['min_domains']} domains, row has {nd}"))
        if "max_domains" in spec and nd > spec["max_domains"]:
            out.append(Finding(ARITY_MAX_DOMAINS, tier_for(ctx, ARITY_MAX_DOMAINS), item,
                               f"depth={depth_word} allows <= {spec['max_domains']} domains, row has {nd}"))
        if "min_groups" in spec and ng < spec["min_groups"]:
            out.append(Finding(ARITY_MIN_GROUPS, tier_for(ctx, ARITY_MIN_GROUPS), item,
                               f"depth={depth_word} needs >= {spec['min_groups']} groups, row has {ng}"))
        if "max_groups" in spec and ng > spec["max_groups"]:
            out.append(Finding(ARITY_MAX_GROUPS, tier_for(ctx, ARITY_MAX_GROUPS), item,
                               f"depth={depth_word} allows <= {spec['max_groups']} groups, row has {ng}"))
        if spec.get("primary") == "forbidden" and (row.get(col["primary"]) or "").strip():
            out.append(Finding(ARITY_PRIMARY, tier_for(ctx, ARITY_PRIMARY), item,
                               f"depth={depth_word} admits no rank, but primary={row.get(col['primary'])!r}"))
        if spec.get("primary") == "required" and not (row.get(col["primary"]) or "").strip():
            out.append(Finding(ARITY_PRIMARY, tier_for(ctx, ARITY_PRIMARY), item, f"depth={depth_word} requires a primary"))
        comp = computed_class(nd, ng, ctx)
        if comp != AMBIGUOUS_NARROW and comp != str(cid):
            out.append(Finding(GROUP_COVERAGE_CLASS_MISMATCH, tier_for(ctx, GROUP_COVERAGE_CLASS_MISMATCH), item,
                               f"authored depth={depth_word} ({cid}) but the domain vector supports {comp}"))
    primary = (row.get(col["primary"]) or "").strip()
    if primary and finals and primary != finals[0]:
        out.append(Finding(PRIMARY_NOT_FIRST, tier_for(ctx, PRIMARY_NOT_FIRST), item,
                           f"primary {primary!r} != first typed token {finals[0]!r} (owner rule: first domain "
                           f"in a set is primary)"))
    return out


def load_grouped_axes(ctx: Context) -> dict[str, list[str]]:
    """The axis->group membership, read from the ONE declaration the generator also reads (C21/C12).

    Raises:
        KeyError: if the declaration has no `axis_groups` block. A checker that defaults its own grouping is
            the defect this check exists to find.
    """
    doc = yaml.safe_load(read_text(REPO / ctx.cfg["inputs"]["menu_axis_groups"])[0])
    return {g: list(axes) for g, axes in doc["axis_groups"].items()}


def validate_menu_pin(ctx: Context) -> list[Finding]:
    """Check the TWO drifts SEPARATELY: the answer space (fatal) and the definitions (recorded).

    BUG-447/D-371: `menu_hash` is a COMPOSITE of 7 sub-objects but was consumed as the ANSWER-SPACE pin, so a
    reworded discipline definition (D-321) and a changed answer slot were indistinguishable - and D-285 vs
    D-321 were both recorded RESOLVED while reading as contradictory. They are not contradictory: the
    DEFINITION moved, the ANSWER SPACE did not. One code cannot carry both facts.

    `menu_hash` is a hash of the CANONICAL RENDERING (pipeline.closed_menu), not of the `.json` bytes: the
    first version of this check hashed the file and reported a mismatch that did not exist. The instrument
    that stamps the rows must be the instrument that verifies them (C21) - never re-derive it here.
    """
    out: list[Finding] = []
    pin = ctx.cfg["menu_pin"]
    try:
        import sys as _sys  # noqa: PLC0415 - repo root + scripts/ must be importable before the modules below

        _sys.path.insert(0, str(REPO))
        _sys.path.insert(0, str(REPO / "scripts"))
        from pipeline.closed_menu import canonical_json, menu_hash, render_closed_menu  # noqa: PLC0415
        from menu_axis_hashes import axis_hash  # noqa: PLC0415 - ONE implementation, never a second

        stored_menu = json.loads(read_text(REPO / ctx.cfg["inputs"]["menu"])[0])
        live_menu = render_closed_menu()
        pins = yaml.safe_load(read_text(REPO / ctx.cfg["inputs"]["menu_axis_hashes"])[0])
        frozen = (REPO / pin["composite_pin_file"]).read_text(encoding="utf-8").split()[0].strip()
        artifact = menu_hash(stored_menu)
    except Exception as exc:  # noqa: BLE001 - provenance that cannot be recomputed is unverifiable, not absent
        out.append(Finding(ANSWER_SPACE_PIN_UNVERIFIABLE, tier_for(ctx, ANSWER_SPACE_PIN_UNVERIFIABLE), "-",
                           f"cannot recompute the menu pins ({type(exc).__name__}: {exc}) - every stored label's "
                           f"provenance is unverifiable, which is worse than a mismatch"))
        return out
    if artifact != frozen:
        out.append(Finding(MENU_HASH_ARTIFACT_STALE, tier_for(ctx, MENU_HASH_ARTIFACT_STALE), "-",
                           f"the frozen artifact hashes {artifact[:16]}... but {pin['composite_pin_file']} says "
                           f"{frozen[:16]}... - the artifact was edited after it was frozen"))
    try:
        groups = load_grouped_axes(ctx)
    except Exception as exc:  # noqa: BLE001 - a missing group declaration means nothing is pinnable
        out.append(Finding(ANSWER_SPACE_PIN_UNVERIFIABLE, tier_for(ctx, ANSWER_SPACE_PIN_UNVERIFIABLE), "-",
                           f"cannot read {ctx.cfg['inputs']['menu_axis_groups']} ({type(exc).__name__}: {exc})"))
        return out
    grouped = {a for axes in groups.values() for a in axes}
    ungrouped = sorted(set(live_menu) - grouped)
    if pin.get("require_every_axis_grouped") and ungrouped:
        out.append(Finding(UNCLASSIFIED_MENU_AXIS, tier_for(ctx, UNCLASSIFIED_MENU_AXIS), "-",
                           f"live menu axes {ungrouped} belong to NO group in "
                           f"{ctx.cfg['inputs']['menu_axis_groups']} - an ungrouped axis is pinned by nothing, "
                           f"so a change to it is invisible to every check in this file"))
    # BUG-483 residual: the axis hashes are a LIST of {axis, sha256} records. An axis name in KEY
    # position collided with the decision-citation vocabulary and needed an exemption; a name in VALUE
    # position cannot. Fail-closed on any other shape: an unreadable pin is unverifiable, not absent.
    recorded_axes: dict[str, str] = {
        str(e["axis"]): str(e["sha256"]) for e in (pins.get("hashes") or [])
    }
    answer_axes = groups.get("answer_space", [])
    recorded_pin = pins.get(pin["answer_space_pin_key"])
    if not recorded_pin or not answer_axes:
        out.append(Finding(AXIS_PIN_MISSING, tier_for(ctx, AXIS_PIN_MISSING), "-",
                           f"no {pin['answer_space_pin_key']} recorded in "
                           f"{ctx.cfg['inputs']['menu_axis_hashes']} - the answer space is unpinned, so no "
                           f"answer-space claim is checkable"))
    else:
        live_pin = hashlib.sha256(canonical_json({a: live_menu[a] for a in answer_axes}).encode()).hexdigest()
        if live_pin != recorded_pin:
            out.append(Finding(ANSWER_SPACE_DRIFT, tier_for(ctx, ANSWER_SPACE_DRIFT), "-",
                               f"a classifier may EMIT something different today: the answer space "
                               f"[{', '.join(answer_axes)}] renders to {live_pin[:16]}... but is pinned at "
                               f"{recorded_pin[:16]}... - every stored label count is incomparable until the pin "
                               f"is re-frozen UNDER A DECISION (an owner act, not a re-render)"))
    for group, axes in sorted(groups.items()):
        if group == "answer_space":
            continue
        for axis in axes:
            recorded = recorded_axes.get(axis)
            if recorded is None:
                out.append(Finding(AXIS_PIN_MISSING, tier_for(ctx, AXIS_PIN_MISSING), "-",
                                   f"axis {axis!r} is declared in group {group!r} but has no recorded hash in "
                                   f"{ctx.cfg['inputs']['menu_axis_hashes']}"))
                continue
            live_axis = axis_hash(live_menu, axis)
            if live_axis != recorded:
                out.append(Finding(DEFINITION_DRIFT, tier_for(ctx, DEFINITION_DRIFT), "-",
                                   f"{group}/{axis} moved {recorded[:16]}... -> {live_axis[:16]}... - RECORDED, "
                                   f"not fatal: the answer space did not move, so no stored label is "
                                   f"invalidated (D-371). Re-freeze only if the change was meant to be visible "
                                   f"to future rows (an owner act)"))
    if ctx.cfg["provenance"].get("require_menu_version_stamp"):
        manifest = REPO / ctx.cfg["inputs"]["anchor_manifest"]
        doc = json.loads(read_text(manifest)[0]) if manifest.exists() else {}
        keys = ctx.cfg["provenance"]["menu_version_stamp_keys"]
        if not any(doc.get(k) for k in keys):
            out.append(Finding(MISSING_MENU_VERSION, tier_for(ctx, MISSING_MENU_VERSION), "-",
                               f"no {'/'.join(keys)} stamp on {ctx.cfg['inputs']['anchor_manifest']}: every "
                               f"stored domain count is unversioned"))
        else:
            # A stamp that is never CHECKED against the pin it claims to be is a decoration, not provenance.
            for mkey, pkey in (ctx.cfg["provenance"]["stamp_verify_keys"] or {}).items():
                got, want = doc.get(mkey), pins.get(pkey)
                if got and want and got != want:
                    out.append(Finding(MENU_VERSION_STAMP_MISMATCH, tier_for(ctx, MENU_VERSION_STAMP_MISMATCH),
                                       "-", f"{mkey} on the manifest is {str(got)[:16]}... but {pkey} in "
                                            f"{ctx.cfg['inputs']['menu_axis_hashes']} is {str(want)[:16]}... - a "
                                            f"stamp that disagrees with the pin it claims is worse than no stamp"))
    return out


def load_rows(path: Path | None, ctx: Context) -> list[dict[str, str]]:
    """Read the workbook (or a synthetic row file) into dicts.

    Raises:
        FileNotFoundError: never silent - a missing input is a defect, not an empty result.
    """
    target = path or (REPO / ctx.cfg["inputs"]["workbook"])
    if not target.exists():
        raise FileNotFoundError(target)
    return list(csv.DictReader(io.StringIO(read_text(target)[0])))


def build_report(rows: list[dict[str, str]], ctx: Context) -> Report:
    """Validate every row and collect the counts the report prints."""
    findings = validate_menu_pin(ctx)
    per_class: dict[str, int] = {}
    computed: dict[str, int] = {}
    for row in rows:
        findings.extend(validate_row(row, ctx))
        cls = (row.get(ctx.cfg["columns"]["depth_word"]) or "BLANK").strip() or "BLANK"
        per_class[cls] = per_class.get(cls, 0) + 1
        cc = computed_class(len(real_domains(split_cell(row.get(ctx.cfg["columns"]["domains_final"]), ctx.sep), ctx)),
                            len(witnesses(split_cell(row.get(ctx.cfg["columns"]["domains_final"]), ctx.sep), ctx)), ctx)
        computed[cc] = computed.get(cc, 0) + 1
    return Report(findings=findings, rows=len(rows), per_class=per_class, computed_class=computed)


def print_report(rep: Report, ctx: Context, mode: str, strict_owner: bool) -> int:
    """Print the tiered report and return the exit code."""
    print(f"== depth/domain contract {ctx.cfg['contract_version']} (status {ctx.cfg['status']}, mode {mode}) ==")
    print(f"rows {rep.rows} | authored depth {dict(sorted(rep.per_class.items()))}")
    print(f"class defensible from the DOMAIN VECTOR alone: {dict(sorted(rep.computed_class.items()))}")
    print(f"  GAP: {AMBIGUOUS_NARROW} = the vector cannot separate class 3 from class 4 (adjacency/narrowness is "
          f"not in it); refusing to guess is the correct behaviour, not a missing rule.")
    for tier in ("hard", "owner_blocked", "soft"):
        bucket = rep.by_tier(tier)
        codes: dict[str, list[str]] = {}
        for f in bucket:
            codes.setdefault(f.code, []).append(f.item_id)
        print(f"-- {tier}: {len(bucket)} finding(s) across {len(codes)} code(s)")
        for code, ids in sorted(codes.items()):
            shown = ", ".join(ids[:8]) + (f" ... (+{len(ids) - 8})" if len(ids) > 8 else "")
            print(f"     {code:34s} {len(ids):3d}  {shown}")
    hard = len(rep.by_tier("hard"))
    owner = len(rep.by_tier("owner_blocked"))
    if hard:
        print(f"\nFAIL contract: {hard} hard finding(s) - fail closed (nothing may consume this workbook)")
        for f in rep.by_tier("hard")[:12]:
            print(f"     {f.item_id}: {f.code}: {f.detail}")
        return 1
    if owner and strict_owner:
        print(f"\nFAIL(--strict-owner): {owner} owner-owed cell(s) block a complete denominator")
        return 1
    if owner:
        print(f"\nOWNER-OWED (exit 2): {owner} cell(s) cannot be scored; excluded from every denominator "
              f"with parity - loud, not fatal")
        for f in rep.by_tier("owner_blocked"):
            print(f"     {f.item_id}: {f.code}: {f.detail}")
        return 2
    print("\nok contract: no hard findings, no owner-owed cells")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code (0 clean | 1 hard | 2 owner-owed)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("authored", "emitted"), default="authored")
    ap.add_argument("--rows", type=Path, default=None, help="override the workbook with a CSV/JSON row file")
    ap.add_argument("--json", type=Path, default=None, help="write machine-readable counts here")
    ap.add_argument("--strict-owner", action="store_true", help="treat owner-owed cells as exit 1")
    ap.add_argument("--gate-if-active", action="store_true",
                    help="exit non-zero only once the contract is activated (status: active)")
    a = ap.parse_args(argv)
    ctx = load_context(a.mode)
    if a.rows and a.rows.suffix == ".json":
        rows = json.loads(read_text(a.rows)[0])
    else:
        rows = load_rows(a.rows, ctx)
    rep = build_report(rows, ctx)
    if a.json:
        a.json.write_text(json.dumps({
            "contract_version": ctx.cfg["contract_version"],
            "status": ctx.cfg["status"],
            "mode": a.mode,
            "rows": rep.rows,
            "authored_depth": rep.per_class,
            "vector_defensible_class": rep.computed_class,
            "counts": {t: len(rep.by_tier(t)) for t in ("hard", "owner_blocked", "soft")},
            "codes": sorted({f.code for f in rep.findings}),
            "findings": [{"code": f.code, "tier": f.tier, "item_id": f.item_id} for f in rep.findings],
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    code = print_report(rep, ctx, a.mode, a.strict_owner)
    if a.gate_if_active and ctx.cfg["status"] != "active":
        print(f"\nNON-GATING: contract status is {ctx.cfg['status']!r} (owner gate). Findings above are "
              f"real and reported; the exit code {code} is suppressed by --gate-if-active.")
        return 0
    return code


if __name__ == "__main__":
    raise SystemExit(main())
