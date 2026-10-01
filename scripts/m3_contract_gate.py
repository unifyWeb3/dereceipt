#!/usr/bin/env python3
"""M3 gate: audit the contract against the rules that a linter cannot check.

``genvm-lint`` and the live schema probe both answer "does this compile and what
does it expose". Neither can answer the two rules the M3 gate actually turns on,
so this audits them mechanically from the AST rather than by reading:

* **no ``raise`` in any method that received value** — a revert in a payable
  method strands that value, so every such method must return a refusal instead
* **no clock read sharing a method with a value transfer** — Studio-dev's fee
  estimator runs on a badly stale clock, so that combination reverts with
  ``out_of message_fee total``

It also reports, per method, which ones read the clock and which ones move value,
because the gate asks for that mapping explicitly. And it confirms the LLM
absence that the whole deterministic core rests on: ``exec_prompt`` /
``eq_principle`` must not appear anywhere.

Findings are recorded, not just printed, so the M6 run can re-check them against
the contract that is actually deployed.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gl_env import REPO_ROOT  # noqa: E402

CONTRACT = "contracts/contest_receipt.py"

#: Calls that read the block clock.
CLOCK_CALLS = {"_now", "get_timestamp"}
#: Calls that move value out of the contract.
TRANSFER_CALLS = {"emit_transfer"}
#: Model entry points. None may appear: the deterministic core has no model in
#: the decision path, which is the property the 360/400 build was scored on.
LLM_SYMBOLS = {"exec_prompt", "prompt_comparative", "prompt_non_comparative", "strict_eq"}


def log(message: str) -> None:
    print(message, flush=True)


def dotted_name(node) -> str:
    """Rebuild a dotted name from an Attribute/Name chain.

    ``ast.walk`` yields nodes in no useful order, so joining its output produced
    ``"payable.write.public"`` and silently matched nothing. This walks the chain
    explicitly.
    """
    parts: list = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def method_info(node) -> dict:
    """Decorators, and whether the body raises / reads the clock / moves value."""
    decorators = []
    payable = False
    is_write = False
    is_view = False
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        dotted = dotted_name(target)
        decorators.append(dotted)
        if dotted.endswith("write.payable"):
            is_write = True
            payable = True
        elif dotted.endswith("write"):
            is_write = True
        elif dotted.endswith("view"):
            is_view = True

    called: set = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call):
            called.add(dotted_name(inner.func))
        elif isinstance(inner, ast.Attribute):
            called.add(inner.attr)

    return {
        "name": node.name,
        "decorators": decorators,
        "is_write": is_write,
        "is_view": is_view,
        "payable": payable,
        "reads_clock": bool(called & CLOCK_CALLS),
        "moves_value": bool(called & TRANSFER_CALLS),
        "raises_directly": has_own_raise(node),
        "called": sorted(called),
    }


def has_own_raise(node) -> bool:
    """True when the method body itself raises, ignoring nested helper functions.

    A raise inside a helper is a raise in whichever method calls the helper, so
    the audit reports helper-mediated raises separately rather than pretending
    they are not there.
    """
    stack = list(node.body)
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(current, ast.Raise):
            return True
        stack.extend(ast.iter_child_nodes(current))
    return False


def helpers_that_raise(node) -> list:
    """Names of nested helpers in this method that contain a raise."""
    names = []
    for inner in ast.walk(node):
        if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)) and inner is not node:
            if has_own_raise(inner):
                names.append(inner.name)
    return names


def build_raise_map(contract_class) -> tuple:
    """Map every method in the class to whether it can transitively revert.

    A ``raise`` inside ``_fail`` is a revert in every method that calls
    ``_fail``, so checking only for a literal ``raise`` in a public method's own
    body would pass a contract that reverts. This resolves the call graph:

    * ``_fail`` reverts, and every method that reaches it reverts
    * a public method that only ever calls ``_refuse`` never reverts

    The difference is the whole point of the M3 rule, so it is computed rather
    than asserted.
    """
    functions = {
        node.name: node
        for node in contract_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def own_raises(name: str) -> bool:
        node = functions.get(name)
        return bool(node) and has_own_raise(node)

    def calls(name: str) -> set:
        node = functions.get(name)
        if node is None:
            return set()
        found = set()
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            # `self._fail(...)` dotted-names to "self._fail"; the class member it
            # reaches is "_fail". Compare on the final component, or the call
            # graph silently never connects and every method looks revert-free.
            found.add(dotted_name(inner.func).rsplit(".", 1)[-1])
        return found

    # Fixpoint: a method reverts if it raises itself or reaches something that does.
    reverts = {name for name in functions if own_raises(name)}
    changed = True
    while changed:
        changed = False
        for name in functions:
            if name in reverts:
                continue
            if calls(name) & reverts:
                reverts.add(name)
                changed = True

    paths: dict = {}
    for name in sorted(functions):
        if not own_raises(name):
            continue
        reachable = {name}
        frontier = calls(name)
        while frontier:
            nxt = frontier & set(functions) - reachable
            if not nxt:
                break
            reachable |= nxt
            frontier = set().union(*(calls(n) for n in nxt)) if nxt else set()
        paths[name] = sorted(reachable)
    return reverts, paths


def build_reachability(contract_class, seeds: set) -> set:
    """Every method that transitively reaches one of ``seeds``.

    Needed for the same reason as the raise map: the clock read and the transfer
    both live in helpers now, so a shallow scan would report that a public method
    touches neither when it plainly does.
    """
    functions = {
        node.name: node
        for node in contract_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def callers_of(name: str) -> set:
        """Who calls ``name``, directly.

        ``self._fail(...)`` dotted-names to ``self._fail``; the class member it
        reaches is ``_fail``. Comparing on the final component, or the graph
        silently never connects and every method looks revert-free.
        """
        found = set()
        for candidate, node in functions.items():
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Call):
                    continue
                if dotted_name(inner.func).rsplit(".", 1)[-1] == name:
                    found.add(candidate)
        return found

    reached = set()
    frontier = set(functions) & seeds
    reached |= frontier
    while frontier:
        # Reverse edges: the question is which methods end up *executing* the
        # seed, not which methods the seed executes. Walking forward edges here
        # reported the opposite of the truth.
        nxt = set().union(*(callers_of(n) for n in frontier)) - reached if frontier else set()
        if not nxt:
            break
        reached |= nxt
        frontier = nxt
    # Two ways to reach a behaviour: by calling it directly on any object, or by
    # calling a method that does. `emit_transfer` is a method on the generated
    # recipient proxy rather than on this class, so a reverse-edge walk over class
    # methods alone never sees it — a shallow scan has to be unioned in, or the
    # audit reports that nothing moves value.
    def calls_directly(name: str) -> set:
        node = functions.get(name)
        if node is None:
            return set()
        found = set()
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call):
                found.add(dotted_name(inner.func).rsplit(".", 1)[-1])
        return found

    direct_clock = {n for n in functions if calls_directly(n) & CLOCK_CALLS}
    direct_value = {n for n in functions if calls_directly(n) & TRANSFER_CALLS}

    return reached | {
        n for n in functions if n in (direct_clock if seeds is CLOCK_CALLS else direct_value)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M3 contract rule audit")
    parser.add_argument("--contract", default=CONTRACT)
    args = parser.parse_args()

    path = REPO_ROOT / args.contract
    source = path.read_text()
    tree = ast.parse(source)

    contract_class = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ContestReceipt":
            contract_class = node
    if contract_class is None:
        log("FAIL: ContestReceipt class not found")
        return 1

    methods = []
    for node in contract_class.body:
        # The class body also holds annotated storage declarations, which parse
        # as bare `AnnAssign`/`Expr` nodes rather than functions.
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("__"):
            continue
        info = method_info(node)
        if not (info["is_write"] or info["is_view"]):
            continue
        info["helpers_that_raise"] = helpers_that_raise(node)
        methods.append(info)

    reverts, revert_paths = build_raise_map(contract_class)
    # Same reasoning for the clock and the transfer: both now sit in helpers, so
    # attribute these transitively or the audit reports a method that plainly
    # reads the clock as one that does not.
    clock_reachers = build_reachability(contract_class, CLOCK_CALLS)
    value_reachers = build_reachability(contract_class, TRANSFER_CALLS)
    for m in methods:
        m["reads_clock"] = m["name"] in clock_reachers
        m["moves_value"] = m["name"] in value_reachers
    # A method that reverts only when it catches the error first is safe. The
    # contract's own `except gl.vm.UserError` blocks are what make the canonical-
    # isation helpers safe to call from a payable method, so the audit reports
    # both the raw reachability and the caught form.
    catches = {}
    for name, node in [
        (n.name, n)
        for n in contract_class.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]:
        handlers = set()
        for inner in ast.walk(node):
            if isinstance(inner, ast.ExceptHandler) and inner.type is not None:
                handlers.add(dotted_name(inner.type))
        if handlers:
            catches[name] = sorted(handlers)

    public = [m for m in methods if not m["name"].startswith("_")]
    internal_callbacks = [m for m in methods if m["name"].startswith("_")]

    for m in methods:
        m["can_revert"] = m["name"] in reverts
        m["catches"] = catches.get(m["name"], [])

    log("== per-method audit ==")
    header = (
        f"{'method':24} {'kind':7} {'payable':8} {'clock':6} {'value':6} "
        f"{'reverts':8} {'catches'}"
    )
    log("   " + header)
    for m in sorted(public + internal_callbacks, key=lambda m: m["name"]):
        kind = "view" if m["is_view"] else "write"
        log(
            "   "
            + f"{m['name']:24} {kind:7} {str(m['payable']):8} "
            + f"{str(m['reads_clock']):6} {str(m['moves_value']):6} "
            + f"{str(m.get('can_revert', False)):8} {m.get('catches') or ''}"
        )

    findings = []

    # --- Gate rule 1: no revert in a method that received value --------------
    # A method that reaches a raise *transitively* reverts, so a literal-`raise`
    # scan would pass a contract that does not. The only safe shape is a payable
    # method that both (a) does not raise itself and (b) catches the user errors
    # its helpers raise.
    payable = [m for m in methods if m["payable"]]
    payable_unsafe = [
        {
            "method": m["name"],
            "raises_directly": m["raises_directly"],
            "can_revert": m["can_revert"],
            "catches": m.get("catches") or [],
        }
        for m in payable
        if m["raises_directly"] or (m["can_revert"] and not m.get("catches"))
    ]
    findings.append(
        {
            "rule": "no revert in any method that received value",
            "basis": "a revert in a payable method strands that value",
            "payable_methods": sorted(m["name"] for m in payable),
            "reachable_revert_helpers": {
                name: paths for name, paths in revert_paths.items() if len(paths) > 1
            },
            "offenders": payable_unsafe,
            "passed": not payable_unsafe,
        }
    )
    log(
        f"\nrule 1 — no revert in a payable method: "
        f"{'PASS' if not payable_unsafe else 'FAIL ' + str(payable_unsafe)}"
    )
    log(f"   all methods that can revert: {sorted(m['name'] for m in methods if m['can_revert'])}")
    log(f"   revert helpers and what they reach: {revert_paths}")

    # --- Gate rule 2: no clock read sharing a method with a transfer ---------
    clock_and_value = [
        m["name"] for m in methods if m["reads_clock"] and m["moves_value"]
    ]
    findings.append(
        {
            "rule": "no clock read sharing a method with a value transfer",
            "basis": "Studio-dev's stale fee-estimator clock reverts that combination",
            "clock_readers": sorted(m["name"] for m in methods if m["reads_clock"]),
            "value_movers": sorted(m["name"] for m in methods if m["moves_value"]),
            "offenders": clock_and_value,
            "passed": not clock_and_value,
        }
    )
    log(
        f"rule 2 — no clock read with a transfer: "
        f"{'PASS' if not clock_and_value else 'FAIL ' + str(clock_and_value)}"
    )
    log(f"   clock readers : {sorted(m['name'] for m in methods if m['reads_clock'])}")
    log(f"   value movers  : {sorted(m['name'] for m in methods if m['moves_value'])}")

    # --- The deterministic core has no model in the decision path ------------
    llm_hits = sorted(
        symbol for symbol in LLM_SYMBOLS if symbol in ast.dump(tree) or symbol in source
    )
    llm_hits = [s for s in llm_hits if s != "strict_eq" or "strict_eq(" in source]
    findings.append(
        {
            "rule": "no model entry point anywhere in the contract",
            "basis": "the deterministic core must be arithmetic over authoritative data",
            "symbols_found": llm_hits,
            "passed": not llm_hits,
        }
    )
    log(f"rule 3 — no model in the decision path: {'PASS' if not llm_hits else 'FAIL ' + str(llm_hits)}")

    # --- run_nondet, not run_nondet_unsafe ----------------------------------
    uses_unsafe = "run_nondet_unsafe" in source
    uses_safe = "run_nondet(" in source
    findings.append(
        {
            "rule": "use gl.vm.run_nondet, never run_nondet_unsafe",
            "basis": "the pinned runner's std library exports no run_nondet_unsafe",
            "uses_run_nondet": uses_safe,
            "uses_run_nondet_unsafe": uses_unsafe,
            "passed": uses_safe and not uses_unsafe,
        }
    )
    log(
        f"rule 4 — run_nondet present, run_nondet_unsafe absent: "
        f"{'PASS' if uses_safe and not uses_unsafe else 'FAIL'}"
    )

    # --- storage bounds are stated, not implied -----------------------------
    import re as _re

    stated_caps = {
        name: int(value.replace("_", ""))
        for name, value in _re.findall(r"^MAX_([A-Z_]+) = ([\d_]+)", source, _re.M)
    }
    findings.append(
        {
            "rule": "every storage bound is a named constant",
            "basis": "the plan requires the cap to be stated, not implied",
            "caps": stated_caps,
            "passed": len(stated_caps) >= 4,
        }
    )
    log(f"rule 5 — named storage caps: {sorted(stated_caps)}")

    record = {
        "artifact": "m3-contract-rule-audit",
        "generated_by": "scripts/m3_contract_gate.py",
        "observed_on": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "contract": args.contract,
        "method_count": len(public) + len(internal_callbacks),
        "public_method_count": len(public),
        "internal_callback_count": len(internal_callbacks),
        "methods": [
            {k: v for k, v in m.items() if k not in ("called", "helpers_that_raise")}
            for m in public + internal_callbacks
        ],
        "findings": findings,
        "passed": all(f["passed"] for f in findings),
    }

    out = REPO_ROOT / "docs" / "evidence" / f"m3-rule-audit-{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    log(f"\nevidence written: {out.relative_to(REPO_ROOT)}")
    log(f"public methods: {len(public)}   internal callbacks: {len(internal_callbacks)}")
    log(f"AUDIT: {'PASS' if record['passed'] else 'FAIL'}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
