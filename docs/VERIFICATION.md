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
| M0 · environment and pins | stub deploys, reaches `Finalized` on chain 61997, schema derivable, `genvm-lint check` clean | **passed** |
| M1 · consensus spike | measured convergence number, decided comparison mode | **passed** — 6/6 converged, 2-bucket. Read the caveats before relying on it |
| M2 · repo skeleton | `npm run build` succeeds, stub `index.html` serves | **passed** |
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
M1 record: `state/reviews/2026-10-01-m1-consensus-spike/`.
M2 record: `state/reviews/2026-10-01-m2-repo-skeleton/`.
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
| Local `genvm-lint` | **closed.** The package is `genvm-linter`, with an "er"; the M0 report searched for names that do not exist. Installed from the 360/400 build's exact commit, `28450e665666300fc648dbe495110dfd0cb6a7b4`, pinned in `requirements-dev.txt`. `genvm-lint check contracts/m0_stub_probe.py` → `✓ Lint passed (3 checks)` / `✓ Validation passed` / `Contract: M0StubProbe` / `Methods: 1 (1 view, 0 write)`, exit 0. The first attempt failed with `Failed to load SDK: The read operation timed out` until `genvm-lint download` fetched the 310 MB GenVM v0.6.0-rc7 artifact | passed |
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

**6. The published SDK documentation describes an API this runner does not
have.** The equivalence-principle page now recommends
`gl.vm.run_nondet_unsafe` for custom leader/validator patterns. The std library
this runner actually loads — `py-lib-genlayer-std:kzr02ndm9et4qkmbqpq5djjt5sme2yt76n7sz1qbzax0knt6mam0`,
read from the accepted runner's own `runner.json` — exports `run_nondet` and
`run_nondet_default` and **no** `run_nondet_unsafe`. Code written to the
current docs would fail at runtime with an `AttributeError`. The spike uses
`run_nondet`, which is what the 360/400 build used and what exists.

**7. The AST linter passes code the node rejects.** `genvm-lint lint
contracts/m1_panel_spike.py` reported `✓ Lint passed (3 checks)` for a contract
that the live schema probe rejected with
`NameError: name 'u32' is not defined` — the storage annotation needed
`gl.u32`. AST lint does not resolve names. The live
`gen_getContractSchemaForCode` probe is not a weaker check in every respect: it
caught a real defect the linter passed. Both are kept.

**8. A write method's return value is not readable from the transaction
record's `data` field.** `record["data"]` carries the transaction's *input*
calldata (`{"":"run_panel","args":[...]}`), not its return. The accepted result
appears only inside `consensus_data.validators[*].result`, base64-encoded in the
network's compact calldata format, which this SDK version does not decode — a
targeted scan is needed and is labelled a heuristic where used. The fix was to
record the accepted result in contract storage and read it through a view, so
the headline bucket is read from the chain rather than decoded from a receipt.

**9. A superseded M1 deployment, kept for the record.** The first spike was a
single-method contract that only returned its result, which is finding 8 above.
It deployed as `0x3a09a3fc…` → `0x8129D483EbEb965692e3f617CE527c2D3512e083`,
`finalized`, and its three runs — `0xc894fcdc…`, `0x7813945c…`,
`0x6587d954…` — all reached `finalized`/`accepted`. Those runs **are** valid
evidence that the jury converged, but their buckets are not reported, because
the contract did not record them and the receipt alone is not reliably
decodable. They are excluded from the 6/6 figure rather than counted on the
strength of a receipt the tooling cannot read. Counting them would have made the
number larger and the evidence weaker.

## M1 · consensus spike

Machine-generated evidence: [`m1-2026-10-01.json`](evidence/m1-2026-10-01.json)
and [`m1-2026-10-01-pass2.json`](evidence/m1-2026-10-01-pass2.json).
Aggregate, computed from those files and nothing else:
`scripts/m1_aggregate.py`. Record: `state/reviews/2026-10-01-m1-consensus-spike/`.

**This wrote no product code.** `contracts/m1_panel_spike.py` is a throwaway
measurement instrument with one method that asks one question, and it is not
part of Contest Receipt.

The criterion: *does the repository's own README, at the pinned commit, describe
a working product consistent with that commit?* The answer is one of
`CONSISTENT` / `INCONSISTENT` / `INCONCLUSIVE`, compared with **zero tolerance**.

| Check | Evidence | Status |
| --- | --- | --- |
| Convergence number | **6/6** across two independent passes — 3 real repositories twice. No run ended `undetermined` | passed |
| Decided comparison mode | **2-BUCKET**, by the plan's §5 rule: 3/3 converged, so proceed with the strict two-bucket comparison | passed |
| Accepted bucket | `CONSISTENT` on all 6 runs, read from contract storage via `get_last_run` | passed |
| Rounds needed | 0 on every run. No leader rotation, no second round | passed |
| Wall clock | 55.3 s – 69.0 s per run | passed |
| Spike deploys and finalizes | pass 1 deploy `0xb8a5ef71…` → `0x4Fa38687…`; pass 2 deploy `0xe8c91bf8…` → `0xA8AfD9f7…`. Both `finalized`, both addresses HTTP 200 on the explorer. `run_panel` calls: pass 1 `0x58be9ed2…`, `0x025beab9…`, `0xe158c88c…`; pass 2 `0x06636418…`, `0xd78c997c…`, `0x6604e08e…` | passed |
| Spike lints and validates | `genvm-lint check contracts/m1_panel_spike.py` → `✓ Lint passed (3 checks)` / `✓ Validation passed` / `Contract: M1PanelSpike` / `Methods: 2 (1 view, 1 write)`, exit 0. The live schema probe independently derives the same 2 methods | passed |
| `INCONSISTENT` bucket exercised | **no.** Every input was a GenLayer repository with an honest README, so every run answered `CONSISTENT` | **failed — see below** |
| Rotation / retry under disagreement | **no.** No run ever disagreed at the network level | **unverified** |

### What this measurement does not establish

The gate is met literally, and the number should not be read as stronger than it
is.

1. **The discriminating bucket was never tested.** `INCONSISTENT` is where a
   jury is most likely to split, and it is the case the product actually cares
   about. All six runs answered `CONSISTENT` on three repositories from the same
   organisation with honest READMEs. So the spike shows that 2-bucket comparison
   does not *spuriously* split on a document everyone agrees about; it does not
   show that it *reliably* converges on a refuted claim. The cheapest way to
   close this is one repository whose declared stack contradicts its tree —
   which is M6's "Entry B" asset, so it needs the human repo decision rather
   than a guess here.
2. **"Converged" means a bare 3-of-5 majority, not unanimity.** Every run's
   quorum was exactly 3 of 5, with 1–2 validators idle. One run — pass 1 on
   `genlayer-py`, transaction `0x58be9ed2…` — recorded
   `AGREE 3, DISAGREE 1, IDLE 1`, and the network still accepted `CONSISTENT`.
   A three-bucket mode would not have helped that run either: a
   `CONSISTENT`/`INCONSISTENT` disagreement inside three buckets is still a
   disagreement. This is a real limit on M3.5, not a reason to reject 2-bucket.
3. **Idle validators are the norm, not the exception.** 1–2 of 5 failed to
   produce a result in every single run. Any design that assumes a full jury
   answers is wrong. The product's own framing survives this — a criterion the
   jury cannot settle stays on the record — but a "contested criteria" count
   must not be read as a count of validator objections.

### Consequence for M3.5

M1 did not fail, so M3.5 is **not** blocked. But the evidence supports shipping
it as the plan always intended: optional, one criterion, able to label nothing
that moves money. Caveat 1 is the reason to keep that framing — a jury that
converges on the easy case says little about the hard one.

## M2 · repo skeleton

Machine-generated evidence: [`m2-frontend-gate-2026-10-01.json`](evidence/m2-frontend-gate-2026-10-01.json).
Reproduce with `scripts/m2_frontend_gate.py`, which runs the build, asserts the
built artefacts, and starts the preview server itself. Record:
`state/reviews/2026-10-01-m2-repo-skeleton/`.

**No contract code in this milestone.** `contracts/contest_receipt.py` does not
exist; `scripts/deploy_studio_dev.py` says so plainly instead of failing
cryptically.

| Check | Evidence | Status |
| --- | --- | --- |
| `npm run build` succeeds | exit 0, `vite v6.4.3`, 454 modules, `✓ built in 1m 2s` | passed |
| Built `index.html` references hashed assets | `assets/index-*.js`, `assets/index-*.css`, both present on disk | passed |
| Built bundle carries the pinned target | chain `61997` and `https://studio-dev.genlayer.com/api` both found in the bundle | passed |
| No key material in `dist/` | the environment's real key value scanned against every JS asset — clean | passed |
| The built page actually serves | `vite preview` → HTTP 200, app shell and `<title>Contest Receipt` present, hashed asset referenced, so it is the built page and not the dev server | passed |
| Deploy path works end to end | `scripts/deploy_studio_dev.py --contract contracts/m0_stub_probe.py` → deploy `0xd546e880…` → `0xb7ddd73F…`, `finalized`/`accepted`, `MAJORITY_AGREE`, `FINISHED_WITH_RETURN`, explorer HTTP 200, exit 0 | passed |
| Deploy `--dry-run` works | against the M1 spike, 2 methods derived, no transaction sent | passed |
| Both secret guards fire | path guard: 16 cases, all correct — `keys/private.key` and `wallet.keystore` refused inside the checkout, `docs/evidence/*.json` and source files allowed. Content guard: the real key refused when written 0x-prefixed, bare, uppercased, or as an env dump; a transaction ID of identical shape allowed | passed |
| `gltest.config.yaml`, `pyproject.toml`, `vercel.json`, `LICENSE`, `README.md`, `.env.example` | present, with the deliberate version pins and their reasons written down | passed |
| The real interface | **not built.** `frontend/src/main.js` is a skeleton that proves the build, the chain assertion and the lifecycle wait | not started |
| Direct tests | **not written.** `tests/direct/` holds the layout and the rules, no tests | not started |
| Docker | unavailable; direct tests must not require it | unverified |

### 11/11 frontend gate checks

Run by `scripts/m2_frontend_gate.py`, all passing: build exit 0 · `dist/index.html`
present · assets referenced · assets exist · chain id in bundle · RPC in bundle ·
no key in `dist/` · preview HTTP 200 · app markup served · built page not dev
server · page title.

### Two things M2 measured that are worth stating

1. **The bundle is 606 KB, of which the app's own source is about 5 KB.** The
   size is `genlayer-js` plus `viem`, not the interface. The reference build's
   entire hand-written UI was 13.9 KB and shipped the same two dependencies, so
   this is the dependency cost and not a regression. M5 should code-split if it
   wants a smaller first paint, and should not treat the number as a quality
   signal either way.
2. **The `gltest` version pins are a deliberate mismatch.** `genvm_version` is
   `v0.6.0-rc5` while the live target runs GenVM `v0.3.0-rc7`, because the
   contract header targets the older SDK layout. That is what the 360/400 build
   did, and it is recorded in `gltest.config.yaml` with the reason. When a direct
   test disagrees with the live target, the live target is right.

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
