#!/usr/bin/env python3
"""Reproduce the competitive-gap counts quoted in ../HANDOFF.md.

Reads the saved Portal Project Explorer snapshot (portal-explorer-projects.json)
and reports, for each capability probe, how many published GenLayer projects
mention it. This is a keyword probe over project *descriptions*, not a quality
judgement: a hit means "claims this", a miss means "does not claim this".

Run:
    python3 competitor-gap-probe.py
    python3 competitor-gap-probe.py --json

Snapshot provenance:
    https://portal-admin.genlayer.foundation/api/v1/explorer/
    retrieved 2026-10-01, 219 projects.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "portal-explorer-projects.json"

# Each probe is a capability claim. Keep the regexes narrow enough that a
# passing match means the project actually claims the capability.
# These were tightened after a first pass produced false positives: a loose
# "appeal ... one" pattern matched "the agent may appeal once" and inflated the
# targeted-appeal count. Counts below are from the tightened patterns.
PROBES: dict[str, str] = {
    # --- the wedge: is the jury itself accountable? ---
    # 0 — the only honest empty cell in the table.
    "agreement / overturn statistic published": r"agreement rate|consensus rate|vote distribution|confidence spread|overturn rate|appeal success rate|calibrat|disagreement rate|how many validators (agree|agreed)",
    # 0 — nobody anchors judging to a point in time rather than to whatever the
    # page says at judging time.
    "point-in-time / as-of anchor": r"diff.*(deadline|as-?of)|as-?of|point-?in-?time|historical view|what changed since",
    # 1 — GenHire is the only project exposing per-criterion detail on the record.
    "per-criterion breakdown on the public record": r"per-?criteri[a-z]* (confiden|score|band|breakdown|detail)|criteri[a-z]* breakdown",
    # 5 — per-criterion consensus is a minority technique, not the default.
    "per-criterion consensus": r"per-?criteri|each criteri|criteri(on)? by criteri|every criteri|criteria independently|one boolean per|per-?dimension",
    # 21 — appeals are common; they are not the differentiator.
    "any appeal mechanism": r"\bappeal",
    # 1 by description (Hackathon Judge does snapshot at submit time in code but
    # does not claim it in its Explorer copy).
    "submit-time evidence freeze": r"pin(ned)? at (submi|creat)|at submission time|snapshot.*(submit|creat)|submission-?time snapshot|as-?submitted",
    "self-description vs verified artifact": r"self-?describ|overclaim|claim(ed)? vs verified|marketing page|mere claim|unfalsifiable|trust me",
    "inter-model agreement measurement": r"inter-?model|cross-?model|model diversity|agreement across",
    # --- adjacent, already crowded ---
    "immutable commit ref": r"commit sha|head sha|immutable commit|40-character sha|git sha|pinned commit|immutable ref",
    "escalate to a human": r"escalat|triage|second pass|human (review|panel|decide|adjudicat)|manual review|refer to",
    "mechanical entry-validity screen": r"404|dead ?link|private repo|link rot|availability check",
    "weighted scoring / rubric": r"\bscor(e|ing)\b|\brubric\b|weighted|criteri",
    "escrow or payout": r"escrow|payout|claim_award|paid|transfer",
}

# Projects that state the same pitch as "AI consensus replaces human judging".
REPLACES_HUMAN = re.compile(
    r"replac\w*[^.]{0,60}(human|committee|panel|manual|judg)"
    r"|elimin\w*[^.]{0,40}(human|committee|manual)",
    re.I,
)


def blob(project: dict) -> str:
    return " ".join(
        [
            project.get("name") or "",
            project.get("try_it") or "",
            " ".join(project.get("tags") or []),
        ]
    )


def load() -> list[dict]:
    with SNAPSHOT.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    if not SNAPSHOT.exists():
        print(f"missing snapshot: {SNAPSHOT}", file=sys.stderr)
        return 1

    projects = load()
    results: dict[str, dict] = {}

    for name, pattern in PROBES.items():
        hits = [p["name"] for p in projects if re.search(pattern, blob(p), re.I)]
        results[name] = {"count": len(hits), "projects": hits}

    replaces = [p["name"] for p in projects if REPLACES_HUMAN.search(p.get("try_it") or "")]

    # Direct competitors = the user's supplied idea, as already built.
    direct = re.compile(r"\bjudge|judging|jury|\bgrant\b|bount(y|ies)|hackathon|contest|competition|prize", re.I)
    quality = re.compile(r"\bscor(e|ing)\b|\brubric\b|weighted|criteri|\breview|\bmilestone|deliverable|submission", re.I)
    competitor_count = sum(1 for p in projects if direct.search(blob(p)) and quality.search(blob(p)))

    summary = {
        "snapshot_projects": len(projects),
        "direct_competitors": competitor_count,
        "claims_to_replace_human_judging": len(replaces),
        "claims_to_replace_human_judging_projects": replaces,
        "probes": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"snapshot: {summary['snapshot_projects']} published projects")
    print(f"direct competitors (judge|grant|bounty|hackathon AND score|review|milestone): {competitor_count}")
    print(f"projects claiming to replace human judging: {len(replaces)}")
    for name in replaces:
        print(f"  - {name}")
    print()
    width = max(len(name) for name in PROBES)
    for name, data in results.items():
        print(f"[{data['count']:>3}] {name}")
        for project in data["projects"][:6]:
            print(f"        - {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
