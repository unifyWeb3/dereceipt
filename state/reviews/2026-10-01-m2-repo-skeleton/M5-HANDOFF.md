# M5 handoff — the real frontend

M4 accepted. Send the block below.

```text
M4 is reviewed and accepted. 92 tests reproduced on my side, 16/16 mutations
proven red, five real defects found — three of them stranded money. That is the
best milestone so far. Read state/reviews/2026-10-01-m4-direct-tests/REVIEW.md.

Read first:
1. state/reviews/2026-10-01-m4-direct-tests/REVIEW.md
2. docs/VERIFICATION.md sections M0-M4 — match the vocabulary, status columns and
   evidence discipline.
3. docs/ARCHITECTURE.md — twelve hard rules now, the state model, the exclusions.
4. frontend/src/main.js and style.css — the M2 shell you already wrote. It
   already throws on Undetermined/Canceled and renders business state and
   lifecycle state in two separate regions. Extend it; do not start over.

MILESTONE: M5 ONLY — the real frontend. Nothing else.

You now have a real contract with a proven payout path, real per-criterion
verdicts, a challenge log, an accuracy block, a receipt digest, and a refund
path. The UI's job is to make the receipt legible.

THE PRODUCT HAS NO NAME YET. Do not invent one. Keep "Contest Receipt" as the
working title and make it a single constant so it is trivial to change later.

MUST HAVE:
- Wallet connect via EIP-1193. Enforce chainId 61997, and fail loudly and
  helpfully on any other chain. Do not silently proceed.
- program_id is a STR. get_program(0) fails with code=-32000 while
  get_program("0") returns the record. It is silent and reads as a broken view.
  I hit this during M3 review. Every call site must send a string, and add a
  runtime assertion so a future int slips in loudly rather than silently.
- waitForFinalizedLifecycle polling gen_getTransactionLifecycle, throwing on
  Undetermined and Canceled. Never treat a submitted hash or an ACCEPTED state
  as success.
- Business state and lifecycle state stay in two visually separate regions. This
  is rubric criterion 4 and reviewers inspect it directly.
- UNDETERMINED and INCONCLUSIVE are first-class expected outcomes with their own
  styling — not error toasts. A jury that cannot settle a criterion is the
  product working, not failing.
- The receipt view: per-criterion verdicts, the contested list, the challenge log
  with grounds and outcomes, the accuracy block, and the receipt digest with a
  copy button.
- The organizer path: open a programme, see the locked pool, cancel with refund,
  finalise. Show that cancel actually moved value.
- Explorer deep-links for every transaction ID. The Studio-dev explorer is
  explorer-studio-dev.genlayer.com and returns 503 intermittently, so handle a
  failed link gracefully rather than blocking a render.
- Every write goes through one writeAndWait helper. No second code path.

A LABELED, NOT-BUILT SURFACE. The product has no frontend for the entrant
challenge bond flow and none for claiming a payout entry-by-entry until those
paths are exercised at M6. Do not fake a control for a path you cannot demo. An
honest "not yet available on this deployment" beats a button that reverts.
Say which surfaces you left out and why.

Do NOT: add a database. Introduce a framework — vanilla JS plus genlayer-js and
viem is what shipped 360/400 and it is what the lockfile pins. Add a state
library. Build a framework-routed multi-page app. Inline a wallet private key
anywhere. Emit a key or a secret into any log or console statement.

M5 does NOT need a fresh deployment. Point the frontend at an existing deployed
contract and read its real state. If you deploy anything, use
scripts/deploy_studio_dev.py, which exits non-zero when a transaction does not
reach finalized.

Gate: npm run build succeeds; the built page serves and references its hashed
asset; every read path works against the real contract with program_id as a
string; UNDETERMINED renders as a state, not a toast; no key material in dist/.

REPORT BACK WITH: the screens built and the ones deliberately left out with
reasons; how the str program_id assertion is enforced; confirmation that the
built bundle contains chain 61997 and the Studio-dev RPC; a key-material scan of
dist/; and anything you could not build against because the contract does not
expose it. Then stop and wait. Do not submit anything to the Portal.
```

---

# Notes for the human — not instruction for the agent

## Your question about naming and hosting — you are right, and it blocks submission

The Portal's `required_evidence_url_types` for the Projects track is **exactly
one item: a GitHub repository**, validated against
`^https?://github\.com/[^/]+/[^/]+/?$`. No repo means the form will not accept
the submission. This is not a nice-to-have; it is the one hard requirement.

Three things are missing, in dependency order:

| # | Missing | Blocks | Decide |
| --- | --- | --- | --- |
| 1 | **Product name** | M5 copy, README title, demo script | **Yours** |
| 2 | **Public GitHub repo** | M8 submission, hard requirement | **Yours** — the 360 build used `unifyWeb3/milestone-convenant`; a new repo under the same org keeps the track record together |
| 3 | **Vercel deployment** | M8, and "frontend genuinely calls the contract" is much easier to verify from a URL | **Yours** — needs a Vercel account and one public build variable |

The 360/400 build had all three: `unifyWeb3/milestone-convenant` and
`milestone-convenant.vercel.app`. Same pattern, same org, proven to work.

**Why this matters for scoring, not just mechanics.** Two of the five Projects
criteria are checkable *only* from outside:

- Criterion 3, *"complete source code and accurate docs"* — a reviewer reads the
  repo. A local folder does not exist to them.
- Criterion 4, *"frontend genuinely calls the contract and handles the full
  transaction lifecycle"* — a reviewer opens a URL and clicks. If they cannot, the
  criterion is unfalsifiable, and reviewers score what they can check.

The optional accepted-evidence list also pays for a **GenLayer Studio contract**
and a **GenLayer Explorer contract** URL, which are worth extra points and
expedite review. Both need the public repo and a public deployment to reference.

**Recommendation:** decide the name now, before M5 writes copy. M5 is where the
name gets typed into the UI, the page title and the README. Renaming after M5
means touching every string. If you want a default, my suggestion is to keep the
working title and not spend time on this — a clear name beats a clever one, and
the differentiation is the receipt, not the branding.

**Also still open: the M6 demo repo set.** Defect 5 from M4 made step 5 more
load-bearing than I planned — `AFTER_DEADLINE_WORK` was decorative because the
evidence URL was compared for equality against a commit SHA. That ground now has
to resolve on chain, which needs a real post-deadline commit. Three repos:

1. healthy, real README, recent commit
2. declared stack that contradicts its tree
3. a commit dated after the deadline

## Sequence

| | What | Gate | Status |
| --- | --- | --- | --- |
| M0–M3 | ✅ | 14 methods, refund proved live | done |
| ~~M3.5~~ | skipped | | |
| **M4** | 92 tests, 16 mutations | ✅ reproduced | done |
| **M5** | real UI | next | |
| M6 | live run, 12 steps | **needs the repo set** | |
| M7 | docs | | |
| M8 | deploy + submit | **needs name + public repo + Vercel** | |

M5 does not need the demo repos. M6 does. M8 needs all three of your decisions.