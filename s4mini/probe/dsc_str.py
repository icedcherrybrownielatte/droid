import struct, sys
# usage: dsc_str.py <cache> addr...   prints C string at addr, or CFString (4 words) contents with "cf:" prefix
d = open(sys.argv[1], "rb").read()
mo, mc = struct.unpack_from("<II", d, 16)
maps = [struct.unpack_from("<QQQII", d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    for ad, sz, off, _, _ in maps:
        if ad <= a < ad + sz: return a - ad + off
def cs(a):
    o = a2o(a)
    if o is None: return None
    return d[o:d.index(b"\0", o)][:120]
for arg in sys.argv[2:]:
    if arg.startswith("cf:"):
        a = int(arg[3:], 16); o = a2o(a)
        w = struct.unpack_from("<4I", d, o)
        print(arg, [hex(x) for x in w], cs(w[2]))
    elif arg.startswith("p:"):
        a = int(arg[2:], 16); o = a2o(a)
        p = struct.unpack_from("<I", d, o)[0]
        print(arg, hex(p), cs(p))
    else:
        print(arg, cs(int(arg, 16)))
