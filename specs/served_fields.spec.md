# specs/served_fields.spec.md — the fields a serving surface publishes are CLAIMS

**Authority:** D-2989 · **Decided:** 2026-10-13 · **Subjects:** T-107 (owner word), BUG-767, BUG-768
**Applies to:** `config/served_fields.yaml` (the ONE home), `scripts/check_served_fields.py` (the rail),
`config/feedback.yaml` + `scripts/check_feedback_parity.py` (the ledger↔cache arm),
`maxwell_mcp_server.py` / `pipeline/stage6_okf_export.py` / `pipeline/stage6b_anytype_push.py` (the surfaces).
**Paired contract:** `tests/test_served_fields_spec.py` — one named test per invariant (D-2978).

## Why this spec exists

A serving surface that publishes a store column makes a CLAIM about the store. Until this spec, nothing joined the
claim to the registers that already own the column's truth (`config/derivations.yaml` — the home and status of every
derived value, D-2646; `config/store_columns.yaml` — every column's role and status, D-2960). MEASURED 2026-10-13:
53 advertised store fields joined, **3 of them flagged by a register that owns the fact** and still published to
agents, and a fourth defect hidden behind them (the principle the metric was named after is satisfied by only 21% of
served rows). The rail is a JOIN, never a census: a second census of the same fact is the defect the registers exist
to prevent (C12/D-2642).

---

### INV-1 — An advertised field is a CLAIM, and the advertisement is read from the AST
- **Correct:** the advertised set is the string KEYS of the dicts in each declared surface (`kind: dict_keys`) or the
  string constants that name a field (`kind: string_mentions`), INTERSECTED with `PRAGMA table_info(fbs)`: an
  advertised key that names a store column is a claim; a key that does not is payload structure.
- **Wrong:** a hand-maintained field list (it drifts), or a text scan a comment can satisfy.
- **Status:** ✅ SATISFIED — `advertised_fields()` reads the AST; `test_the_scan_reads_the_ast_and_joins_the_store`,
  `test_a_comment_cannot_advertise_a_field`.

### INV-2 — A flagged advertised field MUST carry a declaration
- **Correct:** if either register flags the column (`derivations`: `dead_but_read` | `declared_but_empty` |
  `orphan_magic_threshold`; `store_columns`: `status: debt`), the field carries a `declared` row (an owner word) or
  an `acknowledged` row (a SOURCE-owned repair) in `config/served_fields.yaml`.
- **Wrong:** publishing a value a register calls defective while nothing names it — the BUG-511 family, where a value
  nothing writes is presented as a measurement.
- **Status:** ✅ SATISFIED — `test_an_undeclared_advert_is_refused` (known answer), and the LIVE run reports 0
  undeclared of 53 joined fields.

### INV-3 — The owner word is vocabulary-checked and SIGNED
- **Correct:** the word is one of `retire` | `keep` | `keep-and-declare` | `keep-and-repair` | `promote <field>`; any
  other word is refused BY NAME, and a word that is not `pending` without an `anchor` is refused (T-101: an unsigned
  decision is not a rule).
- **Wrong:** accepting `drop` / `keep-as-is` the way the re-anchor sheet once accepted `keep`/`replace`/`drop`/`add`
  — a token no reader implements.
- **Status:** ✅ SATISFIED — `test_a_word_outside_the_vocabulary_is_refused`, `test_an_unsigned_word_is_refused`.

### INV-4 — A declaration tracks its subject in BOTH directions
- **Correct:** a `declared`/`acknowledged` field that NO declared surface advertises is a DEFECT (an assertion whose
  subject is gone — BUG-488/D-405); a flagged field that IS advertised with no row is a DEFECT (INV-2).
- **Wrong:** the BUG-548 shape (the record kept as if it were the rule), in either direction.
- **Status:** ✅ SATISFIED — `test_a_stale_declaration_is_refused`, `test_an_acknowledgement_must_still_be_advertised`.

### INV-5 — A promotion names a home that RESOLVES
- **Correct:** `promote <field>` requires a `promotions` entry whose `home` is `path.py::symbol` and whose file AND
  symbol exist; the rail asserts it.
- **Wrong:** a promotion that names a home which is only a hope (a plan dressed as a fact).
- **Status:** ✅ SATISFIED — `test_a_promotion_must_name_a_resolving_home` drives a MISSING home to a DEFECT and
  asserts the declared `corroboration` home resolves (`pipeline/schema_accessor.py::isor_score`, D2284).

### INV-6 — The debt is LOUD, not fatal, and its ceiling is SHRINK-ONLY
- **Correct:** `rc 2` when the owner word is owed (or written but not landed) and the count is within
  `coverage.max_declared_debt`; `rc 1` when the count EXCEEDS the ceiling, or on any defect; `rc 0` at the floor.
- **Wrong:** a silent pass (the value is published and nobody is told), or a fatal rail that blocks the commit
  frontier on an owner-gated act (BUG-457 tri-state).
- **Status:** ✅ SATISFIED — `test_the_debt_is_loud_not_fatal_and_shrink_only` (the live rail returns 2 with
  debt == ceiling == 3, floor 0).

### INV-7 — The feedback CACHE is reproducible from its LEDGER through ONE formula
- **Correct:** `pipeline/feedback.py::declared_aggregate` is the formula's ONE home; the writer
  (`_update_fb_aggregates`) and the parity rail both import it, and `scripts/check_feedback_parity.py` proves the
  stored cache equals what the ledger recomputes (D-2642). With `prior_weight` 0 the formula IS the plain mean.
- **Wrong:** a second copy of the formula in the rail (the BUG-499/BUG-502 class), or a cache with `parity_rail:
  null` in `config/derivations.yaml`.
- **Status:** ✅ SATISFIED — `test_the_parity_rail_drives_the_writer_formula`,
  `test_the_formula_is_not_restated_in_the_rail` (source scan), and the live run reports 0 mismatch.

### INV-8 — Absence is NULL, never hollow, and the absence is DECLARED
- **Correct:** an empty ledger writes NOTHING: `feedback_score` stays NULL (D-2957) and the reader reports
  `state: 'no_feedback'`. The serving prior and the aggregate's policy values live in `config/feedback.yaml`.
- **Wrong:** a stored `0.0` for "nobody rated this", or a wire `null` an agent cannot tell from a score of 0.0.
- **Status:** ✅ SATISFIED — `test_an_empty_ledger_leaves_the_absence_absent`.

### INV-9 — A failed read is NEVER a healthy verdict
- **Correct:** `get_fb_feedback_stats` returns a tri-state (`measured` | `no_feedback` | `unmeasured`) and, on error,
  `needs_retirement: None` with the error text — an unmeasured value can never be read as "this FB is fine" (C16).
- **Wrong:** returning `needs_retirement: False` from an `except` clause (the error-leak class).
- **Status:** ✅ SATISFIED — `test_a_failed_read_reports_unmeasured`.

### INV-10 — A granted owner word is JOINED to the thing it names, never restated
- **Correct:** the T-118 word `tier` is granted in `config/served_fields.yaml#tier_policy`, and its vocabulary is
  asserted against the string CONSTANTS of the measure's OWN home function
  (`pipeline/schema_accessor.py::isor_score`); a tier token that exists only in config is refused as a rival
  definition of the value it claims to read (C12/D-2642), and an unsigned word is refused (T-101).
- **Wrong:** a tier vocabulary declared in config but absent from the measure; a grant with no date and no author;
  a declaration that omits the block entirely while the policy gate it answers is GRANTED — silence is the fault.
- **Status:** ✅ SATISFIED — `test_the_tier_word_is_joined_to_the_measure_it_names`.

## Non-goals (out of scope for this spec)
- The COLUMN-shape census of the store — `config/store_columns.yaml` / `scripts/check_store_columns.py` own it
  (BUG-766 tracks its six population-shape drifts).
- The retrieval ranking policy — `specs/retrieval_serving.spec.md` owns it (INV-3 there; `_rank_sql()` is its home).
- The tier MEASURE itself (author independence × domain diversity × source count) — `pipeline/schema_accessor.py` and
  `config/derivations.yaml` own it (D2284/D2309). This spec owns only the POLICY that consumes it (INV-10, T-118).

## Open items recorded by this spec (so they are not blindspots)
1. The owner words for `borp_score`, `feedback_score` and `classification_status` are PENDING (T-107) — the rail
   reports rc 2 (loud, not fatal) until they land, and it refuses a half-move.
2. The serving neutral prior is still a LITERAL in `pipeline/retrieve.py:1070,1071,1090,1091`; the change-set moves
   all four reads onto `config/feedback.yaml#serving.neutral_prior` (declared here, owed to T-107).
3. `isor` — the real corroboration signal (D2284/D2309/D2185, 6,591 populated rows) — is advertised by NO surface
   today; the `corroboration` promotion is the recommendation, not yet a fact.
4. **T-118 is GRANTED (2026-10-14)**: the single-source disposition is `tier`, declared in
   `config/served_fields.yaml#tier_policy` and machine-joined by INV-10. The CHANGE-SET it owes is still open: the
   three surfaces keep publishing `borp_score: 0.0` and publish no tier (BUG-767), so the policy is declared with no
   consumer until that act lands — recorded here rather than implied.
