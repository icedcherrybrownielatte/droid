import struct, sys
# usage: dsc_lookup.py <cache> addr [addr...]  (addresses hex, unslid)
f = open(sys.argv[1], "rb"); d = f.read()
magic = d[:16]
mo, mc, io, ic = struct.unpack_from("<IIII", d, 16)
maps = [struct.unpack_from("<QQQII", d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    for addr, size, off, _, _ in maps:
        if addr <= a < addr + size: return a - addr + off
    return None
print(magic, [(hex(m[0]), hex(m[1])) for m in maps])
imgs = []
for i in range(ic):
    addr, mt, ino, po, pad = struct.unpack_from("<QQQII", d, io + 32 * i)
    path = d[po:d.index(b"\0", po)].decode()
    imgs.append((addr, path))
imgs.sort()

def syms(base, path):
    o = a2o(base)
    ncmds = struct.unpack_from("<I", d, o + 16)[0]
    p = o + 28; segs = {}; out = []; symtab = None
    for _ in range(ncmds):
        cmd, sz = struct.unpack_from("<II", d, p)
        if cmd == 1:
            name = d[p + 8:p + 24].rstrip(b"\0").decode(); va, vs = struct.unpack_from("<II", d, p + 24)
            segs[name] = (va, vs)
        if cmd == 2: symtab = struct.unpack_from("<IIII", d, p + 8)
        if cmd in (0x22, 0x80000022):  # LC_DYLD_INFO(_ONLY): export trie
            eo, es = struct.unpack_from("<II", d, p + 40)
            def uleb(q):
                v = 0; sh = 0
                while True:
                    b = d[q]; q += 1; v |= (b & 0x7f) << sh; sh += 7
                    if b < 0x80: return v, q
            tb = segs.get("__TEXT", (base, 0))[0]
            stack = [(eo, "")]
            while stack:
                q, pre = stack.pop()
                ts, q2 = uleb(q)
                if ts:
                    fl, q3 = uleb(q2)
                    if not fl & 8:
                        off, _ = uleb(q3); out.append(((tb + off) & ~1, pre))
                q = q2 + ts
                n = d[q]; q += 1
                for _ in range(n):
                    e = d.index(b"\0", q); lab = d[q:e].decode(errors="replace"); q = e + 1
                    co, q = uleb(q); stack.append((eo + co, pre + lab))
        if cmd == 0x26:  # LC_FUNCTION_STARTS
            fo, fs = struct.unpack_from("<II", d, p + 8)
            q = fo; a = segs.get("__TEXT", (base, 0))[0]
            while q < fo + fs:
                v = 0; sh = 0
                while True:
                    b = d[q]; q += 1; v |= (b & 0x7f) << sh; sh += 7
                    if b < 0x80: break
                if v == 0: break
                a += v; out.append((a, "fn_%x" % a))
        p += sz
    if symtab:
        so, ns, sto, ss = symtab
        for k in range(ns):
            sx, ty, sc, de, va = struct.unpack_from("<IBBHI", d, so + 12 * k)
            if (ty & 0x0e) == 0x0e and va:
                nm = d[sto + sx:d.index(b"\0", sto + sx)].decode(errors="replace")
                out.append((va & ~1, nm))
    return segs, sorted(out)

for s in sys.argv[2:]:
    a = int(s, 16) & ~1
    cand = [im for im in imgs if im[0] <= a]
    base, path = cand[-1]
    segs, sy = syms(base, path)
    best = max([x for x in sy if x[0] <= a], default=(base, "?"), key=lambda x: (x[0], not x[1].startswith("fn_")))
    print(s, path, "%s+0x%x" % (best[1], a - best[0]), "TEXT", hex(segs["__TEXT"][0]), hex(segs["__TEXT"][1]))
