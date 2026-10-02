"""Shared helpers for the direct suite.

Two things every test needs and neither should re-derive: how to stand up a
programme, and how to mock the three GitHub endpoints ``freeze_entry`` reads.

The mocks are **exact regexes on the full URL**, not loose fragments. A loose
pattern that does not match would leave the request unmocked, and an unmocked
request in the direct runner falls through the dispatcher rather than failing
loudly — so a sloppy mock turns a rejection test into a test of nothing. The
suite therefore checks that the mocks it registered were actually hit.
"""

from __future__ import annotations

import json
import pathlib
import re

#: Three of the five fixed criteria. Three is the documented minimum.
CRITERIA = [
    {"key": "commit_predates_deadline", "weight": 3},
    {"key": "declared_language_present", "weight": 2},
    {"key": "required_files_present", "weight": 1},
]

#: All five, for tests that need the whole set.
ALL_CRITERIA = CRITERIA + [
    {"key": "repo_resolves", "weight": 1},
    {"key": "not_duplicate", "weight": 2},
]

REPO = "genlayerlabs/genlayer-py"
COMMIT = "dd25ef7f43e99a14b8fe42a64e01374845ad4d2d"
DEMO = "https://github.com/genlayerlabs/genlayer-py"

#: An absolute unix second. There is no block clock on this runner, so the deadline
#: is compared arithmetically against GitHub's signed committer date — which means
#: the test constants have to be *mutually* consistent or the deadline criterion
#: will (correctly) fail. 1800000000 is 2027-01-15T08:00:00Z.
DEADLINE = 1_800_000_000

#: The deadline exactly as ISO-8601, for the boundary tests that must straddle it
#: by one second. `_parse_iso8601` is a pure function, so these are arithmetic
#: facts about the contract, not observations about arrival time.
DEADLINE_ISO = "2027-01-15T08:00:00Z"
DEADLINE_PLUS_1 = 1_800_000_001
DEADLINE_MINUS_1 = 1_799_999_999

#: A commit whose committer date is comfortably before DEADLINE.
COMMITTER_BEFORE = "2026-06-10T14:46:12Z"

#: Exactly at DEADLINE. The criterion is `observed < deadline`, so this FAILS:
#: "at the deadline" is not "before the deadline", and the test pins that.
COMMITTER_AT = DEADLINE_ISO

#: One second after DEADLINE, for the other side of the same boundary.
COMMITTER_AFTER = "2027-01-15T08:00:01Z"

#: One second before DEADLINE. This is the only committer date that PASSES.
COMMITTER_MINUS_1 = "2027-01-15T07:59:59Z"

#: The same instant written with a non-UTC offset. 08:00:00+00:00 is
#: 2027-01-15T03:00:00-05:00, and both denote unix second 1800000000, so the
#: contract must judge it identically. A parser that compares strings, or that
#: ignores the offset, fails here.
COMMITTER_OFFSET = "2027-01-15T03:00:00-05:00"

_COMMIT_URL = re.escape(f"api.github.com/repos/{REPO}/commits/{COMMIT}")
_TREE_URL = re.escape(f"api.github.com/repos/{REPO}/git/trees/{COMMIT}")
_REPO_URL = re.escape(f"api.github.com/repos/{REPO}")

COMMIT_PATTERN = rf"https://{_COMMIT_URL}"
TREE_PATTERN = rf"https://{_TREE_URL}\?recursive=1"
REPO_PATTERN = rf"https://{_REPO_URL}"


def criteria_json(criteria=CRITERIA) -> str:
    return json.dumps(criteria)


def open_program(contract, vm, account, pool=1000, criteria=CRITERIA, name="test-programme"):
    """Open a programme as ``account`` with ``pool`` locked.

    Returns the contract's own result dict, so a test can assert on a refusal
    rather than only on the state it left behind.
    """
    vm.sender = account
    vm.value = pool
    return contract.open_program(name, criteria_json(criteria), DEADLINE, 3600, "{}")


def tree_response(paths, truncated=False):
    """A GitHub tree payload for ``paths``."""
    return {
        "status": 200,
        "body": json.dumps(
            {
                "sha": COMMIT,
                "truncated": truncated,
                "tree": [{"path": path, "type": "blob", "sha": "0" * 40} for path in paths],
            }
        ),
    }


def commit_response(committer_date=COMMITTER_BEFORE, sha=COMMIT):
    return {
        "status": 200,
        "body": json.dumps(
            {
                "sha": sha,
                "commit": {"committer": {"date": committer_date}},
            }
        ),
    }


def repo_response():
    return {"status": 200, "body": json.dumps({"full_name": REPO, "private": False})}


def reset_mocks(vm):
    """Drop every registered web and LLM mock, without the unused-mock warning.

    ``gltest``'s ``_match_web_mock`` returns the **first** registered pattern that
    matches, so calling ``mock_web`` twice for one URL leaves the first response in
    force and silently discards the second::

        for i, (pattern, response) in enumerate(self._web_mocks):
            if pattern.search(url):
                ...
                return response

    That is a live hazard for this suite, because most tests need two different
    responses for the same endpoint in sequence — an outage and then a healthy
    reply, or a pre-deadline commit and then a post-deadline one. Getting it wrong
    does not fail loudly; the test just reads the *first* verdict twice and then
    fails somewhere unrelated, having told you nothing.

    ``VMContext.clear_mocks`` would also work but emits ``RuntimeWarning`` for every
    mock that was never hit, which is noise rather than signal here.
    """
    vm._web_mocks = []
    vm._llm_mocks = []
    vm._web_mocks_hit = set()
    vm._llm_mocks_hit = set()


def mock_healthy(vm, paths=None, committer_date=COMMITTER_BEFORE, **extra):
    """Mock all three endpoints with healthy, agreeing responses.

    ``paths`` defaults to a tree that contains a README and a ``.py`` file, so
    ``required_files_present`` and ``declared_language_present`` both pass, and
    ``committer_date`` defaults to comfortably before ``DEADLINE`` so
    ``commit_predates_deadline`` passes too. A "healthy" mock must make every
    criterion pass; a helper that quietly produced a failing verdict would make
    every downstream assertion ambiguous.
    """
    if paths is None:
        paths = ["README.md", "src/genlayer_py/__init__.py", "setup.py"]
    _assert_seeded()
    reset_mocks(vm)
    vm.mock_web(COMMIT_PATTERN, commit_response(committer_date))
    vm.mock_web(TREE_PATTERN, tree_response(paths, truncated=extra.get("truncated", False)))
    vm.mock_web(REPO_PATTERN, extra.get("repo", repo_response()))


def mock_status(vm, status, body="", **extra):
    """Mock every endpoint with one non-200 status.

    Used for the source-failure group: a rate limit or a server error must
    produce ``UNDETERMINED``, never a rejection. Clears previous mocks first —
    see ``reset_mocks`` for why that is not optional.
    """
    _assert_seeded()
    reset_mocks(vm)
    response = {"status": status, "body": body, **extra}
    vm.mock_web(COMMIT_PATTERN, response)
    vm.mock_web(TREE_PATTERN, response)
    vm.mock_web(REPO_PATTERN, response)


def submit_entry(contract, vm, account, program_id="0", *, repo=REPO, commit=COMMIT,
                 demo=DEMO, stack="python", claims=None):
    """Submit one entry and return the contract's own result dict.

    Every identifying field is a keyword so a test can vary exactly one of them
    and leave the rest alone. That matters: a test that changes the commit *and*
    the paths proves nothing about either, because the digest would differ anyway.
    """
    vm.sender = account
    return contract.submit_entry(
        program_id, repo, commit, demo, stack, claims or '["ships a python sdk"]'
    )


def freeze(contract, vm, program_id="0", entry_index=0):
    """Freeze one entry with whatever mocks the caller registered."""
    return contract.freeze_entry(program_id, entry_index)

def _assert_seeded() -> None:
    """Fail loudly if the gltest SDK cache is not seeded.

    Without the seed, ``setup_sdk_paths`` falls through to downloading the
    GenVM release tarball, and the download URL 404s here. The error surfaces as a
    bare ``urllib.error.HTTPError: 404`` deep inside ``mock_healthy``, which reads
    as a test bug rather than a missing cache. This turns it into one clear
    message.
    """
    import os

    cache = pathlib.Path.home() / ".cache" / "gltest-direct"
    needed = cache / "extracted" / "v0.6.0-rc5" / "py-lib-genlayer-std"
    if not needed.is_dir() or not any(needed.iterdir()):
        raise RuntimeError(
            "gltest SDK cache is not seeded, so the SDK loader tries to download "
            "from GitHub releases (404 in this environment).\n"
            "Seed it with:\n"
            "  G=/home/unify/.cache/gltest-direct\n"
            "  L=/home/unify/.cache/genvm-linter\n"
            "  mkdir -p $G/extracted/v0.6.0-rc5/{py-genlayer,py-lib-genlayer-std}\n"
            "  ln -sf $L/genvm-universal-genlayerlabs-genvm-manager-v0.6.0-rc5.tar.xz "
            "$G/genvm-universal-v0.6.0-rc5.tar.xz\n"
            "  ln -sf $L/extracted/genlayerlabs-genvm-manager-v0.6.0-rc5/py-genlayer/"
            "5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng "
            "$G/extracted/v0.6.0-rc5/py-genlayer/\n"
            "  ln -sf $L/extracted/genlayerlabs-genvm-manager-v0.6.0-rc5/"
            "py-lib-genlayer-std/kzr02ndm9et4qkmbqpq5djjt5sme2yt76n7sz1qbzax0knt6mam0 "
            "$G/extracted/v0.6.0-rc5/py-lib-genlayer-std/"
        )


def expect_fail(call, needle, *args, **kwargs):
    """Assert that a contract method *raises* rather than returning a refusal.

    Two shapes of "no" exist in this contract and they are not interchangeable:

    * ``_refuse(...)`` — returns ``{"ok": False, "error": ...}``. Used by methods
      that received value and therefore must not revert, or whose failure is a
      normal business outcome.
    * ``_fail(...)`` — raises. Used where a revert is the honest answer, e.g.
      calling ``finalize_program`` on a programme you do not own.

    A test that catches the wrong one passes for the wrong reason, so this helper
    asserts on the raise and on the message, and ``assert_refused`` below asserts
    on the returned refusal.
    """
    import pytest

    with pytest.raises(Exception) as caught:  # noqa: B017 - the type is the SDK's
        call(*args, **kwargs)
    text = str(caught.value)
    assert needle in text, f"expected {needle!r} in the raised error, got {text!r}"
    return text


def assert_refused(result, needle):
    """Assert a returned refusal, and that it changed nothing."""
    assert result["ok"] is False, result
    assert result.get("state_changed") is False, result
    assert needle in result["error"], result
    return result


def standing_entry(contract, vm, account, program_id, *, commit=COMMIT, stack="python",
                   paths=None, committer_date=COMMITTER_BEFORE, entry_index=None,
                   repo=REPO):
    """Submit and freeze one entry that stands, returning its freeze result.

    "Stands" means every chosen criterion PASSes, so the entry is in the state a
    challenge is allowed against and the state that can win the pool.
    """
    mock_healthy(vm, paths=paths or ["README.md", "src/pkg/__init__.py", "setup.py"],
                 committer_date=committer_date)
    vm.sender = account
    submitted = contract.submit_entry(program_id, repo, commit, DEMO, stack,
                                      '["ships a python sdk"]')
    assert submitted["ok"] is True, submitted
    index = submitted["entry_index"] if entry_index is None else entry_index
    frozen = contract.freeze_entry(program_id, index)
    assert frozen["status"] == "STANDING", frozen
    return frozen
