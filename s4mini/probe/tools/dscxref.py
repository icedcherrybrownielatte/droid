import struct, sys, capstone
P = r'C:\Users\User\Desktop\Droid\ipsw_x\rootfs\Sochi11D257.N42OS\System\Library\Caches\com.apple.dyld\dyld_shared_cache_armv7s'
d = open(P, 'rb').read()
mo, mc, io, ic = struct.unpack_from('<IIII', d, 16)
maps = [struct.unpack_from('<QQQII', d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    for ad, sz, off, _, _ in maps:
        if ad <= a < ad + sz: return a - ad + off
imgname = sys.argv[1]
targets = set(int(x, 16) for x in sys.argv[2:])
# locate image header and __TEXT,__text section
hdr = None
for i in range(ic):
    addr, mt, ino, po, _ = struct.unpack_from('<QQQII', d, io + 32 * i)
    name = d[po:d.index(b'\0', po)].decode()
    if name.endswith('/' + imgname): hdr = addr; break
o = a2o(hdr)
ncmds = struct.unpack_from('<I', d, o + 16)[0]
p = o + 28; text = None
for _ in range(ncmds):
    cmd, sz = struct.unpack_from('<II', d, p)
    if cmd == 1:
        nsect = struct.unpack_from('<I', d, p + 48)[0]
        for k in range(nsect):
            q = p + 56 + 68 * k
            sn = d[q:q + 16].rstrip(b'\0')
            va, vs = struct.unpack_from('<II', d, q + 32)
            if sn == b'__text': text = (va, vs)
    p += sz
print('text', hex(text[0]), hex(text[1]))
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.skipdata = True
lo = {}; hi = {}
base = text[0]; code = d[a2o(base):a2o(base) + text[1]]
for ins in md.disasm(code, base):
    m = ins.mnemonic; ops = ins.op_str
    if m.startswith('movw'):
        r, v = ops.split(', ')
        try: lo[r] = int(v.lstrip('#'), 0); hi.pop(r, None)
        except ValueError: pass
    elif m.startswith('movt'):
        r, v = ops.split(', ')
        try: hi[r] = int(v.lstrip('#'), 0)
        except ValueError: pass
    elif m.startswith('add') and ops.endswith(', pc'):
        r = ops.split(', ')[0]
        if r in lo:
            val = ((hi.get(r, 0) << 16) | lo[r]) + ins.address + 4
            val &= 0xffffffff
            if any(t <= val < t + 0x60 for t in targets): print('xref', hex(val), 'at', hex(ins.address))
