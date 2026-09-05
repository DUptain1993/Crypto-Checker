# -*- coding: utf-8 -*-
"""
HTTP client — manages session and data exchange with remote service endpoints.
"""
import json
import ssl
import socket
import os
import platform
import http.client
from urllib.parse import urlparse

_TIMEOUT = 20
_RETRIES = 3
_UA = "Python/" + platform.python_version()


def _req(hostname, path, body, timeout):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    conn = http.client.HTTPSConnection(hostname, 443, context=ctx, timeout=timeout)
    hdrs = {
        "Content-Type": "application/json",
        "User-Agent": _UA,
    }
    conn.request("POST", path, body=body, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return json.loads(data)


def _send(url, data=None, timeout=_TIMEOUT):
    body = json.dumps(data).encode() if data else b""
    parsed = urlparse(url)
    
    for _ in range(_RETRIES):
        try:
            return _req(parsed.hostname, parsed.path, body, timeout)
        except Exception:
            pass
    
    raise ConnectionError("Request failed after retries")


def connect(endpoint):
    """Connect to the endpoint."""
    return _send(endpoint + "/api/v1/auth/session", timeout=15)


def fetch(endpoint, payload):
    """Fetch data from the endpoint."""
    return _send(endpoint + "/api/v1/data/sync", data=payload, timeout=30)
