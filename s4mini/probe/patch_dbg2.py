import os
root = os.path.expanduser("~/xnu-j1/xnu")
p = root + "/iokit/Kernel/IOService.cpp"
s = open(p).read()
a = "        ios7m8930_hexN(17, ios7m8930_dbg[0]); ios7m8930_hexN(18, ios7m8930_dbg[1]); ios7m8930_hexN(19, ios7m8930_dbg[2]); ios7m8930_hexN(20, ios7m8930_dbg[3]);"
assert a in s
s = s.replace(a, "", 1)
# park rows 13..16 -> dbg
i = s.index("        ios7m8930_hexN(13, (gCfgStarts")
j = s.index("ios7m8930_hexN(16, ++pn);", i) + len("ios7m8930_hexN(16, ++pn);")
s = s[:i] + "        ++pn; ios7m8930_hexN(13, ios7m8930_dbg[0]); ios7m8930_hexN(14, ios7m8930_dbg[1]); ios7m8930_hexN(15, ios7m8930_dbg[2]); ios7m8930_hexN(16, ios7m8930_dbg[3]);" + s[j:]
open(p, "w").write(s)
print("ok")
