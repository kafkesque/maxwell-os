"""The lane's ONE HTTP surface (C21): a JSON read, a text read, and a byte download.

Why a single module: the acquirer talks to two kinds of server — an API that answers JSON and a mirror that
serves bytes — and both must share one user agent, one timeout, one size ceiling and one failure vocabulary. A
second urllib call site is how a lane grows a second, quieter definition of "reachable".
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import AcquisitionError

DEFAULT_UA = "maxwell-acq/1.0 (local sovereign knowledge acquisition; +D-3078)"


@dataclass(frozen=True)
class Failure:
    """A named network refusal. `class_` is the closed vocabulary the receipt records."""

    class_: str
    meaning: str
    url: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"failure_class": self.class_, "meaning": self.meaning, "url": self.url, "detail": self.detail}


class NetworkRefused(AcquisitionError):
    """Raised when a read cannot be performed; carries a Failure so a caller can record the class."""

    def __init__(self, failure: Failure) -> None:
        super().__init__(f"{failure.class_}: {failure.meaning} ({failure.url})")
        self.failure = failure


def _request(url: str, cfg: dict[str, Any], headers: dict[str, str] | None = None) -> urllib.request.Request:
    """Build a request carrying the declared identity and nothing ambient."""
    connection = cfg.get("download") or {}
    merged = {"User-Agent": str(connection.get("user_agent") or DEFAULT_UA), "Accept": "*/*"}
    merged.update(headers or {})
    return urllib.request.Request(url, headers=merged, method="GET")


def read_text(url: str, cfg: dict[str, Any], timeout_s: float | None = None,
              attempts: int | None = None) -> str:
    """Read a URL as text, refusing (never silently returning empty) on any transport failure.

    A 5xx carries its REASON in the body and the reason matters: MEASURED 2026-10-17, every LibGen front answered
    `500` with `Could not connect to the database 3306 … max_user_connections (current value: 300)` — a saturated
    mirror, not a blocked client. The body snippet is kept in the refusal so the reading names what happened.
    """
    connection = cfg.get("download") or {}
    timeout = float(timeout_s or (cfg.get("mirrors") or {}).get("probe_timeout_s", 20))
    #: `attempts` is an override for a PROBE (a mirror liveness check), never for a download: retrying a
    #: guard that answers 403 in a second turns a 3-domain probe into minutes (MEASURED 2026-10-17, BUG-911).
    if attempts is None:
        attempts = 1 + max(0, int(connection.get("retries") or 0))
    backoff = float(connection.get("retry_backoff_s") or 2)
    last: NetworkRefused | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(_request(url, cfg), timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read(4_000_000).decode(charset, errors="replace")
        except urllib.error.HTTPError as error:
            snippet = ""
            try:
                snippet = error.read(240).decode("utf-8", errors="replace")
            except OSError:
                snippet = ""
            last = NetworkRefused(
                Failure("http_status", "the server answered with an error", url, f"rc={error.code} {snippet}".strip())
            )
            # A 4xx will not become a 2xx by asking again; only a 5xx is worth another try.
            if error.code < 500:
                raise last from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = NetworkRefused(Failure("unreachable", "no answer before the timeout", url, str(error)))
        if attempt + 1 < attempts:
            time.sleep(backoff * (attempt + 1))
    if last is not None:
        raise last
    raise NetworkRefused(Failure("unreachable", "no attempt was made", url))


def read_json(url: str, cfg: dict[str, Any], timeout_s: float | None = None) -> Any:
    """Read a URL as JSON, refusing a body that is not JSON (a challenge page is not an answer)."""
    body = read_text(url, cfg, timeout_s)
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise NetworkRefused(
            Failure("not_json", "the body was not JSON — a challenge or error page, not an answer", url, body[:120])
        ) from error


def quote(value: str) -> str:
    """Quote a query for a URL without letting a space through."""
    return urllib.parse.quote_plus(value)


def download(url: str, dest: Path, cfg: dict[str, Any], referer: str | None = None) -> dict[str, Any]:
    """Download to a temp file in dest's directory, fsync, then atomically land it (C6).

    Returns {path, bytes, sha256, content_type}. Raises NetworkRefused for a transport failure and
    AcquisitionError for a body over the declared ceiling. The caller decides whether the bytes are a document.
    """
    connection = cfg.get("download") or {}
    ceiling = int(connection.get("max_bytes") or 268_435_456)
    timeout = float(connection.get("timeout_s") or 180)
    chunk = int(connection.get("chunk_bytes") or 1_048_576)
    headers = {"Referer": referer} if referer else None
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    handle, temp_name = tempfile.mkstemp(dir=str(dest.parent), prefix=".acq-", suffix=".part")
    try:
        with os.fdopen(handle, "wb") as sink:
            with urllib.request.urlopen(_request(url, cfg, headers), timeout=timeout) as response:
                content_type = response.headers.get_content_type()
                while True:
                    block = response.read(chunk)
                    if not block:
                        break
                    written += len(block)
                    if written > ceiling:
                        raise AcquisitionError(
                            f"the body exceeded the declared ceiling of {ceiling} bytes at {url} — a book, not a dataset"
                        )
                    digest.update(block)
                    sink.write(block)
            sink.flush()
            os.fsync(sink.fileno())
        if written == 0:
            raise NetworkRefused(Failure("empty_body", "the server answered with zero bytes", url))
        os.replace(temp_name, dest)
        temp_name = ""
        return {"path": dest, "bytes": written, "sha256": digest.hexdigest(), "content_type": content_type}
    except urllib.error.HTTPError as error:
        raise NetworkRefused(Failure("http_status", "the server answered with an error", url, f"rc={error.code}")) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise NetworkRefused(Failure("unreachable", "no answer before the timeout", url, str(error))) from error
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink(missing_ok=True)
