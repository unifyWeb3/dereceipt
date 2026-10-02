# Project state — DeReceipt

A GenLayer intelligent contract for auditable verdicts in AI-judged hackathons.
Milestones M0–M5 are done. M6 (live run) is next. **No Portal submission is
authorized.**

The plan of record is
`state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`. Evidence
lives in `docs/VERIFICATION.md`; hard rules in `docs/ARCHITECTURE.md`.

## Where things stand

| milestone | status | record |
| --- | --- | --- |
| M0 · environment and pins | passed | `state/reviews/2026-10-01-m0-env-pins/` |
| M1 · consensus spike | passed, 6/6 2-bucket, validator caveat | `state/reviews/2026-10-01-m1-consensus-spike/` |
| M2 · repo skeleton | passed, 11/11 | `state/reviews/2026-10-01-m2-repo-skeleton/` |
| M3 · the deterministic core | passed | `state/reviews/2026-10-01-m3-review/` |
| M3.5 · bounded LLM criterion | **deliberately skipped** | see below |
| M4 · direct tests | passed, 92 tests, 16/16 mutations proved | `state/reviews/2026-10-01-m4-direct-tests/` |
| M5 · frontend | **passed** — 33/33 gate, 27/27 live reads, `freeze_entry` ran against real GitHub | `docs/VERIFICATION.md` M5 |
| M6 · live run and evidence | — | — |
| M7 · docs | — | — |
| M8 · deploy, demo, submit | not authorized | — |

## What is built

`contracts/contest_receipt.py` — 14 methods, 8 writes and 6 views. The current
revision is deployed at `0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D`, finalized,
with a real frozen receipt on programme `0`. Seven steps of the
lifecycle are implemented: open a programme, submit an entry, freeze it against
GitHub, challenge one criterion with a bond, finalize and allocate, claim a
payout, cancel and refund. Six views; the receipt is the challenge log, so
`get_challenge` is deliberately absent.

No subjective criterion and no `run_panel` (M3.5). Both were skipped on purpose:
`run_panel` can label one criterion and never moves money, so it adds no property
the receipt does not already have.

## Validation status

- `genvm-lint check` — **both halves clean**, exit 0. The SDK-validation half
  hung at M3 and was recorded `unverified`; it completes now.
- Direct suite — **92 passed**, twelve groups, 16/16 mutation proofs. See
  `docs/VERIFICATION.md` for the verbatim line.
- Live node — the refund path was observed moving 1000→0 at M3. At M5,
  `freeze_entry` ran against the **real GitHub API** and produced real verdicts
  and a real digest. `finalize_program` and `claim_payout` have **never run on
  chain**; M6 is where they get proven.

## The five things a newcomer must know

1. **There is no block clock on this runner.** The deadline is an absolute unix
   second compared against GitHub's signed `committer.date`. Arrival time is
   neither observable nor claimed.
2. **Only a 404 is a rejection.** Every other GitHub status, and every
   unreadable body, is `UNDETERMINED`. A rate limit must never disqualify.
3. **A green live gate proves nothing about a method it did not call.** M3 was
   green and `freeze_entry` had a `NameError` on its happy path.
4. **A harness can hide a dead product.** M4's biggest finding — an unreachable
   payout path — was invisible because gltest silently discarded internal
   messages. "The test passed" is only as good as the harness under it.
5. **A check that fails for the wrong reason is not a check.** M4 recorded
   `get_entry` as broken on chain; it was the Python client rejecting a string in
   a `uint256` slot. Corrected at M5. Attributing a failure without first
   establishing the check was sound is this project's recurring hazard — three
   times now.
6. **A scheduled transfer is not a delivered one.** Every money-moving claim
   needs an observed balance change, not a `TRANSFER_EMITTED` string.