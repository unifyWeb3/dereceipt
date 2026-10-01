# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

"""M0 environment probe contract.

This file is **not** the product. It is the one-method stub required by the
M0 gate in ``state/reviews/2026-10-01-hackathon-discovery/IMPLEMENTATION-PLAN.md``
§5: prove that the pinned runner is accepted by the live Studio-dev target, that
the contract schema can be derived, that a transaction deploys, and that the
transaction reaches ``Finalized`` on chain 61997.

It is superseded by ``contracts/contest_receipt.py`` at M3 and is kept only so
that the M0 observations remain reproducible. There is no non-determinism here,
so there is no consensus behaviour to verify at this stage.
"""

import genlayer as gl


class M0StubProbe(gl.contract.Contract):
    """A single read-only method, so the gate tests transport only."""

    def __init__(self):
        pass

    @gl.public.view
    def probe(self) -> int:
        return 1
