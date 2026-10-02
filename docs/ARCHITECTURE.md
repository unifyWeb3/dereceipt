# DeReceipt architecture

**Status: M2 skeleton.** The contract does not exist yet — it is written at M3.
Everything below that describes the contract is the *specification being built
to*, not a description of running code. Where a decision has already been made
by measurement, the measurement is named, so a reviewer can check the claim
rather than take it on trust. `docs/VERIFICATION.md` is the live log and is the
authority on what has actually been observed.

## The problem this is built against

An AI-judged hackathon ends with a score, an announcement, and a runner-up who
says the panel was rigged. Nobody can check, because the jury's own
disagreement was thrown away. Three facts about a jury are observable on chain
and countable:

1. **Which criteria reached a verdict at all.** A criterion that ends
   `UNDETERMINED` is a criterion the jury visibly could not agree on.
2. **Whether a challenge succeeded.** An upheld challenge is direct, priced
   evidence that the original verdict was wrong.
3. **The cumulative overturn rate.** Derived by reading storage, per programme,
   forever.

The product is built on exactly those three. It is not built on an agreement
margin, because GenLayer does not persist validators' intermediate answers — the
accepted leader result is the only thing the contract receives, so a contract
**cannot** count how many agreed. Any design that reports that number is
reporting something it does not have.

## Boundary

```text
organiser publishes a programme (criteria snapshotted, pool locked)
    │
    ▼
builder submits a repository pinned to an immutable commit
    │  · the commit SHA is part of every evidence URL, so the read is
    │    point-in-time: the README cannot be changed without changing the SHA
    ▼
GenLayer Intelligent Contract (GenVM)
    │  stores the frozen evidence, the derived receipt, the challenge log
    │  enters a non-deterministic block only to fetch an authoritative source
    ▼
independent validator executions
    │  each validator re-derives the verdict from the same source
    │  and compares the decision field, not the prose
    ▼
consensus result written to contract state, readable through a view
    │  a finalization callback marks state; it moves no value
    ▼
losing entrant stakes a challenge against ONE named criterion
    │  a second pass re-reads that criterion only; neighbours stay byte-identical
    ▼
transfer in its own transaction, after finalization
    │  the contract balance decreasing is the proof, not the message
    ▼
programme's own overturn rate, derived from storage on read
```

## The deterministic / model split

This is inherited deliberately from the 360/400 reference build, whose contract
contains **zero** model calls. That is not an omission; it is the reason it
scored.

**Deterministic, over authoritative data. No model, so no dispute possible.**

| Check | Source | Rejects when |
| --- | --- | --- |
| `repo_resolves` | `api.github.com/repos/{o}/{r}` | non-200 → `UNDETERMINED`, never a rejection |
| `commit_resolves` | `api.github.com/repos/{o}/{r}/commits/{sha}` | **404** → disqualified; 403/429/5xx → `UNDETERMINED` |
| `commit_predates_deadline` | `commit.commit.committer.date` vs stored deadline | committer date ≥ deadline → **disqualified** |
| `tree_digest` | `…/git/trees/{sha}?recursive=1`, hashed | stored as the digest of the file manifest |
| `not_duplicate` | stored `tree_digest` set on the programme | digest already present → disqualified |
| `required_files_present` | the frozen manifest | `README.md` absent → disqualified |
| `declared_language_present` | frozen manifest vs declared stack | declares `typescript`, tree has no `.ts` → **claim refuted** |
| `demo_reachable` | the demo URL on an allow-listed host | 404 → disqualified; anything else → `UNDETERMINED` |

**Only a 404 is a business rejection.** A 403, 429, 5xx, empty body or non-JSON
is `UNDETERMINED`. Validators call `api.github.com` unauthenticated from their
own IPs, so rate limits are expected, and a rate limit must never be recorded as
a builder's fault.

**Optional, bounded, last: one subjective criterion.** M1 measured this. It is
M3.5, it may be cut without breaking anything, and it can label one criterion
and nothing else. It can never release funds, disqualify an entrant, or trigger
a refund.

`declared_language_present` covers most of "unsupported claim" deterministically
by checking the declared stack against the frozen tree, so the wedge does not
depend on the model existing at all.

## State model

Business state and GenLayer protocol state are separate by construction. This
is rubric criterion 4 and it is cheapest to make obviously true by never mixing
the two in one variable.

| Layer | Values |
| --- | --- |
| Programme | `OPEN`, `CLOSED`, `CANCELLED` |
| Entry | `SUBMITTED`, `UNDER_REVIEW`, `STANDING`, `DISQUALIFIED`, `PAYOUT_READY`, `PAID` |
| Criterion verdict | `PASS`, `FAIL`, `UNDETERMINED`, `INCONCLUSIVE` |
| Challenge | `FILED`, `UPHELD`, `DENIED`, `EXPIRED` |
| Transfer | `NOT_SCHEDULED`, `PENDING_FINALITY`, `TRANSFER_EMITTED` |
| GenLayer protocol | `PENDING`, `PROPOSING`, `COMMITTING`, `REVEALING`, `ACCEPTED`, `UNDETERMINED`, `FINALIZED`, timeouts, appeal states |

`ACCEPTED` is not finality. A transfer message being posted is not a payout; the
contract balance decreasing is the only proof of a payout.

## Hard rules the contract must obey

Each is a measured fact or a measured failure, not a preference.

1. **The contract runner is pinned and verified.** `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng`.
   The hash named in the published documentation is **rejected** by this target
   with `invalid_contract runner malformed`. M0 probed both against the live
   node. Never alias to `latest` or `test`.
2. **`gl.vm.run_nondet`, never `run_nondet_unsafe`.** The current
   equivalence-principle documentation recommends `run_nondet_unsafe`. The std
   library this runner actually loads exports `run_nondet` and
   `run_nondet_default` and no `run_nondet_unsafe`, so documentation-current
   code raises `AttributeError` at runtime. The second docs drift M1 found.
3. **Both checks run: `genvm-lint check` *and* the live schema probe.** The AST
   linter passed a contract the node rejected with `NameError: name 'u32' is
   not defined`; AST lint does not resolve names. The live probe is not the
   weaker check — it catches what the linter cannot.
4. **`raise` is forbidden in a method that received value — and so is a silent
   refusal.** A revert in a payable method strands that value. So does returning
   a refusal once the money has already arrived, which is less obvious and was
   the real M3 failure: `open_program` read the clock, the clock threw, a
   catch-all swallowed it, the transaction *finalized successfully*, 1000 GEN
   arrived, and no programme existed. `open_program` therefore **always** creates
   the programme row once value has arrived — invalid terms yield a `CANCELLED`
   programme with the pool locked, one `cancel_program` call from recovery — and
   the reason is stored so it is readable through a view. A refusal recorded
   nowhere is indistinguishable from a success.
5. **No clock read in a method that moves value — currently vacuous, and kept
   anyway.** Studio-dev's fee estimator runs on a badly stale clock, so combining
   the two reverts with `out_of message_fee total`. **Measured at M3: this runner
   has no usable clock at all.** `gl.vm.get_timestamp()` raises
   `SystemError: 2: inval` and is the only time accessor in the pinned std
   library. The contract reads no clock anywhere, which makes this rule *vacuous*
   rather than satisfied — a distinction worth being precise about. It is kept as
   a constraint, and `claim_payout` / `cancel_program` remain clock-free so the
   separation survives if a clock ever appears. The cost is that **arrival-time
   policy is not enforced by the contract**: a late submission is accepted, and
   the challenge window is recorded but not enforced. The deadline *guarantee* is
   unaffected and is the stronger form — see rule 10.
6. **Transfers use `gl.evm.contract_interface`.** The plain `on="finalized"`
   path produces receipts with `skipped=true` and the balance never moves. That
   was measured: a 22.6 GEN real balance against 4.7 GEN of books.
7. **Verdicts are stored and read through a view.** `record["data"]` is a
   write's *input* calldata; the accepted result lives only in
   `consensus_data.validators[*].result`, base64-encoded in a format this SDK
   does not decode. A verdict that cannot be read from contract state is not a
   verdict. The frontend reads views, never receipts.
8. **Criteria are snapshotted at `open_program`.** No setter, ever. A deadline,
   a weight and a criterion never change after open.
9. **The original verdict is never overwritten.** A challenge outcome is
   recorded *beside* it. The receipt is append-only.
10. **The deadline is proven by GitHub's clock, not the chain's.** The
    point-in-time guarantee — that the work existed before the rules closed — is
    `commit.committer.date` compared against the absolute deadline the organiser
    fixed at open. That is arithmetic every validator repeats, over a
    GitHub-signed timestamp no entrant can forge afterwards, and it needs no
    block clock. It proves *when the work existed*, which is the claim being
    made; what it does not prove is *when the transaction arrived*, and with no
    usable clock the contract cannot and does not claim to.
11. **Absence of evidence is never evidence of absence.** A criterion the jury
    could not settle is `UNDETERMINED`, and it does not disqualify. This applies
    in both directions and at every layer: a non-404 from GitHub, a 200 whose
    body cannot be parsed, and a manifest that came back empty are all *no
    observation*, and none of them may be turned into a `FAIL`. M4 found two
    places where they were — a language check that searched zero paths and
    reported "absent", and a tree read that reported "readme absent" for a
    repository nobody managed to read. Both would have disqualified an entrant
    because GitHub was having a bad day, which is the exact failure this product
    exists to prevent.
12. **A view must be safe in every state the contract can reach.** `TreeMap`
    raises `KeyError` for an unwritten key, which means a view that reads a field
    nothing has written yet fails rather than reporting its absence — and the
    most common state there is, "submitted but not yet frozen", had no verdict to
    read. Views read through a defaulted accessor and say `NOT_JUDGED`; write
    paths index directly, so a genuine write-before-read bug still surfaces.
13. **Money moves only after finality is observed, in one direction.**
    `finalize_program` schedules a payout, `_on_entry_finalized` records that
    finality was seen, and only then may `claim_payout` schedule the transfer.
    Each of the three states is distinct and the order is not negotiable: M4
    found `claim_payout` guarding on the pre-finality state, which made the
    whole path unreachable on chain and stranded the pool.

## A contested criterion is not a validator objection

M1 measured that **1–2 of 5 validators were idle in every single run**, and one
run recorded `AGREE 3, DISAGREE 1, IDLE 1` and was still accepted.

So a criterion that ends `UNDETERMINED` means *the jury could not settle this*.
It does **not** mean *N validators objected*, and the two must never be shown as
the same number. The interface keeps "this criterion is contested" separate from
any vote tally, and `docs/VERIFICATION.md` labels the distinction every time it
appears. Idle validators are normal, not an incident.

## Deliberate exclusions

Binding. A narrow, finished, honest slice beats a broad, unfinished one, and a
rejected submission costs one of two weekly slots.

- No general "bring your own rubric" configurator. Three to five fixed criteria,
  integer weights, snapshotted at open.
- No multi-round scoring, judge portal, ceremony mode or analytics dashboard.
  That is a different product and not the trust problem.
- No reputation system for judges or entrants.
- No DAO governance, committee voting or multi-sig.
- No cross-chain support, no indexer, **no off-chain database.** The contract is
  the record; a second source of truth reads as an off-chain dependency.
- No general-purpose oracle. This contract answers one workflow.
- **No model authority over any objective predicate, ever.** The preferred
  outcome is no model in the decision path at all.
- No real-value or stablecoin settlement. Studio-dev GEN has no monetary value
  and the docs must say so plainly.
- No persistence assumption. Studio-dev resets; the demo is re-runnable from
  scratch.

## Not yet built

Honest inventory, so nothing here reads as a claim:

| Piece | Milestone | State |
| --- | --- | --- |
| The contract | M3 | not written |
| The optional subjective criterion | M3.5 | optional; measured, not built |
| Direct tests | M4 | not written |
| The real interface | M5 | skeleton only |
| Live run and evidence | M6 | not run |
| The `INCONSISTENT` bucket | M6 | **never exercised** — see below |

**The one substantive gap in the M1 measurement.** All six M1 runs answered
`CONSISTENT` on three same-organisation repositories with honest READMEs. The
`INCONSISTENT` bucket — the case a jury is most likely to split on, and the one
the product cares about — was never reached. The spike shows a 2-bucket
comparison does not *spuriously* split on an easy document. It does not show that
it *reliably* converges on a refuted claim. That stays open until M6 has a
repository whose declared stack contradicts its tree.
