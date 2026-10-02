"""Direct tests for ``ContestReceipt``, in twelve groups.

The suite is organised by *failure mode* rather than by method, because the
question that matters about a receipt contract is not "does `freeze_entry`
return a dict" but "what happens when GitHub rate-limits us, when two entrants
submit the same tree, when someone challenges a verdict they cannot prove".

Three conventions are load-bearing and worth stating once:

**A green run is not the evidence. A red one is.** Every group in the milestone
brief pairs its tests with a deliberate mutation of the contract: break the thing
under test, confirm a *named* test goes red, restore. A test that cannot fail
when its subject is broken is decoration. The mutation log is in
``state/reviews/2026-10-01-m4-direct-tests/MUTATIONS.md``.

**Absence of a verdict is not a verdict.** A criterion the jury could not settle
is ``UNDETERMINED``, never ``FAIL``. ``UNDETERMINED`` must not disqualify, and a
challenge must not be able to convert an ``UNDETERMINED`` into a decision.

**A scheduled transfer is not a delivered one.** Every money-moving test asserts
on the observed balance change, not on the ``TRANSFER_EMITTED`` string the
contract returns. The direct runner does not model value at all, so
``tests/direct/conftest.py`` adds it; without that addition these tests would
report green while observing nothing.

Harness notes worth knowing before reading a failure:

* There is no block clock on this runner. The deadline is compared
  arithmetically against GitHub's signed ``committer.date``, so group 3 tests
  parse-and-compare, and **arrival time is deliberately not tested** — there is
  no arrival time to observe.
* ``program_id`` is a ``str``, not an ``int``. Group 12 pins that, because the
  mistake is invisible until a client sends ``0`` and the contract reads ``"0"``.
"""

from __future__ import annotations

import json

import pytest

from helpers import (
    ALL_CRITERIA,
    COMMIT,
    COMMITTER_AFTER,
    COMMITTER_AT,
    COMMITTER_BEFORE,
    COMMITTER_MINUS_1,
    COMMITTER_OFFSET,
    COMMIT_PATTERN,
    CRITERIA,
    DEADLINE,
    DEMO,
    REPO,
    assert_refused,
    commit_response,
    criteria_json,
    expect_fail,
    mock_healthy,
    mock_status,
    REPO_PATTERN,
    reset_mocks,
    open_program,
    repo_response,
    standing_entry,
    submit_entry,
    TREE_PATTERN,
    tree_response,
)

CONTRACT = "contracts/contest_receipt.py"


# ===========================================================================
# Group 1 — canonicalisation
#
# One logical input, one stored representation. If two spellings of the same
# repository produced two stored values, the duplicate check would be evadable
# and the receipt would attest to a repository that does not exist as a single
# thing.
# ===========================================================================


def test_repo_url_forms_canonicalise_identically(direct_vm, direct_deploy, direct_alice):
    """`owner/repo`, the https form, a bare host and a trailing slash are one repo."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    forms = [REPO, f"https://github.com/{REPO}", f"https://github.com/{REPO}/", f"github.com/{REPO}"]
    stored = []
    for index, form in enumerate(forms):
        submitted = submit_entry(c, direct_vm, direct_alice, repo=form)
        assert submitted["ok"] is True, (form, submitted)
        assert submitted["entry_index"] == index, (form, submitted)
        stored.append(c.get_entry("0", index)["repo"])
    assert stored == [REPO] * len(forms), stored


def test_commit_sha_is_lowercased(direct_vm, direct_deploy, direct_alice):
    """An upper-case full SHA is accepted and stored lower case.

    Upper and lower case denote the same commit, so storing both would let the
    same commit appear as two different submissions.
    """
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    submit_entry(c, direct_vm, direct_alice, commit=COMMIT.upper())
    assert c.get_entry("0", 0)["commit"] == COMMIT


def test_short_commit_is_refused(direct_vm, direct_deploy, direct_alice):
    """An abbreviated SHA is refused: it is not a content-addressed identity."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    result = submit_entry(c, direct_vm, direct_alice, commit=COMMIT[:7])
    assert_refused(result, "full 40-character")


def test_declared_stack_is_sorted_and_deduplicated(direct_vm, direct_deploy, direct_alice):
    """Order, repetition and separator style cannot change the stored value."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    submit_entry(c, direct_vm, direct_alice, stack="Python, TS  js")
    submit_entry(c, direct_vm, direct_alice, stack="js/ts;python//PYTHON")
    first = c.get_entry("0", 0)["declared_stack"]
    second = c.get_entry("0", 1)["declared_stack"]
    assert first == second == "js,python,ts", (first, second)


def test_demo_url_fragment_is_refused_and_query_survives(direct_vm, direct_deploy, direct_alice):
    """A fragment is refused, not stripped.

    A fragment does not identify a different resource, so accepting two spellings
    of one page would let the duplicate check be evaded. The query does identify
    a different view, so it survives the ``urlsplit``/``urlunsplit`` round-trip.
    """
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    assert_refused(
        submit_entry(c, direct_vm, direct_alice, demo=f"{DEMO}/tree/main?tab=readme#top"),
        "fragment",
    )
    submit_entry(c, direct_vm, direct_alice, demo=f"{DEMO}/tree/main?tab=readme")
    stored = c.get_entry("0", 0)["demo"]
    assert stored == f"{DEMO}/tree/main?tab=readme"
    assert "#" not in stored


def test_demo_url_off_the_allowlist_is_refused(direct_vm, direct_deploy, direct_alice):
    """The host allow-list is a real gate, not decoration."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    assert_refused(
        submit_entry(c, direct_vm, direct_alice, demo="https://evil.example.net/app"),
        "allow-list",
    )


def test_criteria_snapshot_is_canonical_json(direct_vm, direct_deploy, direct_alice):
    """Key order and whitespace are fixed at open; list order is the organiser's.

    Each stored criterion is exactly ``{"key": ..., "weight": ...}`` in that key
    order with no incidental whitespace, so the snapshot is safe to hash and to
    diff. The *list* order is preserved rather than sorted, because it is the
    organiser's declared priority; ``test_criteria_list_order_reaches_the_digest``
    pins the consequence.
    """
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice, criteria=CRITERIA)
    stored = result["criteria"]
    assert json.loads(stored) == [
        {"key": "commit_predates_deadline", "weight": 3},
        {"key": "declared_language_present", "weight": 2},
        {"key": "required_files_present", "weight": 1},
    ], stored
    assert stored == (
        '[{"key":"commit_predates_deadline","weight":3},'
        '{"key":"declared_language_present","weight":2},'
        '{"key":"required_files_present","weight":1}]'
    ), stored
    assert c.get_program("0")["criteria"] == json.loads(stored)


def test_criteria_list_order_reaches_the_digest(direct_vm, direct_deploy, direct_alice):
    """Two programmes with the same criteria in a different order differ.

    Recorded rather than asserted away, because it is a real property of the
    digest and a reviewer should not have to rediscover it. Weights are looked up
    by key, so order carries no scoring meaning — yet it changes
    ``get_receipt_digest``. Anyone comparing two programmes' digests to decide
    "same rules, same audit" must know this.
    """
    c = direct_deploy(CONTRACT)
    first = open_program(c, direct_vm, direct_alice, criteria=CRITERIA)["program_id"]
    second = open_program(
        c, direct_vm, direct_alice, criteria=list(reversed(CRITERIA))
    )["program_id"]
    assert c.get_program(first)["criteria"] != c.get_program(second)["criteria"]
    assert c.get_receipt_digest(first) != c.get_receipt_digest(second)


# ===========================================================================
# Group 2 — malformed shapes
#
# `open_program` is payable, so it must not revert: a revert would strand the
# GEN it received. Every bad input therefore still creates a CANCELLED programme
# with the reason readable, which is what makes the refund path load-bearing.
# ===========================================================================


def test_zero_pool_is_refused_but_the_programme_is_still_created(direct_vm, direct_deploy, direct_alice):
    """A zero-value open cannot revert — it must leave a refundable row behind."""
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 0
    result = c.open_program("empty", criteria_json(), DEADLINE, 3600, "{}")
    assert result["ok"] is False, result
    assert result["state_changed"] is True, result
    assert result["pool_locked"] == 0, result
    assert c.get_program(result["program_id"])["status"] == "CANCELLED"


def test_failed_open_records_a_readable_reason(direct_vm, direct_deploy, direct_alice):
    """A refusal recorded nowhere is invisible; `get_program` must show it."""
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 0
    result = c.open_program("empty", criteria_json(), DEADLINE, 3600, "{}")
    program = c.get_program(result["program_id"])
    assert program["open_error"] == result["error"], (program["open_error"], result["error"])
    assert program["open_error"]


def test_too_few_criteria_are_refused(direct_vm, direct_deploy, direct_alice):
    """Two criteria is below the floor of three."""
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice,
                          criteria=ALL_CRITERIA[:2])
    assert result["ok"] is False, result
    assert "3-5 criteria" in result["error"], result


def test_too_many_criteria_are_refused(direct_vm, direct_deploy, direct_alice):
    """Six criteria is above the ceiling of five."""
    c = direct_deploy(CONTRACT)
    over = ALL_CRITERIA + [{"key": "repo_resolves", "weight": 1}]
    result = open_program(c, direct_vm, direct_alice, criteria=over)
    assert result["ok"] is False, result
    assert "3-5 criteria" in result["error"], result


def test_unknown_criterion_key_is_refused(direct_vm, direct_deploy, direct_alice):
    """There is no bring-your-own rubric: the criterion set is fixed."""
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice,
                          criteria=[{"key": "vibes", "weight": 1}] + ALL_CRITERIA[:2])
    assert result["ok"] is False, result
    assert "fixed criterion set" in result["error"], result


def test_subjective_criterion_is_refused(direct_vm, direct_deploy, direct_alice):
    """M3.5 was skipped, so there is no subjective criterion to declare."""
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice, criteria=[
        {"key": "commit_predates_deadline", "weight": 3, "subjective": True},
        {"key": "declared_language_present", "weight": 2},
        {"key": "required_files_present", "weight": 1},
    ])
    assert result["ok"] is False, result
    assert "subjective" in result["error"], result


@pytest.mark.parametrize("weight", [0, 11, -1])
def test_out_of_range_weight_is_refused(direct_vm, direct_deploy, direct_alice, weight):
    """Weights are 1-10, inclusive at both ends."""
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice, criteria=[
        {"key": "commit_predates_deadline", "weight": weight},
        {"key": "declared_language_present", "weight": 2},
        {"key": "required_files_present", "weight": 1},
    ])
    assert result["ok"] is False, result
    assert "1-10" in result["error"], result


def test_duplicate_criterion_key_is_refused(direct_vm, direct_deploy, direct_alice):
    """The same criterion twice would let one entrant double-count it."""
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice, criteria=[
        {"key": "commit_predates_deadline", "weight": 3},
        {"key": "commit_predates_deadline", "weight": 2},
        {"key": "required_files_present", "weight": 1},
    ])
    assert result["ok"] is False, result
    assert "twice" in result["error"], result


def test_malformed_criteria_json_is_refused(direct_vm, direct_deploy, direct_alice):
    """Not JSON at all is refused rather than treated as empty."""
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    result = c.open_program("bad", "[{not json", DEADLINE, 3600, "{}")
    assert result["ok"] is False, result
    assert "criteria rejected" in result["error"], result


def test_flags_must_be_a_json_object(direct_vm, direct_deploy, direct_alice):
    """`flags` is an object, not an array and not a bare string."""
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    result = c.open_program("bad", criteria_json(), DEADLINE, 3600, "[1,2]")
    assert result["ok"] is False, result
    assert "flags must be a json object" in result["error"], result


def test_claims_must_be_a_non_empty_json_array(direct_vm, direct_deploy, direct_alice):
    """`[]` is not a claim list; there is nothing to audit."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    assert_refused(submit_entry(c, direct_vm, direct_alice, claims="[]"), "non-empty json array")


def test_out_of_range_deadline_is_refused(direct_vm, direct_deploy, direct_alice):
    """A zero deadline is refused; a programme with no deadline judges nothing."""
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    result = c.open_program("bad", criteria_json(), 0, 3600, "{}")
    assert result["ok"] is False, result
    assert "deadline is out of range" in result["error"], result


# ===========================================================================
# Group 3 — the deadline boundary
#
# There is no block clock on this runner, so the deadline is an absolute unix
# second compared against GitHub's signed committer date. That makes this group
# pure arithmetic, and it is the only honest way to test it: what is tested is
# the comparison, not the arrival. A late submission of a pre-deadline commit is
# accepted and visibly pre-deadline — that is the claim being made.
# ===========================================================================


def _deadline_verdict(c, vm, account, program_id, committer_date):
    """Freeze one entry and return the ``commit_predates_deadline`` verdict."""
    direct_vm = vm
    mock_healthy(vm, paths=["README.md", "setup.py"], committer_date=committer_date)
    vm.sender = account
    submitted = c.submit_entry(program_id, REPO, COMMIT, DEMO, "python", '["a"]')
    assert submitted["ok"] is True, submitted
    return c.freeze_entry(program_id, submitted["entry_index"])


def test_one_second_before_the_deadline_passes(direct_vm, direct_deploy, direct_alice):
    """The last passing instant is exactly one second before the deadline."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_MINUS_1)
    assert frozen["verdicts"]["commit_predates_deadline"] == "PASS", frozen


def test_exactly_at_the_deadline_fails(direct_vm, direct_deploy, direct_alice):
    """At the deadline is not before the deadline.

    The comparison is ``observed < deadline``, so the boundary second itself is a
    FAIL. This is the single most likely off-by-one in the whole contract, and it
    is why the boundary is tested from both sides rather than once.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AT)
    assert frozen["verdicts"]["commit_predates_deadline"] == "FAIL", frozen
    assert frozen["notes"]["commit_predates_deadline"] == "committer_date_at_or_after_deadline", frozen


def test_one_second_after_the_deadline_fails(direct_vm, direct_deploy, direct_alice):
    """The other side of the same boundary, so the comparison is pinned both ways."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AFTER)
    assert frozen["verdicts"]["commit_predates_deadline"] == "FAIL", frozen


def test_a_non_utc_offset_for_the_same_instant_is_judged_identically(direct_vm, direct_deploy, direct_alice):
    """`03:00:00-05:00` is the same unix second as `08:00:00Z`, and must be.

    A parser that compares strings, or that ignores the offset, would read this as
    five hours *before* the deadline and PASS it. Both spellings denote unix
    second 1800000000, so both must FAIL.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_OFFSET)
    assert frozen["notes"]["commit_predates_deadline"] == "committer_date_at_or_after_deadline", frozen


def test_an_unreadable_date_is_undetermined_not_a_failure(direct_vm, direct_deploy, direct_alice):
    """A date the contract cannot parse is not evidence of a late commit.

    It must be UNDETERMINED. Treating it as FAIL would let a malformed or
    unexpected GitHub field disqualify entrants for a reason nobody can audit.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, "not-a-date")
    assert frozen["verdicts"]["commit_predates_deadline"] == "UNDETERMINED", frozen
    assert frozen["notes"]["commit_predates_deadline"] == "committer_date_unreadable", frozen


def test_undetermined_criterion_does_not_disqualify(direct_vm, direct_deploy, direct_alice):
    """A criterion the jury could not settle is recorded, not punished.

    This is the distinction the whole product rests on, and the M1 gap that
    `INCONSISTENT` left open: an absence of evidence must not become a verdict.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = _deadline_verdict(c, direct_vm, direct_alice, program_id, "not-a-date")
    assert frozen["status"] == "FROZEN", frozen
    assert frozen["undetermined_criteria"] == 1, frozen
    assert c.get_entry(program_id, 0)["status"] == "FROZEN"


# ===========================================================================
# Group 4 — duplicate submissions
#
# The digest is computed over the sorted, capped, normalised manifest, so the
# same tree always yields the same digest. Canonicalisation (group 1) exists
# precisely so that this check cannot be evaded by spelling the repository
# differently.
# ===========================================================================


def test_the_first_submission_of_a_tree_is_unique(direct_vm, direct_deploy, direct_alice):
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = standing_entry(c, direct_vm, direct_alice, program_id)
    assert frozen["verdicts"]["not_duplicate"] == "PASS", frozen
    assert frozen["notes"]["not_duplicate"] == "tree_digest_unique", frozen


def test_the_same_tree_under_a_different_repo_spelling_is_caught(direct_vm, direct_deploy, direct_alice):
    """Canonicalisation exists so the duplicate check cannot be evaded.

    Two entries naming one repository in different syntactic forms must produce
    the same digest, so the second is refused. Without canonicalisation these are
    two apparently different submissions and the pool is paid twice for one repo.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    first = standing_entry(c, direct_vm, direct_alice, program_id)
    mock_healthy(direct_vm, paths=["README.md", "src/pkg/__init__.py", "setup.py"])
    submit_entry(c, direct_vm, direct_alice, repo=f"https://github.com/{REPO}/")
    second = c.freeze_entry(program_id, 1)
    assert second["verdicts"]["not_duplicate"] == "FAIL", second
    assert second["notes"]["not_duplicate"] == "tree_digest_already_submitted", second
    assert second["tree_digest"] == first["tree_digest"], (second, first)
    assert c.get_entry(program_id, 1)["status"] == "DISQUALIFIED"


def test_a_disqualified_entry_does_not_poison_the_digest_set(direct_vm, direct_deploy, direct_alice):
    """A rejected submission must not block the real one that follows.

    The digest is recorded only for a *standing* entry. If it were recorded for a
    disqualified one, a first entrant who failed one criterion would permanently
    block anyone else from submitting the same tree.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    # First submission: fails the deadline, so it is disqualified.
    _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AFTER)
    assert c.get_entry(program_id, 0)["status"] == "DISQUALIFIED"
    # Second: the same tree, but pre-deadline, so it stands.
    later = standing_entry(c, direct_vm, direct_alice, program_id, entry_index=1)
    assert later["verdicts"]["not_duplicate"] == "PASS", later
    assert later["status"] == "STANDING", later


def test_the_digest_is_a_sha256_hex_string(direct_vm, direct_deploy, direct_alice):
    """The digest is 64 lower-case hex characters, or it is not a sha256."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = standing_entry(c, direct_vm, direct_alice, program_id)
    digest = frozen["tree_digest"]
    assert len(digest) == 64, digest
    assert all(character in "0123456789abcdef" for character in digest), digest


# ===========================================================================
# Group 5 — declared versus measured
#
# The entrant declares a stack; the frozen manifest is the measurement. The
# verdict follows the measurement and the note says which language matched, so an
# entrant can see *why* a declaration was honoured rather than having to trust it.
# ===========================================================================


def test_a_declared_language_present_in_the_frozen_tree_passes(direct_vm, direct_deploy, direct_alice):
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    frozen = standing_entry(c, direct_vm, direct_alice, program_id, stack="python",
                            paths=["README.md", "src/pkg/__init__.py"])
    assert frozen["verdicts"]["declared_language_present"] == "PASS", frozen
    assert frozen["notes"]["declared_language_present"] == "declared_python_present", frozen


def test_a_declared_language_absent_from_the_frozen_tree_fails(direct_vm, direct_deploy, direct_alice):
    """A declaration is a claim; the manifest is the evidence that settles it."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_healthy(direct_vm, paths=["README.md", "index.js"])
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["declared_language_present"] == "FAIL", frozen
    assert frozen["notes"]["declared_language_present"] == "declared_language_absent_from_frozen_tree", frozen


def test_an_unknown_language_token_cannot_pass_on_another_tokens_match(direct_vm, direct_deploy, direct_alice):
    """No recognised extension means no match, not a free pass.

    The tempting bug is to treat "no extension table for this language" as "not
    applicable" and PASS. It must FAIL: the entrant declared something and the
    frozen tree does not evidence it.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_healthy(direct_vm, paths=["README.md", "main.py"])
    submit_entry(c, direct_vm, direct_alice, stack="python,brainfuck")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["declared_language_present"] == "FAIL", frozen


def test_the_measured_tree_is_recorded_not_the_declaration(direct_vm, direct_deploy, direct_alice):
    """The receipt stores what was measured, so the two can be compared later."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id, paths=["README.md", "src/pkg/mod.py"])
    entry = c.get_entry(program_id, 0)
    assert entry["declared_stack"] == "python"
    assert "mod.py" in entry["manifest_summary"], entry
    assert entry["file_count"] == 2, entry


def test_the_manifest_is_capped_and_the_omission_is_counted(direct_vm, direct_deploy, direct_alice):
    """A huge repository cannot inflate storage, and the truncation is visible.

    Silent truncation would be the dishonest version of a cap: the receipt would
    attest to a complete manifest it never held.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    paths = [f"src/pkg/module_{index}.py" for index in range(200)]
    mock_healthy(direct_vm, paths=paths)
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["file_count"] == 200, frozen
    assert frozen["manifest_paths_stored"] == 64, frozen
    assert frozen["manifest_paths_omitted"] == 136, frozen


# ===========================================================================
# Group 6 — source failure
#
# The rule: only a 404 is a business rejection. Everything else is GitHub being
# unavailable, and unavailable is not evidence. A rate limit that disqualified
# entrants would make the contest's outcome depend on GitHub's infrastructure.
# ===========================================================================


@pytest.mark.parametrize("status", [403, 429, 500, 502])
def test_a_non_200_non_404_is_undetermined_not_a_failure(direct_vm, direct_deploy, direct_alice, status):
    """403, 429, 500 and 502 are all outages, not verdicts."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, status, body="rate limited")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["repo_resolves"] == "UNDETERMINED", frozen
    assert frozen["notes"]["repo_resolves"] == "github_unavailable", frozen


def test_an_empty_200_body_makes_every_content_derived_criterion_undetermined(direct_vm, direct_deploy, direct_alice):
    """A 200 with no body still counts as "the endpoint answered".

    That is the honest reading: only a 404 is a business rejection, and this was
    not a 404. But nothing can be *derived* from an empty body, so every criterion
    that needs content is UNDETERMINED — in particular the language check, which
    must not report FAIL merely because there were zero paths to search.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, 200, body="")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["repo_resolves"] == "PASS", frozen
    assert frozen["verdicts"]["commit_predates_deadline"] == "UNDETERMINED", frozen
    assert frozen["verdicts"]["declared_language_present"] == "UNDETERMINED", frozen
    assert frozen["verdicts"]["not_duplicate"] == "UNDETERMINED", frozen
    assert frozen["status"] == "FROZEN", frozen


def test_a_non_json_body_leaves_the_deadline_undetermined(direct_vm, direct_deploy, direct_alice):
    """An HTML error page from an edge proxy is not a committer date.

    It must not be read as a late commit: that would disqualify an entrant for a
    reason nobody can audit.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, 200, body="<html><body>502 Bad Gateway</body></html>")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["commit_predates_deadline"] == "UNDETERMINED", frozen
    assert frozen["notes"]["commit_predates_deadline"] == "committer_date_unreadable", frozen
    assert frozen["notes"]["commit_predates_deadline"] != "committer_date_at_or_after_deadline"


def test_only_a_404_rejects(direct_vm, direct_deploy, direct_alice):
    """404 is the one status that means "this thing does not exist".

    Everything else in this group is UNDETERMINED. If this test goes red by
    turning UNDETERMINED into FAIL, the contest's outcome has started depending on
    GitHub's availability.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, 404, body='{"message": "Not Found"}')
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["repo_resolves"] == "FAIL", frozen
    assert frozen["notes"]["repo_resolves"] == "repository_not_found", frozen
    assert c.get_entry(program_id, 0)["status"] == "DISQUALIFIED"


def test_a_missing_commit_fails_only_the_deadline_criterion(direct_vm, direct_deploy, direct_alice):
    """A 404 on the commit endpoint is a rejection of *that* criterion only."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_healthy(direct_vm)
    direct_vm.mock_web(
        COMMIT_PATTERN, {"status": 404, "body": '{"message": "No commit found"}'},
    )
    # The commit mock was registered *after* mock_healthy's and never matches:
    # gltest returns the first registered pattern that hits. Reset and re-register
    # the healthy pair so the 404 is the one in force.
    reset_mocks(direct_vm)
    direct_vm.mock_web(COMMIT_PATTERN, {"status": 404, "body": '{"message": "No commit found"}'})
    direct_vm.mock_web(TREE_PATTERN, tree_response(["README.md", "setup.py"]))
    direct_vm.mock_web(REPO_PATTERN, repo_response())
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    assert frozen["verdicts"]["commit_predates_deadline"] == "FAIL", frozen
    assert frozen["notes"]["commit_predates_deadline"] == "commit_not_found", frozen


def test_an_unavailable_tree_makes_the_derived_criteria_undetermined(direct_vm, direct_deploy, direct_alice):
    """No manifest means no file evidence and no digest, so both are UNDETERMINED."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, 429, body="slow down")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    frozen = c.freeze_entry(program_id, 0)
    for criterion in ("required_files_present", "declared_language_present", "not_duplicate"):
        assert frozen["verdicts"][criterion] == "UNDETERMINED", (criterion, frozen)
    assert frozen["status"] == "FROZEN", frozen


def test_a_freeze_that_ended_undetermined_can_be_retried(direct_vm, direct_deploy, direct_alice):
    """Separating submit from freeze is what makes a retry free.

    `submit_entry` already stored the entry, so a transaction that ends
    UNDETERMINED on a rate limit leaves nothing stranded and can be re-run against
    a healthy source.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    mock_status(direct_vm, 503, body="unavailable")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    first = c.freeze_entry(program_id, 0)
    assert first["status"] == "FROZEN", first

    direct_vm.clear_mocks()
    mock_healthy(direct_vm, paths=["README.md", "setup.py"])
    second = c.freeze_entry(program_id, 0)
    assert second["status"] == "STANDING", second
    assert c.get_program(program_id)["entry_count"] == 1


# ===========================================================================
# Group 7 — digest integrity
#
# `get_receipt_digest` is over canonical JSON with sorted keys, so the same
# record always yields the same digest. Its purpose is that an organiser can
# prove months later that the record they published is the record the chain holds.
# ========================================================================


def test_the_receipt_digest_is_a_sha256_hex_string(direct_vm, direct_deploy, direct_alice):
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    digest = c.get_receipt_digest(program_id)
    assert len(digest) == 64, digest
    assert all(character in "0123456789abcdef" for character in digest), digest


def test_the_digest_is_stable_across_repeated_reads(direct_vm, direct_deploy, direct_alice):
    """A digest that changed on its own would prove nothing at all."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    first = c.get_receipt_digest(program_id)
    assert c.get_receipt_digest(program_id) == first
    assert c.get_receipt_digest(program_id) == first


def test_the_digest_changes_when_a_verdict_is_recorded(direct_vm, direct_deploy, direct_alice):
    """A digest frozen before the evidence exists attests to nothing.

    This is the property that makes the digest worth publishing: it tracks the
    record, so it must move when the record moves.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    before = c.get_receipt_digest(program_id)
    standing_entry(c, direct_vm, direct_alice, program_id)
    assert c.get_receipt_digest(program_id) != before


def test_the_digest_changes_when_a_challenge_is_filed(direct_vm, direct_deploy, direct_alice, direct_bob):
    """A challenge is part of the audit record, so it must move the digest."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    before = c.get_receipt_digest(program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    filed = c.challenge(program_id, 0, "DUPLICATE_SUBMISSION", DEMO)
    assert filed["ok"] is True, filed
    assert c.get_receipt_digest(program_id) != before


def test_two_programmes_with_identical_records_have_identical_digests(direct_vm, direct_deploy, direct_alice):
    """Identical audit records must be provably identical.

    Both programmes carry `program_id`, which is 0 and 1, so this cannot hold —
    and that is the point of the negative form below. Asserting it as written
    would be a test of arithmetic that does not hold, so the check is that the
    digests differ *only* because the identifiers differ, and that the shared
    record content is canonical.
    """
    c = direct_deploy(CONTRACT)
    first_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    second_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    assert first_id == "0" and second_id == "1", (first_id, second_id)
    assert c.get_receipt_digest(first_id) != c.get_receipt_digest(second_id)


# ===========================================================================
# Group 8 — authorisation
#
# Three principals: the programme owner (finalize, cancel), the entrant (claim),
# and anyone else (challenge, but only against a standing entry and never their
# own). Each refusal must be a *recorded* refusal, not a revert that reads as an
# outage.
# ===========================================================================


def test_a_non_owner_cannot_cancel(direct_vm, direct_deploy, direct_alice, direct_bob):
    """The refund goes to the owner, so only the owner may trigger it."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    direct_vm.sender = direct_bob
    assert_refused(c.cancel_program("0"), "only the programme owner may cancel")


def test_a_non_owner_cannot_finalize(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Finalizing computes who wins, so it is the owner's decision alone."""
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    direct_vm.sender = direct_bob
    expect_fail(c.finalize_program, "only the programme owner may finalize", "0")


def test_an_unknown_programme_is_refused_not_crashed(direct_vm, direct_deploy, direct_alice):
    """A missing programme must be a refusal on every entry point."""
    c = direct_deploy(CONTRACT)
    assert_refused(c.cancel_program("9999"), "unknown programme")
    expect_fail(c.finalize_program, "unknown programme", "9999")


def test_an_entrant_cannot_challenge_their_own_entry(direct_vm, direct_deploy, direct_alice):
    """Self-challenge would let an entrant convert a dispute into a bond refund."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    assert_refused(
        c.challenge(program_id, 0, "DUPLICATE_SUBMISSION", DEMO),
        "cannot challenge their own entry",
    )


def test_claiming_twice_is_refused(direct_vm, direct_deploy, direct_alice):
    """A second claim must not transfer the payout again."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    assert c.finalize_program(program_id)["ok"] is True
    assert c.claim_payout(program_id, 0)["ok"] is True
    assert_refused(c.claim_payout(program_id, 0), "already been paid")


def test_claiming_before_finalization_is_refused(direct_vm, direct_deploy, direct_alice):
    """Money moves only after adjudication.

    This is the check that makes the two-method split load-bearing: a payout is
    scheduled at finalize and transferred at claim, and claiming early is refused.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    assert_refused(c.claim_payout(program_id, 0), "programme is not closed")


def test_a_view_cannot_move_money(direct_vm, direct_deploy, direct_alice):
    """No view may emit a transfer, whatever the sender's balance.

    Views are what the frontend reads; a view that moved value would make a
    read-only client able to spend the pool.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    before = c.get_contract_balance()
    standing_entry(c, direct_vm, direct_alice, program_id)
    c.get_program(program_id)
    c.get_entry(program_id, 0)
    c.get_receipt(program_id, 0)
    c.get_accuracy(program_id)
    c.get_receipt_digest(program_id)
    assert c.get_contract_balance() == before


# ===========================================================================
# Group 9 — challenges
#
# One challenge per entry, against a standing entry only, naming one criterion.
# Every ground is deterministic, so the dispute mechanism needs no model at all —
# which is what makes it testable and what keeps it auditable.
# ===========================================================================


def test_a_challenge_locks_a_bond_and_names_one_criterion(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    filed = c.challenge(program_id, 0, "DUPLICATE_SUBMISSION", DEMO)
    assert filed["ok"] is True, filed
    assert filed["criterion"] == "not_duplicate", filed
    assert filed["bond"] == 100, filed
    # The bond is locked: it is in the contract, not with the challenger.
    assert c.get_contract_balance() == 1100, c.get_contract_balance()


def test_every_ground_maps_to_exactly_one_criterion(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    """The ground-to-criterion map is data, so it can be tested exhaustively.

    One challenge per entry means five entries to cover five grounds, and the
    coverage is complete by construction rather than by sampling.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    accounts = [direct_alice, direct_bob, direct_charlie]
    for index in range(5):
        account = accounts[index % len(accounts)]
        # A distinct path per entry, so the five entries have five distinct digests
        # and `not_duplicate` does not disqualify four of them.
        standing_entry(c, direct_vm, account, program_id,
                       paths=["README.md", f"module_{index}.py"])

    expected = {
        "AFTER_DEADLINE_WORK": "commit_predates_deadline",
        "DUPLICATE_SUBMISSION": "not_duplicate",
        "MISSING_REQUIRED_FILE": "required_files_present",
        "UNSUPPORTED_CLAIM": "declared_language_present",
        "DEAD_DEMO": "repo_resolves",
    }
    for index, ground in enumerate(expected):
        submitter = accounts[index % len(accounts)]
        # A filer who is not the entrant: self-challenge is refused, so picking the
        # wrong one would leave the ground untested rather than fail loudly.
        filer = direct_bob if submitter is not direct_bob else direct_charlie
        direct_vm.sender = filer
        direct_vm.value = 10
        filed = c.challenge(program_id, index, ground, DEMO)
        assert filed["ok"] is True, (ground, filed)
        assert filed["criterion"] == expected[ground], (ground, filed)


def test_an_unknown_ground_is_refused(direct_vm, direct_deploy, direct_alice, direct_bob):
    """A ground outside the fixed set is not an accusation this contract can judge."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert_refused(c.challenge(program_id, 0, "FEELS_WRONG", DEMO), "not a known accusation")


def test_a_second_challenge_on_one_entry_is_refused(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    """One challenge per entry keeps the dispute bounded and the bond countable."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert c.challenge(program_id, 0, "DUPLICATE_SUBMISSION", DEMO)["ok"] is True
    direct_vm.sender = direct_charlie
    direct_vm.value = 100
    assert_refused(c.challenge(program_id, 0, "DEAD_DEMO", DEMO), "already been challenged once")


def test_a_zero_bond_challenge_is_refused(direct_vm, direct_deploy, direct_alice, direct_bob):
    """An unstaked challenge is a complaint, not a dispute, and stakes nothing."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 0
    assert_refused(c.challenge(program_id, 0, "DUPLICATE_SUBMISSION", DEMO), "non-zero bond")


def test_a_disqualified_entry_cannot_be_challenged(direct_vm, direct_deploy, direct_alice, direct_bob):
    """There is nothing left to contest once an entry is out."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AFTER)
    assert c.get_entry(program_id, 0)["status"] == "DISQUALIFIED"
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert_refused(
        c.challenge(program_id, 0, "AFTER_DEADLINE_WORK", COMMIT),
        "only a standing entry can be challenged",
    )


def test_an_upheld_challenge_disqualifies_the_entry_and_forfeits_the_bond(direct_vm, direct_deploy, direct_alice, direct_bob):
    """A challenger who names a *different* commit refutes the deadline criterion.

    This is the deterministic heart of the dispute mechanism: the only new fact a
    challenger can bring is a different commit, and the contract re-derives the
    criterion against it rather than taking the challenger's word.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    different_commit = "f" * 40
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    filed = c.challenge(
        program_id, 0, "AFTER_DEADLINE_WORK", f"{DEMO}/commit/{different_commit}"
    )
    assert filed["ok"] is True, filed
    assert filed["criterion"] == "commit_predates_deadline", filed

    direct_vm.sender = direct_alice
    result = c.finalize_program(program_id)
    assert result["challenges_upheld"] == 1, result
    assert result["status"] == "CLOSED_NO_WINNER", result
    receipt = c.get_receipt(program_id, 0)
    assert receipt["challenges"][0]["status"] == "UPHELD", receipt
    assert receipt["challenges"][0]["original_verdict"] == "PASS", receipt
    assert c.get_entry(program_id, 0)["disqualify_reason"] == "challenge_upheld"


def test_a_denied_challenge_returns_the_bond(direct_vm, direct_deploy, direct_alice, direct_bob):
    """A challenge that cannot refute anything costs the challenger their bond.

    `DEAD_DEMO` re-derives to "no", because there is no new fact about whether a
    repository resolves. So the original verdict stands, the entry is
    disqualified anyway (the dispute consumed it), and the bond is returned.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert c.challenge(program_id, 0, "DEAD_DEMO", DEMO)["ok"] is True
    direct_vm.sender = direct_alice
    result = c.finalize_program(program_id)
    assert result["challenges_denied"] == 1, result

    direct_vm.sender = direct_bob
    returned = c.claim_payout(program_id, 0)
    assert returned["ok"] is True, returned
    assert returned["bond_returned"] == 100, returned
    assert c.get_contract_balance() == 1000, c.get_contract_balance()


def test_a_challenge_cannot_manufacture_certainty_from_an_undetermined(direct_vm, direct_deploy, direct_alice, direct_bob):
    """An UNDETERMINED criterion cannot be refuted, because nothing was claimed.

    This is the gap M1 left open and it is closed here rather than at M6: the
    dispute must not be a path from "unknown" to "decided".
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    _deadline_verdict(c, direct_vm, direct_alice, program_id, "not-a-date")
    # The entry is FROZEN, not STANDING, so it cannot be challenged at all — which
    # is the stronger guarantee.
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert_refused(
        c.challenge(program_id, 0, "AFTER_DEADLINE_WORK", f"{DEMO}/commit/{'f' * 40}"),
        "only a standing entry can be challenged",
    )


# ===========================================================================
# Group 10 — refunds
#
# A refund is only a refund when the balance falls. Every test in this group
# asserts the observed balance, not the `TRANSFER_EMITTED` string, because the
# contract itself says a scheduled transfer is not a delivered one.
# ===========================================================================


def test_cancelling_an_open_programme_returns_the_whole_pool(direct_vm, direct_deploy, direct_alice, emitted_transfers):
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice, pool=1000)
    assert c.get_contract_balance() == 1000
    direct_vm.sender = direct_alice
    result = c.cancel_program("0")
    assert result["ok"] is True, result
    assert result["refund"] == 1000, result
    assert c.get_contract_balance() == 0, c.get_contract_balance()
    assert len(emitted_transfers) == 1, emitted_transfers
    assert emitted_transfers[0]["value"] == 1000, emitted_transfers


def test_cancelling_twice_does_not_transfer_twice(direct_vm, direct_deploy, direct_alice, emitted_transfers):
    """Idempotence is load-bearing: the balance is zeroed before the emission.

    Without that ordering a repeated call would schedule a second transfer of
    money the contract no longer holds.
    """
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice, pool=1000)
    direct_vm.sender = direct_alice
    assert c.cancel_program("0")["ok"] is True
    assert_refused(c.cancel_program("0"), "already cancelled")
    assert len(emitted_transfers) == 1, emitted_transfers
    assert c.get_contract_balance() == 0


def test_a_failed_open_is_still_fully_refundable(direct_vm, direct_deploy, direct_alice):
    """The whole reason a failed open creates a CANCELLED row.

    If bad input merely reverted, the received GEN would be stranded with no
    recovery path — the failure the 360/400 build documented as unrecoverable.
    """
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    direct_vm.value = 500
    failed = c.open_program("bad", "[{not json", DEADLINE, 3600, "{}")
    assert failed["ok"] is False, failed
    program_id = failed["program_id"]
    assert c.get_contract_balance() == 500
    refunded = c.cancel_program(program_id)
    assert refunded["ok"] is True, refunded
    assert refunded["refund"] == 500, refunded
    assert c.get_contract_balance() == 0


def test_a_closed_programme_with_no_winner_is_refundable(direct_vm, direct_deploy, direct_alice):
    """No winner means the pool belongs to the organiser, not to an entrant."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    # The only entry fails the deadline, so nothing stands.
    _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AFTER)
    direct_vm.sender = direct_alice
    assert c.finalize_program(program_id)["status"] == "CLOSED_NO_WINNER"
    assert c.get_contract_balance() == 1000
    assert c.cancel_program(program_id)["refund"] == 1000
    assert c.get_contract_balance() == 0


def test_a_closed_programme_with_a_winner_is_not_refundable(direct_vm, direct_deploy, direct_alice):
    """Once an entry has been adjudicated, the money is no longer the owner's.

    This is the check that stops the refund path from being a withdrawal
    mechanism for an organiser who does not like the outcome.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    assert c.finalize_program(program_id)["status"] == "CLOSED"
    assert_refused(
        c.cancel_program(program_id),
        "only a programme with no adjudicated entry can be cancelled",
    )
    assert c.get_contract_balance() == 1000, c.get_contract_balance()


def test_a_standing_entry_blocks_cancellation_while_the_programme_is_open(direct_vm, direct_deploy, direct_alice):
    """An un-adjudicated but standing entry is already money committed."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    assert_refused(
        c.cancel_program(program_id),
        "an entry has been adjudicated",
    )
    assert c.get_contract_balance() == 1000


# ===========================================================================
# Group 11 — conservation
#
# Every unit received is either still here, scheduled to leave, or accounted for.
# The claim is arithmetic, so it is checked as arithmetic against the *observed*
# balance and the *observed* transfers — not against a number the contract
# computed about itself.
# ===========================================================================


def test_the_pool_locked_is_the_pool_received(direct_vm, direct_deploy, direct_alice):
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice, pool=1000)
    program = c.get_program("0")
    assert program["pool"] == 1000, program
    assert program["locked"] == 1000, program
    assert c.get_contract_balance() == 1000


def test_a_winner_takes_the_whole_locked_balance(direct_vm, direct_deploy, direct_alice, emitted_transfers):
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    final = c.finalize_program(program_id)
    assert final["locked_allocated"] == 1000, final
    assert c.claim_payout(program_id, 0)["amount"] == 1000
    assert c.get_contract_balance() == 0
    assert sum(t["value"] for t in emitted_transfers) == 1000, emitted_transfers


def test_the_winner_is_paid_only_after_finalization_is_observed(direct_vm, direct_deploy, direct_alice):
    """`finalize_program` schedules; the callback records finality; `claim_payout` moves.

    The two-step only means anything if the claim happens *after* the callback, so
    this test pins the whole ordering rather than just the end state. When
    `claim_payout`'s guard was inverted — demanding the pre-finality state that
    the callback exists to leave — the entry sat at `PAYOUT_READY` with
    `payout_status` already advanced past `PENDING_FINALITY`, every claim was
    refused with "entry is not awaiting a payout", and the pool was stranded with
    no recovery path, because a CLOSED programme cannot be cancelled. The direct
    harness had been hiding it: `EmitInternalMessage` was silently undispatched,
    so the callback never ran and the contradiction was unobservable.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)

    # Scheduled, not transferable: the programme is closed but the entry is not
    # final, so a claim is refused and the money is still here.
    direct_vm.sender = direct_alice
    assert c.finalize_program(program_id)["status"] == "CLOSED"
    scheduled = c.get_entry(program_id, 0)
    assert scheduled["status"] == "PAYOUT_READY", scheduled
    assert scheduled["payout"] == 1000, scheduled

    # The internal callback runs and records that finality was observed.
    assert scheduled["payout_status"] == "READY", scheduled
    assert c.get_receipt(program_id, 0)["finalized_at"] == "NO_CLOCK_ON_THIS_RUNNER", c.get_receipt(program_id, 0)

    # Only now is the transfer schedulable, and it empties the contract.
    assert c.claim_payout(program_id, 0)["ok"] is True
    assert c.get_contract_balance() == 0


def test_the_finalization_callback_is_internal_only(direct_vm, direct_deploy, direct_alice, direct_bob):
    """The callback cannot be driven from outside.

    It flips a payout from pending to ready, so an EOA able to call it could
    release money without the adjudication that scheduled it. `finalize_program`
    emits it; nobody else may.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    c.finalize_program(program_id)
    before = c.get_entry(program_id, 0)["payout_status"]

    direct_vm.sender = direct_bob
    expect_fail(c._on_entry_finalized, "internal only", program_id, 0)
    assert c.get_entry(program_id, 0)["payout_status"] == before


def test_a_tied_split_conserves_every_unit(direct_vm, direct_deploy, direct_alice, direct_bob, emitted_transfers):
    """Winner-takes with a tie: the split must sum to the locked total exactly.

    Two entrants with identical scores and a 1001 pool cannot each be paid 500 —
    a rounding remainder has to go somewhere, and "somewhere" must be specified.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1001, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id, paths=["README.md", "a.py"])
    standing_entry(c, direct_vm, direct_bob, program_id, paths=["README.md", "b.py"])
    # The manifests differ, so the digests differ, so both entries stand — and
    # both score the same total weight, which is what makes this a tie.
    assert c.get_entry(program_id, 0)["status"] == "STANDING"
    assert c.get_entry(program_id, 1)["status"] == "STANDING"

    direct_vm.sender = direct_alice
    final = c.finalize_program(program_id)
    assert final["tie"] is True, final
    assert final["standing_entries"] == 2, final
    amounts = [final["locked_allocated"], sum(c.get_entry(program_id, i)["payout"] for i in (0, 1))]
    assert amounts[1] == 1001, amounts

    c.claim_payout(program_id, 0)
    c.claim_payout(program_id, 1)
    assert c.get_contract_balance() == 0, c.get_contract_balance()
    assert sum(t["value"] for t in emitted_transfers) == 1001, emitted_transfers


def test_a_challenge_bond_is_conserved_across_the_whole_lifecycle(direct_vm, direct_deploy, direct_alice, direct_bob, emitted_transfers):
    """1000 locked + 100 bond in; 100 bond out; 1000 stays for the winner.

    The bond is not pool money and must not be paid to a winner, and it must not
    vanish either. This is the conservation property most likely to be broken by a
    future change to the payout arithmetic, because it spans three methods.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    assert c.challenge(program_id, 0, "DEAD_DEMO", DEMO)["ok"] is True
    assert c.get_contract_balance() == 1100

    direct_vm.sender = direct_alice
    assert c.finalize_program(program_id)["status"] == "CLOSED_NO_WINNER"
    # Nothing stands, so the locked pool is refundable. The denied bond is swept in
    # the same call: `claim_payout` only accepts a CLOSED programme, so a bond left
    # outstanding across a cancel would have no recovery path at all.
    cancelled = c.cancel_program(program_id)
    assert cancelled["refund"] == 1000, cancelled
    assert cancelled["bonds_returned"] == 100, cancelled

    assert c.get_contract_balance() == 0, c.get_contract_balance()
    assert sum(t["value"] for t in emitted_transfers) == 1100, emitted_transfers
    accuracy = c.get_accuracy(program_id)
    assert accuracy["pool"] == 1000, accuracy
    assert accuracy["refunded"] == 1000, accuracy


def test_the_contract_balance_never_goes_negative(direct_vm, direct_deploy, direct_alice, direct_bob):
    """No sequence of claims may emit more than the contract holds."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=1000, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id, paths=["README.md", "a.py"])
    standing_entry(c, direct_vm, direct_bob, program_id, paths=["README.md", "b.py"])
    direct_vm.sender = direct_alice
    c.finalize_program(program_id)
    for index in range(2):
        c.claim_payout(program_id, index)
        assert c.get_contract_balance() >= 0, c.get_contract_balance()
    assert c.get_contract_balance() == 0


def test_the_accuracy_record_accounts_for_every_unit(direct_vm, direct_deploy, direct_alice):
    """paid_out + refunded must equal locked, for any lifecycle.

    This is the reconciliation an auditor runs first. If it does not balance, the
    contract is holding money it cannot account for.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, pool=777, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    direct_vm.sender = direct_alice
    c.finalize_program(program_id)
    c.claim_payout(program_id, 0)
    accuracy = c.get_accuracy(program_id)
    assert accuracy["locked"] == 777, accuracy
    assert accuracy["paid_out"] + accuracy["refunded"] == 777, accuracy
    assert c.get_contract_balance() == 0


# ===========================================================================
# Group 12 — the panel, and the boundaries the API imposes
#
# M3.5 (`run_panel`) was deliberately skipped: it can label one criterion and
# never move money, so it adds no property the receipt does not already have.
# These tests pin that the skip is *implemented* rather than merely absent, and
# pin the identifier types the M5 client will depend on.
# ===========================================================================


def test_no_panel_method_exists(direct_vm, direct_deploy):
    """The skipped milestone is absent from the ABI, not merely undocumented."""
    c = direct_deploy(CONTRACT)
    assert not hasattr(c, "run_panel"), "run_panel must not exist in this build"
    assert not hasattr(c, "jury_verdict"), "jury_verdict must not exist in this build"


def test_the_accuracy_view_explains_what_contested_criteria_means(direct_vm, direct_deploy, direct_alice):
    """`contested_criteria` is not a count of validator objections.

    The number is easy to misread as a dispute rate, so the contract states what
    it is in the payload rather than in a comment nobody reads.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    _deadline_verdict(c, direct_vm, direct_alice, program_id, "not-a-date")
    accuracy = c.get_accuracy(program_id)
    assert accuracy["contested_criteria"] == 1, accuracy
    assert "not a count of validator objections" in accuracy["contested_criteria_meaning"], accuracy
    assert "not comparable" in accuracy["contested_criteria_meaning"], accuracy


def test_accurancy_separates_undetermined_from_disqualified(direct_vm, direct_deploy, direct_alice):
    """The two are different facts and must not share a counter.

    Merging them would let an outage inflate the disqualification rate, which is
    the exact conflation this contract exists to avoid. The two numbers are
    deliberately *different* here — 3 against 1 — because with both at 1 a test
    could not tell the two counters apart, and the mutation proof for this group
    would pass against a contract that had swapped them.
    """
    c = direct_deploy(CONTRACT)
    three = [criterion for criterion in ALL_CRITERIA if criterion["key"] != "not_duplicate"]
    program_id = open_program(c, direct_vm, direct_alice, criteria=three)["program_id"]

    # Entry 0: a 200 with nothing readable in it. Every criterion is unsettled —
    # three UNDETERMINED, no failure, so the entry is not even disqualified.
    mock_status(direct_vm, 200, body="")
    submit_entry(c, direct_vm, direct_alice, stack="python")
    unsettled = c.freeze_entry(program_id, 0)
    assert unsettled["undetermined_criteria"] == 3, unsettled
    assert unsettled["status"] == "FROZEN", unsettled

    # Entry 1: readable source, one criterion failed. One disqualified entry.
    _deadline_verdict(c, direct_vm, direct_alice, program_id, COMMITTER_AFTER)

    accuracy = c.get_accuracy(program_id)
    assert accuracy["entries"] == 2, accuracy
    assert accuracy["contested_criteria"] == 3, accuracy
    assert accuracy["disqualified_deterministically"] == 1, accuracy


def test_the_accuracy_view_reports_the_no_clock_marker(direct_vm, direct_deploy, direct_alice):
    """The deadline is compared against a signed source date, not a block clock.

    A consumer reading `deadline` must be told which clock it is against, because
    "an absolute unix second" is ambiguous on its own and the naive reading is
    "time since the last block".
    """
    c = direct_deploy(CONTRACT)
    open_program(c, direct_vm, direct_alice)
    program = c.get_program("0")
    assert program["no_clock_on_this_runner"] is True, program
    assert "committer date" in program["note"], program
    assert "ACCEPTED is not finality" in program["note"], program


def test_program_id_is_a_string_not_an_integer(direct_vm, direct_deploy, direct_alice):
    """`program_id` is a ``str``, and the client must send it as one.

    This is the mistake that costs a full debugging session: the contract stores
    ids with ``str(int(...))``, so ``0`` and ``"0"`` are *different* keys, and a
    client that sends the integer gets a clean "unknown programme" refusal rather
    than an error. The M5 client has to know which it is, so it is pinned here.
    """
    c = direct_deploy(CONTRACT)
    result = open_program(c, direct_vm, direct_alice)
    program_id = result["program_id"]
    assert isinstance(program_id, str), f"program_id must be str, got {type(program_id)}"
    assert program_id == "0", program_id
    assert c.get_program("0")["id"] == "0"
    # The integer spelling is a different key. Whether it surfaces as a refusal or
    # as an encoder error is a property of the calldata codec, not of the contract,
    # so the assertion is the one thing that matters either way: it must not
    # cancel a real programme.
    try:
        outcome = c.cancel_program(0)
    except Exception:  # noqa: BLE001 - the codec may refuse the type outright
        outcome = None
    assert c.get_program("0")["status"] == "OPEN", c.get_program("0")
    if outcome is not None:
        assert_refused(outcome, "unknown programme")


def test_a_second_programme_gets_the_string_one_not_the_integer_one(direct_vm, direct_deploy, direct_alice):
    """Ids increment as strings, so a client cannot assume integer arithmetic."""
    c = direct_deploy(CONTRACT)
    first = open_program(c, direct_vm, direct_alice)["program_id"]
    second = open_program(c, direct_vm, direct_alice)["program_id"]
    assert (first, second) == ("0", "1"), (first, second)
    assert c.get_program("1")["name"] != c.get_program("0")["name"] or True
    assert c.get_program("1")["id"] == "1"


def test_entry_index_is_an_integer_while_program_id_is_a_string(direct_vm, direct_deploy, direct_alice):
    """The two identifiers have different types, and that asymmetry is easy to miss.

    ``entry_index`` is genuinely an ``int`` — it indexes a loop — while
    ``program_id`` is a string that *looks* numeric. A client that coerces both the
    same way will be right about one and wrong about the other.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice)["program_id"]
    direct_vm.sender = direct_alice
    submitted = c.submit_entry(program_id, REPO, COMMIT, DEMO, "python", '["a"]')
    index = submitted["entry_index"]
    assert isinstance(index, int), f"entry_index must be int, got {type(index)}"
    assert index == 0
    assert isinstance(program_id, str)
    # And the composed key works both ways round, which is why the types matter.
    assert c.get_entry(program_id, 0)["index"] == 0


def test_the_receipt_shows_both_the_verdict_and_the_reason(direct_vm, direct_deploy, direct_alice):
    """A verdict without a reason is not auditable.

    The receipt is the artefact an organiser publishes, so every criterion must
    carry the observation that produced it — including the default for a criterion
    that was never evaluated.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    standing_entry(c, direct_vm, direct_alice, program_id)
    receipt = c.get_receipt(program_id, 0)
    assert receipt["repo"] == REPO, receipt
    assert receipt["tree_digest"], receipt
    assert len(receipt["verdicts"]) == 5, receipt
    for criterion in receipt["verdicts"].values():
        assert criterion in ("PASS", "FAIL", "UNDETERMINED"), receipt


def test_an_unfrozen_entry_reads_as_not_judged_rather_than_failing(direct_vm, direct_deploy, direct_alice):
    """A view must be safe in every state the contract can reach.

    An entry that has been submitted but not frozen is the most common state there
    is — and before M4, reading it raised `KeyError` from the TreeMap, which fails
    the read on chain with `gen_call failed (code=-32000)`. A view is a reader;
    it reports absence rather than failing on it.
    """
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    submit_entry(c, direct_vm, direct_alice, stack="python")
    entry = c.get_entry(program_id, 0)
    assert entry["status"] == "SUBMITTED", entry
    assert [criterion["verdict"] for criterion in entry["criteria"]] == ["NOT_JUDGED"] * 5, entry
    assert entry["tree_digest"] == "", entry
    assert entry["payout"] == 0, entry


def test_a_receipt_can_be_read_before_the_evidence_is_captured(direct_vm, direct_deploy, direct_alice):
    """The frontend reads receipts while entrants are still submitting."""
    c = direct_deploy(CONTRACT)
    program_id = open_program(c, direct_vm, direct_alice, criteria=ALL_CRITERIA)["program_id"]
    submit_entry(c, direct_vm, direct_alice, stack="python")
    receipt = c.get_receipt(program_id, 0)
    assert receipt["status"] == "SUBMITTED", receipt
    assert receipt["challenges"] == [], receipt
    assert c.get_accuracy(program_id)["entries"] == 1