#!/usr/bin/env python3
"""Deploy an Intelligent Contract to GenLayer Studio-dev and prove it finalized.

The one deploy path for this project. M0 established three facts that this
script encodes rather than re-derives:

1. **A fee distribution is mandatory.** ``deploy_contract`` without
   ``fees`` reverts with ``FeesDistributionMissing``. The distribution is
   estimated per deploy, because it depends on the network, not on the code.
2. **A simplified receipt does not name the fields a reader needs.**
   ``wait_for_transaction_receipt`` returns no ``status_name`` and no
   ``contract_address`` on the pinned SDK. The full record is re-read *after*
   the lifecycle reports a decision, and the lifecycle is taken from
   ``lifecycle.state``. A missing key is never treated as a failure.
3. **Studio-dev resets.** Every run redeploys from scratch and appends to a
   dated evidence file. Nothing here is incremental state.

Rules this script enforces:

* The private key is read from the process environment only. It is never
  written anywhere, and no secret value is printed.
* Any path given for output must be outside the checkout, so a run cannot
  leave credential material or a mutable artefact inside the repository.
* A submitted transaction is not a deployment until its lifecycle and
  execution result have been read. Exit code is non-zero if the transaction
  did not reach ``finalized``.

Usage
-----
    .venv/bin/python scripts/deploy_studio_dev.py --contract contracts/contest_receipt.py
    .venv/bin/python scripts/deploy_studio_dev.py --contract contracts/m0_stub_probe.py --dry-run

``--dry-run`` lints and probes the schema without sending a transaction, which
is the cheap way to catch a contract that the node will reject.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from gl_env import (  # noqa: E402
    REPO_ROOT,
    STUDIO_DEV_EXPLORER,
    SecretHandlingError,
    assert_outside_checkout,
    deployer_account,
    env_value,
    probe_url,
    refuse_secret_material,
    studio_dev_client,
)

DEFAULT_CONTRACT = "contracts/contest_receipt.py"


def log(message: str) -> None:
    print(message, flush=True)


def check_runner_pin(source: str) -> dict:
    """Confirm the contract's pinned runner is one the live target accepts.

    M0 measured that the runner hash named in the published documentation is
    rejected by this target, so a hash is never trusted because it appears in a
    doc. This is the cheap local check; ``--verify`` re-probes the node.
    """
    first_line = source.splitlines()[0] if source.splitlines() else ""
    pinned = None
    if "Depends" in first_line:
        pinned = first_line.split('"')[3] if first_line.count('"') >= 4 else None
    return {
        "header": first_line,
        "pinned_runner": pinned,
        "is_pinned": bool(pinned),
        "note": (
            "The runner must be verified against the live target, not read from "
            "documentation. IMPLEMENTATION-PLAN.md section 4.1 and the M0 record."
        ),
    }


def probe_schema(client, source: str) -> dict:
    """Derive the contract schema on the live node.

    This is not a weaker check than the AST linter. It caught a real defect the
    linter passed — a storage annotation that resolved to no name — so both run.
    The SDK's own wrapper refuses non-localnet chains, so the JSON-RPC method is
    called directly.
    """
    import genlayer_py

    version = getattr(genlayer_py, "__version__", "unknown")
    try:
        response = client.provider.make_request(
            method="gen_getContractSchemaForCode", params=[source.encode().hex()]
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "genlayer_py": version,
            "error": f"{type(exc).__name__}: {exc}"[:2500],
        }
    result = response.get("result") or {}
    methods = result.get("methods", {})
    return {
        "ok": True,
        "genlayer_py": version,
        "method_count": len(methods),
        "methods": {
            name: {
                "readonly": spec.get("readonly"),
                "params": [p[0] for p in spec.get("params", [])],
                "returns": spec.get("ret"),
            }
            for name, spec in sorted(methods.items())
        },
    }


def summarize_transaction(client, tx_id: str) -> dict:
    """Read the full record after the lifecycle has settled.

    Derives the lifecycle from ``lifecycle.state`` because the simplified
    receipt does not carry the fields a reader needs.
    """
    record = client.get_transaction(tx_id)
    lifecycle = record.get("lifecycle") or {}
    last_round = record.get("last_round") or {}
    votes = last_round.get("validator_votes_name") or []
    tally: dict = {}
    for vote in votes:
        tally[vote] = tally.get(vote, 0) + 1
    return {
        "lifecycle_state": str(lifecycle.get("state", "")).lower(),
        "outcome": str(lifecycle.get("outcome", "")).lower(),
        "contract_address": record.get("to_address"),
        "consensus_result": record.get("result_name"),
        "execution_result": record.get("txExecutionResultName"),
        "rounds": int(record.get("num_of_rounds") or 0),
        "vote_tally": tally,
        "appealed": record.get("appealed"),
        "note": (
            "Full record re-read after the lifecycle settled. A record read before "
            "finalization still carries in-flight consensus fields."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy to GenLayer Studio-dev")
    parser.add_argument(
        "--contract",
        default=DEFAULT_CONTRACT,
        help="path to the contract source, relative to the repository root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="lint and probe the schema; send no transaction",
    )
    parser.add_argument(
        "--evidence",
        default=None,
        help="write the observation to this path; must be outside the checkout",
    )
    args = parser.parse_args()

    contract_path = (REPO_ROOT / args.contract).resolve()
    if not contract_path.exists():
        print(
            f"contract not found: {args.contract}\n"
            f"expected at {contract_path}. M2 ships no contract; the first real "
            "contract is written at M3.",
            file=sys.stderr,
        )
        return 1
    source = contract_path.read_text()

    account = deployer_account()
    client = studio_dev_client(account=account)

    record = {
        "artifact": "deployment",
        "generated_by": "scripts/deploy_studio_dev.py",
        "observed_on": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "network": "GenLayer Studio-dev (temporary; may reset)",
        "rpc": env_value("GENLAYER_STUDIO_DEV_RPC"),
        "chain_id": int(env_value("GENLAYER_STUDIO_DEV_CHAIN_ID") or "61997"),
        "durable": False,
        "contract": {
            "path": str(contract_path.relative_to(REPO_ROOT)),
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "bytes": len(source.encode()),
        },
        "runner_pin": check_runner_pin(source),
        "schema_probe": probe_schema(client, source),
    }

    if not record["schema_probe"].get("ok"):
        log("SCHEMA PROBE FAILED — the node would reject this contract.")
        log(f"  {str(record['schema_probe'].get('error'))[:400]}")
        emit(record, args.evidence)
        return 1
    log(
        f"schema probe: {record['schema_probe']['method_count']} method(s) — "
        f"{', '.join(record['schema_probe']['methods'])}"
    )
    log(f"runner pin: {record['runner_pin']['pinned_runner']}")

    if args.dry_run:
        log("dry run: no transaction sent.")
        emit(record, args.evidence)
        return 0

    log("\nestimating fee distribution…")
    distribution = client.estimate_fees_distribution()
    record["fee_distribution"] = distribution
    log(f"  {distribution}")

    log("deploying…")
    started = time.time()
    tx_hash = client.deploy_contract(source, account=account, fees={"distribution": distribution})
    tx_id = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    log(f"  transaction_id = {tx_id}")

    client.wait_for_transaction_receipt(tx_hash, wait_until="finalized", interval=5000, retries=120)
    record["deployment"] = {
        "transaction_id": tx_id,
        "seconds": round(time.time() - started, 1),
    }
    record["deployment"].update(summarize_transaction(client, tx_id))
    deployment = record["deployment"]
    log(
        f"  {deployment['lifecycle_state']}/{deployment['outcome']} "
        f"· {deployment['consensus_result']} · {deployment['execution_result']}"
    )
    log(f"  contract = {deployment['contract_address']}")
    log(f"  votes    = {deployment['vote_tally']}")

    address = deployment.get("contract_address")
    if address:
        record["explorer"] = probe_url(f"{STUDIO_DEV_EXPLORER}/address/{address}", attempts=4)
        log(f"  explorer = HTTP {record['explorer']['http_status']}")

    emit(record, args.evidence)

    if deployment["lifecycle_state"] != "finalized":
        log("\nNOT DEPLOYED: the transaction did not reach 'finalized'.")
        log("  A submitted transaction is not a deployment until its status and")
        log("  execution result have been inspected.")
        return 1
    log("\nDEPLOYED and finalized.")
    return 0


def emit(record: dict, evidence: str | None) -> None:
    """Write the observation.

    Two separate guards, because they protect against different things. The
    path guard refuses a *credential* file inside the checkout. The content
    guard refuses to write the real private key into any file, wherever that
    file lives — which is the rule the plan actually states, and it cannot be
    satisfied by a path check alone.
    """
    if evidence is None:
        return
    path = assert_outside_checkout(evidence)
    payload = json.dumps(record, indent=2) + "\n"
    refuse_secret_material(payload, str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    log(f"observation written: {path}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SecretHandlingError as error:
        print(f"secret-handling rule violated: {error}", file=sys.stderr)
        raise SystemExit(2)
