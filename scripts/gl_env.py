"""Secret-safe environment loading and Studio-dev client construction.

Rules enforced here, because they are non-negotiable for this build:

* A private key is read from the process environment only. It is never written
  to a file, a log, a doc, a commit, or stdout.
* :func:`require_secret` reports the variable *name* and whether it is
  populated. It never returns the value into any string that could be printed
  by accident; callers get the value from :func:`secret_value` and must treat it
  as sensitive.
* :func:`assert_outside_checkout` refuses any path inside the repository, so a
  run cannot persist a key, keystore, or account file into the checkout.
* ``APP_DATABASE_URL`` is deliberately unused. The contract is the record; a
  second source of truth reads as an off-chain dependency.
"""

from __future__ import annotations

import os
import pathlib
import re
from typing import Dict, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from genlayer_py.chains.studionet import (
    CONSENSUS_DATA_CONTRACT,
    EXPLORER_URL,
)
from genlayer_py.client import GenLayerClient
from genlayer_py.types import GenLayerChain, NativeCurrency

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Variables that must never be written inside the checkout.
FORBIDDEN_INSIDE_CHECKOUT = ("private_key", "keystore", "account", "secret")


class SecretHandlingError(RuntimeError):
    """Raised when a secret-handling rule would be violated."""


def load_env_file(path: Optional[pathlib.Path] = None) -> Dict[str, str]:
    """Parse a ``.env`` file into a dict.

    Values are returned to the caller, so the result must not be printed. Use
    :func:`env_report` to describe which variables are present.
    """
    target = path or (REPO_ROOT / ".env")
    parsed: Dict[str, str] = {}
    if not target.exists():
        return parsed
    for raw_line in target.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        parsed[name.strip()] = value.strip()
    return parsed


def env_value(name: str, env: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Return a configuration value, preferring the real environment.

    ``.env`` is a fallback for non-secret configuration only. Secrets must come
    from the process environment, so :func:`secret_value` refuses ``.env``.
    """
    from_process = os.environ.get(name)
    if from_process:
        return from_process
    source = load_env_file() if env is None else env
    return source.get(name) or None


def secret_value(name: str) -> str:
    """Read a secret from the process environment.

    ``.env`` is deliberately not consulted. A key on disk in the checkout is the
    failure mode this build is required to avoid, so the value must be injected
    into the environment by the operator.
    """
    value = os.environ.get(name)
    if not value:
        raise SecretHandlingError(
            f"{name} is not set in the process environment. Secrets are read "
            "from the environment only; they are never loaded from .env."
        )
    return value


def env_report(names) -> Dict[str, Dict[str, object]]:
    """Describe variables by name and populated-or-not. Never by value."""
    report: Dict[str, Dict[str, object]] = {}
    for name in names:
        in_process = bool(os.environ.get(name))
        in_file = name in load_env_file()
        report[name] = {
            "in_process_env": in_process,
            "in_dotenv_file": in_file,
            "populated": in_process or in_file,
        }
    return report


def assert_outside_checkout(candidate: os.PathLike | str) -> pathlib.Path:
    """Refuse a path that lives inside the repository checkout.

    A run must be able to keep a throwaway key outside the checkout so a
    resumed run is possible after a crash. Writing one inside the checkout is
    refused rather than warned about.
    """
    path = pathlib.Path(candidate).expanduser().resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError:
        return path
    raise SecretHandlingError(
        f"refusing to persist credential material inside the checkout: {path}. "
        f"Choose a path outside {REPO_ROOT}."
    )


def studio_dev_chain(rpc_url: str, chain_id: int) -> GenLayerChain:
    """Build a Studio-dev chain config for ``genlayer-py``.

    ``ConsensusMain`` is fetched from the node by
    ``initialize_consensus_smart_contract``. ``ConsensusData`` is not exposed by
    name on Studio-dev, so the SDK's baked Studio address is used; the
    transaction read path is exercised against it in the M0 gate and the result
    is recorded in ``docs/evidence/``.
    """
    return GenLayerChain(
        id=chain_id,
        name="GenLayer Studio Dev",
        rpc_urls={"default": {"http": [rpc_url]}},
        native_currency=NativeCurrency(name="GEN Token", symbol="GEN", decimals=18),
        block_explorers={
            "default": {"name": "GenLayer Studio Dev Explorer", "url": EXPLORER_URL}
        },
        testnet=True,
        consensus_main_contract=None,
        consensus_data_contract=CONSENSUS_DATA_CONTRACT,
        fee_manager_contract=None,
        rounds_storage_contract=None,
        appeals_contract=None,
        staking_contract=None,
        default_number_of_initial_validators=5,
        default_consensus_max_rotations=3,
    )


def studio_dev_client(account: Optional[LocalAccount] = None) -> GenLayerClient:
    """Construct a ``genlayer-py`` client pointed at Studio-dev."""
    rpc_url = env_value("GENLAYER_STUDIO_DEV_RPC")
    if not rpc_url:
        raise SecretHandlingError("GENLAYER_STUDIO_DEV_RPC is not configured")
    chain_id = int(env_value("GENLAYER_STUDIO_DEV_CHAIN_ID") or "61997")
    return GenLayerClient(studio_dev_chain(rpc_url, chain_id), account=account)


def deployer_account() -> LocalAccount:
    """Load the funded deployer identity from the process environment."""
    key = secret_value("GENLAYER_PRIVATE_KEY")
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", key):
        raise SecretHandlingError(
            "GENLAYER_PRIVATE_KEY is not a 32-byte 0x-prefixed hex key. "
            "The value was not printed."
        )
    return Account.from_key(key)
