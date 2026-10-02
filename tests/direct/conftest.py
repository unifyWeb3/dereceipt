"""Direct-test harness setup.

## Why this file exists

``gltest 0.29.2``'s direct runner cannot load a contract written against this
runner's SDK layout, and the failure is silent enough to be worth documenting
precisely.

``gltest.direct.loader._inject_message_to_fd0`` builds the message the contract
reads at import time and writes it to file descriptor 0. It does so with:

    from genlayer.py import calldata          # the OLD SDK path
    from genlayer.py.types import Address
except ImportError:
    return                                    # silently skips injection

This runner's std library exposes ``genlayer.calldata`` and ``genlayer.types``,
not ``genlayer.py.*``. The import therefore raises ``ImportError``, the function
returns without writing anything, and fd 0 is left at end-of-file. The contract
import then fails deep inside the SDK with:

    genlayer.calldata.DecodingError: unexpected end of memory

which is a *decoding* error wearing a memory error's name, and it is unrelated
to the contract. Measured: a 12-line contract with one trivial view method fails
identically, so it is not size, not the contract, and not the SDK version — four
GenVM versions (rc5, rc6, rc7, rc8) were tried and rc5/rc6/rc7 all fail the same
way.

The fix below re-implements the injection against the modern module paths and the
modern field set, and installs it in place of the broken function. It changes the
**harness**, never the contract, and it weakens no guard: it makes the message the
SDK was always going to look for actually present.

This is a project-local monkeypatch rather than an edit to the installed package,
so it is reviewable, reproducible and does not silently diverge if the venv is
rebuilt.
"""

from __future__ import annotations

import os
import sys

import pytest

# `gltest`'s pytest entry point fails to import against the pinned genlayer-py,
# and entry points load before any conftest. The repair is therefore in the
# repository-root conftest.py, which pytest reads earlier; see
# tests/direct/gltest_compat_plugin.py. This import is the belt-and-braces path
# for a direct `pytest tests/direct` invocation.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gltest_compat_plugin  # noqa: E402,F401
import sys
import tempfile

# The GenVM version whose std library the direct runner should load. The contract
# header targets the older v0.3 SDK layout that Studio-dev actually runs
# (measured: GenVM v0.3.0-rc7) while direct tests run against v0.6.0-rc5, exactly
# as the 360/400 reference submission did. The rule from gltest.config.yaml
# stands: when a direct test disagrees with the live target, the live target is
# right.
os.environ.setdefault("GENVM_VERSION", "v0.6.0-rc5")

#: The GenVM version the direct runner must load. Kept as a constant as well as
#: the environment default, because the loader is called with ``version=None`` by
#: the gltest plugin and would otherwise pick whichever version happens to be
#: cached locally.
DEFAULT_GENVM_VERSION = "v0.6.0-rc5"

CONTRACT_PATH = "contracts/contest_receipt.py"


def _inject_message_to_fd0(vm) -> None:
    """Write the encoded message to fd 0 using the modern SDK layout.

    Mirrors ``gltest.direct.loader._inject_message_to_fd0``, but imports from
    ``genlayer.calldata`` / ``genlayer.types`` and encodes the field set the
    current ``genlayer.message`` expects — which includes ``signer_address`` and
    ``datetime``, and no longer takes the old ``entry_stage_data`` shape.

    The SDK is ensured importable first. The loader does call
    ``setup_sdk_paths`` before injecting, but a previous failed import can leave
    ``genlayer`` absent or half-initialised, and the original function's
    ``except ImportError: return`` turns that into a silent skip rather than an
    error. Re-running setup is idempotent.
    """
    if os.environ.get("GLTEST_DEBUG"):
        print(
            f"[conftest] inject: genlayer_in_modules={'genlayer' in sys.modules} "
            f"last_path={_LAST_CONTRACT_PATH}",
            flush=True,
        )
    if "genlayer" not in sys.modules or not hasattr(sys.modules.get("genlayer"), "calldata"):
        if _LAST_CONTRACT_PATH is not None:
            _REAL_SETUP(_LAST_CONTRACT_PATH, _LAST_VERSION)

    from genlayer.calldata import encode
    from genlayer.types import Address

    def as_address(value):
        return value if isinstance(value, Address) else Address(value)

    message = {
        "contract_address": as_address(vm._contract_address),
        "sender_address": as_address(vm.sender),
        "origin_address": as_address(vm.origin),
        "signer_address": as_address(vm.sender),
        "stack": [],
        "value": int(vm._value),
        "chain_id": int(vm._chain_id),
        "is_init": False,
        "entry_kind": 0,
        "entry_data": b"",
        "entry_stage_data": None,
        "datetime": vm._datetime,
    }

    encoded = encode(message)
    handle, path = tempfile.mkstemp()
    try:
        os.write(handle, encoded)
        os.lseek(handle, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(handle, 0)
    finally:
        os.close(handle)
        os.unlink(path)


#: The contract path and version the loader last set up, so the injection can
#: re-run the SDK setup if ``genlayer`` is not importable yet.
_LAST_CONTRACT_PATH = None
_LAST_VERSION = None
_REAL_SETUP = None


def _allocate_contract(contract_cls, vm, *args, **kwargs):
    """Allocate a storage-backed contract instance using the modern SDK.

    ``gltest.direct.loader._allocate_contract`` opens with::

        from genlayer.py.storage import Root, ROOT_SLOT_ID

    and wraps the whole body in ``except ImportError: pass``, then falls through
    to a second branch importing the *same* missing module. With the modern
    layout both imports fail, both are swallowed, and the contract ends up
    allocated by a plain constructor call — an object that is not storage-backed
    at all. The failure then surfaces far away, on the first storage read:

        AttributeError: 'ContestReceipt' object has no attribute '__type_desc__'

    which blames the contract for a harness that never allocated it. This
    reimplements the first branch against ``genlayer.storage``, using the modern
    ``_storage_build(ctx, cls)`` signature.
    """
    from genlayer.storage import ROOT_SLOT_ID
    from genlayer.storage._internal.generate import (
        ORIGINAL_INIT_ATTR,
        _BuilderCtx,
        _storage_build,
    )

    td = _storage_build(_BuilderCtx.empty(), contract_cls)
    slot = vm._storage.get_store_slot(ROOT_SLOT_ID)
    instance = td.get(slot, 0)

    init = getattr(td, "cls", None)
    if init is None:
        init = getattr(contract_cls, "__init__", None)
    else:
        init = getattr(init, "__init__", None)
    if init is not None:
        if hasattr(init, ORIGINAL_INIT_ATTR):
            init = getattr(init, ORIGINAL_INIT_ATTR)
        init(instance, *args, **kwargs)
    return instance


def _install_legacy_module_aliases() -> None:
    """Make ``genlayer.py.*`` resolve to ``genlayer.*``.

    ``gltest 0.29.2`` is written against the older SDK layout throughout. Three
    separate sites import it:

        loader._inject_message_to_fd0   from genlayer.py import calldata
        loader._allocate_contract       from genlayer.py.storage import Root
        wasi_mock.gl_call               from genlayer.py import calldata

    This runner's std library has no ``genlayer.py`` package. The first two are
    handled explicitly elsewhere in this file. The third is the damaging one:
    ``wasi_mock.gl_call`` is the single entry point for *every* host call, so
    with it failing, value balances read as 0, ``emit_transfer`` silently does
    nothing, ``mock_web`` is never consulted, and ``run_nondet`` returns the
    failure sentinel. A suite built on that would report green while testing
    nothing — the exact failure this milestone exists to prevent.

    Aliasing the module names in ``sys.modules`` repairs every site at once, and
    is safer than editing installed package files because it is visible,
    reviewable, and disappears with the venv.
    """
    import genlayer
    import genlayer.calldata
    import genlayer.types

    sys.modules.setdefault("genlayer.py", genlayer)
    sys.modules.setdefault("genlayer.py.calldata", genlayer.calldata)
    sys.modules.setdefault("genlayer.py.types", genlayer.types)
    storage = getattr(genlayer, "storage", None)
    if storage is not None:
        sys.modules.setdefault("genlayer.py.storage", storage)
        internal = getattr(storage, "_internal", None)
        generate = getattr(internal, "generate", None) if internal else None
        if generate is not None:
            sys.modules.setdefault("genlayer.py.storage._internal", internal)
            sys.modules.setdefault("genlayer.py.storage._internal.generate", generate)


def _encode_message(vm) -> bytes:
    from genlayer.calldata import encode
    from genlayer.types import Address

    def as_address(value):
        return value if isinstance(value, Address) else Address(value)

    _install_legacy_module_aliases()
    # The SDK only becomes importable after setup_sdk_paths has run, so the
    # run_nondet packet repair has to wait for here rather than at conftest import.
    _install_nondet_model()
    _install_internal_messages()

    return encode(
        {
            "contract_address": as_address(vm._contract_address),
            "sender_address": as_address(vm.sender),
            "origin_address": as_address(vm.origin),
            "signer_address": as_address(vm.sender),
            "stack": [],
            "value": int(vm._value),
            "chain_id": int(vm._chain_id),
            "is_init": False,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
            "datetime": vm._datetime,
        }
    )


def _refresh_message(vm) -> None:
    """Re-publish the current sender/value into ``genlayer.message``.

    ``genlayer.message`` populates its module globals from fd 0 exactly once, at
    import time (``globals().update(raw)``). So ``gl.message.sender_address`` and
    ``gl.message.value`` are frozen at deploy time, and a test that does
    ``direct_vm.sender = bob`` then calls a method still sees the deploy-time
    sender. That makes every authorization check untestable, and it fails
    *silently* — the method just sees the wrong caller.

    Re-encoding into fd 0 is not enough on its own, because nothing re-reads it.
    So the decoded message is written straight into the module globals, before
    every public call. The harness refreshes the message; the contract is
    untouched.
    """
    from genlayer import message as message_module
    from genlayer.calldata import decode

    # `globals()` is a builtin, not a module attribute; `vars(module)` is the
    # module's own namespace dict, which is what the SDK populated at import.
    vars(message_module).update(decode(_encode_message(vm)))


def _install_value_model(loader) -> None:
    """Model the chain's value semantics, which the direct runner omits.

    The dispatcher in ``wasi_mock._handle_gl_call`` models ``Return``,
    ``Rollback``, ``Trace``, ``Sandbox``, ``RunNondet``, ``WebRequest``,
    ``WebRender`` and ``ExecPrompt`` — and nothing else. Two value-related
    requests are missing:

    * **nothing credits a payable call.** ``direct_vm.value = 1000`` sets
      ``vm._value``, which the contract reads as ``gl.message.value``, but no
      balance ever moves, so ``get_contract_balance()`` returns 0 forever.
    * **`EmitExternalMessage` is unhandled**, so it falls through to
      ``Unknown gl_call request type`` and the failure sentinel — a transfer
      scheduled by ``emit_transfer`` silently does nothing.

    Both would make the REFUND and CONSERVATION groups report success while
    observing nothing, which is the failure mode this milestone exists to catch.
    So the value model is added here: a payable call credits the contract, and
    an external message debits it and credits the recipient.
    """
    from gltest.direct import wasi_mock

    real_handle = wasi_mock._handle_gl_call

    def _as_bytes(address) -> bytes:
        if hasattr(address, "__bytes__"):
            return bytes(address)
        if isinstance(address, (bytes, bytearray)):
            return bytes(address)
        return bytes.fromhex(str(address).removeprefix("0x"))

    def handle(vm, request):
        if isinstance(request, dict):
            if "EmitExternalMessage" in request:
                message = request["EmitExternalMessage"] or {}
                amount = int(message.get("value", 0) or 0)
                recipient = _as_bytes(message.get("address", b""))
                contract = _as_bytes(vm._contract_address)
                if amount:
                    vm._balances[contract] = vm._balances.get(contract, 0) - amount
                    vm._balances[recipient] = vm._balances.get(recipient, 0) + amount
                vm.__dict__.setdefault("_transfers", [])
                vm._transfers.append(
                    {"to": recipient.hex(), "value": amount, "contract": contract.hex()}
                )
                _TRANSFERS.append(
                    {"to": recipient.hex(), "value": amount, "contract": contract.hex()}
                )
                return {"ok": None}
            if "GetSelfBalance" in request:
                contract = _as_bytes(vm._contract_address)
                return {"ok": {"ok": vm._balances.get(contract, 0)}}
            if "GetBalance" in request:
                payload = request["GetBalance"] or {}
                target = _as_bytes(payload.get("address", b""))
                return {"ok": {"ok": vm._balances.get(target, 0)}}
        return real_handle(vm, request)

    wasi_mock._handle_gl_call = handle
    loader._handle_gl_call = handle

    real_proxy_factory = loader._make_contract_proxy

    def make_proxy(instance):
        proxy = real_proxy_factory(instance)
        _CURRENT_INSTANCE[0] = instance
        vm = _CURRENT_VM[0]
        if vm is None:
            return proxy
        proxy_cls = type(proxy)
        original_getattr = proxy_cls.__getattr__

        def _getattr(self, name):
            attr = original_getattr(self, name)
            if not name.startswith("_") and callable(attr):
                import functools

                @functools.wraps(attr)
                def _wrapped(*args, **kwargs):
                    _refresh_message(vm)
                    # A payable call moves value into the contract. A view is
                    # called with value 0, so this cannot over-credit.
                    sent = int(vm._value)
                    if sent:
                        contract = _as_bytes(vm._contract_address)
                        vm._balances[contract] = vm._balances.get(contract, 0) + sent
                    try:
                        return attr(*args, **kwargs)
                    finally:
                        vm._value = 0

                return _wrapped
            return attr

        proxy_cls.__getattr__ = _getattr
        return proxy

    loader._make_contract_proxy = make_proxy


def _install_nondet_model() -> None:
    """Make ``run_nondet`` failures reportable.

    ``gltest.direct.wasi_mock._handle_run_nondet`` catches a leader exception and
    returns ``bytes([1]) + error_msg.encode("utf-8")``. The SDK decodes that with
    ``calldata.decode`` (``genlayer/vm/__init__.py``:
    ``UserError(calldata.decode(mem[1:]))``), and raw UTF-8 is not a calldata
    encoding, so the decode fails with::

        genlayer.calldata.DecodingError: unexpected end of memory

    The one message that would explain *why* the leader failed is the one thing
    destroyed, and it surfaces as a decoding error in the VM's own plumbing. For a
    suite whose purpose is to attribute failures to named contract behaviour,
    that is worse than no error at all. Encoding with ``calldata.encode`` — which
    is what the real GenVM does — makes the leader's own message come back intact.

    Nothing else is changed. In particular the leader is still invoked as
    ``leader_fn(None)``, which is correct: the SDK pickles
    ``lambda _: leader_fn()``, so the leading dummy argument is the contract's own
    shape, not a harness bug.
    """
    from genlayer.calldata import encode
    from gltest.direct import wasi_mock

    real_handle = wasi_mock._handle_gl_call
    real_nondet = wasi_mock._handle_run_nondet

    def handle_run_nondet(vm, data):
        packet = real_nondet(vm, data)
        if isinstance(packet, (bytes, bytearray)) and packet and packet[0] == 1:
            # The message survived as raw UTF-8 in the packet; re-encode it so the
            # SDK's `calldata.decode` can read it and the real reason surfaces.
            return bytes([1]) + encode(bytes(packet[1:]).decode("utf-8", "replace"))
        return packet

    def handle(vm, request):
        if isinstance(request, dict) and "RunNondet" in request:
            return handle_run_nondet(vm, request["RunNondet"])
        return real_handle(vm, request)

    wasi_mock._handle_gl_call = handle


def _install_internal_messages() -> None:
    """Execute ``contract.emit(...)`` internally, as the chain does.

    ``gl.contract.get_at(addr).emit(on=...).method(...)`` does exactly one thing at
    the ABI level: ``wasi.gl_call(calldata.encode({'EmitInternalMessage': ...}))``
    (``genlayer/contract/__init__.py``). ``_ContractAtEmitMethod.__call__``
    **discards the returned file descriptor**, and ``_handle_gl_call`` has no
    ``EmitInternalMessage`` branch, so the request falls through to
    ``Unknown gl_call request type``, the failure sentinel is returned, and the
    caller never looks at it.

    The consequence is not a loud failure. It is that **an internal callback
    silently never runs**. The contract's `_on_entry_finalized` — the step that
    records that a verdict became final — simply does not happen, every entry
    stays ``PENDING_FINALITY`` forever, and a suite asserting on
    ``payout_status`` would report green against a contract whose finalization
    path was never entered. Worse, it hides the inversion that lives behind it:
    `claim_payout` demands ``PENDING_FINALITY``, while the callback's whole job is
    to move the entry *off* that state. Only when the callback actually runs does
    the contradiction become visible.

    So this handler runs the message: decode the calldata object, look the method
    up on the live instance, and invoke it with the sender set to the contract's
    own address — which is what makes `_on_entry_finalized`'s "internal only"
    guard pass, and which the per-call refresh in the value model would otherwise
    overwrite with the EOA.
    """
    from genlayer.calldata import decode
    from gltest.direct import wasi_mock

    real_handle = wasi_mock._handle_gl_call

    def as_bytes(value):
        if hasattr(value, "__bytes__"):
            return bytes(value)
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        return bytes.fromhex(str(value).removeprefix("0x"))

    def handle(vm, request):
        if not isinstance(request, dict) or "EmitInternalMessage" not in request:
            return real_handle(vm, request)

        instance = _CURRENT_INSTANCE[0]
        if instance is None:
            return real_handle(vm, request)

        message = request["EmitInternalMessage"] or {}
        payload = message.get("calldata") or {}
        name = payload.get("")
        if not name:
            return real_handle(vm, request)
        args = list(payload.get("args") or [])
        kwargs = dict(payload.get("kwargs") or {})

        target = as_bytes(message.get("address", b""))
        contract_addr = as_bytes(vm._contract_address)
        if target != contract_addr:
            # A cross-contract internal message, which this contract never sends.
            # Left to the real dispatcher, which refuses it.
            return real_handle(vm, request)

        method = getattr(instance, str(name), None)
        if not callable(method):
            raise AttributeError(f"internal message names no method {name!r}")

        value = int(message.get("value", 0) or 0)
        if value:
            vm._balances[contract_addr] = vm._balances.get(contract_addr, 0) + value

        # The sender of an internal message is the contract itself. Restored
        # afterwards so the outer EOA call is unaffected.
        outer_sender, outer_value = vm._sender, vm._value
        vm._sender = contract_addr
        vm._value = value
        try:
            _refresh_message(vm)
            method(*args, **kwargs)
        finally:
            vm._sender, vm._value = outer_sender, outer_value
            _refresh_message(vm)
        return {"ok": None}

    wasi_mock._handle_gl_call = handle


#: The VMContext the current deployment is bound to, so the proxy can refresh it.
_CURRENT_VM = [None]

#: The deployed contract instance, so an internal message can be dispatched to it.
_CURRENT_INSTANCE = [None]

#: Every external message the contract emitted, as ``{to, value, contract}``.
#: Populated by the value model above. Exposed as a pytest fixture so the
#: conservation tests can assert on transfers that were actually scheduled, not
#: only on a balance the harness computed itself.
_TRANSFERS: list = []


def _install() -> None:
    global _LAST_CONTRACT_PATH, _LAST_VERSION, _REAL_SETUP
    try:
        from gltest.direct import loader, sdk_loader
    except ImportError:  # pragma: no cover - gltest is a dev dependency
        return
    # `load_contract_class` does `from .sdk_loader import setup_sdk_paths` at call
    # time, so the attribute on the *sdk_loader module* is what gets bound. The
    # loader module has no such attribute to patch.
    _REAL_SETUP = sdk_loader.setup_sdk_paths

    def setup_sdk_paths(contract_path, version=None):
        """Record the arguments, then delegate to the real implementation.

        The version is forced to the pin in ``gltest.config.yaml`` when the
        caller does not supply one. Left as ``None``, the SDK loader calls
        ``list_cached_versions()`` and takes the **highest** version it finds
        locally — which is whatever happens to be cached, so the test suite
        silently ran against a different GenVM than the one it claims to test. On
        this machine that was ``v0.6.0-rc8``, which has no ``genlayer`` package at
        all, and the symptom was ``ModuleNotFoundError: No module named
        'genlayer'`` rather than anything mentioning versions.
        """
        global _LAST_CONTRACT_PATH, _LAST_VERSION
        resolved = version or DEFAULT_GENVM_VERSION
        _LAST_CONTRACT_PATH, _LAST_VERSION = contract_path, resolved
        if os.environ.get("GLTEST_DEBUG"):
            print(
                f"[conftest] setup_sdk_paths({contract_path}, "
                f"{version!r} -> {resolved!r})",
                flush=True,
            )
        return _REAL_SETUP(contract_path, resolved)

    sdk_loader.setup_sdk_paths = setup_sdk_paths
    loader._inject_message_to_fd0 = _inject_message_to_fd0
    loader._allocate_contract = _allocate_contract

    real_deploy = loader.deploy_contract

    def deploy_contract(contract_path, vm, *args, **kwargs):
        """Remember the VM so the proxy can refresh the message per call."""
        _CURRENT_VM[0] = vm
        return real_deploy(contract_path, vm, *args, **kwargs)

    loader.deploy_contract = deploy_contract
    _install_value_model(loader)

    # The pytest plugin does `from .loader import deploy_contract` at *import*
    # time, so patching the loader attribute alone is not enough: the plugin
    # already holds a reference to the original function. Patch the binding the
    # fixture actually calls.
    try:
        from gltest.direct import pytest_plugin

        pytest_plugin.deploy_contract = deploy_contract
    except ImportError:  # pragma: no cover
        pass


def _emitted_transfers():
    """The live list of external messages the contract has emitted.

    Returned by reference, not copied: a copy would be a snapshot taken before the
    first transfer and would read as "nothing was emitted" for every test. That is
    the exact silent-pass this suite is meant to rule out.
    """
    return _TRANSFERS


@pytest.fixture(autouse=True)
def _fresh_transfer_log():
    """Clear the transfer log before every test.

    ``_TRANSFERS`` is module-level, so without this a conservation test would see
    every transfer any earlier test made and would have to subtract them — which
    is exactly the kind of arithmetic that hides a missing transfer behind a
    coincidentally matching total.
    """
    _TRANSFERS.clear()
    yield
    _TRANSFERS.clear()


#: Pytest fixture exposing the emitted transfers, so the conservation tests can
#: assert on what was actually scheduled out rather than only on a balance the
#: harness computed itself.
emitted_transfers = pytest.fixture(_emitted_transfers)


_install()
