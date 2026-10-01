# M3 review — accepted with one caveat

Reviewed: 2026-10-01. Verdict: **gate met on three of four criteria. Proceed to
M4. M3.5 skipped.**

Commit `260d613`. Evidence: `docs/evidence/m3-rule-audit-2026-10-01.json`,
`docs/evidence/m3-smoke-2026-10-01.json`. Deployed
`0xC96156B72404E50e2bF319934c57c285545588FA`.

## The clock finding — independently confirmed

I did not take this on trust. I deployed my own diagnostic probe
(`0x27102bb2…` → `0x80C3158F…`) and read it back through the contract:

```
has_attr          -> has_get_timestamp=True;
                     vm_attrs=[... 'run_nondet', 'run_nondet_default' ...]
try_get_timestamp -> RAISED:SystemError:2: inval
```

**`gl.vm.get_timestamp()` exists in the std lib and raises at runtime.** Isolating
storage semantics, validator primitives, and the clock across three throwaway
deploys was the only way to tell "the clock is absent" from "my contract is
broken". That was the right method.

Two encodings of this are worth keeping:

- **`_now()` is a documented refusal**, not a comment. The contract states its own
  limitation in its own data — `get_program` returns `no_clock_on_this_runner:
  true` — so a reviewer learns it from the chain rather than from prose.
- **Rule 5 is kept even though it is vacuous.** `claim_payout` and
  `cancel_program` stay clock-free so the separation survives if a clock appears.
  That is the difference between satisfying a rule and deleting it.

**The deadline guarantee is unaffected, and is the stronger form.**
`commit_predates_deadline` compares GitHub's *signed* `committer.date` against the
deadline fixed at open. The point-in-time proof never needed a clock, so the
headline wedge — the 0/219 capability — is intact.

**Genuinely lost:** arrival-time policy. A late submission is accepted, and the
challenge window is recorded but not enforced. Correctly listed as a limitation
rather than papered over.

Also caught: the 360/400 reference never read a clock either. **My plan and the
reference build were wrong in the same way, and only the live target found it.**

## The payable-refusal finding is the more important one

`open_program` finalized, took 1000 GEN, created no programme, and **read as PASS
because the transaction finalized.**

My brief said *"no `raise` in a payable method — a revert strands value."* The
mirror image is equally true: **returning a refusal strands the value just as
surely once the money has arrived.** Both are wrong, and only one was in my
instruction.

Fixed correctly: `open_program` always creates the programme row once value
arrives (bad terms → `CANCELLED`, pool locked, one `cancel_program` to recover),
and the reason is stored and readable through a view. **Proved live** —
`cancel_program` took the balance 1000 → 0, and a repeat cancel moved nothing.
That is the exact gap the 360/400 build's own `VERIFICATION.md` admits it left
open, now closed with on-chain evidence.

## The audit passed wrongly three times, then was fixed

| Bug | Effect |
| --- | --- |
| `ast.walk` → `payable.write.public` | decorator detection wrong |
| `self._fail` dotted-names unresolved | call graph stayed empty |
| forward walk over callees | wrong direction for "which methods reach this" |

It reported `methods that raise at all: []` while 11 of 14 could revert, both
payable ones included. The corrected audit is legible: 14 methods (13 public + 1
internal callback), `reachable_revert_helpers: {}`, `offenders: []`, and
`claim_payout`/`cancel_program` are the only value-moving methods and the only
`can_revert: False` ones.

**This is why M4 now carries a mutation requirement.** A suite that cannot fail
certifies work that does not work.

## Independent read of the deployed contract

```
balance              -> 0
get_program("0")     -> status=CANCELLED pool=1000 locked=0 no_clock=True
get_receipt_digest(0)-> 67cf24e1d17dc920d5f370c760539e3b4b3dd1ae397af920160a7fa83c1f91ca
```

**`program_id` is a `str`.** `get_program(0)` fails
`gen_call failed (code=-32000)`; `get_program("0")` returns the record. It reads
as a broken view rather than a type mismatch. The M5 client must send it as a
string, and M4 should include a test for the class.

## Gate: three of four verified

| Criterion | Result |
| --- | --- |
| Live schema probe, raw JSON-RPC | **14 methods** — floor was 9 |
| `genvm-lint` lint | ✓ 3 checks, exit 0 |
| `genvm-lint check` SDK-validation half | **unverified** — hangs >10 min; earlier `Failed to load SDK` |
| No revert in a payable method | passed, transitively audited |
| No clock read with a transfer | **vacuous** — no clock exists |

I agree the SDK-validation failure is transport, not the contract: the same
command passed on the M0 stub and the M1 spike in this session. **Re-run it when
the network is healthy; do not mark it passed on my say-so.** Nothing in the
contract needs to change.

## The 14-vs-13 discrepancy is mine, twice

My M3 correction header said 13 (8 writes + **5** views) while my own table listed
six. I miscounted `get_receipt_digest`. The contract has all 14 and
`get_challenge` is correctly absent, so no capability was cut and the plan's
">14, cut a view before a capability" rule was never triggered. Plan corrected.

## Deviations — all three sound

- **14 methods, not 13** — my arithmetic, above.
- **`submit_entry` is not payable; no entry stake.** Right call. The pool is
  already locked, and a second value pool reintroduces exactly the
  stranded-funds problem the whole design centres on. The challenge bond is the
  skin-in-the-game mechanism.
- **`cancel_program` reads no clock.** My table marked it clock=yes, but rule 5
  forbids clock+transfer and the restriction is on state, not time. Correct, and
  safer than what I specified.

## Not done, correctly marked

`freeze_entry` is the only non-deterministic method and is unexercised.
`challenge`, `finalize_program` and `claim_payout` each need a frozen entry first.
All M6, gated on the demo-repo decision.

## M3.5 is being skipped

M3 landed cleanly without it, and `run_panel` can only label one criterion and
never moves money — risk without a rubric point. The `INCONSISTENT` gap M1 left
open closes deterministically at M6 with a real repo whose declared stack
contradicts its tree. The contract already has the storage and view surface for
it, so this is recoverable at the end if time allows.

## Retire: `m0_stub_probe.py`

The stub is superseded and the M0 probe defaults to the real contract. **The M0
evidence file was left untouched and still records the stub it actually
deployed** — rewriting it would make the record untrue. That is exactly the
discipline the evidence rules demand, and it should stay that way.

## Next: M4 — 45+ direct tests, each proven able to fail

Prompt: `state/reviews/2026-10-01-m2-repo-skeleton/M4-HANDOFF.md`.

The instruction that matters most: **break the contract on purpose and confirm a
specific test goes red.** Report which mutation broke which test. A green run is
not the evidence; a red one is.