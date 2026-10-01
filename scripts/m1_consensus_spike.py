#!/usr/bin/env python3
"""M1 — consensus spike: does the jury converge on one subjective criterion?

Implements the M1 milestone of
``state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md`` §5.

M1 exists to produce **one number and one decision**: how often do validators
converge, and therefore is the comparison mode 2-bucket or 3-bucket. It writes
no product code. The contract it deploys,
``contracts/m1_panel_spike.py``, is a throwaway measurement instrument and is
not part of Contest Receipt.

Per repository it records:

* whether consensus held (the network's own lifecycle and outcome)
* how many rounds it took
* the per-validator vote split, so a near-miss is visible as a near-miss
* the bucket the network accepted

Secrets are read from the process environment only. Every HTTP call has a
timeout, and the record is written after every step, because Studio-dev stalls
and resets. Re-running the script redeploys and re-measures from scratch.
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
    SecretHandlingError,
    deployer_account,
    probe_url,
    studio_dev_client,
)

SPIKE_CONTRACT = "contracts/m1_panel_spike.py"

#: Three real public repositories, each pinned to an immutable commit. The
#: commit SHA is part of the README URL the contract fetches, so the read is
#: point-in-time: an entrant cannot change the README without changing the
#: commit, which would change the URL.
#:
#: Chosen for the spike only. These are **not** the M6 demo repositories, which
#: the plan reserves for an explicit human decision.
SPIKE_REPOSITORIES = (
    {
        "label": "genlayer-py",
        "repo_url": "genlayerlabs/genlayer-py",
        "commit_sha": "dd25ef7f43e99a14b8fe42a64e01374845ad4d2d",
        "expected_readme_bytes": 11035,
        "note": "a published SDK with a substantive README",
    },
    {
        "label": "genlayer-js",
        "repo_url": "genlayerlabs/genlayer-js",
        "commit_sha": "1b7f50a3a3f2963ea857941b0fb386081dd5c326",
        "expected_readme_bytes": 14760,
        "note": "the JavaScript counterpart, a different document and a different length",
    },
    {
        "label": "genlayer-docs",
        "repo_url": "genlayerlabs/genlayer-docs",
        "commit_sha": "1cd8e2d11f74",
        "expected_readme_bytes": 4004,
        "note": "a documentation site, the shortest README of the three",
    },
)

#: Required runs for the milestone's own gate. The plan's rule: 3/3 converge
#: means proceed with 2-bucket; any undetermined means switch to 3-bucket and
#: re-test.
REQUIRED_RUNS = 3

CALL_TIMEOUT_NOTE = "Studio-dev stalls; every wait is bounded and polled"


def log(message: str) -> None:
    print(message, flush=True)


def read_full_record(client, tx_id: str) -> dict:
    """Read the full transaction record.

    The SDK's ``wait_for_transaction_receipt`` returns a simplified receipt that
    does not carry ``status_name`` or ``contract_address`` on this SDK version.
    The full record is the only place the lifecycle, the round count and the
    per-validator votes are visible, and it must be read *after* the lifecycle
    reports a decision.
    """
    record = client.get_transaction(tx_id)
    lifecycle = record.get("lifecycle") or {}
    return {
        "lifecycle_state": str(lifecycle.get("state", "")).lower(),
        "outcome": str(lifecycle.get("outcome", "")).lower(),
        "contract_address": record.get("to_address"),
        "consensus_result": record.get("result_name"),
        "execution_result": record.get("txExecutionResultName"),
        "rounds": int(record.get("num_of_rounds") or 0),
        "last_round": summarize_round(record.get("last_round")),
        "all_round_votes": all_round_votes(record),
        "return_data": record.get("data"),
        "per_validator": per_validator_buckets(record.get("consensus_data") or {}),
        "appealed": record.get("appealed"),
        "created_at": record.get("created_at"),
    }


def summarize_round(last_round) -> dict:
    if not isinstance(last_round, dict):
        return {}
    votes = last_round.get("validator_votes_name") or []
    tally = {}
    for vote in votes:
        tally[vote] = tally.get(vote, 0) + 1
    return {
        "round": last_round.get("round"),
        "leader_index": last_round.get("leader_index"),
        "votes_committed": last_round.get("votes_committed"),
        "votes_revealed": last_round.get("votes_revealed"),
        "rotations_left": last_round.get("rotations_left"),
        "validator_votes_name": votes,
        "vote_tally": tally,
    }


def all_round_votes(record) -> list:
    """Every round's vote tally, so a rotation is visible as extra rounds."""
    out = []
    history = record.get("consensus_history") or {}
    for result in history.get("consensus_results") or []:
        out.append(summarize_round(result.get("last_round")))
    return [entry for entry in out if entry]


def decode_return_value(record) -> object:
    """Best-effort decode of a write method's return value.

    Recorded raw as well as decoded. The authoritative bucket is read from
    contract storage via ``get_last_run``; this is a secondary cross-check.
    """
    from genlayer_py.abi import calldata

    raw = record.get("return_data")
    if not raw:
        return None
    if isinstance(raw, dict):
        return {"note": "record exposes transaction calldata, not a return value", "raw": raw}
    try:
        return calldata.decode(bytes.fromhex(str(raw).removeprefix("0x")))
    except Exception as exc:  # noqa: BLE001
        return {"decode_failed": f"{type(exc).__name__}: {exc}"[:300]}


def read_last_run(client, account, address: str) -> dict:
    """Read the accepted result back from contract storage.

    This is the authoritative bucket. The consensus receipt encodes it in the
    network's compact calldata format, which is not decoded by the SDK here, so
    the contract records the accepted result where a reviewer can read it
    without hand-decoding base64.
    """
    from genlayer_py.types import TransactionHashVariant

    try:
        value = client.read_contract(
            address,
            "get_last_run",
            account=account,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
    except Exception as exc:  # noqa: BLE001
        return {"read_error": f"{type(exc).__name__}: {exc}"[:400]}
    if isinstance(value, dict):
        return value
    return {"unexpected_shape": str(value)[:300]}


def per_validator_buckets(record) -> list:
    """Each validator's own accepted result, decoded from the consensus data.

    A heuristic, and labelled as one: the SDK does not decode the network's
    compact result encoding, so the bucket is recovered by scanning for the
    ``bucket`` key and the printable string that follows it. It is a diagnostic
    for the spike — it shows whether the validators that answered agreed on the
    same bucket — and the stored value remains the authority.
    """
    import base64


    found = []
    for index, validator in enumerate(record.get("validators") or []):
        entry = {
            "index": index,
            "execution_result": validator.get("execution_result"),
        }
        encoded = validator.get("result")
        if not encoded:
            entry["bucket"] = None
            entry["note"] = "no result (idle)"
            found.append(entry)
            continue
        try:
            raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4))
        except Exception as exc:  # noqa: BLE001
            entry["bucket"] = None
            entry["note"] = f"base64 decode failed: {exc}"
            found.append(entry)
            continue
        # The encoding is a length byte followed by the value, and that length
        # byte is itself printable, so matching "bucket" plus a capitalised run
        # picks up the length byte as part of the bucket. Match the known bucket
        # names instead, longest first so CONSISTENT cannot match inside
        # INCONSISTENT.
        entry["bucket"] = None
        for name in ("INCONSISTENT", "INCONCLUSIVE", "CONSISTENT"):
            if name.encode() in raw:
                entry["bucket"] = name
                break
        entry["method"] = "heuristic scan of the consensus receipt"
        found.append(entry)
    return found


def deploy_spike(client, account, source: str) -> dict:
    """Deploy the spike. Inherits the M0 fee-distribution requirement."""
    result = {"transaction_id": None, "contract_address": None, "lifecycle_state": None}
    distribution = client.estimate_fees_distribution()
    result["fee_distribution"] = distribution
    started = time.time()
    tx_hash = client.deploy_contract(source, account=account, fees={"distribution": distribution})
    tx_id = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    result["transaction_id"] = tx_id
    log(f"   spike deploy transaction_id = {tx_id}")
    client.wait_for_transaction_receipt(tx_hash, wait_until="finalized", interval=5000, retries=120)
    record = read_full_record(client, tx_id)
    result.update(
        {
            "lifecycle_state": record["lifecycle_state"],
            "outcome": record["outcome"],
            "contract_address": record["contract_address"],
            "consensus_result": record["consensus_result"],
            "execution_result": record["execution_result"],
            "wait_seconds": round(time.time() - started, 1),
        }
    )
    log(f"   spike deployed at {record['contract_address']} ({record['lifecycle_state']})")
    return result


def run_one(client, account, address: str, repo: dict, fees: dict) -> dict:
    """Run the criterion once and record whether the jury converged."""
    log(f"\n-- {repo['label']}: {repo['repo_url']}@{repo['commit_sha'][:12]}")
    observation = {
        "repository": repo,
        "transaction_id": None,
        "converged": None,
        "lifecycle_state": None,
        "outcome": None,
        "rounds": None,
        "bucket": None,
        "seconds": None,
    }
    started = time.time()
    try:
        tx_hash = client.write_contract(
            address,
            "run_panel",
            account=account,
            args=[repo["repo_url"], repo["commit_sha"]],
            fees={"distribution": fees},
        )
    except Exception as exc:  # noqa: BLE001
        observation["submit_error"] = f"{type(exc).__name__}: {exc}"[:600]
        log(f"   submit failed: {observation['submit_error']}")
        return observation

    tx_id = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    observation["transaction_id"] = tx_id
    log(f"   run_panel transaction_id = {tx_id}")

    try:
        client.wait_for_transaction_receipt(tx_hash, wait_until="finalized", interval=5000, retries=120)
    except Exception as exc:  # noqa: BLE001
        observation["wait_error"] = f"{type(exc).__name__}: {exc}"[:600]
        observation["seconds"] = round(time.time() - started, 1)
        log(f"   wait did not reach a final state: {observation['wait_error']}")
        return observation

    record = read_full_record(client, tx_id)
    observation["seconds"] = round(time.time() - started, 1)
    observation["record"] = record
    observation["decoded_return"] = decode_return_value(record)
    observation["lifecycle_state"] = record["lifecycle_state"]
    observation["outcome"] = record["outcome"]
    observation["rounds"] = record["rounds"]
    observation["execution_result"] = record["execution_result"]
    observation["consensus_result"] = record["consensus_result"]
    observation["final_round_votes"] = record["last_round"].get("vote_tally")
    observation["per_validator"] = record["per_validator"]

    # The bucket the network accepted, read from contract storage.
    stored = read_last_run(client, account, address)
    observation["stored_result"] = stored
    if "bucket" in stored:
        observation["bucket"] = stored.get("bucket")
        observation["confidence"] = stored.get("confidence")
        observation["reason"] = stored.get("reason")
        observation["readme_bytes_seen"] = stored.get("readme_bytes")
        observation["bucket_source"] = "contract storage, read via get_last_run"

    # Convergence is the network's own verdict, not an inference from the
    # bucket. A transaction the network could not settle has not converged,
    # whatever any single operator thought.
    observation["converged"] = (
        record["lifecycle_state"] == "finalized" and record["outcome"] == "accepted"
    )
    log(
        f"   converged={observation['converged']} "
        f"lifecycle={record['lifecycle_state']}/{record['outcome']} "
        f"rounds={record['rounds']} bucket={observation['bucket']} "
        f"votes={observation['final_round_votes']} in {observation['seconds']}s"
    )
    per_validator = observation.get("per_validator") or []
    for entry in per_validator:
        log(
            f"      validator[{entry['index']}] exec={entry.get('execution_result')} "
            f"bucket={entry.get('bucket')}"
        )
    return observation


def decide_mode(observations: list) -> dict:
    """Turn the runs into the decision the milestone is for.

    The plan's rule, applied literally: 3/3 converged means 2-bucket; any
    undetermined means 3-bucket and re-test. The reasoning is stated so a
    reviewer can disagree with the interpretation rather than reverse-engineer
    it from the number.
    """
    total = len(observations)
    attempted = [o for o in observations if o.get("transaction_id")]
    converged = [o for o in attempted if o.get("converged")]
    undetermined = [
        o for o in attempted if o.get("lifecycle_state") not in ("finalized",) or not o.get("converged")
    ]
    buckets = {}
    for observation in attempted:
        bucket = observation.get("bucket") or "UNDECODED"
        buckets[bucket] = buckets.get(bucket, 0) + 1

    convergence_number = f"{len(converged)}/{total}" if total else "0/0"

    if total < REQUIRED_RUNS:
        mode = "UNDECIDED"
        basis = (
            f"Only {total} run(s) completed; the gate needs {REQUIRED_RUNS}. "
            "No comparison mode is decided."
        )
    elif not undetermined:
        mode = "2-BUCKET"
        basis = (
            f"{convergence_number} converged with no undetermined transaction, so a "
            "two-bucket comparison with zero tolerance on the bucket is the mode the "
            "plan calls for."
        )
    else:
        mode = "3-BUCKET"
        basis = (
            f"{len(undetermined)} of {total} runs did not converge "
            f"({', '.join(o['repository']['label'] for o in undetermined)}). Under the "
            "plan's rule that is a switch to three buckets and a re-test. Note that a "
            "non-converged run is a finding about the jury, not a defect in the product: "
            "the plan's whole wedge is that a criterion the jury cannot agree on stays "
            "visible on the record."
        )

    return {
        "convergence": convergence_number,
        "converged": len(converged),
        "total": total,
        "undetermined": [
            {
                "label": o["repository"]["label"],
                "transaction_id": o.get("transaction_id"),
                "lifecycle_state": o.get("lifecycle_state"),
                "outcome": o.get("outcome"),
            }
            for o in undetermined
        ],
        "accepted_buckets": buckets,
        "decided_comparison_mode": mode,
        "basis": basis,
        "rule_applied": (
            "IMPLEMENTATION-PLAN.md §5 M1: 3/3 converge means proceed with the "
            "2-bucket strict comparison; any UNDETERMINED means switch to 3-bucket "
            "and re-test."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M1 consensus spike")
    parser.add_argument("--evidence-dir", default=str(REPO_ROOT / "docs" / "evidence"))
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="measure against an already deployed spike; needs --address",
    )
    parser.add_argument("--address", default=None, help="existing spike address")
    parser.add_argument(
        "--label",
        default="",
        help="suffix for the evidence filename, so a repeat pass is kept alongside the first",
    )
    args = parser.parse_args()

    evidence_dir = pathlib.Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    suffix = f"-{args.label}" if args.label else ""
    evidence_path = evidence_dir / f"m1-{today}{suffix}.json"

    source = (REPO_ROOT / SPIKE_CONTRACT).read_text()
    record = {
        "artifact": "m1-consensus-spike",
        "milestone": "M1",
        "generated_by": "scripts/m1_consensus_spike.py",
        "observed_on": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "network": "GenLayer Studio-dev (temporary; may reset)",
        "durable": False,
        "purpose": (
            "Throwaway measurement. Measures whether validators converge on one "
            "subjective criterion so the 2-bucket vs 3-bucket comparison mode can "
            "be decided. Not part of Contest Receipt."
        ),
        "contract": {
            "path": SPIKE_CONTRACT,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        },
        "criterion": (
            "Does the repository's own README at the pinned commit describe a "
            "working product consistent with that commit?"
        ),
        "buckets": ["CONSISTENT", "INCONSISTENT", "INCONCLUSIVE"],
        "comparison": "bucket compared with zero tolerance; free-form reasoning stored, never compared",
        "pass_label": args.label or "primary",
    }

    account = deployer_account()
    client = studio_dev_client(account=account)

    if args.address:
        record["deployment"] = {
            "contract_address": args.address,
            "note": "reused an existing deployment via --address; not deployed by this run",
        }
        address = args.address
    else:
        log("== deploy the spike ==")
        record["deployment"] = deploy_spike(client, account, source)
        address = record["deployment"].get("contract_address")

    if not address:
        record["decision"] = decide_mode([])
        evidence_path.write_text(json.dumps(record, indent=2) + "\n")
        log("\nM1 GATE: FAILED — no spike contract address, so nothing could be measured.")
        log(f"  see {evidence_path}")
        return 1

    log("\n== run the criterion on real repositories ==")
    fees = client.estimate_fees_distribution()
    record["fee_distribution"] = fees
    observations = []
    for repo in SPIKE_REPOSITORIES:
        observations.append(run_one(client, account, address, repo, fees))
        # Write after every step: a stall mid-run must not destroy the runs
        # already observed.
        record["runs"] = observations
        record["decision"] = decide_mode(observations)
        evidence_path.write_text(json.dumps(record, indent=2) + "\n")

    record["runs"] = observations
    record["decision"] = decide_mode(observations)
    evidence_path.write_text(json.dumps(record, indent=2) + "\n")

    decision = record["decision"]
    explorer = probe_url(
        f"https://explorer-studio-dev.genlayer.com/address/{address}", attempts=3
    )
    record["explorer"] = explorer
    evidence_path.write_text(json.dumps(record, indent=2) + "\n")

    log("\n== M1 decision ==")
    log(f"   convergence          = {decision['convergence']}")
    log(f"   accepted buckets     = {decision['accepted_buckets']}")
    log(f"   comparison mode      = {decision['decided_comparison_mode']}")
    log(f"   explorer address     = {explorer['http_status']}")
    log(f"   basis: {decision['basis']}")
    log(f"\nevidence written: {evidence_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SecretHandlingError as error:
        print(f"secret-handling rule violated: {error}", file=sys.stderr)
        raise SystemExit(2)
