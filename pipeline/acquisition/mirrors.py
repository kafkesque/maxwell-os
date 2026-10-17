"""Mirror resolution: ask the tracker, VALIDATE by content, cache the answer.

MEASURED 2026-10-17, and the reason this module exists at all: `annas-archive.li` answered HTTP 200 with a
27,799-byte PARKED-DOMAIN page ("for sale"), while `annas-archive.org` resolved to no address at all and
`libgen.is` timed out. A status code is therefore not liveness and a domain list is not a belief. A mirror is
used only after its body carries the family's own marker.

The tracker (open-slum.org) is read as HTML: its JSON endpoint is NOT verified, so the HTML parse is a DECLARED
debt, and a parse that finds nothing falls back to the config's candidate list rather than to a hardcoded domain.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

from . import net
from .config import ROOT, AcquisitionError

FAMILY_PATTERN = {
    #: `[a-z]{2,4}` alone matched `libgen.html` — a filename inside the tracker's own markup, not a domain
    #: (MEASURED 2026-10-17: it cost a probe and then failed validation). File suffixes are excluded by name.
    "annas": re.compile(r"\bannas-archive\.(?!html\b|php\b|js\b|css\b)[a-z]{2,4}\b"),
    "libgen": re.compile(r"\blibgen\.(?!html\b|php\b|js\b|css\b|shtml\b)[a-z]{2,4}\b"),
}


def _cache_path(cfg: dict[str, Any]) -> Path:
    """The mirror cache lives beside the lane's other state, never in the corpus."""
    return ROOT / str((cfg.get("mirrors") or {}).get("cache") or "knowledge pipeline/acquisition/mirrors.json")


def _read_cache(cfg: dict[str, Any], family: str) -> list[str] | None:
    """Return a FRESH validated list for this family, or None when the cache is absent, stale or unusable."""
    path = _cache_path(cfg)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    held = payload.get(family) or {}
    stamp = held.get("validated_at")
    if not stamp:
        return None
    try:
        when = _dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None
    age_hours = (_dt.datetime.now(_dt.timezone.utc) - when).total_seconds() / 3600.0
    if age_hours > float((cfg.get("mirrors") or {}).get("ttl_hours") or 6):
        return None
    domains = [str(item) for item in (held.get("domains") or [])]
    return domains or None


def _write_cache(cfg: dict[str, Any], family: str, domains: list[str], rejected: list[dict[str, str]]) -> None:
    """Record what was validated AND what was rejected with its reason: a rejected domain is a finding."""
    path = _cache_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    payload[family] = {
        "validated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domains": domains,
        "rejected": rejected,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def candidates_from_tracker(cfg: dict[str, Any], family: str) -> list[str]:
    """Domains the tracker currently names for a family, de-duplicated and ordered as published."""
    tracker = str((cfg.get("mirrors") or {}).get("source") or "")
    pattern = FAMILY_PATTERN.get(family)
    if not tracker or not pattern:
        return []
    try:
        body = net.read_text(tracker, cfg)
    except net.NetworkRefused:
        return []
    return list(dict.fromkeys(pattern.findall(body)))


def validate(cfg: dict[str, Any], family: str, domain: str) -> tuple[bool, str]:
    """A domain is USABLE only when its body carries the family's marker.

    This is the check that a parked domain fails while returning 200, and it is the reason the acquirer can
    print 'no mirror' instead of downloading a for-sale page into the owner's pen.
    """
    markers = ((cfg.get("mirrors") or {}).get("markers") or {}).get(family) or []
    try:
        body = net.read_text(f"https://{domain}/", cfg)
    except net.NetworkRefused as refusal:
        return False, refusal.failure.class_
    missing = [marker for marker in markers if marker.lower() not in body.lower()]
    if missing:
        # A 200 whose body is a for-sale page is the exact failure this measure catches.
        return False, "marker_absent"
    return True, "marker_present"


def live_domains(cfg: dict[str, Any], family: str, refresh: bool = False) -> list[str]:
    """Validated domains for a family, cached for the declared TTL; refusal is named, never defaulted."""
    if not refresh:
        cached = _read_cache(cfg, family)
        if cached:
            return cached
    declared = [str(item) for item in ((cfg.get("mirrors") or {}).get("declared") or {}).get(family) or []]
    pool = list(dict.fromkeys(candidates_from_tracker(cfg, family) + declared))
    if not pool:
        raise AcquisitionError(f"no candidate mirror for `{family}`: the tracker named none and none is declared")
    usable: list[str] = []
    rejected: list[dict[str, str]] = []
    for domain in pool:
        ok, reason = validate(cfg, family, domain)
        if ok:
            usable.append(domain)
        else:
            rejected.append({"domain": domain, "why": reason})
        if len(usable) >= 3:
            break
    if not usable:
        raise AcquisitionError(f"no VALIDATED mirror for `{family}`: {rejected}")
    _write_cache(cfg, family, usable, rejected)
    return usable
