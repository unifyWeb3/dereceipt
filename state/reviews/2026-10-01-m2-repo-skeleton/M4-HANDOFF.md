# M4 handoff — direct tests

M3 accepted with a caveat. Send the block below.

```text
M3 is reviewed and accepted. The clock finding is verified independently: I
deployed my own probe (0x27102bb2… -> 0x80C3158F…) and read it back.
gl.vm.get_timestamp exists in the std lib and raises SystemError: 2: inval at
runtime. Your _now() refusal is correct and rule 5 is vacuous, not satisfied.

Read first:
1. state/reviews/2026-10-01-m2-repo-skeleton/M3-HANDOFF.md — the "Notes for the
   human" section records the M3 deviations. Your deviations, not mine.
2. docs/VERIFICATION.md sections for M0/M1/M2/M3 — match their vocabulary,
   status columns and evidence discipline. Reviewers read that file.
3. docs/ARCHITECTURE.md — the nine hard rules, the state model, and the
   deliberate exclusions.
4. state/reviews/2026-10-01-hackathon-discovery/evidence/reference-360-build/
   VERIFICATION.md and test_typed_grant_covenant.py — the 360/400 build had 9
   methods and 10 tests. That ratio is the most likely reason 40 points were
   missing. You are writing 45+.

MILESTONE: M4 ONLY — direct tests. Nothing else.

DELIVERABLE: tests/direct/test_contest_receipt.py, 45+ tests.

CRITICAL — read this before writing a single test. Your M3 audit shipped three
bugs that made it pass wrongly: ast.walk produced "payable.write.public",
self._fail dotted-names never resolved so the call graph stayed empty, and the
clock/value walk ran forward over callees when the question was which methods
REACH the behaviour. It reported "methods that raise at all: []" while 11 of 14
could revert. You stopped at the first green result and the gate would have been
certified on an audit that could not fail.

A test suite that cannot fail is worse than no test suite, because it certifies.
Before you trust any green run, break the contract on purpose and confirm a
specific test goes red. Report which tests you deliberately broke and that they
caught it. That is the evidence I want, not "45 passed".

REQUIRED: prove each test can fail. Pick at least one test per group, mutate the
contract to violate that group's rule, run, and record that the expected test
failed. Report the mutation and the failing test name.

THE TWELVE GROUPS. Keep this taxonomy — reviewers read it:
canonicalisation · malformed shapes · deadline boundary · duplicate · declared
vs measured · source failure · digest integrity · auth · challenge · REFUND ·
conservation · panel

The two that are the points, because the 360/400 build's own VERIFICATION.md
admits it left them open:

- REFUND: cancel_program returns the pool exactly; refused after an entry is
  adjudicated; refused twice; balance conserved. This is the gap being closed.
- CONSERVATION: drive the pool in and out to exactly 0 offline, including the
  refund path. No dust, no stranded wei.

Every non-200 from GitHub is UNDETERMINED. Only 404 is a rejection. Test 403,
429, 500, empty body and non-JSON explicitly — a rate limit must never become a
rejection.

On the deadline: there is no block clock, so the deadline is an absolute unix
second compared against GitHub's signed committer.date. Test the boundary
arithmetically — exactly at the deadline, one second either side — and test
committer.date parsing including timezone offsets. Do NOT try to test arrival
time; it cannot be enforced on this runner and get_program says so.

MUST NOT pass a str where an int is expected. program_id is a str. get_program(0)
fails with gen_call failed (code=-32000) while get_program("0") returns the
record. This bit me during review and it is silent — it looks like a broken view.
Include a test that catches this class of mistake, and note it for the M5 client.

ENVIRONMENT:
- No Docker. Direct tests must not require it.
- No network. No model. No live node.
- Run with GENVM_VERSION=v0.6.0-rc5, per gltest.config.yaml. The contract header
  targets the older SDK layout while the live target is v0.3.0-rc7. That mismatch
  is deliberate.
- THE RULE: when a direct test disagrees with the live target, the live target is
  right.
- Paste the pytest output line into docs/VERIFICATION.md verbatim. Do not
  paraphrase it.
- Re-run the genvm-lint check SDK-validation half while you are at it — it hung
  on M3 and is still unverified. Same command, no contract change expected. If it
  hangs again, leave it unverified and say so.

DO NOT: add run_panel (that is M3.5 and is optional — we are skipping it). Touch
the frontend. Weaken any guard in scripts/gl_env.py. Edit contracts/m0_stub_probe.py
or the M0 evidence file. Add a database. Change the contract's behaviour to make
a test pass — if a test fails, tell me before you change the contract.

Report back with: the test count per group; the pytest line verbatim; which
tests you deliberately broke and that they went red as expected; anything in the
contract the tests could not cover and why; and the SDK-validation re-run result.
Then stop and wait.
```

---

# Notes for the human — not instruction for the agent

## The instruction that matters most

The audit shipped three bugs that made it pass wrongly, and the report says it
plainly: *"had I stopped at the first green result, the gate would have been
certified on an audit that couldn't fail."*

So the prompt's spine is **prove each test can fail**. It asks for a named
mutation per group that goes red, not a green run. A 45-test suite that cannot
fail is worse than the 10 it replaces, because it certifies work that does not
work — which is exactly how the M3 audit nearly passed.

## Two things I fixed in the plan while preparing this

**The method count is 14, not 13.** My M3 correction header said 13 (8+5) while my
own table listed 6 views. I miscounted `get_receipt_digest`. The contract has all
14 and `get_challenge` is correctly absent, so the plan's ">14" rule is intact.

**The panel group is smaller than it looks.** `run_panel` is M3.5 and we are
skipping it, so that group covers bucket/verdict bounds, `INCONCLUSIVE` producing
no verdict, and a challenge leaving untargeted criteria byte-identical — not LLM
convergence, which M1 already measured.

## Why M3.5 is being skipped

M3 landed cleanly and the gate is met without it. `run_panel` can only label one
criterion and never moves money, so it adds risk without adding a rubric point.
The INCONSISTENT gap M1 left open closes deterministically at M6 with a real repo
whose declared stack contradicts its tree. If there is time at the end, M3.5 is
recoverable — the contract already has the storage and view surface for it.

## Sequence

| | What | Gate |
| --- | --- | --- |
| ~~M3~~ | deterministic core, 14 methods | ✅ 3 of 4 verified, SDK-validation unverified |
| ~~M3.5~~ | optional `run_panel` | **skipped** |
| **M4** | 45+ direct tests, each proven able to fail | **this is where the 40 points were** |
| M5 | real UI | must send `program_id` as `str` |
| M6 | live run, 12 steps | **needs your repo decision** |

## The one thing still blocking M6

The demo repo set. M6 step 3 needs a real repo at a pinned SHA, step 4 needs one
whose declared stack contradicts its tree, step 5 needs one with a post-deadline
commit. That second one is also the only thing that closes the `INCONSISTENT`
gap M1 left open.

M4 does not need it — direct tests are offline. So this can wait one more
milestone, but not past M4.