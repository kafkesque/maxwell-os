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
