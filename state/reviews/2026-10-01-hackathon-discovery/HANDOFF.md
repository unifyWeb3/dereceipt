# HANDOFF — GenLayer Builders Program, Projects track

Discovery pass for a solo submission to the **Projects** contribution type
(`slug: projects`, id 41) on the GenLayer Portal.

- **Researcher:** OpenCode, `hackathon-discovery` skill
- **Date of research:** 2026-10-01
- **Constraints supplied:** solo team, 18 hr/day, $0 budget, no tech constraints
- **Idea supplied:** "decentralized grants and hackathon evaluation platform built on GenLayer"
- **Status:** research + plan only. Nothing has been built. No accounts created, no funds spent, no submissions made.

---

## 1. Recommendation

**Do not build the supplied idea as described. It is already built, deployed, and published on GenLayer, and a third rebuild is the single most likely way to fail criterion 5 of the Projects rubric.**

The supplied idea — AI-validator-consensus judging of hackathon and grant submissions — exists today as
[**Hackathon Judge**](https://explorer-studio.genlayer.com) by `demigodd`
(`github.com/Demigodd00/demigodd00-genlayer-apps`, 70 commits, 526 tracked files
across a multi-product monorepo,
`contracts/hackathon_judge.py` = 1,193 lines, plus a 76 KB per-criterion
`hackathon_judge_scorecards.py` variant) and as
[**GrantJudge**](https://github.com/kenil1710/grantjudge) by `kenil`
(MIT, 54 commits, 930 offline tests, 5 contract milestones, live on Studio Dev
chain 61997). Both are in the Project Explorer with `deployment_status: verified`.

`evidence/competitor-hackathon-judge-contract.py` is a saved copy of the
competitor contract. Reading it confirms the overlap is not cosmetic — the
competitor already does: rulebook + rubric + deadline + appeal window + prize
escrow, evidence snapshot with SHA-256 digest at submission, prompt-injection
hardening on untrusted submission text, a bounded 0/20/40/60/80/100 score band,
per-decision consensus with a ±20 confidence tolerance, one evidence-based
appeal, permissionless finalization, an inconclusive timeout, and refunds.

**Recommended alternative: keep the same customer, change the artifact.**

> **Build the jury's accountability layer, not another jury.**
> The differentiator is that the verdict is *auditable and challengeable* —
> evidence frozen at submission, the disagreement between validators made
> public per criterion, a staked challenge against one named criterion, and a
> permanent per-program record of how often challenges succeed.

Why this clears the bar the original idea fails:

- It is not "a better LLM response." Its value is that a wrong or rigged
  outcome is now *detectable and contestable*, which is the trust problem.
- It maps to the two genuinely empty cells in the Explorer: **0 of 219**
  projects publish any agreement / consensus / overturn statistic, and **0 of
  219** anchor a decision to a point in time rather than to whatever the page
  says at judging time. (Reproduce: `python3 evidence/competitor-gap-probe.py`.)
- The customer's pain is not "I need a score." It is "I must announce a winner
  I can defend to a sponsor and to the runner-up." Every incumbent stops at the
  score; none of them let anyone audit the jury.

This recommendation is a **clarification of your idea, not a replacement**. The
customer, the moment, and the payout are unchanged. If you decide you would
rather ship the original framing anyway, §6 records what that costs.

---

## 2. Value-articulation result (six gates)

| Gate | Answer | Specificity check | Status |
| --- | --- | --- | --- |
| **Moment** | Hackathon/grant organizer, 3–10 days after the submission deadline, must publish winners before a ceremony or sponsor announcement, with volunteer judge-hours already exhausted. A runner-up who lost on one criterion disputes. Today the options are: re-run the panel by hand (2–5 days, inconsistent between rounds) or concede and absorb a public "judging was rigged" thread. | Named role, named deadline, named failure cost. A person would initiate this unprompted. | **pass** |
| **Reframe** | Category by problem: **contest results defensibility** — the same budget line as Devpost for Teams and HackHQ, not a new "AI" category. Reframe test: if GenLayer vanished overnight, would anyone still pay? Yes — the job is "produce an auditable result and settle challenges cheaply"; the jury is one way to staff it. | Names the incumbent and the price reference. | **pass** |
| **Substitute** | HackHQ (organizer plan, 40+ events, 900+ participants, 400+ submissions, 14,000+ scores processed — a paid product with a free tier for small events); Devpost for Teams (multi-round judging, but its own help centre states it *"does not currently support weighted judging"* and routes that to a spreadsheet); volunteer judges plus a tally sheet. None of them has an evidence-based challenge or second-opinion mechanism — disputes are handled by organizer email. | Substitute named, incumbent named, and its feature gap quoted from its own docs. | **pass** |
| **Payer** | The narrowest buyer who can pay: **the organizer of a sponsor-funded program with a public announcement** — a company innovation program, a foundation hackathon, or a university lab with corporate sponsors. Budget line is event operations / judging. Reachable because the organizer population is public and self-identifying (MLH publishes an organizer guide to thousands of student organizers; HackHQ's entire audience is this buyer). | One segment, one budget line, one channel. | **pass, with a reachability caveat** |
| **Repeat** | The next event, 1–4× per organizer per year. Plus a genuine compounding hook the incumbents lack: the per-program accuracy record is worth more after five programs than after one, so it is a portfolio, not a job. | Second purchase trigger named. | **pass** |
| **Payment evidence** | **Level 3 — users demonstrably spend on the substitute today.** HackHQ sells event plans; Devpost for Teams is a paid product; Superteam and Code4rena pay judges in cash. **No evidence anyone pays for jury accountability specifically.** That second half is the hypothesis, not the fact. | Level stated explicitly, and the borrowed-from-substitute evidence is named as borrowed. | **weakest gate** |

**Weakest gate: payment evidence.** The paid substitute is real; the
*accountability* feature is not yet paid for by anyone. The cheapest credible
upgrade is a paid pilot or a signed letter of intent from one organizer — not
more desk research. Do not contact anyone without your authorization.

---

## 3. Verified event and program constraints

All retrieved **2026-10-01** from the Portal's own API
(`https://portal-admin.genlayer.foundation/api/v1/`), which is the same backend
the portal UI reads. Snapshots saved under `evidence/`.

### The Projects track

| Field | Value | Source |
| --- | --- | --- |
| Name / slug / id | Projects / `projects` / 41 | `GET /api/v1/contribution-types/41/` |
| Description | "Complete GenLayer apps, products, or platforms, where GenLayer is central to the main workflow. A Project has a clear use case, one or more real Intelligent Contracts, and app logic (frontend or backend) that actually interacts with GenLayer." | same |
| Points range shown in UI | **20 – 4,000 pts** = `min_points 1 × multiplier 20` … `max_points 200 × multiplier 20` | `min_points:1, max_points:200, current_multiplier:20.0` |
| **Weekly limit** | **2 Project submissions per user per week** | `max_submissions_per_user_per_week: 2` |
| Weekly window | **Monday 00:00 → Sunday 23:59 UTC**, resets Monday 00:00 UTC | portal UI strings: "Monday 00:00 to Sunday 23:59 UTC", "Resets Monday 00:00 UTC" |
| **Your capacity** | You reported "1 spot left" — the UI renders the literal string "1 spot left" when `user_weekly_submissions_remaining === 1`. You have used 1 of 2. | `max_submissions_per_user_per_week` + UI string `1 spot left` |
| **Your current week** | Mon 2026-09-28 00:00 UTC → **Sun 2026-10-04 23:59 UTC**. Next reset **Mon 2026-10-05 00:00 UTC** (2 fresh slots). | computed from the stated window and today's date |
| Global cap | **None.** `max_submissions: null`, `is_full: false`. | API |
| **Deadline** | **There is no global deadline.** The Projects type carries no start or end date (only `created_at` / `updated_at`). The programme is described as "Open-ended contribution paths for builders, validators, and creators." Rolling weekly caps, not a closing date. | API field audit + UI string |
| Submissions to date | **2,382** Projects submissions; 219 published in Project Explorer | API + `GET /api/v1/explorer/` |
| Required evidence | **A GitHub repository** (`github-repo`, regex `^https?://github\.com/[^/]+/[^/]+/?$`). Nothing else is required at submit time. | `required_evidence_url_types` |
| Accepted-evidence types that earn extra points and speed review | X post, YouTube Short, GitHub repo/file/PR/issue, **GenLayer Studio contract**, **GenLayer Explorer contract**, other | `accepted_evidence_url_types` |
| Review flow | `builder_project`, `requires_ai_review: true`, `escalation_threshold_points: 500`, `rubric_extra_points: 2` | API |
| Human layer | A **Builder Council** — "trusted builders who assist with reviewing incoming Projects & Milestones submissions. Council members score submissions against the five criteria, provide a short justification, and surface a recommendation. Invitation-based." | contribution type id 46 |

### Eligibility

- You must hold the **Builder** role. Portal gate: *"Complete the Builder Welcome
  journey to submit builder contributions. Start from your profile page."*
  (contribution type id 34, "Builder Welcome"). If you have not already claimed
  the Builder role, this blocks you and is the first thing to clear.
- Wallet connection is required to submit (auth is wallet-based).
- No Discord role or linked social account is required for Projects
  (`required_discord_roles: []`, `required_social_accounts: []`).

### The Projects quality bar — all five criteria, verbatim

Recovered from the portal bundle (the criteria are the five items the Builder
Council scores against):

1. **Solves a real trust problem.** Not just a better LLM response.
2. **Uses live or authoritative data** when outcomes depend on real-world facts.
3. **Complete source code and accurate docs.** Submission notes must explain
   what it does, the problem it solves, and how to use it.
4. **Frontend genuinely calls the contract** and handles the full transaction
   lifecycle.
5. **Meaningfully different from boilerplate, from contracts that already exist
   in the ecosystem, with a credible path to continued use.**

Criterion 5 is the one the supplied idea fails.

### Post-submission mechanics (worth knowing before you spend your slot)

- **Accepted → Rejection.** "The use case or implementation falls short. Fixes
  or new evidence require a new submission, **which uses a slot**." A rejection
  costs you one of your two weekly slots.
- **Appeal** challenges only the original decision, with the work as submitted.
  **Does not use a slot.**
- **"We see a path to acceptance and need details"** — you may update the
  existing submission. **Does not use a slot.** This is the recovery path to use
  if a reviewer asks for clarification instead of rejecting.
- **"The same work does not count twice."**
- *live demos, videos, and public posts earn extra points and speed up review.*
  Budget time for an X post and a short demo video.

### Unresolved rule questions (could not be verified from public sources)

- The published weights for the five criteria are **not** exposed. The API
  exposes `rubric_extra_points: 2` and `escalation_threshold_points: 500` but no
  per-criterion weight. Do not assume equal weighting.
- The meaning of `escalation_threshold_points: 500` (presumably: above 500 points
  an extra escalation step runs) is inferred, not documented.
- Whether the **Builder Welcome journey** can still be completed today, or only
  by accounts that held Builder before the journey launched, is not stated. The
  related Agent Tank string says "or use the membership you already earned
  before the journey launched," which hints the gate may be closed to new
  accounts for some contribution types. **Check this on your own account first —
  it is a hard gate and costs nothing to verify.**
- No published statement on whether re-submitting a *materially reworked* project
  counts as "the same work."

---

## 4. Chosen-idea assessment and comparison

### Candidates

| | **A. Supplied idea** — consensus-judged hackathon & grant evaluation | **B. RECOMMENDED** — Jury accountability layer (frozen evidence + per-criterion disagreement disclosure + staked single-criterion challenge + public accuracy record) | **C. Mechanical entry-validity screen** — deterministic pre-judging disqualification |
| --- | --- | --- | --- |
| User pain | Real but **already served here** | Real and **unserved**: nobody can audit a jury's verdict | Real but small: a slice of disputes |
| Existing alternatives on GenLayer | **48 direct competitors** in 219; Hackathon Judge and GrantJudge are exact | **0 of 219** publish an agreement or overturn statistic; 0 use a point-in-time anchor; 1 exposes per-criterion detail | **0 of 219** check link/asset validity |
| Rubric fit | **Fails criterion 5** | Hits 1, 2, 4, 5 cleanly; criterion 3 is table stakes | **Fails "GenLayer is central"** — docs list deterministic checks as the case *against* GenLayer |
| Payer | Weak: hackathon organizers already pay for a human-judging platform | Same payer, sharper job | Weakest: nobody budgets for "disqualification screens" |
| Feasibility (solo, 18 hr/day, $0) | Feasible but pointless — you would be the 49th | Feasible: one contract + one frontend | Feasible but wrong tool |
| Time to demonstrable result | Fast | 2–4 days (see §7) | 1 day |
| **Verdict** | **Do not build** | **Build** | **Fold into B as a component**; not a standalone submission |

Candidate C is kept only because it is cheap and it plugs a real hole — a
demo URL that 404s or a repo that is private is a boring, deterministic
disqualification. It belongs inside B's submission-time freeze step. Standalone
it would fail the "GenLayer is central to the main workflow" requirement,
because a deterministic check belongs in a normal contract.

### What the user's idea gets right, and should be kept

- Choosing a category where a *human panel's inconsistent, unauditable judgment*
  gates real money. That is a genuine trust problem.
- Putting the decision on-chain so the organizer cannot change a rubric or a
  score after the fact. Competitors state this well; GrantJudge's version —
  *"there is no method in this contract by which a treasurer changes a rubric, a
  score, a ranking or an award"* — is the right instinct.
- Frontend genuinely driving the full transaction lifecycle.

### What it gets wrong

- It competes on the artifact ("AI consensus judge") in the one ecosystem where
  that artifact is the most-built thing on the platform.
- Its pitch is innovation language. "Replaces human judging panels with AI
  validator consensus" names a means. The customer's sentence is "I have to
  announce a winner on Friday and the runner-up says the panel was rigged."
- It ignores the part that actually breaks in practice: the *dispute*, not the
  scoring. Every one of the 21 projects with an appeal mechanism re-judges the
  same way and moves on. None of them tells anyone how often they were wrong.

---

## 5. User and competitor evidence

Every claim below is tied to a source inspected directly. Marketing copy is
labelled as a claim, not as established fact.

### The customer's problem is real and quantified

- MLH's public organizer guide gives the arithmetic judges actually face:
  `J = ceil(P × n × t / T)`, with `n = 3` rounds per project and `t = 4` minutes
  per project. **175 projects in a 2-hour judging window requires 18 judges.**
  Their lookup table: 500 projects → 34 judges. Source:
  `github.com/MLH/mlh-hackathon-organizer-guide/.../judging-plan.md`
  (retrieved 2026-10-01). *Evidence strength: high — first-party organizer
  guidance, still maintained for the 2026 season.*
- MLH's 2026 season averages **1 submitted project per 4 checked-in hackers**
  (same source). Judge supply is the binding constraint, which is exactly where
  a machine jury would be bought.
- HackHQ sells the paid substitute and reports real volume: 40+ events, 900+
  participants, 400+ submissions, 14,000+ scores processed; the Better Auth
  hackathon at Y Combinator ran **37 submissions with 11 judges in under 45
  minutes**. Source: `hackhq.io/about-us`, `hackhq.io/features` (retrieved
  2026-10-01). *Evidence strength: medium — vendor-reported, not independently
  audited, but it is a specific named event with numbers.*
- The incumbent feature gap is quoted from Devpost's own help centre: *"The
  platform does not currently support weighted judging. If you need this,
  contact your Devpost for Teams lead. They can help you with this process via a
  separate spreadsheet."* Source: `help.devpost.team/article/231` (last updated
  2026-01-23). *Evidence strength: high — first-party documentation.*
- Disputes are handled by hand today: MLH's rules and HackHQ's docs describe no
  evidence-based appeal path, and Supabase's hackathon docs end at "submit your
  votes." *Evidence strength: medium — absence of a documented feature across
  several first-party docs.*

### The GenLayer-side competition, in detail

Snapshot: `GET /api/v1/explorer/`, 219 projects, retrieved 2026-10-01. Saved as
`evidence/portal-explorer-projects.json`. Counts reproduced by
`evidence/competitor-gap-probe.py`.

| Probe | Count | Notes |
| --- | --- | --- |
| Direct competitors (judge/grant/bounty/hackathon **and** score/review/milestone) | **48 of 219** | includes Hackathon Judge, GrantJudge, AirJudge, GrantGate, GrantAuditor, TrustGrant, MilestoneJudge, Milestone Forge, ImpactDNA, Reverse Spec, AuditBounty, OSS Judge, BountyCourt, TrustRail, Proof Bounty |
| Claims to replace human judging | 3 | AuditorShield, GrantAuditor, TRIBUNAL |
| Any appeal mechanism | 21 | appeals are commodity |
| Per-criterion consensus | 5 | BountyCourt, GenHire, GrantGate, ProofOfShip, VerdictGraph |
| Per-criterion breakdown on the public record | 1 | GenHire |
| **Publishes an agreement / consensus / overturn statistic** | **0** | *the gap* |
| **Anchors the decision to a point in time, not judging time** | **0** | *the gap* |
| Submit-time evidence freeze (claimed in description) | 1 | ClaimRegistry v3; Hackathon Judge does it in code but does not claim it |
| Immutable commit ref | 7 | BountyCourt, GrantGate, ReleaseProof, … |
| Weighted scoring / rubric | 56 | saturated |
| Escrow or payout | 97 | saturated |
| Mechanises a human escalation | 9 | GrantAuditor's ESCALATE, AuditorShield, … |

**Deep reads on the three closest:**

- **Hackathon Judge** (`demigodd00-genlayer-apps`) — read the contract, not just
  the README. `submit_project` calls `_capture_evidence` and stores
  `evidence_digest` (SHA-256) + `evidence_snapshot`; `_judge` re-runs the prompt
  independently in `validator_fn` and compares only `eligibility`, `score_band`,
  and `confidence_bucket ± 20`; `resolve_appeal` re-runs the **same** `_judge`
  with `is_appeal=True` over the whole record. It never stores or publishes how
  many validators agreed, nor any overturn rate. Full copy saved as
  `evidence/competitor-hackathon-judge-contract.py`
  (sha256 `dce90861bfed…`). *This is the direct competitor, and the reason
  candidate A is not recommended.*
- **GrantJudge** (`kenil1710/grantjudge`, MIT) — the most complete submission
  I inspected: 930 offline tests, five milestone features, twelve explicitly
  documented "rejection rules", a two-instance deploy (canonical + fast-clock),
  chain-readback evidence generation, and an honest write-up of a Studio Dev
  limitation. Its `"GenLayer does exactly one thing"` framing is the correct
  instinct. *Evidence strength: high — I read the full README; I did not run the
  code or the deployment.*
- **TrustRail** (`keplr32b/trustrail`) — the closest thing to reusable
  infrastructure: *"the exact same contract, unmodified, was deployed for two
  unrelated domains."* If you build candidate B, this is the reuse-shaped
  alternative to writing your own. Not inspected beyond the Explorer entry.

### Ecosystem support for the recommended wedge

GenLayer's own Builder Program is a working, named instance of the wedge, which
is the strongest available evidence that the pattern is what a real program
operator wants:

- Every builder-facing type carries `requires_ai_review: true`, including
  Projects. (This is *not* true of the whole catalogue: the validator,
  community and quiz types have it `false`.)
- The **Builder Council** exists to review Projects and Milestones — trusted
  builders "score submissions against the five criteria, provide a short
  justification, and surface a recommendation."
- `escalation_threshold_points: 500` implies a machine pass with a human
  escalation above a threshold.

That is precisely "machine pre-screen, human decides the contested slice." A
program with **2,382 Project submissions** and a Builder Council staffed by
invitation is a program that cannot absorb unbounded human review. *Evidence
strength: high for the mechanism, inference for the motive.*

### Weak or absent evidence — stated plainly

- **No user has been interviewed.** No organizer, judge, or foundation officer
  was contacted. Nothing here is level-1 or level-2 payment evidence.
- **21 of 219 Explorer projects have ratings; 198 have none.** Explorer
  engagement is near zero, so "adoption strengthens the case" is not currently
  satisfiable by pointing at Explorer traction. The only featured projects are
  the Foundation's own: Rally, Collective Memory, Internet Court, MicroMarkets,
  Antseed.
- **Deployment maturity is low across the field.** Of 219 projects, 182 declare
  exactly one network and 31 declare none; network tags overlap because 6
  projects declare two. By tag: Studio 157, Bradbury 27, Studio Dev 7, Asimov 3.
  Almost nothing is on a network with real economic consequence. *Readiness, not
  adoption, is what differentiates today* — which is a lever you can use.
- **Not inspected:** live UIs of the competitors (no browser available in this
  session), the 42 direct competitors not named above, non-GenLayer
  alternatives beyond HackHQ/Devpost/MLH, and any private organizer data. I do
  not claim to have surveyed every competitor.

### What would overturn this recommendation

1. A named organizer saying they will *not* use a machine jury at all — the
   market may be human-panel-bound, in which case the accountability layer
   serves an audience that does not exist yet.
2. Evidence that Hackathon Judge or GrantJudge is abandoned, unlicensed, or
   broken in a way that leaves the slot genuinely open. (GrantJudge is MIT;
   Hackathon Judge's repo is proprietary with an all-rights-reserved LICENSE, so
   code reuse is not available from it.)
3. A discovery that the Projects track's acceptance is currently so low that the
   expected value of any submission is near zero — in which case the correct
   advice is to skip the track this week and use the slot on Milestones or a
   smaller type.

---

## 6. Cost of building the supplied idea anyway

If you choose candidate A over candidate B, expect:

- **Rubric criterion 5 to be the rejection reason.** "Meaningfully different
  from boilerplate, from contracts that already exist in the ecosystem" is
  checked against a 219-project Explorer that already contains your idea twice,
  both times more completely than a 3-day solo build will be.
- **A rejection costs a weekly slot.** Only 2 per week. The recoverable path is
  the "we see a path to acceptance and need details" update, which does not
  cost a slot — but it requires that reviewer to want the work.
- Your differentiator would have to be narrower than "consensus judging" and
  would end up close to candidate B anyway. The cheapest way to make A
  submittable is to make it auditable.

---

## 7. Bounded MVP for the recommended candidate

**Name (working):** Jury Ledger — auditable verdicts for AI-judged programs.

**Primary user:** the organizer of a sponsor-funded hackathon or grant round
who must publish a result they can defend.
**Who pays:** the same person, out of event-operations budget.
**If the build targets someone other than the payer, say so:** it does not. The
builder-submission side is the *evidence source*, not the customer. Do not design
the UI around builders — design it around the organizer's Friday afternoon.

### The one decision GenLayer makes

> For one named rubric criterion on one named submission, given evidence frozen
> at submission time, does the archived artifact satisfy that criterion, and how
> close was the validator agreement?

Everything else is deterministic integer arithmetic. This split is the pattern
the strongest accepted competitors use and it is what the rubric's criterion 1
demands: the model is bounded, and the money is never moved by a model.

### Core journey (organizer's view)

1. **Open a program** — name, plain-English rulebook, 3–5 criteria with weights,
   prize pool, submission deadline, appeal window. All snapshotted, no setter.
2. **Builder submits** — repo URL + **immutable commit SHA** + demo URL +
   one-paragraph claim. At submit time, validators fetch the repo at that SHA via
   the GitHub API and the contract stores a **tree manifest + SHA-256 digest**.
   This is the freeze; it is the point-in-time anchor nobody else has.
3. **Mechanical screen** (deterministic, free) — repo resolves, commit resolves,
   demo URL responds, required fields present, no duplicate SHA, before the
   deadline. Folded in from candidate C. Produces `DISQUALIFIED` without spending
   a consensus round.
4. **Run the jury** — per criterion, validators independently re-derive a
   bounded bucket. Consensus per criterion, not on a summary. The contract
   records, for every criterion: the agreed bucket **and the agreement margin**
   (how many validators landed on it vs. the next bucket).
5. **Publish the record** — the organizer gets a per-criterion table, a
   *contested set* (criteria where agreement was thin), and a machine-readable
   accuracy record for the program. The organizer knows exactly which two
   submissions a human needs to look at, and looks at two instead of two
   hundred.
6. **Challenge one criterion** — the losing party stakes to name the single
   criterion they contest and supply new evidence. A second panel re-judges *that
   criterion only*, under a deliberately different prompt formulation. The
   outcome updates that criterion, never the others, and is written to a
   permanent public log.
7. **Finalize** — deterministic ranking and allocation from the agreed buckets.
   Nothing a model produced is ever transferred by a model.

### Essential features

- Program creation with snapshotted, immutable rubric.
- Submission-time evidence freeze (repo at pinned SHA + digest + tree manifest).
- Deterministic mechanical screen.
- Per-criterion consensus with agreement margin recorded.
- Single-criterion staked challenge with a second, differently-framed panel.
- Public, cumulative accuracy record per program.

### Explicit exclusions — do not build these

- No multi-round scoring, analytics dashboards, judge portals, or ceremony mode.
  Those are HackHQ's job and they are not the trust problem.
- No reputation system for judges. It is a whole product and it is not the gap.
- No real-money escrow in the MVP. See the risk in §8 — Studio does not reliably
  execute value transfers. Book the *decision*; book the money separately.
- No general-purpose "bring your own rubric" configurator beyond criteria text
  and weights.

### Differentiator, in one sentence

Every competitor ends at the score; this one ends at **the receipt** — who
agreed, on what, with what margin, and how often the challenge succeeded.

### Hardest technical assumption

That per-criterion consensus over 3–5 criteria will reach agreement often enough
to be usable, and that the agreement margin is a *meaningful* signal rather than
noise. LLM subjectivity is exactly where GenLayer consensus is weakest, and the
competitors all solve it by collapsing to a coarse band (Hackathon Judge uses
0/20/40/60/80/100 precisely because finer buckets do not agree).

**Smallest experiment that would test it — run this before writing the
frontend.** Deploy a throwaway contract that judges one fixed rubric against
three real submissions, for three criteria, and log for each criterion: the
leader's bucket, each validator's re-derived bucket, and whether consensus
succeeded. If per-criterion consensus fails more than about a third of the time
on 3 criteria × 3 submissions, fall back to **consensus on the aggregate score
plus per-criterion buckets recorded but not consensus-critical** — which is what
Hackathon Judge's scorecards variant does. Cost: half a day, and it de-risks the
entire build.

### Interface outline (unverified architectural choices, labelled as such)

- **Placement:** frontend in the browser; no backend of your own. The contract
  is the record. *(Unverified: whether every read you need is available as a
  `@gl.public.view` without an indexer. Assume you need one and design the UI to
  tolerate a slow cold read.)*
- **Auth:** wallet only. No accounts, no email, no OAuth.
- **Data to fetch:** programs, submissions, per-criterion buckets, agreement
  margins, challenge records, program accuracy record. All contract views.
- **Errors to handle, explicitly:** `INCONCLUSIVE` (evidence unreadable or
  missing → no verdict written, appeal or retry), consensus failure → **undetermined,
  no state change** (this is GenLayer's documented behaviour, not an edge case —
  your UI must show it as a normal outcome), appeal window closed, stake
  insufficient, digest mismatch.
- **Pending states:** a consensus round takes real time. Every write that triggers
  consensus needs a pending state with the transaction hash, and the UI must
  survive a page refresh mid-flight. Budget for this; it is the most common
  source of a broken demo.

### First small connected flow to prove the product works

Not implemented here. It is: open a program with 2 criteria → submit one real
repo at a pinned SHA → see the frozen digest on-chain → run the jury → see two
per-criterion buckets with their agreement margins → challenge the weaker
criterion → see it re-judged and the margin change. **If that loop does not work
end to end on Studio, nothing else matters.**

---

## 8. Technical risks and dependencies

### Dependencies — proposed, with official names where they exist

| Need | Service | Config name (documented) | Placement | Cost / quota | Access check |
| --- | --- | --- | --- | --- | --- |
| Contract runtime | GenVM Python runtime | `# { "Depends": "py-genlayer:1jb45aa8ynh…" }` version comment, **required on line 1** | contract | free | Version hash taken from the current docs and from competitor contracts; both agree |
| Deploy / test | GenLayer Studio | Studio UI + `https://studio.genlayer.com/api` | local | free | Open Studio before committing to the build |
| Testnet GEN | Testnet faucet | `https://testnet-faucet.genlayer.foundation/` | browser | free, rate-limited | Claim a little GEN first; a deploy that cannot pay for a message is not a demo |
| Validator-side agent tooling | GenLayer Skills plugin | `/plugin marketplace add genlayerlabs/skills` then `/plugin install genlayer-dev` | local dev | free, MIT | Repo is `github.com/genlayerlabs/skills`; README inspected, contents not |
| Read GitHub at a pinned SHA | GitHub REST API | `api.github.com` | called from inside the contract's non-deterministic block | unauthenticated is rate-limited to 60 req/h per IP | **This is the risk.** Validators run on other machines; an unauthenticated call can be rate-limited per validator. Test with `strict_eq` against the API before relying on it |
| Project scaffold (optional) | `genlayerlabs/genlayer-project-boilerplate` | — | local | free | Referenced by the portal's own resources page; not inspected |
| Chain evidence for your submission | Studio / Bradbury explorer | `https://explorer-studio.genlayer.com/address/0x…` | — | free | Required to earn extra review speed |
| Submission evidence | GitHub repo (required), X post + demo video (optional, earn extra) | — | — | free | — |

**No paid service is required. The $0 budget holds.** Do not add IPFS/Pinata: the
competitors that use it treat the token as server-only and restricted, and it is
unnecessary — pinning a Git commit SHA gives you a stronger immutability
guarantee than content-addressing a rendered page.

### Technical risks, ranked

1. **Studio does not reliably execute value transfers.** GrantJudge documents
   this as measured by three separate projects, three ways each: a transfer
   posted with `on="finalized"` reaches FINALIZED, the message is queued, and no
   balance moves — the contract's real balance read 22.6 GEN while its own books
   said 4.7. *Evidence: `kenil1710/grantjudge` README, "A note on Studio Dev and
   payouts." I did not reproduce this.* **Mitigation: the MVP books the decision,
   not the money.** If you want a real transfer in the demo, deploy to Bradbury
   and test it before you promise it in the submission notes.
2. **Studio Dev fee estimation is wrong for methods that read the block clock
   *and* post a transfer.** The fee simulator runs on a clock ~664 days stale, so
   it simulates the call on the wrong side of its own appeal window; the
   transaction then reverts with `out_of message_fee total`. *Same source;
   GrantJudge's fix is a two-step `claim_remainder_fallback`.* **Mitigation:
   separate every clock read from every transfer.** This is a documented, real
   GenLayer gotcha and separating the two is cheap insurance.
3. **Per-criterion consensus may not converge.** See §7. Test it first.
4. **GitHub API rate limits hit validators, not you.** If the fetch is flaky,
   the failure mode is `INCONCLUSIVE`, not a wrong answer — design for that
   explicitly and make it visible, because an organizer will trust an honest
   "could not reach the evidence" far more than a confident guess.
5. **A single 40 KB snapshot per submission is expensive to store on-chain** and
   may exceed GenVM limits. Competitors cap snapshots at 20,000 characters. Do
   not store rendered HTML; store a **tree manifest + digest** and re-fetch the
   diff on demand. *(The competitor's own bound: `MAX_SNAPSHOT_CHARS = 20_000`.)*
6. **The rubric's criterion 4 is a reviewer's manual check.** "Frontend genuinely
   calls the contract and handles the full transaction lifecycle." Have the
   transaction lifecycle visible in the UI — pending, undetermined, confirmed —
   because that is what gets inspected.

---

## 9. Implementation milestones and acceptance checks

Assumes the Monday 2026-10-05 reset, giving two slots and 18 hr/day. If you use
the remaining slot this week, compress to M0–M3 and submit by Sun 2026-10-04
23:59 UTC.

| # | Milestone | Est. | Acceptance check — inspect this | Status |
| --- | --- | --- | --- | --- |
| **M0** | **Gate check.** Confirm Builder role + weekly slots on your own account. Confirm the Builder Welcome journey can still be completed. | 0.5 h | Your account shows Projects as submittable with 2 weekly slots. | pending |
| **M1** | **Consensus feasibility spike.** Throwaway contract, 3 criteria × 3 real submissions. Log per-criterion agreement. | 3–4 h | You have a real number for consensus success rate per criterion, and a decision on coarse-vs-fine buckets. | pending |
| **M2** | **Deterministic screen.** Repo + SHA + demo URL resolution, duplicate detection, deadline. | 2 h | A bad submission is disqualified with no consensus round spent. | pending |
| **M3** | **Submit-time freeze.** Validators fetch repo at pinned SHA; contract stores tree manifest + SHA-256. | 3 h | `get_submission` returns a digest that you can independently recompute with `sha256sum` from a local clone at that SHA. | pending |
| **M4** | **Per-criterion jury + agreement margin.** | 4 h | For one submission, every criterion shows an agreed bucket *and* a margin. A thin-margin criterion is visibly flagged as contested. | pending |
| **M5** | **Single-criterion challenge.** Staked, second panel, different formulation. | 4 h | Challenge one criterion; that criterion's bucket changes; the other criteria are byte-identical before and after. | pending |
| **M6** | **Accuracy record.** | 2 h | Program view shows challenges filed, upheld, and overturn rate per criterion, derived from storage, not from a counter. | pending |
| **M7** | **Frontend.** Organizer program view, submission record view, challenge flow, full transaction lifecycle including undetermined. | 6–8 h | The connected flow in §7 runs start to finish in a browser against the live contract. | pending |
| **M8** | **Docs + evidence.** README that states what it does, the problem, and how to run it. `docs/WORKED-EXAMPLE.md` with every number derived by reading the chain, not typed. | 4 h | A reviewer can clone, deploy, and reproduce the demo without asking you a question. | pending |
| **M9** | **Demo + submission.** Deploy, record, submit. | 4 h | Submission notes answer: what it does, the problem, how to use it. X post + demo video attached. | pending |

Total ≈ 33–36 h ≈ two 18 h days plus a third morning. Fits the stated capacity
with room for the review cycle.

### Acceptance checks mapped to the rubric

| Rubric requirement | Output | Inspect | Acceptance evidence | Status |
| --- | --- | --- | --- | --- |
| 1. Solves a real trust problem | Jury Ledger contract + README "Why GenLayer" | The gap table in §5 reproduced from the Explorer snapshot | `python3 evidence/competitor-gap-probe.py` shows 0 competitors in the wedge cells | pending |
| 2. Live/authoritative data | `_freeze_evidence` | Validator fetches `api.github.com` at a pinned SHA at submit time | Digest recomputable from a local clone at that SHA | pending |
| 3. Complete source + accurate docs | Public repo, `docs/WORKED-EXAMPLE.md` | Clone, read, run | `verify.sh` passes; every number in the example derived from the chain | pending |
| 4. Frontend genuinely calls the contract | Next.js app | Browser, live contract | Full lifecycle visible: pending → undetermined-or-confirmed → on-chain record; `eth_getCode`/`gen_getContractCode` readback matches the repo | pending |
| 5. Meaningfully different | This build | Explorer comparison | 0 of 219 publish an agreement or overturn statistic; 0 anchor to a point in time | pending |
| Eligibility: Builder role + weekly slot | Account state | Portal | M0 passed | pending |
| Required evidence: GitHub repo | Public repo URL matching `^https?://github\.com/[^/]+/[^/]+/?$` | Portal form validation | URL accepted by the form | pending |
| Optional accelerator: live demo + X post | Video + post | Portal | Both attached; note this "earns extra points and speeds up review" | pending |

**Every check above is planned, not passed.** Nothing has been built.

---

## 10. Demo story (90 seconds, tied to the rubric)

> "Every AI-judged hackathon ends the same way: a score, an announcement, and a
> runner-up who says the panel was rigged. Nobody can check, because the jury's
> own disagreement was thrown away.
>
> Watch: a builder submits a repo pinned to a commit. The contract freezes that
> commit — here is the digest, and here is the proof it is the commit. Four
> rubric criteria. The jury runs per criterion. Three criteria agree cleanly.
> **The fourth is thin — look at the margin.** That is the one a human should
> look at, so instead of 37 submissions to review, the organizer looks at one.
>
> The runner-up doesn't appeal the whole result. They stake, they name the one
> criterion that is wrong, they attach new evidence. A second panel re-judges
> *that criterion only* — the other three are byte-identical — and the record
> shows it move.
>
> And the program now publishes its own accuracy rate. After the fifth program,
> that record is the most valuable thing the organizer owns, because it is the
> only evidence anyone has that their process is fair.
>
> On GenLayer, because the verdict has to be reproducible by people who are not
> the organizer, and auditable after the organizer has moved on."

Cuts, if short on time: the mechanical screen. Keep: the thin margin, the
single-criterion challenge, the byte-identical neighbours, the accuracy record.

---

## 11. Research coverage and limits

**Inspected directly:** the Portal SPA bundle (recovered all five rubric
criteria, the weekly-window strings, and the "1 spot left" logic from the shipped
code), the Portal public API (65 contribution types, 219 Explorer projects, the
leaderboard, open missions, server configuration), the Hackathon Judge contract
source, and the full GrantJudge README.

**Not inspected, and what that costs:**

- **No browser was available in this session.** I could not see any live UI. Every
  claim about a competitor's *runtime* behaviour comes from its description, its
  README, or its source — never from exercising the product. The `try_it` copy in
  the Explorer is written by the submitting builders and should be treated as a
  claim throughout.
- Competitor deployments were not executed and no repository code was run.
- 42 of the 48 direct competitors were not read beyond their Explorer entry.
- Non-GenLayer alternatives were surveyed only as far as HackHQ, Devpost, MLH,
  Supabase, and Superteam.
- No user was contacted, so there is no level-1 or level-2 payment evidence.
- The published per-criterion weights and the `escalation_threshold_points`
  semantics are not public; both are inferences.
- GenLayer Skills plugin contents were not read; only its install path and licence.

**Sources, all retrieved 2026-10-01**

- `https://portal.genlayer.foundation/builders` (rules text; client-rendered, recovered from `assets/App-*.js`)
- `https://portal-admin.genlayer.foundation/api/v1/contribution-types/` and `/contribution-types/41/`
- `https://portal-admin.genlayer.foundation/api/v1/explorer/` and `/explorer/<slug>/`
- `https://portal-admin.genlayer.foundation/api/v1/leaderboard/`, `/missions/`, `/configuration/`
- `https://docs.genlayer.com/understand-genlayer-protocol/typical-use-cases`
- `https://docs.genlayer.com/developers/intelligent-contracts/when-to-use-genlayer`
- `https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle`
- `https://docs.genlayer.com/developers/intelligent-contracts/first-contract`
- `https://skills.genlayer.com/`
- `github.com/Demigodd00/demigodd00-genlayer-apps` → `contracts/hackathon_judge.py`, `contracts/hackathon_judge_scorecards.py`
- `github.com/kenil1710/grantjudge` (README)
- `github.com/MLH/mlh-hackathon-organizer-guide` → `judging-plan.md`
- `hackhq.io/about-us`, `hackhq.io/features`
- `help.devpost.team/article/231-how-judging-works`
- Portal Explorer entries for TrustRail, GrantGate, GrantAuditor, BountyCourt, OSS Judge, ImpactDNA, AirJudge, TrustGrant, Milestone Forge, Reverse Spec, Proof Bounty, AppAudit, BenchSeal, EvidenceQuorum

---

## 12. Next concrete decisions

1. **Decide A vs B.** This is the only decision blocking everything else. A is
   buildable but likely rejected on criterion 5; B is buildable and defensible.
   This is your call, not mine — the skill's job was to surface the trade.
2. **Run M0 today.** It costs 30 minutes and is a hard gate. If the Builder
   Welcome journey is closed to new accounts, the entire plan is moot and you
   need to know before you spend 36 hours.
3. **If B: run M1 before writing any frontend.** The consensus-success-rate
   number decides coarse-vs-fine bucketing and everything downstream.
4. **Decide the demo network.** Studio (fast, but transfers are unreliable) or
   Bradbury (slower, real testnet GEN). This is a promise in your submission
   notes, so decide it from a measured test, not from a preference.

**Do not start implementation on the strength of this document alone.** The
highest-value next action is M0 and M1 — half a day, and they can invalidate or
de-risk the plan before a line of product code exists.
