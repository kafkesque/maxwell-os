"""The downloader: ONE write path from a manifest row to a file in the owner's INBOX.

THE LAW OF THIS MODULE (D-3078): the only path it may write a book to is the pen named by
`config/acquisition.yaml#pens.land`, which RESOLVES to `config/ingest_identity_gate.yaml#
source_library.placement.pens.education_inbox` — the owner's own admission queue, i.e. the INBOX directory itself,
never a subfolder, never `knowledge pipeline/books`, never an `.md`, never a signature, never a conversion.

WHAT IT DOES, in order, for each candidate:
  1. skip when the canonical id is already IN THE INDEX with state `landed` (idempotent by identity, not by name)
  2. walk the declared adapter ladder, LAWFUL FIRST, and ask the first adapter that can serve it
  3. download to a `.part` temp file in the pen, fsync, then `os.replace` (C6 — a crash leaves no half book)
  4. probe the landed bytes with THE DOOR'S OWN probe (no second definition of readable)
     • readable  → keep it in the pen, record `landed`
     • unreadable → move it to the quarantine pen and record `refused_container_unreadable`
  5. append one receipt line (R14: schema_version, gen_model, pipeline_commit) and one index line

A failed transfer is a NAMED refusal, never a silent nothing: `unreachable`, `http_status`, `not_json`,
`adapter_miss`, `adapter_disabled`, `breaker_open`, `over_ceiling`, `probe_absent`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import adapters as adapter_module
from . import net
from .config import ROOT, AcquisitionError, land_pen, name_template, pipeline_commit, probe_map
from .resolvers import Candidate

CONTENT_TYPE_EXTENSION = {
    "application/epub+zip": "epub",
    "application/pdf": "pdf",
    "application/x-mobipocket-ebook": "mobi",
    "application/vnd.amazon.ebook": "azw3",
    "text/plain": "txt",
    "application/rtf": "rtf",
}
UNSAFE = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")


@dataclass
class Outcome:
    """What happened to one candidate, as it will be recorded."""

    canonical_id: str
    title: str
    state: str
    attempts: list[dict[str, Any]] = field(default_factory=list)
    path: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    licence_class: str | None = None
    adapter: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "title": self.title,
            "state": self.state,
            "adapter": self.adapter,
            "licence_class": self.licence_class,
            "path": self.path,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "attempts": self.attempts,
        }


def _stamp() -> str:
    """UTC stamp, the one form the evidence files use."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_name(candidate: Candidate, extension: str, template: str) -> str:
    """Render the owner's own filename template, sanitised — a name is a handle, never a claim.

    MEASURED constraint, not a preference: an admitted name becomes the corpus name AND the door key, and the
    door refuses any name its marker/spine/truncation patterns match. So a new arrival carries no mirror marker,
    no `--`, no 16-hex digest and no trailing `_` — the acquirer must not manufacture a file the door will refuse.
    """
    author = "; ".join(candidate.authors[:3]) if candidate.authors else "Unknown"
    title = candidate.title
    values = {"author": author, "title": title, "year": candidate.year}
    try:
        stem = template.format(**values)
    except (KeyError, IndexError) as error:
        raise AcquisitionError(f"the name template `{template}` cannot be rendered: {error}") from error
    if not candidate.year:
        stem = re.sub(r"\s*-\s*(?:None|)\s*$", "", stem)
    stem = unicodedata.normalize("NFC", stem)
    stem = UNSAFE.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" -_.,;")
    stem = re.sub(r"\s*-\s*", " - ", stem)
    return f"{stem[:200]}.{extension}"


def _extension(delivery: adapter_module.Delivery, content_type: str | None, probes: dict[str, str]) -> str:
    """Decide the suffix from the BODY first, then the adapter's hint, then the URL — and only a probed kind."""
    by_type = CONTENT_TYPE_EXTENSION.get(str(content_type or "").split(";")[0].strip())
    hint = (delivery.content_hint or "").lstrip(".").lower()
    url_suffix = delivery.url.split("?")[0].rsplit(".", 1)[-1].lower()
    for option in (by_type, hint, url_suffix):
        if option and option in probes:
            return option
    raise AcquisitionError(
        f"cannot name the delivered bytes: content_type={content_type!r}, hint={hint!r}, url={delivery.url!r},"
        f" probed kinds={sorted(probes)}"
    )


def _unique_path(directory: Path, name: str) -> Path:
    """A second work with the same author/title/year must not overwrite the first."""
    target = directory / name
    if not target.exists():
        return target
    stem, dot, suffix = name.rpartition(".")
    counter = 2
    while True:
        candidate = directory / f"{stem} ({counter}){dot}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _index_path(cfg: dict[str, Any]) -> Path:
    """The idempotency index: canonical id → what was attempted."""
    return ROOT / str((cfg.get("pens") or {}).get("index") or "knowledge pipeline/acquisition/index.jsonl")


def load_index(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Read the index into memory, last line wins; a corrupt line is skipped, never fatal."""
    path = _index_path(cfg)
    held: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return held
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("canonical_id"):
            held[str(row["canonical_id"])] = row
    return held


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one line, fsynced — the receipt is a record, so it must survive the crash it describes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def probe_landed(path: Path, extension: str, probes: dict[str, str]) -> tuple[bool, str]:
    """Ask the DOOR whether the bytes are the container their name claims."""
    from pipeline.container_integrity import is_readable  # the door's own probe, one definition (D-3071)

    token = probes.get(extension)
    if not token:
        return False, "probe_absent"
    try:
        return (True, token) if is_readable(path, token) else (False, f"{token}_failed")
    except OSError as error:
        return False, f"{token}_error:{error}"


def fetch_manifest(
    manifest_path: Path,
    cfg: dict[str, Any],
    *,
    allow_shadow: bool = False,
    owner_word: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute a manifest: locate, download, probe, land in the INBOX, record. Returns the run's reading.

    `allow_shadow` is the owner's word for the shadow rungs. Without it the ladder stops after the lawful rungs,
    and every shadow adapter that could have served the work is recorded as `adapter_disabled` — the hole is
    visible, never silent.
    """
    if allow_shadow and not (owner_word or "").strip():
        raise AcquisitionError("allow_shadow requires an owner word: D-3078 says the shadow lane is opt-in BY NAME")
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    candidates = [Candidate(**{key: value for key, value in row.items() if key in Candidate.__dataclass_fields__})
                  for row in payload.get("candidates") or []]
    if limit:
        candidates = candidates[: int(limit)]
    pen = land_pen(cfg)
    probes = probe_map()
    template = name_template()
    ladder = adapter_module.ladder(cfg, allow_shadow)
    if not ladder:
        raise AcquisitionError("no adapter is enabled — the ladder is empty and nothing can be fetched")
    index = load_index(cfg)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / str((cfg.get("pens") or {}).get("evidence") or "governance/evidence") / f"ACQUISITION_{stamp}.jsonl"
    quarantine = ROOT / str((cfg.get("pens") or {}).get("quarantine") or "knowledge pipeline/acquisition/quarantine") / stamp
    breaker = {"failures": {}, "open": set()}
    threshold = int(((cfg.get("download") or {}).get("circuit_breaker") or {}).get("failures") or 3)
    outcomes: list[Outcome] = []
    for candidate in candidates:
        outcome = Outcome(canonical_id=candidate.canonical_id, title=candidate.title, state="unattempted")
        held = index.get(candidate.canonical_id)
        if held and held.get("state") == "landed" and held.get("path") and Path(str(held["path"])).exists():
            outcome.state = "skipped_already_landed"
            outcome.path = str(held["path"])
            outcomes.append(outcome)
            continue
        for adapter in ladder:
            if adapter.id in breaker["open"]:
                outcome.attempts.append({"adapter": adapter.id, "failure_class": "breaker_open"})
                continue
            try:
                delivery = adapter.locate(candidate, cfg)
            except adapter_module.AdapterMiss as miss:
                outcome.attempts.append({"adapter": adapter.id, "failure_class": "adapter_miss", "detail": str(miss)[:300]})
                continue
            except AcquisitionError as refusal_error:
                # R5 FINDING (gemma-4-E4B-it, a different family, 2026-10-17): a refusal that is NOT a miss — e.g.
                # `no VALIDATED mirror for libgen` from mirrors.live_domains — used to escape this loop and ABORT THE
                # WHOLE RUN, so one saturated mirror ended a manifest of ten candidates after the first. A source that
                # cannot serve is a property of that SOURCE, not of the run: it is recorded against this adapter and
                # the ladder moves on. A genuine config fault still fails fast, because the declaration is read
                # before this loop (land_pen, ladder, probe_map).
                outcome.attempts.append({"adapter": adapter.id, "failure_class": "adapter_error", "detail": str(refusal_error)[:300]})
                continue
            except net.NetworkRefused as refusal:
                outcome.attempts.append({"adapter": adapter.id, **refusal.failure.as_dict()})
                breaker["failures"][adapter.id] = breaker["failures"].get(adapter.id, 0) + 1
                if breaker["failures"][adapter.id] >= threshold:
                    breaker["open"].add(adapter.id)
                continue
            if dry_run:
                outcome.state = "would_fetch"
                outcome.adapter = adapter.id
                outcome.licence_class = delivery.licence_class
                outcome.attempts.append({"adapter": adapter.id, "url": delivery.url, "dry_run": True})
                break
            try:
                landed = _receive(delivery, candidate, pen.path, cfg, probes, template)
            except (net.NetworkRefused, AcquisitionError) as failure:
                failure_class = getattr(getattr(failure, "failure", None), "class_", "download_failed")
                outcome.attempts.append({"adapter": adapter.id, "failure_class": failure_class, "detail": str(failure)[:300]})
                breaker["failures"][adapter.id] = breaker["failures"].get(adapter.id, 0) + 1
                if breaker["failures"][adapter.id] >= threshold:
                    breaker["open"].add(adapter.id)
                continue
            if landed["readable"]:
                outcome.state = "landed"
                outcome.adapter = adapter.id
                outcome.path = str(landed["path"])
                outcome.bytes = landed["bytes"]
                outcome.sha256 = landed["sha256"]
                outcome.licence_class = delivery.licence_class
                outcome.attempts.append({"adapter": adapter.id, "url": delivery.url, "probe": landed["probe"]})
                # R5 FINDING (gemma-4-E4B-it, 2026-10-17): the failure counter was never RESET, so an adapter that
                # failed three times across a long manifest opened its breaker even while it was still serving —
                # the breaker measured the run's history, not the adapter's health. A success IS the health signal.
                breaker["failures"][adapter.id] = 0
                break
            # The bytes arrived and are NOT the container their name claims: it does not stay in the inbox.
            quarantine.mkdir(parents=True, exist_ok=True)
            parked = quarantine / Path(str(landed["path"])).name
            shutil.move(str(landed["path"]), str(parked))
            outcome.state = "refused_container_unreadable"
            outcome.adapter = adapter.id
            outcome.path = str(parked)
            outcome.attempts.append({"adapter": adapter.id, "url": delivery.url, "probe": landed["probe"], "quarantined": str(parked)})
            break
        if outcome.state in {"unattempted"}:
            outcome.state = "refused_no_adapter_served"
        outcomes.append(outcome)
        _append_jsonl(
            evidence,
            {
                "schema_version": "1.0",
                "gen_model": "deterministic",
                "pipeline_commit": pipeline_commit(),
                "ts": _stamp(),
                "act": "acquisition_fetch",
                "authority": "D-3078",
                "manifest": str(manifest_path),
                "gap": payload.get("gap"),
                "owner_word": owner_word if allow_shadow else None,
                "pent": pen.name,
                "outcome": outcome.as_dict(),
            },
        )
        _append_jsonl(
            _index_path(cfg),
            {
                "schema_version": "1.0",
                "ts": _stamp(),
                "canonical_id": outcome.canonical_id,
                "state": outcome.state,
                "adapter": outcome.adapter,
                "path": outcome.path,
                "sha256": outcome.sha256,
                "licence_class": outcome.licence_class,
            },
        )
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.state] = counts.get(outcome.state, 0) + 1
    # Leave the owner's pen as tidy as it was found: the staging directory is scaffolding, and an empty one left
    # behind is clutter in a queue the owner reads by eye. It is removed ONLY when empty — a leftover .part is a
    # transfer that was interrupted, and deleting it silently would erase the very evidence of the interruption.
    try:
        (pen.path / ".acq-staging").rmdir()
    except OSError:
        pass
    return {
        "schema_version": "1.0",
        "gen_model": "deterministic",
        "act": "acquisition_fetch",
        "authority": "D-3078",
        "pent": pen.name,
        "pent_path": str(pen.path),
        "manifest": str(manifest_path),
        "dry_run": dry_run,
        "allow_shadow": allow_shadow,
        "adapters": [adapter.id for adapter in ladder],
        "outcomes": [outcome.as_dict() for outcome in outcomes],
        "counts": counts,
        "evidence": str(evidence),
    }


def _receive(
    delivery: adapter_module.Delivery,
    candidate: Candidate,
    directory: Path,
    cfg: dict[str, Any],
    probes: dict[str, str],
    template: str,
) -> dict[str, Any]:
    """Download one delivery into the inbox, name it, probe it. Returns the landed facts.

    The temp file lives in the PEN and is renamed in place, so a crash cannot leave a partial book wearing a
    finished name, and a Dropbox sync cannot upload a half file under the work's real identity.
    """
    staging = directory / ".acq-staging"
    staging.mkdir(parents=True, exist_ok=True)
    provisional = staging / f"{hashlib.sha256(candidate.canonical_id.encode()).hexdigest()[:16]}.part"
    try:
        got = net.download(delivery.url, provisional, cfg, referer=delivery.referer)
        extension = _extension(delivery, got["content_type"], probes)
        name = render_name(candidate, extension, template)
        target = _unique_path(directory, name)
        os.replace(str(provisional), str(target))
        readable, probe = probe_landed(target, extension, probes)
        return {
            "path": target,
            "bytes": got["bytes"],
            "sha256": got["sha256"],
            "readable": readable,
            "probe": probe,
            "extension": extension,
        }
    finally:
        if provisional.exists():
            provisional.unlink(missing_ok=True)
