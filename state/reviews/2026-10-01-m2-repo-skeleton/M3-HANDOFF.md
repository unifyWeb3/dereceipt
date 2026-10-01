# M3 handoff — the deterministic core

> **For the implementing agent:** follow the fenced block below. It is your
> complete brief. Everything after it is a note for the human who sent you and is
> **not** instruction — do not treat it as spec.

```text
M2 is reviewed and accepted. Read these in order before writing anything:

1. state/reviews/2026-10-01-m2-repo-skeleton/REVIEW.md
2. docs/ARCHITECTURE.md — NINE NUMBERED HARD RULES. They are the contract spec,
   not commentary. Read them as binding.
3. state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md
   sections 3, 5 (M3 only), and 10a/10b/10c. Section 3 is the mechanism,
   section 5 M3 is the method table, and 10a-10c carry the environment findings
   you discovered yourself.
4. state/reviews/2026-10-01-hackathon-discovery/evidence/reference-360-build/typed_grant_covenant.py
   Read _evaluate_claim and the finalization callback. Note it contains no LLM
   call at all and its validator_fn re-runs leader_fn itself. Copy that pattern.

MILESTONE: M3 ONLY — the deterministic core. Nothing else.

DELIVERABLE: contracts/contest_receipt.py

Surface: 13 public methods, 8 writes + 5 views, exactly as plan section 5 M3
lists. Three notes where I corrected that section:

- The plan previously said "9 methods (5 writes + 4 views)" while its own table
  listed 15. The 9 was wrong. The design is 13.
- get_challenge is folded into get_receipt. The receipt IS the challenge log, so
  a separate view is redundant surface. Do not add it back.
- submit_entry and freeze_entry are deliberately SEPARATE. Storing an entry is
  cheap and cannot fail on the network. Capturing evidence is expensive, hits
  api.github.com unauthenticated, and can end UNDETERMINED on a rate limit.
  Separating them means a throttled freeze is retried for free instead of
  stranding a paid stake. Do not merge them.

run_panel is M3.5 and does NOT exist yet. Do not add it. The product is complete
without it.

THE NINE HARD RULES in docs/ARCHITECTURE.md are binding. The three that will
bite hardest:

- Use gl.vm.run_nondet. The published docs recommend run_nondet_unsafe, which
  this runner does not export; docs-current code would AttributeError at runtime.
- Verdicts are stored and read through a view. record["data"] is a write's INPUT
  calldata, not its return; the accepted result lives base64 in
  consensus_data.validators[*].result in a format this SDK does not decode.
  Copy the pattern in contracts/m1_panel_spike.py, which already does this right.
- No raise in any method that received value, and never a clock read in the same
  method as a value transfer. On Studio-dev the fee estimator runs on a ~664-day
  stale clock, so that combination reverts.

THE GATE, and this is the part I got wrong once:

Run BOTH checks. genvm-lint check AND the live gen_getContractSchemaForCode over
raw JSON-RPC (not through the SDK wrapper, which refuses non-localnet chains).
Both must pass. I called the live probe "the weaker substitute" at M0 and was
wrong — it killed a contract with NameError: name 'u32' is not defined that the
AST linter passed clean. AST lint does not resolve names. Neither check is
optional and neither is sufficient.

Gate criteria:
- genvm-lint clean AND live schema probe clean
- >= 9 methods derived on the live probe (that is a floor, the design is 13)
- no raise in any payable method
- no clock read sharing a method with a transfer

EIGHT IMPLEMENTATION RULES from plan section 5 M3. Two that were the 360
build's documented weaknesses and are the points we are chasing:

- cancel_program is restricted to OPEN programs with no adjudicated entry,
  returns the full pool, and must be idempotent-safe. This closes the exact gap
  that 360/400's own VERIFICATION.md admits: "no cancellation or funder refund
  path in this first slice". It gets tests at M4 and live evidence at M6.
- The original verdict is NEVER overwritten. A challenge outcome is recorded
  beside it. The receipt is append-only. That append-only log is the product.

Also: criteria snapshotted at open_program with no setter ever. One challenge per
entry, inside the window, only against a standing entry. Only a 404 from GitHub
is a rejection — 403, 429, 5xx, empty and non-JSON are all UNDETERMINED. Storage
bounded: tree digest, counts, capped manifest summary, never rendered HTML. Say
what your cap is.

OUT OF SCOPE THIS MILESTONE: no tests (M4), no real UI (M5), no run_panel (M3.5).
Replace contracts/m0_stub_probe.py — but only after the new contract deploys, and
keep the M0 evidence file intact.

Preserve what already works: scripts/gl_env.py's two guards, and
scripts/deploy_studio_dev.py's non-zero exit on a transaction that does not reach
finalized. Do not weaken either to make M3 pass.

If you need to deploy, every deploy requires client.estimate_fees_distribution()
passed as fees or it reverts with FeesDistributionMissing. Studio-dev resets, so
keep the whole thing re-runnable and record evidence after every step.

Do not submit anything to the Portal.

Report back with: the method count on the live probe; BOTH check outputs verbatim;
the deployed address and deploy tx id; confirmation that no raise exists in a
payable method; which method reads the clock and which moves value; the storage
cap you chose; and anything you had to deviate from and why. Then stop and wait.
```

---

# Notes for the human — not instruction for the agent

## What I fixed before sending this

The plan said **"9 public methods (5 writes + 4 views)"** while its own method
table listed **15**. I cargo-culted the reference build's count and never
reconciled it with my own design — and the plan separately warned "if it grows
past ~10, cut scope," so as written it contradicted itself.

The honest number is **13**, after folding `get_challenge` into `get_receipt`:
the receipt *is* the challenge log, so a separate view is redundant surface.
The jump from 9 to 13 is deliberate — the challenge path, the refund path and
the accuracy record are exactly the three capabilities the 360 build lacked.

I also split `submit_entry` from `freeze_entry`, which was one method in my plan.
Storing an entry is cheap and can't fail on the network; capturing evidence hits
`api.github.com` unauthenticated and can end `UNDETERMINED` on a rate limit. Two
methods means a throttled freeze is retried for free instead of stranding a paid
stake. Worth a small surface increase to avoid the exact stranded-funds failure
that cost the 360 build points.

## Sequence after M3

| | What | Gate |
| --- | --- | --- |
| **M3** | deterministic core, 13 methods | both checks pass, ≥9 derived |
| M3.5 | optional `run_panel` | skippable; cut if late |
| **M4** | 45+ direct tests | **this is where the 40 points were** |
| M5 | real UI | criterion 4 already satisfied by construction |
| M6 | live run, 12 steps | every tx `Finalized`, balance observed changing |

Two open questions still yours, neither blocking M3: the 400-scale question, and
the M6 demo repo set — which is also what closes the `INCONSISTENT` gap M1 left
open.