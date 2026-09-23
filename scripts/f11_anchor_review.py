"""Build the F-11 ANCHOR review sheet: every ruler row whose label is absent or contested, on ANY axis.

Row families (a row can be in more than one; the `why` column names them explicitly):

* ``BLANK:<axis>``    - the human never labelled that axis (BUG-363). Round 2 showed the blanks split:
  the 5 FORM blanks are uncontested (both coder families agree 5/5) while the 28 DISC blanks are genuinely
  contested (they agree on only 18/28).
* ``DIVERGE:<axis>`` - the human labelled it, but BOTH coder families agree on a different value. Candidate
  ruler-defect rows. CT carries the quarantine pattern; DISC carries the institution-vs-subject pattern;
  FORM is the weakest axis overall (coder-vs-coder k=0.638 vs human k=0.27-0.31).

Covers ALL THREE axes (content_type, discipline, extraction_type) in one file, because a review that stopped
at one axis would silently leave two thirds of the anchor unaudited.

Every label is emitted as the **menu display value** (what must be typed verbatim); canonical keys are internal.
Read-only over every input; writes one CSV plus an MD legend with the closed menus and their definitions.
Nothing is written back into the ruler sheet - consolidating the anchor is a separate, explicit step (R-D410).
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
SEP_HEADER = ">>> FILL ONLY THE COLUMNS AFTER THIS ONE <<<"
OWNER_COLS = ("owner_ct", "owner_disc", "owner_form", "owner_keep_missing", "owner_notes")
MENU_SECTION = {"content_type": "content_types", "discipline": "disciplines", "extraction_type": "extraction_types"}


def _load_cfg() -> dict[str, Any]:
    """Load the F-11 coder config and refuse to run if the review block is absent (C12: config-first)."""
    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    if "anchor_review" not in cfg:
        raise SystemExit(f"{CFG_PATH}: missing 'anchor_review' block - refusing to guess paths (C12)")
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
    """Return (items, canonical->display) for one closed-menu section, stably sorted by display value."""
    raw = json.loads(MENU_PATH.read_text(encoding="utf-8"))[section]
    items = sorted((raw if isinstance(raw, list) else [{"value": k} for k in raw]), key=lambda d: d["value"])
    return items, {_canon(i["value"], {}): i["value"] for i in items}


def _read_coder(path: pathlib.Path, aliases: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Read one coder's raw label file into {item_id: {axis: (canonical_label, confidence)}}.

    Accepts JSONL and markdown-wrapped JSONL alike (the Kimi return was delivered as .md).
    """
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        obj = json.loads(line)
        iid = str(obj.get("item_id", "")).strip()
        if not iid:
            continue
        out[iid] = {
            ax: (_canon(str(obj.get(ax, "")), aliases), obj.get(conf_key)) for ax, conf_key in CONF_KEYS.items()
        }
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


def _fmt(label: str, conf: Any, menu_display: dict[str, str]) -> str:
    """Render 'menu value (confidence)' - confidence inline keeps the sheet 12 columns narrower."""
    text = _display(label, menu_display)
    if not text or not isinstance(conf, (int, float)):
        return text
    return f"{text} ({float(conf):.2f})"


def build() -> tuple[list[str], list[list[str]], dict[str, Any]]:
    """Build the review table: header, rows, and a provenance/stats dict for the legend."""
    cfg = _load_cfg()
    rc = cfg["anchor_review"]
    aliases = _aliases(cfg)
    menus = {ax: _menu(sec) for ax, sec in MENU_SECTION.items()}
    ruler = _read_indexed(PROJECT_ROOT / rc["ruler_sheet"])
    sheet = _read_indexed(PROJECT_ROOT / rc["decision_sheet"])
    coders = {c["tag"]: _read_coder(PROJECT_ROOT / c["path"], aliases) for c in rc["coders"]}
    tags = list(coders)
    if len(tags) < 2:
        raise SystemExit("anchor_review needs at least two coders to be a cross-check (R5)")

    def coder_label(tag: str, iid: str, axis: str) -> tuple[str, Any]:
        return coders[tag].get(iid, {}).get(axis, ("", None))

    per_item: dict[str, dict[str, Any]] = {}
    for iid, row in ruler.items():
        flags: list[str] = []
        cells: dict[str, dict[str, Any]] = {}
        for axis, human_col in rc["columns"].items():
            human = _canon(row.get(human_col, ""), aliases)
            values = {coder_label(t, iid, axis)[0] for t in tags}
            agree = len(values) == 1 and ("",) != tuple(values)
            consensus = next(iter(values)) if agree else ""
            if not human:
                flags.append(f"BLANK:{axis}")
            elif agree and consensus and consensus != human:
                flags.append(f"DIVERGE:{axis}")
            cells[axis] = {"human": human, "agree": agree, "consensus": consensus,
                           "menus": menus[axis][1], "coder": {t: coder_label(t, iid, axis) for t in tags}}
        if flags:
            per_item[iid] = {"flags": flags, "cells": cells}

    header = ["item_id", "name", "why", "DECIDE", "DEFINITION", "APPLICATION"]
    for axis in MENU_SECTION:
        short = {"content_type": "ct", "discipline": "disc", "extraction_type": "form"}[axis]
        header += [f"human_{short}", f"{tags[0]}_{short}", f"{tags[1]}_{short}",
                   f"{short}_agree", f"{short}_consensus"]
    header += ["menu_check", SEP_HEADER, *OWNER_COLS]

    stats: dict[str, Any] = {
        "flags": collections.Counter(),
        "n_rows": len(per_item),
        "n_out_of_menu_cells": 0,
        "out_of_menu": collections.Counter(),
        "inputs": {},
        "tags": tags,
    }
    rows: list[list[str]] = []
    for iid in sorted(per_item, key=lambda i: (not per_item[i]["flags"][0].startswith("BLANK"), i)):
        cells = per_item[iid]["cells"]
        unknown: list[str] = []
        out: list[str] = [iid, sheet.get(iid, {}).get("name", ruler[iid].get("name", "")),
                          " | ".join(per_item[iid]["flags"]), sheet.get(iid, {}).get("DECIDE", ""),
                          (sheet.get(iid, {}).get("DEFINITION", "") or "")[:TRUNC],
                          (sheet.get(iid, {}).get("APPLICATION", "") or "")[:TRUNC]]
        for axis in MENU_SECTION:
            c = cells[axis]
            for t in tags:
                label = c["coder"][t][0]
                if label and label not in c["menus"]:
                    unknown.append(f"{t}:{label}")
            out += [_display(c["human"], c["menus"]),
                    _fmt(*c["coder"][tags[0]], c["menus"]),
                    _fmt(*c["coder"][tags[1]], c["menus"]),
                    "YES" if c["agree"] else "NO",
                    _display(c["consensus"], c["menus"])]
        for f in per_item[iid]["flags"]:
            stats["flags"][f] += 1
        stats["out_of_menu"].update(unknown)
        stats["n_out_of_menu_cells"] += len(unknown)
        out += ["OK" if not unknown else "; ".join(unknown), "", "", "", "", "", ""]
        rows.append(out)
    stats["flags"] = dict(stats["flags"])
    stats["out_of_menu"] = dict(stats["out_of_menu"])
    stats["n_menu_items"] = {ax: len(menus[ax][0]) for ax in menus}
    stats["inputs"] = {
        str(rc["ruler_sheet"]): _sha256(PROJECT_ROOT / rc["ruler_sheet"]),
        str(rc["decision_sheet"]): _sha256(PROJECT_ROOT / rc["decision_sheet"]),
        "config/closed_menu_v5.json": _sha256(MENU_PATH),
        **{f"coder[{c['tag']}]": _sha256(PROJECT_ROOT / c["path"]) for c in rc["coders"]},
    }
    return header, rows, stats


def _legend(header: list[str], stats: dict[str, Any]) -> str:
    """Render the companion markdown: how to fill the sheet, plus the three closed menus and definitions."""
    menu_lines: list[str] = []
    for axis, section in MENU_SECTION.items():
        items, _ = _menu(section)
        menu_lines += [f"## Closed menu — {axis} ({len(items)} values, type verbatim)", ""]
        by_group: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
        for i in items:
            by_group[i.get("group", "ungrouped")].append(i)
        for group in sorted(by_group):
            menu_lines += [f"### {group}", ""]
            for i in by_group[group]:
                definition = (i.get("definition", "") or "").replace("\n", " ")[:MENU_DEF_TRUNC]
                more = "…" if len(i.get("definition", "") or "") > MENU_DEF_TRUNC else ""
                menu_lines.append(f"- `{i['value']}` — {definition}{more}")
            menu_lines.append("")
    blanks = {k: v for k, v in stats["flags"].items() if k.startswith("BLANK")}
    diverges = {k: v for k, v in stats["flags"].items() if k.startswith("DIVERGE")}
    return "\n".join([
        "# F-11 ANCHOR REVIEW SHEET — every absent or contested ruler label, all three axes",
        "",
        f"Built {datetime.datetime.now().isoformat(timespec='seconds')} · {stats['n_rows']} rows · "
        f"all three axes in one file (a review that stopped at one axis would leave the rest unaudited)",
        "",
        f"Blank (never labelled by a human): {blanks}",
        f"Divergent (both coder families agree AGAINST the human): {diverges}",
        "",
        "## Columns (letters as in the CSV)",
        "",
        *[f"- `{chr(65 + i)}{i + 1}` {c}" for i, c in enumerate(header)],
        "",
        "## What you do",
        "",
        f"1. Fill **only** `{'`, `'.join(OWNER_COLS)}` — column "
        f"`{chr(65 + header.index(SEP_HEADER))}{header.index(SEP_HEADER) + 1}` is a blank fence column, and it "
        "exists so an empty column can never again be mistaken for free space (BUG-368).",
        "2. Each `owner_ct` / `owner_disc` / `owner_form`: exactly one value from the matching closed menu, typed "
        "verbatim. Leave a cell EMPTY to mean 'the human label stands as written' (blank stays blank, a divergence "
        "stays a divergence) - or fill it to override. An empty cell is a decision, not an omission.",
        "3. `owner_keep_missing = yes` marks a row whose blank you judge genuinely unlabelable: it stays "
        "declared-missing and will NEVER be imputed (set it only where the coders also disagree).",
        "4. `owner_notes`: free text, any language — the *why* (contract, provenance, ambiguity, near-neighbour).",
        "5. Nothing else: do not rename, reorder, delete or add columns or rows. Do not edit A–U.",
        "",
        "## Reading the columns",
        "",
        "* `why` names the family per axis, e.g. `BLANK:discipline | DIVERGE:content_type`.",
        "* `coders_agree=YES` on a `DIVERGE` axis means both families independently produced that value — "
        "a candidate RULER defect, not coder noise. `NO` means there is nothing to inherit.",
        "* confidences are inline as `label (0.50)`; read them as a relative signal only (Kimi is systematically "
        "more confident: mean 0.81 vs 0.59 on CT).",
        f"* `menu_check=OK` means every coder value resolves against the closed menu. Out-of-menu coder cells in "
        f"this build: {stats['n_out_of_menu_cells']}"
        + (f" → {stats['out_of_menu']}" if stats["n_out_of_menu_cells"] else ""),
        "",
        *menu_lines,
        "## Provenance of the inputs read (R14)",
        "",
        *[f"- `{k}` sha256 `{v[:16]}…`" for k, v in stats["inputs"].items()],
        "",
        "## What happens next",
        "",
        "You return the file. The anchor is then consolidated in ONE explicit, append-only step: your value wins "
        "where you ruled, an empty cell leaves the human label as written, `owner_keep_missing=yes` stays "
        "declared-missing (never imputed), and the ruler sheet itself is NOT rewritten — the consolidation lands "
        "as a new artifact with its own stamp. Tier stays human-mixed + `llm-attested`: this still cannot unfreeze "
        "F-11 or any eval floor. Only a genuinely independent second HUMAN coder can.",
    ])


def main() -> None:
    """Write the review CSV + legend, refusing to overwrite an earlier export (append-only discipline)."""
    global CONF_KEYS
    cfg = _load_cfg()
    CONF_KEYS = dict(cfg["conf_columns"])
    header, rows, stats = build()
    out_csv = PROJECT_ROOT / cfg["anchor_review"]["out_csv"].replace("{date}", TODAY)
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
    print(f"   flags: {stats['flags']}")
    print(f"   menus: {stats['n_menu_items']} | out-of-menu coder cells: {stats['n_out_of_menu_cells']}")


CONF_KEYS: dict[str, str] = {}

if __name__ == "__main__":
    main()
