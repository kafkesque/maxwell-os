# HANDOFF — 2026-10-26 — the Hugging Face token, the sovereignty rail that already existed, and the gate that was silent

**Read this before the new session.** It carries the whole state: what was wrong, what was fixed, what only the
owner can do, what is still open, and the exact commands to resume. Nothing here is reconstructed from memory —
every claim carries the reading that produced it (D-3109).

Repo: `12b539a` · working tree clean · **whole-set certification GREEN: 194 lines, 0 faults, 546.8 s** (see §7).

---

## 1. The short version

| # | Finding | State |
|---|---|---|
| 1 | **There is NO Hugging Face token field anywhere in oMLX.** Measured from the app's shipped i18n bundle: `Settings → Hugging Face` holds exactly ONE field — **"Mirror Endpoint"** (`settings.huggingface.endpoint`) — and the only two token inputs in the whole product are the per-download **"HF Token (optional)"** and the uploader's write token. Two instructions sent you to a door that does not exist. | **BUG-1024 + BUG-1027** — CORRECTED 11:37 (§2.2, §3) |
| 2 | The token you pasted into **Mirror Endpoint** was not stored as a credential — it was copied into `HF_ENDPOINT`, which **502'd every Hugging Face call in the product** from 10:46:45 until 11:37. Cleared through the app's own API; browsing green again (200, 38 models). | **BUG-1027 FIXED**, two-sided receipt |
| 2b | The mislabelled sub-key is **already deleted** (`auth.sub_keys` = 0), so the read-only token is no longer a working local inference bearer. | **CLOSED** by you, verified at 11:37 |
| 3 | Three files held the **revoked** token, and a revoked token is refused even for a PUBLIC repo. | **CLOSED** — the live token is now in both canonical homes, verified by the library |
| 4 | `just preflight` was **dying at its 7th of 13 declared lines**, so six rails never ran — including the only `check_omlx_health` line in the whole justfile. | **BUG-1025 CLOSED** |
| 5 | Closing #4 revealed **10 C12 items** (9 unchecked hardcoded values + 1 mismatch) the dead gate had been hiding. | **T-206 open**, ceiling declared |
| 6 | **T-205's premise was false**: a sovereignty rail already exists, is 0.32 s, and already catches a cloud provider. The gap was *invocation*, not absence. | **T-205 CLOSED** on the falsified premise, corrected in place |
| 7 | `gov_sync` faulted a correct entry for containing the constant name `RC_OWNER_OWED`. | **BUG-1026 open** (LOW), filed not worked around |
| 8 | **My own append to `config/decisions.yaml` bypassed `write_guard`**, so the file's bytes were attributable to nothing — the handoff attribution control and one test both went red, on one defect read twice. | **FIXED** and re-appended through `write_guard` (twice: the first attempt failed because a *relative* path makes an unusable record) |
| 9 | `write_guard.append_lines` accepts a **relative** path and journals it verbatim, producing a receipt no reader can join — while printing success. | **BUG-1026 INSTANCE 2**, fix shape declared |

---

## 2. The Hugging Face token — the complete answer

### 2.1 Your question: which key class?

**Measured, not advised.** `https://huggingface.co/api/whoami-v2` with the token you pasted:

```
user = 'neanderground'   type = 'access_token'   role = 'read'   createdAt = 2026-10-26T09:41:43Z
```

`role: read` with **no `fineGrained` block** — so what you made is a **plain read token**, which is exactly the right
class for oMLX. "Inference Presets" was never needed: **oMLX runs inference locally**; the token is used only to
*downgrade nothing and unlock gated weights*. A token that can spend money is strictly worse than one that cannot.
No expiry recorded = nothing will stop working on a future date.

### 2.2 Where the token actually lives (and where it does not)

`~/.omlx/settings.json` → `huggingface: {endpoint: '', hf_cache_enabled: true}`. **No token field exists there.**
What you switched on ("huggingface local cache") is `hf_cache_enabled: true` — confirmed, and it is the correct
switch, but it is not a place to put a credential.

The app's own strings settle it:

```
Row label for the HF token input
Section heading inside the upload sheet for the HF token row
Button label that triggers HF token validation
Subtitle when a token has been validated. Placeholder is the HF username
Stored in macOS Keychain. Needs write access to your account.
Add Model from Hugging Face
```

⇒ **those strings belong to the UPLOAD sheet** (`models.uploader.hf_token_label` — "HuggingFace Token", placeholder
*"Enter HF write token (hf_…)"*, validated by `POST /admin/api/upload/validate-token`). It is a **write** token for
uploading models TO the Hub, **not** a download token, and it is **not persisted**. The download path has no stored
token at all.

**CORRECTED 2026-10-26 11:37 — the exhaustive, measured list of every token-bearing field in oMLX v0.7.3.dev2**, read
from the app's own i18n bundle and source, not from a UI description:

```
settings.huggingface.endpoint        "Mirror Endpoint"     <- the ONLY field Settings -> Hugging Face has. A URL.
settings.huggingface.endpoint_hint   "Custom endpoint URL for HuggingFace API (e.g. https://hf-mirror.com)"
settings.huggingface.endpoint_clear_hint "To use the default endpoint, clear the field and save."
models.downloader.hf_token          "HF Token (optional)"  <- per-download ONLY; DownloadTask.token is
                                       "Never in to_dict()"; passed as token=hf_token or None
models.uploader.hf_token_label       "HuggingFace Token"   <- WRITE token for uploading, validate-only
```

⇒ **there is nowhere in oMLX to store an HF token, and nothing needs storing.** With no per-request token the app calls
`snapshot_download(token=None)`, so `huggingface_hub` uses `HF_TOKEN` or the `hf auth login` token file — the home that
already holds your live token. oMLX's own client proves it accepts it: `hf_token_invalid=False`, a flag
`_list_models_stale_token_fallback` sets **only** on a 401.

### 2.3 What "Sub Keys" really is

`Settings → Security → Sub Keys`, subtitle: *"Issue scoped keys for individual apps or users. Sub keys cannot grant
admin access."* These are **additional local API keys for the inference server**. Measured:

```
/v1/models/status   no header                    -> HTTP 401
                    Bearer <16-char auth.api_key> -> HTTP 200
                    Bearer <37-char HF sub-key>   -> HTTP 200   <-- your HF token, working as a door key
```

So it did not help downloads and it did acquire a power. Delete it (§3 step 3).

### 2.4 The dead-token hazard, now closed on the Python side

| home | sha256[:12] | mtime | `whoami-v2` |
|---|---|---|---|
| `~/Library/Application Support/oMLX/config.json#hf_token` | `a78e54f87d15` | 2026-07-22 18:00 | — (app-owned) |
| `~/.cache/huggingface/token` | `a78e54f87d15` → **`dbc9178ddc7b`** | now | **401 → 200** |
| `~/.huggingface/token` | `a78e54f87d15` → **`dbc9178ddc7b`** | now | 401 → 200 |
| `~/.omlx/settings.json#auth.sub_keys[0]` | `dbc9178ddc7b` | 2026-10-26 09:42 | 200 (wrong store) |

**A dead token is worse than no token**: `huggingface_hub` *sends* whatever token it has, so a revoked one is
refused with 401 **even for a public model**, while an absent one degrades politely to anonymous. Nothing had broken
yet only because both models the pipeline needs were already cached — DeBERTa-v3-large NLI `3.9G`, bge-m3 `4.3G`.

**Done and verified:** the live token was written to both canonical homes at mode `600` (tmp → fsync → replace,
fingerprints only, never the secret), and confirmed by the library itself — `huggingface_hub 1.9.0`
`whoami() → neanderground`.

---

## 3. Your manual steps — numbered, with the branch when it differs

> **Step 1 — DO NOTHING. There is no token field to paste into.** (Corrected 11:37: the previous version of this step
> described a sheet that does not exist. It cost you a wrong paste into **Mirror Endpoint**, which broke every HF call
> in oMLX — BUG-1027. That is on the instruction, not on you.) The token belongs in exactly one place, and it is
> already there: `~/.cache/huggingface/token` at mode 600, verified `whoami → neanderground`.
> *Verify in one line:*
> `python3 -c "import huggingface_hub as h;print(h.HfApi().whoami()['name'])"` → *Expected:* `neanderground`.

> **Step 2 — CHECK the one HF field in oMLX is EMPTY** (it is now, verified 11:37, and this is the field that broke it).
> oMLX → **Settings → Hugging Face → Mirror Endpoint** → it must be **empty**; `Save`. The app's own hint:
> *"To use the default endpoint, clear the field and save."*
> *Verify:* `python3 -c "import json,pathlib;d=json.loads((pathlib.Path.home()/'.omlx/settings.json').read_text());print(repr(d['huggingface']['endpoint']))"`
> *Expected:* `''`. *If it shows `'hf_…'`:* a token has been pasted there again — clear it. A non-URL value sets
> `HF_ENDPOINT` in the server's environment and every Hugging Face request then fails **502** with
> *"Request URL is missing an 'http://' or 'https://' protocol"*, while local-only pages keep answering 200 and hide it.

> **Step 3 — delete the mislabelled sub-key.** oMLX → **Settings → Security → Sub Keys** → the row named
> **`hugging face`** → delete.
> *Verify:* `python3 -c "import json,pathlib;d=json.loads((pathlib.Path.home()/'.omlx/settings.json').read_text());print('sub_keys:',len(d['auth']['sub_keys']))"`
> *Expected:* `sub_keys: 0`. *If it still says `1`:* the app had the file open — re-open Settings and delete again.

> **Step 4 — a gated model, only if you ever download one.** Then use the downloader's own per-download field:
> **Models → Model Downloader → "Download from HuggingFace" → `HF Token` (optional)** — paste there for THAT download
> only; it is never stored. Public downloads need nothing: your two pipeline models are already cached and no gated
> download is pending.

> **Step 5 — the provider (this is "Task C").** go to go and the *new* session's check, not the dropdown.
> The config on disk already reads `active_provider: maxwell_omlx` (mtime 09:34:57, nothing has re-flipped it;
> `providers.huggingface.enabled: false`, `model: ''`, `HF_HOST` absent). `custom_deepseek` is `enabled: true`
> but **not active** — it is the "deepseek" you see. Since D-295 and the whole harness design already require
> `maxwell_omlx`, and `custom_deepseek` is banned for delegation anyway (DELEGATE-001), the clean state is:
> **Settings → Providers → select `maxwell_omlx`**, and switch `custom_deepseek` **off** so a session cannot be born
> on it by accident. Then start the new session and verify it by *record*, not by eye:
>
> ```
> sqlite3 "file:$HOME/.local/share/goose/sessions/sessions.db?mode=ro" \
>   "select id, provider_name from sessions order by created_at desc limit 1;"
> ```
> *Expected:* a `2026-10-26_x` row whose `provider_name` is `maxwell_omlx`.
> *If it reads `custom_deepseek` or `huggingface`:* the birth picked the wrong provider — switch again in Settings and
> start **another** new session; a session keeps the provider it was born with.

> **Step 6 — after any settings change, cheap proof (0.32 s).**
> ```
> python3 scripts/check_harness_homes.py; echo "rc=$?"
> ```
> *Expected:* `5 declared fact(s) | bound 5 | conflicting 0` and `rc=0`, with
> `BOUND active_provider (harness_config#active_provider)` as the first line.
> *If it says `CONFLICT`:* something rewrote `~/.config/goose/config.yaml` — the line names what the file says and
> which decision owns it. Fix the file, do not argue with the rail.

---

## 4. What was actually wrong with the two instructions (owned)

Both told you to paste into an oMLX **"Settings → Hugging Face"** section. It does not exist. The rule that was
broken is D-3100's strongest clause, now made explicit as **D-3153 clause (2)**: *an instruction must name a surface
that RESOLVES, and the resolver must be the application's own strings or the configuration's own keys — never a
plausible-looking menu.* A plausible menu is a declaration with no referent (D-3034 applied to prose).

---

## 5. The rail that already existed — and why T-205 was wrong

`T-205` was registered on this premise: *"Not one of the 194 declaring lines reads that file."* **False.**

* `config/agent_context.yaml#home_facts[0]` declares `active_provider` and compares it to
  `config/engine.yaml#harnesses.goose_provider_id` **through a pointer** (C12 — no literal, no value with two homes),
  `decided_by: [D-295, D-3023, D-3044]`, `row: T-174`.
* `scripts/check_harness_homes.py` reads it: **0.32 s**, **7/7 known-answer controls**, and control #2 is exactly
  BUG-1022's shape — a home that says `someone_else` reads **CONFLICT**, rc 2, and **names** the decision that owns it.
* `justfile:81` runs it inside the ladder.

**So why did the 09:29 flip pass unseen?** Invocation, not absence: the whole-set scan **ended 09:20:12Z** and the
paste landed at **09:29** — nine minutes later — and a **resumed** session never re-runs the boot sequence.

**What changed:** the reading is now the **second declared line of `just preflight`**, *ahead* of the fragile gate, so
no later abort can shadow it. Measured working: `harness homes: 5 bound | 0 conflicting` prints before anything can
fail. Building the rail T-205 described would have created a **second rail reading the same key** — drift wearing the
costume of diligence — so the premise is retired **in place** with its reason (D-3038), never deleted.

---

## 6. The gate that was silent (BUG-1025) — the most transferable finding

`pipeline/dspy_trainer.py` guarded its import with `print(...) + sys.exit(1)`.
**`SystemExit` derives from `BaseException`**, so it escaped the `except Exception` that
`pipeline/config_audit.py#get_code_value` uses to make an unimportable module *harmless* — and killed the **audit**.
`just preflight` then died at its **7th of 13** declared lines; six readings never ran:

taxonomy · **`check_omlx_health`** (its **only** declaring line in the entire justfile) · `recompute_decision_summary`
· `check_config_duplicate_keys` · `subagent_fanout doctor` · `research_run --check`.

> *A gate that cannot run does not report "unknown". It reports SILENCE — and silence is indistinguishable from clean.*

Fixed two-sided: the CLI keeps its one clean sentence; an importer gets a catchable `ImportError`. Then it **spoke**,
and had ten things to say that had never been reportable: `container_integrity.py` ×6, `model_store_census.py` ×2,
`stage0_convert.py` ×1, plus `s2.dspy_max_tokens` (4096) whose default is unreadable while dspy-ai is absent.
Registered as **T-206** against a shrink-only ceiling — **not** folded into `ACKNOWLEDGED_HARDCODED`, because an
acknowledgement set that absorbs a finding is a register that can never shrink.

---

## 7. State at handover

```
head                 12b539a   working tree clean
certification        GREEN — schema 2, state finished, recipe health, 194 lines, worst_rc 0, 546.8 s
                     started 2026-10-26T10:16:21Z -> measured 10:25:28Z
                     head_at_start == head_at_end == 12b539a · all four worktree readings EMPTY · faults []
                     fingerprint 18d1b2d71f73dc70 · log temp/ladder_final.log
                     -> re-read with: python3 scripts/run_ladder.py --receipt-check
                     A FIRST run (b9cd108, 551.3 s) was RED on 2 faults, both §1 row 8; that receipt is superseded.
census               1279 decisions / 790 bugs (247 open, 543 closed, DIVERGENT 0) / 107 tasks
                     (60 open, 46 done, 1 rule; movers pipeline 88 / owner 19)
gov_sync             4 faces equal their re-derivation
rails                divergence 0 · bug_status ok · decision_summary ok · buglog coverage ok (1123 blocks)
                     route graph ok · harness homes 5 bound / 0 conflicting
engine               127.0.0.1:11435, auth required by design (keyless 401 is CORRECT — BUG-1023)
```

**Named limits, stated rather than hidden**
* `just preflight` is still **rc=1** — now for a real, newly visible reason (the 10 items in T-206). The six rails
  behind that line are unreachable *in preflight*; they do run in the whole-set ladder.
* `~/Library/Application Support/oMLX/config.json#hf_token` still holds the **revoked** token. It is app-owned and the
  app was running, so it was not hand-edited. If step 1 succeeds, the app rewrites/overrides it; if step 1 is skipped,
  it stays as inert legacy until something asks oMLX to fetch gated weights.
* **BUG-789** already registers "the local model server's app config carries a Hugging Face token in plaintext"
  (OPEN). BUG-1024 is the *placement and liveness* defect on top of it, not a duplicate — cross-reference them.
* The green receipt certifies **`12b539a`**. If the head has moved since (documentation-only commits included), the
  receipt still names the head it MEASURED — that is T-204's whole point: believe the receipt's `head_at_*`, never this
  prose. Check with `python3 scripts/run_ladder.py --receipt-check`.
* `just preflight` remains rc=1 (T-206's ten items) while the whole-set ladder is green: they are different doors, and
  the certification does not cover the cheap one.
* `gov_sync --apply` **re-wraps** `config/task_register.yaml`, so exact-text edits to it must be re-read after every
  sync (measured this turn: one edit failed on stale wrapping).

---

## 8. Next critical steps, in consequential order

1. **T-206 — the ten C12 items** (SHOULD, open, pipeline). Highest leverage this second: `just preflight` is the
   door you walk through before work, it is 5.5 s now, and it is red. Count them against a shrink-only ceiling first;
   then classify: *meaning* values → YAML, *exit-code vocabulary* → stays in code with its reason, *binary format
   offsets* → declared as a format spec. Keep the dangling `s2.dspy_max_tokens` leg conditional on an interpreter that
   can import the module.
2. **BUG-1020 — restore the delegation path** (MED, open). The harness has now failed 4/4 across two sessions while
   *direct* temperature-0.0 calls answered the same class in 8.18 s, 44.02 s and 27.9 s. This is the standing
   "delegate to the right local model" rule's own blocker; nothing else on this list is worth more once it is fixed.
3. **BUG-1015 — `just audit` cannot fail its own lint gate** (`| tail -5` makes the exit status tail's; `scripts/` is
   linted nowhere). Same family as BUG-1025: *the instrument reports success because its status was replaced.*
4. **BUG-1026 — the substring-vs-token fault** in `gov_sync` (LOW, open). One boundary test + a two-sided control;
   until then the register must write around variable names.
5. **T-101 / T-116 — the retrieval golden set is saturated** (recall@10 = 1.000, self-referential top-5 pool, D-2991).
   Mission-critical and the only item that asks whether the *output* is good; T-116 is the growth instrument.
6. **T-202** — `gpt-oss-20b` enum falsifier before any path sends a `tools` payload.
7. **BUG-1021** — one declared record home, two recipes; **T-204** — the verdict should name the head it measured in
   both directions; **T-203** — a prose table may not restate a hub count.
8. **Receipt durability** — the green verdict lives in gitignored `temp/` with `max_age_hours: 72`, so it expires and
   is machine-local.
9. Batched with the next real change to `scripts/lib/yaml_guard.py`: the `source_digest()` docstring NAMED LIMIT
   (it claims to digest "every input to a per-file verdict" but would not cover a helper moved out of the module).
   Free then, one 500 s rescan otherwise.

---

## 9. How to resume in the new session

```
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
python3 scripts/check_harness_homes.py; echo rc=$?      # 0.32 s: is the machine still sovereign?
python3 scripts/run_ladder.py --receipt-check           # did the last whole-set run certify THIS tree?
python3 scripts/bug_status.py | head -1                 # 247 open / 543 closed / 0 divergent
git log --oneline -1 && git status --porcelain | wc -l  # b9cd108, 0 dirty
```

Then say which of §8 you want, and the session picks up from the receipt rather than from this prose.
