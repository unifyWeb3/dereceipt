"""Repairs ``gltest``'s import before the ``gltest`` pytest entry point loads.

``gltest`` is registered as a ``pytest11`` entry point, so pytest imports it
during plugin discovery — before any ``conftest.py`` runs. Its import fails
against the pinned ``genlayer-py``:

    ImportError: cannot import name 'TransactionStatus' from 'genlayer_py.types'

``genlayer-test 0.29.2`` wants ``genlayer-py>=0.13,<0.17``, whose
``genlayer_py.types`` exports ``TransactionStatus``. M0 pinned
``genlayer-py 0.19.0rc2``, which removed that name in favour of
``TransactionLifecycle`` — the version that names ``FeesDistributionMissing``
instead of reporting a bare "Transaction reverted". Downgrading would undo an M0
finding, so the name is restored here.

Load order is handled by a ``conftest.py`` at the **repository root**, which
pytest reads during startup argument handling, ahead of entry-point plugins:

    .venv/bin/python -m pytest tests/direct -q

If that ever stops being true, the explicit form is:

    .venv/bin/python -m pytest tests/direct -q -p tests.direct.gltest_compat

This is a test-harness shim. It defines no contract behaviour, is not on the
contract's import path, and changes nothing the deployed contract can observe.
"""

from __future__ import annotations

import enum


def install() -> None:
    """Reintroduce ``TransactionStatus`` if the pinned SDK removed it."""
    try:
        import genlayer_py.types as genlayer_types
    except ImportError:  # pragma: no cover - SDK not installed yet
        return

    if hasattr(genlayer_types, "TransactionStatus"):
        return

    class TransactionStatus(str, enum.Enum):
        """The 0.13-0.16 lifecycle enum, restored for ``gltest``'s re-export.

        The direct runner never uses it — it needs only
        ``MockedWebResponseData`` and ``MockedLLMResponse``, which are plain
        TypedDicts in the same module. Only the re-export is missing.
        """

        UNINITIALIZED = "UNINITIALIZED"
        PENDING = "PENDING"
        PROPOSING = "PROPOSING"
        COMMITTING = "COMMITTING"
        REVEALING = "REVEALING"
        ACCEPTED = "ACCEPTED"
        UNDETERMINED = "UNDETERMINED"
        FINALIZED = "FINALIZED"
        CANCELED = "CANCELED"
        APPEAL_REVEALING = "APPEAL_REVEALING"
        APPEAL_COMMITTING = "APPEAL_COMMITTING"
        READY_TO_FINALIZE = "READY_TO_FINALIZE"
        VALIDATORS_TIMEOUT = "VALIDATORS_TIMEOUT"
        LEADER_TIMEOUT = "LEADER_TIMEOUT"

    genlayer_types.TransactionStatus = TransactionStatus

    # The 0.13-0.16 SDK also exported the name/number maps `gltest` imports.
    if not hasattr(genlayer_types, "TRANSACTION_STATUS_NAME_TO_NUMBER"):
        number_to_name = {str(member.value): member.name for member in TransactionStatus}
        genlayer_types.TRANSACTION_STATUS_NAME_TO_NUMBER = {
            member: index for index, member in enumerate(number_to_name)
        }
        genlayer_types.TRANSACTION_STATUS_NUMBER_TO_NAME = number_to_name


install()