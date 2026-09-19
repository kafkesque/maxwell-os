#!/bin/bash
# next_critical_queue.sh — the three fixes that stand between us and a defensible freeze.
#
# 1. VERIFY the S2 cross-family relabel. The stage probe failed 12/12 with "content missing from
#    message (reasoning-...)" — gpt-oss returned reasoning_content and no content. If that is the
#    production behaviour, the R5 control for FORM drift has been producing nothing. One call with
#    and one without the reasoning-off prefix decides it.
# 2. RE-RUN planning on the 21 generated items (plangen-*), whose answers are computed by Dijkstra /
#    brute force / simulation. The hand-written 17 were invalid (13 failed by every model, my gold
#    answers were wrong).
# 3. CHECK S4_5: the probe recorded 12/12 'declarative', which is suspicious. Compare against the
#    stored procedural_skill column before believing it.
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/next_critical.log
say() { echo "[next] $*  $(date '+%F %T')" | tee -a "$LOG"; }

# serialised: nothing else may touch oMLX (BUG-255)
while pgrep -f 'model_eval_suite.py|pipe_s4_classify_gold.py|retrieval_benchmark.py|reclaim_optiq.sh' > /dev/null 2>&1; do
  sleep 30
done

say 'step1 — S2 relabel: does gpt-oss return content at all?'
python3 - <<'PY' >> "$LOG" 2>&1
import json
import time

import requests

from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import VERIFY_REASONING_OFF_PREFIX
from pipeline.stage2_relabel_extraction_type import SYSTEM_PROMPT, _build_prompt, _extract_label

URL = "http://127.0.0.1:11435/v1/chat/completions"
KEY = "sk-maxwell-local"


def warmup(model: str, tries: int = 4) -> bool:
    """Load and warm the model before testing: a cold reasoning model returns no content."""
    for i in range(tries):
        try:
            r = requests.post(URL, headers={"Authorization": "Bearer " + KEY},
                              json={"model": model, "messages": [{"role": "user", "content":
                                    'Reply with JSON only: {"ok":true}'}],
                                    "temperature": 0.0, "max_tokens": 40}, timeout=600)
            if r.status_code == 200:
                msg = r.json()["choices"][0]["message"]
                txt = (msg.get("content") or msg.get("reasoning_content") or "")
                if txt.strip():
                    print(f"  warmup {i + 1}: model is answering ({len(txt)} chars)")
                    return True
                print(f"  warmup {i + 1}: 200 but empty content — waiting 45s")
        except Exception as exc:
            print(f"  warmup {i + 1}: {type(exc).__name__} — waiting 45s")
        time.sleep(45)
    return False


print("S2 RELABEL — reasoning-off prefix check (gpt-oss-20b-MXFP4-Q8)")
try:
    warmup("gpt-oss-20b-MXFP4-Q8")
except Exception as exc:
    print("  warmup failed hard:", type(exc).__name__, str(exc)[:120])

rec = {"name": "Loss Aversion in Pricing",
       "definition": ("Buyers weight a possible loss more heavily than an equivalent gain, so a "
                      "discount framed as avoiding a loss converts better than the same discount "
                      "framed as a gain of equal size."),
       "mechanism": "Losses loom larger than gains, shifting the reference point.",
       "boundary": "Applies to consumer pricing, not to expert procurement.",
       "consequence": "Framing effects change conversion without changing the offer.",
       "extraction_type": "causal_mechanism", "evidence_passages": ["passage one", "passage two"]}
prompt = _build_prompt(rec)

print("S2 RELABEL — reasoning-off prefix check (gpt-oss-20b-MXFP4-Q8)")
for label, system in (("bare SYSTEM_PROMPT", SYSTEM_PROMPT),
                      ("SYSTEM_PROMPT + reasoning-off prefix",
                       VERIFY_REASONING_OFF_PREFIX + "\n\n" + SYSTEM_PROMPT)):
    try:
        res = call_omlx_json(prompt=prompt, model="gpt-oss-20b-MXFP4-Q8", system=system, max_tokens=64)
        lab = _extract_label(res)
        print(f"  {label}: returned {res!r}"[:200])
        print(f"    extracted label: {lab!r}  -> {'USABLE' if lab else 'EMPTY = relabel silently does nothing'}")
    except Exception as exc:
        print(f"  {label}: FAILED -> {type(exc).__name__}: {str(exc)[:160]}")
PY

say 'step2 — S4_5 truth check from the DB (is 12/12 declarative real?)'
python3 - <<'PY' >> "$LOG" 2>&1
import json, sqlite3, collections
ck = [json.loads(l) for l in open('governance/pipe_stage_probe_checkpoint.jsonl', encoding='utf-8')
      if l.strip() and json.loads(l).get('stage') == 's4_5_skill']
ids = [r['id'] for r in ck]
db = sqlite3.connect('knowledge pipeline/maxwell.db')
cols = {r[1] for r in db.execute("pragma table_info(fbs)")}
if 'procedural_skill' not in cols:
    print("  no procedural_skill column — S4_5 has never written production values")
else:
    q = ','.join('?' * len(ids))
    rows = db.execute(f"select fb_id, procedural_skill from fbs where fb_id in ({q})", ids).fetchall()
    filled = [(i, s) for i, s in rows if (s or '').strip()]
    print(f"  probed {len(ids)} FBs | stored procedural_skill non-empty in {len(filled)}/{len(rows)}")
    print(f"  model said 'declarative' for {sum(1 for r in ck if r.get('pred') == '(declarative)')}/{len(ck)}")
    for i, s in filled[:5]:
        print(f"    {i[:12]} stored={s!r}  model={(next((r['pred'] for r in ck if r['id']==i), '?'))!r}")
PY

say 'step3 — re-run planning on the 21 COMPUTED items (7 models)'
python3 tools/model_eval_suite.py \
  --models Ornith-1.5-35B-A3B-REAP-19B Qwen3.8-27B-MLX-4bit Qwen3-Coder-30B-A3B-Instruct-MLX-4bit \
           gemma-4-E4B-it-MLX-4bit Ornith-1.5-9B-MLX-8bit Phi-4-mini-instruct-8bit gpt-oss-20b-MXFP4-Q8 \
  --suites planning >> governance/model_eval_roles.log 2>&1
say 'step3 done'

say 'step4 — refresh report + audit'
python3 tools/model_eval_report.py --md governance/model_eval_report.md >> "$LOG" 2>&1
python3 scripts/audit_final_chain.py >> "$LOG" 2>&1
say 'ALL DONE — planning is now computable, relabel verdict logged'
