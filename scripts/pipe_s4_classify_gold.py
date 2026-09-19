#!/usr/bin/env python3
"""pipe_s4_classify_gold.py — score the REAL production S4 classifier path against gold_4axis.

Unlike tools/benchmark_s4_classifiers.py (field-agreement only) and
tools/benchmark_s4_merged_production.py (latency only), this calls the true
pipeline.stage4_merged_call.merged_cribs_classify() — real system prompt, real reasoning
suppression, real max_tokens, real fail-closed validators — on real FBs pulled from
maxwell.db, and scores discipline exact-match + domain F1 against the human-adjudicated
governance/gold_4axis.jsonl.

Authority: D-2637 (S4 classifier swap gate). Resumable, append-only checkpoint (C6/R14).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage4_merged_call import merged_cribs_classify  # noqa: E402
# BUG-260: the production path does NOT compare the LLM's raw label to the taxonomy.
# merged_cribs_classify() returns a RAW scientific label by design and stage4_merge then maps it
# into the taxonomy (D2138 two-stage: the raw label captures what the principle IS, the canonical
# label organises it). Scoring the raw label directly against canonical gold understates EVERY
# model — measured 2026-09-16 on 60 gold rows: Qwen3.8 discipline 0.217 unmapped vs 0.350 mapped,
# domain F1 0.109 vs 0.335. We therefore replicate the production mapping (including D2515
# compound decomposition) and score on the MAPPED labels, keeping the raw numbers alongside.
from pipeline.stage4_merge import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    map_to_canonical_with_fallback,
    split_compound,
)
from pipeline.schemas import get_synonym_index  # noqa: E402

_SYNONYM_INDEX = get_synonym_index()

# RETIRED MODELS (D-2637 gate [[G3]], retired 2026-09-16). Measured: Qwen3.8-27B-OptiQ-4bit
# failed the output contract on 40 of 128 voting rows ('no json': it reasons first, exceeds
# max_tokens, and the JSON is cut mid-string) at 75.9s/row vs 16.5s for the uniform 4-bit. For a
# fail-closed S4 path that means mostly SparseClassificationError, so an S4 run on it would
# measure the format failure, not accuracy. Refusing to run it also stops a retired (hence
# unregistered → 404) model from burning an hour of requests.
RETIRED_MODELS: set[str] = {"Qwen3.8-27B-OptiQ-4bit"}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / 'governance' / 'gold_4axis.jsonl'
DB = PROJECT_ROOT / 'knowledge pipeline' / 'maxwell.db'
CKPT = PROJECT_ROOT / 'governance' / 'pipe_s4_classify_checkpoint.jsonl'
SUITE = 'pipe_s4_classify'
FB_FIELDS = ('name', 'definition', 'mechanism', 'boundary', 'consequence')


def canon(x: object) -> str:
    """Normalise a label for comparison (case/space insensitive)."""
    return str(x).strip().lower()


def load_gold() -> dict[str, dict]:
    """Return {fb_id: gold_row} for rows carrying both discipline and domains."""
    gold: dict[str, dict] = {}
    for line in GOLD.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get('discipline') and r.get('domains'):
            gold[r['fb_id']] = r
    return gold


def load_fbs(fb_ids: list[str]) -> dict[str, dict]:
    """Return {fb_id: {name, definition, mechanism, boundary, consequence}} from maxwell.db."""
    db = sqlite3.connect(DB)
    placeholders = ','.join('?' * len(fb_ids))
    cols = ','.join(FB_FIELDS)
    rows = db.execute(
        f'select fb_id,{cols} from fbs where fb_id in ({placeholders})', fb_ids
    ).fetchall()
    db.close()
    return {r[0]: dict(zip(FB_FIELDS, r[1:])) for r in rows}


def domain_f1(pred: set[str], gold: set[str]) -> float:
    """Per-row F1 over the domain label sets."""
    if not pred or not gold:
        return 0.0
    tp = len(pred & gold)
    if tp == 0:
        return 0.0
    prec, rec = tp / len(pred), tp / len(gold)
    return 2 * prec * rec / (prec + rec)


def map_discipline(raw: str) -> str:
    """Map a raw LLM discipline label into the canonical taxonomy (production logic)."""
    if not raw or not raw.strip():
        return 'emerging'
    return map_to_canonical_with_fallback(
        raw, 'discipline', _SYNONYM_INDEX, CANONICAL_DISCIPLINES
    )


def map_domains(raws: list[str]) -> list[str]:
    """Map raw LLM domain labels to canonical, incl. D2515 compound decomposition.

    Mirrors the production loop in stage4_merge: synonyms first, then split compound labels
    ("marketing & advertising") into constituents, and only then park as 'emerging'.
    """
    out: list[str] = []
    seen: set[str] = set()
    for d in raws:
        mapped = map_to_canonical_with_fallback(d, 'domain', _SYNONYM_INDEX, CANONICAL_DOMAINS)
        if mapped != 'emerging':
            if mapped not in seen:
                seen.add(mapped)
                out.append(mapped)
            continue
        parts = split_compound(d)
        decomposed = False
        if len(parts) > 1:
            for part in parts:
                pm = map_to_canonical_with_fallback(part, 'domain', _SYNONYM_INDEX, CANONICAL_DOMAINS)
                if pm != 'emerging':
                    decomposed = True
                    if pm not in seen:
                        seen.add(pm)
                        out.append(pm)
        if not decomposed and 'emerging' not in seen:
            seen.add('emerging')
            out.append('emerging')
    return out or ['emerging']


def score_row(row: dict, gold: dict) -> dict:
    """Score a checkpoint row on MAPPED labels, keeping the unmapped comparison for audit.

    Recomputes from the stored raw predictions, so it retro-corrects rows measured before
    BUG-260 was fixed without re-running the model.
    """
    pred_disc_raw = canon(row.get('pred_discipline', ''))
    pred_dom_raw = {canon(x) for x in (row.get('pred_domains') or [])}
    pred_disc = canon(map_discipline(pred_disc_raw))
    pred_dom = {canon(x) for x in map_domains(sorted(pred_dom_raw))}
    gold_disc = canon(gold['discipline'])
    gold_dom = {canon(x) for x in gold['domains']}
    return {
        'disc_exact': int(pred_disc == gold_disc),
        'dom_f1': round(domain_f1(pred_dom, gold_dom), 4),
        'raw_disc_exact': int(pred_disc_raw == gold_disc),
        'raw_dom_f1': round(domain_f1(pred_dom_raw, gold_dom), 4),
        'pred_discipline_canonical': pred_disc,
        'domains_emerging': int('emerging' in pred_dom),
    }


def done_keys() -> set[tuple[str, str]]:
    """(model, fb_id) pairs already measured — transport errors are retried (BUG-253)."""
    done: set[tuple[str, str]] = set()
    if not CKPT.exists():
        return done
    for line in CKPT.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get('err'):
            continue
        done.add((d['model'], d['fb_id']))
    return done


def append(row: dict) -> None:
    """Append one result row to the checkpoint (crash-safe append)."""
    with CKPT.open('a') as fh:
        fh.write(json.dumps(row) + chr(10))


def measure(model: str, fb_id: str, fb: dict, gold: dict) -> dict:
    """Run the production merged CRIBS+classify call once and score it against gold."""
    t0 = time.time()
    row = {'suite': SUITE, 'model': model, 'fb_id': fb_id, 'ts': time.time()}
    try:
        out = merged_cribs_classify(dict(fb), model=model)
        row['secs'] = round(time.time() - t0, 2)
        row.update({
            'ok': True,
            'pred_discipline': canon(out.get('discipline', '')),
            'pred_domains': sorted({canon(x) for x in (out.get('domains') or [])}),
            'n_fields': sum(1 for k in ('application', 'failure_mode', 'elaboration',
                                        'keywords', 'discipline', 'domains', 'depth')
                            if out.get(k)),
            'depth': out.get('depth'),
        })
        row.update(score_row(row, gold))
    except Exception as exc:  # noqa: BLE001 — fail-closed, record and continue
        row.update({'ok': False, 'err': f'{type(exc).__name__}: {exc}',
                    'secs': round(time.time() - t0, 2)})
    return row


def report(models: list[str], gold: dict[str, dict]) -> None:
    """Print the production-path scoreboard, scoring MAPPED labels (BUG-260 corrected).

    Scores are recomputed from the stored raw predictions, so rows measured before the fix are
    corrected in place without re-running any model.
    """
    if not CKPT.exists():
        print('no checkpoint yet')
        return
    rows = [json.loads(l) for l in CKPT.read_text().splitlines() if l.strip()]
    print()
    print('PRODUCTION PATH — merged_cribs_classify() vs gold_4axis')
    print('  disc/domF1 = after the production raw->canonical mapping (D2138)  '
          '| raw_* = unmapped, for audit')
    print(f"{'model':40s} {'n':>4s} {'disc':>6s} {'domF1':>6s} {'raw_disc':>9s} {'raw_domF1':>10s} "
          f"{'emerg%':>7s} {'valid':>6s} {'med_s':>6s}")
    for m in models:
        rs = [r for r in rows if r['model'] == m]
        if not rs:
            continue
        ok = [r for r in rs if r.get('ok')]
        scored = [dict(r, **score_row(r, gold[r['fb_id']])) for r in ok if r['fb_id'] in gold]
        disc = statistics.mean(r['disc_exact'] for r in scored) if scored else 0.0
        domf = statistics.mean(r['dom_f1'] for r in scored) if scored else 0.0
        rdisc = statistics.mean(r['raw_disc_exact'] for r in scored) if scored else 0.0
        rdomf = statistics.mean(r['raw_dom_f1'] for r in scored) if scored else 0.0
        emg = statistics.mean(r['domains_emerging'] for r in scored) if scored else 0.0
        med = statistics.median(r['secs'] for r in rs) if rs else 0.0
        print(f"{m[:38]:40s} {len(rs):4d} {disc:6.3f} {domf:6.3f} {rdisc:9.3f} {rdomf:10.3f} "
              f"{emg:6.1%} {len(ok)/len(rs):6.3f} {med:6.1f}")


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', nargs='+', required=True)
    ap.add_argument('--limit', type=int, default=100, help='rows per model (0 = all 251)')
    ap.add_argument('--seed', type=int, default=20260915)
    args = ap.parse_args()

    gold = load_gold()
    retired = [m for m in args.models if m in RETIRED_MODELS]
    if retired:
        print(f"SKIP retired model(s): {', '.join(retired)} — see RETIRED_MODELS (D-2637/[[G3]])")
        args.models = [m for m in args.models if m not in RETIRED_MODELS]
        if not args.models:
            return 0
    ids = sorted(gold)
    if args.limit and args.limit < len(ids):
        import random
        random.Random(args.seed).shuffle(ids)
        ids = sorted(ids[:args.limit])
    fbs = load_fbs(ids)
    print(f'gold rows={len(gold)}  sampled={len(ids)}  fbs_from_db={len(fbs)}', flush=True)

    done = done_keys()
    for model in args.models:
        todo = [i for i in ids if i in fbs and (model, i) not in done]
        print(f'== {model}: {len(todo)} to do ({len(ids)-len(todo)} cached)', flush=True)
        for n, fb_id in enumerate(todo, 1):
            row = measure(model, fb_id, fbs[fb_id], gold[fb_id])
            append(row)
            if n % 10 == 0 or not row.get('ok'):
                tag = 'ok' if row.get('ok') else 'ERR ' + str(row.get('err'))[:60]
                print(f'   {n}/{len(todo)} disc={row.get("disc_exact")} domF1={row.get("dom_f1")} {row["secs"]}s {tag}', flush=True)
        report(args.models, gold)
    return 0


if __name__ == '__main__':
    sys.exit(main())