"""The research-source register's ONE reader: load, check, and rank (D-3080).

Three jobs, and the third is the one an advisory agent needs:

  `load()`   — the declaration, parsed.
  `check()`  — every declared source RESOLVES: an `api` names a URL, an `env` names a variable, a `manual` source
               says why it cannot be automated, and an `access: none` carries a reason. A register that cannot be
               checked becomes a prose list within a month (D-3034).
  `rank()`   — which sources a given task may actually use, in weight order, with the missing limb stated.

`rank()` deliberately returns DECLARATIONS, not answers: this module never calls a network. Resolving a work is
the resolvers' job and fetching bytes is the downloader's; a register that also fetched would be a fourth writer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import AcquisitionError

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "config" / "research_sources.yaml"

SECTIONS = ("book_sources", "paper_sources", "shadow_sources", "tools_not_integrated")
#: A SECTION is where a source sits; a FAMILY is what it answers. They differ because `shadow_sources` holds both
#: books and papers, and a rank that conflated the two would offer Anna's to a paper gap and Sci-Hub to a book gap.
SECTION_FAMILY = {"book_sources": "books", "paper_sources": "papers",
                  "shadow_sources": "shadow", "tools_not_integrated": "tools"}

#: The access vocabulary. `credential` and `captcha` are DISTINCT from `none`: one is waiting for the owner and the
#: other is waiting for a wall to move, and collapsing them would make the register lie in a useful direction.
ACCESS = {"api", "scrape", "browser", "credential", "captcha", "manual", "none"}


def load(path: Path | None = None) -> dict[str, Any]:
    """Read the register, refusing anything that is not a mapping (a silent empty register is worse than a crash)."""
    target = path or REGISTER
    try:
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AcquisitionError(f"the research-source register is missing: {target}") from error
    if not isinstance(document, dict):
        raise AcquisitionError(f"{target} did not parse into a mapping")
    return document


def entries(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Every source as `{family, id, ...}` — one flat list, so a check cannot miss a section by forgetting one."""
    flat: list[dict[str, Any]] = []
    for section in SECTIONS:
        for name, block in (document.get(section) or {}).items():
            block = block or {}
            flat.append({**block, "section": section,
                         "family": str(block.get("family") or SECTION_FAMILY[section]) or SECTION_FAMILY[section],
                         "id": str(name)})
    return flat


def check(document: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    """Return `(faults, notes)`. A fault is a declaration that does not resolve; a note is a measured absence."""
    document = document or load()
    faults: list[str] = []
    notes: list[str] = []
    for entry in entries(document):
        where = f"{entry['family']}.{entry['id']}"
        access = str(entry.get("access") or "")
        if access not in ACCESS:
            faults.append(f"{where}: access `{access}` is outside the declared vocabulary {sorted(ACCESS)}")
            continue
        if access == "api" and not str(entry.get("api_url") or "").strip():
            faults.append(f"{where}: access `api` with no api_url — a route that cannot be taken")
        auth = entry.get("auth")
        if isinstance(auth, str) and auth.startswith("env:") and not auth.split(":", 1)[1].strip():
            faults.append(f"{where}: auth names an env var but the name is empty")
        if access in {"manual", "none"} and not str(entry.get("why") or "").strip():
            faults.append(f"{where}: access `{access}` must say WHY it cannot be automated (D-3038)")
        measured = entry.get("measured") or {}
        if not measured.get("at"):
            faults.append(f"{where}: no `measured.at` — an unmeasured source is a rumour")
        elif not measured.get("code"):
            notes.append(f"{where}: NOT MEASURED (code {measured.get('code')}) — {measured.get('note', '')[:80]}")
    return faults, notes


def rank(task: str, document: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The sources a `task` may use, best first, with the limbs each one contributes.

    `task` is `books`, `papers`, `shadow` or `all`. Ordering is by tier (A before B before C before S), then by the
    number of signal limbs a source carries — because a source that can supply TWO limbs can settle a disagreement
    that a one-limb source can only add to. Integrability is a filter, not a preference: `manual` and `none` are
    returned LAST with their reason, so a caller that ignores them cannot pretend they were usable.
    """
    document = document or load()
    wanted = {"books": ("books",), "papers": ("papers",), "shadow": ("shadow",),
              "all": tuple(SECTION_FAMILY.values())}.get(task)
    if wanted is None:
        raise AcquisitionError(f"unknown task `{task}`; declared tasks are books|papers|shadow|all")
    usable = {"api", "scrape", "browser", "credential", "captcha"}
    rows = [entry for entry in entries(document) if entry["family"] in wanted]
    rows.sort(key=lambda entry: (
        0 if str(entry.get("access")) in usable else 1,
        {"A": 0, "B": 1, "C": 2, "S": 3}.get(str(entry.get("tier") or "C"), 2),
        -len(entry.get("signal") or []),
        str(entry["id"]),
    ))
    return rows
