# specs/ — THE SPEC / TEST SANDBOX (charter, D-2978 + D-2981)

**What this directory is.** One SPEC per GOVERNED SURFACE: a written definition of correct that exists
BEFORE a change lands and STAYS as the definition afterwards. Every spec is paired 1:1 with its
executable contract under tests/, and the MACHINE RUNNER (pytest) is the grader.

## The rules (standing)

1. **One surface, one spec, one contract.** specs/<surface>.spec.md pairs 1:1 with
   tests/test_<surface>_spec.py. A surface with no spec is a surface whose "correct" is somebody's memory.
2. **Overwrite in place (D-2978).** A spec is never appended and never duplicated per change: the
   contract changes, the file is rewritten, and the history lives in git plus the D-number that changed
   it. File proliferation is the failure mode this rule exists to prevent.
3. **The runner grades; a model may only DRAFT.** R5 (generator is not the verifier) and R7 (temp=0.0 on
   the runner). A local LLM may propose a spec or a test; the pytest result is the verdict.
4. **Deterministic detectors FIRST, advisory model second.** An invariant is checked by code that needs
   no LLM wherever code can decide it. Same order as the R5 gate (D-2962) and the rails: syntax, lint and
   contracts mechanically, then one advisory reviewer.
5. **Diagnostics name the REMEDY.** A failing invariant prints what is wrong AND the derived fix (the act,
   the command, the field to change) — never a bare assertion failure. A failure a reader cannot act on
   is not a diagnostic.
6. **An invariant must be FALSIFIABLE.** State the failure it prevents. "The ranking signal must not be a
   constant" is a spec line because someone MEASURED it collapsing to a constant (BUG-710).

## Inventory

| spec | contract | invariants | status |
|---|---|---|---|
| specs/retrieval_serving.spec.md | tests/test_retrieval_serving_spec.py | INV-1..INV-7: golden anchoring, run pinning, ranking signal, fail-loud gate, ONE dispatch point, the harness measures the SERVED path, ONE pool home | live; 8/8 green 2026-10-13 |
| specs/governance_faces.spec.md | tests/test_governance_faces_spec.py | INV-1..INV-16: the claim surface of the faces - history region (label, census marker, decision rows, OPEN assertions, repair-naming, ordering, mutation lock), the LIVE region (one live label, citations resolve, the OWNER LANE leads, the re-cut's scope), the index HEADINGS between them (what a heading that names a state owes, and the count it may not carry) AND the STATES themselves (every declared state carries a sign the authority renders, and the declared decision buckets partition the register) | live; 17/17 green 2026-10-13 |
| specs/label_store_write.spec.md | tests/test_label_store_write_spec.py | INV-1..INV-8: the LICENSED store write for OWNER-RULED labels - the owner word as the whole authority (no licence, no write), execute-never-mint (a licensed unit no ruling reaches is refused), the licence may not be NARROWER than the rulings, the TRIPLY agreed target (mapper == owner == packet), scope by IDENTITY with a stale surface refused, the SHRINK-ONLY cap and the declared C29 tier, the receipt as a MEASUREMENT rather than a claim, and the raw plus the macro/counts homes untouched | live; 9/9 green 2026-10-13 |
| specs/task_register.spec.md | tests/test_task_register_spec.py | INV-1..INV-6: a standing RULE is not a task, WHO must move it is declared, an owner gate is a MOVER, a count has ONE home, OPEN-ness is the census's (the severity line partitions it), the rule is mutation-locked | live; 7/7 green 2026-10-13 |
| specs/config_defaults_census.spec.md | tests/test_config_defaults_census_spec.py | the undeclared-default census: the alias-aware key set, the receipt, the shrink-only ceiling | live 2026-10-13 |

**MEASURED 2026-10-13 (D-2985): this inventory had drifted.** It listed ONE spec while `specs/` held four - an
inventory that names one of four files is the BUG-588 shape in the sandbox's own front door. The rows above are
the set that exists; a new spec adds its row here in the same change (rule 1, applied to this file).
**D-2987 kept the row honest the same way:** the governance_faces row moved 14 invariants -> 16 in the same act
that added INV-15 (a declared state carries a sign the authority renders) and INV-16 (the decision-state buckets
partition the register). **D-2986 kept the row honest the same way:** the governance_faces row moved 13 invariants -> 14 in the same act
that added INV-14, and its status line moved with it - an inventory row is a claim too.

## Prior art assessed 2026-10-13 (NOT adopted as tools; two mechanisms borrowed)

The owner asked whether pbakaus/impeccable and shadcn-ui/lint are adaptable into this sandbox.
Verdict: neither is adoptable, and both are worth citing.

* **impeccable** — design guidance for AI coding agents: one skill, 24 commands, live browser iteration,
  and 59 deterministic detector rules for AI-generated frontend design. Maxwell OS has NO frontend
  surface, so the tool does not apply. Two of its MECHANISMS match this sandbox and are now rules above:
  (a) a durable product-truth file read before any change, so surface direction is never confused with
  product fact (CONSTITUTION.md plus governance/CONTEXT_INDEX.md play that role here); (b) a BOUNDED,
  COUNTABLE set of deterministic detector rules per surface with the LLM layer strictly advisory.
* **shadcn-ui/lint** — an AGENT-FIRST linter for Tailwind design systems: you declare what is allowed and
  a violation EXPLAINS what is wrong and SUGGESTS a fix derived from your own components and theme. The
  tool targets React/Svelte/Vue design systems and does not apply here; the mechanism does, and it is now
  rule 5 (diagnostics name the derived remedy). It is the same shape as our declared config plus
  fail-closed rails, which already print the required act (D-2971's rebaseline prints its own command).

Both references are recorded in governance/NOT-YET-EVALUATED-RESEARCH.md with the same verdict, so the
question is answered once instead of re-asked every session.
