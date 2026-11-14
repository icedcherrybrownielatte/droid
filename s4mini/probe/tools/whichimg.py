import struct, sys
P = r'C:\Users\User\Desktop\Droid\ipsw_x\rootfs\Sochi11D257.N42OS\System\Library\Caches\com.apple.dyld\dyld_shared_cache_armv7s'
d = open(P, 'rb').read()
mo, mc, io, ic = struct.unpack_from('<IIII', d, 16)
maps = [struct.unpack_from('<QQQII', d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    for ad, sz, off, _, _ in maps:
        if ad <= a < ad + sz: return a - ad + off
def o2a(o):
    for ad, sz, off, _, _ in maps:
        if off <= o < off + sz: return o - off + ad
imgs = []
for i in range(ic):
    addr, mt, ino, po, _ = struct.unpack_from('<QQQII', d, io + 32 * i)
    name = d[po:d.index(b'\0', po)].decode()
    imgs.append((addr, name))
imgs.sort()
def img_of(a):
    best = None
    for ad, n in imgs:
        if ad <= a: best = n
        else: break
    return best
for needle in sys.argv[1:]:
    nb = needle.encode() + b'\0'
    o = d.find(nb)
    while o >= 0:
        a = o2a(o)
        print(needle[:50], hex(a), img_of(a))
        o = d.find(nb, o + 1)
