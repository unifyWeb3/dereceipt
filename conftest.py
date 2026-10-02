"""Repository-root conftest: repair ``gltest``'s import before plugins load.

``gltest`` registers a ``pytest11`` entry point, so pytest imports it during
plugin discovery — before ``tests/direct/conftest.py`` runs — and its import
fails against the pinned ``genlayer-py``:

    ImportError: cannot import name 'TransactionStatus' from 'genlayer_py.types'

A root-level conftest is read during startup argument handling, which is early
enough. The shim itself, and the reasoning, live in
``tests/direct/gltest_compat_plugin.py``.

This file exists only to make the load order deterministic. If it stops being
sufficient, the explicit alternative is on the test command:

    .venv/bin/python -m pytest tests/direct -q -p tests.direct.gltest_compat
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "direct"))

import gltest_compat_plugin  # noqa: E402,F401