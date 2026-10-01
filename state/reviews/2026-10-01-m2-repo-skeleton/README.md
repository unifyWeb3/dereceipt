# M2 — repo skeleton

Milestone 2 of `state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`
§5. **Gate: `npm run build` succeeds and a stub `index.html` serves. Passed.**

**No contract code.** `contracts/contest_receipt.py` does not exist; it is M3.

## Gate evidence

Machine-generated: `docs/evidence/m2-frontend-gate-2026-10-01.json`, 11/11 checks.
Reproduce with `scripts/m2_frontend_gate.py`, which runs the build, asserts the
built artefacts, scans them for key material, starts the preview server and
verifies the *served content* — a directory listing returning 200 would not
count.

| | |
| --- | --- |
| `npm run build` | exit 0 · `vite v6.4.3` · 454 modules · `✓ built in 1m 2s` |
| Built bundle carries the pinned target | chain `61997` and the Studio-dev RPC both present |
| `dist/` free of key material | the environment's real key scanned against every JS asset — clean |
| The built page serves | HTTP 200, app shell and title present, hashed asset referenced |

## What is here

```text
frontend/          Vite 6 + vanilla JS + genlayer-js 2.0.0-rc.1 + viem 2.57.2
  index.html       the app shell
  src/main.js      the skeleton: chain assertion, lifecycle wait, two state regions
  src/style.css    plain CSS, no framework, no build-time styling
  vite.config.js   base "./" so it also serves from a subpath
tests/direct/      the layout and the rules; no tests yet (M4)
docs/ARCHITECTURE.md  the boundary, the split, the hard rules, the exclusions
gltest.config.yaml the direct-test pins, with the reason for each
scripts/deploy_studio_dev.py  the one deploy path
scripts/m2_frontend_gate.py    the gate check
pyproject.toml     deps, the runner pin, pytest config
vercel.json        vite, rootDirectory frontend
README.md  LICENSE  .env.example
```

## The deploy path was exercised, not just written

A deploy script first run at M6 is a deploy script that fails at M6. So it ran
here, twice:

- `--dry-run` against the M1 spike: 2 methods derived, no transaction sent
- full deploy of the M0 stub: `0xd546e880…` → `0xb7ddd73F…`, `finalized`/
  `accepted`, `MAJORITY_AGREE`, `FINISHED_WITH_RETURN`, explorer HTTP 200, exit 0

It exits non-zero if the transaction does not reach `finalized`, because a
submitted transaction is not a deployment.

## Two guards, because they protect against different things

The plan says the deploy script "must refuse to persist a key anywhere inside
the checkout". Implemented as two separate checks, which is what the sentence
actually requires:

1. **Path guard** — refuses a *credential* file inside the checkout. Narrow on
   purpose: a blanket "no writes inside the repo" rule would also refuse the
   evidence records the plan requires at `docs/evidence/`. 16 cases tested, all
   correct — `keys/private.key` and `wallet.keystore` refused, evidence files and
   source files allowed.
2. **Content guard** — refuses to write the *real key value* into any file,
   wherever that file lives. Compared against the actual key, not pattern
   matched, because a transaction ID has the identical 32-byte hex shape and
   refusing those would make the evidence file impossible to write. The
   0x-prefixed, bare, uppercased and env-dump forms are all refused; a
   transaction ID is allowed.

The first implementation of the path guard refused *every* path inside the
checkout, including `docs/evidence/*.json`. That was wrong rather than merely
strict, and is fixed.

## Two things M2 measured

1. **The bundle is 606 KB; the app's own source is about 5 KB.** The rest is
   `genlayer-js` plus `viem`. The reference build shipped the same two
   dependencies with a 13.9 KB UI, so this is dependency cost, not a regression.
   M5 may code-split; the number is not a quality signal.
2. **The `gltest` version pins are a deliberate mismatch.** `genvm_version`
   `v0.6.0-rc5` against a live GenVM `v0.3.0-rc7`, because the contract header
   targets the older SDK layout. Copied from the reference build, with the reason
   written into `gltest.config.yaml`. **When a direct test disagrees with the
   live target, the live target is right.**

## Not built, and not claimed

- The real interface. `frontend/src/main.js` is a skeleton that proves the build,
  the chain assertion and the lifecycle wait. The lifecycle wait already throws
  on `Undetermined` and `Canceled`, and the page already renders business state
  and transaction lifecycle state in two separate regions — both because the
  reviewer will look for them and both are cheapest to get right by construction.
- Direct tests. `tests/direct/` has the layout, the twelve groups and the rules
  (no Docker, no network, no model) but no tests.
- Any contract.

## Still open, not this milestone's business

- The M6 demo repository set is a human decision.
- The `INCONSISTENT` bucket has still never been exercised.
- The browser wallet flow is user-driven; the desktop browser tool is
  unavailable, so any wallet result must be recorded as
  `user_reported_manual_browser_plus_independent_explorer_check`.

## Reproduce

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cd frontend && npm install && cd ..
set -a; . ./.env; set +a
.venv/bin/python scripts/m2_frontend_gate.py          # the gate
.venv/bin/python scripts/deploy_studio_dev.py --contract contracts/m0_stub_probe.py --dry-run
```

No Portal submission is involved.
