import struct, sys, bisect
P = r'C:\Users\User\Desktop\Droid\ipsw_x\rootfs\Sochi11D257.N42OS\System\Library\Caches\com.apple.dyld\dyld_shared_cache_armv7s'
d = open(P, 'rb').read()
mo, mc, io, ic = struct.unpack_from('<IIII', d, 16)
lso, lss = struct.unpack_from('<QQ', d, 0x48)
print('local syms', hex(lso), hex(lss))
# local symbols info: nlistOffset, nlistCount, stringsOffset, stringsSize, entriesOffset, entriesCount
nlo, nlc, so, ss, eo, ec = struct.unpack_from('<6I', d, lso)
imgs = []
for i in range(ic):
    addr, mt, ino, po, _ = struct.unpack_from('<QQQII', d, io + 32 * i)
    imgs.append((addr, d[po:d.index(b'\0', po)].decode()))
want = sys.argv[1]
syms = []
for k in range(ec):
    dylibOffset, nstart, ncount = struct.unpack_from('<3I', d, lso + eo + 12 * k)
    # dylibOffset is file offset of mach header in cache; map to image by matching
    for j in range(ncount):
        sx, ty, sc, de, va = struct.unpack_from('<IBBHI', d, lso + nlo + 12 * (nstart + j))
        if va and (ty & 0x0e) == 0x0e:
            nm = d[lso + so + sx:d.index(b'\0', lso + so + sx)].decode(errors='replace')
            syms.append((va & ~1, nm))
syms.sort()
addrs = [a for a, _ in syms]
for q in sys.argv[2:]:
    if q.startswith('='):
        for a, n in syms:
            if q[1:] in n: print(hex(a), n)
    else:
        a = int(q, 16) & ~1
        i = bisect.bisect_right(addrs, a) - 1
        print(q, syms[i][1], '+0x%x' % (a - syms[i][0]))
