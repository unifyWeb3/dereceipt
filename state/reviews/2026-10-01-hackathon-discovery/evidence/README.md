# Evidence index

Research artifacts for the GenLayer Builders Program discovery pass and the
Contest Receipt implementation plan. All retrieved **2026-10-01**.

## Regenerate the live sources

```bash
# full contribution-type catalogue (65 types, 2 pages)
for p in 1 2; do
  curl -sS "https://portal-admin.genlayer.foundation/api/v1/contribution-types/?page=$p&page_size=100" \
    -o portal-contribution-types-page$p.json
done
curl -sS https://portal-admin.genlayer.foundation/api/v1/explorer/    -o portal-explorer-projects.json
curl -sS https://portal-admin.genlayer.foundation/api/v1/leaderboard/  -o portal-leaderboard.json
curl -sS https://portal-admin.genlayer.foundation/api/v1/missions/     -o portal-missions.json
curl -sS https://portal-admin.genlayer.foundation/api/v1/configuration/ -o portal-configuration.json
```

The Portal UI is a client-rendered Svelte SPA, so the rules text was recovered
from the shipped bundle at
`https://portal.genlayer.foundation/assets/index-sc_CCLUA.js` and its lazy
`App-*.js` chunk. The API base is `https://portal-admin.genlayer.foundation`
(found in the bundle, not in the HTML).

## Competitive gap counts

```bash
python3 competitor-gap-probe.py          # table
python3 competitor-gap-probe.py --json   # machine-readable
```

## Files

| File | What it is | How obtained |
| --- | --- | --- |
| `portal-contribution-types.json` | 65 contribution types. `projects` = id 41, min 1 / max 200, multiplier 20, 2 submissions per user per week, 2382 submissions. | `GET /api/v1/contribution-types/` |
| `portal-explorer-projects.json` | 219 published Project Explorer entries with descriptions, tags, networks, owners, ratings. | `GET /api/v1/explorer/` |
| `portal-leaderboard.json` | Validator leaderboard. | `GET /api/v1/leaderboard/` |
| `portal-missions.json` | Open missions. One live: "My First Step into GenLayer", closes 2026-10-08 12:00 UTC. | `GET /api/v1/missions/` |
| `portal-configuration.json` | `{"maintenance":{"is_active":false},"mochi":{"is_active":true}}` | `GET /api/v1/configuration/` |
| `competitor-hackathon-judge-contract.py` | `contracts/hackathon_judge.py`, 1193 lines, sha256 `dce90861…`. The direct competitor. Read to confirm the overlap is real, not cosmetic. | `raw.githubusercontent.com/Demigodd00/demigodd00-genlayer-apps` |
| `competitor-hackathon-judge-scorecards-contract.py` | `contracts/hackathon_judge_scorecards.py`, 76 KB, sha256 `cba8e362…` | same |
| `competitor-gap-probe.py` | Reproduces every gap count quoted in the plan. | written for this review |
| `reference-360-build/` | The user's own prior 360/400 submission, saved so the implementing session does not depend on network access. | `github.com/unifyWeb3/milestone-convenant` |

## Provenance notes

- `portal-explorer-projects.json` descriptions are written by the submitting
  builders. They are **claims**, not verified behaviour. No live UI was
  inspected: no browser was available in the research session.
- The competitor contracts were read as source only. No repository code was
  executed and no deployment was called.
- Secret values from the project `.env` were never read into any file in this
  directory. Only variable names and non-secret values (chain IDs, RPC URLs,
  addresses) are recorded.
