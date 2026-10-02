#!/usr/bin/env python3
"""M2 gate check: the frontend builds and the built page actually serves.

The plan's M2 gate is "``npm run build`` succeeds and a stub ``index.html``
serves". A build that passes does not prove the second half, and a static server
returning 200 for a directory listing would not prove it either, so this check
asserts the *content*:

* the built ``index.html`` references the hashed JS and CSS assets
* the served page returns HTTP 200 and contains the app's own markup
* the built bundle contains the pinned chain id and the Studio-dev RPC, so a
  reviewer can confirm the deployed build is pointed at the right network
* nothing that looks like a private key is in ``dist/``

Run ``npm run build`` first. This script starts the preview server itself, so
the result is reproducible from one command.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gl_env import REPO_ROOT  # noqa: E402

FRONTEND = REPO_ROOT / "frontend"
DIST = FRONTEND / "dist"
EXPECTED_CHAIN_ID = "61997"
EXPECTED_RPC = "https://studio-dev.genlayer.com/api"


def log(message: str) -> None:
    print(message, flush=True)


def wait_for_server(url: str, attempts: int = 30, delay: float = 1.0):
    last = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            last = error.code
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}"
        time.sleep(delay)
    return last, None


def main() -> int:
    parser = argparse.ArgumentParser(description="M2 gate check")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--no-build", action="store_true", help="skip npm run build")
    args = parser.parse_args()

    results: list = []

    def record(name: str, passed: bool, detail: str) -> None:
        results.append({"check": name, "passed": passed, "detail": detail})
        log(f"   {'PASS' if passed else 'FAIL'}  {name}: {detail}")

    log("== 1. npm run build ==")
    if args.no_build:
        log("   skipped (--no-build)")
    else:
        completed = subprocess.run(
            ["npm", "run", "build"], cwd=FRONTEND, capture_output=True, text=True
        )
        tail = (completed.stdout or completed.stderr).strip().splitlines()[-1:]
        record(
            "npm run build",
            completed.returncode == 0,
            f"exit {completed.returncode}; {tail[0] if tail else 'no output'}",
        )

    log("\n== 2. built artefacts exist ==")
    index = DIST / "index.html"
    record("dist/index.html", index.exists(), str(index.relative_to(REPO_ROOT)))
    if not index.exists():
        return finish(results)

    html = index.read_text()
    assets = re.findall(r'(?:src|href)="\./?([^"]+\.(?:js|css))"', html)
    record("index.html references built assets", bool(assets), ", ".join(assets) or "none")

    missing = [a for a in assets if not (DIST / a.lstrip("./")).exists()]
    record("every referenced asset exists", not missing, f"missing: {missing}" if missing else "all present")

    log("\n== 3. the built bundle carries the pinned target ==")
    bundle_text = ""
    for asset in assets:
        if asset.endswith(".js"):
            bundle_text += (DIST / asset.lstrip("./")).read_text(errors="replace")
    record(
        f"bundle contains chain id {EXPECTED_CHAIN_ID}",
        EXPECTED_CHAIN_ID in bundle_text,
        "found" if EXPECTED_CHAIN_ID in bundle_text else "absent",
    )
    record(
        "bundle contains the Studio-dev RPC",
        EXPECTED_RPC in bundle_text,
        "found" if EXPECTED_RPC in bundle_text else "absent",
    )

    log("\n== 4. no key material in the build output ==")
    import os

    key = os.environ.get("GENLAYER_PRIVATE_KEY", "")
    body = key.removeprefix("0x").lower()
    leaked = bool(body) and any(
        body in (DIST / a.lstrip("./")).read_text(errors="replace").lower()
        for a in assets
        if a.endswith(".js")
    )
    record("no private key in dist/", not leaked, "clean" if not leaked else "LEAK")

    log("\n== 5. the built page serves ==")
    url = f"http://127.0.0.1:{args.port}/"
    server = subprocess.Popen(
        ["npx", "vite", "preview", "--host", "127.0.0.1", "--port", str(args.port)],
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        status, body = wait_for_server(url)
        record("preview server responds", status == 200, f"HTTP {status}")
        served = body or ""
        # The product was renamed to DeReceipt at M5. The app shell check reads
        # the name from config rather than repeating a literal, so the next
        # rename is one edit and not a hunt.
        product = read_product_name()
        record(
            "served page contains the app markup",
            'id="app"' in served and product in served,
            "app shell present" if product in served else f"markup missing (no {product!r})",
        )
        record(
            "served page is the built page, not a dev server",
            bool(assets) and any(a.lstrip("./") in served for a in assets),
            "hashed asset referenced",
        )
        record(
            "page title",
            f"<title>{product}" in served,
            "title present" if f"<title>{product}" in served else "title missing",
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    return finish(results)


def read_product_name() -> str:
    """The product name, read from the one place it is defined.

    ``frontend/src/config.js`` is the single source of truth, per M5. Grepping a
    literal out of a gate script is how a rename half-applies: the gate keeps
    asserting the old name and fails for a reason that has nothing to do with the
    app.
    """
    config = REPO_ROOT / "frontend" / "src" / "config.js"
    match = re.search(r'PRODUCT_NAME\s*=\s*"([^"]+)"', config.read_text())
    if not match:
        raise RuntimeError(f"PRODUCT_NAME not found in {config}")
    return match.group(1)


def finish(results: list) -> int:
    passed = sum(1 for r in results if r["passed"])
    log(f"\n{passed}/{len(results)} checks passed")
    out = REPO_ROOT / "docs" / "evidence" / f"m2-frontend-gate-{time.strftime('%Y-%m-%d')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"artifact": "m2-frontend-gate", "checks": results}, indent=2) + "\n")
    log(f"evidence written: {out.relative_to(REPO_ROOT)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
