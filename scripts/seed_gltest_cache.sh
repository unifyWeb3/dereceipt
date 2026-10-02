#!/usr/bin/env bash
# Seed the gltest direct-runner SDK cache from the genvm-linter cache.
#
# Why this exists
# ---------------
# `gltest.direct.sdk_loader` downloads its GenVM artifacts from GitHub releases.
# That download 404s in this environment, so the direct test runner cannot load
# the contract SDK at all:
#
#   urllib.error.HTTPError: HTTP Error 404: Not Found
#
# which surfaced inside test setup and read as a test bug rather than a missing
# cache. The same artifacts are already on disk, because `genvm-lint check`
# downloads the identical `genvm-universal-genlayerlabs-genvm-manager-*.tar.xz`
# bundles. This script links them into the layout the gltest loader expects:
#
#   ~/.cache/gltest-direct/genvm-universal-<version>.tar.xz
#   ~/.cache/gltest-direct/extracted/<version>/py-genlayer/<hash>
#   ~/.cache/gltest-direct/extracted/<version>/py-lib-genlayer-std/<hash>
#
# Nothing is downloaded and nothing is copied; every path is a symlink, so this
# costs a few kilobytes and cannot drift out of sync with the linter's cache.
#
# Usage: bash scripts/seed_gltest_cache.sh [version]   (default v0.6.0-rc5)

set -euo pipefail

VERSION="${1:-v0.6.0-rc5}"
LINTER_CACHE="${GENVM_LINTER_CACHE:-$HOME/.cache/genvm-linter}"
GLTEST_CACHE="${GLTEST_DIRECT_CACHE:-$HOME/.cache/gltest-direct}"

LINTER_DIR="$LINTER_CACHE/extracted/genlayerlabs-genvm-manager-$VERSION"

if [[ ! -d "$LINTER_DIR" ]]; then
  echo "error: $LINTER_DIR not found." >&2
  echo "Available in the linter cache:" >&2
  ls -1 "$LINTER_CACHE/extracted" 2>/dev/null | grep '^genlayerlabs-genvm-manager' >&2 || true
  exit 1
fi

mkdir -p "$GLTEST_CACHE/extracted/$VERSION/py-genlayer" \
         "$GLTEST_CACHE/extracted/$VERSION/py-lib-genlayer-std"

link_tarball() {
  local src="$1"
  local dest="$GLTEST_CACHE/genvm-universal-$VERSION.tar.xz"
  [[ -e "$dest" ]] && { echo "  tarball already linked"; return; }
  [[ -f "$src" ]] || { echo "  warning: no tarball at $src (extraction will need it)"; return; }
  ln -s "$src" "$dest"
  echo "  linked tarball"
}

link_kind() {
  local kind="$1"
  local srcdir="$LINTER_DIR/$kind"
  local dstdir="$GLTEST_CACHE/extracted/$VERSION/$kind"
  [[ -d "$srcdir" ]] || { echo "  warning: no $kind in linter cache"; return; }
  local count=0
  for hash in "$srcdir"/*; do
    [[ -e "$hash" ]] || continue
    ln -sfn "$hash" "$dstdir/$(basename "$hash")"
    count=$((count + 1))
  done
  echo "  linked $count $kind artifact(s)"
}

echo "seeding gltest-direct cache from the genvm-linter cache"
echo "  version: $VERSION"
echo "  from:    $LINTER_DIR"
echo "  to:      $GLTEST_CACHE"
link_tarball "$LINTER_CACHE/genvm-universal-genlayerlabs-genvm-manager-$VERSION.tar.xz"
link_kind py-genlayer
link_kind py-lib-genlayer-std

echo
echo "verify with:"
echo "  .venv/bin/python -c \"import sys; sys.path.insert(0,'tests/direct'); import helpers; helpers._assert_seeded(); print('ok')\""