# M1 — consensus spike

Milestone 1 of `state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`
§5. **This wrote no product code.** `contracts/m1_panel_spike.py` is a throwaway
measurement instrument, not part of Contest Receipt.

## The answer

| | |
| --- | --- |
| **Convergence** | **6/6** — three real repositories, run twice, no `undetermined` |
| **Comparison mode** | **2-BUCKET**, bucket compared with zero tolerance |
| **Accepted bucket** | `CONSISTENT` on all six runs |
| **Rounds needed** | 0 on every run |
| **Wall clock** | 55.3 s – 69.0 s per run |

The mode follows the plan's own rule: 3/3 converged with nothing undetermined, so
proceed with the strict two-bucket comparison.

## The criterion

*Does the repository's own README, at the pinned commit, describe a working
product consistent with that commit?* `CONSISTENT` / `INCONSISTENT` /
`INCONCLUSIVE`. Only the bucket is consensus-critical; free-form reasoning is
stored and never compared, because a fuzzy band on prose would hide exactly the
disagreement the product exists to keep.

Inputs, all real public repositories at immutable commits, chosen for the spike
only and **not** the M6 demo set (the plan reserves that for a human decision):

- `genlayerlabs/genlayer-py@dd25ef7f…` — published SDK, substantive README
- `genlayerlabs/genlayer-js@1b7f50a3…` — the JS counterpart, different document
- `genlayerlabs/genlayer-docs@1cd8e2d1…` — a docs site, the shortest README

## Read this before relying on the number

1. **The discriminating bucket was never exercised.** All six runs answered
   `CONSISTENT`. `INCONSISTENT` is the case a jury is most likely to split on
   and the case the product actually cares about. The spike shows that
   2-bucket comparison does not *spuriously* split on a document everyone
   agrees about; it does not show that it *reliably* converges on a refuted
   claim. Closing this needs one repository whose declared stack contradicts its
   tree — which is M6's "Entry B" asset, so it needs the human repo decision.
2. **"Converged" is a bare 3-of-5 majority, not unanimity.** Every run's quorum
   was exactly 3 of 5 with 1–2 validators idle. One run (pass 1, `genlayer-py`,
   `0x58be9ed2…`) recorded `AGREE 3, DISAGREE 1, IDLE 1` and the network still
   accepted `CONSISTENT`. A 3-bucket mode would not have rescued that run: a
   `CONSISTENT`/`INCONSISTENT` split inside three buckets is still a split. This
   limits M3.5 rather than arguing against 2-bucket.
3. **Idle validators are normal.** 1–2 of 5 produced no result in every run. A
   "contested criteria" count must never be read as a count of validator
   objections.

## Consequence for M3.5

M1 did not fail, so M3.5 is not blocked — but the evidence supports shipping it
exactly as the plan framed it: optional, one criterion, unable to move money or
disqualify anyone. Caveat 1 is the reason to keep that framing.

## Environment facts M1 added

- **The published docs describe an API this runner does not have.** The
  equivalence-principle page now recommends `gl.vm.run_nondet_unsafe`. The std
  library the accepted runner loads
  (`py-lib-genlayer-std:kzr02ndm9et4qkmbqpq5djjt5sme2yt76n7sz1qbzax0knt6mam0`,
  read from that runner's own `runner.json`) exports `run_nondet` and
  `run_nondet_default` and **no** `run_nondet_unsafe`. Docs-current code would
  fail at runtime.
- **The AST linter passes code the node rejects.** `genvm-lint lint` reported
  `✓ Lint passed (3 checks)` on a contract the live schema probe rejected with
  `NameError: name 'u32' is not defined`. AST lint does not resolve names. Both
  checks are kept, for this reason.
- **A write method's return value is not in the transaction record's `data`.**
  That field holds the *input* calldata. The accepted result lives only in
  `consensus_data.validators[*].result`, base64-encoded in a format this SDK does
  not decode. The spike now records the accepted result in storage and reads it
  through `get_last_run`, so the headline bucket is read from the chain.

## Files

| Path | Role |
| --- | --- |
| `scripts/m1_consensus_spike.py` | deploys the spike, runs 3 repos, writes evidence after every step |
| `scripts/m1_aggregate.py` | computes the headline number and the caveats from the evidence files only |
| `contracts/m1_panel_spike.py` | the throwaway contract |
| `docs/VERIFICATION.md` | the live log |
| `docs/evidence/m1-2026-10-01*.json` | two passes, machine-generated |
| `docs/evidence/m0-2026-10-01.json` | the M0 gate record |

## Reproduce

```sh
set -a; . ./.env; set +a
.venv/bin/python scripts/m1_consensus_spike.py            # pass 1
.venv/bin/python scripts/m1_consensus_spike.py --label pass2
.venv/bin/python scripts/m1_aggregate.py                   # the reported figure
```

Redeploys from scratch each run. Studio-dev is temporary; `--address` reuses a
live deployment instead of redeploying. No Portal submission is involved.
