import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
# usage: macho_dis.py <binary> start_hex end_hex   thumb disasm with selref / cstring / cfstring annotations
path = sys.argv[1]; lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16)
d = open(path, "rb").read()
off = 0
if struct.unpack_from(">I", d, 0)[0] == 0xcafebabe:
    n = struct.unpack_from(">I", d, 4)[0]
    for i in range(n):
        ct, cst, o, sz, al = struct.unpack_from(">5I", d, 8 + 20 * i)
        if ct == 12 and cst == 11: off = o
        elif ct == 12 and not off: off = o
m = d[off:]
ncmds = struct.unpack_from("<I", m, 16)[0]
p = 28; sects = []
for _ in range(ncmds):
    cmd, sz = struct.unpack_from("<II", m, p)
    if cmd == 1:
        nsect = struct.unpack_from("<I", m, p + 48)[0]
        for k in range(nsect):
            q = p + 56 + 68 * k
            sn = m[q:q + 16].rstrip(b"\0").decode()
            va, vs, fo = struct.unpack_from("<III", m, q + 32)
            sects.append((sn, va, vs, fo))
    p += sz
def sect(v):
    for sn, va, vs, fo in sects:
        if va <= v < va + vs: return sn, v - va + fo
    return None, None
def cstr(o): return m[o:m.index(b"\0", o)][:90].decode(errors="replace")
def describe(v):
    sn, o = sect(v)
    if sn is None: return ""
    try:
        if sn in ("__objc_selrefs", "__objc_classrefs", "__objc_superrefs"):
            w = struct.unpack_from("<I", m, o)[0]; sn2, o2 = sect(w)
            if sn2 and "methname" in sn2: return "sel:" + cstr(o2)
            if sn2 == "__objc_data":
                ro = struct.unpack_from("<I", m, o2 + 16)[0] & ~3; _, oro = sect(ro)
                nm = struct.unpack_from("<I", m, oro + 16)[0]; _, on = sect(nm); return "class:" + cstr(on)
            return "%s->%x" % (sn, w)
        if sn == "__cfstring":
            w = struct.unpack_from("<I", m, o + 8)[0]; _, o2 = sect(w); return "@\"" + cstr(o2) + "\""
        if sn in ("__cstring", "__objc_methname"): return '"' + cstr(o) + '"'
        return sn
    except Exception as e:
        return sn
cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB); cs.skipdata = True
_, o = sect(lo)
regs = {}
for ins in cs.disasm(m[o:o + (hi - lo)], lo):
    mn, op = ins.mnemonic, ins.op_str; note = ""
    if mn == "movw":
        try: r, v = op.split(", #"); regs[r] = int(v, 0)
        except ValueError: pass
    elif mn == "movt":
        try:
            r, v = op.split(", #")
            if r in regs: regs[r] |= int(v, 0) << 16
        except ValueError: pass
    elif mn == "add" and op.endswith(", pc") and op.count(",") == 1:
        r = op.split(",")[0]
        if r in regs: val = (regs[r] + ins.address + 4) & 0xffffffff; note = describe(val); del regs[r]
    print("%x: %s %s %s" % (ins.address, mn, op, ("; " + note) if note else ""))
