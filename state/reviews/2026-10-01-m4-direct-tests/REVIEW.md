# M4 review — direct tests

Milestone: **M4 · direct tests**. Date: 2026-10-02.

Gate: 45+ direct tests, and a *red* run per group as the evidence.

## Verdict

**Accepted, with five contract defects found and fixed.** The gate is met by a
wide margin — 92 tests across the twelve groups, and 16 of 16 mutations
demonstrating a named test going red.

The important result is not the test count. It is that the direct runner found
five defects that the live-node evidence from M0–M3 had missed, three of them
money-stranding, and one of those was invisible *because the harness itself was
silently broken*.

## The count

```
92 passed in 128.52s (0:02:08)
```

Reproduce with:

```bash
bash run_direct_tests.sh
```

`run_direct_tests.sh` sets `GENVM_VERSION=v0.6.0-rc5`, puts `tests/direct` on
`PYTHONPATH`, loads the `gltest_compat_plugin` shim ahead of gltest's entry
point, and seeds the SDK cache if it is missing. No Docker, no network, no
model, no live node.

### One ergonomic landmine, recorded

`run_direct_tests.sh -q` produces **no pytest summary line**. The progress dots
print and the exit code is right, but pytest's `92 passed in …` never appears.
It is a `-q` interaction with gltest's plugin set on this runner, not something
the suite does — so the evidence line in `docs/VERIFICATION.md` was captured
**without** `-q`. Do not add `-q` to the documented command and conclude the
suite is broken.

For a machine-readable result regardless, `--junitxml=path` works:

```
$ .venv/bin/python -c "…junit parse…"
tests=92 failures=0 errors=0 skipped=0 time=68.310s
```

## The twelve groups, and what each one is actually for

| group | tests | the behaviour it defends |
| --- | --- | --- |
| canonicalisation | 8 | one logical input, one stored representation, so the duplicate check cannot be evaded |
| malformed shapes | 13 | a payable method must never revert — every bad input still leaves a refundable row |
| deadline boundary | 6 | the comparison is `observed < deadline`, tested from both sides and across a timezone offset |
| duplicate | 4 | the digest set records standing entries only |
| declared vs measured | 5 | the manifest settles a declaration, and the note says which language matched |
| source failure | 8 | only 404 is a rejection; 403/429/500/502, empty and non-JSON are UNDETERMINED |
| digest integrity | 5 | the receipt digest tracks the record, and two things it deliberately does not hide |
| authorisation | 7 | owner finalises and cancels, entrant claims, nobody else |
| challenge | 9 | one challenge per entry, against a standing entry, naming one criterion |
| refund | 6 | a refund is a refund when the observed balance falls |
| conservation | 6 | value in == value scheduled out, for any lifecycle |
| panel and API boundaries | 11 | M3.5 really is absent, and `program_id` is a `str` while `entry_index` is an `int` |

Three things the suite deliberately does **not** test, and why:

- **Arrival time.** There is no block clock, so there is no arrival time to
  observe. The deadline group tests the comparison, which is the claim being
  made; a late submission of a pre-deadline commit is accepted and visibly
  pre-deadline by design.
- **`validator_fn`.** gltest's direct runner executes the leader and returns its
  result without running the validator (`_handle_run_nondet`: *"In direct mode,
  we skip the leader/validator consensus"*). The M1 convergence evidence — 6/6,
  2-bucket — therefore remains the only evidence for validator behaviour. This
  is a **coverage gap, stated rather than papered over**; closing it needs a
  harness change, not a test.
- **Live settlement.** `TRANSFER_EMITTED` is a scheduled transfer. Every
  money-moving test asserts on the observed balance, but only the direct
  runner's value model makes that meaningful, and the model is ours (below).

## The harness: five bugs in gltest 0.29.2, all in this file's docstrings

`tests/direct/conftest.py` carries a project-local monkeypatch layer. It patches
`gltest.direct.loader`, `gltest.direct.sdk_loader`, `gltest.direct.wasi_mock`,
and `gltest.direct.pytest_plugin` — **not** the installed package files, so
every change is visible, reviewable, and disappears with the venv.

1. **`wasi_mock.gl_call` could not decode a single request.** It does
   `from genlayer.py import calldata`; this SDK has no `genlayer.py` package, so
   every host call returned the failure sentinel. Balances read 0,
   `emit_transfer` did nothing, `mock_web` was never consulted, `run_nondet`
   failed. A suite built on that would have reported green while testing
   nothing. Fixed with three `sys.modules` aliases, which repairs every site at
   once.
2. **`_inject_message_to_fd0` swallowed its own `ImportError`**, so fd 0 was
   never written and every call died with `DecodingError: unexpected end of
   memory`. Reimplemented against the modern encoder, including
   `signer_address` and `datetime`.
3. **`_allocate_contract` fell through to a second branch importing the same
   missing module**, producing a non-storage-backed instance and
   `AttributeError: 'ContestReceipt' object has no attribute '__type_desc__'` on
   the first read. Reimplemented with modern `_storage_build`.
4. **`setup_sdk_paths` was called with `version=None`**, which takes the
   *highest cached* GenVM — here `v0.6.0-rc8`, which has no `genlayer` package
   at all. The symptom was `ModuleNotFoundError`, mentioning nothing about
   versions. Forced to the pinned `v0.6.0-rc5`.
5. **`genlayer.message` populates its globals once at import**, freezing
   `gl.message.sender_address` and `.value` for the whole process. Authorisation
   was therefore untestable *and silently wrong*. Fixed by refreshing the
   message before each public call, and by patching the plugin's own
   `deploy_contract` binding, which it captures at import time.

Plus three things gltest does not model at all, and this milestone needed:

- **Value.** The dispatcher handles `Return`, `Rollback`, `Trace`, `Sandbox`,
  `RunNondet`, `WebRequest`, `WebRender` and `ExecPrompt` — and nothing else.
  Nothing credits a payable call, so `get_contract_balance()` was 0 forever, and
  `EmitExternalMessage` was unhandled, so a scheduled transfer did nothing. Both
  would have let the refund and conservation groups report success while
  observing nothing.
- **Internal messages.** `contract.emit(...)` sends
  `{'EmitInternalMessage': …}` and *discards the returned descriptor*. With no
  dispatcher branch, an internal callback **silently never runs** — see
  defect 2 below, which this was hiding.
- **`run_nondet` error reporting.** A leader exception was returned as raw
  UTF-8 in a packet the SDK decodes with `calldata.decode`, so the one message
  that would explain the failure was destroyed and surfaced as a decoding error
  in the VM's plumbing. That one-word change is what turned "a test is failing
  somewhere" into `UserError("name 'committer_block' is not defined")`.

## Five defects found

Ordered by consequence. All five were confirmed against the contract's own
stated rules, not against my expectations, and all five are fixed.

### 1. `freeze_entry` never worked — a typo on the happy path

`contracts/contest_receipt.py:572` read `committer_block.get("committer")` where
the local was `commit_block`. A `NameError` on every 200 from the commit
endpoint — that is, every successful freeze.

It was not caught at M3 because `freeze_entry` is the only method that needs
GitHub, and M3 had no network. The M3 smoke test read `get_program`,
`get_receipt_digest`, `get_accuracy` and `get_contract_balance`; it never
froze an entry. **A green live gate that never exercised the method is not
evidence about that method.**

### 2. The winner could never be paid — an inverted guard, invisible for a month

`claim_payout` required `payout_status == PENDING_FINALITY`. But
`_on_entry_finalized` — the clock-reading half of rule 5's split — exists to move
an entry *off* that state and onto `PAYOUT_READY`. The two conditions could
never both hold: after finality was observed the claim was refused
("entry is not awaiting a payout"), and before it, the programme was not closed.
The payout path was dead on chain, with the pool stranded, because a `CLOSED`
programme cannot be cancelled.

This one was masked by harness defect 5 above: with `EmitInternalMessage`
undispatched the callback never ran, `payout_status` stayed `PENDING_FINALITY`
forever, and `claim_payout` *succeeded*. The suite would have gone green against
a contract that could not pay anyone on chain.

**This is the finding that justifies the milestone.** A silent harness failure
produced a green suite over a dead product. Fixed in `claim_payout`; the guard
now requires `PAYOUT_READY`, which is what makes the two-method split mean
anything.

### 3. An outage could disqualify an entrant

Two places turned missing data into a verdict:

- `freeze_entry`'s post-processing for `declared_language_present` ran
  unconditionally, so when the leader returned **no paths** because GitHub was
  unavailable it searched zero paths for `.py`, found none, and recorded `FAIL`.
- Inside `leader_fn`, a 200 whose body carried no tree at all produced zero
  blobs, so `required_files_present` was recorded as `readme_absent` — a `FAIL`
  for a repository nobody managed to read.

Both are the same inversion: absence of evidence read as evidence of absence,
which is the precise failure mode this product exists to prevent. Both now yield
`UNDETERMINED`. The tree case costs no genuine detection — a real repository
always has at least one blob.

### 4. A denied challenge's bond could be stranded

A bond is returned by `claim_payout`, which accepts only `CLOSED` or
`CLOSED_NO_WINNER`. `cancel_program` sets the status to `CANCELLED`. So a
programme cancelled with a denied bond outstanding returned the pool to the
owner and left the challenger's GEN in the contract with **no path out** —
1000 refunded, 100 stuck. `cancel_program` now sweeps outstanding denied bonds
in the same call, keeping one rule true: everything the contract holds goes back
through a method that moves value.

### 5. `AFTER_DEADLINE_WORK` could never be upheld

`_refutes_claim` compared `evidence.strip()` to the stored commit SHA, but
`evidence` had already been canonicalised by `_canonical_demo` as an **https
URL**. A valid URL never equals a 40-character hex digest, so the one ground a
deterministic re-derivation can actually settle was decorative. The commit is now
extracted from the evidence with a 40-hex pattern.

## Also fixed, without changing behaviour

- **`get_entry` raised on an unfrozen entry.** `TreeMap.__getitem__` raises
  `KeyError` for an unwritten key — measured on the live target, not assumed —
  so reading a submitted-but-not-frozen entry failed. **Confirmed on chain at
  M4**: `submit_entry` finalized, then `get_entry("0","0")` returned
  `gen_call failed (code=-32000)`. This is the state the frontend reads most
  often. Views now read through `_read(tree, key, default)` and report absence
  as `NOT_JUDGED`; write paths still index directly, so a genuine
  write-before-read bug in this contract would still surface.
- **`finalize_program` raised on any unchallenged entry.** Its bond-return loop
  indexed `challenge_status` for every entry, but that key is written only for
  challenged ones. The method the product exists to reach could not run on a
  programme with no challenge at all.
- **`_require_entry` indexed `program_entry_count` directly**, so an unknown
  programme raised rather than refusing. Fixed.
- `finalized_at` was written by the callback and unreachable from any view, so an
  audit record could not show *when* a verdict became final. Now on `get_receipt`.

`scripts/m4_ast_scan.py` lists every remaining unguarded `TreeMap` read, so the
next person does not have to rediscover this class of bug by reading 1900 lines.

## Mutation proofs

**A green run is not the evidence. A red one is.** Full table in
[`MUTATIONS.md`](MUTATIONS.md), regenerated by
`scripts/m4_mutation_proof.py` — 16 deliberate one-line breaks, each with the
name of the test that noticed.

```
[canonicalisation] RED as expected: test_repo_url_forms_canonicalise_identically (2 test(s) red)
[malformed-shapes] RED as expected: test_too_few_criteria_are_refused (2 test(s) red)
[deadline-boundary] RED as expected: test_exactly_at_the_deadline_fails (2 test(s) red)
[duplicate] RED as expected: test_the_same_tree_under_a_different_repo_spelling_is_caught (1 test(s) red)
[declared-vs-measured] RED as expected: test_an_unknown_language_token_cannot_pass_on_another_tokens_match (1 test(s) red)
[source-failure] RED as expected: test_a_non_200_non_404_is_undetermined_not_a_failure (1 test(s) red)
[digest-integrity] RED as expected: test_the_digest_changes_when_a_verdict_is_recorded (4 test(s) red)
[authorisation] RED as expected: test_a_non_owner_cannot_cancel (1 test(s) red)
[challenge] RED as expected: test_a_second_challenge_on_one_entry_is_refused (1 test(s) red)
[refund] RED as expected: test_cancelling_twice_does_not_transfer_twice (1 test(s) red)
[conservation] RED as expected: test_a_tied_split_conserves_every_unit (1 test(s) red)
[panel] RED as expected: test_accurancy_separates_undetermined_from_disqualified (2 test(s) red)
[payout-ordering] RED as expected: test_the_winner_is_paid_only_after_finalization_is_observed (6 test(s) red)
[evidence-intersection] RED as expected: test_an_upheld_challenge_disqualifies_the_entry_and_forfeits_the_bond (1 test(s) red)
[absent-evidence] RED as expected: test_an_empty_200_body_makes_every_content_derived_criterion_undetermined (4 test(s) red)
[bond-recovery] RED as expected: test_a_challenge_bond_is_conserved_across_the_whole_lifecycle (1 test(s) red)

working tree restored: NO
contract restored from backup: yes
```

Three of these re-introduce a defect this milestone found
(`payout-ordering`, `evidence-intersection`, `absent-evidence`,
`bond-recovery`) — so each new test is proven to fail against the exact bug it
was written for, not merely against some hypothetical one.

`working tree restored: NO` is **a bug in my own check**, recorded rather than
tidied away: it compared the contract against the pre-run state *before* the
restore ran, so it was reading the last mutation and reporting a false negative.
Fixed to restore first and then compare. The line above it is the one that means
anything: `contract restored from backup: yes`.

## Linter: no longer `unverified`

The M3 record listed `genvm-lint check`'s SDK-validation half as
`unverified` — it hung indefinitely on SDK-load network timeouts. At M4 it
completes:

```
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: ContestReceipt
  Methods: 14 (6 view, 8 write)
```

Exit 0. Both halves are now verified, and the method count still matches the
plan's tolerance of at most 14.

## What M4 does not establish

Stated plainly, because the next milestone will read this file:

- **The validator is still unexercised.** Direct mode runs the leader only.
  M1's 6/6 2-bucket convergence remains the only validator evidence.
- **No live run of `freeze_entry`.** Every GitHub call here is mocked. The M6
  live run is the first time `freeze_entry` executes against real GitHub, and
  defects 1, 3 and 5 were all in that path.
- **The payout path has not moved real value on chain.** Defect 2 was found and
  fixed here, but proving it needs M6's finalization plus an observed balance
  decrease — the same observation M3 made for the refund path, which is why
  `claim_payout` should not be trusted until then.
- **The value model is ours.** `direct_vm.deal`, the payable-call credit and the
  `EmitExternalMessage` debit are all modelled in `conftest.py`, not by gltest.
  Conservation tests are therefore only as good as that model. It is modelled to
  match the chain's semantics and the refund path was cross-checked against the
  live 1000→0 observation from M3, but it is not independent evidence.
- **`gltest_compat_plugin` reintroduces `TransactionStatus`.** A test-harness
  shim for a name `genlayer-py 0.19.0rc2` removed; downgrading would have undone
  an M0 finding. It is not on the contract's import path.

## Reproducing

```bash
# the suite
bash run_direct_tests.sh                          # 92 passed in ~2 minutes

# the mutation proofs (16 runs, ~20 minutes)
.venv/bin/python scripts/m4_mutation_proof.py

# the linter, both halves
GENVM_VERSION=v0.6.0-rc5 .venv/bin/genvm-lint check contracts/contest_receipt.py

# if the SDK cache is missing
bash scripts/seed_gltest_cache.sh

# remaining unguarded TreeMap reads
.venv/bin/python scripts/m4_ast_scan.py
```

Environment: Python 3.12.3, `genlayer-test 0.29.2`, `genlayer-py 0.19.0rc2`,
GenVM `v0.6.0-rc5`, offline. Contract at the time of the run: 1891 lines,
14 methods (8 writes, 6 views), `git rev-parse --short HEAD` = `237662a` plus
the uncommitted M4 changes listed in the commit that follows this record.