"""The acquisition lane (D-3078): gap → manifest → bytes in a PEN.

Four acts, four modules, one invariant:

    gaps.py       DETECT   what the knowledge layer cannot back, in its three declared classes (T0, no network)
    resolvers.py  ASK      a gap becomes a ranked manifest of RESOLVER-RETURNED works (T1, no model writes a title)
    adapters.py   LOCATE   one protocol, N sources, lawful-first; a shadow rung needs an owner word (T0)
    downloader.py FETCH    one write path: probed bytes into the owner's INBOX, and a receipt (T0)

`scripts/acquire.py` is the only entry point. Nothing here writes the corpus, an `.md`, a signature or a
conversion — the ingest door owns all four (D-3078).
"""

from __future__ import annotations

__all__ = [
    "AcquisitionError",
    "adapters",
    "config",
    "downloader",
    "gaps",
    "mirrors",
    "net",
    "resolvers",
]

LANE = "acquisition"
AUTHORITY = "D-3078"
