#!/usr/bin/env bash
# Run the direct test suite.
#
# Every requirement this script encodes was found the hard way, so they are
# explicit here rather than left to the reader to rediscover:
#
#   GENVM_VERSION=v0.6.0-rc5   the contract header targets the older v0.3 SDK
#                               layout the live Studio-dev target runs
#                               (measured: GenVM v0.3.0-rc7), while direct tests
#                               run against v0.6.0-rc5. Deliberate mismatch,
#                               copied from the 360/400 reference build.
#                               THE RULE: when a direct test disagrees with the
#                               live target, the live target is right.
#
#   -p gltest_compat_plugin     gltest's pytest entry point is imported before any
#                               conftest and fails against genlayer-py 0.19.0rc2,
#                               which removed TransactionStatus. Loading the shim
#                               by name puts it ahead of the entry point.
#                               Needs tests/direct on PYTHONPATH.
#
#   seed_gltest_cache.sh        gltest downloads its SDK from GitHub releases,
#                               which 404s here; the artifacts are symlinked
#                               from the linter's cache instead.
#
# No Docker, no network, no live node, no model.

set -euo pipefail

cd "$(dirname "$0")"

export GENVM_VERSION="${GENVM_VERSION:-v0.6.0-rc5}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/tests/direct${PYTHONPATH:+:$PYTHONPATH}"

if ! .venv/bin/python -c "import sys; sys.path.insert(0,'tests/direct'); import helpers; helpers._assert_seeded()" 2>/dev/null; then
  echo "gltest SDK cache is not seeded; running scripts/seed_gltest_cache.sh" >&2
  bash scripts/seed_gltest_cache.sh >&2
fi

exec .venv/bin/python -m pytest tests/direct \
  -p gltest_compat_plugin \
  -p no:cacheprovider \
  "$@"