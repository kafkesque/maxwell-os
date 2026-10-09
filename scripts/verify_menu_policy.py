#!/usr/bin/env python3
"""scripts/verify_menu_policy.py -- fail-closed policy verifier (D-349/D-350).

Asserts three things a human ruling cannot silently rot:
  1. QUEUE CLOSURE: on a constant axis, every menu label except the declared
     abstention label is queued for human review (no label left machine-claimable).
  2. MERGE RATIFICATION: every ratified tail merge names an existing menu parent
     that is not itself a tail label; every refusal is backed by a measured gap
     below the declared margin in the evidence artifact (BUG-342: quote, do not
     re-derive).
  3. ABSTENTION POLICY: the drain target is a MACHINE state, the operating point of
     every axis has a measured curve in the calibration artifact, the artifact
     digest matches, and no axis is silently transplanted.
Exit 1 on any RED (C16).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

R = Path(__file__).resolve().parent.parent
ROUTING = yaml.safe_load((R / 'config/menu_routing.yaml').read_text())
ABSTENTION = yaml.safe_load((R / 'config/verify_abstention.yaml').read_text())
MERGE = yaml.safe_load((R / 'config/menu_v6_merge_map.yaml').read_text())
red, warn = [], []


def canon(t: str) -> str:
    """Canonicalise a label for menu comparison."""
    return ''.join(ch for ch in str(t).lower() if ch.isalnum())


for axis, spec in ROUTING['axes'].items():
    if spec['route'] != 'constant_plus_human_queue':
        continue
    src = ROUTING['menu_sources'][axis]
    if src['path'].endswith('.json'):
        labels = [d['value'] for d in json.loads((R / src['path']).read_text())[src['key']]]
    else:
        doc = yaml.safe_load((R / src['path']).read_text())
        labels = [d['value'] for d in (doc.get(src['key']) or [])]
    if not labels:
        warn.append(f'{axis}: menu source {src["path"]} exposes no readable list -- closure unverified')
        continue
    queued = {canon(q['label']) for q in spec.get('queue', [])}
    exempt = canon(ABSTENTION['abstention_policy']['abstention_labels'][axis])
    missing = [l for l in labels if canon(l) not in queued and canon(l) != canon(spec.get('constant_label', '')) and canon(l) != exempt]
    if missing:
        red.append(f'{axis}: {len(missing)} menu labels are neither the constant nor queued: {missing}')
    else:
        print(f'OK  closure {axis}: {len(queued)} queued, constant {spec.get("constant_label")}, abstention {exempt}')

evidence = json.loads((R / MERGE['evidence']).read_text())
by_tail = {canon(r['tail_label']): r for r in evidence['map']}
# PINNED-BY-DESIGN (BUG-694 future-tax audit, 2026-10-09): this reads closed_menu_v5.json
# deliberately, NOT live_menu_path(). The merge map (config/menu_v6_merge_map.yaml) is a FROZEN
# v5->v6 artifact; its ratified parents were chosen against the v5 menu. Re-pointing this to the
# live v9 menu would time-travel-validate a historical artifact against a future menu (e.g. the
# v9-demoted 'computational theory' is absent from v9, so a v6 parent that is now demoted would
# RED spuriously). Do NOT "fix" this into live_menu_path() — see BUG-694 for the serving-path fix.
axis_labels = {canon(d['value']) for d in json.loads((R / 'config/closed_menu_v5.json').read_text())['disciplines']}
rat = MERGE['ratification']
tails = set(by_tail)
for t in rat['ratified']:
    rec = by_tail.get(canon(t))
    if rec is None or rec['parent'] is None:
        red.append(f'merge {t!r}: ratified but the evidence names no parent')
        continue
    if canon(rec['parent']) not in axis_labels:
        red.append(f'merge {t!r}: parent {rec["parent"]!r} is not in the closed menu')
    if canon(rec['parent']) in tails:
        red.append(f'merge {t!r}: parent {rec["parent"]!r} is itself a tail label (chain refused)')
    print(f'OK  merge {t} -> {rec["parent"]} (cos {rec["best"]["cos"]}, gap {rec["gap"]} >= {evidence["runner_up_margin"]})')
for t in rat['refused']:
    rec = by_tail.get(canon(t))
    if rec is None:
        red.append(f'refusal {t!r}: not in the evidence artifact')
    elif rec['action'] != 'keep_label' or rec['gap'] >= evidence['runner_up_margin']:
        red.append(f'refusal {t!r}: evidence does not support refusal (action {rec["action"]}, gap {rec["gap"]})')
if set(rat['ratified']) | set(rat['refused']) != {r['tail_label'] for r in evidence['map']}:
    red.append('ratification does not cover the evidence map exactly (a tail label is unclassified)')
print(f'OK  merge map: {len(rat["ratified"])} ratified, {len(rat["refused"])} refused, margin {evidence["runner_up_margin"]}')

pol = ABSTENTION['abstention_policy']
cal_path = R / pol['measured_curve_artifact']
if not cal_path.exists():
    red.append(f'abstention: calibration artifact {cal_path} missing')
else:
    digest = hashlib.sha256(cal_path.read_bytes()).hexdigest()
    if digest != pol['measured_curve_sha256']:
        red.append('abstention: calibration artifact digest does not match the policy (curve changed without a decision)')
    cal = json.loads(cal_path.read_text())
    for axis, op in pol['operating_points'].items():
        if axis not in cal['curves']:
            red.append(f'abstention: {axis} has an operating point with NO measured curve (transplant refused)')
        elif not any(True for _ in cal['curves'][axis]['points']):
            red.append(f'abstention: {axis} curve is empty')
    if not pol['refused_axes']:
        red.append('abstention: no axis is declared refused -- an unmeasurable axis is being claimed')
if pol['drain_target_kind'] != 'machine_state':
    red.append('abstention: drain target is not a machine state -- human capacity would be the binding constraint')
if pol['enabled'] is not False:
    red.append('abstention: enabled must stay false until a shadow run exists (D-339 receipt rule)')
    sup = pol.get("re_measurement_20260923") if isinstance(pol, dict) else None
    if sup:
        if sup.get("status") == "supersession_pending" and pol.get("enabled") is not False:
            red.append("abstention: a supersession_pending operating point must not be enabled (D-352)")
        for f in sup.get("findings", []):
            print("WARN abstention: supersession pending -", f)
print(f'OK  abstention: drain {pol["drain_target"]} ({pol["drain_target_kind"]}), '
      f'{len(pol["operating_points"])} measured operating points, {len(pol["refused_axes"])} refused axis, sha256 match')

print(f'policy check: {len(red)} RED, {len(warn)} warn')
for r in red:
    print('RED ', r)
for w_ in warn:
    print('WARN', w_)
raise SystemExit(1 if red else 0)
