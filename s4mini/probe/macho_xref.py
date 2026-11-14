import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
# usage: macho_xref.py <binary> <string>   finds the selref/cstring and thumb code that loads it via movw/movt+add pc
path, needle = sys.argv[1], sys.argv[2].encode()
d = open(path, "rb").read()
off = 0
if struct.unpack_from(">I", d, 0)[0] == 0xcafebabe:
    n = struct.unpack_from(">I", d, 4)[0]
    for i in range(n):
        ct, cst, o, sz, al = struct.unpack_from(">5I", d, 8 + 20 * i)
        if ct == 12 and cst == 11: off = o  # armv7s
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
            sn = m[q:q + 16].rstrip(b"\0").decode(); sg = m[q + 16:q + 32].rstrip(b"\0").decode()
            va, vs, fo = struct.unpack_from("<III", m, q + 32)
            sects.append((sn, sg, va, vs, fo))
    p += sz
def v2o(v):
    for sn, sg, va, vs, fo in sects:
        if va <= v < va + vs and fo: return v - va + fo
def o2v(o):
    for sn, sg, va, vs, fo in sects:
        if fo and fo <= o < fo + vs: return o - fo + va
targets = set()
i = m.find(needle + b"\0")
while i >= 0:
    if m[i - 1:i] == b"\0":
        sv = o2v(i); targets.add(sv); print("string at", hex(sv))
    i = m.find(needle + b"\0", i + 1)
for sn, sg, va, vs, fo in sects:
    if sn in ("__objc_selrefs", "__cfstring", "__objc_methname") or True:
        if sn in ("__objc_selrefs", "__cfstring"):
            step = 4 if sn == "__objc_selrefs" else 16
            for a in range(va, va + vs, step):
                w = struct.unpack_from("<I", m, fo + a - va + (8 if step == 16 else 0))[0]
                if w in targets: print(sn, "ref at", hex(a)); targets.add(a)
text = [s for s in sects if s[0] == "__text"][0]
_, _, tva, tvs, tfo = text
cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB); cs.skipdata = True
regs = {}
for ins in cs.disasm(m[tfo:tfo + tvs], tva):
    mn, op = ins.mnemonic, ins.op_str
    if mn == "movw":
        r, v = op.split(", #"); regs[r] = int(v, 0)
    elif mn == "movt":
        r, v = op.split(", #")
        if r in regs: regs[r] |= int(v, 0) << 16
    elif mn == "add" and op.endswith(", pc") and op.count(",") == 1:
        r = op.split(",")[0]
        if r in regs:
            val = (regs[r] + ins.address + 4) & 0xffffffff
            if val in targets: print("xref", hex(ins.address), hex(val))
            del regs[r]
