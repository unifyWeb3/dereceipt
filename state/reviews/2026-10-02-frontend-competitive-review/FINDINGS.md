# Competitive frontend review — what the peers actually do

Date: 2026-10-02. Research only; **no code was changed**. The brief for the next
phase has not been given yet, so this is a diagnosis and a recommendation, not
an implementation.

Profiles studied: `enoch208` (66 public repos), `mystiquemide` (50),
`mrnetwork0001` (92). Eight projects read at source level, four read closely.

## 1. Our current state, stated precisely

Not a dashboard. There is no dashboard.

| file | lines | what it is |
| --- | --- | --- |
| `frontend/index.html` | 13 | `<div id="app">` and a script tag |
| `frontend/src/main.js` | 162 | ~60% engineering comments, then one `innerHTML` template |
| `frontend/src/style.css` | 176 | dark palette, 7 CSS variables, no web fonts |

What that template renders: a notice reading *"Skeleton build. The interface is
wired at M5."*, **two `<pre>` blocks**, and a `<dl>` of environment facts
(chain id, RPC, explorer, contract address).

- Routes: **0**
- Components: **0** — one template literal
- Motion: **none**. Zero `@keyframes`, zero `animation` properties.
- Web fonts: **none**. System stack only.
- Dependencies: `genlayer-js`, `viem`. No React, no Tailwind.
- Per-entity pages: none. A receipt is not addressable by URL.
- Copy: one paragraph, inline in a template literal.

`grep -c "@keyframes" frontend/src/style.css` → `0`.

So the honest diagnosis is: **we have a build-proof page, and it is one
milestone behind the contract it is supposed to present.** Everything the
contract can already prove — 92 tests, 16 mutation proofs, a tamper-evident
receipt digest, a deadline boundary tested to the second — is invisible because
there is no surface to put it on.

## 2. What the peers do, from source

### Stack, uniformly

Next.js 15 + React 19 + Tailwind (v4 with token sets for Erilog), framer-motion
for motion, lucide-react for icons, shadcn-style primitives. Ours is Vite +
vanilla JS + `innerHTML`. This is not a detail — see §5.

### 2.1 Judr — `mrnetwork0001/Judr` (arbitration over escrowed money)

The closest analogue to our product, and the best-executed landing page in the
set. Nine landing components under `src/components/landing/`.

**The hero *is* the product, replayed.** `HeroLive.tsx` loops a **saved real run**
as four cards: screening returns and the flag appears, the clauses and finding
follow, three adjudications count in, the verifier passes, the verdict fills.
Then it rests, fades, restarts. The comment block is explicit about the design
intent:

> The cards also drift a little, and lean away from the pointer.

And the caption under it:

> A. Moreau and B. Adeyemi are a sample case; the reasoning shown is a real
> decision, made live on SERV on 26 September 2026 and saved as it came back,
> timings included.

This is the single most important thing in the whole review. It is not a mockup
and not a screenshot. It is a **recorded real transaction, replayed as a looping
vignette, captioned with its own provenance.**

**The headline is a stake, not a noun.** `Hero.tsx`:

> Too small to litigate.
> *Too big to walk away from.*

**Three assurances, each a falsifiable claim:**

```
Every verdict names the clause that decided it
Confidence is measured across re-runs, never self-reported
Funds move on-chain only after the appeal window closes, or a reviewer decides
```

**The verdict panel sells with numbers and a cost comparison.** `VerdictPanel.tsx`
renders four cells — Confidence (`stability × citations · never self-reported`),
Decision stability (`agreed/runs`), Clause support, Citations (`valid` /
`failed`) — then a cost strip: **$0.02–0.03 and ~25 s** against **"$3,000+ ·
6–12 weeks"**.

**How-it-works is four numbered stages with a live specimen in each**, not three
feature cards. `HowItWorks.tsx` step 3 is worth quoting because it is the same
instinct as ours:

> Not in aggregate. For each clause in dispute, both sides' positions are
> recorded … An honest indeterminate is worth more than a confident guess — the
> verdict is not permitted to rest on one.

### 2.2 Erilog — `enoch208/Erilog` (relief-distribution ledger)

The best *narrative* structure of the set. Thirteen `components/marketing/*`
files plus a `lib/content.ts` that is the single source of truth for every word
and number, headed:

> No magic numbers in JSX — read from here.

**Every claim is paired with its evidence.** `INTEGRITY_GUARANTEES`:

| claim | evidence |
| --- | --- |
| Events are append-only | Accepted physical events cannot be deleted via any API or admin operation |
| Replays cannot create another handout | Same event ID accepted exactly once; retries return `already_seen` |
| Merge order cannot change the result | **Property-tested: all permutations produce byte-equivalent output** |
| Duplicate entitlements are never silently resolved | Cross-device conflicts become persistent exceptions with all events as peers |

**A named problem section**, before the product. `OfflineProblemStory.tsx`:
"( the real problem )" → *"Two honest devices can produce one uncomfortable
truth."* Two device cards, then a pill: `HH-042 appears in both histories`, then
the resolution stated as a principle, not a feature.

**A frozen fixture is the demo.** The entire marketing page reads from
`SEED_42`, one `as const` object. Deterministic, so the demo cannot break and
every displayed number is checkable.

**The honesty tell.** The README caption under the hero image:

> *Illustrative product artwork. The working interface is available locally
> through Judge Mode.*

And the README closes on limits. Their demo video chapter table ends at
`3:14 | What Erilog does and does not promise`.

### 2.3 EquiGrant — `mystiquemide/equigrant` (AI-governed grants, GenLayer)

**This is our product's pitch, written more weakly than we could write it.**

Its `HowItWorks` is three steps: **Post Grant** → **Submit Your Work** →
**Get Funded by AI**. Builders stake GEN and submit GitHub repos and demo URLs.

Its `JudgingLayerPreview` has four signals that map almost one-to-one onto our
architecture:

| EquiGrant signal | our equivalent |
| --- | --- |
| Proof-of-work review — "Validators inspect repositories, demos, descriptions" | `freeze_entry` |
| Consensus judging — "Multiple AI validators compare each entry" | `run_nondet`, 2-BUCKET |
| **Appeals path — "instead of disappearing into a black box"** | `challenge` with a bond |
| Onchain audit trail | `get_receipt_digest` |

Their positioning line: *"Built for the messy middle between grants and
hackathons."* We would be competing on the substance and currently losing on
the presentation.

### 2.4 Strata — `enoch208/Strata` (archived-video investigation)

Three pillars in the hero: **Exact** (source moments) · **Full** (archive
search) · **Second** (challenge pass).

The `challenge-panel.tsx` is the best example of showing a *negative* result
honestly, which is our wheelhouse:

> No counter-evidence was found in this archive. **This does not prove the
> conclusion is true.**

Named components for the parts that matter: `challenge-panel`,
`submission-proof-panel`, `evidence-inspector`, `evidence-timeline`.

### 2.5 Inktoll — `mrnetwork0001/Inktoll` (★60, micro-settlement)

**They have the artefact we named ourselves after.** `dashboard/app/receipt/[id]/`
— a receipt at a shareable URL — plus `ReceiptImageCard.tsx`, a pure-canvas
1200×675 branded PNG with a pre-filled tweet intent URL:

> An AI agent just read "…" and paid the author $0.0123 USDC — settled gaslessly
> on @arc via @getinktoll. **Verifiable receipt:**

Their receipt page is 480px wide, one card, close button, monospace `#id`, an
on-chain badge, copy-hash, share, and download-image. We have a SHA-256 over
our entire audit record and no way to show it to anyone.

## 3. The comparison that matters

| | **ours** | Judr | Erilog | EquiGrant |
| --- | --- | --- | --- | --- |
| frontend LOC | 351 | ~30 components | 25 tsx + 10 marketing | 38 tsx |
| routes | 0 | `/`, `/app` | `/`, `/judge/*`, `/verify` | 9 |
| motion | **none** | looping real-run vignette | word-reveal, scroll | framer-motion |
| web fonts | none | yes | heading + handwritten accent | yes |
| design tokens | 7 CSS vars | full theme | Tailwind v4 token set | theme + dark mode |
| copy location | inline in a template literal | typed content module | typed module + fixtures | i18n provider |
| **a real artefact on a URL** | **no** | `/app` | `/verify` (drag a bundle) | `/results/[bountyId]/[submissionId]` |

Two structural conclusions:

1. **We do not have a UI problem, we have a zero.** There is nothing to polish.
   The gap is not "our dashboard is worse than theirs" — it is that a 13-line
   `index.html` cannot be made to sell anything.
2. **We have the harder and better product and the weakest presentation.**
   EquiGrant and Judr both describe an appeals path. We *built* one: a bond, a
   deterministic re-derivation, a forfeiture rule, and an append-only record that
   keeps the original verdict beside the challenge outcome. They describe it;
   we shipped it and cannot show it.

## 4. What we have that none of them do

Worth stating plainly, because it changes the recommendation:

- **Absence of evidence is never evidence of absence.** Only a 404 rejects. A
  rate limit produces `UNDETERMINED` and cannot disqualify anyone. EquiGrant has
  nothing like this. Erilog has the nearest cousin — conflicts preserved, no
  winner selected — but frames it as a data property, not a failure-mode
  property. This is our strongest defensible claim and **no one in this set is
  showing it.**
- **A claim↔evidence table we can populate from our own test suite.** Erilog's
  `INTEGRITY_GUARANTEES` is hand-written prose. Ours would be *machine-backed*:
  "A rate limit cannot disqualify" → 8 tests in the source-failure group; "Every
  unit received is either still here, scheduled to leave, or accounted for" →
  the conservation group, 6 tests; 16/16 mutation proofs. That is a stronger
  claim than any of these projects can make, and it is already true.
- **A tamper-evident digest over the whole audit record**, with two documented
  things it deliberately does *not* hide (criteria list order reaches the
  digest; identical records with different `program_id` differ).
- **A deadline boundary tested to the second, including across a timezone
  offset.** Nobody else has a deadline at all.

## 5. The recommendation

**One screen that replays a real receipt.** That is Judr's `HeroLive` applied to
our own `get_receipt` payload, and it is worth more than every other idea here
combined. Our contract already returns every field the story needs:

```
submit_entry → freeze_entry → per-criterion verdict + reason string
             → challenge (ground, criterion, bond, filer)
             → finalize_program → payout → balance observed to fall
```

Rendered as a five-beat looping vignette with the receipt digest in the corner,
that is a demo that cannot be faked and needs no narration.

Then, in priority order:

1. **`content.ts` equivalent.** All copy in one typed module, every number read
   from a frozen fixture. Erilog and Judr both do this; it costs about an hour
   and it makes the demo unbreakable.
2. **A `ReceiptStage` component** (above) + a `ProgrammeView` + an `EntryView`.
   Three components, three routes, the whole product.
3. **The `UNDETERMINED` section.** A freeze that hit a 429, showing
   `UNDETERMINED`, showing the entry standing as `FROZEN` rather than
   disqualified. This is the screenshot that wins the rubric, and no reference
   project has an equivalent.
4. **A claim↔evidence strip** populated from the test suite (§4).
5. **A shareable receipt URL** at `/receipt/[programId]/[entryIndex]`, showing
   the digest. Inktoll's canvas card if time allows.

### The stack question, honestly

Every reference is Next.js + React + Tailwind. We are on Vite + vanilla JS with
one `innerHTML` string. Building a replaying multi-beat stage with per-entity
routes, typed props, and a component split is real work that React does for
free, and doing it in vanilla means hand-rolling the state machine that
`HeroLive` gets from 30 lines of `useState` + `requestAnimationFrame`.

Recommendation: **React + Tailwind, keep Vite.** We do not need Next.js's server
side — we read views from a public RPC and have no database to host. But this is
a real decision with a real cost, and it should be made deliberately rather than
drifted into.

### The scheduling constraint

Our hero wants to replay a **real** receipt. Our contract has never run against
real GitHub — that is M6. So either:

- M5's fixture is labelled as a fixture, the way Erilog labels its hero
  (*"Illustrative product artwork"*) and seeds everything from `SEED_42`; or
- the receipt stage ships at M6 with a genuine captured run.

Either is defensible. What is **not** defensible is labelling a mock as real —
`docs/ARCHITECTURE.md` and our own evidence rules forbid it, and Erilog's
careful caption is the standard to hold.

### One warning

Some of what these projects do is marketing theatre we should decline to copy:

- EquiGrant's hero has animated score bars reading 92% / 85% / 78%. Those are
  decoration, not data. Copying them would be dishonest and would break rule 11.
- Inktoll's receipt reads from a REST API backed by a database. We have
  explicitly ruled out a database.
- Judr's cost strip ($0.02 vs $3,000) is real and measured; ours would have to
  be measured too or not stated at all.

The bar we must not drop is the one already written down in
`docs/ARCHITECTURE.md` rules 11–13. It is also, not coincidentally, the thing
these projects mostly do not have.

## Reproducing

Every claim above is from source at the default branch. The projects and their
default branches at the time of reading:

| repo | branch | homepage |
| --- | --- | --- |
| `enoch208/Erilog` | `feat/app-backend-judge-mode` | — |
| `enoch208/Strata` | `main` | strata-amber-one.vercel.app |
| `enoch208/knot` | `main` | — |
| `mystiquemide/equigrant` | `main` | equigrant.online |
| `mystiquemide/Dervyx` | `main` | dervyx.vercel.app |
| `mrnetwork0001/Judr` | `main` | tryjudr.vercel.app |
| `mrnetwork0001/Inktoll` | `main` | inktoll.xyz |
| `mrnetwork0001/vero-guardian-dashboard` | `main` | — |