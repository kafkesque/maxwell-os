#!/usr/bin/env python3
"""omlx_reload.py — re-discover oMLX models WITHOUT quitting the app.

D-2637: oMLX caches its model registry at app start, so a newly symlinked model is
invisible (and a deleted one still listed) until a GUI quit+reopen. The supported
path is the local admin API:

    POST /admin/api/login   {"api_key": ...}   -> session cookie
    POST /admin/api/reload  {}                  -> re-read model settings,
                                                   re-discover models, preload pinned

This supersedes scripts/_omlx_restart.py (which drove a stale control socket and never
worked) and MUST be used instead of `omlx-cli restart` (D2455/D2456 spawns a duplicate
managed server — caught by guard_stacks_single_source.py).

Usage:
    python3 scripts/omlx_reload.py            # reload + print registry
    python3 scripts/omlx_reload.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

OMLX_BASE = os.environ.get('OMLX_BASE_URL', 'http://127.0.0.1:11435')
API_KEY = os.environ.get('OMLX_API_KEY', 'sk-maxwell-local')
TIMEOUT_S = int(os.environ.get('OMLX_RELOAD_TIMEOUT_S', '180'))


def _post(path: str, payload: dict, cookie: str | None = None) -> tuple[dict, str | None]:
    """POST JSON to the oMLX admin API; return (body, session-cookie).

    Raises urllib.error.HTTPError on non-2xx so a failure is never silent (C16).
    """
    req = urllib.request.Request(
        OMLX_BASE + path,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': f'Bearer {API_KEY}',
                 **({'Cookie': cookie} if cookie else {})},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        body = json.loads(resp.read().decode() or '{}')
        set_cookie = resp.headers.get('Set-Cookie')
    new_cookie = set_cookie.split(';')[0] if set_cookie else cookie
    return body, new_cookie


def _list_models() -> list[str]:
    """Return the model ids currently served on /v1/models."""
    req = urllib.request.Request(OMLX_BASE + '/v1/models',
                                 headers={'Authorization': f'Bearer {API_KEY}'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return sorted(m['id'] for m in data.get('data', []))


def reload_models() -> dict:
    """Re-discover models and re-read per-model settings; return a summary dict."""
    _, cookie = _post('/admin/api/login', {'api_key': API_KEY})
    result, _ = _post('/admin/api/reload', {}, cookie=cookie)
    ids = _list_models()
    return {'reload': result, 'count': len(ids), 'models': ids}


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    args = ap.parse_args()

    try:
        summary = reload_models()
    except Exception as exc:
        print(f'ERROR: oMLX reload failed ({type(exc).__name__}: {exc})', file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=1))
    else:
        print(summary['reload'].get('message', summary['reload']))
        print(f'{summary["count"]} models:')
        for mid in summary['models']:
            print('  ' + mid)
    return 0


if __name__ == '__main__':
    sys.exit(main())