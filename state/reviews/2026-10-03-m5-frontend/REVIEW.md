# M5 review — accepted; repo visibility is now the blocker

Reviewed: 2026-10-03. Verdict: **gate met, 33/33. One unmet gate item, honestly
declared. The submission blocker is repo visibility, which is yours to fix.**

Commit `eb39e65`, pushed to `unifyWeb3/dereceipt`.

## Independently reproduced

| Check | My result |
| --- | --- |
| `scripts/m5_gate.py` | **33/33 passed** |
| Direct suite | 92 passed |
| `git status` | clean |
| Remote | `unifyWeb3/dereceipt` |

The gate's own log confirms the key-material story you described: our chunk is
clean, vendor chunks are scanned separately, and the 13 surviving 32-byte hex
values are classified — Baby Jubjub field prime, 6× EVM init code, `keccak256("")`,
secp256k1 `n`, secp256k1 `p`, 3× synthetic pattern. **Widening the pattern until
it passed would have been the wrong fix**, and classifying by shape is right.

That the gate reads identifier types **off the deployed schema** rather than
trusting assumptions is also right — see the correction below.

## Your correction is right, and my M3 claim was wrong

I told you at M3 that `program_id` is a `str` and warned that M5 "must send it as
a string." I applied that to the wrong slot. On the M5 deployment:

```
get_program('0')       -> OK
get_entry('0', 0)      -> OK            ← int is correct
get_entry('0', '0')    -> code=-32000
```

`get_entry(program_id: string, entry_index: int)` — `program_id` is the `str`,
`entry_index` is the `int`. **I conflated the two and the warning propagated into
the M4 handoff.** Your verifier asserts exactly this from the deployed schema,
which is why it caught what I missed.

So `code=-32000` at M3 was the *probe* passing `"0"` where the contract wanted
`0` — not a defect in `get_entry`. Your M4 record of that as a chain finding was
itself wrong, and you have corrected it in both places. The hardened accessor is
still correct and worth keeping: an unfrozen entry reading as `NOT_JUDGED` rather
than raising is better behaviour regardless.

**That is the fourth instance of the recurring hazard**, not the third: a check
reported a finding that the evidence did not support, in both directions — once
by asserting success it could not verify, once by asserting failure that had not
happened. Same root cause: a check whose failure modes were not enumerated.

## `freeze_entry` ran against real GitHub

First time, on chain, 64 seconds — real verdicts, real `committer.date` of
`2026-06-10T14:46:12Z`, real tree digest. **The Studio-dev validators have
internet.** That is the single most useful de-risking in the project: M6 is
viable, and defect 5's `AFTER_DEADLINE_WORK` — which M4 found decorative — can
now be exercised for real rather than asserted.

## Naming: DeReceipt

`PRODUCT_NAME` in `frontend/src/config.js` is the single definition. The gate
checks both that the bundle uses DeReceipt **and that "Contest Receipt" is gone
from it** — so a half-finished rename fails the gate rather than shipping. That
is the right way to enforce a rename.

**Leaving `contracts/contest_receipt.py` alone is the right call.** M0–M5 all
cite that path, six scripts and the whole suite reference it, and the deployed
contract's identity is its content, not its filename. Conflating the product name
with the artefact name would make the evidence trail lie.

**On the docstring — do change it.** You are right that it is arguable, and your
reasoning about not widening a UI milestone is also right. But the deployed source
is what a reviewer reads first, and `docs/ARCHITECTURE.md` and the README describe
a product called DeReceipt implemented by a contract whose docstring calls itself
Contest Receipt. That reads as two products. One-line change, and it belongs with
M7 rather than M5 — I will ask for it there.

## Both deliberate omissions are right

**No React/Tailwind.** My M5 handoff said vanilla JS plus `genlayer-js` and
`viem`, and 38 KB of hand-written CSS (13 KB gzipped) is the property I asked
for. The competitive finding worth keeping was *absence of design*, not absence
of Tailwind — and hand-written CSS is what produced the checkable details: the
amber `UNDETERMINED` treatment distinct from `--bad`, `border-left` on both state
regions, `prefers-reduced-motion` honoured, no `innerHTML` assignment anywhere in
application code.

Those four are individually small and collectively what "the frontend genuinely
handles the full transaction lifecycle" looks like to a reviewer who opens the
page.

**Not rendered in a browser.** Correct to declare unmet. The build, the served
page, every asset, the bundle and all six read paths are verified; the paint is
not. Nothing here can substitute for a human opening the URL.

## The blocker: the repo is private

Confirmed anonymously — both the repo page and `raw.githubusercontent.com` return
**404**, which is what a private repo does.

The Portal validates the URL pattern and accepts it. **A reviewer cannot read a
private repo.** Criterion 3 is *"complete source code and accurate docs"* — scored
by reading the repository. Right now there is nothing for a reviewer to read.

**This is one click and it is the last hard blocker on submission.** Make
`unifyWeb3/dereceipt` public, then confirm `https://github.com/unifyWeb3/dereceipt`
loads anonymously. I will re-verify.

Vercel then needs one public build variable, `VITE_CONTRACT_ADDRESS`, and
`vercel.json` is already correct. The default address in `config.js` is
`0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D` — the M5 deployment, balance 1000,
which I read independently.

## The two decisions that close the program

| # | Needed for | Item |
| --- | --- | --- |
| 1 | criterion 3 | **make `unifyWeb3/dereceipt` public** |
| 2 | criterion 4 | **Vercel deploy** at `VITE_CONTRACT_ADDRESS=0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D` |

Both are yours. Neither is code.

## Next: M6 — and the demo repo set is the last open input

M6 needs three real repositories, per §12:

1. healthy, honest README, recent commit
2. declared stack that contradicts its tree
3. a commit dated **after** the deadline

**Item 3 is now load-bearing** because M4 found `AFTER_DEADLINE_WORK` decorative
and M5 proved `freeze_entry` reaches real GitHub. That ground has to resolve on
chain or the challenge path is unproven.

I will not choose repositories to freeze on a public chain without explicit
instruction. Two names and two decisions is all that stands between this and M6.