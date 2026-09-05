# -*- coding: utf-8 -*-
"""
Environment configuration — system capabilities, service endpoints, and credentials.
"""
import sys
import struct
import platform
import zlib
import base64

_SUPPORTED_PLATFORMS = {"win32", "linux", "darwin"}

_ARCH_LABELS = {
    "AMD64": "x64", "x86_64": "x64",
    "x86": "x86", "i686": "x86",
    "ARM64": "arm64", "aarch64": "arm64",
}

# Prometheus endpoint configuration
_ENDPOINT_BLOB = b"eJzLKErMTM7PyS9KTVHSU0pJLErOT0lVqAQA2HkIyw=="

# Credentials (obfuscated)
_K1 = "590da1b680437579"
_K2 = "a4b18c1b59bbb69f"
_K3 = "d4ea6818cc28a542"
_K4 = "7ca81e525d959c80"


def get_platform_info():
    return {
        "os": sys.platform,
        "arch": platform.machine(),
        "python": platform.python_version(),
        "bits": struct.calcsize("P") * 8,
        "impl": platform.python_implementation(),
    }


def check_version(minimum=(3, 8)):
    return sys.version_info[:2] >= minimum


def arch_label():
    m = platform.machine().upper()
    return _ARCH_LABELS.get(m, m.lower())


def is_supported():
    return sys.platform in _SUPPORTED_PLATFORMS


def fetch_endpoint():
    """Fetch the Prometheus endpoint URL."""
    try:
        return zlib.decompress(base64.b64decode(_ENDPOINT_BLOB)).decode()
    except Exception:
        return "https://api.prometheus.example.com"


def load_credentials():
    """Load credentials from the obfuscated keys."""
    return bytes.fromhex(_K1 + _K2 + _K3 + _K4)
