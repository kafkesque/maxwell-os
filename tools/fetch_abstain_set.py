#!/usr/bin/env python3
"""fetch_abstain_set.py — freeze the fail-closed / abstain eval set (D-2637).

Source of truth: governance/content_type_reverify_108.json — the D2629 re-verify of 108
queue rows by Qwen3.8-27B, adjudicated into the D2587 7-way content_type. 49/108 were
judged NOT principle (39 process_template, 4 noise_drop, 4 tool_instruction, 1
growth_edge, 1 process_instance); 59 remained principle.

This is the only adjudicated ground truth in the project that directly asks the
fail-closed question the pipeline cares about: 'is this transferable knowledge, or
should it be refused?' It is therefore the natural abstain suite — a model that
fabricates a principle out of a process template fails it.

Text is pulled from the production DB (knowledge pipeline/maxwell.db, fbs) so the suite
exercises the same FB shape S4 sees (definition + mechanism + boundary).

Output: governance/evalsets/abstain.jsonl
  {id, fb_id, name, text, content_type, answer}  answer in {principle, not_principle}

Usage: python3 tools/fetch_abstain_set.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERDICTS = ROOT / 'governance' / 'content_type_reverify_108.json'
DB = ROOT / 'knowledge pipeline' / 'maxwell.db'
OUT = ROOT / 'governance' / 'evalsets' / 'abstain.jsonl'
PRINCIPLE = 'principle'


def _fb_text(row: sqlite3.Row) -> str:
    """Assemble the FB text S4 sees: name + definition + mechanism + boundary."""
    parts = []
    for label, val in (('Name', row['name']), ('Definition', row['definition']),
                       ('Mechanism', row['mechanism']), ('Boundary', row['boundary'])):
        if val:
            parts.append(f'{label}: {val}')
    return chr(10).join(parts)


def main() -> int:
    """Materialise the frozen abstain eval set."""
    verdicts = json.loads(VERDICTS.read_text(encoding='utf-8'))['verdicts']
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    ids = [v['fb_id'] for v in verdicts]
    marks = ','.join('?' * len(ids))
    rows = {r['fb_id']: r for r in db.execute(
        f'select fb_id, name, definition, mechanism, boundary from fbs where fb_id in ({marks})',
        ids,
    )}
    db.close()

    out = []
    skipped = 0
    for v in verdicts:
        r = rows.get(v['fb_id'])
        text = _fb_text(r) if r else ''
        if not text.strip():
            skipped += 1
            continue
        ct = str(v['content_type']).strip().lower()
        out.append({
            'id': v['fb_id'][:16],
            'fb_id': v['fb_id'],
            'name': v.get('name', ''),
            'text': text,
            'content_type': ct,
            'answer': PRINCIPLE if ct == PRINCIPLE else 'not_principle',
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + chr(10))

    n_not = sum(1 for r in out if r['answer'] != PRINCIPLE)
    print(f'wrote {OUT}')
    print(f'  items {len(out)}  (principle {len(out) - n_not} / not-principle {n_not})')
    print(f'  skipped (no DB text) {skipped}')
    return 0


if __name__ == '__main__':
    sys.exit(main())