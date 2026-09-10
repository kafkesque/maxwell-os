#!/usr/bin/env python3
"""Selective-prediction curve (D2610): depth encoder confidence vs coverage.

Reports the accuracy the depth encoder buys if it is allowed to ABSTAIN on its
low-confidence rows (the serving-time analogue of the labeler's abstain policy).
This is the gate replacement for the unreachable 0.85 macro-F1 target.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'scripts'))
import eval_depth_classifier as edc
from transformers import AutoTokenizer
EVAL=Path(os.environ.get('DEPTH_V2_TEST', ROOT/'governance'/'depth_v2_test.yaml'))
CKPTS=[('v2 (D2610 reliable-pair labels)', ROOT/'knowledge pipeline'/'classifier_depth_core'),
       ('v1 (D2577 3-voter labels)', ROOT/'knowledge pipeline'/'classifier_depth_cleanC')]
COVERAGES=(1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.2)
def main() -> int:
    examples=edc.load_depth_examples(str(EVAL))
    out={}
    for name,ck in CKPTS:
        maps=json.loads((ck/'label_maps.json').read_text())
        dmap={k:int(v) for k,v in maps['depth_to_idx'].items()}; inv={v:k for k,v in dmap.items()}
        tok=AutoTokenizer.from_pretrained(edc.BASE_MODEL_NAME)
        model=edc.DepthClassifier(backbone=edc.AutoModel.from_pretrained(edc.BASE_MODEL_NAME))
        model.load_state_dict(torch.load(str(ck/'model_state.pt'), map_location='cpu'))
        dev=edc._device(); model.to(dev); model.eval()
        ds=edc.DepthDataset(examples,tok,dmap)
        rows=[]
        with torch.no_grad():
            for i in range(len(ds)):
                it=ds[i]
                logits=model(it['input_ids'].unsqueeze(0).to(dev), it['attention_mask'].unsqueeze(0).to(dev))
                p=torch.softmax(logits,dim=-1)[0]; conf=float(p.max()); pred=inv[int(p.argmax())]
                rows.append({'conf':conf,'correct':pred==examples[i].get('depth',''),'pred':pred,'gold':examples[i].get('depth','')})
        rows.sort(key=lambda r:-r['conf'])
        curve=[]
        for cov in COVERAGES:
            k=max(1,int(round(cov*len(rows))))
            sel=rows[:k]
            curve.append({'coverage':round(k/len(rows),3),'n':k,'accuracy':round(sum(r['correct'] for r in sel)/k,4)})
        out[name]={'n':len(rows),'accuracy_all':round(sum(r['correct'] for r in rows)/len(rows),4),'curve':curve}
        print(name)
        for c in curve:
            print(f"   coverage {c['coverage']:.0%} (n={c['n']:3d}) accuracy {c['accuracy']:.3f}")
    dest=ROOT/'governance'/'depth_selective_prediction.json'
    tmp=dest.with_suffix('.json.tmp'); tmp.write_text(json.dumps(out,indent=2)); os.replace(tmp,dest)
    print('wrote',dest)
    return 0
if __name__=='__main__': raise SystemExit(main())