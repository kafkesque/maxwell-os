"""The one browser engine for the acquisition lane (C21): a real Chrome window, one persistent profile.

WHY THIS FILE EXISTS AT ALL, AND WHY IT IS NOT HEADLESS (MEASURED 2026-10-17, three receipts):

  * `annas-archive.gl/search?q=...` with `urllib` (browser headers, retries)  -> HTTP 403, 902 B, title
    `DDoS-Guard`. Same for `/md5/<hash>` and `/scidb/<doi>`: EVERY page of the only shadow library whose
    catalogue indexes all three families is behind a JS challenge a plain HTTP client cannot answer.
  * Playwright **headless** Chrome, same URL -> HTTP 403, 1,896 B, title `DDoS-Guard`. Headless is detected.
  * Playwright **headed** Chrome (`channel="chrome"`, `--disable-blink-features=AutomationControlled`,
    persistent profile) -> the challenge runs, the page RELOADS ITSELF, and 14 s later the settled document is
    693,342 B with 116 `/md5/` rows. From that page, `/md5/<hash>` yields 16 `slow_download` and 105
    `fast_download` links, and `/slow_download/<hash>/0/0` settles in 24 s to a direct node URL carrying a real
    `.epub`.

So the engine is DECLARED, not assumed: a rung whose source needs JavaScript says so, and when the engine is
missing the miss NAMES the remedy instead of pretending the source is dead (D-3034/D-3038). Nothing here decides
what to fetch: the engine returns settled HTML to an adapter, and only the downloader writes bytes.
"""

from __future__ import annotations

import re
import time
from typing import Any

from .config import AcquisitionError

#: The settled-document test: a challenge page is small and carries the guard's own name; a settled page does not.
CHALLENGE = re.compile(r"(?i)ddos-guard|checking your browser|cf-browser-verification|just a moment")


class BrowserRefused(AcquisitionError):
    """The engine cannot serve this request — a MISS with a named remedy, never a silent empty body."""


def available() -> tuple[bool, str]:
    """Whether a browser engine is installed, and what to do when it is not.

    Returns `(ok, detail)`. `detail` is read by the miss message, so an absent engine reads as an instruction
    (`pip install playwright`) rather than as `annas is down` — the two are different facts.
    """
    try:
        import playwright  # noqa: F401
    except Exception:
        return False, "playwright is not installed (`python3 -m pip install playwright && playwright install chrome`)"
    return True, "playwright"


class Browser:
    """A context manager over ONE headed Chrome with a persistent profile.

    The profile is not cosmetic: it holds the challenge cookie, so a second request in the same run (search →
    md5 → slow_download) pays the challenge once instead of three times (MEASURED: first settle 14 s, later
    navigations 3–24 s).
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        block = (cfg.get("browser") or {})
        self.headless = bool(block.get("headless", False))
        self.timeout_ms = int(float(block.get("navigation_timeout_s") or 60) * 1000)
        self.challenge_s = float(block.get("challenge_wait_s") or 30)
        self.profile = str(block.get("profile_dir") or "knowledge pipeline/acquisition/browser-profile")
        self._pw = None
        self._ctx = None

    # -- lifecycle -------------------------------------------------------------------------------------
    def __enter__(self) -> "Browser":
        ok, detail = available()
        if not ok:
            raise BrowserRefused(detail)
        from playwright.sync_api import sync_playwright  # imported HERE: the engine is optional (C28)

        self._pw = sync_playwright().start()
        try:
            self._ctx = self._pw.chromium.launch_persistent_context(
                self.profile,
                headless=self.headless,
                channel=str((self.cfg.get("browser") or {}).get("channel") or "chrome"),
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
        except Exception as error:  # a missing Chrome binary is a NAMED fault, not a crash
            self._stop()
            raise BrowserRefused(f"the browser engine could not start: {type(error).__name__}: {error}") from error
        return self

    def __exit__(self, *_exc: object) -> None:
        self._stop()

    def _stop(self) -> None:
        for closer in (getattr(self._ctx, "close", None), getattr(self._pw, "stop", None)):
            if closer is not None:
                try:
                    closer()
                except Exception:
                    pass
        self._ctx = None
        self._pw = None

    # -- reading ----------------------------------------------------------------------------------------
    def get(self, url: str, *, settled: "re.Pattern[str] | None" = None, wait_s: float | None = None) -> str:
        """Navigate, let the challenge settle, and return the settled HTML.

        `settled` is a pattern the caller knows appears only on a real page (an `/md5/` row, a `download` link) —
        the loop waits for THAT rather than for a timer, because a challenge that passes in 14 s would otherwise
        cost a fixed 30 s on every call. `wait_s` overrides the ceiling for a source that serves a countdown.
        """
        if self._ctx is None:
            raise BrowserRefused("the browser engine is not open (use it as a context manager)")
        page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        try:
            page.goto(url, wait_until="commit", timeout=self.timeout_ms)
        except Exception as error:
            raise BrowserRefused(f"navigation refused: {type(error).__name__}: {error}") from error
        ceiling = float(wait_s if wait_s is not None else self.challenge_s)
        deadline = time.monotonic() + ceiling
        last = ""
        while time.monotonic() < deadline:
            time.sleep(1.5)
            try:
                body = page.content()
            except Exception:
                continue  # the challenge is reloading the document; that is the expected state, not an error
            last = body
            if settled is not None and settled.search(body):
                return body
            if settled is None and not CHALLENGE.search(body):
                return body
        raise BrowserRefused(
            f"no settled document within {ceiling:.0f}s for {url}: the page still reads "
            f"{'a JS challenge' if CHALLENGE.search(last) else 'incomplete'} ({len(last)} B)"
        )
