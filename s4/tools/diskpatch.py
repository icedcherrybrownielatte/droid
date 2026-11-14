"""S4 GT-I9500: apply the S4 mini's on-disk iOS patches to the S4's copy of card.img (SYSTEM, mmcblk0p20).

Same bytes as s4mini/probe/tools/{bbpatch,buddypatch,mpavpatch,assistivepatch,tccpatch,renamesetup}.py
and the powerd/MobileKeyBag/QuartzCore patches listed in s4mini/docs/PATCHES.md.
Every write is sector by sector: read the sector from the phone, back it up into s4/disk_backup/, verify the
original bytes, patch, write, re-read and compare md5 (CLAUDE.md rule). Device pinned by serial.
Usage: python diskpatch.py [--dry]
"""
import mmap
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, 'ipsw_x', 'rootfs', 'Sochi11D257.N42OS', 'System', 'Library', 'Caches',
                     'com.apple.dyld', 'dyld_shared_cache_armv7s')
CARD = os.path.join(ROOT, 'ipsw_x', 'card.img')
ADB = os.path.join(ROOT, 'tools', 'platform-tools-dl', 'platform-tools', 'adb.exe')
BK = os.path.join(ROOT, 's4', 'disk_backup')
SERIAL = '4d0023254b106097'
PART = '/dev/block/mmcblk0p20'
TMP = '/data/local/tmp'
DELTA = 0x551da800          # card.img offset = shared-cache file offset + DELTA
ENV = dict(os.environ, MSYS_NO_PATHCONV='1')
DRY = '--dry' in sys.argv

CACHE_PATCHES = [  # (name, cache address, new bytes) - all Thumb
    ('powerd_IOKitFn_bxlr', 0x2e1a2914, bytes.fromhex('7047')),
    ('MobileKeyBag_sendwait_ok', 0x32bc3498, bytes.fromhex('01207047')),
    ('QuartzCore_gles_to_sw_context', 0x2f9ff260, bytes.fromhex('fff7ccbf')),
    ('TCCAccessPreflight', 0x34a27318, bytes.fromhex('00207047')),
    ('TCCAccessRequest', 0x34a26bd8, bytes.fromhex('01207047')),
    ('TCCAccessCheckAuditToken', 0x34a2758c, bytes.fromhex('01207047')),
    ('BBDPC_skipUIAppProbe', 0x310f72be, bytes.fromhex('00f098b8')),
    ('PSSetupAssistantNeedsToRun_NO', 0x34146140, bytes.fromhex('00207047')),
    ('MPAVRoutingController_volumeControlIsAvailable_NO', 0x2e7658a4, bytes.fromhex('00207047')),
    ('AXSAssistiveTouchEnabled_YES', 0x3714f39c, bytes.fromhex('01207047')),
    ('AXSAssistiveTouchUIEnabled_YES', 0x3714fee8, bytes.fromhex('01207047')),
]


def adb(*a):
    return subprocess.run([ADB, '-s', SERIAL] + list(a), capture_output=True, text=True, env=ENV).stdout


def sh(c):
    return adb('shell', c)


def read_sector(sec, name):
    sh('dd if=%s bs=512 skip=%d count=1 of=%s/s.bin 2>/dev/null' % (PART, sec, TMP))
    path = os.path.join(BK, 'sec_%d_%s.bin' % (sec, name))
    adb('pull', TMP + '/s.bin', path)
    blk = open(path, 'rb').read()
    assert len(blk) == 512, (sec, len(blk))
    return bytearray(blk)


def write_sector(sec, blk):
    p = os.path.join(BK, 'new.bin')
    open(p, 'wb').write(blk)
    adb('push', p, TMP + '/n.bin')
    sh('dd if=%s/n.bin of=%s bs=512 seek=%d count=1 conv=notrunc 2>/dev/null; sync' % (TMP, PART, sec))
    a = sh('dd if=%s bs=512 skip=%d count=1 2>/dev/null | md5sum' % (PART, sec)).split()[0]
    b = sh('md5sum %s/n.bin' % TMP).split()[0]
    return a == b


def patch_at(off, orig, new, name):
    sec, inn = off // 512, off % 512
    assert inn + len(new) <= 512, name
    blk = read_sector(sec, name)
    cur = bytes(blk[inn:inn + len(new)])
    if cur == new:
        print('%-50s sector %d already patched' % (name, sec)); return
    assert cur == orig[:len(new)], (name, cur.hex(), orig.hex())
    blk[inn:inn + len(new)] = new
    if DRY:
        print('%-50s sector %d +%d %s -> %s (dry)' % (name, sec, inn, cur.hex(), new.hex())); return
    ok = write_sector(sec, blk)
    print('%-50s sector %d +%d %s -> %s %s' % (name, sec, inn, cur.hex(), new.hex(), 'OK' if ok else 'VERIFY FAIL'))
    if not ok:
        sys.exit('verify failed at sector %d: restore from %s' % (sec, BK))


def main():
    os.makedirs(BK, exist_ok=True)
    tgt = sh('readlink -f /dev/block/platform/dw_mmc.0/by-name/SYSTEM').strip()
    assert tgt == PART, 'SYSTEM is %r' % tgt
    d = open(CACHE, 'rb').read()
    mo, mc = struct.unpack_from('<II', d, 16)
    ad, sz, foff, _, _ = struct.unpack_from('<QQQII', d, mo)
    card = open(CARD, 'rb')
    for name, addr, new in CACHE_PATCHES:
        assert ad <= addr < ad + sz, name
        co = addr - ad + foff
        orig = d[co:co + len(new)]
        card.seek(co + DELTA)
        assert card.read(len(new)) == orig, ('card.img does not hold the cache at DELTA', name)
        patch_at(co + DELTA, orig, new, name)
    # /Applications/Setup.app -> Setux.app: HFS catalog keys + thread records (renamesetup.py)
    m = mmap.mmap(card.fileno(), 0, access=mmap.ACCESS_READ)
    pat = b'\x00\x09' + 'Setup.app'.encode('utf-16-be')
    i = m.find(pat)
    while i >= 0:
        off = i + 2 + 4 * 2 + 1      # low byte of the 5th UTF-16 char ('p')
        assert m[off] == 0x70
        patch_at(off, b'\x70', b'\x78', 'Setup.app_rename_%x' % i)
        i = m.find(pat, i + 1)
    sh('rm -f %s/s.bin %s/n.bin' % (TMP, TMP))


main()
