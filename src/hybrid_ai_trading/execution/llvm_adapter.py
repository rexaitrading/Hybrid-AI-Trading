"""
LLVM Engine Adapter (Hybrid AI Quant Pro v3.2 Ã¢â‚¬â€œ Hedge Fund Level)
-----------------------------------------------------------------
- Wraps llvmlite ExecutionEngine for JIT compilation
- Provides safe module add, finalize, dispose
- Exposes function pointers via get_fn_addr
- Full error handling for robustness
"""

import logging

from llvmlite import binding

logger = logging.getLogger(__name__)

# Ã¢Å“â€¦ Re-export binding.create_mcjit_compiler so tests can monkeypatch here
create_mcjit_compiler = binding.create_mcjit_compiler


class LLVMEngineAdapter:
    """Safe wrapper around llvmlite MCJIT ExecutionEngine."""

    def __init__(self, llvm_module, target_machine):
        try:
            # use the re-exported symbol, patchable in tests
            self.engine = create_mcjit_compiler(llvm_module, target_machine)
        except Exception as e:
            logger.error("Ã¢ÂÅ’ Failed to create LLVM engine: %s", e)
            raise RuntimeError("Failed to create LLVM engine") from e

        self.modules = {llvm_module}
        self.finalized = False
        logger.debug("Ã¢Å“â€¦ LLVMEngineAdapter initialized")

    # ------------------------------------------------------------------
    def add_module(self, module):
        if module in self.modules:
            raise RuntimeError("Module already added to engine")
        try:
            self.engine.add_module(module)
            self.modules.add(module)
            logger.debug("Ã¢Å“â€¦ Module added to LLVM engine")
        except Exception as e:
            logger.error("Ã¢ÂÅ’ add_module failed: %s", e)
            raise

    # ------------------------------------------------------------------
    def finalize(self):
        try:
            self.engine.finalize_object()
            self.finalized = True
            logger.debug("Ã¢Å“â€¦ LLVM engine finalized")
        except Exception as e:
            logger.error("Ã¢ÂÅ’ Finalize failed: %s", e)

    # ------------------------------------------------------------------
    def get_fn_addr(self, name: str) -> int:
        try:
            addr = self.engine.get_function_address(name)
            if not addr:
                raise RuntimeError(f"Function not found: {name}")
            logger.debug("Ã¢Å“â€¦ Function %s resolved at %s", name, addr)
            return addr
        except Exception as e:
            logger.error("Ã¢ÂÅ’ get_fn_addr failed: %s", e)
            raise RuntimeError(f"Failed to resolve function: {name}") from e

    # ------------------------------------------------------------------
    def dispose(self):
        try:
            self.engine = None
            self.modules.clear()
            self.finalized = False
            logger.debug("Ã°Å¸â€”â€˜Ã¯Â¸Â LLVM engine disposed")
        except Exception as e:
            logger.warning("Ã¢Å¡Â Ã¯Â¸Â Dispose error: %s", e)
