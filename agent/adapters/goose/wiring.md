# `agent/adapters/goose/` — the DEFAULT client's binding home (D-3037 / D-3041 / T-169)

This directory is what `config/agent_surface.yaml#adapter.provider_bindings.goose.binding_home` declares, and it
holds **no value of its own**. Every name it needs is a **pointer** to the one home that owns it (C12), and the
wiring itself is the **engine's own module**, not a copy of it: `omlx launch goose` runs it. There is exactly one
copy of the integration code, and it ships with the engine.

## What this binding reads, and where each name lives

| what | the ONE home | how it resolves |
|---|---|---|
| the provider id the client must use | `config/engine.yaml#harnesses.goose_provider_id` | `pipeline/harness_env.py` reads it by pointer |
| the client's own wiring module | the engine's `integrations/` (installed with the app) | `omlx launch goose` — never vendored into this repo |
| the context knobs (window, compaction) | `config/agent_context.yaml#ratified.knobs` | read by `pipeline/harness_env.py` |
| the client's config home (outside the repo) | `config/agent_context.yaml#homes.harness_config` | declared here, **never mirrored**; T-157 owns its census |
| the measured state of the binding | `python3 pipeline/harness_contract.py` | rc 2 = UNBOUND (owner-owed, T-174) |

## Run it — the exact working form (this is the form that was WRONG twice)

```bash
# the wrapper's own contract: --exec takes the command AFTER a separator `--`
python3 pipeline/harness_env.py --exec -- /Applications/Goose.app/Contents/Resources/bin/goose run -t "Reply with exactly: PONG"
# a shell that needs the binding for everything it launches:
source scripts/bind_harness_env.sh
```

**Two form facts that cost a real attempt each (MEASURED 2026-10-16):**

1. `--exec` **without** the `--` separator still runs, but every later flag is then parsed as the wrapper's own —
   the declared usage is `--exec -- <cmd> [args]`, and the `--` is what makes the boundary explicit.
2. `goose run -t` requires its **TEXT**: the client's own error was
   `error: a value is required for '--text <TEXT>' but none was supplied`. That error is the CLIENT refusing an
   incomplete command, not the wrapper failing — which is the useful reading: the wrapper had already launched it.

## The proof that the binding is real (T-174's gate, and the reason a declaration is not enough)

A client that answers while the engine's counter stands still is **not local** (MEASURED 2026-10-15: a headless run
answered `PONG` with the engine's request counter unmoved — BUG-849). The witness is the engine's own counter, and
its home is the engine's stats file under the app's support directory (`total_requests`), **which nothing in this
repository reads yet** — so today the check is a measurement taken by hand:

```bash
python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.omlx/stats.json')))['total_requests'])"
```

Take that number, run the command above, take it again. **A rise is the only proof that the declared provider is
bound in the process that acted**; an unchanged number means the run left the machine (T-174 / BUG-849).

## Swapping this client out (the whole procedure, from `agent/adapters/CONTRACT.md`)

1. `omlx launch <client> --model <declared model>` — adoption is one command and needs no disk state of ours.
2. Add the client's row to `config/harness_policy.yaml#harness_matrix` (measured, with a verdict and a reason) and
   create `agent/adapters/<client>/wiring.md` as a pointer table like this one.
3. Re-point nothing else: the skills under `agent/skills/` are portable (the rail faults a client name in one),
   the pipeline never learns the client's name, and `config/agent_context.yaml` owns every knob.
4. Then run the rails: `just health`, `scripts/resolve_route.py --check`, `scripts/check_agent_surface.py`.
