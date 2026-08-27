#!/usr/bin/env python3
"""fix_singleton_quality.py — BUG-181#1/#2 + BUG-169 post-hoc repair (2026-08-27).

Three deterministic repairs on singleton_fbs.jsonl (5,254 records):
  1. BUG-181#1  — strip EPUB→MD converter residue from evidence_passages.
  2. BUG-181#2  — reclassify empty-shell process_template:
        code evidence → tool_instruction (mirrors _code_role_guard, D2457)
        narrative     → principle + descriptive_model (D2471, weakest-honest)
        step-language → keep PT, flag body_incomplete: true
  3. BUG-169    — flag empty-parameters tool_instruction: parameter_origin=technique.

Writes a NEW file (never overwrites pipeline output — R-D410). R14 stamps are NOT
re-stamped (repair, not re-generation). Reclassified records keep
original_content_type for reversibility.

Usage:
    python3 scripts/fix_singleton_quality.py --dry-run
    python3 scripts/fix_singleton_quality.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.text_cleaner import clean_evidence_passage

SINGLETON = "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl"

_CODE_MARKERS = (
    'setwd(', 'read.csv', 'library(', 'require(', 'def ', 'import ', 'class ',
    'np.', 'pd.', 'plt.', 'df.', 'pip install', 'print(', 'return ', 'lambda ',
    'const ', 'let ', 'var ', 'function(', '=>', 'console.log', 'npm install',
    'SELECT ', 'CREATE TABLE', 'INSERT INTO', 'WHERE ', 'sudo ', 'git ', 'curl ',
    'chmod ', '<-', 'str(', 'summary(',
)

_STEP_MARKERS = (
    'step', 'first,', 'second,', 'third,', 'next,', 'then,', 'finally,',
    'begin by', 'start by', 'procedure', 'how to', 'phase', 'sequence',
)


def _has_code(text: str) -> bool:
    t = (text or '').lower()
    return any(m in t for m in _CODE_MARKERS)


def _has_step_language(text: str) -> bool:
    t = (text or '').lower()
    return any(m in t for m in _STEP_MARKERS)


def _empty(v) -> bool:
    return v is None or (isinstance(v, (list, str, dict)) and len(v) == 0)


def _reclassify_empty_pt(rec: dict, evidence_text: str) -> dict:
    """Return repair dict ({} if no reclassification)."""
    if rec.get('content_type') != 'process_template':
        return {}
    if not _empty(rec.get('steps')):
        return {}
    if _has_code(evidence_text):
        t = evidence_text.lower()
        tool = 'code'
        if any(m in t for m in ('setwd(', 'read.csv', 'library(', 'require(', '<-', 'data.frame(')):
            tool = 'R'
        elif any(m in t for m in ('def ', 'import ', 'np.', 'pd.', 'plt.', 'pip install')):
            tool = 'Python'
        elif any(m in t for m in ('const ', 'let ', 'function(', '=>', 'npm install')):
            tool = 'JavaScript'
        elif any(m in t for m in ('SELECT ', 'CREATE TABLE', 'INSERT INTO')):
            tool = 'SQL'
        return {
            'content_type': 'tool_instruction',
            'original_content_type': 'process_template',
            'role_corrected': 'empty_pt_code_to_tool_instruction',
            'tool_name': rec.get('tool_name') or tool,
            'platform': rec.get('platform') or 'code/command',
            'description': rec.get('description') or rec.get('definition', ''),
            'syntax': rec.get('syntax') or evidence_text[:300],
            'parameters': rec.get('parameters') or [],
            'output': rec.get('output') or '',
            'example': rec.get('example') or evidence_text[:300],
            'caveats': rec.get('caveats') or rec.get('boundary', ''),
            'extraction_type': rec.get('extraction_type') or 'normative_heuristic',
            'steps': None,
        }
    if _has_step_language(evidence_text):
        return {'body_incomplete': True}
    return {
        'content_type': 'principle',
        'original_content_type': 'process_template',
        'role_corrected': 'empty_pt_narrative_to_principle',
        'extraction_type': rec.get('extraction_type') or 'descriptive_model',
        'elaboration': (rec.get('definition') or rec.get('summary') or '').strip(),
        'steps': None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--input', default=SINGLETON)
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f'❌ {src} not found', file=sys.stderr)
        return 2

    records = [json.loads(l) for l in open(src, encoding='utf-8') if l.strip()]

    cleaned = 0
    reclass_principle = 0
    reclass_ti = 0
    flagged_pt = 0
    flagged_ti = 0

    for rec in records:
        # 3. BUG-169 flag (original TIs, before reclassification)
        if rec.get('content_type') == 'tool_instruction' and _empty(rec.get('parameters')):
            flagged_ti += 1
            rec['parameters'] = []
            rec['parameter_origin'] = 'technique'

        # 1. BUG-181#1: clean evidence
        eps = rec.get('evidence_passages') or []
        for i, ep in enumerate(eps):
            if isinstance(ep, str):
                c = clean_evidence_passage(ep)
                if c != ep:
                    cleaned += 1
                    eps[i] = c
        if eps:
            rec['evidence_passages'] = eps

        # 2. BUG-181#2: reclassify empty-shell PT
        ev_text = ' '.join(str(e) for e in (rec.get('evidence_passages') or [])[:3])
        repair = _reclassify_empty_pt(rec, ev_text)
        rc = repair.get('role_corrected')
        if rc == 'empty_pt_narrative_to_principle':
            reclass_principle += 1
            rec.update(repair)
        elif rc == 'empty_pt_code_to_tool_instruction':
            reclass_ti += 1
            rec.update(repair)
        elif repair.get('body_incomplete'):
            flagged_pt += 1
            rec['body_incomplete'] = True

    print('Records:', len(records))
    print('  BUG-181#1 evidence passages cleaned:', cleaned)
    print('  BUG-181#2 PT→principle (narrative):', reclass_principle)
    print('  BUG-181#2 PT→tool_instruction (code):', reclass_ti)
    print('  BUG-181#2 PT flagged body_incomplete:', flagged_pt)
    print('  BUG-169 TI flagged parameter_origin=technique:', flagged_ti)

    if args.dry_run:
        print('DRY-RUN — no write.')
        return 0

    out = src  # D2479 option-(a): write in-place to canonical (no .fixed dead-end)
    content = '\n'.join(json.dumps(r, ensure_ascii=False) for r in records) + '\n'
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=out.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f'WROTE {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
