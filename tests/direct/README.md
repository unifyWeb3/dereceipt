# Direct tests

**Empty at M2, by design.** The test suite is M4, targeting 45+ tests across the
twelve groups in `IMPLEMENTATION-PLAN.md` §5. What M2 fixes is the *place* they
go and the rules they will follow, so M4 is a matter of writing them rather than
deciding how to run them.

## Rules carried into M4

- **No Docker.** Docker is unavailable in this environment. A direct test that
  needs it does not belong here, and must be listed as unverified in
  `docs/VERIFICATION.md` rather than quietly skipped.
- **No network.** The direct suite is the deterministic core only. Anything
  requiring a live source, a localnet, or an LLM provider is excluded and
  belongs to the M6 live run.
- **The optional model criterion is excluded.** `gltest.config.yaml` excludes
  `*_panel.py` and `*_nondet_llm.py`. Direct tests must stay reproducible.
- **Tests mirror requirements, not implementation.** A test that restates the
  code it tests proves nothing. Each test should name the rule it defends —
  "only a 404 is a rejection" is a testable rule; "the helper returns a tuple" is
  not.

## Layout

```text
tests/direct/
  conftest.py            shared fixtures and helpers (M4)
  test_canonical.py      URL, SHA and host canonicalisation
  test_malformed.py      every length bound, empty strings, injection attempts
  test_deadline.py       exactly-at-deadline and one second either side
  test_duplicate.py      a repeated tree_digest is refused
  test_declared.py       declared stack vs the frozen tree
  test_source_failure.py 403 / 429 / 500 / empty / non-JSON -> UNDETERMINED, never FAIL
  test_auth.py           only the entrant submits, only the owner finalises
  test_challenge.py      grounds, window, one-per-entry, bond outcome
  test_refund.py         cancel_program returns the pool exactly
  test_conservation.py   offline: value in equals value out, including refunds
  test_views.py          every view the frontend reads
```

Twelve files, one per group in the plan. The grouping is not cosmetic: the
360/400 build shipped 10 tests for 9 methods and lost points there, and its
`VERIFICATION.md` described coverage in exactly this kind of taxonomy. A reviewer
reads a taxonomy.

## Running

```sh
.venv/bin/python -m pytest tests/direct -q
```

`genlayer-test` and its runner are pinned in `requirements-dev.txt` but are not
installed yet. M4 installs them and records the real pytest output line in
`docs/VERIFICATION.md` verbatim, rather than a paraphrase.
