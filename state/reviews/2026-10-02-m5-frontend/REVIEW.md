# M5 review — the real frontend

Milestone: **M5 · the real frontend**. Date: 2026-10-02.
Product name: **DeReceipt**. Repo: `unifyWeb3/dereceipt`.

## Verdict

**Accepted.** 33/33 gate checks and 27/27 live read checks. `freeze_entry` ran
against the real GitHub API for the first time, which unblocks M6.

And one M4 finding was **wrong** and has been corrected in place.

## What was built

Vanilla ES modules behind a hash router. No framework, no database, no backend,
no state library — the M5 handoff forbids all four, and `vite.config.js` states
why: the reviewer is meant to read the whole transaction path in one sitting.
Our own code is **38 KB, 13 KB gzipped**; vendor is split into separate chunks.

```
frontend/src/
  config.js              PRODUCT_NAME, chain, RPC, explorer, contract address, the copy
  main.js                boot, hash router, the two persistent state regions, one write path
  lib/identifiers.js     assertProgramId / assertEntryIndex / parseRoute / buildRoute
  lib/contract.js        the only path to the chain: reads, writeAndWait, lifecycle, presence
  lib/wallet.js          EIP-1193 connect, chain assertion and switch
  lib/dom.js             el() / badge() / stat() / copyable() / stateBlock()
  lib/format.js          gen, dates, digests, verdict and status wording
  views/stage.js         the receipt stage — the product's own output, replayed
  views/landing.js       the claim, the objection answered, the rubric, what is live
  views/programme.js     business state, accuracy, digest, organizer controls, lifecycle region
  views/receipt.js       the receipt itself
  views/openProgramme.js the organizer form
```

Four routes: `#/`, `#/open`, `#/program/0`, `#/program/0/entry/1`.

## Design decisions, and where they came from

`state/reviews/2026-10-02-frontend-competitive-review/FINDINGS.md` studied eight
projects across the three profiles and found five things they all do:

| finding | what DeReceipt does |
| --- | --- |
| lead with a stake, not a noun | "A verdict you can check." |
| put the product doing the thing above the fold | `views/stage.js` replays the **real** receipt read from the chain |
| pair every claim with what checks it | `ASSURANCES` in `config.js`, each with a pointer to the tests that prove it |
| say what is deliberately absent | the objection "you are letting an AI judge a hackathon" is answered before it is asked, and the answer is that there is no model in the decision path |
| a labelled, honest fixture | if the chain has no frozen receipt the stage says so and refuses to substitute a mock |

One departure from the review's own recommendation, recorded deliberately: the
review argued for React + Tailwind. **The handoff forbids introducing a
framework**, and the handoff wins — so this is hand-written CSS. The gap the
review identified was *absence of design*, not absence of Tailwind: a type
scale, a palette, a motion layer and a component vocabulary do that work, and
they are readable in one sitting.

## A correction to M4

M4's record claimed `get_entry` **raised on an unfrozen entry, "confirmed on
chain: `gen_call failed, code=-32000`"**. That confirmation was wrong.

`genlayer-py` rejects a string in a `uint256` slot, and `entry_index` is a
`uint256`. The M4 probe called `get_entry("0", "0")` and read the resulting error
as the contract failing. Called correctly it returns the record.

Measured at M5 on the same chain, with both clients:

| call | `genlayer-py` 0.19.0rc2 | `genlayer-js` 2.0.0-rc.1 |
| --- | --- | --- |
| `get_entry("0", 0)` | works | works |
| `get_entry("0", "0")` | **`code=-32000`** | **works — coerces** |

So the browser is the *lenient* client and only the Python one enforces the
type. **The hardening is still correct** — `TreeMap.__getitem__` does raise
`KeyError` for an unwritten key, the direct suite proves it, and `_read` is still
the right accessor — but it was never a chain finding. Corrected in
`docs/VERIFICATION.md` and in the M4 review.

That is this project's recurring hazard, third instance: a check whose failure I
attributed to the thing under test without first establishing that the check was
sound. The M3 audit and the M4 mutation self-check were the first two.

## What the gate checks, and why each one exists

`scripts/m5_gate.py` — 33 checks. Each exists because its absence is a specific,
plausible failure. Two are worth singling out.

**Key material, in two tiers.** The first run failed on 13 matches. All 13 were
`keccak256("")` in vendor code. Widening the pattern until it passed would have
been the wrong fix, so the check now classifies by *shape* — EVM init code, a
published constant, or a synthetic repeating-nibble pattern — and our own chunk
is scanned separately and strictly. That survives a dependency bump; an
allowlist would not.

**Identifier types read off the deployed contract.** Rather than trusting the
interface's assumptions, the verifier reads the schema and asserts
`get_program(program_id: string)` and `get_entry(program_id: string, entry_index: int)`
are what the *chain* says. If a future revision changed either, the interface's
assertions are wrong with it and this fails.

## Deliberately not built, and why

| not built | why |
| --- | --- |
| an entrant challenge-bond form | the contract path has never been exercised on chain; a control that reverts is worse than an honest gap. Labelled as not-yet-available rather than faked. |
| an entry-by-entry payout claim form | same — `claim_payout` has never run on chain, and M4 found its guard was inverted. |
| a "leaderboard" | the contract publishes `get_accuracy`, which is an accuracy record, not a ranking. Rendering it as a leaderboard would imply a score the product deliberately does not compute. |
| a dark/light toggle | a receipt is read on one screen in one lighting. A toggle is a feature nobody asked for. |
| a framework | the handoff forbids it. |

## Still unverified after M5

| check | why |
| --- | --- |
| rendering in a browser | **no browser is available in this session.** The build, the served page, every asset, the bundle contents and all six read paths are verified; the paint is not. This is the one gate item not met, and it is the only thing standing between this and a Vercel URL. |
| `finalize_program` and `claim_payout` on chain | never run. M6. |
| `challenge` on chain | never run. M6. |
| `validator_fn` behaviour | direct mode runs the leader only; M1's 6/6 remains the only evidence. |

## Naming — where the name lives, and where it deliberately does not

The instruction was: if "Contest Receipt" appears anywhere beyond one constant,
say so rather than replacing occurrences one by one.

**It does, and here is every remaining occurrence with its reason:**

| location | occurrence | decision |
| --- | --- | --- |
| `frontend/src/config.js` | `PRODUCT_NAME = "DeReceipt"` | **the single definition** |
| `frontend/index.html` | `<title>DeReceipt …`, `noscript` copy | changed |
| `frontend/package.json` | `"name": "dereceipt"` | changed |
| `scripts/m2_frontend_gate.py` | read `PRODUCT_NAME` from config | changed — it used to hard-code the literal |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/VERIFICATION.md` | headings and prose | changed |
| `contracts/contest_receipt.py` | **filename** | **not changed** |
| `contracts/contest_receipt.py` | module docstring, line 3 | **not changed** — see below |
| `docs/evidence/m1-*.json`, `scripts/m1_consensus_spike.py` | historical M1 record | **not changed** — evidence is not edited |
| `scripts/m5_gate.py` | `OLD_NAME = "Contest Receipt"` | deliberate — it is the check that the old name is *gone* |

**Why the contract keeps its name.** A file's name is part of the record of what
was measured: M0 through M5 all cite `contracts/contest_receipt.py`, six scripts
and the whole direct suite reference that path, and the deployed contract's
identity comes from its content, not its filename. Renaming it would touch every
evidence row for no product benefit.

The contract's **docstring** is the one genuinely arguable case — it is the first
line a reviewer reads on the deployed source at M8, and it will say "Contest
Receipt" while the product is DeReceipt. It is a comment, so changing it is
behaviour-free. **I left it alone** because M5 is scoped to the frontend and the
honest move is to flag it rather than quietly widen the milestone. It is a
one-line change whenever you want it.

## Reproducing

```bash
.venv/bin/python scripts/m5_gate.py                        # 33 checks, incl. live reads
.venv/bin/python scripts/m5_gate.py                        # again, if you changed anything
cd frontend && npm run build                               # dist/
node frontend/.m5-verify-build/verify-reads.mjs            # 27 live read checks
bash run_direct_tests.sh                                   # 92 tests
GENVM_VERSION=v0.6.0-rc5 .venv/bin/genvm-lint check contracts/contest_receipt.py
```

Deployed contract: `0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D`, Studio-dev chain
61997, finalized, holding a real frozen receipt on programme `0`.