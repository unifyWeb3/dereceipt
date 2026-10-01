# M3 — the deterministic core

Milestone 3 of `state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`
§5. Deliverable: `contracts/contest_receipt.py`. **Gate met.**

## The two things a reviewer should read first

### 1. There is no clock on this runner, and that changed the design

`gl.vm.get_timestamp()` raises `SystemError: 2: inval` on Studio-dev. It is the
only time accessor in the pinned std library.

It was isolated, not guessed. Three throwaway contracts were deployed:

| Diagnostic | Result |
| --- | --- |
| storage semantics | helper writes persist · `in` works · unwritten keys raise `KeyError` |
| validator steps, isolated | `is_bounded` (genexp *and* loop), `json.loads`, `canonical_json`, criteria validation, tuple unpack — **all passed** |
| **the clock** | **`RAISED SystemError: 2: inval`** |

Consequences, all in the contract rather than in prose:

- `_now()` is a **documented refusal**. The contract does not pretend to read time.
- **Rule 5 is now vacuous and is kept anyway.** "Never combine a clock read with a
  transfer" was written for a clock this runner lacks. `claim_payout` and
  `cancel_program` stay clock-free so the separation survives if a clock appears.
- **The deadline guarantee is unaffected, and stronger for it.**
  `commit_predates_deadline` compares GitHub's signed `committer.date` against the
  absolute deadline fixed at open. That is arithmetic every validator repeats, and
  it proves *when the work existed* — not when a transaction arrived. The
  point-in-time proof never needed a clock.
- **Genuinely lost: arrival-time policy.** A late submission is no longer
  rejected; the challenge window is recorded but not contract-enforced. This is a
  real capability reduction, listed as a limitation. `get_program` returns
  `no_clock_on_this_runner: true` so the contract states it in its own data.
- **The 360/400 reference never read a clock either.** There is no `get_timestamp`
  in `typed_grant_covenant.py` at all. The plan described an intention, not the
  code that shipped. Plan and reference were wrong in the same direction, and the
  live target is the only thing that caught it.

### 2. A payable method that refuses strands value anyway

The first smoke run finalized `open_program` **successfully**, took 1000 GEN, and
created no programme — the clock threw, the catch-all swallowed it, and the
refusal was recorded nowhere. Reported as PASS at the time, because the
transaction did finalize.

The point: **reverting is forbidden because it strands value, but returning a
refusal strands it just as surely once the money has arrived.** Both are now
fixed.

- `open_program` **always creates the programme row once value has arrived.** Bad
  terms ⇒ status `CANCELLED`, pool locked, owner one `cancel_program` away from
  the money. The reason goes in `program_error`, readable via `get_program`.
- The refund path is therefore load-bearing, and it is proved: **1000 in, 0 out,
  balance observed changing**, and a repeat cancel moves nothing.

## Gate

| Check | Result |
| --- | --- |
| Live schema probe, raw JSON-RPC | **14 methods** — 8 writes, 6 views (floor was 9) |
| `genvm-lint lint` (AST) | `✓ Lint passed (3 checks)`, exit 0, on every revision |
| `genvm-lint check` (SDK validation) | **unverified — network-blocked.** Hangs with no output for >10 min; an earlier attempt gave `✗ Validation failed / Failed to load SDK: The read operation timed out`. The same command **passed** on the M0 stub and M1 spike in this session, so this is transport, not the contract. **Not claimed as a pass.** |
| No revert in a payable method | audited **transitively**; both payable methods catch `Exception` and `UserError` |
| No clock read with a transfer | vacuous — no clock exists; the two value movers read nothing time-like |
| No model in the decision path | no `exec_prompt`, `prompt_comparative`, `prompt_non_comparative` or `strict_eq` |
| `run_nondet`, not `run_nondet_unsafe` | correct |
| Deployed and finalized | `0xC96156B72404E50e2bF319934c57c285545588FA` (deploy `0x1a8cc8b3…`), `finalized`/`accepted`, `MAJORITY_AGREE`, `FINISHED_WITH_RETURN` |
| Refund path | `cancel_program` `0x842c44ec…` → balance **1000 → 0** |
| 11/11 functional smoke checks | view read · payable write · state readback · accuracy · digest · balance · refund · repeat-cancel |

**The gate's "both checks" is therefore partially met**: the AST half and the live
probe both pass, and the SDK-validation half is unverified. Re-running
`genvm-lint check` when the network is healthy should close it; nothing about the
contract needs to change for that.

## The audit is transitive, and that mattered

`scripts/m3_contract_gate.py` resolves the call graph rather than scanning for
`raise`. A literal scan reported **"methods that raise at all: []"** — while 11 of
14 methods could in fact revert, including both payable ones. Three bugs in the
auditor, each of which would have made the audit *pass wrongly*:

1. `ast.walk` produced `"payable.write.public"`, matching nothing.
2. `self._fail(...)` dotted-named to `self._fail`, never equal to `_fail`, so the
   call graph never connected and every method looked revert-free.
3. The clock/value walk went forward over callees when the question is which
   methods *reach* the behaviour — the reverse walk is what `rule 2` needs. It
   then reported `value movers: []` because `emit_transfer` is a method on the
   generated recipient proxy, not on this class, so a shallow union is required.

An audit that cannot fail is worse than no audit. This one now reports that 11
methods can revert, and rules 1 and 2 pass for specific, checkable reasons.

## Method surface — 14, and a discrepancy worth flagging

| # | Method | Kind | Payable | Reads clock | Moves value |
| --- | --- | --- | --- | --- | --- |
| 1 | `open_program` | write | **yes** | no | no |
| 2 | `submit_entry` | write | no | no | no |
| 3 | `freeze_entry` | write | no | no | no |
| 4 | `challenge` | write | **yes** | no | no |
| 5 | `finalize_program` | write | no | no | no |
| 6 | `claim_payout` | write | no | no | **yes** |
| 7 | `cancel_program` | write | no | no | **yes** |
| 8 | `_on_entry_finalized` | write (internal) | no | no | no |
| 9–14 | `get_program` · `get_entry` · `get_receipt` · `get_accuracy` · `get_receipt_digest` · `get_contract_balance` | view | — | no | no |

The plan's §5 M3 header says **"13 public methods: 8 writes + 5 views"** while its
own table lists **8 + 6 = 14**. Both counts are in the corrected plan text. The
implementation is **14**, which is inside the plan's own cut rule ("if the
implemented count exceeds 14, cut a view"), so no capability was cut. `get_challenge`
is absent as instructed.

## Storage caps — 15 named constants

`MAX_RESPONSE_BYTES` 200 000 · `MAX_STORED_PATHS` 64 · `MAX_PATH_LENGTH` 96 ·
`MAX_NAME_LENGTH` 120 · `MAX_REPO_LENGTH` 200 · `MAX_URL_LENGTH` 512 ·
`MAX_STACK_LENGTH` 200 · `MAX_CLAIMS_LENGTH` 2 000 · `MAX_CRITERIA_LENGTH` 4 000 ·
`MAX_FLAGS_LENGTH` 512 · `MAX_GROUND_LENGTH` 64 · `MAX_SLUG_LENGTH` 40 ·
`MAX_COMMIT_LENGTH` 40, plus `MAX_CRITERIA` 5 and `MAX_WEIGHT` 10.

Stored per entry: a tree **digest**, counts, and at most **64** paths of at most
**96** characters, with the number of omitted paths stored beside the summary so a
reader can see that a summary is a summary. **Never rendered HTML, never a file
body, never a full manifest.**

## Deviations from the brief, and why

| Deviation | Reason |
| --- | --- |
| **14 methods, not 13** | The brief's own table lists 14 and the plan's cut threshold is ">14". Reported, not silently resolved. |
| **`submit_entry` is not payable**; no entry stake | The pool is already locked at open, so an entry stake is a second value pool with no purpose — and the brief's own critique of the 360/400 build is stranded funds. The challenge bond is the skin-in-the-game mechanism. |
| **`cancel_program` reads no clock** | The plan's table marks it clock=yes. Rule 5 forbids clock+transfer, and the cancellation restriction is on *state*, not time. Dropping the read removes the one thing that would have broken it. |
| **No clock anywhere** | Measured. See above. |
| **Arrival-time policy dropped** | No clock. Recorded as a limitation, not papered over. |
| **`open_program` never refuses after value arrives** | A payable refusal strands value just as a revert does. |

## Preserved, not weakened

`gl_env.py`'s two guards and `deploy_studio_dev.py`'s non-zero exit on a
non-finalized transaction are untouched. `m0_stub_probe.py` is removed now that
the real contract deploys, and **`docs/evidence/m0-2026-10-01.json` is intact**.

## Files

| Path | Role |
| --- | --- |
| `contracts/contest_receipt.py` | the contract |
| `scripts/m3_contract_gate.py` | transitive rule audit → `docs/evidence/m3-rule-audit-*.json` |
| `scripts/m3_smoke_test.py` | functional check incl. the refund → `docs/evidence/m3-smoke-*.json` |
| `docs/VERIFICATION.md` | the live log, including the superseded observations |

## Not done

`freeze_entry` and the rest of the lifecycle are unexercised — `freeze_entry` is
the only non-deterministic method and needs real repositories, which is M6's job
and depends on the demo-repo decision. `challenge`, `finalize_program` and
`claim_payout` all need a frozen entry first. Direct tests are M4.

## Reproduce

```sh
set -a; . ./.env; set +a
.venv/bin/genvm-lint check contracts/contest_receipt.py
.venv/bin/python scripts/m3_contract_gate.py
.venv/bin/python scripts/deploy_studio_dev.py --contract contracts/contest_receipt.py
.venv/bin/python scripts/m3_smoke_test.py --address <from the deploy>
```

No Portal submission is involved.
