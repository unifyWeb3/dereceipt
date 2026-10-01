# Verification record — Contest Receipt

This file is a **live evidence log**. It must not claim completion before the
corresponding observation exists. Every row starts `pending`. A row becomes
`passed` only when its observation exists and is recorded, in
`docs/evidence/`, from reading the chain rather than from a claim in prose.

Status vocabulary:

- `pending` — not attempted, or attempted with no observation yet
- `passed` — the observation exists
- `failed` — the observation exists and the check did not pass
- `unverified` — the check cannot be run in this environment; stays listed
- `manual pass` — completed by a person, not observed by the agent

## Milestone status

| Milestone | Gate | Status |
| --- | --- | --- |
| M0 · environment and pins | stub deploys, reaches `Finalized` on chain 61997, schema derivable. **Partly unverified:** no local linter exists in this environment, so the "lints" half of the gate ran as a live schema probe and is recorded as `unverified` below | **passed with a gap** |
| M1 · consensus spike | measured convergence number, decided comparison mode | pending |
| M2 · repo skeleton | `npm run build` succeeds, stub `index.html` serves | pending |
| M3 · deterministic core | 9+ methods on the live probe, no `raise` in a payable method, no clock read sharing a method with a transfer. A lint step can only be claimed if a tool is found that runs | pending |
| M3.5 · bounded LLM criterion | optional; the product is complete without it | pending |
| M4 · direct tests | 45+ tests, pytest line pasted verbatim below | pending |
| M5 · frontend | build succeeds, real lifecycle, business and lifecycle state shown separately | pending |
| M6 · live run and evidence | steps 1–12 present, every tx `Finalized`, balance observed changing | pending |
| M7 · docs | a stranger can clone, deploy and reproduce without asking | pending |
| M8 · deploy, demo, submit | every link resolves; **submission is not authorized** | pending |

## M0 · environment and pins

Environment: Python 3.12.3, Node v22.23.2, npm 10.9.8,
`genlayer-py==0.19.0rc2`, `genlayer` CLI 0.40.0-rc.3.
Plan and handoff: `state/reviews/2026-10-01-hackathon-discovery/`.
M0 record: `state/reviews/2026-10-01-m0-env-pins/`.
Machine-generated evidence: [`docs/evidence/m0-2026-10-01.json`](evidence/m0-2026-10-01.json).
Reproduce with `scripts/m0_env_probe.py`, which reads secrets from the process
environment only and writes the JSON from its own observations. The evidence
file holds the most recent run; the deployments below are the full M0 history.

Re-running `scripts/m0_env_probe.py` redeploys the stub and overwrites the
evidence file, so the record shows the gate was reached repeatedly rather than
once.

### Stub deployments observed during M0

| # | Deploy transaction ID | Contract address | Lifecycle | Explorer |
| --- | --- | --- | --- | --- |
| 1 | `0xbce185bc616357922a0cc91d15747f48177cdf3a0f621e2bf55ff8d137e5fac1` | `0x6D1814d1cC14390B8E1DE5eBeBB3Ad6aa0397c1A` | `finalized`/`accepted` | 200 |
| 2 | `0x9ffc85e4f77de749bcfeffbed33621998d882c015e5578002fe56ba707b721ec` | `0x8e16517013D8989ECdd509296ab4170cFF7AFe4e` | `finalized`/`accepted` | 503, then 200 |
| 3 | `0x78625468273b9d375ed57a844de6abd02ef8bf524c33866f77b10bdf56699d91` | `0xfce3BBFeCD25cFc32bFB819f68dC0b8Cb12b0d13` | `finalized`/`accepted` | 200 |
| 4 | `0xd9121029480de010f73328cc85588ee07949aa1db6dbcecea15b77a972e3699a` | `0xCe8184167e121b68ea1d60246DaB1CFB63d45358` | `finalized`/`accepted` | 200 |

An earlier run also produced deploy
`0x0caa65940b3611f4460892d1f1b18e8da400502d1db92a973a7ee01c97b361f4` →
`0xD81B9cbd49D449bB36f4263BE0d1003bc2552f72`, `finalized`/`accepted`. It was
the first successful deployment, made by hand while resolving the fee problem
below, before the probe script existed. It is the proof that the fee
distribution was the whole obstacle.

| Check | Evidence | Status |
| --- | --- | --- |
| Runner hash probed against the live target, not copied | `gen_getContractSchemaForCode` on `https://studio-dev.genlayer.com/api`. `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` **accepted**, 1 method (`probe`). `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` — the hash in the published docs — **rejected**, `VM_ERROR: invalid_contract runner malformed` | passed |
| GenVM version observed on the live target | `v0.3.0-rc7-x86_64-linux-release`, parsed from the `genvm_log` the target attaches to the rejected-runner probe. Read from the target, not copied from a doc | passed |
| Chain identity | `eth_chainId` `0xf22d`, `net_version` `61997`, matching `GENLAYER_STUDIO_DEV_CHAIN_ID` | passed |
| Deployer identity and funding | key-derived address `0x3211d1419709682b81c53CC51cb63622E25488d3` equals `DEPLOYER_ADDRESS`; `eth_getBalance` ≈ 98.16 GEN, drifting slightly per run as fees are spent | passed |
| Stub contract derives a schema | `gen_getContractSchemaForCode` returns 1 method, `probe` | passed |
| Stub contract deploys and reaches `Finalized` | 5 stub deployments, every one `finalized`/`accepted` with `MAJORITY_AGREE` and `FINISHED_WITH_RETURN` in 31–38 s. Transaction IDs and addresses in the table above | passed |
| Address and transaction resolve on the explorer | `https://explorer-studio-dev.genlayer.com/address/0xCe81…` and `/tx/0xd912…` both HTTP 200 | passed |
| Studio-dev explorer is intermittent | 503 observed three times consecutively on a previous address, then 200 on a later retry. `probe_url` therefore retries up to 4 times and logs every attempt, so a 503 is recorded as a transport observation rather than as a missing page | passed |
| Secrets read from the environment only | `scripts/gl_env.py` reads `GENLAYER_PRIVATE_KEY` from the process environment and **refuses** to load it from `.env`; `assert_outside_checkout` refuses any credential path inside the checkout. Both guards were exercised: with the variable unset, `secret_value` raises rather than falling back to `.env`; and a run from a fully empty environment still refuses. No secret value appears in this file, in the evidence JSON, or in any log | passed |
| Local `genvm-lint` | **not available** in this environment, so the "lints" half of the M0 gate is unverified. Checked: `genvm`, `genvm-lint`, `genvm_lint`, `genlayer-lint` and `gl-lint` are all absent from PyPI (HTTP 404), and `genlayer` CLI 0.40.0-rc.3 has no lint subcommand. The substitute is the live `gen_getContractSchemaForCode` probe, which is a **weaker** check: it proves the node compiles the contract and derives a schema, not that a static analysis pass is clean. `genlayer-test` is the likely carrier of a local check and is not yet installed — M4 should test whether it runs without Docker | unverified |
| Docker | unavailable. Direct tests must not require it, and the docs say so plainly | unverified |
| `APP_DATABASE_URL` unused | present in `.env`, listed in the evidence file under `unused_by_design`, referenced by no code. The contract is the record | passed |

## Failed and superseded M0 observations

Published because a negative observation with transaction IDs is worth more to
a reviewer than a claim of success.

**1. The documented runner hash is rejected by this target.** Probing the hash
named in the current published docs returned `VM_ERROR: invalid_contract
runner malformed`. This is the drift the plan warned about, now measured rather
than assumed. The contract header must carry the accepted hash above.

**2. `deploy_contract` without a fee distribution reverts.** The first two
deploy attempts were rejected by the consensus contract with
`FeesDistributionMissing`:

- `0xe8343f2f1622654a27a1360f75234f1736e7866515e0b830ba56bb557caef186`
- `0x65a0303bb7a4c757090330ad94da3fadaca73247e0a15a2419f02be44a90f8b1`

Both reached the node with `status 0`, `gasUsed 0`, and no logs, so neither
produced a GenLayer transaction ID and neither can be read back as a contract
transaction. `scripts/m0_env_probe.py` now calls
`client.estimate_fees_distribution()` and passes the result to every deploy.

**3. A receipt's field names changed between SDK versions, and the return shape
is not self-describing.** With `genlayer-py` 0.18.0,
`wait_for_transaction_receipt` returned a simplified receipt with no
`status_name`, `contract_address` or `tx_execution_result` keys at all; those
names do not exist in that version. The full record reports them as
`lifecycle.state`, `to_address`, `txExecutionResultName`. The probe therefore
reads the transaction again after the wait and derives the lifecycle from
`lifecycle.state`, and never treats a missing key as a failure. This is the
concrete form of the rule that a record read before finalization still carries
in-flight consensus fields.

**4. `genlayer-py` 0.18.0 cannot deploy to this target; 0.19.0rc2 can.** The
0.18.0 call reverted with a bare `Transaction reverted` and no reason, and it
sent no fee distribution. 0.19.0rc2 adds the `fees` parameter and reports
`FeesDistributionMissing` by name, which is what identified the cause. Both
versions are pinned in `requirements.txt`; only 0.19.0rc2 is used.

**5. The SDK's `gen_getContractSchemaForCode` wrapper refuses non-localnet
chains.** `get_contract_schema_for_code` raises `Contract schema is not
supported on this network` for any chain that is not localnet. The probe
therefore calls the JSON-RPC method directly through the provider, which is
what the plan asked for in the first place.

## Evidence rules

Carried forward from the previously scoring 360/400 build, which is the right
set of rules.

- A submitted transaction is not a successful deployment until its status and
  execution result are inspected.
- An `ACCEPTED` result is not final settlement.
- A UI badge is not authoritative; the contract state, protocol receipt,
  explorer and balance are.
- Synthetic direct-test fixtures are test evidence only. The public demo must
  use real public inputs.
- Any unavailable check remains listed as **unverified** rather than being
  described as passed.
