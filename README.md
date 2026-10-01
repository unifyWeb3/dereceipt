# Contest Receipt

**Auditable verdicts for AI-judged hackathons and grant rounds.**

Every AI-judged hackathon ends with a score, an announcement, and a runner-up
who says the panel was rigged. Nobody can check, because the jury's own
disagreement was thrown away. Contest Receipt keeps it.

A builder submits a repository pinned to an immutable commit. The contract
freezes that evidence and derives a receipt from it. A losing entrant can stake
a challenge against **one** named criterion, and the second pass re-reads that
criterion only — the neighbouring criteria stay byte-identical. The programme
publishes its own overturn rate, derived from storage on read, forever.

> **Status: under construction.** The repository skeleton, the environment pins
> and a consensus measurement are done. **The contract is not written yet** — it
> is M3. `docs/VERIFICATION.md` is the live evidence log and is the authority on
> what has actually been observed; nothing in this README is a claim that has
> not been measured. Read that file before trusting anything below.

## What it does

1. **The organiser publishes a programme.** Three to five fixed criteria, an
   integer weight each, a deadline, and a pool. Criteria are snapshotted onto
   the programme at that moment. There is no setter, ever.
2. **A builder submits a repository** at a pinned commit, with a declared stack
   and a demo URL.
3. **The contract freezes the evidence** and derives a receipt: the tree digest
   of the file manifest, and the commit's committer date. The commit SHA is part
   of every evidence URL, so the read is point-in-time — a README cannot be
   polished into existence after the deadline, because changing it changes the
   SHA, which changes the URL.
4. **A challenge is possible.** A losing entrant stakes a bond against one named
   criterion and attaches new evidence. The original verdict is never
   overwritten; the outcome is recorded beside it.
5. **The programme publishes its own accuracy record**: entries, criteria that
   ended contested, challenges filed and upheld, and the overturn rate.

## Why the receipt is different

From 219 published GenLayer projects, five capabilities are empty:

| Capability | Competitors |
| --- | --- |
| Verdict anchored to a point in time, not judging time | **0 / 219** |
| Declared claim checked against the actual artifact | **0 / 219** |
| Publishes an agreement / consensus / overturn statistic | **0 / 219** |
| Contested criteria kept on the public record | **0 / 219** |
| Any refund path on cancellation | 0 / 219 |

The three deterministic checks that carry the wedge are arithmetic over
authoritative sources, and a model has no authority over any of them:

- **`commit_predates_deadline`** — `committer.date` against the stored deadline.
  A point-in-time proof the work existed before the rules closed, signed by
  GitHub and unforgeable after the fact.
- **`declared_language_present`** — the declared stack checked against the frozen
  tree. An entrant who declares `typescript` in a repository containing no `.ts`
  is refuted by the artifact, not by opinion.
- **`not_duplicate`** — a repeated `tree_digest` across the programme is refused.

**Only a 404 from a source is a business rejection.** A 403, 429, 5xx, empty
body or non-JSON is `UNDETERMINED`, never a failure. Validators call
`api.github.com` unauthenticated from their own machines, so rate limits are
expected, and a rate limit is never recorded as a builder's fault.

## Running it

Requires Python 3.12+ and Node 20+.

```sh
# Python side
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Frontend
cd frontend && npm install && npm run build
```

Secrets come from the **process environment only**. `scripts/gl_env.py` refuses
to load a private key from `.env` and refuses to write credential material
inside the checkout. `.env.example` holds public configuration only.

### Environment verification (M0)

```sh
set -a; . ./.env; set +a
.venv/bin/python scripts/m0_env_probe.py
```

Probes the contract runner against the live target, deploys a one-method stub,
and writes `docs/evidence/m0-<date>.json`. Exit code 0 means the gate passed.

### Deploying

```sh
.venv/bin/python scripts/deploy_studio_dev.py --contract contracts/contest_receipt.py
.venv/bin/python scripts/deploy_studio_dev.py --contract contracts/contest_receipt.py --dry-run
```

`--dry-run` lints and probes the schema without sending a transaction. A
submitted transaction is not a deployment until its lifecycle and execution
result have been read; the script exits non-zero if the transaction did not
reach `finalized`.

### Measuring the jury (M1)

```sh
.venv/bin/python scripts/m1_consensus_spike.py
.venv/bin/python scripts/m1_aggregate.py
```

## What is measured so far

| Milestone | Gate | Status |
| --- | --- | --- |
| M0 environment and pins | stub deploys, reaches `Finalized` on chain 61997, `genvm-lint check` clean | **passed** |
| M1 consensus spike | convergence number, decided comparison mode | **passed** — 6/6, 2-bucket |
| M2 repo skeleton | `npm run build` succeeds, a stub `index.html` serves | **passed** |
| M3 the contract | 9+ methods on the live probe, both checks clean | not started |
| M3.5 optional model criterion | cuttable without breaking anything | not started |
| M4 direct tests | 45+ tests, pytest line pasted verbatim | not started |
| M5 frontend | real lifecycle, business and lifecycle state shown separately | not started |
| M6 live run and evidence | every tx `Finalized`, contract balance observed changing | not started |
| M7 docs | a stranger can clone and reproduce without asking | not started |
| M8 deploy, demo, submit | every link resolves | **submission is not authorized** |

Three findings worth knowing before reading the code, each measured rather than
assumed:

- **The published documentation names a runner hash this network rejects.**
  `py-genlayer:1jb45aa8ynh…` returns `invalid_contract runner malformed` on
  Studio-dev. The hash in the contract header is
  `py-genlayer:5jycge4q8k…`, verified by probing the live node.
- **The same documentation recommends an API this runner does not export.**
  It says to use `gl.vm.run_nondet_unsafe`; the std library this runner loads
  has `run_nondet` and `run_nondet_default` and no `run_nondet_unsafe`.
- **`genvm-lint` passes code the node rejects.** The AST linter does not resolve
  names — it passed a contract that failed at load with
  `NameError: name 'u32' is not defined`. Both checks run, because each catches
  what the other cannot.

## Honest limits

- **Studio-dev is a temporary network.** Contracts there can vanish without
  notice. Nothing in this repository treats a Studio-dev address as durable, and
  the demo is designed to be re-runnable from scratch.
- **Test GEN has no monetary value.** This is not real-value settlement and does
  not claim to be.
- **The `INCONSISTENT` bucket has never been exercised.** All six M1 runs
  answered `CONSISTENT` on three same-organisation repositories with honest
  READMEs. The spike shows a 2-bucket comparison does not *spuriously* split on
  an easy document. It does **not** show that it reliably converges on a refuted
  claim, which is the case the product cares about. That gap stays open until the
  live run has a repository whose declared stack contradicts its tree.
- **A contested criterion is not a count of validator objections.** 1–2 of 5
  validators were idle in every M1 run, and one run was accepted on
  `AGREE 3 / DISAGREE 1 / IDLE 1`. "The jury could not settle this" and "N
  validators objected" are different claims and are never shown as one number.
- **The browser wallet flow is user-driven.** The desktop browser tool was
  unavailable during development, so any wallet result must be recorded as
  `user_reported_manual_browser_plus_independent_explorer_check` — never as an
  agent-observed one, and never with a simulated provider substituted for a real
  wallet.

## Repository layout

```text
contracts/          the Intelligent Contract (M3) and the M0/M1 probes
frontend/           Vite + vanilla JS + genlayer-js + viem, no framework
tests/direct/       direct tests, no Docker and no network (M4)
docs/ARCHITECTURE.md the boundary, the deterministic/model split, the rules
docs/VERIFICATION.md  the live evidence log; every row starts `pending`
docs/evidence/      machine-generated observations, read back from the chain
scripts/            the probes, the deploy path and the gates
gltest.config.yaml  direct-test configuration, with the deliberate version pins
```

## Evidence rules

These bind every claim in this repository, and they are the rules the
previously scoring reference build used:

- A submitted transaction is not a successful deployment until its status and
  execution result are inspected.
- An `ACCEPTED` result is not final settlement.
- A UI badge is not authoritative; the contract state, protocol receipt,
  explorer and balance are.
- A verdict must be readable from contract state through a view. It is never
  decoded out of a consensus receipt.
- Synthetic fixtures are test evidence only. The public demo must use real
  public inputs.
- Any unavailable check stays listed as **unverified** rather than being
  described as passed.
- Publish failures. A negative observation with transaction IDs is worth more
  than a paragraph claiming success.

## License

MIT. See [`LICENSE`](LICENSE).
