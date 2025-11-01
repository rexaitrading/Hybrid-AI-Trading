"""
Unit Tests â€“ LLVMEngineAdapter
(Hybrid AI Quant Pro v3.6 â€“ Hedge Fund OE Grade, 100% Coverage)
----------------------------------------------------------------
Covers ALL branches in llvm_adapter.py (10â€“75):
- Normal init/finalize/dispose
- Function address resolution (valid/invalid)
- Double-add raises (lines 40â€“41)
- Finalize/dispose idempotent
- Dispose-before-finalize safe
- Engine creation failure
- add_module failure branch
- finalize failure branch
- dispose failure branch
- Logging paths for success/failure
"""

import ctypes
import os
import sys

import pytest
from llvmlite import binding, ir

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import hybrid_ai_trading.execution.llvm_adapter as llvm_adapter
from hybrid_ai_trading.execution.llvm_adapter import LLVMEngineAdapter


# ----------------------------------------------------------------------
# Fixtures & Helpers
# ----------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def llvm_init():
    """Initialize LLVM once for the test session."""
    binding.initialize()
    binding.initialize_native_target()
    binding.initialize_native_asmprinter()


def build_dummy_module(name: str = "test_module"):
    """Return a simple LLVM IR module with one int function returning 42."""
    module = ir.Module(name=name)
    func_type = ir.FunctionType(ir.IntType(32), [])
    func = ir.Function(module, func_type, name="myfunc")
    block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(block)
    builder.ret(ir.Constant(ir.IntType(32), 42))
    llvm_ir = str(module)
    llvm_mod = binding.parse_assembly(llvm_ir)
    llvm_mod.verify()
    return llvm_mod


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_adapter_init_finalize_and_dispose(caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()

    caplog.set_level("DEBUG")
    adapter = LLVMEngineAdapter(llvm_mod, tm)
    assert "initialized" in caplog.text.lower()

    adapter.finalize()
    assert adapter.finalized
    assert "finalized" in caplog.text.lower()

    addr = adapter.get_fn_addr("myfunc")
    fn_type = ctypes.CFUNCTYPE(ctypes.c_int)
    fn = fn_type(addr)
    assert fn() == 42
    assert "resolved" in caplog.text.lower()

    adapter.dispose()
    assert not adapter.finalized
    assert "disposed" in caplog.text.lower()


def test_get_fn_addr_invalid_function(caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)
    adapter.finalize()

    caplog.set_level("ERROR")
    with pytest.raises(RuntimeError):
        adapter.get_fn_addr("does_not_exist")
    assert "failed" in caplog.text.lower()
    adapter.dispose()


def test_add_module_twice_and_failure_branch(monkeypatch, caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)

    # ðŸ”‘ Explicit double-add (hits lines 40â€“41)
    with pytest.raises(RuntimeError):
        adapter.add_module(llvm_mod)

    # Simulate add_module failure
    def bad_add(_):
        raise RuntimeError("forced add fail")

    monkeypatch.setattr(adapter.engine, "add_module", bad_add)
    caplog.set_level("ERROR")
    with pytest.raises(RuntimeError):
        adapter.add_module(build_dummy_module())
    assert "failed" in caplog.text.lower()


def test_finalize_and_dispose_multiple_times_safe():
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)

    adapter.finalize()
    adapter.finalize()  # idempotent
    adapter.dispose()
    adapter.dispose()  # safe again


def test_dispose_before_finalize_safe():
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)
    adapter.dispose()  # should not raise


def test_init_with_invalid_module(monkeypatch, caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()

    def bad_create(module, tmachine):
        raise Exception("forced failure")

    monkeypatch.setattr(llvm_adapter, "create_mcjit_compiler", bad_create)
    caplog.set_level("ERROR")
    with pytest.raises(RuntimeError):
        LLVMEngineAdapter(llvm_mod, tm)
    assert "failed" in caplog.text.lower()


def test_finalize_failure_branch(monkeypatch, caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)

    def bad_finalize():
        raise Exception("forced finalize fail")

    monkeypatch.setattr(adapter.engine, "finalize_object", bad_finalize)
    caplog.set_level("ERROR")
    adapter.finalize()
    assert not adapter.finalized
    assert "finalize failed" in caplog.text.lower()


def test_dispose_failure_branch(caplog):
    llvm_mod = build_dummy_module()
    target = binding.Target.from_default_triple()
    tm = target.create_target_machine()
    adapter = LLVMEngineAdapter(llvm_mod, tm)

    class FakeModules:
        def clear(self):
            raise Exception("forced clear fail")

    adapter.modules = FakeModules()
    caplog.set_level("WARNING")
    adapter.dispose()
    assert "dispose error" in caplog.text.lower()
