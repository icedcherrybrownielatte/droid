import os
root = os.path.expanduser("~/xnu-j1/xnu/")
p = root + "osfmk/kern/sched_prim.c"
s = open(p).read()
i = s.index("\t{ static unsigned tcn;")
j = s.index("\n", i)
s = s[:i] + "\t{ static unsigned tcn; extern void ios7m8930_hexN(unsigned int, unsigned int); tcn++; ios7m8930_hexN(20, tcn); ios7m8930_hexN(21, (unsigned)self); ios7m8930_hexN(22, (unsigned)continuation); }" + s[j:]
open(p, "w").write(s)
p = root + "pexpert/arm/pe_msm8930_serrano.c"
s = open(p).read()
i = s.index("void ios7m8930_tbr(")
s = s[:i] + "void ios7m8930_tbr(unsigned int pend, void *thr){ static unsigned n; n++; ios7m8930_hexN(23, (n << 24) | (pend & 0xffffffU)); (void)thr; }\n"
open(p, "w").write(s)
print("ok")
