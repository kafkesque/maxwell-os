# THE ADAPTER ROOT — what may live here, and what a client must do before it is used

D-3037 (modular core + ONE adapter surface) | T-138 (harness adoption on demand) | T-169 (the checker that reads
the declaration) | T-171 (the trace at the harness boundary) | measured 2026-10-16.

**This directory is the ONLY place a harness touches Maxwell OS.** Everything outside it — `pipeline/`,
`config/`, `governance/`, `scripts/`, the registers, MCP — is the CORE and is harness-agnostic (C21/C25). A
harness is a CLIENT: it can be swapped, or replaced by `curl`, without the pipeline noticing.

## 1. WHAT MAY LIVE HERE

A directory per client, `agent/adapters/<client>/`, holding ONLY the binding:

1. `wiring.md` — how this client is pointed at the local engine (the env it needs, the launch form). The engine's
   OWN wiring module is the thing to reference (`omlx launch <tool>`; the modules ship in
   `/Applications/oMLX.app/Contents/Resources/omlx/integrations/`), so nothing is hand-written (C12).
2. `wrapper.sh` (optional) — the command that BINDS the environment for a launch that does not inherit a shell
   (`pipeline/harness_env.py --exec ...`), because a declaration not present in the process is a comment
   (T-132/D-3003, BUG-849).
3. `hook/` (optional, T-171) — the interception point that makes the DELEGATED-RUN TRACE automatic
   (`scripts/delegate_journal.py start|end`) instead of a discipline the agent must remember (D-3039).
4. A row in `config/harness_policy.yaml#harness_matrix` naming what was MEASURED for this client.

## 2. WHAT MAY NEVER LIVE HERE

- pipeline logic, a governed artifact, or anything a portable artifact (a SKILL.md, a task, a decision) would
  have to name to work: a portable artifact that names a harness or a provider is a fault (T-169/D-3037).
- a second copy of a value the core already declares (the model, the provider id, the port) — C12: one home per
  fact.
- load-bearing work. No harness may be on a path whose failure costs data (C27).

## 3. ADDING A CLIENT (the standing procedure, five steps, no exceptions)

1. **A JOB**, named first: what work needs this client that goose cannot do (C28: bloat is opt-in). "It looks
   nicer" is not a job.
2. **One command**: `omlx launch <client> --model <served-model>` — MEASURED to exist for all nine clients
   (`claude, copilot, codex, codex_app, opencode, openclaw, hermes, pi, dsh`), so adoption needs NO disk state of
   ours and installs nothing load-bearing.
3. **A ROW** in `config/harness_policy.yaml#harness_matrix` with what was measured (headless form, footprint if
   taken, whether the traffic landed on the LOCAL engine — the counter, not the claim).
4. **A BINDING** here if the client needs env it does not inherit, plus the wrapper for launches that start
   outside a shell.
5. **A READING, not a promise**: the proof that the client's traffic reached `127.0.0.1:11435`. A client that
   answers while the engine's counter stands still is not local, whatever its config says (MEASURED 2026-10-15:
   `goose run -t` answered PONG with the counter unmoved — BUG-849). The CORRECT WAY TO CHECK is not a new
   instrument: `python3 pipeline/harness_contract.py` already reads the binding (rc 2 = UNBOUND, OWNER-OWED) and
   `python3 pipeline/harness_env.py --exec <cmd>` binds it for a child process. What no rail reads is the
   counter — that gap is T-174's, and it is why this step says READING rather than CONFIG.

## 4. THE SWAP CHECKLIST (what a swap must NOT have to touch)

The core is unchanged by a swap: `pipeline/**`, `config/**`, `governance/**`, `scripts/**`, the registers, the
MCP surface. A swap re-points the EXTERNAL roots a session names and nothing else (D-3037):
`~/.config/goose/config.yaml`, `~/.config/goose/custom_providers/maxwell_omlx.json`, `~/.config/goose/skills/`.
Anything a swap would have to edit OUTSIDE this directory is misplaced: move it here or declare it in
`config/agent_surface.yaml`.

## 5. OPEN, AND NAMED

- **T-171** — the delegate trace must fire AT this boundary, so the start row precedes the call without the agent
  typing two commands. Until it does, the trace is a disciple the caller keeps (D-3039 says so out loud).
- **T-169** — `config/agent_surface.yaml` declares this root; `scripts/check_agent_surface.py` does not exist
  yet, so the declaration has no reader and a second adapter surface could appear unnoticed.
- **T-174 / BUG-849** — the default client's DECLARED provider is not BOUND in the app process, so the everyday
  path can leave the machine. Measured; remedy declared; census owned by T-157.
