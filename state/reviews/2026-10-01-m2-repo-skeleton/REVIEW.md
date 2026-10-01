# M2 review — accepted

Reviewed: 2026-10-01. Verdict: **M2 gate met, 11/11. Proceed to M3.**

Commit `b693f20`. Evidence: `docs/evidence/m2-frontend-gate-2026-10-01.json`,
`state/reviews/2026-10-01-m2-repo-skeleton/`.

## Independently re-verified

| Claim | My check | Result |
| --- | --- | --- |
| `npm run build` exit 0, vite 6.4.3 | lockfile resolves `vite 6.4.3`, `genlayer-js 2.0.0-rc.1`, `viem 2.57.2` | confirmed |
| Built page serves, not a status code | `dist/index.html` references `./assets/index-C34PqlLS.js` and the hashed CSS — the built page, not a dev server | confirmed |
| Bundle carries the pinned target | `61997` and `studio-dev.genlayer.com` both present in `dist/assets/*.js` | confirmed |
| `dist/` free of key material | the gate compares the real key against every asset; I re-ran both guards below | confirmed |
| Full deploy `0xd546e880…` → `0xb7ddd73F…` | I queried the explorer directly: address **HTTP 200**, tx **HTTP 200** | confirmed |

Resolved dependency versions match the plan: `genlayer-js 2.0.0-rc.1` pinned
exactly, `viem 2.57.2`, `vite 6.4.3`. `package-lock.json` committed (lockfile v3),
so a reviewer gets the same build.

## The two guards, exercised by me

I did not take the 16-case claim on trust. Ran both directly.

**Path guard** — refuses credential paths inside the checkout only:

| Path | Refused | Expected |
| --- | --- | --- |
| `keys/private.key` | ✅ | ✅ |
| `wallet.keystore` | ✅ | ✅ |
| `acct.pem` | ✅ | ✅ |
| `a/private-key` | ✅ | ✅ |
| `b/secret.txt` | ✅ | ✅ |
| `docs/evidence/m1-2026-10-01.json` | no | no |
| `contracts/contest_receipt.py` | no | no |
| `frontend/dist/index.html` | no | no |

**Content guard** — refuses the real key wherever it lands:

| Payload | Refused | Expected |
| --- | --- | --- |
| real key, `0x`-prefixed | ✅ | ✅ |
| bare key body, no prefix | ✅ | ✅ |
| uppercased key | ✅ | ✅ |
| `GENLAYER_PRIVATE_KEY=0x…` env dump | ✅ | ✅ |
| a public transaction ID | no | no |
| an evidence JSON with a tx ID | no | no |

10/10 and 6/6 correct. The separator normalisation is the right fix —
`private.key`, `private-key` and `private_key` now agree.

## Your correction was right, and it was a real bug

The first guard refused **every** path inside the checkout, including
`docs/evidence/*.json`. That was not "stricter than asked" — it would have made
M6's evidence file impossible to write, and the plan requires that file. Caught
before M3, fixed, and now split into two correctly-scoped checks.

Worth naming why the content guard compares the **actual key value** rather
than pattern-matching 64 hex characters: transaction IDs and data hashes are
also 32 bytes. Refusing those would make every evidence file unwritable. Shape
matching was never the right test; value comparison is.

## The gate checks served content, not a status code

Right call, and a real one. A directory listing returns 200 and would have
passed a naive check. Verifying the page references its hashed asset proves it is
the **built** page rather than the dev server — which is what the M8 acceptance
row for Vercel needs.

## Exercising the deploy script at M2

This is the most valuable thing in the report. A deploy script first run at M6
is a script that fails at M6, with a half-finished evidence file. Running
`--dry-run` against the M1 spike and a full deploy of the M0 stub — and exiting
non-zero when a transaction does not reach `finalized` — means M6's step 1 is a
known quantity.

## Two measurements worth keeping

**Bundle is 606 KB; app source ~5 KB.** The rest is `genlayer-js` + `viem`. The
360/400 build shipped the same two dependencies with a 13.9 KB UI, so this is
dependency cost, not regression. Logging it as *not a quality signal* stops
someone at M5 optimising the wrong thing — and the rubric does not measure bytes.

**`gltest.config.yaml` pins a deliberate mismatch**: `genvm_version v0.6.0-rc5`
against a live GenVM `v0.3.0-rc7`, because the contract header targets the older
SDK layout. Copied from the reference build with the reason written down, plus
the rule *when a direct test disagrees with the live target, the live target is
right*. That rule is load-bearing — it will matter at M4.

## Hard rules are in the right place

All four M1 constraints plus the two plan rules are in `docs/ARCHITECTURE.md` as
**nine numbered hard rules**, not left in a review file that M3 might not read:

1. runner pin · 2. `run_nondet` not `run_nondet_unsafe` · 3. both checks run ·
4. no `raise` in a payable method · 5. no clock read in a method that moves value ·
6. `gl.evm.contract_interface` for transfers · 7. verdicts via a view ·
8. criteria snapshotted at open · 9. the original verdict is never overwritten

And a dedicated section on *a contested criterion is not a validator objection*.

`frontend/src/main.js` already throws on `Undetermined`/`Canceled` and renders
business state and lifecycle state separately — so criterion 4 is right **by
construction** rather than retrofitted at M5.

## Not built, and correctly marked as such

The real interface (M5), direct tests (M4 — `tests/direct/` has the twelve-group
layout and the rules, zero tests), any contract (M3). Nothing claimed early.

## One thing to tighten at M3, not blocking

`viem` and `vite` are caret ranges in `package.json` (`^2.21.0`, `^6.0.0`).
The lockfile pins them, so builds are reproducible — but a reviewer reading
`package.json` alone sees ranges. `genlayer-js` is exact, which is the one that
matters most. If you touch `package.json` at M3, pin the other two exactly and
note it. Low priority; the lockfile makes it correct today.

## Proceed to M3

The deterministic core. Nine hard rules are already in `ARCHITECTURE.md`.

Gate: `genvm-lint check` **and** the live schema probe both pass, ≥9 methods
derived, no `raise` in a payable method, no clock read sharing a method with a
transfer.

Two things to hold onto:

- **Run both checks.** The linter is not optional and it is not sufficient — it
  passed a contract the node killed with `NameError: name 'u32' is not defined`.
- **Verdicts are stored and read through a view.** `record["data"]` is input
  calldata; the accepted result is base64 in a format this SDK does not decode.
  The M1 spike already has the right pattern — copy it.

`M3.5` stays optional and gated on M1, which passed, so it is available if M3
lands cleanly. But **M3 first**, and the deterministic core is where the points
are. Cut M3.5 if you are running late.
