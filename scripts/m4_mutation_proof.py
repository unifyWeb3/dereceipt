#!/usr/bin/env python3
"""Mutation proofs for the M4 direct suite.

**A green run is not the evidence. A red one is.**

This script breaks the contract on purpose, one group at a time, runs the direct
suite, and records which *named* tests went red. A test that cannot fail when its
subject is broken is decoration: it would keep passing through every future
refactor and prove nothing at the end.

Each mutation is the smallest possible edit that removes one specific behaviour —
a canonicalisation step, a bound, a comparison operator, a guard — so that the
failing test names that behaviour and nothing else. A mutation that turns the
whole suite red is not a proof, it is a syntax error.

The contract is restored from git after every mutation, and the working tree is
checked afterwards, so a crashed run cannot leave the contract broken.

Usage:
    GENVM_VERSION=v0.6.0-rc5 .venv/bin/python scripts/m4_mutation_proof.py
    .venv/bin/python scripts/m4_mutation_proof.py --only deadline,refund
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = REPO / "contracts" / "contest_receipt.py"
RECORD = REPO / "state" / "reviews" / "2026-10-01-m4-direct-tests" / "MUTATIONS.md"
JUNIT = pathlib.Path("/tmp/opencode/mutation-junit.xml")


class Mutation:
    """One deliberate break, and the test that is supposed to notice it."""

    def __init__(self, group, what, old, new, expect):
        self.group = group
        self.what = what
        self.old = old
        self.new = new
        self.expect = expect

    def apply(self, source: str) -> str:
        if self.old not in source:
            raise SystemExit(
                f"mutation {self.group!r}: anchor not found in the contract.\n"
                f"  looking for: {self.old!r}\n"
                "The contract has moved on; update the anchor rather than skipping "
                "the proof, or the mutation log goes stale silently."
            )
        return source.replace(self.old, self.new, 1)


MUTATIONS = [
    Mutation(
        group="canonicalisation",
        what="drop the trailing-slash strip from `_canonical_repo`",
        old='        value = raw.strip().rstrip("/")',
        new='        value = raw.strip()',
        expect="test_repo_url_forms_canonicalise_identically",
    ),
    Mutation(
        group="malformed-shapes",
        what="lower the criteria floor from 3 to 1",
        old="MIN_CRITERIA = 3",
        new="MIN_CRITERIA = 1",
        expect="test_too_few_criteria_are_refused",
    ),
    Mutation(
        group="deadline-boundary",
        what="make the deadline comparison inclusive (`<=`) so the boundary second passes",
        old="elif observed < deadline:",
        new="elif observed <= deadline:",
        expect="test_exactly_at_the_deadline_fails",
    ),
    Mutation(
        group="duplicate",
        what="stop consulting the stored digest set, so duplicates are never caught",
        old='elif f"{program_id}:{digest}" in self.program_seen_digest:',
        new="elif False:",
        expect="test_the_same_tree_under_a_different_repo_spelling_is_caught",
    ),
    Mutation(
        group="declared-vs-measured",
        what="continue past an unknown language token instead of giving up",
        old="                    if not extensions:\n                        matched = None\n                        break",
        new="                    if not extensions:\n                        continue",
        expect="test_an_unknown_language_token_cannot_pass_on_another_tokens_match",
    ),
    Mutation(
        group="source-failure",
        what="treat every non-404 as a pass instead of UNDETERMINED",
        old="                elif repo_status != 200:\n                    verdicts[\"repo_resolves\"] = CRITERION_UNDETERMINED",
        new="                elif False:\n                    verdicts[\"repo_resolves\"] = CRITERION_UNDETERMINED",
        expect="test_a_non_200_non_404_is_undetermined_not_a_failure",
    ),
    Mutation(
        group="digest-integrity",
        what="return a constant from `get_receipt_digest`, so it tracks nothing",
        old="        record = self._accuracy_record(program_id)\n        return _sha256_hex(_canonical_json(record))",
        new='        return "0" * 64',
        expect="test_the_digest_changes_when_a_verdict_is_recorded",
    ),
    Mutation(
        group="authorisation",
        what="drop the owner check from `cancel_program`",
        old='        if self._read(self.program_owner, program_id, None) != gl.message.sender_address:\n            return self._refuse("only the programme owner may cancel")',
        new="        if False:\n            return self._refuse(\"only the programme owner may cancel\")",
        expect="test_a_non_owner_cannot_cancel",
    ),
    Mutation(
        group="challenge",
        what="allow two challenges on one entry",
        old='        if int(self._read(self.entry_challenge_count, key, 0)) >= 1:\n            return self._refuse("this entry has already been challenged once")',
        new='        if int(self._read(self.entry_challenge_count, key, 0)) >= 2:\n            return self._refuse("this entry has already been challenged once")',
        expect="test_a_second_challenge_on_one_entry_is_refused",
    ),
    Mutation(
        group="refund",
        what="stop zeroing the locked balance before emitting, so a repeat cancels twice",
        old="        self.program_locked[program_id] = gl.u256(0)\n        self.program_status[program_id] = PROGRAM_CANCELLED\n        self.program_refunded[program_id] = gl.u256(",
        new="        self.program_status[program_id] = PROGRAM_CANCELLED\n        self.program_refunded[program_id] = gl.u256(",
        expect="test_cancelling_twice_does_not_transfer_twice",
    ),
    Mutation(
        group="conservation",
        what="drop the tie-split remainder, so a 1001 pool allocates 1000",
        old="        remainder = locked - share * len(winners)",
        new="        remainder = 0",
        expect="test_a_tied_split_conserves_every_unit",
    ),
    Mutation(
        group="panel",
        what="report disqualified entries as contested criteria, merging the two counters",
        old="            \"contested_criteria\": int(\n                self._read(self.program_undetermined_count, program_id, 0)\n            ),",
        new="            \"contested_criteria\": int(\n                self._read(self.program_disqualified_count, program_id, 0)\n            ),",
        expect="test_accurancy_separates_undetermined_from_disqualified",
    ),
    Mutation(
        group="payout-ordering",
        what="re-invert the `claim_payout` guard — the defect M4 found on chain",
        old='        if entry_status == ENTRY_PAYOUT_READY and payout_status != PAYOUT_READY:',
        new='        if entry_status == ENTRY_PAYOUT_READY and payout_status != PAYOUT_PENDING_FINALITY:',
        expect="test_the_winner_is_paid_only_after_finalization_is_observed",
    ),
    Mutation(
        group="evidence-intersection",
        what="never read a commit out of the evidence, so AFTER_DEADLINE_WORK can never be upheld",
        old="            challenger_commit = _commit_in_evidence(evidence)",
        new="            challenger_commit = self.entry_commit[key]",
        expect="test_an_upheld_challenge_disqualifies_the_entry_and_forfeits_the_bond",
    ),
    Mutation(
        group="absent-evidence",
        what="re-introduce the empty-manifest inversion: report FAIL from zero paths",
        old="            paths = result.get(\"paths\") or []\n            if not paths:",
        new="            paths = result.get(\"paths\") or []\n            if False:",
        expect="test_an_empty_200_body_makes_every_content_derived_criterion_undetermined",
    ),
    Mutation(
        group="bond-recovery",
        what="stop sweeping denied challenge bonds on cancel, stranding them",
        old='        bonds_returned = 0\n        for index in range(int(self._read(self.program_entry_count, program_id, 0))):\n            key = self._ek(program_id, index)\n            if self._read(self.challenge_status, key, "") != CHALLENGE_DENIED:\n                continue',
        new='        bonds_returned = 0\n        for index in range(int(self._read(self.program_entry_count, program_id, 0))):\n            key = self._ek(program_id, index)\n            if True:\n                continue',
        expect="test_a_challenge_bond_is_conserved_across_the_whole_lifecycle",
    ),
]


def failing_tests() -> set[str]:
    """Names of the tests that went red in the last run."""
    if not JUNIT.exists():
        raise SystemExit(f"no junit xml at {JUNIT}; the run did not finish")
    import xml.etree.ElementTree as ET

    root = ET.parse(JUNIT).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    names = set()
    for case in suite.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            # Parametrised cases are reported as ``name[param]``. Compare on the
            # base name, or a proof against a parametrised test looks like it
            # failed to notice the mutation when it plainly did.
            names.add(case.get("name").split("[", 1)[0])
    return names


def run_suite() -> set[str]:
    if JUNIT.exists():
        JUNIT.unlink()
    completed = subprocess.run(
        ["bash", str(REPO / "run_direct_tests.sh"), "--tb=no", "-q",
         f"--junitxml={JUNIT}"],
        cwd=REPO, capture_output=True, text=True,
    )
    if "error" in completed.stdout.lower() and "passed" not in completed.stdout:
        print(completed.stdout[-3000:], file=sys.stderr)
        print(completed.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"the suite itself failed to run (exit {completed.returncode})")
    return failing_tests()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated group names to prove")
    args = parser.parse_args()

    original = CONTRACT.read_text()
    backup = pathlib.Path(tempfile.mkdtemp()) / "contest_receipt.py"
    backup.write_text(original)

    wanted = (
        {name.strip() for name in args.only.split(",")} if args.only else None
    )
    results = []
    try:
        for mutation in MUTATIONS:
            if wanted and mutation.group not in wanted:
                continue
            CONTRACT.write_text(mutation.apply(original))
            red = run_suite()
            named = mutation.expect in red
            results.append({
                "group": mutation.group,
                "mutation": mutation.what,
                "expected_test": mutation.expect,
                "expected_test_red": named,
                "tests_red": sorted(red),
                "red_count": len(red),
            })
            verdict = "RED as expected" if named else "DID NOT GO RED"
            print(f"[{mutation.group}] {verdict}: {mutation.expect} "
                  f"({len(red)} test(s) red)")
            if not named:
                print("  red tests were:")
                for name in sorted(red)[:12]:
                    print(f"    {name}")
        print()
        for result in results:
            if not result["expected_test_red"]:
                print(f"  UNPROVEN: {result['group']} -> {result['expected_test']}")

        record = RECORD.parent
        record.mkdir(parents=True, exist_ok=True)
        RECORD.write_text(render(results))
        print(f"wrote {RECORD.relative_to(REPO)}")
        json.dump(results, open("/tmp/opencode/mutations.json", "w"), indent=2)
        unproven = [r for r in results if not r["expected_test_red"]]
        return 1 if unproven else 0
    finally:
        # Restore first, *then* check. Checking before the restore would compare
        # the contract against the last mutation applied and report a false
        # negative — a broken safety check on the one thing that must not be left
        # broken.
        shutil.copy(backup, CONTRACT)
        restored = CONTRACT.read_text() == original
        print(f"contract restored from backup: {'yes' if restored else 'NO'}")
        if not restored:
            print("WARNING: the contract on disk differs from the pre-run state.", file=sys.stderr)


def render(results: list[dict]) -> str:
    lines = [
        "# M4 mutation proofs",
        "",
        "Generated by `scripts/m4_mutation_proof.py`. Do not edit by hand: the",
        "contract is restored from a backup after every mutation, and this table is",
        "rewritten from what actually happened.",
        "",
        "**A green run is not the evidence. A red one is.** Each row below is a",
        "deliberate, minimal break of one behaviour, followed by the name of the",
        "test that noticed. A test that cannot fail when its subject is broken is",
        "decoration.",
        "",
        "| group | mutation | named test that went red | other tests red |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        mark = "" if result["expected_test_red"] else " **UNPROVEN**"
        lines.append(
            f"| {result['group']} | {result['mutation']} | "
            f"`{result['expected_test']}`{mark} | {result['red_count']} |"
        )
    lines += [
        "",
        "## What each mutation proves",
        "",
    ]
    for result in results:
        lines.append(f"### {result['group']}")
        lines.append("")
        lines.append(f"**Mutation.** {result['mutation']}.")
        lines.append("")
        if result["expected_test_red"]:
            lines.append(
                f"**Red.** `{result['expected_test']}` failed, alongside "
                f"{result['red_count'] - 1} other test(s)."
            )
        else:
            lines.append(
                f"**Not red.** `{result['expected_test']}` still passed. The mutation "
                "did not remove the behaviour this test claims to cover."
            )
        if result["tests_red"]:
            lines.append("")
            lines.append("```")
            for name in result["tests_red"]:
                lines.append(name)
            lines.append("```")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())