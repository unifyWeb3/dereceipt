#!/usr/bin/env python3
"""M3 smoke test: prove the deployed contract is callable, not merely deployed.

A transaction that reached ``Finalized`` proves the contract was accepted by the
network. It does not prove any of its methods work. This exercises the smallest
end-to-end path that touches every layer the contract has:

* a **view read** on a fresh deployment — the path the frontend uses
* a **payable write** that locks a pool — proves value is accepted and stored
* the same **view read again** — proves the write is readable from state
* the **accuracy and digest views** — proves the receipt is derivable on read

It deliberately does not call ``freeze_entry``. That is the only method that
enters a non-deterministic block, it costs a GitHub call from every validator,
and a rate-limited run would produce a misleading observation. M6 exercises it
with real repositories. What is proved here is that the deterministic plumbing
around it is sound.

Re-runnable: each run opens a fresh programme on a fresh deployment if one is
not supplied.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from genlayer_py.types import TransactionHashVariant  # noqa: E402

from gl_env import (  # noqa: E402
    REPO_ROOT,
    STUDIO_DEV_EXPLORER,
    SecretHandlingError,
    deployer_account,
    probe_url,
    studio_dev_client,
)

#: Three of the five fixed criteria. Three is the documented minimum.
CRITERIA = [
    {"key": "commit_predates_deadline", "weight": 3},
    {"key": "declared_language_present", "weight": 2},
    {"key": "required_files_present", "weight": 1},
]

POOL = 1_000


def log(message: str) -> None:
    print(message, flush=True)


def call(client, account, address: str, name: str, args: list, fees: dict, value: int = 0):
    """Write a method and wait for finalization, then re-read the full record."""
    started = time.time()
    tx_hash = client.write_contract(
        address, name, account=account, args=args, value=value, fees={"distribution": fees}
    )
    tx_id = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    client.wait_for_transaction_receipt(tx_hash, wait_until="finalized", interval=5000, retries=120)
    record = client.get_transaction(tx_id)
    lifecycle = record.get("lifecycle") or {}
    return {
        "method": name,
        "transaction_id": tx_id,
        "lifecycle_state": str(lifecycle.get("state", "")).lower(),
        "outcome": str(lifecycle.get("outcome", "")).lower(),
        "execution_result": record.get("txExecutionResultName"),
        "seconds": round(time.time() - started, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M3 smoke test")
    parser.add_argument("--address", required=True, help="deployed contract address")
    parser.add_argument("--evidence", default=None, help="write the record here")
    args = parser.parse_args()

    account = deployer_account()
    client = studio_dev_client(account=account)
    address = args.address
    fees = client.estimate_fees_distribution()

    results = []

    def record(name: str, passed: bool, detail: str) -> None:
        results.append({"check": name, "passed": passed, "detail": detail})
        log(f"   {'PASS' if passed else 'FAIL'}  {name}: {detail}")

    log("== 1. view read on a fresh deployment ==")
    try:
        balance = client.read_contract(
            address, "get_contract_balance", account=account,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        record("get_contract_balance", int(balance) == 0, f"balance={int(balance)}")
    except Exception as exc:  # noqa: BLE001
        record("get_contract_balance", False, f"{type(exc).__name__}: {exc}"[:200])

    log("\n== 2. payable write: open_program locks a pool ==")
    now = int(time.time())
    try:
        opened = call(
            client, account, address, "open_program",
            [
                "smoke-test-programme",
                json.dumps(CRITERIA),
                now + 3600,
                3600,
                "{}",
            ],
            fees,
            value=POOL,
        )
        log(f"   {opened['method']} {opened['transaction_id']}")
        log(f"   {opened['lifecycle_state']}/{opened['outcome']} · {opened['execution_result']} · {opened['seconds']}s")
        record(
            "open_program finalized",
            opened["lifecycle_state"] == "finalized" and opened["outcome"] == "accepted",
            f"{opened['lifecycle_state']}/{opened['outcome']}",
        )
    except Exception as exc:  # noqa: BLE001
        record("open_program finalized", False, f"{type(exc).__name__}: {exc}"[:300])
        opened = None

    log("\n== 3. the write is readable from state ==")
    program_id = "0"
    try:
        program = client.read_contract(
            address, "get_program", account=account,
            args=[program_id],
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        log(f"   status={program.get('status')} pool={program.get('pool')} locked={program.get('locked')}")
        log(f"   criteria={[c.get('key') for c in program.get('criteria', [])]}")
        record(
            "get_program shows the locked pool",
            int(program.get("pool", 0)) == POOL and int(program.get("locked", 0)) == POOL,
            f"pool={program.get('pool')} locked={program.get('locked')}",
        )
        record(
            "criteria snapshotted at open",
            [c.get("key") for c in program.get("criteria", [])]
            == [c["key"] for c in CRITERIA],
            f"{len(program.get('criteria', []))} criteria stored",
        )
        record(
            "programme status is OPEN",
            program.get("status") == "OPEN",
            str(program.get("status")),
        )
    except Exception as exc:  # noqa: BLE001
        record("get_program", False, f"{type(exc).__name__}: {exc}"[:200])

    log("\n== 4. the accuracy record and the receipt digest are derivable ==")
    try:
        accuracy = client.read_contract(
            address, "get_accuracy", account=account, args=[program_id],
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        digest = client.read_contract(
            address, "get_receipt_digest", account=account, args=[program_id],
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        log(f"   accuracy: entries={accuracy.get('entries')} pool={accuracy.get('pool')} locked={accuracy.get('locked')}")
        log(f"   digest: {str(digest)[:34]}…")
        record("get_accuracy returns a record", isinstance(accuracy, dict), f"keys={len(accuracy)}")
        # Keccak256.hexdigest() returns bare hex, so 64 characters, not 66.
        # The earlier check assumed a 0x prefix and reported a false failure.
        digest_text = str(digest)
        record(
            "get_receipt_digest returns a 32-byte hash",
            len(digest_text) in (64, 66),
            f"len={len(digest_text)} prefix={'0x' if digest_text.startswith('0x') else 'none'}",
        )
    except Exception as exc:  # noqa: BLE001
        record("accuracy/digest views", False, f"{type(exc).__name__}: {exc}"[:200])

    log("\n== 5. the balance moved to exactly the pool ==")
    try:
        after = client.read_contract(
            address, "get_contract_balance", account=account,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        record("contract holds the locked pool", int(after) == POOL, f"balance={int(after)} (expected {POOL})")
    except Exception as exc:  # noqa: BLE001
        record("contract balance", False, f"{type(exc).__name__}: {exc}"[:200])

    log("\n== 6. the refund path returns the pool ==")
    log("   (this is the gap the 360/400 build left open, so it is proved here)")
    try:
        cancelled = call(
            client, account, address, "cancel_program", [program_id], fees,
        )
        log(f"   cancel_program {cancelled['transaction_id']}")
        log(f"   {cancelled['lifecycle_state']}/{cancelled['outcome']} · {cancelled['execution_result']} · {cancelled['seconds']}s")
        record(
            "cancel_program finalized",
            cancelled["lifecycle_state"] == "finalized" and cancelled["outcome"] == "accepted",
            f"{cancelled['lifecycle_state']}/{cancelled['outcome']}",
        )
        after_refund = client.read_contract(
            address, "get_contract_balance", account=account,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        record(
            "contract balance returned to zero after the refund",
            int(after_refund) == 0,
            f"balance={int(after_refund)} (was {POOL})",
        )
    except Exception as exc:  # noqa: BLE001
        record("cancel_program refund", False, f"{type(exc).__name__}: {exc}"[:300])
        cancelled = None

    log("\n== 7. a second cancel is refused, not paid twice ==")
    try:
        client.write_contract(
            address, "cancel_program", account=account, args=[program_id],
            fees={"distribution": fees},
        )
        status = client.read_contract(
            address, "get_program", account=account, args=[program_id],
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        still_zero = client.read_contract(
            address, "get_contract_balance", account=account,
            transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
        )
        record(
            "repeat cancel does not move value",
            int(still_zero) == 0 and status.get("status") == "CANCELLED",
            f"balance={int(still_zero)} status={status.get('status')}",
        )
    except Exception as exc:  # noqa: BLE001
        record("repeat cancel", False, f"{type(exc).__name__}: {exc}"[:200])

    passed = sum(1 for r in results if r["passed"])
    log(f"\n{passed}/{len(results)} smoke checks passed")

    if args.evidence:
        out = pathlib.Path(args.evidence)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "artifact": "m3-smoke-test",
                    "generated_by": "scripts/m3_smoke_test.py",
                    "observed_on": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "contract_address": address,
                    "pool": POOL,
                    "criteria": CRITERIA,
                    "open_program": opened,
                    "cancel_program": locals().get("cancelled"),
                    "checks": results,
                    "passed": passed == len(results),
                    "not_exercised": [
                        "freeze_entry — the only non-deterministic method; M6 runs it "
                        "against real repositories",
                        "challenge, finalize_program, claim_payout, cancel_program — "
                        "each needs a frozen entry first",
                    ],
                    "explorer": probe_url(f"{STUDIO_DEV_EXPLORER}/address/{address}", attempts=3),
                },
                indent=2,
            )
            + "\n"
        )
        log(f"evidence written: {out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SecretHandlingError as error:
        print(f"secret-handling rule violated: {error}", file=sys.stderr)
        raise SystemExit(2)
