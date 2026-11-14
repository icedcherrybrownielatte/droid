#!/usr/bin/env python3
"""Pack a raw kernel binary into an Android boot image for the S4 (GT-I9500).

Reuses the original BOOT header (addresses, page size 2048, cmdline) and its ramdisk from
../backup/BOOT.img; only the kernel changes. Output must stay <= 8 MiB (BOOT partition size).
Usage: pack_boot.py kernel.bin out.img
"""
import hashlib
import struct
import sys

PART = 8 * 1024 * 1024
src = open(sys.argv[1], 'rb').read()
orig = open(__file__.rsplit('\\', 1)[0].rsplit('/', 1)[0] + '/../backup/BOOT.img', 'rb').read()
assert orig[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from('<8I', orig, 8)
ramdisk = orig[ps + ((ks + ps - 1) // ps) * ps:][:rs]
hdr = bytearray(orig[:ps])
struct.pack_into('<I', hdr, 8, len(src))           # kernel size
h = hashlib.sha1()
for blob in (src, ramdisk, b''):
    h.update(blob); h.update(struct.pack('<I', len(blob)))
hdr[576:576 + 32] = h.digest().ljust(32, b'\0')     # id field (informational)
pad = lambda b: b + b'\0' * ((-len(b)) % ps)
img = bytes(hdr) + pad(src) + pad(ramdisk)
assert len(img) <= PART, len(img)
open(sys.argv[2], 'wb').write(img)
print('boot image', sys.argv[2], len(img), 'bytes; kernel', len(src), 'ramdisk', len(ramdisk))
