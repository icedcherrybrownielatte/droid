import struct, sys, capstone
# usage: dsc_dis.py <cache> start_hex end_hex   (thumb, unslid addresses)
d = open(sys.argv[1], "rb").read()
mo, mc = struct.unpack_from("<II", d, 16)
maps = [struct.unpack_from("<QQQII", d, mo + 32 * i) for i in range(mc)]
def a2o(a):
    for ad, sz, of, _, _ in maps:
        if ad <= a < ad + sz: return a - ad + of
s, e = int(sys.argv[2], 16) & ~1, int(sys.argv[3], 16)
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
o = a2o(s)
for ins in md.disasm(d[o:o + (e - s)], s):
    print("%x: %s %s" % (ins.address, ins.mnemonic, ins.op_str))
