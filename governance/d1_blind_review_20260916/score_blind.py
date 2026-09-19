#!/usr/bin/env python3
"""Score the blind D1 re-adjudication. Run after BLIND_D1_sheet.csv is filled in."""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    """Compare the adjudicated picks against the hidden model key."""
    key = json.loads((HERE / 'KEY_do_not_open_until_finished.json').read_text())
    rows = list(csv.DictReader((HERE / 'BLIND_D1_sheet.csv').open(encoding='utf-8')))
    tally = {'deepseek-v4-pro': 0, 'qwen3.8': 0}
    neither = blank = 0
    for r in rows:
        pick = (r.get('YOUR_PICK') or '').strip().lower()
        k = key[str(r['row'])]
        if pick in ('1', '2'):
            tally[k['candidate_' + pick]] += 1
        elif pick == 'neither':
            neither += 1
        else:
            blank += 1
    n = sum(tally.values())
    print('BLIND D1 RESULT — discipline, 60 disagreement rows')
    print('-' * 52)
    print(f"  deepseek-v4-pro : {tally['deepseek-v4-pro']}")
    print(f"  qwen3.8         : {tally['qwen3.8']}")
    print(f'  neither         : {neither}')
    print(f'  left blank      : {blank}')
    if n:
        print()
        print(f'  of {n} adjudicated: deepseek {tally["deepseek-v4-pro"]/n:.1%} '
              f'vs qwen3.8 {tally["qwen3.8"]/n:.1%}')
    if blank:
        print()
        print(f'  WARNING: {blank} rows blank — result is partial.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
