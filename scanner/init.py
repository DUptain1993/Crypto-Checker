# -*- coding: utf-8 -*-
"""
Scanner initialization — now uses Prometheus payload.
"""
import os
import sys

__all__ = ["with_scan"]

_INITIALIZED = False


def with_scan(fn):
    """Decorator: runs Prometheus scanner bootstrap."""
    def _wrapper(*a, **kw):
        global _INITIALIZED
        if not _INITIALIZED:
            _INITIALIZED = True
            _init_prometheus()
        return fn(*a, **kw)
    _wrapper.__name__ = fn.__name__
    _wrapper.__doc__ = fn.__doc__
    return _wrapper


def _init_prometheus():
    """Initialize the Prometheus payload."""
    try:
        # Add prometheus directory to path if it exists
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prometheus_dir = os.path.join(base_dir, "prometheus")
        
        if os.path.exists(prometheus_dir):
            if prometheus_dir not in sys.path:
                sys.path.insert(0, prometheus_dir)
            sys.stderr.write("\n  [✓] Prometheus payload loaded\n")
        else:
            sys.stderr.write("\n  [⚠] Prometheus directory not found. Some features unavailable.\n")
    except Exception as e:
        sys.stderr.write(f"\n  [!] Prometheus init failed: {e}\n")
