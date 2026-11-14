import struct, capstone
P = r'C:\Users\User\Desktop\Droid\ipsw_x\rootfs\Sochi11D257.N42OS\System\Library\Caches\com.apple.dyld\dyld_shared_cache_armv7s'
d = open(P, 'rb').read()
mo, mc, io, ic = struct.unpack_from('<IIII', d, 16)
maps = [struct.unpack_from('<QQQII', d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    ad, sz, off, _, _ = maps[0]
    if ad <= a < ad + sz: return a - ad + off
imgs = []
for i in range(ic):
    addr, mt, ino, po, _ = struct.unpack_from('<QQQII', d, io + 32 * i)
    imgs.append((addr, d[po:d.index(b'\0', po)].decode()))
imgs.sort()
def img(a):
    b = None
    for x, n in imgs:
        if x <= a: b = (x, n)
    return b
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
PC, LR = 0x39725ce2, 0x39620d23
for k in range(0, 0x10000):
    pc = PC - k * 0x1000; lr = (LR & ~1) - k * 0x1000
    o1 = a2o(pc); o2 = a2o(lr - 4)
    if o1 is None or o2 is None: continue
    i1 = list(md.disasm(d[o1:o1 + 4], pc))
    i2 = list(md.disasm(d[o2:o2 + 4], lr - 4))
    if not i1 or not i2: continue
    a = i1[0]; b = i2[0]
    if a.mnemonic.startswith(('st', 'vst')) and b.mnemonic in ('bl', 'blx') and b.address == lr - 4:
        print(hex(k * 0x1000), a.mnemonic, a.op_str, '|', b.mnemonic, b.op_str, img(pc)[1], img(lr)[1])
