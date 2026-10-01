# M0 review — accepted with one correction

Reviewed: 2026-10-01. Verdict: **M0 gate passed with a gap. Proceed to M1.**

Reviewed against `IMPLEMENTATION-PLAN.md` §5 M0 and §9. Full record in
`state/reviews/2026-10-01-m0-env-pins/`, `docs/evidence/m0-2026-10-01.json`,
`docs/VERIFICATION.md`.

## What I independently re-verified

I did not accept the runner-hash finding on trust. I re-probed both hashes
against the live Studio-dev target myself:

| Runner hash | My result |
| --- | --- |
| `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` | **accepted** — schema derived, method `probe` |
| `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (what the current docs name) | **rejected** — `VM_ERROR: invalid_contract runner malformed` |

Also confirmed: `eth_chainId` → `0xf22d` = 61997; the stub's `source_sha256` in
the evidence matches the file on disk; `.gitignore` covers `.env` and `.venv`;
and a scan of every file outside `.env` found none of the three secret values in
your `.env`. `scripts/gl_env.py` refuses to load a key from `.env` and refuses
credential paths inside the checkout — enforced in code, and exercised.

**The published docs are wrong about the runner hash.** That is a real finding,
independently reproduced, and the report was right to flag it for a second pair
of eyes. Use `py-genlayer:5jycge4q8k…` on line 1 of the contract.

## The one correction: the linter exists

The report says `genvm-lint` and its variants are 404 on PyPI. The package is
named **`genvm-linter`** — with an *er*. I checked:

| Check | Result |
| --- | --- |
| PyPI `genvm-linter` | **HTTP 200**, latest 0.11.0, *"Fast validation and schema extraction for GenLayer intelligent contracts"* |
| `github.com/genlayerlabs/genvm-linter` | **HTTP 200** |
| Commit `28450e66…` (the 360/400 build's pin) | **HTTP 200**, still resolves |
| PyPI `genvm-lint` / `genvm_lint` / `gl-lint` | 404 — these names do not exist |

That build installed it from git, not PyPI:

```
genvm-linter @ git+https://github.com/genlayerlabs/genvm-linter@28450e665666300fc648dbe495110dfd0cb6a7b4
```

**Action, before or alongside M3:**

1. Add that pinned git line to `requirements-dev.txt`.
2. Run the linter on `contracts/m0_stub_probe.py`.
3. Replace the `unverified` row in `docs/VERIFICATION.md` with the real output,
   or keep it `unverified` if it still will not install.

Until then the "lints" half of the M0 gate stays **unverified** and the live
schema probe remains the weaker substitute. The report was right to label it
that way rather than claiming a pass — the *reason* was wrong, not the caution.

**Not a blocker for M1**, which writes no contract code.

## Three environment facts that will change how M3 is written

1. **Every deploy needs an estimated fee distribution.** Two attempts died with
   `FeesDistributionMissing`. `genlayer-py` 0.18.0 sends no `fees` argument and
   reports a bare "Transaction reverted"; 0.19.0rc2 names the error and is pinned.
   Call `client.estimate_fees_distribution()` on every deploy — as
   `scripts/m0_env_probe.py:293` already does.
2. **Receipt field names differ from the 360/400 build's.** 0.18.0's
   `wait_for_transaction_receipt` returns no `status_name` or `contract_address`
   at all; the full record uses `lifecycle.state`, `to_address`,
   `txExecutionResultName`. **Read the full transaction record after the wait,
   and never treat a missing key as a failure.** Anyone coding to the old
   `VERIFICATION.md` field names would produce silently-empty evidence. This is
   the concrete form of plan §4.2's re-read rule.
3. **`GENLAYER_EXPLORER_URL` in `.env` points at Bradbury, a different network.**
   Studio-dev is `https://explorer-studio-dev.genlayer.com` and returns 503
   intermittently. Use `scripts/gl_env.py`'s retrying probe.

## Publishing failures was the right call

The failed-deploy transactions, the fee-distribution diagnosis, the SDK
field-name break and the 0.18.0-vs-0.19.0rc2 comparison are all recorded with
transaction IDs. That is exactly the habit the 360/400 build's `VERIFICATION.md`
established, and it is what a reviewer will read. Keep doing it.

## Proceed to M1

M1 is the consensus spike: 3 real repositories, one subjective criterion, measure
whether validators converge. It writes no product code, so the linter question
does not gate it.

Two things to carry into M1:

- **M1's output decides M3.5, and M3.5 is optional.** If it will not converge,
  the product ships without it. Do not let the spike become a blocker.
- If the spike needs a contract on chain, it inherits the fee-distribution
  requirement from above.

Report back with the convergence number and the decided comparison mode, as the
handoff in `IMPLEMENTATION-PLAN.md` §11 specifies. Still no Portal submission.
