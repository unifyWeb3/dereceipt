# Left off — M4 complete, M5 next

**Status:** M0–M4 done and committed. M5 (frontend) is the next milestone.
**No Portal submission is authorized.**

## What to do next: M5

The contract surface is stable — 14 methods, unchanged since M4 — so M5 can read
`get_program`, `get_entry`, `get_receipt`, `get_accuracy`, `get_receipt_digest`
and `get_contract_balance` without further contract work. M2 left a stub
`index.html` that builds and serves; M5 replaces it with the real lifecycle.

Three things M5 must get right, each of which cost a defect elsewhere:

1. **`program_id` is a `str`, not an `int`.** `0` and `"0"` are different keys
   and the integer spelling is refused as an unknown programme. `entry_index`
   *is* an `int`. The asymmetry is easy to get backwards. Pinned by
   `test_program_id_is_a_string_not_an_integer`.
2. **Show business state and protocol lifecycle separately.** `ACCEPTED` is not
   finality, and `get_program` says so in its own payload
   (`no_clock_on_this_runner`, and a `note` that spells it out). Do not render
   one badge that merges them.
3. **Unfrozen entries read `NOT_JUDGED`, not an error.** That was a live crash
   until M4 fixed it. If the frontend ever shows a red error for a submitted
   entry, something regressed.

## What still needs proving, and where

| claim | status | where it gets proven |
| --- | --- | --- |
| the refund path moves real value | **observed** 1000→0 at M3 | M6 re-confirms |
| `freeze_entry` against real GitHub | **never run live** | M6, steps 1–12 |
| `finalize_program` allocates on chain | **never run live** | M6 |
| `claim_payout` moves real value | **never run live**; the guard was inverted until M4 fixed it | M6 — do not trust it before an observed balance drop |
| validator convergence | 6/6, 2-bucket, from M1 | not re-provable offline |
| `genvm-lint check` | both halves clean | re-run at M8 |

## Reproducing the current state

```bash
bash run_direct_tests.sh                                        # 92 passed
.venv/bin/python scripts/m4_mutation_proof.py                  # 16/16 red
GENVM_VERSION=v0.6.0-rc5 .venv/bin/genvm-lint check contracts/contest_receipt.py
```

Do **not** add `-q` to `run_direct_tests.sh`: it suppresses pytest's summary
line on this runner, which looks exactly like a broken suite.

## Environment notes worth not rediscovering

- `gltest` 0.29.2 targets the old `genlayer.py.*` SDK layout and has five bugs
  against `v0.6.0-rc5`. All are worked around in `tests/direct/conftest.py`,
  with the reasoning in each function's docstring. Read that before touching the
  tests — the workarounds are load-bearing.
- The direct SDK cache is symlinked from the genvm-linter cache by
  `scripts/seed_gltest_cache.sh`. Without it the loader tries to download from
  GitHub releases and 404s.
- `run_direct_tests.sh` loads `gltest_compat_plugin` ahead of gltest's pytest
  entry point, because that entry point fails to import against the pinned
  `genlayer-py 0.19.0rc2`.