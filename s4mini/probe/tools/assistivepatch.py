import struct, subprocess, os
C = r'C:\Users\User\Desktop\Droid\ipsw_x\rootfs\Sochi11D257.N42OS\System\Library\Caches\com.apple.dyld\dyld_shared_cache_armv7s'
CARD = r'C:\Users\User\Desktop\Droid\ipsw_x\card.img'
A = r'C:\Users\User\Desktop\Droid\tools\platform-tools-dl\platform-tools\adb.exe'
PD = r'C:\Users\User\Desktop\Droid\s4mini\probe'
DELTA = 0x551da800
d = open(C, 'rb').read()
mo, mc = struct.unpack_from('<II', d, 16)
maps = [struct.unpack_from('<QQQII', d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    ad, sz, off, _, _ = maps[0]
    assert ad <= a < ad + sz
    return a - ad + off
patches = [  # (name, addr, new bytes)
    # libAccessibility: force AssistiveTouch on (user request; no plist file needed on HFS).
    ('AXSAssistiveTouchEnabled_YES', 0x3714f39c, bytes.fromhex('01207047')),    # movs r0,#1; bx lr
    ('AXSAssistiveTouchUIEnabled_YES', 0x3714fee8, bytes.fromhex('01207047')),
]
def sh(c):
    return subprocess.run([A, '-s', '077af85a', 'shell', c], capture_output=True, text=True,
                          env=dict(os.environ, MSYS_NO_PATHCONV='1')).stdout
card = open(CARD, 'rb')
for name, addr, new in patches:
    co = a2o(addr); off = co + DELTA
    orig = d[co:co + 4]
    card.seek(off); assert card.read(4) == orig, name
    sec, inn = off // 512, off % 512
    sh('dd if=/dev/block/mmcblk0p24 bs=512 skip=%d count=1 of=/cache/t.bin 2>/dev/null' % sec)
    subprocess.run([A, '-s', '077af85a', 'pull', '/cache/t.bin', PD + '\\s_axat_%s.bin' % name], capture_output=True,
                   env=dict(os.environ, MSYS_NO_PATHCONV='1'))
    blk = bytearray(open(PD + '\\s_axat_%s.bin' % name, 'rb').read())
    if bytes(blk[inn:inn + 4]) == new:
        print(name, 'already patched'); continue
    assert bytes(blk[inn:inn + 4]) == orig, (name, blk[inn:inn + 4].hex(), orig.hex())
    blk[inn:inn + 4] = new
    open(PD + '\\t_p.bin', 'wb').write(blk)
    subprocess.run([A, '-s', '077af85a', 'push', PD + '\\t_p.bin', '/cache/t_p.bin'], capture_output=True,
                   env=dict(os.environ, MSYS_NO_PATHCONV='1'))
    sh('dd if=/cache/t_p.bin of=/dev/block/mmcblk0p24 bs=512 seek=%d count=1 conv=notrunc 2>/dev/null; sync' % sec)
    chk = sh('dd if=/dev/block/mmcblk0p24 bs=512 skip=%d count=1 2>/dev/null | md5sum' % sec).split()[0]
    want = sh('md5sum /cache/t_p.bin').split()[0]
    print(name, 'sector', sec, '+', inn, orig.hex(), '->', new.hex(), 'OK' if chk == want else 'VERIFY FAIL')
