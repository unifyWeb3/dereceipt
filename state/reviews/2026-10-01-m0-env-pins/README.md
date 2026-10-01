# M0 — environment and pins

Milestone 0 of `state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`
§5. The gate: **a one-method stub contract lints, deploys, and reaches
`Finalized` on chain 61997.** Gate result: **passed**.

Nothing here is the product. `contracts/m0_stub_probe.py` is a transport probe
and is superseded by the real contract at M3.

## What was measured

| Fact | Value | How |
| --- | --- | --- |
| Accepted runner hash | `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng` | `gen_getContractSchemaForCode` against the live target |
| Rejected runner hash | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` — **the hash the published docs name** | same probe, `VM_ERROR: invalid_contract runner malformed` |
| GenVM version | `v0.3.0-rc7-x86_64-linux-release` | parsed from the GenVM log the target returns with a failure |
| Chain | `eth_chainId` `0xf22d` = 61997 | JSON-RPC |
| Client SDK | `genlayer-py==0.19.0rc2` | 0.18.0 cannot deploy to this target |
| Explorer | `https://explorer-studio-dev.genlayer.com` | the `.env` explorer variable points at Bradbury, a different network |

The plan asked for the runner hash to be resolved before any contract code was
written. It is resolved, and the answer contradicts the current published docs.

## What is not established

- **No local linter ran.** `genvm-lint` and its variants are absent from PyPI and
  the `genlayer` CLI exposes no lint subcommand. The live schema probe is a
  weaker check — it proves the node compiles the contract, not that static
  analysis is clean. M3's gate must name the tool that actually ran.
- **Docker is unavailable**, so no integration test ran.
- Studio-dev is temporary. Every address in this record may vanish.

## Files

| Path | Role |
| --- | --- |
| `scripts/m0_env_probe.py` | produces every observation and writes the evidence file |
| `scripts/gl_env.py` | secret-safe env loading, Studio-dev client, checkout guard |
| `contracts/m0_stub_probe.py` | one-method stub used for the gate |
| `docs/VERIFICATION.md` | the live log, including the failed attempts |
| `docs/evidence/m0-2026-10-01.json` | machine-generated, from the chain |

## Reproduce

Secrets come from the process environment only; `.env` is not consulted for
them, by design.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
set -a; . ./.env; set +a          # non-secret config; the key is already exported
.venv/bin/python scripts/m0_env_probe.py
```

Exit code 0 means the gate passed. The script redeploys the stub each run and
overwrites the evidence file for that date.
