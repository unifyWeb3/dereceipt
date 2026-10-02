# M4 review — accepted, with two changes to review

Reviewed: 2026-10-02. Verdict: **the strongest milestone so far. 92 tests, 16/16
mutations proven red, five real defects found. Proceed to M5.**

Commit `d47bc1c`. Record: `state/reviews/2026-10-01-m4-direct-tests/`,
`MUTATIONS.md`, `docs/VERIFICATION.md` §M4.

## Independently reproduced

```
$ bash run_direct_tests.sh
92 passed in 116.99s (0:01:56)
```

87 test functions plus 2 parametrized cases = 92 collected, confirmed with
`--collect-only`. Group coverage as reported: 8 canonicalisation · 13 malformed
shapes · 6 deadline boundary · 4 duplicate · 5 declared-vs-measured · 8 source
failure · 5 digest integrity · 7 authorisation · 9 challenge · 6 refund · 6
conservation · 11 panel/API boundaries.

**The mutation proof is the real deliverable.** Sixteen one-line mutations, each
producing a named test that went red. Regenerable via
`scripts/m4_mutation_proof.py`. This is the standard M3 failed to meet, and it is
what makes the green run meaningful rather than merely reported.

## The defects — three of them stranded money

| # | Defect | Consequence |
| --- | --- | --- |
| 1 | `committer_block` vs local `commit_block` | `NameError` on **every** successful freeze. `freeze_entry` had never worked. |
| 2 | `claim_payout` required `PENDING_FINALITY` — the state `_on_entry_finalized` exists to leave | **The winner could never be paid.** Pool stranded on a `CLOSED` programme that could not be cancelled. |
| 3 | Zero paths from an unavailable GitHub searched for `.py`, found none, recorded `FAIL` | **An outage disqualified an entrant**, twice, in two methods. |
| 4 | `claim_payout` only accepts closed; `cancel_program` sets `CANCELLED` | A denied challenge's **bond stranded**. |
| 5 | `AFTER_DEADLINE_WORK` evidence canonicalised as a URL, compared for equality against a 40-hex commit | The one ground a deterministic re-derivation can settle was **decorative**. |

Plus `get_entry` raising on an unfrozen entry (confirmed on chain:
`gen_call failed, code=-32000`) and `finalize_program` raising on any
unchallenged entry, which is the common case.

**Defect 2 is the one that matters most, and so is why it was invisible.**

`gltest` silently discards internal messages, so `EmitInternalMessage` never
dispatched, the finalization callback never ran, and the suite went green over a
contract that **could not pay anyone on chain**. A harness failure hid a dead
product.

This is the same failure class as the M3 audit that reported `methods that raise
at all: []` while 11 of 14 could revert — *the check cannot fail, so it certifies.*
Two milestones running, two independent instances. It is now the project's
recurring hazard and is recorded as such.

Note also defect 3's shape: **absence of evidence read as evidence of absence.**
That is precisely the error the product exists to prevent, appearing in the
product itself. Worth naming in the submission — it is the honest kind of
evidence that the problem is real.

## Your two contract changes — I accept both

**`claim_payout` guard now requires `PAYOUT_READY` instead of `PENDING_FINALITY`.**
Correct, and your rationale is the right argument: the callback's only job is to
leave the pre-finality state, so *requiring* that state makes the two-method split
meaningless. My original guard was the exact inverse of the flow it served.

**`cancel_program` now sweeps denied challenge bonds.** Necessary — it closes
defect 4. Both are one-line reverts if you would rather solve them differently.

**On reporting instead of stopping:** you were right to fix defect 2 and wrong to
do it silently. Leaving the payout path unreachable was not defensible, and the
instruction to report first was not a veto — it exists so a reviewer knows what
changed. Flagging and fixing is the correct response; the disagreement was
procedural, and it did not cost anything here.

## `genvm-lint check` — both halves pass

```
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: ContestReceipt
  Methods: 14 (6 view, 8 write)
```

Exit 0. **The SDK-validation half that hung at M3 is no longer unverified.**

## Honest gaps, all accepted

| Gap | Why it is acceptable |
| --- | --- |
| `validator_fn` never executes in direct mode | gltest runs the leader only. M1's 6/6 two-bucket convergence is the validator evidence, and it is real on-chain evidence. Noted, not hand-waved. |
| `freeze_entry` never ran against real GitHub | M6. **Defects 1, 3 and 5 were all in this path**, so M6 is where they get proven fixed on chain — which is exactly why M6 is not optional. |
| Payout has not moved real value | M6 step 10. Same reason. |
| Conservation uses our value model, not gltest's | Acknowledged. The model is explicit and the tie-split remainder is covered by a mutation. |
| Do not run with `-q` | Real and worth knowing: `-q` suppresses the summary line on this runner while the exit code stays correct, so it *looks* like a broken suite. `run_direct_tests.sh` encodes this. |

## Something the tests did not catch, that you should know

`get_program(0)` fails `gen_call failed (code=-32000)` while `get_program("0")`
returns the record — `program_id` is a `str`. I hit this during M3 review. The
direct tests now cover unfrozen-entry reads, so the defaulted accessor works, but
**the str/int distinction is a client-side concern and M5 must handle it.** It is
silent and looks like a broken view.

## Two open items before M5 can be the last mile

1. **Naming and hosting** — raised 2026-10-02, still open. The product has no
   name and no public home, and the Projects track requires a GitHub repository
   URL matching `^https?://github\.com/[^/]+/[^/]+/?$` as *required* evidence. The
   360/400 build had both. This blocks M8 submission and is tracked in
   `IMPLEMENTATION-PLAN.md` §12.
2. **The M6 demo repo set** — one healthy repo at a pinned SHA, one whose declared
   stack contradicts its tree, one with a post-deadline commit. Defect 5
   (`AFTER_DEADLINE_WORK` was decorative) makes step 5 more load-bearing than I
   planned: that ground must now actually resolve on chain.

## Next: M5

Real frontend. The app already throws on `Undetermined`/`Canceled` and renders
business and lifecycle state separately, so **rubric criterion 4 is right by
construction** — this milestone makes it real rather than structural.

Must include: `program_id` sent as a string; the receipt view with per-criterion
verdicts, the contested list, the challenge log with grounds and outcomes, the
accuracy block and the receipt digest; the `cancel_program` refund path; and
explorer deep-links for every transaction ID.