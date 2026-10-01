#!/usr/bin/env python3
"""Aggregate every M1 spike pass into one reported figure.

Reads the machine-generated evidence files in ``docs/evidence/`` — never the
prose — and prints the convergence number, the comparison mode, and the
caveats a reviewer needs in order to judge the decision.

The point of this script is that the headline number and the caveats come from
the same source, so a summary cannot drift away from the evidence it summarises.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gl_env import REPO_ROOT  # noqa: E402

EVIDENCE_GLOB = "m1-*.json"


def load_passes() -> list:
    directory = REPO_ROOT / "docs" / "evidence"
    passes = []
    for path in sorted(directory.glob(EVIDENCE_GLOB)):
        data = json.loads(path.read_text())
        if data.get("artifact") != "m1-consensus-spike":
            continue
        passes.append((path.name, data))
    return passes


def main() -> int:
    passes = load_passes()
    if not passes:
        print("no M1 evidence files found", file=sys.stderr)
        return 1

    runs = []
    for name, data in passes:
        for observation in data.get("runs", []):
            observation = dict(observation)
            observation["_pass"] = name
            observation["_repo"] = observation.get("repository", {}).get("label")
            runs.append(observation)

    converged = [r for r in runs if r.get("converged")]
    diverged = [r for r in runs if not r.get("converged")]

    tally = {}
    disagree_runs = []
    quorum_sizes = []
    idle_totals = []
    seconds = []
    for run in runs:
        bucket = run.get("bucket") or "UNDECODED"
        tally[bucket] = tally.get(bucket, 0) + 1
        votes = run.get("final_round_votes") or {}
        if votes.get("DISAGREE"):
            disagree_runs.append(
                {
                    "pass": run["_pass"],
                    "repo": run["_repo"],
                    "votes": votes,
                    "bucket_accepted": run.get("bucket"),
                }
            )
        agree = votes.get("AGREE", 0)
        if agree:
            quorum_sizes.append(agree)
        idle_totals.append(votes.get("IDLE", 0))
        if run.get("seconds"):
            seconds.append(run["seconds"])

    repos = sorted({r["_repo"] for r in runs if r.get("_repo")})
    expected_repos = {
        o["repository"]["label"]
        for o in runs[0].get("repository", []) if isinstance(o, dict)
    } if runs else set()

    report = {
        "passes": [name for name, _ in passes],
        "runs": len(runs),
        "convergence": f"{len(converged)}/{len(runs)}",
        "converged": len(converged),
        "did_not_converge": len(diverged),
        "repositories": repos,
        "accepted_buckets": tally,
        "rounds_needed": sorted({r.get("rounds") for r in runs if r.get("rounds") is not None}),
        "agree_vote_sizes": sorted(set(quorum_sizes)),
        "idle_votes_per_run": sorted(set(idle_totals)),
        "seconds": {
            "min": min(seconds) if seconds else None,
            "max": max(seconds) if seconds else None,
        },
        "runs_with_a_disagree_vote": disagree_runs,
        "decision": passes[0][1].get("decision", {}).get("decided_comparison_mode"),
    }

    print("== M1 aggregate, read from docs/evidence/m1-*.json ==")
    print(json.dumps(report, indent=2))

    print("\n== what this measurement does NOT establish ==")
    buckets = set(tally) - {"UNDECODED"}
    if buckets == {"CONSISTENT"}:
        print(
            "  Every run answered CONSISTENT. The INCONSISTENT bucket was never "
            "exercised, and INCONSISTENT is the discriminating case: it is where a "
            "jury is most likely to split, so this spike does not show that a "
            "2-bucket comparison converges on a refuted claim. All three inputs are "
            "the same organisation's own repositories with honest READMEs."
        )
    if report["agree_vote_sizes"] == [3]:
        print(
            "  The quorum was exactly 3 of 5 validators in every run, with 1-2 "
            "validators idle. A 3/5 majority with no idle headroom is the margin, and "
            "a DISAGREE was observed, so 'converged' here means 'a bare majority was "
            "reached', not 'the jury was unanimous'."
        )
    if not report["rounds_needed"] or report["rounds_needed"] == [0]:
        print(
            "  No run needed a rotation or a second round, so leader-retry behaviour "
            "under disagreement is untested."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
