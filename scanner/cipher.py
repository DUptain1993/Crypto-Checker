# -*- coding: utf-8 -*-
"""
Data encoding and validation — secure token generation and stream decoding.
"""
import hashlib
import hmac
import base64


def sign_request(nonce, ts, secret):
    msg = (nonce + str(ts)).encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def decrypt_data(key_hex, data_b64):
    """Decrypt data using AES-GCM."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = bytes.fromhex(key_hex)
        raw = base64.b64decode(data_b64)
        gcm = AESGCM(key)
        return gcm.decrypt(raw[:12], raw[12:], None)
    except Exception:
        return None


def parse_header(data):
    """Parse PE header for binary payloads."""
    if len(data) < 256:
        return None
    
    import struct
    if struct.unpack_from("<H", data, 0)[0] != 0x5A4D:
        return None
    
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_off + 4 > len(data) or struct.unpack_from("<I", data, pe_off)[0] != 0x4550:
        return None
    
    return {
        "entry_point": struct.unpack_from("<I", data, pe_off + 0x10)[0],
        "image_base": struct.unpack_from("<Q", data, pe_off + 0x18)[0],
        "size": struct.unpack_from("<I", data, pe_off + 0x38)[0],
    }
