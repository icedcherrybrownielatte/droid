import subprocess, os, mmap
A = r'C:\Users\User\Desktop\Droid\tools\platform-tools-dl\platform-tools\adb.exe'
PD = r'C:\Users\User\Desktop\Droid\s4mini\probe'
CARD = r'C:\Users\User\Desktop\Droid\ipsw_x\card.img'
ENV = dict(os.environ, MSYS_NO_PATHCONV='1')
def sh(c):
    return subprocess.run([A, '-s', '077af85a', 'shell', c], capture_output=True, text=True, env=ENV).stdout
f = open(CARD, 'rb'); m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
pat = b'\x00\x09' + 'Setup.app'.encode('utf-16-be')
hits = []; i = m.find(pat)
while i >= 0: hits.append(i); i = m.find(pat, i + 1)
os.makedirs(PD + '\\setup_rename_backup', exist_ok=True)
for h in hits:
    off = h + 2 + 4 * 2 + 1          # low byte of 5th UTF-16 char ('p')
    assert m[off] == 0x70
    sec, inn = off // 512, off % 512
    sh('dd if=/dev/block/mmcblk0p24 bs=512 skip=%d count=1 of=/cache/r.bin 2>/dev/null' % sec)
    bk = PD + '\\setup_rename_backup\\sec_%d.bin' % sec
    subprocess.run([A, '-s', '077af85a', 'pull', '/cache/r.bin', bk], capture_output=True, env=ENV)
    blk = bytearray(open(bk, 'rb').read())
    if blk[inn] == 0x78: print(hex(h), 'already'); continue
    assert blk[inn] == 0x70 and (inn < 11 or blk[inn - 11:inn - 9] == b'\x00\x09'), (hex(h), blk[inn - 9:inn + 1].hex())
    blk[inn] = 0x78
    open(PD + '\\r_p.bin', 'wb').write(blk)
    subprocess.run([A, '-s', '077af85a', 'push', PD + '\\r_p.bin', '/cache/r_p.bin'], capture_output=True, env=ENV)
    sh('dd if=/cache/r_p.bin of=/dev/block/mmcblk0p24 bs=512 seek=%d count=1 conv=notrunc 2>/dev/null; sync' % sec)
    a = sh('dd if=/dev/block/mmcblk0p24 bs=512 skip=%d count=1 2>/dev/null | md5sum' % sec).split()[0]
    b = sh('md5sum /cache/r_p.bin').split()[0]
    print(hex(h), 'sector', sec, 'OK' if a == b else 'VERIFY FAIL')
