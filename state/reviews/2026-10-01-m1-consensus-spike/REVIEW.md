# M1 review — accepted

Reviewed: 2026-10-01. Verdict: **M1 gate met. Proceed to M2.**

Evidence: `docs/evidence/m1-2026-10-01.json`, `…-pass2.json`,
`state/reviews/2026-10-01-m1-consensus-spike/aggregate.txt`, commit `c7aa0cc`.

## Independently re-verified

I re-ran the aggregate and re-derived the numbers from the raw evidence rather
than reading them off the summary:

| Claim | My result |
| --- | --- |
| Convergence 6/6, two passes, 3 repos each | confirmed — 6 runs, 0 undetermined |
| Bucket read from contract storage, not a receipt | confirmed — `bucket_source: contract storage, read via get_last_run` |
| Every run `AGREE 3` | confirmed, per-run votes re-extracted from the raw JSON |
| 1 DISAGREE on pass-1 `genlayer-py` `0x58be9ed2…` | confirmed — `{"AGREE":3,"DISAGREE":1,"IDLE":1}` |
| Idle 1–2 every run | confirmed — pass 2 shows `IDLE 2` on all three |
| `genvm-lint` now installed | confirmed — `genvm-lint, version 0.11.1-rc.2`; I ran it against `contracts/m1_panel_spike.py` myself: **✓ Lint passed (3 checks) / ✓ Validation passed / Methods: 2** |
| Tree clean, `.env` untracked, key only in `.env` | confirmed |

## The three caveats are the most valuable part of the report

The gate is met literally, and writing down what it does *not* establish is
exactly what the 360/400 build's `VERIFICATION.md` did. Specifically recorded as
a **failed** row rather than hidden:

**`INCONSISTENT` was never exercised.** All six runs answered `CONSISTENT` on
three same-organisation repos with honest READMEs. So the spike proves 2-bucket
does not *spuriously split* on an easy document; it does not prove it converges
on a **refuted** claim — the case the product cares about. Correct call not to
invent a fake input. This is now a dependency on the M6 repo decision, not a
spike defect.

**"Converged" is a bare 3-of-5, not unanimity.** Verified. And the reasoning
that a 3-bucket mode would not have rescued `0x58be9ed2…` is right: a
`CONSISTENT`/`INCONSISTENT` split inside three buckets is still a split. That
argues *against* switching mode, and M3.5 is unaffected.

**Idle validators are the norm.** 1–2 of 5 in every run. Carried forward as a
hard design constraint: **M3 must not present a "contested criteria" count as a
count of validator objections.** A criterion the jury cannot settle stays on the
record — which is the product's own framing and survives this — but the two are
not the same number.

## Three environment findings, all actionable

1. **The published docs describe an API this runner does not have.** The
   equivalence-principle page recommends `gl.vm.run_nondet_unsafe`; the accepted
   runner's own `runner.json` exports `run_nondet` and `run_nondet_default` and
   no `run_nondet_unsafe`. Docs-current code would `AttributeError` at runtime.
   **`contracts/m1_panel_spike.py:213` uses `gl.vm.run_nondet` — correct for this
   runner.** M3 must do the same. Second confirmation today that the docs have
   drifted from the live target.
2. **The AST linter passes code the node rejects.** `genvm-lint` reported clean
   on a contract the live schema probe killed with
   `NameError: name 'u32' is not defined` — AST lint does not resolve names. This
   corrects my M0 review: I called the live probe "the weaker substitute." It is
   **not** weaker; it caught a real defect the linter missed. **M3 runs both.**
3. **`record["data"]` is a write's input calldata, not its return.** The accepted
   result lives only in `consensus_data.validators[*].result`, base64, in a format
   this SDK does not decode. Hence the spike writes its result into storage and
   reads it via a view. **This is the pattern the whole product must follow** —
   the headline verdict must be readable from the chain, never decoded from a
   receipt. It also means the frontend must read views, not receipts, to show a
   verdict.

## On the process notes

`--skip-deploy` overwrote the passing M0 evidence with a not-evaluated one. You
caught it, restored from the archive, and made the script refuse to do it. That
is the right response — and it is exactly the class of bug that would have made
M6's evidence file quietly empty.

Excluding the superseded 1-method deployment `0x3a09a3fc…` and its three
converged runs was also right. They are valid convergence evidence but the
buckets are not reliably readable, so counting them would have made the headline
number larger and the evidence weaker. **6/6 with readable verdicts beats 9/9
with three unreadable.**

## Carry into M3

- Contract runner `py-genlayer:5jycge4q8k…`, and **`gl.vm.run_nondet`**, not
  `run_nondet_unsafe`.
- **Run both checks:** `genvm-lint check` *and* `gen_getContractSchemaForCode`
  over raw JSON-RPC. The linter is no longer optional.
- Verdicts must be readable **via a view**, not from a receipt.
- A criterion that ends `undetermined` is "the jury could not settle this." Never
  label it a count of validator objections.
- The clock/transfer separation and the `raise`-in-payable prohibition from the
  plan still bind.

## Proceed to M2

Repo skeleton: `frontend/` (Vite + vanilla JS + `genlayer-js@2.0.0-rc.1` +
`viem`), `tests/direct/`, `docs/ARCHITECTURE.md`, `gltest.config.yaml`,
`scripts/deploy_studio_dev.py`, `.env.example`, `README.md`, `LICENSE`.

Gate: `npm run build` succeeds and a stub `index.html` serves. M2 writes no
contract code. Report back and stop — M3 is where the real work starts.
