"""Build the F-11 DISC review sheet: the rows where the ruler's discipline label is absent or contested.

Two row families, one CSV, flagged in the `why` column:

* ``BLANK_ABSTENTION``  - the human never labelled the discipline axis (BUG-363, 28 rows). Round 2 showed
  these are genuinely contested: the two independent coder families agree on only 18/28.
* ``CONSENSUS_DIVERGENCE`` - the human labelled it, but BOTH coder families agree on a different value
  (F-11 round 1/2), i.e. the candidate ruler-defect rows.

Every label shown to the owner is emitted as the **menu display value** (what must be typed verbatim), with a
`menu_check` column proving it resolves against config/closed_menu_v5.json - canonical keys are internal only.

Read-only over every input. Writes one CSV plus an MD legend carrying the closed menu with definitions.
Nothing is written back into the ruler sheet: consolidating the anchor is a separate, explicit step (R-D410).
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

import yaml

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from f11_llm_coder import _canon  # noqa: E402  (single source of truth for label canonicalisation)

CFG_PATH = PROJECT_ROOT / "config" / "f11_llm_coder.yaml"
MENU_PATH = PROJECT_ROOT / "config" / "closed_menu_v5.json"
TODAY = datetime.date.today().strftime("%Y%m%d")
TRUNC = 300
MENU_DEF_TRUNC = 150
SEP_HEADER = ">>> FILL ONLY THE 3 COLUMNS AFTER THIS ONE <<<"
OWNER_COLS = ("owner_disc_final", "owner_keep_missing", "owner_notes")


def _load_cfg() -> dict[str, Any]:
    """Load the F-11 coder config and refuse to run if the review block is absent (C12: config-first)."""
    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if "disc_review" not in cfg:
        raise SystemExit(f"{CFG_PATH}: missing 'disc_review' block - refusing to guess paths (C12)")
    return cfg


def _sha256(path: pathlib.Path) -> str:
    """Return the hex sha256 of a file, or 'MISSING' - used to stamp the inputs actually read (R14)."""
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"


def _read_indexed(path: pathlib.Path, key: str = "item_id") -> dict[str, dict[str, str]]:
    """Read a CSV into {item_id: {header: value}}; rows without a key are dropped (junk/trailing rows)."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    idx = head.index(key)
    return {r[idx]: dict(zip(head, r)) for r in rows[1:] if len(r) > idx and r[idx].strip()}


def _menu(section: str) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Return (items, canonical->display) for a closed-menu section, sorted for stable output."""
    raw = json.loads(MENU_PATH.read_text(encoding="utf-8"))[section]
    items = sorted((raw if isinstance(raw, list) else [{"value": k} for k in raw]), key=lambda d: d["value"])
    return items, {_canon(i["value"], {}): i["value"] for i in items}


def _read_coder(path: pathlib.Path, axis: str, aliases: dict[str, str]) -> dict[str, tuple[str, Any]]:
    """Read one coder's raw label file into {item_id: (canonical_label, confidence)}.

    Accepts JSONL and markdown-wrapped JSONL alike (the Kimi return was delivered as .md).
    """
    out: dict[str, tuple[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        obj = json.loads(line)
        iid = str(obj.get("item_id", "")).strip()
        if not iid:
            continue
        out[iid] = (_canon(str(obj.get(axis, "")), aliases), obj.get(f"conf_{axis[:4]}"))
    return out


def _aliases(cfg: dict[str, Any]) -> dict[str, str]:
    """Build the as-written -> canonical alias map from the declared_aliases block."""
    return {
        _canon(str(a["as_written"]), {}): _canon(str(a["canonical"]), {})
        for a in cfg.get("declared_aliases") or []
    }


def _display(label: str, menu_display: dict[str, str]) -> str:
    """Render a canonical label as the menu value the owner must type; mark anything unrecognised loudly."""
    if not label:
        return ""
    return menu_display.get(label, f"⚠ OUT-OF-MENU: {label}")


def build() -> tuple[list[str], list[list[str]], dict[str, Any]]:
    """Build the review table: header, rows, and a provenance/stats dict for the legend."""
    cfg = _load_cfg()
    rc = cfg["disc_review"]
    aliases = _aliases(cfg)
    items, menu_display = _menu("disciplines")
    ruler = _read_indexed(PROJECT_ROOT / rc["ruler_sheet"])
    sheet = _read_indexed(PROJECT_ROOT / rc["decision_sheet"])
    coders = {c["tag"]: _read_coder(PROJECT_ROOT / c["path"], c["axis"], aliases) for c in rc["coders"]}
    tags = list(coders)
    if len(tags) < 2:
        raise SystemExit("disc_review needs at least two coders to be a cross-check (R5)")

    human_col = rc["human_column"]
    blank_ids = sorted(i for i, r in ruler.items() if not _canon(r.get(human_col, ""), aliases))
    blank_set = set(blank_ids)
    diverge_ids: list[str] = []
    for iid, r in ruler.items():
        if iid in blank_set:
            continue
        coder_values = {coders[t].get(iid, ("", None))[0] for t in tags}
        # exactly one distinct non-empty coder value, and it is not what the human wrote -> the coders agree
        # with each other AGAINST the ruler on this row (candidate ruler defect, not coder noise).
        if len(coder_values) == 1:
            (only,) = coder_values
            if only and only != _canon(r.get(human_col, ""), aliases):
                diverge_ids.append(iid)
    diverge_ids.sort()

    header = [
        "item_id", "name", "why", "DECIDE", "human_disc_now",
        f"{tags[0]}_disc", f"{tags[0]}_conf", f"{tags[1]}_disc", f"{tags[1]}_conf",
        "coders_agree", "menu_check", "coders_consensus", "DEFINITION", "APPLICATION",
        SEP_HEADER, *OWNER_COLS,
    ]
    rows: list[list[str]] = []
    out_of_menu: collections.Counter[str] = collections.Counter()
    for why, ids in (("BLANK_ABSTENTION", blank_ids), ("CONSENSUS_DIVERGENCE", diverge_ids)):
        for iid in ids:
            c0, c1 = coders[tags[0]].get(iid, ("", None)), coders[tags[1]].get(iid, ("", None))
            agree = "YES" if c0[0] and c0[0] == c1[0] else "NO"
            unknown = [f"{t}:{v[0]}" for t, v in ((tags[0], c0), (tags[1], c1)) if v[0] and v[0] not in menu_display]
            out_of_menu.update(unknown)
            src = sheet.get(iid, {})
            rows.append([
                iid, src.get("name", ruler.get(iid, {}).get("name", "")), why, src.get("DECIDE", ""),
                _display(_canon(ruler.get(iid, {}).get(human_col, ""), aliases), menu_display),
                _display(c0[0], menu_display), "" if c0[1] is None else str(c0[1]),
                _display(c1[0], menu_display), "" if c1[1] is None else str(c1[1]),
                agree, "OK" if not unknown else "; ".join(unknown),
                _display(c0[0], menu_display) if agree == "YES" else "",
                (src.get("DEFINITION", "") or "")[:TRUNC], (src.get("APPLICATION", "") or "")[:TRUNC],
                "", "", "", "",
            ])
    stats = {
        "n_blank_abstention": len(blank_ids),
        "n_consensus_divergence": len(diverge_ids),
        "coder_agreement_on_blanks": sum(
            1 for i in blank_ids
            if coders[tags[0]].get(i, ("", None))[0] == coders[tags[1]].get(i, ("", None))[0] != ""
        ),
        "n_out_of_menu_cells": sum(out_of_menu.values()),
        "out_of_menu": dict(out_of_menu),
        "n_menu_items": len(items),
        "inputs": {
            str(rc["ruler_sheet"]): _sha256(PROJECT_ROOT / rc["ruler_sheet"]),
            str(rc["decision_sheet"]): _sha256(PROJECT_ROOT / rc["decision_sheet"]),
            "config/closed_menu_v5.json": _sha256(MENU_PATH),
            **{f"coder[{c['tag']}]": _sha256(PROJECT_ROOT / c["path"]) for c in rc["coders"]},
        },
        "tags": tags,
    }
    return header, rows, stats


def _legend(header: list[str], stats: dict[str, Any]) -> str:
    """Render the companion markdown: how to fill the sheet, plus the closed menu with its definitions."""
    items, _ = _menu("disciplines")
    by_group: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for i in items:
        by_group[i.get("group", "ungrouped")].append(i)
    menu_lines: list[str] = []
    for group in sorted(by_group):
        menu_lines.append(f"### {group}")
        menu_lines.append("")
        for i in by_group[group]:
            definition = (i.get("definition", "") or "").replace("\n", " ")[:MENU_DEF_TRUNC]
            menu_lines.append(f"- `{i['value']}` — {definition}{'…' if len(i.get('definition','') or '') > MENU_DEF_TRUNC else ''}")
        menu_lines.append("")
    return "\n".join([
        "# F-11 DISC REVIEW SHEET — how to fill it",
        "",
        f"Built {datetime.datetime.now().isoformat(timespec='seconds')} · "
        f"BLANK_ABSTENTION {stats['n_blank_abstention']} rows · CONSENSUS_DIVERGENCE {stats['n_consensus_divergence']} rows",
        "",
        f"On the {stats['n_blank_abstention']} rows no human ever labelled, the two independent coder families agree "
        f"on only {stats['coder_agreement_on_blanks']} of them — so on the other "
        f"{stats['n_blank_abstention'] - stats['coder_agreement_on_blanks']} there is NO consensus to inherit. "
        "You are the only adjudicator for those.",
        "",
        "## Columns (letters as in the CSV)",
        "",
        *[f"- `{chr(65 + i)}{i + 1}` {c}" for i, c in enumerate(header)],
        "",
        "## What you do",
        "",
        f"1. Fill **only** `{OWNER_COLS[0]}`, `{OWNER_COLS[1]}`, `{OWNER_COLS[2]}` — column "
        f"`{chr(65 + header.index(SEP_HEADER))}{header.index(SEP_HEADER) + 1}` is a blank fence column, and it "
        "exists so an empty column can never again be mistaken for free space (BUG-368).",
        "2. `owner_disc_final`: exactly one value from the closed menu below, typed verbatim, **or** leave it "
        "empty and set `owner_keep_missing = yes` if you judge the row genuinely unlabelable. The two are "
        "mutually exclusive: a filled cell with `keep_missing = yes` is a contradiction and will be rejected.",
        "3. `owner_notes`: free text, any language — the *why* (contract, provenance, ambiguity, near-neighbour).",
        "4. Nothing else: do not rename, reorder, delete or add columns or rows. Do not edit A–N.",
        "",
        "## Reading the columns",
        "",
        "* `why=BLANK_ABSTENTION` — no human discipline label ever existed for this row (BUG-363).",
        "* `why=CONSENSUS_DIVERGENCE` — you labelled it, both coder families agreed on something else.",
        "* `coders_agree=YES` — both families independently produced the same value (`coders_consensus`).",
        "* `coders_agree=NO` — they disagree; `coders_consensus` is empty, and there is nothing to inherit.",
        f"* `menu_check=OK` means every coder value resolves against the closed menu. "
        f"Out-of-menu cells in this build: {stats['n_out_of_menu_cells']}"
        + (f" → {stats['out_of_menu']}" if stats["n_out_of_menu_cells"] else ""),
        "* `claude_conf` / `kimi_conf` — the coder's own confidence, read as a relative signal only "
        "(Kimi is systematically more confident: mean 0.81 vs 0.59 on CT).",
        "",
        f"## Closed menu — disciplines ({stats['n_menu_items']} values, type verbatim)",
        "",
        *menu_lines,
        "## Provenance of the inputs read (R14)",
        "",
        *[f"- `{k}` sha256 `{v[:16]}…`" for k, v in stats["inputs"].items()],
        "",
        "## What happens next",
        "",
        "You return the file. The anchor is then consolidated in ONE explicit, append-only step: your value wins "
        "where you ruled, `owner_keep_missing=yes` stays declared-missing (never imputed), and the ruler sheet is "
        "not rewritten — the consolidation lands as a new artifact with its own stamp, and the tier stays "
        "`llm-attested`/human-mixed until a genuinely independent human coder exists (F-11 stays open).",
    ])


def main() -> None:
    """Write the review CSV + legend, refusing to overwrite an earlier export (append-only discipline)."""
    cfg = _load_cfg()
    header, rows, stats = build()
    out_csv = PROJECT_ROOT / cfg["disc_review"]["out_csv"].replace("{date}", TODAY)
    out_md = out_csv.with_suffix(".md")
    for p in (out_csv, out_md):
        if p.exists():
            raise SystemExit(f"refusing to overwrite {p.relative_to(PROJECT_ROOT)} (append-only, R-D410)")
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([header, *rows])
    out_md.write_text(_legend(header, stats), encoding="utf-8")
    print(f"✅ {out_csv.relative_to(PROJECT_ROOT)}  ({len(rows)} rows x {len(header)} cols)")
    for i, c in enumerate(header):
        print(f"   {chr(65 + i)}{i + 1:>3}  {c}")
    print(f"   sha256 {hashlib.sha256(out_csv.read_bytes()).hexdigest()[:16]}…")
    print(f"✅ legend {out_md.relative_to(PROJECT_ROOT)}")
    print(f"   menu: {stats['n_menu_items']} values | out-of-menu coder cells: {stats['n_out_of_menu_cells']}")


if __name__ == "__main__":
    main()
