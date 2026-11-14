import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/sched_prim.c")
s = open(p).read()
i = s.index("\t{ static unsigned tcn;")
j = s.index("\n", i)
s = s[:i] + "\t{ static unsigned tcn; extern void ios7m8930_hexN(unsigned int, unsigned int); if (self->task != kernel_task) { tcn++; ios7m8930_hexN(20, 0x10000000U | tcn); ios7m8930_hexN(21, (unsigned)self); ios7m8930_hexN(22, (unsigned)continuation); } }" + s[j:]
open(p, "w").write(s)
print("ok")
