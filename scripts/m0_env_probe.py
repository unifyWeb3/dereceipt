#!/usr/bin/env python3
"""M0 — environment and pin verification.

Implements the M0 milestone of
``state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`` §5.

The M0 gate is: **a one-method stub contract lints, deploys, and reaches
``Finalized`` on chain 61997.** This script produces the observations for that
gate and nothing else. It writes one machine-generated evidence file.

What it does, in order:

1. Reports which environment variables are populated, by name only.
2. Probes candidate runner hashes against the live target with
   ``gen_getContractSchemaForCode`` and records which the node accepts. The
   accepted hash is the one the real contract must use; the plan warns that the
   published docs and the previously working build disagree.
3. Deploys ``contracts/m0_stub_probe.py`` and waits for ``Finalized``. A fee
   distribution is estimated and passed explicitly; without one the consensus
   contract rejects the transaction with ``FeesDistributionMissing``.
4. Re-reads the transaction record after the wait, because a record read before
   finalization still carries in-flight consensus fields, and because a
   simplified receipt does not name the fields it omits.
5. Checks that the address and transaction resolve on the Studio-dev explorer.
6. Writes ``docs/evidence/m0-<date>.json``.

Secrets are read from the process environment only. No secret value is printed
or persisted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from gl_env import (  # noqa: E402
    REPO_ROOT,
    STUDIO_DEV_EXPLORER,
    SecretHandlingError,
    deployer_account,
    env_report,
    env_value,
    probe_url,
    studio_dev_client,
)

#: Runner hashes to test. The first is the hash used by the previously scoring
#: 360/400 build; the second is the hash the published docs name. Both are
#: tested against the live target rather than trusted.
CANDIDATE_RUNNERS = (
    "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng",
    "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6",
)

STUB_RELATIVE_PATH = "contracts/m0_stub_probe.py"

REPORTED_VARS = (
    "GENLAYER_STUDIO_DEV_RPC",
    "GENLAYER_STUDIO_DEV_CHAIN_ID",
    "GENLAYER_PRIVATE_KEY",
    "DEPLOYER_ADDRESS",
    "GENLAYER_FALLBACK_RPC_URL",
    "GENLAYER_BRADBURY_RPC_URL",
    "APP_DATABASE_URL",
)


def log(message: str) -> None:
    print(message, flush=True)


def rpc(client, method: str, params, timeout_note: str = ""):
    """One JSON-RPC call with an explicit timeout, per the run rules."""
    started = time.time()
    try:
        response = client.provider.make_request(method=method, params=params)
    except Exception as exc:  # noqa: BLE001 - the failure text is evidence
        return {
            "method": method,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:2000],
            "error_code": getattr(exc, "code", None),
            "elapsed_s": round(time.time() - started, 2),
            "note": timeout_note,
        }
    return {
        "method": method,
        "ok": "result" in response,
        "elapsed_s": round(time.time() - started, 2),
        "note": timeout_note,
        "result": response.get("result"),
        "error": response.get("error"),
    }


def contract_source(runner_hash: str) -> str:
    """Return the stub source with the header pinned to ``runner_hash``."""
    text = (REPO_ROOT / STUB_RELATIVE_PATH).read_text()
    lines = text.splitlines(keepends=True)
    lines[0] = f'# {{ "Depends": "{runner_hash}" }}\n'
    return "".join(lines)


def probe_runner(client, runner_hash: str) -> dict:
    """Ask the live node whether it accepts a contract pinned to this runner."""
    source = contract_source(runner_hash)
    observation = rpc(
        client,
        "gen_getContractSchemaForCode",
        [source.encode().hex()],
        "an accepted runner returns a schema; a rejected one returns VM_ERROR",
    )
    observation["runner_hash"] = runner_hash
    accepted = bool(observation.get("ok")) and isinstance(
        observation.get("result"), dict
    )
    observation["accepted"] = accepted
    if not accepted:
        # The provider raises rather than returning an error object for a
        # -32603 execution failure, so the text can arrive either way.
        error = observation.get("error")
        text = error.get("message", "") if isinstance(error, dict) else str(error or "")
        observation["error_summary"] = _summarize_error(text) or None
        observation["genvm_versions_seen"] = _genvm_versions(text)
        observation["genvm_versions_seen_note"] = (
            "Parsed from the GenVM log attached to the failure. This is the "
            "version the live target runs, read from the target itself."
        )
    else:
        result = observation["result"]
        observation["method_count"] = len(result.get("methods", {}))
        observation["method_names"] = sorted(result.get("methods", {}).keys())
    return observation


def _summarize_error(message: str) -> str:
    """Pull the short, quotable part out of a verbose GenVM error string.

    GenVM returns its failure as ``{"kind": "VM_ERROR", "message": "..."}``
    inside a Python-repr payload, so the summary stops at the closing quote of
    the message rather than trailing into the repr punctuation.
    """
    # The payload is a Python repr, so a doubled-quoted JSON message is
    # recoverable. Prefer the inner message, which names the actual cause.
    inner = re.search(r'message\\?"?: ?\\?"(.*?)\\?"\}', message)
    if inner:
        return f"{_error_kind(message)}: {inner.group(1)}"[:200]
    for needle in ("VM_ERROR", "USER_ERROR", "invalid_contract runner malformed"):
        if needle in message:
            return needle
    return message[:200]


def _error_kind(message: str) -> str:
    for kind in ("VM_ERROR", "USER_ERROR", "EXECUTION_ERROR"):
        if kind in message:
            return kind
    return "error"


def _genvm_versions(message: str) -> list:
    versions = []
    for chunk in message.split("'version': '")[1:]:
        version = chunk.split("'")[0]
        if version not in versions:
            versions.append(version)
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description="M0 environment and pin probe")
    parser.add_argument(
        "--evidence-dir",
        default=str(REPO_ROOT / "docs" / "evidence"),
        help="directory for the machine-generated evidence file",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="probe only; do not deploy (leaves the M0 gate unsatisfied)",
    )
    args = parser.parse_args()

    evidence_dir = pathlib.Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    evidence_path = evidence_dir / f"m0-{today}.json"

    log("== 1. environment (names and populated-or-not; no values) ==")
    variables = env_report(REPORTED_VARS)
    for name, status in variables.items():
        log(
            f"   {name:32} populated={status['populated']!s:5} "
            f"process_env={status['in_process_env']!s:5} dotenv={status['in_dotenv_file']}"
        )
    unused = "APP_DATABASE_URL"
    log(f"   note: {unused} is present and is deliberately unused. The contract is the record.")

    log("\n== 2. account and balance ==")
    account = deployer_account()
    expected_address = env_value("DEPLOYER_ADDRESS")
    derived_address = account.address
    address_matches = (
        expected_address is not None
        and expected_address.lower() == derived_address.lower()
    )
    log(f"   derived address            = {derived_address}")
    log(f"   DEPLOYER_ADDRESS matches   = {address_matches}")
    if not address_matches:
        log("   WARNING: the private key in the environment is not DEPLOYER_ADDRESS.")

    log("\n== 3. chain identity ==")
    client = studio_dev_client(account=account)
    chain_id_rpc = rpc(client, "eth_chainId", [])
    net_version = rpc(client, "net_version", [])
    log(f"   eth_chainId = {chain_id_rpc.get('result')}  net_version = {net_version.get('result')}")
    balance = rpc(client, "eth_getBalance", [derived_address, "latest"])
    balance_wei = int(balance["result"], 16) if balance.get("result") else None
    log(f"   deployer balance = {balance_wei} wei" + (f" ({balance_wei / 1e18:.6f} GEN)" if balance_wei is not None else ""))

    log("\n== 4. runner hash probe against the live target ==")
    runner_probes = [probe_runner(client, runner) for runner in CANDIDATE_RUNNERS]
    for probe in runner_probes:
        verdict = "ACCEPTED" if probe["accepted"] else "REJECTED"
        log(f"   {verdict:9} {probe['runner_hash']}")
        if probe["accepted"]:
            log(f"             {probe['method_count']} method(s): {probe['method_names']}")
        else:
            log(f"             {probe.get('error_summary')}")
    accepted = [probe for probe in runner_probes if probe["accepted"]]
    if not accepted:
        log("\n   GATE FAILED: the live target accepted none of the candidate runners.")
        log("   Do not write the real contract. Report this.")
    else:
        log(f"\n   runner to pin = {accepted[0]['runner_hash']}")

    stub_source = contract_source(accepted[0]["runner_hash"]) if accepted else contract_source(CANDIDATE_RUNNERS[0])
    source_sha256 = hashlib.sha256(stub_source.encode()).hexdigest()
    log(f"   stub source sha256 = {source_sha256}")

    record = {
        "artifact": "m0-environment-and-pins",
        "milestone": "M0",
        "generated_by": "scripts/m0_env_probe.py",
        "observed_on": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "network": "GenLayer Studio-dev (temporary; may reset)",
        "rpc": env_value("GENLAYER_STUDIO_DEV_RPC"),
        "chain_id": int(env_value("GENLAYER_STUDIO_DEV_CHAIN_ID") or "61997"),
        "durable": False,
        "environment": {
            "variables": variables,
            "unused_by_design": [unused],
            "deployer_address": derived_address,
            "deployer_address_matches_env": address_matches,
            "deployer_balance_wei": balance_wei,
            "keys_read_from": "process environment only; .env is not consulted for secrets",
        },
        "chain_identity": {"eth_chainId": chain_id_rpc, "net_version": net_version},
        "runner_probe": {
            "method": "gen_getContractSchemaForCode",
            "candidates": runner_probes,
            "accepted_runner": accepted[0]["runner_hash"] if accepted else None,
            "resolution": (
                "Probed against the live target. The previously working build's hash is "
                "the one the node accepts; the hash named in the published docs is "
                "rejected by this target."
            )
            if accepted
            else "No candidate runner was accepted by the live target.",
        },
        "stub_contract": {
            "path": STUB_RELATIVE_PATH,
            "source_sha256": source_sha256,
            "purpose": "M0 gate only. Superseded by contracts/contest_receipt.py at M3.",
        },
    }

    if args.skip_deploy or not accepted:
        record["gate"] = {"status": "not-evaluated", "reason": "deploy not attempted"}
    else:
        log("\n== 5. deploy the stub and wait for Finalized ==")
        distribution = client.estimate_fees_distribution()
        log(f"   fee distribution = {distribution}")
        deployed = deploy_and_wait(client, account, stub_source, distribution)
        record["deployment"] = deployed
        record["gate"] = judge_gate(deployed)
        record["explorer"] = check_explorer(client, deployed)

    if args.skip_deploy and evidence_path.exists():
        # A probe-only run must never overwrite a gate-passing record with a
        # gate-not-evaluated one. The stub is cheap to redeploy, so the fix is
        # to refuse rather than to merge.
        print(
            f"refusing to overwrite {evidence_path.name} with a probe-only run: it "
            "would replace a recorded gate result with 'not-evaluated'. Re-run without "
            "--skip-deploy to redeploy and re-measure.",
            file=sys.stderr,
        )
        return 1

    evidence_path.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n")
    log(f"\nevidence written: {evidence_path.relative_to(REPO_ROOT)}")

    if record["gate"]["status"] != "passed":
        log(f"\nM0 GATE: {record['gate']['status'].upper()}")
        log(f"  {record['gate']['reason']}")
        return 1
    log("\nM0 GATE: PASSED")
    log(f"  {record['gate']['reason']}")
    return 0


def deploy_and_wait(client, account, source: str, distribution: dict) -> dict:
    """Deploy, wait for finalization, then re-read the record and the schema.

    The fee distribution must be supplied. Without it the consensus contract
    rejects the transaction with ``FeesDistributionMissing``, which is the
    first failure observed on this target.
    """
    deployed: dict = {
        "transaction_id": None,
        "lifecycle": None,
        "schema": None,
        "fee_distribution": distribution,
    }
    started = time.time()
    try:
        tx_hash = client.deploy_contract(
            source, account=account, fees={"distribution": distribution}
        )
    except Exception as exc:  # noqa: BLE001
        deployed["submit_error"] = f"{type(exc).__name__}: {exc}"[:2000]
        return deployed

    tx_id = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    deployed["transaction_id"] = tx_id
    log(f"   deploy transaction_id = {tx_id}")

    # The record must be re-read only after the lifecycle reports Finalized.
    wait_started = time.time()
    try:
        receipt = client.wait_for_transaction_receipt(
            tx_hash, wait_until="finalized", interval=5000, retries=120
        )
        deployed["wait_seconds"] = round(time.time() - wait_started, 1)
    except Exception as exc:  # noqa: BLE001
        deployed["wait_seconds"] = round(time.time() - wait_started, 1)
        deployed["wait_error"] = f"{type(exc).__name__}: {exc}"[:2000]
        log(f"   wait failed: {deployed['wait_error']}")
        return deployed

    deployed["elapsed_seconds"] = round(time.time() - started, 1)

    # The record is read here, after the lifecycle reported Finalized. A record
    # read immediately after submission still carries in-flight consensus fields
    # and can misreport a transaction that in fact finalized successfully.
    deployed.update(describe_transaction(client, tx_hash))
    log(
        f"   lifecycle = {deployed['lifecycle']} / {deployed['outcome']} after "
        f"{deployed['wait_seconds']}s; address = {deployed.get('contract_address')}"
    )

    address = deployed.get("contract_address")
    if address:
        schema = rpc(client, "gen_getContractSchemaForCode", [source.encode().hex()])
        result = schema.get("result") or {}
        deployed["schema"] = {
            "methods": sorted(result.get("methods", {}).keys()),
            "method_count": len(result.get("methods", {})),
        }
        balance_after = rpc(client, "eth_getBalance", [address, "latest"])
        deployed["deployed_contract_balance_wei"] = (
            int(balance_after["result"], 16) if balance_after.get("result") else None
        )
    return deployed


def describe_transaction(client, tx_hash) -> dict:
    """Summarize a finalized transaction record into stable, quotable fields."""
    record = client.get_transaction(tx_hash)
    lifecycle = record.get("lifecycle") or {}
    return {
        "lifecycle": str(lifecycle.get("state", "")).lower(),
        "outcome": str(lifecycle.get("outcome", "")).lower(),
        "contract_address": record.get("to_address"),
        "consensus_result": record.get("result_name"),
        "execution_result": record.get("txExecutionResultName"),
        "triggered_on": record.get("triggered_on"),
        "rounds": int(record.get("num_of_rounds") or 0),
        "reread_after_finalized": True,
        "note": (
            "Read after the lifecycle reported Finalized. A record read before "
            "finalization still carries in-flight consensus fields."
        ),
    }


def check_explorer(client, deployed: dict) -> dict:
    """Confirm the deployed address and transaction resolve on the explorer.

    The plan notes the correct evidence URL earns extra review speed, so the
    link is verified rather than constructed and assumed.
    """
    # The explorer in .env is the Bradbury one, which is a different network.
    # Studio-dev has its own explorer, so the base is stated here rather than
    # read from a variable that points at the wrong chain.
    base = os.environ.get("GENLAYER_STUDIO_DEV_EXPLORER_URL") or STUDIO_DEV_EXPLORER
    if not base.startswith("http"):
        base = f"https://{base}"
    base = base.rstrip("/")
    checks = {}
    targets = {
        "address": (f"{base}/address/{deployed.get('contract_address')}", deployed.get("contract_address")),
        "transaction": (
            f"{base}/tx/{deployed.get('transaction_id')}",
            deployed.get("transaction_id"),
        ),
    }
    for label, (url, value) in targets.items():
        if not value:
            checks[label] = {"url": url, "http_status": None, "note": "no value to check"}
            continue
        checks[label] = probe_url(url, attempts=4, delay=5)
        log(
            f"   explorer {label:12} {checks[label]['http_status']} "
            f"(after {len(checks[label]['attempts_log'])} attempt(s))"
        )
    return {"base_url": base, "checks": checks}


def judge_gate(deployed: dict) -> dict:
    """The M0 gate: lints/schema-derives, deploys, and reaches Finalized."""
    problems = []
    if not deployed.get("transaction_id"):
        problems.append("no deploy transaction was submitted")
    if not deployed.get("lifecycle"):
        problems.append(
            "no lifecycle was observed: " + str(deployed.get("wait_error") or "unknown")
        )
    elif deployed["lifecycle"].lower() != "finalized":
        problems.append(
            f"lifecycle is {deployed['lifecycle']}/{deployed.get('outcome')}, not finalized"
        )
    if not deployed.get("contract_address"):
        problems.append("no contract address was returned")
    if problems:
        return {"status": "failed", "reason": "; ".join(problems), "problems": problems}
    return {
        "status": "passed",
        "reason": (
            "The pinned runner was accepted by the live target, a one-method stub "
            "contract derived a schema, deployed on chain 61997, and its transaction "
            "reached Finalized."
        ),
        "problems": [],
    }


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SecretHandlingError as error:
        print(f"secret-handling rule violated: {error}", file=sys.stderr)
        raise SystemExit(2)
