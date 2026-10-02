# Memory — durable constraints and lessons

Things that were learned the hard way and will be expensive to learn again.
Not a log; a list of traps.

## The runner

- **There is no block clock.** `get_timestamp` does not work. Anything needing
  "now" must compare against an external signed source, or record
  `NO_CLOCK_ON_THIS_RUNNER` where a timestamp would go. This is why the deadline
  is proven by GitHub's `committer.date` and why rule 5 (never combine a clock
  read with a transfer) is vacuously satisfied rather than actively enforced.
- **Studio-dev's fee estimator runs on a badly stale clock**, so a method that
  both reads the block clock and posts a transfer reverts with
  `out_of message_fee total`. Keep the two in separate methods.
- `genlayer-py 0.19.0rc2` names `FeesDistributionMissing`, which `0.18.0` and
  below report as a bare "Transaction reverted". M0 pinned 0.19.0rc2 for that
  reason and `genlayer-test 0.29.2` wants `<0.17` — hence the test-only shim in
  `tests/direct/gltest_compat_plugin.py`. Do not "fix" the conflict by
  downgrading.
- `genlayer-py` 0.19 removed `TransactionStatus` in favour of
  `TransactionLifecycle`, which is what breaks `gltest`'s import.
- **The two SDKs disagree on identifier types, measured at M5.** `genlayer-py`
  rejects a string in a `uint256` slot (`code=-32000`); `genlayer-js` coerces it
  and succeeds. `program_id` is a `str`, `entry_index` is an `int`, and **only
  the Python client enforces it**. So a JS-side bug here is silent, and a
  Python-side bug here looks exactly like a broken contract. This caused a false
  M4 finding.

## GenLayer storage

- **`TreeMap.__getitem__` raises `KeyError` for a key that was never written.**
  Measured, not assumed. A view that reads a field nothing has written yet
  fails rather than reporting absence. This is why views go through
  `_read(tree, key, default)`.
- Canonical JSON sorts *keys*, not *list* order. Criteria are snapshotted in the
  organiser's declared order, and that order reaches `get_receipt_digest` — two
  programmes with the same criteria declared in a different order get different
  digests. Not a bug, but it will surprise anyone comparing two programmes.

## Testing traps

- **`gltest`'s direct runner does not model value.** Nothing credits a payable
  call and `EmitExternalMessage` is unhandled, so balances read 0 and transfers
  do nothing. `tests/direct/conftest.py` adds both.
- **The direct runner does not dispatch internal messages.** `contract.emit(...)`
  discards the returned descriptor, so `_on_entry_finalized` silently never ran —
  and that hid an unreachable payout path. A harness can hide a dead product.
- **The direct runner executes the leader and never the validator.** M1's
  convergence evidence is therefore the only validator evidence there is.
- **`mock_web` matches the *first* registered pattern.** Registering a second
  mock for the same URL leaves the first in force, silently. `reset_mocks` in
  `tests/direct/helpers.py` exists for this and must be called before re-mocking.
- **`-q` suppresses pytest's summary line** on this runner. The suite looks like
  it hung or crashed when it has not.
- Shell commands here get killed when the caller's shell exits. Use
  `setsid bash -c '… > file 2>&1' &` and poll the file.

## Judgement calls made, and why

- **M3.5 (`run_panel`) was skipped.** It can label one criterion and never moves
  money, so it adds no property the receipt lacks. The `INCONSISTENT` gap it left
  is closed deterministically at M6 with a real refuted repo.
- **A 404 is the only rejection.** Everything else is `UNDETERMINED`. A rate
  limit must not decide a contest.
- **A failed `open_program` still creates a `CANCELLED` programme.** It received
  GEN and cannot revert or transfer, so the row is what makes the refund
  recoverable. Same reasoning for `challenge`.
- **The contract was changed five times during M4** — a typo, an inverted guard,
  two absence-of-evidence inversions, a stranded bond, a dead ground, and view
  reads. Each is recorded in
  `state/reviews/2026-10-01-m4-direct-tests/REVIEW.md` with the reasoning,
  because "the tests were failing so I changed the code" is exactly the move
  that needs a paper trail. **Do not change contract behaviour to make a test
  pass without writing down why the old behaviour was wrong.**

## Naming

The product is **DeReceipt**. The name is defined once, in
`frontend/src/config.js`, as `PRODUCT_NAME`. Renaming it is a one-line change
there plus the README title.

The contract file stays `contracts/contest_receipt.py` and is **not** renamed. A
file's name is part of the record of what was measured — M0 through M5 all cite
that exact path, and the deployed contract's identity comes from its content, not
its filename. Conflating the two would make the evidence trail lie.

## Do not

- Do not touch `scripts/gl_env.py`'s two secret guards.
- Do not add a database.
- Do not weaken a test to make it pass; break the contract and prove the test
  goes red instead.
- Do not claim a check passed when it was not run. `docs/VERIFICATION.md` keeps
  `unverified` rows, and that vocabulary is load-bearing.