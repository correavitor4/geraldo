# core/__init__.py
"""Módulo core do assistente Geraldo."""

def __getattr__(name):
    if name in ("GeraldoIPCServer", "IPCManager"):
        from .ipc import GeraldoIPCServer, IPCManager
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["GeraldoIPCServer", "IPCManager"]

