# F-11 — LLM SECOND CODER (package, ready to send)

**Why this exists.** F-11 is the gate everything else waits behind. The ruler (150 rows built; 122 fully answered)
(`governance/RULER_BLIND_SHEET_20260917.csv`, stratum A 100 + stratum B 50) was answered by **one** human
coder (`reviewer=human`). With one coder the labels are **attested**, not independent: a win measured against
them cannot license adoption (D-317), cannot unfreeze the eval floors, and cannot open laya Phase B. A second
coder is the missing piece; there is no second human, so this package gets a second coder from a **different
model family**.

**What it buys.** Inter-coder agreement (Cohen's kappa per axis) between the human and the second coder → the
first measurement of the ruler's *reliability* (as opposed to accuracy), plus a list of the rows and classes
where the two coders disagree — which is where the taxonomy, not the model, is usually the problem.

**What it does NOT buy.** The second coder is an LLM. Its label set is a THIRD attested set, tier
**`llm-attested`**. It never becomes `human-blind`; it cannot move the D-300 adoption bar; it is advisory.
Sending the rows off-machine is the C22 hybrid-sovereignty opt-in (step 0).

---

## Step 0 — the opt-in (one line, yours)

The rows are book-derived text. Sending them to an API model leaves this machine. Either:

* **opt in** — set `coder.sovereign_opt_in: true` in `config/f11_llm_coder.yaml`, or
* **stay local** — use a local model **not used in the pipeline** (so its blind spots are not the generator's):
  a local Qwen/DeepSeek/LLaMA instruct model served by Ollama would work, *except* the pipeline generator is
  Qwen — prefer a local **Mistral/Mixtral or LLaMA-family** model, and say which one you used.

Preferred API choice, in order (family-diversity is the whole point):

| rank | model | why | caveat |
|---|---|---|---|
| 1 | **Claude (Opus/Sonnet 4.x)** | different family from the generator (Qwen3-Coder) and the classifier (gpt-oss-20b) → disagreement is informative | API = C22 opt-in |
| 2 | **DeepSeek (V3.x / R1)** | good independent family, cheap | API = C22 opt-in |
| 3 | local Mistral/Mixtral | keeps sovereignty | weaker on 62-slot discipline menus |
| ✗ | anything Qwen | same family as the generator → agreement inflated | — |
| ✗ | anything GPT-OSS | same lineage as the S4 classifier → agreement inflated | — |

## Step 1 — materialise the blind rows (one command, no labels in them)

```bash
python3 scripts/f11_llm_coder.py --export
```

Writes `ROWS_BLIND.csv` (identity/text columns only — the 9 answer columns are dropped, so the human's
answers cannot leak) and `MANIFEST.json` (sha256 of the source sheet, the blind export, the menus, this
package). The export **refuses** if any source row is missing a human answer (an incomplete ruler is not a
reliability measurement) or if any answer column survives the strip.

## Step 2 — fill the coder identity, then send

Edit `config/f11_llm_coder.yaml` → `coder.model`, `coder.family`, `coder.sovereign_opt_in: true`,
`coder.prompt_sha256` = sha256 of `PROMPT.md` as actually sent (the export prints it).
One model version, one prompt, **temperature 0.0**, no retries (R7 + D-317 one-shot rule).

Open a **fresh** conversation (no prior context, no repo access, no tools). Attach
`RULER_MENUS_20260917.md` + `ROWS_BLIND.csv`, paste `PROMPT.md`, and save the reply exactly as
`governance/F11_LLM_CODER_20260921/LLM_LABELS_20260921.jsonl` (one JSON line per row in ROWS_BLIND.csv - see MANIFEST.json n_rows, no prose).
Do **not** show the model the human's answers, the key, or this README.

## Step 3 — score the agreement

```bash
python3 scripts/f11_llm_coder.py --score governance/F11_LLM_CODER_20260921/LLM_LABELS_20260921.jsonl
```

Refuses on any row count other than MANIFEST.json n_rows, and on duplicates or stray prose. Writes `governance/f11_llm_coder_20260921.{json,md}` with, per
axis: agreement %, Cohen's kappa, the confusion matrix, each coder's distinct-label counts, and every label a
coder used that the other never used (a soft out-of-vocabulary signal). It records provenance
`llm-attested` and states, in the artifact itself, that it cannot unfreeze the floors.

## Step 4 — read it as a triangle, not a verdict

* kappa(human, LLM) **high** on an axis → the ruler is reliable on that axis; the axis can carry a floor.
* kappa **low** with disagreements concentrated in one class pair → the TAXONOMY is ambiguous there, not the
  model. That is a boundary/discriminator decision, and the config to change is
  `config/boundary_discriminators.yaml` (D-325), not the model.
* If the coder's labels drift out of the closed menu, that is the **menu-compliance** defect already measured
  on the S4 classifier (D-327): it must be reported as an emission error, not as a wrong label.
