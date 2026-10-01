# Implementation handoff — Contest Receipt

Paste the block below into the implementation session. It is written to stand
alone: that session gets none of this conversation's context.

**Prefer to start in the implementation session itself.** Open `/home/unify/traige`,
load the `hackathon-build` skill, and paste the prompt. If you want a
planning-only pass first, use the short prompt at the end.

---

## What to paste

```text
You are implementing a GenLayer Intelligent Contract product. Work in
/home/unify/traige. Start with the $hackathon-build skill.

The full plan is already written and researched. Read it before writing any code:

1. state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md
   Read sections 0-5 completely, then 7-10. This is the specification.
2. state/reviews/2026-10-01-hackathon-discovery/HANDOFF.md
   Section 3 (verified GenLayer program rules) and section 5 (competitor
   evidence).
3. state/reviews/2026-10-01-hackathon-discovery/evidence/reference-360-build/
   My previous submission, which scored 360/400. Its patterns are adopted
   deliberately. Read typed_grant_covenant.py FIRST and note that it contains
   no LLM call at all — that is the single most important thing this plan
   learned. Then read ARCHITECTURE.md and VERIFICATION.md, which document both
   what earned the score and the three gaps that cost the missing points.
4. Current GenLayer docs:
   https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
   https://docs.genlayer.com/developers/intelligent-contracts/when-to-use-genlayer
   The docs must be re-read against the live target; they have drifted from the
   pinned runner hash in the reference build.

WHAT TO BUILD: "Contest Receipt" — a GenLayer app for auditable verdicts in
AI-judged hackathons and grant rounds. The organizer publishes a program; builders
submit a repo pinned to an immutable commit; the contract freezes that evidence and
derives a receipt; a losing entrant can stake a challenge against ONE named
criterion; and the program publishes its own overturn rate. Plan section 2 has the
one-sentence pitch and section 3 has the exact mechanism.

TARGET: GenLayer Studio-dev, chain 61997. Config is already in the project .env
(GENLAYER_STUDIO_DEV_RPC, GENLAYER_STUDIO_DEV_CHAIN_ID, GENLAYER_PRIVATE_KEY,
DEPLOYER_ADDRESS). Network is temporary and resets, so every step must be
re-runnable from scratch.

FOLLOW THE MILESTONE SEQUENCE: M0 -> M1 -> M2 -> M3 -> M3.5 (optional) -> M4 ->
M5 -> M6 -> M7 -> M8. Each has a stated gate. Do not start a milestone until the
previous gate passes, and if a gate fails, stop and report it rather than working
around it.

M3.5 is the only milestone you may cut. Everything that earns points is
deterministic. If you are running late, cut M3.5 — never M4 or M6.

START AT M0 ONLY. Probe the runner hash and confirm a stub contract lints,
deploys and reaches Finalized on chain 61997. Do not write the real contract
until that gate passes. Then report back to me before continuing.

NON-NEGOTIABLES (these are measured facts, not preferences):
- Nothing is done until its observation exists. docs/VERIFICATION.md starts with
  every row "pending". Never pre-claim.
- Never write a secret into the repo, a log, a doc, or a commit. Read keys from
  the environment only. The deploy script must refuse to persist a key anywhere
  inside the checkout.
- Never print or persist a secret's value in any output. Report variable names
  and whether they are populated, never the values.
- There is a local SQLite database variable in your .env. Do not use it. The
  contract is the record; a second source of truth reads as an off-chain
  dependency to a reviewer.
- "raise" is forbidden in any method that received value — a revert in a payable
  method strands that value.
- Never combine a block-clock read with a value transfer in one method. Studio-dev
  has a fee-estimator bug (~664-day-stale clock) that makes that combination
  revert.
- Transfers must use gl.evm.contract_interface. The plain on="finalized" path
  produces receipts with skipped=true and the balance never moves.
- Only a 404 from GitHub is a business rejection. 403, 429, 5xx, empty body and
  non-JSON are all UNDETERMINED, never FAIL. The GitHub API is unauthenticated
  from validators, so rate limits are expected.
- The exclusions in plan section 8 are binding. A narrow finished honest slice
  beats a broad unfinished one — a rejected submission costs one of two weekly
  slots, and the slot resets Monday 00:00 UTC.
- Publish failures. A negative observation with transaction IDs is worth more to
  a reviewer than a paragraph claiming success.
- Docker is unavailable in this environment. Direct tests must not require it,
  and the docs must say so plainly rather than pretending.
- The desktop browser tool is unavailable. The wallet flow is user-driven and
  the evidence must be labelled
  "user_reported_manual_browser_plus_independent_explorer_check". Do not claim an
  agent-observed wallet result and do not substitute a simulated provider.

DO NOT SUBMIT TO THE PORTAL. Not at any point. Report back and I will review
before anything is submitted.

REPORT BACK WITH: the runner hash and GenVM version you verified; the M1
convergence number; the deployed contract address; the full transaction ID list
with lifecycle status; the final contract balance; the test count and the pytest
output line; the Vercel URL; and an honest list of anything still unverified.
I will review it against plan section 9 and tell you what to fix.
```

---

## Answers to the three open questions

The plan blocks on these only for M6. Fill them in when you have them.

1. **The 400 scale.** `IMPLEMENTATION-PLAN.md` §1 assumes the target is the
   Projects top band (3,200–4,000). If 400 *was* a Projects score, tell me and I
   will re-derive the target. The build does not change either way.
2. **Which weekly slot.** Recommended: build against **Mon 2026-10-05**, which
   gives 2 fresh slots. Do not attempt the Sun 2026-10-04 slot — M0–M3 alone is
   ~11 h, and a half-build burns a slot.
3. **Three demo repos at pinned SHAs**, needed for M6: one healthy, one whose
   declared stack does not match its tree, one with a post-deadline commit if you
   have one. I will not choose repos to freeze on a public chain without you.

If you have not decided, the implementation session can start on M0 anyway — it
is environment verification, costs ~1 h, and touches none of the three.

---

## Planning-only start (alternative)

If you want the implementation session to plan before it builds, paste this
instead of the block above:

```text
You are implementing a GenLayer Intelligent Contract product. Work in
/home/unify/traige. Start with the $hackathon-build skill.

Read state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md in full,
plus HANDOFF.md sections 3 and 5, plus
state/reviews/2026-10-01-hackathon-discovery/evidence/reference-360-build/
(my previous 360/400 submission — read typed_grant_covenant.py first, it has no
LLM call at all, which is the key lesson).

Do NOT write code yet. Produce instead:
1. Confirmation of the M0 runner hash and GenVM version, probed against
   GENLAYER_STUDIO_DEV_RPC. Your repo uses py-genlayer:5jycge4q8k… and the
   current docs say py-genlayer:1jb45aa8ynh… — resolve this before anything else.
2. The exact contract method signatures and the state enums for plan section 3,
   including which method reads the clock and which moves value.
3. The test list for M4, mapped to the 12 groups in the plan.
4. Any place where you think the plan is wrong, with evidence. If you think the
   deterministic/LLM split is wrong, say so and say what you would do instead.
5. Confirmation of the Studio-dev quirks in plan section 4.2 against the live
   endpoint, if you can check them cheaply.

Flag anything ambiguous rather than guessing. Do not submit anything to the
Portal.
```

---

## After the report comes back

Bring it here. I check it against `IMPLEMENTATION-PLAN.md` §9 — nineteen
acceptance rows, all currently `pending` — and specifically:

- every acceptance row has a real observation, or is honestly marked unverified
- the runner hash is the one the live target reported, not a copy
- the contract balance **actually changed** (a posted message is not a payout)
- `raise` appears in no payable method
- no clock read shares a method with a transfer
- test count is 45+ and the pytest line is pasted verbatim
- the evidence JSON was generated by reading the chain, not typed
- Studio-dev was not treated as durable anywhere in the docs

Then we decide whether to fix, or submit.
