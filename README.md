# DeReceipt

**Auditable verdicts for AI-judged hackathons and grant rounds.**

When an AI jury judges a hackathon entry, the losing side has no way to find out
why. DeReceipt keeps the reasoning, the evidence and the disputes — and publishes
the programme's own overturn rate.

- **Live interface:** **https://dereceipt.vercel.app** — a receipt is shareable
  by URL, e.g. `https://dereceipt.vercel.app/program/0/entry/0`
- **Contract:** [`contracts/contest_receipt.py`](contracts/contest_receipt.py) — an
  [Intelligent Contract](https://docs.genlayer.com) on GenLayer Studio-dev,
  deployed at `0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D` (chain 61997)
- **Interface source:** [`frontend/`](frontend/) — vanilla ES modules, no
  framework, no database, no backend
- **Architecture and the hard rules:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **What has actually been observed:** [`docs/VERIFICATION.md`](docs/VERIFICATION.md)

---

## The problem

A hackathon judged by a model produces a score and a winner. It does not produce
anything a loser can check. Three things usually go wrong, and all three are
worse when nobody can see them:

1. **The reasoning is discarded.** A builder is told `6/10` with no indication of
   which criterion failed or on what evidence.
2. **An outage is indistinguishable from a verdict.** GitHub rate-limits every
   validator at once. If "we could not read the repository" is recorded as "the
   repository does not exist", then the contest's outcome depends on GitHub's
   availability, and a builder is eliminated for someone else's outage.
3. **A dispute has nowhere to go.** If you think the jury was wrong, there is no
   procedure, no record, and no way to show what you would have seen instead.

## What this does instead

- **Evidence is frozen at the moment of judgement.** The commit, the manifest
  and GitHub's signed `committer.date` are read from the API and committed on
  chain. Every criterion records the observation that produced it.
- **Only a 404 is a rejection.** A 403, a 429, a 5xx, an empty body or a
  non-JSON body is `UNDETERMINED` — recorded, and it does not disqualify anyone.
  The absence of evidence is not evidence of absence.
- **There is no model in the decision path.** Every criterion is arithmetic over
  facts fetched from GitHub, re-derived independently by each validator under
  the equivalence principle. A fact is a fact; a model has no authority over one.
- **Disputes are a feature, not an escape hatch.** One challenge per entry,
  staked with a bond, against one named criterion. The contract re-derives that
  criterion deterministically on chain. The original verdict is never
  overwritten — the outcome is recorded *beside* it, which is why the receipt
  contains the challenge log and there is no separate `get_challenge` view.
- **The rubric is fixed and snapshotted.** Five criteria, no custom rubric and no
  subjectivity. The snapshot is fixed when the programme opens, so a builder
  knows before submitting what is being judged.
- **The programme publishes its own accuracy.** Entries, unsettled criteria,
  deterministically disqualified entries, challenges filed and upheld, and the
  overturn rate — all readable from `get_accuracy`, with the two counters kept
  separate so an outage cannot inflate a disqualification rate.
- **The receipt has a digest.** `get_receipt_digest` is a SHA-256 over the
  programme's whole audit record in canonical JSON with sorted keys. Re-ordering
  the record cannot change it; changing the record must. An organiser can prove
  months later that the record they published is the record the chain holds.

## The interface

Four views, hash-routed, no framework:

| route | what it is for |
| --- | --- |
| `/` | the product claim, backed by the live receipt it has actually produced |
| `/open` | the organizer path — open a programme, pick the rubric, lock the pool |
| `/program/0` | business state, the accuracy block, the digest, the organizer controls |
| `/program/0/entry/1` | one receipt, shareable by URL |

Legacy `#/…` links are still accepted, so an old bookmark lands somewhere.

Reading needs no wallet. Only a write does, and the app never holds a key.

**Two regions are kept visibly separate on every view** — contract business state
and the GenLayer protocol lifecycle — because they are different layers and
merging them makes `ACCEPTED` look like settlement. Only `FINALIZED` moves value.

`UNDETERMINED` has its own styling and is never rendered as an error. A jury that
could not settle a criterion is the product working.

## Running it

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # -> dist/
```

The deployed contract address is a public build variable with a working default:

```bash
VITE_CONTRACT_ADDRESS=0xYourAddress npm run build
```

GenLayer Studio-dev **resets periodically**. After a reset the default address
holds no contract and the interface says so plainly rather than rendering an
empty dashboard that looks like a product with no data.

## Verifying it

```bash
.venv/bin/python scripts/m5_gate.py          # 33 checks, including live reads
bash run_direct_tests.sh                     # 92 tests, 16 mutation proofs
.venv/bin/python scripts/m4_mutation_proof.py
GENVM_VERSION=v0.6.0-rc5 .venv/bin/genvm-lint check contracts/contest_receipt.py
```

`scripts/m5_gate.py` runs the *actual shipped modules* against the live chain via
an SSR build, so the read paths are exercised as the browser exercises them. See
[`docs/VERIFICATION.md`](docs/VERIFICATION.md) for what each check observed.

## What is deliberately not here

- **No database and no backend.** Every read is a contract view. There is
  nothing to run and nothing to sign up for.
- **No model in the decision path.** A bounded subjective criterion is a later,
  optional milestone. The product is complete and defensible without it.
- **No custom rubric.** Criteria come from a fixed set of five.
- **No block clock.** This runner exposes none. The deadline is proven by
  comparing GitHub's signed committer date against an absolute unix second — it
  proves *when the work existed*, which is the claim being made, and it does not
  claim when the transaction arrived.

## Licence and attribution

Built on [GenLayer](https://genlayer.com). See `docs/ARCHITECTURE.md` for the
design, including the thirteen hard rules the contract obeys.