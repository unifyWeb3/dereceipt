# Verification record — DeReceipt

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
| M3 · the contract | both checks clean, 9+ methods on the live probe, no `raise` in a payable method, no clock read with a transfer | **passed** — the SDK-validation half that was `unverified` at M3 now completes; see the M4 section. One environment finding forced a design change; read it |
| M3.5 · bounded LLM criterion | optional; the product is complete without it | pending |
| M4 · direct tests | 45+ tests, pytest line pasted verbatim below | **passed** — 92 tests in twelve groups, 16/16 mutations proved a named test red. Five contract defects found, three of them money-stranding; read them before deploying |
| M5 · frontend | build succeeds, real lifecycle, business and lifecycle state shown separately | **passed** — 33/33 gate checks, 27/27 live read checks. `freeze_entry` ran against the real GitHub API for the first time. One M4 claim corrected; read it |
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
part of DeReceipt.

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
| The built page actually serves | `vite preview` → HTTP 200, app shell and `<title>` naming the product present (the gate reads the name from `frontend/src/config.js`), hashed asset referenced, so it is the built page and not the dev server | passed |
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

## M3 · the deterministic core

Machine-generated evidence: [`m3-rule-audit-2026-10-01.json`](evidence/m3-rule-audit-2026-10-01.json)
and [`m3-smoke-2026-10-01.json`](evidence/m3-smoke-2026-10-01.json).
Reproduce with `scripts/m3_contract_gate.py` (the rule audit) and
`scripts/m3_smoke_test.py --address <deployed>` (the functional check).
Record: `state/reviews/2026-10-01-m3-contract/`.

| Check | Evidence | Status |
| --- | --- | --- |
| `genvm-lint` — AST half | `genvm-lint lint contracts/contest_receipt.py` → `✓ Lint passed (3 checks)`, exit 0. Local, no network, reproduced on every revision | passed |
| `genvm-lint` — SDK validation half | **unverified in this run.** `genvm-lint check` and `genvm-lint validate` both hang with no output for >10 min, and an earlier attempt failed with `✗ Validation failed / Failed to load SDK: The read operation timed out`. The same commands **passed** on the M0 stub and the M1 spike in this same session, so the tool works and this is transport, not the contract. Not claimed as a pass | **unverified** |
| Live schema probe, raw JSON-RPC | **14 methods** — 8 writes, 6 views. Floor was 9 | passed |
| No revert in a payable method | audited transitively, not by scanning for `raise`. Both payable methods catch `Exception` and a `UserError`, so no input can revert them | passed |
| No clock read sharing a method with a transfer | **vacuous** — this runner has no clock. `claim_payout` and `cancel_program` move value and read nothing time-like | passed, with a caveat |
| No model in the decision path | `exec_prompt`, `prompt_comparative`, `prompt_non_comparative`, `strict_eq` — none present | passed |
| `gl.vm.run_nondet`, not `run_nondet_unsafe` | present / absent respectively | passed |
| Storage caps are named constants | 15 `MAX_*` constants, listed in the audit JSON | passed |
| Deployed and finalized | deploy `0x1a8cc8b3…` → `0xC96156B72404E50e2bF319934c57c285545588FA`, `finalized`/`accepted`, `MAJORITY_AGREE`, `FINISHED_WITH_RETURN`, explorer 200. Smoke on that address: `open_program` `0x83e59729…` (on the previous, identical deployment `0x26245c07…`) and `cancel_program` `0x842c44ec…`, both `finalized` | passed |
| **The refund path returns the pool** | `cancel_program` `0x842c44ec…` → contract balance **1000 → 0**, observed. Also `0x17612cfd…` on the previous identical deployment | passed |
| A repeat cancel does not pay twice | second `cancel_program` moved nothing; status stayed `CANCELLED` | passed |
| Criteria snapshotted at open | `get_program` returned exactly the 3 declared criteria, in order | passed |
| Verdict readable through a view | `get_program`, `get_entry`, `get_receipt`, `get_accuracy`, `get_receipt_digest` all read back from storage; 11/11 smoke checks | passed |
| `freeze_entry` and the rest of the lifecycle | **not exercised.** `freeze_entry` is the only non-deterministic method and needs real repositories; M6 runs it. Challenge, finalize, payout need a frozen entry first | not started |
| 45+ direct tests | M4 | not started |

### The finding that changed the design: there is no clock on this runner

**`gl.vm.get_timestamp()` raises `SystemError: 2: inval` on Studio-dev.** It is
the only time accessor in the pinned std library, and it is broken.

This was not inferred. Three throwaway diagnostic contracts were deployed to
isolate it, and the second one named the culprit exactly:

| Diagnostic | Result |
| --- | --- |
| storage write in a helper, read back | `contains: true` — helper writes persist, `in` works, unwritten keys raise `KeyError` |
| validator steps, one at a time | `is_bounded` (generator expression **and** plain loop), `json.loads`, `canonical_json`, and the criteria validator **all passed**; `criteria_unpack` returned `count=3 len=138` |
| **`gl.vm.get_timestamp()`** | **`RAISED SystemError: 2: inval`** |

Consequences, all recorded in the contract rather than papered over:

1. **`_now()` is now a documented refusal, not a working clock.** The contract
   does not pretend to read time.
2. **Rule 5 is vacuous, and is kept anyway.** "Never combine a clock read with a
   transfer" was written for a clock this runner does not have. It is retained as
   a constraint rather than quietly deleted, and `claim_payout` / `cancel_program`
   are still clock-free so the separation survives if a clock appears.
3. **The deadline guarantee is unaffected, and is actually the stronger form.**
   `commit_predates_deadline` compares GitHub's signed `committer.date` against
   the absolute deadline the organiser fixed at open. That is arithmetic every
   validator repeats, and it proves *when the work existed* rather than when a
   transaction arrived. The point-in-time proof — the wedge — never needed a
   clock.
4. **What is genuinely lost: arrival-time policy.** A late submission is no
   longer rejected, and the challenge window is recorded but not enforced by the
   contract. This is a real capability reduction and is listed as a limitation
   rather than dressed up. `get_program` exposes `no_clock_on_this_runner: true`
   so the contract states it in its own data rather than only in a doc.
5. **The reference build never read a clock either.** Reading
   `typed_grant_covenant.py` again, there is no `get_timestamp` in it at all —
   the plan's claim that it "reads the clock in a callback" described an
   intention, not the code that shipped. So this is the plan and the reference
   build both being wrong in the same direction, and the live target is the only
   thing that caught it.

### A second finding: a payable method that refuses strands value anyway

The first smoke run exposed a real hazard, and it is the hazard rule 4 exists to
prevent.

`open_program` read the clock, and the clock threw. The throw was caught by the
method's own `except Exception`, which returned a refusal — so the transaction
**finalized successfully**, 1000 GEN arrived, and no programme was created. The
run reported "open_program finalized: PASS". The value was stranded, the refusal
was recorded nowhere, and the only reason it was found at all is that the smoke
test then read `get_program` and got `unknown programme`.

Two defects, both fixed:

1. **A catch-all refusal is not a safe payable path.** Reverting is forbidden
   because it strands value; returning a refusal strands it just as surely if the
   method already took the money. The fix is that `open_program` now **always
   creates the programme row once value has arrived**. If the terms are
   invalid, the row is created with status `CANCELLED` and the pool locked, so
   the owner is one `cancel_program` call from recovering. The reason is stored
   in `program_error` and readable through `get_program`, so a refusal is never
   invisible again.
2. **Reading a write's return value is not possible** — M1's finding 8, hit again.
   `record["data"]` is input calldata, and the accepted result is base64 in
   `consensus_data.validators[*].result`. It took decoding a consensus receipt by
   hand to see `SystemError: 2: inval`, which is exactly the workflow rule 7
   exists to prevent. The contract now records its own refusals in storage, so
   the frontend and the runner read a view.

The refund path is therefore load-bearing rather than decorative, and it is
proved: **1000 in, 0 out, balance observed changing.**

### Failed and superseded M3 observations

**A first `open_program` stranded 1000 GEN.** Deploy
`0xb8db801ab4906cd9fa0f2c3a95c4e35b8ac2b0d63d662b7e389dccc209aa8f0b` →
`0xCD812a8aDD0A6F3780C9CB9c90B50393feb4954F`, `finalized`/`accepted`. Its
`open_program` `0xa3d27737aa85027fb77a5238b3b92276d8feaf29efd1491ffa7dd872564ee8f7`
also finalized and the balance rose to 1000 — with no programme. Recorded here
because "the transaction finalized" and "the contract worked" are different
claims, and this is the case where they diverged.

**Three diagnostic contracts were deployed and then deleted.**
`0x7F9AE04bF5958d074d0ae3bbD8DF95953eD47915` (storage semantics) and
`0xE85cf84BBed4E1F70E9AE6b3e360f8d061B08f58` (validator steps) found the clock
bug. The third, a clock-source probe, failed to deploy with `exit_code 1` — it
imported `genlayer._internal.*` at module scope, which a contract may not do.
Not retried: by then the standard library had already been read directly and
`get_timestamp` was the only accessor, so a third deploy could not have changed
the conclusion.

### One discrepancy in the brief, reported rather than silently resolved

The plan's §5 M3 header says **"13 public methods: 8 writes + 5 views"** while
its own method table lists **8 writes and 6 views = 14**. Both counts appear in
the corrected plan text. The implemented surface is **14 (8 writes, 6 views)**:
`open_program`, `submit_entry`, `freeze_entry`, `challenge`,
`finalize_program`, `claim_payout`, `cancel_program`, `_on_entry_finalized`, and
`get_program`, `get_entry`, `get_receipt`, `get_accuracy`,
`get_receipt_digest`, `get_contract_balance`.

`get_challenge` is **not** present, as instructed — the receipt is the challenge
log. The 14th is the internal finalization callback, which the plan's own table
lists. The plan's cut rule is "if the implemented count exceeds 14, cut a view",
so 14 is inside the stated tolerance and no capability was cut to reach it.

## M4 · direct tests

Record: `state/reviews/2026-10-01-m4-direct-tests/REVIEW.md`.
Mutation proofs: `state/reviews/2026-10-01-m4-direct-tests/MUTATIONS.md`.

```bash
bash run_direct_tests.sh
```

Offline. No Docker, no network, no model, no live node. `GENVM_VERSION=v0.6.0-rc5`.

### The pytest line, verbatim

```
92 passed in 128.52s (0:02:08)
```

Machine-readable cross-check, from `--junitxml`:

```
tests=92 failures=0 errors=0 skipped=0 time=68.310s
```

**Do not run the suite with `-q`.** On this runner `-q` suppresses pytest's
session summary entirely: the progress dots print, the exit code is right, and
the `92 passed in …` line never appears. It is a `-q` interaction with gltest's
plugin set, not a broken suite — but it looks exactly like one. The line above
was captured without `-q` for that reason.

### Group coverage

| group | tests | mutation that made it red |
| --- | --- | --- |
| canonicalisation | 8 | drop the trailing-slash strip in `_canonical_repo` |
| malformed shapes | 13 | lower the criteria floor from 3 to 1 |
| deadline boundary | 6 | make the deadline comparison inclusive (`<=`) |
| duplicate | 4 | stop consulting the stored digest set |
| declared vs measured | 5 | continue past an unknown language token |
| source failure | 8 | treat every non-404 as a pass |
| digest integrity | 5 | return a constant from `get_receipt_digest` |
| authorisation | 7 | drop the owner check from `cancel_program` |
| challenge | 9 | allow two challenges on one entry |
| refund | 6 | stop zeroing the locked balance before emitting |
| conservation | 6 | drop the tie-split remainder |
| panel and API boundaries | 11 | report disqualified entries as contested criteria |

Sixteen mutations, sixteen named tests that went red. Reproduce with
`.venv/bin/python scripts/m4_mutation_proof.py`.

### Five defects found by these tests

1. **`freeze_entry` never worked.** `committer_block` where the local was
   `commit_block` — a `NameError` on every successful freeze. Missed at M3
   because M3 had no network and the smoke test never froze an entry.
2. **The winner could never be paid.** `claim_payout` required
   `PENDING_FINALITY`, but `_on_entry_finalized` exists to move the entry *off*
   that state, so the claim was always refused and the pool was stranded on a
   `CLOSED` programme that could not be cancelled. Hidden by a *harness* bug:
   `EmitInternalMessage` was silently undispatched, so the callback never ran and
   the suite would have gone green over a contract that could not pay anyone.
3. **An outage could disqualify an entrant.** Zero paths from an unavailable
   GitHub were searched for `.py`, found nothing, and recorded `FAIL`. Absence of
   evidence read as evidence of absence, twice, in two different methods.
4. **A denied challenge's bond could be stranded.** `claim_payout` only accepts a
   closed programme and `cancel_program` sets `CANCELLED`, so cancelling with a
   bond outstanding returned the pool and left the challenger's GEN stuck.
5. **`AFTER_DEADLINE_WORK` could never be upheld.** The evidence was
   canonicalised as an https URL and then compared for equality against a 40-hex
   commit, so the one ground a deterministic re-derivation can settle was
   decorative.

Also: `finalize_program` raised `KeyError` on any unchallenged entry, which is
the common case, because its bond-return loop indexed `challenge_status` for
every entry while that key is written only for challenged ones. Fixed by reading
through a defaulted accessor; write paths still index directly.

### A correction to the above, found at M5

This record originally also claimed that `get_entry` **raised on an unfrozen
entry, confirmed on chain with `gen_call failed (code=-32000)`**. **That
confirmation was wrong.** It was not a contract defect; it was the caller.

`genlayer-py` rejects a string in a `uint256` slot, and `entry_index` is a
`uint256`. The M4 probe called `get_entry("0", "0")` — a string where an integer
belongs — and read the resulting `code=-32000` as the contract failing. Called
correctly, `get_entry("0", 0)` returns the record.

Measured at M5 against the same live contract, with both clients:

| call | `genlayer-py` 0.19.0rc2 | `genlayer-js` 2.0.0-rc.1 |
| --- | --- | --- |
| `get_entry("0", 0)` | works | works |
| `get_entry("0", "0")` | **`code=-32000`** | **works — coerces** |
| `get_program(0)` | refused (a different key) | refused by our own guard |

So the browser is the *lenient* client and the Python one is strict. The
underlying hardening is still correct — `TreeMap.__getitem__` really does raise
`KeyError` for an unwritten key, the 92 direct tests still prove it, and the
`_read` accessor is still the right fix. What was wrong is the claim that it had
been confirmed on chain. The confirmed-on-chain finding in this milestone is
`freeze_entry`, which ran against the live GitHub API for the first time.

**The lesson is the project's recurring hazard again:** a check whose failure I
attributed to the thing under test, without first establishing that the check
itself was sound.

### `genvm-lint check`, both halves

The SDK-validation half was `unverified` at M3 — it hung on SDK-load network
timeouts. It completes now:

```
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: ContestReceipt
  Methods: 14 (6 view, 8 write)
```

Exit 0.

### Still `unverified` after M4

| check | why |
| --- | --- |
| `validator_fn` behaviour | gltest's direct runner executes the leader and returns its result without running the validator. M1's 6/6 2-bucket convergence remains the only validator evidence. |
| any live `freeze_entry` | every GitHub call in the suite is mocked. M6 is the first real one. |
| a real payout on chain | the inversion in defect 2 was found offline; proving the fix needs M6's finalization plus an observed balance decrease. |
| the value model itself | `direct_vm.deal`, the payable-call credit and the transfer debit are modelled in `tests/direct/conftest.py`, not by gltest. Conservation tests are only as good as that model. |

## M5 · the real frontend

Named **DeReceipt**. Gate script: `scripts/m5_gate.py`. Interface: `frontend/`,
vanilla ES modules, no framework, no database, no backend.

### What is deployed, and read by the interface

Deployed with `scripts/deploy_studio_dev.py`, which exits non-zero unless the
transaction reaches `finalized`:

```
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: ContestReceipt
  Methods: 14 (6 view, 8 write)
finalized/accepted · MAJORITY_AGREE · FINISHED_WITH_RETURN
contract = 0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D
votes    = {'AGREE': 3, 'IDLE': 2}
DEPLOYED and finalized.
```

`IDLE: 2` is the M1 measurement reproducing itself on a different method.

### `freeze_entry` against real GitHub — first time on chain

The only method that calls the network, and it had never run live. It did, on
this deployment, in 64 seconds:

```
submit → frozen
get_entry    {"status": "STANDING", "committer_date": "2026-06-10T14:46:12Z",
              "criteria": [{"criterion": "repo_resolves", "verdict": "PASS",
                            "reason": "repository_resolves"}, …]}
get_receipt  {"status": "STANDING",
              "tree_digest": "6e0a4ca9dc91a67a9c1dc0dffda478ac13318fde55a4903306c9c2289e32412b"}
get_accuracy {"undetermined": 0, "disqualified": 0, "overturn_rate_bps": 0}
get_receipt_digest  1df5b44339d9a682814bdb9a4170dcc78f4798283f34356306b433641ef53513
get_contract_balance  1000
```

So **the Studio-dev validators do have internet access.** M6's live run is
therefore viable, and defect 5's `AFTER_DEADLINE_WORK` — which needs a real
post-deadline commit — can be exercised for real.

### Gate: 33/33

```
33/33 checks passed
```

| group | checks | what it catches |
| --- | --- | --- |
| build | 2 | a broken import shipped; `dist/` absent |
| serving | 6 | the dev server answered and the built page was never tested |
| pinned target | 4 | a build pointing at mainnet, or at nothing |
| identifier guards | 2 | a rename silently dropped the guard keeping `program_id` a string |
| naming | 2 | a half-finished rename |
| key material | 6 | a `.env` value in the bundle |
| UNDETERMINED as a state | 2 | the amber treatment collapsing into the error treatment |
| state regions | 2 | business state and lifecycle state merged into one summary |
| motion | 1 | an indefinite animation ignoring `prefers-reduced-motion` |
| injection | 1 | `innerHTML` parsing chain-supplied strings |
| live reads | 3 | the page rendering zeroes and looking broken |

### Live read paths: 27/27

`frontend/scripts/verify-reads.mjs`, built to an SSR bundle so it runs the
*actual shipped modules* — not a copy — against the chain:

```
27/27 checks passed
```

All six views read with `program_id` a string and `entry_index` a number. The
strongest of these reads the types off the deployed contract rather than trusting
the interface's assumptions:

```
PASS  deployed schema declares get_program(program_id: string) — declared string
PASS  deployed schema declares get_entry(program_id: string, entry_index: int) — declared string, int
PASS  the two payable methods are exactly open_program and challenge — challenge,open_program
PASS  get_challenge is absent — the receipt IS the challenge log — absent, as designed
```

### Two SDK clients disagree about identifier types

| call | `genlayer-py` 0.19.0rc2 | `genlayer-js` 2.0.0-rc.1 |
| --- | --- | --- |
| `get_entry("0", 0)` | works | works |
| `get_entry("0", "0")` | **`code=-32000`** | **works — coerces** |
| `get_program(0)` | refused (a different key) | refused by our own guard |

The browser is the lenient client. `assertEntryIndex` normalises a numeric string
from a URL before sending, and `assertProgramId` refuses an integer with a
sentence naming which argument was wrong.

### Key-material scan

Two tiers, because one concatenated scan cannot tell a leaked key from a
published constant. **Our own chunk: zero** — no 32-byte hex, no `PRIVATE_KEY`,
no seed phrase. **Vendor chunks:** 13 distinct 32-byte values, every one
classified by shape rather than enumerated, so the check survives a dependency
bump:

```
PASS  every 32-byte hex in vendor chunks is bytecode, a published constant, or a test pattern
      — 13 found: 6×EVM init code, 3×synthetic repeating pattern, 4×published constant
PASS  vendor chunks contain nothing from this project
```

### The M2 gate still passes

The M2 gate read the product name as a literal. It now reads it from
`frontend/src/config.js`, so the next rename is one edit:

```
11/11 checks passed
```

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
